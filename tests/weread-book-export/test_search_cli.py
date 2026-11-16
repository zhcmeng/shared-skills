#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜书命令行的参数检查：模式互斥、默认值、退出前的报错。

    python -X utf8 tests/weread-book-export/test_search_cli.py
"""

import argparse
import contextlib
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
from issues import DEFAULT_TEMPLATE  # noqa: E402
import weread_search  # noqa: E402
from weread_search import check_args, run_exact, run_fuzzy, run_semantic, run_series  # noqa: E402


class FakeBrowser:
    """只提供 run_semantic 用到的两样：page 和停顿。"""

    page = object()

    def human_pause(self, *seconds):
        pass


def fake_search(page, title):
    """每个词都返回一条含该词的书，地址各不相同。"""
    return {
        "hits": [
            {
                "title": "%s 入门" % title,
                "author": "甲",
                "href": "https://x/%s" % title,
            }
        ],
        "total_count": 1,
        "has_more": False,
        "logged_in": True,
    }


def empty_search(page, title):
    return {
        "hits": [],
        "total_count": 0,
        "has_more": False,
        "logged_in": False,
    }


def hit_search(page, title):
    return {
        "hits": [{"title": title, "author": "甲", "href": "https://x"}],
        "total_count": 1,
        "has_more": False,
        "logged_in": True,
    }


def miss_search(logged_in):
    def search(page, title):
        return {
            "hits": [],
            "total_count": 0,
            "has_more": False,
            "logged_in": logged_in,
        }

    return search


def args(**overrides):
    data = dict(
        exact=None,
        fuzzy=None,
        semantic=None,
        terms=None,
        series=None,
        year=None,
        max=None,
        template=None,
        out=None,
        show=False,
        profile=None,
        channel=None,
    )
    data.update(overrides)
    return argparse.Namespace(**data)


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

    eq("精确模式", check_args(args(exact="书名")), "exact")
    eq("模糊模式", check_args(args(fuzzy="估值")), "fuzzy")
    eq("语义模式", check_args(args(semantic="AI", terms="人工智能,大模型")), "semantic")

    series_args = args(series="财经", year=2026)
    eq("系列模式", check_args(series_args), "series")
    eq("系列模式默认 max", series_args.max, 60)
    eq("系列模式默认模板", series_args.template, DEFAULT_TEMPLATE)

    raises(
        "两种模式不能一起给",
        lambda: check_args(args(exact="x", fuzzy="y")),
        "只能给一个",
    )
    raises(
        "精确模式不能给 --out",
        lambda: check_args(args(exact="x", out="f.md")),
        "只和",
    )
    raises(
        "--terms 只能配语义模式",
        lambda: check_args(args(fuzzy="x", terms="a,b")),
        "--terms",
    )
    raises("空书名要报错", lambda: check_args(args(exact="  ")), "不能是空串")
    raises(
        "系列模式缺年份",
        lambda: check_args(args(series="财经")),
        "同时给",
    )

    eq("语义模式没有 --terms 也行", check_args(args(semantic="AI")), "semantic")
    raises(
        "语义模式不能给 --out",
        lambda: check_args(args(semantic="AI", out="f.md")),
        "只和",
    )
    raises("空概念要报错", lambda: check_args(args(semantic="  ")), "不能是空串")

    original = weread_search.search_books_page
    try:
        weread_search.search_books_page = fake_search
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run_semantic(
                FakeBrowser(), args(semantic="AI", terms="人工智能")
            )
        text = out.getvalue()
        eq("语义档逐词搜完合并", code, 0)
        eq(
            "语义档输出含合并结果",
            "去重后 2 本" in text and "命中 1 词" in text,
            True,
        )

        weread_search.search_books_page = empty_search
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_semantic(FakeBrowser(), args(semantic="AI"))
        eq("一个词也没搜到且未登录返回 2", code, 2)
        eq("未登录时提示加 --show", "--show" in err.getvalue(), True)

        weread_search.search_books_page = hit_search
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run_exact(FakeBrowser(), args(exact="同名"))
        eq("精确档命中返回 0", code, 0)
        eq("精确档命中列出地址", "https://x" in out.getvalue(), True)

        weread_search.search_books_page = miss_search(True)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = run_exact(FakeBrowser(), args(exact="没有的书"))
        eq("精确档未命中且已登录返回 3", code, 3)

        weread_search.search_books_page = miss_search(False)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = run_exact(FakeBrowser(), args(exact="没有的书"))
        eq("精确档未命中且未登录返回 2", code, 2)

        weread_search.search_books_page = miss_search(True)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = run_fuzzy(FakeBrowser(), args(fuzzy="不存在"))
        eq("模糊档未命中且已登录返回 3", code, 3)

        weread_search.search_books_page = miss_search(False)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = run_fuzzy(FakeBrowser(), args(fuzzy="不存在"))
        eq("模糊档未命中且未登录返回 2", code, 2)

        def series_search(page, title):
            if title == "财经（2026年第1期）":
                return {
                    "hits": [
                        {"title": title, "author": "财经", "href": "https://x/1"}
                    ],
                    "total_count": 1,
                    "has_more": False,
                    "logged_in": True,
                }
            return {
                "hits": [],
                "total_count": 0,
                "has_more": False,
                "logged_in": True,
            }

        weread_search.search_books_page = series_search
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run_series(
                FakeBrowser(),
                args(series="财经", year=2026, max=1, template=DEFAULT_TEMPLATE),
            )
        eq("系列档命中返回 0", code, 0)
        eq("系列档列出第 1 期", "财经（2026年第1期）" in out.getvalue(), True)

        weread_search.search_books_page = miss_search(True)
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_series(
                FakeBrowser(),
                args(series="财经", year=2026, max=1, template=DEFAULT_TEMPLATE),
            )
        eq("系列档一期没搜到且已登录返回 3", code, 3)

        weread_search.search_books_page = miss_search(False)
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run_series(
                FakeBrowser(),
                args(series="财经", year=2026, max=1, template=DEFAULT_TEMPLATE),
            )
        eq("系列档一期没搜到且未登录返回 2", code, 2)

        def semantic_search(page, title):
            if title == "人工智能":
                return {
                    "hits": [
                        {
                            "title": "人工智能导论",
                            "author": "乙",
                            "href": "https://b",
                        }
                    ],
                    "total_count": 1,
                    "has_more": False,
                    "logged_in": True,
                }
            return {
                "hits": [],
                "total_count": 0,
                "has_more": False,
                "logged_in": True,
            }

        weread_search.search_books_page = semantic_search
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = run_semantic(FakeBrowser(), args(semantic="AI", terms="人工智能"))
        text = out.getvalue()
        eq("语义档一个词 0 条不影响其余词", code, 0)
        eq("语义档标出 0 条的那个词", "AI：0 条" in text, True)
        eq(
            "语义档合并其余词的结果",
            "去重后 1 本" in text and "人工智能导论" in text,
            True,
        )
    finally:
        weread_search.search_books_page = original

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
