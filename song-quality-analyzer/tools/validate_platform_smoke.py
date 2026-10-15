"""Synthetic platform regression through the sole canonical analyzer, not a classifier."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import sys
import subprocess
import tempfile
import threading

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
if (PROJECT / '.localdeps').is_dir():
    sys.path.insert(0, str(PROJECT / '.localdeps'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, help='macOS .app: exercise its frozen worker in an isolated environment')
    args = parser.parse_args()
    import av
    import numpy as np
    from music_library_lab.analyzer import analyze_tracks
    from music_library_lab.inventory import scan_library
    from tools.audio_test_fixtures import CASES, create_audio
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
        root = Path(temporary).resolve()
        music = root / 'Synthetic café % audio'
        music.mkdir()
        create_audio(music)
        before = {p.name: digest(p) for p in music.iterdir()}
        inventory = scan_library(str(music))
        assert len(inventory['tracks']) == 6 and all(t['enabled'] for t in inventory['tracks'])
        result = analyze_tracks(scanner, music, inventory['tracks'], root / 'analysis',
                                os.getenv('SONG_AUDIT_MPG123_PATH', ''))
        frozen = None
        if args.bundle:
            assert sys.platform == 'darwin', 'The .app check must run on macOS'
            bundle = args.bundle.resolve()
            executable = bundle / 'Contents/MacOS/Spectracraft'
            internal = bundle / 'Contents/Frameworks'
            decoder = internal / 'decoder/libmpg123.0.dylib'
            assert digest(internal / 'canonical/scan_quality.py') == manifest['sha256']
            assert not json.loads((internal / 'build-manifest.json').read_text())['ui_test_driver']
            expected = platform.machine()
            for binary in (executable, decoder):
                assert subprocess.check_output(['/usr/bin/lipo', '-archs', str(binary)], text=True).strip() == expected
            saved_env = os.environ.copy()
            saved_executable = sys.executable
            prior_frozen = getattr(sys, 'frozen', None)
            try:
                for key in list(os.environ):
                    if key.startswith(('PYTHON', 'DYLD_', 'SONG_AUDIT_', 'MUSIC_LIBRARY_')):
                        os.environ.pop(key, None)
                os.environ['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
                os.environ['SONG_AUDIT_MPG123_PATH'] = str(decoder)
                check = subprocess.run([str(executable), '--scanner-worker', '--self-test'],
                                       capture_output=True, text=True, timeout=60, cwd=root)
                assert check.returncode == 0 and 'SELF_TEST passed:' in check.stdout, check.stderr
                sys.executable, sys.frozen = str(executable), True
                frozen = analyze_tracks(internal / 'canonical/scan_quality.py', music, inventory['tracks'],
                                        root / 'frozen-analysis', str(decoder))
                for source, packaged in zip(result['records'], frozen['records'], strict=True):
                    for key in ('source_path', 'status', 'quality', 'duration_seconds', 'coverage_20khz',
                                'coverage_18khz', 'time_bins', 'spectrogram', 'codec', 'sample_rate'):
                        assert source[key] == packaged[key], (source['source_path'], key)
                paused = threading.Event()
                paused.set()
                acknowledged = threading.Event()
                def frozen_progress(event):
                    if event.get('paused') and not acknowledged.is_set():
                        acknowledged.set()
                        threading.Timer(.15, paused.clear).start()
                retry = analyze_tracks(internal / 'canonical/scan_quality.py', music, inventory['tracks'][:1],
                                       root / 'frozen-paused', str(decoder), progress=frozen_progress, paused=paused.is_set)
                assert acknowledged.is_set() and len(retry['records']) == 1
                frozen = {'passed': True, 'native_architecture': expected, 'bundled_decoder_used': True,
                          'source_metrics_time_bins_and_spectrograms_exact': True,
                          'pause_resume_acknowledged': True, 'no_python_or_homebrew_on_path': True,
                          'normal_bundle_without_ui_driver': True}
            finally:
                sys.executable = saved_executable
                if prior_frozen is None and hasattr(sys, 'frozen'):
                    del sys.frozen
                elif prior_frozen is not None:
                    sys.frozen = prior_frozen
                os.environ.clear()
                os.environ.update(saved_env)
        expected = {name: grade for name, _, _, _, grade in CASES}
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
                      frozen_bundle=frozen,
                      records=[dict(file=r['source_path'], grade=r['quality'], codec=r.get('codec'),
                                    duration_seconds=r.get('duration_seconds')) for r in result['records']])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
