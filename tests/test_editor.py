import json, tempfile, unittest
from pathlib import Path
from studio.editor import captions,export_srt,mix_stems
from studio.model import Blocked
from studio.adapters import run
class EditorTests(unittest.TestCase):
 def items(self):return [{"text":"기술 시험","startMs":0,"endMs":1000,"timestampMs":None,"confidence":None}]
 def test_srt_export(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/"test.srt";export_srt(self.items(),1,p);self.assertIn("00:00:00,000 --> 00:00:01,000",p.read_text())
 def test_caption_time_overlap(self):
  items=self.items();items.append({**items[0],"startMs":500,"endMs":1500})
  with self.assertRaises(Blocked):captions(items,2)
 def test_caption_mobile_line_count(self):
  items=self.items();items[0]["text"]="첫줄\n둘째줄\n셋째줄"
  with self.assertRaises(Blocked):captions(items,1)
 def test_caption_duplicate_text(self):
  with self.assertRaises(Blocked):captions(self.items(),1,{"TITLE":["기술시험"]})
 def test_audio_stem_mix_actual(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);run(["ffmpeg","-v","error","-f","lavfi","-i","sine=frequency=440:duration=0.3",str(base/"voice.wav")])
   run(["ffmpeg","-v","error","-f","lavfi","-i","sine=frequency=800:duration=0.3",str(base/"impact.wav")])
   manifest=base/"mix.json";manifest.write_text(json.dumps({"stems":[{"type":"VOICE","file":"voice.wav"},{"type":"IMPACT","file":"impact.wav","gain":0.2}]}))
   result=mix_stems(manifest,base/"mix.wav");self.assertEqual(result["execution"],"SUCCESS");self.assertTrue((base/"voice.wav").exists());self.assertTrue((base/"impact.wav").exists())

class LayerTests(unittest.TestCase):
 def test_layer_composition_actual(self):
  from studio.adapters import compose_layers
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp)
   run(["ffmpeg","-v","error","-f","lavfi","-i","color=c=green:s=64x96:d=0.1","-frames:v","1",str(base/"background.png")])
   run(["ffmpeg","-v","error","-f","lavfi","-i","color=c=red:s=16x16:d=0.1","-frames:v","1",str(base/"subject.png")])
   p=base/"layers.json";p.write_text(json.dumps({"width":64,"height":96,"duration":0.2,"layers":[{"type":"BACKGROUND","file":"background.png"},{"type":"SUBJECT","file":"subject.png","x":10,"y":10}]}))
   result=compose_layers(p,base/"layers.mp4");self.assertTrue((base/"layers.mp4").exists());self.assertEqual(result["streams"][0]["width"],64)
