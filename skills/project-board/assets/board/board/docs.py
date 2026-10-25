"""STATUS.md, BRIEF.md and USER_DIRECTIONS.md, read into what the board
shows. Anything that does not match a known shape is passed on as its raw
markdown so the screen can show it as written instead of guessing."""
import re

from . import md
from .roadmap import ID, header

DAY = re.compile(r"(?<![\d-])(\d{2}-\d{2})(?![\d-])")


def lead(text):
    """A "**lead** rest" bullet as its two parts."""
    m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", text, re.S)
    return {"lead": m.group(1), "text": m.group(2)} if m else {"lead": None, "text": text}


def status(lines, h):
    if lines is None:
        return None
    q = md.quote(lines)
    upd = re.search(r"마지막 갱신:?\s*(\d{4}-\d{2}-\d{2})", " ".join(q))
    out = {"updated": upd.group(1) if upd else None, "memo": q}
    now = md.chapter(lines, h.get("now", "★ 지금"))
    out["now"] = [lead(t) for t in md.items(now[3])] if now else []
    pr = md.chapter(lines, h.get("prompt", "다음 세션 시작 프롬프트"))
    if pr:
        meta = " ".join(md.quote(pr[3]))
        written = re.search(r"작성\s*(\d{4}-\d{2}-\d{2})", meta)
        nxt = re.search(r"다음(?: 세션)?:\s*(?:세션\s*)?([A-Za-z]+\d+)", meta)
        blocks = md.fences(pr[3])
        out["prompt"] = {"text": blocks[0] if blocks else None, "meta": meta,
                         "written": written.group(1) if written else None,
                         "next": nxt.group(1) if nxt else None, "line": pr[0] + 1}
    else:
        out["prompt"] = None
    run = md.chapter(lines, h.get("running", "진행 중인 세션"))
    out["running"] = md.table(run[3]) if run else []
    for key in ("open", "issues", "verified"):
        ch = md.chapter(lines, h.get(key, key))
        out[key] = md.items(ch[3]) if ch else []
    return out


def split_steps(text):
    """One "~~old~~ (source) → new (date, source)" record as its steps. Arrows
    inside struck text belong to that text, so struck spans are masked first."""
    spans = [(m.start(), m.end()) for m in re.finditer(r"~~.+?~~", text)]
    masked = list(text)
    for a, b in spans:
        for k in range(a, b):
            if masked[k] == "→":
                masked[k] = "\0"
    masked = "".join(masked)
    out, pos = [], 0
    for m in re.finditer(r"\s→\s", masked):
        out.append(text[pos:m.start()])
        pos = m.end()
    out.append(text[pos:])
    steps = []
    for part in out:
        part = part.strip().strip(",").strip()
        struck = part.startswith("~~")
        dates = []
        for p in re.findall(r"\(([^()]*)\)", part):
            dates += DAY.findall(p)
        steps.append({"text": part, "struck": struck, "date": dates[-1] if dates else None})
    return steps


def brief(lines, h):
    if lines is None:
        return None
    out = header(lines)
    out["changelog"] = []
    for line in out["memo"]:
        m = re.match(r"^-\s*판\s*(\d+)\s*→\s*판\s*(\d+)\s*(?:\(([^)]*)\))?:\s*(.*)$", line)
        if m:
            out["changelog"].append({"from": int(m.group(1)), "to": int(m.group(2)),
                                     "date": m.group(3), "text": m.group(4)})
    ch = md.chapter(lines, h.get("changes", "바뀐 결정"))
    out["changes"] = [{"raw": t, "steps": split_steps(t)} for t in md.items(ch[3])] if ch else []
    out["changes_line"] = ch[0] + 1 if ch else None
    dc = md.chapter(lines, h.get("decide", "정할 것"))
    out["decide"] = []
    for n, t in md.numbered(dc[3]) if dc else []:
        m = re.match(r"^\*\*(.+?):?\*\*:?\s*(.*)$", t, re.S)
        title, text = (m.group(1).rstrip(":"), m.group(2)) if m else (t.split(":")[0], t)
        when = re.search(r"\(([^()]*)\)\s*$", title)
        out["decide"].append({"num": n, "title": title[:when.start()].strip() if when else title,
                              "when": when.group(1) if when else None, "text": text.strip()})
    out["decide_line"] = dc[0] + 1 if dc else None
    return out


def deadlines(decide, open_items):
    """A decision's deadline from STATUS "정할 것이 있는 곳" when that line names
    the decision and ends with "<session> 전까지" (as STATUS writes it)."""
    for d in decide:
        if d["when"]:
            continue
        for t in open_items:
            due = re.search(r"([A-Z]\d+)\s*전까지", t)
            if due and d["title"] in t:
                d["when"] = f"{due.group(1)} 전까지"
    return decide


def directions(lines):
    """USER_DIRECTIONS.md: its dated chapters, newest last."""
    if lines is None:
        return []
    out = []
    for i, text, body in md.chapters(lines, 2):
        m = re.match(r"^(\d+)\.\s+(\d{4}-\d{2}-\d{2})(?:~(\d{2}))?\s*(밤)?[:\s]*(.*)$", text)
        if not m:
            continue
        subs = [t for _, lv, t in md.headings(body) if lv == 3]
        out.append({"num": int(m.group(1)), "date": m.group(2), "until": m.group(3),
                    "title": m.group(5).strip(), "subs": subs,
                    "sessions": sorted(set(ID.findall(text))),
                    "line": i + 1})
    return out


def old_directions(lines):
    """The direction table of the old-plans index (board.toml old_index, e.g. old/README.md): period, name, what is left, source."""
    if lines is None:
        return []
    out = []
    for row in md.table(lines):
        cells = list(row.values())
        if len(cells) < 4:
            continue
        name = re.match(r"^\*\*(.+?):?\*\*:?\s*(.*)$", cells[1])
        days = DAY.findall(cells[0])
        out.append({"period": cells[0], "start": days[0] if days else None,
                    "end": days[1] if len(days) > 1 else None, "open": cells[0].rstrip().endswith("~"),
                    "name": name.group(1).rstrip(":") if name else cells[1],
                    "text": name.group(2) if name else "", "left": cells[2], "source": cells[3]})
    return out
