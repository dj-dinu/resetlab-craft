"""Verify native startup with an Internet-zone marker on an owned EXE copy."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    assert sys.platform == 'win32'
    base = PROJECT / '.work/test-temp'
    base.mkdir(parents=True, exist_ok=True)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    source_sha = digest(args.executable)
    results = []
    with tempfile.TemporaryDirectory(prefix='download-café-', dir=base) as temporary:
        owned = Path(temporary) / 'Bandprism.exe'
        shutil.copyfile(args.executable, owned)
        marker = '[ZoneTransfer]\nZoneId=3\n'
        with open(str(owned) + ':Zone.Identifier', 'w', encoding='ascii') as stream:
            stream.write(marker)
        for mode in ('--runtime-info', '--desktop-self-test'):
            run = subprocess.run([str(owned.resolve()), mode], capture_output=True, text=True,
                                 encoding='utf-8', timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
            assert run.returncode == 0, (mode, run.returncode, run.stdout[-3000:], run.stderr[-3000:])
            result = json.loads(run.stdout)
            if mode == '--desktop-self-test':
                assert result['passed'] and result['native_window_loaded'] and result['server_stopped'], result
                assert result['executable_zone_before'] == 3 and result['download_marker_retained'], result
                assert all(zone is None for zone in result['managed_library_zones'].values()), result
            results.append({'mode': mode, 'result': result})
        with open(str(owned) + ':Zone.Identifier', encoding='ascii') as stream:
            assert stream.read() == marker
        assert digest(owned) == source_sha == digest(args.executable)
    report = dict(passed=True, executable_sha256=source_sha, internet_marker_retained=True,
                  executable_bytes_unchanged=True, os_security_settings_changed=False,
                  synthetic_marker_scope='owned copy only; no download/referrer URLs', checks=results)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
