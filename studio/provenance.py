"""기술시험 출처의 해시 추적. 복사·관리되는 변환·실패 잔여물을 보존한다."""
import contextlib, fcntl, hashlib, json, os, uuid, zipfile
from pathlib import Path
from .model import file_hash

def workspace(path, root=None):
    if root is not None:return Path(root).resolve()
    path=Path(path).resolve(); project=Path(__file__).resolve().parent.parent
    if path.is_relative_to(project):return project
    for p in path.parents:
        if p.name=="runs":return p.parent
    return path if path.is_dir() else path.parent

def index(root):
    p=Path(root)/"runs/fixture-provenance.json"
    return json.loads(p.read_text()) if p.exists() else {"hashes":{}}

def mark(path):
    p=Path(path);marker=p/".fixture.json" if p.is_dir() else p.with_name(p.name+".fixture.json")
    marker.write_text(json.dumps({"fixture":True,"quality":"NOT_REVIEWED"})+"\n")

def register(path,root=None):
    path=Path(path);root=workspace(path,root);folder=root/"runs";folder.mkdir(parents=True,exist_ok=True)
    files=[p for p in path.rglob("*") if p.is_file() and p.name!=".fixture.json"] if path.is_dir() else ([path] if path.is_file() else [])
    if not files:return
    with (folder/"fixture-provenance.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        data=index(root)
        for p in files:data["hashes"][file_hash(p)]={"fixture":True,"origin":str(p.resolve())}
        dest=folder/"fixture-provenance.json";temp=folder/(".provenance-"+uuid.uuid4().hex+".tmp")
        temp.write_text(json.dumps(data,ensure_ascii=False,indent=2));os.replace(temp,dest)

def is_fixture(path,root=None):
    path=Path(path).resolve();root=workspace(path,root)
    if path.with_name(path.name+".fixture.json").exists():return True
    for p in path.parents:
        if (p/".fixture.json").exists():return True
        if p==root:break
    known=index(root)["hashes"]
    if path.is_file() and file_hash(path) in known:return True
    if path.suffix==".json":
        try:
            data=json.loads(path.read_text())
            if isinstance(data,dict) and data.get("fixture") is True:return True
        except (ValueError,UnicodeError):pass
    if path.is_file() and zipfile.is_zipfile(path):
        # 추출하지 않고 번들 안의 원본 바이트를 확인한다.
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.is_dir():continue
                if info.filename.endswith(".fixture.json"):return True
                h=hashlib.sha256()
                with z.open(info) as f:
                    while chunk:=f.read(1024*1024):h.update(chunk)
                if h.hexdigest() in known:return True
    return False
