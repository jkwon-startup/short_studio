"""Claude 숏폼 무인 제작: 대본 이후의 기계적인 단계를 한 명령으로 실행한다.

창작 단계(Research/Fact/Script/plan.json)는 Claude가 만든다. 이 스크립트는 그 파일을 읽어
녹음 → 길이 맞춤 → 시간 측정 → 이미지·클립 생성 → 렌더 → 원장 등록 → short 저장 → Slack 알림을 한다.

  python3.11 autopilot.py voice  <ID>   # script.json tts_text → voice/ + timing.json
  python3.11 autopilot.py assets <ID>   # plan.json images/clips 생성(이미 있으면 건너뜀)
  python3.11 autopilot.py render <ID>   # plan.json shots → render/<ID>_draft.mp4
  python3.11 autopilot.py finish <ID>   # 번들·ingest 전 단계·short 저장·Slack 알림
  python3.11 autopilot.py motion <ID>   # source.type=motion 장면을 Remotion(motion/)으로 렌더
  python3.11 autopilot.py review <ID>   # 자동 대리 검수(정지·컷·음량·재전사 대조), 사람 시청 대기로 기록
  python3.11 autopilot.py all    <ID>   # assets → render → previews → review → finish
  python3.11 autopilot.py notify <ID> "메시지"

중단 조건(config/claude-autopilot.json stop_only_when)에 걸리면 BLOCKED를 출력하고 Slack으로 알린 뒤 종료 코드 2.
"""
import hashlib, json, math, os, re, shutil, subprocess, sys, zipfile, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
AD = ROOT / "scripts/claude_adapters"
PY_STUDIO = "python3"  # studio CLI(3.11+)
W, H, FPS = 1080, 1920, 30
# 화면 비율: brief.format. 기본 길이는 세로 30초, 가로 60초, 정사각 30초(설치 마법사·brief에서 바꿀 수 있음)
FORMATS = {"9:16": {"size": (1080, 1920), "duration": 30, "pixverse": "9:16", "label": "Vertical 9:16"},
           "16:9": {"size": (1920, 1080), "duration": 60, "pixverse": "16:9", "label": "Horizontal 16:9 widescreen"},
           "1:1": {"size": (1080, 1080), "duration": 30, "pixverse": "1:1", "label": "Square 1:1"}}
FMT = "9:16"


def set_format(brief):
    """brief.format에 맞춰 출력 크기를 정한다. 한 프로세스는 제작 하나만 다룬다."""
    global W, H, FMT
    FMT = brief.get("format", "9:16")
    if FMT not in FORMATS: raise ValueError(f"지원하지 않는 화면 비율: {FMT} (9:16, 16:9, 1:1)")
    W, H = FORMATS[FMT]["size"]
    os.environ["PIXVERSE_ASPECT"] = FORMATS[FMT]["pixverse"]; os.environ["PIXVERSE_FRAMING"] = FORMATS[FMT]["label"]


def landscape():
    return W > H


def ui_scale():
    return min(W, H) / 1080
FONTS = Path.home() / "Library/Fonts"
F_BOLD, F_MED = str(FONTS / "GmarketSansTTFBold.ttf"), str(FONTS / "GmarketSansTTFMedium.ttf")
CFG = json.loads((ROOT / "config/claude-autopilot.json").read_text())
LOCAL = json.loads((ROOT / "config/local.json").read_text()) if (ROOT / "config/local.json").exists() else {}
# 설치 마법사(scripts/setup/setup.py)가 저장한 개인 값으로 공개 기본값을 덮는다(local.json은 깃 제외)
if LOCAL.get("voice", {}).get("voice_id"): CFG["voice"]["default_voice"] = LOCAL["voice"]["voice_id"]
if LOCAL.get("budget_caps"): CFG["budget_caps_per_short"] = LOCAL["budget_caps"]
_b = LOCAL.get("brand", {})
for _k, _v in {"wordmark_text": _b.get("name"), "slogan": _b.get("slogan"), "accent": _b.get("accent")}.items():
    if _v: CFG["visual"]["endcard"][_k] = _v
WHISPER = LOCAL.get("whisper") or shutil.which("mlx_whisper") or "/Library/Frameworks/Python.framework/Versions/3.11/bin/mlx_whisper"


class Blocked(Exception):
    pass


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise Blocked(f"명령 실패: {' '.join(map(str, cmd[:4]))} …\n{(r.stdout + r.stderr)[-1200:]}")
    return r.stdout


def layer_key(*parts):
    """글자 레이어 PNG의 캐시 키. 문구 전체와 화면 크기로 만든다(앞 몇 글자만 쓰면 다른 문구가 같은 PNG를 쓰게 된다)."""
    return hashlib.sha256(json.dumps([W, H, *parts], ensure_ascii=False).encode()).hexdigest()[:16]


def media_duration(path, stream="v:0"):
    out = sh(["ffprobe", "-v", "error", "-select_streams", stream, "-show_entries", "stream=duration:format=duration", "-of", "json", str(path)])
    d = json.loads(out); v = (d.get("streams") or [{}])[0].get("duration") or d.get("format", {}).get("duration")
    if v in (None, "N/A"): raise Blocked(f"길이를 읽을 수 없음: {Path(path).name}")
    return float(v)


def require_duration(path, target, label, tol=0.1, stream="v:0"):
    got = media_duration(path, stream)
    if abs(got - target) > tol: raise Blocked(f"{label} 길이 {got:.2f}초 ≠ 목표 {target:.2f}초 ({Path(path).name})")


def paths(pid):
    w = ROOT / "work" / pid
    brief = json.loads((w / "brief.json").read_text()); set_format(brief)
    return w, brief


def duration(p):
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).strip())


# ---------- 알림 ----------
def notify(pid, text):
    sys.path.insert(0, str(AD))
    from notify import send  # 키체인 → 환경변수 → ~/.claude/.env 순서로 웹훅을 찾는다
    send(f"short_studio · {pid}", text)


def creative_direction(brief, plan):
    """Explicit user direction wins; a conflicting plan is not an override."""
    defaults = CFG.get("creative_direction", {})
    user = brief.get("creative_direction", {})
    proposed = plan.get("creative_direction", {})
    if user.get("mode") and user.get("selection_source") != "DEFAULT":
        if proposed.get("mode") and proposed["mode"] != user["mode"]:
            raise Blocked("계획 표현 방식이 사용자의 명시적 방향과 충돌합니다. 계획을 수정하세요")
        return {**defaults, **proposed, **user}
    return {**defaults, **user, **proposed}


MOTION_DIR = ROOT / "motion"


def motion_ready():
    return (MOTION_DIR / "node_modules/remotion").exists() and shutil.which("npx") is not None


MOTION_LAYER_TYPES = {"app_screen", "kinetic_text", "notify_card", "logo_sting", "data_bars", "kinetic_full"}
DATA_TRACK = {"vertical": ("h", 0.56), "horizontal": ("w", 0.58)}  # motion/src/DataBars.tsx와 같은 값
KINETIC_MIN_HOLD = 12  # 구 하나가 화면에 머무는 최소 프레임(30fps 0.4초)


def data_bar_mapping(layer):
    """data_bars의 값→픽셀 매핑. 0에서 시작하는 선형 축만 쓴다(축 절단·로그 없음). 검수 근거로 props에 남긴다."""
    side, frac = DATA_TRACK[layer.get("orientation", "vertical")]
    vals = [float(i["value"]) for i in layer["items"]]
    top = float(layer.get("max") or max(vals)); track = layer["box"][side] * frac
    return {"axis": "linear_from_zero", "max": top, "track_px": round(track, 2),
            "bars": [{"label": i["label"], "value": i["value"], "px": round(track * v / top, 2)} for i, v in zip(layer["items"], vals)]}


def validate_motion_scene(scene, assets, frames):
    """렌더 전에 장면 props를 점검한다. 지원하지 않는 레이어나 근거 없는 데이터는 그려 놓고 구현됐다고 하지 않는다."""
    for l in scene.get("layers", []):
        t = l.get("type")
        if t not in MOTION_LAYER_TYPES:
            raise Blocked(f"지원하지 않는 모션 레이어: {t} (지원: {', '.join(sorted(MOTION_LAYER_TYPES))})")
        if t == "data_bars":
            items = l.get("items") or []
            if not 1 <= len(items) <= 6: raise Blocked("data_bars 항목은 1~6개")
            if any(isinstance(i.get("value"), bool) or not isinstance(i.get("value"), (int, float)) or not i.get("label") for i in items):
                raise Blocked("data_bars 항목은 label과 숫자 value가 필요합니다")
            vals = [i["value"] for i in items]
            if min(vals) < 0 or max(vals) <= 0: raise Blocked("data_bars는 0 이상 값만 지원합니다(0 기준 막대)")
            if "unit" not in l or not str(l.get("source") or "").strip(): raise Blocked("data_bars에는 unit(단위)과 source(출처)가 필요합니다")
            if l.get("max") is not None and l["max"] < max(vals): raise Blocked("data_bars max가 최댓값보다 작습니다(막대가 잘림)")
            if l.get("orientation", "vertical") not in DATA_TRACK or not isinstance(l.get("box"), dict): raise Blocked("data_bars에는 box와 orientation(vertical|horizontal)이 필요합니다")
        elif t == "logo_sting":
            if not l.get("src") or not (Path(assets) / l["src"]).exists(): raise Blocked(f"logo_sting 로고 파일 없음: assets/{l.get('src')}")
        elif t == "kinetic_full":
            ph = l.get("phrases") or []
            if not ph or any(not str(p.get("text") or "").strip() for p in ph): raise Blocked("kinetic_full에는 text가 있는 phrases가 필요합니다")
            at = [int(p.get("at", 0)) for p in ph] + [frames]
            if any(b - a < KINETIC_MIN_HOLD for a, b in zip(at, at[1:])):
                raise Blocked(f"kinetic_full 구 사이가 {KINETIC_MIN_HOLD}프레임보다 짧거나 순서가 뒤바뀜: at={at[:-1]}, 샷 길이 {frames}f")


def require_supported_render(brief, plan):
    uses_motion = any(s.get("source", {}).get("type") == "motion" for s in plan.get("shots", []))
    if creative_direction(brief, plan).get("mode") == "motion_graphics" and not uses_motion:
        raise Blocked("전편 모션그래픽은 shot.source.type=\"motion\"(Remotion) 장면으로 설계해야 합니다. 정적 PNG 합성으로 대신하지 않습니다")
    if uses_motion and not motion_ready():
        raise Blocked("모션 엔진(Remotion) 미설치: cd motion && npm install")


def voice_fit_factor(raw_seconds, target, choice=None):
    """Do not silently speed up ad copy just to fit a runtime."""
    choice = choice or {}
    factor = float(choice.get("atempo", 1.0))
    if not 0.85 <= factor <= 1.2:
        raise Blocked("음성 조정 범위 밖: 카피·정보량·호흡 수정 필요")
    if factor != 1.0 and not str(choice.get("reason", "")).strip():
        raise Blocked("음성 배속/감속 조정 이유를 brief.voice_fit.reason에 기록하세요")
    if raw_seconds / factor > target - 0.4 + 0.01:
        raise Blocked("음성 길이가 넘칩니다: 무조건 배속하지 말고 대본·정보량·호흡부터 수정하세요")
    return factor


def endcard_options(brief, plan):
    default = CFG["visual"]["endcard"]
    override = plan.get("endcard", {})
    if re.sub(r"\s+", "", brief["brand"]) != re.sub(r"\s+", "", default["wordmark_text"]):
        if not all(k in override for k in ("bg", "accent", "wordmark_text", "slogan")):
            raise Blocked("다른 브랜드의 엔드카드를 재사용하지 않습니다: 현재 브랜드명·슬로건·색을 명시하세요")
    return {**default, **override}


# ---------- voice ----------
def cmd_voice(pid):
    w, brief = paths(pid)
    script = json.loads((w / "script.json").read_text())
    target = float(brief["duration"])
    vdir = w / "voice"; vdir.mkdir(exist_ok=True)
    voice_id = brief.get("voice_id") or LOCAL.get("voice", {}).get("voice_id")
    if not voice_id: raise Blocked("목소리(voice_id)가 없습니다: 설치 마법사에서 지정하거나 brief.voice_id를 넣으세요")
    context = {"tts_text":script["tts_text"], "provider":CFG["voice"]["provider"],
               "model":CFG["voice"]["model"], "voice_id":voice_id}
    context_hash = hashlib.sha256(json.dumps(context, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    generation = vdir / "generations" / context_hash
    generation.mkdir(parents=True, exist_ok=True)
    (generation / "context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2))
    (generation / "tts.txt").write_text(script["tts_text"])
    raw = generation / "voice_raw.mp3"
    if not raw.exists():
        sh([PY_STUDIO, str(AD / "elevenlabs_tts.py"), "tts", "--voice-id", voice_id, "--text-file", str(generation / "tts.txt"),
            "--out", str(raw), "--production", pid])
    d = duration(raw); fit = target - 0.4
    factor = voice_fit_factor(d, target, brief.get("voice_fit"))
    final = generation / f"voice-atempo-{factor:.3f}.mp3"
    if factor != 1.0:
        sh(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-filter:a", f"atempo={factor}", str(final)])
    else:
        sh(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-c", "copy", str(final)])
    sh([WHISPER, str(final), "--language", "ko", "--word-timestamps", "True", "--output-format", "json", "--output-dir", str(generation / "whisper")])
    seg = json.loads((generation / "whisper" / (final.stem + ".json")).read_text())["segments"]
    # Selected aliases remain compatible with the renderer; prior selected bytes survive.
    alias = vdir / "voice.mp3"
    if alias.exists():
        previous = hashlib.sha256(alias.read_bytes()).hexdigest()
        history = vdir / "selected-history" / previous
        history.mkdir(parents=True, exist_ok=True)
        shutil.copy2(alias, history / "voice.mp3")
        for name in ("tts.txt", "voice-comparison.json", "voice-bundle.zip"):
            if (vdir / name).exists(): shutil.copy2(vdir / name, history / name)
    shutil.copy2(final, alias)
    shutil.copy2(generation / "tts.txt", vdir / "tts.txt")
    timing = {"voice": "voice.mp3", "raw_duration": d, "atempo": factor, "duration": duration(final),
              "segments": [{"start": round(s["start"], 2), "end": round(s["end"], 2), "heard": s["text"].strip()} for s in seg],
              "note": "heard는 Whisper가 들은 문장(오인식 가능). 이 시간으로 plan.json 샷 시간을 정한다"}
    (w / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=2))
    comp = {"script_id": script.get("script_id"), "status": "SELECTED", "selected": "voice.mp3",
            "selected_by": "autopilot 기본값(config/claude-autopilot.json voice)", "voice_id": voice_id,
            "script_context_hash": context_hash, "raw_voice": str(raw.relative_to(w)),
            "model": CFG["voice"]["model"], "raw_duration_s": d, "atempo": factor, "listened": False,
            "license": "ElevenLabs 플랜 조건 확인 필요(Free=비상업+표기)"}
    (vdir / "voice-comparison.json").write_text(json.dumps(comp, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(vdir / "voice-bundle.zip", "w") as z:
        for f in [alias, raw, generation / "tts.txt", generation / "context.json", vdir / "voice-comparison.json"] + list(generation.glob("voice_raw.mp3.json")):
            z.write(f, f.name)
    print(json.dumps({"status": "VOICE_READY", "duration": timing["duration"], "atempo": factor}, ensure_ascii=False))


# ---------- assets ----------
def cmd_assets(pid):
    w, brief = paths(pid); plan = json.loads((w / "plan.json").read_text())
    require_supported_render(brief, plan)  # Before any paid image/video call.
    a = w / "assets"; a.mkdir(exist_ok=True)
    cs = plan.get("character_sheet", "")
    for im in plan["images"]:
        out = a / f"{im['id']}.png"
        if out.exists(): continue
        ref = str(a / f"{im['ref']}.png") if im.get("ref") else ""
        prompt = (cs + " " if im.get("use_character_sheet", True) else "") + im["prompt"]
        args = [str(AD / "pixverse_image.sh"), "image", pid, str(out), prompt] + ([ref] if ref else [])
        out_txt = sh(args)
        if "BLOCKED" in out_txt: raise Blocked(out_txt)
    for c in plan.get("clips", []):
        out = a / f"{c['id']}.mp4"
        if out.exists(): continue
        sh([str(AD / "pixverse_image.sh"), "video", pid, str(a / f"{c['image']}.png"), str(out), c["prompt"], str(c.get("generate_s", 5))])
    print(json.dumps({"status": "ASSETS_READY", "images": len(plan["images"]), "clips": len(plan.get("clips", []))}))


# ---------- render ----------
def wrap(text, font, maxw):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1))); lines, cur = [], ""
    for wd in text.split(" "):
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = wd
    return lines + [cur]


class Renderer:
    def __init__(self, pid):
        self.w, self.brief = paths(pid); self.pid = pid
        self.plan = json.loads((self.w / "plan.json").read_text())
        require_supported_render(self.brief, self.plan)
        self.A, self.R = self.w / "assets", self.w / "render"
        self.L, self.S = self.R / "layers", self.R / "segments"
        for d in (self.L, self.S): d.mkdir(parents=True, exist_ok=True)
        self.style = {"accent": CFG["visual"]["endcard"]["accent"], **self.plan.get("style", {})}
        self.zoom = self.plan.get("zoom", 1.3)
        self.screen = self.measure_screen(self.plan["screen_image"]) if self.plan.get("screen_image") else None

    def measure_screen(self, img_id):
        im = ImageOps.fit(Image.open(self.A / f"{img_id}.png").convert("L"), (W, H)); px = im.load()
        ys = [y for y in range(int(H * 0.26), int(H * 0.91)) if sum(1 for x in range(0, W, 4) if px[x, y] > 235) > 40]
        if not ys: return None
        xs = [x for x in range(W) if sum(1 for y in range(min(ys), max(ys), 4) if px[x, y] > 235) > 20]
        return {"x": min(xs) + 8, "y": min(ys) + 8, "w": max(xs) - min(xs) - 16, "h": max(ys) - min(ys) - 16}

    def zbox(self):
        s, z = self.screen, self.zoom; cx, cy = s["x"] + s["w"] / 2, s["y"] + s["h"] / 2
        return {"x": int(cx + (s["x"] - cx) * z), "y": int(cy + (s["y"] - cy) * z), "w": int(s["w"] * z), "h": int(s["h"] * z)}

    # 레이어
    def caption(self, c):
        p = self.L / f"cap_{layer_key('cap', c['text'], c.get('pos', ''), c.get('sub', ''))}.png"
        if p.exists(): return p
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); k = ui_scale(); f = ImageFont.truetype(F_BOLD, round(62 * k)); step = round(80 * k)
        maxw = W * (0.66 if landscape() else 0.8)
        lines = wrap(c["text"], f, maxw)
        bottom = H * (0.84 if landscape() else 0.765)
        y = H * 0.13 if c.get("pos") == "top" else bottom - (len(lines) - 1) * step / 2
        for ln in lines:
            d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill="white", stroke_width=6, stroke_fill="black"); y += step
        if c.get("sub"):
            fs = ImageFont.truetype(F_MED, round(40 * ui_scale()))
            d.text(((W - d.textlength(c["sub"], font=fs)) / 2, y + 4), c["sub"], font=fs, fill="#BFE6E0", stroke_width=4, stroke_fill="black")
        img.save(p); return p

    def tag(self, text="예시"):
        p = self.L / f"tag_{layer_key('tag', text)}.png"
        if p.exists(): return p
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); f = ImageFont.truetype(F_MED, 30)
        y0 = round(H * 0.073); x1 = W - 60
        d.rounded_rectangle((x1 - 120, y0, x1, y0 + 60), 14, fill=(255, 255, 255, 190))
        d.text((x1 - 60 - d.textlength(text, font=f) / 2, y0 + 14), text, font=f, fill="#555555"); img.save(p); return p

    def notify_card(self, box):
        x0, y0 = box
        p = self.L / f"notify_{x0}_{y0}.png"
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); acc = self.style["accent"]
        d.rounded_rectangle((x0, y0, x0 + 480, y0 + 140), 36, fill=(255, 255, 255, 235))
        d.ellipse((x0 + 30, y0 + 30, x0 + 110, y0 + 110), fill=acc)
        d.rounded_rectangle((x0 + 130, y0 + 40, x0 + 440, y0 + 70), 12, fill="#CBD5D4")
        d.rounded_rectangle((x0 + 130, y0 + 85, x0 + 350, y0 + 110), 12, fill="#E1E7E6"); img.save(p); return p

    def screen_ui(self, state, zoomed=False):
        b = self.zbox() if zoomed else self.screen
        p = self.L / f"ui_{state}{'_z' if zoomed else ''}.png"
        if p.exists(): return p
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); acc = self.style["accent"]
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]; pad = int(w * .06)
        if state.startswith(("input", "typed")):
            bx = (x + pad, y + h - pad - int(h * .22), x + w - pad, y + h - pad)
            d.rounded_rectangle(bx, 24, fill="white", outline="#C9D3D2", width=3)
            n = int(state[-1]) if state[-1].isdigit() else 0
            for i in range(n):
                ly = y + pad + i * int(h * .13); d.rounded_rectangle((x + pad, ly, x + w - pad - i * 90, ly + int(h * .07)), 12, fill="#D7DDDC")
            if state == "input_cursor": d.rectangle((bx[0] + 30, bx[1] + 22, bx[0] + 36, bx[3] - 22), fill=acc)
            d.ellipse((bx[2] - 70, bx[1] + 14, bx[2] - 16, bx[3] - 14), fill=acc if n else "#9FB3B1")
        else:
            n = {"blocks1": 1, "blocks2": 2, "blocks3": 3, "blocks4": 4}.get(state, 5)
            d.rectangle((x, y, x + w, y + h), fill="#F7FAF9")
            if n >= 1: d.rectangle((x, y, x + w, y + int(h * .14)), fill=acc)
            if n >= 2: d.rounded_rectangle((x + pad, y + int(h * .2), x + w - pad, y + int(h * .48)), 16, fill="#CFE3E0")
            if n >= 3: d.rounded_rectangle((x + pad, y + int(h * .53), x + w / 2 - pad / 2, y + int(h * .74)), 14, fill="#E4ECEB")
            if n >= 4: d.rounded_rectangle((x + w / 2 + pad / 2, y + int(h * .53), x + w - pad, y + int(h * .74)), 14, fill="#E4ECEB")
            if n >= 5:
                bw, bh = int(w * .36), int(h * .12); bx, by = x + (w - bw) / 2, y + int(h * .8)
                if state == "misaligned":
                    btn = Image.new("RGBA", (bw, bh), (0, 0, 0, 0)); ImageDraw.Draw(btn).rounded_rectangle((0, 0, bw - 1, bh - 1), 20, fill="#D93A3A")
                    img.alpha_composite(btn.rotate(-6, expand=True), (int(bx + 60), int(by - 70)))
                else:
                    d.rounded_rectangle((bx, by, bx + bw, by + bh), 20, fill=acc, outline="#2E9E6B" if state == "aligned" else None, width=6)
        img.save(p); return p

    def endcard(self):
        ec = endcard_options(self.brief, self.plan)
        p = self.A / "ENDCARD.png"; img = Image.new("RGB", (W, H), ec["bg"]); d = ImageDraw.Draw(img)
        f1, f2 = ImageFont.truetype(F_BOLD, 96), ImageFont.truetype(F_MED, 48)
        d.text(((W - d.textlength(ec["wordmark_text"], font=f1)) / 2, H * 0.4375), ec["wordmark_text"], font=f1, fill=ec["accent"])
        d.rectangle((W / 2 - 60, H * 0.51, W / 2 + 60, H * 0.51 + 6), fill=ec["accent"])
        d.text(((W - d.textlength(ec["slogan"], font=f2)) / 2, H * 0.531), ec["slogan"], font=f2, fill="#333333")
        if ec.get("extra_line"):
            f3 = ImageFont.truetype(F_MED, 36); d.text(((W - d.textlength(ec["extra_line"], font=f3)) / 2, H * 0.573), ec["extra_line"], font=f3, fill="#666666")
        img.save(p); return p

    def zoomed_still(self, img_id):
        im = ImageOps.fit(Image.open(self.A / f"{img_id}.png").convert("RGB"), (W, H)); s, z = self.screen, self.zoom
        cx, cy = s["x"] + s["w"] / 2, s["y"] + s["h"] / 2; l, t = cx - cx / z, cy - cy / z
        p = self.R / f"{img_id}_zoom.png"; im.crop((int(l), int(t), int(l + W / z), int(t + H / z))).resize((W, H)).save(p); return p

    # 세그먼트
    def seg_still(self, name, img, dur, motion):
        frames = int(round(dur * FPS)); big = f"scale={int(W*1.08)}:{int(H*1.08)}:force_original_aspect_ratio=increase,crop={int(W*1.08)}:{int(H*1.08)}"
        mv = {"pan_left": f"{big},crop={W}:{H}:x='(iw-{W})*(1-n/{frames})':y='(ih-{H})/2'",
              "pan_right": f"{big},crop={W}:{H}:x='(iw-{W})*n/{frames}':y='(ih-{H})/2'",
              "rise": f"{big},crop={W}:{H}:x='(iw-{W})/2':y='(ih-{H})*(1-n/{frames})'"}.get(motion)
        if motion == "push":
            s, z = self.screen, self.zoom; cx, cy = s["x"] + s["w"] / 2, s["y"] + s["h"] / 2
            mv = f"scale={W}:{H},zoompan=z='min({z}\\,1+({z}-1)*on/15)':x='{cx}-{cx}/zoom':y='{cy}-{cy}/zoom':d={frames}:s={W}x{H}:fps={FPS}"
        mv = mv or f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
        out = self.S / f"{name}.mp4"
        sh(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(img), "-frames:v", str(frames),
            "-vf", mv + ",format=yuv420p", "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)]); return out

    def seg_clip(self, name, clip, dur, start):
        out = self.S / f"{name}.mp4"
        have = media_duration(clip)
        if have + 0.05 < start + dur:  # 모자란 채로 자르면 뒤 샷이 전부 음성과 어긋난다
            raise Blocked(f"{name}: {Path(clip).name} 길이 {have:.2f}초가 샷 구간({start}초부터 {dur}초)보다 짧습니다. 샷을 줄이거나 클립을 더 길게 다시 만드세요")
        sh(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-i", str(clip), "-t", str(dur), "-an", "-vf",
            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},format=yuv420p", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)]); return out

    def overlay(self, seg, layers):
        if not layers: return seg
        out = seg.with_name(seg.stem + "_ov.mp4"); cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(seg)]; chain, last = [], "0:v"
        for p, *_ in layers: cmd += ["-i", str(p)]
        for i, (p, t0, t1) in enumerate(layers, 1):
            chain.append(f"[{last}][{i}:v]overlay=0:0:enable='between(t,{t0},{t1})'[v{i}]"); last = f"v{i}"
        sh(cmd + ["-filter_complex", ";".join(chain), "-map", f"[{last}]", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)]); return out

    def run(self):
        target = float(self.brief["duration"]); shots = self.plan["shots"]; prev = 0.0; segs = []
        for s in shots:
            if abs(s["start"] - prev) > 1e-6: raise Blocked(f"샷 시간 불연속: {s['id']}")
            prev = s["end"]; dur = round(s["end"] - s["start"], 3); src = s["source"]
            if src["type"] == "motion":
                mf = self.A / f"MOTION-{s['id']}.mp4"
                if not mf.exists(): raise Blocked(f"{s['id']} 모션 렌더 없음: ap motion <ID> 먼저 실행")
                seg = self.seg_clip(s["id"], mf, dur, 0)
            elif src["type"] == "clip" and (self.A / f"{src['id']}.mp4").exists():
                seg = self.seg_clip(s["id"], self.A / f"{src['id']}.mp4", dur, src.get("clip_start", 0))
            elif src["type"] == "endcard":
                seg = self.seg_still(s["id"], self.endcard(), dur, "none")
            else:
                img_id = src.get("image") or src["id"]
                img = self.zoomed_still(img_id) if src.get("zoomed") else self.A / f"{img_id}.png"
                seg = self.seg_still(s["id"], img, dur, src.get("motion", "none"))
            layers = []
            for o in s.get("overlays", []):
                t0, t1 = o.get("t0", 0), o.get("t1", dur)
                if o["type"] == "caption": layers.append((self.caption(o), t0, t1))
                elif o["type"] == "tag": layers.append((self.tag(o.get("text", "예시")), t0, t1))
                elif o["type"] == "notify": layers.append((self.notify_card(tuple(o.get("at", (int(W * 0.5), int(H * 0.5625))))), t0, t1))
                elif o["type"] == "ui": layers.append((self.screen_ui(o["state"], o.get("zoomed", False)), t0, t1))
            segs.append(self.overlay(seg, layers))
        if abs(prev - target) > 1e-6: raise Blocked(f"샷 합계 {prev}초 ≠ brief {target}초")
        lst = self.R / "concat.txt"; lst.write_text("".join(f"file '{p}'\n" for p in segs))
        silent = self.R / "silent.mp4"; sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)])
        tol = max(0.1, len(shots) * 0.5 / FPS)  # 샷마다 반 프레임까지의 반올림은 허용
        require_duration(silent, target, "이어 붙인 영상", tol)
        cues = [(c["sfx"], round(s["start"] + c.get("t", 0), 3), c.get("gain_db", SFX_GAIN[c["sfx"]]))
                for s in shots for c in s.get("sfx_cues", []) if c["sfx"] in SFX]
        audio = self.plan.get("audio", {})
        bgm = (self.w / audio["bgm_file"]).resolve() if audio.get("bgm_file") else None
        if bgm and (not bgm.is_relative_to(self.w.resolve()) or not bgm.is_file()):
            raise Blocked("BGM은 제작 폴더 내부 실제 음원 파일이어야 합니다")
        if bgm and not all(str(audio.get(k, "")).strip() for k in ("source", "license")):
            raise Blocked("BGM 출처·사용권 근거를 계획과 권리 원장에 인계하세요")
        if not bgm and not str(audio.get("music_omission_reason", "")).strip():
            raise Blocked("광고 BGM이 없습니다. 실제 음원을 준비하거나 사용자 무음 요청/생략 이유를 기록하세요")
        mix = build_audio(self.R, self.w / "voice/voice.mp3", cues, target,
                          bgm=bgm, bgm_gain_db=float(audio.get("bgm_gain_db", -19)))
        (self.R / "audio/audio-source.json").write_text(json.dumps(audio, ensure_ascii=False, indent=2))
        out = self.R / f"{self.pid}_draft.mp4"
        sh(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(mix), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-t", str(target), "-movflags", "+faststart", str(out)])
        require_duration(out, target, "최종 영상", tol); require_duration(out, target, "최종 음성", stream="a:0")
        self.frame_sheet(out, shots); print(json.dumps({"status": "RENDERED", "video": str(out)}, ensure_ascii=False)); return out

    def frame_sheet(self, video, shots):
        F = self.R / "frames"; F.mkdir(exist_ok=True); tiles = []
        for s in shots:
            p = F / f"{s['id']}.jpg"; t = (s["start"] + s["end"]) / 2
            sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", str(p)]); tiles.append(Image.open(p).resize((480, 270) if landscape() else (270, 270) if W == H else (270, 480)))
        tw, th = tiles[0].size; cols = 4 if landscape() else 7
        sheet = Image.new("RGB", (tw * cols, th * ((len(tiles) + cols - 1) // cols)), "black")
        for i, im in enumerate(tiles): sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
        sheet.save(self.R / "frame_sheet.jpg", quality=85)


# ---------- 효과음: FFmpeg 합성(비용·라이선스 없음) ----------
SR = 48000
SFX = {  # 이름: (lavfi 소스, 길이초). 화면의 분명한 사건에 붙는 짧고 맑은 소리만.
    "click": (f"aevalsrc='0.8*sin(2*PI*2000*t)*exp(-t*120)+0.3*(random(0)*2-1)*exp(-t*300)':s={SR}:d=0.06", 0.06),
    "pop": (f"aevalsrc='0.6*sin(2*PI*(500+2400*t)*t)*exp(-t*28)':s={SR}:d=0.18", 0.18),
    "rise": (f"aevalsrc='0.28*sin(2*PI*(300*t+(900/1.4)*t*t/2))*sin(PI*t/1.4)':s={SR}:d=1.4", 1.4),
    "error": (f"aevalsrc='0.45*(sin(2*PI*233*t)*lt(t,0.11)+sin(2*PI*175*t)*gt(t,0.15)*lt(t,0.3))':s={SR}:d=0.32", 0.32),
    "snap": (f"aevalsrc='0.55*sin(2*PI*1320*t)*exp(-t*18)+0.3*sin(2*PI*1980*t)*exp(-t*22)':s={SR}:d=0.4", 0.4),
    "notify": (f"aevalsrc='0.5*sin(2*PI*988*t)*exp(-t*6)+0.5*sin(2*PI*1319*(t-0.14))*exp(-(t-0.14)*6)*gt(t,0.14)':s={SR}:d=0.9", 0.9),
    "outro": (f"aevalsrc='(sin(2*PI*523*t)+sin(2*PI*659*t)+sin(2*PI*784*t))/3*0.45*exp(-t*1.4)*min(1,t*25)':s={SR}:d=2.2", 2.2),
}
# 노이즈 합성음(종이·펜·타이핑·whoosh)은 "쓸리는 잡음"으로 들려 제거(2026-10-02 사용자 피드백). 맑은 사건음만 둔다.
SFX_GAIN = {"click": -18, "pop": -19, "rise": -22, "error": -19, "snap": -18, "notify": -16, "outro": -20}


def sfx_file(rdir, name):
    d = rdir / "sfx"; d.mkdir(exist_ok=True); p = d / f"{name}.wav"
    if not p.exists():
        src, dur = SFX[name]
        sh(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", src, "-af", f"afade=t=out:st={max(dur-0.03,0)}:d=0.03", "-ac", "1", "-ar", str(SR), str(p)])
    return p


def build_audio(rdir, voice, cues, target, bgm=None, bgm_gain_db=-19):
    """cues: [(name, 절대초, gain_dB)] → sfx 스템 + 최종 믹스. 스템은 분리 보존."""
    adir = rdir / "audio"; adir.mkdir(exist_ok=True)
    vstem = adir / "voice_stem.wav"
    sh(["ffmpeg", "-y", "-v", "error", "-i", str(voice), "-af", f"apad,atrim=0:{target}", "-ac", "1", "-ar", str(SR), str(vstem)])
    sstem = adir / "sfx_stem.wav"
    if cues:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono:d={target}"]
        chain = []
        for i, (name, t, g) in enumerate(cues, 1):
            cmd += ["-i", str(sfx_file(rdir, name))]
            ms = int(t * 1000); chain.append(f"[{i}:a]adelay={ms}:all=1,volume={g}dB[s{i}]")
        mix = "".join(f"[s{i}]" for i in range(1, len(cues) + 1))
        chain.append(f"[0:a]{mix}amix=inputs={len(cues)+1}:normalize=0:duration=first,atrim=0:{target}[o]")
        sh(cmd + ["-filter_complex", ";".join(chain), "-map", "[o]", str(sstem)])
    else:
        sh(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono:d={target}", str(sstem)])
    mixf = adir / "mix.wav"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(vstem), "-i", str(sstem)]
    if bgm is not None:
        bstem = adir / "bgm_stem.wav"
        sh(["ffmpeg", "-y", "-v", "error", "-i", str(bgm), "-af",
            f"apad,atrim=0:{target},volume={bgm_gain_db}dB,afade=t=in:d=0.08,afade=t=out:st={max(0,target-0.5)}:d=0.5",
            "-ac", "2", "-ar", str(SR), str(bstem)])
        cmd += ["-i", str(bstem)]
        chain = "[0:a]asplit=2[spoken][control];[2:a][control]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=250[bed];[spoken][1:a][bed]amix=inputs=3:normalize=0:duration=first"
    else:
        chain = "[0:a][1:a]amix=inputs=2:normalize=0:duration=first"
    # 스튜디오 웹 믹스 권장값; 플랫폼의 보편 공식 규격이 아니다.
    # 무음/측정 불가 입력에 loudnorm을 강제하면 NaN/클리핑이 생길 수 있다.
    meter = subprocess.run(cmd + ["-v", "info", "-filter_complex", chain + ",loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json[o]",
                                  "-map", "[o]", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=180)
    if meter.returncode:
        raise Blocked("믹스 라우드니스 측정 실패: " + meter.stderr[-1200:])
    start, end = meter.stderr.rfind("{"), meter.stderr.rfind("}")
    try:
        measured = json.loads(meter.stderr[start:end+1])
        measurable = all(math.isfinite(float(measured[k]))
                         for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"))
    except (ValueError, KeyError):
        raise Blocked("믹스 라우드니스 측정 결과 누락/오류")
    (adir / "normalization-input.json").write_text(json.dumps({"measurement": measured,
        "status": "MEASURED" if measurable else "UNMEASURABLE_NORMALIZATION_SKIPPED",
        "target_source": "STUDIO_RECOMMENDATION_NOT_PLATFORM_STANDARD", "target_lufs": -16,
        "observed_audio": False, "note": "정규화 전 입력 측정. 인코딩 후 측정/실제 청취는 별도."}, ensure_ascii=False, indent=2))
    if measurable:
        chain += (",loudnorm=I=-16:TP=-1.5:LRA=11:linear=true"
                  f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
                  f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
                  f":offset={measured['target_offset']}")
    chain += f",alimiter=limit=0.89:level=false,afade=t=out:st={max(0,target-0.3)}:d=0.3[o]"
    sh(cmd + ["-filter_complex", chain, "-map", "[o]", "-ar", str(SR), str(mixf)])
    (adir / "cues.json").write_text(json.dumps([{"sfx": n, "t": t, "gain_db": g} for n, t, g in cues], ensure_ascii=False, indent=2))
    return mixf


def cmd_previews(pid):
    """Extract current 3/8-second previews; never claim real observation."""
    w, _ = paths(pid)
    video = w / "render" / f"{pid}_draft.mp4"
    if not video.is_file():
        raise Blocked("현재 초안 렌더가 없어 훅/시제품을 추출할 수 없습니다")
    preview = w / "render/previews"; preview.mkdir(exist_ok=True)
    files = []
    for seconds, name in [(3, "hook3"), (8, "prototype8")]:
        out = preview / (name + ".mp4")
        sh(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-t", str(seconds),
            "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(out)])
        files.append(str(out))
    print(json.dumps({"status":"PREVIEWS_EXTRACTED_NOT_QA", "files":files,
                      "observed_video":False, "observed_audio":False}, ensure_ascii=False))
    return files


def cmd_motion(pid):
    """shot.source.type == "motion" 장면을 Remotion으로 렌더한다(motion/src). props 해시가 같으면 건너뛴다."""
    import hashlib as _h
    w, brief = paths(pid); plan = json.loads((w / "plan.json").read_text()); A = w / "assets"
    shots = [s for s in plan["shots"] if s.get("source", {}).get("type") == "motion"]
    if not shots: print(json.dumps({"status": "NO_MOTION_SHOTS"})); return
    if not motion_ready(): raise Blocked("모션 엔진(Remotion) 미설치: cd motion && npm install")
    fonts = A / "fonts"; fonts.mkdir(parents=True, exist_ok=True)
    for f in [F_BOLD, F_MED, str(FONTS / "GmarketSansTTFLight.ttf")]:
        if Path(f).exists() and not (fonts / Path(f).name).exists(): shutil.copy2(f, fonts / Path(f).name)
    r = Renderer(pid); done = []
    for s in shots:
        scene = json.loads(json.dumps(s["source"]["scene"]))
        for l in scene.get("layers", []):  # "box": "screen" → 측정한 화면 위치
            if l.get("box") == "screen":
                if not r.screen: raise Blocked("screen_image에서 화면 영역을 찾지 못했습니다")
                l["box"] = r.screen
        cam = scene.get("camera")
        if cam and cam.get("origin") == "screen" and r.screen:
            cam["origin"] = {"x": r.screen["x"] + r.screen["w"] / 2, "y": r.screen["y"] + r.screen["h"] / 2}
        props = {"width": W, "height": H, "fps": FPS, "durationInFrames": int(round((s["end"] - s["start"]) * FPS)), **scene}
        validate_motion_scene(scene, A, props["durationInFrames"])
        for l in scene.get("layers", []):  # 값→픽셀 매핑을 props에 남겨 렌더와 검수가 같은 수치를 쓴다
            if l["type"] == "data_bars": l["mapping"] = data_bar_mapping(l)
        pj =A / f"MOTION-{s['id']}.props.json"; out = A / f"MOTION-{s['id']}.mp4"
        digest = _h.sha256(json.dumps(props, sort_keys=True).encode()).hexdigest()
        if out.exists() and pj.exists() and json.loads(pj.read_text()).get("_digest") == digest: continue
        pj.write_text(json.dumps({**props, "_digest": digest}, ensure_ascii=False, indent=2))
        sh(["npx", "remotion", "render", "src/index.ts", "Scene", str(out), f"--props={pj}", f"--public-dir={A}",
            "--codec=h264", "--crf=16", "--log=error"], cwd=MOTION_DIR)
        done.append(s["id"])
    print(json.dumps({"status": "MOTION_RENDERED", "rendered": done, "motion_shots": [s["id"] for s in shots]}, ensure_ascii=False))


def cmd_render(pid):
    return Renderer(pid).run()


# ---------- finish ----------
SHOT_KEYS = ["id", "start", "end", "purpose", "visual_focus", "subject", "event", "movement", "new_information", "next_reason", "camera", "caption", "sfx", "assets"]


def cmd_finish(pid):
    w, brief = paths(pid); plan = json.loads((w / "plan.json").read_text()); A, R = w / "assets", w / "render"
    shots = [{k: s.get(k, [] if k in ("caption", "sfx", "assets") else "") for k in SHOT_KEYS} for s in plan["shots"]]
    for s, p in zip(shots, plan["shots"]):
        s["caption"] = [o["text"] for o in p.get("overlays", []) if o["type"] == "caption"]
        s["assets"] = s["assets"] or [p["source"].get("id") or p["source"].get("image")]
    (w / "shot.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2))
    caps = [{"start": round(p["start"] + o.get("t0", 0), 2), "end": round(p["start"] + o.get("t1", p["end"] - p["start"]), 2), "text": o["text"]}
            for p in plan["shots"] for o in p.get("overlays", []) if o["type"] == "caption"]
    (w / "captions.json").write_text(json.dumps({"production_id": pid, "captions": caps}, ensure_ascii=False, indent=2))

    def bundle(name, files):
        with zipfile.ZipFile(w / name, "w") as z:
            for f in files:
                if f.exists(): z.write(f, f.relative_to(w) if f.is_relative_to(w) else f.name)
    bundle("asset-bundle.zip", sorted(A.glob("IMG-*.png")) + [A / "ENDCARD.png", w / "plan.json"] + sorted(A.glob("IMG-*.json")))
    bundle("audio-bundle.zip", sorted((R / "audio").glob("*")) + sorted((R / "sfx").glob("*.wav")))
    bundle("motion-bundle.zip", sorted(A.glob("CLIP-*.mp4")) + sorted((R / "segments").glob("*.mp4")) + [Path(__file__)])
    order = [("RESEARCH", "research.json", "research-subagent"), ("FACT", "fact.json", "fact-rights"), ("SCRIPT", "script.json", "story-script"),
             ("VOICE", "voice/voice-bundle.zip", "voice"), ("SHOT", "shot.json", "director"), ("ASSET", "asset-bundle.zip", "art"),
             ("MOTION", "motion-bundle.zip", "motion"), ("CAPTION", "captions.json", "editor-caption"),
             ("AUDIO", "audio-bundle.zip", "audio"), ("VIDEO", f"render/{pid}_draft.mp4", "editor-caption")]
    for kind, f, author in order:
        out = sh([PY_STUDIO, "-m", "studio", "ingest", pid, kind, str(w / f), "--author", author], cwd=ROOT)
        if '"BLOCKED"' in out: raise Blocked(f"{kind} 등록 차단: {out[-300:]}")
    saved = json.loads(sh([PY_STUDIO, "short/save_output.py", "--id", pid, "--tool", "claude"], cwd=ROOT))
    sys.path.insert(0, str(AD)); import budget; usage = budget.usage(pid)
    path = saved[0].get("path", "")
    notify(pid, f"초안 완성 ✅ {brief.get('topic', '')} · {brief['duration']}초\n저장: {path}\n사용량: {usage}\n남은 일: 사람 시청 후 Viewer QA·업로드 권리 확인")
    print(json.dumps({"status": "FINISHED_DRAFT", "short": path, "usage": usage}, ensure_ascii=False))


def cmd_review(pid):
    """AUTO_PROXY_REVIEW: 사람 시청을 대신하지 않는 자동 측정 근거. 결과는 render/auto-review.json."""
    import difflib
    w, brief = paths(pid); R = w / "render"; video = R / f"{pid}_draft.mp4"
    if not video.is_file(): raise Blocked("리뷰할 현재 렌더가 없습니다")
    def log(args):
        return subprocess.run(["ffmpeg", "-v", "info", "-i", str(video)] + args + ["-f", "null", "-"], capture_output=True, text=True).stderr
    freeze = re.findall(r"freeze_start: ([\d.]+).*?freeze_duration: ([\d.]+)", log(["-vf", "freezedetect=n=0.003:d=1.5", "-an"]), re.S)
    cuts = [float(x) for x in re.findall(r"lavfi.scd.time: ([\d.]+)", log(["-vf", "scdet=t=10,metadata=print", "-an"]))]
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", log(["-af", "ebur128", "-vn"]))
    out = R / "review_whisper"; sh([WHISPER, str(video), "--language", "ko", "--output-format", "txt", "--output-dir", str(out)])
    heard = (out / f"{video.stem}.txt").read_text().strip()
    script = json.loads((w / "script.json").read_text()).get("full_narration", "")
    norm = lambda t: re.sub(r"[^가-힣A-Za-z0-9]", "", t)
    ratio = round(difflib.SequenceMatcher(None, norm(script), norm(heard)).ratio(), 3)
    # 구도 변화 시점: plan의 샷 경계 중 소스가 바뀌거나 모션 카메라 배율이 0.15 이상 변하는 곳(scdet는 비슷한 색의 컷을 놓친다)
    plan = json.loads((w / "plan.json").read_text()) if (w / "plan.json").exists() else {"shots": []}
    def key(sh_):
        src = sh_.get("source", {}); sc = src.get("scene", {})
        img = (sc.get("background") or {}).get("src") if src.get("type") == "motion" else (src.get("id") or src.get("image"))
        return img, bool(src.get("zoomed"))
    changes = []
    for prev_s, cur in zip(plan["shots"], plan["shots"][1:]):
        cam = cur.get("source", {}).get("scene", {}).get("camera") or {}
        big_move = abs((cam.get("to") or {}).get("scale", 1) - (cam.get("from") or {}).get("scale", 1)) >= 0.15
        if key(prev_s) != key(cur) or big_move: changes.append(cur["start"])
    marks = changes or cuts
    gaps = [round(b - a, 2) for a, b in zip([0.0] + marks, marks + [float(brief["duration"])])]
    issues = []
    if freeze: issues.append(f"1.5초 이상 정지 구간 {len(freeze)}곳: " + ", ".join(f"{float(a):.1f}s({float(d):.1f}s)" for a, d in freeze))
    if gaps and max(gaps) > 4.0: issues.append(f"컷 없이 4초 넘는 구간 최대 {max(gaps)}초")
    if ratio < 0.85: issues.append(f"Whisper 재전사와 대본 일치율 {ratio} (발음·누락 의심)")
    if lufs and abs(float(lufs[-1]) + 16) > 2.5: issues.append(f"통합 음량 {lufs[-1]} LUFS (목표 약 -16)")
    rep = {"kind": "AUTO_PROXY_REVIEW", "status": "PARTIAL_EVIDENCE", "viewer_qa": "PENDING_HUMAN_VIEW",
           "freeze": freeze, "cut_times_scdet": cuts, "composition_changes": marks, "max_gap_s": max(gaps) if gaps else None, "integrated_lufs": lufs[-1] if lufs else None,
           "transcript_match": ratio, "heard": heard, "frame_sheet": "render/frame_sheet.jpg", "issues": issues,
           "note": "자동 측정은 사람의 실제 시청·청취를 대신하지 않는다"}
    (R / "auto-review.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2))
    print(json.dumps({"status": "REVIEWED", "issues": issues, "transcript_match": ratio}, ensure_ascii=False))


def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    cmd, pid = sys.argv[1], sys.argv[2]
    if not pid.startswith("claude-"): sys.exit("Claude 제작 ID는 claude- 로 시작해야 합니다")
    try:
        if cmd == "notify": notify(pid, " ".join(sys.argv[3:]))
        elif cmd == "all":
            cmd_assets(pid); cmd_motion(pid); cmd_render(pid); cmd_previews(pid); cmd_review(pid); cmd_finish(pid)
        else: {"voice": cmd_voice, "assets": cmd_assets, "render": cmd_render, "previews": cmd_previews,
               "review": cmd_review, "motion": cmd_motion, "finish": cmd_finish}[cmd](pid)
    except Blocked as e:
        print("BLOCKED:", e); notify(pid, f"⛔ 중단 ({cmd}): {str(e)[:500]}"); sys.exit(2)
    except Exception as e:  # 예상 못 한 오류도 알림 없이 죽지 않게 한다
        print("ERROR:", type(e).__name__, e); notify(pid, f"⛔ 오류 ({cmd}): {type(e).__name__}: {str(e)[:400]}"); sys.exit(3)


if __name__ == "__main__":
    main()
