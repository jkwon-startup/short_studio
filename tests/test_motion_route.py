"""모션그래픽 경로 분기: 모션 샷이 없으면 전편 모션을 정적 합성으로 대신하지 않고, 엔진이 없으면 막는다."""
import importlib.util, sys, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load():
    try:
        import PIL  # noqa: F401
    except ImportError:
        return None
    spec = importlib.util.spec_from_file_location("ap_motion", ROOT / "scripts/claude_adapters/autopilot.py")
    mod = importlib.util.module_from_spec(spec); sys.path.insert(0, str(ROOT / "scripts/claude_adapters")); spec.loader.exec_module(mod)
    return mod


class MotionRouteTests(unittest.TestCase):
    def setUp(self):
        self.ap = load()
        if self.ap is None: self.skipTest("Pillow 없음")

    def test_full_motion_without_motion_shots_is_blocked(self):
        brief = {"brand": "ExampleBrand", "creative_direction": {"mode": "motion_graphics", "selection_source": "USER", "reason": "test"}}
        plan = {"shots": [{"source": {"type": "image", "id": "IMG-01"}}]}
        with self.assertRaises(self.ap.Blocked):
            self.ap.require_supported_render(brief, plan)

    def test_motion_shots_need_engine(self):
        plan = {"shots": [{"source": {"type": "motion", "scene": {"layers": []}}}]}
        with mock.patch.object(self.ap, "motion_ready", return_value=False):
            with self.assertRaises(self.ap.Blocked):
                self.ap.require_supported_render({"brand": "ExampleBrand"}, plan)
        with mock.patch.object(self.ap, "motion_ready", return_value=True):
            self.ap.require_supported_render({"brand": "ExampleBrand"}, plan)


if __name__ == "__main__":
    unittest.main()
