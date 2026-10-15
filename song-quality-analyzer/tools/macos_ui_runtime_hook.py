"""Build-only driver for a separate CI app; absent from the distributable app.

Uses real Cocoa/WKWebView, the shipped page, HTTP server and frozen worker.
File/folder/save dialog selections are substituted. This does not qualify Finder
drag, native pickers, TCC, Gatekeeper, trackpads or clean-user installation.
"""
import sys

if '--scanner-worker' not in sys.argv:
    import hashlib
    import faulthandler
    import json
    import os
    from pathlib import Path
    import subprocess
    import time
    import webview
    from music_library_lab import desktop

    report_path = Path(os.environ['SPECTRACRAFT_UI_REPORT']).resolve()
    fixture_root = Path(os.environ['SPECTRACRAFT_UI_FIXTURES']).resolve()
    results = {'passed': False, 'instrumented_bundle': True, 'renderer': 'Cocoa/WKWebView',
               'native_dialogs_automated': False, 'checks': [], 'screenshots': []}
    session = None
    base_session = desktop.LocalSession
    original_start = webview.start
    results['native_calls'] = []
    original_folder = desktop.DesktopBridge.choose_folder
    def tracked_folder(self):
        results['native_calls'].append('choose_folder entered')
        value = original_folder(self)
        results['native_calls'].append('choose_folder selected' if value else 'choose_folder cancelled/refused')
        return value
    desktop.DesktopBridge.choose_folder = tracked_folder

    class TestSession(base_session):
        def __init__(self, *args, **kwargs):
            global session
            super().__init__(*args, **kwargs)
            session = self

    desktop.LocalSession = TestSession

    def driver():
        window = webview.windows[0]
        def js(code):
            # Cocoa run_js uses WKWebView's native completion result directly.
            # It does not need evaluate_js's eval or an extra exposed API.
            raw = window.run_js('JSON.stringify((function(){try{return {ok:true,value:(function(){' +
                                code + '})()};}catch(error){return {ok:false,error:String(error)};}})())')
            assert raw is not None, 'WKWebView did not return a native JavaScript result'
            reply = json.loads(str(raw))
            assert reply.get('ok'), reply
            return reply.get('value')
        def until(condition, description, timeout=60):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if condition():
                    return
                time.sleep(.1)
            raise AssertionError('Timed out: ' + description)
        def dom(expression):
            return js('return (' + expression + ');')
        def click(identifier):
            js('document.getElementById(' + json.dumps(identifier) + ').click();')
        def check(name, **details):
            results['checks'].append(dict(name=name, passed=True, **details))
        def job():
            with session.state.lock:
                audits = [j for j in session.state.jobs.values() if j['kind'] == 'audit']
                return audits[-1] if audits else None
        def load(path, count):
            js('const input=document.getElementById("root-path"); input.value=' + json.dumps(str(path)) +
               '; input.dispatchEvent(new Event("input")); input.dispatchEvent(new Event("change"));')
            until(lambda: dom('document.getElementById("track-count").textContent === ' + json.dumps(str(count)) +
                              ' && !document.getElementById("audit-button").disabled'), 'inventory ' + str(count))
        def pick(path, kind, count):
            window.create_file_dialog = lambda *args, **kwargs: (str(path),) if path else None
            click('scan-button')
            click('browse-button' if kind == 'folder' else 'browse-file-button')
            until(lambda: dom('document.getElementById("track-count").textContent === ' + json.dumps(str(count)) +
                              ' && !document.getElementById("audit-button").disabled'), 'picker bridge inventory')
        def analyze():
            previous = job()
            click('audit-button')
            until(lambda: job() is not None and job() is not previous, 'new audit')
            until(lambda: dom('!document.getElementById("job-panel").hidden'), 'progress shown')
        def complete():
            until(lambda: job()['status'] != 'running', 'complete audit', timeout=180)
            assert job()['status'] == 'complete', job().get('error')
            until(lambda: dom('!document.getElementById("export-button").disabled'), 'results rendered')
        def pause():
            until(lambda: dom('!document.getElementById("pause-button").disabled'), 'pause enabled')
            assert job()['status'] == 'running', 'Control fixture finished before Pause was requested'
            click('pause-button')
            until(lambda: job()['progress'].get('paused') is True, 'decoder pause acknowledgment')
            until(lambda: dom('document.getElementById("pause-button").textContent === "Resume"'), 'resume control')
        def screenshot(name):
            destination = report_path.parent / (name + '.png')
            capture = subprocess.run(['/usr/sbin/screencapture', '-x', str(destination)], capture_output=True)
            if capture.returncode == 0 and destination.is_file():
                results['screenshots'].append(destination.name)
        before = {str(p.relative_to(fixture_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in fixture_root.rglob('*') if p.is_file()}
        try:
            assert window.events.loaded.wait(45), 'Cocoa page did not load'
            until(lambda: dom('!!window.pywebview.api && !document.getElementById("theme-toggle").disabled'), 'app ready')
            bridge = dom('({folder:typeof window.pywebview.api.choose_folder, file:typeof window.pywebview.api.choose_file, save:typeof window.pywebview.api.save_report})')
            results['bridge_methods'] = bridge
            assert all(value == 'function' for value in bridge.values()), 'Native bridge methods unavailable: ' + str(bridge)
            check('native-bridge-methods-available')
            results['listener_port'] = session.server.server_port
            check('native-window-and-shipped-page-loaded')
            window.resize(640, 700)
            until(lambda: dom('innerWidth <= 650'), 'half-screen resize')
            assert dom('document.documentElement.scrollWidth <= innerWidth + 2'), 'Page overflows a half-screen window'
            check('half-screen-resize', width=640)
            initial = dom('document.documentElement.dataset.theme')
            click('theme-toggle')
            until(lambda: dom('!document.getElementById("theme-toggle").disabled'), 'appearance saved')
            assert dom('document.documentElement.dataset.theme') != initial
            check('appearance-toggle')
            original_font = dom('parseFloat(getComputedStyle(document.getElementById("root-path")).fontSize)')
            click('text-size-toggle')
            for size in ('110', '125', '150'):
                click('text-size-increase')
                until(lambda: dom('!document.getElementById("text-size-reset").disabled'), 'text size saved')
                assert dom('document.documentElement.dataset.textSize') == size
            assert dom('document.getElementById("text-size-increase").disabled')
            assert dom('parseFloat(getComputedStyle(document.getElementById("root-path")).fontSize)') > original_font * 1.49
            from music_library_lab.server import interface_preferences
            assert interface_preferences()['text_size'] == '150'
            click('text-size-reset')
            until(lambda: dom('!document.getElementById("text-size-reset").disabled'), 'default text size saved')
            assert dom('document.documentElement.dataset.textSize') == '100'
            assert interface_preferences()['text_size'] == '100'
            click('text-size-toggle')
            check('text-size-controls-and-saved-choice')
            screenshot('mac-ui-half-screen')
            pick(fixture_root / 'Formats café % audio', 'folder', 6)
            check('folder-picker-through-native-bridge', dialog_selection_substituted=True)
            check('unicode-folder-auto-inventory')
            analyze()
            check('progress-visible')
            complete()
            assert len(job()['result']['records']) == 6 and job()['result']['errors'] == 0
            check('six-formats-through-packaged-worker')
            js('const filter=document.getElementById("grade-filter"); filter.value="HQ"; filter.dispatchEvent(new Event("change"));')
            assert dom('document.querySelectorAll(".track-title").length') == job()['result']['counts']['HQ']
            js('const filter=document.getElementById("grade-filter"); filter.value="All"; filter.dispatchEvent(new Event("change"));')
            check('grade-filter')
            click('evidence-button-0')
            assert dom('!document.getElementById("timeline-0").hidden')
            check('evidence-expanded')
            click('text-size-toggle')
            for size in ('110', '125', '150'):
                click('text-size-increase')
                until(lambda: dom('!document.getElementById("text-size-reset").disabled'), 'large result text saved')
            window.resize(420, 700)
            until(lambda: dom('innerWidth <= 430'), 'narrow window with large text')
            assert dom('document.documentElement.scrollWidth <= innerWidth + 2'), 'Large text overflows the narrow page'
            assert dom('document.getElementById("track-count").textContent') == '6'
            screenshot('mac-ui-large-text')
            click('text-size-reset')
            until(lambda: dom('!document.getElementById("text-size-reset").disabled'), 'restore result text size')
            click('text-size-toggle')
            window.resize(640, 700)
            check('large-text-narrow-results', width=420, text_percent=150)
            target = report_path.parent / 'synthetic-export.json'
            # Exercise the real button/bridge/export sanitization, substituting
            # only a dialog's selected destination. Native dialog remains manual.
            window.create_file_dialog = lambda *args, **kwargs: (str(target),)
            click('export-button')
            until(target.is_file, 'report export')
            exported = target.read_text(encoding='utf-8')
            assert str(fixture_root) not in exported and len(json.loads(exported)['records']) == 6
            check('export-via-ui-and-bridge', save_dialog_selection_substituted=True)
            screenshot('mac-ui-results')
            pick(fixture_root / 'Formats café % audio/01 HQ.wav', 'file', 1)
            check('single-file-picker-through-native-bridge', dialog_selection_substituted=True)
            pick(None, 'folder', 1)
            assert dom('document.getElementById("root-path").value').endswith('01 HQ.wav')
            check('picker-cancel-preserves-selection', dialog_selection_substituted=True)
            load(fixture_root / 'Batch 103 café % తెలుగు', 103)
            titles = dom('Array.from(document.querySelectorAll(".track-title"), e=>e.textContent)')
            assert titles == sorted(titles), titles[:3]
            analyze()
            complete()
            assert job()['completed_batches'] == 3 and len(job()['summaries']) == 103
            assert job()['result']['completed_tracks'] == 103 and len(job()['result']['records']) == 3
            assert [r['source_path'] for r in job()['summaries']] == sorted(r['source_path'] for r in job()['summaries'])
            assert dom('document.getElementById("folder-score-value").textContent') == '100.0'
            assert dom('document.getElementById("folder-score-coverage").textContent') == '103 of 103 folder tracks measured'
            check('alphabetical-auto-batches-50-50-3', completed=103)
            load(fixture_root / 'Pause and close', 1)
            analyze()
            pause()
            click('pause-button')
            until(lambda: not job()['pause_event'].is_set(), 'resume request')
            until(lambda: job()['progress'].get('paused') is False, 'decoder resume acknowledgment')
            until(lambda: not dom('document.getElementById("pause-button").disabled'), 'pause ready again')
            pause()
            check('pause-resume-acknowledged-by-worker')
            click('cancel-button')
            until(lambda: job()['status'] == 'cancelled', 'stop while paused')
            until(lambda: dom('!document.getElementById("audit-button").disabled'), 'stop UI ready')
            check('stop-while-paused')
            analyze()
            pause()
            check('close-requested-with-paused-worker')
            results['original_hashes_unchanged'] = all(hashlib.sha256((fixture_root / p).read_bytes()).hexdigest() == h
                                                       for p, h in before.items())
            assert results['original_hashes_unchanged']
            results['passed'] = True
        except Exception as exc:
            results['error'] = repr(exc)
            results['native_renderer'] = getattr(window.gui, 'renderer', None)
            results['backend_busy'] = session.state.busy
            results['backend_jobs'] = len(session.state.jobs)
            current = job()
            if current is not None:
                results['last_audit'] = {key: current.get(key) for key in ('status', 'progress', 'error')}
                results['last_audit']['pause_requested'] = current['pause_event'].is_set()
            try:
                results['ui_diagnostic'] = dom('({count:document.getElementById("track-count").textContent, root:document.getElementById("root-path").value, alerts:document.getElementById("alerts").textContent, folderHidden:document.getElementById("browse-button").hidden, folderDisabled:document.getElementById("browse-button").disabled, pendingFolder:Object.keys(window.pywebview._returnValuesCallbacks.choose_folder||{}).length})')
            except Exception:
                pass
            screenshot('mac-ui-failure')
        finally:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
            # Only this separate test app emits a bounded stack if closing hangs.
            faulthandler.dump_traceback_later(25, file=sys.stderr)
            window.destroy()

    def start(*args, **kwargs):
        kwargs['func'] = driver
        original_start(*args, **kwargs)
        if not results['passed']:
            raise SystemExit(1)

    webview.start = start
