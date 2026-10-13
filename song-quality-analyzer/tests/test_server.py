"""Tests local-session authorization and read-only analyzer boundaries."""
from pathlib import Path
import json
import io
import os
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch, MagicMock
from http.server import ThreadingHTTPServer

from music_library_lab.analyzer import AnalysisError, analyze_tracks, file_hash, spectrogram_data
from music_library_lab.core import CoreError
from music_library_lab.demo import create_demo
from music_library_lab.server import State, make_handler, PROJECT, sanitize_report, MAX_INVENTORIES, save_interface_preferences


class LocalServerTests(unittest.TestCase):
    def setUp(self):
        base = PROJECT / ".work" / "test-temp"
        base.mkdir(parents=True, exist_ok=True)
        self.preference_temp = tempfile.TemporaryDirectory(dir=base)
        self.preference_root = Path(self.preference_temp.name)
        self.work_patch = patch("music_library_lab.server.WORK", self.preference_root)
        self.work_patch.start()
        self.state = State(scanner=str(PROJECT / "not-a-scanner.py"))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.state))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.work_patch.stop()
        self.preference_temp.cleanup()

    def request(self, path, data=None, token=True, origin=None, host=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Local-Token"] = self.state.token
        if origin:
            headers["Origin"] = origin
        if host:
            headers["Host"] = host
        request = Request(self.base + path, data=json.dumps(data).encode() if data is not None else None,
                          headers=headers)
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_no_api_without_session_token(self):
        code, _ = self.request("/api/config", token=False)
        self.assertEqual(code, 403)
        code, config = self.request("/api/config")
        self.assertEqual(code, 200)
        self.assertFalse(config["manager_enabled"])

    def test_cross_origin_and_dns_rebinding_hosts_rejected(self):
        self.assertEqual(self.request("/api/config", origin="https://other.example")[0], 403)
        self.assertEqual(self.request("/api/config", host="other.example")[0], 403)

    def test_non_ascii_invalid_token_fails_closed(self):
        request = Request(self.base + "/api/config", headers={"X-Local-Token": "caf\u00e9"})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 403)

    def test_private_read_routes_require_a_token(self):
        for path in ("/api/config", "/api/demo", "/api/jobs/anything", "/api/report/anything"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path, token=False)[0], 403)
        self.assertEqual(self.request("/api/config", origin="null")[0], 403)

    def test_static_headers_restrict_external_content_and_referrers(self):
        with urlopen(self.base + "/", timeout=5) as response:
            headers = response.headers
        policy = headers["Content-Security-Policy"]
        for directive in ("connect-src 'self'", "frame-ancestors 'none'", "object-src 'none'", "form-action 'self'"):
            self.assertIn(directive, policy)
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Cross-Origin-Resource-Policy"], "same-origin")

    def test_missing_static_asset_does_not_reveal_private_paths(self):
        with patch("music_library_lab.server.STATIC", PROJECT / "private-missing-static"):
            code, payload = self.request("/")
        self.assertEqual(code, 500)
        self.assertNotIn(str(PROJECT), json.dumps(payload))
        self.assertNotIn("private-missing-static", json.dumps(payload))

    def test_preferences_survive_a_new_server_session_and_seed_initial_theme(self):
        self.assertEqual(self.request("/api/config")[1]["ui_preferences"],
                         {"theme": "system", "scrolling": "smooth"})
        self.assertEqual(self.request("/api/preferences", {"theme": "dark"}),
                         (200, {"theme": "dark", "scrolling": "smooth"}))
        self.assertEqual(self.request("/api/preferences", {"scrolling": "native"}),
                         (200, {"theme": "dark", "scrolling": "native"}))
        # Desktop sessions use a fresh random port and session token. Storage must
        # survive that boundary without depending on origin-local browser storage.
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.state = State(scanner=str(PROJECT / "not-a-scanner.py"))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.state))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.assertEqual(self.request("/api/config")[1]["ui_preferences"],
                         {"theme": "dark", "scrolling": "native"})
        with urlopen(self.base + "/", timeout=5) as response:
            html = response.read().decode("utf-8")
        self.assertIn('<html lang="en" data-initial-theme="dark">', html)
        self.assertFalse(list(self.preference_root.glob("ui-preferences-*.tmp")))

    def test_preference_writes_require_session_and_local_origin(self):
        saved = self.request("/api/preferences", {"theme": "light"})
        self.assertEqual(saved[0], 200)
        path = self.preference_root / "ui-preferences.json"
        before = path.read_bytes()
        for kwargs in ({"token": False}, {"origin": "https://other.example"},
                       {"host": "other.example"}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.request("/api/preferences", {"theme": "dark"}, **kwargs)[0], 403)
                self.assertEqual(path.read_bytes(), before)

    def test_preference_payload_allowlist_preserves_existing_file(self):
        self.assertEqual(self.request("/api/preferences", {"theme": "dark", "scrolling": "native"})[0], 200)
        path = self.preference_root / "ui-preferences.json"
        before = path.read_bytes()
        for payload in ({}, {"theme": "unknown"}, {"scrolling": "instant"},
                        {"theme": ["dark"]}, {"theme": None}, {"path": "../outside.json"},
                        {"theme": "light", "unknown": True}, ["dark"]):
            with self.subTest(payload=payload):
                self.assertEqual(self.request("/api/preferences", payload)[0], 400)
                self.assertEqual(path.read_bytes(), before)
        self.assertEqual(sorted(item.name for item in self.preference_root.iterdir()), [path.name])

    def test_corrupt_preferences_recover_without_injecting_html(self):
        path = self.preference_root / "ui-preferences.json"
        for text, expected in (("{broken", {"theme": "system", "scrolling": "smooth"}),
                               ('["dark"]', {"theme": "system", "scrolling": "smooth"}),
                               ("x" * 4097, {"theme": "system", "scrolling": "smooth"}),
                               (json.dumps({"theme": '"><script>unsafe</script>', "scrolling": "native"}),
                                {"theme": "system", "scrolling": "native"})):
            with self.subTest(text=text[:40]):
                path.write_text(text, encoding="utf-8")
                self.assertEqual(self.request("/api/config")[1]["ui_preferences"], expected)
                with urlopen(self.base + "/", timeout=5) as response:
                    html = response.read().decode("utf-8")
                self.assertIn('<html lang="en" data-initial-theme="system">', html)
                self.assertNotIn("unsafe", html)
        self.assertEqual(self.request("/api/preferences", {"theme": "light"}),
                         (200, {"theme": "light", "scrolling": "native"}))

    def test_failed_preference_replacement_keeps_prior_choice_and_removes_temp(self):
        self.assertEqual(self.request("/api/preferences", {"theme": "dark"})[0], 200)
        path = self.preference_root / "ui-preferences.json"
        before = path.read_bytes()
        with patch("music_library_lab.server.Path.replace", side_effect=OSError("Simulated replacement failure")):
            with self.assertRaisesRegex(OSError, "replacement failure"):
                save_interface_preferences({"theme": "light"})
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(list(self.preference_root.glob("ui-preferences-*.tmp")))

    def test_no_library_modification_endpoints(self):
        for path in ("/api/apply", "/api/restore", "/api/preview"):
            self.assertEqual(self.request(path, {})[0], 404)

    def test_selected_tracks_must_come_from_inventory(self):
        self.assertEqual(self.request("/api/audit", {"root": str(PROJECT), "tracks": [{"id": "made-up"}]})[0], 400)

    def test_file_inventory_cannot_authorize_a_sibling_or_parent_folder(self):
        chosen = self.preference_root / "chosen.wav"
        sibling = self.preference_root / "sibling.wav"
        chosen.write_bytes(b"chosen"); sibling.write_bytes(b"sibling")
        code, started = self.request("/api/scan", {"root": str(chosen)})
        self.assertEqual(code, 200)
        for _ in range(100):
            job = self.request("/api/jobs/" + started["job_id"])[1]
            if job["status"] != "running":
                break
            threading.Event().wait(.01)
        self.assertEqual(job["status"], "complete")
        self.assertEqual(len(job["result"]["tracks"]), 1)
        self.assertEqual(job["result"]["source_kind"], "file")
        track_id = job["result"]["tracks"][0]["id"]
        self.assertEqual(self.request("/api/audit", {"root": str(chosen.parent), "tracks": [{"id": track_id}]})[0], 400)
        self.assertEqual(self.request("/api/audit", {"root": str(sibling), "tracks": [{"id": track_id}]})[0], 400)
        called = []
        def operation(scanner, source, tracks, *args):
            called.append((str(source), [t["source_path"] for t in tracks]))
            return {"records": [], "audio_files_modified": False}
        with patch("music_library_lab.server.analyze_tracks", operation):
            code, audit = self.request("/api/audit", {"root": str(chosen), "tracks": [{"id": track_id, "source_path": sibling.name}]})
            self.assertEqual(code, 200)
            for _ in range(100):
                if self.state.jobs[audit["job_id"]]["status"] != "running":
                    break
                threading.Event().wait(.01)
        self.assertEqual(called, [(str(chosen.resolve()), [chosen.name])])

    def test_only_explicit_static_assets_are_served(self):
        self.assertEqual(self.request("/local_settings.json")[0], 404)
        self.assertEqual(self.request("/../README.md")[0], 404)

    def test_public_license_is_exact_and_does_not_expand_file_access(self):
        with urlopen(self.base + "/license.txt", timeout=5) as response:
            self.assertEqual(response.read(), (PROJECT / "LICENSE").read_bytes())
            self.assertTrue(response.headers["Content-Type"].startswith("text/plain"))
        for path in ("/LICENSE", "/license.txt/../local_settings.json", "/REUSE_AND_BRANDING.md"):
            self.assertEqual(self.request(path, token=False)[0], 404)

    def test_background_cancel_terminates_job_state(self):
        started = threading.Event()
        def fake_operation(scanner, root, tracks, output_dir, decoder, progress, cancel):
            started.set()
            while not cancel():
                started.wait(.01)
            raise InterruptedError("Cancelled read-only operation")
        with patch("music_library_lab.server.analyze_tracks", fake_operation):
            job_id = self.state.job(str(PROJECT), [{"id": "test"}])
            self.assertTrue(started.wait(2))
            self.assertEqual(self.request("/api/cancel", {"job_id": job_id})[0], 200)
            for _ in range(100):
                if self.state.jobs[job_id]["status"] != "running":
                    break
                threading.Event().wait(.01)
            self.assertEqual(self.state.jobs[job_id]["status"], "cancelled")
            self.assertFalse(self.state.busy)

    def test_scan_is_a_background_job_and_cancelled_scan_is_not_registered(self):
        started = threading.Event()
        def fake_scan(root, progress, cancel):
            started.set()
            progress({"done": 1, "total": None, "message": "Reading audio"})
            while not cancel():
                threading.Event().wait(.01)
            raise InterruptedError("Scan cancelled")
        with patch("music_library_lab.server.scan_library", fake_scan):
            code, started_job = self.request("/api/scan", {"root": str(PROJECT)})
            self.assertEqual(code, 200)
            self.assertTrue(started.wait(2))
            job_id = started_job["job_id"]
            self.assertEqual(self.request("/api/jobs/" + job_id)[1]["kind"], "scan")
            self.assertEqual(self.request("/api/cancel", {"job_id": job_id})[0], 200)
            for _ in range(100):
                if self.state.jobs[job_id]["status"] != "running":
                    break
                threading.Event().wait(.01)
            self.assertEqual(self.state.jobs[job_id]["status"], "cancelled")
            self.assertFalse(self.state.inventories)

    def test_completed_inventory_cache_is_bounded(self):
        def fake_scan(root, progress, cancel):
            return {"root": root, "tracks": [], "warnings": []}
        with patch("music_library_lab.server.scan_library", fake_scan):
            for index in range(MAX_INVENTORIES + 2):
                root = str(PROJECT / f"test-inventory-{index}")
                job_id = self.state.scan_job(root)
                for _ in range(100):
                    if self.state.jobs[job_id]["status"] != "running":
                        break
                    threading.Event().wait(.01)
                self.assertEqual(self.state.jobs[job_id]["status"], "complete")
        self.assertEqual(len(self.state.inventories), MAX_INVENTORIES)
        self.assertLessEqual(len(self.state.jobs), 3)

    def test_report_export_omits_absolute_paths_and_private_decoder_errors(self):
        private = str(PROJECT / "private-user" / "track.flac")
        result = {"method": "canonical", "records": [
            {"source_path": "set/track.flac", "path": private, "spectrum_file": private + ".npz",
             "status": "decode_error", "quality": None, "reason": "Decoder error in " + private,
             "private_metadata": {"path": private}, "analysis_context": ["Failure in " + private],
             "spectrum_evidence_unavailable_reason": "Evidence unavailable for " + private,
             "analysis_limits": {"max_seconds": 86400, "cache_location": private + ".npz"}},
            {"source_path": "track.wav", "path": private, "status": "analyzed", "quality": "HQ",
             "coverage_20khz": .3}], "audio_files_modified": False}
        report = sanitize_report(result)
        encoded = json.dumps(report)
        self.assertNotIn(private, encoded)
        self.assertNotIn("spectrum_file", encoded)
        self.assertEqual(report["records"][0]["source_path"], "set/track.flac")
        self.assertIn("set/track.flac", report["records"][0]["spectrum_evidence_unavailable_reason"])
        self.state.jobs["export-test"] = {"id": "export-test", "kind": "audit", "status": "complete", "result": result}
        code, exported = self.request("/api/report/export-test")
        self.assertEqual(code, 200)
        self.assertEqual(exported, report)


class AnalyzerBoundaryTests(unittest.TestCase):
    def test_integrity_error_cannot_be_exported_as_hq(self):
        result = {"records": [{"source_path": "short.wav", "status": "integrity_error", "quality": "HQ",
                    "integrity_check": "duration_mismatch", "declared_duration_seconds": 240,
                    "decoded_duration_seconds": 60, "declared_duration_source": "WAV declared data sample count"}]}
        row = sanitize_report(result)["records"][0]
        self.assertIsNone(row["quality"])
        self.assertEqual(row["declared_duration_seconds"], 240)
        self.assertEqual(row["decoded_duration_seconds"], 60)
        self.assertIn("incomplete", row["reason"])

    def setUp(self):
        base = PROJECT / ".work" / "test-temp"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_scanner_and_no_selection_fail_without_input_edits(self):
        sample = self.root / "readme.txt"
        sample.write_text("original", encoding="utf-8")
        expected = file_hash(sample)
        with self.assertRaises(AnalysisError):
            analyze_tracks(self.root / "absent.py", self.root, [], self.root / "report")
        self.assertEqual(file_hash(sample), expected)

    def test_path_escape_is_rejected_before_decoder_runs(self):
        scanner = self.root / "source.py"
        scanner.write_text("# not executed", encoding="utf-8")
        outside = self.root.parent / (self.root.name + "-outside.mp3")
        outside.write_bytes(b"input")
        try:
            with self.assertRaises(ValueError):
                analyze_tracks(scanner, self.root,
                               [{"id": "escape", "source_path": "../" + outside.name}], self.root / "report")
        finally:
            outside.unlink()

    def test_changed_input_rejected_before_decoder_runs(self):
        scanner = self.root / "source.py"
        scanner.write_text("# not executed", encoding="utf-8")
        sample = self.root / "sample.mp3"
        sample.write_bytes(b"changed")
        with self.assertRaises(AnalysisError):
            analyze_tracks(scanner, self.root, [{"id": "x", "source_path": sample.name,
                           "original_sha256": "stale"}], self.root / "report")

    def test_single_file_analysis_rejects_a_sibling_selection(self):
        scanner = self.root / "source.py"
        scanner.write_text("# not executed", encoding="utf-8")
        chosen = self.root / "chosen.wav"
        sibling = self.root / "sibling.wav"
        chosen.write_bytes(b"selected")
        sibling.write_bytes(b"private sibling")
        with patch("music_library_lab.analyzer._analyze_tracks") as worker:
            with self.assertRaisesRegex(AnalysisError, "only the audio file"):
                analyze_tracks(scanner, chosen, [{"id": "x", "source_path": sibling.name}], self.root / "report")
            worker.assert_not_called()

    def test_single_file_analysis_at_home_passes_only_that_file(self):
        scanner = self.root / "source.py"
        scanner.write_text("# not executed", encoding="utf-8")
        chosen = self.root / "chosen.wav"
        chosen.write_bytes(b"selected")
        before = file_hash(chosen)
        selected = [{"id": "x", "source_path": chosen.name, "original_sha256": before}]
        with patch("music_library_lab.inventory.Path.home", return_value=self.root), patch("music_library_lab.analyzer._analyze_tracks", return_value={"records": []}) as worker:
            self.assertEqual(analyze_tracks(scanner, chosen, selected, self.root / "report"), {"records": []})
        self.assertEqual(worker.call_args.args[1], chosen)
        self.assertEqual(file_hash(chosen), before)

    def test_disk_full_or_disconnected_file_fails_without_a_grade(self):
        scanner = self.root / "source.py"
        scanner.write_text("# not executed", encoding="utf-8")
        chosen = self.root / "chosen.wav"
        chosen.write_bytes(b"selected")
        before = file_hash(chosen)
        selected = [{"id": "x", "source_path": chosen.name, "original_sha256": before}]
        with patch("music_library_lab.analyzer.subprocess.Popen", side_effect=OSError(28, "No space left on device")):
            with self.assertRaises(OSError):
                analyze_tracks(scanner, chosen, selected, self.root / "disk-full-report")
        self.assertFalse((self.root / "disk-full-report/report.json").exists())
        self.assertEqual(file_hash(chosen), before)
        chosen.unlink()  # Owned temporary fixture simulates disconnected storage.
        with self.assertRaises(ValueError):
            analyze_tracks(scanner, chosen, selected, self.root / "missing-file-report")
        self.assertFalse((self.root / "missing-file-report").exists())

    def test_external_change_is_detected_even_after_cancellation(self):
        scanner = self.root / "source.py"
        scanner.write_text("# not executed", encoding="utf-8")
        sample = self.root / "sample.mp3"
        sample.write_bytes(b"before")
        def interrupted(*args, **kwargs):
            sample.write_bytes(b"external change")
            raise InterruptedError("Cancelled")
        with patch("music_library_lab.analyzer._analyze_tracks", interrupted):
            with self.assertRaisesRegex(AnalysisError, "input changed"):
                analyze_tracks(scanner, self.root, [{"id": "x", "source_path": sample.name}], self.root / "report")

    def test_duplicate_selection_is_refused(self):
        scanner = self.root / "source.py"
        scanner.write_text("# not executed", encoding="utf-8")
        sample = self.root / "sample.mp3"
        sample.write_bytes(b"unchanged")
        selected = [{"id": str(i), "source_path": sample.name} for i in (1, 2)]
        with self.assertRaisesRegex(AnalysisError, "more than once"):
            analyze_tracks(scanner, self.root, selected, self.root / "report")

    def test_decode_error_is_ungraded_and_input_unchanged(self):
        scanner = self.root / "source.py"
        scanner.write_text("# transport stub, no classifier", encoding="utf-8")
        sample = self.root / "broken.flac"
        sample.write_bytes(b"not decodable")
        before = file_hash(sample)
        def fake_process(command, **kwargs):
            destination = Path(command[command.index("--output") + 1])
            destination.write_text(json.dumps({"method": "transport test", "records": [
                {"path": str(sample), "status": "decode_error", "quality": "LQ", "reason": "No decodable audio"}]}), encoding="utf-8")
            proc = MagicMock()
            proc.stdout = io.StringIO("PROGRESS {}\n")
            proc.wait.return_value = 1
            proc.poll.return_value = 1
            return proc
        with patch("music_library_lab.analyzer.subprocess.Popen", fake_process):
            result = analyze_tracks(scanner, self.root, [{"id": "file", "source_path": sample.name,
                                    "original_sha256": before}], self.root / "report")
        self.assertEqual(result["records"][0]["quality"], None)
        self.assertEqual(result["counts"]["LQ"], 0)
        self.assertEqual(result["errors"], 1)
        self.assertEqual(file_hash(sample), before)

    def test_spectrum_positions_do_not_stretch_over_missing_tail(self):
        import numpy as np
        spectrum = self.root / "power.npz"
        np.savez_compressed(spectrum, power=np.ones((2, 1025)), sample_rate=48000,
                            bin_start_seconds=np.array([0., .5]), bin_duration_seconds=np.array([.5, .5]))
        display = spectrogram_data({"spectrum_file": str(spectrum), "duration_seconds": 1.001})
        self.assertEqual(display["start_seconds"], [0., .5])
        self.assertEqual(display["seconds"], [.5, .5])
        self.assertLess(display["start_seconds"][-1] + display["seconds"][-1], display["duration_seconds"])

    def test_packaged_engine_ignores_environment_override_and_refuses_other_explicit_source(self):
        snapshot = self.root / "canonical" / "scan_quality.py"
        snapshot.parent.mkdir()
        snapshot.write_text("# bundled canonical asset", encoding="utf-8")
        external = self.root / "external.py"
        external.write_text("# different engine", encoding="utf-8")
        with patch("music_library_lab.server.FROZEN", True), patch("music_library_lab.server.PROJECT", self.root):
            with patch.dict(os.environ, {"MUSIC_LIBRARY_SCANNER": str(external)}):
                self.assertEqual(State().scanner, snapshot)
                self.assertEqual(State(scanner=str(snapshot)).scanner, snapshot)
                with self.assertRaisesRegex(ValueError, "bundled canonical engine"):
                    State(scanner=str(external))

    def test_engine_change_during_run_prevents_report_publication(self):
        scanner = self.root / "source.py"
        scanner.write_text("# original engine", encoding="utf-8")
        sample = self.root / "sample.wav"
        sample.write_bytes(b"original bytes")
        expected = file_hash(sample)
        destination = self.root / "report"
        def fake_process(command, **kwargs):
            report = Path(command[command.index("--output") + 1])
            report.write_text(json.dumps({"method": "transport test", "records": [
                {"path": str(sample), "status": "decode_error", "quality": None, "reason": "Test transport"}]}), encoding="utf-8")
            scanner.write_text("# changed engine", encoding="utf-8")
            proc = MagicMock()
            proc.stdout = io.StringIO("PROGRESS {}\n")
            proc.wait.return_value = 1
            proc.poll.return_value = 1
            return proc
        with patch("music_library_lab.analyzer.subprocess.Popen", fake_process):
            with self.assertRaisesRegex(AnalysisError, "engine changed"):
                analyze_tracks(scanner, self.root, [{"id": "x", "source_path": sample.name}], destination)
        self.assertFalse((destination / "report.json").exists())
        self.assertEqual(file_hash(sample), expected)


if __name__ == "__main__":
    unittest.main()
