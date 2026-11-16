#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""issues.py 的测试：标题模板、精确匹配、缺号与清单渲染。

    python -X utf8 tests/weread-book-export/test_issues.py
"""

import datetime
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
from issues import (  # noqa: E402
    DEFAULT_TEMPLATE,
    check_template,
    gaps,
    issue_title,
    pick_extras,
    render_markdown,
    render_text,
    summary,
)


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

    def raises(name, func, needle):
        nonlocal bad
        try:
            func()
        except Exception as exc:
            if needle not in str(exc):
                bad += 1
                print("[失败] %s" % name)
                print("       报错里没有 %r：%s" % (needle, exc))
            else:
                print("[通过] %s" % name)
        else:
            bad += 1
            print("[失败] %s：没有报错" % name)

    eq("默认模板拼出完整标题", issue_title(DEFAULT_TEMPLATE, "财经", 2026, 5), "财经（2026年第5期）")
    eq(
        "模板可以补零",
        issue_title("{series} {year}年第{n:02d}期", "读者", 2026, 5),
        "读者 2026年第05期",
    )
    eq("能用的模板原样返回", check_template(DEFAULT_TEMPLATE), DEFAULT_TEMPLATE)
    raises("模板里没有 n 要报错", lambda: check_template("《{series}》{year}年"), "必须有 {n}")
    raises(
        "占位符写错要报错",
        lambda: check_template("{series}（{year}年第{n2}期）"),
        "n2",
    )
    raises(
        "花括号不配对要报错",
        lambda: check_template("{series（{year}年第{n}期）"),
        "标题模板用不了",
    )

    eq("缺号只算到最大期号", gaps([{"n": 1}, {"n": 2}, {"n": 4}, {"n": 6}]), [3, 5])
    eq("没找到第 1 期也算缺号", gaps([{"n": 2}, {"n": 3}]), [1])
    eq("一期都没有时不报缺号", gaps([]), [])
    eq("连续时没有缺号", summary([{"n": 1}, {"n": 2}]), "第 1～2 期都在，没有缺号。")
    eq(
        "缺号写清楚是哪几期",
        summary([{"n": 1}, {"n": 3}]),
        "第 1～3 期里缺：第 2 期。",
    )
    eq("一期都没有", summary([]), "一期也没搜到。")

    extra_hits = [
        {"title": "财经年刊（2026预测与战略）", "href": "annual"},
        {"title": "第一财经（2026年第5期）", "href": "yicai"},
        {"title": "财经（2026年第5期）", "href": "issue5"},
        {"title": "财经爆点：春晚背后的资本盛宴（2026年第2期）（轻财经）", "href": "baodian"},
        {"title": "财经年刊（2026预测与战略）", "href": "annual"},
        {"title": "另一本 2026 年的书", "href": "other"},
    ]
    eq(
        "另见只留年刊这类不按期号编的",
        pick_extras(extra_hits, "财经", 2026, ["财经（2026年第5期）"]),
        [{"title": "财经年刊（2026预测与战略）", "url": "annual"}],
    )

    issues = [
        {"n": 1, "title": "财经（2026年第1期）", "urls": ["https://a"]},
        {"n": 3, "title": "财经（2026年第3期）", "urls": ["https://c1", "https://c2"]},
    ]
    extras = [{"title": "财经年刊（2026预测与战略）", "url": "https://annual"}]
    text = render_text("财经", 2026, issues, extras)
    for needle in (
        "《财经》2026 年各期（共 2 期）",
        "  1. 财经（2026年第1期）",
        "https://a",
        "第 1～3 期里缺：第 2 期。",
        "同名 2 条",
        "另见",
        "财经年刊（2026预测与战略）",
    ):
        eq("文字清单里有 %s" % needle, needle in text, True)

    md = render_markdown(
        "财经", 2026, issues, extras, today=datetime.date(2026, 11, 14)
    )
    for needle in (
        "# 《财经》2026 年各期",
        "截至 2026-11-14。",
        "| 1 | 财经（2026年第1期） | https://a |",
        "https://c1<br>https://c2",
        "## 另见",
    ):
        eq("Markdown 清单里有 %s" % needle, needle in md, True)

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
