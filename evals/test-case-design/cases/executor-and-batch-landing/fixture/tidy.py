#!/usr/bin/env python3
"""临时文件整理：列候选、删候选。"""
import sys
from pathlib import Path

SUFFIXES = (".tmp", ".bak")


def candidates(root):
    return sorted(p for p in Path(root).rglob("*") if p.suffix in SUFFIXES)


def main(argv):
    if len(argv) != 3 or argv[1] not in ("--list", "--clean"):
        print("用法：tidy.py --list|--clean <目录>", file=sys.stderr)
        return 2
    root = Path(argv[2])
    if not root.is_dir():
        print("不是有效目录：%s" % root, file=sys.stderr)
        return 1
    found = candidates(root)
    if argv[1] == "--list":
        for p in found:
            print(p)
    else:
        for p in found:
            p.unlink()
        print("删了 %d 个" % len(found))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
