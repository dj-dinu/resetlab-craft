"""Record installed dependencies and optionally query public OSV advisories.

Only public package names and versions leave the computer with --query-advisories.
Music, paths, settings and tokens are never included. Native-library coverage is
recorded separately and is not implied by a Python-package advisory lookup.
"""
import argparse
import ctypes
import hashlib
import importlib.metadata as metadata
import json
import platform
import pyexpat
import ssl
from pathlib import Path
import sys
from urllib.request import Request, urlopen

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / '.localdeps'))
from packaging.requirements import Requirement


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query-advisories', action='store_true')
    args = parser.parse_args()
    pending = ['av', 'numpy', 'mutagen', 'pywebview', 'pyinstaller', 'Pillow']
    packages = {}; missing = []
    while pending:
        name = pending.pop()
        normalized = name.lower().replace('_', '-')
        if normalized in packages:
            continue
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        packages[normalized] = {'name': distribution.metadata['Name'], 'version': distribution.version,
            'license_expression': distribution.metadata.get('License-Expression'),
            'license_field': distribution.metadata.get('License')}
        for text in distribution.requires or []:
            dependency = Requirement(text)
            if dependency.marker is None or dependency.marker.evaluate({'extra': ''}):
                pending.append(dependency.name)
    report = {'packages': list(packages.values()), 'missing_dependencies': sorted(set(missing)),
        'python_version': platform.python_version(),
        'runtime': {'python': platform.python_version(), 'openssl': ssl.OPENSSL_VERSION,
                    'expat': pyexpat.EXPAT_VERSION}, 'native_advisory_review_complete': False,
        'redistribution_review_complete': False, 'source_and_relink_materials_complete': False}
    import av
    report['ffmpeg_library_versions'] = {key: list(value) for key, value in av.library_versions.items()}
    av_package = Path(av.__file__).resolve().parent
    candidates = [av_package.parent / 'av.libs', av_package / '.dylibs']
    libraries = next((p for p in candidates if p.is_dir()), None)
    suffix = '*.dylib' if sys.platform == 'darwin' else '*.dll'
    if sys.platform in {'win32', 'darwin'} and libraries:
        codec = ctypes.CDLL(str(next(p for p in libraries.glob(suffix) if 'avcodec' in p.name).resolve()))
        util = ctypes.CDLL(str(next(p for p in libraries.glob(suffix) if 'avutil' in p.name).resolve()))
        codec.avcodec_license.restype = ctypes.c_char_p
        codec.avcodec_configuration.restype = ctypes.c_char_p
        util.av_version_info.restype = ctypes.c_char_p
        report['ffmpeg'] = {'version': util.av_version_info().decode(),
            'reported_license': codec.avcodec_license().decode(),
            'configuration': codec.avcodec_configuration().decode()}
        report['native_files'] = [{'name': path.name,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in sorted(libraries.glob(suffix))]
    if args.query_advisories:
        queries = [{'package': {'name': row['name'], 'ecosystem': 'PyPI'},
            'version': row['version']} for row in report['packages']]
        request = Request('https://api.osv.dev/v1/querybatch',
            data=json.dumps({'queries': queries}).encode(), headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=30) as response:
            results = json.loads(response.read())['results']
        assert len(results) == len(queries), 'Incomplete advisory response'
        report['python_package_advisories'] = [{'name': row['name'], 'version': row['version'],
            'advisory_ids': [item['id'] for item in result.get('vulns', [])]}
            for row, result in zip(report['packages'], results)]
        report['advisory_source'] = 'https://api.osv.dev/v1/querybatch'
    destination = PROJECT / '.work/release-dependency-review.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'packages': len(report['packages']), 'missing': report['missing_dependencies'],
        'queried': args.query_advisories,
        'known_python_advisories': sum(len(row['advisory_ids']) for row in report.get('python_package_advisories', [])),
        'affected_python_packages': [{'name': row['name'], 'version': row['version'],
            'advisory_count': len(row['advisory_ids'])}
            for row in report.get('python_package_advisories', []) if row['advisory_ids']],
        'native_review_complete': False, 'redistribution_complete': False}, indent=2))


if __name__ == '__main__':
    main()
