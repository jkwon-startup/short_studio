---
name: studio-rights
description: 로컬 숏폼 studio-rights 단계 운영
---

# 실행 계약

핵심 주장별 근거를 실제 확인한다. 이미지·폰트·음성·음악·영상별 라이선스, 출처, 사용범위, 상업권, 허락, 확인일을 기록한다. 하나라도 미확인이면 FACT BLOCKED. 자격증명을 복사하거나 API 키를 만들지 않는다.

입력은 production ID와 현재 파일 경로/해시. 출력은 단계 컨텍스트, 산출물, 상태, 증거, 다음 단계 인계. 저장은 Producer가 `python3 -m studio ingest`로 수행한다. 실행 전에 `python3 -m studio status ID`와 `resume ID`를 확인한다. 미연결 어댑터는 BLOCKED로 남긴다. 전역 레지스트리 수정과 외부 공개는 별도 승인 대상이다.

## 광고 창작·품질 계약

제작·복구·검수 전 [실사·카피·영상미 기준](../../../docs/advertising-creative-standard.md)을 읽는다. 실제 촬영/제공 소스와 AI 생성 실사풍을 구별하고 인물·영상·음악·폰트·음성의 사용권 및 광고 주장의 근거를 확인한다. 생성 장면을 실제 수업/후기/성과의 증거로 삼지 않는다.

## 모션 단계 인계와 검수

모션이 포함된 작업은 [공통 모션 기준](../../../docs/motion-design-standard.md)을 읽고 해당 역할 범위에서 장르별 목적·사전 애니매틱·브랜드 모션 토큰을 인계한다. [정량·납품 기준](../../../docs/motion-delivery-spec.md)의 공식/권장/미확인을 구별하고 [2층 검수](../../../docs/motion-review-protocol.md)의 자동 증거와 실제 정상 속도 관찰을 분리한다. 미관찰은 해당 검수만 사람 확인 대기로 남기며 가능한 제작·수정·저장은 재승인 질문 없이 계속한다.
