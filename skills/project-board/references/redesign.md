# 현황판 디자인을 다시 정하기

> SKILL.md 4장에서 사용자가 "이 프로젝트에 맞게 다시 정하기"를 골랐을 때만 읽는다. 절차는 PORTFOLIO에서 현황판을 만든 순서(현황판 `README.md` 6장)와 같다.

## 1. 크기와 시작

- 세션 하나 크기다(PORTFOLIO에서는 질문·시안·검수까지 하루 저녁). 먼저 plan-first로 계획을 보고하고 승인을 받는다.
- 그동안 현황판은 지금 디자인으로 돈다. 다시 정하는 일은 `tools/board/` 안에서만 한다.

## 2. 사용자가 처음부터 정한 것 (PORTFOLIO 원문, 2026-10-25)

- 디자인은 AI 티가 나면 안 된다.
- 금지: 그라디언트, 글로우, 무지개 차트, 지어낸 수치, 카드 속 카드.
- 실제 데이터만 쓴다. 시안도 그 프로젝트의 진짜 문서로 그린다.

## 3. 순서

1. **impeccable init** (`--target tools/board/`): `tools/board/PRODUCT.md`가 생긴다. `--target`을 주지 않으면 프로젝트 맨 위의 PRODUCT.md(그 프로젝트 본체의 것)를 쓰므로 꼭 준다.
   - 물을 것(추천 답을 붙이고, 생각이 필요한 것은 서술형으로): 누가 언제 보나, 제 몫을 했다고 느낄 때, 열자마자 답할 질문, 창 크기, 밝은·어두운 판, 가장 자주 할 일.
2. **impeccable shape**: 화면 방향 계약(`tools/board/.impeccable/surfaces/`).
3. **design-taste-frontend app-screens**: 방향 셋을 뽑아 첫 화면(개요)만 실제 데이터로 그려 나란히 보인다. 사용자가 고르거나 섞는다.
4. **구현**: 주로 `static/app.css`(색·글꼴·간격)를 고친다. 짜임이 바뀌면 `static/*.js`도.
   - 바꾸지 않는 것: 서버 주소(`/api/...`)와 데이터 모양, `textContent`로만 그리기(`innerHTML` 없음), CSP(외부 글꼴·스크립트 없음).
   - 새 글꼴은 파일로 `static/fonts/`에 둔다. 받는 것은 매번 허락을 받는다.
5. **검수**: design-taste lint와 `inspect --app`, impeccable critique·audit·polish, 마감 검토.
6. **기록**: impeccable document → `tools/board/DESIGN.md`.
7. `python3 tools/board/check.py`가 0 failed인지 본다.

## 4. PORTFOLIO에서 배운 것

- design-taste가 고르는 글꼴에 한글이 없을 수 있다(Public Sans). 한글은 Pretendard를 쓰고 검사기의 `font-not-dealt`를 이유와 함께 허용한다.
- 문서에서 온 기호("★ 지금")는 바꾸지 않고 `emoji` 검사를 이유와 함께 허용한다.
- 숨겨진 창에서는 animation frame과 ResizeObserver가 멈춘다. 그림은 타이머로도 한 번 그린다.
- 사용자는 시안을 보고 고른다. 숫자나 말보다 화면을 먼저 보인다.
