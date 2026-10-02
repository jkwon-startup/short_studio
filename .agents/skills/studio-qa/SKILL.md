---
name: studio-qa
description: 로컬 숏폼 studio-qa 단계 운영
---

# 실행 계약

Technical QA와 Viewer QA는 제작자와 다른 검수자다. 실제 현재 영상과 음성을 확인하지 못하면 PASS 금지. 첫3초,5초 이후 새 정보,화면/말 반복,자막만 남는 콘텐츠,시선,마지막 회수를 평가한다. 타임코드·문제 레이어·근거를 기록한다. 실제 시청률을 보장하지 않는다. 모든 Research/Fact/Script/Shot/Asset/Motion/Caption/Audio/Technical QA/Viewer QA가 같은 현재 스냅샷 PASS여야 출고.

입력은 production ID와 현재 파일 경로/해시. 출력은 단계 컨텍스트, 산출물, 상태, 증거, 다음 단계 인계. 저장은 Producer가 `python3 -m studio ingest`로 수행한다. 실행 전에 `python3 -m studio status ID`와 `resume ID`를 확인한다. 미연결 어댑터는 BLOCKED로 남긴다. 전역 레지스트리 수정과 외부 공개는 별도 승인 대상이다.

## 몰입·리듬 계약

제작·복구·검수 시 [공통 기준](../studio-produce/references/attention-and-pacing.md)을 읽는다. Viewer QA는 실제 속도 연속 재생으로 첫3초 사건, 다음 장면의 이유, 정보 공백·반복 구도·읽기 시간·음향 리듬을 타임코드로 검수한다. 정지 프레임/디코드/가독성만으로 몰입 PASS 금지. 실시간 관찰에서 기다릴 이유 없는 정지·반복 또는 이해를 깨뜨리는 속도가 확인되면 FAIL과 새 복구 가설을 보고한다.

## 광고 창작·품질 계약

제작·복구·검수 전 [실사·카피·영상미 기준](../../../docs/advertising-creative-standard.md)을 읽는다. 현재 파일의 디코드·프레임/길이·오디오·합성/자막 싱크를 검수하고 기술 결과와 광고 창작 품질을 구별한다. 관찰하지 않은 운동/광고 품질을 해상도나 파일 존재로 통과시키지 않는다. 현재 SHA의 연속 시청·청취로 카피·실사 인물/행동·영상미·리듬·음향·CTA를 타임코드로 검수한다. 모션이면 전문 모션 기준도 적용한다. 실제 비교작이 있을 때만 같은 조건의 우열 근거를 기록한다.

## 모션 단계 인계와 검수

모션이 포함된 작업은 [공통 모션 기준](../../../docs/motion-design-standard.md)을 읽고 해당 역할 범위에서 장르별 목적·사전 애니매틱·브랜드 모션 토큰을 인계한다. [정량·납품 기준](../../../docs/motion-delivery-spec.md)의 공식/권장/미확인을 구별하고 [2층 검수](../../../docs/motion-review-protocol.md)의 자동 증거와 실제 정상 속도 관찰을 분리한다. 미관찰은 해당 검수만 사람 확인 대기로 남기며 가능한 제작·수정·저장은 재승인 질문 없이 계속한다.
