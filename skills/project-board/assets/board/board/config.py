"""The board's settings: board.toml says where the project's documents are and
what is locked. Nothing in it is a fact about the project's state."""
import os
import tomllib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # tools/board

# where a project keeps each kind of file, for guessing roles when MAP.md has no role table
# (board.toml [roles]; these defaults are the second-brain layout the board was first built in)
ROLES = {"record": ["docs/record/"], "report": ["docs/research/"], "old": ["old/"], "user": ["refs/"],
         "tool": [".claude/"], "data": ["data/", "logs/"], "work": []}


class Config:
    def __init__(self, path=None, root=None):
        path = path or os.path.join(HERE, "board.toml")
        with open(path, "rb") as f:
            raw = tomllib.load(f)
        base = os.path.dirname(os.path.abspath(path))
        self.root = os.path.realpath(root or os.path.join(base, raw.get("root", ".")))
        self.name = raw.get("name") or os.path.basename(self.root)
        self.port = int(raw.get("port", 8790))
        docs = raw.get("docs", {})
        self.docs = {k: v for k, v in docs.items() if isinstance(v, str)}
        self.search = docs.get("search", ["docs"])
        self.headings = raw.get("headings", {})
        self.check_cmd = raw.get("check", {}).get("command")
        here = os.path.relpath(os.path.realpath(HERE), self.root)
        self.board_dir = "" if here.startswith("..") else here.replace(os.sep, "/")     # the board's own folder, "" when outside
        files = raw.get("files", {})
        self.hidden = set(files.get("hidden", [".git"]))
        self.trash = files.get("trash", f"{self.board_dir or 'tools/board'}/.trash").rstrip("/")
        self.state = files.get("state", f"{self.board_dir or 'tools/board'}/.state").rstrip("/")
        self.roles = {**ROLES, **{k: [v] if isinstance(v, str) else list(v) for k, v in raw.get("roles", {}).items()}}
        self.records = files.get("records", [])
        self.skip_search = files.get("skip_search", [])
        self.locked = [(x["path"], x["why"]) for x in files.get("locked", [])]
        self.facts = raw.get("facts", {})       # what the documents said when the board was set up (check.py)

    def abs(self, rel):
        return os.path.join(self.root, rel)

    def doc(self, key):
        """Absolute path of a named document (status, roadmap ...), or None."""
        rel = self.docs.get(key)
        return self.abs(rel) if rel else None

    def head(self, key, default=""):
        return self.headings.get(key, default)

    def lock_reason(self, rel, inside_only=False):
        """Why a project path may not be renamed, moved or deleted, or None.
        A locked folder locks everything in it, and a folder that holds a
        locked path is locked too, so moving a parent cannot carry one away.
        inside_only asks only whether rel lies in a locked place (a move's
        destination may hold locked paths; it just may not be one)."""
        rel = rel.strip("/")
        top = rel.split("/", 1)[0]
        if top in self.hidden or any(rel == d or rel.startswith(d + "/") for d in (self.trash, self.state)):
            return "현황판과 git이 쓰는 곳입니다"
        for p, why in self.locked:
            q = p.rstrip("/")
            if rel == q or rel.startswith(q + "/"):
                return why
        if not inside_only:
            held = [p for p, _ in self.locked if p.rstrip("/").startswith(rel + "/")]
            if held:
                return f"안에 잠긴 곳({', '.join(held)})이 있어 폴더째 다룰 수 없습니다"
        return None

    def is_record(self, rel):
        return any(rel.startswith(r) for r in self.records)

    def under(self, kind, rel):
        """Whether rel lies in one of the places board.toml [roles] gives for kind."""
        return any(rel.startswith(p) for p in self.roles.get(kind, []))
