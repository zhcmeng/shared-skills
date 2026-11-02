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
from markdown import render_book_chapter  # noqa: E402
from weread import _parse_title, attach_downloads  # noqa: E402


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

    parts = [
        {"title": "第2章", "paragraphs": [], "images": []},
        {
            "title": "封杀品类",
            "paragraphs": [{"kind": "text", "level": 0, "text": "正文。", "y": 500}],
            "images": [
                {"src": "https://x/a.jpg", "alt": "示意图", "y": 100},
                {"src": "https://x/b.jpg", "alt": "", "y": 200},
            ],
        },
    ]
    saved = [
        {"src": "https://x/a.jpg", "file_name": "02-001.jpg"},
        {"src": "https://x/b.jpg", "file_name": "02-002.jpg"},
    ]
    eq("下载结果按 src 写回各节的 images", attach_downloads(parts, saved), 2)
    eq(
        "写回的图带着文件名，整章渲染不再缺键",
        render_book_chapter("第2章", parts),
        "# 第2章\n\n## 封杀品类\n\n![示意图](images/02-001.jpg)\n\n"
        "![](images/02-002.jpg)\n\n正文。\n",
    )

    parts = [
        {"title": "第2章", "images": [{"src": "https://x/a.jpg", "alt": "", "y": 100},
                                      {"src": "https://x/lost.jpg", "alt": "", "y": 200}]},
    ]
    eq(
        "没下下来的图丢掉，不留在正文里",
        attach_downloads(parts, [{"src": "https://x/a.jpg", "file_name": "02-001.jpg"}]),
        1,
    )
    eq("丢掉的图从 images 里去除", [i["file_name"] for i in parts[0]["images"]], ["02-001.jpg"])

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
