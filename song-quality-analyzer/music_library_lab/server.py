"""Loopback-only local prototype, not an internet-hosted server."""
from __future__ import annotations

import argparse
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler
from importlib.util import find_spec
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import uuid
import webbrowser
from urllib.parse import parse_qs, urlsplit

from . import __version__, APP_NAME, SUITE_NAME, TOOL_NAME
from .analyzer import analyze_tracks, MAX_TRACKS_PER_RUN
from .inventory import scan_library, music_source as _source, SUPPORTED_EXTENSIONS, SUPPORTED_FORMATS, MAX_INVENTORY_TRACKS
from .cache import AnalysisCache
from .loopback_server import LoopbackHTTPServer

FROZEN = bool(getattr(sys, "frozen", False))
PROJECT = Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parent.parent
STATIC = PROJECT / "music_library_lab" / "static"
if os.getenv("MUSIC_LIBRARY_WORK_DIR"):
    WORK = Path(os.environ["MUSIC_LIBRARY_WORK_DIR"]).expanduser().absolute()
elif FROZEN:
    WORK = (Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "SongQualityAnalyzer"
            if os.name == "nt" else Path.home() / "Library" / "Caches" / "SongQualityAnalyzer")
else:
    WORK = PROJECT / ".work"
MAX_INVENTORIES = 3
UI_PREFERENCE_CHOICES = {
    "theme": ("system", "light", "dark"),
    "scrolling": ("smooth", "native"),
    "text_size": ("90", "100", "110", "125", "150"),
}

def interface_preferences():
    defaults = {"theme": "system", "scrolling": "smooth", "text_size": "100"}
    path = WORK / "ui-preferences.json"
    try:
        if path.stat().st_size > 4096:
            return defaults
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return defaults
        for key, choices in UI_PREFERENCE_CHOICES.items():
            if value.get(key) in choices:
                defaults[key] = value[key]
    except (OSError, ValueError):
        pass
    return defaults

def save_interface_preferences(value):
    choices = UI_PREFERENCE_CHOICES
    if not value or any(key not in choices or value[key] not in choices[key] for key in value):
        raise ValueError("Only appearance, text size and scrolling preferences can be saved.")
    saved = interface_preferences() | value
    WORK.mkdir(parents=True, exist_ok=True)
    temporary = WORK / ("ui-preferences-" + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(saved), encoding="utf-8")
        temporary.replace(WORK / "ui-preferences.json")
    finally:
        temporary.unlink(missing_ok=True)
    return saved


def sanitize_report(result: dict) -> dict:
    """Portable report: opt in fields; never export local absolute/cache paths.

Relative filenames and artist/title remain useful report content. Decoder error
strings can contain arbitrary OS paths, so exported failures use generic text.
Private job details and the on-disk diagnostic report remain local.
"""
    allowed = {"id", "source_path", "source_sha256", "artist", "title", "status", "quality", "size",
               "duration_seconds", "sample_rate", "channels", "codec", "codec_profile", "container",
               "bit_depth", "encoded_bitrate", "coverage_20khz", "coverage_15khz", "seconds_20khz",
               "seconds_15khz", "time_bins", "spectrogram", "analysis_limits", "decoder",
               "decoded_sample_format", "channel_layout", "attached_picture_streams",
               "native_frequency_ceiling_hz", "analysis_context", "unanalyzable_tail_seconds",
               "silent_seconds", "non_active_seconds", "spectrum_evidence_status", "spectrum_evidence_unavailable_reason",
               "spectrum_evidence_budget_bytes", "spectrum_evidence_bytes", "spectrum_evidence_estimated_peak_bytes",
               "mpeg_layer", "first_frame_bitrate", "codec_metadata_source", "encoded_bitrate_source"}
    allowed.update({"integrity_check", "integrity_note", "declared_duration_seconds", "decoded_duration_seconds",
                    "declared_duration_source", "duration_tolerance_seconds", "duration_difference_seconds", "coverage_threshold", "quality_rule_version"})
    rows = []
    for record in result.get("records", []):
        row = {key: record[key] for key in allowed if key in record}
        private_locations = []
        for field in ("path", "spectrum_file"):
            location = record.get(field)
            if isinstance(location, str) and location:
                replacement = record.get("source_path", "[local audio file]") if field == "path" else "[local spectrum omitted]"
                private_locations.extend((variant, replacement) for variant in
                                         {location, location.replace("\\", "/"), location.replace("/", "\\")})
                parent = str(Path(location).parent)
                if parent not in {".", "/", "\\"} and len(parent) > 3:
                    private_locations.extend((variant, "[local folder omitted]") for variant in
                                             {parent, parent.replace("\\", "/"), parent.replace("/", "\\")})

        def portable(value):
            if isinstance(value, dict):
                return {key: portable(item) for key, item in value.items()
                        if key not in {"path", "spectrum_file", "cache_path", "cache_location", "root", "scanner_path"}}
            if isinstance(value, list):
                return [portable(item) for item in value]
            if isinstance(value, str):
                for secret, replacement in sorted(private_locations, key=lambda item: len(item[0]), reverse=True):
                    value = value.replace(secret, replacement)
                return value
            return value

        row = portable(row)
        if record.get("status") != "analyzed":
            row["quality"] = None
            row["reason"] = ("Decoded audio duration differs from the header declaration. The file may be incomplete or have an incorrect header."
                             if record.get("status") == "integrity_error" else
                             "This file could not be analyzed. Inspect its details locally in the app.")
        rows.append(row)
    return {key: result[key] for key in ("method", "scanner_sha256", "counts", "analyzed", "errors", "total", "audio_files_modified",
                                      "selected_total", "completed_tracks", "completed_batches", "batch_count", "report_scope")
            if key in result} | {"records": rows, "export": "relative paths; local decoder/cache paths omitted"}


class State:
    def __init__(self, scanner=None, decoder=None):
        settings = PROJECT / "local_settings.json"
        config = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() and not FROZEN else {}
        bundled_scanner = PROJECT / "canonical" / "scan_quality.py"
        if FROZEN:
            if scanner and Path(scanner).resolve() != bundled_scanner.resolve():
                raise ValueError("The packaged app uses its bundled canonical engine; external scanner overrides are not supported.")
            # The frozen scanner worker dispatches this exact asset. An inherited
            # developer environment override must not misidentify its engine.
            self.scanner = bundled_scanner
        else:
            self.scanner = Path(scanner or os.getenv("MUSIC_LIBRARY_SCANNER") or config.get("scanner_path", str(bundled_scanner)))
        decoder_name = "libmpg123.0.dylib" if sys.platform == "darwin" else "libmpg123-0.dll"
        bundled_decoder = PROJECT / "decoder" / decoder_name
        self.decoder = decoder or os.getenv("SONG_AUDIT_MPG123_PATH") or config.get("decoder_path", "") or (str(bundled_decoder) if bundled_decoder.is_file() else "")
        self.token = secrets.token_urlsafe(32)
        self.jobs = {}
        self.inventories = OrderedDict()
        self.lock = threading.RLock()
        self.busy = False

    def _start_job(self, kind, total, operation, metadata=None):
        with self.lock:
            if self.busy:
                raise ValueError("Another scan or analysis is running. Wait or cancel it first.")
            self.busy = True
            completed = [key for key, value in self.jobs.items() if value["status"] != "running"]
            for key in completed[:-2]:
                del self.jobs[key]
            job_id = uuid.uuid4().hex
            job = {"id": job_id, "kind": kind, "status": "running",
                   "progress": {"done": 0, "total": total, "message": "Scanning folders" if kind == "scan" else "Starting canonical full-track analysis"},
                   "result": None, "error": None, "cancel_event": threading.Event(), "pause_event": threading.Event(),
                   "completed_batches": 0, "summaries": []}
            self.jobs[job_id] = job
            if metadata:
                job.update(metadata)

        def update(event):
            with self.lock:
                job["progress"] = event

        def work():
            try:
                result = operation(job_id, update, job["cancel_event"].is_set)
                with self.lock:
                    if job["cancel_event"].is_set():
                        job.update(status="cancelled", error="Operation cancelled. Song files were not changed.")
                    else:
                        if kind == "scan":
                            self.inventories[result["root"]] = result["tracks"]
                            self.inventories.move_to_end(result["root"])
                            while len(self.inventories) > MAX_INVENTORIES:
                                self.inventories.popitem(last=False)
                        job.update(status="complete", result=result)
            except InterruptedError as exc:
                with self.lock:
                    job.update(status="cancelled", error=str(exc))
            except Exception as exc:
                with self.lock:
                    job.update(status="failed", error=str(exc))
            finally:
                with self.lock:
                    self.busy = False

        threading.Thread(target=work, daemon=True).start()
        return job_id

    def job(self, root, tracks):
        def operation(job_id, update, cancel):
            cache = AnalysisCache(WORK)
            job = self.jobs[job_id]
            pause = job["pause_event"]
            total = len(tracks)
            batches = (total + MAX_TRACKS_PER_RUN - 1) // MAX_TRACKS_PER_RUN
            summaries = []
            engine_sha = None
            with self.lock:
                job.update(source_root=str(root), source_kind="file" if Path(root).is_file() else "folder",
                           selected_ids=[row["id"] for row in tracks])
            for index, offset in enumerate(range(0, total, MAX_TRACKS_PER_RUN)):
                while pause.is_set():
                    update({"done": offset, "total": total, "paused": True,
                            "batch_index": index + 1, "batch_count": batches,
                            "message": "Paused between batches. Resume to continue."})
                    if job["cancel_event"].wait(.1):
                        raise InterruptedError("Stopped. Completed batches are retained.")
                if cancel():
                    raise InterruptedError("Stopped. Completed batches are retained.")
                batch = tracks[offset:offset + MAX_TRACKS_PER_RUN]
                cache_id = uuid.uuid4().hex
                output = cache.prepare(cache_id)
                def batch_progress(event):
                    update(dict(event, done=offset + min(len(batch), max(0, event.get("done", 0))),
                                total=total, batch_index=index + 1, batch_count=batches))
                try:
                    result = analyze_tracks(self.scanner, Path(root), batch, output, self.decoder,
                                            batch_progress, cancel, paused=pause.is_set)
                finally:
                    cache.finish(cache_id)
                current_sha = result.get("scanner_sha256")
                if engine_sha is not None and current_sha != engine_sha:
                    raise ValueError("The canonical engine changed between batches. Completed earlier batches are retained; restart with a stable engine.")
                engine_sha = current_sha
                compact_keys = {"id", "source_path", "quality", "status", "coverage_20khz", "coverage_15khz",
                                "duration_seconds", "sample_rate", "sample_rate_hz", "channels", "codec",
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
                self.send_header("Content-Disposition", 'attachment; filename="bandprism-report.json"')
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
                               "quality_rule": "HQ: >=40% at or above 20 kHz; MQ: otherwise >=40% at or above 15 kHz; LQ: otherwise. Bitrate is informational.",
                               "python_version": sys.version.split()[0], "manager_enabled": False,
                               "coverage_threshold": 0.4, "quality_rule_version": "2026-10-16-hq20-mq15-40-percent",
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
                                ('<html lang="en" data-initial-theme="' + preferences["theme"] +
                                 '" data-initial-text-size="' + preferences["text_size"] + '">').encode())
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
    server = LoopbackHTTPServer(("127.0.0.1", args.port), make_handler(state))
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
