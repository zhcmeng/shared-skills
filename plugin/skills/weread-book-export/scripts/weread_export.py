#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把微信读书里的一整本书导成 Markdown，按章拆文件，另出一份目录页。

    uv run --with playwright python weread_export.py --out <目录> [--title 书名]

退出码：0 完成；2 需要人来操作（登录、点开一本书）；3 导出中断；1 其它错误。
"""

import argparse
import datetime
import sys
import time
from pathlib import Path

from browser import Browser, BrowserError, default_base_dir
from catalog import chapter_file_name, flatten_to_leaves
from layout import extract_chapter, group_lines, identify_chapter
from markdown import render_chapter, render_readme
from state import first_pending, load_state, mark_done, save_state
from weread import (
    READER_TIMEOUT,
    WEREAD_HOME,
    canvas_height,
    capture_glyphs,
    clear_capture,
    collect_images,
    download_images,
    install_glyph_hook,
    is_logged_out,
    jump_to_chapter,
    open_weread,
    read_catalog,
    scroll_through_chapter,
    search_books,
    switch_to_scroll_mode,
    wait_canvas_ready,
    wait_for_reader,
)

# 页面正文区出现这些字样，说明这一章之后要付费
PAYWALL_MARKS = ("购买", "试读结束", "订阅后继续")

# 画布高过这个数说明这一章撑破了浏览器的渲染上限，截到的内容不保证完整
MAX_CANVAS_HEIGHT = 30000

# 连续这么多章一个字都截不到，判定钩子失效
EMPTY_CHAPTER_LIMIT = 3


def fail(message, code=3):
    print(message, file=sys.stderr)
    sys.exit(code)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="把微信读书里的一本书导出成 Markdown")
    parser.add_argument("--out", required=True, help="产出目录")
    parser.add_argument("--title", help="书名；已经打开着书时可以不填")
    parser.add_argument("--url", help="阅读器地址；给了就直接进这本书，不搜索")
    parser.add_argument("--state", help="续跑状态文件；默认放在用户配置目录下")
    parser.add_argument("--browser-channel", dest="channel", help="浏览器，默认 msedge（Windows）")
    parser.add_argument("--headless", action="store_true", help="不显示浏览器窗口（不推荐）")
    parser.add_argument("--fresh", action="store_true", help="删掉续跑状态，从头再来")
    return parser.parse_args(argv)


def _paywall(page):
    """正文区里出现付费字样就返回 True。"""
    try:
        text = page.evaluate(
            """() => { const el = document.querySelector('.readerChapterContent');
                return (el ? el.innerText : document.body.innerText) || ''; }"""
        )
    except Exception:
        return False
    return any(mark in text for mark in PAYWALL_MARKS)


def _identify(page, leaves, expected=None):
    """屏幕上画的是哪一章；认不出返回 None。"""
    return identify_chapter(
        group_lines(capture_glyphs(page)), [leaf["title"] for leaf in leaves], expected
    )


# 点完目录后多久没见到目标章名，就认为这一下没跳成
CHAPTER_SWITCH_TIMEOUT = 15.0


def _wait_for_chapter(page, leaves, expected, timeout=CHAPTER_SWITCH_TIMEOUT):
    """等目标章画出来并画稳：章名出现在屏幕第一行，画布高度也不再变。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _identify(page, leaves, expected) == expected:
            return wait_canvas_ready(page, timeout=10.0)
        time.sleep(0.3)
    return False


def _bridge_index(expected, total):
    """跳板用第 1 章；目标就是第 1 章时改用第 2 章，免得跳板原地不动。"""
    if total <= 1:
        return None
    return 1 if expected == 0 else 0


def _goto_chapter(browser, leaves, expected):
    """从目录直接跳到目标章，确认画出来的是它。

    如果页面本来就停在目标章，点目录里那一条不会重画——这时先跳到第 1 章
    （目标就是第 1 章则用第 2 章）再跳回来，用两次真实跳转逼出重画。
    全程不判断「现在停在哪一章」。
    """
    page = browser.page
    title = leaves[expected]["title"]
    index = leaves[expected]["index"]
    if _identify(page, leaves, expected) == expected:
        return True

    bridge = _bridge_index(expected, len(leaves))
    for _ in range(2):
        if jump_to_chapter(browser, title, index) and _wait_for_chapter(page, leaves, expected):
            return True
        if bridge is None:
            break
        jump_to_chapter(browser, leaves[bridge]["title"], leaves[bridge]["index"])
        _wait_for_chapter(page, leaves, bridge, timeout=5.0)
        if jump_to_chapter(browser, title, index) and _wait_for_chapter(page, leaves, expected):
            return True
    return False


def _write_readme(out_dir, book_title, author, source_url, export_date, chapters):
    text = render_readme(book_title, author, source_url, export_date, chapters)
    (out_dir / "README.md").write_text(text, encoding="utf-8")


def main(argv=None):
    args = parse_args(argv)
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    state_path = Path(
        args.state or (default_base_dir() / "state" / (out_dir.name + ".json"))
    )
    if args.fresh and state_path.exists():
        state_path.unlink()

    export_date = datetime.date.today().isoformat()

    with Browser(channel=args.channel, headless=args.headless) as browser:
        page = browser.page

        # 1. 进站，确认登录
        if args.url:
            page.goto(args.url, wait_until="domcontentloaded")
        already = open_weread(page)
        if is_logged_out(page):
            fail("没有登录。请在打开的浏览器窗口里扫码登录后重跑。", 2)

        # 2. 不在书里就先找书；候选多于一条时让用户自己挑
        if not already:
            if not args.title:
                fail("现在没打开着书，得用 --title 告诉我书名。", 2)
            hits = search_books(page, args.title)
            if not hits:
                fail("没搜到《%s》。" % args.title, 3)
            if len(hits) == 1:
                page.goto(hits[0]["href"], wait_until="domcontentloaded")
            else:
                print("搜到 %d 条，请在弹出的浏览器窗口里点开要导出的那本：" % len(hits))
                for i, hit in enumerate(hits, 1):
                    print("  %d. %s — %s" % (i, hit["title"], hit["author"]))
                try:
                    page.wait_for_url("**/web/reader/**", timeout=READER_TIMEOUT * 1000)
                except Exception:
                    fail("等了 %d 秒没见你点开书，先停下。" % int(READER_TIMEOUT), 2)

        book = wait_for_reader(page)
        if book is None:
            fail("没能进入阅读器。", 2)
        book_title = book["book_title"]
        author = book["author"]
        source_url = WEREAD_HOME + "web/reader/" + book["book_id"]
        print("要导出的是《%s》（%s）。" % (book_title, author or "作者未知"))

        # 3. 装钩子。这一步会 reload，阅读位置会退回本章开头
        install_glyph_hook(browser)
        browser.human_pause()
        if "/web/reader/" not in page.url:
            book = wait_for_reader(page)
            if book is None:
                fail("装完钩子后不在阅读器里了。", 2)

        if switch_to_scroll_mode(browser) is None:
            fail("切不到滚动模式，没法一次拿到整章。", 3)

        # 4. 目录与续跑状态
        leaves = flatten_to_leaves(read_catalog(page))
        if not leaves:
            fail("目录是空的。", 3)

        chapters = [
            {
                "file_name": chapter_file_name(pos, len(leaves), leaf["title"]),
                "title": leaf["title"],
                "parents": leaf["parents"],
            }
            for pos, leaf in enumerate(leaves)
        ]
        pos_by_index = {leaf["index"]: pos for pos, leaf in enumerate(leaves)}

        state = load_state(state_path)
        pending = first_pending(leaves, state)
        _write_readme(out_dir, book_title, author, source_url, export_date, chapters)

        if pending == -1:
            print("目录里每一章都已经导过了，不用再做。")
            return 0

        pos = pos_by_index[pending]
        print("共 %d 章，从第 %d 章《%s》开始。" % (len(leaves), pos + 1, leaves[pos]["title"]))
        browser.human_pause()
        if not _goto_chapter(browser, leaves, pos):
            fail("没能跳到《%s》。停下。" % leaves[pos]["title"], 3)

        # 5. 逐章取
        written = 0
        total_images = 0
        empty_streak = 0

        while pos < len(leaves):
            chapter = leaves[pos]
            file_name = chapters[pos]["file_name"]
            prefix = file_name.split("-", 1)[0]

            browser.human_pause()
            clear_capture(page)
            if not _goto_chapter(browser, leaves, pos):
                fail("没能跳到《%s》。停下。" % chapter["title"], 3)

            if _paywall(page):
                fail("从《%s》开始拿不到正文：页面要求购买或订阅。到此为止。" % chapter["title"], 3)

            height = canvas_height(page)
            if height > MAX_CANVAS_HEIGHT:
                fail(
                    "《%s》的画布高 %d 像素，可能撑破了浏览器的渲染上限，截到的内容不保证完整。停下。"
                    % (chapter["title"], height),
                    3,
                )

            paragraphs = extract_chapter(capture_glyphs(page), book_title, chapter["title"])

            # 截完字再滚一遍本章：一是像人在读，二是让一开始没进视野的插图也加载出来
            browser.human_pause()
            scroll_through_chapter(browser)
            images = collect_images(page)
            saved = download_images(browser, images, out_dir / "images", prefix)
            name_by_src = {item["src"]: item["file_name"] for item in saved}
            placed = [
                {"y": image["y"], "alt": image["alt"], "file_name": name_by_src[image["src"]]}
                for image in images
                if image["src"] in name_by_src
            ]

            if not paragraphs and not placed:
                empty_streak += 1
                print("警告：《%s》一个字也没截到，也没有图。" % chapter["title"], file=sys.stderr)
                if empty_streak >= EMPTY_CHAPTER_LIMIT:
                    fail("连续 %d 章都截不到内容，钩子可能已经失效。停下。" % empty_streak, 3)
            else:
                empty_streak = 0

            (out_dir / file_name).write_text(
                render_chapter(chapter["title"], paragraphs, placed), encoding="utf-8"
            )
            written += 1
            total_images += len(placed)

            state = mark_done(state, chapter["index"])
            save_state(state_path, state)
            _write_readme(out_dir, book_title, author, source_url, export_date, chapters)
            print(
                "写完 %s（%d 段，%d 张图）" % (file_name, len(paragraphs), len(placed)), flush=True
            )

            pos += 1

        print("完成 %d 章、%d 张图，写在 %s" % (written, total_images, out_dir))
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrowserError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
