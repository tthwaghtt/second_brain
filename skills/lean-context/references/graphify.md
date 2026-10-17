# Graphify로 코드 지도 만들기

> 근거: Graphify-Labs/graphify README·docs(2026-10-17에 읽음, 0.9.92). 아직 실제로 써 보지 않음. 처음 쓰면 결과를 second_brain inbox에 남깁니다.

## 언제
- 코드 파일이 수십 개 이상이고, 세션마다 구조를 다시 탐색하고 있을 때.
- 파일 몇 개짜리는 그냥 읽는 편이 낫습니다(README도 같은 말).

## 명령
```bash
uv tool install graphifyy        # y 두 개. 다른 graphify* 패키지는 관계없음
graphify install --project       # 이 저장소에만 스킬 설치
graphify claude install          # "코드 질문은 그래프 먼저" + 훅(Grep/Glob/Read 전에 유도)
graphify hook install            # 커밋·브랜치 전환 때 갱신. git pull 뒤엔 graphify update .
```
Claude Code 안에서: `/graphify .`, 바뀐 것만 `/graphify . --update`.
질의: `graphify query "<질문>"`, `graphify path A B`, `graphify explain X`.

## 결과
`graphify-out/`: `graph.html`(사람용), `GRAPH_REPORT.md`(요약), `graph.json`(질의용). 보고서도 통째로 읽지 말고 `query`부터 씁니다.

## 주의
- 코드만 다루면 로컬에서 돌고 LLM 토큰이 0입니다. 문서·PDF·이미지까지 넣으면 토큰이 들고 설정된 외부 API로 내용을 보냅니다. 민감하면 `--code-only` 또는 `GRAPHIFY_BACKEND=none`.
- 선마다 `EXTRACTED`(코드에 그대로 있음)와 `INFERRED`(추론함)가 붙습니다. `INFERRED`는 고치기 전에 원본 코드로 확인합니다.
- 질의 기록이 `~/.cache/graphify-queries.log`에 남습니다(끄기: `GRAPHIFY_QUERY_LOG_DISABLE=1`).
- README의 "토큰 80% 절감"은 유료 클라우드 광고이고, 성능 숫자는 모두 자기 측정입니다.
- 한국어 마크다운 노트 모음(second_brain 같은 것)에는 맞지 않습니다. 그런 곳에는 검색이 더 낫습니다.
