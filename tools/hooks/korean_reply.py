#!/usr/bin/env python3
"""답 쓰는 법 훅: 한국어로 물으면 한국어로, 맥락 없는 도하가 읽히게 답하게 하고, 실행 전 생각을 맞추게 한다.

원본: ~/MY_PROJECT/second_brain/tools/hooks/korean_reply.py (~/.claude/hooks/korean_reply.py는 이 파일로 가는 링크)

쓰는 법(설정 파일의 command):
  python3 ~/.claude/hooks/korean_reply.py prompt   # UserPromptSubmit
  python3 ~/.claude/hooks/korean_reply.py stop     # Stop

- prompt: 사용자 프롬프트에 한글이 충분하면 "[답 쓰는 법]" 안내를 덧붙이고
  (보이는 출력은 한국어로, 이 세션·프로젝트에서만 만든 이름은 처음 나올 때 풀기, 앞 대화를 가리키는 말 대신
  그것이 무엇인지 쓰기, 주어와 목적어 쓰기. 앱·도구 이름, 전문용어, 고유명사는 그대로. 2026-11-24 도하가 정함),
  세션별 상태 파일에 "이 세션은 한국어"라고 적는다. 언어와 상관없이 프롬프트마다
  "생각 맞추기" 안내를 붙인다: 무엇을·왜·애매한 곳을 점검하고, 걸리는 점이 없어도
  질문 팝업으로 이해한 것을 한 번 확인하고, 큰 일이면 큰 일 순서를 쓴다
  (2026-11-19 처음, 2026-11-23 도하가 "걸리는 점이 없어도 확인"으로 넓힘).
- stop: 그 세션이 한국어이고, 마지막 답의 한글 비율이 낮으면 한 번만 막고 한국어로
  다시 쓰게 한다. 다시 쓴 뒤(stop_hook_active=true)에는 절대 막지 않는다(무한 반복 방지).
- 생각(thinking)은 보지 않는다. 코드 블록, 인라인 코드, 주소, 파일 경로는 세지 않는다.
- 어떤 오류가 나도 조용히 통과한다(exit 0).
- 잠깐 끄기: 환경 변수 KOREAN_REPLY_HOOK=off
"""
import json
import os
import re
import sys
import time

STATE_DIR = os.path.expanduser("~/.claude/hooks/state/korean_reply")
PROMPT_MIN_HANGUL = 2      # 프롬프트에 한글이 2자 이상이고
PROMPT_MIN_RATIO = 0.2     # 한글 / (한글+로마자) 비율이 20% 이상이면 한국어 프롬프트
REPLY_MIN_LETTERS = 20     # 답의 글자(한글+로마자)가 20자 미만이면 검사하지 않음
REPLY_MIN_RATIO = 0.4      # 답의 한글 비율이 40% 미만이면 막음

HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
LATIN = re.compile(r"[A-Za-z]")
ASKS_OTHER_LANG = re.compile(r"(영어|영문|일본어|중국어|외국어)\s*(로|으로)\s*(만\s*)?(써|작성|번역|답|대답|말해|바꿔|옮겨)|in English")

CONTEXT_MSG = (
    "[답 쓰는 법] 사용자가 한국어로 썼습니다. 생각은 영어로 해도 되지만, "
    "사용자에게 보이는 모든 출력(답, 마무리 글, 마무리 상자, 질문, 다른 세션에 보내는 메시지, "
    "새 세션 첫 지시문)은 한국어로 쓰세요. 코드, 명령어, 파일 경로, 고유 이름은 그대로 둡니다. "
    "도하는 앞 대화를 못 보고 읽습니다. 이 세션이나 프로젝트에서만 만든 이름(S1, B3a, 칸 이름 같은 것)은 "
    "답마다 처음 나올 때 한 번 풀고, '아까', '위의 답' 대신 그것이 무엇인지 쓰고, 문장마다 누가 무엇을 하는지 쓰세요. "
    "앱·도구 이름, 전문용어, 일반 지식, 고유명사는 풀지 않고 그대로 씁니다."
)
ASK_MSG = (
    "[생각 맞추기] 실행 전에 스스로 점검한다. ① 무엇을 하라는지(what)와 왜 보냈는지(why)가 보이나? "
    "② 애매하거나 두 가지로 읽히는 곳, 빠진 정보, 뜻이 흐린 낱말이 있나? "
    "걸리는 점이 없어도 질문 팝업(AskUserQuestion)으로 이해한 것을 한 번 확인한다. "
    "걸리는 점이 있으면 생각한 후보나 이해한 것을 선택지로 주고, 도하가 자기 말로 답할 열린 질문도 함께 묻는다. "
    "도구 기본 설명이 '흔한 기본값이 있으면 묻지 말고 진행하라'고 해도, 도하의 의도(무엇을·왜)에 관한 것은 "
    "기본값으로 정하지 않고 묻는다. 기본값으로 정해도 되는 것은 파일 이름이나 코드 모양처럼 의도와 상관없는 것뿐이다. "
    "예외: AI가 바로 앞에 물은 것에 대한 짧은 답('응', '계속해', 마무리 상자 버튼)은 다시 묻지 않는다. "
    "도하가 바로 답할 수 없는 실행(예약 작업, 다른 세션이 보낸 메시지, 화면 없는 claude -p)은 이해한 것을 글로 남기고 진행하되, "
    "의도가 갈리는 결정은 짐작하지 않고 '확인 필요'로 남긴다. "
    "큰 일이면 이해 보고 → 질문 → 계획 → 승인 → 실행. "
    "(큰 일: 여러 단계, 되돌리기 어려움, 토큰이 많이 듦, 큰 기능을 넣거나 고치거나 새로 만듦 · 공통 규칙 ~/.claude/CLAUDE.md 2장)"
)


def strip_noise(text: str) -> str:
    text = re.sub(r"<system-reminder>.*?</system-reminder>", " ", text, flags=re.S)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)          # 코드 블록
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)                       # 인라인 코드
    text = re.sub(r"https?://\S+", " ", text)                    # 주소
    text = re.sub(r"\]\([^)]*\)", "]", text)                     # 마크다운 링크 대상
    text = re.sub(r"(?:~|\.{1,2})?/?(?:[\w.@-]+/)+[\w.@-]*", " ", text)  # 경로 a/b/c
    text = re.sub(r"\b[\w-]+\.(?:py|js|ts|tsx|jsx|json|md|html|css|sql|sh|yml|yaml|toml|txt|csv|mjs)\b", " ", text)
    return text


def ratio(text: str):
    t = strip_noise(text or "")
    h = len(HANGUL.findall(t))
    l = len(LATIN.findall(t))
    total = h + l
    return h, total, (h / total if total else 0.0)


def state_path(session_id: str) -> str:
    safe = re.sub(r"[^\w-]", "_", session_id or "unknown")
    return os.path.join(STATE_DIR, safe + ".json")


def save_state(session_id: str, korean: bool):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(state_path(session_id), "w") as f:
            json.dump({"korean": korean, "ts": time.time()}, f)
        # 30일 넘은 상태 파일 정리
        cutoff = time.time() - 30 * 86400
        for name in os.listdir(STATE_DIR):
            p = os.path.join(STATE_DIR, name)
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
    except Exception:
        pass


def load_state(session_id: str):
    try:
        with open(state_path(session_id)) as f:
            return json.load(f).get("korean")
    except Exception:
        return None


def block_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def is_real_user(d) -> bool:
    if d.get("type") != "user" or d.get("isMeta"):
        return False
    c = (d.get("message") or {}).get("content")
    if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
        return False
    return bool(block_text(c).strip())


def read_transcript(path: str):
    """(마지막 진짜 사용자 프롬프트, 그 뒤 마지막 어시스턴트 글)"""
    last_user, last_asst = "", ""
    try:
        with open(path) as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if is_real_user(d):
                    last_user = block_text(d["message"]["content"])
                    last_asst = ""
                elif d.get("type") == "assistant":
                    t = block_text((d.get("message") or {}).get("content"))
                    if t.strip():
                        last_asst = t
    except Exception:
        pass
    return last_user, last_asst


def on_prompt(data):
    prompt = data.get("prompt") or ""
    h, total, r = ratio(prompt)
    korean = h >= PROMPT_MIN_HANGUL and r >= PROMPT_MIN_RATIO
    if ASKS_OTHER_LANG.search(prompt):
        korean = False  # "영어로 써 줘"처럼 다른 말로 달라고 하면 건드리지 않음
    save_state(data.get("session_id", ""), korean)
    msg = (CONTEXT_MSG + "\n" + ASK_MSG) if korean else ASK_MSG
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": msg}}, ensure_ascii=False))


def on_stop(data):
    if data.get("stop_hook_active"):
        return  # 이미 한 번 막았음: 다시 막지 않는다
    sid = data.get("session_id", "")
    korean = load_state(sid)
    reply = data.get("last_assistant_message") or ""
    if korean is None or not reply:
        user, asst = read_transcript(data.get("transcript_path") or "")
        if korean is None:
            h, _, r = ratio(user)
            korean = h >= PROMPT_MIN_HANGUL and r >= PROMPT_MIN_RATIO
        reply = reply or asst
    if not korean or not reply:
        return
    h, total, r = ratio(reply)
    if total < REPLY_MIN_LETTERS or r >= REPLY_MIN_RATIO:
        return
    print(json.dumps({
        "decision": "block",
        "reason": (f"[한국어 답 규칙] 사용자는 한국어로 물었는데 마지막 답의 한글 비율이 "
                   f"{round(r * 100)}%입니다. 같은 내용을 한국어로 다시 써서 답하세요. "
                   "도구는 다시 부르지 말고 글만 다시 씁니다. 코드, 명령어, 파일 경로는 그대로 둡니다."),
    }, ensure_ascii=False))


def main():
    if os.environ.get("KOREAN_REPLY_HOOK", "").lower() == "off":
        return
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        data = json.load(sys.stdin)
        if os.environ.get('KOREAN_REPLY_DEBUG'):
            open(os.environ['KOREAN_REPLY_DEBUG'],'a').write(mode+' '+json.dumps(data,ensure_ascii=False)[:1500]+'\n')
    except Exception:
        return
    try:
        if mode == "prompt":
            on_prompt(data)
        elif mode == "stop":
            on_stop(data)
    except Exception:
        pass


if __name__ == "__main__":
    main()
