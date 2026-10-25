#!/usr/bin/env python3
"""Checks the board: its parsers against the project's real documents, and
every file operation in a throwaway copy of the project (git init'ed in the
system temp folder). The project itself is never touched.

  python3 tools/board/check.py           # both
  python3 tools/board/check.py --docs    # parsers only
  python3 tools/board/check.py --ops     # file operations and request guards only
  python3 tools/board/check.py --config other/board.toml --root /path/to/project

A document the project does not have is skipped, not failed: its screen
stays empty and says so, and every chapter the screens read that is not
there is listed as a skip. A chapter name board.toml sets must be in its
document. board.toml [facts] holds what this project's documents said when
the board was set up (README.md 5장); a project starts with none, and every
key is optional."""
import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import server  # noqa: E402
from board import index, lookup, md, ops, tree  # noqa: E402
from board.config import Config  # noqa: E402

# board.toml [facts] keys (all optional): done [ids], stage1 [ids in order], outline [ids], edges [[from, to]],
# brief_edition n, decide n, directions n (old-plans rows), writes [ids that list 쓸 파일]
# e.g. done = ["P3"], stage1 = ["B1", "B2", "B3", "B4", "B5"], brief_edition = 7
# the chapters the screens read: [headings] key → (document, the board's default name)
HEAD_DOC = {"now": ("status", "★ 지금"), "prompt": ("status", "다음 세션 시작 프롬프트"), "running": ("status", "진행 중인 세션"),
            "open": ("status", "정할 것이 있는 곳"), "plan": ("roadmap", "큰 그림"), "changes": ("brief", "바뀐 결정"),
            "decide": ("brief", "정할 것"), "map_tree": ("map", "폴더 지도"), "map_roles": ("map", "파일의 역할"),
            "map_terms": ("map", "용어"), "start": ("rules", "세션 시작")}
# chapters a document may not have yet (the planning session writes the role table later; a status
# document drops its table of running sessions when none runs): missing is a skip, not a failure
LATER = {"map_roles", "map_terms", "running", "open", "issues", "verified"}
results, skipped = [], []


def ok(cond, what):
    results.append((bool(cond), what))
    print(("  ok   " if cond else "  FAIL ") + what)


def skip(what):
    skipped.append(what)
    print("  skip " + what)


def docs_checks(cfg):
    print("parsers, on the real documents")
    for key, rel in sorted(cfg.docs.items()):
        if not os.path.isfile(cfg.abs(rel)):
            skip(f"board.toml [docs] {key} = {rel}: 파일이 없음 (그 화면은 비어 있음)")
    for key, (role, default) in HEAD_DOC.items():
        rel = cfg.docs.get(role) or ("CLAUDE.md" if role == "rules" else None)
        lines = md.read(cfg.abs(rel)) if rel else None
        if lines is None:
            continue
        name, mine = cfg.headings.get(key, default), key in cfg.headings
        if md.chapter(lines, name):
            ok(True, f'board.toml [headings] {key} = "{name}": {rel}에 그 장이 있음')
        elif mine and key not in LATER:
            ok(False, f'board.toml [headings] {key} = "{name}": {rel}에 그 장이 있음')
        else:
            skip(f'{rel}에 "{name}" 장이 {"아직 " if key in LATER else ""}없음: 그 칸은 비어 있음{" (생기면 저절로 읽음)" if key in LATER else ""}')
    st = server.state(cfg)
    f = cfg.facts
    road = st["roadmap"]
    if road is None:
        skip("로드맵이 없음: 노선도·로드맵 화면과 읽는 길의 세션 몫은 비어 있음")
    else:
        ok(road["sessions"], f"로드맵에서 세션을 읽음 ({len(road['sessions'])}개)")
        states = {s["id"]: s["state"] for s in road["sessions"]}
        counts = {}
        for v in states.values():
            counts[v] = counts.get(v, 0) + 1
        ok(sum(counts.values()) == len(states), f"상태별 세션 수의 합 = 전체 ({counts})")
        heads = {m.group(1): "— 완료" in m.group(0) for m in re.finditer(r"^#{2,4}\s+([A-Z]\d+)\.\s.*$", "\n".join(md.read(cfg.doc("roadmap"))), re.M)}
        ok(all((s["state"] == "done") == heads.get(s["id"], False) for s in road["sessions"] if s["detail"]),
           "끝남은 세션 머리의 '완료'로만 판단 (체크박스 수와 무관)")
        ticked = sum(c["done"] for s in road["sessions"] for fl in s["fields"] for c in fl.get("checks", []))
        ok(True, f"완성 기준 체크박스: 체크된 것 {ticked}개 (문서에 적힌 그대로 보여 줌)")
        if "done" in f:
            ok(all(states.get(i) == "done" for i in f["done"]), f"끝난 세션 {f['done']}")
        if "stage1" in f:
            ok([s["id"] for s in road["sessions"] if s["stage"] == 1] == f["stage1"], "단계 1의 세션 순서")
        if "outline" in f:
            ok(all(states.get(i) == "outline" for i in f["outline"]), f"한 줄 항목 {f['outline']}")
        if "edges" in f:
            es = [e[:2] for e in road["edges"] if e[2] == "prereq"]
            ok(all(e in es for e in f["edges"]), f"전제에서 선로를 읽음 {f['edges']}")
        sf = road["files"]
        ok(all(x["kind"] in ("write", "read") for x in sf), f"세션 × 파일 {len(sf)}개 (로드맵의 쓸 파일·읽을 것)")
        ok(all(x["path"] is None for x in sf if x["name"].startswith("../")), "프로젝트 밖 이름은 경로로 바꾸지 않음")
        for sid in f.get("writes", []):
            ok(any(x["session"] == sid and x["kind"] == "write" for x in sf), f"{sid}의 쓸 파일을 읽음")
    rules = cfg.docs.get("rules", "CLAUDE.md")
    rp = st["reading"]
    start = md.chapter(md.read(cfg.abs(rules)) or [], cfg.head("start", "세션 시작"))
    cmds = len(re.findall(index.DOC_SECTION, "\n".join(start[3]))) if start else 0
    ok(rp["common"] and rp["common"][0]["doc"] == rules and (not cmds or len(rp["common"]) == cmds + 1),
       f"읽는 길: {' → '.join(c['doc'] for c in rp['common'])} ({rules}의 세션 시작 장에서, 로드맵이 없어도)")
    br = st["brief"]
    if br is None:
        skip("기획서가 없음: 정할 것·바뀐 결정은 비어 있음")
    else:
        if "brief_edition" in f:
            ok(br["edition"] == f["brief_edition"], f"기획서 판 {f['brief_edition']}")
        if "decide" in f:
            ok(len(br["decide"]) == f["decide"], f"정할 것 {f['decide']}개")
        ch = md.chapter(md.read(cfg.doc("brief")), cfg.head("changes", "바뀐 결정"))
        raw = sum(1 for line in ch[3] if line.startswith("- ")) if ch else 0
        ok(len(br["changes"]) == raw, f"바뀐 결정 {raw}줄을 모두 읽음")
        ok(all(c["steps"][0]["struck"] and len(c["steps"]) >= 2 for c in br["changes"]), "바뀐 결정마다 옛(취소선) → 새")
    if "directions" in f:
        ok(len(st["old"]) == f["directions"], f"방향 {f['directions']}개 ({cfg.docs.get('old_index')})")
    h = server.history.build(cfg)
    whens = [e["when"] for e in h["events"]]
    ok(whens == sorted(whens), f"판 기록이 시간순 ({len(h['events'])}개)")
    log = server.gitinfo.log(cfg, *[p for p in (cfg.docs.get("brief"), cfg.docs.get("roadmap")) if p])
    ok(len(h["events"]) <= len(log) and len({e["hash"] for e in h["events"]}) == len(h["events"]),
       "판을 두 번 세지 않음 (문서의 지금 경로의 커밋만)")
    eds = [e["brief"]["edition"] for e in h["events"] if e.get("brief") and e["brief"]["edition"]]
    ok(eds == sorted(eds), f"기획서 판이 줄지 않음 {eds}")
    desc = tree.descriptions(cfg)
    if not desc:
        skip("지도 문서의 폴더 지도 나무가 없음: 파일 설명은 비어 있음")
    else:
        gone = [p for p in desc if not os.path.lexists(cfg.abs(p))]
        ok(len(gone) <= max(2, len(desc) // 10), f"지도 설명 {len(desc)}개 중 없는 경로 {len(gone)}개 {gone[:4]}")
    t = tree.build(cfg)["root"]
    walked = sum(len([n for n in fs if n not in cfg.hidden]) for d, ds, fs in os.walk(cfg.root)
                 if not any(part in cfg.hidden for part in os.path.relpath(d, cfg.root).split(os.sep)))
    ok(t["files"] == walked, f"나무의 파일 수 = 실제 파일 수 ({t['files']})")
    ck = st["check"]
    ok(ck is None or ck["ok"], "문서 검사 결과 줄을 읽음" if ck else "문서 검사 명령 없음 (board.toml [check])")
    ix = index.build(cfg, server.version(cfg))
    ok(len(ix["files"]) == walked, f"파일 색인의 수 = 실제 파일 수 ({len(ix['files'])})")
    ok(all(r["role"] and r["tier"] in (0, 1, 2, 3) for r in ix["files"]), "모든 파일에 역할과 무게가 있음")
    ok(ix["map_roles"] or all(r["inferred"] for r in ix["files"]), "지도의 역할 표가 없으면 모든 역할을 추정으로 표시")
    tot = sum(v["total"] for v in ix["progress"].values())
    ok(tot == sum(1 for r in ix["files"] if r["tier"] < 3), f"파악 진도의 합 = 기계가 만든 것을 뺀 파일 수 ({tot})")
    ok(all(not r["stale"] or (r["tier"] == 0 and not any(w in r["how"] for w in index.FROZEN)) for r in ix["files"]),
       "신선도는 지휘 문서만 따지고 얼린 기록·보고서는 빼고")


BIG = 20 * 1024 * 1024


def copy_project(cfg):
    """A throwaway copy without git, the board's own scratch, the places the
    board does not search (render outputs and the like) and files over 20 MB."""
    tmp = tempfile.mkdtemp(prefix="board-check-")
    root = os.path.join(tmp, cfg.name)
    skip_dirs = [s.rstrip("/") for s in cfg.skip_search] + [cfg.trash, cfg.state]

    def ignore(d, names):
        rel_d = os.path.relpath(d, cfg.root)
        rel_d = "" if rel_d == "." else rel_d.replace(os.sep, "/") + "/"
        out = []
        for n in names:
            p = os.path.join(d, n)
            if (n in (".git", "node_modules", "__pycache__", ".taste-skill") or n.endswith(".woff2")
                    or (rel_d + n) in skip_dirs or (os.path.isfile(p) and not os.path.islink(p) and os.path.getsize(p) > BIG)):
                out.append(n)
        return out
    shutil.copytree(cfg.root, root, symlinks=True, ignore=ignore)
    return tmp, root


def commit_copy(root):
    g = ["git", "-c", "user.name=board-check", "-c", "user.email=board-check@localhost"]
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "copy"]):
        subprocess.run(g + args, cwd=root, check=True, capture_output=True)


def expect(cfg, rel):
    st = os.lstat(cfg.abs(rel))
    return {"mtime_ns": st.st_mtime_ns, "size": st.st_size}


def raises(fn, status, words=None):
    try:
        fn()
    except ops.OpError as e:
        return e.status == status and (words is None or words in e.msg)
    return False


def probe_place(c):
    """A folder for the probe documents: inside the first search folder that is
    not locked (so bare-name clashes apply), else at the project's top."""
    for d in c.search:
        base = "" if d.strip("/") in ("", ".") else d.rstrip("/") + "/"
        if not c.lock_reason(base + "board-check", inside_only=True):
            return base + "board-check", True
    return "board-check", False


def add_role_row(c, folder):
    """A row for folder in the map's role table (made when the map has none)."""
    rel = c.docs.get("map") or "docs/MAP.md"
    c.docs["map"] = rel
    os.makedirs(os.path.dirname(c.abs(rel)) or c.root, exist_ok=True)
    lines = md.read(c.abs(rel)) or ["# MAP", ""]
    row = f"| `{folder}/` | 설계 | 고쳐 씀 | 기획 책임 세션 | 지휘 |"
    ch = md.chapter(lines, c.head("map_roles", "파일의 역할"))
    sep = next((ch[0] + 1 + k for k, x in enumerate(ch[3]) if re.match(r"^\|\s*:?-{3,}", x)), None) if ch else None
    if sep is not None:
        lines = lines[:sep + 1] + [row] + lines[sep + 1:]
    else:
        lines = lines + ["", f"## 9. {c.head('map_roles', '파일의 역할')}", "",
                         "| 경로 | 역할 | 바뀌는 법 | 누가 고치나 | 무게 |", "|---|---|---|---|---|", row]
    with open(c.abs(rel), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def ops_checks(cfg, config_path):
    print("file operations, in a throwaway copy")
    tmp, root = copy_project(cfg)
    try:
        c = Config(config_path, root=root)
        place, clash_ok = probe_place(c)
        os.makedirs(os.path.join(root, place, "other"), exist_ok=True)
        a = f"{place}/PROBE.md"
        for rel, text in ((a, "# 시험 문서\n\n본문\n"), (f"{place}/other/OTHER.md", "# 다른 문서\n")):
            with open(c.abs(rel), "w", encoding="utf-8") as fh:
                fh.write(text)
        commit_copy(root)
        before = hashlib.sha256(open(c.abs(a), "rb").read()).hexdigest()
        r = ops.rename(c, a, "RENAMED.md", expect(c, a))
        b = r["to"]
        ok(os.path.exists(c.abs(b)) and not os.path.exists(c.abs(a)), f"이름 바꾸기 {a} → {b}")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        st = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True).stdout
        ok(re.search(r"^R\s+.*RENAMED\.md", st, re.M), "git이 옮긴 것으로 알아봄 (R)")
        ok(raises(lambda: ops.rename(c, b, "x.md", {"mtime_ns": 1, "size": 1}), 409), "그사이 바뀐 파일은 거절 (409)")
        d = ops.delete(c, b, expect(c, b))
        ok(not os.path.exists(c.abs(b)) and os.path.isdir(os.path.join(c.abs(c.trash), d["trash"])), "휴지통으로 옮김")
        ok(any(x["id"] == d["trash"] for x in ops.trash(c)), "휴지통 목록에 보임")
        rr = ops.restore(c, d["trash"])
        ok(rr["to"] == b and rr["sha_ok"] and hashlib.sha256(open(c.abs(b), "rb").read()).hexdigest() == before, "되살리기, 내용이 같음")
        ok(not ops.trash(c), "되살린 뒤 휴지통이 빔")
        os.makedirs(c.abs("scratch/inner"))
        open(c.abs("scratch/note.txt"), "w").write("x")
        m = ops.move(c, "scratch/note.txt", "scratch/inner", expect(c, "scratch/note.txt"))
        ok(os.path.exists(c.abs(m["to"])), "옮기기")
        ok(raises(lambda: ops.move(c, "scratch", "scratch/inner", expect(c, "scratch")), 400), "폴더를 자기 안으로 옮기지 않음")
        if clash_ok:
            ok(raises(lambda: ops.rename(c, b, "OTHER.md", expect(c, b)), 409, "이름이 같아집니다"), "찾는 곳 안에 같은 이름 문서를 만들지 않음")
        else:
            skip("문서를 이름으로 찾는 곳이 모두 잠겨 같은 이름 검사는 건너뜀")
        locked = [p.rstrip("/") for p, _ in c.locked] + ([f"{cfg.board_dir}/board.toml"] if cfg.board_dir else [])
        for rel in locked:
            if os.path.lexists(c.abs(rel)):
                ok(raises(lambda rel=rel: ops.delete(c, rel, expect(c, rel)), 403), f"잠긴 곳은 지우지 않음: {rel}")
            if os.path.isdir(c.abs(rel)):
                inner = next((os.path.relpath(os.path.join(dp, n), c.root) for dp, _, ns in os.walk(c.abs(rel)) for n in ns), None)
                if inner:
                    ok(raises(lambda inner=inner: ops.delete(c, inner, expect(c, inner)), 403), f"잠긴 곳 안의 것도 지우지 않음: {inner}")
        parent = next((p.split("/")[0] for p in locked if "/" in p and os.path.isdir(c.abs(p.split("/")[0]))), None)
        if parent:
            ok(raises(lambda: ops.delete(c, parent, expect(c, parent)), 403), f"잠긴 곳을 품은 폴더는 다루지 않음: {parent}")
        else:
            skip("잠긴 곳을 품은 폴더가 없어 그 검사는 건너뜀")
        folder = next((p for p in locked if os.path.isdir(c.abs(p))), None)
        if folder:
            ok(raises(lambda: ops.move(c, "scratch/inner/note.txt", folder, expect(c, "scratch/inner/note.txt")), 403), f"잠긴 곳 안으로 옮기지 않음: {folder}")
        else:
            skip("잠긴 폴더가 없어 '잠긴 곳 안으로 옮기기' 검사는 건너뜀")
        ok(raises(lambda: ops.delete(c, "../outside", None), 400), "../ 경로 거절")
        ok(raises(lambda: ops.delete(c, "/etc/hosts", None), 400), "절대 경로 거절")
        os.symlink(tmp, c.abs("scratch/link"))
        ok(raises(lambda: ops.delete(c, "scratch/link", expect(c, "scratch/link")), 403), "링크는 다루지 않음")
        ok(raises(lambda: ops.move(c, "scratch/inner/note.txt", "scratch/link", expect(c, "scratch/inner/note.txt")), 403), "링크를 따라 밖으로 나가지 않음")
        cv = server.version(c)
        und = index.understood_set(c, b, True, os.lstat(c.abs(b)).st_mtime_ns)
        ok(und and os.path.isfile(os.path.join(c.abs(c.state), "understood.json")), "파악함은 현황판의 .state/에만 적음")
        row = next(r for r in index.build(c, cv + "u")["files"] if r["path"] == b)
        ok(row["understood"] == "yes", "파악함 표시가 읽힘")
        with open(c.abs(b), "a", encoding="utf-8") as fh:
            fh.write("\n바뀜\n")
        row = next(r for r in index.build(c, cv + "v")["files"] if r["path"] == b)
        ok(row["understood"] == "changed", "파악한 뒤 바뀐 파일은 '다시 볼 것'")
        d = lookup.diff(c, b, server.gitinfo.status(c))
        ok(d["kind"] == "new" or any(r["k"] == "add" and "바뀜" in r["t"] for r in d["rows"]), "바뀐 내용에 더한 줄이 보임")
        add_role_row(c, place)
        ix2 = index.build(c, cv + "w")
        r2 = next(r for r in ix2["files"] if r["path"] == b)
        ok(ix2["map_roles"] and r2["role"] == "설계" and not r2["inferred"], "지도의 역할 표가 있으면 그것을 따름 (추정 아님)")
        s = lookup.search(c, "바뀜")
        ok(any(x["file"] == b for x in s["hits"]), "본문 찾기")
        with contextlib.redirect_stderr(io.StringIO()):      # the test server's access log: its 403s are the expected refusals
            http_checks(c, b)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def http_checks(c, path):
    httpd = server.serve(c, 0)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"

    def call(p, body=None, headers=None):
        req = urllib.request.Request(base + p, data=None if body is None else json.dumps(body).encode(), headers=headers or {},
                                     method="GET" if body is None else "POST")
        try:
            with urllib.request.urlopen(req) as f:
                return f.status, f.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()
    try:
        s, page = call("/")
        token = re.search(r'name="board-token" content="([^"]+)"', page).group(1)
        ok(s == 200 and token != "__BOARD_TOKEN__", "화면에 실행마다 새 토큰")
        ok(call("/api/state", headers={"Host": "evil.example"})[0] == 403, "다른 Host 거절 (DNS rebinding)")
        good = {"Content-Type": "application/json", "Origin": base, "X-Board-Token": token}
        st = os.lstat(c.abs(path))
        body = {"path": path, "name": "VIA_HTTP.md", "expect": {"mtime_ns": st.st_mtime_ns, "size": st.st_size}}
        ok(call("/api/op/rename", body, {**good, "X-Board-Token": "wrong"})[0] == 403, "토큰이 틀리면 거절")
        ok(call("/api/op/rename", body, {**good, "Origin": "http://evil.example"})[0] == 403, "다른 출처 거절")
        ok(call("/api/op/rename", body, {**good, "Content-Type": "text/plain"})[0] == 403, "JSON이 아니면 거절")
        s, out = call("/api/op/rename", body, good)
        ok(s == 200 and json.loads(out)["to"].endswith("VIA_HTTP.md"), "화면에서 보낸 요청은 받음")
        ok(call("/api/doc?name=../../../../etc/passwd.md")[0] == 404, "문서 읽기도 프로젝트 밖으로 나가지 않음")
        ok(call("/api/understood", {"path": "VIA", "on": True}, {**good, "X-Board-Token": "wrong"})[0] == 403, "파악함 표시도 토큰이 있어야 받음")
        ok(call("/api/file?path=../../etc/hosts")[0] in (400, 403, 404), "원문 읽기도 프로젝트 밖으로 나가지 않음")
        ok(call("/api/diff?path=.git/config")[0] in (400, 403, 404), "git 내부는 보여 주지 않음")
        ok(call("/static/../server.py")[0] in (403, 404), "static 밖 파일은 주지 않음")
    finally:
        httpd.shutdown()


def main(argv=None):
    ap = argparse.ArgumentParser(description="현황판 검사 (README.md 1장)")
    ap.add_argument("--docs", action="store_true", help="파서만, 실제 문서로")
    ap.add_argument("--ops", action="store_true", help="파일 조작과 요청 검사만, 임시 복사본에서")
    ap.add_argument("--config", help="board.toml (기본: 이 폴더의 board.toml)")
    ap.add_argument("--root", help="프로젝트 맨 위 (기본: board.toml의 root)")
    a = ap.parse_args(argv)
    cfg = Config(a.config, a.root)
    both = not (a.docs or a.ops)
    if a.docs or both:
        docs_checks(cfg)
    if a.ops or both:
        ops_checks(cfg, a.config)
    bad = [w for good, w in results if not good]
    print(f"board check: {len(results) - len(bad)} ok, {len(bad)} failed, {len(skipped)} skipped")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
