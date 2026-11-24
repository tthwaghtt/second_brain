#!/usr/bin/env python3
"""저장공간 분류표 만들기. 읽기만 한다. 파일을 옮기거나 지우지 않는다.
쓰는 법: python3 scan.py   → out/분류표_날짜.md 와 out/분류표_날짜.csv 를 만든다.
칸: 맥(최근 쓴 것) / 클라우드 후보(오래 안 건드린 것) / 재생성(건드리지 않음) / 확인 필요(앱 데이터) / 건드리지 않음
"""
import csv, json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
HOME = Path.home()
exp = lambda p: Path(os.path.expanduser(p))

def size_mb(p):
    r = subprocess.run(["du", "-sk", str(p)], capture_output=True, text=True)
    try: return int(r.stdout.split()[0]) / 1024
    except Exception: return 0.0

def has_recent(p, days):
    # 최근 days일 안에 바뀐 파일이 하나라도 있으면 True
    if p.is_file(): return (time.time() - p.stat().st_mtime) < days * 86400
    r = subprocess.run(["find", str(p), "-type", "f", "-mtime", f"-{days}", "-print", "-quit"],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())

def last_mtime(p):
    try:
        if p.is_file(): return p.stat().st_mtime
        r = subprocess.run(f'find "{p}" -type f -exec stat -f %m {{}} + 2>/dev/null | sort -n | tail -1',
                           shell=True, capture_output=True, text=True)
        return float(r.stdout.strip() or p.stat().st_mtime)
    except Exception: return 0.0

def classify(p, app_roots):
    n = p.name
    if n in CFG["never_touch_names"]: return "건드리지 않음", "보호 목록"
    if n in CFG["regenerable_names"]: return "재생성", "다시 만들어지는 것(도하 결정: 지우지 않음)"
    if p.parent in app_roots: return "확인 필요", "앱 데이터. 앱을 닫고 앱 안에서 정리"
    if has_recent(p, CFG["old_days"]): return "맥", f"{CFG['old_days']}일 안에 바뀜"
    return "클라우드 후보", f"{CFG['old_days']}일 넘게 안 바뀜"

def main():
    app_roots = {exp(r) for r in CFG["app_data_roots"]}
    targets = []
    if CFG["scan_home_children"]:
        targets += [c for c in HOME.iterdir() if c.name not in ("Library",)]
    for r in CFG["scan_children_of"]:
        rp = exp(r)
        if rp.exists(): targets += [c for c in rp.iterdir() if not c.name.startswith(".DS_Store")]
    seen, rows = set(), []
    for p in targets:
        if p in seen or p.is_symlink(): continue
        seen.add(p)
        mb = size_mb(p)
        if mb < CFG["min_size_mb"]: continue
        cat, why = classify(p, app_roots)
        lm = last_mtime(p)
        rows.append([cat, round(mb), time.strftime("%Y-%m-%d", time.localtime(lm)) if lm else "?", str(p).replace(str(HOME), "~"), why])
    rows.sort(key=lambda r: (r[0], -r[1]))
    out = HERE / "out"; out.mkdir(exist_ok=True)
    d = time.strftime("%Y-%m-%d")
    with open(out / f"분류표_{d}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["칸", "MB", "마지막 변경", "경로", "이유"]); w.writerows(rows)
    with open(out / f"분류표_{d}.md", "w") as f:
        f.write(f"# 저장공간 분류표 {d}\n\n읽기만 했고 아무것도 옮기거나 지우지 않았습니다.\n\n")
        for cat in ["클라우드 후보", "확인 필요", "맥", "재생성", "건드리지 않음"]:
            sub = [r for r in rows if r[0] == cat]
            if not sub: continue
            f.write(f"## {cat} ({sum(r[1] for r in sub)/1024:.1f} GB)\n\n| MB | 마지막 변경 | 경로 | 이유 |\n|---|---|---|---|\n")
            for r in sub: f.write(f"| {r[1]} | {r[2]} | {r[3]} | {r[4]} |\n")
            f.write("\n")
    print(out / f"분류표_{d}.md")

if __name__ == "__main__": main()
