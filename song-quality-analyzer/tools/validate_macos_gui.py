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
           if not k.startswith(('PYTHON', 'DYLD_', 'SONG_AUDIT_', 'MUSIC_LIBRARY_',
                                'BANDPRISM_UI_', 'BANDPRISM_DESKTOP_CHECK_'))}
    env['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
    env['MUSIC_LIBRARY_WORK_DIR'] = str(cache)
    return env


def executable(bundle):
    return bundle.resolve() / 'Contents/MacOS/Bandprism'


def window_inventory(windows):
    """Record useful screen state without window titles, paths or tokens."""
    result = []
    for window in windows:
        owner = str(window.get('kCGWindowOwnerName', ''))
        result.append({
            'owner': owner if re.fullmatch(r'[\w .()+-]{1,80}', owner) else '[redacted]',
            'pid': window.get('kCGWindowOwnerPID'),
            'layer': window.get('kCGWindowLayer'),
            'bounds': dict(window.get('kCGWindowBounds', {})),
            'on_screen': bool(window.get('kCGWindowIsOnscreen')),
        })
    return result


def launch(bundle, output):
    import Quartz
    report = {'passed': False, 'normal_bundle_without_ui_driver': True,
              'gatekeeper_tested': False, 'permissions_modified': False,
              'native_input_automated': False}
    manifest = json.loads((bundle / 'Contents/Frameworks/build-manifest.json').read_text())
    assert not manifest['ui_test_driver'], 'Normal launch must use the shipping app.'
    prelaunch = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
    report['prelaunch_windows'] = window_inventory(prelaunch)
    report['preexisting_python_owner_windows'] = sum(
        'python' in row['owner'].lower() for row in report['prelaunch_windows'])
    before_image = output.parent / 'before-normal-app-launch.png'
    try:
        before_image.unlink(missing_ok=True)
        subprocess.run(['/usr/sbin/screencapture', '-x', str(before_image)],
                       check=True, capture_output=True, timeout=15)
        assert before_image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        report['prelaunch_screenshot_captured'] = True
    except Exception as exc:
        report['prelaunch_screenshot_captured'] = False
        report['error_type'] = type(exc).__name__
        output.write_text(json.dumps(report, indent=2) + '\n')
        raise
    env = environment(output.parent / 'normal-launch-cache')
    ready_image = output.parent / 'normal-app-launch.png'
    ready_image.unlink(missing_ok=True)
    env['BANDPRISM_DESKTOP_CHECK_SCREENSHOT'] = str(ready_image)
    with (output.parent / 'normal-launch.log').open('wb') as log:
        proc = subprocess.Popen([str(executable(bundle)), '--desktop-self-test'],
                                env=env, cwd=output.parent, stdout=log, stderr=log)
        try:
            returncode = proc.wait(timeout=120)
            report['returncode'] = returncode
            log.flush()
            diagnostic = None
            for line in reversed((output.parent / 'normal-launch.log').read_text(errors='replace').splitlines()):
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if isinstance(value, dict) and 'native_window_loaded' in value:
                    diagnostic = value
                    break
            assert diagnostic is not None, 'Normal packaged app did not complete its loaded diagnostic.'
            report['desktop_check'] = diagnostic
            assert returncode == 0 and diagnostic['passed'], 'Normal packaged desktop check failed.'
            assert diagnostic['native_window_loaded'] and diagnostic['bridge_ready']
            assert diagnostic['native_window_visible'] and diagnostic['readiness_screenshot_captured']
            assert diagnostic['server_stopped'], 'Normal desktop left its local server alive.'
            with socket.socket() as probe:
                assert probe.connect_ex(('127.0.0.1', diagnostic['listener_port'])) != 0, 'Normal app server is still listening.'
            children = subprocess.check_output(['/bin/ps', '-axo', 'pid=,command='], text=True)
            assert str(executable(bundle)) + ' --scanner-worker' not in children, 'Normal app left a decoder worker alive.'
            report['native_window_visible'] = True
            report['native_window_bounds'] = diagnostic['native_window_bounds']
            report['native_quit_clean'] = True
            report['quit_method'] = 'shipping desktop on_loaded diagnostic; normal native window close'
            report['close_reaped_worker_and_server'] = True
            report['passed'] = True
        except Exception as exc:
            report['error_type'] = type(exc).__name__
            raise
        finally:
            remaining = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
            report['postlaunch_windows'] = window_inventory(remaining)
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
