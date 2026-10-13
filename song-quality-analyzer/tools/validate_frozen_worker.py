"""Validate the bundled CLI worker without opening or automating its GUI."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import zipfile

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
sys.path.insert(0,str(PROJECT/'.localdeps'))
import numpy as np
from music_library_lab import BUNDLE_NAME

EXPECTED_ENGINE_SHA='7408713ec47389f52f221940c7feeb523f302cd5114186958f36b84ab77fd3cf'
CORE_KEYS=('duration_seconds','coverage_20khz','coverage_18khz','seconds_20khz','seconds_18khz','sample_rate','time_bins')


def digest(path:Path)->str:
    value=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def missing_engine_imports(internal:Path,scanner:Path)->list[str]:
    """Inspect build inventory for the canonical data file's hidden imports."""
    imports=set()
    for node in ast.walk(ast.parse(scanner.read_text(encoding='utf-8'))):
        if isinstance(node,ast.Import):imports.update(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:imports.add(node.module)
    toc=PROJECT/'.work'/'desktop-build'/'pyinstaller-work'/BUNDLE_NAME/'Analysis-00.toc'
    pending=[ast.literal_eval(toc.read_text(encoding='utf-8'))];present=set(sys.builtin_module_names)
    while pending:
        item=pending.pop()
        if isinstance(item,(list,tuple)):
            if len(item)==3 and isinstance(item[0],str) and isinstance(item[2],str) and (item[2].startswith('PYMODULE') or item[2]=='EXTENSION'):
                present.add(item[0])
            pending.extend(item)
    with zipfile.ZipFile(internal/'base_library.zip') as base:
        present.update(name[:-4].replace('/','.') for name in base.namelist() if name.endswith('.pyc'))
    return sorted(imports-present)


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,default=PROJECT/'dist'/BUNDLE_NAME)
    parser.add_argument('--scanner',type=Path,help='Canonical scanner; defaults to ignored local_settings.json scanner_path')
    parser.add_argument('--track',type=Path,action='append',default=[],help='Real-track regression input, repeat to cover HQ/MQ/LQ')
    parser.add_argument('--regression-report',type=Path,default=PROJECT/'.work'/'multiformat-mp3-validation.json',help='Ignored local regression report supplying real input paths when --track is omitted')
    parser.add_argument('--report',type=Path,default=PROJECT/'.work'/'frozen-worker-validation.json')
    args=parser.parse_args()
    settings_path=PROJECT/'local_settings.json'
    settings=json.loads(settings_path.read_text(encoding='utf-8')) if settings_path.is_file() else {}
    scanner_value=args.scanner or settings.get('scanner_path')
    if not scanner_value:parser.error('Provide --scanner or configure scanner_path in local_settings.json')
    scanner=Path(scanner_value).resolve()
    real_paths=list(args.track)
    if not real_paths:
        if not args.regression_report.is_file():parser.error('Provide --track inputs or an existing local --regression-report')
        regressions=json.loads(args.regression_report.read_text(encoding='utf-8'))
        real_paths=[Path(item['path']) for item in regressions.get('mp3_regressions',regressions.get('records',[]))
            if item.get('quality') in ('HQ','MQ','LQ')]
        if not real_paths:parser.error('Local regression report contains no HQ/MQ/LQ inputs')
    executable=args.bundle/(BUNDLE_NAME+'.exe');internal=args.bundle/'_internal'
    bundled_engine=internal/'canonical'/'scan_quality.py';decoder=internal/'decoder'/'libmpg123-0.dll'
    work=PROJECT/'.work'/'frozen-worker-check';work.mkdir(exist_ok=True)
    evidence=work/'evidence';evidence.mkdir(exist_ok=True)
    report={'passed':False,'bundle':str(args.bundle),'executable_sha256':digest(executable),
        'engine_sha256':digest(bundled_engine),'expected_engine_sha256':EXPECTED_ENGINE_SHA,
        'decoder_sha256':digest(decoder),'gui_opened':False,'records':[]}
    try:
        assert digest(scanner)==digest(bundled_engine)==EXPECTED_ENGINE_SHA,'Bundled engine differs from canonical'
        report['missing_engine_imports']=missing_engine_imports(internal,scanner)
        assert not report['missing_engine_imports'],('Canonical data-file imports missing from frozen bundle',report['missing_engine_imports'])
        env=os.environ.copy()
        for key in ('PYTHONPATH','PYTHONHOME','SONG_AUDIT_MPG123_PATH','SONG_AUDIT_NODE','SONG_AUDIT_DECODER_ADDON','SONG_AUDIT_LEGACY_ROOT','SONG_AUDIT_TEST_MP3'):
            env.pop(key,None)
        windows=Path(env.get('WINDIR','C:/Windows'))
        env['PATH']=os.pathsep.join(map(str,(args.bundle,internal,windows/'System32',windows)))
        env['SONG_AUDIT_MPG123_PATH']=str(decoder)
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)

        def worker(arguments:list[str]):
            result=subprocess.run([str(executable),'--scanner-worker',*arguments],cwd=str(work),env=env,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90,creationflags=flags)
            stdout=result.stdout.decode('utf-8','replace');stderr=result.stderr.decode('utf-8','replace')
            assert result.returncode==0,{'returncode':result.returncode,'stdout':stdout[-4000:],'stderr':stderr[-4000:]}
            return stdout,stderr

        stdout,stderr=worker(['--self-test'])
        assert 'SELF_TEST passed:' in stdout,'Frozen windowed worker did not preserve redirected stdout'
        report['self_test']={'passed':True,'stdout':stdout.strip(),'stderr':stderr.strip()}

        fixtures=PROJECT/'.work'/'multiformat-fixtures'
        paths=[fixtures/'first.mp3',fixtures/'HQ-lossless24.wav',fixtures/'MQ-lossless24.aiff',
            fixtures/'LQ-lossless24.flac',fixtures/'aac-native.m4a',fixtures/'HQ-lossless24.m4a',*real_paths]
        before={str(path.resolve()):digest(path) for path in paths}
        os.environ['SONG_AUDIT_MPG123_PATH']=str(decoder)
        source_module=runpy.run_path(str(scanner),run_name='canonical_frozen_reference')
        expected={}
        for path in paths:
            result,power=source_module['analyze_full_duration'](path,True)
            expected[str(path.resolve())]=(result,power)
        real_grades={source_module['spectrum_grade'](expected[str(path.resolve())][0]['coverage_20khz'],
            expected[str(path.resolve())][0]['coverage_18khz']) for path in real_paths}
        assert real_grades=={'HQ','MQ','LQ'},('Real-track regression inputs must cover HQ/MQ/LQ',real_grades)

        payload_path=work/'quality-results.json'
        stdout,stderr=worker(['--full-spectrum',*[str(path) for path in paths],
            '--output',str(payload_path),'--spectra-dir',str(evidence)])
        assert stdout.count('PROGRESS ')==len(paths) and 'DONE ' in stdout,'Frozen progress stdout is incomplete'
        payload=json.loads(payload_path.read_text(encoding='utf-8'))
        assert len(payload['records'])==len(paths),'Frozen report lost a selected input'
        for record in payload['records']:
            key=str(Path(record['path']).resolve());reference,power=expected[key]
            assert record['status']=='analyzed',record
            for field in CORE_KEYS:assert record[field]==reference[field],(key,field,'Frozen metrics differ')
            grade=source_module['spectrum_grade'](reference['coverage_20khz'],reference['coverage_18khz'])
            assert record['quality']==grade,(key,'Frozen grade differs')
            for field in ('codec','container','codec_profile','channels','bit_depth','mpeg_layer','native_frequency_ceiling_hz'):
                assert record.get(field)==reference.get(field),(key,field,'Frozen metadata differs')
            with np.load(record['spectrum_file'],allow_pickle=False) as arrays:
                assert np.array_equal(arrays['power'],power),(key,'Frozen spectrum differs')
                assert np.array_equal(arrays['bin_start_seconds'],reference['spectrum_bin_start_seconds'])
                assert np.array_equal(arrays['bin_duration_seconds'],reference['spectrum_bin_duration_seconds'])
            assert before[key]==digest(Path(key)),(key,'Source file changed')
            report['records'].append({'path':key,'codec':record['codec'],'container':record['container'],
                'quality':grade,'duration_seconds':record['duration_seconds'],
                'coverage_20khz':record['coverage_20khz'],'coverage_18khz':record['coverage_18khz'],
                'all_metrics_and_time_bins_exact':True,'spectrum_and_positions_exact':True,
                'source_unchanged':True,'source_sha256':before[key]})
        report.update(passed=True,stdout_progress_records=stdout.count('PROGRESS '),
            stderr=stderr.strip(),isolated_python_environment=True,bundled_decoder_used=True,
            distinct_codecs=sorted({r['codec'] for r in report['records']}),payload=str(payload_path))
        integrity=PROJECT/'.work'/'integrity-fixtures'
        integrity_output=work/'duration-integrity.json'
        negative=subprocess.run([str(executable),'--scanner-worker','--full-spectrum',
            str(integrity/'declares-4min-decodes-1min.wav'),str(integrity/'valid-60-second-edit.wav'),
            '--output',str(integrity_output)],cwd=str(work),env=env,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,timeout=30,creationflags=flags)
        assert negative.returncode==1,negative.stderr.decode('utf-8','replace')
        measured=json.loads(integrity_output.read_text(encoding='utf-8'))['records']
        bad=next(r for r in measured if r['status']=='integrity_error')
        assert bad['quality'] is None and bad['declared_duration_seconds']==240 and bad['decoded_duration_seconds']==60
        assert next(r for r in measured if r['status']=='analyzed')['quality']=='HQ'
        report['packaged_4min_header_1min_audio_ungraded']=True
        report['packaged_valid_1min_edit_hq']=True
    except Exception as exc:
        report['error']=repr(exc)
        raise
    finally:
        args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(json.dumps({'passed':report['passed'],'records':len(report['records']),'report':str(args.report),
            'error':report.get('error')},indent=2))


if __name__=='__main__':main()
