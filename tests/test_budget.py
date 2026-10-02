"""비용 한도: 승인값은 config에서만 읽고 brief는 낮출 수만 있다. 사용량은 work/ 밖 usage/에 쌓이고 새 ID를 만들어도 하루 총량은 이어진다."""
import importlib.util, json, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("budget_under_test", ROOT / "scripts/claude_adapters/budget.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.b = load(); self.root = Path(tempfile.mkdtemp()); self.b.ROOT = self.root
        (self.root / "config").mkdir()
        (self.root / "config/claude-autopilot.json").write_text(json.dumps({
            "budget_caps_per_short": {"pixverse_images": 12, "pixverse_clips": 4, "elevenlabs_chars": 800},
            "budget_caps_by_format": {"16:9": {"pixverse_images": 20, "pixverse_clips": 6, "elevenlabs_chars": 1500}},
            "max_shorts_per_day": 2}))

    def brief(self, pid, caps=None, fmt="9:16"):
        w = self.root / "work" / pid; w.mkdir(parents=True)
        (w / "brief.json").write_text(json.dumps({"format": fmt, **({"budget_caps": caps} if caps is not None else {})}))

    def local(self, **cfg):
        (self.root / "config/local.json").write_text(json.dumps(cfg))

    def test_brief_cannot_raise_cap(self):
        self.brief("claude-a", {"pixverse_clips": 999})
        for _ in range(4): self.b.charge("claude-a", "pixverse_clips")
        with self.assertRaises(self.b.OverBudget):
            self.b.charge("claude-a", "pixverse_clips")

    def test_brief_can_lower_cap(self):
        self.brief("claude-a", {"pixverse_clips": 1})
        self.b.charge("claude-a", "pixverse_clips")
        with self.assertRaises(self.b.OverBudget):
            self.b.charge("claude-a", "pixverse_clips")

    def test_approved_local_caps_win_over_public_default(self):
        self.local(budget_caps={"pixverse_images": 12, "pixverse_clips": 4, "elevenlabs_chars": 800},
                   approved={"budget_caps": {"pixverse_images": 2, "pixverse_clips": 1, "elevenlabs_chars": 100}})
        self.brief("claude-a")
        self.assertEqual(self.b.approved_caps("9:16")["pixverse_images"], 2)
        with self.assertRaises(self.b.OverBudget):
            self.b.charge("claude-a", "elevenlabs_chars", 101)

    def test_format_default_without_local(self):
        self.assertEqual(self.b.approved_caps("16:9")["pixverse_images"], 20)
        self.assertEqual(self.b.approved_caps("9:16")["pixverse_images"], 12)

    def test_new_id_does_not_reset_daily_total(self):
        for pid in ("claude-a", "claude-b"):
            self.brief(pid)
            for _ in range(4): self.b.charge(pid, "pixverse_clips")
        self.brief("claude-c")
        with self.assertRaises(self.b.OverBudget) as e:
            self.b.charge("claude-c", "pixverse_clips")
        self.assertIn("하루", str(e.exception))

    def test_usage_is_outside_work_and_failed_charge_not_counted(self):
        self.brief("claude-a")
        self.b.charge("claude-a", "elevenlabs_chars", 700)
        with self.assertRaises(self.b.OverBudget):
            self.b.charge("claude-a", "elevenlabs_chars", 200)
        self.assertEqual(self.b.usage("claude-a"), {"elevenlabs_chars": 700})
        self.assertTrue((self.root / "usage/claude-a.json").exists())
        # work/ 안의 사본을 고쳐도 한도 계산에는 영향이 없다
        (self.root / "work/claude-a/usage.json").write_text("{}")
        with self.assertRaises(self.b.OverBudget):
            self.b.charge("claude-a", "elevenlabs_chars", 200)

    def test_bad_ids_and_kinds_rejected(self):
        for pid in ("../x", "a/b", ""):
            with self.assertRaises(ValueError):
                self.b.charge(pid, "pixverse_clips")
        self.brief("claude-a")
        with self.assertRaises(ValueError):
            self.b.charge("claude-a", "gpu_hours")

    def test_adhoc_tts_without_production_still_counts(self):
        self.b.charge(None, "elevenlabs_chars", 800)
        with self.assertRaises(self.b.OverBudget):
            self.b.charge(None, "elevenlabs_chars", 900)


if __name__ == "__main__":
    unittest.main()
