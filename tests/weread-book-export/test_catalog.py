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
from catalog import chapter_file_name, flatten_to_leaves  # noqa: E402


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
        "平铺目录全部是叶子",
        flatten_to_leaves([{"title": "封面", "level": 1}, {"title": "序言", "level": 1}]),
        [
            {"index": 0, "title": "封面", "parents": []},
            {"index": 1, "title": "序言", "parents": []},
        ],
    )

    leaves = flatten_to_leaves([
        {"title": "序言", "level": 1},
        {"title": "上篇 认知", "level": 1},
        {"title": "第一章 定位", "level": 2},
        {"title": "第二章 品类", "level": 2},
        {"title": "后记", "level": 1},
    ])
    eq("上篇不算一章，其下的章各成一章",
       [l["title"] for l in leaves], ["序言", "第一章 定位", "第二章 品类", "后记"])
    eq("叶子记着自己的父级", leaves[1]["parents"], ["上篇 认知"])
    eq("平铺条目的父级为空", leaves[0]["parents"], [])

    eq(
        "两层嵌套的 parents 从外到内",
        flatten_to_leaves([
            {"title": "上篇", "level": 1},
            {"title": "第一节", "level": 2},
            {"title": "一、小节", "level": 3},
        ]),
        [{"index": 2, "title": "一、小节", "parents": ["上篇", "第一节"]}],
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
