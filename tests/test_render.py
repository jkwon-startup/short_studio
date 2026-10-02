"""실제 FFmpeg 렌더·decode 시험. 영상 창작 품질 PASS로 사용하지 않는다."""
import json, shutil, tempfile, unittest
from pathlib import Path
from studio.adapters import fixture_video, technical_check, say_candidate, blender_fixture
from studio.model import Blocked
@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg 없음: 미실행")
class RenderTests(unittest.TestCase):
    def test_render_decode_av_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"technical.mp4";m=fixture_video(p,3);check=technical_check(p,3)
            self.assertEqual(check["errors"],[]);self.assertEqual(check["quality"],"NOT_REVIEWED")
            self.assertEqual({s["codec_type"] for s in m["streams"]},{"video","audio"})
            self.assertEqual(next(s for s in m["streams"] if s["codec_type"]=="video")["width"],270)
    def test_tts_existing_output_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"voice.aiff";p.write_text("original")
            with self.assertRaises(Blocked):say_candidate("시험","Yuna",p)
            self.assertEqual(p.read_text(),"original")
    def test_blender_nonempty_output_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/"fixture.blend").write_text("original")
            with self.assertRaises(Blocked):blender_fixture(p,p,1)
            self.assertEqual((p/"fixture.blend").read_text(),"original")
    def test_partial_failed_fixture_keeps_marker(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"partial.mp4"
            def partial(*args,**kwargs):p.write_bytes(b"partial");raise Blocked("injected failure")
            with patch("studio.adapters.run",side_effect=partial):
                with self.assertRaises(Blocked):fixture_video(p,3)
            self.assertTrue(p.with_name(p.name+".fixture.json").exists())
class DeliverySpecTests(unittest.TestCase):
    def test_requested_aspect_and_audio_optional_do_not_imply_quality_pass(self):
        from unittest.mock import patch
        for width,height,ratio in ((1080,1080,"1:1"),(1920,1080,"16:9"),(1080,1920,"9:16")):
            with self.subTest(ratio=ratio):
                meta={"streams":[{"codec_type":"video","width":width,"height":height}],"format":{"duration":"3"}}
                with patch("studio.adapters.probe",return_value=meta),patch("studio.adapters.run"):
                    result=technical_check("declared.mp4",3,{"aspect_ratio":ratio,"audio_required":False})
                    self.assertEqual(result["errors"],[])
                    self.assertEqual(result["quality"],"NOT_REVIEWED")
                    self.assertIn("영상·오디오 스트림 누락",technical_check("declared.mp4",3)["errors"])

    def test_wrong_requested_ratio_and_invalid_spec_are_not_accepted(self):
        from unittest.mock import patch
        from studio.model import Blocked
        meta={"streams":[{"codec_type":"video","width":1920,"height":1080}],"format":{"duration":"3"}}
        with patch("studio.adapters.probe",return_value=meta),patch("studio.adapters.run"):
            self.assertIn("납품 비율 불일치",technical_check("declared.mp4",3,{"aspect_ratio":"9:16","audio_required":False})["errors"])
            with self.assertRaises(Blocked):technical_check("declared.mp4",3,{"audio_required":"false"})
            with self.assertRaises(Blocked):technical_check("declared.mp4",3,{"aspect_ratio":"4:3"})

if __name__=="__main__":unittest.main()
