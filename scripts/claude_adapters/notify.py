"""Slack 웹훅 알림. 웹훅은 키체인(short-studio-slack-webhook) → 환경변수 SLACK_WEBHOOK_URL → ~/.claude/.env 순서로 찾는다.
값은 출력하지 않는다. AUTOPILOT_NO_NOTIFY=1이면 보내지 않는다."""
import json, os, re, subprocess, urllib.request
from pathlib import Path


def webhook():
    r = subprocess.run(["security", "find-generic-password", "-s", "short-studio-slack-webhook", "-w"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip(): return r.stdout.strip()
    if os.environ.get("SLACK_WEBHOOK_URL"): return os.environ["SLACK_WEBHOOK_URL"]
    env = Path.home() / ".claude/.env"
    if env.exists():
        m = re.search(r"^SLACK_WEBHOOK_URL=(.+)$", env.read_text(), re.M)
        if m: return m.group(1).strip().strip('"\'')
    return None


def send(scope, text):
    if os.environ.get("AUTOPILOT_NO_NOTIFY"):
        print("NOTIFY_DISABLED:", text); return
    url = webhook()
    if not url:
        print("NOTIFY_SKIPPED(no webhook):", text); return
    body = json.dumps({"text": f"[{scope}] {text}"}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, body, {"Content-Type": "application/json"}), timeout=15)
    except Exception as e:  # 알림 실패가 제작을 막지는 않는다
        print("NOTIFY_FAILED:", type(e).__name__)
