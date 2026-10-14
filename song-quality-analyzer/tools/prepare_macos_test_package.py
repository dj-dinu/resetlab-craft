"""Assemble a bounded, unsigned volunteer kit after native package checks pass.

Downloads public corresponding sources only. Never reads a user music folder,
settings, session token or signing credential. This does not publish a release.
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import re
import shutil
import ssl
import subprocess
import sys
import tarfile
from urllib.request import Request, urlopen
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
SHARED_SOURCES_URL = ('https://github.com/dj-dinu/resetlab-craft/releases/download/v0.1.0-alpha.5/'
                      'Spectracraft-0.1.0-alpha.5-dependency-sources.zip')
SHARED_SOURCES_SHA = 'a9f93deeeddbfb4879bc3d499433f0dfe54a3cf84a02bd0e7cc66639fc753664'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def download(url, destination, expected=None):
    request = Request(url, headers={'User-Agent': 'Spectracraft-Mac-qualification'})
    with urlopen(request, timeout=60) as source, destination.open('wb') as output:
        total = 0
        while block := source.read(1024 * 1024):
            total += len(block)
            assert total <= 250 * 1024 * 1024, 'Source archive exceeds the download budget'
            output.write(block)
    digest = sha(destination)
    if expected:
        assert digest == expected, 'Public source hash mismatch: ' + destination.name
    return dict(file=destination.name, url=url, sha256=digest, upstream_hash_verified=bool(expected))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decoder', type=Path, required=True)
    args = parser.parse_args()
    assert sys.platform == 'darwin' and platform.machine() == 'arm64'
    work = PROJECT / '.work'
    gui = json.loads((work / 'mac-gui-evidence/mac-ui.json').read_text())
    normal = json.loads((work / 'mac-gui-evidence/normal-launch.json').read_text())
    frozen = json.loads((work / 'macos-frozen.json').read_text())
    assert gui['passed'] and gui['close_reaped_worker_and_server'] and normal['native_quit_clean']
    assert frozen['frozen_bundle']['passed'] and frozen['original_hashes_unchanged']
    manifest = json.loads((work / 'mac-package/build-manifest.json').read_text())
    assert not manifest['ui_test_driver'] and manifest['architecture'] == 'arm64'
    dependencies = json.loads((work / 'release-dependency-review.json').read_text())
    assert not dependencies['missing_dependencies']
    assert dependencies['ffmpeg']['version'] == '9.0.2', 'Review new native FFmpeg source materials before sharing'
    formula = json.loads(subprocess.check_output(['brew', 'info', '--json=v2', 'mpg123'], text=True))['formulae'][0]
    assert formula['versions']['stable'] == '1.33.7', 'Review new mpg123 source materials before sharing'
    target = work / 'mac-test-kit'
    target.mkdir(exist_ok=True)
    sources = target / 'sources'
    sources.mkdir(exist_ok=True)
    receipts = []
    shared = sources / 'Shared-native-sources-and-notices.zip'
    receipts.append(download(SHARED_SOURCES_URL, shared, SHARED_SOURCES_SHA))
    # Confirm that the reviewed upstream recipe and MP3 sources are supplied.
    with zipfile.ZipFile(shared) as archive:
        names = archive.namelist()
        assert any(name.endswith('/sources/ffmpeg-9.0.2.tar.xz') for name in names)
        assert any(name.endswith('/sources/mpg123-1.33.7.tar.bz2') for name in names)
        assert any('/upstream/pyav-ffmpeg/scripts/build-ffmpeg.py' in name for name in names)
    for package in dependencies['packages']:
        name, version = package['name'], package['version']
        with urlopen('https://pypi.org/pypi/' + name + '/' + version + '/json', timeout=30) as response:
            release = json.load(response)
        source = next(row for row in release['urls'] if row['packagetype'] == 'sdist')
        assert Path(source['filename']).name == source['filename']
        receipts.append(dict(package=name, version=version,
                             **download(source['url'], sources / source['filename'], source['digests']['sha256'])))
        distribution = metadata.distribution(name)
        # Keep original relative locations; do not collapse several LICENSE files.
        for entry in distribution.files or ():
            path = Path(str(entry))
            if 'licenses' in path.parts or path.name.lower().startswith(('license', 'copying', 'notice')):
                installed = Path(distribution.locate_file(entry))
                if installed.is_file() and installed.suffix.lower() not in {'.py', '.pyc', '.pyo', '.so', '.pyd', '.dll', '.dylib', '.a', '.lib'} and '..' not in path.parts:
                    copied = target / 'notices' / name / path
                    copied.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(installed, copied)
    version = platform.python_version()
    receipts.append(download(f'https://www.python.org/ftp/python/{version}/Python-{version}.tgz',
                             sources / f'Python-{version}.tgz'))
    with tarfile.open(sources / f'Python-{version}.tgz') as archive:
        member = next(m for m in archive if m.name.endswith('/LICENSE') and m.isfile())
        (target / 'PYTHON_LICENSE.txt').write_bytes(archive.extractfile(member).read())
    openssl_version = re.match(r'OpenSSL ([\d.]+)', ssl.OPENSSL_VERSION).group(1)
    receipts.append(download(f'https://github.com/openssl/openssl/releases/download/openssl-{openssl_version}/openssl-{openssl_version}.tar.gz',
                             sources / f'openssl-{openssl_version}.tar.gz'))
    with tarfile.open(sources / f'openssl-{openssl_version}.tar.gz') as archive:
        member = next(m for m in archive if m.name.endswith(('/LICENSE.txt', '/LICENSE')) and m.isfile())
        (target / 'OPENSSL_LICENSE.txt').write_bytes(archive.extractfile(member).read())
    prefix = args.decoder.resolve().parents[1]
    homebrew = target / 'homebrew-mpg123'
    homebrew.mkdir(exist_ok=True)
    for filename in ('INSTALL_RECEIPT.json', '.brew/mpg123.rb'):
        source = prefix / filename
        assert source.is_file(), 'Missing installed Homebrew recipe: ' + filename
        shutil.copyfile(source, homebrew / source.name)
    (homebrew / 'formula.json').write_text(json.dumps(formula, indent=2))
    source_zip = target / 'Spectracraft-matching-project-source.zip'
    subprocess.run(['git', 'archive', '--format=zip', '--output=' + str(source_zip), 'HEAD'],
                   cwd=PROJECT.parent, check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT.parent, text=True).strip()
    for filename in ('LICENSE', 'docs/MACOS_VOLUNTEER_TEST.md', 'docs/MACOS_TESTING.md', 'docs/REUSE_AND_BRANDING.md'):
        shutil.copyfile(PROJECT / filename, target / Path(filename).name)
    shutil.copyfile(work / 'mac-package/Spectracraft-apple-silicon-test.zip', target / 'Spectracraft-apple-silicon-test.zip')
    shutil.copyfile(work / 'mac-package/build-manifest.json', target / 'build-manifest.json')
    shutil.copyfile(work / 'release-dependency-review.json', target / 'dependency-inventory.json')
    (target / 'source-receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
    (target / 'README.txt').write_text(
        'Spectracraft Apple silicon volunteer test — macOS 15 or later\n'
        'Extract Spectracraft-apple-silicon-test.zip with Finder, then open Spectracraft.app.\n'
        'Python and Homebrew are not needed to run the app. Use MACOS_VOLUNTEER_TEST.md.\n'
        'Ad-hoc signed, not notarized. Record first-launch security prompts; do not disable Gatekeeper globally.\n'
        'This is a test artifact, not a public supported Mac release.\n'
        'The app analyzes locally and leaves music, tags and artwork unchanged.\n'
        'Matching project source, native source archives/recipes and exact Python package sources are included.\n'
        'Shared native source materials contain additional Windows materials; Mac uses the same reviewed\n'
        'PyAV FFmpeg 9.0.2-1 recipe and mpg123 1.33.7 source plus its installed Homebrew formula.\n'
        'Each dependency retains its own license; do not assume all native libraries are LGPL.\n'
        'For modified/relinked builds, recreate a native Python 3.12 environment, build native decoder\n'
        'libraries using the supplied sources/recipes, then use the matching tools/build_desktop.py.\n'
        'Re-run package checks after changes. The separate --ui-test-driver app is never distributed.\n'
        'Source commit: ' + commit + '\n', encoding='utf-8')
    sums = []
    for path in sorted(target.rglob('*')):
        if path.is_file():
            sums.append(sha(path) + '  ' + path.relative_to(target).as_posix())
    (target / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n')
    print(json.dumps({'prepared': True, 'source_commit': commit, 'sources': len(receipts),
                      'app_sha256': sha(target / 'Spectracraft-apple-silicon-test.zip'), 'release_published': False}))


if __name__ == '__main__':
    main()
