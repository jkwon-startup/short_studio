---
name: studio-voice
description: 로컬 숏폼 studio-voice 단계 운영
---

# 실행 계약

같은 현재 대본으로 한국어 TTS 후보를 실제 생성·청취하고 발음/억양/속도/감정/피로도/라이선스를 비교한다. 로컬 say는 기술시험 가능하나 상업권 확인 전 최종 사용 BLOCKED. 외부 TTS는 승인된 provider·모델·한도(Claude: config/claude-autopilot.json, Codex: 승인 기록) 안에서 재승인 없이 사용, 그 밖은 별도 승인. 무인 자동 제작은 기본 음성 1종을 쓰고 후보 비교는 `SKIPPED_AUTOPILOT_DEFAULT`로 기록하며, Whisper 재전사와 대본 대조로 발음 오류만 자동 점검한다(실제 청취는 사람 시청 대기). SCRIPT/voice model/style/speed/tool version 해시를 기록한다.

입력은 production ID와 현재 파일 경로/해시. 출력은 단계 컨텍스트, 산출물, 상태, 증거, 다음 단계 인계. 저장은 Producer가 `python3 -m studio ingest`로 수행한다. 실행 전에 `python3 -m studio status ID`와 `resume ID`를 확인한다. 미연결 어댑터는 BLOCKED로 남긴다. 전역 레지스트리 수정과 외부 공개는 별도 승인 대상이다.

## 광고 창작·품질 계약

제작·복구·검수 전 [실사·카피·영상미 기준](../../../docs/advertising-creative-standard.md)을 읽는다. 광고 카피의 의미·브랜드·인물 감정에 맞는 발음·강세·호흡을 실제 청취로 비교한다. 싼/로컬 도구 또는 기계 배속만으로 광고 목소리 품질을 인정하지 않는다.

## 모션 단계 인계와 검수

모션이 포함된 작업은 [공통 모션 기준](../../../docs/motion-design-standard.md)을 읽고 해당 역할 범위에서 장르별 목적·사전 애니매틱·브랜드 모션 토큰을 인계한다. [정량·납품 기준](../../../docs/motion-delivery-spec.md)의 공식/권장/미확인을 구별하고 [2층 검수](../../../docs/motion-review-protocol.md)의 자동 증거와 실제 정상 속도 관찰을 분리한다. 미관찰은 해당 검수만 사람 확인 대기로 남기며 가능한 제작·수정·저장은 재승인 질문 없이 계속한다.
