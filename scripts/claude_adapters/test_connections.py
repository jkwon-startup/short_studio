"""연결 최소 테스트: (a) API 연결 (b) 데이터 형식 (c) 짧은 예시 1개.

  python3 scripts/claude_adapters/test_connections.py            # 무료 확인만
  python3 scripts/claude_adapters/test_connections.py --tts-sample  # 한국어 20자 내외 1회 생성
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PX = Path.home() / ".claude/tools/pixverse/node_modules/pixverse/dist/index.js"
OUT = HERE.parents[1] / "work" / "_connection_test"
results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


ap = argparse.ArgumentParser()
ap.add_argument("--tts-sample", action="store_true")
args = ap.parse_args()

# Pixverse
r = run(["node", str(PX), "account", "info"])
px_out = r.stdout + r.stderr  # Pixverse CLI는 정보를 stderr로 출력
check("pixverse 로그인", r.returncode == 0 and "Credits" in px_out,
      next((l.strip() for l in px_out.splitlines() if "Total" in l), ""))

# ElevenLabs 키
r = run(["security", "find-generic-password", "-s", "elevenlabs-api-key"])
check("elevenlabs 키체인", r.returncode == 0)

# ElevenLabs 목소리 목록 (형식 확인)
r = run([sys.executable, str(HERE / "elevenlabs_tts.py"), "voices"])
voices = [json.loads(l) for l in r.stdout.splitlines() if l.startswith("{")]
check("elevenlabs voices API", r.returncode == 0 and voices and "voice_id" in voices[0],
      f"{len(voices)}개" if voices else r.stdout[-200:] + r.stderr[-200:])
ko = [v for v in voices if "ko" in (v.get("languages") or [])]
for v in ko[:5]:
    print("   ko:", v["name"], v["voice_id"], v.get("category"))

# 한국어 샘플 1회
if args.tts_sample and voices:
    vid = (ko or voices)[0]["voice_id"]
    out = OUT / "sample_ko.mp3"
    r = run([sys.executable, str(HERE / "elevenlabs_tts.py"), "tts", "--voice-id", vid,
             "--text", "앱은 금방 나옵니다. 근데, 다 보입니다.", "--out", str(out)])
    ok = r.returncode == 0 and out.exists() and out.stat().st_size > 1000
    if ok:
        p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)])
        check("elevenlabs 한국어 샘플", True, f"{out} ({p.stdout.strip()}초)")
    else:
        check("elevenlabs 한국어 샘플", False, r.stdout[-300:] + r.stderr[-300:])

sys.exit(0 if all(ok for _, ok in results) else 1)
