import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from collections import defaultdict
from unittest.mock import patch

from music_library_lab.desktop import DesktopBridge


class Window:
    def __init__(self, url, selection=None):
        self.url, self.selection = url, selection
        self.dialogs = 0
        self.last_dialog = None

    def get_current_url(self):
        return self.url

    def create_file_dialog(self, *args, **kwargs):
        self.dialogs += 1
        self.last_dialog = (args, kwargs)
        return self.selection


class DesktopBridgeTests(unittest.TestCase):
    def setUp(self):
        self.state = SimpleNamespace(lock=threading.RLock(), jobs={
            "job": {"kind": "audit", "status": "complete", "result": {
                "total": 1, "analyzed": 1, "audio_files_modified": False,
                "records": [{"source_path": "Song.mp3", "path": "C:/Private/Song.mp3",
                             "spectrum_file": "C:/Private/cache/spectrum.npz", "quality": "HQ",
                             "status": "analyzed", "coverage_20khz": .8}],
            }},
        })
        self.session = SimpleNamespace(origin="http://127.0.0.1:8765", state=self.state)
        module = SimpleNamespace(FileDialog=SimpleNamespace(FOLDER=1, SAVE=2, OPEN=3))
        self.bridge = DesktopBridge(self.session, module)

    def test_external_page_cannot_open_dialogs_or_export_job(self):
        self.bridge._window = Window("https://example.com/")
        self.assertIsNone(self.bridge.choose_folder())
        self.assertIsNone(self.bridge.choose_file())
        self.assertIn("error", self.bridge.save_report("job"))
        self.assertEqual(self.bridge._window.dialogs, 0)

    def test_local_folder_selection_and_cancel(self):
        self.bridge._window = Window(self.session.origin + "/#library", ("Music folder",))
        self.assertEqual(self.bridge.choose_folder(), "Music folder")
        self.bridge._window.selection = None
        self.assertIsNone(self.bridge.choose_folder())
        self.assertEqual(self.bridge.save_report("job"), {"cancelled": True})

    def test_single_file_picker_and_cancel(self):
        self.bridge._window = Window(self.session.origin + "/#library", ("Music.wav",))
        self.assertEqual(self.bridge.choose_file(), "Music.wav")
        args, kwargs = self.bridge._window.last_dialog
        self.assertEqual(args, (3,))
        self.assertFalse(kwargs["allow_multiple"])
        self.assertIn("*.flac", kwargs["file_types"][0])
        self.bridge._window.selection = None
        self.assertIsNone(self.bridge.choose_file())

    def test_save_uses_sanitized_report_and_adds_json_extension(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "My report"
            self.bridge._window = Window(self.session.origin + "/", (str(destination),))
            result = self.bridge.save_report("job")
            self.assertTrue(result["saved"])
            report = Path(str(destination) + ".json").read_text(encoding="utf-8")
            self.assertNotIn("Private", report)
            self.assertEqual(json.loads(report)["records"][0]["source_path"], "Song.mp3")

    def test_existing_report_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "keep.json"
            destination.write_bytes(b"existing report")
            self.bridge._window = Window(self.session.origin + "/", (str(destination),))
            self.assertIn("error", self.bridge.save_report("job"))
            self.assertEqual(destination.read_bytes(), b"existing report")

    def test_failed_or_scan_jobs_cannot_be_saved_as_measurements(self):
        self.bridge._window = Window(self.session.origin + "/")
        for kind, status in (("scan", "complete"), ("audit", "failed"), ("audit", "running")):
            self.state.jobs["job"].update(kind=kind, status=status)
            self.assertIn("error", self.bridge.save_report("job"))
        self.assertEqual(self.bridge._window.dialogs, 0)

    def test_drop_local_file_or_folder_preserves_sources_and_consumes_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            audio = root / "chosen.wav"
            audio.write_bytes(b"owned fixture")
            self.bridge._window = Window(self.session.origin + "/")
            for source in (audio, root):
                self.bridge._on_drop({"dataTransfer": {"files": [{"pywebviewFullPath": str(source)}]}})
                self.assertEqual(self.bridge.take_drop(), {"path": str(source.resolve())})
                self.assertIsNone(self.bridge.take_drop())
            self.assertEqual(audio.read_bytes(), b"owned fixture")

    def test_drop_rejects_external_page_multiple_items_urls_and_busy_operation(self):
        self.bridge._window = Window("https://example.com")
        self.bridge._on_drop({"dataTransfer": {"files": [{"pywebviewFullPath": "file:///etc/passwd"}]}})
        self.assertIsNone(self.bridge.take_drop())
        self.bridge._window.url = self.session.origin + "/"
        for event in (None, {}, {"dataTransfer": {"files": [{}, {}]}},
                      {"dataTransfer": {"files": [{"pywebviewFullPath": "https://example.com/song.mp3"}]}}):
            self.bridge._on_drop(event)
            self.assertIn("error", self.bridge.take_drop())
        with tempfile.TemporaryDirectory() as temporary:
            self.state.busy = True
            self.bridge._on_drop({"dataTransfer": {"files": [{"pywebviewFullPath": temporary}]}})
            self.assertIn("error", self.bridge.take_drop())

    def test_drop_binding_keeps_csp_and_registers_one_native_receiver(self):
        from webview.dom import _dnd_state
        document = SimpleNamespace(_node_id="document", _event_handlers=defaultdict(list))
        window = Window(self.session.origin + "/")
        window.dom = SimpleNamespace(document=document, _elements={})
        scripts = []
        window.run_js = scripts.append
        self.bridge._window = window
        with patch.dict(_dnd_state, {"num_listeners": 0}):
            try:
                self.bridge._bind_drop()
                self.bridge._bind_drop()
                self.assertEqual(_dnd_state["num_listeners"], 1)
                self.assertEqual(len(document._event_handlers["drop"]), 1)
                self.assertTrue(self.bridge.drop_status()["available"])
                self.assertTrue(all("eval(" not in script for script in scripts))
            finally:
                self.bridge._unbind_drop()
            self.assertEqual(_dnd_state["num_listeners"], 0)


if __name__ == "__main__":
    unittest.main()
