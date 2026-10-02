"""발화 단위 자막과 분리 오디오 스템 편집. 품질 자동 승인 없음."""
import json, re
from pathlib import Path
from .model import Blocked
from . import provenance
from .adapters import run, probe
STEMS=("VOICE","BGM","AMBIENCE","IMPACT","WHOOSH","OBJECT","TRANSITION SOUND")

def captions(items,duration,other_text=None):
    previous=0
    normalized=lambda text: re.sub(r"\s+","",text).casefold()
    other_text=other_text or {}
    for item in items:
        for k in ("text","startMs","endMs","timestampMs","confidence"):
            if k not in item: raise Blocked("자막 JSON 필드 누락: "+k)
        if not isinstance(item["text"],str) or not item["text"].strip(): raise Blocked("빈 자막")
        if not 0<=previous<=item["startMs"]<item["endMs"]<=duration*1000: raise Blocked("자막 시간/겹침 오류")
        lines=item["text"].splitlines()
        if len(lines)>2 or any(len(x)>22 for x in lines): raise Blocked("모바일 자막: 1~2줄, 줄당 22자 이내로 나누세요")
        for label,entries in other_text.items():
            if label not in ("TITLE","INFOGRAPHIC TEXT","PLATFORM CAPTION"): raise Blocked("텍스트 레이어 종류 오류")
            if any(normalized(item["text"])==normalized(x) for x in entries): raise Blocked("자막과 "+label+"의 정확한 텍스트 중복")
        previous=item["endMs"]
    return {"execution":"SUCCESS","quality":"NOT_REVIEWED","caption_count":len(items),"note":"의미상 중복과 실제 화면 가독성은 독립 수동 QA 필요"}

def export_srt(items,duration,output,other_text=None):
    result=captions(items,duration,other_text)
    def stamp(ms):
        ms=int(ms);sec,ms=divmod(ms,1000);minute,sec=divmod(sec,60);hour,minute=divmod(minute,60)
        return f"{hour:02}:{minute:02}:{sec:02},{ms:03}"
    output=Path(output)
    if output.exists(): raise Blocked("기존 자막 출력 덮어쓰기 금지")
    output.write_text("\n\n".join(f"{i}\n{stamp(x['startMs'])} --> {stamp(x['endMs'])}\n{x['text']}" for i,x in enumerate(items,1))+"\n",encoding="utf-8")
    return result

def mix_stems(manifest,output,root=None):
    manifest=Path(manifest).resolve();data=json.loads(manifest.read_text());base=manifest.parent
    root=provenance.workspace(output,root)
    if not data.get("stems") or not any(x["type"]=="VOICE" for x in data["stems"]): raise Blocked("VOICE 스템 필요")
    args=["ffmpeg","-v","error","-n"];filters=[];labels=[]
    for i,stem in enumerate(data["stems"]):
        if stem["type"] not in STEMS: raise Blocked("알 수 없는 오디오 스템")
        path=(base/stem["file"]).resolve()
        if not path.is_relative_to(base) or not path.is_file(): raise Blocked("오디오 경로 이탈/누락")
        if not any(x["codec_type"]=="audio" for x in probe(path)["streams"]): raise Blocked("오디오 스트림 없음")
        gain=float(stem.get("gain",1));delay=int(stem.get("delay_ms",0))
        if not 0<=gain<=2 or delay<0: raise Blocked("게인/시간 오류")
        args += ["-i",str(path)];filters.append(f"[{i}:a]volume={gain},adelay={delay}:all=1[a{i}]");labels.append(f"[a{i}]")
    filters.append("".join(labels)+f"amix=inputs={len(labels)}:duration=longest:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    args += ["-filter_complex",";".join(filters),"-map","[out]","-ar","48000","-c:a","pcm_s16le",str(output)]
    marked=any(provenance.is_fixture((base/x["file"]).resolve(),root) for x in data["stems"])
    if marked:provenance.mark(output)
    try:run(args)
    finally:
        if marked:provenance.register(output,root)
    return {"execution":"SUCCESS","quality":"NOT_REVIEWED","metadata":probe(output),"stems_preserved":True}
