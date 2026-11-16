너는 데일리 바이럴 카드 프로젝트의 S5c 중첩 세션이야. 목표는 경쟁사 분석 탭의 데이터 만들기야(docs/PLAN.md 3장 S5c). 지휘 세션이 너를 열었고, 끝나면 지휘 세션이 결과를 검토해.
배경: 팀원이 대시보드에 '경쟁사 분석' 탭을 원한다. 도하가 회사 노션 계정 25개를 회사 유료 Apify로 직접 소규모 크롤해(데모 전 2번), 계정마다 평소 조회수(최근 릴스 중앙값), 터진 릴스의 훅·형식·CTA, 계정끼리 겹치는 훅을 정리한다. 형 DB에서 나온 처음 보는 계정 3~5개를 제안 박스에 넣는다. 결과는 Supabase의 comp_ 표 3개에 넣을 예정이지만, 표 적용은 카드 API 담당 팀원과 칸을 맞추고 도하가 허락한 뒤 지휘 세션이 한다. S5a(형 DB 가공), S5b(깊은 분석)가 동시에 돈다.
먼저 읽을 것(장 단위로만): CLAUDE.md 전체, STATUS.md 1·2·6장, docs/PLAN.md 0·1·3장(S5c), docs/PROJECT_BRIEF.md 5장, docs/reports/2026-11-14_replan-v32-answers.md, docs/reports/2026-11-14_competitor-tab-design.md(전부), docs/reports/2026-11-14_company-notion.md 5·6장, docs/reports/2026-11-14_apify-price-check.md, docs/reports/2026-11-14_S4b-media-tool.md 12장과 team-repo/pipeline/media/README.md, team-repo/pipeline/analysis/의 playbook.md·prompt.md(훅·형식·CTA를 회사 사전 이름으로 붙일 때).
작업 장소: 이 폴더 안의 team-repo/(브랜치 feature/pipeline)에서 pipeline/competitors/와 supabase/migrations/의 새 초안 파일 1개만 만들고 고쳐. 산출물은 pipeline/data/competitors/<날짜>/(git 제외). pipeline/media/는 쓰기만 하고 고치지 마. 다른 폴더는 다른 세션 몫이다. 커밋·push 금지, 지휘 문서 수정 금지. 보고는 docs/reports/2026-11-14_S5c-competitors.md에 써.
대상 25개: 경쟁사 account01, account02, account03, account04, account05, account06 / AI SaaS account07, account08, account09, account10 / 인사이트 account11, account12, account13, account14, account15, account16, account17, account18, account19, account20, account21, account22, account23, account24, account25
할 일:
1) 1차 크롤: apify/instagram-reel-scraper에 계정 이름(계정마다 최근 15개, 대본·영상 보관·공유 수 추가 기능은 끔), apify/instagram-profile-scraper로 팔로워 수. 회사 계정 커넥터로만, 이번 크롤 총 요금 상한 $1.2. 먼저 3개 계정으로 시험해 칸과 비용을 확인한 뒤 나머지를 돌린다. 실제 비용과 시간을 적는다.
2) 계정마다: 평소 조회수 = 최근 릴스 조회수(videoPlayCount) 중앙값(계정당 하나, 5개 미만이면 비움). 배수 = 조회수 ÷ 평소 조회수. 터진 릴스 = 3배 이상 + 6개월 안 + 광고·이벤트 아님.
3) 터진 릴스 가운데 계정마다 상위 3편만 S4b ingest로 영상 재료를 만들고, 훅 문장(첫 3초 말·자막, 근거 표시)·훅 공식·형식(이야기 구조)·CTA를 회사 사전 이름으로 채운다(하위 에이전트 사용, 다른 하위 에이전트가 검사).
4) 겹치는 훅: 같은 훅 공식을 쓴 계정 수.
5) 제안 박스: 기준은 "형 판독 그대로 + 안전장치"(최근 14일 형 판독 통과 릴스 2편 이상, 광고 아님, comp 계정과 노션 계정에 없음, 배수 순, AI가 분류를 거름, 3~5개). 형 DB가 없으면 함수만 만들고 비워 둔다.
6) 저장 준비: 설계 초안의 표 3개(comp_accounts, comp_reels, comp_suggestions) 모양 그대로 JSON 3개를 pipeline/data/competitors/<날짜>/에 쓴다. 마이그레이션 SQL 초안을 supabase/migrations/에 새 파일로 두되 원격에는 절대 적용하지 마.
7) 카드 API 담당 팀원에게 보낼 칸 설명 초안(표마다 칸 이름·뜻·예시 값, 대시보드에서 읽는 법)을 보고서에 적어. 보내는 것은 도하가 한다.
지킬 것: Supabase는 읽기만, 쓰기·표 만들기·바꾸기 절대 금지(도하 허락은 지휘 세션이 받는다). Apify는 회사 계정 커넥터로만, 개인 계정 금지, 상한. 댓글 단 사람 이름·태그된 사람은 저장하지 마. 영상·원본은 git 밖. 도하에게 직접 묻지 말고 물을 것은 보고서에.
멈출 곳: 1차 크롤 결과와 JSON·SQL 초안을 보고한 뒤.
완성 기준: 25개 계정 요약과 터진 릴스 표(JSON)가 있다. 3개 계정의 중앙값·배수를 손으로 다시 계산해 맞는다. 실제 비용이 상한 안이다. 마지막 메시지에 보고서 경로와 한 줄 요약을 써.
시작할 때 이해한 계획을 10줄 이내로 적고 바로 시작해(답을 기다리지 마).
