"""화면 비율: brief.format이 출력 크기·Pixverse 비율·기본 길이를 정한다."""
import importlib.util, json, os, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    try:
        import PIL  # noqa: F401
    except ImportError:
        return None
    spec = importlib.util.spec_from_file_location("ap_fmt", ROOT / "scripts/claude_adapters/autopilot.py")
    mod = importlib.util.module_from_spec(spec); sys.path.insert(0, str(ROOT / "scripts/claude_adapters")); spec.loader.exec_module(mod)
    return mod


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.ap = load()
        if self.ap is None: self.skipTest("Pillow 없음")

    def test_sizes_and_aspect(self):
        for fmt, size, asp in [("9:16", (1080, 1920), "9:16"), ("16:9", (1920, 1080), "16:9"), ("1:1", (1080, 1080), "1:1")]:
            self.ap.set_format({"format": fmt})
            self.assertEqual((self.ap.W, self.ap.H), size)
            self.assertEqual(os.environ["PIXVERSE_ASPECT"], asp)
        self.ap.set_format({})
        self.assertEqual((self.ap.W, self.ap.H), (1080, 1920))

    def test_default_durations(self):
        self.assertEqual(self.ap.FORMATS["16:9"]["duration"], 60)
        self.assertEqual(self.ap.FORMATS["9:16"]["duration"], 30)
        cfg = json.loads((ROOT / "config/claude-autopilot.json").read_text())
        self.assertEqual(cfg["formats"]["16:9"]["default_duration_s"], 60)

    def test_unknown_format_rejected(self):
        with self.assertRaises(ValueError):
            self.ap.set_format({"format": "4:3"})


if __name__ == "__main__":
    unittest.main()
