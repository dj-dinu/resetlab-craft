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
            if not job or job.get("kind") != "audit" or job.get("status") != "complete":
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
            js_api=bridge, width=1280, height=840, min_size=(960, 640),
            background_color="#f6f5f0",
        )
        bridge._window = window
        # Windows uses the installed Edge WebView2 runtime; macOS uses WKWebView.
        renderer = "edgechromium" if os.name == "nt" else None
        webview.start(gui=renderer, debug=args.debug, private_mode=True)
    finally:
        session.stop()


if __name__ == "__main__":
    main()
