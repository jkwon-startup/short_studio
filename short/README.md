# Codex·Claude 공통 제작물 저장

저장 루트는 프로젝트의 `short/`다. **한국시간의 저장 날짜·시간**을 기준으로 `YYYY-MM-DD/HH-MM-SS_도구_제작ID/`에 영상·음성·대본·자막·편집 소스를 복사한다. 원래 제작/파일 수정 시각은 manifest.json에 별도 기록한다.

폴더의 `README.md`는 파일별 원본 위치를 보여주며, `INDEX.md`에서 전체 제작물을 찾을 수 있다. 원본은 runs/work에 유지한다. 복사본은 현재 제작 상태와 SHA256을 기록하며, 저장을 대본 승인·품질 PASS·최종 출고로 취급하지 않는다. fixture와 외부 심볼릭 링크는 제외한다. 기존 이름의 파일과 서로 다른 버전은 덮어쓰지 않는다. 내용이 같은 스냅샷은 기존 폴더를 재사용한다.

프로젝트 루트에서 아래 명령을 사용한다.

```sh
# Codex 제작물
python3 short/save_output.py --id startup-lab-vibecoding-design-20261002-v2 --tool codex

# Claude 제작물
python3 short/save_output.py --id claude-20261002-solo-founder --tool claude

# 현재 두 도구의 모든 production 제작물
python3 short/save_output.py --all
```

Producer는 대본·음성·렌더 파일을 저장한 뒤 해당 제작 ID로 위 명령을 실행한다. 제작물 내용이 바뀌면 새 저장시각 폴더가 생긴다. 이 스크립트는 계속 실행되는 감시 프로그램이 아니며, 현재 세션에서 자동으로 다른 세션을 깨우거나 메시지를 보내지 않는다. 작성 중인 파일이 복사 도중 바뀌면 그 작업을 완료로 표시하지 않는다.

이 폴더는 로컬 결과 보관용이다. 향후 공개 배포에는 개인 제작 데이터와 원본 경로가 담긴 이 폴더를 기본 포함하지 않는다.
