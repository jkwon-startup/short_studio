"""short_studio 첫 설치 마법사 (사람이 한 번만 실행).

  python3 scripts/setup/setup.py

1) 환경 점검 → 2) 도구·실행 위치·일정·주제 방식·브랜드 기본값 선택 → 3) 로그인·키 저장
→ 4) 테스트 영상 1편 제작 → 5) 사용자가 보고 승인 → 6) 자동 실행 등록.
승인 결과와 개인 값은 config/local.json(깃 제외)에만 저장한다. 키는 macOS 키체인에만 둔다.
"""
import json, os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "config/local.json"
TOPICS = ROOT / "config/topics.txt"
PLIST_LABEL = "com.shortstudio.autorun"


def ask(q, default=None, choices=None):
    hint = f" [{'/'.join(choices)}]" if choices else ""
    hint += f" (기본: {default})" if default not in (None, "") else ""
    while True:
        v = input(f"{q}{hint}: ").strip() or (default or "")
        if not choices or v in choices: return v
        print("  선택지 중에서 입력해 주세요.")


def yes(q, default="y"):
    return ask(q, default, ["y", "n"]) == "y"


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, **kw)


def find_pillow_python():
    cands = [os.environ.get("SHORT_STUDIO_PY"), sys.executable, shutil.which("python3"),
             "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3", "/opt/homebrew/bin/python3"]
    for c in [c for c in cands if c]:
        if run([c, "-c", "import PIL"], capture_output=True).returncode == 0: return c
    return None


def doctor():
    print("\n[1/6] 환경 점검")
    ok = True
    for tool in ["ffmpeg", "ffprobe", "node"]:
        p = shutil.which(tool); print(f"  {tool:8s} {'OK ' + p if p else '없음'}"); ok &= bool(p)
    py = find_pillow_python(); print(f"  Pillow   {'OK ' + py if py else '없음 → pip install pillow'}"); ok &= bool(py)
    px = os.environ.get("PIXVERSE_REAL") or next((p for p in [
        str(Path.home() / ".claude/tools/pixverse/node_modules/pixverse/dist/index.js"),
        run(["npm", "root", "-g"], capture_output=True).stdout.strip() + "/pixverse/dist/index.js"] if Path(p).exists()), None)
    print(f"  Pixverse {'OK ' + px if px else '없음 → npm install -g pixverse (또는 PIXVERSE_REAL 지정)'}"); ok &= bool(px)
    wh = shutil.which("mlx_whisper") or "/Library/Frameworks/Python.framework/Versions/3.11/bin/mlx_whisper"
    print(f"  Whisper  {'OK ' + wh if Path(wh).exists() else '없음 → pip install mlx-whisper (Apple Silicon)'}")
    fonts = list((Path.home() / "Library/Fonts").glob("GmarketSans*"))
    print(f"  폰트     {'OK Gmarket Sans' if fonts else '없음 → https://corp.gmarket.com/fonts/ (OFL)에서 설치'}"); ok &= bool(fonts)
    mot = (ROOT / "motion/node_modules/remotion").exists()
    print(f"  모션엔진 {'OK Remotion' if mot else '없음 → cd motion && npm install (개인·3인 이하 무료, 그 이상 Company License)'}")
    if not mot and shutil.which("npm") and yes("모션그래픽 엔진(Remotion)을 motion/에 설치할까요?", "y"):
        run(["npm", "install", "--no-fund", "--no-audit"], cwd=ROOT / "motion")
    for t in ["claude", "codex"]: print(f"  {t:8s} {shutil.which(t) or '없음'}")
    r = run(["python3", "-m", "studio", "doctor"], cwd=ROOT, capture_output=True); print("  studio doctor", "OK" if r.returncode == 0 else "실패")
    return ok, py, px, wh


def choose():
    print("\n[2/6] 실행 방식과 기본값 (나중에 config/local.json에서 바꿀 수 있어요)")
    cfg = json.loads(LOCAL.read_text()) if LOCAL.exists() else {}
    cfg["tool"] = ask("제작 도구", cfg.get("tool", "claude"), ["claude", "codex"])
    cfg["runner"] = ask("실행 위치: app=Claude/Codex 앱의 예약 기능, server=이 맥(맥북·맥미니)에서 launchd", cfg.get("runner", "server"), ["app", "server"])
    sch = cfg.get("schedule", {})
    cfg["schedule"] = {"weekday": ask("요일(0=일 1=월 … 6=토, *=매일)", str(sch.get("weekday", "1"))),
                       "hour": int(ask("시(0-23)", str(sch.get("hour", 9)))), "minute": int(ask("분", str(sch.get("minute", 0))))}
    cfg["topic_mode"] = ask("주제: list=config/topics.txt 위에서부터 하나씩, fixed=매번 같은 주제", cfg.get("topic_mode", "list"), ["list", "fixed"])
    if cfg["topic_mode"] == "fixed": cfg["fixed_topic"] = ask("고정 주제", cfg.get("fixed_topic", ""))
    b = cfg.get("brand", {})
    cfg["brand"] = {"name": ask("브랜드 이름", b.get("name", "")), "audience": ask("기본 대상", b.get("audience", "")),
                    "slogan": ask("슬로건(엔드카드)", b.get("slogan", "")), "accent": ask("강조색 HEX", b.get("accent", "#0B4F4A")),
                    "tone": ask("톤앤매너 한 줄", b.get("tone", "실전적이고 독려하는 전문가 톤"))}
    v = cfg.get("voice", {})
    cfg["voice"] = {"voice_id": ask("ElevenLabs 기본 voice_id(목소리)", v.get("voice_id", "")),
                    "model": v.get("model", "eleven_multilingual_v2")}
    cfg["format"] = ask("기본 화면 비율: 9:16=세로(쇼츠·릴스), 16:9=가로(유튜브), 1:1=정사각", cfg.get("format", "9:16"), ["9:16", "16:9", "1:1"])
    dflt = {"9:16": 30, "16:9": 60, "1:1": 30}[cfg["format"]]
    cfg["duration"] = int(ask("기본 길이(초)", str(cfg.get("duration", dflt))))
    base = {"9:16": (12, 4, 800), "16:9": (20, 6, 1500), "1:1": (12, 4, 800)}[cfg["format"]]
    scale = cfg["duration"] / dflt
    caps = cfg.get("budget_caps") or {"pixverse_images": round(base[0] * scale), "pixverse_clips": round(base[1] * scale), "elevenlabs_chars": round(base[2] * scale)}
    cfg["budget_caps"] = {k: int(ask(f"1편 한도 {k}", str(val))) for k, val in caps.items()}
    cfg["max_shorts_per_day"] = int(ask("하루 최대 제작 편수(하루 총 한도 = 1편 한도 × 이 값)", str(cfg.get("max_shorts_per_day", 3))))
    cfg["max_run_minutes"] = int(ask("1회 실행 시간 한도(분)", str(cfg.get("max_run_minutes", 90))))
    if not TOPICS.exists():
        TOPICS.write_text("# 한 줄에 주제 하나. 실행할 때마다 맨 위의 [ ] 항목을 쓰고 [x]로 표시합니다.\n# 형식: [ ] 주제 | 대상(생략 가능)\n")
    return cfg


def credentials(px):
    print("\n[3/6] 로그인과 키 (값은 키체인에만 저장, 화면·파일에 남기지 않음)")
    if px and yes("Pixverse 로그인을 진행할까요? 브라우저가 열립니다"):
        run(["node", px, "auth", "login"])
    have = run(["security", "find-generic-password", "-s", "elevenlabs-api-key"], capture_output=True).returncode == 0
    if not have or yes("ElevenLabs API 키를 새로 저장할까요?", "n"):
        print("  ElevenLabs → Developers → API Keys (권한: Text to Speech, Voices 읽기). 붙여넣어도 화면에 안 보여요.")
        run(["security", "add-generic-password", "-U", "-a", os.environ.get("USER", "user"), "-s", "elevenlabs-api-key", "-w"])
    if yes("Slack 완성 알림 웹훅을 저장할까요?", "y"):
        run(["security", "add-generic-password", "-U", "-a", os.environ.get("USER", "user"), "-s", "short-studio-slack-webhook", "-w"])
    r = run(["python3", "scripts/claude_adapters/test_connections.py"], cwd=ROOT)
    return r.returncode == 0


def test_video(cfg):
    print("\n[4/6] 테스트 영상 1편 제작 (실제 크레딧 사용, 한도 안)")
    topic = ask("테스트 주제", "AI로 혼자 창업 시작하기")
    started = datetime.now()
    # 예약 실행과 같은 권한·한도로 만든다(조사 세션과 제작 세션 분리, 셸은 허용 목록만)
    r = run(["bash", "scripts/setup/run_scheduled.sh", "--test", topic], cwd=ROOT)
    vids = sorted((p for p in (ROOT / "work").glob("*/render/*_draft.mp4") if datetime.fromtimestamp(p.stat().st_mtime) > started),
                  key=lambda p: p.stat().st_mtime)
    if r.returncode or not vids:
        print("  테스트 제작 실패. logs/의 최근 autorun 로그를 확인하고 다시 실행하세요."); return None
    print("  완성:", vids[-1]); run(["open", str(vids[-1])]); return vids[-1]


def approve(cfg, video):
    print("\n[5/6] 승인 (이후 자동 실행은 이 승인을 근거로 묻지 않고 진행)")
    print("  영상을 실제로 보고 들은 뒤 답해 주세요.")
    if not yes("이 품질·목소리·톤으로 자동 제작을 시작할까요?", "n"): return False
    rights = {"pixverse_commercial": yes("Pixverse 플랜의 상업적 사용 조건을 확인했나요?", "n"),
              "elevenlabs_commercial": yes("ElevenLabs 유료 플랜(상업 이용 가능)인가요? (무료면 n → 영상 제목에 elevenlabs.io 표기)", "n")}
    cfg["approved"] = {"at": datetime.now().isoformat(timespec="seconds"), "test_video": str(video.relative_to(ROOT)),
                       "budget_caps": cfg["budget_caps"], "format": cfg.get("format", "9:16"), "duration": cfg.get("duration", 30), "voice": cfg["voice"], "rights_acknowledged": rights,
                       "scope": "이 설정·한도 안의 자동 제작(대본 선택·생성·렌더·저장·알림). 외부 업로드는 포함하지 않음"}
    cfg["auto_progress"] = {"enabled": True, "since": cfg["approved"]["at"][:10], "source": "설치 마법사 테스트 영상 승인"}
    return True


def enable(cfg):
    print("\n[6/6] 자동 실행 등록")
    s = cfg["schedule"]
    if cfg["runner"] == "server":
        tpl = (ROOT / "scripts/setup/launchd.plist.template").read_text()
        cal = "".join(f"<key>{k}</key><integer>{v}</integer>" for k, v in
                      [("Weekday", s["weekday"]), ("Hour", s["hour"]), ("Minute", s["minute"])] if str(v) != "*")
        plist = tpl.replace("{{LABEL}}", PLIST_LABEL).replace("{{ROOT}}", str(ROOT)).replace("{{CALENDAR}}", cal).replace("{{PATH}}", os.environ.get("PATH", ""))
        dest = Path.home() / f"Library/LaunchAgents/{PLIST_LABEL}.plist"; dest.write_text(plist)
        run(["launchctl", "unload", str(dest)], capture_output=True); run(["launchctl", "load", str(dest)])
        print(f"  등록 완료: {dest}\n  맥이 그 시각에 켜져 있어야 실행됩니다(잠자기 상태면 깨어난 뒤 실행).")
    else:
        line = "bash scripts/setup/run_scheduled.sh"
        print("  앱 예약 기능에 아래 문장을 그대로 넣고, 작업 폴더를 이 프로젝트로 지정하세요.")
        print(f"   - Claude 앱: 예약 작업 → 프롬프트: '{line} 를 실행하고 결과를 요약해'")
        print(f"   - Codex 앱: Automations → 프롬프트: '{line} 를 실행해'")
        print(f"   - 일정: 요일 {s['weekday']}, {s['hour']:02d}:{s['minute']:02d}")


def main():
    print("short_studio 설치 마법사 —", ROOT)
    ok, py, px, wh = doctor()
    if not ok and not yes("필수 도구가 빠져 있어요. 그래도 계속할까요?", "n"): return
    cfg = choose(); cfg["python_pillow"] = py; cfg["pixverse_real"] = px; cfg["whisper"] = wh
    LOCAL.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    if not credentials(px): print("  연결 테스트 실패 항목을 해결한 뒤 다시 실행하세요."); return
    video = test_video(cfg)
    if not video: return
    if not approve(cfg, video):
        LOCAL.write_text(json.dumps(cfg, ensure_ascii=False, indent=2)); print("승인하지 않았어요. 설정을 바꾸고 다시 실행하세요."); return
    LOCAL.write_text(json.dumps(cfg, ensure_ascii=False, indent=2)); enable(cfg)
    print("\n설정 완료. 주제는 config/topics.txt에 한 줄씩 추가하세요.")


if __name__ == "__main__":
    main()
