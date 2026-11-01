#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""markdown.py 自己的测试。

    python -X utf8 tests/weread-book-export/test_markdown.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层。
# 这条路径排在 sys.path 最前，是为了让 import markdown 取到技能目录下那份，
# 而不是 PyPI 上同名的 markdown 包。
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
from markdown import render_chapter, render_readme  # noqa: E402


def t(text, y):
    return {"kind": "text", "level": 0, "text": text, "y": y}


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
        "章名成为一级标题，段落之间空行",
        render_chapter("第一章 定位", [t("第一段。", 500), t("第二段。", 580)], []),
        "# 第一章 定位\n\n第一段。\n\n第二段。\n",
    )

    eq(
        "章内标题降一级",
        render_chapter(
            "第一章",
            [{"kind": "heading", "level": 1, "text": "第一节", "y": 460}, t("正文。", 500)],
            [],
        ),
        "# 第一章\n\n## 第一节\n\n正文。\n",
    )

    eq(
        "图片按 y 插到对应段落之后",
        render_chapter(
            "第一章", [t("第一段。", 500), t("第二段。", 700)],
            [{"y": 600, "file_name": "03-001.jpg", "alt": "示意图"}],
        ),
        "# 第一章\n\n第一段。\n\n![示意图](images/03-001.jpg)\n\n第二段。\n",
    )

    eq(
        "章首的图排在第一段之前",
        render_chapter("第一章", [t("第一段。", 700)], [{"y": 100, "file_name": "03-001.jpg", "alt": ""}]),
        "# 第一章\n\n![](images/03-001.jpg)\n\n第一段。\n",
    )

    eq(
        "整章只有图没有字也照样出文档",
        render_chapter(
            "图版一", [],
            [{"y": 100, "file_name": "05-001.jpg", "alt": ""},
             {"y": 200, "file_name": "05-002.jpg", "alt": ""}],
        ),
        "# 图版一\n\n![](images/05-001.jpg)\n\n![](images/05-002.jpg)\n",
    )

    md = render_readme(
        "抢占心智", "江南春", "https://weread.qq.com/web/reader/xxx", "2026-11-01",
        [
            {"file_name": "01-序言.md", "title": "序言", "parents": []},
            {"file_name": "02-第一章-定位.md", "title": "第一章 定位", "parents": ["上篇 认知"]},
        ],
    )
    eq("目录页开头是书名", md.startswith("# 抢占心智\n\n"), True)
    eq("目录页有作者", "作者：江南春" in md, True)
    eq("目录页有来源", "来源：https://weread.qq.com/web/reader/xxx" in md, True)
    eq("目录页有导出日期", "导出日期：2026-11-01" in md, True)
    eq("目录页按顺序链接到每章", "- [序言](./01-序言.md)" in md, True)
    eq("父级单独成行", "### 上篇 认知" in md, True)
    eq("带父级的章节也链得上", "- [第一章 定位](./02-第一章-定位.md)" in md, True)

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
