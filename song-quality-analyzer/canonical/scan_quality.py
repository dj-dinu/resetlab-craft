import os, sys, json, time, math, re, base64, hashlib, struct, ctypes as C
import subprocess, threading, queue, concurrent.futures, collections, wave
from pathlib import Path
import shutil
from ctypes import util as C_util
import numpy as np

ROOT = Path(os.environ.get('SONG_AUDIT_LEGACY_ROOT',os.getcwd())).resolve()
WORK = Path(__file__).parent
NODE = os.environ.get('SONG_AUDIT_NODE') or shutil.which('node')
EXTS = {'.mp3', '.m4a', '.aac', '.wav', '.mp4'}
N = 8192
WIN = np.hanning(N).astype(np.float32)
TLS = threading.local()
PROCS = []
LOCK = threading.RLock()
CACHE = {}

NODE_CODE = r'''
const addon=require(process.env.SONG_AUDIT_DECODER_ADDON);
const readline=require("readline");
const rl=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
const N=8192;
const send=async b=>{if(!process.stdout.write(b))await new Promise(resolve=>process.stdout.once("drain",resolve));};
(async()=>{for await(const line of rl){if(!line)continue;const q=JSON.parse(line);if(q.exit)break;
try {let meta,parts=[];
if(q.segments){for(const text of q.segments){
const b=Buffer.from(text,"base64");const ab=b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);
const r=await addon.decodeAudioData(ab,44100);const skip=Math.floor(r.sampleRate*0.8);const limit=Math.floor(r.sampleRate*8);
const piece=r.data.map(a=>{const bytes=Buffer.from(a);const usable=Math.max(0,Math.min(bytes.length/4-skip,limit));const samples=Math.floor(usable/N)*N;return Buffer.from(bytes.subarray(skip*4,(skip+samples)*4));});
if(piece[0].length)parts.push(piece);meta={sr:r.sampleRate,ch:r.channels,coverage:"3 sections across audio data"};
}if(!parts.length)throw new Error("No decodable sampled sections");
}else{const r=await addon.decodeAudioData(q.path,44100);const samples=r.data[0].byteLength/4;const seconds=samples/r.sampleRate;
if(seconds<=30){parts=[r.data.map(a=>Buffer.from(a))];meta={sr:r.sampleRate,ch:r.channels,coverage:"Full short track",track_seconds:seconds};}
else{for(const fraction of [0.08,0.45,0.85]){const length=Math.floor(r.sampleRate*8/N)*N;const start=Math.max(0,Math.min(samples-length,Math.floor(samples*fraction)));parts.push(r.data.map(a=>Buffer.from(Buffer.from(a).subarray(start*4,(start+length)*4))));}
meta={sr:r.sampleRate,ch:r.channels,coverage:"3 sections across decoded track",track_seconds:seconds};}}
const channels=[];for(let c=0;c<meta.ch;c++)channels.push(Buffer.concat(parts.map(p=>p[c])));
meta.bytes=channels.map(a=>a.length);meta.section_samples=parts.map(p=>p[0].length/4);
const header=Buffer.from(JSON.stringify(meta));const prefix=Buffer.alloc(8);prefix.write("SPCM");prefix.writeUInt32LE(header.length,4);
await send(prefix);await send(header);for(const c of channels)await send(c);
}catch(e){const header=Buffer.from(JSON.stringify({error:e.message}));const prefix=Buffer.alloc(8);prefix.write("SPCM");prefix.writeUInt32LE(header.length,4);await send(prefix);await send(header);}
}process.exit(0);})();
'''

def read_exact(stream, size):
    parts=[]
    while size:
        block=stream.read(size)
        if not block: raise RuntimeError('Decoder stopped before returning audio')
        parts.append(block); size-=len(block)
    return b''.join(parts)

def get_process():
    if not hasattr(TLS, 'proc') or TLS.proc.poll() is not None:
        node=NODE
        addon=os.environ.get('SONG_AUDIT_DECODER_ADDON')
        if not node or not addon:
            raise RuntimeError('Legacy sampled decoding needs Node and an optional audio-decoder addon. '
                'Configure SONG_AUDIT_NODE and SONG_AUDIT_DECODER_ADDON, or use --full-spectrum '
                'for MP3 grading with libmpg123 instead.')
        env=os.environ.copy();env['SONG_AUDIT_DECODER_ADDON']=os.path.expanduser(addon)
        TLS.proc=subprocess.Popen([node, '-e', NODE_CODE], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,env=env)
        with LOCK: PROCS.append(TLS.proc)
    return TLS.proc

def header_info(path):
    offset=0
    with open(path,'rb') as f:
        first=f.read(10)
        if first[:3]==b'ID3' and len(first)==10:
            offset=10+sum((v&127)<<(7*(3-i)) for i,v in enumerate(first[6:10]))
            f.seek(offset)
        else: f.seek(0)
        tail=f.read(64)
        if tail.startswith((b'ERR_SESSION',b'ERR_GEOLOCK',b'#EXTM3U')):
            return offset, tail[:24].decode('ascii','replace')
    return offset,None

FRAME_MATCH=re.compile(rb'\xff[\xe0-\xff]')
def mp3_header(data,pos):
    if pos+4>len(data): return None
    a,b,c,d=data[pos:pos+4]
    if a!=255 or (b&224)!=224:return None
    version=(b>>3)&3;layer=(b>>1)&3;bi=(c>>4)&15;ri=(c>>2)&3
    if version==1 or layer==0 or bi in (0,15) or ri==3:return None
    sr=(44100,48000,32000)[ri]//(1 if version==3 else 2 if version==2 else 4)
    if version==3:
        rates={1:(0,32,40,48,56,64,80,96,112,128,160,192,224,256,320),
            2:(0,32,48,56,64,80,96,112,128,160,192,224,256,320,384),
            3:(0,32,64,96,128,160,192,224,256,288,320,352,384,416,448)}[layer]
    else: rates=(0,8,16,24,32,40,48,56,64,80,96,112,128,144,160) if layer==1 else (0,32,48,56,64,80,96,112,128,144,160,176,192,224,256)
    rate=rates[bi];pad=(c>>1)&1
    length=4*(12000*rate//sr+pad) if layer==3 else (72000 if layer==1 and version!=3 else 144000)*rate//sr+pad
    samples=384 if layer==3 else 576 if layer==1 and version!=3 else 1152
    return length,sr,samples,version,layer,rate

def frame_start(data):
    for match in FRAME_MATCH.finditer(data,0,min(len(data),65536)):
        at=match.start();a=mp3_header(data,at)
        if not a:continue
        b=mp3_header(data,at+a[0]);c=mp3_header(data,at+a[0]+b[0]) if b else None
        if b and c and a[1:5]==b[1:5]==c[1:5]:return at,a
    raise RuntimeError('No consecutive MPEG audio frames found')

def mp3_segments(path,offset):
    size=os.path.getsize(path)
    with open(path,'rb') as f:
        f.seek(offset);initial=f.read(65536);_,header=frame_start(initial)
        if (size-offset)*8/(header[5]*1000)<30:return None
        segments=[]
        for fraction in (0.08,0.45,0.85):
            f.seek(offset+int((size-offset)*fraction));data=f.read(1048576)
            start,_=frame_start(data);pos=start;seconds=0
            while seconds<9:
                info=mp3_header(data,pos)
                if not info or pos+info[0]>len(data):break
                seconds+=info[2]/info[1];pos+=info[0]
            if seconds<1.3:raise RuntimeError('Insufficient MP3 audio at sample position')
            segments.append(base64.b64encode(data[start:pos]).decode('ascii'))
        return segments

def native_decode(path,offset):
    p=get_process();request={'path':str(path)}
    if path.suffix.lower()=='.mp3':
        try: segments=mp3_segments(path,offset)
        except Exception: segments=None
        if segments:request['segments']=segments
    answers=queue.Queue()
    def collect():
        try:
            magic=p.stdout.read(4)
            while magic!=b'SPCM':
                b=p.stdout.read(1)
                if not b:raise RuntimeError('Decoder stopped')
                magic=magic[1:]+b
            size=struct.unpack('<I',read_exact(p.stdout,4))[0]
            if size>100000:raise RuntimeError('Invalid decoder response')
            meta=json.loads(read_exact(p.stdout,size))
            if 'error' in meta:raise RuntimeError(meta['error'])
            pcm=[np.frombuffer(read_exact(p.stdout,n),dtype='<f4') for n in meta['bytes']]
            answers.put((meta,pcm,None))
        except Exception as exc:answers.put((None,None,exc))
    threading.Thread(target=collect,daemon=True).start()
    try:
        p.stdin.write((json.dumps(request)+'\n').encode());p.stdin.flush()
        meta,pcm,error=answers.get(timeout=20)
        if error:raise error
        return meta,pcm
    except Exception:
        if p.poll() is None:p.terminate()
        try:p.wait(timeout=2)
        except Exception:p.kill()
        raise

# Decode dependencies are loaded only when a track is analyzed. Synthetic
# self-tests and help do not require libmpg123, Rekordbox, DJ.Studio, or Node.
MPG=None

def _mpg123_candidates():
    configured=os.environ.get('SONG_AUDIT_MPG123_PATH')
    if configured:
        return [os.path.expandvars(os.path.expanduser(configured))]
    if sys.platform=='win32':names=('libmpg123-0.dll','libmpg123.dll','mpg123.dll')
    elif sys.platform=='darwin':names=('libmpg123.0.dylib','libmpg123.dylib')
    else:names=('libmpg123.so.0','libmpg123.so')
    candidates=[str(folder/name) for folder in (WORK/'lib',WORK) for name in names]
    discovered=C_util.find_library('mpg123')
    if discovered:candidates.append(discovered)
    if sys.platform=='darwin':
        candidates.extend(str(Path(prefix)/name) for prefix in
            ('/opt/homebrew/lib','/usr/local/lib') for name in names)
    candidates.extend(names)
    return list(dict.fromkeys(candidates))

def _ensure_mpg123():
    global MPG,READ_CB,SEEK_CB
    if MPG is not None:return
    with LOCK:
        if MPG is not None:return
        failures=[];lib=None
        for candidate in _mpg123_candidates():
            try:lib=C.CDLL(candidate);break
            except OSError as exc:failures.append(str(exc))
        if lib is None:
            detail=failures[-1] if failures else 'no library candidates'
            raise RuntimeError('MP3 spectrum analysis needs libmpg123 for this OS/architecture. '
                'Install or bundle libmpg123 and set SONG_AUDIT_MPG123_PATH to its DLL/dylib/shared '
                'library path. Rekordbox and DJ.Studio are optional. Loader detail: '+detail)
        functions={}
        def bind(short,name,result,args):
            fn=getattr(lib,name);fn.restype=result;fn.argtypes=args;functions[short]=fn;return fn
        if bind('_init','mpg123_init',C.c_int,[])()!=0:
            raise RuntimeError('libmpg123 initialization failed')
        bind('mnew','mpg123_new',C.c_void_p,[C.c_char_p,C.POINTER(C.c_int)])
        bind('mdel','mpg123_delete',None,[C.c_void_p])
        bind('mnone','mpg123_format_none',C.c_int,[C.c_void_p])
        bind('mfmt','mpg123_format',C.c_int,[C.c_void_p,C.c_long,C.c_int,C.c_int])
        bind('mget','mpg123_getformat',C.c_int,[C.c_void_p,C.POINTER(C.c_long),C.POINTER(C.c_int),C.POINTER(C.c_int)])
        # off_t has a platform ABI; prefer the explicit 64-bit wrapper family
        # where the complete older stable API is exported. Standard macOS
        # off_t is 64 bits; the original Windows DLL uses 32-bit off_t.
        family=('mpg123_seek','mpg123_length','mpg123_replace_reader_handle','mpg123_open_handle')
        suffix='_64' if all(hasattr(lib,name+'_64') for name in family) else ''
        offset_type=C.c_int64 if suffix or sys.platform=='darwin' else C.c_long
        bind('mseek','mpg123_seek'+suffix,offset_type,[C.c_void_p,offset_type,C.c_int])
        bind('mlength','mpg123_length'+suffix,offset_type,[C.c_void_p])
        bind('mscan','mpg123_scan',C.c_int,[C.c_void_p])
        bind('mread','mpg123_read',C.c_int,[C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)])
        read_type=C.CFUNCTYPE(C.c_ssize_t,C.c_void_p,C.c_void_p,C.c_size_t)
        seek_type=C.CFUNCTYPE(offset_type,C.c_void_p,offset_type,C.c_int)
        bind('mreplace','mpg123_replace_reader_handle'+suffix,C.c_int,[C.c_void_p,read_type,seek_type,C.c_void_p])
        bind('mhandle','mpg123_open_handle'+suffix,C.c_int,[C.c_void_p,C.c_void_p])
        functions.pop('_init')
        globals().update(functions)
        READ_CB=read_type;SEEK_CB=seek_type;MPG=lib

def mpg_decode(path):
    _ensure_mpg123()
    h=mnew(None,None)
    with open(path,'rb') as f:
        @READ_CB
        def read_cb(handle,buffer,size):
            try:
                data=f.read(size);C.memmove(buffer,data,len(data));return len(data)
            except Exception:return -1
        @SEEK_CB
        def seek_cb(handle,offset,whence):
            try:return f.seek(offset,whence)
            except Exception:return -1
        try:
            mnone(h)
            for r in (8000,11025,12000,16000,22050,24000,32000,44100,48000):mfmt(h,r,3,0x200)
            if mreplace(h,read_cb,seek_cb,None) or mhandle(h,C.c_void_p(1)):raise RuntimeError('Alternate decoder could not open audio')
            sr=C.c_long();channels=C.c_int();encoding=C.c_int()
            if mget(h,C.byref(sr),C.byref(channels),C.byref(encoding)) or encoding.value!=0x200:raise RuntimeError('Alternate decoder could not read audio format')
            total=mlength(h)
            if total<=0:mscan(h);total=mlength(h)
            if total<=0:raise RuntimeError('Alternate decoder could not determine audio duration')
            pieces=[[] for _ in range(channels.value)];lengths=[]
            section=min(total,sr.value*8)
            for fraction in (0.08,0.45,0.85):
                position=max(0,min(total-section,int(total*fraction)))
                if mseek(h,position,0)<0:raise RuntimeError('Alternate decoder seek failed')
                request=section*channels.value*4;buffer=C.create_string_buffer(request);used=0
                while used<request:
                    done=C.c_size_t();rc=mread(h,C.byref(buffer,used),request-used,C.byref(done));used+=done.value
                    if rc in (-10,-12):break
                    if rc not in (0,-11):raise RuntimeError('Alternate decoder could not decode audio')
                pcm=np.frombuffer(buffer,dtype='<f4',count=used//4).reshape(-1,channels.value)
                samples=len(pcm)//N*N;lengths.append(samples)
                for c in range(channels.value):pieces[c].append(pcm[:samples,c].copy())
            return {'sr':sr.value,'ch':channels.value,'section_samples':lengths,'coverage':'3 sections, alternate decoder','track_seconds':total/sr.value},[np.concatenate(p) for p in pieces]
        finally:mdel(h)

def wav_decode(path):
    with wave.open(str(path),'rb') as w:
        sr=w.getframerate();channels=w.getnchannels();width=w.getsampwidth();total=w.getnframes()
        pieces=[[] for _ in range(channels)];lengths=[];section=min(total,sr*8)
        for fraction in (0.08,0.45,0.85):
            w.setpos(max(0,min(total-section,int(total*fraction))));raw=w.readframes(section)
            if width==2:pcm=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
            elif width==4:pcm=np.frombuffer(raw,dtype='<i4').astype(np.float32)/2147483648
            elif width==3:
                b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3)
                value=b[:,0].astype(np.int32)|(b[:,1].astype(np.int32)<<8)|(b[:,2].astype(np.int32)<<16)
                value=(value^0x800000)-0x800000;pcm=value.astype(np.float32)/8388608
            else:raise RuntimeError('Unsupported WAV sample width')
            pcm=pcm.reshape(-1,channels);samples=len(pcm)//N*N;lengths.append(samples)
            for c in range(channels):pieces[c].append(pcm[:samples,c].copy())
        return {'sr':sr,'ch':channels,'section_samples':lengths,'coverage':'3 sections from WAV','track_seconds':total/sr},[np.concatenate(p) for p in pieces]

def measure(sr,pcm):
    samples=min(len(p) for p in pcm);count=samples//N
    if not count:raise ValueError('Too short for spectrum analysis')
    power=None;active=0
    for at in range(0,count,128):
        size=min(128,count-at);local=None;energy=None
        for channel in pcm:
            block=channel[at*N:(at+size)*N].reshape(size,N);e=np.mean(block**2,axis=1)
            energy=e if energy is None else energy+e
            fft=np.fft.rfft(block*WIN,axis=1);value=np.abs(fft)**2
            local=value if local is None else local+value
        keep=energy/len(pcm)>1e-7
        if keep.any():
            part=local[keep].sum(axis=0)/len(pcm);power=part if power is None else power+part;active+=int(keep.sum())
    if power is None:raise ValueError('Too little active audio for spectrum analysis')
    p=power/active;hz=np.fft.rfftfreq(N,1/sr);ref=float(p[(hz>=1000)&(hz<10000)].mean())
    if ref<=0:raise ValueError('No usable frequency reference')
    smooth=np.convolve(p,np.ones(19)/19,'same');db=10*np.log10(np.maximum(smooth,1e-30)/ref)
    selected=(hz>=10000)&(db>-65);edge=float(hz[np.flatnonzero(selected)[-1]]) if selected.any() else None
    frequencies=np.arange(11000,min(21500,sr/2-800),100)
    indexes=np.searchsorted(hz,np.column_stack((frequencies-500,frequencies-150,frequencies+150,frequencies+500)))
    cumulative=np.concatenate(([0.],np.cumsum(p[::-1])));a,b,c,d=indexes.T;length=len(p)
    lo=(cumulative[length-a]-cumulative[length-b])/(b-a);hi=(cumulative[length-c]-cumulative[length-d])/(d-c)
    before=10*np.log10(np.maximum(lo,1e-30)/ref);after=10*np.log10(np.maximum(hi,1e-30)/ref)
    valid=(before>-50)&(after<-65);sharp=None
    if valid.any():
        index=int(np.argmax(np.where(valid,before-after,-np.inf)))
        sharp={'db':round(float(before[index]-after[index]),1),'hz':int(frequencies[index])}
    status='inconclusive'
    if sharp and sharp['db']>=25 and sharp['hz']<=18000 and edge is not None and edge<18500:status='low_cutoff'
    elif sharp and sharp['db']>=25 and sharp['hz']<19500 and edge is not None and edge<19500:status='mid_cutoff'
    elif edge is not None and edge>=19500:status='wide_band'
    return {'status':status,'analysis_rate':sr,'upper_energy_edge_hz':None if edge is None else round(edge),'sharp_drop':sharp,'sampled_audio_seconds':round(samples/sr,2)}

def audio_hash(path,offset):
    size=path.stat().st_size;end=size
    with open(path,'rb') as f:
        if path.suffix.lower()=='.mp3' and size>=128:
            f.seek(size-128)
            if f.read(3)==b'TAG':end-=128
        f.seek(min(offset,size));remaining=max(0,end-offset);digest=hashlib.sha256()
        while remaining:
            block=f.read(min(remaining,1048576))
            if not block:break
            digest.update(block);remaining-=len(block)
    return path.suffix.lower()+':'+digest.hexdigest()

def analyze(path):
    stat=path.stat();base={'path':str(path.relative_to(ROOT)),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,'duplicate_reused':False}
    if '(hq)' in path.name.lower():return dict(base,status='skipped_hq',reason='Skipped as requested because filename contains (HQ)')
    offset,invalid=header_info(path)
    if invalid:return dict(base,status='invalid_audio',reason=invalid)
    key=audio_hash(path,offset)
    with LOCK:
        cached=CACHE.get(key)
        owner=cached is None
        if owner:cached=concurrent.futures.Future();CACHE[key]=cached
    if not owner:return dict(cached.result(),**dict(base,duplicate_reused=True))
    try:
        alternate=False
        if 'Tera Ban Jaunga - DJ Doc X DJ Ajay' in path.name or path.name.startswith('Aata Kaavala Full Video Song'):
            meta,pcm=mpg_decode(path);alternate=True
        elif path.suffix.lower()=='.wav' and stat.st_size>100000000:meta,pcm=wav_decode(path)
        else:
            try:meta,pcm=native_decode(path,offset)
            except Exception:
                if path.suffix.lower()!='.mp3':raise
                meta,pcm=mpg_decode(path);alternate=True
        result=measure(meta['sr'],pcm);sections=[];position=0
        for length in meta['section_samples']:
            try:section=measure(meta['sr'],[p[position:position+length] for p in pcm])
            except ValueError:section={'status':'inconclusive','upper_energy_edge_hz':None,'sharp_drop':None}
            sections.append(section);position+=length
        if any(s['status']=='low_cutoff' for s in sections) and any(s['status']=='wide_band' for s in sections):result['status']='mixed_bandwidth'
        result['sections']=sections;result['coverage']=meta['coverage']
        if 'track_seconds' in meta:result['track_seconds']=round(meta['track_seconds'],2)
        if alternate:result['reason']='Alternate decoder used'
    except ValueError as exc:result={'status':'inconclusive','reason':str(exc)}
    except Exception as exc:result={'status':'decode_error','reason':str(exc)}
    cached.set_result(dict(result))
    return dict(result,**base)

def safe_analyze(path):
    try:return analyze(path)
    except Exception as exc:
        stat=path.stat()
        return {'path':str(path.relative_to(ROOT)),'status':'decode_error','reason':str(exc),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,'duplicate_reused':False}

def inventory():
    return sorted((p for p in ROOT.rglob('*') if p.is_file() and p.suffix.lower() in EXTS and not p.name.startswith('._')),key=lambda p:str(p).casefold())

def shutdown():
    for p in PROCS:
        if p.poll() is None:
            try:p.stdin.write(b'{"exit":true}\n');p.stdin.flush()
            except Exception:p.terminate()
    for p in PROCS:
        try:p.wait(timeout=3)
        except Exception:p.kill()

def main():
    if not os.environ.get('SONG_AUDIT_LEGACY_ROOT'):
        raise RuntimeError('Legacy sampled scans require explicit SONG_AUDIT_LEGACY_ROOT; use --full-spectrum with explicit input paths for quality grades')
    records={};start=time.monotonic();last=start
    paths=inventory();print('START '+json.dumps({'listed_files':len(paths),'workers':8}),flush=True)
    try:
        with open(WORK/'quality_records.ndjson','w',encoding='utf-8') as log:
            for cycle in range(3):
                pending=[p for p in paths if str(p.relative_to(ROOT)) not in records or
                    (records[str(p.relative_to(ROOT))].get('size'),records[str(p.relative_to(ROOT))].get('mtime_ns'))!=(p.stat().st_size,p.stat().st_mtime_ns)]
                if not pending:break
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    futures={pool.submit(safe_analyze,p):p for p in pending}
                    for future in concurrent.futures.as_completed(futures):
                        result=future.result();records[result['path']]=result;log.write(json.dumps(result,ensure_ascii=False)+'\n');log.flush()
                        now=time.monotonic()
                        if len(records)%500==0 or now-last>=20:
                            print('PROGRESS '+json.dumps({'done':len(records),'total':len(paths),'seconds':round(now-start),'counts':dict(collections.Counter(r['status'] for r in records.values()))}),flush=True);last=now
                paths=inventory()
        final=[]
        for path in paths:
            name=str(path.relative_to(ROOT));result=records.get(name)
            if result is None:result={'path':name,'status':'inconclusive','reason':'Added after the final screening pass'}
            elif (result.get('size'),result.get('mtime_ns'))!=(path.stat().st_size,path.stat().st_mtime_ns):result=dict(result,status='inconclusive',reason='Changed after screening; recheck required')
            final.append(result)
        payload={'root':str(ROOT),'as_of_date':'2026-10-08','method':'Sampled spectrum screening. Usually three sections near 8%, 45%, and 85% of audio data; short tracks analyzed in full. 8192-sample Hann FFT. Sharp-drop threshold 25 dB. Spectrum alone cannot establish original encoding bitrate.','elapsed_seconds':round(time.monotonic()-start),'records':final,'counts':dict(collections.Counter(r['status'] for r in final))}
        with open(WORK/'quality_results.json','w',encoding='utf-8') as f:json.dump(payload,f,ensure_ascii=False)
        print('DONE '+json.dumps({'total':len(final),'seconds':payload['elapsed_seconds'],'counts':payload['counts'],'data_file':str(WORK/'quality_results.json')}),flush=True)
    finally:shutdown()


# Full-duration mode added 2026-10-09 for the user's 30% / 20 kHz quality rule.
FULL_N=2048;FULL_WIN=np.hanning(FULL_N);FULL_HOP=1024
FULL_COVERAGE_THRESHOLD=.40
FULL_RULE_VERSION="2026-10-16-hq20-mq15-40-percent"

def full_spectrum_power(pcm,sr):
    blocks=np.lib.stride_tricks.sliding_window_view(pcm,FULL_N,axis=0)[::FULL_HOP]
    # sliding_window_view shape: time, channels, FFT samples.
    ft=np.fft.rfft(blocks*FULL_WIN,axis=-1)
    return ((2*np.abs(ft)/FULL_WIN.sum())**2).mean(axis=(0,1))

def full_spectrum_metrics(pcm,sr):
    p=full_spectrum_power(pcm,sr);hz=np.fft.rfftfreq(FULL_N,1/sr)
    ref=p[(hz>=1000)&(hz<10000)].mean()
    active=float(p.sum())>3e-6
    def reaches(f):
        band=p[hz>=f]  # Only frequencies at or above the requested cutoff count.
        if not len(band) or f>sr/2:return False
        energy=float(band.mean())
        return bool(active and energy>=1e-11 and energy>=ref*10**(-6.5))
    return reaches(20000),reaches(15000),p

FULL_EXTS={'.mp3','.wav','.wave','.aif','.aiff','.flac','.aac','.m4a','.mp4'}
FULL_MAX_DURATION_SECONDS=24*60*60
FULL_MAX_TIME_BINS=172800
FULL_MAX_REPORT_TIME_BINS=250000
FULL_MIN_SAMPLE_RATE=8000
FULL_MAX_SAMPLE_RATE=192000
FULL_MAX_CHANNELS=8
FULL_DEFAULT_SPECTRUM_BUDGET_BYTES=32*1024*1024

class _FullSpectrumResourceLimit(RuntimeError):
    pass

class _FullSpectrumControlClosed(InterruptedError):
    pass

class _FullPauseControl:
    """Optional parent-owned stdin control; no audio or grade changes."""
    def __init__(self,stream,emit=None):
        self.running=threading.Event();self.running.set();self.closed=False
        self.emit=emit or (lambda paused: print('CONTROL '+json.dumps({'paused':paused}),flush=True))
        self.reader=threading.Thread(target=self._read,args=(stream,),daemon=True)
        self.reader.start()

    def _read(self,stream):
        try:
            while True:
                line=stream.readline(4097)
                if not line or len(line)>4096 or not line.endswith('\n'):break
                try: command=json.loads(line)
                except (ValueError,TypeError):continue
                if isinstance(command,dict):self._apply(command.get('action'))
        finally:
            self.closed=True;self.running.set()

    def finish(self):
        # Parent closes stdin after DONE; join before Python finalizes stdin.
        self.reader.join()

    def _apply(self,action):
        if action=='pause':self.running.clear()
        elif action=='resume':self.running.set()

    def wait(self):
        if self.closed:raise _FullSpectrumControlClosed('Analysis control connection closed')
        if self.running.is_set():return
        self.emit(True)
        self.running.wait()
        if self.closed:raise _FullSpectrumControlClosed('Analysis control connection closed')
        self.emit(False)

class _FullSpectrumAccumulator:
    def __init__(self,sr,channels,retain_spectrum,budget_bytes,metadata=None):
        if not isinstance(sr,int) or not FULL_MIN_SAMPLE_RATE<=sr<=FULL_MAX_SAMPLE_RATE:
            raise ValueError('Native sample rate is unsupported (8000 through 192000 Hz): '+str(sr))
        if channels<=0 or channels>FULL_MAX_CHANNELS:
            raise ValueError('Native channel count is unsupported (maximum 8): '+str(channels))
        if not isinstance(budget_bytes,int) or not 0<=budget_bytes<=256*1024*1024:
            raise ValueError('Spectrum evidence budget must be an integer from 0 through 256 MiB')
        self.sr=sr;self.channels=channels;self.retain=retain_spectrum;self.budget=budget_bytes
        self.metadata=metadata or {};self.duration=0.;self.high=0.;self.mid=0.
        self.series=[];self.spectra=[];self.starts=[];self.lengths=[];self.evidence_bytes=0
        self.evidence_reason=None;self.short_seconds=0.;self.silent_seconds=0.;self.quiet_seconds=0.

    def add(self,pcm):
        control=getattr(TLS,"full_pause",None)
        if control is not None:control.wait()
        if pcm.ndim!=2 or pcm.shape[1]!=self.channels:raise ValueError('Invalid decoded PCM shape')
        if not len(pcm):return
        seconds=len(pcm)/self.sr
        if len(self.series)>=FULL_MAX_TIME_BINS or self.duration+seconds>FULL_MAX_DURATION_SECONDS:
            raise _FullSpectrumResourceLimit('Full-duration analysis limit exceeded: maximum 24 hours/172800 bins; no partial grade is valid')
        if not np.isfinite(pcm).all():raise ValueError('Decoded PCM contains non-finite samples')
        if len(pcm)>=FULL_N:
            a,b,p=full_spectrum_metrics(pcm,self.sr)
            if not np.isfinite(p).all():raise ValueError('Decoded PCM produces non-finite spectrum power')
            if float(p.sum())<=3e-6:self.quiet_seconds+=seconds
            if self.retain and self.evidence_reason is None:
                # Reserve the final contiguous matrix copy and bounded row
                # bookkeeping before keeping a power row; grade calculation
                # does not depend on retaining evidence.
                projected_peak=2*(self.evidence_bytes+p.nbytes)+256*(len(self.spectra)+1)
                if projected_peak>self.budget:
                    self.spectra.clear();self.starts.clear();self.lengths.clear();self.evidence_bytes=0
                    self.evidence_reason='Spectrum evidence exceeds the configured '+str(self.budget)+' byte budget; the full-duration grade still uses every decoded bin'
                else:
                    self.spectra.append(p);self.starts.append(self.duration);self.lengths.append(seconds)
                    self.evidence_bytes+=p.nbytes
        else:
            a=b=False;self.short_seconds+=seconds
        if not np.any(pcm):self.silent_seconds+=seconds
        self.series.append(dict(start_seconds=round(self.duration,3),seconds=seconds,reaches_20khz=a,reaches_15khz=b))
        self.duration+=seconds;self.high+=seconds*a;self.mid+=seconds*b

    def finish(self):
        if self.duration<=0:raise ValueError('No decoded audio')
        context=[]
        if self.duration<2:context.append('Very short audio: fewer than four full 0.5-second bins; treat the spectral label as limited evidence')
        if self.sr/2<20000:context.append('Native frequency ceiling is below 20 kHz; the target band is partially available or unavailable. Interpret measured coverage with this limit and the unchanged target-frequency rule')
        if self.short_seconds:context.append('Tail shorter than 2048 samples remains in the duration denominator but has no measurable spectrum')
        if self.silent_seconds==self.duration:context.append('Silent decoded audio; the label describes absent qualifying spectral signal')
        elif self.quiet_seconds:context.append('Quiet/non-active bins remain in the full-duration denominator')
        if self.retain and not self.spectra and self.evidence_reason is None:
            self.evidence_reason='No bin contained at least 2048 decoded samples for spectrum evidence'
        status='not_requested' if not self.retain else 'unavailable' if self.evidence_reason else 'available'
        result=dict(quality_rule_version=FULL_RULE_VERSION,coverage_threshold=FULL_COVERAGE_THRESHOLD,
            duration_seconds=self.duration,coverage_20khz=self.high/self.duration,
            coverage_15khz=self.mid/self.duration,seconds_20khz=self.high,seconds_15khz=self.mid,
            sample_rate=self.sr,time_bins=self.series,channels=self.channels,
            native_frequency_ceiling_hz=self.sr/2,analysis_context=context,
            unanalyzable_tail_seconds=self.short_seconds,silent_seconds=self.silent_seconds,
            non_active_seconds=self.quiet_seconds,spectrum_evidence_status=status,
            spectrum_evidence_budget_bytes=self.budget,spectrum_evidence_bytes=self.evidence_bytes,
            spectrum_evidence_estimated_peak_bytes=2*self.evidence_bytes+256*len(self.spectra),
            spectrum_bin_start_seconds=self.starts,spectrum_bin_duration_seconds=self.lengths,
            analysis_limits={'maximum_duration_seconds':FULL_MAX_DURATION_SECONDS,
                'maximum_time_bins':FULL_MAX_TIME_BINS,'maximum_native_sample_rate':FULL_MAX_SAMPLE_RATE,
                'minimum_native_sample_rate':FULL_MIN_SAMPLE_RATE,
                'maximum_channels':FULL_MAX_CHANNELS})
        result.update(self.metadata)
        if self.evidence_reason:result['spectrum_evidence_unavailable_reason']=self.evidence_reason
        power=np.array(self.spectra) if self.spectra else np.empty((0,FULL_N//2+1),dtype=np.float64)
        return result,power

def _mpeg_audio_metadata(path):
    metadata={'codec':'mpeg_audio','container':'mpeg_audio','decoder':'libmpg123','decoded_sample_format':'flt'}
    try:
        offset,_invalid=header_info(path)
        with path.open('rb') as stream:stream.seek(offset);raw=stream.read(65536)
        _at,header=frame_start(raw);layer=4-header[4]
        metadata.update(codec='mp'+str(layer),container='mp'+str(layer),mpeg_layer=layer,
            codec_profile=('MPEG-1' if header[3]==3 else 'MPEG-2' if header[3]==2 else 'MPEG-2.5')+' Layer '+str(layer),
            first_frame_bitrate=header[5]*1000,codec_metadata_source='Validated MPEG frame header')
    except (OSError,RuntimeError,ValueError):
        metadata['codec_metadata_source']='MPEG decoder; exact layer not established from initial headers'
    return metadata

def _analyze_mpg123_full(path,retain_spectrum,budget_bytes):
    _ensure_mpg123();h=mnew(None,None)
    if not h:raise RuntimeError('libmpg123 could not allocate a decoder')
    try:
        with path.open('rb') as f:
            @READ_CB
            def reader(handle,buf,n):
                try:data=f.read(n);C.memmove(buf,data,len(data));return len(data)
                except Exception:return -1
            @SEEK_CB
            def seeker(handle,offset,whence):
                try:return f.seek(offset,whence)
                except Exception:return -1
            mnone(h)
            for rate in (8000,11025,12000,16000,22050,24000,32000,44100,48000):mfmt(h,rate,3,0x200)
            if mreplace(h,reader,seeker,None)!=0 or mhandle(h,C.c_void_p(1))!=0:
                raise RuntimeError('libmpg123 could not open audio')
            sr=C.c_long();ch=C.c_int();enc=C.c_int()
            if mget(h,C.byref(sr),C.byref(ch),C.byref(enc))!=0 or enc.value!=0x200:
                raise RuntimeError('libmpg123 could not read float PCM format')
            native_format=(sr.value,ch.value,enc.value)
            state=_FullSpectrumAccumulator(sr.value,ch.value,retain_spectrum,budget_bytes,_mpeg_audio_metadata(path))
            samples_per_bin=int(sr.value*.5);requested=samples_per_bin*ch.value*4
            buf=C.create_string_buffer(requested)
            while True:
                used=0;ended=False;format_events=0
                while used<requested:
                    done=C.c_size_t();rc=mread(h,C.byref(buf,used),requested-used,C.byref(done));used+=done.value
                    if rc==-12:ended=True;break
                    if rc not in (0,-11):raise RuntimeError('libmpg123 decode error: '+str(rc))
                    if rc==-11:
                        rate=C.c_long();channels=C.c_int();encoding=C.c_int()
                        if mget(h,C.byref(rate),C.byref(channels),C.byref(encoding))!=0:
                            raise RuntimeError('libmpg123 could not inspect a changed stream format')
                        if (rate.value,channels.value,encoding.value)!=native_format:
                            raise RuntimeError('Midstream native sample rate/channel/encoding change is unsupported; no partial grade is valid')
                        format_events+=1
                        if format_events>32:raise RuntimeError('libmpg123 repeated format events without bounded progress')
                    if done.value==0 and rc==0:raise RuntimeError('Decoder returned no audio and no completion signal')
                if not used:break
                if used%(ch.value*4):raise RuntimeError('libmpg123 returned incomplete PCM frames')
                pcm=np.frombuffer(buf,dtype='<f4',count=used//4).reshape(-1,ch.value)
                state.add(pcm)
                if ended:break
            return state.finish()
    finally:mdel(h)

def _pyav_frame_pcm(frame):
    channels=len(frame.layout.channels);data=frame.to_ndarray()
    if frame.format.is_planar:data=data.T
    else:data=data.reshape(-1,channels)
    if len(data)!=frame.samples:raise RuntimeError('PyAV returned an inconsistent PCM sample count')
    if data.dtype==np.uint8:return (data.astype(np.float32)-128)/128
    if np.issubdtype(data.dtype,np.signedinteger):
        return data.astype(np.float32)/float(2**(np.iinfo(data.dtype).bits-1))
    if np.issubdtype(data.dtype,np.floating):return data
    raise RuntimeError('Unsupported decoded PCM sample format: '+frame.format.name)

def _analyze_pyav_full(path,retain_spectrum,budget_bytes):
    try:import av
    except ImportError as exc:
        raise RuntimeError('WAV/AIFF/FLAC/AAC/ALAC analysis requires PyAV. Install a matching binary wheel with pip install av==19.0.0; audio stays local') from exc
    with av.open(str(path),mode='r',options={'protocol_whitelist':'file','format_whitelist':'wav,aiff,flac,aac,mov'}) as container:
        audio=list(container.streams.audio)
        if len(audio)!=1:raise ValueError('Exactly one audio stream is required; multiple/no audio streams are unsupported')
        for video in container.streams.video:
            if not (int(video.disposition)&0x0400):
                raise ValueError('Video-bearing files are unsupported; audio-only MP4 with attached cover art is allowed')
        stream=audio[0];ctx=stream.codec_context;codec=ctx.name
        if codec not in ('aac','alac','flac') and not codec.startswith('pcm_'):
            raise ValueError('Unsupported actual audio codec: '+str(codec)+'; DRM/encrypted audio is not supported')
        if codec.startswith('pcm_') and container.format.name not in ('wav','aiff'):
            raise ValueError('PCM is supported in WAV/AIFF containers only')
        if codec=='flac' and container.format.name!='flac':raise ValueError('FLAC container required for FLAC audio')
        if codec in ('aac','alac') and not any(x in container.format.name.split(',') for x in ('aac','mov','mp4','m4a')):
            raise ValueError('AAC/ALAC requires ADTS AAC or MP4/M4A container')
        if any(k in container.metadata for k in ('encryption','encryption_scheme')):
            raise ValueError('Encrypted/DRM audio is unsupported')
        state=None;native_format=None;buffer=None;filled=0;empty_frames=0
        for frame in container.decode(audio=0):
            if frame.samples<=0:
                empty_frames+=1
                if empty_frames>64:raise RuntimeError('Decoder produced too many empty frames')
                continue
            empty_frames=0;sr=int(frame.sample_rate);channels=len(frame.layout.channels)
            current=(sr,channels,frame.layout.name,frame.format.name)
            if state is None:
                native_format=current
                metadata={'codec':codec,'codec_profile':ctx.profile,'container':container.format.name,
                    'decoder':'PyAV '+av.__version__,'decoded_sample_format':frame.format.name,
                    'channel_layout':frame.layout.name,'encoded_bitrate':ctx.bit_rate or None,
                    'encoded_bitrate_source':'audio codec context; informational only' if ctx.bit_rate else 'unknown',
                    'attached_picture_streams':len(container.streams.video)}
                if any(name in container.format.name.split(',') for name in ('mov','mp4','m4a')) and stream.duration is not None and stream.time_base is not None:
                    metadata['_container_declared_duration_seconds']=float(stream.duration*stream.time_base)
                bit_depth=int(getattr(ctx,'bits_per_raw_sample',0) or 0)
                if bit_depth>0 and (codec in ('alac','flac') or codec.startswith('pcm_')):metadata['bit_depth']=bit_depth
                state=_FullSpectrumAccumulator(sr,channels,retain_spectrum,budget_bytes,metadata)
                samples_per_bin=int(sr*.5)
            elif current!=native_format:
                raise RuntimeError('Midstream native sample rate/channel/layout/sample-format change is unsupported; no partial grade is valid')
            if frame.samples>sr*2:raise RuntimeError('Decoded audio frame exceeds bounded two-second frame size')
            pcm=_pyav_frame_pcm(frame)
            if buffer is None:buffer=np.empty((samples_per_bin,channels),dtype=pcm.dtype)
            position=0
            while position<len(pcm):
                take=min(samples_per_bin-filled,len(pcm)-position)
                buffer[filled:filled+take]=pcm[position:position+take];filled+=take;position+=take
                if filled==samples_per_bin:state.add(buffer);filled=0
        if state is None:raise ValueError('No decoded audio')
        if filled:state.add(buffer[:filled])
        return state.finish()


class _AudioIntegrityError(RuntimeError):
    def __init__(self, details):
        self.details=details
        expected=details['declared_duration_seconds'];actual=details['decoded_duration_seconds']
        super().__init__('Duration mismatch: the audio header declares '+format(expected,'.3f')+
            ' seconds but '+format(actual,'.3f')+' seconds decoded. The file may be incomplete or have an incorrect header; no spectral grade is valid. Review or obtain a complete copy')

def _trusted_audio_duration(path,result):
    # Read only structural audio lengths, never ID3 TLEN or bitrate/file-size guesses.
    with path.open('rb') as source:
        magic=source.read(12)
        if magic[:4] in (b'RIFF',b'RF64') and magic[8:12]==b'WAVE':
            rate=alignment=0;extended_size=None
            for _ in range(4096):
                header=source.read(8)
                if len(header)!=8:break
                name=header[:4];size=int.from_bytes(header[4:],'little');position=source.tell()
                if name==b'ds64' and size>=28:
                    data=source.read(28);extended_size=int.from_bytes(data[8:16],'little') if len(data)==28 else None
                elif name==b'fmt ' and size>=16:
                    data=source.read(16)
                    if len(data)==16:rate=int.from_bytes(data[4:8],'little');alignment=int.from_bytes(data[12:14],'little')
                elif name==b'data' and rate>0 and alignment>0:
                    length=extended_size if size==0xffffffff else size
                    if length is not None:return length/alignment/rate,'WAV declared data sample count'
                source.seek(position+size+(size&1))
        elif magic[:4]==b'FORM' and magic[8:12] in (b'AIFF',b'AIFC'):
            for _ in range(4096):
                header=source.read(8)
                if len(header)!=8:break
                size=int.from_bytes(header[4:],'big');position=source.tell()
                if header[:4]==b'COMM' and size>=18:
                    data=source.read(18)
                    if len(data)==18:
                        frames=int.from_bytes(data[2:6],'big');exponent=int.from_bytes(data[8:10],'big')
                        mantissa=int.from_bytes(data[10:18],'big')
                        rate=math.ldexp(mantissa, (exponent&0x7fff)-16383-63) if exponent&0x7fff!=0x7fff else 0
                        if not exponent&0x8000 and rate>0:return frames/rate,'AIFF COMM declared sample count'
                source.seek(position+size+(size&1))
        elif magic[:4]==b'fLaC':
            source.seek(4)
            for _ in range(4096):
                header=source.read(4)
                if len(header)!=4:break
                size=int.from_bytes(header[1:],'big')
                if header[0]&127==0 and size==34:
                    data=source.read(34)
                    if len(data)==34:
                        packed=int.from_bytes(data[10:18],'big');rate=packed>>44;samples=packed&((1<<36)-1)
                        if rate>0 and samples>0:return samples/rate,'FLAC STREAMINFO total sample count'
                else:source.seek(size,1)
                if header[0]&128:break
    if result.get('decoder')=='libmpg123' and result.get('mpeg_layer')==3:
        offset,_=header_info(path)
        with path.open('rb') as source:source.seek(offset);raw=source.read(65536)
        at,header=frame_start(raw);mono=(raw[at+3]>>6)==3
        xing=at+(21 if mono else 36) if header[3]==3 else at+(13 if mono else 21)
        if raw[xing:xing+4] in (b'Xing',b'Info') and len(raw)>=xing+12:
            flags=int.from_bytes(raw[xing+4:xing+8],'big')
            if flags&1:
                frames=int.from_bytes(raw[xing+8:xing+12],'big')
                if frames>0:return frames*header[2]/header[1],'MP3 Xing/Info declared frame count'
        vbri=at+36
        if raw[vbri:vbri+4]==b'VBRI' and len(raw)>=vbri+18:
            frames=int.from_bytes(raw[vbri+14:vbri+18],'big')
            if frames>0:return frames*header[2]/header[1],'MP3 VBRI declared frame count'
    if result.get('_container_declared_duration_seconds'):
        return result['_container_declared_duration_seconds'],'MP4 audio stream timeline'
    return None,None

def _verify_audio_duration(path,result):
    try:expected,origin=_trusted_audio_duration(path,result)
    except (OSError,ValueError,RuntimeError,OverflowError,struct.error):expected=origin=None
    result.pop('_container_declared_duration_seconds',None)
    actual=result['duration_seconds'];result['decoded_duration_seconds']=actual
    if expected is None or not math.isfinite(expected) or expected<=0:
        result['integrity_check']='duration_not_verifiable'
        result['integrity_note']='No trustworthy complete-duration declaration is available. A cleanly ending shorter edit cannot be distinguished from missing original content'
        return
    tolerance=max(.25,expected*.02)
    details={'declared_duration_seconds':expected,'decoded_duration_seconds':actual,
        'declared_duration_source':origin,'duration_tolerance_seconds':tolerance,
        'duration_difference_seconds':actual-expected,'integrity_check':'duration_mismatch'}
    if abs(actual-expected)>tolerance:raise _AudioIntegrityError(details)
    result.update(details);result['integrity_check']='duration_matches_declaration'
    result['integrity_note']='Decoded duration matches the available header within tolerance; this does not establish the intended original song length'

def analyze_full_duration(path,retain_spectrum=False,spectrum_budget_bytes=FULL_DEFAULT_SPECTRUM_BUDGET_BYTES):
    path=Path(path)
    if path.suffix.lower() not in FULL_EXTS:raise ValueError('Unsupported audio extension: '+path.suffix)
    result,power=(_analyze_mpg123_full(path,retain_spectrum,spectrum_budget_bytes) if path.suffix.lower()=='.mp3' else _analyze_pyav_full(path,retain_spectrum,spectrum_budget_bytes))
    _verify_audio_duration(path,result)
    return result,power

def full_spectrum_self_test():
    sr=48000;random=np.random.default_rng(41)
    def filtered(edge):
        x=random.normal(0,.1,(sr//2,2));f=np.fft.rfft(x,axis=0);f[np.fft.rfftfreq(len(x),1/sr)>edge]=0
        return np.fft.irfft(f,n=len(x),axis=0).astype(np.float32)
    assert full_spectrum_metrics(filtered(14000),sr)[:2]==(False,False)
    assert full_spectrum_metrics(filtered(16000),sr)[:2]==(False,True)
    assert full_spectrum_metrics(filtered(18500),sr)[:2]==(False,True)
    assert full_spectrum_metrics(filtered(20500),sr)[:2]==(True,True)
    assert full_spectrum_metrics(filtered(19500),sr)[:2]==(False,True)
    tone=np.sin(2*np.pi*22000*np.arange(sr//2)/sr).astype(np.float32)
    assert full_spectrum_metrics(np.column_stack((tone,tone)),sr)[:2]==(True,True)
    assert full_spectrum_metrics(np.zeros((sr//2,2)),sr)[:2]==(False,False)
    results=[full_spectrum_metrics(filtered(16000 if i<6 else 20500),sr)[0] for i in range(10)]
    assert sum(results)/len(results)==.4
    assert spectrum_grade(.399999,.5)=='MQ'
    assert spectrum_grade(.40,.5)=='HQ'
    assert spectrum_grade(.400001,.5)=='HQ'
    assert spectrum_grade(0,.40)=='MQ'
    assert spectrum_grade(0,.399999)=='LQ'
    control=_FullPauseControl.__new__(_FullPauseControl)
    control.running=threading.Event();control.running.set();control.closed=False
    observed=threading.Event();finished=threading.Event();states=[]
    control.emit=lambda paused:(states.append(paused),observed.set())
    control._apply('pause')
    worker=threading.Thread(target=lambda:(control.wait(),finished.set()),daemon=True)
    worker.start();assert observed.wait(2) and not finished.is_set()
    control._apply('resume');assert finished.wait(2);worker.join(2)
    assert states==[True,False]
    control.closed=True
    try:control.wait();raise AssertionError('Closed control must fail')
    except _FullSpectrumControlClosed:pass
    print('SELF_TEST passed: known 14, 16, 18.5, 20.5 kHz cutoffs, silence, and 40% mixed coverage and strict at-or-above frequency regions',flush=True)

FULL_SPECTRUM_METHOD = (
    'Full decoded duration, including quiet sections; 0.5-second bins; 2048-point Hann FFT, '
    '1024-sample hop; mean power over channels. A bin qualifies at or above a frequency when '
    'the mean power of available FFT bins from that frequency to Nyquist is >= -110 dBFS '
    'and >= -65 dB relative to the 1-10 kHz band, with summed spectral power >3e-6 to exclude silence. '
    'HQ: >=40% at or above 20 kHz; MQ: otherwise >=40% at or above 15 kHz; '
    'LQ: otherwise. Encoded bitrate is informational only. '
    'Spectrum grades do not establish original source bitrate.'
)

def spectrum_grade(coverage_20khz,coverage_15khz):
    return 'HQ' if coverage_20khz>=FULL_COVERAGE_THRESHOLD else 'MQ' if coverage_15khz>=FULL_COVERAGE_THRESHOLD else 'LQ'

def full_spectrum_cli(argv):
    import argparse
    from datetime import datetime
    parser=argparse.ArgumentParser(description='Full-duration spectrum quality grading. Read-only audio analysis.')
    parser.add_argument('inputs',nargs='*',help='MP3/WAV/AIFF/FLAC/AAC/M4A and audio-only MP4 files or folders to scan recursively')
    parser.add_argument('--full-spectrum',action='store_true')
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--output',type=Path,help='Optional JSON report; parent must already exist')
    parser.add_argument('--spectra-dir',type=Path,help='Optional existing folder for per-track spectrum arrays')
    parser.add_argument('--skip-hq',action='store_true',help='Skip (HQ) files only when explicitly requested')
    parser.add_argument('--keep-input-order',action='store_true',help='Retain explicit file order; folder contents remain path-sorted')
    parser.add_argument('--interactive-control',action='store_true',help='Parent-owned stdin JSON pause/resume control at decoded-bin boundaries')
    parser.add_argument('--spectrum-budget-mib',type=float,default=32,help='Bound retained spectrum evidence memory, 0 through 256 MiB; full grading continues without evidence if exceeded')
    args=parser.parse_args(argv)
    if not math.isfinite(args.spectrum_budget_mib) or not 0<=args.spectrum_budget_mib<=256:parser.error('Spectrum budget must be between 0 and 256 MiB')
    if args.self_test:full_spectrum_self_test();return
    if not args.inputs:parser.error('Supply files or folders; no implicit full-library scan')
    if args.output and not args.output.parent.is_dir():parser.error('Output parent folder does not exist')
    if args.spectra_dir and not args.spectra_dir.is_dir():parser.error('Spectrum output folder does not exist')
    control=None
    if args.interactive_control:
        if sys.stdin is None:parser.error('Interactive control needs a redirected stdin pipe')
        control=_FullPauseControl(sys.stdin)
    TLS.full_pause=control
    paths=[];seen=set()
    for text in args.inputs:
        p=Path(text)
        if not p.exists():parser.error('Input does not exist: '+text)
        if p.is_dir():found=sorted((q.resolve() for q in p.rglob('*') if q.is_file() and q.suffix.lower() in FULL_EXTS and not q.name.startswith('._')),key=lambda q:str(q).casefold())
        elif p.suffix.lower() in FULL_EXTS:found=[p.resolve()]
        else:parser.error('Unsupported full-duration audio extension: '+text)
        for q in found:
            if q not in seen:seen.add(q);paths.append(q)
    records=[];start=time.monotonic();failures=0;retained_time_bins=0;batch_limit_exceeded=False
    batch_limit_reason='Batch report time-bin budget exceeded ('+str(FULL_MAX_REPORT_TIME_BINS)+'); scan smaller batches. The offending and remaining inputs are ungraded'
    for index,p in enumerate(paths if args.keep_input_order else sorted(paths,key=lambda q:str(q).casefold())):
        if control is not None:control.wait()
        stat=p.stat();base={'path':str(p),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns}
        if batch_limit_exceeded:
            result=dict(base,status='analysis_limit',quality=None,reason=batch_limit_reason);failures+=1
        elif args.skip_hq and '(hq)' in p.name.lower():
            result=dict(base,status='skipped_hq',quality=None)
        else:
            try:
                result,_power=analyze_full_duration(p,bool(args.spectra_dir),int(args.spectrum_budget_mib*1024*1024))
                if (p.stat().st_size,p.stat().st_mtime_ns)!=(stat.st_size,stat.st_mtime_ns):raise RuntimeError('File changed during scan')
                bins=len(result['time_bins'])
                if retained_time_bins+bins>FULL_MAX_REPORT_TIME_BINS:
                    batch_limit_exceeded=True
                    raise _FullSpectrumResourceLimit(batch_limit_reason)
                retained_time_bins+=bins
                grade=spectrum_grade(result['coverage_20khz'],result['coverage_15khz'])
                result=dict(base,**result,status='analyzed',quality=grade)
                if args.spectra_dir and result['spectrum_evidence_status']=='available':
                    name=hashlib.sha256(str(p).encode()).hexdigest()[:16]+'.npz'
                    np.savez_compressed(args.spectra_dir/name,power=_power,sample_rate=result['sample_rate'],bin_start_seconds=np.asarray(result['spectrum_bin_start_seconds']),bin_duration_seconds=np.asarray(result['spectrum_bin_duration_seconds']))
                    result['spectrum_file']=str(args.spectra_dir/name)
            except _FullSpectrumControlClosed:raise
            except Exception as exc:
                result=dict(base,status='integrity_error' if isinstance(exc,_AudioIntegrityError) else 'analysis_limit' if isinstance(exc,_FullSpectrumResourceLimit) else 'decode_error',quality=None,reason=str(exc));failures+=1
                if isinstance(exc,_AudioIntegrityError):result.update(exc.details)
        records.append(result)
        print('PROGRESS '+json.dumps({k:result[k] for k in ('path','status','quality','coverage_20khz','coverage_15khz','reason') if k in result}),flush=True)
    report={'as_of':datetime.now().astimezone().isoformat(),'method':FULL_SPECTRUM_METHOD,'records':records,
        'counts':dict(collections.Counter(r['quality'] or r['status'] for r in records)),
        'elapsed_seconds':round(time.monotonic()-start,2),'retained_time_bins':retained_time_bins,
        'maximum_report_time_bins':FULL_MAX_REPORT_TIME_BINS}
    if args.output:
        temp=args.output.with_suffix(args.output.suffix+'.tmp')
        if temp.exists():raise FileExistsError('Temporary report already exists: '+str(temp))
        temp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(args.output)
    print('DONE '+json.dumps({'total':len(records),'counts':report['counts'],'output':str(args.output) if args.output else None}),flush=True)
    if control is not None:control.finish()
    if failures:raise SystemExit(1)

if __name__=='__main__':
    if '--full-spectrum' in sys.argv or '--self-test' in sys.argv:
        full_spectrum_cli(sys.argv[1:])
    elif '--test' in sys.argv:
        if not os.environ.get('SONG_AUDIT_TEST_MP3'):raise RuntimeError('Legacy --test requires SONG_AUDIT_TEST_MP3')
        p=Path(os.environ['SONG_AUDIT_TEST_MP3'])
        meta,pcm=mpg_decode(p);print(json.dumps(measure(meta['sr'],pcm)),flush=True)
        print(json.dumps(safe_analyze(p)),flush=True);shutdown()
    else:main()
