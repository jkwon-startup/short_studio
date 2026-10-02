"""출고 계약·버전 무효화·복구 실제 단위 검증. 품질 검수를 모사한 테스트이다."""
import copy, json, tempfile, unittest
from pathlib import Path
from studio.store import Store, write_json
from studio.model import Blocked, KINDS, GATES, digest, descendants, validate_brief, validate_shots
from studio import gates, pipeline
ROOT=Path(__file__).resolve().parents[1]
class StudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.settings=json.loads((ROOT/"config/studio.json").read_text())["settings"]
        self.brief={"production_id":"test-unit","mode":"production","brand":"test","core_sentence":"핵심","viewer_question":"왜?","duration":3,"settings":self.settings}
        self.store=Store(self.root,"test-unit");self.store.create(self.brief)
        self.source=self.root/"input.json";write_json(self.source,{"test":"계약 시험"})
    def tearDown(self): self.tmp.cleanup()
    def fill(self,fixture=False):
        for k in KINDS: self.store.artifact(k,self.source,"maker",{"fixture":fixture})
    def report(self,gate):
        r=gates.template(self.store,gate,"independent-reviewer");r.update(status="PASS",checks={k:True for k in gates.CHECKS[gate]},evidence=["UNIT TEST SIMULATED ATTESTATION: 실제 콘텐츠 검수 아님"],observed_video=True,observed_audio=True);return r
    def pass_all(self):
        for g in GATES:gates.submit(self.store,self.report(g))
    def test_no_overwrite_existing_production(self):
        with self.assertRaises(Blocked): self.store.create(self.brief)
    def test_path_traversal(self):
        with self.assertRaises(Blocked): Store(self.root,"../escape")
    def test_dependencies_missing_blocks_ingest(self):
        with self.assertRaises(Blocked): self.store.artifact("VOICE",self.source,"maker")
    def test_missing_qa_blocks_release(self):
        self.fill()
        with self.assertRaises(Blocked): gates.release(self.store)
    def test_old_voice_caption_blocked_after_script_change(self):
        self.fill();before=self.store.load();self.store.artifact("SCRIPT",self.source,"maker")
        state=self.store.load()
        for k in ("VOICE","CAPTION","SHOT","ASSET","MOTION","AUDIO","VIDEO"):self.assertEqual(self.store.freshness(state,k),"STALE")
        self.assertEqual(self.store.freshness(state,"RESEARCH"),"CURRENT")
        self.assertEqual(self.store.freshness(state,"FACT"),"CURRENT")
        self.assertTrue((self.store.path/before["artifacts"]["VOICE"]["path"]).exists())
    def test_stale_input_cannot_reuse(self):
        self.fill();self.store.artifact("SCRIPT",self.source,"maker")
        with self.assertRaises(Blocked):self.store.artifact("CAPTION",self.source,"maker")
    def test_file_tamper_stale(self):
        self.fill();state=self.store.load();(self.store.path/state["artifacts"]["VOICE"]["path"]).write_text("changed")
        self.assertEqual(self.store.freshness(state,"VOICE"),"STALE")
        self.assertEqual(self.store.freshness(state,"VIDEO"),"STALE")
    def test_setting_invalidation_all_cache_fields(self):
        self.fill();state=self.store.load()
        for field in self.settings:
            changed=copy.deepcopy(state);changed["brief"]["settings"][field]="changed"
            self.assertEqual(self.store.freshness(changed,"VIDEO"),"STALE",field)
    def test_code_and_tool_signature(self):
        self.fill();state=self.store.load();(self.root/"studio").mkdir();(self.root/"studio/new.py").write_text("# changed")
        self.assertEqual(self.store.freshness(state,"VIDEO"),"STALE")
    def test_old_qa_rejected(self):
        self.fill();r=self.report("Script");self.store.artifact("SCRIPT",self.source,"maker")
        with self.assertRaises(Blocked):gates.submit(self.store,r)
    def test_viewer_unwatched_blocked(self):
        self.fill();r=self.report("Viewer QA");r["observed_video"]=False
        with self.assertRaises(Blocked):gates.submit(self.store,r)
    def test_viewer_unheard_blocked(self):
        self.fill();r=self.report("Viewer QA");r["observed_audio"]=False
        with self.assertRaises(Blocked):gates.submit(self.store,r)
    def test_qa_independent_reviewer_required(self):
        self.fill();r=self.report("Technical QA");r["reviewer"]="maker"
        with self.assertRaises(Blocked):gates.submit(self.store,r)
    def test_check_false_and_missing_evidence_blocks(self):
        self.fill();r=self.report("Caption");r["checks"]["sync"]=False
        with self.assertRaises(Blocked):gates.submit(self.store,r)
        r=self.report("Caption");r["evidence"]=[]
        with self.assertRaises(Blocked):gates.submit(self.store,r)
    def test_fixture_no_final_even_all_gate_pass(self):
        self.fill();self.pass_all();state=self.store.load();state["mode"]="fixture";self.store.save(state)
        with self.assertRaises(Blocked):gates.release(self.store)
    def test_fixture_artifact_no_laundering(self):
        self.fill(fixture=True)
        with self.assertRaises(Blocked):gates.submit(self.store,self.report("Script"))
        with self.assertRaises(Blocked):gates.release(self.store)
    def test_all_exact_gates_release_package_and_idempotent(self):
        self.fill();self.pass_all();result=Path(gates.release(self.store));self.assertEqual(str(result),gates.release(self.store))
        for folder in ("PROJECT","ASSETS","AUDIO","SCRIPT","SHOT","RESEARCH","QA","FAIL","LOG"):self.assertTrue((result/folder).is_dir())
        self.assertTrue((result/"release.json").is_file())
    def test_fail_preserved_and_same_hypothesis_blocked(self):
        self.fill();r=self.store.fail("ASSET","잘림","레이어 여백 확대")
        with self.assertRaises(Blocked):self.store.fail("ASSET","잘림","레이어 여백 확대")
        self.store.fail("ASSET","잘림","카메라 구도를 변경")
        self.assertTrue((self.store.path/"FAIL"/(r["id"]+".json")).exists())
        self.assertEqual(len(list((self.store.path/"FAIL").glob("*.json"))),2)
    def test_failure_invalidates_old_pass(self):
        self.fill();self.pass_all();self.store.fail("ASSET","잘림","수정 계획")
        with self.assertRaises(Blocked):gates.release(self.store)
    def test_partial_recovery_preserves_upstream(self):
        self.fill();result=pipeline.recovery(self.store,"ASSET","잘림","전경 위치 수정")
        self.assertIn("RESEARCH",result["preserve"]);self.assertIn("VOICE",result["preserve"]);self.assertIn("VIDEO",result["invalidate_on_change"])
        self.store.artifact("ASSET",self.source,"maker")
        plan=pipeline.resume(self.store);self.assertIn("VOICE",plan["reusable"]);self.assertIn("VIDEO",[x["stage"] for x in plan["pending"]])
    def test_shot_contract(self):
        shots=json.loads((ROOT/"examples/shot.json").read_text());validate_shots(shots,3)
        del shots[0]["event"]
        with self.assertRaises(Blocked):validate_shots(shots,3)
    def test_brief_missing_cache_fields(self):
        for field in self.settings:
            b=copy.deepcopy(self.brief);del b["settings"][field]
            with self.assertRaises(Blocked):validate_brief(b)
    def test_fixture_copy_retains_provenance(self):
        fixture=Store(self.root,"fixture-source");b=copy.deepcopy(self.brief);b.update(production_id="fixture-source",mode="fixture");fixture.create(b)
        a=fixture.artifact("RESEARCH",self.source,"fixture-maker",{"fixture":True})
        copied=self.root/"copied.json";copied.write_bytes((fixture.path/a["path"]).read_bytes())
        result=self.store.artifact("RESEARCH",copied,"maker")
        self.assertTrue(result["metadata"]["fixture"])
    def test_old_failure_hypothesis_cannot_repeat_after_other(self):
        self.store.fail("ASSET","잘림","가설A");self.store.fail("ASSET","잘림","가설B")
        with self.assertRaises(Blocked):self.store.fail("ASSET","잘림","가설A")
    def test_symlink_input_rejected(self):
        link=self.root/"link.json";link.symlink_to(self.source)
        with self.assertRaises(Blocked):self.store.artifact("RESEARCH",link,"maker")
    def test_native_roles_valid(self):
        import tomllib
        roles=list((ROOT/".codex/agents").glob("*.toml"));self.assertEqual(len(roles),14)
        for p in roles:
            d=tomllib.loads(p.read_text());self.assertEqual(d["sandbox_mode"],"read-only");self.assertTrue(d["developer_instructions"]);self.assertNotIn("model",d)
if __name__=="__main__":unittest.main()
