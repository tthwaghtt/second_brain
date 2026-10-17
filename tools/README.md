# 도구

| 도구 | 상태 | 설명 |
|---|---|---|
| `doc_section.py` | **바로 씀** (일반판) | 문서의 장 하나만 통째로 꺼냄. 이름만 주면 지금 폴더 아래에서 찾음. second_brain 노트 읽기에도 씀 |
| `add_note.py` | **바로 씀** (10-17) | 노트와 `INDEX.md` 줄을 함께 고침: `new`(머리 형식째 새 노트 + INDEX 줄), `append`(덧붙이기, `--summary`로 INDEX 줄도), `index`(INDEX 줄만), `check`(없는 파일을 가리키는 링크, INDEX에 없는 노트, 날짜·규칙 줄이 빠진 노트), `inbox`(inbox/YYYY-MM.md에 세션 메모 한 줄). 세션 끝에 `check` |
| `codemap.py` | 원본만 있음 | MAGNUM OPUS `scripts/docs/codemap.py`. 코드 폴더를 스스로 훑어 `CODEMAP.md` 생성(작품 순서, 파일별 목적·함수·줄 번호·import, 데이터 폴더의 쓰기/읽기 코드). 프로젝트마다 폴더 이름과 "작품 순서" 부분을 바꿔 복사 |
| `doc_check.py` | 원본만 있음 | MAGNUM OPUS `scripts/docs/doc_check.py`. 없는 장 참조, 없는 파일 경로(문서와 코드 속), 원본 데이터와 다른 숫자, 낡은 코드 지도를 찾음. 프로젝트마다 "원본 데이터 대조" 부분을 바꿔 복사 |
| `making_stats.py` | 원본만 있음 | MAGNUM OPUS `scripts/docs/making_stats.py`. `~/.claude/projects/<프로젝트 키>*/` 대화 기록에서 세션별 토큰·API 환산·작업 시간을 누적 |
| 프로젝트 지도 (`map/`) | 원본만 있음 | MAGNUM OPUS `project/map/`(build.py, server.py, query.py, page/). 폴더 상자 지도 + 연결선 + Claude 실시간 작업 + 지난 세션 다시 보기 + 일대기 띠. 만드는 법과 옮길 때 바꿀 것은 `playbooks/project-map-dashboard.md` |

- 원본은 읽기만 하고 복사해서 씁니다(원본 프로젝트를 고치지 않음).
- 일반판으로 다듬을 만하면 여기에 옮기고 이 표를 고칩니다(ROADMAP 2단계).
