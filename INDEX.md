# INDEX (입구: 이 파일만 먼저 읽습니다)

> 노트마다 한 줄. 필요한 것만 엽니다. 긴 노트는 장 하나만: `python3 tools/doc_section.py <노트> <장>`. 쓰는 법은 `README.md`.

## 시작할 때
- [playbooks/new-project-kickoff.md](playbooks/new-project-kickoff.md) — 새 프로젝트 첫 세션: 붙여 넣을 프롬프트, 크기별로 만들 파일, 처음부터 지킬 습관 7가지
- [playbooks/handoff.md](playbooks/handoff.md) — 인수인계: HANDOFF 6항목 + 원문 기록·시작 프롬프트·장 단위 읽을 것, 닫기 전 체크리스트 8단계
- [templates/](templates/) — HANDOFF.md, CLAUDE.md(200줄 이하 틀), USER_DIRECTIONS.md 복사용

## 인사이트
- **[insights/context-consistency.md](insights/context-consistency.md) — 가장 중요.** 문서끼리 어긋나지 않게: 문서 네 종류(덮어씀·기준·덧붙이기·얼림), 결정의 생애(ADR식 대체 링크), 바꿀 때 영향 범위, 시작 프롬프트는 상태 문서 한 곳(미리 만들지 않음), 기계 검사 + 읽기만 하는 의미 점검, 장황함 줄이기. 근거: 이 프로젝트의 모순 8건 + 외부 조사(Anthropic, Chroma, spec-kit, adr-tools, Cline)
- [insights/token-economy.md](insights/token-economy.md) — 토큰의 60%는 긴 세션의 다시 읽기(측정: 응답당 56만 토큰). 규칙 파일·연결·읽기 목록 줄이기
- [insights/context-hygiene.md](insights/context-hygiene.md) — 한 세션 한 목표, 새 세션으로 넘어가는 네 가지 때, 원문 한 곳, 다음 세션 프롬프트 하나만(상태 문서)
- [insights/doc-structure.md](insights/doc-structure.md) — 한 사실은 한 곳에만(기준 문서 표), docs/ 폴더 묶기, 겹치지 않는 이름, 장 번호 참조
- [insights/file-index-tools.md](insights/file-index-tools.md) — 지도 세 겹(규칙 파일 표, 폴더 나무, 자동 코드 지도)과 도구 세 개(장 읽기, 코드 지도, 문서 검사)
- [insights/project-goals-methods.md](insights/project-goals-methods.md) — 사용자 목표 다섯 갈래(주체성, 토큰, 오염, 꼬임, 의도)와 방법: 그래프 지도, 결정 카드, 완성 기준 먼저

## 삽질과 절차
- [lessons/mistakes.md](lessons/mistakes.md) — 17가지: 코드로 확인 안 한 계획 숫자, 각도 부호, 일괄 치환이 놓친 조각 경로, stash가 푼 rename, 전역으로 바뀐 연결 설정 등
- [playbooks/reorganize-folders.md](playbooks/reorganize-folders.md) — 폴더 옮기기 9단계: 조사 → 커밋 → git mv → 경로(조각 경로 포함) → 실행 확인 → 지도 → 모순 점검
- [playbooks/project-map-dashboard.md](playbooks/project-map-dashboard.md) — 사람용 프로젝트 지도 만들기: 폴더 상자 지도, 연결선, Claude 실시간 작업(대화 기록을 읽기만), 다시 보기, 일대기 띠(로드맵 표 + 상태 문서). 짜임, 기록 해석 규칙, 옮길 때 바꿀 것

## 도구와 방향
- [tools/README.md](tools/README.md) — doc_section.py(바로 씀), codemap·doc_check·making_stats(원본 위치)
- [ROADMAP.md](ROADMAP.md) — 이 저장소의 목표와 다음 단계(스킬로 포장, 한 줄 더하기 도구, 정리·검증, 효과 재기)
- [점검.md](점검.md) — 10-17 점검 보고서(얼림): 문제 16개, 해결안 후보 A~E와 혼합안, Graphify 코드 지도 인사이트(6장), 정할 것(8장). 0장 요약만 먼저, 나머지는 장 단위로





## 토큰 아끼기

**A. 세션을 짧게 끊기 (효과 가장 큼, 습관)**

- 한 세션은 한 목표만 합니다. 목표가 끝나면 새 세션을 열거나 `/clear`합니다. 지금 규칙에도 있지만, 첫 세션은 4일 동안 이어졌습니다.
- 1시간 넘게 쉰 뒤에는 같은 세션을 이어 쓰지 않습니다. 캐시가 만료되어 대화 전체를 다시 저장하는 비용이 듭니다.
- `/compact`도 대화 전체를 한 번 읽습니다. 이어 갈 필요가 없으면 새 세션이 더 쌉니다.

**B. 매번 읽히는 규칙 파일 줄이기 (파일 조작, 효과 큼)**

- 맨 위 `CLAUDE.md`는 project/CLAUDE.md를 불러옵니다. 그래서 278줄, 약 1만 3천 자가 **모든 세션의 모든 응답에** 실립니다.
- 공식 권장은 200줄 이하입니다.
- 그중 183줄이 3장 "현재 결정"인데, 대부분 DESIGN.md와 겹칩니다.
- 3장은 "지금 단계, 꼭 지킬 원칙, 어디를 보면 되는지"만 남기고 줄입니다. 장면별 값은 DESIGN.md에서 필요할 때만 읽게 합니다. 이러면 규칙 파일이 지금의 절반 이하로 줄 것으로 봅니다(아직 재 보지 않음).
- 사람만 볼 메모는 `<!-- -->` 주석으로 쓰면 Claude에게 실리지 않습니다.

**C. 세션 시작 읽기 목록 줄이기 (파일 조작)**

- 지금 규칙대로면 세션마다 처음에 다섯 파일을 통째로 읽습니다: CLAUDE, STATUS, ROADMAP, 계획서, 조사서. 합치면 약 9만 자입니다.
- ROADMAP은 그 세션 항목만, 계획서는 그 세션 장만 읽게 바꿉니다. 조사서(약 3만 5천 자)는 필요할 때만 열게 HANDOVER.md와 CLAUDE.md 0장을 고칩니다.
- 긴 코드 파일(cathedral.py 1,167줄, player.js 984줄)도 통째로 읽지 않고, 찾아서 필요한 부분만 읽습니다.

**D. 안 쓰는 연결 끄기 (설정)**

- 이 세션에는 이 작품과 관계없는 연결이 많이 붙어 있습니다: 영상 생성, Figma, Gmail, 캘린더, 노션, 구글 문서, Adobe, 소셜 게시 등.
- 이들의 도구 이름 수백 개와 설명이 응답마다 실립니다. 앱 설정에서 이 프로젝트에 쓰지 않는 것을 끄면 매 응답의 기본 무게가 줄어듭니다.

**E. 노력 수준과 모델 고르기 (습관)**

- 문서 정리나 상태 확인 같은 가벼운 일은 낮은 노력 수준(`/effort`)이나 Sonnet으로 충분합니다.
- 카메라 설계 같은 무거운 판단에만 높은 노력 수준을 씁니다.

**F. 큰 출력은 걸러서 받기 (작업 방식)**

- 렌더 로그와 감사 결과는 `tail`이나 `grep`으로 필요한 줄만 받습니다.
- 화면 캡처는 이미지 한 장도 토큰이 들므로, 여러 장을 한 장에 모은 작은 시트로 봅니다.
- `web/node_modules` 같은 큰 폴더는 읽지 않습니다.

**G. 별도 세션과 알림 줄이기 (작업 방식)**

- 별도 세션은 그 자체로 토큰을 씁니다.
- 끝났다는 알림이 오면 이 세션이 대화 전체를 들고 다시 깨어납니다. 오늘 리포 확인 세션도 그랬습니다.
- 꼭 필요한 때만 제안하겠습니다.
