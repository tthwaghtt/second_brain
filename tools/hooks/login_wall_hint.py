#!/usr/bin/env python3
"""로그인 화면 감지 훅 (PostToolUse).

원본: ~/MY_PROJECT/second_brain/tools/hooks/login_wall_hint.py (~/.claude/hooks/에는 링크)
설정: matcher에 웹 읽기 도구(WebFetch), 앱 브라우저 읽기 도구(mcp__Claude_Browser__get_page_text·read_page·navigate),
      Chrome 읽기 도구(mcp__claude-in-chrome__get_page_text·read_page·navigate), Artifact를 건다.
      command: python3 ~/.claude/hooks/login_wall_hint.py

하는 일: 도구 결과에 로그인 화면 표시('로그인', 'Sign in', 'Log in', 401·403)가 보이면
  "[로그인 화면] 포기하지 말고 …" 안내를 붙인다(additionalContext). 막지 않는다.
- 로그인 말은 짧은 결과(로그인 화면은 보통 짧다)나 비밀번호 칸이 함께 있을 때만 센다.
  로그인에 대한 긴 글을 읽은 것까지 잡지 않기 위해서다.
- 같은 세션, 같은 주소(호스트)는 10분에 한 번만 알린다.
- Artifact는 읽기(action: read)만 본다.
- 어떤 오류가 나도 출력 없이 종료 코드 0. 잠깐 끄기: 환경 변수 LOGIN_WALL_HINT=off
표준 라이브러리만 쓴다.
"""
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

READ_TOOLS = {
    "WebFetch",
    "mcp__Claude_Browser__get_page_text", "mcp__Claude_Browser__read_page", "mcp__Claude_Browser__navigate",
    "mcp__claude-in-chrome__get_page_text", "mcp__claude-in-chrome__read_page", "mcp__claude-in-chrome__navigate",
    "Artifact",
}
MAX_SCAN = 60000          # 결과 앞쪽 이만큼만 본다
SHORT = 4000              # 이보다 짧은 결과에서는 로그인 말만으로도 로그인 화면으로 본다
WINDOW = 600              # 같은 곳은 10분에 한 번
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "login-wall-hint")

STATUS_RX = re.compile(
    r"\b(?:HTTP(?:/\d(?:\.\d)?)?\s*|status(?:\s*code)?\s*[:=]?\s*|error\s*)(401|403)\b"
    r"|\b401\s+Unauthorized\b|\b403\s+Forbidden\b|\bUnauthorized\b|\bForbidden\b",
    re.I)
LOGIN_RX = re.compile(
    r"로그인|log\s?in\b|sign\s?in\b|sign\s?up to|continue with (?:google|github|apple|email)"
    r"|접근 권한이 없|권한이 필요|authentication required|session expired",
    re.I)
PASSWORD_RX = re.compile(r"비밀번호|password|passcode|2단계 인증|two-factor|verification code|인증 코드", re.I)

HINT = (
    "[로그인 화면] {where}로그인해야 보이는 페이지 같아요. \"못 읽었다\"로 넘기지 마세요. "
    "순서: ① Aside(도하가 로그인해 둔 브라우저를 움직이는 도구)로 같은 주소를 연다 → "
    "② 안 되면 앱 브라우저나 Chrome에서 그 주소를 열고, 어느 주소의 로그인 화면인지 밝혀 도하에게 로그인을 부탁한다. "
    "비밀번호나 인증 번호는 받지도 넣지도 않는다. 자세한 것: second_brain playbooks/login-pages.md"
)


def text_of(v, out, budget=[MAX_SCAN]):
    if budget[0] <= 0:
        return
    if isinstance(v, str):
        out.append(v[:budget[0]])
        budget[0] -= len(v)
    elif isinstance(v, dict):
        for k, x in v.items():
            if k in ("image", "data", "base64", "source") and isinstance(x, (str, dict)) and not isinstance(x, str):
                continue
            text_of(x, out, budget)
    elif isinstance(v, list):
        for x in v:
            text_of(x, out, budget)


def find_url(ti):
    for k in ("url", "uri", "href"):
        u = ti.get(k)
        if isinstance(u, str) and u:
            return u
    return ""


def looks_like_wall(text):
    if STATUS_RX.search(text):
        return True
    if not LOGIN_RX.search(text):
        return False
    return len(text) < SHORT or bool(PASSWORD_RX.search(text))


def seen_recently(session, host):
    try:
        os.makedirs(CACHE, exist_ok=True)
        key = re.sub(r"[^A-Za-z0-9_.-]", "_", "%s-%s" % (session or "nosession", host or "nohost"))[:180]
        p = os.path.join(CACHE, key)
        now = time.time()
        if os.path.exists(p) and now - os.path.getmtime(p) < WINDOW:
            return True
        with open(p, "w") as f:
            f.write(str(now))
        for name in os.listdir(CACHE):
            q = os.path.join(CACHE, name)
            if now - os.path.getmtime(q) > 86400:
                os.remove(q)
    except Exception:
        pass
    return False


def handle(data):
    if not isinstance(data, dict) or data.get("hook_event_name", "PostToolUse") != "PostToolUse":
        return None
    tool = data.get("tool_name") or ""
    if tool not in READ_TOOLS:
        return None
    ti = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    if tool == "Artifact" and ti.get("action") != "read":
        return None
    parts = []
    text_of(data.get("tool_response"), parts, [MAX_SCAN])
    text = "\n".join(parts).strip()
    if not text or not looks_like_wall(text):
        return None
    url = find_url(ti)
    host = urlparse(url).netloc if url else ""
    if seen_recently(data.get("session_id"), host or tool):
        return None
    where = ("%s의 " % host) if host else ""
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                   "additionalContext": HINT.format(where=where)}}


def main():
    if os.environ.get("LOGIN_WALL_HINT", "").lower() == "off":
        return 0
    try:
        raw = sys.stdin.read()
        out = handle(json.loads(raw) if raw.strip() else {})
        if out:
            sys.stdout.write(json.dumps(out, ensure_ascii=False))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
