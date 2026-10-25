"""Read-only lookups for the files screen: what changed in a file (git diff),
where a word appears in the project's text files, and the glossary."""
import os
import re

from . import gitinfo, md, refs

DIFF_LINES = 3000


def parse_diff(text):
    rows = []
    for line in text.splitlines():
        if line.startswith(("diff --git", "index ", "--- ", "+++ ", "similarity", "rename ", "new file", "deleted file")):
            continue
        kind = "hunk" if line.startswith("@@") else "add" if line.startswith("+") else "del" if line.startswith("-") else "same"
        rows.append({"k": kind, "t": line[1:] if kind != "hunk" else line})
        if len(rows) >= DIFF_LINES:
            break
    return rows


def diff(cfg, rel, status):
    """What changed: uncommitted changes against HEAD, the whole file for a new
    one, or, for a clean file, what its last commit changed."""
    st = (status or {}).get(rel)
    code = st["code"] if st else ""
    if code == "?":
        with open(cfg.abs(rel), encoding="utf-8", errors="replace") as f:
            lines = f.read(512 * 1024).splitlines()
        return {"path": rel, "kind": "new", "rows": [{"k": "add", "t": l} for l in lines[:DIFF_LINES]]}
    if code in ("M", "A", "R", "D"):
        args = ["diff", "HEAD", "-M", "--no-color", "--", rel] + ([st["from"]] if st.get("from") else [])
        return {"path": rel, "kind": "uncommitted", "rows": parse_diff(gitinfo.run(cfg, *args) or "")}
    last = gitinfo.log(cfg, rel, n=1)
    if not last:
        return {"path": rel, "kind": "none", "rows": []}
    out = gitinfo.run(cfg, "show", "--format=", "--no-color", "-M", last[0]["hash"], "--", rel) or ""
    return {"path": rel, "kind": "last_commit", "commit": {k: last[0][k] for k in ("short", "when")}, "rows": parse_diff(out)}


def search(cfg, q, limit=150):
    """Lines that contain q (case-insensitive) in the project's text files, each
    with the nearest markdown heading above it."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"q": q, "hits": [], "files": 0, "cut": False}
    needle = q.lower()
    hits, files = [], set()
    for rel in refs.files(cfg):
        try:
            with open(cfg.abs(rel), encoding="utf-8", errors="ignore") as f:
                lines = f.read().split("\n")
        except OSError:
            continue
        head = None
        for n, line in enumerate(lines, 1):
            if rel.endswith(".md"):
                m = md.HEAD.match(line)
                if m:
                    head = m.group(2).strip()
            if needle in line.lower():
                hits.append({"file": rel, "line": n, "text": line.strip()[:220], "heading": head})
                files.add(rel)
    board = cfg.board_dir + "/" if cfg.board_dir else None
    hits.sort(key=lambda x: (cfg.is_record(x["file"]), bool(board) and x["file"].startswith(board), x["file"], x["line"]))
    return {"q": q, "hits": hits[:limit], "files": len(files), "cut": len(hits) > limit}


# the method's and the board's own words (portable to any second-brain project); MAP.md's 용어 table adds this project's
WORDS = [
    ("기준 문서", "고쳐 쓰고 판과 날짜를 적는 문서. 기획서, 로드맵, 지도처럼 '지금 무엇이 맞는가'를 말함"),
    ("흐름 문서", "매번 통째로 덮어쓰는 문서. STATUS처럼 '지금 상태'만 담음"),
    ("기록", "끝에 덧붙이기만 하는 문서. 사용자 원문처럼 지우거나 고치지 않음"),
    ("보고서", "그날의 조사 결과로 얼린 문서. 틀린 곳은 머리에 정정 메모만 붙임"),
    ("판", "기준 문서의 버전. 크게 바뀌면 판 번호가 올라감 (예: 기획서 판 7)"),
    ("장", "문서 안의 번호 붙은 절 (예: BRIEF.md 2장). 세션은 필요한 장만 읽음"),
    ("세션", "Claude와 한 번 일하는 대화. S1, B3처럼 로드맵의 번호로 부름"),
    ("기획 책임 세션", "기획서·로드맵·상태 문서를 고칠 수 있는 세션 (규칙 파일의 세션 역할)"),
    ("일꾼 세션", "로드맵에서 맡은 '쓸 파일'만 만들고 고치는 세션. 커밋하지 않음"),
    ("전제", "그 세션을 시작하려면 먼저 끝나야 하는 세션. 노선도의 선로가 됨"),
    ("멈출 곳", "세션이 사용자의 '좋다'를 기다리며 멈추는 지점"),
    ("완성 기준", "세션이 끝났다고 말하려면 확인해야 할 것들"),
    ("정할 것", "사용자가 답해야 다음으로 갈 수 있는 질문"),
    ("커밋", "바뀐 파일을 git 기록에 한 덩어리로 남기는 것. 커밋 전의 변경은 '커밋 안 된 변경'"),
    ("스테이징", "커밋하려고 골라 둔 상태. 다른 세션이 커밋을 준비 중일 수 있음"),
    ("역할 판", "파일을 역할(규칙, 기준, 흐름, 기록, 보고서, 코드 …)별로 늘어놓은 현황판 화면"),
    ("추정", "MAP.md의 역할 표에 아직 없어서 현황판이 규칙으로 짐작한 역할"),
    ("무게", "지휘 문서 > 작업물 > 참고 자료 > 기계가 만든 것. 지휘할 때 볼 순서"),
    ("누가 고치나", "그 파일의 내용을 고칠 수 있는 쪽. 현황판의 자물쇠(옮기기·지우기를 막음)와는 다름"),
    ("현황판 자물쇠", "현황판에서 이름 바꾸기·옮기기·휴지통을 막은 파일. 내용을 고치는 권한과는 다름"),
    ("신선도", "이 문서가 가리키는 파일이 이 문서보다 나중에 바뀌었는지. 기록과 보고서는 얼린 것이라 따지지 않음"),
    ("파악함", "사용자가 '이 파일을 안다'고 표시한 것. 그 뒤 파일이 바뀌면 '다시 볼 것'이 됨"),
    ("가리키는 곳", "다른 파일이 이 파일의 경로나 이름을 적은 곳. 옮기면 옛 경로가 됨"),
    ("노선도", "로드맵의 세션을 역으로, 전제를 선로로 그린 그림"),
    ("읽는 길", "세션이 일을 시작하기 전에 읽는 문서의 순서 (규칙 파일의 '세션 시작' 장 + 그 세션의 '읽을 것')"),
]


def glossary(cfg):
    out = [{"word": w, "meaning": m, "source": "현황판"} for w, m in WORDS]
    lines = md.read(cfg.doc("map")) if cfg.doc("map") else None
    ch = md.chapter(lines, cfg.head("map_terms", "용어")) if lines else None
    for row in md.table(ch[3]) if ch else []:
        cells = list(row.values())
        if len(cells) >= 2:
            out.insert(0, {"word": md.strip(cells[0]), "meaning": md.strip(cells[1]), "source": os.path.basename(cfg.docs["map"])})
    return out
