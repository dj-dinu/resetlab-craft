"""CSP-compatible adapter for the pinned pywebview Cocoa bridge.

pywebview 6.2.1 generates API wrappers with new Function and resolves Python
results with evaluate_js/eval. WKWebView enforces our strict CSP on both. Use
ordinary closures and its native completion API, preserving local-page guards,
the existing argument/result protocol and the five permitted desktop methods.
No dependency files, security headers or permissions are modified.
"""
import sys

ALLOWED_METHODS = {'choose_folder', 'choose_file', 'save_report', 'drop_status', 'take_drop'}
SAFE_API = r"""
window.pywebview._createApi = function(funcList) {
    var allowed = ['choose_folder', 'choose_file', 'save_report', 'drop_status', 'take_drop'];
    funcList.forEach(function(item) {
        var name = item.func;
        if (allowed.indexOf(name) < 0) return;
        window.pywebview._returnValuesCallbacks[name] = {};
        window.pywebview.api[name] = function() {
            var args = Array.prototype.slice.call(arguments);
            var id = (Math.random() + '').substring(2);
            var promise = new Promise(function(resolve, reject) {
                window.pywebview._checkValue(name, resolve, reject, id);
            });
            window.pywebview._jsApiCallback(name, args, id);
            return promise;
        };
    });
};
"""


def install_cocoa_bridge(window):
    """Install before webview.start; return an idempotent restoration function."""
    from webview import util
    original_loader = util.load_js_files
    original_dispatch = util.js_bridge_call
    cached_cocoa = sys.modules.get('webview.platforms.cocoa')
    original_cocoa_dispatch = getattr(cached_cocoa, 'js_bridge_call', None)
    original_evaluate = window.evaluate_js

    def loader(target, platform):
        code, finish = original_loader(target, platform)
        if target is window and platform == 'cocoa':
            code += '\n' + SAFE_API
        return code, finish

    def evaluate(script, callback=None):
        if callback is None and getattr(window.gui, 'renderer', None) in {'cocoa', 'wkwebview'}:
            # Cocoa already returns the last native JavaScript completion value.
            # DOM initialization and bridge response dispatch need no eval wrapper.
            return window.run_js(script)
        return original_evaluate(script, callback=callback)

    def dispatch(target, name, params, identifier):
        if target is window and name not in ALLOWED_METHODS:
            if not (name == 'pywebviewEventHandler' and isinstance(params, dict)
                    and params.get('nodeId') == 'document' and isinstance(params.get('event'), dict)
                    and params['event'].get('type') == 'drop'):
                return  # Do not let low-level RPC walk private Python attributes.
        return original_dispatch(target, name, params, identifier)

    util.load_js_files = loader
    util.js_bridge_call = dispatch
    if cached_cocoa is not None:
        cached_cocoa.js_bridge_call = dispatch
    window.evaluate_js = evaluate
    restored = False

    def restore():
        nonlocal restored
        if not restored:
            if util.load_js_files is loader:
                util.load_js_files = original_loader
            if util.js_bridge_call is dispatch:
                util.js_bridge_call = original_dispatch
            cocoa = sys.modules.get('webview.platforms.cocoa')
            if cocoa is not None and getattr(cocoa, 'js_bridge_call', None) is dispatch:
                cocoa.js_bridge_call = original_cocoa_dispatch or original_dispatch
            if window.evaluate_js is evaluate:
                window.evaluate_js = original_evaluate
            restored = True

    return restore
