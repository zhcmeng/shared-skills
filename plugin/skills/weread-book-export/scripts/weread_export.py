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
from catalog import chapter_file_name, flatten_to_chapters
from layout import group_lines, identify_chapter, is_clipped, strip_noise_lines, to_paragraphs
from markdown import render_book_chapter, render_readme
from state import first_pending, load_state, mark_done, save_state
from weread import (
    READER_TIMEOUT,
    WEREAD_HOME,
    attach_downloads,
    canvas_css_heights,
    capture_glyphs,
    capture_segments,
    clear_capture,
    collect_images,
    download_images,
    install_glyph_hook,
    is_logged_out,
    jump_to_chapter,
    open_weread,
    read_catalog,
    search_books,
    switch_to_paged_mode,
    switch_to_scroll_mode,
    turn_page,
    wait_for_reader,
)

# 页面正文区出现这些字样，说明这一章之后要付费
PAYWALL_MARKS = ("购买", "试读结束", "订阅后继续")

# 连续这么多章一个字都截不到，判定钩子失效
EMPTY_CHAPTER_LIMIT = 3

# 一章之内两次停顿的时长。逐章都要停两回，用短一点的范围；仍是随机，不定死
CHAPTER_PAUSE = (1.0, 2.5)

# 滚动模式取整节用的窗口。窗口越宽，一行装的字越多，撞上画布上限的节越少
SCROLL_VIEWPORT = {"width": 1500, "height": 1000}

# 翻页模式用窄窗口：宽窗口会排成两栏，一栏一栏分开取很麻烦，窄窗口是单栏
PAGED_VIEWPORT = {"width": 800, "height": 1000}

# 翻页模式下每翻一屏的停顿
PAGE_PAUSE = (1.0, 2.0)

# 一节最多翻这么多屏。正常一节 3～15 屏，翻过头说明没认出结尾
MAX_PAGES = 200

# 翻页取数时，每一屏的 y 坐标加一个这么大的基数，免得各屏的段落与图混在一起
PAGE_Y_BASE = 10000


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


def _identify(page, titles, expected=None):
    """屏幕上画的是目录里的哪一条；认不出返回 None。"""
    return identify_chapter(group_lines(capture_glyphs(page)), titles, expected)


# 点完目录后多久没见到目标章名，就认为这一下没跳成
CHAPTER_SWITCH_TIMEOUT = 15.0


# 抓到的字形数要连续这么多次采样都不再增加，才算这一章画完了
RENDER_STABLE_SAMPLES = 3
RENDER_SAMPLE_INTERVAL = 1.0


def _wait_drawn(page, timeout=15.0):
    """等这一章画完：抓到的字形数连续几次采样都不再增加。

    只看画布高度不行：高度在开头就定下来了，字是随后一块块画上去的，
    高度还稳着的时候尾巴可能还没画，截出来就断在句子中间（实测第 10 章
    停在「谁都理」，后面还有字）。
    """
    deadline = time.monotonic() + timeout
    previous = -1
    stable = 0
    while time.monotonic() < deadline:
        captured = page.evaluate("() => (window.__wereadCap || []).length")
        if captured > 0 and captured == previous:
            stable += 1
            if stable >= RENDER_STABLE_SAMPLES - 1:
                return True
        else:
            stable = 0
        previous = captured
        time.sleep(RENDER_SAMPLE_INTERVAL)
    return False


def _wait_for_chapter(page, titles, expected, timeout=CHAPTER_SWITCH_TIMEOUT):
    """等目标条目画出来并画完：标题出现在屏幕第一行，字形也不再增加。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _identify(page, titles, expected) == expected:
            return _wait_drawn(page)
        time.sleep(0.3)
    return False


def _bridge_index(expected, total):
    """跳板用第 1 条；目标就是第 1 条时改用第 2 条，免得跳板原地不动。"""
    if total <= 1:
        return None
    return 1 if expected == 0 else 0


def _goto_chapter(browser, titles, expected):
    """从目录直接跳到目标条目（章或节），确认画出来的是它。

    如果页面本来就停在目标条目上，点目录里那一条不会重画——这时先跳到第 1 条
    （目标就是第 1 条则用第 2 条）再跳回来，用两次真实跳转逼出重画。
    全程不判断「现在停在哪一条」。
    """
    page = browser.page
    title = titles[expected]
    if _identify(page, titles, expected) == expected:
        return True

    bridge = _bridge_index(expected, len(titles))
    for _ in range(2):
        if jump_to_chapter(browser, title, expected) and _wait_for_chapter(page, titles, expected):
            return True
        if bridge is None:
            break
        jump_to_chapter(browser, titles[bridge], bridge)
        _wait_for_chapter(page, titles, bridge, timeout=5.0)
        if jump_to_chapter(browser, title, expected) and _wait_for_chapter(page, titles, expected):
            return True
    return False


def _write_readme(out_dir, book_title, author, source_url, export_date, chapters):
    text = render_readme(book_title, author, source_url, export_date, chapters)
    (out_dir / "README.md").write_text(text, encoding="utf-8")


# 翻页时等新的一屏画出来：字形数有一阵不再增加就算画好了。比整章渲染的判据轻，
# 一屏就这么点字，等三次采样太慢
PAGE_SAMPLE_INTERVAL = 0.4

# 一屏最多等这么久。翻页很快，超过说明这一下没翻动
PAGE_TIMEOUT = 10.0


def _squeeze(text):
    """去掉所有空白。"""
    return "".join((text or "").split())


def _wait_page(page, timeout=PAGE_TIMEOUT):
    """等新的一屏画出来：字形数非零，且与上一采样相同。"""
    deadline = time.monotonic() + timeout
    previous = -1
    while time.monotonic() < deadline:
        captured = page.evaluate("() => (window.__wereadCap || []).length")
        if captured > 0 and captured == previous:
            return True
        previous = captured
        time.sleep(PAGE_SAMPLE_INTERVAL)
    return False


def _starts_other_unit(lines, titles, unit_title):
    """这一屏的第一行是不是别的目录标题——是就说明已经翻过本单元的结尾了。"""
    if not lines:
        return False
    head = _squeeze(lines[0]["text"])
    if not head or head == _squeeze(unit_title):
        return False
    return any(head == _squeeze(title) for title in titles)


def _capture_scroll(browser, book_title, titles, unit):
    """滚动模式下取一个阅读单元（章或节），返回 (段落, 图, 是否被画布截断)。

    屏幕上本来就是这一条时直接用它；不是才清空抓取、从目录跳过去。
    清空会让「已经在目标上」的那一屏消失（点当前条目不会重画），所以不能先清再判。
    """
    page = browser.page
    if _identify(page, titles, unit["index"]) == unit["index"]:
        _wait_drawn(page)
    else:
        clear_capture(page)
        if not _goto_chapter(browser, titles, unit["index"]):
            fail("没能跳到《%s》。停下。" % unit["title"], 3)
    if _paywall(page):
        fail("从《%s》开始拿不到正文：页面要求购买或订阅。到此为止。" % unit["title"], 3)

    lines = group_lines(capture_glyphs(page))
    clipped = is_clipped(lines, canvas_css_heights(page))
    paragraphs = to_paragraphs(strip_noise_lines(lines, book_title, unit["title"]))
    return paragraphs, collect_images(page), clipped


def _capture_paged(browser, book_title, titles, unit):
    """翻页模式下一屏一屏取完整个单元，返回 (段落, 图)。

    窄窗口下翻页模式是单栏一屏，翻一屏读一次抓取；翻到下一单元的第一屏
    （首行是别的目录标题）就停。同一屏偶尔会被重画一遍，按整屏文字去重。
    每一屏的 y 坐标加一个基数，各屏的段落与图不会混到一起。
    """
    page = browser.page
    page.set_viewport_size(PAGED_VIEWPORT)
    if not switch_to_paged_mode(browser):
        fail("切不到翻页模式，没法取完《%s》。停下。" % unit["title"], 3)
    # 切模式前抓到的可能是整节（滚动模式）或别的屏，一律丢掉，从本单元第一屏重新取
    clear_capture(page)
    if not _goto_chapter(browser, titles, unit["index"]):
        fail("没能跳到《%s》。停下。" % unit["title"], 3)
    if _paywall(page):
        fail("从《%s》开始拿不到正文：页面要求购买或订阅。到此为止。" % unit["title"], 3)

    paragraphs = []
    images = []
    seen = set()
    y_base = 0

    for page_no in range(MAX_PAGES):
        if not _wait_page(page):
            print("翻页后没有新内容，按本单元结束处理。", flush=True)
            break
        # 第一屏只取最后一轮：跳转时前面可能还留着上一屏的重画
        segments = [capture_glyphs(page)] if page_no == 0 else capture_segments(page)
        page_height = max(canvas_css_heights(page) or [0])
        added = False
        for segment in segments:
            lines = group_lines(segment)
            text = _squeeze("".join(line["text"] for line in lines))
            if not text or text in seen:
                continue
            if _starts_other_unit(lines, titles, unit["title"]):
                return paragraphs, images
            seen.add(text)
            for paragraph in to_paragraphs(
                strip_noise_lines(lines, book_title, unit["title"])
            ):
                paragraph = dict(paragraph)
                paragraph["y"] += y_base
                paragraphs.append(paragraph)
            for image in collect_images(page):
                if 0 <= image["y"] <= page_height:
                    images.append(dict(image, y=image["y"] + y_base))
            y_base += PAGE_Y_BASE
            added = True

        if not added and page_no > 0:
            return paragraphs, images

        clear_capture(page)
        turn_page(browser)
        browser.human_pause(*PAGE_PAUSE)

    if page_no + 1 >= MAX_PAGES:
        fail("翻到 %d 屏还没取完《%s》。停下。" % (MAX_PAGES, unit["title"]), 3)
    return paragraphs, images


def _place_images(browser, parts, out_dir, prefix):
    """把一个章里各节的图去重下载，再按 src 放回各节。返回放好的图数。"""
    unique = {}
    for part in parts:
        for image in part["images"]:
            unique.setdefault(image["src"], image)
    saved = download_images(browser, list(unique.values()), out_dir / "images", prefix)
    return attach_downloads(parts, saved)


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
        page.set_viewport_size(SCROLL_VIEWPORT)
        install_glyph_hook(browser)
        browser.human_pause()
        if "/web/reader/" not in page.url:
            book = wait_for_reader(page)
            if book is None:
                fail("装完钩子后不在阅读器里了。", 2)

        if switch_to_scroll_mode(browser) is None:
            fail("切不到滚动模式，没法一次拿到整节。", 3)

        # 4. 目录与续跑状态
        items = read_catalog(page)
        chapters = flatten_to_chapters(items)
        if not chapters:
            fail("目录是空的。", 3)
        titles = [item["title"] for item in items]

        files = [
            {
                "file_name": chapter_file_name(pos, len(chapters), chapter["title"]),
                "title": chapter["title"],
                "parents": chapter["parents"],
            }
            for pos, chapter in enumerate(chapters)
        ]
        pos_by_index = {chapter["index"]: pos for pos, chapter in enumerate(chapters)}

        state = load_state(state_path)
        pending = first_pending(chapters, state)
        _write_readme(out_dir, book_title, author, source_url, export_date, files)

        if pending == -1:
            print("目录里每一章都已经导过了，不用再做。")
            return 0

        pos = pos_by_index[pending]
        print(
            "共 %d 章，从第 %d 章《%s》开始。"
            % (len(chapters), pos + 1, chapters[pos]["title"])
        )
        browser.human_pause()
        if not _goto_chapter(browser, titles, chapters[pos]["index"]):
            fail("没能跳到《%s》。停下。" % chapters[pos]["title"], 3)

        # 5. 逐章取：一章一个文件，章里的节写成二级标题
        written = 0
        total_images = 0
        empty_streak = 0

        while pos < len(chapters):
            chapter = chapters[pos]
            file_name = files[pos]["file_name"]
            prefix = file_name.split("-", 1)[0]
            # 有节的章：第一项留给章本身（目录条目只是一张封面，没有正文），
            # 各节写成二级标题。没有节的章（版权信息、推荐序）整章就是一个单元，不加小标题
            units = chapter["parts"]
            parts = (
                [{"title": chapter["title"], "paragraphs": [], "images": []}] if units else []
            )

            for unit in units or [chapter]:
                browser.human_pause(*CHAPTER_PAUSE)
                paragraphs, images, clipped = _capture_scroll(
                    browser, book_title, titles, unit
                )
                if clipped:
                    print(
                        "《%s》画到了画布上限，改翻页取全。" % unit["title"], flush=True
                    )
                    paragraphs, images = _capture_paged(browser, book_title, titles, unit)
                    page.set_viewport_size(SCROLL_VIEWPORT)
                    if switch_to_scroll_mode(browser) is None:
                        fail("切不回滚动模式。停下。", 3)
                    # 切回来会重画整节，但抓取里还留着翻页时的最后一屏，丢掉重取
                    clear_capture(page)
                parts.append(
                    {"title": unit["title"], "paragraphs": paragraphs, "images": images}
                )

            placed = _place_images(browser, parts, out_dir, prefix)
            paragraph_count = sum(len(part["paragraphs"]) for part in parts)

            if paragraph_count == 0 and placed == 0:
                empty_streak += 1
                print("警告：《%s》一个字也没截到，也没有图。" % chapter["title"], file=sys.stderr)
                if empty_streak >= EMPTY_CHAPTER_LIMIT:
                    fail("连续 %d 章都截不到内容，钩子可能已经失效。停下。" % empty_streak, 3)
            else:
                empty_streak = 0

            (out_dir / file_name).write_text(
                render_book_chapter(chapter["title"], parts), encoding="utf-8"
            )
            written += 1
            total_images += placed

            state = mark_done(state, chapter["index"])
            save_state(state_path, state)
            _write_readme(out_dir, book_title, author, source_url, export_date, files)
            print(
                "写完 %s（%d 段，%d 张图）" % (file_name, paragraph_count, placed), flush=True
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
