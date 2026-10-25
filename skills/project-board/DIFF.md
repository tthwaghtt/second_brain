# PORTFOLIO 원본과 다른 곳

> 판 1 · 2026-10-26. 원본은 `making-coolassbitch/PORTFOLIO/tools/board/`, 커밋 6e5b6bd(사용자 승인 "현황판 좋다", 그 프로젝트 `USER_DIRECTIONS.md` 16-9). 스킬의 코드를 고치거나 원본의 새 판을 옮길 때마다 이 문서를 고쳐 씁니다.

## 1. 한 줄로

PORTFOLIO에만 맞게 고정돼 있던 경로·장 번호·세션 글자를 `board.toml`과 문서 이름에서 읽게 바꿨고, 문서가 적은 프로젝트(로드맵·기획서·지도가 없음)에서도 화면과 검사가 맞게 비도록 고쳤습니다. 화면의 디자인(`app.css`, `index.html`)은 그대로입니다.

## 2. 빼고 복사한 것

| 원본에 있는 것 | 스킬에서 | 이유 |
|---|---|---|
| `PRODUCT.md`, `DESIGN.md`, `.impeccable/` | 없음. `DESIGN.md`는 `references/design-system.md`에 얼린 사본 | PORTFOLIO 현황판의 제품·디자인 기록. 다른 프로젝트는 그대로 쓰거나 다시 정함(SKILL.md 4장) |
| `.trash/`, `.state/`, `.taste-skill/`, `__pycache__/` | 없음 | 그 컴퓨터의 휴지통, 사용자의 "파악함", 디자인 도구의 작업 폴더 |
| `board.toml` | 없음. `scripts/setup_board.py install`이 그 프로젝트에 맞게 씀 | 문서 위치와 잠긴 곳은 프로젝트마다 다름 |

## 3. 그대로인 것

`board/checks.py`, `board/gitinfo.py`, `board/history.py`, `board/md.py`, `board/refs.py`, `board/roadmap.py`, `board/tree.py`, `static/app.css`, `static/index.html`, `static/search.js`, `static/mark.svg`, `static/fonts/`, `.gitignore`

## 4. 바꾼 것

### 4-1. PORTFOLIO에 박힌 것을 설정에서 읽게

| 파일 | 원본 | 스킬 | 왜 |
|---|---|---|---|
| `board/config.py` | 휴지통·상태 기본 경로가 `tools/board/` | `board_dir`(현황판 폴더를 스스로 앎), `[roles]` 표(기록·보고서·옛 방향·사용자 자료·도구·데이터·작업물이 있는 곳, 기본값은 원본의 경로), `under()`, `[facts]` | 역할 짐작이 다른 폴더 이름에서도 맞게. 사실을 코드가 아닌 설정에 두어 코드를 바꿔도 남게 |
| `board/index.py` `GUESS` | `docs/record/`, `docs/research/`, `old/`, `refs/`, `.claude/`, `tools/board/`, `data/`·`logs/`를 글자로 박음. 기준 문서는 `docs/*.md` | `[roles]`의 곳으로 판단. 작업물(`work`) 줄을 더함. 기준 문서는 `board.toml`이 이름을 댄 문서와 찾는 곳의 `.md`(찾는 곳이 프로젝트 전체면 맨 위의 `.md`만). 사용자 원문 문서는 어디 있든 "기록". 곳 규칙을 기준 문서 규칙보다 먼저 봄 | 문서가 `docs/`에 없는 프로젝트에서 사용자의 글(`notes/*.md`)이 "기준 문서"로 잘못 보이지 않게 |
| `board/index.py` 현황판 줄 | "현황판 세션이 고침", "현황판 세션" | "project-board 스킬로 세우고 바꿈", "현황판을 맡은 세션" | 그런 세션 이름이 없는 프로젝트에서도 맞는 말 |
| `board/index.py` `commits_by_file` | 세션 번호를 `[PRDB]\d+`(PORTFOLIO의 글자)로 찾음 | 첫 `[A-Z]\d+`(로드맵과 같은 모양) | 다른 글자의 세션(S1, N3 …). PORTFOLIO 커밋 전부에서 결과가 같음을 확인 |
| `board/index.py` 설명 없는 파일·새 파일 검토함 | `tools/board/`를 글자로 뺌 | 현황판 폴더(`board_dir`)를 뺌 | `--dest`로 다른 곳에 세워도 |
| `board/index.py` `reading_path` | 규칙 파일 세션 시작 장의 `doc_section.py` 명령만 읽음 | 명령이 없으면 그 장이 `` `이름.md` ``로 적은 문서를 차례로 읽음(로드맵이면 세션 칸) | second_brain 틀(`templates/CLAUDE.md`)은 명령 없이 "`HANDOFF.md`의 "지금" → 로드맵의 그 세션 항목"으로 씀 |
| `board/docs.py` `directions` | 원문 장 제목의 세션을 `[PRDB]\d+`로 찾음 | 로드맵과 같은 `ID` | 위와 같음 |
| `board/ops.py` `doc_clash` | 찾는 곳이 폴더일 때만 | `.`(프로젝트 전체)도 | 문서를 프로젝트 전체에서 이름으로 찾는 프로젝트 |
| `board/lookup.py` | 용어 풀이의 예가 PORTFOLIO 것("P3, B1", "CLAUDE.md 4장"), 찾기 결과에서 `tools/board/`를 뒤로, 용어 출처 "MAP.md" | 일반 예("S1, B3", "규칙 파일의 세션 역할"), `board_dir`, 지도 문서의 실제 이름 | 다른 프로젝트에서 틀린 말이 되지 않게 |
| `static/ui.js` | (없음) | `docName()`, `docPath()`, `headName()`: 문서 이름과 장 이름을 `board.toml`에서 | 아래 화면 글자 |
| `static/app.js`, `line.js`, `roadmap.js`, `files.js`, `history.js` | "STATUS", "ROADMAP", "USER_DIRECTIONS", "MAP.md", "old/README.md", "BRIEF 12장", "B1 씀"을 글자로 씀 | 그 프로젝트의 문서 이름(예: `HANDOFF`)과 장 이름 | 상태 문서가 `HANDOFF.md`인 프로젝트에서 "STATUS 기준"이라고 쓰면 거짓이 됨 |
| `static/files.js` 역할 표 프롬프트 | `docs/MAP.md`, "CLAUDE.md 2·4·5장", "1장 폴더 지도", `tools/doc_check.py`를 글자로 씀 | `board.toml`의 지도·규칙 파일·장 이름·검사 명령. 지도 문서가 없으면 먼저 만들어 `board.toml`에 적고 잠그라는 줄. 그 프로젝트에 없을 수 있는 장(문서 표, 세션 역할)은 "있으면"으로 | 그 프로젝트의 기획 책임 세션이 그대로 붙여 넣을 수 있게 |
| `README.md` | PORTFOLIO의 기준 문서(출처가 "BRIEF 14장" 등) | 일반판: 출처를 `[docs]` 열쇠로, "이 프로젝트에 맞추기" 장, 처음 정한 것에 사용자의 디자인 금지 목록 | 복사된 프로젝트에서 그대로 맞는 설명 |

### 4-2. 문서가 적은 프로젝트에서 드러난 것 (시험 프로젝트에서 찾음)

| 파일 | 원본 | 스킬 | 왜 |
|---|---|---|---|
| `server.py` `state()` | 읽는 길을 로드맵이 있을 때만 셈 | 언제나 세고 `reading`으로도 냄 | 로드맵이 없는 프로젝트에서도 규칙 파일 → 상태 문서의 읽는 길이 보이게 |
| `static/app.js` 개요의 다음 차례 칸 | 지금·다음 세션이 없으면 "찾지 못했습니다"만 쓰고 끝냄. 그 아래 상태 문서의 "지금", 읽는 길, 시작 프롬프트·복사 버튼(C 키)이 사라짐. 로드맵 없이 "다음: S2"가 있으면 `road.sessions`에서 멈춤 | 세션 칸만 비우고 나머지는 그대로 그림. `road?.` | HANDOFF만 있는 프로젝트에서 첫 화면이 텅 비지 않게 |
| `static/app.js` 장부 줄 | 검사 명령이 없어도 "다시 검사" 단추 | "문서 검사 없음 (board.toml [check])" | 없는 도구를 누르게 하지 않음 |
| `static/app.js` 정할 것, `history.js` 바뀐 결정 | 기획서가 없어도 "BRIEF 원문" 단추, "기획서에 … 없습니다" | 단추를 숨기고 "이 프로젝트에는 기획서가 없습니다" | 없는 문서를 있는 것처럼 보이지 않게 |
| `static/history.js` 방향 | "old/README.md에 방향 표가 없습니다" | 옛 방향 문서가 없으면 "이 프로젝트에는 옛 방향 표가 없습니다" | 위와 같음 |
| `server.py` `log_message` | 요청 줄이 깨진 요청이면 `self.path`가 없어 연결이 끊김 | `getattr(self, "path", "")` | 원본에도 있는 잘못. 400으로 답하게 |
| `check.py` | `FACTS`에 PORTFOLIO 사실, 문서가 없으면 멈춤, 파일 조작 시험이 PORTFOLIO 경로(`docs/design/CAMERA.md`, `old`, `refs/user` …)에 기댐, 시험 서버의 접속 기록이 화면에 섞임 | 사실은 `board.toml [facts]`(키마다 고를 수 있음). 없는 문서와 화면이 읽는 장 가운데 없는 것은 skip으로 모두 보임. `board.toml`이 적은 장이 문서에 없으면 실패. 읽는 길은 로드맵 없이도 검사. 시험용 문서를 복사본 안에 만들어 씀, 잠긴 곳은 `board.toml`에서 읽음. 20 MB 넘는 파일과 `skip_search` 폴더는 복사하지 않음. 시험 서버의 기록은 숨김. `--config`, `--root` | 어느 second-brain 프로젝트에서도 "0 failed"가 맞추기의 끝이 되고, skip 목록이 곧 "비어 있는 칸" 목록이 되게 |

## 5. 확인한 것 (2026-10-26)

- **PORTFOLIO 그대로인가:** PORTFOLIO 저장소를 시스템 임시 폴더에 복제하고(원본은 그대로) 그 안의 `tools/board/`에 스킬 코드를 덮어 비교했습니다.
  - 서버가 내놓는 값(상태, 로드맵, 기획서, 계획 변화, 136개 파일의 역할·세션)이 원본과 같았습니다. 다른 것은 현황판 자신의 파일 37개에 붙는 말(4-1의 현황판 줄)과 새 `reading` 값, 덮어쓴 파일이 "커밋 안 된 변경"으로 보인 것뿐입니다.
  - 스킬의 `check.py`: 78 ok, 0 failed, 2 skip(MAP에 아직 없는 "파일의 역할", "용어" 장).
- **다른 프로젝트에서 되는가:** `evals/`의 두 과제를 스킬만 받은 다른 세션 둘이 각각 빈 폴더에서 처음부터 따라 했습니다.
  - 레시피 책(문서가 다 있는 중간 크기): 74 ok, 0 failed. 프로젝트 문서는 그대로. 확인 항목 7개 모두 통과
  - 공책(`CLAUDE.md` + `HANDOFF.md`만): 53 ok, 0 failed, 3 skip. 확인 항목 6개 모두 통과
  - 두 세션이 찾은 문제(4-2, 포트, `[roles]`, 프롬프트의 말, SKILL.md의 빈 곳)를 고친 뒤 두 과제를 다시 세워 0 failed(74 ok·2 skip, 54 ok·5 skip)와 앱 안 브라우저의 다섯 화면을 확인했습니다.

## 6. 원본의 새 판을 옮길 때

1. 원본이 바뀐 곳을 봅니다: `git -C <making-coolassbitch> log --oneline 6e5b6bd.. -- PORTFOLIO/tools/board/`
2. 3장의 "그대로인 것"은 복사하고, 4장의 파일은 바뀐 곳만 손으로 옮깁니다(4장의 일반화를 지우지 않게).
3. 5장처럼 PORTFOLIO 복제본과 `evals/`에서 다시 확인하고, 이 문서의 판·커밋·5장을 고칩니다.

- 4장을 PORTFOLIO 원본에도 넣으면 두 사본이 `board.toml`만 빼고 같아져 6장이 쉬워집니다. 특히 4-2의 `log_message` 잘못은 원본에도 있습니다. 넣을지는 PORTFOLIO 기획 책임 세션이 정합니다.
