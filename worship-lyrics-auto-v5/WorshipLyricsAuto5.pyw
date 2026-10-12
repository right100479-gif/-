# -*- coding: utf-8 -*-
import os, re, csv, json, math, queue, hashlib, threading, traceback, subprocess, sys
from pathlib import Path
from difflib import SequenceMatcher
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD

APP_NAME="찬양 자막 자동생성"
APP_VERSION="5.0"
LOCALAPPDATA=Path(os.environ.get("LOCALAPPDATA", str(Path.home()/"AppData"/"Local")))
APP_DIR=LOCALAPPDATA/"WorshipLyricsAuto5"
DATA_DIR=APP_DIR/"data"
CACHE_DIR=APP_DIR/"cache"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE=DATA_DIR/"settings.json"
HF_DIR=CACHE_DIR/"huggingface"
TORCH_DIR=CACHE_DIR/"torch"
HF_DIR.mkdir(parents=True, exist_ok=True)
TORCH_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME",str(HF_DIR))
os.environ.setdefault("TORCH_HOME",str(TORCH_DIR))
os.environ.setdefault("TOKENIZERS_PARALLELISM","false")
_CONSOLE_LOG=None

def ensure_console_streams():
    global _CONSOLE_LOG
    if sys.stdout is not None and sys.stderr is not None: return
    if _CONSOLE_LOG is None:
        _CONSOLE_LOG=open(DATA_DIR/"engine_console.log","a",encoding="utf-8",buffering=1,errors="replace")
    if sys.stdout is None: sys.stdout=_CONSOLE_LOG
    if sys.stderr is None: sys.stderr=_CONSOLE_LOG

def read_text_safely(path):
    data=Path(path).read_bytes()
    for enc in ("utf-8-sig","utf-16","cp949","euc-kr","utf-8"):
        try: return data.decode(enc)
        except Exception: pass
    return data.decode("utf-8",errors="replace")

def parse_sections(text):
    sections=[]; current=None
    for raw in text.splitlines():
        s=raw.strip()
        if not s: continue
        m=re.match(r"^\[([^\]]+)\]$",s)
        if m:
            current={"name":m.group(1).strip(),"lines":[]}
            sections.append(current); continue
        if s.startswith("#"): continue
        if current is None:
            current={"name":"Lyrics","lines":[]}; sections.append(current)
        current["lines"].append(s)
    sections=[s for s in sections if s["lines"]]
    for i,s in enumerate(sections):
        s["index"]=i; s["display_name"]="%02d_%s"%(i+1,s["name"])
    return sections

def norm(s):
    return "".join(ch.lower() for ch in str(s) if ch.isalnum() or ("가"<=ch<="힣"))

def file_key(path):
    p=Path(path); st=p.stat()
    return hashlib.sha1(f"{p.resolve()}|{st.st_size}|{int(st.st_mtime)}".encode("utf-8","ignore")).hexdigest()[:16]

def run_hidden(args):
    flags=getattr(subprocess,"CREATE_NO_WINDOW",0) if os.name=="nt" else 0
    cp=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",creationflags=flags)
    if cp.returncode!=0: raise RuntimeError("외부 처리 명령이 실패했습니다.\n\n"+(cp.stdout or "")[-5000:])
    return cp.stdout or ""

def extract_wav(source,wav_path):
    wav_path.parent.mkdir(parents=True,exist_ok=True)
    run_hidden(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(source),"-vn","-ac","2","-ar","44100","-c:a","pcm_s16le",str(wav_path)])

def separate_vocals(wav_path,sep_root,device):
    sep_root.mkdir(parents=True,exist_ok=True)
    run_hidden([sys.executable,"-m","demucs.separate","--two-stems=vocals","-n","htdemucs","-o",str(sep_root),"-d",device,str(wav_path)])
    expected=sep_root/"htdemucs"/wav_path.stem/"vocals.wav"
    if expected.exists(): return expected
    hits=list(sep_root.rglob("vocals.wav"))
    if hits: return max(hits,key=lambda p:p.stat().st_mtime)
    raise RuntimeError("Demucs 보컬 파일을 찾지 못했습니다.")

def _load_audio_16k_mono(path):
    import numpy as np
    flags=getattr(subprocess,"CREATE_NO_WINDOW",0) if os.name=="nt" else 0
    cmd=[
        "ffmpeg","-nostdin","-hide_banner","-loglevel","error",
        "-i",str(path),"-f","s16le","-ac","1","-acodec","pcm_s16le","-ar","16000","-"
    ]
    cp=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags)
    if cp.returncode!=0:
        raise RuntimeError("16kHz 보컬 변환 실패:\n"+cp.stderr.decode("utf-8","replace")[-3000:])
    return np.frombuffer(cp.stdout,dtype=np.int16).astype(np.float32)/32768.0

def _mms_emissions(audio,model,device,batch_size=2):
    import torch
    import torch.nn.functional as F
    import numpy as np

    sr=16000
    ratio=int(model.config.inputs_to_logits_ratio)
    window=30*sr
    context=2*sr
    waveform=torch.from_numpy(audio)

    if waveform.numel()<window:
        inputs=waveform.unsqueeze(0)
        context_frames=0
        window_frames=None
        extension=0
    else:
        extension=math.ceil(waveform.numel()/window)*window-waveform.numel()
        padded=F.pad(waveform,(context,context+extension))
        inputs=padded.unfold(0,window+2*context,window)
        context_frames=context//ratio
        window_frames=window//ratio

    pieces=[]
    with torch.inference_mode():
        for i in range(0,inputs.size(0),max(1,batch_size)):
            batch=inputs[i:i+max(1,batch_size)].to(device=device,dtype=model.dtype)
            logits=model(batch).logits
            if window_frames is not None:
                logits=logits[:,context_frames:context_frames+window_frames]
            pieces.append(logits.float().cpu())

    emissions=torch.cat(pieces,dim=0)
    if emissions.dim()==3:
        emissions=emissions.flatten(0,1)
    if extension>0:
        trim=extension//ratio
        if trim>0:
            emissions=emissions[:-trim]

    emissions=torch.log_softmax(emissions,dim=-1).numpy().astype(np.float32,copy=False)
    stride=ratio/sr
    return emissions,stride

def _ctc_viterbi(log_probs,targets,blank_id):
    import numpy as np

    targets=np.asarray(targets,dtype=np.int32)
    T,C=log_probs.shape
    L=len(targets)
    if L==0:
        raise RuntimeError("CTC 대상 토큰이 비어 있습니다.")

    repeats=int(np.sum(targets[1:]==targets[:-1])) if L>1 else 0
    if T<L+repeats:
        raise RuntimeError("오디오 프레임이 가사 토큰 수보다 짧아 강제정렬할 수 없습니다.")

    ext=np.full(2*L+1,blank_id,dtype=np.int32)
    ext[1::2]=targets
    S=len(ext)
    neg=np.float32(-1e30)

    prev=np.full(S,neg,dtype=np.float32)
    prev[0]=log_probs[0,blank_id]
    if S>1:
        prev[1]=log_probs[0,targets[0]]

    back=np.zeros((T,S),dtype=np.uint8)
    skip_allowed=np.zeros(S,dtype=bool)
    if S>2:
        idx=np.arange(2,S)
        skip_allowed[2:]=(ext[2:]!=blank_id)&(ext[2:]!=ext[:-2])

    for t in range(1,T):
        best=prev.copy()
        choice=np.zeros(S,dtype=np.uint8)

        step=np.full(S,neg,dtype=np.float32)
        step[1:]=prev[:-1]
        mask=step>best
        best[mask]=step[mask]
        choice[mask]=1

        skip=np.full(S,neg,dtype=np.float32)
        skip[2:]=prev[:-2]
        skip[~skip_allowed]=neg
        mask=skip>best
        best[mask]=skip[mask]
        choice[mask]=2

        prev=best+log_probs[t,ext]
        back[t]=choice

    if S==1:
        state=0
    else:
        state=S-1 if prev[S-1]>=prev[S-2] else S-2

    states=np.empty(T,dtype=np.int32)
    for t in range(T-1,-1,-1):
        states[t]=state
        if t>0:
            state-=int(back[t,state])
            if state<0:
                state=0
    return states

def align_lines_mms(vocals_path,sections,device,log_cb=None):
    import numpy as np
    import torch
    from transformers import AutoModelForCTC, AutoTokenizer
    from uroman import Uroman

    lyric_rows=[]
    for section in sections:
        for line in section["lines"]:
            lyric_rows.append({"section":section["display_name"],"text":line})
    if not lyric_rows:
        raise RuntimeError("정렬할 가사가 없습니다.")

    model_name="MahmoudAshraf/mms-300m-1130-forced-aligner"
    if log_cb:
        log_cb("MMS-300M 다국어 정렬 모델을 준비하는 중... 첫 실행은 모델 다운로드로 오래 걸릴 수 있습니다.")

    dtype=torch.float16 if device=="cuda" else torch.float32
    try:
        model=AutoModelForCTC.from_pretrained(model_name,dtype=dtype).to(device).eval()
    except TypeError:
        model=AutoModelForCTC.from_pretrained(model_name,torch_dtype=dtype).to(device).eval()
    tokenizer=AutoTokenizer.from_pretrained(model_name,word_delimiter_token=None)

    if log_cb:
        log_cb("분리된 보컬을 16kHz로 준비하는 중...")
    audio=_load_audio_16k_mono(vocals_path)

    if log_cb:
        log_cb("30초 창 + 2초 문맥으로 곡 전체 음소 확률맵을 만드는 중...")
    emissions,stride=_mms_emissions(audio,model,device,2 if device=="cpu" else 4)

    dictionary={str(k).lower():int(v) for k,v in tokenizer.get_vocab().items()}
    blank_id=dictionary.get("<blank>",tokenizer.pad_token_id)
    star_id=emissions.shape[1]
    emissions=np.concatenate(
        [emissions,np.zeros((emissions.shape[0],1),dtype=np.float32)],
        axis=1
    )

    uroman=Uroman()
    targets=[]
    line_ranges=[]
    valid_rows=[]

    for row in lyric_rows:
        text=row["text"].strip().lower()
        try:
            roman=uroman.romanize_string(text,lcode="kor")
        except Exception:
            roman=uroman.romanize_string(text)
        roman=re.sub(r"[^a-z']+","",roman.lower())

        ids=[dictionary[ch] for ch in roman if ch in dictionary]
        if not ids:
            continue

        targets.append(star_id)
        line_start=len(targets)
        targets.extend(ids)
        line_end=len(targets)-1
        line_ranges.append((line_start,line_end))
        valid_rows.append(row)

    targets.append(star_id)

    if not valid_rows:
        raise RuntimeError("가사를 로마자화한 뒤 정렬할 토큰이 남지 않았습니다.")

    if log_cb:
        log_cb("정답 가사를 받아쓰지 않고 CTC Viterbi로 직접 강제정렬하는 중...")
    states=_ctc_viterbi(emissions,targets,blank_id)

    rows=[]
    for row,(a,b) in zip(valid_rows,line_ranges):
        frame_ids=[]
        frame_scores=[]
        for target_pos in range(a,b+1):
            state_id=2*target_pos+1
            frames=np.flatnonzero(states==state_id)
            if frames.size:
                frame_ids.append(frames)
                tok=targets[target_pos]
                frame_scores.append(emissions[frames,tok])
        if not frame_ids:
            raise RuntimeError("일부 가사 줄의 MMS 정렬 프레임을 찾지 못했습니다: "+row["text"])

        frames=np.concatenate(frame_ids)
        st=max(0.0,float(frames.min())*stride-.03)
        en=max(st+.12,float(frames.max()+1)*stride+.05)
        score=float(np.concatenate(frame_scores).mean()) if frame_scores else 0.0

        rows.append({
            "section":row["section"],
            "text":row["text"],
            "start":st,
            "end":en,
            "mms_score":score
        })

    for i in range(len(rows)-1):
        if rows[i]["end"]>=rows[i+1]["start"]:
            rows[i]["end"]=max(rows[i]["start"]+.10,rows[i+1]["start"]-.03)

    try:
        del model
        if device=="cuda":
            torch.cuda.empty_cache()
    except Exception:
        pass

    return rows

def detect_vocal_span(audio,sr=16000):
    import numpy as np
    if audio is None or len(audio)<sr: return 0.0,max(1.0,len(audio)/sr if audio is not None else 1.0)
    frame=int(sr*.20); hop=int(sr*.05); vals=[]
    for pos in range(0,max(1,len(audio)-frame),hop):
        c=audio[pos:pos+frame]
        if len(c): vals.append(float(np.sqrt(np.mean(c*c)+1e-12)))
    if not vals: return 0.0,len(audio)/sr
    arr=np.asarray(vals,float); vmax=float(arr.max())+1e-12
    db=20*np.log10((arr+1e-12)/vmax); active=db>-31.0; run=4
    first=0; last=len(active)-1
    for i in range(0,max(1,len(active)-run+1)):
        if active[i:i+run].all(): first=i; break
    for i in range(len(active)-run,-1,-1):
        if active[i:i+run].all(): last=i+run-1; break
    start=max(0.0,first*hop/sr-.4)
    end=min(len(audio)/sr,(last*hop+frame)/sr+.45)
    return start,max(start+1.0,end)

def section_signature(section):
    return norm(" ".join(section["lines"][:2]))

def coarse_section_boundaries(sections,segs,vocal_start,vocal_end):
    candidates=[]
    for i in range(len(segs)):
        t=""
        for j in range(i,min(len(segs),i+3)):
            t+=str(segs[j].get("text","")).strip()
            candidates.append({"start":float(segs[i].get("start",0.0)),"end":float(segs[j].get("end",0.0)),"norm":norm(t)})
    starts=[None]*len(sections); scores=[0.0]*len(sections)
    starts[0]=vocal_start; scores[0]=1.0; min_time=vocal_start
    for si in range(1,len(sections)):
        sig=section_signature(sections[si]); best=None
        for c in candidates:
            if c["start"]<min_time+2.0 or c["start"]>vocal_end or not sig or not c["norm"]: continue
            ratio=SequenceMatcher(None,sig,c["norm"],autojunk=False).ratio()
            lr=min(len(sig),len(c["norm"]))/max(1,max(len(sig),len(c["norm"])))
            score=.84*ratio+.16*lr
            if sig[:8] and sig[:8] in c["norm"]: score+=.08
            if best is None or score>best["score"]: best={**c,"score":score}
        if best and best["score"]>=.28:
            starts[si]=max(vocal_start,best["start"]-.7); scores[si]=min(1.0,best["score"]); min_time=best["start"]+2.0
    weights=[max(8,sum(len(norm(x)) for x in s["lines"])) for s in sections]
    known=[i for i,t in enumerate(starts) if t is not None]
    for a,b in zip(known,known[1:]):
        if b<=a+1: continue
        span=starts[b]-starts[a]; inner=list(range(a+1,b)); denom=weights[a]+sum(weights[k] for k in inner); acc=weights[a]
        for k in inner:
            starts[k]=starts[a]+span*(acc/max(1,denom)); scores[k]=0.0; acc+=weights[k]
    last=max(i for i,x in enumerate(starts) if x is not None)
    if last<len(sections)-1:
        inner=list(range(last+1,len(sections))); avail=max(1.0,vocal_end-starts[last]); denom=weights[last]+sum(weights[k] for k in inner); acc=weights[last]
        for k in inner:
            starts[k]=starts[last]+avail*(acc/max(1,denom)); scores[k]=0.0; acc+=weights[k]
    for i in range(1,len(starts)):
        if starts[i]<=starts[i-1]+3.0: starts[i]=starts[i-1]+3.0
    wins=[]
    for i,s in enumerate(sections):
        st=max(vocal_start,starts[i]-(.4 if i==0 else 2.0))
        en=min(vocal_end,starts[i+1]+2.5) if i+1<len(sections) else vocal_end
        if en<=st+5.0: en=min(vocal_end,st+20.0)
        wins.append({"start":st,"end":en,"anchor_score":scores[i]})
    return wins

def flatten_chars(aligned):
    chars=[]
    for seg in aligned.get("segments",[]) or []:
        for ch in seg.get("chars",[]) or []:
            n=norm(ch.get("char",""))
            if not n: continue
            for unit in n:
                chars.append({"ch":unit,"start":ch.get("start"),"end":ch.get("end"),"score":ch.get("score")})
    return chars

def align_char_sequences(target,actual):
    n,m=len(target),len(actual)
    if not n or not m: return {}
    prev=[j*-0.7 for j in range(m+1)]; trace=[bytearray(m+1) for _ in range(n+1)]
    for j in range(1,m+1): trace[0][j]=2
    for i in range(1,n+1):
        cur=[i*-1.0]+[0.0]*m; trace[i][0]=1; tc=target[i-1]["ch"]
        for j in range(1,m+1):
            ac=actual[j-1]["ch"]; diag=prev[j-1]+(3.0 if tc==ac else -2.0); up=prev[j]-1.0; left=cur[j-1]-.7
            if diag>=up and diag>=left: cur[j]=diag; trace[i][j]=0
            elif up>=left: cur[j]=up; trace[i][j]=1
            else: cur[j]=left; trace[i][j]=2
        prev=cur
    mp={}; i=n; j=m
    while i>0 or j>0:
        d=trace[i][j]
        if i>0 and j>0 and d==0:
            if target[i-1]["ch"]==actual[j-1]["ch"]: mp[i-1]=j-1
            i-=1; j-=1
        elif i>0 and (j==0 or d==1): i-=1
        else: j-=1
    return mp

def line_times_from_section(section,aligned):
    target=[]; counts=[]
    for li,line in enumerate(section["lines"]):
        n=norm(line); counts.append(len(n))
        for pos,ch in enumerate(n): target.append({"ch":ch,"line":li,"pos":pos})
    achars=flatten_chars(aligned); mapping=align_char_sequences(target,achars)
    per=[[] for _ in section["lines"]]; matched=[0]*len(section["lines"])
    for ti,tc in enumerate(target):
        ai=mapping.get(ti)
        if ai is None: continue
        c=achars[ai]
        if c["start"] is None or c["end"] is None: continue
        per[tc["line"]].append(c); matched[tc["line"]]+=1
    rows=[]
    for li,text in enumerate(section["lines"]):
        cov=matched[li]/max(1,counts[li]); cs=per[li]
        if cs:
            st=min(float(c["start"]) for c in cs); en=max(float(c["end"]) for c in cs)
            sc=[float(c["score"]) for c in cs if c.get("score") is not None]
            ctc=sum(sc)/len(sc) if sc else None
        else: st=en=ctc=None
        rows.append({"section":section["display_name"],"text":text,"start":st,"raw_end":en,"coverage":cov,"ctc_score":ctc,"direct":bool(cs) and cov>=.35})
    known=[i for i,r in enumerate(rows) if r["direct"]]
    if len(known)<max(2,int(math.ceil(len(rows)*.50))):
        raise RuntimeError("%s 구간의 강제정렬 신뢰도가 낮습니다. (%d/%d줄 직접 정렬)"%(section["display_name"],len(known),len(rows)))
    for a,b in zip(known,known[1:]):
        if b<=a+1: continue
        left=rows[a]["start"]; right=rows[b]["start"]; missing=list(range(a+1,b))
        weights=[max(3,len(norm(rows[k]["text"]))) for k in missing]; base=max(3,len(norm(rows[a]["text"]))); denom=base+sum(weights); acc=base
        for k,w in zip(missing,weights):
            rows[k]["start"]=left+(right-left)*acc/max(1,denom); rows[k]["direct"]=False; acc+=w
    segs=aligned.get("segments",[]) or []
    sec_start=min(float(s.get("start",0.0)) for s in segs) if segs else 0.0
    sec_end=max(float(s.get("end",sec_start+1.0)) for s in segs) if segs else sec_start+1.0
    first=known[0]
    if first>0:
        missing=list(range(first)); span=max(.5,rows[first]["start"]-sec_start); weights=[max(3,len(norm(rows[k]["text"]))) for k in missing]; total=sum(weights) or 1; cur=sec_start
        for k,w in zip(missing,weights): rows[k]["start"]=cur; cur+=span*w/total
    last=known[-1]
    if last<len(rows)-1:
        missing=list(range(last+1,len(rows))); span=max(.5,sec_end-rows[last]["start"]); base=max(3,len(norm(rows[last]["text"]))); weights=[max(3,len(norm(rows[k]["text"]))) for k in missing]; total=base+sum(weights); acc=base
        for k,w in zip(missing,weights): rows[k]["start"]=rows[last]["start"]+span*acc/max(1,total); acc+=w
    prev=-1.0
    for r in rows:
        if r["start"] is None: raise RuntimeError("%s에서 시작 시간을 결정하지 못했습니다."%section["display_name"])
        r["start"]=max(0.0,float(r["start"])-.08)
        if r["start"]<=prev+.08: r["start"]=prev+.08
        prev=r["start"]
    for i,r in enumerate(rows):
        nxt=rows[i+1]["start"] if i+1<len(rows) else sec_end
        heard=float(r["raw_end"]) if r["raw_end"] is not None else nxt-.06
        r["end"]=max(r["start"]+.45,min(heard+.12,nxt-.04 if i+1<len(rows) else sec_end))
        if r["end"]<=r["start"]: r["end"]=r["start"]+.45
    return rows

def srt_time(sec):
    ms=max(0,int(round(sec*1000))); h,rem=divmod(ms,3600000); m,rem=divmod(rem,60000); s,ms=divmod(rem,1000)
    return "%02d:%02d:%02d,%03d"%(h,m,s,ms)

def vegas_tc(sec,fps):
    total=max(0,int(round(float(sec)*fps))); fi=int(fps); h,rem=divmod(total,fi*3600); m,rem=divmod(rem,fi*60); s,ff=divmod(rem,fi)
    return "%02d:%02d:%02d.%02d"%(h,m,s,ff)

def get_media_duration_seconds(source):
    try:
        flags=getattr(subprocess,"CREATE_NO_WINDOW",0) if os.name=="nt" else 0
        cp=subprocess.run(
            ["ffprobe","-v","error","-show_entries","format=duration",
             "-of","default=noprint_wrappers=1:nokey=1",str(source)],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
            encoding="utf-8",errors="replace",creationflags=flags
        )
        if cp.returncode==0:
            return max(0.0,float((cp.stdout or "").strip()))
    except Exception:
        pass
    return 0.0

def extend_all_lyric_tails(source,rows):
    if not rows:
        return {"adjusted":0,"last_original":0.0,"last_adjusted":0.0,"duration":0.0}

    adjusted=0

    # CTC의 end는 "마지막 음소가 끝난 지점"에 가깝다.
    # 자막 표시는 그 지점에서 바로 끊지 않고 다음 가사 시작 전까지 여운을 준다.
    # 짧은 가사 간격: 다음 줄 0.10초 전까지 유지
    # 긴 무가사 간격/간주: 최대 1.20초만 추가 유지
    for i in range(len(rows)-1):
        cur=rows[i]
        nxt=rows[i+1]
        original=float(cur["end"])
        gap=float(nxt["start"])-original

        if gap <= 0.10:
            continue

        if gap <= 2.20:
            desired=float(nxt["start"])-0.10
        else:
            desired=original+1.20

        # 최소 0.35초의 여운을 주되 다음 가사를 침범하지 않는다.
        desired=max(desired, min(original+0.35, float(nxt["start"])-0.05))
        desired=min(desired, float(nxt["start"])-0.05)

        if desired>original:
            cur["end"]=desired
            adjusted+=1

    # 마지막 가사는 실제 곡 끝의 여운까지 유지한다.
    last=rows[-1]
    last_original=float(last["end"])
    duration=get_media_duration_seconds(source)

    if duration>last_original:
        target=min(max(last_original+1.50,duration-0.20),last_original+8.0)
        if target>last_original:
            last["end"]=target
            adjusted+=1

    return {
        "adjusted":adjusted,
        "last_original":last_original,
        "last_adjusted":float(last["end"]),
        "duration":duration
    }

def write_outputs(source,rows,out_dir):
    tail_info=extend_all_lyric_tails(source,rows)
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); base=Path(source).stem
    srt=out/(base+"_SRT.srt")
    rep=out/(base+"_SYNC_REPORT.csv")
    jsn=out/(base+"_MMS_ALIGNMENT.json")
    t24=out/(base+"_VEGAS_TimeFrames_24fps.txt")
    t30=out/(base+"_VEGAS_TimeFrames_30fps.txt")

    blocks=[]
    for i,r in enumerate(rows,1):
        blocks.append("%d\r\n%s --> %s\r\n%s\r\n"%(i,srt_time(r["start"]),srt_time(r["end"]),r["text"]))
    srt.write_text("\r\n".join(blocks),encoding="utf-8-sig")

    for path,fps in ((t24,24),(t30,30)):
        with path.open("w",encoding="utf-8-sig",newline="") as f:
            for r in rows:
                txt=r["text"].replace("\t"," ").replace("\r"," ").replace("\n"," ")
                f.write("%s\t%s\t%s\t%s\r\n"%(
                    vegas_tc(r["start"],fps),
                    vegas_tc(r["end"],fps),
                    vegas_tc(max(.04,r["end"]-r["start"]),fps),
                    txt
                ))

    with rep.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f)
        w.writerow(["번호","구간","시작초","종료초","MMS점수","가사"])
        for i,r in enumerate(rows,1):
            w.writerow([i,r["section"],"%.3f"%r["start"],"%.3f"%r["end"],"%.4f"%r["mms_score"],r["text"]])

    jsn.write_text(json.dumps({
        "engine":"MMS-300M + built-in CTC Viterbi",
        "rows":rows
    },ensure_ascii=False,indent=2),encoding="utf-8-sig")
    return {"srt":srt,"report":rep,"json":jsn,"txt24":t24,"txt30":t30,"tail_info":tail_info}

class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__(); self.title(APP_NAME+" "+APP_VERSION); self.geometry("900x760"); self.minsize(820,680); self.q=queue.Queue(); self._build(); self.after(150,self._poll)
    def _build(self):
        import tkinter as tk
        pad={"padx":10,"pady":6}
        ttk.Label(self,text="찬양 자막 자동생성",font=("Malgun Gothic",20,"bold")).pack(pady=(16,2))
        ttk.Label(self,text="보컬 분리 → MMS-300M 다국어 강제정렬 → VEGAS 자막").pack(pady=(0,12))
        frm=ttk.Frame(self); frm.pack(fill="x",padx=18)
        self.audio_var=tk.StringVar(); self.lyrics_var=tk.StringVar(); self.out_var=tk.StringVar()
        ttk.Label(frm,text="1. 음악/영상").grid(row=0,column=0,sticky="nw",**pad)
        self.audio_drop=tk.Label(frm,text="🎵 MP4/WAV/MP3 파일을 여기에 끌어놓으세요",relief="groove",borderwidth=2,padx=18,pady=20,bg="#f4f8f2",font=("Malgun Gothic",10,"bold"),cursor="hand2")
        self.audio_drop.grid(row=0,column=1,sticky="ew",**pad); self.audio_drop.bind("<Button-1>",lambda e:self.pick_audio()); self.audio_drop.drop_target_register(DND_FILES); self.audio_drop.dnd_bind("<<Drop>>",self.on_drop_audio); ttk.Button(frm,text="찾기",command=self.pick_audio).grid(row=0,column=2,**pad)
        ttk.Label(frm,text="2. 정확한 가사 TXT").grid(row=1,column=0,sticky="nw",**pad)
        self.lyrics_drop=tk.Label(frm,text="📝 [Verse], [Chorus] 구분이 있는 TXT를 여기에 끌어놓으세요",relief="groove",borderwidth=2,padx=18,pady=20,bg="#f4f8f2",font=("Malgun Gothic",10,"bold"),cursor="hand2")
        self.lyrics_drop.grid(row=1,column=1,sticky="ew",**pad); self.lyrics_drop.bind("<Button-1>",lambda e:self.pick_lyrics()); self.lyrics_drop.drop_target_register(DND_FILES); self.lyrics_drop.dnd_bind("<<Drop>>",self.on_drop_lyrics); ttk.Button(frm,text="찾기",command=self.pick_lyrics).grid(row=1,column=2,**pad)
        ttk.Label(frm,text="3. 결과 폴더").grid(row=2,column=0,sticky="w",**pad); ttk.Entry(frm,textvariable=self.out_var).grid(row=2,column=1,sticky="ew",**pad); ttk.Button(frm,text="찾기",command=self.pick_out).grid(row=2,column=2,**pad); frm.columnconfigure(1,weight=1)
        self.go_btn=ttk.Button(self,text="MMS 자동 싱크 생성 시작",command=self.start,width=30); self.go_btn.pack(pady=(14,8),ipady=8)
        self.pb=ttk.Progressbar(self,mode="indeterminate",length=620); self.pb.pack(pady=(0,8))
        ttk.Label(self,text="※ 곡마다 마커를 찍지 않습니다. 반복 Chorus도 TXT 순서대로 자동 정렬합니다.").pack(pady=(0,6))
        self.log=tk.Text(self,height=20,wrap="word",font=("Malgun Gothic",9)); self.log.pack(fill="both",expand=True,padx=18,pady=8); self.log.configure(state="disabled")
        bottom=ttk.Frame(self); bottom.pack(fill="x",padx=18,pady=(0,15)); ttk.Button(bottom,text="결과 폴더 열기",command=self.open_out).pack(side="left"); ttk.Button(bottom,text="캐시 폴더 열기",command=lambda:os.startfile(str(CACHE_DIR))).pack(side="left",padx=8); ttk.Label(bottom,text="VEGAS는 Insert → Insert Subtitles from Files 사용").pack(side="right")
    def logmsg(self,msg):
        self.log.configure(state="normal"); self.log.insert("end",msg.rstrip()+"\n"); self.log.see("end"); self.log.configure(state="disabled")
    def _drop_first(self,data):
        try:
            a=self.tk.splitlist(data); return a[0] if a else ""
        except Exception: return data.strip().strip("{}")
    def _set_audio(self,p):
        if p and Path(p).suffix.lower() in {".mp4",".mov",".mkv",".wav",".mp3",".m4a",".flac",".aac"}:
            self.audio_var.set(p); self.audio_drop.config(text="🎵 선택됨\n"+Path(p).name); self.out_var.set(self.out_var.get() or str(Path(p).parent))
    def _set_lyrics(self,p):
        if p and Path(p).suffix.lower()==".txt": self.lyrics_var.set(p); self.lyrics_drop.config(text="📝 선택됨\n"+Path(p).name)
    def on_drop_audio(self,e): self._set_audio(self._drop_first(e.data))
    def on_drop_lyrics(self,e): self._set_lyrics(self._drop_first(e.data))
    def pick_audio(self):
        p=filedialog.askopenfilename(filetypes=[("Media","*.mp4 *.mov *.mkv *.wav *.mp3 *.m4a *.flac *.aac"),("All","*.*")])
        if p:self._set_audio(p)
    def pick_lyrics(self):
        p=filedialog.askopenfilename(filetypes=[("Text","*.txt"),("All","*.*")])
        if p:self._set_lyrics(p)
    def pick_out(self):
        p=filedialog.askdirectory()
        if p:self.out_var.set(p)
    def open_out(self):
        p=self.out_var.get().strip()
        if p and Path(p).exists(): os.startfile(p)
    def start(self):
        source=self.audio_var.get().strip(); lyrics=self.lyrics_var.get().strip(); out=self.out_var.get().strip() or (str(Path(source).parent) if source else "")
        if not source or not Path(source).exists(): messagebox.showwarning(APP_NAME,"음악/영상 파일을 선택해 주세요."); return
        if not lyrics or not Path(lyrics).exists(): messagebox.showwarning(APP_NAME,"가사 TXT 파일을 선택해 주세요."); return
        self.out_var.set(out); self.go_btn.configure(state="disabled"); self.pb.start(10); self.logmsg("="*64); self.logmsg("5.0 MMS 자동 싱크를 시작합니다.")
        threading.Thread(target=self._work,args=(source,lyrics,out),daemon=True).start()
    def _work(self,source,lyrics,out_dir):
        try:
            ensure_console_streams()
            sections=parse_sections(read_text_safely(lyrics))
            if not sections:
                raise RuntimeError("가사 구간을 찾지 못했습니다.")
            total_lines=sum(len(s["lines"]) for s in sections)
            self.q.put(("log","가사: %d개 구간 / %d줄"%(len(sections),total_lines)))

            key=file_key(source)
            work=CACHE_DIR/key
            work.mkdir(parents=True,exist_ok=True)
            source_wav=work/"source.wav"

            self.q.put(("log","1/4 원본 오디오 준비 중..."))
            if not source_wav.exists():
                extract_wav(source,source_wav)

            device="cpu"
            try:
                import torch
                if torch.cuda.is_available():
                    device="cuda"
            except Exception:
                pass
            self.q.put(("log","장치: "+("NVIDIA GPU" if device=="cuda" else "CPU")))

            self.q.put(("log","2/4 보컬 분리 중..."))
            sep_root=work/"separated"
            vocals=sep_root/"htdemucs"/source_wav.stem/"vocals.wav"
            if not vocals.exists():
                vocals=separate_vocals(source_wav,sep_root,device)
            else:
                self.q.put(("log","기존 보컬 분리 캐시를 재사용합니다."))

            self.q.put(("log","3/4 MMS-300M으로 정답 가사 강제정렬 중..."))
            all_rows=align_lines_mms(
                vocals,sections,device,
                log_cb=lambda msg:self.q.put(("log",msg))
            )
            self.q.put(("log","MMS 정렬 완료: %d/%d줄"%(len(all_rows),total_lines)))
            self.q.put(("log","앞 10줄 타이밍:"))
            for i,r in enumerate(all_rows[:10],1):
                self.q.put(("log","  %02d. %7.2f ~ %7.2f  %s"%(i,r["start"],r["end"],r["text"])))

            weakest=sorted(enumerate(all_rows,1),key=lambda x:x[1]["mms_score"])[:5]
            self.q.put(("log","점수가 낮은 5줄(먼저 확인할 곳):"))
            for idx,r in weakest:
                self.q.put(("log","  %02d. score=%7.3f  %s"%(idx,r["mms_score"],r["text"])))

            self.q.put(("log","4/4 SRT와 VEGAS 파일 생성 중..."))
            self.q.put(("done",write_outputs(source,all_rows,out_dir)))
        except Exception as e:
            self.q.put(("error",str(e)+"\n\n"+traceback.format_exc()))

    def _poll(self):
        try:
            while True:
                kind,p=self.q.get_nowait()
                if kind=="log": self.logmsg(p)
                elif kind=="done":
                    self.pb.stop(); self.go_btn.configure(state="normal")
                    self.logmsg("완료!")
                    self.logmsg("24fps VEGAS: "+str(p["txt24"]))
                    self.logmsg("30fps VEGAS: "+str(p["txt30"]))
                    self.logmsg("SRT: "+str(p["srt"]))
                    self.logmsg("싱크 리포트: "+str(p["report"]))
                    self.logmsg("MMS 정렬 JSON: "+str(p["json"]))
                    if p.get("tail_info"):
                        ti=p["tail_info"]
                        self.logmsg("가사 여운 보정: %d줄"%ti["adjusted"])
                        self.logmsg("마지막 가사: %.2f초 → %.2f초 (곡 끝 %.2f초)"%(ti["last_original"],ti["last_adjusted"],ti["duration"]))
                    messagebox.showinfo(APP_NAME,"5.0 MMS 자동 싱크가 끝났습니다.\n\n곡마다 마커를 찍지 않습니다.\n먼저 앞/중간/뒤 3곳만 재생해서 싱크를 확인해 주세요.\n\n30p 프로젝트는 *_VEGAS_TimeFrames_30fps.txt를 사용하세요.")
                elif kind=="error":
                    self.pb.stop(); self.go_btn.configure(state="normal"); self.logmsg("오류:"); self.logmsg(p); messagebox.showerror(APP_NAME,p.split("\n\n")[0])
        except queue.Empty: pass
        self.after(150,self._poll)

if __name__=="__main__": App().mainloop()
