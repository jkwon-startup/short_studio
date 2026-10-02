---
name: studio-audio
description: 로컬 숏폼 studio-audio 단계 운영
---

# 실행 계약

VOICE/BGM/AMBIENCE/IMPACT/WHOOSH/OBJECT/TRANSITION SOUND 스템을 독립 저장한다. 필요한 스템만 사용하고 불필요한 소리로 빈 화면을 덮지 않는다. 실제 청취로 말 명료도/피로도/클리핑/시간 싱크를 검수한다. 전환 소리는 사건 의미와 연결한다.

입력은 production ID와 현재 파일 경로/해시. 출력은 단계 컨텍스트, 산출물, 상태, 증거, 다음 단계 인계. 저장은 Producer가 `python3 -m studio ingest`로 수행한다. 실행 전에 `python3 -m studio status ID`와 `resume ID`를 확인한다. 미연결 어댑터는 BLOCKED로 남긴다. 전역 레지스트리 수정과 외부 공개는 별도 승인 대상이다.

## 몰입·리듬 계약

제작·복구·검수 시 [공통 기준](../studio-produce/references/attention-and-pacing.md)을 읽는다. 말의 강세·쉼, 사건 소리, 필요한 음악과 의도적 정적을 비트에 맞춰 설계한다. 클릭·Whoosh 추가만으로 재미 개선을 주장하지 않는다. 음성이 필요한 콘셉트의 TTS가 미연결이면 무내레이션 초안의 한계를 밝히고 음성 완성은 BLOCKED로 남긴다.

## 광고 창작·품질 계약

제작·복구·검수 전 [실사·카피·영상미 기준](../../../docs/advertising-creative-standard.md)을 읽는다. 광고 기본의 실제 BGM/SFX와 인물 행동/컷/카피의 감정 곡선을 설계하고 음성 공간·강약·시작/끝을 믹스한다. 사용자 무음 요청은 우선하고 실제 청취 없는 음악 품질 PASS를 주지 않는다.

## 모션 단계 인계와 검수

모션이 포함된 작업은 [공통 모션 기준](../../../docs/motion-design-standard.md)을 읽고 해당 역할 범위에서 장르별 목적·사전 애니매틱·브랜드 모션 토큰을 인계한다. [정량·납품 기준](../../../docs/motion-delivery-spec.md)의 공식/권장/미확인을 구별하고 [2층 검수](../../../docs/motion-review-protocol.md)의 자동 증거와 실제 정상 속도 관찰을 분리한다. 미관찰은 해당 검수만 사람 확인 대기로 남기며 가능한 제작·수정·저장은 재승인 질문 없이 계속한다.
