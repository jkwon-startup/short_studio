"""광고 기본값/사용자 방향의 역할 인계와 기존 제작 호환성 검증."""
import copy, json, shutil, tempfile, unittest
from pathlib import Path
from studio import pipeline
from studio.store import Store

ROOT=Path(__file__).resolve().parents[1]

class CreativeRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'.codex/agents',self.root/'.codex/agents')
        (self.root/'config').mkdir()
        self.config=json.loads((ROOT/'config/studio.json').read_text())
        self.save_config()

    def tearDown(self):
        self.tmp.cleanup()

    def save_config(self):
        (self.root/'config/studio.json').write_text(json.dumps(self.config))

    def production(self,mode='production',direction=None):
        brief={'production_id':'routing-test','mode':mode,'brand':'ExampleBrand',
               'core_sentence':'부모가 먼저 AI를 배우는 교육',
               'viewer_question':'아이 질문에 어떻게 답할까?',
               'duration':30,'settings':copy.deepcopy(self.config['settings'])}
        if direction is not None:brief['creative_direction']=direction
        store=Store(self.root,'routing-test');store.create(brief)
        return store

    def test_all_roles_receive_default_without_generation(self):
        for role_file in (self.root/'.codex/agents').glob('*.toml'):
            plan=pipeline.agent_plan(self.root,role_file.stem)
            self.assertEqual(plan['creative_direction']['mode'],'photoreal_ad')
            self.assertEqual(plan['execution'],'PLAN_ONLY')
            self.assertIn(json.dumps(plan['creative_direction'],ensure_ascii=False),plan['prompt'])
        self.assertFalse((self.root/'runs').exists())

    def test_explicit_motion_request_wins_and_does_not_change_approval(self):
        requested={'mode':'motion_graphics','selection_source':'USER_REQUEST',
                   'reason':'사용자가 모션그래픽 광고를 명시 요청'}
        store=self.production(direction=requested)
        before=store.state_path.read_bytes()
        plan=pipeline.agent_plan(self.root,'motion',store)
        self.assertEqual(plan['creative_direction']['mode'],'motion_graphics')
        self.assertEqual(plan['creative_direction']['selection_source'],'USER_REQUEST')
        self.assertEqual(plan['creative_direction']['reason'],requested['reason'])
        self.assertEqual(store.state_path.read_bytes(),before)
        self.assertFalse(self.config['cost_approval'])
        self.assertFalse(self.config['quality_auto_pass'])

    def test_fixture_is_not_reclassified_as_an_ad(self):
        store=self.production(mode='fixture')
        self.assertEqual(pipeline.agent_plan(self.root,'producer',store)['creative_direction'],{})
        self.assertEqual(store.load()['mode'],'fixture')

    def test_changed_ad_policy_invalidates_cache_but_preserves_output(self):
        policy=self.root/'docs/advertising-creative-standard.md'
        policy.parent.mkdir();policy.write_text('Original creative policy')
        store=self.production()
        source=self.root/'research.json';source.write_text('{"source":"user brief"}')
        artifact=store.artifact('RESEARCH',source,'producer')
        self.assertEqual(store.freshness(store.load(),'RESEARCH'),'CURRENT')
        policy.write_text('Revised creative policy')
        self.assertEqual(store.freshness(store.load(),'RESEARCH'),'STALE')
        self.assertEqual((store.path/artifact['path']).read_bytes(),source.read_bytes())

    def test_each_motion_reference_invalidates_old_cache_without_rewriting_outputs(self):
        store=self.production()
        source=self.root/'research.json';source.write_text('{"source":"user brief"}')
        for name in ('motion-genres.md','motion-delivery-spec.md','motion-review-protocol.md'):
            with self.subTest(policy=name):
                policy=self.root/'docs'/name
                policy.parent.mkdir(exist_ok=True);policy.write_text('Original policy')
                artifact=store.artifact('RESEARCH',source,'producer')
                self.assertEqual(store.freshness(store.load(),'RESEARCH'),'CURRENT')
                state_before=store.state_path.read_bytes()
                policy.write_text('Revised policy')
                self.assertEqual(store.freshness(store.load(),'RESEARCH'),'STALE')
                self.assertEqual(store.state_path.read_bytes(),state_before)
                self.assertEqual((store.path/artifact['path']).read_bytes(),source.read_bytes())

    def test_nested_adapter_change_invalidates_cached_inputs(self):
        adapter=self.root/'scripts/claude_adapters/autopilot.py'
        adapter.parent.mkdir(parents=True);adapter.write_text('# Original adapter')
        store=self.production()
        source=self.root/'research.json';source.write_text('{"source":"user brief"}')
        store.artifact('RESEARCH',source,'producer')
        self.assertEqual(store.freshness(store.load(),'RESEARCH'),'CURRENT')
        adapter.write_text('# Changed render/mix behavior')
        self.assertEqual(store.freshness(store.load(),'RESEARCH'),'STALE')

    def test_legacy_project_without_new_defaults_still_plans(self):
        self.config.pop('creative_direction',None);self.save_config()
        store=self.production()
        plan=pipeline.agent_plan(self.root,'producer',store)
        self.assertEqual(plan['creative_direction'],{})
        self.assertEqual(plan['execution'],'PLAN_ONLY')
        self.assertEqual(store.load()['brief']['brand'],'ExampleBrand')

if __name__=='__main__':unittest.main()
