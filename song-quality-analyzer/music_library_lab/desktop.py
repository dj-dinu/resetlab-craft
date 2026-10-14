"""A small native window around the local analyzer, with no online services."""
from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from . import __version__, APP_NAME, SUITE_NAME
from .server import State, make_handler, sanitize_report
from .inventory import music_source


class LocalSession:
    def __init__(self, scanner=None, decoder=None):
        self.state = State(scanner, decoder)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.state))
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.url = self.origin + "/#token=" + self.state.token
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.closed = False

    def start(self):
        self.thread.start()

    def stop(self):
        if self.closed:
            return
        self.closed = True
        with self.state.lock:
            for job in self.state.jobs.values():
                event = job.get("cancel_event")
                if event is not None:
                    event.set()
        if self.thread.is_alive():
            self.server.shutdown()
            self.thread.join(timeout=3)
        self.server.server_close()
        # Give cancellation handlers time to reap the decoder and finish their
        # input-preservation checks before the native process exits.
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            with self.state.lock:
                running = any(j.get("status") == "running" for j in self.state.jobs.values())
            if not running:
                break
            time.sleep(.05)


class DesktopBridge:
    """Only user-initiated music selection and report dialogs are exposed."""
    def __init__(self, session, webview_module):
        self._session = session
        self._webview = webview_module
        self._window = None
        self._drop_lock = threading.Lock()
        self._drop_message = None
        self._drop_document = None
        self._drop_available = False

    def drop_status(self):
        return {"available": self._drop_available} if self._local_page() else {"available": False}

    def take_drop(self):
        if not self._local_page():
            return None
        with self._drop_lock:
            message, self._drop_message = self._drop_message, None
        return message

    def _on_drop(self, event):
        if not self._local_page():
            return
        files = []
        try:
            if not isinstance(event, dict):
                raise ValueError("Invalid drop event.")
            transfer = event.get("dataTransfer", {})
            if not isinstance(transfer, dict):
                raise ValueError("Invalid drop event.")
            files = transfer.get("files", [])
            if not isinstance(files, list) or len(files) != 1:
                raise ValueError("Drop one audio file or one folder at a time.")
            path = files[0].get("pywebviewFullPath") if isinstance(files[0], dict) else None
            if not isinstance(path, str) or not path or not Path(path).is_absolute():
                raise ValueError("The desktop could not resolve this drop. Use Add music instead.")
            if getattr(self._session.state, "busy", False):
                raise ValueError("Wait for the current operation to finish, or cancel it before adding music.")
            message = {"path": str(music_source(path))}
        except (ValueError, OSError, TypeError):
            message = {"error": "Drop one accessible audio file or music folder. Links, URLs and unsupported files cannot be loaded."}
            if isinstance(files, list) and len(files) != 1:
                message = {"error": "Drop one audio file or one folder at a time."}
            elif getattr(self._session.state, "busy", False):
                message = {"error": "Wait for the current operation to finish, or cancel it before adding music."}
        with self._drop_lock:
            self._drop_message = message

    def _bind_drop(self):
        """Pinned pywebview 6.2.1 drop adapter, retaining the strict CSP.

        Its DOM.on uses eval, which our CSP forbids. Register the equivalent
        native event dispatcher with run_js instead; no eval or CSP relaxation.
        Full paths still come from pywebview's native WebView2/WKWebView handler.
        """
        if not self._local_page():
            return
        from webview.dom import _dnd_state
        self._unbind_drop()
        document = self._window.dom.document
        self._window.dom._elements[document._node_id] = document
        document._event_handlers["drop"].append(self._on_drop)
        _dnd_state["num_listeners"] += 1
        self._drop_document = document
        try:
            self._window.run_js("""
                if (!window.__spectracraftDropBound) {
                    window.__spectracraftDropBound = true;
                    document.addEventListener('drop', function(event) {
                        event.preventDefault();
                        if (!event.dataTransfer || !event.dataTransfer.files.length) return;
                        window.pywebview._jsApiCallback('pywebviewEventHandler',
                            {event: event, nodeId: 'document'}, 'eventHandler');
                    });
                }
            """)
            self._drop_available = True
        except Exception:
            self._unbind_drop()

    def _unbind_drop(self):
        if self._drop_document is not None:
            from webview.dom import _dnd_state
            callbacks = self._drop_document._event_handlers["drop"]
            if self._on_drop in callbacks:
                callbacks.remove(self._on_drop)
            _dnd_state["num_listeners"] = max(0, _dnd_state["num_listeners"] - 1)
        self._drop_document = None
        self._drop_available = False

    def _local_page(self):
        if self._window is None:
            return False
        current = self._window.get_current_url()
        if not current:
            return False
        parts = urlsplit(current)
        return parts.scheme + "://" + parts.netloc == self._session.origin

    def choose_folder(self):
        if not self._local_page():
            return None
        selection = self._window.create_file_dialog(self._webview.FileDialog.FOLDER)
        return str(selection[0]) if selection else None

    def choose_file(self):
        if not self._local_page():
            return None
        selection = self._window.create_file_dialog(
            self._webview.FileDialog.OPEN, allow_multiple=False,
            file_types=("Audio files (*.mp3;*.wav;*.wave;*.aif;*.aiff;*.flac;*.aac;*.m4a;*.mp4)",),
        )
        return str(selection[0]) if selection else None

    def save_report(self, job_id):
        if not self._local_page():
            return {"error": "Open the local analyzer to save a report."}
        with self._session.state.lock:
            job = self._session.state.jobs.get(job_id)
            ready = job and (job.get("status") == "complete" or job.get("status") in {"cancelled", "failed"} and job.get("completed_batches", 0) > 0)
            if not ready or job.get("kind") != "audit" or not job.get("result"):
                return {"error": "Complete an analysis before saving its report."}
            payload = json.dumps(sanitize_report(job["result"]), ensure_ascii=False, indent=2).encode("utf-8")
        selection = self._window.create_file_dialog(
            self._webview.FileDialog.SAVE,
            save_filename="spectracraft-report.json",
            file_types=("JSON report (*.json)",),
        )
        if not selection:
            return {"cancelled": True}
        target = Path(selection[0])
        if target.suffix.lower() != ".json":
            target = target.with_name(target.name + ".json")
        try:
            # Never overwrite an existing music file or report from this bridge.
            # A new destination is explicit and safely reviewable by the user.
            with target.open("xb") as stream:
                stream.write(payload)
        except FileExistsError:
            return {"error": "That report already exists. Choose a new filename."}
        except OSError:
            return {"error": "The report could not be saved. Check the destination folder and free space."}
        return {"saved": True, "path": str(target)}


def main():
    parser = argparse.ArgumentParser(description=APP_NAME + " desktop alpha")
    parser.add_argument("--scanner")
    parser.add_argument("--decoder")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    import webview
    session = LocalSession(args.scanner, args.decoder)
    bridge = DesktopBridge(session, webview)
    session.start()
    try:
        window = webview.create_window(
            f"{APP_NAME} · {__version__} — by {SUITE_NAME}", session.url,
            # Sizes are logical pixels; allow half-screen windows on scaled displays.
            js_api=bridge, width=1280, height=840, min_size=(420, 360), resizable=True,
            background_color="#f6f5f0",
        )
        bridge._window = window
        window.events.loaded += bridge._bind_drop
        # Windows uses the installed Edge WebView2 runtime; macOS uses WKWebView.
        renderer = "edgechromium" if os.name == "nt" else None
        webview.start(gui=renderer, debug=args.debug, private_mode=True)
    finally:
        bridge._unbind_drop()
        session.stop()


if __name__ == "__main__":
    main()
