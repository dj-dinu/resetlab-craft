"""Fast local syntax/protocol feedback; does not qualify a release package."""
import ast
from pathlib import Path
import shutil
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]


def main():
    files = list((PROJECT / 'music_library_lab').rglob('*.py'))
    files += list((PROJECT / 'tools').glob('*.py')) + list((PROJECT / 'tests').glob('*.py'))
    files += list(PROJECT.glob('*.py'))
    for path in files:
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    node = shutil.which('node')
    if node is None:
        raise SystemExit('Node.js is required for the JavaScript checks.')
    for path in sorted((PROJECT / 'music_library_lab/static').glob('*.js')):
        subprocess.run([node, '--check', str(path)], check=True)
    for name in ('test_library_view.js', 'test_cocoa_bridge.js'):
        subprocess.run([node, str(PROJECT / 'tests' / name)], check=True)
    print(f'Quick checks passed: {len(files)} Python sources and JavaScript syntax/protocols. '
          'Native packaging and release tests are separate.')


if __name__ == '__main__':
    main()
