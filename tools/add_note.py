#!/usr/bin/env python3
"""Write a second_brain note and its INDEX.md line together, so the two never
drift apart (점검.md P1, P5). Standard library only.

  python3 tools/add_note.py new insights/x.md --section 인사이트 \
      --title "제목" --rule "일반 규칙 한 줄" --scope "적용 범위" \
      --summary "INDEX에 실을 한 줄" [--basis 경험] [--tags "토큰, 세션"] \
      [--source "프로젝트/세션"] [--date 2026-10-17]
  python3 tools/add_note.py append lessons/mistakes.md "덧붙일 글" [--summary "새 INDEX 한 줄"]
  python3 tools/add_note.py index insights/x.md --section 인사이트 --summary "한 줄"
  python3 tools/add_note.py check

new     makes the note with the README header (날짜·출처·근거·태그 + 규칙·적용 범위)
        and adds its INDEX line under the INDEX heading that contains --section.
append  adds text at the end of a note (use "\\n" for new lines); --summary also
        rewrites the note's INDEX line.
index   adds or rewrites the INDEX line of an existing note.
check   lists INDEX links to missing files, notes missing from INDEX, and notes
        without the 날짜 or 규칙 header line. Exit code 1 if anything is found.

Paths are relative to the second_brain folder (the parent of tools/).
"""
import argparse
import datetime
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "INDEX.md")
NOTE_DIRS = ("insights", "lessons", "playbooks")
ROOT_SKIP = {"INDEX.md", "README.md"}
LINK = re.compile(r"\]\(([^)]+)\)")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def full(rel):
    return os.path.join(ROOT, rel)


def index_line(rel, summary):
    return f"- [{rel}]({rel}) — {summary}"


def find_line(lines, rel):
    pat = re.compile(r"^- (\*\*)?\[" + re.escape(rel) + r"\]\(" + re.escape(rel) + r"\)")
    return next((i for i, l in enumerate(lines) if pat.match(l)), None)


def set_index(rel, summary, section=None):
    lines = read(INDEX).split("\n")
    i = find_line(lines, rel)
    new = index_line(rel, summary)
    if i is not None:
        print(f"INDEX 줄 바꿈:\n  전: {lines[i]}\n  후: {new}")
        lines[i] = new
    else:
        if not section:
            sys.exit(f"INDEX에 {rel} 줄이 없습니다. --section을 주세요.")
        heads = [k for k, l in enumerate(lines) if l.startswith("## ") and section in l]
        if len(heads) != 1:
            names = [l for l in lines if l.startswith("## ")]
            sys.exit(f"'{section}'을 담은 INDEX 장이 {len(heads)}개입니다. 장 목록: {names}")
        h = heads[0]
        last = h
        for k in range(h + 1, len(lines)):
            if lines[k].startswith("#"):
                break
            if lines[k].startswith("- "):
                last = k
        lines.insert(last + 1, new)
        print(f"INDEX 줄 더함 ({lines[h]}):\n  {new}")
    write(INDEX, "\n".join(lines))


def cmd_new(a):
    path = full(a.path)
    if os.path.exists(path):
        sys.exit(f"{a.path}가 이미 있습니다. append를 쓰세요(같은 주제는 새로 만들지 않고 고칩니다).")
    if find_line(read(INDEX).split("\n"), a.path) is not None:
        sys.exit(f"INDEX에 이미 {a.path} 줄이 있습니다.")
    date = a.date or datetime.date.today().isoformat()
    head = (
        f"# {a.title}\n\n"
        f"> 날짜: {date} · 출처: {a.source} · 근거: {a.basis} · 태그: {a.tags}\n"
        f"> **규칙:** {a.rule} · **적용 범위:** {a.scope}\n\n"
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write(path, head)
    print(f"노트 만듦: {a.path}")
    set_index(a.path, a.summary, a.section)


def cmd_append(a):
    path = full(a.path)
    if not os.path.isfile(path):
        sys.exit(f"{a.path}가 없습니다. new를 쓰세요.")
    if find_line(read(INDEX).split("\n"), a.path) is None and not a.summary:
        sys.exit(f"INDEX에 {a.path} 줄이 없습니다. index로 먼저 더하세요.")
    text = read(path).rstrip("\n") + "\n" + a.text.replace("\\n", "\n").rstrip("\n") + "\n"
    write(path, text)
    print(f"덧붙임: {a.path}")
    if a.summary:
        set_index(a.path, a.summary, a.section)


def cmd_index(a):
    if not os.path.exists(full(a.path)):
        sys.exit(f"{a.path}가 없습니다.")
    set_index(a.path, a.summary, a.section)


def notes():
    out = []
    for d in NOTE_DIRS:
        base = full(d)
        if os.path.isdir(base):
            out += [f"{d}/{f}" for f in sorted(os.listdir(base)) if f.endswith(".md")]
    out += [f for f in sorted(os.listdir(ROOT)) if f.endswith(".md") and f not in ROOT_SKIP]
    return out


def cmd_check(a):
    text = read(INDEX)
    linked = {l.split("#")[0] for l in LINK.findall(text)}
    problems = []
    for rel in sorted(linked):
        if not os.path.exists(full(rel)):
            problems.append(f"INDEX가 없는 파일을 가리킴: {rel}")
    for rel in notes():
        if rel not in linked:
            problems.append(f"INDEX에 없는 노트: {rel}")
        if rel.split("/")[0] in NOTE_DIRS:
            head = read(full(rel)).split("\n")[:12]
            if not any(l.startswith("> 날짜:") for l in head):
                problems.append(f"머리에 날짜 줄이 없음: {rel}")
            if not any(l.startswith("> **규칙:**") for l in head):
                problems.append(f"머리에 규칙 줄이 없음: {rel}")
    for p in problems:
        print(p)
    print(f"검사: 노트 {len(notes())}개, INDEX 링크 {len(linked)}개, 문제 {len(problems)}개")
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("path")
    n.add_argument("--section", required=True)
    n.add_argument("--title", required=True)
    n.add_argument("--rule", required=True)
    n.add_argument("--scope", required=True)
    n.add_argument("--summary", required=True)
    n.add_argument("--basis", default="경험")
    n.add_argument("--tags", default="")
    n.add_argument("--source", default="")
    n.add_argument("--date")
    p = sub.add_parser("append")
    p.add_argument("path")
    p.add_argument("text")
    p.add_argument("--summary")
    p.add_argument("--section")
    i = sub.add_parser("index")
    i.add_argument("path")
    i.add_argument("--summary", required=True)
    i.add_argument("--section")
    sub.add_parser("check")
    a = ap.parse_args()
    return {"new": cmd_new, "append": cmd_append, "index": cmd_index, "check": cmd_check}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
