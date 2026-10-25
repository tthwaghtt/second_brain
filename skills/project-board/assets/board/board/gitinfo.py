"""Read-only git calls. GIT_OPTIONAL_LOCKS=0 keeps "git status" from taking
index.lock, so the board never blocks another session's commit. Paths come
back relative to the project root (the repository root may be a parent)."""
import os
import subprocess

ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0", LC_ALL="C.UTF-8", GIT_PAGER="cat")


def run(cfg, *args, text=True):
    try:
        p = subprocess.run(["git", *args], cwd=cfg.root, env=ENV, capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace") if text else p.stdout


_prefix = {}


def prefix(cfg):
    """The project's path inside the repository ("PORTFOLIO/"), or ""."""
    if cfg.root not in _prefix:
        out = run(cfg, "rev-parse", "--show-prefix")
        _prefix[cfg.root] = (out or "").strip()
    return _prefix[cfg.root]


def rel(cfg, path):
    p = prefix(cfg)
    return path[len(p):] if p and path.startswith(p) else path


def git_dir(cfg):
    out = run(cfg, "rev-parse", "--absolute-git-dir")
    return out.strip() if out else None


def head(cfg):
    out = run(cfg, "rev-parse", "--short", "HEAD")
    return out.strip() if out else None


def status(cfg):
    """Changes not yet committed, as {path: code}: M changed, A added,
    D deleted, R moved (with "from"), ? new, ! ignored (folders)."""
    raw = run(cfg, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching", "--", ".", text=False)
    out = {}
    if raw is None:
        return None
    parts = raw.decode("utf-8", "replace").split("\0")
    i = 0
    while i < len(parts):
        e = parts[i]
        i += 1
        if len(e) < 4:
            continue
        xy, path = e[:2], rel(cfg, e[3:])
        item = {"xy": xy, "staged": xy[0] not in " ?!"}
        if "R" in xy or "C" in xy:
            item["from"] = rel(cfg, parts[i])
            i += 1
            code = "R"
        elif xy == "??":
            code = "?"
        elif xy == "!!":
            code = "!"
        elif "D" in xy:
            code = "D"
        elif "A" in xy:
            code = "A"
        else:
            code = "M"
        item["code"] = code
        out[path] = item
    return out


def tracked(cfg):
    raw = run(cfg, "ls-files", "-z", "--", ".", text=False)
    if raw is None:
        return set()
    return {rel(cfg, p) for p in raw.decode("utf-8", "replace").split("\0") if p}


def is_tracked(cfg, path):
    return run(cfg, "ls-files", "--error-unmatch", "--", path) is not None


def log(cfg, *paths, n=None):
    """Commits touching paths (default: the whole project), newest first."""
    args = ["log", "--format=%H%x1f%h%x1f%aI%x1f%s"]
    if n:
        args.append(f"-n{n}")
    out = run(cfg, *args, "--", *(paths or (".",)))
    rows = []
    for line in (out or "").splitlines():
        f = line.split("\x1f")
        if len(f) == 4:
            rows.append({"hash": f[0], "short": f[1], "when": f[2], "subject": f[3]})
    return rows


def show(cfg, rev, path):
    """A file's text at a commit, or None when it did not exist there."""
    return run(cfg, "show", f"{rev}:./{path}")


def changed_files(cfg, rev):
    out = run(cfg, "show", "--format=", "--name-status", "-M", rev, "--", ".")
    rows = []
    for line in (out or "").splitlines():
        f = line.split("\t")
        if len(f) >= 2:
            rows.append({"code": f[0][0], "path": rel(cfg, f[-1]), "from": rel(cfg, f[1]) if len(f) == 3 else None})
    return rows
