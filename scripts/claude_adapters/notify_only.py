"""제작 ID 없이 Slack 알림만 보낸다(예약 실행기의 사전 점검 실패 알림용)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notify import send  # noqa: E402

send("short_studio 예약 실행", " ".join(sys.argv[1:]) or "알림")
