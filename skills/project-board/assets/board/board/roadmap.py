"""ROADMAP.md: stages, sessions, their fields and the prerequisites between
them (the "전제" field), which the overview draws as a line diagram.

A session is done only when its heading says "— 완료": the completion
checkboxes are never ticked, even on finished sessions, so they are listed
as checks, never counted as progress."""
import re

from . import md

STAGE = re.compile(r"^단계\s+(\d+)\.\s+(.*)$")
SESSION = re.compile(r"^(?P<id>[A-Z]\d+)\.\s+(?P<title>.+?)(?:\s+—\s+(?P<state>완료|진행 중|중단)(?P<note>.*))?$")
ONE = re.compile(r"^- ([A-Z]\d+)\.\s+(.+)$")
FIELD = re.compile(r"^- ([^:`*]{1,12}):\s*(.*)$")
CHECK = re.compile(r"\[([ xX])\]\s+(.*?)(?=\s+(?:-\s)?\[[ xX]\]|$)")
ID = re.compile(r"(?<![A-Za-z0-9])([A-Z]\d+)(?![0-9])")
DATE = re.compile(r"(?<![\d-])(\d{2}-\d{2})(?![\d-])")
STATES = {"완료": "done", "진행 중": "running", "중단": "dropped"}


def short(title):
    """The station name: the title up to its first comma, colon or bracket."""
    return re.split(r"[,:(（]|\s—\s|\s→\s", title, maxsplit=1)[0].strip() or title


def header(lines):
    q = md.quote(lines)
    first = q[0] if q else ""
    ed = re.search(r"판\s*(\d+)", first)
    date = re.search(r"(\d{4}-\d{2}-\d{2})", first)
    state = re.search(r"상태:\s*\*\*(.+?)\*\*", first)
    return {"edition": int(ed.group(1)) if ed else None,
            "date": date.group(1) if date else None,
            "state": state.group(1) if state else None,
            "memo": q}


def fields(body):
    """The "- 키: 값" fields of a session, each with its sub-items."""
    out, cur, fence = [], None, False
    for n, line in enumerate(body):
        if line.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = FIELD.match(line)
        if m:
            cur = {"key": m.group(1).strip(), "text": m.group(2).strip(), "items": []}
            out.append(cur)
        elif cur is not None and re.match(r"^\s{2,}(\d+\.|-)\s+", line):
            cur["items"].append(re.sub(r"^\s+(\d+\.|-)\s+", "", line).strip())
        elif cur is not None and line.startswith("  ") and line.strip():
            if cur["items"]:
                cur["items"][-1] += " " + line.strip()
            else:
                cur["text"] += " " + line.strip()
        elif line.strip() and not line.startswith(" "):
            cur = None
    for f in out:
        if f["key"] == "완성 기준":
            f["checks"] = []
            for m in CHECK.finditer(f["text"] + " " + " ".join(f["items"])):
                text = m.group(2).strip()
                how = re.search(r"\(확인:\s*(.*?)\)\s*$", text)
                f["checks"].append({"done": m.group(1) != " ",
                                    "text": text[:how.start()].strip() if how else text,
                                    "how": how.group(1) if how else None})
    return out


def parse(lines, next_id=None, plan_key="큰 그림"):
    """The roadmap as stages, sessions and edges. next_id is the session
    STATUS.md names as next; it is marked "next" unless already done."""
    if lines is None:
        return None
    plan = md.chapter(lines, plan_key)
    plan_rows = {}
    for row in md.table(plan[3]) if plan else []:
        cells = list(row.values())
        m = re.match(r"^(\d+)\.", cells[0]) if cells else None
        if m and len(cells) >= 4:
            plan_rows[int(m.group(1))] = {"period": cells[1], "output": cells[2],
                                          "checkpoints": [c.strip() for c in re.split(r",\s*", cells[3]) if c.strip()]}
    stages, sessions = [], []
    for i, text, body in md.chapters(lines, 2):
        m = STAGE.match(text)
        if not m:
            continue
        num, rest = int(m.group(1)), m.group(2)
        note = rest.split(" — ", 1)[1].strip() if " — " in rest else None
        name = re.split(r"\s+\(|\s+—\s", rest, maxsplit=1)[0].strip()
        period = re.search(r"\(([^)]*)\)", rest.split(" — ")[0])
        stage = {"num": num, "name": name, "period": period.group(1) if period else None,
                 "note": note, "line": i + 1, "sessions": [], **plan_rows.get(num, {})}
        stages.append(stage)
        hs = md.headings(body)
        for n, (j, level, htext) in enumerate(hs):
            sm = SESSION.match(htext)
            if not sm:
                continue
            end = len(body)
            for k, lv, _ in hs[n + 1:]:
                if lv <= level:
                    end = k
                    break
            title = sm.group("title").strip()
            role = re.search(r"\(([^()]*)\)\s*$", title)
            if role:
                title = title[:role.start()].strip()
            note = (sm.group("note") or "").strip()
            date = DATE.search(note)
            sessions.append({
                "id": sm.group("id"), "title": title, "short": short(title),
                "role": role.group(1) if role else None, "stage": num,
                "state": STATES.get(sm.group("state"), "planned"),
                "date": date.group(1) if date else None,
                "note": note or None, "detail": True,
                "fields": fields(body[j + 1:end]), "line": i + 2 + j})
        top = body[:hs[0][0]] if hs else body
        for j, line in enumerate(top):
            om = ONE.match(line)
            if om:
                sessions.append({"id": om.group(1), "title": om.group(2).strip(),
                                 "short": short(om.group(2)), "role": None, "stage": num,
                                 "state": "outline", "date": None, "note": None,
                                 "detail": False, "fields": [], "line": i + 2 + j})
    known = {s["id"] for s in sessions}
    for s in sessions:
        pre = next((f for f in s["fields"] if f["key"] == "전제"), None)
        s["prereqs"] = []
        if pre:
            for pid in ID.findall(pre["text"] + " " + " ".join(pre["items"])):
                if pid in known and pid != s["id"] and pid not in s["prereqs"]:
                    s["prereqs"].append(pid)
        if s["id"] == next_id and s["state"] in ("planned", "outline"):
            s["state"] = "next"
    for st in stages:
        st["sessions"] = [s["id"] for s in sessions if s["stage"] == st["num"]]
    return {"header": header(lines), "stages": stages, "sessions": sessions,
            "edges": edges(stages, sessions), "next": next_id}


def edges(stages, sessions):
    """Track pieces between sessions. "prereq" pieces come from the 전제 field;
    "order" pieces only join a session that names no prerequisite to the end
    of the stage before it (or to the one-line item before it), so the
    diagram never invents a parallel branch the documents do not state."""
    by = {s["id"]: s for s in sessions}
    out = [[p, s["id"], "prereq"] for s in sessions for p in s["prereqs"]]
    prev_ends = []
    for st in stages:
        ids = st["sessions"]
        for n, sid in enumerate(ids):
            s = by[sid]
            if s["prereqs"]:
                continue
            if s["state"] == "outline" and n and by[ids[n - 1]]["state"] == "outline":
                out.append([ids[n - 1], sid, "order"])
            else:
                for p in prev_ends:
                    out.append([p, sid, "order"])
        inside = {e[0] for e in out if e[1] in ids}
        ends = [sid for sid in ids if sid not in inside]
        prev_ends = ends or prev_ends
    return out
