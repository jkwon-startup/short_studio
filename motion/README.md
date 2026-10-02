# motion — 모션그래픽 렌더러 (Remotion)

`plan.json`에서 `source.type: "motion"`인 샷을 렌더한다. `bash scripts/claude_adapters/ap motion <ID>`가 샷마다 props를 만들어 `npx remotion render`를 호출하고, 결과 `work/<ID>/assets/MOTION-<샷>.mp4`를 본 렌더가 클립처럼 이어 붙인다. 자막·태그·효과음·음량은 기존 렌더 단계가 그대로 얹는다.

설치(한 번): `cd motion && npm install` — Remotion 첫 렌더 때 Chrome Headless Shell을 내려받는다.

**라이선스**: Remotion은 개인·3인 이하 팀·비영리는 무료, 그보다 큰 영리 조직은 [Remotion Company License](https://www.remotion.dev/license)가 필요하다. 설치 전에 본인 조건을 확인한다.

## 설계 원칙

- 무대(배경 이미지 + 화면 UI)를 한 컨테이너로 카메라가 움직인다 → 확대해도 UI가 화면에 붙어 따라간다.
- 움직임은 `src/tokens.ts` 모션 토큰을 따른다(등장 `cubic-bezier(0.16,1,0.3,1)`, 연결 `(0.65,0,0.35,1)`, 시차 2~5f, UI 스프링 무오버슈트). 기준: `docs/motion-design-standard.md`.
- 모든 동작은 `useCurrentFrame()` 기반이라 같은 props면 같은 프레임이 나온다(결정적 렌더).

## 장면 props (`shot.source.scene`)

```json
{
  "background": {"type": "image", "src": "IMG-03.png"},
  "camera": {"from": {"scale": 1.08}, "to": {"scale": 1.3}, "start": 0, "end": 18, "origin": "screen", "ease": "enter"},
  "layers": [
    {"type": "app_screen", "box": "screen", "inputAt": -60, "typeAt": -40, "sendAt": -6, "buildAt": 10},
    {"type": "kinetic_text", "text": "혼자서도 시작합니다", "x": 540, "y": 300, "size": 76, "mode": "mask_up", "highlight": ["혼자서도"]},
    {"type": "notify_card", "x": 540, "y": 1080, "start": 12}
  ]
}
```

- 시간은 샷 기준 **프레임**(30fps). 음수면 앞 샷에서 이미 일어난 상태로 시작해 샷 사이 상태가 이어진다.
- `"box": "screen"`, `"origin": "screen"`은 `plan.screen_image`에서 측정한 화면 영역으로 자동 치환된다.
- `app_screen` 단계: `inputAt`(입력창 등장) → `typeAt`(입력 줄) → `sendAt`(전송) → `buildAt`(헤더·히어로·카드·버튼 순차 조립) → `misalignAt`(버튼 어긋남) → `realignAt`(스프링 복귀 + 링 + 체크).
- `kinetic_text`: 단어 단위 `word_rise` 또는 `mask_up`, 핵심어 한 가지 속성만 강조.
- `background.type`: `image`(assets 안 파일) / `color` / `transparent`.

## 장르 레이어

기준은 `docs/motion-genres.md`. 세 레이어 모두 카메라와 무관하게 화면 좌표에 놓인다.

```json
{"type": "logo_sting", "src": "LOGO.png", "x": 540, "y": 900, "width": 720, "accent": "#7FE0D2", "tagline": "내 손안의 모험"}
{"type": "data_bars", "box": {"x": 90, "y": 480, "w": 900, "h": 900}, "title": "제목", "unit": "%", "source": "기관명, 조사명(연도)",
 "items": [{"label": "A", "value": 20}, {"label": "B", "value": 87.5, "highlight": true}], "orientation": "vertical"}
{"type": "kinetic_full", "phrases": [{"text": "혼자서도", "at": 0}, {"text": "앱 하나쯤은\n만듭니다", "at": 30, "highlight": ["만듭니다"]}]}
```

- `logo_sting`: 선이 그어지고(0~10f) 그 선을 따라 로고가 드러난 뒤(~30f) 정착하고, 그다음 `tagline`이 단어 단위로 올라온다. 로고 이미지는 균일 배율과 가림만 쓰므로 비율·색이 바뀌지 않는다. 로고 파일(투명 PNG 권장)은 `work/<ID>/assets/`에 둔다. 정착 뒤 식별 시간을 남기려면 샷을 2초 이상으로 잡는다.
- `data_bars`: 0에서 시작하는 선형 축만 지원한다(축 절단·로그 없음). 숫자는 막대와 같은 진행도로 올라가 끝에서 원래 값과 같아지고, 오버슈트가 없다. `unit`과 `source`는 필수이며 출처는 화면 아래에 표시된다. `max`를 주면 그 값이 막대 전체 길이가 된다(최댓값보다 작으면 거부). `orientation`은 `vertical`(기본) 또는 `horizontal`. 항목은 1~6개, 0 이상 값만.
- `kinetic_full`: 구(의미 단위)마다 화면을 채운다. 글자 크기는 가장 긴 줄에 맞춰 자동으로 정해지고, 다음 구의 `at`에 맞춰 앞 구가 위로 밀려 나간다. `at`은 그 구가 발화되는 프레임으로 잡고, 구 사이는 12프레임 이상 띄운다. `highlight`는 띄어쓰기 단위 단어와 정확히 같아야 한다.

`ap motion`은 렌더 전에 장면을 점검한다. 지원하지 않는 레이어 타입, 출처·단위 없는 데이터, 없는 로고 파일, 너무 촘촘한 구 간격은 BLOCKED로 멈춘다. `data_bars`의 값→픽셀 매핑은 `assets/MOTION-<샷>.props.json`의 `mapping`에 남는다(검수 근거).

새 컴포넌트를 추가할 때는 `src/types.ts`에 레이어 타입을, `src/Scene.tsx`에 분기를, `scripts/claude_adapters/autopilot.py`의 `MOTION_LAYER_TYPES`에 이름을 추가한다.
