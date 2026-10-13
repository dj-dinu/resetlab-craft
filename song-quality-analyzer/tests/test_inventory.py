"""Read-only inventory safety and useful filesystem/metadata boundaries."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
import wave

from mutagen.id3 import ID3, TXXX
from music_library_lab.demo import create_demo
from music_library_lab.inventory import scan_library, safe_path, music_root, hash_file, InventoryError, inspect_metadata
from music_library_lab.inventory import music_source
from music_library_lab.server import PROJECT


class ReadOnlyInventoryTests(unittest.TestCase):
    def setUp(self):
        base = PROJECT / ".work" / "test-temp"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def wav(self, name="native sample.wav", sample_rate=32000):
        path = self.root / name
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(sample_rate)
            stream.writeframes(b"\x00\x00" * sample_rate)
        return path

    def test_pcm_metadata_and_original_bytes_are_preserved(self):
        path = self.wav("Unicode caf\u00e9 \u65e5\u672c (mix).WAV")
        before = hash_file(path)
        result = scan_library(str(self.root))
        self.assertEqual(len(result["tracks"]), 1)
        track = result["tracks"][0]
        self.assertTrue(track["enabled"])
        self.assertEqual(track["codec"], "PCM")
        self.assertEqual(track["sample_rate"], 32000)
        self.assertEqual(track["channels"], 1)
        self.assertEqual(track["bit_depth"], 16)
        self.assertEqual(track["quality"], "")
        self.assertEqual(track["original_sha256"], before)
        self.assertEqual(hash_file(path), before)

    def test_single_file_inventory_never_walks_or_reads_siblings(self):
        chosen = self.wav("chosen café (HQ).wav")
        self.wav("do not read.wav")
        before = hash_file(chosen)
        with patch("music_library_lab.inventory.os.walk", side_effect=AssertionError("Must not walk a selected file's parent")):
            result = scan_library(str(chosen))
        self.assertEqual(result["root"], str(chosen.resolve()))
        self.assertEqual(result["source_kind"], "file")
        self.assertEqual([t["source_path"] for t in result["tracks"]], [chosen.name])
        self.assertEqual(result["visited_entries"], 1)
        self.assertEqual(result["tracks"][0]["original_sha256"], before)
        self.assertEqual(hash_file(chosen), before)

    def test_single_file_at_home_keeps_folder_root_restriction(self):
        chosen = self.wav()
        with patch("music_library_lab.inventory.Path.home", return_value=self.root):
            self.assertEqual(music_source(str(chosen)), chosen.resolve())
            with self.assertRaises(InventoryError):
                music_source(str(self.root))

    def test_single_file_rejects_non_audio_missing_sidecars_and_audit_records(self):
        non_audio = self.root / "readme.txt"
        non_audio.write_text("not audio", encoding="utf-8")
        sidecar = self.wav("._metadata.wav")
        audit = self.root / "_Organization"
        audit.mkdir()
        hidden = audit / "record.wav"
        hidden.write_bytes(b"not audio")
        for path in (non_audio, sidecar, hidden, self.root / "missing.wav"):
            with self.subTest(path=path.name), self.assertRaises(InventoryError):
                scan_library(str(path))

    def test_single_file_cancel_preserves_source(self):
        chosen = self.wav()
        before = hash_file(chosen)
        with self.assertRaises(InterruptedError):
            scan_library(str(chosen), cancel=lambda: True)
        self.assertEqual(hash_file(chosen), before)

    def test_bad_manager_tag_does_not_block_readable_audio(self):
        create_demo(self.root)
        path = next(self.root.glob("*.mp3"))
        tags = ID3(path)
        tags.add(TXXX(encoding=3, desc="MUSIC_LIBRARY_VOCAL_BUCKET", text=["irrelevant:manager?tag"]))
        tags.save(path)
        before = hash_file(path)
        result = scan_library(str(self.root))
        self.assertTrue(all(track["enabled"] for track in result["tracks"]))
        self.assertTrue(all("bit_depth" not in track for track in result["tracks"]))
        self.assertEqual(hash_file(path), before)

    @unittest.skipIf(os.name == "nt", "Native POSIX names require native macOS/Linux validation")
    def test_posix_special_names_remain_literal_paths(self):
        for name in ("mix:one?.wav", "literal\\backslash.wav", "sample .wav"):
            self.wav(name)
        result = scan_library(str(self.root))
        self.assertEqual(len(result["tracks"]), 3)
        self.assertTrue(all(track["enabled"] for track in result["tracks"]))
        for track in result["tracks"]:
            self.assertTrue(safe_path(self.root, track["source_path"]).is_file())

    def test_hard_link_aliases_are_read_only_candidates(self):
        first = self.wav()
        alias = self.root / "alias.wav"
        try:
            os.link(first, alias)
        except OSError as exc:
            self.skipTest(str(exc))
        before = hash_file(first)
        result = scan_library(str(self.root))
        self.assertEqual(len(result["tracks"]), 2)
        self.assertTrue(all(track["enabled"] for track in result["tracks"]))
        self.assertEqual(hash_file(first), before)
        self.assertEqual(hash_file(alias), before)
        self.assertEqual(len({track["id"] for track in result["tracks"]}), 2)

    def test_inventory_limit_is_explicit_and_cannot_claim_complete(self):
        self.wav("a.wav")
        self.wav("b.wav")
        result = scan_library(str(self.root), max_tracks=1)
        self.assertEqual(len(result["tracks"]), 1)
        self.assertTrue(result["truncated"])
        self.assertTrue(any("not a complete" in warning for warning in result["warnings"]))

    def test_permission_failure_is_reported(self):
        def blocked_walk(root, followlinks, onerror):
            onerror(PermissionError(13, "denied", str(self.root / "private")))
            yield str(root), [], []
        with patch("music_library_lab.inventory.os.walk", blocked_walk):
            result = scan_library(str(self.root))
        self.assertEqual(result["skipped"]["unreadable"], 1)
        self.assertTrue(any("could not be read" in warning for warning in result["warnings"]))

    def test_cancelled_inventory_stops_before_reading_sources(self):
        path = self.wav()
        before = hash_file(path)
        with self.assertRaises(InterruptedError):
            scan_library(str(self.root), cancel=lambda: True)
        self.assertEqual(hash_file(path), before)

    def test_native_containment_still_rejects_escape(self):
        for relative in ("../outside.wav", str(self.root / "absolute.wav")):
            with self.assertRaises(InventoryError):
                safe_path(music_root(str(self.root)), relative)

    def test_bad_metadata_is_not_a_quality_grade(self):
        path = self.root / "broken.flac"
        path.write_bytes(b"not audio")
        result = scan_library(str(self.root))
        track = result["tracks"][0]
        self.assertTrue(track["enabled"])
        self.assertEqual(track["quality"], "")
        self.assertTrue(track["issues"])

    def test_untagged_flac_is_identified_despite_incompatible_tag_keys(self):
        import av
        import numpy as np
        path = self.root / "untagged.flac"
        with av.open(str(path), mode="w", format="flac") as output:
            stream = output.add_stream("flac", rate=48000)
            stream.layout = "mono"
            frame = av.AudioFrame.from_ndarray(np.zeros((1, 4800), dtype=np.int16), format="s16", layout="mono")
            frame.sample_rate = 48000
            for packet in stream.encode(frame):
                output.mux(packet)
            for packet in stream.encode(None):
                output.mux(packet)
        before = hash_file(path)
        metadata = inspect_metadata(path)
        self.assertEqual(metadata["codec"], "FLAC")
        self.assertEqual(metadata["sample_rate"], 48000)
        self.assertEqual(metadata["bit_depth"], 16)
        self.assertEqual(metadata["artist"], "")
        self.assertEqual(metadata["title"], "")
        result = scan_library(str(self.root))
        self.assertEqual(result["tracks"][0]["codec"], "FLAC")
        self.assertFalse(result["tracks"][0]["issues"])
        self.assertEqual(hash_file(path), before)


if __name__ == "__main__":
    unittest.main()
