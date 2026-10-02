"""모션 장면 검증: 지원하지 않는 레이어·출처 없는 데이터·없는 로고 파일을 렌더 전에 막고, 데이터 값→픽셀 매핑이 0 기준 선형인지 확인한다."""
import importlib.util, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    try:
        import PIL  # noqa: F401
    except ImportError:
        return None
    spec = importlib.util.spec_from_file_location("ap_scene", ROOT / "scripts/claude_adapters/autopilot.py")
    mod = importlib.util.module_from_spec(spec); sys.path.insert(0, str(ROOT / "scripts/claude_adapters")); spec.loader.exec_module(mod)
    return mod


BARS = {"type": "data_bars", "box": {"x": 90, "y": 500, "w": 900, "h": 800}, "unit": "%", "source": "예시 조사 2026",
        "items": [{"label": "A", "value": 20}, {"label": "B", "value": 50}, {"label": "C", "value": 100}]}


class MotionSceneTests(unittest.TestCase):
    def setUp(self):
        self.ap = load()
        if self.ap is None: self.skipTest("Pillow 없음")
        self.tmp = Path(tempfile.mkdtemp())

    def check(self, layers, frames=90):
        return self.ap.validate_motion_scene({"layers": layers}, self.tmp, frames)

    def test_unknown_layer_is_blocked(self):
        with self.assertRaises(self.ap.Blocked):
            self.check([{"type": "particle_storm"}])

    def test_data_mapping_is_linear_from_zero(self):
        m = self.ap.data_bar_mapping(BARS)
        px = [b["px"] for b in m["bars"]]
        self.assertAlmostEqual(px[2], m["track_px"])
        self.assertAlmostEqual(px[0] / px[2], 0.2, places=3)
        self.assertAlmostEqual(px[1] / px[2], 0.5, places=3)
        wide = self.ap.data_bar_mapping({**BARS, "max": 200})
        self.assertAlmostEqual(wide["bars"][2]["px"], wide["track_px"] / 2)

    def test_data_needs_unit_source_and_no_cut_axis(self):
        self.check([BARS])
        for bad in ({**BARS, "source": ""}, {k: v for k, v in BARS.items() if k != "unit"},
                    {**BARS, "max": 80}, {**BARS, "items": [{"label": "A", "value": -3}, {"label": "B", "value": 5}]},
                    {**BARS, "items": [{"label": "A", "value": "많음"}]}):
            with self.assertRaises(self.ap.Blocked):
                self.check([bad])

    def test_logo_file_must_exist(self):
        layer = {"type": "logo_sting", "src": "LOGO.png", "x": 540, "y": 900, "width": 520}
        with self.assertRaises(self.ap.Blocked):
            self.check([layer])
        (self.tmp / "LOGO.png").write_bytes(b"x")
        self.check([layer])

    def test_kinetic_full_phrases_ordered_and_readable(self):
        ok = {"type": "kinetic_full", "phrases": [{"text": "혼자서도", "at": 0}, {"text": "시작합니다", "at": 30}]}
        self.check([ok])
        for bad in ({"type": "kinetic_full", "phrases": []},
                    {"type": "kinetic_full", "phrases": [{"text": "하나", "at": 30}, {"text": "둘", "at": 10}]},
                    {"type": "kinetic_full", "phrases": [{"text": "하나", "at": 0}, {"text": "둘", "at": 4}]},
                    {"type": "kinetic_full", "phrases": [{"text": "하나", "at": 0}, {"text": "둘", "at": 88}]}):
            with self.assertRaises(self.ap.Blocked):
                self.check([bad])


if __name__ == "__main__":
    unittest.main()
