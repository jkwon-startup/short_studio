# short_studio

한국어 영상 광고를 **설치 후 자동으로 계속 만드는** 로컬 제작 스튜디오입니다. 세로 9:16(쇼츠·릴스, 기본 30초), 가로 16:9(유튜브, 기본 60초), 정사각 1:1을 지원합니다([비율별 기준](docs/format-guide.md)). Codex와 Claude Code가 같은 지침·원장·검수 계약을 함께 씁니다. 14개 전문 역할(조사·사실/권리·대본·연출·아트·3D·모션·음성·오디오·편집·기술 QA·시청자 QA·복구/출고)과 10개 공통 스킬, 버전 원장, 독립 QA와 FINAL 출고 게이트를 제공합니다.

- **기본 방향**: 실사풍 광고. 영상미·속도감·탁월한 카피([광고 기준](docs/advertising-creative-standard.md))
- **필요하거나 요청할 때**: 전문가 수준 모션그래픽([모션 기준](docs/motion-design-standard.md)). Remotion 기반 렌더러 [motion/](motion/README.md)가 화면 UI 애니메이션·키네틱 타이포·카메라 푸시/드리프트를 모션 토큰(이징·시차·스프링)으로 렌더합니다
- **대본**: 말 먼저, 장면은 나중. AI 문체를 걸러 내는 [내레이션 기준](.agents/skills/studio-story/references/narration-writing.md)(한국어 AI 문체 분류는 [im-not-ai](https://github.com/epoko77-ai/im-not-ai), MIT를 요약·각색)

## 동작 방식

```
주제 ─▶ 조사·사실확인 ─▶ 대본(훅 3·초안 2·체크리스트) ─▶ 음성(ElevenLabs) ─▶ 시간 측정(Whisper)
     ─▶ 샷 설계(plan.json) ─▶ 이미지·클립(Pixverse) ─▶ 모션 장면(Remotion) ─▶ 합성·자막·효과음·음량 정규화(FFmpeg)
     ─▶ 자동 대리 검수 ─▶ 원장 등록 ─▶ short/날짜/시간_도구_ID/완성본.mp4 ─▶ Slack 알림
```

창작 단계는 Codex/Claude가, 기계 단계는 `scripts/claude_adapters/autopilot.py`가 맡습니다. 실행 중에는 사용자에게 묻지 않고, **비용 한도 초과·인증 만료·같은 원인의 반복 실패**에서만 멈춥니다. 실제 시청이 필요한 Viewer QA는 사람 확인 대기로 남기고, 그 전에는 FINAL로 출고하지 않습니다.

## 요구 환경

macOS(Apple Silicon 권장), Python 3.11+, FFmpeg/FFprobe, Node(모션 엔진: `cd motion && npm install`), Pillow, Gmarket Sans 폰트(OFL), 그리고 다음 중 하나: [Claude Code](https://claude.com/claude-code) 또는 Codex CLI. 생성 서비스: Pixverse CLI(이미지·영상, 구독 필요), ElevenLabs(TTS). 선택: mlx-whisper(시간 측정·재전사), Blender(3D 장면).

## 설치 → 테스트 영상 → 자동 실행

```bash
git clone https://github.com/jkwon-startup/short_studio.git
cd short_studio
python3 -m unittest discover -s tests -q
python3 scripts/setup/setup.py
```

설치 마법사가 한 번에 진행합니다.

1. **환경 점검**: 필수 도구·폰트·Pillow·Pixverse·Whisper 확인
2. **선택**: 제작 도구(Claude/Codex), **화면 비율과 기본 길이**, 실행 위치, 일정(요일·시각), 주제 방식, 브랜드(이름·대상·슬로건·강조색·톤), 기본 목소리, 1편당 비용 한도
3. **로그인과 키**: Pixverse 브라우저 로그인, ElevenLabs API 키와 Slack 웹훅을 macOS 키체인에 저장(파일에 남기지 않음)
4. **테스트 영상 1편**을 실제로 제작
5. **승인**: 영상을 보고 듣고 승인하면, 플랜별 상업 이용 조건 확인 여부와 함께 기록
6. **자동 실행 등록**
   - `server`: 이 맥(맥북·맥미니)의 launchd에 등록, 정해진 시각에 `scripts/setup/run_scheduled.sh` 실행
   - `app`: Claude 앱 예약 작업 또는 Codex 앱 Automations에 넣을 문장을 안내

개인 값과 승인 기록은 `config/local.json`, 주제 목록은 `config/topics.txt`에만 저장되며 둘 다 깃에서 제외됩니다(형식은 [config/local.example.json](config/local.example.json)). 주제는 `config/topics.txt`에 한 줄씩 추가합니다.

```
[ ] 바이브코딩으로 1인 창업 시작하기 | 예비 창업자
[ ] 퇴근 후 1시간 AI 자동화 | 직장인
```

수동 실행: Claude Code에서 `/short-auto 주제=… 브랜드=… 대상=… [형식=16:9 길이=60]`, Codex에서 `pipeline-short-studio`로 Producer 지휘 요청.

## 결과물

`short/YYYY-MM-DD/HH-MM-SS_도구_제작ID/`에 **`완성본.mp4`(영상+음성)**가 맨 위에 있고, 대본·음성·이미지·오디오 스템·원본 위치가 함께 복사됩니다. 원본은 `runs/`·`work/`에 그대로 남고 이전 버전도 보존됩니다. `short/INDEX.md`에서 전체 목록과 완성본 링크를 볼 수 있습니다.

## 사용권과 비용

- Remotion은 개인·3인 이하 팀은 무료, 그보다 큰 영리 조직은 Company License가 필요합니다.

- Pixverse·ElevenLabs·음악·폰트 등 제3자 결과물에는 각 서비스 약관이 적용됩니다. 무료 플랜은 상업 이용이 제한될 수 있습니다(예: ElevenLabs 무료 플랜은 비상업 + 출처 표기). 업로드 전에 직접 확인하세요.
- 비용은 어댑터가 호출 전에 막습니다. 1편 한도(`budget_caps`: 이미지·클립·TTS 글자 수)와 하루 총량(1편 한도 × `max_shorts_per_day`)을 `config/local.json`에서 읽고, 사용량은 `usage/`에 쌓습니다. 제작 폴더의 brief는 한도를 낮출 수만 있습니다.
- 예약 실행은 웹을 읽는 조사 세션과 명령을 실행하는 제작 세션을 나눕니다. 제작 세션은 웹 도구가 없고 셸은 `.claude/settings.json` 허용 목록만 쓰며, 1회 실행 시간 한도(`max_run_minutes`)와 중복 실행 잠금이 있습니다. Codex 경로에는 이 분리가 아직 없습니다.
- 효과음은 FFmpeg로 합성해 비용·사용권 문제가 없습니다. BGM은 사용권이 확인된 음원만 씁니다.

## 검수와 복구

현재 버전의 Research·Fact·Script·Shot·Asset·Motion·Caption·Audio·Technical QA·Viewer QA가 모두 PASS여야 FINAL을 만듭니다. 자동 대리 검수(`ap review`: 정지 구간·컷 간격·음량·재전사 대조)는 부분 근거이며 실제 시청을 대신하지 않습니다. 실패 기록은 지우지 않고 `recover`가 영향받는 단계만 다시 계획합니다. [운영 매뉴얼](docs/운영매뉴얼.md) · [아키텍처](docs/아키텍처.md)

## 라이선스

프로젝트 코드와 문서는 [MIT License](LICENSE)입니다. 포함하지 않은 제3자 도구·모델·폰트·에셋의 권리는 이 라이선스가 대신 부여하지 않습니다.
