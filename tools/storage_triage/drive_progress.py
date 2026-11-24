#!/usr/bin/env python3
"""Google Drive 업로드 진행 보기. 읽기만 한다(Drive 데이터베이스를 읽기 전용으로 열고, 폴더를 세기만 한다).
쓰는 법: python3 drive_progress.py [폴더 이름, 기본 NEXT_15]   종료: Ctrl+C
"""
import os, sqlite3, subprocess, sys, time
from collections import deque

NAME = sys.argv[1] if len(sys.argv) > 1 else "NEXT_15"
HOME = os.path.expanduser("~")
ROOT = f"{HOME}/Library/CloudStorage/GoogleDrive-dohagi0558@gmail.com/내 드라이브/{NAME}"
DB = f"{HOME}/Library/Application Support/Google/DriveFS/102490364884587586681/metadata_sqlite_db"

def db_stats():
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)
        items = c.execute("select count(*) from items").fetchone()[0]
        ops = c.execute("select count(*) from operations").fetchone()[0]
        c.close()
        return items, ops
    except Exception:
        return None, None

def count(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try: return int(r.stdout.strip())
    except Exception: return 0

def free_gb():
    st = os.statvfs("/System/Volumes/Data")
    return st.f_bavail * st.f_frsize / 1e9

def bar(frac, w=40):
    frac = max(0.0, min(1.0, frac)); n = int(frac * w)
    return "█" * n + "░" * (w - n)

hist = deque(maxlen=12)       # (시각, 항목 수) 최근 몇 분
local_total = local_only = 0
last_count = 0
base_items = None
peak = 0
while True:
    now = time.time()
    items, ops = db_stats()
    if now - last_count > 30:  # 폴더 세기는 무거워서 30초마다
        local_total = count(f'find "{ROOT}" 2>/dev/null | wc -l')
        local_only = count(f'find "{ROOT}" -type f -flags +dataless 2>/dev/null | wc -l')
        last_count = now
    if items is not None:
        if base_items is None: base_items = items
        hist.append((now, items))
    rate = 0.0
    if len(hist) >= 2 and hist[-1][0] > hist[0][0]:
        rate = (hist[-1][1] - hist[0][1]) / (hist[-1][0] - hist[0][0]) * 60  # 분당
    print("\033[2J\033[H", end="")
    print(f"Google Drive 업로드 진행 · {NAME} · {time.strftime('%H:%M:%S')}\n")
    if items is None:
        print("Drive 데이터베이스를 읽지 못했습니다. Drive 앱이 켜져 있는지 보세요.")
    else:
        # Drive는 폴더별 진행률을 주지 않아서, 대기 작업 수가 줄어 0이 되는 것을 끝 신호로 본다
        peak = max(peak, ops or 0)
        frac = 1 - (ops / peak) if peak else 1
        print(f"  대기 작업 해소  {bar(frac)} {frac*100:5.1f}%   (남은 대기 {ops:,}건 / 이번 최대 {peak:,}건)")
        print(f"  Mac의 {NAME} 안 항목     {local_total:>9,} 개")
        print(f"  Drive가 알고 있는 항목   {items:>9,} 개  (Drive 전체)")
        print(f"  항목 증가 속도           {rate:>9,.0f} 개/분")
        if ops == 0: print("\n  ✔ 대기 작업이 0건입니다. 동기화가 끝났습니다.")
        print(f"\n  클라우드에만 있는 파일   {local_only:>9,} 개  (이 수가 늘어야 Mac 용량이 줄어듭니다)")
    print(f"  Mac 빈 공간              {free_gb():>9.1f} GB")
    print("\n※ 진행률은 대기 작업 수로 본 추정입니다. 종료: Ctrl+C")
    sys.stdout.flush()
    time.sleep(5)
