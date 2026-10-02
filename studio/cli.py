"""한국어 운영 CLI."""
import argparse, json, sys
from pathlib import Path
from .model import Blocked, KINDS, GATES, validate_shots
from .store import Store, write_json
from . import pipeline, gates, capabilities, adapters, editor

def main():
    p=argparse.ArgumentParser(description="로컬 숏폼 제작 스튜디오")
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parent.parent)
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("doctor")
    x=sub.add_parser("init");x.add_argument("brief",type=Path)
    x=sub.add_parser("fixture");x.add_argument("id")
    for cmd in ("status","resume","release"):
        x=sub.add_parser(cmd);x.add_argument("id")
    x=sub.add_parser("ingest");x.add_argument("id");x.add_argument("kind",choices=KINDS);x.add_argument("file",type=Path);x.add_argument("--author",required=True)
    x=sub.add_parser("qa-template");x.add_argument("id");x.add_argument("gate",choices=GATES);x.add_argument("--reviewer",required=True)
    x=sub.add_parser("qa");x.add_argument("id");x.add_argument("file",type=Path)
    x=sub.add_parser("recover");x.add_argument("id");x.add_argument("stage",choices=KINDS);x.add_argument("--problem",required=True);x.add_argument("--hypothesis",required=True)
    x=sub.add_parser("agent-plan");x.add_argument("role");x.add_argument("--id")
    x=sub.add_parser("compose");x.add_argument("manifest",type=Path);x.add_argument("output",type=Path)
    x=sub.add_parser("blender-fixture");x.add_argument("output",type=Path);x.add_argument("--frames",type=int,default=1)
    x=sub.add_parser("voice-candidate");x.add_argument("text");x.add_argument("voice");x.add_argument("output",type=Path);x.add_argument("--speed",type=int,default=180)
    x=sub.add_parser("captions");x.add_argument("file",type=Path);x.add_argument("output",type=Path);x.add_argument("--duration",type=float,required=True)
    x=sub.add_parser("mix");x.add_argument("manifest",type=Path);x.add_argument("output",type=Path)
    args=p.parse_args();root=args.root.resolve()
    try:
        cmd=args.command
        if cmd=="doctor": result=capabilities.inspect(root)
        elif cmd=="init":
            brief=json.loads(args.brief.read_text());result=Store(root,brief["production_id"]).create(brief)
        elif cmd=="fixture": result=pipeline.fixture(root,args.id)
        elif cmd=="agent-plan": result=pipeline.agent_plan(root,args.role,Store(root,args.id) if args.id else None)
        elif cmd in ("compose","blender-fixture","voice-candidate","captions","mix"):
            if not args.output.resolve().is_relative_to(root): raise Blocked("미디어 출력은 프로젝트 내부여야 합니다")
            if cmd=="captions": result=editor.export_srt(json.loads(args.file.read_text()),args.duration,args.output)
            elif cmd=="mix": result=editor.mix_stems(args.manifest,args.output,root)
            elif cmd=="compose": result=adapters.compose_layers(args.manifest,args.output,root)
            elif cmd=="blender-fixture": result={"log":adapters.blender_fixture(root,args.output,args.frames),"quality":"NOT_REVIEWED"}
            else: result=adapters.say_candidate(args.text,args.voice,args.output,args.speed)
        else:
            store=Store(root,args.id)
            if cmd=="status": result=pipeline.status(store)
            elif cmd=="resume": result=pipeline.resume(store)
            elif cmd=="release": result={"path":gates.release(store)}
            elif cmd=="ingest":
                if args.kind=="SHOT": validate_shots(json.loads(args.file.read_text()),store.load()["brief"]["duration"])
                result=store.artifact(args.kind,args.file,args.author)
            elif cmd=="qa-template": result=gates.template(store,args.gate,args.reviewer)
            elif cmd=="qa": result=gates.submit(store,json.loads(args.file.read_text()))
            elif cmd=="recover": result=pipeline.recovery(store,args.stage,args.problem,args.hypothesis)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (Blocked,ValueError,KeyError,FileNotFoundError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc)},ensure_ascii=False),file=sys.stderr);sys.exit(2)
if __name__=="__main__": main()
