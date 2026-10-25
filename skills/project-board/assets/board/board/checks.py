"""The project's own document check (board.toml [check] command), its English
lines put into Korean sentences. The raw line is kept beside each one."""
import re
import subprocess
import time

# doc_check's message shapes (tools/doc_check.py) → Korean
SHAPES = [
    (r"^no chapter (\S+) in (\S+)$", lambda m: f"{m[2]}에 {m[1]}장이 없습니다"),
    (r'^no chapter "(.+)" in (\S+)$', lambda m: f'{m[2]}에 "{m[1]}" 장이 없습니다'),
    (r"^missing file (\S+)$", lambda m: f"없는 파일을 가리킵니다: {m[1]}"),
    (r"^stale wording \((.+?)\): (.*)$", lambda m: f"낡은 말이 남았습니다({m[1]}): {m[2]}"),
    (r"^the start prompt has no '> 작성 <date>' line$", lambda m: "시작 프롬프트에 '작성 날짜' 줄이 없습니다"),
    (r"^the start prompt has no fenced prompt", lambda m: "시작 프롬프트 칸이 비었습니다"),
    (r"^the prompt does not name (\S+)$", lambda m: f"시작 프롬프트에 {m[1]}이 없습니다"),
    (r"^'★ 지금' does not name the prompt's next session (\S+)$", lambda m: f"'★ 지금'이 다음 세션 {m[1]}을 말하지 않습니다"),
    (r"^the prompt \((.+?)\) is older than the status \((.+?)\)$", lambda m: f"시작 프롬프트({m[1]})가 상태({m[2]})보다 오래됐습니다"),
    (r"^no heading for session (\S+)$", lambda m: f"{m[1]} 세션의 머리가 없습니다"),
    (r"^holds a start prompt \(only STATUS\.md may\)$", lambda m: "시작 프롬프트는 STATUS.md에만 둡니다"),
    (r"^(\d+) lines, more than its own limit of (\d+)$", lambda m: f"{m[1]}줄로, 한도 {m[2]}줄을 넘었습니다"),
    (r"^is older than (\d+) source file", lambda m: f"코드 {m[1]}개보다 오래됐습니다"),
]
_cache = {}


def ko(msg):
    for rx, fn in SHAPES:
        m = re.search(rx, msg)
        if m:
            return fn(m)
    return None


def parse(text):
    items, summary = [], None
    for line in text.splitlines():
        if line.startswith("! "):
            body = line[2:]
            m = re.match(r"^([^:\s]+?)(?::(\d+))?: (.*)$", body)
            f, n, msg = (m.group(1), int(m.group(2)) if m.group(2) else None, m.group(3)) if m else (None, None, body)
            items.append({"file": f, "line": n, "ko": ko(msg) or ko(body), "raw": body})
        s = re.match(r"^\S+: (\d+) problem\(s\) in (\d+) documents", line)
        if s:
            summary = {"problems": int(s.group(1)), "documents": int(s.group(2))}
    return items, summary


def run(cfg, key):
    """Runs the check at most once per project version."""
    if not cfg.check_cmd:
        return None
    if key in _cache:
        return _cache[key]
    try:
        p = subprocess.run(cfg.check_cmd, cwd=cfg.root, capture_output=True, timeout=60)
        text = p.stdout.decode("utf-8", "replace")
        items, summary = parse(text)
        out = {"items": items, "summary": summary, "ran": time.time(), "ok": summary is not None,
               "error": None if summary else (p.stderr.decode("utf-8", "replace")[-400:] or "결과 줄이 없습니다")}
    except (OSError, subprocess.TimeoutExpired) as e:
        out = {"items": [], "summary": None, "ran": time.time(), "ok": False, "error": str(e)}
    _cache.clear()
    _cache[key] = out
    return out
