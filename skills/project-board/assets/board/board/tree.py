"""The project's file tree with each path's git state, its description from
MAP.md's folder map, and whether it is locked."""
import os
import re

from . import gitinfo, md

MAP_LINE = re.compile(r"^((?:│   |    )*)(?:├── |└── )(.+?)(?:\s{2,}(.*))?$")


def descriptions(cfg):
    """{path: description} from the code-block tree in MAP.md's folder map.
    A line may name several paths ("TREE.md, TREE/"); they share its text.
    A child never inherits its parent's description."""
    path = cfg.doc("map")
    lines = md.read(path) if path else None
    if not lines:
        return {}
    ch = md.chapter(lines, cfg.head("map_tree", "폴더 지도"))
    blocks = md.fences(ch[3]) if ch else []
    out, stack = {}, []
    for line in (blocks[0].split("\n") if blocks else []):
        m = MAP_LINE.match(line)
        if not m:
            continue
        depth = len(m.group(1)) // 4
        names = [n.strip() for n in m.group(2).split(", ") if n.strip()]
        desc = (m.group(3) or "").strip()
        stack = stack[:depth]
        base = "".join(stack)
        for n in names:
            out[(base + n).rstrip("/")] = desc
        stack.append(names[0] if names[0].endswith("/") else names[0] + "/")
    return out


def build(cfg):
    st = gitinfo.status(cfg) or {}
    tracked = gitinfo.tracked(cfg)
    desc = descriptions(cfg)
    ignored = [p.rstrip("/") for p, v in st.items() if v["code"] == "!"]

    def is_ignored(rel):
        return any(rel == p or rel.startswith(p + "/") for p in ignored)

    def node(abs_path, rel, entry=None):
        name = os.path.basename(abs_path) if rel else cfg.name
        try:
            s = (entry.stat(follow_symlinks=False) if entry else os.stat(abs_path, follow_symlinks=False))
        except OSError:
            return None
        link = entry.is_symlink() if entry else os.path.islink(abs_path)
        is_dir = (entry.is_dir(follow_symlinks=False) if entry else os.path.isdir(abs_path)) and not link
        g = st.get(rel) or st.get(rel + "/")
        n = {"name": name, "path": rel, "kind": "link" if link else ("dir" if is_dir else "file"),
             "mtime": s.st_mtime, "mtime_ns": s.st_mtime_ns, "git": g["code"] if g else ("" if rel in tracked or is_dir else ("!" if is_ignored(rel) else "")),
             "from": g.get("from") if g else None, "staged": bool(g and g["staged"]),
             "ignored": is_ignored(rel), "desc": desc.get(rel), "locked": cfg.lock_reason(rel) if rel else "프로젝트 맨 위입니다",
             "dest_ok": cfg.lock_reason(rel, inside_only=True) is None if rel else True}
        if is_dir:
            kids = []
            try:
                entries = sorted(os.scandir(abs_path), key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
            except OSError:
                entries = []
            for e in entries:
                if e.name in cfg.hidden:
                    continue
                k = node(e.path, f"{rel}/{e.name}" if rel else e.name, e)
                if k:
                    kids.append(k)
            n["children"] = kids
            n["size"] = sum(k.get("size", 0) for k in kids)
            n["files"] = sum(k.get("files", 1 if k["kind"] == "file" else 0) for k in kids)
            n["changed"] = sum(k.get("changed", 1 if k["git"] in "MADR?" and k["git"] else 0) for k in kids)
        else:
            n["size"] = s.st_size
        return n

    root = node(cfg.root, "")
    gone = [{"path": p, "code": v["code"], "from": v.get("from")} for p, v in st.items()
            if v["code"] in "DR" and not os.path.lexists(cfg.abs(p))]
    return {"root": root, "deleted": gone}
