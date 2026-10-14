from types import SimpleNamespace
import unittest
from unittest.mock import patch

from music_library_lab.cocoa_bridge import install_cocoa_bridge


class CocoaBridgeTests(unittest.TestCase):
    def test_native_completion_and_loader_scope_restore(self):
        scripts = []
        evaluate_calls = []
        window = SimpleNamespace(gui=SimpleNamespace(renderer='cocoa'),
                                 run_js=lambda script: scripts.append(script) or ['drop'],
                                 evaluate_js=lambda script, callback=None: evaluate_calls.append((script, callback)))
        original_evaluate = window.evaluate_js
        loader = lambda target, platform: ('base', 'finish')
        with patch('webview.util.load_js_files', loader):
            from webview import util
            restore = install_cocoa_bridge(window)
            try:
                code, finish = util.load_js_files(window, 'cocoa')
                self.assertIn('_createApi = function', code)
                self.assertEqual(finish, 'finish')
                self.assertEqual(util.load_js_files(object(), 'cocoa'), ('base', 'finish'))
                self.assertEqual(util.load_js_files(window, 'edgechromium'), ('base', 'finish'))
                self.assertEqual(window.evaluate_js('native completion'), ['drop'])
                self.assertEqual(scripts, ['native completion'])
                self.assertFalse(evaluate_calls)
            finally:
                restore()
                restore()
            self.assertIs(util.load_js_files, loader)
            self.assertIs(window.evaluate_js, original_evaluate)


if __name__ == '__main__':
    unittest.main()
