#!/usr/bin/env python3
"""second_brain 훅과 권한 확인 창을 전역 설정(~/.claude/settings.json)에 넣는 덩어리를 만든다.

  python3 tools/hooks/settings_block.py            # 넣을 덩어리(JSON)를 보여 주기만 한다
  python3 tools/hooks/settings_block.py --apply    # 백업을 만든 뒤 넣는다(전에 넣은 우리 덩어리는 바꿔 끼움)
  python3 tools/hooks/settings_block.py --check    # 설정에 지금 덩어리가 그대로 있으면 0, 아니면 1
  python3 tools/hooks/settings_block.py --remove   # 우리 덩어리만 뺀다(백업을 만든 뒤)

- 다른 훅(Clawd on Desk, impeccable 등)과 다른 설정 칸은 건드리지 않는다.
- 우리 덩어리는 command에 plain_lint.py·login_wall_hint.py가 들었거나, prompt가 "너는 '읽기 검사'다"로 시작하는 것으로 알아본다.
- 한국어 답 훅(korean_reply.py)은 이미 설정에 있어서 여기서 다루지 않는다(링크만 원본으로 바꿈).
- 읽기 검사 지시문은 read_check_prompt.md의 ```prompt 덩어리 두 개에서 읽는다.
표준 라이브러리만 쓴다.
"""
import argparse
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.expanduser("~/.claude/settings.json")
MODEL = "claude-sonnet-5-5"
LINT = 'python3 "$HOME/.claude/skills/plain-words/scripts/plain_lint.py" --hook'
LOGIN = 'python3 "$HOME/.claude/hooks/login_wall_hint.py"'
SEND = "mcp__ccd_turn__wrap_up|SendMessage|mcp__ccd_session__start_session|mcp__ccd_session__hand_off_to_session"
LOGIN_MATCH = ("^(WebFetch|Artifact|mcp__Claude_Browser__(get_page_text|read_page|navigate)"
               "|mcp__claude-in-chrome__(get_page_text|read_page|navigate))$")
ASK = [
    "Bash(git push *)",
    "Bash(git -C * push *)",
    "Bash(gh pr create *)",
    "Bash(gh pr merge *)",
    "mcp__d6595627-c179-45a4-9fab-2718fd480a52__apply_migration",
]
MARK = "너는 '읽기 검사'다"


def prompts():
    text = open(os.path.join(HERE, "read_check_prompt.md"), encoding="utf-8").read()
    blocks = re.findall(r"```prompt\n(.*?)\n```", text, re.S)
    if len(blocks) != 2 or not all(b.startswith(MARK) for b in blocks):
        sys.exit("read_check_prompt.md에서 prompt 덩어리 두 개를 찾지 못했어요.")
    return blocks


def block():
    stop_prompt, page_prompt = prompts()
    lint = {"type": "command", "command": LINT, "timeout": 20}
    return {
        "Stop": [
            {"hooks": [lint]},
            {"hooks": [{"type": "prompt", "prompt": stop_prompt, "model": MODEL, "timeout": 30,
                        "statusMessage": "읽기 검사"}]},
        ],
        "PreToolUse": [
            {"matcher": SEND, "hooks": [lint]},
            {"matcher": "Artifact", "hooks": [{"type": "agent", "prompt": page_prompt, "model": MODEL,
                                               "timeout": 120, "continueOnBlock": True,
                                               "statusMessage": "페이지 읽기 검사"}]},
        ],
        "PostToolUse": [
            {"matcher": "Artifact|" + SEND, "hooks": [lint]},
            {"matcher": LOGIN_MATCH, "hooks": [{"type": "command", "command": LOGIN, "timeout": 10}]},
        ],
    }


def ours(hook):
    c = hook.get("command") or ""
    p = hook.get("prompt") or ""
    return "plain_lint.py" in c or "login_wall_hint.py" in c or p.startswith(MARK)


def strip_ours(settings):
    hooks = settings.get("hooks") or {}
    for ev in list(hooks):
        kept = []
        for group in hooks[ev]:
            hs = [h for h in group.get("hooks", []) if not ours(h)]
            if hs:
                g = dict(group)
                g["hooks"] = hs
                kept.append(g)
        hooks[ev] = kept
    perms = settings.get("permissions")
    if isinstance(perms, dict) and isinstance(perms.get("ask"), list):
        perms["ask"] = [r for r in perms["ask"] if r not in ASK]
        if not perms["ask"]:
            del perms["ask"]
        if not perms:
            del settings["permissions"]
    return settings


def merged(settings):
    s = strip_ours(json.loads(json.dumps(settings)))
    hooks = s.setdefault("hooks", {})
    for ev, groups in block().items():
        hooks.setdefault(ev, []).extend(groups)
    perms = s.setdefault("permissions", {})
    ask = perms.setdefault("ask", [])
    for r in ASK:
        if r not in ask:
            ask.append(r)
    return s


def load():
    with open(SETTINGS, encoding="utf-8") as f:
        return json.load(f)


def save(s, tag):
    bak = SETTINGS + ".bak-" + time.strftime("%Y-%m-%d")
    if os.path.exists(bak):
        bak = SETTINGS + ".bak-" + time.strftime("%Y-%m-%d-%H%M%S")
    shutil.copy2(SETTINGS, bak)
    tmp = SETTINGS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(tmp, encoding="utf-8") as f:
        json.load(f)  # 깨졌으면 여기서 멈춘다(원본은 그대로)
    os.replace(tmp, SETTINGS)
    print("%s: %s (백업 %s)" % (tag, SETTINGS, bak))


def main(argv):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--remove", action="store_true")
    a = ap.parse_args(argv)
    if a.apply:
        save(merged(load()), "넣었어요")
    elif a.remove:
        save(strip_ours(load()), "뺐어요")
    elif a.check:
        cur = load()
        ok = merged(cur) == cur
        print("같아요" if ok else "달라요: --apply로 다시 넣으세요")
        return 0 if ok else 1
    else:
        print(json.dumps({"hooks": block(), "permissions": {"ask": ASK}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
