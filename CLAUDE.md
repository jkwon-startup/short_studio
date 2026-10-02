# short_studio — Claude Code 지침

## 0. 공통 지침 먼저

**어떤 작업이든 시작하기 전에 공통 지침 `AGENTS.md`를 먼저 읽고 따른다.** Codex와 Claude가 같은 지침·원장·검수 계약을 쓴다. 이 파일은 공통 지침에 없는 Claude Code 전용 차이만 적는다. 둘이 충돌하면 `AGENTS.md`가 우선하고, 충돌을 발견하면 이 파일을 공통 지침에 맞게 고친다.

@AGENTS.md

## 1. Claude Code 전용 차이

공통 지침의 자동 진행·승인 재사용·저장·검수 규칙을 그대로 적용한다. 아래는 Claude Code에서만 필요한 실행 방식이다.

- **제작 ID**: Claude가 만드는 제작은 `claude-` 접두어로 시작한다(예: `claude-20261005-ai-tip`). `claude-`로 시작하지 않는 `runs/<id>/`는 Codex 제작이므로 읽기만 하고 ingest/qa/recover/release를 실행하지 않는다.
- **역할과 스킬 위치**: 역할 원본은 `.codex/agents/*.toml`, Claude용 변환본은 `.claude/agents/*.md`다. 역할을 고칠 때는 두 파일을 함께 고친다. `.claude/skills`는 `.agents/skills` 심볼릭 링크라서 스킬은 한 곳만 고친다.
- **Producer = 메인 세션**: `.claude/agents/`의 서브에이전트는 모두 읽기 전용이다. 파일 저장, `python3 -m studio ...`, 렌더는 메인 세션이 한다. 서브에이전트는 작업 폴더 밖을 읽지 못하므로 필요한 외부 소스는 `work/<ID>/sources/`에 복사해서 넘긴다.
- **자동 진행 기본값**: 공통 지침의 자동 진행에서 Producer가 고르는 기본값은 `config/claude-autopilot.json`(공개 범용값) 위에 `config/local.json`(설치 마법사가 만든 개인 브랜드·목소리·한도·승인, 깃 제외)을 덮어 쓴다. 개인 값은 local.json에서만 고친다.
- **무인 제작 진입점**: `/short-auto 주제=… 브랜드=… 대상=…` (`.claude/commands/short-auto.md`). 창작 단계는 Claude가, 대본 이후 기계 단계는 `scripts/claude_adapters/autopilot.py`(voice/assets/render/previews/review/finish/all/notify, 실행은 `bash scripts/claude_adapters/ap <명령> <ID>`)가 한다. 테스트할 때는 `AUTOPILOT_NO_NOTIFY=1`로 Slack 알림을 끈다.
- **모션그래픽 엔진**: `motion/`(Remotion). plan.json의 `source.type: "motion"` 샷은 `ap motion <ID>`가 렌더한다. 장면 props와 컴포넌트는 `motion/README.md`.
- **Claude 어댑터**: `scripts/claude_adapters/`의 `elevenlabs_tts.py`(키는 macOS 키체인 `elevenlabs-api-key`), `pixverse_image.sh`(Pixverse CLI, 레퍼런스 이미지 지원), `test_connections.py`. 비용 한도는 `budget.py`가 막는다: 승인 한도는 `config/local.json`(없으면 공개 기본값)에서 읽고, 사용량은 `usage/`에 쌓으며, 하루 총량(1편 한도 × `max_shorts_per_day`)도 센다. `work/<ID>/brief.json`의 `budget_caps`는 한도를 낮출 수만 있다.
- **글자 레이어**: 로컬 FFmpeg에 drawtext가 없으므로 자막·UI·엔드카드 글자는 Pillow가 있는 Python(`config/local.json`의 `python_pillow`, 래퍼 `scripts/claude_adapters/ap`가 자동 선택)로 PNG를 만들어 얹는다. 폰트는 Gmarket Sans.
- **권한**: 무인 실행에 필요한 명령은 `.claude/settings.json` 허용 목록에 있다. 예약 실행(`scripts/setup/run_scheduled.sh`)은 웹 조사 세션(웹 도구만)과 제작 세션(웹 없음, 셸은 허용 목록만, 쓰기는 `work/`만)을 나눠 돌리고 `scripts/setup/unattended-settings.json`으로 추가 차단한다. 무인 실행에 `Bash` 전체 허용을 다시 넣지 않는다. 새 명령 형태가 필요하면 목록에 추가하고, `cd … &&` 같은 묶음 명령 대신 허용된 형태로 실행한다.
- **git**: 사용자 요청 없이 commit·push하지 않는다. 공개 배포는 `scripts/publish/build_release.py`로 개인정보 검사 후 별도 배포 폴더에서만 한다.
- **알림**: 제작 알림은 Slack 웹훅만 사용한다(Telegram 금지는 공통 지침).

## 광고 창작 방향

실사풍 광고 기본값과 모션그래픽 선택·전문 검수는 AGENTS.md 및 docs/advertising-creative-standard.md를 따른다. 실행 한도와 도구별 승인 범위는 그대로 유지한다. config/local.json의 브랜드·인물·엔드카드는 그 브랜드의 기본값이며, 다른 브랜드/대상에는 brief와 브랜드 자료에 맞게 인물·공간·톤·엔드카드를 재설계한다.
