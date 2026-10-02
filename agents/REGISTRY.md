# 프로젝트 역할 레지스트리

총 14개. 전역 REGISTRY.md와 SKILL-AGENT-MAP.md가 없던 상태에서 필수 등록 규칙과 추가 승인을 확인하여 프로젝트 참조를 신규 등록했다. 프로젝트 안에서 명시 호출한다. 네이티브 파일은 .codex/agents/*.toml. 모든 자식은 읽기 전용, 저장·렌더 명령 실행은 부모가 담당한다. Tier는 역할의 최대 작업 범위이며 TOML 단독으로 세밀한 도구 ACL이 구현되지는 않는다.

|역할|Tier|스킬|입력|출력|
|---|---|---|---|---|
|Producer|2|studio-produce|brief・원장・이전 체크포인트|제작 계획・단계 인계・현재 상태|
|Research|1|studio-research|brief・허가된 참고 영상과 출처|관찰 구분 연구 JSON・Hook 분석|
|Fact & Rights|1|studio-rights|연구・주장・에셋・음성 라이선스|주장별 근거와 권리 원장|
|Story & Script|2|studio-story|핵심 문장・시청자 질문・FACT|사건 중심 대본・SCRIPT ID|
|Director|2|studio-visual|SCRIPT・스타일・플랫폼 분량|Shot 목록・시선 및 전환 설계|
|Art|2|studio-visual|SHOT・스타일・권리 원장|레이어별 에셋 명세・검수|
|3D|3|studio-visual|SHOT・ASSET・공간 목적|Blender 장면・렌더 명세|
|Motion|3|studio-visual|SHOT・ASSET・3D 레이어|사건별 프레임 모션・전환 근거|
|Voice|3|studio-voice|현재 SCRIPT・후보・라이선스|후보 비교・선정 음성・VOICE 해시|
|Audio|3|studio-audio|VOICE・SHOT・권리 원장|스템・믹스・오디오 검수|
|Editor & Caption|3|studio-edit|현재 음성・모션・오디오・대본|VIDEO・CAPTION・텍스트 중복 보고|
|Technical QA|1|studio-qa|현재 VIDEO・AUDIO・원장|독립 기술 QA 보고|
|Viewer QA|1|studio-qa|현재 VIDEO・AUDIO・타깃 질문|시청자 QA・시간별 문제와 레이어|
|Recovery & Release|3|studio-recovery|FAIL・현재 원장・QA|부분 복구 계획・출고 패키지|

## 共通 광고 기준

14개 역할 모두 docs/advertising-creative-standard.md의 단계별 인계와 실제 관찰 기준을 따른다. 가능한 실사풍 광고 기본값, 목적/사용자 요청에 따른 모션그래픽 선택, docs/motion-design-standard.md의 전문 품질 목표는 Codex TOML·역할 계약·Claude 변환본에 함께 적용한다.
