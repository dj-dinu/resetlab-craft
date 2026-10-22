"""Verify an uninstrumented .app launch and a separate packaged Cocoa UI run."""
import argparse
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


def environment(cache):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('PYTHON', 'DYLD_', 'SONG_AUDIT_', 'MUSIC_LIBRARY_', 'BANDPRISM_UI_'))}
    env['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
    env['MUSIC_LIBRARY_WORK_DIR'] = str(cache)
    return env


def executable(bundle):
    return bundle.resolve() / 'Contents/MacOS/Bandprism'


def launch(bundle, output):
    from AppKit import NSRunningApplication
    import Quartz
    report = {'passed': False, 'normal_bundle_without_ui_driver': True, 'gatekeeper_tested': False}
    env = environment(output.parent / 'normal-launch-cache')
    with (output.parent / 'normal-launch.log').open('wb') as log:
        proc = subprocess.Popen([str(executable(bundle))], env=env, cwd=output.parent, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and proc.poll() is None:
                windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
                owned = [w for w in windows if w.get('kCGWindowOwnerPID') == proc.pid and w.get('kCGWindowLayer') == 0]
                if owned:
                    report['native_window_bounds'] = dict(owned[0]['kCGWindowBounds'])
                    report['native_window_visible'] = True
                    break
                time.sleep(.2)
            assert report.get('native_window_visible'), 'Normal packaged app did not display a Cocoa window'
            subprocess.run(['/usr/sbin/screencapture', '-x', str(output.parent / 'normal-app-launch.png')], check=True)
            application = NSRunningApplication.runningApplicationWithProcessIdentifier_(proc.pid)
            assert application is not None and application.terminate(), 'Native application quit request failed'
            assert proc.wait(timeout=20) == 0, 'App did not exit cleanly after native quit'
            report['native_quit_clean'] = True
            report['passed'] = True
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            output.write_text(json.dumps(report, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--ui-test-bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert sys.platform == 'darwin', 'Run this qualification on a native Mac'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    normal_manifest = args.bundle / 'Contents/Frameworks/build-manifest.json'
    assert not json.loads(normal_manifest.read_text())['ui_test_driver']
    assert json.loads((args.ui_test_bundle / 'Contents/Frameworks/build-manifest.json').read_text())['ui_test_driver']
    launch(args.bundle, output / 'normal-launch.json')
    from tools.audio_test_fixtures import create_audio
    fixtures = output / 'fixtures'
    create_audio(fixtures / 'Formats café % audio', gui=True)
    report_path = output / 'mac-ui.json'
    report_path.unlink(missing_ok=True)
    env = environment(output / 'ui-cache')
    env['BANDPRISM_UI_FIXTURES'] = str(fixtures)
    env['BANDPRISM_UI_REPORT'] = str(report_path)
    with (output / 'instrumented-ui.log').open('wb') as log:
        proc = subprocess.Popen([str(executable(args.ui_test_bundle))], env=env, cwd=output, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 420
            close_deadline = None
            while proc.poll() is None:
                if close_deadline is None and report_path.is_file():
                    try:
                        completed = json.loads(report_path.read_text())
                    except (OSError, ValueError):
                        completed = {}
                    if 'passed' in completed:
                        close_deadline = time.monotonic() + 35
                if time.monotonic() >= deadline or (close_deadline is not None and time.monotonic() >= close_deadline):
                    raise subprocess.TimeoutExpired([str(executable(args.ui_test_bundle))], 35 if close_deadline else 420)
                time.sleep(.2)
            returncode = proc.returncode
            if report_path.is_file():
                print(report_path.read_text(), flush=True)
            if returncode:
                log.flush()
                details = (output / 'instrumented-ui.log').read_text(errors='replace')[-12000:]
                details = re.sub(r'#token=[^\s\"\x27<>]+', '#token=[redacted]', details)
                print(details, flush=True)
            assert returncode == 0, 'Packaged UI flow failed; inspect mac-ui.json and instrumented-ui.log'
        except subprocess.TimeoutExpired:
            log.flush()
            details = (output / 'instrumented-ui.log').read_text(errors='replace')[-12000:]
            details = re.sub(r'#token=[^\s\"\x27<>]+', '#token=[redacted]', details)
            print(details, flush=True)
            if report_path.is_file():
                print(report_path.read_text(), flush=True)
            raise
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
    report = json.loads(report_path.read_text())
    assert report['passed'], report.get('error')
    with socket.socket() as probe:
        assert probe.connect_ex(('127.0.0.1', report['listener_port'])) != 0, 'Local server still listening after close'
    children = subprocess.check_output(['/bin/ps', '-axo', 'pid=,command='], text=True)
    assert str(executable(args.ui_test_bundle)) + ' --scanner-worker' not in children, 'Decoder worker survived app close'
    report['close_reaped_worker_and_server'] = True
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
