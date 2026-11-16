#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜索微信读书：按精确书名、模糊关键词、相关词，或按系列名 + 年份查全。

    uv run --with playwright python weread_search.py --exact "估值：难点、解决方案"
    uv run --with playwright python weread_search.py --fuzzy "估值 价值投资"
    uv run --with playwright python weread_search.py --semantic AI --terms "人工智能,大模型"
    uv run --with playwright python weread_search.py --series 财经 --year 2026

搜索页只按书名匹配，没有全文搜索；一次最多回约 40 条、顺序不规则。
--exact 按归一化后的标题全等认定；--fuzzy 标题含任意一个词即命中；
--semantic 把概念和一组相关词逐个搜、按书合并去重；--series/--year
逐期把完整标题搜一遍，绕开这个上限。

退出码：0 列完了；2 没登录且一条也没搜到；3 一条也没搜到；1 其它错误。
"""

import argparse
import datetime
import sys
from pathlib import Path

from browser import Browser, BrowserError
from issues import (
    DEFAULT_TEMPLATE,
    check_template,
    issue_title,
    pick_extras,
    render_markdown,
    render_text,
)
from matches import (
    exact_hits,
    fuzzy_hits,
    merge_hits,
    parse_terms,
    render_exact,
    render_fuzzy,
    render_semantic,
    term_hits,
)
from weread import search_books_page, wait_for_login

# 逐期搜索之间的停顿；搜索页比阅读器轻，停得比导出的 2～6 秒短
SEARCH_PAUSE = (0.3, 0.8)


def prefer_utf8(stream):
    """这一路输出被重定向走时，改成按 UTF-8 吐字节；真控制台不动。

    与 pdf-to-md、skill-judge 里的同名函数是同一份逻辑：Windows 中文版上
    标准流接管道时按区域编码 cp936 输出，中文落成 GBK 字节，接住的一方
    按 UTF-8 解，屏幕上就是乱码。真控制台的编码由 Python 按终端挑好，
    不切。
    """
    if stream.isatty():
        return
    if (getattr(stream, "encoding", "") or "").lower().replace("-", "") == "utf8":
        return
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


class _ArgumentParser(argparse.ArgumentParser):
    """参数写错按 1 退出。

    argparse 默认按 2 退出，这里的 2 留给了「要人来操作」（登录、点书），
    两者混在一起会让人把打错参数当成没登录。
    """

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, "%s: 参数错误：%s\n" % (self.prog, message))


def parse_args(argv=None):
    parser = _ArgumentParser(
        description="搜索微信读书：精确书名、模糊关键词、相关词，或按系列名和年份逐期列全"
    )
    parser.add_argument("--exact", help="按完整书名精确搜，同名多本全部列出")
    parser.add_argument("--fuzzy", help="按关键词模糊搜，标题含任意一个词就算")
    parser.add_argument("--semantic", help="按概念搜，配合 --terms 给一组相关词")
    parser.add_argument(
        "--terms", help="语义模式的相关词，逗号分隔，如 人工智能,大模型"
    )
    parser.add_argument("--series", help="期刊/系列名，如 财经")
    parser.add_argument("--year", type=int, help="年份，如 2026")
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="逐期搜到第几期为止（默认 60，周刊一年 52 期）",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="标题模板，默认「%s」；占位符是 {series}、{year}、{n}"
        % DEFAULT_TEMPLATE,
    )
    parser.add_argument("--out", help="把清单另写成 Markdown 文件（只和 --series 一起用）")
    parser.add_argument(
        "--show", action="store_true", help="显示浏览器窗口（默认无头；要登录时用）"
    )
    parser.add_argument(
        "--profile",
        help="浏览器配置目录；默认用登录态所在的那个。搜索不登录也能用，"
        "导出占着默认目录时可以指一个空目录",
    )
    parser.add_argument(
        "--browser-channel", dest="channel", help="浏览器，默认 msedge（Windows）"
    )
    return parser.parse_args(argv)


def check_args(args):
    """确认参数组合成立；不成立抛 ValueError。返回模式名。"""
    modes = [
        name
        for name in ("exact", "fuzzy", "semantic", "series")
        if getattr(args, name) is not None
    ]
    if not modes:
        if args.year is not None:
            raise ValueError("给 --year 时也要给 --series。")
        raise ValueError("要给 --exact、--fuzzy、--semantic 或 --series 之一。")
    if len(modes) > 1:
        raise ValueError("--exact、--fuzzy、--semantic、--series 只能给一个。")
    mode = modes[0]

    if args.terms is not None and mode != "semantic":
        raise ValueError("--terms 只能和 --semantic 一起用。")
    if mode != "series":
        for name in ("year", "max", "template", "out"):
            if getattr(args, name) is not None:
                raise ValueError("--%s 只和 --series 一起用。" % name)

    if mode == "exact" and not args.exact.strip():
        raise ValueError("--exact 给一个完整书名，不能是空串。")
    if mode == "fuzzy" and not args.fuzzy.strip():
        raise ValueError("--fuzzy 给一个关键词，不能是空串。")
    if mode == "semantic" and not args.semantic.strip():
        raise ValueError("--semantic 给一个概念，不能是空串。")

    if mode == "series":
        if not args.series or args.year is None:
            raise ValueError("系列模式要同时给 --series 和 --year。")
        if not 1000 <= args.year <= 9999:
            raise ValueError("--year 给四位数年份，如 2026。")
        if args.max is None:
            args.max = 60
        if args.template is None:
            args.template = DEFAULT_TEMPLATE
        if args.max < 1:
            raise ValueError("--max 至少是 1。")
    return mode


def run_exact(browser, args):
    """精确档：按完整书名搜，只列标题完全一致的那些。"""
    result = search_books_page(browser.page, args.exact)
    hits = exact_hits(result["hits"], args.exact)
    if hits:
        print(render_exact(args.exact, hits, []))
        return 0
    print(render_exact(args.exact, [], result["hits"]), file=sys.stderr)
    if result["logged_in"] is False:
        print("现在没登录。书名确认没错的话，加 --show 登录后再试。", file=sys.stderr)
        return 2
    return 3


def run_fuzzy(browser, args):
    """模糊档：标题含任意一个词就算，按页面顺序列结果。"""
    result = search_books_page(browser.page, args.fuzzy)
    hits = fuzzy_hits(result["hits"], args.fuzzy)
    if not hits:
        if result["logged_in"] is False:
            print(
                "标题里一个都没含这些词，而且现在没登录。加 --show 登录后重跑。",
                file=sys.stderr,
            )
            return 2
        print(
            "标题里一个都没含这些词：%s。换个词，或用 --semantic 给一组相关词。"
            % args.fuzzy,
            file=sys.stderr,
        )
        return 3
    capped = result["has_more"] is True or len(result["hits"]) >= 40
    print(render_fuzzy(args.fuzzy, hits, capped))
    return 0


def run_semantic(browser, args):
    """语义档：概念加一组相关词逐个搜，按书合并去重再列。"""
    terms = parse_terms(args.semantic, args.terms)
    per_term = []
    for index, term in enumerate(terms, 1):
        result = search_books_page(browser.page, term)
        hits = term_hits(result["hits"], term)
        per_term.append(
            {
                "term": term,
                "hits": hits,
                "capped": result["has_more"] is True or len(result["hits"]) >= 40,
                "logged_in": result["logged_in"],
            }
        )
        print(
            "搜第 %d/%d 个词：%s，%d 条" % (index, len(terms), term, len(hits)),
            flush=True,
        )
        if index < len(terms):
            browser.human_pause(*SEARCH_PAUSE)

    merged = merge_hits(per_term)
    print(render_semantic(terms, per_term, merged))
    if merged:
        return 0
    if any(item["logged_in"] is False for item in per_term):
        print(
            "这些词一个也没搜到，而且现在没登录。加 --show 登录后重跑。",
            file=sys.stderr,
        )
        return 2
    return 3


def find_issues(browser, args):
    """逐期用完整标题精确搜索，返回按编号排好的各期和最后一次的登录状态。"""
    issues = []
    logged_in = None
    print(
        "逐期搜索《%s》%s 年，第 1 到 %d 期……" % (args.series, args.year, args.max),
        flush=True,
    )
    for n in range(1, args.max + 1):
        title = issue_title(args.template, args.series, args.year, n)
        result = search_books_page(browser.page, title)
        logged_in = result["logged_in"]
        matched = exact_hits(result["hits"], title)
        if matched:
            issues.append(
                {
                    "n": n,
                    "title": (matched[0].get("title") or title).strip(),
                    "urls": [hit["href"] for hit in matched],
                }
            )
            print("第 %d 期：%s" % (n, title), flush=True)
        if n % 10 == 0:
            print("……查到第 %d 期，已找到 %d 期" % (n, len(issues)), flush=True)
        browser.human_pause(*SEARCH_PAUSE)
    return issues, logged_in


def run_series(browser, args):
    """按系列名 + 年份逐期查全，打印清单，可另写 Markdown。"""
    issues, logged_in = find_issues(browser, args)
    if not issues:
        if logged_in is False:
            print(
                "一期也没搜到，而且现在没登录。加 --show 打开窗口登录后重跑。",
                file=sys.stderr,
            )
            return 2
        print(
            "一期也没搜到：确认 --series 写的是书名里的系列名；"
            "标题格式不同时用 --template 改。",
            file=sys.stderr,
        )
        return 3

    extras_result = search_books_page(
        browser.page, "%s %s" % (args.series, args.year)
    )
    extras = pick_extras(
        extras_result["hits"],
        args.series,
        args.year,
        [item["title"] for item in issues],
    )

    print()
    print(render_text(args.series, args.year, issues, extras))

    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            render_markdown(
                args.series,
                args.year,
                issues,
                extras,
                today=datetime.date.today(),
            ),
            encoding="utf-8",
        )
        print()
        print("清单写在 %s" % path.resolve())
    return 0


def main(argv=None):
    prefer_utf8(sys.stdout)
    prefer_utf8(sys.stderr)

    args = parse_args(argv)
    try:
        mode = check_args(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if mode == "series":
        try:
            check_template(args.template)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    try:
        with Browser(
            profile_dir=args.profile,
            channel=args.channel,
            headless=not args.show,
        ) as browser:
            if args.show:
                wait_for_login(browser.page)
            if mode == "exact":
                return run_exact(browser, args)
            if mode == "fuzzy":
                return run_fuzzy(browser, args)
            if mode == "semantic":
                return run_semantic(browser, args)
            return run_series(browser, args)
    except BrowserError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrowserError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
