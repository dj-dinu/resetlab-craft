"""Owned-fixture runtime checks using only the configured canonical analyzer.

No classifier is implemented here. Results are private in the ignored .work
directory. This checks backend shutdown, not an actual OS window or dialog.
"""
from pathlib import Path
import json
import sys
import threading
import time
import uuid
import wave
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / '.localdeps'))
from music_library_lab.analyzer import analyze_tracks, file_hash
from music_library_lab.inventory import scan_library
from music_library_lab.desktop import LocalSession
from music_library_lab import analyzer


def main():
    settings = json.loads((PROJECT / 'local_settings.json').read_text(encoding='utf-8'))
    work = PROJECT / '.work' / 'launch-runtime' / uuid.uuid4().hex
    work.mkdir(parents=True)
    assert work.resolve().is_relative_to((PROJECT / '.work').resolve())
    report = {'passed': False, 'actual_native_gui_tested': False, 'checks': []}
    try:
        library = work / 'large-inventory'
        library.mkdir()
        for i in range(10001):
            (library / f'{i:05}.wav').write_bytes(b'owned corrupt synthetic fixture')
        started = time.monotonic()
        inventory = scan_library(str(library))
        assert len(inventory['tracks']) == 10000 and inventory['truncated']
        assert any('not a complete' in x for x in inventory['warnings'])
        report['checks'].append({'name': '10001-candidate-inventory', 'passed': True,
            'retained': len(inventory['tracks']), 'explicitly_partial': True,
            'seconds': round(time.monotonic() - started, 3)})

        source = work / '20-minute-silence.wav'
        with wave.open(str(source), 'wb') as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(32000)
            block = b'\0\0' * 32000
            for _ in range(1200):
                output.writeframesraw(block)
        before = file_hash(source)
        single = scan_library(str(source))
        started = time.monotonic()
        result = analyze_tracks(Path(settings['scanner_path']), source, single['tracks'],
            work / 'long-result', settings['decoder_path'])
        row = result['records'][0]
        assert row['status'] == 'analyzed' and row['quality'] == 'LQ'
        assert row['duration_seconds'] == 1200 and row['silent_seconds'] == 1200
        assert file_hash(source) == before
        report['checks'].append({'name': '20-minute-single-file', 'passed': True,
            'decoded_seconds': row['duration_seconds'], 'quality': row['quality'],
            'graph_available': row['spectrogram'] is not None,
            'graph_reason': row.get('spectrum_evidence_unavailable_reason'),
            'source_unchanged': True, 'seconds': round(time.monotonic() - started, 3)})

        processes = []; launched = threading.Event()
        original_popen = analyzer.subprocess.Popen
        def tracked_popen(*args, **kwargs):
            child = original_popen(*args, **kwargs)
            processes.append(child)
            launched.set()
            return child
        with patch('music_library_lab.server.WORK', work / 'shutdown-cache'):
            session = LocalSession(settings['scanner_path'], settings['decoder_path'])
            session.start()
            try:
                with patch('music_library_lab.analyzer.subprocess.Popen', tracked_popen):
                    identifier = session.state.job(str(source), single['tracks'])
                    assert launched.wait(15), 'No real decoder worker was started'
                    started = time.monotonic()
                    session.stop()
                    elapsed = time.monotonic() - started
                assert session.state.jobs[identifier]['status'] == 'cancelled'
                assert not session.state.busy and not session.thread.is_alive()
                assert processes and all(child.poll() is not None for child in processes)
                assert file_hash(source) == before
                report['checks'].append({'name': 'backend-close-during-real-worker',
                    'passed': True, 'seconds': round(elapsed, 3), 'child_workers_reaped': True,
                    'server_stopped': True, 'source_unchanged': True})
            finally:
                session.stop()
        report['passed'] = True
    finally:
        (PROJECT / '.work/launch-runtime-validation.json').write_text(
            json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
