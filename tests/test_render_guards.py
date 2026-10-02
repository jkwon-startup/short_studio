"""렌더 방어: 샷보다 짧은 클립은 조용히 넘어가지 않고 막는다. 글자 레이어 캐시는 문구 전체로 구분한다."""
import importlib.util, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def load():
    try:
        import PIL  # noqa: F401
    except ImportError:
        return None
    spec = importlib.util.spec_from_file_location("ap_guards", ROOT / "scripts/claude_adapters/autopilot.py")
    mod = importlib.util.module_from_spec(spec); sys.path.insert(0, str(ROOT / "scripts/claude_adapters")); spec.loader.exec_module(mod)
    return mod


def make_clip(path, seconds):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=s=320x568:r=30:d={seconds}", "-pix_fmt", "yuv420p", str(path)], check=True)


class RenderGuardTests(unittest.TestCase):
    def setUp(self):
        self.ap = load()
        if self.ap is None: self.skipTest("Pillow 없음")
        self.tmp = Path(tempfile.mkdtemp())

    def renderer(self):
        r = object.__new__(self.ap.Renderer); r.L = self.tmp / "layers"; r.S = self.tmp / "segments"
        r.L.mkdir(); r.S.mkdir(); return r

    def test_layer_key_uses_whole_text(self):
        a = "혼자서도 앱 하나쯤은 충분히 만들 수 있습니다 오늘 바로 시작해 보세요"
        b = "혼자서도 앱 하나쯤은 충분히 만들 수 있습니다 오늘 바로 그만두세요"
        self.assertNotEqual(self.ap.layer_key("cap", a), self.ap.layer_key("cap", b))
        self.assertNotEqual(self.ap.layer_key("cap", a, "top"), self.ap.layer_key("cap", a, ""))
        self.assertEqual(self.ap.layer_key("cap", a), self.ap.layer_key("cap", a))

    def test_captions_and_tags_with_same_prefix_get_own_png(self):
        if not Path(self.ap.F_BOLD).exists(): self.skipTest("Gmarket Sans 없음")
        r = self.renderer(); head = "가나다라마바사아자차카타파하가나다라마바사아자차카타파하"
        p1, p2 = r.caption({"text": head + " 첫째"}), r.caption({"text": head + " 둘째"})
        self.assertNotEqual(p1, p2)
        self.assertNotEqual(p1.read_bytes(), p2.read_bytes())
        self.assertNotEqual(r.caption({"text": "같은 문구", "sub": "보조 하나"}), r.caption({"text": "같은 문구", "sub": "보조 둘"}))
        self.assertEqual(r.caption({"text": head + " 첫째"}), p1)
        t1, t2 = r.tag("예시"), r.tag("광고")
        self.assertNotEqual(t1, t2)
        self.assertNotEqual(t1.read_bytes(), t2.read_bytes())

    @unittest.skipUnless(HAS_FFMPEG, "FFmpeg 없음: 미실행")
    def test_clip_shorter_than_shot_is_blocked(self):
        r = self.renderer(); clip = self.tmp / "CLIP-01.mp4"; make_clip(clip, 2)
        with self.assertRaises(self.ap.Blocked) as e:
            r.seg_clip("S01", clip, 3.0, 0)
        self.assertIn("CLIP-01", str(e.exception))
        with self.assertRaises(self.ap.Blocked):
            r.seg_clip("S01", clip, 1.5, 1.0)  # 시작 위치 때문에 모자람
        out = r.seg_clip("S01", clip, 2.0, 0)
        self.assertAlmostEqual(self.ap.media_duration(out), 2.0, delta=0.05)

    @unittest.skipUnless(HAS_FFMPEG, "FFmpeg 없음: 미실행")
    def test_final_length_mismatch_is_blocked(self):
        clip = self.tmp / "draft.mp4"; make_clip(clip, 2)
        self.ap.require_duration(clip, 2.0, "최종 영상")
        with self.assertRaises(self.ap.Blocked):
            self.ap.require_duration(clip, 3.0, "최종 영상")


if __name__ == "__main__":
    unittest.main()
