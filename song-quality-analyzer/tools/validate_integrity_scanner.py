"""Synthetic duration-integrity regressions for the canonical engine."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import struct
import sys
import wave

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'.localdeps'))

def validate(module,project):
    folder=project/'.work'/'integrity-fixtures';folder.mkdir(exist_ok=True)
    fixtures=project/'.work'/'multiformat-fixtures';checks=[]
    def scan(path,expected=None,fail=False):
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            record,_=module['analyze_full_duration'](path,True)
        except Exception as exc:
            if not fail:raise
            assert isinstance(exc,module['_AudioIntegrityError']) or isinstance(exc,(ValueError,RuntimeError)),repr(exc)
            record={'status':'ungraded','reason':str(exc)}
            if isinstance(exc,module['_AudioIntegrityError']):record.update(exc.details)
        else:
            assert not fail,('Incomplete file received measurements',path)
            if expected:assert record['integrity_check']==expected,(path,record)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
        checks.append({'fixture':path.name,'passed':True,'integrity_check':record.get('integrity_check'),'source_unchanged':True})
        return record

    # Exact user example: high-bandwidth60s of PCM; WAV header claims240s.
    with wave.open(str(fixtures/'HQ-lossless.wav'),'rb') as audio:
        params=audio.getparams();pcm=audio.readframes(audio.getnframes())
    full=folder/'valid-60-second-edit.wav'
    with wave.open(str(full),'wb') as audio:audio.setparams(params);audio.writeframes(pcm*12)
    valid=scan(full,'duration_matches_declaration')
    assert valid['duration_seconds']==60 and module['spectrum_grade'](valid['coverage_20khz'],valid['coverage_18khz'])=='HQ'
    damaged=bytearray(full.read_bytes());at=damaged.index(b'data');size=int.from_bytes(damaged[at+4:at+8],'little')
    damaged[at+4:at+8]=(size*4).to_bytes(4,'little');damaged[4:8]=(len(damaged)-8+size*3).to_bytes(4,'little')
    short=folder/'declares-4min-decodes-1min.wav';short.write_bytes(damaged)
    mismatch=scan(short,fail=True)
    assert mismatch['declared_duration_seconds']==240 and mismatch['decoded_duration_seconds']==60

    for name in ('HQ-lossless.aiff','HQ-lossless.flac','HQ-lossless.m4a','aac-native.m4a','first.mp3'):
        scan(fixtures/name)
    aiff=bytearray((fixtures/'HQ-lossless.aiff').read_bytes());at=aiff.index(b'COMM')+10
    aiff[at:at+4]=(int.from_bytes(aiff[at:at+4],'big')*4).to_bytes(4,'big')
    target=folder/'incomplete.aiff';target.write_bytes(aiff);scan(target,fail=True)
    flac=bytearray((fixtures/'HQ-lossless.flac').read_bytes());packed=int.from_bytes(flac[18:26],'big')
    samples=packed&((1<<36)-1);packed=(packed>>36<<36)|samples*4
    flac[18:26]=packed.to_bytes(8,'big');target=folder/'incomplete.flac';target.write_bytes(flac);scan(target,fail=True)
    mp3=bytearray((fixtures/'first.mp3').read_bytes())
    positions=[p for p in (mp3.find(b'Info'),mp3.find(b'Xing')) if p>=0]
    assert positions,'MP3 fixture must retain a declared frame-count header'
    at=min(positions);assert int.from_bytes(mp3[at+4:at+8],'big')&1
    frames=int.from_bytes(mp3[at+8:at+12],'big');mp3[at+8:at+12]=(frames*4).to_bytes(4,'big')
    target=folder/'incomplete.mp3';target.write_bytes(mp3);scan(target,fail=True)
    for name in ('aac-native.m4a','HQ-lossless.m4a'):
        raw=(fixtures/name).read_bytes();target=folder/('truncated-'+name);target.write_bytes(raw[:len(raw)//3]);scan(target,fail=True)
    scan(fixtures/'aac-native.aac','duration_not_verifiable')
    target=folder/'misleading-title-duration.mp3';shutil.copyfile(fixtures/'first.mp3',target)
    from mutagen.id3 import ID3,TLEN,ID3NoHeaderError
    try:tags=ID3(target)
    except ID3NoHeaderError:tags=ID3()
    tags.add(TLEN(encoding=3,text=['240000']));tags.save(target)
    scan(target)
    # Encoder padding / incomplete declaration does not fabricate corruption.
    record={'duration_seconds':.02,'analysis_context':[]}
    module['_verify_audio_duration'](fixtures/'aac-native.aac',record)
    assert record['integrity_check']=='duration_not_verifiable'
    checks.append({'fixture':'valid-short-unknown-duration','passed':True})
    output=folder/'integrity-cli.json'
    try:module['full_spectrum_cli'](['--full-spectrum',str(full),str(short),'--output',str(output)])
    except SystemExit as exc:assert exc.code==1
    else:raise AssertionError('Integrity failure must be reported as a failed input')
    payload=json.loads(output.read_text(encoding='utf-8'));bad=next(r for r in payload['records'] if r['path']==str(short.resolve()))
    assert bad['quality'] is None and bad['status']=='integrity_error'
    assert bad['declared_duration_seconds']==240 and bad['decoded_duration_seconds']==60
    checks.append({'fixture':'canonical-cli-integrity-error-ungraded','passed':True})
    return {'fixture_cases':len(checks),'checks':checks,'user_4min_1min_case':'ungraded_duration_mismatch','valid_1min_edit':'HQ'}

def main():
    settings=json.loads((PROJECT/'local_settings.json').read_text(encoding='utf-8-sig'))
    os.environ['SONG_AUDIT_MPG123_PATH']=settings['decoder_path']
    module=runpy.run_path(settings['scanner_path'],run_name='canonical_integrity_validation')
    report=validate(module,PROJECT)
    (PROJECT/'.work'/'integrity-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
