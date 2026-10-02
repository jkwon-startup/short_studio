"""제작 계약·의존성·입력 검증."""
import hashlib, json, re, shutil
from pathlib import Path
KINDS = ("RESEARCH", "FACT", "SCRIPT", "SHOT", "ASSET", "MOTION", "VOICE", "CAPTION", "AUDIO", "VIDEO")
DEPS = {"RESEARCH": (), "FACT": ("RESEARCH",), "SCRIPT": ("RESEARCH", "FACT"),
        "SHOT": ("SCRIPT",), "ASSET": ("SHOT", "FACT"), "MOTION": ("SHOT", "ASSET"),
        "VOICE": ("SCRIPT",), "CAPTION": ("SCRIPT", "VOICE"),
        "AUDIO": ("VOICE", "FACT"), "VIDEO": ("MOTION", "AUDIO", "CAPTION")}
GATES = ("Research", "Fact", "Script", "Shot", "Asset", "Motion", "Caption", "Audio", "Technical QA", "Viewer QA")
SETTINGS = ("voice_model", "style", "speed", "shot_version", "asset_version", "caption_version", "render_version", "tool_versions")
PACKAGES = ("FINAL", "PROJECT", "ASSETS", "AUDIO", "SCRIPT", "SHOT", "RESEARCH", "QA", "FAIL", "LOG")
SHOT_FIELDS = ("id", "purpose", "visual_focus", "subject", "event", "movement", "new_information", "next_reason", "camera", "caption", "sfx", "assets", "start", "end")
class Blocked(RuntimeError): pass

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()).hexdigest()

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def safe_id(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise Blocked("ID는 영문·숫자·밑줄·하이픈, 최대 80자입니다")
    return value

def descendants(kind):
    result = {kind}
    while True:
        more = {k for k,v in DEPS.items() if set(v) & result}
        if more <= result: return result
        result |= more

def code_hash(root):
    paths = sorted((Path(root)/"studio").glob("*.py")) + sorted((Path(root)/"scripts").glob("*.py"))
    paths += sorted((Path(root)/".codex/agents").glob("*.toml")) + sorted((Path(root)/".agents/skills").glob("*/SKILL.md")) + sorted((Path(root)/"schemas").glob("*.json"))
    paths += sorted((Path(root)/"scripts/claude_adapters").glob("*.py"))
    paths += sorted((Path(root)/"scripts/claude_adapters").glob("*.sh"))
    # Creative policies are input decisions too: old QA must not survive a policy change.
    policy_files=("config/studio.json", "config/claude-autopilot.json", "docs/advertising-creative-standard.md",
                  "docs/motion-design-standard.md", "docs/motion-genres.md", "docs/motion-delivery-spec.md",
                  "docs/motion-review-protocol.md", "docs/short-form-design-and-music.md",
                  ".agents/skills/studio-story/references/narration-writing.md",
                  ".agents/skills/studio-produce/references/attention-and-pacing.md")
    paths += [Path(root)/name for name in policy_files if (Path(root)/name).is_file()]
    binaries={}
    for tool in ("python3", "ffmpeg", "ffprobe", "blender", "say"):
        executable=shutil.which(tool)
        if executable:
            p=Path(executable).resolve();stat=p.stat();binaries[tool]=[str(p),stat.st_size,stat.st_mtime_ns]
        else: binaries[tool]="MISSING"
    return digest({"files":{str(p.relative_to(root)):file_hash(p) for p in paths},"tools":binaries})

def validate_brief(brief):
    for field in ("production_id", "mode", "brand", "core_sentence", "viewer_question", "duration", "settings"):
        if field not in brief: raise Blocked("brief 누락: " + field)
    safe_id(brief["production_id"])
    if brief["mode"] not in ("fixture", "production"): raise Blocked("mode 오류")
    if not isinstance(brief["duration"],(int,float)) or not 0 < brief["duration"] <= 180: raise Blocked("분량은 0~180초입니다")
    if brief["mode"] == "production" and (not brief["core_sentence"] or not brief["viewer_question"]): raise Blocked("핵심 문장·시청자 질문이 필요합니다")
    for field in SETTINGS:
        if field not in brief["settings"]: raise Blocked("캐시 설정 누락: " + field)
    if not isinstance(brief["settings"]["speed"],(float,int)) or brief["settings"]["speed"] <= 0: raise Blocked("음성 속도 오류")

def validate_shots(shots, duration):
    if not isinstance(shots,list) or not shots: raise Blocked("Shot 목록이 필요합니다")
    previous=0
    for shot in shots:
        missing=set(SHOT_FIELDS)-set(shot)
        if missing: raise Blocked("Shot 필드 누락: " + str(sorted(missing)))
        if shot["start"] != previous or not shot["start"] < shot["end"] <= duration: raise Blocked("Shot 시간·연속성 오류")
        previous=shot["end"]
    if previous != duration: raise Blocked("Shot 총 분량 불일치")
