"""CSP-compatible adapter for the pinned pywebview Cocoa bridge.

pywebview 6.2.1 generates API wrappers with new Function and resolves Python
results with evaluate_js/eval. WKWebView enforces our strict CSP on both. Use
ordinary closures and its native completion API, preserving local-page guards,
the existing argument/result protocol and the five permitted desktop methods.
No dependency files, security headers or permissions are modified.
"""
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
    original_evaluate = window.evaluate_js

    def loader(target, platform):
        code, finish = original_loader(target, platform)
        if target is window and platform == 'cocoa':
            code += '\n' + SAFE_API
        return code, finish

    def evaluate(script, callback=None):
        if callback is None and getattr(window.gui, 'renderer', None) == 'cocoa':
            # Cocoa already returns the last native JavaScript completion value.
            # DOM initialization and bridge response dispatch need no eval wrapper.
            return window.run_js(script)
        return original_evaluate(script, callback=callback)

    util.load_js_files = loader
    window.evaluate_js = evaluate
    restored = False

    def restore():
        nonlocal restored
        if not restored:
            if util.load_js_files is loader:
                util.load_js_files = original_loader
            if window.evaluate_js is evaluate:
                window.evaluate_js = original_evaluate
            restored = True

    return restore
