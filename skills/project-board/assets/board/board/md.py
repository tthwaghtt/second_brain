"""Markdown pieces the board reads: headings, chapters, bullet items, tables,
fenced blocks. headings() and the chapter rule are copied from
tools/doc_section.py (2026-10-25) so the board also runs in projects that do
not have that tool."""
import os
import re

HEAD = re.compile(r"^(#{1,6})\s+(.*)$")
_cache = {}


def read(path):
    """A file's lines, re-read only when its size or mtime changes."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (st.st_mtime_ns, st.st_size)
    hit = _cache.get(path)
    if hit and hit[0] == key:
        return hit[1]
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().split("\n")
    _cache[path] = (key, lines)
    return lines


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


def chapter(lines, key):
    """(heading index, heading text, level, body lines) of the first chapter
    matching key, running to the next heading of the same or a higher level."""
    hs = headings(lines)
    for n, (i, level, text) in enumerate(hs):
        if matches(text, key):
            end = len(lines)
            for j, lv, _ in hs[n + 1:]:
                if lv <= level:
                    end = j
                    break
            return i, text, level, lines[i + 1:end]
    return None


def chapters(lines, level):
    """Every chapter at one heading level: (line index, text, body lines)."""
    hs = headings(lines)
    out = []
    for n, (i, lv, text) in enumerate(hs):
        if lv != level:
            continue
        end = len(lines)
        for j, lv2, _ in hs[n + 1:]:
            if lv2 <= level:
                end = j
                break
        out.append((i, text, lines[i + 1:end]))
    return out


def items(body):
    """Top-level "- " items, each with its indented continuation lines."""
    out, cur, fence = [], None, False
    for line in body:
        if line.startswith("```"):
            fence = not fence
        if fence:
            continue
        if line.startswith("- "):
            cur = [line[2:]]
            out.append(cur)
        elif cur is not None and line.startswith(("  ", "\t")) and line.strip():
            cur.append(line.strip())
        elif not line.strip():
            continue
        else:
            cur = None
    return ["\n".join(x) for x in out]


def numbered(body):
    """Top-level "1. " items with their continuation lines: (number, text)."""
    out, cur = [], None
    for line in body:
        m = re.match(r"^(\d+)\.\s+(.*)$", line)
        if m:
            cur = [int(m.group(1)), [m.group(2)]]
            out.append(cur)
        elif cur is not None and line.startswith(("  ", "\t")) and line.strip():
            cur[1].append(line.strip())
        elif line.strip() and not line.startswith(" "):
            cur = None
    return [(n, "\n".join(t)) for n, t in out]


def table(body):
    """The first markdown table in body as a list of {header: cell}."""
    rows = [l for l in body if l.strip().startswith("|")]
    if len(rows) < 2:
        return []
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, data = cells[0], [c for c in cells[1:] if not all(re.fullmatch(r":?-+:?", x or "-") for x in c)]
    return [dict(zip(head, c)) for c in data]


def fences(body):
    """Fenced blocks as their text."""
    out, cur = [], None
    for line in body:
        if line.startswith("```"):
            if cur is None:
                cur = []
            else:
                out.append("\n".join(cur))
                cur = None
        elif cur is not None:
            cur.append(line)
    return out


def quote(lines):
    """The text of the first blockquote (header memo) of a document."""
    out = []
    for line in lines:
        if line.startswith(">"):
            out.append(line.lstrip("> ").rstrip())
        elif out:
            break
    return out


def strip(text):
    """Plain text: markdown emphasis and code marks removed."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()
