"""셸 없는 로컬 미디어 실행. 생성 API를 암묵적으로 호출하지 않는다."""
import json, shutil, subprocess
from pathlib import Path
from .model import Blocked
from . import provenance

def run(args,timeout=90):
    if not shutil.which(args[0]) and not Path(args[0]).is_file(): raise Blocked("도구 없음: "+args[0])
    p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if p.returncode: raise Blocked("도구 실행 실패: "+args[0]+"\n"+p.stderr[-2500:])
    return p.stdout

def probe(path):
    return json.loads(run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)]))

def mark_fixture(path):
    provenance.mark(path);provenance.register(path)

def fixture_video(output,duration=3):
    if Path(output).exists(): raise Blocked("기존 fixture 출력 덮어쓰기 금지")
    provenance.mark(output)
    try:
        run(["ffmpeg","-v","error","-n","-f","lavfi","-i",f"color=c=0x042A24:s=270x480:r=24:d={duration}","-f","lavfi","-i",f"sine=frequency=440:sample_rate=48000:duration={duration}","-vf","drawbox=x=30:y=180:w=70:h=70:color=white:t=fill,drawbox=x=160:y=180:w=70:h=70:color=red:t=fill,rotate=0.12*sin(2*PI*t):fillcolor=0x042A24","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(output)])
    finally:provenance.register(output)
    return probe(output)

def technical_check(video,expected_duration,delivery_spec=None):
    spec=delivery_spec or {}
    ratio=spec.get("aspect_ratio")
    if ratio not in (None,"9:16","16:9","1:1"): raise Blocked("미지원 납품 비율")
    audio_required=spec.get("audio_required",True)
    if not isinstance(audio_required,bool): raise Blocked("audio_required는 bool이어야 합니다")
    meta=probe(video); streams=meta["streams"]
    v=next((s for s in streams if s["codec_type"]=="video"),None);a=next((s for s in streams if s["codec_type"]=="audio"),None)
    errors=[]
    if not v or audio_required and not a: errors.append("영상·오디오 스트림 누락" if audio_required else "영상 스트림 누락")
    if abs(float(meta["format"]["duration"])-expected_duration)>0.15: errors.append("분량 불일치")
    if v:
        if ratio:
            rw,rh=map(int,ratio.split(":"))
            if abs(v["width"]*rh-v["height"]*rw)>max(rw,rh): errors.append("납품 비율 불일치")
        elif v["width"]>=v["height"]: errors.append("세로 화면 아님")
    run(["ffmpeg","-v","error","-i",str(video),"-f","null","-"])
    return {"execution":"SUCCESS","quality":"NOT_REVIEWED","errors":errors,"metadata":meta}

def say_candidate(text,voice,output,speed=180):
    if Path(output).exists(): raise Blocked("기존 음성 출력 덮어쓰기 금지")
    provenance.mark(output)
    try:run(["say","-v",voice,"-r",str(speed),"-o",str(output),text],timeout=60)
    finally:provenance.register(output)
    return probe(output)

def blender_fixture(root,output_dir,frames=1):
    output_dir=Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()): raise Blocked("Blender 출력은 비어 있는 새 디렉토리가 필요합니다")
    output_dir.mkdir(parents=True,exist_ok=True)
    provenance.mark(output_dir)
    try:log=run(["blender","--background","--factory-startup","--python",str(Path(root)/"scripts"/"blender_fixture.py"),"--",str(output_dir),str(frames)],timeout=150)
    finally:provenance.register(output_dir,root)
    return log

def compose_layers(manifest,output,root=None):
    """검수된 2D Shot 레이어 합성. 모든 입력은 같은 폴더 내부 실제 파일."""
    manifest=Path(manifest).resolve(); data=json.loads(manifest.read_text());base=manifest.parent
    root=provenance.workspace(output,root)
    args=["ffmpeg","-v","error","-n"];names=[]
    for layer in data["layers"]:
        p=(base/layer["file"]).resolve()
        if not p.is_relative_to(base) or not p.is_file(): raise Blocked("레이어 파일 경로 오류")
        args += ["-loop","1","-i",str(p)];names.append(layer)
    if not names or names[0]["type"]!="BACKGROUND": raise Blocked("BACKGROUND 레이어가 첫 입력이어야 합니다")
    graph=[f"[0:v]scale={data['width']}:{data['height']},format=rgba[v0]"]
    for i,layer in enumerate(names[1:],1):
        graph.append(f"[v{i-1}][{i}:v]overlay=x={int(layer.get('x',0))}:y={int(layer.get('y',0))}:format=auto[v{i}]")
    args += ["-filter_complex",";".join(graph),"-map",f"[v{len(names)-1}]","-t",str(data["duration"]),"-r","24","-c:v","libx264","-pix_fmt","yuv420p",str(output)]
    marked=any(provenance.is_fixture((base/x["file"]).resolve(),root) for x in names)
    if marked:provenance.mark(output)
    try:run(args)
    finally:
        if marked:provenance.register(output,root)
    return probe(output)
