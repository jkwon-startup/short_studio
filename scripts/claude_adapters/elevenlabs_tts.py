"""ElevenLabs TTS 어댑터 (Claude Code 전용).

키는 macOS 키체인(service=elevenlabs-api-key)에서만 읽고 출력하지 않는다.
한도와 사용량은 budget.py가 관리한다(승인 한도는 config에서, 사용량은 usage/에).

사용:
  python3 scripts/claude_adapters/elevenlabs_tts.py voices [--lang ko]
  python3 scripts/claude_adapters/elevenlabs_tts.py tts --voice-id ID --text "..." --out a.mp3 [--production ID]
"""
import argparse, json, subprocess, sys, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import budget

API = "https://api.elevenlabs.io"
DEFAULT_MODEL = "eleven_multilingual_v2"  # 베타가 아닌 GA 모델
ROOT = Path(__file__).resolve().parents[2]


def api_key():
    r = subprocess.run(["security", "find-generic-password", "-s", "elevenlabs-api-key", "-w"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit("BLOCKED: 키체인에 elevenlabs-api-key 가 없습니다")
    return r.stdout.strip()


def request(method, path, body=None, accept="application/json"):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"xi-api-key": api_key(), "Content-Type": "application/json",
                                          "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"FAIL: ElevenLabs HTTP {e.code}: {e.read()[:300].decode(errors='replace')}")


def charge(production, chars):
    """예산 확인 후 사용량 누적. 초과 시 호출 전에 중단. 제작 ID가 없어도 하루 총량에는 잡힌다."""
    try:
        budget.charge(production, "elevenlabs_chars", chars)
    except (budget.OverBudget, ValueError) as e:
        sys.exit(f"BLOCKED: {e}")


def cmd_voices(a):
    data = json.loads(request("GET", "/v2/voices?page_size=100"))
    for v in data.get("voices", []):
        labels = v.get("labels") or {}
        langs = [l.get("language") for l in (v.get("verified_languages") or [])]
        if a.lang and a.lang not in langs and labels.get("language") != a.lang:
            continue
        print(json.dumps({"voice_id": v["voice_id"], "name": v.get("name"), "category": v.get("category"),
                          "labels": labels, "languages": langs}, ensure_ascii=False))


def cmd_tts(a):
    text = Path(a.text_file).read_text().strip() if a.text_file else a.text
    charge(a.production, len(text))
    body = {"text": text, "model_id": a.model,
            "voice_settings": {"stability": a.stability, "similarity_boost": 0.75, "speed": a.speed}}
    audio = request("POST", f"/v1/text-to-speech/{a.voice_id}?output_format=mp3_44100_128", body, "audio/mpeg")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    sidecar = {"provider": "elevenlabs", "model_id": a.model, "voice_id": a.voice_id, "speed": a.speed,
               "stability": a.stability, "chars": len(text), "text": text, "bytes": len(audio),
               "created": datetime.now(timezone.utc).isoformat()}
    out.with_suffix(out.suffix + ".json").write_text(json.dumps(sidecar, ensure_ascii=False, indent=2))
    print(json.dumps({"status": "SUCCESS", "out": str(out), "chars": len(text), "bytes": len(audio)}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("voices"); v.add_argument("--lang"); v.set_defaults(fn=cmd_voices)
    t = sub.add_parser("tts")
    t.add_argument("--voice-id", required=True)
    g = t.add_mutually_exclusive_group(required=True)
    g.add_argument("--text"); g.add_argument("--text-file")
    t.add_argument("--out", required=True)
    t.add_argument("--model", default=DEFAULT_MODEL)
    t.add_argument("--speed", type=float, default=1.0)
    t.add_argument("--stability", type=float, default=0.5)
    t.add_argument("--production")
    t.set_defaults(fn=cmd_tts)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
