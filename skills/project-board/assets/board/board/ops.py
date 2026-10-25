"""Rename, move, delete and restore, inside the project only.

- A path must resolve inside the project root: absolute paths, "..",
  symbolic links and anything under a locked path (board.toml) are refused.
- Moves use os.rename, not "git mv": git mv stages the change, and another
  session's commit of its own chosen files could carry it half-done. Git
  sees the rename when the change is committed.
- Delete moves the item into the board's trash with a meta.json (where it
  was, size, hash, git state), and restore puts it back.
- The caller sends the file's mtime and size as it last saw them; if the file
  changed since (another session wrote it), the operation is refused.
- One operation at a time."""
import hashlib
import json
import os
import re
import secrets
import threading
import time
import unicodedata

from . import gitinfo

LOCK = threading.Lock()
TRASH_ID = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{6}$")


class OpError(Exception):
    def __init__(self, status, msg, **extra):
        super().__init__(msg)
        self.status, self.msg, self.extra = status, msg, extra


def clean(rel):
    if not isinstance(rel, str) or "\0" in rel:
        raise OpError(400, "경로가 올바르지 않습니다")
    rel = unicodedata.normalize("NFC", rel).strip()
    if os.path.isabs(rel) or rel.startswith("~"):
        raise OpError(400, "경로가 올바르지 않습니다")
    rel = rel.rstrip("/")
    if not rel or any(p in ("", ".", "..") for p in rel.split("/")):
        raise OpError(400, "경로가 올바르지 않습니다")
    return rel


def resolve(cfg, rel, must_exist=True):
    """(rel, absolute path) for a path whose real parent lies in the project."""
    rel = clean(rel)
    parent = os.path.realpath(os.path.join(cfg.root, os.path.dirname(rel)))
    if parent != cfg.root and not parent.startswith(cfg.root + os.sep):
        raise OpError(403, "프로젝트 밖의 경로입니다")
    target = os.path.join(parent, os.path.basename(rel))
    if must_exist and not os.path.lexists(target):
        raise OpError(404, "없는 경로입니다. 화면을 새로 고쳐 주세요")
    if os.path.islink(target):
        raise OpError(403, "링크는 다루지 않습니다")
    return rel, target


def name_ok(name):
    if not isinstance(name, str):
        raise OpError(400, "이름이 올바르지 않습니다")
    name = unicodedata.normalize("NFC", name)
    if (not name.strip() or name != name.strip() or "/" in name or "\0" in name
            or name in (".", "..") or len(name.encode()) > 255):
        raise OpError(400, "이름에 쓸 수 없는 글자가 있거나 비었습니다")
    return name


def guard(cfg, rel, dest=False):
    why = cfg.lock_reason(rel, inside_only=dest)
    if why:
        raise OpError(403, f"잠긴 곳입니다: {why}")


def unchanged(target, expect):
    if not expect:
        raise OpError(400, "파일의 마지막 상태(수정 시각)를 함께 보내야 합니다")
    st = os.lstat(target)
    if int(expect.get("mtime_ns", -1)) != st.st_mtime_ns or (
            os.path.isfile(target) and "size" in expect and int(expect["size"]) != st.st_size):
        raise OpError(409, "그사이 다른 곳에서 바뀌었습니다. 새로 고친 뒤 다시 해 주세요")


def doc_clash(cfg, new_rel, old_rel):
    """Documents under the search folders are found by bare name (doc_section),
    so two of the same name there would make "BRIEF.md 2장" ambiguous. A
    search folder of "." is the whole project."""
    if not any(d.strip("/") in ("", ".") or new_rel.startswith(d.rstrip("/") + "/") for d in cfg.search):
        return
    base = os.path.basename(new_rel)
    for d in cfg.search:
        for dirpath, dirs, files in os.walk(cfg.abs(d)):
            dirs[:] = [x for x in dirs if x not in cfg.hidden]
            if base in files:
                rel = os.path.relpath(os.path.join(dirpath, base), cfg.root)
                if rel != old_rel:
                    raise OpError(409, f"{rel}과 이름이 같아집니다. 문서는 이름으로 찾기 때문에 같은 이름을 둘 수 없습니다")


def rename(cfg, rel, name, expect):
    with LOCK:
        rel, src = resolve(cfg, rel)
        guard(cfg, rel)
        unchanged(src, expect)
        name = name_ok(name)
        new_rel = clean(f"{os.path.dirname(rel)}/{name}" if "/" in rel else name)
        if new_rel == rel:
            raise OpError(400, "이름이 그대로입니다")
        guard(cfg, new_rel, dest=True)
        dst = os.path.join(os.path.dirname(src), name)
        case_only = os.path.lexists(dst) and os.path.samefile(src, dst)
        if os.path.lexists(dst) and not case_only:
            raise OpError(409, "같은 이름이 이미 있습니다")
        doc_clash(cfg, new_rel, rel)
        if case_only:
            tmp = f"{src}.board-{secrets.token_hex(3)}"
            os.rename(src, tmp)
            os.rename(tmp, dst)
        else:
            os.rename(src, dst)
        return {"op": "rename", "from": rel, "to": new_rel}


def move(cfg, rel, dest_dir, expect):
    with LOCK:
        rel, src = resolve(cfg, rel)
        guard(cfg, rel)
        unchanged(src, expect)
        dest_rel = "" if dest_dir in ("", "/", ".", None) else clean(dest_dir)
        dest_abs = cfg.root if not dest_rel else resolve(cfg, dest_rel)[1]
        if not os.path.isdir(dest_abs):
            raise OpError(400, "옮길 곳이 폴더가 아닙니다")
        if dest_rel:
            guard(cfg, dest_rel, dest=True)
        if dest_abs == src or dest_abs.startswith(src + os.sep):
            raise OpError(400, "폴더를 자기 안으로 옮길 수 없습니다")
        new_rel = f"{dest_rel}/{os.path.basename(rel)}" if dest_rel else os.path.basename(rel)
        if new_rel == rel:
            raise OpError(400, "지금 있는 곳입니다")
        dst = os.path.join(dest_abs, os.path.basename(src))
        if os.path.lexists(dst):
            raise OpError(409, "옮길 곳에 같은 이름이 이미 있습니다")
        doc_clash(cfg, new_rel, rel)
        os.rename(src, dst)
        return {"op": "move", "from": rel, "to": new_rel}


def measure(path):
    if os.path.isfile(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return os.path.getsize(path), 1, h.hexdigest()
    size = files = 0
    for d, _, names in os.walk(path):
        for n in names:
            p = os.path.join(d, n)
            if not os.path.islink(p):
                size += os.path.getsize(p)
                files += 1
    return size, files, None


def delete(cfg, rel, expect):
    with LOCK:
        rel, src = resolve(cfg, rel)
        guard(cfg, rel)
        unchanged(src, expect)
        size, count, sha = measure(src)
        tracked = bool((gitinfo.run(cfg, "ls-files", "--", rel) or "").strip())
        tid = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + secrets.token_hex(3)
        box = os.path.join(cfg.abs(cfg.trash), tid)
        os.makedirs(os.path.join(box, "item"))
        meta = {"id": tid, "path": rel, "kind": "dir" if os.path.isdir(src) else "file",
                "deleted_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "size": size, "files": count,
                "sha256": sha, "tracked": tracked, "head": gitinfo.head(cfg)}
        with open(os.path.join(box, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
        try:
            os.rename(src, os.path.join(box, "item", os.path.basename(src)))
        except OSError:
            os.remove(os.path.join(box, "meta.json"))
            os.rmdir(os.path.join(box, "item"))
            os.rmdir(box)
            raise
        return {"op": "delete", "from": rel, "trash": tid, **meta}


def trash(cfg):
    root = cfg.abs(cfg.trash)
    out = []
    for tid in sorted(os.listdir(root), reverse=True) if os.path.isdir(root) else []:
        mp = os.path.join(root, tid, "meta.json")
        if TRASH_ID.match(tid) and os.path.isfile(mp):
            with open(mp, encoding="utf-8") as f:
                m = json.load(f)
            m["present"] = os.path.lexists(os.path.join(root, tid, "item", os.path.basename(m["path"])))
            m["occupied"] = os.path.lexists(cfg.abs(m["path"]))
            out.append(m)
    return out


def restore(cfg, tid, name=None):
    with LOCK:
        if not isinstance(tid, str) or not TRASH_ID.match(tid):
            raise OpError(400, "휴지통 항목이 올바르지 않습니다")
        box = os.path.join(cfg.abs(cfg.trash), tid)
        with open(os.path.join(box, "meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
        orig = clean(meta["path"])
        new_rel = orig if not name else clean(
            f"{os.path.dirname(orig)}/{name_ok(name)}" if "/" in orig else name_ok(name))
        guard(cfg, new_rel, dest=True)
        parent_rel, made = os.path.dirname(new_rel), False
        if parent_rel and not os.path.isdir(cfg.abs(parent_rel)):
            resolve(cfg, parent_rel, must_exist=False)      # the folder it was in is gone: remake it, inside only
            os.makedirs(cfg.abs(parent_rel))
            made = True
        new_rel, target = resolve(cfg, new_rel, must_exist=False)
        if os.path.lexists(target):
            raise OpError(409, "그 자리에 같은 이름이 있습니다. 새 이름으로 되살릴 수 있습니다", conflict=True, path=new_rel)
        item = os.path.join(box, "item", os.path.basename(orig))
        os.rename(item, target)
        sha_ok = None
        if meta.get("sha256"):
            sha_ok = measure(target)[2] == meta["sha256"]
        os.remove(os.path.join(box, "meta.json"))
        os.rmdir(os.path.join(box, "item"))
        os.rmdir(box)
        return {"op": "restore", "to": new_rel, "from": f"{cfg.trash}/{tid}", "sha_ok": sha_ok, "made_folder": made}
