"""전체 구현 전에 실행하는 최소 환경·형식·핵심 로직 검증."""
import hashlib, json, shutil, subprocess, unittest
class Preflight(unittest.TestCase):
    def test_local_tool_connection(self):
        for tool in ("ffmpeg", "ffprobe", "python3", "node"):
            self.assertIsNotNone(shutil.which(tool))
        result=subprocess.run(["ffprobe", "-v", "error", "-f", "lavfi", "-i", "color=size=16x16:duration=0.1", "-show_streams", "-of", "json"],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(result.stdout)["streams"][0]["codec_type"], "video")
    def test_expected_format(self):
        sample={"production_id":"fixture", "version":1, "status":"BLOCKED"}
        self.assertEqual(json.loads(json.dumps(sample)),sample)
    def test_dependency_hash(self):
        digest=lambda s: hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
        self.assertNotEqual(digest({"script":"이전"}),digest({"script":"수정"}))
if __name__=="__main__": unittest.main(verbosity=2)
