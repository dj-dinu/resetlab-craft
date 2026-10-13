from pathlib import Path
import tempfile
import unittest
import os
from unittest.mock import patch
from music_library_lab.cache import AnalysisCache, MARKER
from music_library_lab.server import PROJECT


class CacheRetentionTests(unittest.TestCase):
    def setUp(self):
        base = PROJECT / '.work/test-temp'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.work = Path(self.temp.name)
        self.cache = AnalysisCache(self.work)

    def tearDown(self):
        self.temp.cleanup()

    def job(self, number):
        identifier = f'{number:032x}'
        output = self.cache.prepare(identifier)
        output.mkdir()
        (output / 'report.json').write_text('{}', encoding='utf-8')
        return identifier, output

    def test_finished_retention_preserves_active_legacy_exports_and_music(self):
        active, active_output = self.job(99)
        legacy = self.work / 'audits/old'
        legacy.mkdir(parents=True)
        (legacy / 'report.json').write_text('old', encoding='utf-8')
        music = self.work / 'original.wav'
        music.write_bytes(b'original audio')
        export = self.work / 'saved-report.json'
        export.write_text('exported', encoding='utf-8')
        for i in range(5):
            identifier, _ = self.job(i)
            self.cache.finish(identifier)
        self.assertEqual(sorted(p.name for p in self.cache.root.iterdir()), [f'{i:032x}' for i in (2,3,4,99)])
        self.assertTrue(active_output.exists())
        self.assertEqual(music.read_bytes(), b'original audio')
        self.assertEqual(export.read_text(), 'exported')
        self.assertEqual((legacy / 'report.json').read_text(), 'old')

    def test_unexpected_audio_and_unmarked_directories_are_never_removed(self):
        protected, output = self.job(0)
        audio = output / 'private.wav'
        audio.write_bytes(b'preserve this audio')
        self.cache.finish(protected)
        unknown = self.cache.root / f'{100:032x}'
        unknown.mkdir()
        (unknown / 'report.json').write_text('unmarked', encoding='utf-8')
        for i in range(1,6):
            identifier, _ = self.job(i)
            self.cache.finish(identifier)
        self.assertEqual(audio.read_bytes(), b'preserve this audio')
        self.assertEqual((unknown / 'report.json').read_text(), 'unmarked')

    def test_invalid_identifier_cannot_escape_cache(self):
        for identifier in ('../music', '', 'C:/music', 'x' * 32):
            with self.assertRaises(ValueError):
                self.cache.prepare(identifier)
        self.assertFalse(self.cache.root.exists())

    def test_marker_tampering_preserves_cache(self):
        identifier, output = self.job(0)
        marker = output.parent / MARKER
        marker.write_text('{"owner":"other"}', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.cache.finish(identifier)
        self.assertTrue(output.exists())

    def test_new_music_arriving_during_cleanup_is_preserved(self):
        identifier, output = self.job(0)
        self.cache.finish(identifier)
        real_unlink = Path.unlink
        music = output / 'arriving.wav'
        def interrupted_unlink(path, *args, **kwargs):
            if path.name == 'report.json':
                music.write_bytes(b'preserve arriving music')
            return real_unlink(path, *args, **kwargs)
        with patch('pathlib.Path.unlink', interrupted_unlink):
            self.cache._remove_generated(output.parent)
        self.assertEqual(music.read_bytes(), b'preserve arriving music')
        self.assertTrue((output.parent / MARKER).exists())

    def test_hard_linked_marker_is_not_written_or_removed(self):
        identifier, output = self.job(0)
        marker = output.parent / MARKER
        alias = self.work / 'preserve-marker.json'
        os.link(marker, alias)
        before = alias.read_bytes()
        with self.assertRaises(ValueError):
            self.cache.finish(identifier)
        self.assertEqual(alias.read_bytes(), before)
        self.assertTrue(output.exists())
