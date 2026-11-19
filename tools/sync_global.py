#!/usr/bin/env python3
"""공통 규칙 파일의 원본(global/CLAUDE.md)을 ~/.claude/CLAUDE.md로 복사하거나, 둘이 같은지 본다.

  python3 tools/sync_global.py          # 원본을 복사한다(다르면 먼저 옛 복사본을 .bak으로 남긴다)
  python3 tools/sync_global.py --check  # 같으면 종료 코드 0, 다르거나 없으면 1

왜 링크가 아니라 복사본인가: 데스크톱 Cowork 세션은 링크로 된 ~/.claude/CLAUDE.md를 건너뛴다.
표준 라이브러리만 쓴다.
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "global", "CLAUDE.md")
DST = os.path.expanduser("~/.claude/CLAUDE.md")


def read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="복사하지 않고 같은지만 본다")
    ap.add_argument("--dst", default=DST, help="복사할 곳(시험용, 기본 ~/.claude/CLAUDE.md)")
    args = ap.parse_args(argv)
    src = read(SRC)
    if src is None:
        print("원본을 찾지 못했어요: %s" % SRC, file=sys.stderr)
        return 2
    dst_is_link = os.path.islink(args.dst)
    dst = read(args.dst)
    if args.check:
        if dst_is_link:
            print("다름: %s가 링크예요. 복사본이어야 해요(Cowork 세션이 링크를 건너뜀)." % args.dst)
            return 1
        if dst is None:
            print("없음: %s" % args.dst)
            return 1
        if dst != src:
            print("다름: %s가 원본과 달라요. python3 tools/sync_global.py 로 복사하세요." % args.dst)
            return 1
        print("같음: %s" % args.dst)
        return 0
    if dst == src and not dst_is_link:
        print("이미 같아요: %s" % args.dst)
        return 0
    os.makedirs(os.path.dirname(args.dst), exist_ok=True)
    if dst is not None and not dst_is_link:
        shutil.copy2(args.dst, args.dst + ".bak")
        print("옛 복사본을 남겼어요: %s.bak" % args.dst)
    if dst_is_link:
        os.remove(args.dst)
    shutil.copyfile(SRC, args.dst)
    print("복사했어요: %s → %s" % (SRC, args.dst))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
