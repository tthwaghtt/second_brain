#!/usr/bin/env python3
"""Print one chapter of a markdown document, whole, so a session reads only
what it needs. General version of MAGNUM OPUS scripts/docs/doc_section.py.

  python3 doc_section.py DESIGN.md 4-7        # chapter 4-7, to the next heading of its level
  python3 doc_section.py STATUS.md "지금"      # by heading text
  python3 doc_section.py DESIGN.md --list     # the headings with line numbers

A document is a path, or a bare name found anywhere under the current folder
(names should be unique). A chapter id ("4-7", "3") matches a heading whose
text starts with it; any other key matches a heading containing it. The
chapter runs to the next heading of the same or a higher level.
"""
import os
import re
import sys

HEAD = re.compile(r"^(#{1,6})\s+(.*)$")
SKIP = {".git", "node_modules", "__pycache__", "render", "dist"}


def find(name, root="."):
    if os.path.isfile(name):
        return name
    base = os.path.basename(name)
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP]
        if base in files:
            return os.path.join(d, base)
    return None


def headings(lines):
    out, fence = [], False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            fence = not fence
        m = None if fence else HEAD.match(line)
        if m:
            out.append((i, len(m.group(1)), m.group(2).strip()))
    return out


def matches(text, key):
    if re.fullmatch(r"[0-9]+(-[0-9]+)*", key):
        return re.match(re.escape(key) + r"[.\s]", text + " ") is not None
    return key in text


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = find(argv[0])
    if not path:
        print(f"no document {argv[0]}", file=sys.stderr)
        return 1
    lines = open(path, encoding="utf-8").read().splitlines()
    hs = headings(lines)
    if argv[1] == "--list":
        for i, lvl, text in hs:
            print(f"{i + 1:5d}  {'  ' * (lvl - 1)}{text}")
        return 0
    for n, (i, lvl, text) in enumerate(hs):
        if matches(text, argv[1]):
            end = next((j for j, l2, _ in hs[n + 1:] if l2 <= lvl), len(lines))
            print(f"[{path} lines {i + 1}-{end}]")
            print("\n".join(lines[i:end]).rstrip())
            return 0
    print(f"no chapter '{argv[1]}' in {path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
