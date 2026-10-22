"""Assemble versioned beta assets and exact sources after native checks; never publish."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
from urllib.request import urlopen
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from music_library_lab import __version__, BUILD_NUMBER
from tools.prepare_macos_test_package import download, sha, SHARED_SOURCES_URL, SHARED_SOURCES_SHA


def require_no_python_advisories(inventory):
    findings = [f"{row['name']}=={row['version']}: {', '.join(row['advisory_ids'])}"
        for row in inventory['python_package_advisories'] if row['advisory_ids']]
    assert not findings, 'Unresolved Python package advisories: ' + '; '.join(findings)


def collect_sources(target, inventory, decoder):
    sources = target / 'sources'
    sources.mkdir()
    shared = sources / 'Shared-native-sources-and-notices.zip'
    receipts = [download(SHARED_SOURCES_URL, shared, SHARED_SOURCES_SHA)]
    assert inventory['ffmpeg']['version'] == '9.0.2', 'Review changed native FFmpeg sources first'
    assert metadata.version('av') == '19.0.0' and metadata.version('numpy') == '2.3.5'
    with zipfile.ZipFile(shared) as archive:
        assert any(n.endswith('/sources/mpg123-1.33.7.tar.bz2') for n in archive.namelist())
        assert any(n.endswith('/sources/ffmpeg-9.0.2.tar.xz') for n in archive.namelist())

    def package_source(package):
        name, version = package['name'], package['version']
        with urlopen(f'https://pypi.org/pypi/{name}/{version}/json', timeout=30) as response:
            release = json.load(response)
        source = next(row for row in release['urls'] if row['packagetype'] == 'sdist')
        assert Path(source['filename']).name == source['filename']
        receipt = download(source['url'], sources / source['filename'], source['digests']['sha256'])
        return dict(package=name, version=version, **receipt)

    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts.extend(pool.map(package_source, inventory['packages']))
    for package in inventory['packages']:
        distribution = metadata.distribution(package['name'])
        for entry in distribution.files or ():
            relative = Path(str(entry))
            if relative.is_absolute() or '..' in relative.parts:
                continue
            if 'licenses' not in relative.parts and not relative.name.lower().startswith(('license', 'copying', 'notice')):
                continue
            original = Path(distribution.locate_file(entry))
            if not original.is_file() or original.suffix.lower() in {'.py', '.pyc', '.pyo', '.so', '.pyd', '.dll', '.dylib', '.a', '.lib'}:
                continue
            destination = target / 'notices' / package['name'] / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, destination)
    version = inventory['runtime']['python']
    python_archive = sources / f'Python-{version}.tgz'
    receipts.append(download(f'https://www.python.org/ftp/python/{version}/Python-{version}.tgz', python_archive))
    with tarfile.open(python_archive) as archive:
        (target / 'PYTHON_LICENSE.txt').write_bytes(archive.extractfile(f'Python-{version}/LICENSE').read())
    openssl = re.match(r'OpenSSL ([\d.]+)', inventory['runtime']['openssl']).group(1)
    openssl_archive = sources / f'openssl-{openssl}.tar.gz'
    receipts.append(download(f'https://github.com/openssl/openssl/releases/download/openssl-{openssl}/openssl-{openssl}.tar.gz', openssl_archive))
    with tarfile.open(openssl_archive) as archive:
        (target / 'OPENSSL_LICENSE.txt').write_bytes(archive.extractfile(f'openssl-{openssl}/LICENSE.txt').read())
    if sys.platform == 'darwin':
        formula = json.loads(subprocess.check_output(['brew', 'info', '--json=v2', 'mpg123'], text=True))['formulae'][0]
        assert formula['versions']['stable'] == '1.33.7', 'Review changed MP3 decoder sources first'
        (target / 'homebrew-mpg123.json').write_text(json.dumps(formula, indent=2))
        for name in ('INSTALL_RECEIPT.json', '.brew/mpg123.rb'):
            shutil.copyfile(decoder.resolve().parents[1] / name, target / Path(name).name)
    (target / 'source-receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
    (target / 'DEPENDENCY_INVENTORY.json').write_text(json.dumps(inventory, indent=2) + '\n')
    (target / 'BUILD_MATERIALS.md').write_text(
        '# Corresponding sources and build materials\n\n'
        'Shared native materials contain FFmpeg 9.0.2 / PyAV-Org pyav-ffmpeg 9.0.2-1 recipes, '
        'patches, vendor sources, NumPy/OpenBLAS sources and mpg123 1.33.7 source. '
        'Keep the included licenses, including GPL codec and GCC runtime terms. '
        'Do not treat the whole bundle as BSD or LGPL.\n\n'
        'Exact installed Python package source archives and notices are included separately. '
        'The Python source includes its bundled Expat. OpenSSL source and license are included. '
        'Use the recorded Python/runtime/package versions, the matching project source, '
        'requirements-build.txt, tools/build_desktop.py and a platform-native decoder. '
        'Mac includes its Homebrew formula and receipt; Windows uses the reviewed replaceable '
        'mpg123 DLL from alpha.5. Native libraries remain replaceable for relinking. '
        'Compiler/SDK identity and byte-for-byte reproduction are not claimed.\n', encoding='utf-8')


def archive(folder, destination, prefix):
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                output.write(path, prefix + '/' + path.relative_to(folder).as_posix())
    with zipfile.ZipFile(destination) as check:
        assert check.testzip() is None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--decoder', type=Path, required=True)
    args = parser.parse_args()
    mac = sys.platform == 'darwin'
    assert sys.platform in {'win32', 'darwin'}
    name = 'macos-arm64' if mac else 'windows-x64'
    assert platform.machine().lower() in ({'arm64'} if mac else {'amd64', 'x86_64'})
    if mac:
        internal = args.bundle / 'Contents/Frameworks'
        manifest = json.loads((internal / 'build-manifest.json').read_text())
    else:
        from PyInstaller.archive.readers import CArchiveReader
        embedded = CArchiveReader(str(args.bundle))
        manifest = json.loads(embedded.extract('build-manifest.json'))
        assert manifest['packaging'] == 'onefile'
    inventory = json.loads((PROJECT / '.work/release-dependency-review.json').read_text())
    assert not manifest['ui_test_driver'] and manifest['version'] == __version__
    assert manifest['runtime'] == inventory['runtime']
    assert manifest['runtime']['python'] == '3.13.16', 'Use the reviewed patched release runtime'
    assert manifest['runtime']['openssl'].startswith('OpenSSL 3.5.9 ')
    assert manifest['runtime']['expat'] == 'expat_2.8.5'
    assert not inventory['missing_dependencies']
    require_no_python_advisories(inventory)
    if mac:
        gui = json.loads((PROJECT / '.work/mac-gui-evidence/mac-ui.json').read_text())
        normal = json.loads((PROJECT / '.work/mac-gui-evidence/normal-launch.json').read_text())
        frozen = json.loads((PROJECT / '.work/macos-frozen.json').read_text())
        assert gui['passed'] and len(gui['checks']) >= 19 and gui['close_reaped_worker_and_server']
        assert normal['passed'] and normal['native_quit_clean']
        assert normal['desktop_check']['native_window_loaded']
        assert normal['desktop_check']['bridge_ready'] and normal['desktop_check']['server_stopped']
        assert frozen['frozen_bundle']['passed']
        plist = plistlib.loads((args.bundle / 'Contents/Info.plist').read_bytes())
        assert plist['CFBundleVersion'] == BUILD_NUMBER and plist['BandprismVersion'] == __version__
    else:
        frozen = json.loads((PROJECT / '.work/windows-frozen.json').read_text())
        assert frozen['passed']
        desktop = json.loads((PROJECT / '.work/windows-desktop.json').read_text())
        assert desktop['passed'] and desktop['internet_marker_retained']
        assert desktop['executable_sha256'] == sha(args.bundle)
    output = PROJECT / '.work/public-beta-2' / name
    output.mkdir(parents=True, exist_ok=False)
    materials = output / 'materials'
    materials.mkdir()
    collect_sources(materials, inventory, args.decoder)
    stem = f'Bandprism-{__version__}'
    archive(materials, output / f'{stem}-{name}-dependency-sources.zip', 'dependency-source-materials')
    source_zip = output / f'{stem}-source.zip'
    subprocess.run(['git', 'archive', '--format=zip', '--output=' + str(source_zip), 'HEAD'], cwd=PROJECT.parent, check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT.parent, text=True).strip()
    app_zip = output / f'{stem}-{name}.zip'
    if mac:
        subprocess.run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(args.bundle), str(app_zip)], check=True)
    else:
        staging = output / 'app-stage' / 'Bandprism'
        staging.mkdir(parents=True)
        shutil.copyfile(args.bundle, staging / 'Bandprism.exe')
        shutil.copyfile(args.bundle, output / f'{stem}-{name}.exe')
        shutil.copytree(PROJECT / 'docs', staging / 'docs')
        shutil.copyfile(PROJECT / 'LICENSE', staging / 'LICENSE')
        shutil.copyfile(materials / 'DEPENDENCY_INVENTORY.json', staging / 'DEPENDENCY_INVENTORY.json')
        (staging / 'README.txt').write_text(
            f'Bandprism {__version__} by ResetLab Craft — Windows public beta\n\n'
            'Open Bandprism.exe as a normal user. Everything is included in that executable; '
            'no _internal folder or ZIP Unblock step is required for the managed-DLL issue. '
            'Microsoft Edge WebView2 Runtime is required.\n'
            'This beta is unsigned. Follow your device security policy.\n'
            'Use Add music for a file/folder, then Analyze. Aa changes text size. '
            'Music, tags and artwork stay unchanged; analysis is local.\n'
            'See docs/USER_GUIDE.md, docs/PRIVACY.md and the release notes for scope and limits.\n'
            'Project source is GPL-3.0-only. Third-party terms and exact sources are in '
            'the separate dependency source ZIP. Rebuild from matching source to replace native libraries. '
            'Do not describe the entire bundle as BSD or LGPL.\n'
            'Downloads and exact matching sources: https://github.com/dj-dinu/resetlab-craft/releases\n',
            encoding='utf-8')
        archive(staging, app_zip, 'Bandprism')
    assets = [dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(output.iterdir()) if p.suffix in {'.zip', '.exe'}]
    (output / f'SHA256SUMS-{name}.txt').write_text(''.join(a['sha256'] + '  ' + a['file'] + '\n' for a in assets))
    (output / f'RELEASE-MANIFEST-{name}.json').write_text(json.dumps(dict(version=__version__,
        build_number=BUILD_NUMBER, platform=name, source_commit=commit, runtime=manifest['runtime'],
        signing=manifest['signing'], assets=assets, published=False), indent=2) + '\n')
    notes = (PROJECT / 'docs/RELEASE_NOTES_0.1.0_BETA2.md').read_text(encoding='utf-8')
    (output / 'RELEASE_NOTES.md').write_text(notes, encoding='utf-8')
    print(json.dumps(dict(prepared=True, platform=name, source_commit=commit, assets=assets, published=False)))


if __name__ == '__main__':
    main()
