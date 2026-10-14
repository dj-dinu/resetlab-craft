"""Self-contained tests. Fixtures contain MPEG frames, not private music.

The frame payloads exercise the metadata/encoded-byte engine. They are not
used to claim decoder fidelity or spectral accuracy; those belong to the
canonical scanner's real-track regressions.
"""
import hashlib
import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from mutagen.id3 import ID3, APIC, COMM, TALB, TIT2, TPE1, TCON, TLAN, TXXX

from music_library_lab import core


def fixture(path, *, artist="Fixture Artist", title="Fixture Song", genre="Deep House", version=4):
    path.parent.mkdir(parents=True, exist_ok=True)
    # MPEG-1 Layer III, 128kbps, 44.1kHz, stereo: 417-byte complete frames.
    path.write_bytes((bytes.fromhex("fffb9000") + b"\x00" * 413) * 120)
    tags = ID3()
    encoding = 1 if version == 3 else 3
    if artist:
        tags.add(TPE1(encoding=encoding, text=[artist]))
    tags.add(TIT2(encoding=encoding, text=[title]))
    tags.add(TCON(encoding=encoding, text=[genre]))
    tags.add(TALB(encoding=encoding, text=["Unrelated fixture album"]))
    tags.add(COMM(encoding=encoding, lang="eng", desc="DJ notes", text=["Keep this cue note."]))
    tags.add(APIC(encoding=encoding, mime="image/png", type=3, desc="Cover", data=b"\x89PNG\r\nfixture-artwork"))
    tags.add(TXXX(encoding=encoding, desc="CUSTOM_TEST", text=["Preserve me"]))
    tags.save(path, v2_version=version)
    return path.read_bytes()


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="music-lab-tests-")
        self.root = Path(self.temporary.name).resolve() / "Library"
        self.root.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def scan(self):
        return core.scan_library(str(self.root))

    def plan(self):
        result = self.scan()
        return core.preview_plan(result["root"], result["tracks"])

    def test_inventory_is_read_only_and_excludes_backups(self):
        path = self.root / "original.mp3"
        original = fixture(path)
        fixture(self.root / "_Organization" / "copied.mp3")
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        scanned = self.scan()
        self.assertEqual(len(scanned["tracks"]), 1)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")))
        track = scanned["tracks"][0]
        self.assertEqual(track["original_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(track["vocal_bucket"], "Instrumental & Vocal Samples")
        self.assertEqual(track["group"], "Deep & Soulful House")
        self.assertTrue(track["enabled"])

    def test_missing_artist_remains_analyzable_but_cannot_organize(self):
        fixture(self.root / "unknown.mp3", artist="")
        result = self.scan()
        self.assertTrue(result["tracks"][0]["enabled"])
        self.assertEqual(result["tracks"][0]["artist"], "")
        self.assertFalse(core.preview_plan(result["root"], result["tracks"])["can_apply"])

    def test_corrupt_file_is_reported_and_disabled(self):
        path = self.root / "bad.mp3"
        path.write_bytes(b"This is not a music file")
        scanned = self.scan()
        self.assertFalse(scanned["tracks"][0]["enabled"])
        self.assertTrue(scanned["tracks"][0]["issues"])
        self.assertEqual(path.read_bytes(), b"This is not a music file")

    def test_language_tag_does_not_confirm_vocals(self):
        path = self.root / "language.mp3"
        fixture(path, genre="Organic House")
        tags = ID3(path)
        tags.add(TLAN(encoding=3, text=["eng"]))
        tags.save(path)
        track = self.scan()["tracks"][0]
        self.assertEqual(track["vocal_bucket"], "Instrumental & Vocal Samples")
        self.assertEqual(track["group"], "Chill & Melodic Electronic")
        self.assertTrue(any("TLAN" in item for item in track["evidence"]))

    def test_confirmed_instrumental_melodic_house_uses_exact_group(self):
        path = self.root / "organic.mp3"
        fixture(path, genre="Organic House")
        tags = ID3(path)
        tags.add(TXXX(encoding=3, desc="MUSIC_LIBRARY_VOCAL_BUCKET", text=["Instrumental"]))
        tags.save(path)
        track = self.scan()["tracks"][0]
        self.assertEqual(track["group"], "Chill & Melodic House")

    def test_quality_is_not_inferred_from_bitrate(self):
        fixture(self.root / "normal.mp3")
        track = self.scan()["tracks"][0]
        self.assertEqual(track["quality"], "")
        self.assertGreater(track["original_metadata"]["encoded_bitrate"], 0)
        track["quality"] = "HQ"
        preview = core.preview_plan(str(self.root), [track])
        self.assertFalse(preview["can_apply"])
        self.assertIn("canonical full-spectrum", " ".join(preview["warnings"]))

    def test_quality_evidence_is_bound_to_source(self):
        fixture(self.root / "normal.mp3")
        track = self.scan()["tracks"][0]
        track["quality"] = "HQ"
        track["quality_evidence"] = {"mode": "full-spectrum", "grade": "HQ", "source_sha256": "wrong"}
        self.assertFalse(core.preview_plan(str(self.root), [track])["can_apply"])
        track["quality_evidence"]["source_sha256"] = track["original_sha256"]
        self.assertTrue(core.preview_plan(str(self.root), [track])["can_apply"])

    def test_full_roundtrip_unicode_mix_hq_artwork_and_playlist(self):
        path = self.root / "messy.mp3"
        original = fixture(path, artist="Ártist", title="Ártist - Morning_Mix (Extended Mix) (HQ)")
        playlist = self.root / "favorites.m3u8"
        playlist_original = b"\xef\xbb\xbf#EXTM3U\r\n#EXTINF:5,Fixture\r\nmessy.mp3\r\n"
        playlist.write_bytes(playlist_original)
        audio = core._audio_hash(path)
        plan = self.plan()
        self.assertTrue(plan["can_apply"], plan["warnings"])
        self.assertEqual(plan["entries"][0]["metadata"]["title"], "Morning Mix (Extended Mix) (HQ)")
        result = core.apply_plan(plan)
        destination = self.root / plan["entries"][0]["new_path"]
        self.assertFalse(path.exists())
        self.assertTrue(destination.exists())
        self.assertEqual(core._audio_hash(destination), audio)
        tags = ID3(destination)
        self.assertEqual(str(tags["TIT2"]), "Morning Mix (Extended Mix) (HQ)")
        self.assertEqual(str(tags["TPE1"]), "Ártist")
        self.assertEqual(tags.getall("APIC")[0].data, b"\x89PNG\r\nfixture-artwork")
        self.assertEqual(str(tags["TXXX:CUSTOM_TEST"]), "Preserve me")
        self.assertIn(destination.name.encode("utf-8"), playlist.read_bytes())
        # Restore reloads the journal; it does not depend on in-memory apply state.
        importlib.reload(core)
        restored = core.restore_run(str(self.root), result["run_id"])
        self.assertEqual(restored["changed"], 1)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(playlist.read_bytes(), playlist_original)
        self.assertFalse(destination.exists())
        self.assertEqual(core.list_runs(str(self.root))[0]["state"], "restored")

    def test_id3v23_version_and_unrelated_metadata_preserved(self):
        path = self.root / "v23.mp3"
        fixture(path, title="Old_Title (Dub Mix)", version=3)
        plan = self.plan()
        result = core.apply_plan(plan)
        destination = self.root / plan["entries"][0]["new_path"]
        self.assertEqual(ID3(destination, translate=False).version, (2, 3, 0))
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertTrue(manifest["entries"][0]["metadata_audit"]["artwork_preserved"])
        self.assertGreater(manifest["entries"][0]["metadata_audit"]["unchanged_frame_count"], 2)

    def test_case_insensitive_collision_is_refused_without_writes(self):
        original_a = fixture(self.root / "a.mp3", artist="Same", title="Song")
        original_b = fixture(self.root / "b.mp3", artist="same", title="song")
        plan = self.plan()
        self.assertFalse(plan["can_apply"])
        with self.assertRaises(core.CoreError):
            core.apply_plan(plan)
        self.assertEqual((self.root / "a.mp3").read_bytes(), original_a)
        self.assertEqual((self.root / "b.mp3").read_bytes(), original_b)
        self.assertFalse((self.root / "_Organization").exists())

    def test_source_change_after_scan_or_preview_is_refused(self):
        path = self.root / "source.mp3"
        fixture(path)
        scanned = self.scan()
        plan = core.preview_plan(str(self.root), scanned["tracks"])
        with path.open("ab") as stream:
            stream.write(b"changed")
        self.assertFalse(core.preview_plan(str(self.root), scanned["tracks"])["can_apply"])
        with self.assertRaises(core.CoreError):
            core.apply_plan(plan)
        self.assertFalse((self.root / "_Organization").exists())

    def test_unsafe_paths_and_tampered_plan_are_refused(self):
        fixture(self.root / "source.mp3")
        scanned = self.scan()
        scanned["tracks"][0]["source_path"] = "../escape.mp3"
        self.assertFalse(core.preview_plan(str(self.root), scanned["tracks"])["can_apply"])
        plan = self.plan()
        plan["entries"][0]["new_path"] = "../escape.mp3"
        with self.assertRaises(core.CoreError):
            core.apply_plan(plan)
        with self.assertRaises(core.CoreError):
            core.restore_run(str(self.root), "../../escape")

    def test_existing_destination_is_never_overwritten(self):
        fixture(self.root / "source.mp3")
        plan = self.plan()
        dest = self.root / plan["entries"][0]["new_path"]
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"external file")
        with self.assertRaises(core.CoreError):
            core.apply_plan(plan)
        self.assertEqual(dest.read_bytes(), b"external file")

    def test_unknown_genre_uses_root_needs_review(self):
        fixture(self.root / "source.mp3", genre="Unverified Experimental")
        plan = self.plan()
        self.assertTrue(plan["can_apply"])
        self.assertEqual(plan["entries"][0]["new_path"].split("/")[0], "Needs Review")
        self.assertEqual(len(plan["entries"][0]["new_path"].split("/")), 2)

    def test_restart_recovery_from_interrupted_commit(self):
        path = self.root / "source.mp3"
        original = fixture(path)
        plan = self.plan()
        result = core.apply_plan(plan)
        manifest_path = Path(result["manifest"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # This is the on-disk state after a process stops immediately before
        # recording its last successful commit. Hashes establish what happened.
        manifest["state"] = "applying"
        manifest["entries"][0]["state"] = "destination_written"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        importlib.reload(core)
        self.assertTrue(core.list_runs(str(self.root))[0]["can_restore"])
        core.restore_run(str(self.root), result["run_id"])
        self.assertEqual(path.read_bytes(), original)

    def test_restore_refuses_external_edits_before_restoring_anything(self):
        original = fixture(self.root / "a.mp3", title="First")
        fixture(self.root / "b.mp3", title="Second")
        plan = self.plan()
        result = core.apply_plan(plan)
        destinations = [self.root / e["new_path"] for e in plan["entries"]]
        destinations[1].write_bytes(b"external change")
        with self.assertRaises(core.CoreError):
            core.restore_run(str(self.root), result["run_id"])
        self.assertFalse((self.root / "a.mp3").exists())
        self.assertTrue(destinations[0].exists())
        self.assertNotEqual(destinations[1].read_bytes(), original)

    def test_mid_commit_failure_rolls_back_originals(self):
        a = fixture(self.root / "a.mp3", title="First")
        b = fixture(self.root / "b.mp3", title="Second")
        def progress(event):
            if event["phase"] == "apply" and event["current"] == 1:
                raise RuntimeError("Simulated interface interruption")
        with self.assertRaises(core.CoreError) as caught:
            core.apply_plan(self.plan(), progress=progress)
        self.assertIn("originals were restored", str(caught.exception))
        self.assertEqual((self.root / "a.mp3").read_bytes(), a)
        self.assertEqual((self.root / "b.mp3").read_bytes(), b)
        self.assertEqual(core.list_runs(str(self.root))[0]["state"], "restored")


if __name__ == "__main__":
    unittest.main()
