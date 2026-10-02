---
name: studio-recovery
description: 로컬 숏폼 studio-recovery 단계 운영
---

# 실행 계약

FAIL을 삭제하지 않는다. 원인·단계·문제·수정·교훈·다음 가설 기록. 같은 실패/같은 가설 반복을 차단하고 도구/방법/입력 가설을 변경한다. WATCH→문제 감지→레이어 식별→부분 수정→재렌더. FINAL/PROJECT/ASSETS/AUDIO/SCRIPT/SHOT/RESEARCH/QA/FAIL/LOG 및 상태 원장을 묶는다. 무효화 의존성만 복구하고 현재 독립 QA 후 출고한다.

입력은 production ID와 현재 파일 경로/해시. 출력은 단계 컨텍스트, 산출물, 상태, 증거, 다음 단계 인계. 저장은 Producer가 `python3 -m studio ingest`로 수행한다. 실행 전에 `python3 -m studio status ID`와 `resume ID`를 확인한다. 미연결 어댑터는 BLOCKED로 남긴다. 전역 레지스트리 수정과 외부 공개는 별도 승인 대상이다.

## 광고 창작·품질 계약

제작·복구·검수 전 [실사·카피·영상미 기준](../../../docs/advertising-creative-standard.md)을 읽는다. 밋밋함/카피/실사 오류/모션 마감을 해당 SCRIPT·SHOT·에셋·키프레임·오디오 레이어의 새 가설로 복구한다. 기존 FAIL/버전 보존, 현재 독립 QA와 공통 short 저장을 유지한다.

## 모션 단계 인계와 검수

모션이 포함된 작업은 [공통 모션 기준](../../../docs/motion-design-standard.md)을 읽고 해당 역할 범위에서 장르별 목적·사전 애니매틱·브랜드 모션 토큰을 인계한다. [정량·납품 기준](../../../docs/motion-delivery-spec.md)의 공식/권장/미확인을 구별하고 [2층 검수](../../../docs/motion-review-protocol.md)의 자동 증거와 실제 정상 속도 관찰을 분리한다. 미관찰은 해당 검수만 사람 확인 대기로 남기며 가능한 제작·수정·저장은 재승인 질문 없이 계속한다.
