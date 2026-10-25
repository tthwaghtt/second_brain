#!/usr/bin/env python3
"""Sets up the project status board (assets/board/) in a second-brain project.

  python3 setup_board.py scan <project>                  # 무엇을 찾았는지만 보여 줌, 아무것도 쓰지 않음
  python3 setup_board.py install <project> [--dest tools/board] [--name NAME] [--port N]
  python3 setup_board.py prompt <project> [--dest tools/board]    # 기획 책임 세션에 줄 역할 표 프롬프트

scan reads only file names, each candidate document's header line and its
chapter list (headings), plus the rules file's "do not touch" lines and the
roadmap's 쓸 파일 lines, never whole bodies, and prints what it found and a
board.toml draft. install copies the board's code into <project>/<dest>/
and writes that draft as board.toml; it refuses when <dest> already exists.
prompt prints the prompt for the project's planning session: the map's role
table, one-line descriptions of the files the map does not describe, and the
board's own entry (the same text as the files screen's button, plus that).
Python 3.11+ standard library only."""
import argparse
import json
import os
import re
import shutil
import socket
import sys
import tomllib
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.join(os.path.dirname(HERE), "assets", "board")
HEAD = re.compile(r"^(#{1,6})\s+(.*)$")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".trash", ".state", ".taste-skill", ".impeccable"}
OLD_PARTS = ("old", "archive", "옛")

# each document the board reads: names it usually has (best first) and chapters it usually holds
ROLES = {
    "status": (["STATUS.md", "HANDOFF.md"], ["now", "prompt", "running", "open"]),
    "roadmap": (["ROADMAP.md"], ["plan"]),
    "brief": (["BRIEF.md", "PLAN.md", "SPEC.md", "DESIGN.md"], ["changes", "decide"]),
    "map": (["MAP.md"], ["map_tree", "map_roles", "map_terms"]),
    "directions": (["USER_DIRECTIONS.md"], []),
}
# [headings] keys: the board's default chapter name (README.md 3장) and the words to look for when it is not there
HEADINGS = {
    "now": ("★ 지금", ["지금"]),
    "prompt": ("다음 세션 시작 프롬프트", ["시작 프롬프트", "프롬프트"]),
    "running": ("진행 중인 세션", ["진행 중"]),
    "open": ("정할 것이 있는 곳", ["정할 것이 있는", "정할 것"]),
    "plan": ("큰 그림", ["큰 그림", "전체"]),
    "changes": ("바뀐 결정", ["바뀐", "결정 기록"]),
    "decide": ("정할 것", ["정할 것", "열린 질문"]),
    "map_tree": ("폴더 지도", ["폴더", "나무"]),
    "map_roles": ("파일의 역할", ["역할"]),
    "map_terms": ("용어", ["용어"]),
    "start": ("세션 시작", ["세션 시작", "세션을 시작", "시작하면"]),
}
# which document each [headings] key names a chapter of (check.py HEAD_DOC)
HEAD_DOC = {"now": "status", "prompt": "status", "running": "status", "open": "status",
            "plan": "roadmap", "changes": "brief", "decide": "brief",
            "map_tree": "map", "map_roles": "map", "map_terms": "map", "start": "rules"}
LATER = {"map_roles", "map_terms", "running", "open"}     # check.py LATER


def md_files(root):
    out = []
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith(".claude"))
        for n in sorted(names):
            if n.endswith(".md"):
                out.append(os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/"))
    return out


def outline(path):
    """(header line, [(line, level, text)]) of a markdown file: its first quote line and its headings."""
    heads, quote, fence = [], None, False
    with open(path, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if line.startswith("```"):
                fence = not fence
                continue
            if fence:
                continue
            if quote is None and line.startswith(">"):
                quote = line.lstrip("> ").strip()
            m = HEAD.match(line)
            if m:
                heads.append((i, len(m.group(1)), m.group(2).strip()))
    return quote, heads


def is_old(rel):
    return any(p.lower() in OLD_PARTS or p.lower().startswith(OLD_PARTS) for p in rel.split("/")[:-1])


def find_heading(heads, key):
    """The chapter name to write for key: the default when a heading holds it, else the heading
    holding most of the key's words (its text without the leading number), else None."""
    default, words = HEADINGS[key]
    for _, _, text in heads:
        if default in text:
            return default, True
    best, score = None, 0
    for _, _, text in heads:
        s = sum(1 for w in words if w in text)
        if s > score:
            best, score = text, s
    if not best:
        return None, False
    name = re.sub(r"^[0-9]+(?:-[0-9]+)*\.?\s+", "", best).strip()
    return name, name in words            # a heading that is exactly one of the words is no guess ("## 지금")


def scan(root):
    root = os.path.realpath(root)
    files = md_files(root)
    found = {"root": root, "docs": {}, "alts": {}, "outlines": {}, "headings": {}, "guessed": {}}
    rules = "CLAUDE.md" if os.path.isfile(os.path.join(root, "CLAUDE.md")) else ("AGENTS.md" if os.path.isfile(os.path.join(root, "AGENTS.md")) else None)
    if rules:
        found["docs"]["rules"] = rules
    for role, (names, keys) in ROLES.items():
        cands = []
        for rel in files:
            base = os.path.basename(rel)
            if rel == rules:
                continue
            q, hs = outline(os.path.join(root, rel))
            hits = sum(1 for k in keys if any(HEADINGS[k][0] in t for _, _, t in hs))
            if base not in names and hits < 2:
                continue
            score = hits * 10 + (len(names) - names.index(base)) * 3 if base in names else hits * 10
            if is_old(rel):
                score -= 100
            if base == "DESIGN.md" and hits == 0:
                continue          # impeccable's design record has this name too
            cands.append((score, rel))
        cands.sort(key=lambda x: (-x[0], x[1]))
        if cands and cands[0][0] > -50:
            found["docs"][role] = cands[0][1]
        found["alts"][role] = [r for _, r in cands[1:4]]
    old_index = next((r for r in ("old/README.md", "archive/README.md") if r in files), None)
    if old_index:
        found["docs"]["old_index"] = old_index
    for role, rel in found["docs"].items():
        found["outlines"][rel] = outline(os.path.join(root, rel))
    for key in HEADINGS:
        rel = found["docs"].get(HEAD_DOC[key])
        if not rel:
            continue
        name, exact = find_heading(found["outlines"][rel][1], key)
        if name:
            found["headings"][key] = name
            found["guessed"][key] = not exact
    found["git"] = os.path.isdir(os.path.join(root, ".git")) or os.system(f"git -C '{root}' rev-parse >/dev/null 2>&1") == 0
    found["check"] = ["python3", "tools/doc_check.py"] if os.path.isfile(os.path.join(root, "tools", "doc_check.py")) else None
    found["locked"] = locked_paths(root, found)
    tops = sorted({d.split("/")[0] if "/" in d else "." for k, d in found["docs"].items() if k != "rules"})
    found["search"] = ["."] if "." in tops or not tops else tops
    found["places"] = places(root, found)
    found["skip"] = [d + "/" for d in ("render", "renders", "dist", "build", "out", ".claude", "node_modules", "media", "assets/raw")
                     if os.path.isdir(os.path.join(root, d))]
    return found


def locked_paths(root, found):
    """[(path, why)] to propose: the rules file, the documents the board finds by name, the user's
    records, and the paths the rules file's "do not touch" chapter names (existing ones only)."""
    out, seen = [], set()

    def add(p, why):
        if p and p not in seen and os.path.lexists(os.path.join(root, p.rstrip("/"))):
            seen.add(p)
            out.append((p, why))
    docs = found["docs"]
    add(docs.get("rules"), "규칙 문서라 세션마다 이 경로로 자동으로 읽힙니다")
    for k in ("brief", "map", "roadmap", "status"):
        add(docs.get(k), "기준 문서라 다른 문서와 도구가 이 이름으로 찾습니다")
    d = docs.get("directions")
    if d:
        folder = os.path.dirname(d)
        add(folder + "/" if folder and not is_old(d) and os.path.basename(folder) in ("record", "records", "기록") else d,
            "사용자 원문은 덧붙이기만 합니다")
    rel = docs.get("rules")
    if rel:
        _, heads = found["outlines"][rel]
        lines = open(os.path.join(root, rel), encoding="utf-8", errors="replace").read().split("\n")
        keep = ("건드리지 않", "손대지 않", "고치지 않")

        def paths(text, why):
            for p in re.findall(r"`([^`\s]+)`", text):
                if not p.startswith(("../", "/", "~")) and "*" not in p:
                    add(p, why)
        for n, (i, level, text) in enumerate(heads):      # a "do not touch" chapter
            if any(w in text for w in keep):
                end = next((j for j, lv, _ in heads[n + 1:] if lv <= level), len(lines) + 1)
                for line in lines[i:end - 1]:
                    paths(line, f"{rel}의 \"{text}\" 장")
        for line in lines:                                 # or a "건드리지 않는 것: `a/`" line (templates/CLAUDE.md)
            if any(w in line for w in keep) and not HEAD.match(line):
                paths(line, f"{rel}: {line.strip().lstrip('-* ').split(':')[0][:30]}")
    for p in ("old/", "archive/"):
        add(p, "옛 방향의 기록이라 고치지 않습니다")
    return out


def places(root, found):
    """[roles] and records: the folders this project keeps records, reports, old plans, user material
    and work in. User material also takes the rules file's "do not touch" folders; work takes the
    folders the roadmap's 쓸 파일 lines name (outside the documents' own folders)."""
    have = lambda *ps: [p for p in ps if os.path.isdir(os.path.join(root, p.rstrip("/")))]
    out = {"record": have("docs/record/", "record/", "docs/records/"),
           "report": have("docs/research/", "research/", "docs/reports/", "reports/"),
           "old": have("old/", "archive/"),
           "user": have("refs/", "refs/user/", "references/"),
           "data": have("data/", "logs/"), "work": []}
    rules = found["docs"].get("rules")
    known = [p for k in ("record", "report", "old", "user") for p in out[k]]
    for p, why in found["locked"]:
        if why.startswith(f"{rules}") and p.endswith("/") and not any(p.startswith(k) for k in known):
            out["user"].append(p)
    road = found["docs"].get("roadmap")
    docs_dirs = {os.path.dirname(v) + "/" for v in found["docs"].values() if "/" in v}
    if road:
        for line in open(os.path.join(root, road), encoding="utf-8", errors="replace"):
            if re.match(r"^\s*-\s*쓸 파일:", line):
                for p in re.findall(r"`([^`\s]+/)`", line):
                    if (os.path.isdir(os.path.join(root, p)) and p not in out["work"] and not p.startswith(("../", "/"))
                            and not any(p.startswith(d) for d in docs_dirs) and not any(p.startswith(k) for k in known + out["user"])):
                        out["work"].append(p)
    return out


def free_port(name):
    """A port of this project's own (8791-8889 by its name, so two boards rarely meet), moved on when busy now."""
    start = 8791 + zlib.crc32(name.encode()) % 99
    for port in list(range(start, 8890)) + list(range(8791, start)):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def q(x):
    """A TOML basic string (JSON's escapes are TOML's)."""
    return json.dumps(x, ensure_ascii=False)


def toml_list(xs):
    return "[" + ", ".join(q(x) for x in xs) + "]"


def draft(found, dest, name, port):
    root_rel = os.path.relpath(found["root"], os.path.join(found["root"], dest)).replace(os.sep, "/")
    d = found["docs"]
    pl = found["places"]
    records = pl["record"] + pl["report"] + pl["old"]
    L = ["# 현황판 설정 (README.md 3장)",
         "# 이 프로젝트에서 문서가 어디 있는지, 무엇을 잠그는지만 적습니다. 사실(단계, 세션, 결정)은 문서에만 있습니다.",
         "# 경로는 모두 프로젝트 맨 위(root) 기준입니다. setup_board.py가 장 목록으로 쓴 초안이며, '# 짐작' 줄은 확인할 것.",
         "", f"name = {q(name)}", f"root = {q(root_rel)}            # 이 파일에서 프로젝트 맨 위까지", f"port = {port}", "", "[docs]"]
    for key, why in (("status", ""), ("roadmap", ""), ("brief", "   # 기획서: 판, 정할 것, 바뀐 결정"), ("directions", "   # 사용자 원문"),
                     ("map", "   # 폴더 지도, 파일의 역할, 용어"), ("old_index", "   # 옛 방향 표"),
                     ("rules", "   # 규칙 파일: 세션을 열면 저절로 읽힘. 세션 시작 장이 \"읽는 길\"이 됨")):
        L.append(f'{key} = {q(d[key])}{why}' if key in d else f'# {key} = ""   # 이 프로젝트에는 없음 (그 화면은 비어 있음)')
    L += [f'search = {toml_list(found["search"])}   # "BRIEF.md"처럼 이름만 적은 문서를 찾는 곳 (앞의 것이 먼저, "."은 프로젝트 전체)', "",
          "[headings]                # 문서 속 장 이름 (장 번호 없이 제목의 일부)"]
    for key, (default, _) in HEADINGS.items():
        doc = d.get(HEAD_DOC[key])
        if key in found["headings"]:
            mark = "   # 짐작: 기본 이름이 없어 비슷한 장을 고름" if found["guessed"][key] else ""
            L.append(f'{key} = {q(found["headings"][key])}{mark}')
        elif doc:
            later = " (나중에 생기면 저절로 읽음)" if key in LATER else ""
            L.append(f'# {key} = {q(default)}   # {doc}에 이 장이 없음{later}')
    L += ["", "[check]"]
    L.append(f"command = {toml_list(found['check'])}" if found["check"] else "# command = [\"python3\", \"tools/doc_check.py\"]   # 문서 검사 도구가 없음")
    L += ["", "[roles]                   # MAP에 역할 표가 없을 때 역할을 짐작하는 곳 (README.md 3장)"]
    for k, v in pl.items():
        L.append(f"{k} = {toml_list(v)}")
    L += ["", "[files]", 'hidden = [".git", ".DS_Store", "__pycache__", "node_modules"]',
          f"trash = {q(dest + '/.trash')}", f"state = {q(dest + '/.state')}   # 사용자의 \"파악함\" 표시 (이 컴퓨터에만, git에 담지 않음)",
          "# 가리키는 곳을 찾을 때 \"기록\"으로 따로 묶는 곳: 고치지 않는 문서라 경로가 옛 그대로여도 됨",
          f"records = {toml_list(records)}",
          "# 찾지 않는 곳: 크거나 도구가 만든 것",
          f"skip_search = {toml_list(found['skip'] + [dest + '/.trash/', dest + '/.taste-skill/', dest + '/static/fonts/'])}"]
    for p, why in found["locked"] + [(dest + "/", "현황판 자기 자신입니다")]:
        L += ["", "[[files.locked]]", f"path = {q(p)}", f"why = {q(why)}"]
    text = "\n".join(L) + "\n"
    tomllib.loads(text)           # the draft must be valid TOML before anyone reads it
    return text


def report(found, text):
    d = found["docs"]
    print(f"프로젝트: {found['root']}")
    print(f"git: {'있음' if found['git'] else '없음 (계획 변화·커밋 연결·바뀐 내용 화면이 비어 있음)'}")
    print("\n문서 (역할 → 파일, 다른 후보)")
    for role in ("rules", *ROLES, "old_index"):
        alts = found["alts"].get(role) or []
        print(f"  {role:10} {d.get(role, '없음')}" + (f"   다른 후보: {', '.join(alts)}" if alts else ""))
    print("\n장 목록 (본문은 읽지 않음)")
    for role, rel in d.items():
        quote, heads = found["outlines"][rel]
        print(f"  {rel}" + (f"   머리: {quote[:90]}" if quote else ""))
        for i, level, t in heads:
            if level <= 3:
                print(f"    {i:5} {'  ' * (level - 1)}{t[:90]}")
    print("\nboard.toml 초안\n" + "-" * 40 + "\n" + text + "-" * 40)


def short(found, text):
    d = found["docs"]
    print(f"프로젝트: {found['root']}")
    print("문서: " + ", ".join(f"{k} {v}" for k, v in d.items()) + (" · 없음: " + ", ".join(k for k in ("status", "roadmap", "brief", "map", "directions", "old_index") if k not in d) if len(d) < 7 else ""))
    print(f"포트: {re.search(r'port = (\d+)', text).group(1)} · 초안은 scan과 같음 (board.toml에 씀)")


def install(found, dest, text):
    target = os.path.join(found["root"], dest)
    if os.path.lexists(target):
        sys.exit(f"{target}가 이미 있습니다. 덮어쓰지 않습니다. 다른 --dest를 쓰거나, 사용자에게 물은 뒤 직접 치우세요.")
    shutil.copytree(ASSET, target, ignore=shutil.ignore_patterns("__pycache__", "board.toml", ".trash", ".state"))
    with open(os.path.join(target, "board.toml"), "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\n복사함: {ASSET} → {target}")
    print(f"다음: python3 {dest}/check.py --docs   (0 failed가 될 때까지 board.toml의 장 이름과 경로를 맞춤)")
    print(f"켜기: python3 {dest}/server.py   → http://127.0.0.1:{re.search(r'port = (\d+)', text).group(1)}")


def role_prompt(project, dest):
    """The files screen's role-table prompt (static/files.js rolesPrompt), built
    from the installed board, plus registering the board itself in the map."""
    board = os.path.join(os.path.realpath(project), dest)
    if not os.path.isfile(os.path.join(board, "board.toml")):
        sys.exit(f"{board}/board.toml이 없습니다. 먼저 install을 하세요.")
    sys.path.insert(0, board)
    import server                      # noqa: E402  (the installed board's own code)
    from board import index
    from board.config import Config
    cfg = Config(os.path.join(board, "board.toml"))
    ix = index.build(cfg, server.version(cfg))
    st = server.state(cfg)
    m = cfg.docs.get("map") or ("docs/MAP.md" if os.path.isdir(cfg.abs("docs")) else "MAP.md")
    name, rules = os.path.basename(m), cfg.docs.get("rules", "CLAUDE.md")
    roles, tree = cfg.head("map_roles", "파일의 역할"), cfg.head("map_tree", "폴더 지도")
    items = ix["undescribed"]
    n = 1
    out = [f"{cfg.name}의 기획 책임 세션(문서를 맡아 고치는 세션)이다. {m}를 파일의 역할을 적는 한 곳으로 만들어 줘."]
    if "map" not in cfg.docs:
        out.append(f"0. 아직 {m}가 없다. 먼저 만들어 {rules}에 등록하고(문서 표가 있으면 그 표에, 없으면 한 줄로), "
                   f"현황판 설정 {dest}/board.toml에서 [docs] map에 그 경로를 적고 [[files.locked]]에도 더해 줘(현황판에서 옮기거나 지우지 않게). board.toml은 이 두 곳만 고쳐.")
    if not ix["map_roles"]:
        out.append(f"{n}. {name}에 \"{roles}\" 장을 만들어, | 경로 | 역할 | 바뀌는 법 | 누가 고치나 | 무게 | 표로 적어 줘. 경로는 `파일`이나 `폴더/`, "
                   f"무게는 지휘·작업·참고·기계 중 하나. 역할과 누가 고치나는 {rules}에 적힌 규칙(있으면 문서 표, 세션 역할, 건드리지 않는 것)에 맞춰 적고, "
                   "현황판이 지금 짐작한 역할(현황판 파일 화면의 역할 판)은 참고만 해.")
        n += 1
    if items:
        out.append(f"{n}. {name}의 \"{tree}\" 장 나무(없으면 만들어서)에 아래 {len(items)}개 파일의 한 줄 설명을 더해 줘. "
                   "파일을 열어 보고 쓰고, 모르는 것은 추측하지 말고 나에게 물어봐.\n" + "\n".join(f"   - {p}" for p in items))
        n += 1
    out.append(f"{n}. 새로 생긴 현황판 `{dest}/`도 나무에 한 줄로 등록하고(\"현황판: 문서와 git을 읽어 진행을 그림으로 보여 줌, 켜기 python3 {dest}/server.py\"), "
               f"역할 표에는 `{dest}/` | 현황판 | project-board 스킬로 세우고 바꿈 | 현황판을 맡은 세션 | 기계 로 적어 줘. {rules}에도 한 줄(켜는 법)을 더할지는 나에게 물어봐.")
    check = " ".join(cfg.check_cmd) + "와 " if cfg.check_cmd else ""
    out.append(f"고친 뒤 {check}python3 {dest}/check.py --docs가 0 failed인지 확인하고, 바꾼 곳을 짧게 보고해 줘.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="현황판을 second-brain 프로젝트에 세움 (SKILL.md)")
    ap.add_argument("what", choices=["scan", "install", "prompt"])
    ap.add_argument("project")
    ap.add_argument("--dest", default="tools/board", help="현황판 폴더 (프로젝트 맨 위 기준, 기본 tools/board)")
    ap.add_argument("--name", help="현황판에 보일 프로젝트 이름 (기본: 폴더 이름)")
    ap.add_argument("--port", type=int, help="포트 (기본: 8791부터 비어 있는 것)")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.project):
        sys.exit(f"폴더가 아닙니다: {a.project}")
    if sys.version_info < (3, 11):
        sys.exit("파이썬 3.11 이상이 필요합니다 (tomllib)")
    dest = a.dest.strip("/")
    if a.what == "prompt":
        print(role_prompt(a.project, dest))
        return 0
    found = scan(a.project)
    name = a.name or os.path.basename(found["root"])
    text = draft(found, dest, name, a.port or free_port(name))
    if a.what == "install":
        short(found, text)
        install(found, dest, text)
    else:
        report(found, text)
        print("포트는 이 프로젝트 이름으로 정해지고, install 때 그 포트가 쓰이고 있으면 다음 것으로 넘어갑니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
