---
name: studio-story
description: 로컬 숏폼 studio-story 단계 운영
---

# 실행 계약

핵심 한 문장과 시청자 질문을 먼저 정한다. HOOK→EVENT→DISCOVERY→ESCALATION→PAYOFF를 사건 중심 Shot으로 만든다. 첫 3초에 장면 자체의 변화/충돌/의문을 만든다. 대본 변경은 SCRIPT 새 버전 ingest로 반영하고 VOICE/CAPTION/AUDIO/VIDEO STALE을 확인한다.

입력은 production ID와 현재 파일 경로/해시. 출력은 단계 컨텍스트, 산출물, 상태, 증거, 다음 단계 인계. 저장은 Producer가 `python3 -m studio ingest`로 수행한다. 실행 전에 `python3 -m studio status ID`와 `resume ID`를 확인한다. 미연결 어댑터는 BLOCKED로 남긴다. 전역 레지스트리 수정과 외부 공개는 별도 승인 대상이다.

## 내레이션 글쓰기 계약

대본을 쓰기 전에 [내레이션 글쓰기 기준](references/narration-writing.md)을 읽고 따른다. 핵심: 메시지 하나를 고정하고 콘텐츠 유형(가능성·경고·방법)에 맞는 말의 흐름을 고른다. 귀로만 들어도 이해되는 이어진 말을 먼저 쓰고 장면은 그 다음에 붙인다. 사실은 메시지를 받칠 때만 쓰고, AI 티 나는 표현(번역투·관용구·대구 반복·균일한 리듬)을 걸러 낸다. 훅 3개와 초안 2개를 체크리스트로 점검해 넘긴다. 대본 확정은 AGENTS.md "자동 진행과 승인 재사용"을 따른다(자동 제작이면 Producer 추천안이 사전 승인, 사용자가 검토를 요청한 제작만 확인 대기). 음성용 `tts_text`에는 숫자를 한글로 쓴다.

## 몰입·리듬 계약

제작·복구·검수 시 [공통 기준](../studio-produce/references/attention-and-pacing.md)을 읽는다. 주제 소개보다 구체적인 문제·충돌·결과로 첫 화면을 시작한다. 설명 문장을 행동·입력·결과·수정 비트로 바꾸고 다음 장면을 기다릴 이유와 읽기 시간을 설계한다. 컷 수를 채우거나 단순 배속으로 대본의 정보 공백을 감추지 않는다.

## 광고 창작·품질 계약

제작·복구·검수 전 [실사·카피·영상미 기준](../../../docs/advertising-creative-standard.md)을 읽는다. 타깃의 망설임 하나→가치 하나→근거→CTA의 광고 카피를 설계한다. im-not-ai 기준과 훅 3/초안 2를 유지하고 ad_copy_review와 장면/훅의 연결을 인계한다.

## 모션 단계 인계와 검수

모션이 포함된 작업은 [공통 모션 기준](../../../docs/motion-design-standard.md)을 읽고 해당 역할 범위에서 장르별 목적·사전 애니매틱·브랜드 모션 토큰을 인계한다. [정량·납품 기준](../../../docs/motion-delivery-spec.md)의 공식/권장/미확인을 구별하고 [2층 검수](../../../docs/motion-review-protocol.md)의 자동 증거와 실제 정상 속도 관찰을 분리한다. 미관찰은 해당 검수만 사람 확인 대기로 남기며 가능한 제작·수정·저장은 재승인 질문 없이 계속한다.
