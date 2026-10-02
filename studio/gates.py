"""현재 버전 QA·실제 관찰·독립 검수 및 출고 차단."""
import json, os, shutil, uuid
from .model import Blocked, GATES, KINDS, PACKAGES, digest, file_hash
from .store import now, write_json
CHECKS={
 "Research":("observation_separated","hook_curiosity_shot_analysis","sources"),
 "Fact":("claims_verified","all_rights_cleared","tts_license"),
 "Script":("core_sentence_question","event_arc","scene_hook_first3s","payoff"),
 "Shot":("complete_fields","one_message","new_information","transition_reason"),
 "Asset":("layer_separation","anatomy_text_crop_perspective","motion_space","style"),
 "Motion":("event_reason","no_repeated_zoom_whoosh","space_occlusion"),
 "Caption":("short_1_2_lines","mobile_readability","text_nonredundancy","sync"),
 "Audio":("voice_candidates_listened","pronunciation_emotion_fatigue","stems","license","mix"),
 "Technical QA":("decode","dimensions_duration","sync","no_missing_frames","audio_clipping"),
 "Viewer QA":("first3s","new_information_after5s","no_word_visual_repeat","not_caption_only","visual_focus","payoff")}

def template(store,gate,reviewer):
    state=store.load()
    return {"gate":gate,"snapshot":store.snapshot(state),"status":"BLOCKED","reviewer":reviewer,"checks":{k:False for k in CHECKS[gate]},"evidence":[],"observed_video":False,"observed_audio":False,"notes":"실제 확인 후 작성; fixture는 완성 콘텐츠가 아닙니다"}

def submit(store,report):
    if report.get("gate") not in GATES: raise Blocked("QA 종류 오류")
    if report.get("status") not in ("PASS","FAIL","BLOCKED"): raise Blocked("QA 판정 오류")
    gate=report["gate"]
    with store.lock():
        state=store.load()
        if report.get("snapshot")!=store.snapshot(state): raise Blocked("STALE QA: 현재 제작 해시와 다릅니다")
        if not report.get("reviewer"): raise Blocked("검수자 ID가 필요합니다")
        if report["status"]=="PASS":
            if state["mode"]=="fixture" or any(a.get("metadata",{}).get("fixture") for a in state["artifacts"].values()): raise Blocked("기술 fixture의 품질 PASS 금지")
            if set(report.get("checks",{}))!=set(CHECKS[gate]) or not all(v is True for v in report["checks"].values()): raise Blocked("모든 필수 검수 항목이 정확히 True여야 합니다")
            if not report.get("evidence") or not all(isinstance(x,str) and x.strip() for x in report["evidence"]): raise Blocked("검수 근거가 필요합니다")
            for k in KINDS:
                if store.freshness(state,k)!="CURRENT": raise Blocked("출고용 QA의 입력 전체가 현재여야 합니다: "+k)
            if gate in ("Technical QA","Viewer QA"):
                authors={v["produced_by"] for v in state["artifacts"].values()}
                if report["reviewer"] in authors: raise Blocked("독립 QA 검수자가 제작자와 같습니다")
                if report.get("observed_video") is not True or report.get("observed_audio") is not True: raise Blocked("실제 영상·음성 확인 없이는 PASS 금지")
        saved={**report,"id":uuid.uuid4().hex,"at":now()}
        write_json(store.path/"QA"/(saved["id"]+".json"),saved)
        state["qa"][gate]=saved;store.save(state);store.log("QA",saved)
    if report["status"]=="FAIL": store.fail(gate,report.get("notes") or "검수 실패","검수 결과에 따라 레이어 식별",enforce_new_hypothesis=False)
    return saved

def release_reasons(store,state):
    reasons=[]
    if state["mode"]!="production": reasons.append("기술시험 fixture의 FINAL 저장 금지")
    if any(a.get("metadata",{}).get("fixture") for a in state["artifacts"].values()): reasons.append("fixture 산출물을 본편으로 재분류할 수 없습니다")
    for kind in KINDS:
        status=store.freshness(state,kind)
        if status!="CURRENT": reasons.append(kind+": "+status)
    snap=store.snapshot(state)
    for gate in GATES:
        qa=state["qa"].get(gate)
        if not qa: reasons.append(gate+": MISSING")
        elif qa["snapshot"]!=snap: reasons.append(gate+": STALE")
        elif qa["status"]!="PASS": reasons.append(gate+": "+qa["status"])
        else:
            path=store.path/"QA"/(str(qa.get("id",""))+".json")
            if not path.resolve().is_relative_to((store.path/"QA").resolve()) or not path.is_file() or json.loads(path.read_text())!=qa:
                reasons.append(gate+": QA 원장 변조/누락")
            if set(qa.get("checks",{}))!=set(CHECKS[gate]) or not all(v is True for v in qa.get("checks",{}).values()) or not qa.get("evidence"):
                reasons.append(gate+": 검수 근거/항목 오류")
            if gate in ("Technical QA","Viewer QA") and (qa.get("observed_video") is not True or qa.get("observed_audio") is not True or qa.get("reviewer") in {x["produced_by"] for x in state["artifacts"].values()}):
                reasons.append(gate+": 관찰/독립 검수 조건 오류")
    return reasons

def verify_package(store,state,target):
    if target.is_symlink():raise Blocked("FINAL 심볼릭 링크 금지")
    manifest_path=target/"release.json"
    if not manifest_path.is_file():raise Blocked("FINAL 출고 원장 누락")
    manifest=json.loads(manifest_path.read_text())
    if manifest.get("snapshot")!=store.snapshot(state):raise Blocked("FINAL 스냅샷 불일치")
    saved=state.get("releases",{}).get(manifest["snapshot"])
    if not saved or saved["manifest_hash"]!=file_hash(manifest_path):raise Blocked("FINAL 원장 무결성 불일치")
    expected=set(manifest["files"])
    actual={str(p.relative_to(target)) for p in target.rglob("*") if p.is_file() and p!=manifest_path}
    if expected!=actual:raise Blocked("FINAL 패키지 파일 목록 불일치")
    for rel,sha in manifest["files"].items():
        p=target/rel
        if p.is_symlink() or not p.resolve().is_relative_to(target.resolve()) or not p.is_file() or file_hash(p)!=sha:raise Blocked("FINAL 파일 무결성 불일치: "+rel)
    return str(target)

def release(store):
    with store.lock():
        state=store.load();reasons=release_reasons(store,state)
        if reasons: raise Blocked("FINAL 차단: "+"; ".join(reasons))
        snap=store.snapshot(state); target=store.path/"FINAL"/snap
        if target.exists(): return verify_package(store,state,target)
        temp=store.path/"FINAL"/(".pending-"+uuid.uuid4().hex);temp.mkdir()
        try:
            for folder in PACKAGES:
                if folder=="FINAL": continue
                shutil.copytree(store.path/folder,temp/folder)
            video=state["artifacts"]["VIDEO"]
            shutil.copyfile(store.path/video["path"],temp/"video.mp4")
            if file_hash(temp/"video.mp4")!=video["sha256"]: raise Blocked("복사 후 영상 해시 오류")
            write_json(temp/"release.json",{"production_id":state["production_id"],"snapshot":snap,"at":now(),"files":{str(p.relative_to(temp)):file_hash(p) for p in temp.rglob("*") if p.is_file()}})
            for kind,a in state["artifacts"].items():
                if file_hash(temp/a["path"])!=a["sha256"]:raise Blocked("FINAL 산출물 복사 해시 불일치: "+kind)
            os.replace(temp,target)
            state.setdefault("releases",{})[snap]={"manifest_hash":file_hash(target/"release.json")};store.save(state)
            verify_package(store,state,target);store.log("RELEASE",{"snapshot":snap,"path":str(target)})
        except BaseException:
            # 실패한 패키지도 삭제하지 않는다.
            raise
        return str(target)
