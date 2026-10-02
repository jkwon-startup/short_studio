---
name: studio-edit
description: 로컬 숏폼 studio-edit 단계 운영
---

# 실행 계약

짧은 발화 단위 JSON 자막을 만들고 1~2줄 모바일 가독성을 검수한다. TITLE/INFOGRAPHIC TEXT/BURNED CAPTION/PLATFORM CAPTION 사이 의미 중복을 검사한다. 프레임 시간으로 결정적 렌더. 변경한 레이어/Shot만 재렌더하고 합친 현재 VIDEO를 다시 WATCH한다. 개인 remotion-best-practices가 있으면 원본을 읽어 재사용하되 런타임 설치 상태를 먼저 확인한다.

입력은 production ID와 현재 파일 경로/해시. 출력은 단계 컨텍스트, 산출물, 상태, 증거, 다음 단계 인계. 저장은 Producer가 `python3 -m studio ingest`로 수행한다. 실행 전에 `python3 -m studio status ID`와 `resume ID`를 확인한다. 미연결 어댑터는 BLOCKED로 남긴다. 전역 레지스트리 수정과 외부 공개는 별도 승인 대상이다.

## 몰입·리듬 계약

제작·복구·검수 시 [공통 기준](../studio-produce/references/attention-and-pacing.md)을 읽는다. 비트별 정보 변화와 실제 읽기 시간을 함께 편집한다. 읽기 목적 없는 긴 정지·반복 구도를 지우되 과한 속도로 이해를 깨뜨리지 않는다. 느리다는 피드백을 단순 전체 배속으로 처리하지 않고 대본·Shot·컷 배치부터 고친다.

## 광고 창작·품질 계약

제작·복구·검수 전 [실사·카피·영상미 기준](../../../docs/advertising-creative-standard.md)을 읽는다. 실사 행동·반응·시선·소리의 연결로 속도감을 만들고 짧은 디테일과 읽기 시간을 대비시킨다. 얼굴/손/시연을 자막이 가리지 않게 하고 전체 배속/반복 줌으로 지루함을 감추지 않는다.

## 모션 단계 인계와 검수

모션이 포함된 작업은 [공통 모션 기준](../../../docs/motion-design-standard.md)을 읽고 해당 역할 범위에서 장르별 목적·사전 애니매틱·브랜드 모션 토큰을 인계한다. [정량·납품 기준](../../../docs/motion-delivery-spec.md)의 공식/권장/미확인을 구별하고 [2층 검수](../../../docs/motion-review-protocol.md)의 자동 증거와 실제 정상 속도 관찰을 분리한다. 미관찰은 해당 검수만 사람 확인 대기로 남기며 가능한 제작·수정·저장은 재승인 질문 없이 계속한다.
