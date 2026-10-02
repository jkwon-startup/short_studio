"""비용 한도와 사용량 기록 (유료 호출 전에 어댑터가 부른다).

- 한도는 설정에서만 읽는다: config/local.json의 approved.budget_caps → budget_caps → 공개 기본값(config/claude-autopilot.json).
  work/<ID>/brief.json의 budget_caps는 그 값을 낮출 수만 있고 올릴 수 없다.
- 사용량은 usage/<ID>.json과 usage/daily-YYYY-MM-DD.json에 쌓는다. 제작 폴더(work/) 밖이라 제작 중인 에이전트가 고쳐 쓰는 경로가 아니다.
- 하루 총량 = 1편 한도 × max_shorts_per_day(기본 3). 새 제작 ID를 만들어도 하루 총량은 이어진다.

  python3 scripts/claude_adapters/budget.py charge <ID> <kind> [수량]   # 초과면 BLOCKED 출력, 종료 코드 2
  python3 scripts/claude_adapters/budget.py show [ID]
"""
import fcntl, json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KINDS = ("pixverse_images", "pixverse_clips", "elevenlabs_chars")
ADHOC = "adhoc"  # 제작 ID 없이 부른 호출(연결 시험 등)


class OverBudget(Exception):
    pass


def _json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else ({} if default is None else default)


def _config():
    return _json(ROOT / "config/local.json"), _json(ROOT / "config/claude-autopilot.json")


def approved_caps(fmt="9:16"):
    local, public = _config()
    caps = (local.get("approved") or {}).get("budget_caps") or local.get("budget_caps") \
        or (public.get("budget_caps_by_format") or {}).get(fmt) or public.get("budget_caps_per_short") or {}
    return {k: int(caps.get(k, 0)) for k in KINDS}


def daily_caps(fmt="9:16"):
    local, public = _config()
    if local.get("daily_budget_caps"): return {k: int(local["daily_budget_caps"].get(k, 0)) for k in KINDS}
    n = int(local.get("max_shorts_per_day") or public.get("max_shorts_per_day") or 3)
    return {k: v * n for k, v in approved_caps(fmt).items()}


def usage(production=None):
    return _json(ROOT / "usage" / f"{production or ADHOC}.json")


def charge(production, kind, amount=1, today=None):
    """한도 안이면 사용량을 올리고, 넘으면 아무것도 기록하지 않고 OverBudget."""
    pid = ADHOC if production is None else production
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", pid): raise ValueError(f"제작 ID 형식 오류: {production!r}")
    if kind not in KINDS or int(amount) <= 0: raise ValueError(f"한도 항목·수량 오류: {kind} {amount}")
    amount = int(amount)
    brief = _json(ROOT / "work" / pid / "brief.json")
    fmt = brief.get("format", "9:16")
    cap = approved_caps(fmt)[kind]
    lower = (brief.get("budget_caps") or {}).get(kind)
    if isinstance(lower, (int, float)) and not isinstance(lower, bool): cap = min(cap, int(lower))
    day_cap = daily_caps(fmt)[kind]
    udir = ROOT / "usage"; udir.mkdir(exist_ok=True)
    day = today or datetime.now().strftime("%Y-%m-%d")
    with open(udir / ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        per_file, day_file = udir / f"{pid}.json", udir / f"daily-{day}.json"
        per, total = _json(per_file), _json(day_file)
        if per.get(kind, 0) + amount > cap:
            raise OverBudget(f"{kind} 1편 한도 초과 ({per.get(kind, 0)}+{amount} > {cap})")
        if total.get(kind, 0) + amount > day_cap:
            raise OverBudget(f"{kind} 하루 한도 초과 ({total.get(kind, 0)}+{amount} > {day_cap})")
        per[kind] = per.get(kind, 0) + amount; total[kind] = total.get(kind, 0) + amount
        per_file.write_text(json.dumps(per, ensure_ascii=False, indent=2)); day_file.write_text(json.dumps(total, ensure_ascii=False, indent=2))
    mirror = ROOT / "work" / pid
    if mirror.is_dir(): (mirror / "usage.json").write_text(json.dumps(per, ensure_ascii=False, indent=2))  # 보기용 사본
    return per


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "charge":
        try:
            charge(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else 1)
        except (OverBudget, ValueError) as e:
            print(f"BLOCKED: {e}"); sys.exit(2)
    elif len(sys.argv) >= 2 and sys.argv[1] == "show":
        pid = sys.argv[2] if len(sys.argv) > 2 else None
        fmt = _json(ROOT / "work" / (pid or ADHOC) / "brief.json").get("format", "9:16")
        day = _json(ROOT / "usage" / f"daily-{datetime.now():%Y-%m-%d}.json")
        print(json.dumps({"production": usage(pid), "today": day, "caps": approved_caps(fmt), "daily_caps": daily_caps(fmt)}, ensure_ascii=False))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
