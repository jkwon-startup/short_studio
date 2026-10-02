"""불변 산출물, 원자적 상태 쓰기, 잠금과 실패 보존."""
import contextlib, datetime, fcntl, json, os, shutil, uuid
from pathlib import Path
from .provenance import is_fixture, register
from .model import Blocked, KINDS, DEPS, PACKAGES, safe_id, digest, file_hash, code_hash, validate_brief

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def write_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(temp,path)

class Store:
    def __init__(self, root, production_id):
        self.root=Path(root).resolve(); self.path=self.root/"runs"/safe_id(production_id)
        if not self.path.resolve().is_relative_to(self.root): raise Blocked("경로 이탈")
        self.state_path=self.path/"PROJECT"/"state.json"
    @contextlib.contextmanager
    def lock(self):
        self.path.mkdir(parents=True,exist_ok=True)
        with (self.path/"PROJECT.lock").open("a") as f:
            fcntl.flock(f,fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(f,fcntl.LOCK_UN)
    def load(self):
        if not self.state_path.exists(): raise Blocked("제작 ID가 없습니다. init을 먼저 실행하세요")
        return json.loads(self.state_path.read_text())
    def save(self,state): write_json(self.state_path,state)
    def log(self,event,data):
        p=self.path/"LOG"/"events.jsonl";p.parent.mkdir(parents=True,exist_ok=True)
        with p.open("a") as f: f.write(json.dumps({"at":now(),"event":event,"data":data},ensure_ascii=False)+"\n")
    def create(self,brief):
        validate_brief(brief)
        with self.lock():
            if self.state_path.exists(): raise Blocked("기존 제작을 덮어쓰지 않습니다")
            for name in PACKAGES: (self.path/name).mkdir(parents=True,exist_ok=True)
            state={"production_id":brief["production_id"],"mode":brief["mode"],"brief":brief,"created":now(),"artifacts":{},"qa":{},"history":[],"generation":0}
            self.save(state);write_json(self.path/"PROJECT"/"brief.json",brief);self.log("INIT",{"mode":brief["mode"]})
        return state
    def artifact(self,kind,source,author, metadata=None):
        if kind not in KINDS: raise Blocked("알 수 없는 산출물 종류")
        if Path(source).is_symlink(): raise Blocked("심볼릭 링크 입력은 등록하지 않습니다")
        source=Path(source).resolve()
        if not source.is_file(): raise Blocked("실제 파일이 필요합니다")
        metadata=dict(metadata or {})
        source_digest=file_hash(source)
        if is_fixture(source,self.root):metadata["fixture"]=True
        # 같은 바이트를 복사/이름 변경해도 알려진 fixture 이력을 전파한다.
        if source.with_name(source.name+".fixture.json").exists(): metadata["fixture"]=True
        for parent in source.parents:
            if (parent/".fixture.json").exists(): metadata["fixture"]=True;break
            if parent==self.root:break
        if source.suffix==".json":
            try:
                payload=json.loads(source.read_text())
                if isinstance(payload,dict) and payload.get("fixture") is True:metadata["fixture"]=True
            except (ValueError,UnicodeError):pass
        for ledger in (self.root/"runs").glob("*/PROJECT/state.json"):
            prior=json.loads(ledger.read_text())
            for item in prior.get("history",[]):
                if item["sha256"]==source_digest and (prior["mode"]=="fixture" or item.get("metadata",{}).get("fixture")):
                    metadata["fixture"]=True
        with self.lock():
            state=self.load()
            if any(state["artifacts"].get(k,{}).get("metadata",{}).get("fixture") for k in DEPS[kind]):metadata["fixture"]=True
            for dep in DEPS[kind]:
                if self.freshness(state,dep) != "CURRENT": raise Blocked(kind+" 입력이 없거나 STALE: "+dep)
            deps={k:state["artifacts"][k]["identity"] for k in DEPS[kind]}
            version=1+sum(x["kind"]==kind for x in state["history"])
            aid=f"{state['production_id']}-{kind.lower()}-v{version}"
            folder={"ASSET":"ASSETS","FACT":"RESEARCH","VOICE":"AUDIO","MOTION":"PROJECT","CAPTION":"SCRIPT","VIDEO":"PROJECT"}.get(kind,kind)
            dest=self.path/folder/(aid+source.suffix)
            if dest.exists(): raise Blocked("불변 파일 충돌")
            shutil.copyfile(source,dest)
            record={"id":aid,"kind":kind,"version":version,"path":str(dest.relative_to(self.path)),"sha256":file_hash(dest),"dependencies":deps,"settings_hash":digest(state["brief"]["settings"]),"code_hash":code_hash(self.root),"produced_by":author,"created":now(),"metadata":metadata or {}}
            record["identity"]=digest(record)
            write_json(self.path/"PROJECT"/"manifests"/(aid+".json"),record)
            state["artifacts"][kind]=record;state["history"].append(record);state["generation"]+=1
            if record["metadata"].get("fixture"):register(dest,self.root)
            self.save(state);self.log("ARTIFACT",record)
            return record
    def freshness(self,state,kind,seen=None):
        a=state["artifacts"].get(kind)
        if not a: return "MISSING"
        if digest({k:v for k,v in a.items() if k!="identity"})!=a.get("identity"):return "STALE"
        manifest=self.path/"PROJECT/manifests"/(a["id"]+".json")
        if not manifest.is_file() or json.loads(manifest.read_text())!=a:return "STALE"
        seen=(seen or set())|{kind}
        p=self.path/a["path"]
        if not p.resolve().is_relative_to(self.path.resolve()): return "STALE"
        if not p.is_file() or file_hash(p)!=a["sha256"]: return "STALE"
        if a["settings_hash"]!=digest(state["brief"]["settings"]) or a["code_hash"]!=code_hash(self.root): return "STALE"
        for dep,identity in a["dependencies"].items():
            if dep in seen or state["artifacts"].get(dep,{}).get("identity")!=identity or self.freshness(state,dep,seen)!="CURRENT": return "STALE"
        return "CURRENT"
    def snapshot(self,state):
        return digest({"artifacts":{k:v["identity"] for k,v in state["artifacts"].items()},"settings":state["brief"]["settings"],"brief":state["brief"],"code":code_hash(self.root),"generation":state["generation"]})
    def fail(self,stage,problem,hypothesis,fix="미적용",enforce_new_hypothesis=True):
        with self.lock():
            state=self.load(); prior=[]
            for p in (self.path/"FAIL").glob("*.json"):
                x=json.loads(p.read_text())
                if x["stage"]==stage and x["problem"]==problem: prior.append(x)
            if enforce_new_hypothesis and any(x["next_hypothesis"]==hypothesis for x in prior): raise Blocked("동일 실패·가설 반복입니다. 방법을 바꾸세요")
            report={"id":uuid.uuid4().hex,"at":now(),"snapshot":self.snapshot(state),"stage":stage,"problem":problem,"cause":"추가 진단 필요","fix":fix,"lesson":"관련 레이어와 의존 단계만 복구","next_hypothesis":hypothesis}
            write_json(self.path/"FAIL"/(report["id"]+".json"),report);state["generation"]+=1;self.save(state);self.log("FAIL",report);return report
