"""공개 배포 폴더 만들기: 허용 경로만 복사 → 개인 값 일반화 → 개인정보·비밀값 검사 → 테스트.

  python3 scripts/publish/build_release.py <배포 폴더(기존 git clone)>

검사에 하나라도 걸리면 종료 코드 1로 멈춘다(커밋·푸시는 하지 않음).
"""
import re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INCLUDE = ["AGENTS.md", "CLAUDE.md", "LICENSE", "pyproject.toml", ".gitignore", ".env.example",
           "studio", "schemas", "examples", "tests", "agents", "config", "docs", "design-skills",
           ".agents", ".codex", ".claude/agents", ".claude/commands", ".claude/settings.json",
           "scripts", "short/save_output.py", "short/README.md", "motion"]
EXCLUDE_NAMES = {"node_modules", "out", "__pycache__", ".DS_Store", "local.json", "topics.txt", "settings.local.json", "publish-private-patterns.txt"}
EXCLUDE_DOCS = {"환경점검.md", "추가검증.md", "구축검증.md", "codex-vibecoding-design-audit-20261002.md"}  # 개인 환경 감사 기록
REPLACE = [
    (re.compile(r"/Users/[A-Za-z0-9._-]+/DEV/short_studio"), "<저장소 루트>"),
    (re.compile(r"/Users/[A-Za-z0-9._-]+/"), "~/"),
]
# 누구에게나 해당하는 패턴만 여기에 둔다. 본인 이름·계정명·ID 조각 같은 개인 패턴은
# config/publish-private-patterns.txt(깃 제외, 한 줄에 정규식 하나)에 적는다. 이 파일은 공개되므로 개인 값을 넣지 않는다.
FORBIDDEN = [r"/Users/[A-Za-z0-9._-]+", r"hooks\.slack\.com/services/[A-Za-z0-9/]+", r"xox[abp]-[A-Za-z0-9-]{10,}", r"sk-[A-Za-z0-9]{20,}",
             r"AKIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"[A-Za-z0-9._%+-]+@(?:gmail|naver|daum|kakao|hanmail|outlook|icloud)\.[a-z.]+"]
PRIVATE_PATTERNS = ROOT / "config/publish-private-patterns.txt"
TEXT_EXT = {".md", ".py", ".json", ".toml", ".sh", ".txt", ".template", ".yml", ".yaml", ""}


def copy(dst):
    for item in [p for p in dst.iterdir() if p.name != ".git"]:
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    for rel in INCLUDE:
        src = ROOT / rel
        if not src.exists(): continue
        target = dst / rel; target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, target, symlinks=True, ignore=lambda d, names: [n for n in names if n in EXCLUDE_NAMES or n in EXCLUDE_DOCS])
        else:
            shutil.copy2(src, target)
    link = dst / ".claude/skills"
    if not link.exists(): link.symlink_to("../.agents/skills")
    shutil.copy2(ROOT / "scripts/publish/README.public.md", dst / "README.md")
    (dst / "scripts/publish").mkdir(parents=True, exist_ok=True)
    for f in ["build_release.py", "README.public.md"]: shutil.copy2(ROOT / "scripts/publish" / f, dst / "scripts/publish" / f)


def sanitize(dst):
    for p in dst.rglob("*"):
        if ".git" in p.parts or not p.is_file() or p.is_symlink() or p.suffix not in TEXT_EXT: continue
        s = p.read_text(errors="ignore"); o = s
        for pat, rep in REPLACE: s = pat.sub(rep, s)
        if s != o: p.write_text(s)


def private_patterns():
    if not PRIVATE_PATTERNS.exists():
        print(f"알림: {PRIVATE_PATTERNS.relative_to(ROOT)} 없음 → 공통 패턴만 검사합니다. 본인 이름·계정명·ID를 걸러내려면 이 파일에 정규식을 적으세요.")
        return []
    return [l.strip() for l in PRIVATE_PATTERNS.read_text().splitlines() if l.strip() and not l.startswith("#")]


def scan(dst, patterns=None):
    hits = []; patterns = FORBIDDEN + private_patterns() if patterns is None else patterns
    for p in dst.rglob("*"):
        if ".git" in p.parts or not p.is_file() or p.is_symlink(): continue
        if p.suffix.lower() in {".mp4", ".mp3", ".wav", ".zip", ".png", ".jpg", ".blend"}: hits.append(f"미디어 파일: {p.relative_to(dst)}"); continue
        s = p.read_text(errors="ignore")
        for i, pat in enumerate(patterns):  # 개인 패턴은 출력에도 그대로 찍지 않는다
            name = pat if pat in FORBIDDEN else f"개인 패턴 #{i - len(FORBIDDEN) + 1}"
            for m in re.finditer(pat, s): hits.append(f"{p.relative_to(dst)}: {name}")
    return hits


def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    dst = Path(sys.argv[1]).resolve()
    if not (dst / ".git").exists(): sys.exit("배포 폴더는 git clone이어야 합니다")
    copy(dst); sanitize(dst)
    hits = scan(dst)
    if hits:
        print("개인정보·비밀값 검사 실패:"); [print("  -", h) for h in hits[:80]]; sys.exit(1)
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=dst, capture_output=True, text=True)
    print((r.stdout + r.stderr)[-600:])
    if r.returncode: sys.exit("테스트 실패")
    print("RELEASE_READY", dst)


if __name__ == "__main__":
    main()
