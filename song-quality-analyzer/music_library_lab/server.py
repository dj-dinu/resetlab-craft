"""Build-only driver for a separate CI app; absent from the distributable app.

Uses real Cocoa/WKWebView, the shipped page, HTTP server and frozen worker.
Only the save-dialog selection is substituted. This does not qualify Finder
drag, native pickers, TCC, Gatekeeper, trackpads or clean-user installation.
"""
import sys

if '--scanner-worker' not in sys.argv:
    import hashlib
    import json
    import os
    from pathlib import Path
    import queue
    import subprocess
    import time
    import webview
    from music_library_lab import desktop

    report_path = Path(os.environ['SPECTRACRAFT_UI_REPORT']).resolve()
    fixture_root = Path(os.environ['SPECTRACRAFT_UI_FIXTURES']).resolve()
    results = {'passed': False, 'instrumented_bundle': True, 'renderer': 'Cocoa/WKWebView',
               'native_dialogs_automated': False, 'checks': [], 'screenshots': []}
    session = None
    base_session = desktop.LocalSession
    original_start = webview.start

    class TestSession(base_session):
        def __init__(self, *args, **kwargs):
            global session
            super().__init__(*args, **kwargs)
            session = self

    desktop.LocalSession = TestSession

    def driver():
        window = webview.windows[0]
        replies = queue.Queue()
        def qa_result(payload):
            replies.put(payload)
        def js(code):
            window.run_js('Promise.resolve().then(() => {' + code +
                          '}).then(value => window.pywebview.api.qa_result({ok:true,value}),' +
                          'error => window.pywebview.api.qa_result({ok:false,error:String(error)}));')
            reply = replies.get(timeout=30)
            assert reply.get('ok'), reply
            return reply.get('value')
        def until(condition, description, timeout=60):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if condition():
                    return
                time.sleep(.1)
            raise AssertionError('Timed out: ' + description)
        def dom(expression):
            return js('return (' + expression + ');')
        def click(identifier):
            js('document.getElementById(' + json.dumps(identifier) + ').click();')
        def check(name, **details):
            results['checks'].append(dict(name=name, passed=True, **details))
        def job():
            with session.state.lock:
                audits = [j for j in session.state.jobs.values() if j['kind'] == 'audit']
                return audits[-1] if audits else None
        def load(path, count):
            js('const input=document.getElementById("root-path"); input.value=' + json.dumps(str(path)) +
               '; input.dispatchEvent(new Event("input")); input.dispatchEvent(new Event("change"));')
            until(lambda: dom('document.getElementById("track-count").textContent === ' + json.dumps(str(count)) +
                              ' && !document.getElementById("audit-button").disabled'), 'inventory ' + str(count))
        def analyze():
            previous = job()
            click('audit-button')
            until(lambda: job() is not None and job() is not previous, 'new audit')
            until(lambda: dom('!document.getElementById("job-panel").hidden'), 'progress shown')
        def complete():
            until(lambda: job()['status'] != 'running', 'complete audit', timeout=180)
            assert job()['status'] == 'complete', job().get('error')
            until(lambda: dom('!document.getElementById("export-button").disabled'), 'results rendered')
        def pause():
            until(lambda: dom('!document.getElementById("pause-button").disabled'), 'pause enabled')
            click('pause-button')
            until(lambda: job()['progress'].get('paused') is True, 'decoder pause ackn…7287 tokens truncated…"codec",
                                "container", "bit_depth", "encoded_bitrate", "integrity_check",
                                "declared_duration_seconds", "decoded_duration_seconds", "error"}
                summaries.extend({key: value[:700] if key == "error" and isinstance(value, str) else value
                                  for key, value in row.items() if key in compact_keys}
                                 for row in result.get("records", []))
                result.update(selected_total=total, completed_tracks=offset + len(batch),
                              completed_batches=index + 1, batch_count=batches,
                              report_scope="Latest completed batch; folder summary includes all completed batches")
                with self.lock:
                    job.update(result=result, completed_batches=index + 1, summaries=list(summaries))
            return job["result"]
        return self._start_job("audit", len(tracks), operation,
                               {"source_root": str(root), "source_kind": "file" if Path(root).is_file() else "folder",
                                "selected_ids": [row["id"] for row in tracks]})

    def active_job(self):
        with self.lock:
            return next(({"id": key, "kind": value["kind"]} for key, value in self.jobs.items()
                         if value["status"] == "running"), None)

    def scan_job(self, root):
        return self._start_job("scan", None, lambda job_id, update, cancel:
                               scan_library(root, progress=update, cancel=cancel), {"source_root": str(root)})


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(15)
            super().setup()

        def log_message(self, *_):
            pass

        def send(self, value, status=200, content_type="application/json; charset=utf-8", download=False):
            data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'; form-action 'self'")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="spectracraft-report.json"')
            self.end_headers()
            self.wfile.write(data)

        def allowed(self, api=False):
            host = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != host:
                self.send({"error": "Only the local application host is accepted."}, 403)
                return False
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + host:
                self.send({"error": "Cross-origin requests are refused."}, 403)
                return False
            if api and not secrets.compare_digest(self.headers.get("X-Local-Token", "").encode("utf-8"), state.token.encode("ascii")):
                self.send({"error": "Open the local launch link to authenticate this session."}, 403)
                return False
            return True

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if not self.allowed(path.startswith("/api/")):
                return
            try:
                if path == "/api/config":
                    self.send({"app": APP_NAME, "suite": SUITE_NAME, "tool": TOOL_NAME, "version": __version__,
                               "ui_preferences": interface_preferences(),
                               "default_root": "", "scanner_available": state.scanner.is_file(),
                               "engine_source": "bundled canonical snapshot" if FROZEN else "configured canonical source",
                               "quality_rule": "HQ: >=40% at or above 20 kHz; MQ: otherwise >=40% at or above 18 kHz; LQ: otherwise. Bitrate is informational.",
                               "python_version": sys.version.split()[0], "manager_enabled": False,
                               "coverage_threshold": 0.4, "quality_rule_version": "2026-10-13-40-percent-at-or-above",
                               "max_tracks_per_run": MAX_TRACKS_PER_RUN,
                               "max_selected_tracks": MAX_INVENTORY_TRACKS, "active_job": state.active_job(),
                               "max_inventory_tracks": MAX_INVENTORY_TRACKS,
                               "supported_formats": list(SUPPORTED_FORMATS),
                               "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
                               "decoder_status": {"mp3_configured": bool(state.decoder),
                                                  "additional_formats_available": find_spec("av") is not None},
                               "format_scope": "Actual codec/profile and audio-only container support are checked during analysis.",
                               "cache_retention": "The latest three finished owned analysis caches are retained. Active, legacy or unrecognized folders are preserved; exported reports and music are never cleanup targets."})
                elif path.startswith("/api/jobs/") or path.startswith("/api/report/"):
                    identifier = path.rsplit("/", 1)[-1]
                    with state.lock:
                        job = state.jobs.get(identifier)
                        if job:
                            snapshot = {k: v for k, v in job.items() if k not in {"cancel_event", "pause_event", "selected_ids"}}
                            pause = job.get("pause_event")
                            snapshot["pause_requested"] = bool(pause and pause.is_set())
                            query = parse_qs(urlsplit(self.path).query)
                            after_batch = int(query.get("after_batch", ["-1"])[0])
                            if job["status"] == "running" and after_batch >= job.get("completed_batches", 0):
                                snapshot["result"] = None
                                snapshot["summaries"] = []
                            if query.get("with_inventory") == ["1"]:
                                snapshot["inventory"] = state.inventories.get(job.get("source_root"), [])
                                snapshot["selected_ids"] = job.get("selected_ids", [])
                    if job is None:
                        self.send({"error": "Unknown analysis."}, 404)
                    elif path.startswith("/api/report/"):
                        ready = snapshot["status"] == "complete" or snapshot["status"] in {"cancelled", "failed"} and snapshot.get("completed_batches", 0) > 0
                        if not ready or snapshot["kind"] != "audit" or not snapshot.get("result"):
                            self.send({"error": "The report is not ready."}, 409)
                        else:
                            self.send(sanitize_report(snapshot["result"]), download=True)
                    else:
                        self.send(snapshot)
                else:
                    files = {"/": ("index.html", "text/html; charset=utf-8"),
                             "/index.html": ("index.html", "text/html; charset=utf-8"),
                             "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                             "/styles.css": ("styles.css", "text/css; charset=utf-8"),
                             "/theme.css": ("theme.css", "text/css; charset=utf-8"),
                             "/theme.js": ("theme.js", "text/javascript; charset=utf-8"),
                             "/scroll-engine.js": ("scroll-engine.js", "text/javascript; charset=utf-8"),
                             "/library-view.js": ("library-view.js", "text/javascript; charset=utf-8"),
                             "/license.txt": ("LICENSE", "text/plain; charset=utf-8"),
                             "/mark.svg": ("mark.svg", "image/svg+xml")}
                    if path not in files:
                        self.send({"error": "Not found"}, 404)
                    else:
                        filename, kind = files[path]
                        content = ((PROJECT / "LICENSE") if filename == "LICENSE" else (STATIC / filename)).read_bytes()
                        if filename == "index.html":
                            preferences = interface_preferences()
                            content = content.replace(b'<html lang="en">',
                                ('<html lang="en" data-initial-theme="' + preferences["theme"] + '">').encode())
                        self.send(content, content_type=kind)
            except Exception:
                self.send({"error": "The local resource could not be loaded. Restart the app or check its installation."}, 500)

        def do_POST(self):
            if not self.allowed(api=True):
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4 * 1024 * 1024:
                    self.send({"error": "Invalid request size."}, 413)
                    return
                if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                    self.send({"error": "JSON is required."}, 415)
                    return
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, dict):
                    raise ValueError("Expected a JSON object.")
                if self.path == "/api/preferences":
                    with state.lock:
                        self.send(save_interface_preferences(value))
                elif self.path == "/api/scan":
                    root = str(_source(value["root"]))
                    self.send({"job_id": state.scan_job(root)})
                elif self.path == "/api/audit":
                    root = str(_source(value["root"]))
                    with state.lock:
                        inventory = state.inventories.get(root)
                    if inventory is None:
                        raise ValueError("Read this folder or file first.")
                    submitted = value.get("tracks", [])
                    if not isinstance(submitted, list) or len(submitted) > MAX_INVENTORY_TRACKS:
                        raise ValueError(f"Select no more than {MAX_INVENTORY_TRACKS} inventoried tracks.")
                    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in submitted):
                        raise ValueError("Select tracks from the current inventory.")
                    ids = {row["id"] for row in submitted if row.get("enabled", True)}
                    if len(ids) != sum(bool(row.get("enabled", True)) for row in submitted):
                        raise ValueError("A selected track was submitted more than once.")
                    lookup = {row["id"]: row for row in inventory}
                    if not ids or not ids.issubset(lookup):
                        raise ValueError("Select tracks from the current inventory.")
                    if any(not lookup[key].get("enabled") for key in ids):
                        raise ValueError("A selected file is not a readable ordinary audio file. Rescan the folder.")
                    tracks = [dict(lookup[row["id"]], enabled=True) for row in submitted if row.get("enabled", True)]
                    self.send({"job_id": state.job(root, tracks)})
                elif self.path == "/api/pause":
                    if type(value.get("paused")) is not bool:
                        raise ValueError("Choose pause or resume.")
                    with state.lock:
                        job = state.jobs[value["job_id"]]
                        if job["kind"] != "audit":
                            raise ValueError("Only audio analysis can be paused.")
                        if value["paused"]:
                            job["pause_event"].set()
                        else:
                            job["pause_event"].clear()
                    self.send({"pause_requested": value["paused"], "processing": job["status"] == "running"})
                elif self.path == "/api/cancel":
                    with state.lock:
                        job = state.jobs[value["job_id"]]
                        job["cancel_event"].set()
                    self.send({"requested": True})
                elif self.path == "/api/shutdown":
                    self.send({"stopping": True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                else:
                    self.send({"error": "This analyzer release has no library-modification endpoints."}, 404)
            except (ValueError, KeyError, OSError) as exc:
                self.send({"error": str(exc)}, 400)
            except Exception:
                self.send({"error": "Local operation failed. Rescan or restart the app."}, 500)
    return Handler


def main():
    parser = argparse.ArgumentParser(description="Local " + APP_NAME)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--scanner")
    parser.add_argument("--decoder")
    args = parser.parse_args()
    state = State(args.scanner, args.decoder)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(state))
    url = f"http://127.0.0.1:{server.server_port}/#token={state.token}"
    print("LOCAL_APP " + json.dumps({"url": url, "port": server.server_port, "manager_enabled": False}), flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with state.lock:
            for job in state.jobs.values():
                job["cancel_event"].set()
        server.server_close()


if __name__ == "__main__":
    main()
