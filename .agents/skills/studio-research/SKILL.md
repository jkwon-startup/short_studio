---
name: studio-research
description: 로컬 숏폼 studio-research 단계 운영
---

# 실행 계약

참고 영상의 Hook/Curiosity/Shot/Visual Focus/Text/Caption/Motion/Transition/Sound/Payoff를 시간별 분석한다. 직접 영상 확인, 설명·자막을 통한 간접 분석, 추론을 필드로 분리한다. 원본 접근권·출처·확인일을 기록한다. SPA는 fetch 접근을 건너뛰고 제공된 로컬 파일/캐시/내용을 사용한다. 미시청은 반드시 미시청으로 표시한다.

입력은 production ID와 현재 파일 경로/해시. 출력은 단계 컨텍스트, 산출물, 상태, 증거, 다음 단계 인계. 저장은 Producer가 `python3 -m studio ingest`로 수행한다. 실행 전에 `python3 -m studio status ID`와 `resume ID`를 확인한다. 미연결 어댑터는 BLOCKED로 남긴다. 전역 레지스트리 수정과 외부 공개는 별도 승인 대상이다.

## 광고 창작·품질 계약

제작·복구·검수 전 [실사·카피·영상미 기준](../../../docs/advertising-creative-standard.md)을 읽는다. 타깃의 망설임·실제 광고 카피·인물 행동·카메라·빛·컷·소리를 근거와 관찰 범위로 분석한다. 다른 브랜드의 참고작과 같은 브리프 비교작을 구별한다.

## 모션 단계 인계와 검수

모션이 포함된 작업은 [공통 모션 기준](../../../docs/motion-design-standard.md)을 읽고 해당 역할 범위에서 장르별 목적·사전 애니매틱·브랜드 모션 토큰을 인계한다. [정량·납품 기준](../../../docs/motion-delivery-spec.md)의 공식/권장/미확인을 구별하고 [2층 검수](../../../docs/motion-review-protocol.md)의 자동 증거와 실제 정상 속도 관찰을 분리한다. 미관찰은 해당 검수만 사람 확인 대기로 남기며 가능한 제작·수정·저장은 재승인 질문 없이 계속한다.
