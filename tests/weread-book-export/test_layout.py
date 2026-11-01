#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""layout.py 自己的测试。

    python -X utf8 tests/weread-book-export/test_layout.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
from layout import group_lines  # noqa: E402


def g(t, x, y, px=16):
    return {"t": t, "x": x, "y": y, "font": "%dpx serif" % px}


def main():
    bad = 0

    def eq(name, got, want):
        nonlocal bad
        if got != want:
            bad += 1
            print("[失败] %s" % name)
            print("       实际: %r" % (got,))
            print("       期望: %r" % (want,))
        else:
            print("[通过] %s" % name)

    eq(
        "同一基线的字按 x 从左到右拼成一行",
        group_lines([g("眠", 116, 500), g("春", 100, 500)]),
        [{"y": 500, "x": 100, "text": "春眠", "font_size": 16}],
    )

    lines = group_lines([g("春", 100, 500), g("眠", 116, 501)])
    eq("基线差 1px 仍算同一行", (len(lines), lines[0]["text"]), (1, "春眠"))

    eq(
        "行按 y 升序输出，与输入顺序无关",
        [l["text"] for l in group_lines([g("晓", 100, 580), g("春", 100, 500), g("眠", 100, 540)])],
        ["春", "眠", "晓"],
    )

    line = group_lines([g("春", 100, 500, 16), g("眠", 132, 500, 24)])[0]
    eq("行内字号取最大值", line["font_size"], 24)
    eq("x 取行内最小者", line["x"], 100)

    line = group_lines([{"t": "春", "x": 100, "y": 500, "font": "bold 20px/1.5 sans-serif"}])[0]
    eq("font 带前缀也能取到字号", line["font_size"], 20)

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
