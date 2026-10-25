#!/usr/bin/env python3
"""The project status board: a local server that reads the project's
markdown documents and git, and serves the board page.

  python3 tools/board/server.py                 # http://127.0.0.1:8790
  python3 tools/board/server.py --port 8791 --root /path/to/project

Python 3.11+ standard library only. Listens on 127.0.0.1 alone. Read
requests re-read the documents (cached by mtime); write requests (rename,
move, delete to the board's trash, restore) need the page's per-launch
token, the same origin and JSON. See tools/board/README.md."""
import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from board import checks, docs, gitinfo, history, index, lookup, md, ops, refs, roadmap, tree  # noqa: E402
from board.config import Config  # noqa: E402

STATIC = os.path.join(HERE, "static")
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".woff2": "font/woff2", ".svg": "image/svg+xml", ".txt": "text/plain; charset=utf-8", ".json": "application/json"}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
       "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


def version(cfg):
    """A short hash that changes when any project file or git's HEAD/index changes."""
    h = hashlib.sha1()
    for d, dirs, names in os.walk(cfg.root):
        dirs[:] = sorted(x for x in dirs if x not in cfg.hidden)
        for n in sorted(names):
            try:
                st = os.lstat(os.path.join(d, n))
            except OSError:
                continue
            h.update(f"{d}/{n}:{st.st_mtime_ns}:{st.st_size};".encode())
    gd = gitinfo.git_dir(cfg)
    for f in ("HEAD", "index", "ORIG_HEAD"):
        try:
            h.update(f"{f}:{os.stat(os.path.join(gd, f)).st_mtime_ns};".encode())
        except (OSError, TypeError):
            pass
    return h.hexdigest()[:12]


def lines(cfg, key):
    p = cfg.doc(key)
    return md.read(p) if p else None


def running_ids(rows):
    """Sessions the STATUS "진행 중인 세션" table says are in progress."""
    out = {}
    for row in rows:
        state = next((v for k, v in row.items() if "상태" in k), "")
        if state.strip().startswith("진행 중"):
            for v in row.values():
                for sid in roadmap.ID.findall(v):
                    out.setdefault(sid, state.strip())
    return out


def state(cfg):
    ver = version(cfg)
    st = docs.status(lines(cfg, "status"), cfg.headings)
    nxt = st["prompt"]["next"] if st and st.get("prompt") else None
    road = roadmap.parse(lines(cfg, "roadmap"), nxt, cfg.head("plan", "큰 그림"))
    if road and st:
        run = running_ids(st["running"])
        for s in road["sessions"]:
            if s["id"] in run and s["state"] != "done":
                s["state"], s["running"] = "running", run[s["id"]]
    br = docs.brief(lines(cfg, "brief"), cfg.headings)
    if br and st:
        docs.deadlines(br["decide"], st["open"])
    gs = gitinfo.status(cfg)
    changes = None
    if gs is not None:
        live = {p: v for p, v in gs.items() if v["code"] != "!"}
        counts = {}
        for v in live.values():
            counts[v["code"]] = counts.get(v["code"], 0) + 1
        changes = {"total": len(live), "counts": counts, "staged": sum(1 for v in live.values() if v["staged"]),
                   "paths": sorted(live)[:400]}
    last = gitinfo.log(cfg, n=1)
    dirs = docs.directions(lines(cfg, "directions"))
    reading = index.reading_path(cfg, road)          # the rules file's part is there even without a roadmap
    if road:
        road["files"] = index.session_files(cfg, road)
        road["reading"] = reading
    return {"project": cfg.name, "version": ver, "root": cfg.root, "docs": cfg.docs, "headings": cfg.headings, "check_cmd": cfg.check_cmd,
            "status": st, "roadmap": road, "reading": reading, "brief": br, "changes": changes,
            "last_commit": last[0] if last else None, "head": gitinfo.head(cfg),
            "directions": {"count": len(dirs), "recent": dirs[-3:]},
            "old": docs.old_directions(lines(cfg, "old_index")),
            "check": checks.run(cfg, ver)}


def find_doc(cfg, name):
    """A markdown document by project path, or by bare name in the search folders."""
    if not isinstance(name, str) or not name.endswith(".md") or "\0" in name:
        return None
    try:
        rel, path = ops.resolve(cfg, name)
        if os.path.isfile(path):
            return rel, path
    except ops.OpError:
        pass
    base = os.path.basename(name)
    for d in cfg.search:
        for dirpath, dirs, files in os.walk(cfg.abs(d)):
            dirs[:] = sorted(x for x in dirs if x not in cfg.hidden)
            if base in files:
                p = os.path.join(dirpath, base)
                return os.path.relpath(p, cfg.root), p
    return None


TEXT_EXT = {".md", ".txt", ".py", ".js", ".mjs", ".css", ".html", ".json", ".toml", ".sh", ".yml", ".yaml", ".csv",
            ".svg", ".gitignore", ".cfg", ".ini", ".xml", ".jsonl", ".log"}
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
               ".webp": "image/webp", ".svg": "image/svg+xml"}
TEXT_LIMIT = 512 * 1024


def readable(cfg, q):
    """(rel, path) of a project file the board may show: inside the root, not a
    link, not git's own folder."""
    rel, path = ops.resolve(cfg, (q.get("path") or [""])[0])
    if rel.split("/", 1)[0] in cfg.hidden or not os.path.isfile(path):
        raise ops.OpError(404, "보여 줄 수 있는 파일이 아닙니다")
    return rel, path


def file_view(cfg, q):
    """A file's content for the files screen: markdown, text, an image, or the
    reason it cannot be shown. Text is sent as text and drawn with textContent."""
    rel, path = readable(cfg, q)
    size = os.path.getsize(path)
    ext = os.path.splitext(path)[1].lower() or os.path.basename(path).lower()
    out = {"path": rel, "size": size, "ext": ext}
    if ext in IMAGE_TYPES:
        return {**out, "kind": "image", "url": f"/api/raw?path={quote(rel)}"}
    with open(path, "rb") as f:
        head = f.read(TEXT_LIMIT + 1)
    if b"\0" in head[:8192] and ext not in TEXT_EXT:
        return {**out, "kind": "binary"}
    text = head[:TEXT_LIMIT].decode("utf-8", "replace")
    return {**out, "kind": "md" if ext == ".md" else "text", "text": text,
            "truncated": size > TEXT_LIMIT, "lines": text.count("\n") + 1}


def doc(cfg, q):
    found = find_doc(cfg, (q.get("name") or [""])[0])
    if not found:
        return 404, {"error": "그 문서를 찾지 못했습니다"}
    rel, path = found
    ls = md.read(path) or []
    key = (q.get("ch") or [""])[0].strip()
    if key:
        ch = md.chapter(ls, key)
        if not ch:
            return 404, {"error": f"{rel}에 {key}장이 없습니다", "doc": rel}
        i, title, level, body = ch
        return 200, {"doc": rel, "title": title, "level": level, "line": i + 1, "text": "\n".join(body[:3000])}
    return 200, {"doc": rel, "title": rel, "level": 0, "line": 1, "text": "\n".join(ls[:3000])}


class Board(BaseHTTPRequestHandler):
    cfg = None
    token = None
    server_version = "board/1"
    sys_version = ""

    def log_message(self, fmt, *args):
        path = getattr(self, "path", "")      # unset when the request line itself was malformed
        if "/api/version" not in path and "/static/" not in path:
            sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))

    def host_ok(self):
        port = self.server.server_address[1]
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def send(self, status, body, ctype="application/json; charset=utf-8", cache="no-store"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.host_ok():
            return self.send(403, {"error": "이 주소로는 열 수 없습니다"})
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path in ("/", "/index.html"):
                with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
                    page = f.read().replace("__BOARD_TOKEN__", self.token).replace("__BOARD_NAME__", self.cfg.name)
                return self.send(200, page.encode(), TYPES[".html"])
            if u.path.startswith("/static/"):
                p = os.path.realpath(os.path.join(STATIC, u.path[len("/static/"):]))
                if not p.startswith(STATIC + os.sep) or not os.path.isfile(p):
                    return self.send(404, {"error": "없음"})
                with open(p, "rb") as f:
                    return self.send(200, f.read(), TYPES.get(os.path.splitext(p)[1], "application/octet-stream"),
                                     "max-age=31536000, immutable" if p.endswith(".woff2") else "no-cache")
            if u.path == "/api/version":
                return self.send(200, {"v": version(self.cfg)})
            if u.path == "/api/state":
                return self.send(200, state(self.cfg))
            if u.path == "/api/history":
                br = docs.brief(lines(self.cfg, "brief"), self.cfg.headings)
                return self.send(200, {**history.build(self.cfg),
                                       "directions": docs.directions(lines(self.cfg, "directions")),
                                       "old": docs.old_directions(lines(self.cfg, "old_index")),
                                       "changes": br["changes"] if br else [], "changelog": br["changelog"] if br else [],
                                       "brief": {k: br[k] for k in ("edition", "date", "state")} if br else None})
            if u.path == "/api/tree":
                return self.send(200, {**tree.build(self.cfg), "trash": ops.trash(self.cfg)})
            if u.path == "/api/doc":
                return self.send(*doc(self.cfg, q))
            if u.path == "/api/file":
                return self.send(200, file_view(self.cfg, q))
            if u.path == "/api/raw":
                rel, path = readable(self.cfg, q)
                ctype = IMAGE_TYPES.get(os.path.splitext(path)[1].lower())
                if not ctype:
                    return self.send(404, {"error": "그림 파일만 그대로 보냅니다"})
                with open(path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; sandbox")
                self.end_headers()
                self.wfile.write(data)
                return None
            if u.path == "/api/files":
                ix = index.build(self.cfg, version(self.cfg))
                return self.send(200, {k: v for k, v in ix.items() if not k.startswith("_")})
            if u.path == "/api/profile":
                rel = ops.clean((q.get("path") or [""])[0])
                p = index.profile(self.cfg, version(self.cfg), rel)
                return self.send(200, p) if p else self.send(404, {"error": "그 파일을 찾지 못했습니다"})
            if u.path == "/api/diff":
                rel, _ = readable(self.cfg, q) if not (q.get("path") or [""])[0].endswith("/") else (None, None)
                return self.send(200, lookup.diff(self.cfg, rel, gitinfo.status(self.cfg)))
            if u.path == "/api/search":
                return self.send(200, lookup.search(self.cfg, (q.get("q") or [""])[0]))
            if u.path == "/api/glossary":
                return self.send(200, {"words": lookup.glossary(self.cfg)})
            if u.path == "/api/refs":
                rel = ops.clean((q.get("path") or [""])[0])
                return self.send(200, refs.find(self.cfg, rel))
            return self.send(404, {"error": "없는 주소입니다"})
        except ops.OpError as e:
            return self.send(e.status, {"error": e.msg, **e.extra})
        except Exception as e:  # noqa: BLE001 - the page shows the error in the block that asked
            sys.stderr.write(f"error {u.path}: {e!r}\n")
            return self.send(500, {"error": f"서버에서 읽다가 멈췄습니다: {type(e).__name__}"})

    def do_POST(self):
        port = self.server.server_address[1]
        origin = self.headers.get("Origin")
        site = self.headers.get("Sec-Fetch-Site")
        if (not self.host_ok() or origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")
                or (site and site != "same-origin")
                or not (self.headers.get("Content-Type") or "").startswith("application/json")
                or not hmac.compare_digest(self.headers.get("X-Board-Token", ""), self.token)):
            return self.send(403, {"error": "이 요청은 받을 수 없습니다(현황판 화면에서만 됩니다)"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.send(400, {"error": "요청 내용이 올바르지 않습니다"})
        path = urlparse(self.path).path
        try:
            if path == "/api/op/rename":
                out = ops.rename(self.cfg, body.get("path"), body.get("name"), body.get("expect"))
            elif path == "/api/op/move":
                out = ops.move(self.cfg, body.get("path"), body.get("dest"), body.get("expect"))
            elif path == "/api/op/delete":
                out = ops.delete(self.cfg, body.get("path"), body.get("expect"))
            elif path == "/api/op/restore":
                out = ops.restore(self.cfg, body.get("id"), body.get("name"))
            elif path == "/api/understood":
                rel, p = ops.resolve(self.cfg, body.get("path"))
                if not os.path.isfile(p):
                    raise ops.OpError(400, "파일만 표시할 수 있습니다")
                mark = index.understood_set(self.cfg, rel, bool(body.get("on")), os.lstat(p).st_mtime_ns)
                return self.send(200, {"path": rel, "understood": "yes" if mark else None})
            elif path == "/api/check":
                return self.send(200, checks.run(self.cfg, version(self.cfg) + secrets.token_hex(2)))
            else:
                return self.send(404, {"error": "없는 주소입니다"})
        except ops.OpError as e:
            return self.send(e.status, {"error": e.msg, **e.extra})
        except OSError as e:
            return self.send(500, {"error": f"파일을 다루지 못했습니다: {e.strerror or e}"})
        sys.stderr.write(f"op {out['op']}: {out.get('from')} -> {out.get('to') or out.get('trash')}\n")
        return self.send(200, {**out, "check": checks.run(self.cfg, version(self.cfg))})


def serve(cfg, port, ready=None):
    handler = type("BoardHandler", (Board,), {"cfg": cfg, "token": secrets.token_urlsafe(24)})
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    httpd.daemon_threads = True
    if ready:
        ready(httpd)
    return httpd


def main(argv=None):
    ap = argparse.ArgumentParser(description="프로젝트 현황판 (tools/board/README.md)")
    ap.add_argument("--config", help="board.toml (기본: 이 폴더의 board.toml)")
    ap.add_argument("--root", help="프로젝트 맨 위 (기본: board.toml의 root)")
    ap.add_argument("--port", type=int, help="포트 (기본: board.toml의 port)")
    a = ap.parse_args(argv)
    cfg = Config(a.config, a.root)
    port = a.port or cfg.port
    try:
        httpd = serve(cfg, port)
    except OSError as e:
        print(f"현황판을 열지 못했습니다: 127.0.0.1:{port} ({e.strerror}). 다른 포트는 --port", file=sys.stderr)
        return 1
    print(f"현황판: http://127.0.0.1:{port}  (프로젝트 {cfg.root}, 끄려면 Ctrl+C)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
