"""독립 검토에서 재현한 우회 경로의 회귀 테스트."""
import json, shutil, subprocess, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
from studio import adapters, editor, gates, provenance
from studio.model import Blocked, KINDS, GATES
from studio.store import Store, write_json
ROOT=Path(__file__).resolve().parents[1]
class HardeningTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root,"hardening")
  settings=json.loads((ROOT/"config/studio.json").read_text())["settings"]
  self.store.create({"production_id":"hardening","mode":"production","brand":"UNIT","core_sentence":"시험","viewer_question":"왜?","duration":3,"settings":settings})
  self.src=self.root/"input.json";write_json(self.src,{"test":"단위 계약 시험"})
 def tearDown(self):self.tmp.cleanup()
 def fill(self):
  for k in KINDS:self.store.artifact(k,self.src,"maker")
 def report(self,gate,status="PASS"):
  r=gates.template(self.store,gate,"independent");r.update(status=status,checks={k:True for k in gates.CHECKS[gate]},evidence=["UNIT SIMULATION"],observed_video=True,observed_audio=True,notes="같은 관찰 문제");return r
 def pass_all(self):
  for g in GATES:gates.submit(self.store,self.report(g))
 def test_unregistered_fixture_copy_detected_without_sidecar(self):
  out=self.root/"runs/pilot";out.mkdir(parents=True);p=out/"candidate.wav";p.write_bytes(b"unregistered-technical-audio")
  provenance.mark(p);provenance.register(p,self.root)
  copied=self.root/"copy.wav";shutil.copyfile(p,copied)
  result=self.store.artifact("RESEARCH",copied,"maker")
  self.assertTrue(result["metadata"]["fixture"])
 def test_unregistered_fixture_zip_bundle_detected(self):
  p=self.root/"raw.wav";p.write_bytes(b"technical-only");provenance.mark(p);provenance.register(p,self.root)
  bundle=self.root/"assets.zip"
  with zipfile.ZipFile(bundle,"w") as z:z.write(p,"renamed.wav")
  self.assertTrue(self.store.artifact("RESEARCH",bundle,"maker")["metadata"]["fixture"])
 def test_partial_failed_copy_detected(self):
  out=self.root/"runs/partial";out.mkdir(parents=True);p=out/"bad.mp4"
  def fail(*args,**kwargs):p.write_bytes(b"partial-not-a-real-movie");raise Blocked("injected")
  with patch("studio.adapters.run",side_effect=fail):
   with self.assertRaises(Blocked):adapters.fixture_video(p)
  copy=self.root/"partial-copy.mp4";shutil.copyfile(p,copy)
  self.assertTrue(self.store.artifact("RESEARCH",copy,"maker")["metadata"]["fixture"])
 def test_repeat_qa_fail_preserved_and_old_pass_stale(self):
  self.fill();gates.submit(self.store,self.report("Viewer QA","FAIL"));self.pass_all()
  before=self.store.load()["generation"]
  gates.submit(self.store,self.report("Viewer QA","FAIL"))
  self.assertGreater(self.store.load()["generation"],before)
  self.assertEqual(len(list((self.store.path/"FAIL").glob("*.json"))),2)
  gates.submit(self.store,self.report("Viewer QA"))
  reasons=gates.release_reasons(self.store,self.store.load());self.assertTrue(any("STALE" in x for x in reasons))
  with self.assertRaises(Blocked):gates.release(self.store)
 def test_existing_final_video_corruption_blocked(self):
  self.fill();self.pass_all();target=Path(gates.release(self.store));(target/"video.mp4").write_bytes(b"corrupted")
  with self.assertRaises(Blocked):gates.release(self.store)
 def test_existing_final_manifest_corruption_blocked(self):
  self.fill();self.pass_all();target=Path(gates.release(self.store));(target/"release.json").write_text("{}")
  with self.assertRaises(Blocked):gates.release(self.store)
 def test_compose_fixture_propagation_actual(self):
  folder=self.root/"runs/pilot-images";folder.mkdir(parents=True)
  p=folder/"background.png";adapters.run(["ffmpeg","-v","error","-f","lavfi","-i","color=c=green:s=32x48:d=0.1","-frames:v","1",str(p)])
  provenance.mark(p);provenance.register(p,self.root)
  manifest=self.root/"layers.json";write_json(manifest,{"width":32,"height":48,"duration":0.2,"layers":[{"type":"BACKGROUND","file":"runs/pilot-images/background.png"}]})
  output=self.root/"converted.mp4";adapters.compose_layers(manifest,output)
  copy=self.root/"copy-converted.mp4";shutil.copyfile(output,copy)
  self.assertTrue(self.store.artifact("RESEARCH",copy,"maker")["metadata"]["fixture"])
 def test_audio_fixture_propagation_actual(self):
  folder=self.root/"runs/pilot-audio";folder.mkdir(parents=True);p=folder/"voice.wav"
  adapters.run(["ffmpeg","-v","error","-f","lavfi","-i","sine=frequency=440:duration=0.2",str(p)])
  provenance.mark(p);provenance.register(p,self.root)
  manifest=self.root/"mix.json";write_json(manifest,{"stems":[{"type":"VOICE","file":"runs/pilot-audio/voice.wav"}]})
  out=self.root/"converted.wav";editor.mix_stems(manifest,out)
  copied=self.root/"copy-converted.wav";shutil.copyfile(out,copied)
  self.assertTrue(self.store.artifact("RESEARCH",copied,"maker")["metadata"]["fixture"])

 def test_artifact_metadata_tamper_detected(self):
  self.fill();state=self.store.load();state["artifacts"]["VIDEO"]["metadata"]={"fixture":False,"forged":True}
  self.assertEqual(self.store.freshness(state,"VIDEO"),"STALE")
 def test_qa_state_tamper_detected(self):
  self.fill();self.pass_all();state=self.store.load();state["qa"]["Viewer QA"]["evidence"]=["changed in raw state"]
  self.store.save(state)
  with self.assertRaises(Blocked):gates.release(self.store)

 def test_external_fixture_input_conversion_uses_project_index(self):
  with tempfile.TemporaryDirectory() as outside:
   external=Path(outside);raw=self.root/"known.png"
   adapters.run(["ffmpeg","-v","error","-f","lavfi","-i","color=c=green:s=32x48:d=0.1","-frames:v","1",str(raw)])
   provenance.mark(raw);provenance.register(raw,self.root)
   copied=external/"external.png";shutil.copyfile(raw,copied)
   manifest=external/"layers.json";write_json(manifest,{"width":32,"height":48,"duration":0.2,"layers":[{"type":"BACKGROUND","file":"external.png"}]})
   output=self.root/"external-converted.mp4";adapters.compose_layers(manifest,output,self.root)
   self.assertTrue(provenance.is_fixture(output,self.root))
 def test_external_fixture_audio_uses_project_index(self):
  with tempfile.TemporaryDirectory() as outside:
   external=Path(outside);raw=self.root/"known.wav"
   adapters.run(["ffmpeg","-v","error","-f","lavfi","-i","sine=frequency=440:duration=0.2",str(raw)])
   provenance.mark(raw);provenance.register(raw,self.root)
   copied=external/"external.wav";shutil.copyfile(raw,copied)
   manifest=external/"mix.json";write_json(manifest,{"stems":[{"type":"VOICE","file":"external.wav"}]})
   output=self.root/"external-mixed.wav";editor.mix_stems(manifest,output,self.root)
   self.assertTrue(provenance.is_fixture(output,self.root))
