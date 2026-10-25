"""Every project file with what the user needs to direct the work: its role,
how it changes, who edits it, what points at it and what it points at, the
commits (and so the sessions) that touched it, whether something it points
at changed after it, and whether the user has marked it understood.

Roles come from one place: a "파일의 역할" table in MAP.md (a project
document, written by the planning session). A file the table does not cover
gets a role guessed from the project's conventions and is marked inferred,
so the screen never presents a guess as the project's own word."""
import fnmatch
import json
import os
import re
import time
from datetime import datetime

from . import gitinfo, md, roadmap, tree

WEIGHT = {"지휘": 0, "작업": 1, "참고": 2, "기계": 3}
WEIGHT_NAME = ["지휘 문서", "작업물", "참고 자료", "기계가 만든 것"]


def in_search(p, c):
    """Whether p lies where documents are found by bare name (board.toml [docs] search; "." is the whole project)."""
    return any(d.strip("/") in ("", ".") or p.startswith(d.rstrip("/") + "/") for d in c.search)


def is_ref(p, c):
    """A reference document: one board.toml names, or a .md in a search folder. When the search
    folder is the whole project, only top-level .md files count; notes deeper down are work, not plans."""
    if p in c.docs.values():
        return True
    if not p.endswith(".md") or not in_search(p, c):
        return False
    whole = any(d.strip("/") in ("", ".") for d in c.search)
    return not whole or "/" not in p or any(p.startswith(d.rstrip("/") + "/") for d in c.search if d.strip("/") not in ("", "."))


# guessed roles (inferred), from the conventions of a second-brain project and the places board.toml [roles]
# gives; MAP's table always wins
GUESS = [
    ("rules", lambda p, c: p in (c.docs.get("rules", "CLAUDE.md"), "README.md", ".gitignore"),
     "규칙·입구", "고쳐 쓰고 판과 날짜를 적음", "기획 책임 세션", 0),
    ("status", lambda p, c: p == c.docs.get("status"), "흐름", "매번 통째로 덮어씀", "기획 책임 세션", 0),
    ("record", lambda p, c: c.under("record", p) or p == c.docs.get("directions"), "기록", "끝에 덧붙이기만", "기획 책임 세션 (덧붙이기만)", 0),
    ("report", lambda p, c: c.under("report", p), "보고서", "그날로 얼림, 정정은 머리에", "고치지 않음", 2),
    ("old", lambda p, c: c.under("old", p), "옛 방향", "따르지 않음, 고치지 않음", "아무도", 2),
    ("user", lambda p, c: c.under("user", p), "사용자 자료", "고치지 않음", "아무도", 2),
    ("tool", lambda p, c: c.under("tool", p), "도구 설정", "설치한 것", "사용자", 3),
    ("board", lambda p, c: bool(c.board_dir) and p.startswith(c.board_dir + "/"), "현황판", "project-board 스킬로 세우고 바꿈", "현황판을 맡은 세션", 3),
    ("work", lambda p, c: c.under("work", p), "작업물", "세션이 고침", "ROADMAP의 쓸 파일에 적힌 세션", 1),
    ("ref", is_ref, "기준", "고쳐 쓰고 판과 날짜를 적음", "기획 책임 세션", 0),
    ("code", lambda p, c: p.endswith((".py", ".js", ".mjs", ".sh", ".html", ".css")), "코드", "세션이 고침", "ROADMAP의 쓸 파일에 적힌 세션", 1),
    ("data", lambda p, c: c.under("data", p) or p.endswith((".json", ".jsonl", ".csv", ".txt")), "데이터", "도구가 씀", "도구", 1),
]
FROZEN = ("얼림", "덧붙이기", "따르지 않음", "고치지 않음")      # roles where "older than what it cites" is normal
_cache = {}


def map_roles(cfg):
    """[(pattern, role, how, who, weight)] from MAP.md's role table, longest pattern first."""
    lines = md.read(cfg.doc("map")) if cfg.doc("map") else None
    ch = md.chapter(lines, cfg.head("map_roles", "파일의 역할")) if lines else None
    out = []
    for row in md.table(ch[3]) if ch else []:
        cells = list(row.values())
        if len(cells) < 4:
            continue
        for pat in re.findall(r"`([^`]+)`", cells[0]) or [cells[0].strip()]:
            w = WEIGHT.get((cells[4] if len(cells) > 4 else "").strip(), 1)
            out.append((pat.strip(), md.strip(cells[1]), md.strip(cells[2]), md.strip(cells[3]), w))
    return sorted(out, key=lambda r: -len(r[0].rstrip("/*")))


def role_of(cfg, rel, ignored, table):
    for pat, name, how, who, w in table:
        if pat.endswith("/") and (rel + "/").startswith(pat) or fnmatch.fnmatch(rel, pat) or rel == pat:
            return {"role": name, "how": how, "who": who, "tier": w, "inferred": False}
    for kind, test, name, how, who, w in GUESS:      # places first, then "not in git", then file types
        if kind in ("code", "data") and ignored:
            break
        if test(rel, cfg):
            return {"role": name, "how": how, "who": who, "tier": w, "inferred": True}
    if ignored:
        return {"role": "만든 결과물", "how": "도구가 다시 만듦 (git에 담지 않음)", "who": "도구", "tier": 3, "inferred": True}
    return {"role": "분류 안 됨", "how": "", "who": "", "tier": 1, "inferred": True}


def commits_by_file(cfg):
    """{path: [{short, when, session, subject}]} newest first, cached by HEAD."""
    head = gitinfo.head(cfg)
    key = ("commits", head)
    if key in _cache:
        return _cache[key]
    out, cur = {}, None
    raw = gitinfo.run(cfg, "log", "--format=@%h\x1f%aI\x1f%s", "--name-only", "--", ".") or ""
    for line in raw.splitlines():
        if line.startswith("@"):
            h, when, subj = line[1:].split("\x1f", 2)
            sid = roadmap.ID.search(subj)       # the first session number ("PORTFOLIO B1 …"), also of sessions the roadmap no longer lists
            cur = {"short": h, "when": when, "session": sid.group(1) if sid else None, "subject": subj}
        elif line.strip() and cur:
            out.setdefault(gitinfo.rel(cfg, line.strip()), []).append(cur)
    _cache[key] = out
    return out


def reference_edges(cfg, paths, texts, version):
    """[(source, target)]: source's text names target as a path standing alone
    (or by its bare name when no other file has that name)."""
    key = ("edges", version)
    if key in _cache:
        return _cache[key]
    names = {}
    for p in paths:
        names.setdefault(os.path.basename(p), []).append(p)
    keys = {}
    for p in paths:
        keys[p] = p
        b = os.path.basename(p)
        if len(names[b]) == 1 and len(b) >= 6 and "." in b:
            keys.setdefault(b, p)
    alt = "|".join(re.escape(k) for k in sorted(keys, key=len, reverse=True))
    rx = re.compile(rf"(?<![\w./-])(?:\.\./)*({alt})(?![\w/-])") if alt else None
    edges = set()
    for src in texts:
        try:
            with open(cfg.abs(src), encoding="utf-8", errors="ignore") as f:
                body = f.read()
        except OSError:
            continue
        for m in rx.finditer(body) if rx else []:
            dst = keys[m.group(1)]
            if dst != src:
                edges.add((src, dst))
    out = sorted(edges)
    for k in [k for k in _cache if k[0] == "edges"]:
        del _cache[k]
    _cache[key] = out
    return out


def understood_path(cfg):
    return os.path.join(cfg.abs(cfg.state), "understood.json")


def understood_load(cfg):
    try:
        with open(understood_path(cfg), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def understood_set(cfg, rel, on, mtime_ns):
    data = understood_load(cfg)
    if on:
        data[rel] = {"mtime_ns": mtime_ns, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    else:
        data.pop(rel, None)
    p = understood_path(cfg)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return data.get(rel)


def session_files(cfg, road):
    """[{session, kind, name, path}] from the roadmap's 쓸 파일 / 읽을 것 fields;
    path is None when the name is outside the project or does not exist yet."""
    out = []
    if not road:
        return out
    for s in road["sessions"]:
        for f in s["fields"]:
            if f["key"] not in ("쓸 파일", "읽을 것"):
                continue
            text = f["text"] + " " + " ".join(f["items"])
            for m in re.finditer(r"`([^`]+)`((?:\s*(?:\d+(?:-\d+)*)(?:\s*[·,]\s*\d+(?:-\d+)*)*\s*장)?)", text):
                name = m.group(1).strip()
                chs = re.findall(r"\d+(?:-\d+)*", m.group(2) or "")
                out.append({"session": s["id"], "kind": "write" if f["key"] == "쓸 파일" else "read",
                            "name": name, "chapters": chs, "path": resolve(cfg, name)})
    return out


def resolve(cfg, name):
    """A project path for a name as the documents write it: a path, a folder,
    or a bare document name looked up where documents are found by name."""
    n = name.strip().rstrip("/")
    if not n or n.startswith(("../", "/", "~")) or "<" in n:
        return None
    if os.path.lexists(cfg.abs(n)):
        return n + ("/" if os.path.isdir(cfg.abs(n)) else "")
    if "/" not in n and n.endswith(".md"):
        for d in cfg.search:
            for dirpath, dirs, files in os.walk(cfg.abs(d)):
                dirs[:] = sorted(x for x in dirs if x not in cfg.hidden)
                if n in files:
                    return os.path.relpath(os.path.join(dirpath, n), cfg.root)
    return None


DOC_SECTION = r'doc_section\.py\s+(\S+\.md)\s+(?:"([^"]+)"|(<[^>]+>)|(\S+?))`(?:\(([^)]*)\))?'
NAMED = r'`([^`\s]+\.md)`(?:\([^)]*\))?(?:의)?\s*(?:"([^"]+)"|(\d+(?:-\d+)*)\s*장)?'


def reading_path(cfg, road):
    """The start-of-session reading order, taken from the rules document's own
    commands (CLAUDE.md 1장: doc_section calls joined by →), then each
    session's 읽을 것."""
    rules = cfg.docs.get("rules", "CLAUDE.md")
    lines = md.read(cfg.abs(rules)) or []
    ch = md.chapter(lines, cfg.head("start", "세션 시작"))
    common = [{"doc": rules, "ch": None, "why": "규칙 파일 (세션을 열면 저절로 읽힘)", "path": rules if os.path.exists(cfg.abs(rules)) else None}]
    if ch:
        text = "\n".join(ch[3])
        for m in re.finditer(DOC_SECTION, text):
            key = m.group(2) or m.group(3) or m.group(4)
            common.append({"doc": m.group(1), "ch": key, "why": m.group(5) or "",
                           "session_slot": "<" in key, "path": resolve(cfg, m.group(1))})
        if len(common) == 1:
            # a rules file that names the documents without doc_section commands
            # ("`HANDOFF.md`(또는 `STATUS.md`)의 "지금" → 로드맵의 그 세션 항목"): each named document once, in order
            seen = {rules}
            for m in re.finditer(NAMED, text):
                if m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                path = resolve(cfg, m.group(1))
                common.append({"doc": m.group(1), "ch": m.group(2) or m.group(3), "why": "",
                               "session_slot": bool(path) and path == cfg.docs.get("roadmap"), "path": path})
    per = {}
    for x in session_files(cfg, road):
        if x["kind"] == "read":
            per.setdefault(x["session"], []).append({"doc": x["name"], "ch": "·".join(x["chapters"]) or None, "path": x["path"]})
    return {"common": common, "per": per}


def build(cfg, version):
    key = ("index", version)
    if key in _cache:
        return _cache[key]
    t = tree.build(cfg)
    files = []

    def walk(n):
        for k in n.get("children", []):
            (files.append(k) if k["kind"] == "file" else walk(k))
    walk(t["root"])
    table = map_roles(cfg)
    commits = commits_by_file(cfg)
    from . import refs as refs_mod
    texts = [p for p in refs_mod.files(cfg)]
    paths = [f["path"] for f in files]
    edges = reference_edges(cfg, paths, texts, version)
    out_e, in_e = {}, {}
    for a, b in edges:
        out_e.setdefault(a, []).append(b)
        in_e.setdefault(b, []).append(a)
    road = roadmap.parse(md.read(cfg.doc("roadmap")), plan_key=cfg.head("plan", "큰 그림")) if cfg.doc("roadmap") else None
    sf = session_files(cfg, road)
    writers, readers = {}, {}
    for x in sf:
        if not x["path"]:
            continue
        target = (writers if x["kind"] == "write" else readers)
        if x["path"].endswith("/"):
            for p in paths:
                if p.startswith(x["path"]):
                    target.setdefault(p, set()).add(x["session"])
        else:
            target.setdefault(x["path"], set()).add(x["session"])
    und = understood_load(cfg)
    rows = {}
    for f in files:
        r = role_of(cfg, f["path"], f["ignored"], table)
        cs = commits.get(f["path"], [])
        dirty = f["git"] in ("M", "?", "A", "R")
        last = f["mtime"] if (dirty or not cs) else datetime.fromisoformat(cs[0]["when"]).timestamp()
        u = und.get(f["path"])
        rows[f["path"]] = {
            "path": f["path"], "name": f["name"], **r, "desc": f["desc"], "git": f["git"], "staged": f["staged"],
            "ignored": f["ignored"], "locked": f["locked"], "size": f["size"], "mtime": f["mtime"], "mtime_ns": f["mtime_ns"],
            "last": last, "commits": len(cs), "sessions": sorted({c["session"] for c in cs if c["session"]}),
            "writers": sorted(writers.get(f["path"], [])), "readers": sorted(readers.get(f["path"], [])),
            "in": len(in_e.get(f["path"], [])), "out": len(out_e.get(f["path"], [])),
            "understood": None if not u else ("yes" if u["mtime_ns"] == f["mtime_ns"] else "changed"),
        }
    for p, row in rows.items():
        stale = []
        if row["tier"] == 0 and not any(w in row["how"] for w in FROZEN):
            stale = [b for b in out_e.get(p, []) if b in rows and rows[b]["tier"] <= 1 and rows[b]["last"] > row["last"] + 60]
        row["stale"] = stale
    weights = {}
    for row in rows.values():
        if row["tier"] < 3:
            w = weights.setdefault(row["tier"], {"total": 0, "yes": 0, "changed": 0})
            w["total"] += 1
            w["yes"] += row["understood"] == "yes"
            w["changed"] += row["understood"] == "changed"
    mine = (cfg.board_dir or "tools/board") + "/"
    out = {
        "files": list(rows.values()), "map_roles": bool(table), "edges": len(edges),
        "undescribed": [p for p, r in rows.items() if r["tier"] <= 1 and not r["desc"] and not r["ignored"] and not p.startswith(mine)],
        "review": [p for p, r in rows.items() if r["git"] == "?" and not r["ignored"] and not r["desc"] and not p.startswith(mine)],
        "progress": {WEIGHT_NAME[k]: v for k, v in sorted(weights.items())},
        "weights": WEIGHT_NAME,
        "_in": in_e, "_out": out_e, "_commits": commits,
    }
    for k in [k for k in _cache if k[0] == "index"]:
        del _cache[k]
    _cache[key] = out
    return out


def profile(cfg, version, rel):
    ix = build(cfg, version)
    row = next((r for r in ix["files"] if r["path"] == rel), None)
    if not row:
        return None
    by = {r["path"]: r for r in ix["files"]}
    pick = lambda ps: [{"path": p, "role": by[p]["role"], "tier": by[p]["tier"], "desc": by[p]["desc"]} for p in sorted(ps) if p in by]
    return {**row, "in_files": pick(ix["_in"].get(rel, [])), "out_files": pick(ix["_out"].get(rel, [])),
            "history": ix["_commits"].get(rel, [])[:12]}
