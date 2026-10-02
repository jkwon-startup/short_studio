#!/usr/bin/env bash
# Pixverse CLI 어댑터 (Claude Code 전용).
# 텍스트 없는 이미지 / image-to-video. 비율은 PIXVERSE_ASPECT(기본 9:16, autopilot이 brief.format으로 설정). 한도·사용량은 budget.py(승인 한도는 config, 사용량은 usage/).
#
# 사용:
#   pixverse_image.sh image PRODUCTION_ID OUT.png "프롬프트" [REF.png]
#   pixverse_image.sh video PRODUCTION_ID IN.png OUT.mp4 "모션 프롬프트" [초=5]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIXVERSE_REAL="${PIXVERSE_REAL:-$HOME/.claude/tools/pixverse/node_modules/pixverse/dist/index.js}"
[ -f "$PIXVERSE_REAL" ] || { echo "BLOCKED: Pixverse CLI 없음 ($PIXVERSE_REAL)"; exit 2; }
px() { node "$PIXVERSE_REAL" "$@"; }
ASPECT="${PIXVERSE_ASPECT:-9:16}"; FRAMING="${PIXVERSE_FRAMING:-Vertical $ASPECT}"

NO_TEXT="No text, no letters, no captions, no UI words, no logos in the image. Leave safe empty space at top and bottom for subtitles."

# 예산 확인 + 누적 (kind: pixverse_images | pixverse_clips)
charge() {
  python3 "$ROOT/scripts/claude_adapters/budget.py" charge "$1" "$2" || exit 2
}

# JSON 결과에서 결과 URL을 찾아 내려받는다
download() {
  local json="$1" out="$2"
  local url
  url="$(python3 -c 'import json,re,sys; s=open(sys.argv[1]).read(); m=re.findall(r"https://[^\"\s]+\.(?:png|jpg|jpeg|webp|mp4)[^\"\s]*", s); print(m[0] if m else "")' "$json")"
  [ -n "$url" ] || { echo "FAIL: 결과 URL 없음 ($json)"; exit 3; }
  curl -fsSL "$url" -o "$out"
}

mode="${1:-}"; shift || true
case "$mode" in
  image)
    id="$1"; out="$2"; prompt="$3"; ref="${4:-}"
    charge "$id" pixverse_images
    mkdir -p "$(dirname "$out")"
    refargs=(); [ -n "$ref" ] && refargs=(--image "$ref")
    px create image --prompt "$FRAMING composition. $prompt $NO_TEXT" -m gpt-image-2.0 --aspect-ratio "$ASPECT" ${refargs[@]+"${refargs[@]}"} --json > "$out.json" 2>"$out.log"
    download "$out.json" "$out"
    echo "SUCCESS image $out"
    ;;
  video)
    id="$1"; in="$2"; out="$3"; prompt="$4"; dur="${5:-5}"
    charge "$id" pixverse_clips
    mkdir -p "$(dirname "$out")"
    px create video --image "$in" --prompt "$prompt. Stable composition, no new text, preserve subject." \
      -m v6 --aspect-ratio "$ASPECT" -d "$dur" --no-audio --json > "$out.json" 2>"$out.log"
    download "$out.json" "$out"
    echo "SUCCESS video $out"
    ;;
  *)
    echo "usage: $0 image ID OUT.png PROMPT | video ID IN.png OUT.mp4 PROMPT [SECONDS]"; exit 1 ;;
esac
