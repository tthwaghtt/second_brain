# INDEX (입구: 이 파일만 먼저 읽습니다)

> 노트마다 한 줄. 필요한 것만 엽니다. 긴 노트는 장 하나만: `python3 tools/doc_section.py <노트> <장>`. 쓰는 법은 `README.md`.

## 시작할 때
- [playbooks/new-project-kickoff.md](playbooks/new-project-kickoff.md) — 새 프로젝트 첫 세션: 붙여 넣을 프롬프트, 크기별로 만들 파일, 처음부터 지킬 습관 7가지
- [playbooks/handoff.md](playbooks/handoff.md) — 인수인계: HANDOFF 6항목 + 원문 기록·시작 프롬프트·장 단위 읽을 것, 닫기 전 체크리스트 8단계
- [templates/](templates/) — HANDOFF.md, CLAUDE.md(200줄 이하 틀), USER_DIRECTIONS.md 복사용
- [inbox/README.md](inbox/README.md) — 정제 안 된 세션 메모함: 세션은 쓰기만(add_note.py inbox), 읽고 옮기는 건 컴파일 세션만
- [skills/second-brain/SKILL.md](skills/second-brain/SKILL.md) — 스킬 묶음 6개(입구 second-brain, plan-first, session-handoff, lean-context, doc-hygiene, brain-compile)의 원본. 컴파일 결과, 판 2026-10-17. 고치면 .skill로 다시 저장. 출처는 skills/ATTRIBUTION.md

## 인사이트
- **[insights/context-consistency.md](insights/context-consistency.md) — 가장 중요.** 문서끼리 어긋나지 않게: 문서 네 종류(덮어씀·기준·덧붙이기·얼림), 결정의 생애(ADR식 대체 링크), 바꿀 때 영향 범위, 시작 프롬프트는 상태 문서 한 곳(미리 만들지 않음), 기계 검사 + 읽기만 하는 의미 점검, 장황함 줄이기. 근거: 이 프로젝트의 모순 8건 + 외부 조사(Anthropic, Chroma, spec-kit, adr-tools, Cline)
- [insights/token-economy.md](insights/token-economy.md) — 토큰의 60%는 긴 세션의 다시 읽기(측정: 응답당 56만 토큰). 규칙 파일·연결·읽기 목록 줄이기
- [insights/context-hygiene.md](insights/context-hygiene.md) — 한 세션 한 목표, 새 세션으로 넘어가는 네 가지 때, 원문 한 곳, 다음 세션 프롬프트 하나만(상태 문서)
- [insights/doc-structure.md](insights/doc-structure.md) — 한 사실은 한 곳에만(기준 문서 표), docs/ 폴더 묶기, 겹치지 않는 이름, 장 번호 참조
- [insights/file-index-tools.md](insights/file-index-tools.md) — 지도 세 겹(규칙 파일 표, 폴더 나무, 자동 코드 지도)과 도구 세 개(장 읽기, 코드 지도, 문서 검사)
- [insights/project-goals-methods.md](insights/project-goals-methods.md) — 사용자 목표 다섯 갈래(주체성, 토큰, 오염, 꼬임, 의도)와 방법: 그래프 지도, 결정 카드, 완성 기준 먼저

## 삽질과 절차
- [lessons/mistakes.md](lessons/mistakes.md) — 18가지: 코드로 확인 안 한 계획 숫자, 각도 부호, 일괄 치환이 놓친 조각 경로, stash가 푼 rename, 전역으로 바뀐 연결 설정, 입구에 붙은 세션 보고 등
- [playbooks/reorganize-folders.md](playbooks/reorganize-folders.md) — 폴더 옮기기 9단계: 조사 → 커밋 → git mv → 경로(조각 경로 포함) → 실행 확인 → 지도 → 모순 점검
- [playbooks/project-map-dashboard.md](playbooks/project-map-dashboard.md) — 사람용 프로젝트 지도 만들기: 폴더 상자 지도, 연결선, Claude 실시간 작업(대화 기록을 읽기만), 다시 보기, 일대기 띠(로드맵 표 + 상태 문서). 짜임, 기록 해석 규칙, 옮길 때 바꿀 것

## 도구와 방향
- [tools/README.md](tools/README.md) — doc_section.py·add_note.py(바로 씀), codemap·doc_check·making_stats(원본 위치)
- [ROADMAP.md](ROADMAP.md) — 이 저장소의 목표와 다음 단계(스킬로 포장, 한 줄 더하기 도구, 정리·검증, 효과 재기)
- [점검.md](점검.md) — 10-17 점검 보고서(얼림): 문제 16개, 해결안 후보 A~E와 혼합안, Graphify 코드 지도 인사이트(6장), 정할 것(8장). 0장 요약만 먼저, 나머지는 장 단위로
- [skills/project-board/SKILL.md](skills/project-board/SKILL.md) — 현황판 스킬: second-brain 문서와 git을 읽는 로컬 웹 현황판(`tools/board/`)을 그 프로젝트에 명령 하나로 세움. PORTFOLIO 것(10-26 승인)의 일반판, 원본과 다른 곳은 DIFF.md. 판 2026-10-26
