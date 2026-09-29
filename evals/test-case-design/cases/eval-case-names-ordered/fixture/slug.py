#!/usr/bin/env python3
"""把一段标题转成文件名用的短名：小写、空格与下划线换成连字符、其余标点去掉。"""
import sys

KEEP = set("abcdefghijklmnopqrstuvwxyz0123456789-")


def slug(text):
    out = []
    for ch in text.lower():
        if ch in KEEP:
            out.append(ch)
        elif ch in " _":
            out.append("-")
    name = "".join(out)
    while "--" in name:
        name = name.replace("--", "-")
    return name.strip("-")


def main(argv):
    if len(argv) != 2:
        print("用法：python slug.py <标题>", file=sys.stderr)
        return 1
    print(slug(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
