#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plain_lint.py — 쉬운 말 검사 (plain-words 스킬의 검사 프로그램)

도하(앞뒤 맥락 없이 읽는 사람)에게 가는 글에서, 풀어 쓰지 않은 분석 번호·만든 말·코드 이름을 찾는다.
찾을 말은 그 프로젝트 용어집(`docs/GLOSSARY.md`)의 "검사가 세는 글자" 칸에서 읽는다.
용어집이 없는 프로젝트에서는 아무것도 하지 않는다.

세지 않는 곳
  백틱(`) 안, 코드 블록, 괄호 안, 주소(http…), HTML 주석,
  원문 구역(<!-- 원문 --> … <!-- /원문 -->, 페이지에서는 data-raw 를 단 요소와 요약에 "원문"이 든 <details>).
  페이지(HTML)는 화면에 보이는 글과, 스크립트 안의 한글이 든 문자열만 본다.

쓰는 법
  손으로:  python3 plain_lint.py <파일>... [--glossary 경로] [--json]
           찾으면 종료 코드 1, 없으면 0, 용어집을 못 찾으면 2.
           python3 plain_lint.py --text "검사할 글" [--glossary 경로]
  훅으로:  python3 plain_lint.py --hook   (표준 입력으로 Claude Code 훅 JSON을 받는다)
           PostToolUse  Write·Edit·MultiEdit(문서 파일), Artifact(페이지 올리기), 보내는 도구 → 경고만 한다.
                        저장이나 보내기를 막지 않는다.
           PreToolUse   보내는 도구(마무리 상자, 세션 메시지, 새 세션 첫 지시문) → 남은 말이 있으면
                        첫 시도만 멈춘다(deny). 10분 안에 다시 보내면 그대로 통과(경고는 PostToolUse가 붙인다).
           어떤 오류가 나도 종료 코드 0, 출력 없음. 오류는 ~/.cache/plain-words/error.log 에 남긴다.

표준 라이브러리만 쓴다.
"""
import argparse
import bisect
import json
import os
import re
import sys
import time
import traceback
from collections import OrderedDict

DENY_WINDOW_SEC = 600          # 멈춘 뒤 이 시간 안에 다시 보내면 통과
MAX_ITEMS = 20                 # 알림에 적는 낱말 가짓수
MAX_MEANING = 140              # 알림에 적는 뜻 길이
MAX_MESSAGE = 6000             # 알림 전체 길이(훅 출력 한도 10,000자 안)
GLOSSARY_REL = os.path.join("docs", "GLOSSARY.md")
SKILL_PATH = "~/.claude/skills/plain-words/SKILL.md"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "plain-words")

SEND_TOOLS = ("mcp__ccd_turn__wrap_up", "SendMessage", "mcp__ccd_session__start_session")
SEND_FIELDS = ("recap", "ask", "message", "summary", "content", "prompt", "background", "title", "label", "text")
FILE_TOOLS = ("Write", "Edit", "MultiEdit")
PAGE_TOOLS = ("Artifact",)
DOC_EXTS = (".md", ".markdown", ".txt", ".html", ".htm")
HTML_EXTS = (".html", ".htm")
ROOT_FILES = ("STATUS.md", "CLAUDE.md")
SKIP_FILES = ("docs/GLOSSARY.md", "docs/USER_NOTES.md")
SKIP_DIRS = ("docs/archive/",)

AW = "A-Za-z0-9_"
LEAD = "(?<![" + AW + "])"
TRAIL = "(?![" + AW + "])"
HANGUL = re.compile("[가-힣]")


class Rule(object):
    __slots__ = ("label", "meaning", "rx", "source")

    def __init__(self, label, meaning, rx, source):
        self.label = label
        self.meaning = meaning
        self.rx = rx
        self.source = source


CODE_NAME_RULE = Rule(
    "밑줄로 이은 영어 이름",
    "코드 이름이에요. 쉬운 뜻으로 바꾸거나, 꼭 남길 거면 백틱(`) 안에 두세요. 인스타 같은 계정 이름이면 앞에 @를 붙이세요.",
    # @가 붙은 것(@sample_creator 같은 계정 이름)은 세지 않는다.
    re.compile(r"(?<![A-Za-z0-9_@])[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]*[A-Za-z0-9]" + TRAIL),
    "기본 규칙",
)


# ---------------------------------------------------------------- 용어집 읽기

def split_row(line):
    """마크다운 표 한 줄을 칸으로 나눈다. `\\|`는 칸 나눔이 아니라 글자 |로 본다."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, i = [], [], 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur.append("|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    cells.append("".join(cur).strip())
    return cells


def compile_pattern(p):
    """`~`로 시작하면 정규식, 아니면 글자 그대로. 영어·숫자로 시작하거나 끝나면 앞뒤 영어·숫자 붙음을 막는다."""
    if p.startswith("~"):
        return re.compile(LEAD + "(?:" + p[1:] + ")" + TRAIL)
    lead = LEAD if re.match("[" + AW + "]", p[0]) else ""
    trail = TRAIL if re.match("[" + AW + "]", p[-1]) else ""
    return re.compile(lead + re.escape(p) + trail)


def _col(cells, name, default):
    for i, c in enumerate(cells):
        if c == name:
            return i
    for i, c in enumerate(cells):
        if name in c:
            return i
    return default


def load_glossary(path):
    """용어집에서 (세는 규칙들, 빼는 규칙들, 문제 목록)을 읽는다.

    - 머리 칸에 "검사가 세는 글자"가 있는 표: 그 칸의 백틱 글자를 센다.
    - 머리 칸에 "검사가 빼는 글자"가 있는 표: 그 칸의 백틱 글자는 세지 않는다(도하가 아는 이름).
    """
    rules, allows, problems = [], [], []
    mode = None
    cols = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for n, raw in enumerate(f, 1):
            line = raw.rstrip("\n")
            if not line.lstrip().startswith("|"):
                mode, cols = None, None
                continue
            cells = split_row(line)
            if mode is None:
                if any("검사가 세는 글자" in c for c in cells):
                    mode = "count"
                    cols = (_col(cells, "말", 0), _col(cells, "쉬운 뜻", 1), _col(cells, "검사가 세는 글자", len(cells) - 1))
                elif any("검사가 빼는 글자" in c for c in cells):
                    mode = "allow"
                    cols = (_col(cells, "말", 0), 1, _col(cells, "검사가 빼는 글자", len(cells) - 1))
                else:
                    mode = "other"
                continue
            if mode == "other" or re.fullmatch(r"[\s|:\-]+", line):
                continue
            w, m, pc = cols
            if pc >= len(cells):
                continue
            for p in re.findall(r"`([^`]+)`", cells[pc]):
                try:
                    rx = compile_pattern(p)
                except re.error as e:
                    problems.append("용어집 %d줄 `%s`: %s" % (n, p, e))
                    continue
                if mode == "count":
                    label = cells[w] if w < len(cells) else p
                    meaning = cells[m] if m < len(cells) else ""
                    rules.append(Rule(label, meaning, rx, "용어집 %d줄" % n))
                else:
                    allows.append(rx)
    return rules, allows, problems


def find_project_root(start):
    """start에서 위로 올라가며 docs/GLOSSARY.md가 있는 폴더를 찾는다. 없으면 None."""
    if not start:
        return None
    d = os.path.abspath(os.path.expanduser(start))
    if os.path.isfile(d):
        d = os.path.dirname(d)
    while True:
        if os.path.isfile(os.path.join(d, GLOSSARY_REL)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


# ---------------------------------------------------------------- 세지 않는 곳 가리기
# 가린 글자는 공백으로 바꾸되 줄바꿈은 남긴다. 그래서 위치와 줄 번호가 원문과 같다.

def _blank(s):
    return re.sub(r"[^\n]", " ", s)


def blank_re(text, pattern, flags=0):
    return re.sub(pattern, lambda m: _blank(m.group(0)), text, flags=flags)


def blank_spans(text, spans):
    if not spans:
        return text
    out, last = [], 0
    for a, b in sorted(spans):
        if b <= last:
            continue
        a = max(a, last)
        out.append(text[last:a])
        out.append(_blank(text[a:b]))
        last = b
    out.append(text[last:])
    return "".join(out)


RAW_COMMENT = r"<!--\s*(?:원문|raw)\s*-->.*?(?:<!--\s*/(?:원문|raw)\s*-->|\Z)"
URL_RE = r"(?:https?://|www\.)[^\s<>()\[\]\"'`]+|(?<![A-Za-z0-9])[A-Za-z0-9.-]+\.(?:ai|com|org|io|net|dev|app|kr)/[^\s<>()\[\]\"'`]*"
# @가 붙은 계정 이름(@ai.design_rachael 같은 것)은 통째로 세지 않는다. 점이 섞여도 한 이름으로 본다.
HANDLE_RE = r"(?<![A-Za-z0-9_.])@[A-Za-z0-9_](?:[A-Za-z0-9_.]*[A-Za-z0-9_])?"
TAG_RE = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9-]*)\b[^>]*?(/?)>", re.S)


def paren_spans(text, max_len=600):
    """괄호 ( ) 와 （ ） 안. 문단(빈 줄)을 넘지 않고, 너무 길면 괄호로 보지 않는다."""
    spans, stack = [], []
    n = len(text)
    for i, ch in enumerate(text):
        if ch == "(" or ch == "（":
            stack.append(i)
        elif ch == ")" or ch == "）":
            if stack:
                a = stack.pop()
                if i - a <= max_len:
                    spans.append((a, i + 1))
        elif ch == "\n" and i + 1 < n and text[i + 1] == "\n":
            stack = []
    return spans


def _element_end(text, open_match):
    name = open_match.group(2).lower()
    depth = 1
    for m in TAG_RE.finditer(text, open_match.end()):
        if m.group(2).lower() != name:
            continue
        if m.group(1) == "/":
            depth -= 1
        elif m.group(3) != "/":
            depth += 1
        if depth == 0:
            return m.end()
    return len(text)


def raw_element_spans(text):
    """data-raw 를 단 요소, 요약(summary)에 "원문"이 든 <details> 요소 전체."""
    spans = []
    for m in TAG_RE.finditer(text):
        if m.group(1) == "/" or m.group(3) == "/":
            continue
        tag = m.group(0)
        name = m.group(2).lower()
        if re.search(r"\sdata-raw\b", tag):
            spans.append((m.start(), _element_end(text, m)))
        elif name == "details":
            end = _element_end(text, m)
            sm = re.search(r"<summary\b[^>]*>(.*?)</summary>", text[m.end():end], re.S | re.I)
            if sm and "원문" in sm.group(1):
                spans.append((m.start(), end))
    return spans


def mask_fragment(s):
    """HTML 조각(스크립트 문자열 안 글 등)에서 코드 요소와 태그, 백틱을 가린다."""
    s = blank_re(s, r"<(pre|code|kbd|samp)\b[^>]*>.*?</\1\s*>", re.S | re.I)
    s = blank_re(s, r"<[^>]*>", re.S)
    s = blank_re(s, r"``.+?``", re.S)
    s = blank_re(s, r"`[^`\n]*`")
    return s


JS_TOKEN = re.compile(
    r"\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`|/\*.*?\*/|//[^\n]*",
    re.S,
)


def mask_script(code):
    """스크립트는 한글이 든 문자열 안쪽 글만 남기고 모두 가린다."""
    out = list(_blank(code))
    for m in JS_TOKEN.finditer(code):
        tok = m.group(0)
        if tok[0] not in "\"'`" or not HANGUL.search(tok):
            continue
        inner = tok[1:-1]
        if tok[0] == "`":
            inner = blank_re(inner, r"\$\{[^}]*\}")
        inner = mask_fragment(inner)
        a = m.start() + 1
        out[a:a + len(inner)] = list(inner)
    return "".join(out)


def mask_html(text):
    t = blank_re(text, RAW_COMMENT, re.S | re.I)
    t = blank_re(t, r"<!--.*?(?:-->|\Z)", re.S)
    pieces, last = [], 0
    for m in re.finditer(r"(<script\b[^>]*>)(.*?)(</script\s*>|\Z)", t, re.S | re.I):
        pieces.append(t[last:m.start()])
        pieces.append(_blank(m.group(1)) + mask_script(m.group(2)) + _blank(m.group(3)))
        last = m.end()
    pieces.append(t[last:])
    t = "".join(pieces)
    t = blank_spans(t, raw_element_spans(t))
    t = blank_re(t, r"<(style|pre|code|kbd|samp|textarea|noscript|template)\b[^>]*>.*?</\1\s*>", re.S | re.I)
    t = blank_re(t, r"<[^>]*>", re.S)
    t = blank_re(t, r"`[^`\n]*`")
    t = blank_re(t, URL_RE)
    t = blank_re(t, HANDLE_RE)
    t = blank_spans(t, paren_spans(t))
    return t


def mask_markdown(text):
    t = blank_re(text, r"\A---\n.*?\n---\n", re.S)
    t = blank_re(t, RAW_COMMENT, re.S | re.I)
    t = blank_re(t, r"<!--.*?(?:-->|\Z)", re.S)
    t = blank_re(t, r"(?ms)^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$")
    m = re.search(r"(?m)^[ \t]*(`{3,}|~{3,})", t)
    if m:  # 닫히지 않은 코드 블록은 끝까지
        t = t[:m.start()] + _blank(t[m.start():])
    t = blank_spans(t, raw_element_spans(t))
    t = blank_re(t, r"<(pre|code|kbd|samp)\b[^>]*>.*?</\1\s*>", re.S | re.I)
    t = blank_re(t, r"``.+?``", re.S)
    t = blank_re(t, r"`[^`\n]*`")
    t = blank_re(t, r"</?[A-Za-z][^>\n]*>")
    t = blank_re(t, URL_RE)
    t = blank_re(t, HANDLE_RE)
    t = blank_spans(t, paren_spans(t))
    return t


def mask(text, kind):
    return mask_html(text) if kind == "html" else mask_markdown(text)


# ---------------------------------------------------------------- 찾기

def find_hits(masked, rules, allows=()):
    t = masked
    for rx in allows:
        t = blank_re(t, rx)
    starts, spans, hits = [], [], []
    for rule in list(rules) + [CODE_NAME_RULE]:
        for m in rule.rx.finditer(t):
            a, b = m.span()
            if a == b:
                continue
            i = bisect.bisect_left(starts, b)
            if i > 0 and spans[i - 1][1] > a:
                continue
            k = bisect.bisect_left(starts, a)
            if k < len(starts) and starts[k] < b:
                continue
            starts.insert(k, a)
            spans.insert(k, (a, b))
            hits.append((a, b, rule, m.group(0)))
    hits.sort(key=lambda h: h[0])
    return hits


def check_text(text, kind, rules, allows=()):
    masked = mask(text, kind)
    return find_hits(masked, rules, allows), masked


def kind_of(path):
    return "html" if str(path).lower().endswith(HTML_EXTS) else "md"


# ---------------------------------------------------------------- 알림 글

def _line_starts(text):
    starts = [0]
    i = text.find("\n")
    while i != -1:
        starts.append(i + 1)
        i = text.find("\n", i + 1)
    return starts


def _snippet(masked, a, b, width=28):
    """찾은 곳 앞뒤 글. 그 줄 안에서만 자른다(옛 줄이 섞여 보이지 않게)."""
    ls = masked.rfind("\n", 0, a) + 1
    le = masked.find("\n", b)
    le = len(masked) if le == -1 else le
    s0, s1 = max(ls, a - width), min(le, b + width)
    s = re.sub(r"\s+", " ", masked[s0:s1]).strip()
    return ("…" if s0 > ls else "") + s + ("…" if s1 < le else "")


def group_hits(hits, text, masked):
    starts = _line_starts(text)
    groups = OrderedDict()
    for a, b, rule, word in hits:
        key = (word, rule.label)
        g = groups.get(key)
        if g is None:
            g = {"word": word, "rule": rule, "lines": [], "snip": _snippet(masked, a, b)}
            groups[key] = g
        g["lines"].append(bisect.bisect_right(starts, a))
    return list(groups.values())


def _short(s, n=MAX_MEANING):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def describe(groups, with_lines=True):
    out = []
    for g in groups[:MAX_ITEMS]:
        cnt = len(g["lines"])
        times = " ×%d" % cnt if cnt > 1 else ""
        if with_lines:
            ls = sorted(set(g["lines"]))
            where = ", ".join(str(x) for x in ls[:3]) + ("…" if len(ls) > 3 else "")
            where = " (%s줄)" % where
        else:
            where = ""
        out.append('- "%s"%s%s → %s' % (g["word"], times, where, _short(g["rule"].meaning)))
        out.append("  보인 곳: %s" % g["snip"])
    if len(groups) > MAX_ITEMS:
        out.append("- 그 밖에 %d가지 더" % (len(groups) - MAX_ITEMS))
    return out


HOW_TO_FIX = (
    "고치는 법: 쉬운 뜻으로 바꿔 쓰세요. 꼭 남겨야 하면 쉬운 뜻 뒤 괄호 안이나 백틱(`) 안에 두세요. "
    "기계가 읽는 원문은 원문 구역(<!-- 원문 --> … <!-- /원문 -->, 페이지는 data-raw)으로 감싸고, 그 위에 쉬운 말 요약을 두세요."
)


def josa(word, with_final, without_final):
    """받침이 있으면 with_final(은·을), 없으면 without_final(는·를). 끝 괄호는 빼고 마지막 한글로 판단."""
    w = re.sub(r"\([^()]*\)\s*$", "", word).strip()
    for ch in reversed(w):
        if "가" <= ch <= "힣":
            return with_final if (ord(ch) - 0xAC00) % 28 else without_final
    return with_final


def build_message(where, groups, total, mode):
    kinds = len(groups)
    if mode == "pre":
        head = ("[쉬운 말 검사] 보내기 전에 한 번 멈췄어요. %s%s 도하나 다른 세션이 앞뒤 맥락 없이 읽는 글인데, "
                "풀어 쓰지 않은 말이 %d개(%d가지) 남았어요." % (where, josa(where, "은", "는"), total, kinds))
        tail = ["쉬운 뜻으로 고쳐서 다시 보내세요. %d분 안에 다시 보내면 남은 말이 있어도 그대로 나가요(그때는 경고만 붙어요)."
                % (DENY_WINDOW_SEC // 60)]
        lines_ok = False
    elif mode == "sent":
        head = ("[쉬운 말 검사] %s%s 이미 보냈는데, 풀어 쓰지 않은 말이 %d개(%d가지) 남아 있었어요. "
                "받는 쪽이 못 읽을 수 있어요." % (where, josa(where, "을", "를"), total, kinds))
        tail = ["필요하면 고친 글을 다시 보내고, 다음 글부터는 보내기 전에 풀어 쓰세요."]
        lines_ok = False
    else:
        head = ("[쉬운 말 검사] %s에 도하가 바로 못 읽을 말이 %d개(%d가지) 남았어요. "
                "파일은 저장됐어요(막지 않아요)." % (where, total, kinds))
        tail = []
        lines_ok = True
    body = describe(groups, with_lines=lines_ok)
    foot = [HOW_TO_FIX, "자세한 법: plain-words 스킬(%s)의 \"경고를 받았을 때\" · 뜻은 용어집 docs/GLOSSARY.md" % SKILL_PATH]
    msg = "\n".join([head] + body + tail + foot)
    if len(msg) > MAX_MESSAGE:
        msg = msg[:MAX_MESSAGE - 1] + "…"
    return msg


# ---------------------------------------------------------------- 훅

def _log_error():
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(os.path.join(CACHE_DIR, "error.log"), "a", encoding="utf-8") as f:
            f.write("---- %s\n%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), traceback.format_exc()))
    except Exception:
        pass


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None


def in_scope(rel):
    if rel.startswith("../") or rel == "..":
        return False
    if rel in ROOT_FILES:
        return True
    if not rel.startswith("docs/"):
        return False
    if rel in SKIP_FILES or any(rel.startswith(d) for d in SKIP_DIRS):
        return False
    return rel.lower().endswith(DOC_EXTS)


def _rules_for(root):
    rules, allows, _ = load_glossary(os.path.join(root, GLOSSARY_REL))
    return rules, allows


def _post(msg):
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}


def _abs(path, data):
    p = os.path.expanduser(path)
    if not os.path.isabs(p):
        p = os.path.join(data.get("cwd") or os.getcwd(), p)
    return os.path.abspath(p)


def _find_all(hay, needle):
    out, i = [], hay.find(needle)
    while i != -1:
        out.append((i, i + len(needle)))
        i = hay.find(needle, i + 1)
    return out


def post_file(data, tool, ti):
    fp = ti.get("file_path")
    if not isinstance(fp, str) or not fp:
        return None
    fp = _abs(fp, data)
    root = find_project_root(os.path.dirname(fp))
    if not root:
        return None
    rel = os.path.relpath(fp, root).replace(os.sep, "/")
    if not in_scope(rel):
        return None
    rules, allows = _rules_for(root)
    kind = kind_of(fp)
    if tool == "Write":
        text = ti.get("content")
        if not isinstance(text, str):
            text = _read(fp)
        if not text:
            return None
        hits, masked = check_text(text, kind, rules, allows)
    else:
        if tool == "Edit":
            news = [ti.get("new_string")]
        else:
            news = [e.get("new_string") for e in (ti.get("edits") or []) if isinstance(e, dict)]
        news = [s for s in news if isinstance(s, str) and s.strip()]
        if not news:
            return None
        full = _read(fp)
        ranges = []
        if full is not None:
            for s in news:
                ranges.extend(_find_all(full, s))
        if full is not None and ranges:
            masked = mask(full, kind)
            hits = [h for h in find_hits(masked, rules, allows)
                    if any(x <= h[0] and h[1] <= y for x, y in ranges)]
            text = full
        else:
            text = "\n".join(news)
            hits, masked = check_text(text, kind, rules, allows)
    if not hits:
        return None
    groups = group_hits(hits, text, masked)
    return _post(build_message(rel, groups, len(hits), "file"))


def post_page(data, ti):
    action = ti.get("action") or "publish"
    if action != "publish" or ti.get("asset"):
        return None
    fp = ti.get("file_path")
    if not isinstance(fp, str) or not fp.lower().endswith(DOC_EXTS):
        return None
    root = find_project_root(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
    if not root:
        return None
    fp = _abs(fp, data)
    text = _read(fp)
    if not text:
        return None
    rules, allows = _rules_for(root)
    hits, masked = check_text(text, kind_of(fp), rules, allows)
    if not hits:
        return None
    groups = group_hits(hits, text, masked)
    return _post(build_message("올린 페이지(%s)" % os.path.basename(fp), groups, len(hits), "file"))


def send_text(ti):
    parts = []

    def walk(v, key=None):
        if isinstance(v, str):
            if key in SEND_FIELDS and v.strip():
                parts.append(v)
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(x, k)
        elif isinstance(v, list):
            for x in v:
                walk(x, key)

    walk(ti)
    return "\n\n".join(parts)


SEND_NAMES = {
    "mcp__ccd_turn__wrap_up": "마무리 상자 글",
    "SendMessage": "세션 메시지",
    "mcp__ccd_session__start_session": "새 세션 첫 지시문",
}


def _state_path(session, tool):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", "%s-%s" % (session or "nosession", tool))[:180]
    return os.path.join(CACHE_DIR, "deny-" + safe + ".json")


def _clean_old_states(now):
    try:
        for name in os.listdir(CACHE_DIR):
            if name.startswith("deny-"):
                p = os.path.join(CACHE_DIR, name)
                if now - os.path.getmtime(p) > 86400:
                    os.remove(p)
    except Exception:
        pass


def send_check(data, tool, ti, event):
    root = find_project_root(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
    if not root:
        return None
    text = send_text(ti)
    if not text.strip():
        return None
    rules, allows = _rules_for(root)
    hits, masked = check_text(text, "md", rules, allows)
    where = SEND_NAMES.get(tool, "보내는 글")
    if event == "PostToolUse":
        if not hits:
            return None
        return _post(build_message(where, group_hits(hits, text, masked), len(hits), "sent"))
    # PreToolUse: 한 번만 멈춘다
    now = time.time()
    sp = _state_path(data.get("session_id"), tool)
    st = None
    try:
        with open(sp, encoding="utf-8") as f:
            st = json.load(f)
    except Exception:
        st = None
    if st and now - float(st.get("t", 0)) <= DENY_WINDOW_SEC:
        try:
            os.remove(sp)
        except Exception:
            pass
        return None
    if not hits:
        if st:
            try:
                os.remove(sp)
            except Exception:
                pass
        return None
    os.makedirs(CACHE_DIR, exist_ok=True)
    _clean_old_states(now)
    with open(sp, "w", encoding="utf-8") as f:
        json.dump({"t": now, "n": len(hits)}, f)
    reason = build_message(where, group_hits(hits, text, masked), len(hits), "pre")
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def handle_hook(data):
    if not isinstance(data, dict):
        return None
    event = data.get("hook_event_name") or ""
    tool = data.get("tool_name") or ""
    ti = data.get("tool_input")
    if not isinstance(ti, dict):
        return None
    if tool in SEND_TOOLS and event in ("PreToolUse", "PostToolUse"):
        return send_check(data, tool, ti, event)
    if event != "PostToolUse":
        return None
    if tool in FILE_TOOLS:
        return post_file(data, tool, ti)
    if tool in PAGE_TOOLS:
        return post_page(data, ti)
    return None


def hook_main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        out = handle_hook(data)
        if out:
            sys.stdout.write(json.dumps(out, ensure_ascii=False))
    except Exception:
        _log_error()
    return 0


# ---------------------------------------------------------------- 손으로 돌리기

def cli_main(argv):
    ap = argparse.ArgumentParser(description="쉬운 말 검사: 도하가 읽을 글에서 풀어 쓰지 않은 말을 찾는다.")
    ap.add_argument("files", nargs="*", help="검사할 파일(.md, .html 등)")
    ap.add_argument("--hook", action="store_true", help="Claude Code 훅으로 돌린다(표준 입력 JSON)")
    ap.add_argument("--glossary", help="용어집 경로(없으면 파일 위치에서 위로 docs/GLOSSARY.md를 찾음)")
    ap.add_argument("--text", help="파일 대신 이 글을 검사")
    ap.add_argument("--kind", choices=["md", "html"], help="글 종류(기본: 확장자로 판단, --text는 md)")
    ap.add_argument("--json", action="store_true", help="결과를 JSON으로")
    args = ap.parse_args(argv)
    if args.hook:
        return hook_main()
    if not args.files and args.text is None:
        ap.print_help()
        return 2

    def glossary_for(start):
        if args.glossary:
            return args.glossary
        root = find_project_root(start)
        return os.path.join(root, GLOSSARY_REL) if root else None

    jobs = []
    if args.text is not None:
        jobs.append(("(글)", args.text, args.kind or "md", glossary_for(os.getcwd())))
    for p in args.files:
        text = _read(p)
        if text is None:
            print("%s: 읽지 못했어요" % p, file=sys.stderr)
            return 2
        jobs.append((p, text, args.kind or kind_of(p), glossary_for(os.path.dirname(os.path.abspath(p)))))

    total, report = 0, []
    cache = {}
    for name, text, kind, gpath in jobs:
        if not gpath or not os.path.isfile(gpath):
            print("%s: 용어집(docs/GLOSSARY.md)을 찾지 못했어요. --glossary로 알려 주세요." % name, file=sys.stderr)
            return 2
        if gpath not in cache:
            rules, allows, problems = load_glossary(gpath)
            for pr in problems:
                print("용어집 문제: " + pr, file=sys.stderr)
            cache[gpath] = (rules, allows)
        rules, allows = cache[gpath]
        hits, masked = check_text(text, kind, rules, allows)
        total += len(hits)
        groups = group_hits(hits, text, masked)
        if args.json:
            for g in groups:
                report.append({"file": name, "word": g["word"], "label": g["rule"].label,
                               "meaning": g["rule"].meaning, "lines": g["lines"], "seen": g["snip"]})
        else:
            if hits:
                print("%s: 풀어 쓰지 않은 말 %d개(%d가지)" % (name, len(hits), len(groups)))
                for line in describe(groups):
                    print("  " + line)
            else:
                print("%s: 깨끗해요" % name)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(cli_main(sys.argv[1:]))
