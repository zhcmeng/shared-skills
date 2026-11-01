#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""weread.py 里纯逻辑部分的测试。

    python -X utf8 tests/weread-book-export/test_weread.py

浏览器上的动作（搜索、跳章、截字）连不上真站点就没有意义，不在这里测。
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
from weread import _parse_title  # noqa: E402


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
        "进了章之后是四段：书名 - 章名 - 作者 - 微信读书",
        _parse_title("抢占心智 - 第1章 打造企业的护城河 - 江南春 - 微信读书"),
        ("抢占心智", "江南春"),
    )
    eq(
        "还没进章时是三段：书名 - 作者 - 微信读书",
        _parse_title("抢占心智 - 江南春 - 微信读书"),
        ("抢占心智", "江南春"),
    )
    eq("只有书名和尾巴时作者留空", _parse_title("抢占心智 - 微信读书"), ("抢占心智", ""))
    eq("标题为空时不崩", _parse_title(""), ("", ""))

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
