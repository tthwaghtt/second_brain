"""Where a path is mentioned: documents and code that would point at the old
place after a rename or a move. The board only shows them; it never edits a
document. Mentions inside records (sources the project never rewrites) are
listed apart, since an old path there is expected."""
import os
import re

TEXT = (".md", ".py", ".js", ".mjs", ".sh", ".json", ".html", ".css", ".txt", ".toml", ".yml", ".yaml")


def files(cfg):
    for d, dirs, names in os.walk(cfg.root):
        rel_d = os.path.relpath(d, cfg.root)
        rel_d = "" if rel_d == "." else rel_d + "/"
        dirs[:] = [x for x in dirs if x not in cfg.hidden
                   and not any((rel_d + x + "/").startswith(s) for s in cfg.skip_search)]
        for n in names:
            if n.endswith(TEXT):
                yield rel_d + n


def find(cfg, rel, limit=200):
    """Lines that name rel. A file is also found by its bare name when no
    other file in the project has that name (documents are often named
    that way: "BRIEF.md 2장")."""
    rel = rel.strip("/")
    base = os.path.basename(rel)
    all_files = list(files(cfg))
    same_name = sum(1 for f in all_files if os.path.basename(f) == base)
    keys = [rel]
    if base != rel and same_name <= 1 and len(base) >= 6 and "." in base:
        keys.append(base)
    # a mention is the key standing alone: not the tail of another path ("old/README.md" is not "README.md"),
    # optionally reached through "../"
    rx = re.compile("|".join(rf"(?<![\w./-])(?:\.\./)*{re.escape(k)}(?![\w/-])" for k in keys))
    live, records = [], []
    for f in all_files:
        if f == rel or f.startswith(rel + "/"):
            continue
        try:
            with open(cfg.abs(f), encoding="utf-8", errors="ignore") as fh:
                for n, line in enumerate(fh, 1):
                    if rx.search(line):
                        hit = {"file": f, "line": n, "text": line.strip()[:200]}
                        (records if cfg.is_record(f) else live).append(hit)
                        if len(live) + len(records) >= limit:
                            return {"keys": keys, "live": live, "records": records, "cut": True}
        except OSError:
            continue
    return {"keys": keys, "live": live, "records": records, "cut": False}
