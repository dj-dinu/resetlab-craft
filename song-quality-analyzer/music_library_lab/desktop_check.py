"""Opt-in native-window diagnostic; never runs during normal app startup.

Exercises the shipping executable's actual desktop path. Reports no music,
machine paths, session token, download URL or user preferences.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time


def capture_macos_readiness(destination, report):
    """Capture only this diagnostic's ready window, without native input."""
    import Quartz
    import subprocess

    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
    owned = [window for window in windows
             if window.get('kCGWindowOwnerPID') == os.getpid()
             and window.get('kCGWindowLayer') == 0]
    assert owned, 'The ready Cocoa window is not visible.'
    window = max(owned, key=lambda item: item['kCGWindowBounds']['Width'] *
                 item['kCGWindowBounds']['Height'])
    report['native_window_visible'] = True
    report['native_window_bounds'] = dict(window['kCGWindowBounds'])
    target = Path(destination)
    assert target.is_absolute(), 'Use an absolute private diagnostic screenshot path.'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    subprocess.run(['/usr/sbin/screencapture', '-x', '-l',
                    str(window['kCGWindowNumber']), str(target)],
                   check=True, capture_output=True, timeout=15)
    assert target.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), 'Readiness screenshot is not a PNG.'
    report['readiness_screenshot_captured'] = True


def download_zone(path):
    try:
        with open(str(path) + ':Zone.Identifier', encoding='utf-8') as stream:
            text = stream.read(4096)
        from configparser import ConfigParser
        config = ConfigParser(interpolation=None)
        config.read_string(text)
        return config.getint('ZoneTransfer', 'ZoneId', fallback=None)
    except (OSError, ValueError, KeyError):
        return None


def main():
    if sys.platform not in {'win32', 'darwin'} or not getattr(sys, 'frozen', False):
        raise SystemExit('Run this diagnostic with the packaged Windows or Mac executable.')
    from . import APP_NAME
    windows = sys.platform == 'win32'
    report = {'passed': False, 'native_window_loaded': False, 'platform': sys.platform}
    original_zone = download_zone(sys.executable) if windows else None
    root = Path(sys._MEIPASS)
    libraries = ('pythonnet/runtime/Python.Runtime.dll',
                 'webview/lib/Microsoft.Web.WebView2.Core.dll',
                 'webview/lib/Microsoft.Web.WebView2.WinForms.dll') if windows else ()
    before = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in libraries}
    if windows:
        report['executable_zone_before'] = original_zone
        report['managed_library_zones'] = {name: download_zone(root / name) for name in libraries}
    saved_work = os.environ.get('MUSIC_LIBRARY_WORK_DIR')
    sys.argv = [sys.argv[0]]
    with tempfile.TemporaryDirectory(prefix='bandprism-desktop-check-') as temporary:
        os.environ['MUSIC_LIBRARY_WORK_DIR'] = temporary
        from .desktop import main as desktop_main
        def loaded(window, session, bridge):
            report['session'] = session
            report['listener_port'] = session.server.server_port
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    ready = window.evaluate_js('!!window.pywebview?.api && !document.getElementById("theme-toggle").disabled')
                    if ready:
                        break
                    time.sleep(.1)
                else:
                    raise RuntimeError('The local interface did not become ready.')
                assert APP_NAME in window.evaluate_js('document.title')
                assert not window.evaluate_js('/spectracraft/i.test(document.body.innerText)')
                assert bridge._local_page() and bridge.drop_status()['available']
                assert window.evaluate_js('typeof window.pywebview.api.choose_folder') == 'function'
                assert window.evaluate_js('typeof window.pywebview.api.choose_file') == 'function'
                assert window.evaluate_js('typeof window.pywebview.api.save_report') == 'function'
                report['native_window_loaded'] = True
                report['bridge_ready'] = True
                if windows:
                    report['download_marker_retained'] = download_zone(sys.executable) == original_zone
                    report['managed_library_bytes_unchanged'] = all(
                        hashlib.sha256((root / name).read_bytes()).hexdigest() == digest for name, digest in before.items())
                    report['passed'] = report['download_marker_retained'] and report['managed_library_bytes_unchanged']
                else:
                    screenshot = os.environ.get('BANDPRISM_DESKTOP_CHECK_SCREENSHOT')
                    if screenshot:
                        capture_macos_readiness(screenshot, report)
                    report['passed'] = True
            except Exception as exc:
                report['error_type'] = type(exc).__name__
            finally:
                window.destroy()
        try:
            desktop_main(on_loaded=loaded)
        except Exception as exc:
            report['passed'] = False
            report['error_type'] = type(exc).__name__
        finally:
            session = report.pop('session', None)
            report['server_stopped'] = bool(session and session.closed and not session.thread.is_alive())
            report['passed'] = report['passed'] and report['server_stopped']
            if saved_work is None:
                os.environ.pop('MUSIC_LIBRARY_WORK_DIR', None)
            else:
                os.environ['MUSIC_LIBRARY_WORK_DIR'] = saved_work
    print(json.dumps(report), flush=True)
    if not report['passed']:
        raise SystemExit(1)
