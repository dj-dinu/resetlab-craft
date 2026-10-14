"""Synthetic platform regression through the sole canonical analyzer, not a classifier."""
from pathlib import Path
import argparse
from fractions import Fraction
import hashlib
import json
import os
import platform
import sys
import tempfile
import threading

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
if (PROJECT / '.localdeps').is_dir():
    sys.path.insert(0, str(PROJECT / '.localdeps'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    import av
    import numpy as np
    from music_library_lab.analyzer import analyze_tracks
    from music_library_lab.inventory import scan_library
    scanner = PROJECT / 'canonical/scan_quality.py'
    manifest = json.loads((PROJECT / 'canonical/manifest.json').read_text())
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(scanner) == manifest['sha256']
    backend = 'not tested on this platform'
    if sys.platform == 'darwin':
        expected_arch = os.getenv('EXPECTED_ARCHITECTURE')
        if expected_arch:
            assert platform.machine() == {'x64': 'x86_64', 'arm64': 'arm64'}[expected_arch]
        from webview.platforms import cocoa
        assert cocoa is not None
        backend = 'Cocoa backend imported; window not exercised'
    base = PROJECT / '.work/test-temp'
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base, prefix='platform-smoke-') as temporary:
        root = Path(temporary)
        music = root / 'Synthetic café % audio'
        music.mkdir()
        rate = 48000
        t = np.arange(rate * 3, dtype=np.float64) / rate
        def pcm(frequency):
            values = .18 * np.sin(2 * np.pi * 1000 * t) + .18 * np.sin(2 * np.pi * frequency * t)
            return np.round(values * 32767).astype(np.int16).reshape(1, -1)
        cases = [('01 HQ.wav', 'wav', 'pcm_s16le', 22000, 'HQ'),
                 ('02 MQ.aiff', 'aiff', 'pcm_s16be', 18500, 'MQ'),
                 ('03 LQ.flac', 'flac', 'flac', 1000, 'LQ'),
                 ('04 ALAC.m4a', 'ipod', 'alac', 22000, 'HQ'),
                 ('05 AAC.m4a', 'ipod', 'aac', 18500, None),
                 ('06 MP3.mp3', 'mp3', 'libmp3lame', 18500, None)]
        for name, container, codec, frequency, expected in cases:
            with av.open(str(music / name), 'w', format=container) as output:
                stream = output.add_stream(codec, rate=rate)
                stream.layout = 'mono'
                if codec in {'aac', 'libmp3lame'}:
                    stream.bit_rate = 256000
                frame = av.AudioFrame.from_ndarray(pcm(frequency), format='s16', layout='mono')
                frame.sample_rate = rate
                frame.time_base = Fraction(1, rate)
                frame.pts = 0
                for packet in stream.encode(frame):
                    output.mux(packet)
                for packet in stream.encode(None):
                    output.mux(packet)
        before = {p.name: digest(p) for p in music.iterdir()}
        inventory = scan_library(str(music))
        assert len(inventory['tracks']) == 6 and all(t['enabled'] for t in inventory['tracks'])
        result = analyze_tracks(scanner, music, inventory['tracks'], root / 'analysis',
                                os.getenv('SONG_AUDIT_MPG123_PATH', ''))
        expected = {name: grade for name, _, _, _, grade in cases}
        for row in result['records']:
            assert row['status'] == 'analyzed', row.get('reason')
            assert row['quality'] in {'HQ', 'MQ', 'LQ'}
            if expected[row['source_path']]:
                assert row['quality'] == expected[row['source_path']], row['source_path']
        # Exercise real stdin pause/resume acknowledgments with synthetic audio.
        paused = threading.Event()
        paused.set()
        acknowledged = threading.Event()
        def progress(event):
            if event.get('paused') and not acknowledged.is_set():
                acknowledged.set()
                threading.Timer(.15, paused.clear).start()
        retry = analyze_tracks(scanner, music, inventory['tracks'][:1], root / 'paused-analysis',
                               os.getenv('SONG_AUDIT_MPG123_PATH', ''),
                               progress=progress, paused=paused.is_set)
        assert acknowledged.is_set() and len(retry['records']) == 1
        assert all(digest(music / name) == value for name, value in before.items())
        report = dict(passed=True, system=platform.system(), architecture=platform.machine(),
                      python=platform.python_version(), pyav=av.__version__, numpy=np.__version__,
                      canonical_sha256=manifest['sha256'], original_hashes_unchanged=True,
                      pause_resume_acknowledged=True, cocoa_backend=backend,
                      native_gui_exercised=False,
                      records=[dict(file=r['source_path'], grade=r['quality'], codec=r.get('codec'),
                                    duration_seconds=r.get('duration_seconds')) for r in result['records']])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
