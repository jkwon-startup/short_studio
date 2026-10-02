"""재개·캐시·기술시험·부분 복구. 상업 콘텐츠를 자동 승인하지 않는다."""
import json
from pathlib import Path
from .model import KINDS, GATES, DEPS, Blocked, descendants, digest
from .store import Store, write_json
from .gates import release_reasons
from .adapters import fixture_video, technical_check

def status(store):
    state=store.load();snap=store.snapshot(state)
    return {"production_id":state["production_id"],"mode":state["mode"],"snapshot":snap,"artifacts":{k:store.freshness(state,k) for k in KINDS},"qa":{g:("MISSING" if g not in state["qa"] else "STALE" if state["qa"][g]["snapshot"]!=snap else state["qa"][g]["status"]) for g in GATES},"final_blockers":release_reasons(store,state)}

def resume(store):
    state=store.load();pending=[];reusable=[]
    for k in KINDS:
        if store.freshness(state,k)=="CURRENT": reusable.append(k)
        else: pending.append({"stage":k,"inputs":DEPS[k],"ready":all(store.freshness(state,d)=="CURRENT" for d in DEPS[k]),"status":store.freshness(state,k),"adapter":"MANUAL_OR_AUTHORIZED_AGENT"})
    return {"reusable":reusable,"pending":pending,"qa":status(store)["qa"],"execution":"PLAN_ONLY_NO_IMPLICIT_MODEL_CALL"}

def recovery(store,stage,problem,hypothesis):
    if stage not in KINDS: raise Blocked("복구 단계 오류")
    report=store.fail(stage,problem,hypothesis,fix="부분 복구 계획 생성; 아직 수정하지 않음")
    return {"failure_id":report["id"],"invalidate_on_change":sorted(descendants(stage)),"preserve":sorted(set(KINDS)-descendants(stage)),"next_hypothesis":hypothesis,"action":"레이어 수정 → ingest → 재렌더 → WATCH → 현재 스냅샷 QA"}

def fixture(root,production_id):
    store=Store(root,production_id)
    if store.state_path.exists(): raise Blocked("기술시험 ID가 존재합니다. 새로운 ID를 사용하세요")
    config=json.loads((Path(root)/"config"/"studio.json").read_text())
    brief={"production_id":production_id,"mode":"fixture","brand":"TECHNICAL_TEST","core_sentence":"기술 시험 신호","viewer_question":"완성 콘텐츠 아님","duration":3,"settings":config["settings"]}
    store.create(brief)
    source=store.path/"PROJECT"/"fixture-input.json"
    for kind in KINDS:
        if kind=="VIDEO": continue
        write_json(source,{"kind":kind,"fixture":True,"quality":"NOT_REVIEWED","description":"제작 파이프라인 기술시험용 의존성 표식. 실제 에셋·음성·연구 아님"})
        store.artifact(kind,source,"fixture-generator",{"fixture":True})
    output=store.path/"PROJECT"/"fixture.mp4"
    try:
        result=fixture_video(output)
        store.artifact("VIDEO",output,"fixture-generator",{"fixture":True})
        check=technical_check(output,3)
        write_json(store.path/"QA"/"technical-execution.json",check)
        store.log("TECHNICAL_EXECUTION",{"execution":"SUCCESS","quality":"NOT_REVIEWED"})
    except Exception as exc:
        store.fail("VIDEO",str(exc),"도구 로그와 입력 형식을 확인한 후 다른 방식으로 재시도")
        raise
    return {"video":str(output),"metadata":result,"status":status(store)}

def agent_plan(root,role,store=None):
    path=Path(root)/".codex"/"agents"/(role+".toml")
    if role not in {p.stem for p in (Path(root)/".codex"/"agents").glob("*.toml")}: raise Blocked("등록 역할 없음")
    import tomllib
    agent=tomllib.loads(path.read_text())
    prompt=agent["developer_instructions"]
    config_path=Path(root)/"config"/"studio.json"
    defaults=json.loads(config_path.read_text()).get("creative_direction",{}) if config_path.exists() else {}
    creative_direction=dict(defaults)
    if store:
        brief=store.load()["brief"]
        creative_direction={} if brief["mode"]=="fixture" else {**defaults,**brief.get("creative_direction",{})}
    if creative_direction:
        prompt += "\n광고 창작 방향(계획 인계; 비용·도구 권한·품질 PASS 아님):\n"+json.dumps(creative_direction,ensure_ascii=False)
    if store: prompt += "\n현재 파일 인계 컨텍스트:\n"+json.dumps(resume(store),ensure_ascii=False)+"\n제작 원장: "+str(store.state_path)
    return {"role":role,"native_definition":str(path),"prompt":prompt,"creative_direction":creative_direction,"execution":"PLAN_ONLY","manual_command":["codex","-C",str(root)],"note":"프로젝트를 로컬 Codex에서 열고 이 이름으로 위임. 파일 존재만으로 무인 자율 호출되지는 않음. 모델 호출 비용·권한 별도 승인. read-only 역할의 산출물 저장은 Producer가 담당."}
