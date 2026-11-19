#!/usr/bin/env python3
"""한국어로 물으면 한국어로 답하게 하는 훅.

원본: ~/MY_PROJECT/second_brain/tools/hooks/korean_reply.py (~/.claude/hooks/korean_reply.py는 이 파일로 가는 링크)

쓰는 법(설정 파일의 command):
  python3 ~/.claude/hooks/korean_reply.py prompt   # UserPromptSubmit
  python3 ~/.claude/hooks/korean_reply.py stop     # Stop

- prompt: 사용자 프롬프트에 한글이 충분하면 "보이는 출력은 한국어로" 지시를 덧붙이고,
  세션별 상태 파일에 "이 세션은 한국어"라고 적는다. 언어와 상관없이 프롬프트마다
  "애매하면 질문 팝업, 큰 일이면 큰 일 순서" 안내 한 줄을 붙인다(2026-11-19).
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
    "[한국어 답 규칙] 사용자가 한국어로 썼습니다. 생각은 영어로 해도 되지만, "
    "사용자에게 보이는 모든 출력(답, 마무리 글, 마무리 상자, 질문, 다른 세션에 보내는 메시지, "
    "새 세션 첫 지시문)은 한국어로 쓰세요. 코드, 명령어, 파일 경로, 고유 이름은 그대로 둡니다."
)
ASK_MSG = (
    "[애매하면 질문 팝업] 작은 일인데 두 가지로 읽히면 실행 전에 질문 팝업(AskUserQuestion)으로 묻는다. "
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
