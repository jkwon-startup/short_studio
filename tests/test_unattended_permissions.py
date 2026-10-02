"""무인 실행 권한: 웹을 읽는 세션과 셸을 쓰는 세션이 분리돼 있고, 셸 전체 허용이 다시 들어오지 않았는지 확인한다."""
import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = {"WebSearch", "WebFetch"}


def claude_calls(text):
    """claude -p 호출마다 (허용 도구, 금지 도구) 집합을 뽑는다."""
    calls = []
    for chunk in re.split(r"\bclaude -p\b", text)[1:]:
        allow = re.search(r'--allowedTools\s+"([^"]*)"', chunk); deny = re.search(r'--disallowedTools\s+"([^"]*)"', chunk)
        calls.append((set(allow.group(1).split(",")) if allow else set(), set(deny.group(1).split(",")) if deny else set(), chunk))
    return calls


class UnattendedPermissionTests(unittest.TestCase):
    def setUp(self):
        self.script = (ROOT / "scripts/setup/run_scheduled.sh").read_text()
        self.calls = claude_calls(re.sub(r"(?m)^\s*#.*$", "", self.script))

    def test_no_session_has_both_web_and_shell(self):
        self.assertEqual(len(self.calls), 2)
        for allow, deny, _ in self.calls:
            self.assertNotIn("Bash", allow, "셸 전체 허용 금지: .claude/settings.json 허용 목록만 쓴다")
            self.assertFalse(allow & WEB and "Bash" not in deny, "웹 도구를 쓰는 세션은 Bash를 명시적으로 막아야 한다")

    def test_research_session_is_web_only(self):
        allow, deny, _ = self.calls[0]
        self.assertEqual(allow, WEB)
        self.assertTrue({"Bash", "Read", "Write", "Edit", "Agent"} <= deny)

    def test_production_session_has_no_web_and_extra_denies(self):
        allow, deny, chunk = self.calls[1]
        self.assertTrue(WEB <= deny); self.assertFalse(allow & WEB)
        self.assertIn("--settings scripts/setup/unattended-settings.json", chunk)
        self.assertNotIn("acceptEdits", chunk)
        denied = set(json.loads((ROOT / "scripts/setup/unattended-settings.json").read_text())["permissions"]["deny"])
        self.assertTrue(WEB | {"Bash(cp:*)", "Edit(scripts/**)", "Edit(config/**)", "Edit(usage/**)"} <= denied)

    def test_project_allow_list_has_no_blanket_shell(self):
        allowed = json.loads((ROOT / ".claude/settings.json").read_text())["permissions"]["allow"]
        for rule in allowed:
            self.assertNotIn(rule, ("Bash", "Bash(*)", "Bash(:*)"))
            self.assertFalse(rule.startswith(("Bash(security", "Bash(curl", "Bash(sh ", "Bash(bash -c", "Bash(python3 -c")), rule)

    def test_setup_wizard_uses_same_runner(self):
        setup = (ROOT / "scripts/setup/setup.py").read_text()
        self.assertNotIn("--allowedTools", setup)
        self.assertIn("run_scheduled.sh", setup)

    def test_lock_and_time_limit_present(self):
        self.assertIn(".autorun.lock", self.script)
        self.assertIn("run_limited", self.script)


if __name__ == "__main__":
    unittest.main()
