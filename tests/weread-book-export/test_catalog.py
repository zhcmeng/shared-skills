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
from catalog import chapter_file_name, chapter_level, flatten_to_chapters  # noqa: E402


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
        "标题带第X章的那一层就是章",
        chapter_level(
            [
                {"title": "版权信息", "level": 1},
                {"title": "第1章 定位", "level": 1},
                {"title": "人心比流量重要", "level": 2},
            ]
        ),
        1,
    )

    eq(
        "带部/篇的书，章在第二层",
        chapter_level(
            [{"title": "上篇 认知", "level": 1}, {"title": "第一章 定位", "level": 2}]
        ),
        2,
    )

    eq(
        "一层都没有第X章时按最深的一层拆",
        chapter_level([{"title": "上篇", "level": 1}, {"title": "一、小节", "level": 2}]),
        2,
    )

    eq(
        "章下面的小节归到该章，不再单独成章",
        [
            (c["title"], [p["title"] for p in c["parts"]])
            for c in flatten_to_chapters(
                [
                    {"title": "版权信息", "level": 1},
                    {"title": "第1章 定位", "level": 1},
                    {"title": "第2章 抢占消费者心智", "level": 1},
                    {"title": "人心比流量重要", "level": 2},
                    {"title": "封杀品类", "level": 2},
                    {"title": "第3章 渠道", "level": 1},
                    {"title": "三云合一", "level": 2},
                ]
            )
        ],
        [
            ("版权信息", []),
            ("第1章 定位", []),
            ("第2章 抢占消费者心智", ["人心比流量重要", "封杀品类"]),
            ("第3章 渠道", ["三云合一"]),
        ],
    )

    eq(
        "章的 index 就是它在完整目录里的位置",
        [
            c["index"]
            for c in flatten_to_chapters(
                [
                    {"title": "版权信息", "level": 1},
                    {"title": "第1章", "level": 1},
                    {"title": "小节", "level": 2},
                    {"title": "第2章", "level": 1},
                ]
            )
        ],
        [0, 1, 3],
    )

    eq(
        "部/篇记在父级里，章下的小节照收",
        [
            (c["title"], c["parents"], [p["title"] for p in c["parts"]])
            for c in flatten_to_chapters(
                [
                    {"title": "上篇", "level": 1},
                    {"title": "第1章", "level": 2},
                    {"title": "第1节", "level": 3},
                    {"title": "第2章", "level": 2},
                    {"title": "下篇", "level": 1},
                    {"title": "第3章", "level": 2},
                ]
            )
        ],
        [("第1章", ["上篇"], ["第1节"]), ("第2章", ["上篇"], []), ("第3章", ["下篇"], [])],
    )

    eq(
        "没有第X章时按最深一层拆，父级仍从外到内",
        [
            (c["title"], c["parents"])
            for c in flatten_to_chapters(
                [
                    {"title": "上篇", "level": 1},
                    {"title": "第一节", "level": 2},
                    {"title": "一、小节", "level": 3},
                ]
            )
        ],
        [("一、小节", ["上篇", "第一节"])],
    )

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
