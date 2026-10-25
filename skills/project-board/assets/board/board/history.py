"""How the plan changed, from git: for every commit that touched the brief or
the roadmap, the edition and state each one had and which sessions appeared,
finished or dropped since the commit before. Only the documents' current
paths are followed: the old editions were copied into old/ and following
them as well would count every early commit twice. Editions that were never
committed have no row; the screen says so instead of filling them in."""
from collections import Counter

from . import gitinfo, md, roadmap

_cache = {}


def build(cfg):
    head = gitinfo.head(cfg)
    if head and head in _cache:
        return _cache[head]
    brief_p, road_p = cfg.docs.get("brief"), cfg.docs.get("roadmap")
    paths = [p for p in (brief_p, road_p) if p]
    commits = list(reversed(gitinfo.log(cfg, *paths))) if paths else []
    events, prev_b, prev_r, prev_s = [], None, None, {}
    for c in commits:
        ev = {"hash": c["short"], "when": c["when"], "subject": c["subject"]}
        if brief_p:
            text = gitinfo.show(cfg, c["hash"], brief_p)
            if text is not None and text != prev_b:
                ev["brief"] = roadmap.header(text.split("\n"))
                prev_b = text
        if road_p:
            text = gitinfo.show(cfg, c["hash"], road_p)
            if text is not None and text != prev_r:
                r = roadmap.parse(text.split("\n"), plan_key=cfg.head("plan", "큰 그림"))
                ev["roadmap"] = r["header"]
                now = {s["id"]: s for s in r["sessions"]}
                ev["sessions"] = {
                    "added": [{"id": k, "short": s["short"]} for k, s in now.items() if k not in prev_s],
                    "done": [{"id": k, "short": s["short"]} for k, s in now.items()
                             if s["state"] == "done" and (k not in prev_s or prev_s[k]["state"] != "done")],
                    "dropped": [{"id": k, "short": s["short"], "state": s["state"]} for k, s in prev_s.items() if k not in now],
                }
                prev_s, prev_r = now, text
        if len(ev) > 3:
            events.append(ev)
    per_day = Counter(c["when"][:10] for c in gitinfo.log(cfg))
    out = {"events": events, "commits_per_day": dict(sorted(per_day.items()))}
    if head:
        _cache.clear()
        _cache[head] = out
    return out
