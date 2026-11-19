# 훅 원본 (tools/hooks/)

> 날짜: 2026-11-19 · 출처: Creazy 바이럴 카드(ist-virerfind)/지휘 · 근거: 경험 · 태그: 훅, 설정, 권한
> **규칙:** 글로 된 규칙만으로는 안 지켜지는 것을 기계로 지키게 한다. 훅 원본은 여기 두고 `~/.claude/hooks/`에는 링크를 둔다. 전역 설정에 넣는 덩어리는 `settings_block.py` 하나로 만든다. · **적용 범위:** 도하의 모든 프로젝트(전역 설정)

## 1. 무엇이 어디에 걸리나

| 훅 | 언제 | 하는 일 | 막나 |
|---|---|---|---|
| `korean_reply.py prompt` | 프롬프트마다(UserPromptSubmit) | 한국어 프롬프트면 "보이는 글은 한국어로" 안내, 언제나 "애매하면 질문 팝업, 큰 일이면 큰 일 순서" 안내 한 줄 | 아니오 |
| `korean_reply.py stop` | 답 끝(Stop) | 한국어 세션인데 답의 한글 비율이 40% 아래면 한 번 막고 다시 쓰게 함 | 한 번 |
| `plain_lint.py --hook` (plain-words 스킬) | 답 끝(Stop) | 용어집(`docs/GLOSSARY.md`)이 있는 프로젝트에서 마지막 답에 풀지 않은 말이 있으면 한 번 막음 | 한 번 |
| 〃 | 보내기 직전(PreToolUse): 마무리 상자, 세션 메시지, 새 세션 지시문, 세션 넘기기 지시문 | 남은 말이 있으면 첫 시도만 멈춤(10분 안에 다시 보내면 통과) | 한 번 |
| 〃 | 보낸 뒤·올린 뒤(PostToolUse): 위 보내는 도구, 페이지(Artifact) | 경고만 붙임 | 아니오 |
| 읽기 검사 `prompt` 훅(Sonnet) | 답 끝(Stop) | 300자쯤 넘는 한국어 답을 맥락 없는 도하 눈으로 읽고 함축어·추상화·빠진 주어와 목적어·풀지 않은 내부 이름을 짚음 | 한 번 |
| 읽기 검사 `agent` 훅(Sonnet) | 페이지 올리기 직전(PreToolUse: Artifact) | 페이지 파일을 읽고 같은 기준으로 봄. 분명한 문제가 2개 이상이면 올리기를 막고 이유를 도구 오류로 돌려줌(`continueOnBlock`) | 문제가 있으면 |
| `login_wall_hint.py` | 웹·브라우저 읽기 뒤(PostToolUse) | 로그인 화면 표시가 보이면 "[로그인 화면]" 안내(Aside → 앱 브라우저·Chrome에서 로그인 부탁) | 아니오 |

- **파일 저장(Write·Edit·MultiEdit)에는 걸지 않는다**(2026-11-19 도하 결정). 상태 문서와 보고서는 쓴 뒤 손으로 `plain_lint.py <파일>`을 돌린다.
- 판정 지시문 원본: `read_check_prompt.md`(1장 채팅 답, 2장 페이지).
- 권한 확인 창(`permissions.ask`): `Bash(git push *)`, `Bash(git -C * push *)`, `Bash(gh pr create *)`, `Bash(gh pr merge *)`, Supabase 표 바꾸기 도구(`mcp__d6595627-c179-45a4-9fab-2718fd480a52__apply_migration`). 확인 창은 허용 목록보다 먼저라서, 넓은 허용 규칙이 있어도 뜬다. Supabase SQL 실행 도구는 읽기에도 쓰여서 넣지 않았다.

## 2. 넣고 빼기

```bash
python3 tools/hooks/settings_block.py            # 넣을 덩어리를 보여 주기만
python3 tools/hooks/settings_block.py --apply    # 백업(~/.claude/settings.json.bak-날짜) 뒤 넣기
python3 tools/hooks/settings_block.py --check    # 설정이 원본과 같은지
python3 tools/hooks/settings_block.py --remove   # 우리 덩어리만 빼기
python3 tools/hooks/test_hooks.py                # 한국어 훅·로그인 훅 시험
```

- 다른 훅(Clawd on Desk, impeccable)과 다른 설정 칸은 건드리지 않는다. 한국어 답 훅은 원래 설정에 있던 줄을 그대로 쓴다(파일만 링크로 바뀜).
- 잠깐 끄기: 한국어 훅 `KOREAN_REPLY_HOOK=off`, 로그인 훅 `LOGIN_WALL_HINT=off`. 읽기 검사와 쉬운 말 검사는 `--remove`로 뺀다.

## 3. 잰 것 (2026-11-19, 임시 폴더에서 `claude -p`, 본 모델 Sonnet)

- 채팅 답 읽기 검사: 막지 않을 때 답 하나에 **약 2초**가 더 걸렸다(짧은 답 6.6초 → 8.5초, 300자쯤 답 8.5초 → 10.7초, 각 3번 잰 대략값). 막으면 다시 쓰는 시간이 더 든다(일부러 추상적으로 쓴 600자 답: 모두 32초).
- 막을 때 Claude에게 돌아가는 글에는 판정 지시문 전체가 이름표로 붙는다(약 1,400자). 막을 때만 드는 비용이다.
- 페이지 읽기 검사: 올리기 한 번에 **약 10~20초**(파일을 읽는 하위 에이전트). 어려운 시험 페이지는 두 번 다 막혔고 올라가지 않았다. 쉬운 시험 페이지는 통과했다.
