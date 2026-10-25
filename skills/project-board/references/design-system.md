---
name: 현황판
description: 프로젝트 진행을 엷은 미색 종이 위의 관제실 노선도로 보여 주는 혼자 쓰는 작업 화면
colors:
  ink-blue: "#2c5a9a"
  ink-blue-wash: "#dfe6f0"
  paper-ground: "#f8f6f0"
  paper-panel: "#f1ede3"
  paper-raised: "#e9e4d8"
  paper-well: "#fdfcf9"
  paper-active: "#e6e0d2"
  paper-edge: "#e0d9cb"
  paper-rule: "#e4ddd0"
  control-edge: "#c2b8a4"
  field-edge: "#8f8572"
  warm-ink: "#26231e"
  ink-muted: "#605a4f"
  ink-faint: "#6d665a"
  failed-red: "#a52a21"
  failed-red-wash: "#f5e1dc"
  dark-ground: "#1d1b17"
  dark-panel: "#171512"
  dark-raised: "#27241f"
  dark-well: "#12110e"
  dark-active: "#2a2722"
  dark-edge: "#2d2a24"
  dark-rule: "#29261f"
  dark-control-edge: "#4f4a40"
  dark-field-edge: "#6e675b"
  dark-ink: "#efeadf"
  dark-ink-muted: "#b3ab9c"
  dark-ink-faint: "#a0988a"
  dark-ink-blue: "#93b3e6"
  dark-ink-blue-wash: "#24303f"
  dark-failed-red: "#e98a7c"
  dark-failed-red-wash: "#3a211d"
typography:
  title:
    fontFamily: "Pretendard Variable, Pretendard, -apple-system, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "26px"
    fontWeight: 700
    lineHeight: "32px"
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Pretendard Variable, Pretendard, -apple-system, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: "26px"
  card-title:
    fontFamily: "Pretendard Variable, Pretendard, -apple-system, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    lineHeight: "22px"
  body:
    fontFamily: "Pretendard Variable, Pretendard, -apple-system, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "21px"
    fontFeature: "tnum"
  small:
    fontFamily: "Pretendard Variable, Pretendard, -apple-system, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: "19px"
  label:
    fontFamily: "Pretendard Variable, Pretendard, -apple-system, Apple SD Gothic Neo, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: "16px"
  figure:
    fontFamily: "Courier Prime, Courier New, monospace"
    fontSize: "13px"
    fontWeight: 700
    lineHeight: "16px"
    letterSpacing: "0"
    fontFeature: "tnum"
rounded:
  hair: "2px"
  control: "3px"
  panel: "4px"
  round: "50%"
spacing:
  rail: "80px"
  pad-x: "40px"
  gap: "20px"
  card-pad: "20px"
  control-height: "34px"
components:
  button-primary:
    backgroundColor: "{colors.warm-ink}"
    textColor: "{colors.paper-ground}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "34px"
    typography: "{typography.small}"
  button:
    backgroundColor: "{colors.paper-ground}"
    textColor: "{colors.warm-ink}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "34px"
    typography: "{typography.small}"
  button-small:
    backgroundColor: "{colors.paper-ground}"
    textColor: "{colors.warm-ink}"
    rounded: "{rounded.control}"
    padding: "0 11px"
    height: "28px"
    typography: "{typography.label}"
  button-danger:
    backgroundColor: "{colors.paper-ground}"
    textColor: "{colors.failed-red}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "34px"
  input-text:
    backgroundColor: "{colors.paper-well}"
    textColor: "{colors.warm-ink}"
    rounded: "{rounded.control}"
    padding: "0 10px"
    height: "34px"
  card:
    backgroundColor: "{colors.paper-panel}"
    textColor: "{colors.warm-ink}"
    rounded: "{rounded.panel}"
    padding: "18px 20px"
  prompt-well:
    backgroundColor: "{colors.paper-well}"
    textColor: "{colors.warm-ink}"
    rounded: "{rounded.control}"
    padding: "11px 14px"
    typography: "{typography.small}"
  pill:
    backgroundColor: "{colors.paper-raised}"
    textColor: "{colors.warm-ink}"
    rounded: "{rounded.control}"
    padding: "0 7px"
    height: "20px"
    typography: "{typography.label}"
  pill-failed:
    backgroundColor: "{colors.failed-red-wash}"
    textColor: "{colors.failed-red}"
    rounded: "{rounded.control}"
    padding: "0 7px"
    height: "20px"
  row-selected:
    backgroundColor: "{colors.paper-active}"
    textColor: "{colors.warm-ink}"
    rounded: "{rounded.control}"
    padding: "8px 8px"
  file-tile:
    backgroundColor: "{colors.paper-panel}"
    textColor: "{colors.warm-ink}"
    rounded: "{rounded.control}"
    padding: "6px 10px"
  floating-layer:
    backgroundColor: "{colors.paper-well}"
    textColor: "{colors.warm-ink}"
    rounded: "{rounded.panel}"
    padding: "16px 18px"
---

# Design System: 현황판

> 얼린 사본: PORTFOLIO `tools/board/DESIGN.md`(커밋 6e5b6bd, 2026-10-26)를 그대로 옮겼습니다. 고치지 않습니다. 원본이 바뀌면 다시 복사하고 `DIFF.md`에 적습니다. 현황판 디자인을 "그대로 쓰기"로 고른 프로젝트에서 화면을 고칠 때 기준으로 읽습니다.

## Overview

**Creative North Star: "관제실 노선도판"**

현황판은 이 프로젝트의 관제실에 걸린 노선도판입니다. 세션은 역이고, ROADMAP의 "전제"는 선로이며, 사용자가 확인하는 지점은 역 아래 이름으로 붙습니다. 판은 엷은 미색 종이 위에 따뜻한 먹으로 그리고, 지금 위치와 다음 차례와 고른 것만 기록계의 잉크 청색 한 줄로 짚습니다. 빨강 잉크는 실패한 사실에만 씁니다.

밀도는 일하는 화면의 밀도입니다. 맥 전체 화면(1440×900 안팎)에서 개요의 세 줄(다음 차례와 정할 것, 노선도, 장부 줄)이 한눈에 들어옵니다. 깊이는 그림자가 아니라 종이 한 단계 어두운 판과 1px 가장자리로 냅니다. 숫자·날짜·세션 번호·커밋은 타자기 글꼴로 찍혀 장부처럼 읽힙니다. 화면의 글은 모두 쉬운 한국어입니다.

KPI 타일 줄, 큰 차트, 표로 이어지는 대시보드 기본형을 따르지 않습니다. 그라디언트, 글로우, 무지개 차트, 카드 속 카드는 사용자가 금지했습니다.

**Key Characteristics:**
- 엷은 미색 종이 바탕, 한 단계 어두운 종이 판, 1px 종이 가장자리, 3~4px 모서리
- 강조색은 잉크 청색 하나, 고름은 언제나 1px 청색 선
- 주의는 색이 아니라 먹색 글자와 1px 선으로
- 본문은 Pretendard Variable, 숫자와 식별자는 Courier Prime
- 대표 요소는 노선도(역, 갈래 선로, 점선 순서 선로)
- 어두운 판은 갈색 기 도는 숯검정 바탕에 미색 글자

## Colors

따뜻한 종이와 먹의 무채색 위에, 잉크 청색 하나와 실패에만 쓰는 빨강 하나가 있는 팔레트입니다.

### Primary
- **기록계 잉크 청색** (ink-blue): 지금 위치와 다음 차례(노선도의 역 테두리와 가운데 점, 세션 번호 글자), 고른 것(왼쪽 줄의 고른 화면, 고른 역·행·파일 조각·탭·구분 단추의 1px 밑줄), 링크에 올린 손, 키보드 초점의 2px 윤곽, 체크 상자 색, 꽃 마크. 면으로 칠하지 않습니다.
- **청색 물** (ink-blue-wash): 글자 선택 바탕과, 바구니에 담은 파일을 표시하는 작은 꼬리표 바탕에만 씁니다.

### Neutral
- **엷은 미색 종이** (paper-ground): 화면 바탕, 보통 단추의 바탕, 좁은 창 아래 막대의 바탕.
- **한 단계 진한 종이** (paper-panel): 카드와 파일 조각, 노선도 역의 속.
- **덧댄 종이** (paper-raised): 손을 올린 행과 역, 보통 꼬리표 바탕, 진행 막대의 홈, 불러오는 중 자리.
- **고른 종이** (paper-active): 고른 역·행·파일 조각·구분 단추의 바탕(청색 1px 밑줄과 함께).
- **우물 종이** (paper-well): 시작 프롬프트, 입력칸, 파일 보기, 떠 있는 층(팝오버, 서랍, 확인 창)의 바탕. 바탕보다 밝아 "안쪽"으로 읽힙니다.
- **종이 가장자리 / 줄** (paper-edge, paper-rule): 카드 테두리와 행 사이 1px 줄.
- **단추 가장자리 / 입력칸 가장자리** (control-edge, field-edge): 보통 단추와 빈 자리 점선, 입력칸·구분 단추·점선 순서 선로·버린 노선.
- **따뜻한 먹** (warm-ink): 글자, 노선도 선로와 끝난 역, 채움 단추, 주의 줄의 위쪽 선, 갱신 램프.
- **흐린 먹 / 더 흐린 먹** (ink-muted, ink-faint): 이름표, 보조 글, 지운 줄, 줄 번호.

### Tertiary
- **실패 빨강** (failed-red, failed-red-wash): 실패한 사실에만. 읽기 실패 문구, 문서 검사에서 나온 문제 수, 서버가 끊긴 램프, 중단된 세션 꼬리표, 지우기 단추의 글자.

### Named Rules
**한 줄 청색 규칙.** 청색은 지금, 다음, 고른 것에만 씁니다. 고름은 언제나 1px 청색 선(줄의 오른쪽 선, 행과 역의 밑줄, 탭 밑줄)이고, 청색으로 면을 채우지 않습니다.

**빨강은 사실 규칙.** 빨강은 실패했거나 문제가 난 사실에만 씁니다. 주의, 경고, 바뀐 것에는 빨강도 호박색도 초록도 쓰지 않습니다.

**먹과 선의 주의 규칙.** 알림과 주의는 위에 1px 먹선, 아래에 1px 종이 줄을 두고 그 사이에 먹색 글자로 적습니다. 다시 볼 것 같은 표시는 1px 테두리만 있는 꼬리표로 적습니다.

## Typography

**Body Font:** Pretendard Variable (with Pretendard, -apple-system, Apple SD Gothic Neo, system-ui)
**Label/Mono Font:** Courier Prime (with Courier New, monospace), 400과 700

**Character:** 반듯한 한국어 고딕이 문장을 맡고, 타자기 글꼴이 숫자·날짜·세션 번호·커밋·경로를 장부에 찍듯 맡습니다. 두 글꼴의 역할은 섞이지 않습니다.

### Hierarchy
여섯 크기 토큰(`--fs-title` 26px, `--fs-lg` 20px, `--fs-card` 15px, `--fs-body` 14px, `--fs-sm` 13px, `--fs-xs` 12px)만 씁니다.
- **Title** (700, 26px, 32px): 화면 제목 하나("개요", "계획 변화"). 좁은 창에서는 20px.
- **Headline** (700, 20px, 22~28px): 다음 차례의 세션 이름, 세부 칸 제목, 팝오버·서랍·확인 창 제목.
- **Card title** (700, 15px, 22px): 카드 머리, 문서 본문의 장 제목. 제목 아래 발견 한 줄도 15px.
- **Body** (400, 14px, 21px): 본문. 숫자는 고른 폭(tabular-nums). 문서 문단은 72ch까지.
- **Small** (13px): 행, 장부 줄, 프롬프트, 묶음 이름(600, 흐린 먹).
- **Label** (12px): 역 이름, 왼쪽 줄 이름, 범례, 꼬리표. 대문자 바꾸기와 자간 넓히기는 없습니다.
- **Figure** (Courier Prime, 13~14px, 700): 세션 번호, 날짜, 시각, 커밋, 파일 경로, 판 번호.

### Named Rules
**타자기 숫자 규칙.** 숫자·날짜·세션 번호·커밋·경로는 언제나 Courier Prime으로 찍습니다. 문장은 언제나 Pretendard입니다.

**여섯 크기 규칙.** 새 화면도 여섯 크기 토큰 밖의 크기를 만들지 않습니다.

## Layout

왼쪽에 80px 줄(`--rail`)이 붙어 있고, 나머지는 캔버스입니다. 줄에는 꽃 마크와 다섯 화면(개요, 계획 변화, 로드맵, 파일, 찾기)이 아이콘 아래 12px 한국어 이름과 함께 섭니다. 고른 화면은 줄 오른쪽 가장자리의 1px 청색 선으로 표시합니다.

캔버스는 좌우 40px(`--pad-x`) 여백에 12칸 격자, 칸 사이 20px(`--gap`)입니다. 개요는 1행 다음 차례(8칸) | 정할 것(4칸), 2행 노선도(전체 폭), 3행 장부 줄입니다. 로드맵은 목록 4 : 세부 8로 나누고 세부 칸은 붙어 따라옵니다. 파일은 목록 3 : 조각 4 : 파일 장 5입니다. 카드 안쪽 여백은 18px 20px, 묶음 이름은 위 30px 아래 10px 간격으로 섭니다.

좁은 창에서는 이렇게 바뀝니다.
- 1100px 아래: 여백 24px, 모든 칸이 한 줄씩 쌓이고 나눈 화면도 한 칸이 됩니다.
- 900px 아래: 계획 변화의 날짜 격자 대신 하루씩 이어지는 날짜 목록.
- 640px 아래: 여백 16px, 왼쪽 줄이 화면 아래 58px 막대가 되고(고른 화면은 막대 위쪽 1px 청색 선), 제목은 20px, 이름-값 목록은 한 줄로 쌓입니다.
- 노선도 상자가 600px보다 좁으면: 노선도 대신 단계별 역 목록.

## Elevation & Depth

평평한 종이입니다. 바탕에 놓인 것은 그림자 없이, 한 단계 어두운 종이와 1px 가장자리로 구분합니다. 그림자는 화면 위에 떠 있는 층(팝오버, 서랍, 확인 창) 셋에만 있습니다. 서랍과 확인 창이 열리면 뒤의 앱은 반투명 먹빛 가림막 아래에서 눌리지 않게(inert) 됩니다.

### Shadow Vocabulary
- **떠 있는 층** (`box-shadow: 0 10px 30px rgba(38, 35, 30, .14), 0 1px 3px rgba(38, 35, 30, .10)`): 팝오버, 서랍, 확인 창에만.
- **떠 있는 층, 어두운 판** (`box-shadow: 0 12px 32px rgba(0, 0, 0, .5), 0 1px 3px rgba(0, 0, 0, .4)`): 같은 자리.

### Named Rules
**떠 있을 때만 그림자 규칙.** 종이 위에 놓인 카드, 조각, 행, 단추에는 그림자가 없습니다. 그림자는 다른 것 위에 떠서 열리는 층의 표시입니다.

## Shapes

모서리는 거의 각진 종이입니다. 카드와 떠 있는 층은 4px, 단추·입력칸·행·조각·꼬리표는 3px, 아주 작은 것(체크 상자, 눌리는 글 조각)은 2px입니다. 둥근 것은 노선도의 역, 읽을 길의 번호 원, 갱신 램프뿐입니다. 선은 1px이 기본이고, 노선도 선로만 2px(지나온 구간은 4px)입니다. 빈 자리는 1px 점선 상자, 꺼진 단추는 점선 테두리로 적습니다.

## Components

### Buttons
반듯하고 조용한 종이 단추입니다.
- **Shape:** 살짝 깎은 모서리(3px), 높이 34px, 작은 단추 28px.
- **Primary:** 한 화면에 하나뿐인 채움 단추(개요의 "시작 프롬프트 복사"). 먹 바탕에 종이색 글자. 올리면 먹이 종이 쪽으로 12% 옅어집니다.
- **Default:** 종이 바탕, 1px 단추 가장자리, 올리면 가장자리가 먹색. 누르면 1px 내려갑니다.
- **Danger:** 빨강 글자와 빨강 섞인 가장자리, 지우기에만.
- **Disabled:** 흐린 글자, 점선 테두리, 바탕 없음.
- **Link:** 굵은 먹 글자에 단추 가장자리 색 밑줄, 올리면 글자와 밑줄이 청색.

### Chips
- **Style:** 높이 20px, 3px 모서리, 덧댄 종이 바탕에 12px 글자(생김, 끝남, 추정, 세션 꼬리표).
- **State:** 다시 볼 것 같은 주의는 바탕 없이 1px 입력칸 가장자리 선만. 중단은 빨강 물 바탕에 빨강 글자. 바구니에 담은 것은 청색 물 바탕에 청색 글자.

### Cards / Containers
- **Corner Style:** 4px.
- **Background:** 한 단계 진한 종이.
- **Shadow Strategy:** 없음(Elevation & Depth).
- **Border:** 1px 종이 가장자리.
- **Internal Padding:** 18px 20px. 카드 안은 행과 줄로 나누고, 카드를 다시 넣지 않습니다. 시작 프롬프트와 파일 보기는 카드 안의 밝은 우물(3px 모서리)입니다.

### Rows and file tiles
- **행:** 위쪽 1px 종이 줄로만 나눕니다(첫 행은 줄 없음). 왼쪽 글, 오른쪽 흐린 먹 날짜.
- **고른 행:** 고른 종이 바탕에 1px 청색 밑줄. 역, 로드맵 세션 행, 파일 나무, 파일 조각, 구분 단추, 탭이 모두 같습니다.
- **파일 조각:** 3px 모서리, 진한 종이, 1px 가장자리, 이름(600) 아래 설명 두 줄과 흐린 경로. 좁게 접은 칸에서는 테두리 없는 행이 됩니다.

### Inputs / Fields
- **Style:** 우물 바탕, 1px 입력칸 가장자리, 3px 모서리, 높이 34px(찾기 칸은 40px, 15px 글자).
- **Focus:** 가장자리가 청색이 되고 2px 청색 윤곽.

### Navigation
- **왼쪽 줄:** 80px, 18px 선 아이콘 위, 12px 이름 아래. 기본은 흐린 먹, 올리거나 고르면 먹. 고른 화면은 오른쪽 1px 청색 선. 640px 아래는 아래 막대.

### Transit line diagram (signature)
- **역:** 끝난 역은 먹으로 찬 원, 남은 역은 진한 종이 속에 2px 먹 테두리, 다음 차례는 2px 청색 테두리, 진행 중은 청색 점에 1px 청색 고리, 전제 없이 순서만 적힌 역은 입력칸 가장자리 색 테두리, 빠진 역은 단추 가장자리 색 테두리.
- **선로:** 2px 먹 선, 이미 지나온 구간은 4px. 나란히 가는 세션은 전제에서 갈라지는 갈래 선로. 전제가 없는 순서만의 연결은 입력칸 가장자리 색 점선(5 6).
- **이름:** 역 아래 타자기 세션 번호(700, 13px), 12px 이름, 흐린 역할. 다음 차례 위에는 청색 "다음" 표시. 단계 사이는 1px 세로 줄, 단계 이름은 위에.
- **고름:** 역을 누르면 팝오버로 그 세션이 할 일을 보여 주고, 고른 역은 고른 종이 바탕과 1px 청색 밑줄.
- **범례:** 위 오른쪽에 같은 그림으로 끝남, 진행 중, 다음 차례, 남음, 순서만 적힘.

### Abandoned directions (disused track)
계획 변화의 방향 줄은 날짜에 걸친 선로로 그립니다. 지금 가는 방향은 4px 먹 선로와 먹으로 찬 출발점. 버린 방향은 이름에 취소선, 2px 점선 선로, 속이 빈 출발점, 끝에 세로 멈춤 막대를 둔 폐선입니다.

### Ledger line
노선도 아래, 위아래 1px 가장자리 사이의 타자기 장부 한 줄입니다. 커밋 안 된 변경, 마지막 커밋(시각과 해시), 문서 검사, 계획 변화(옛 방향은 취소선, 화살표로 이어 지금 방향)를 13px 글과 14px 타자기 숫자로 나란히 적습니다.

### Reading path
다음 차례 카드 안의 읽을 길입니다. 26px 번호 원(2px 먹 테두리)을 2px 먹 선으로 이어, 모든 세션이 읽는 곳은 먹으로 찬 원, 이 세션만 읽는 곳은 빈 원으로 적고 원 아래 12px 문서 이름을 답니다. 1100px 아래에서는 넷씩 줄을 바꾸고 이음선을 뺍니다.

### Typewriter diff
바뀐 내용은 타자기 글꼴로 보여 줍니다. 더한 줄은 먹색 굵은 글씨에 "+", 지운 줄은 흐린 먹에 취소선과 "−", 묶음 머리는 흐린 먹입니다. 초록과 빨강은 쓰지 않습니다.

### Floating layers
- **팝오버:** 역 옆에 뜨는 우물 바탕 창(최대 460px), 4px 모서리, 떠 있는 그림자, 160ms 떠오름.
- **서랍:** 오른쪽에서 나오는 문서 본문(최대 620px), 왼쪽 1px 가장자리, 200ms 미끄러짐. 열리면 가림막과 함께 앱이 inert가 됩니다.
- **확인 창:** 옮기기·지우기 앞에 반드시 뜨는 창(최대 560px). 대상 경로는 타자기, 주의는 위 1px 먹선 아래 먹 글자, 가리키는 곳 목록, 오른쪽 끝 단추.
- 움직임 줄이기 설정에서는 모든 움직임이 꺼집니다.

## Do's and Don'ts

### Do:
- **Do** 고른 것은 고른 종이 바탕과 1px 청색 선 하나로 표시합니다.
- **Do** 카드 위에 놓인 것은 1px 종이 가장자리와 한 단계 진한 종이로 구분합니다.
- **Do** 숫자·날짜·세션 번호·커밋·경로는 Courier Prime, 문장은 Pretendard Variable로 씁니다.
- **Do** 주의는 위 1px 먹선과 아래 1px 종이 줄 사이에 먹색 글자로 적습니다.
- **Do** 바뀐 내용은 더한 줄 굵게, 지운 줄 취소선으로 적습니다.
- **Do** 한 화면에 채움 단추는 하나만 둡니다.
- **Do** 좁은 창에서는 그림을 목록으로 바꿉니다(노선도 600px, 날짜 격자 900px, 왼쪽 줄 640px).

### Don't:
- **Don't** 그라디언트, 글로우, 무지개 차트, 카드 속 카드를 쓰지 않습니다.
- **Don't** 팝오버·서랍·확인 창이 아닌 곳에 그림자를 넣지 않습니다.
- **Don't** 청색으로 면을 칠하거나, 지금·다음·고름(과 꽃 마크)이 아닌 곳에 청색을 쓰지 않습니다.
- **Don't** 주의에 호박색이나 초록을 쓰지 않고, 실패가 아닌 것에 빨강을 쓰지 않습니다.
- **Don't** 체크박스 수로 진행 막대를 그리거나 문서에 없는 수치를 지어내지 않습니다.
- **Don't** 여섯 크기 토큰 밖의 글자 크기, 대문자 바꾸기, 넓힌 자간을 쓰지 않습니다.
