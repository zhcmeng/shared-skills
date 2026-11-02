#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""catalog.py 自己的测试。

    python -X utf8 tests/weread-book-export/test_catalog.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
from catalog import chapter_file_name, flatten_to_chapters  # noqa: E402


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
        "最上层条目各成一章，与标题怎么命名无关",
        [
            (c["title"], [p["title"] for p in c["parts"]])
            for c in flatten_to_chapters(
                [
                    {"title": "文前", "level": 1},
                    {"title": "第一级阶梯", "level": 1},
                    {"title": "可可西里", "level": 2},
                    {"title": "阿里", "level": 2},
                    {"title": "第二级阶梯", "level": 1},
                    {"title": "伊犁", "level": 2},
                ]
            )
        ],
        [
            ("文前", []),
            ("第一级阶梯", ["可可西里", "阿里"]),
            ("第二级阶梯", ["伊犁"]),
        ],
    )

    eq(
        "书里没有第X章这种编号，也按最上层拆，不往最深层钻",
        [
            (c["title"], [p["title"] for p in c["parts"]])
            for c in flatten_to_chapters(
                [
                    {"title": "上篇", "level": 1},
                    {"title": "第一节", "level": 2},
                    {"title": "一、小节", "level": 3},
                ]
            )
        ],
        [("上篇", ["第一节", "一、小节"])],
    )

    eq(
        "目录都在同一层时每条各成一章",
        [
            c["title"]
            for c in flatten_to_chapters(
                [{"title": "其一", "level": 1}, {"title": "其二", "level": 1}]
            )
        ],
        ["其一", "其二"],
    )

    eq(
        "章的 index 就是它在完整目录里的位置",
        [
            c["index"]
            for c in flatten_to_chapters(
                [
                    {"title": "文前", "level": 1},
                    {"title": "第一级阶梯", "level": 1},
                    {"title": "可可西里", "level": 2},
                    {"title": "第二级阶梯", "level": 1},
                ]
            )
        ],
        [0, 1, 3],
    )

    eq(
        "深层的节按目录顺序收进所属章，碰到下一个上层条目就断开",
        [
            [p["title"] for p in c["parts"]]
            for c in flatten_to_chapters(
                [
                    {"title": "上篇", "level": 1},
                    {"title": "第一章", "level": 2},
                    {"title": "第一节", "level": 3},
                    {"title": "第二章", "level": 2},
                    {"title": "下篇", "level": 1},
                    {"title": "第三章", "level": 2},
                ]
            )
        ],
        [["第一章", "第一节", "第二章"], ["第三章"]],
    )

    eq(
        "最上层条目没有父级",
        [
            c["parents"]
            for c in flatten_to_chapters(
                [{"title": "上篇", "level": 1}, {"title": "第一章", "level": 2}]
            )
        ],
        [[]],
    )

    eq("空目录返回空表", flatten_to_chapters([]), [])

    eq("同名章节生成的文件名不撞",
       chapter_file_name(0, 10, "译后记") != chapter_file_name(1, 10, "译后记"), True)
    eq("序号按总数补零", chapter_file_name(0, 9, "扉页"), "01-扉页.md")
    eq("三位数总数补三位", chapter_file_name(119, 120, "后记"), "120-后记.md")
    eq("标题里的路径非法字符换成连字符",
       chapter_file_name(9, 120, '第10章 / 转折'), "010-第10章-转折.md")
    eq("五种非法字符都换掉",
       chapter_file_name(0, 5, 'A:B*C?D"E<F>G|H\\I'), "01-A-B-C-D-E-F-G-H-I.md")
    eq("过长的标题截断到 40 字", chapter_file_name(0, 5, "一" * 80), "01-" + "一" * 40 + ".md")

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
