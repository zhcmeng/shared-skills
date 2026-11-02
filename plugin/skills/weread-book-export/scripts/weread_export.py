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
from content import blocks_to_part, matches_screen
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
    install_capture_hooks,
    is_logged_out,
    jump_to_chapter,
    open_weread,
    pre_render_blocks,
    read_catalog,
    search_books,
    switch_to_paged_mode,
    switch_to_scroll_mode,
    turn_back_page,
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

# 翻页模式用窄窗口：宽窗口会排成两栏，一栏一栏分开取很麻烦，窄窗口是单栏。
# 窗口调高，一屏能多装几倍的字，长节要翻的屏数跟着少几倍
PAGED_VIEWPORT = {"width": 800, "height": 3000}

# 翻页模式下每翻一屏的停顿
PAGE_PAUSE = (1.0, 2.0)

# 翻页模式下整页都是图、一个字都没有的屏，安静这么久就收下
PAGE_EMPTY_SETTLE = 2.5

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

# 地址已经变了、标题却还没出现时，再给标题这么多秒
TITLELESS_GRACE = 1.5

# 不画目录标题的前置页（如「文前」）等画稳的时长
TITLELESS_TIMEOUT = 6.0


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


def _wait_titleless_page(page, timeout=TITLELESS_TIMEOUT):
    """等一张不画目录标题的页画稳。

    这类页多半是整页图（实测《这里是中国》的「文前」只画了「-特别鸣谢-」
    几个字，另配几张图）。先按整章的标准等字画完；一个字都没有时，再等
    画布尺寸连续两次采样相同。
    """
    if _wait_drawn(page, timeout=timeout):
        return True
    deadline = time.monotonic() + 2.0
    previous = None
    while time.monotonic() < deadline:
        heights = canvas_css_heights(page)
        if not heights:
            return False
        if heights == previous:
            return True
        previous = heights
        time.sleep(0.4)
    return False


def _wait_for_chapter(
    page, titles, expected, timeout=CHAPTER_SWITCH_TIMEOUT, before_url=None
):
    """等目标画出来并画完：标题出现在屏幕第一行，字形也不再增加。

    给了 ``before_url`` 时，地址变了、标题又一直不出现，说明这是一张不画
    目录标题的前置页，按「已经翻到新的一页」处理。
    """
    deadline = time.monotonic() + timeout
    changed_at = None
    while time.monotonic() < deadline:
        if _identify(page, titles, expected) == expected:
            return _wait_drawn(page)
        if before_url is not None and page.url != before_url:
            if changed_at is None:
                changed_at = time.monotonic()
            elif time.monotonic() - changed_at >= TITLELESS_GRACE:
                return _wait_titleless_page(page)
        time.sleep(0.3)
    return False


def _jump_and_confirm(browser, titles, expected):
    """点目录里的目标条，确认落到了新的一页。

    「标题在第一行」是最可靠的确认。有的前置页不画目录标题，这时地址变了
    就说明确实翻到了另一章，等这一页画稳即收。
    """
    page = browser.page
    before = page.url
    if not jump_to_chapter(browser, titles[expected], expected):
        return False
    return _wait_for_chapter(page, titles, expected, before_url=before)


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
    if _identify(page, titles, expected) == expected:
        return True

    bridge = _bridge_index(expected, len(titles))
    for _ in range(2):
        if _jump_and_confirm(browser, titles, expected):
            return True
        if bridge is None:
            break
        jump_to_chapter(browser, titles[bridge], bridge)
        _wait_for_chapter(page, titles, bridge, timeout=5.0)
        if _jump_and_confirm(browser, titles, expected):
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
    """等新的一屏画稳。

    有字的屏等字形数不再增加；整页都是图的屏一个字都没有，安静一会儿就收下
    ——摄影书里这样的屏很常见，不能当成「没有新内容」。
    """
    deadline = time.monotonic() + timeout
    previous = -1
    zero_since = None
    while time.monotonic() < deadline:
        captured = page.evaluate("() => (window.__wereadCap || []).length")
        if captured > 0 and captured == previous:
            return True
        if captured == 0:
            if zero_since is None:
                zero_since = time.monotonic()
            elif time.monotonic() - zero_since >= PAGE_EMPTY_SETTLE:
                return True
        else:
            zero_since = None
        previous = captured
        time.sleep(PAGE_SAMPLE_INTERVAL)
    return False


def _wait_url(page, url, timeout=CHAPTER_SWITCH_TIMEOUT):
    """等地址变成指定的那一个。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if page.url == url:
            return True
        time.sleep(0.3)
    return False


def _wait_url_change(page, before, timeout=CHAPTER_SWITCH_TIMEOUT):
    """等地址从 ``before`` 换走。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if page.url != before:
            return True
        time.sleep(0.3)
    return False


def _starts_other_unit(lines, titles, unit_title):
    """这一屏的第一行是不是别的目录标题——是就说明已经翻过本单元的结尾了。"""
    if not lines:
        return False
    head = _squeeze(lines[0]["text"])
    if not head or head == _squeeze(unit_title):
        return False
    return any(head == _squeeze(title) for title in titles)


def _capture_scroll(browser, book_title, titles, unit, nested=False):
    """滚动模式下取一个阅读单元（章或节），返回 (段落, 图, 是否被画布截断)。

    优先用阅读器预渲染的整章 HTML：它就是完整的一章，不受「滚动模式只画两块
    画布」的限制。截不到（没有预渲染步骤的格式，PDF、导入书可能是这类，尚未
    实测）才退回截字形，
    那一套要判断画布有没有被截断。

    屏幕上本来就是这一条时不能直接取：预渲染里可能还是上一页的 HTML。reload
    会停在当前这一节并整节重画，截到的就是这一节。
    """
    page = browser.page
    if _identify(page, titles, unit["index"]) == unit["index"]:
        clear_capture(page)
        page.reload(wait_until="domcontentloaded")
        wait_for_reader(page)
        switch_to_scroll_mode(browser)
        _wait_drawn(page)
    else:
        clear_capture(page)
        if not _goto_chapter(browser, titles, unit["index"]):
            fail("没能跳到《%s》。停下。" % unit["title"], 3)
    if _paywall(page):
        fail("从《%s》开始拿不到正文：页面要求购买或订阅。到此为止。" % unit["title"], 3)

    # 预渲染的 HTML 在画字之前就赋值好了；跳到目标、等它画稳之后，截到的一定是这一节。
    # 仍拿屏幕上画出的几行核一次：万一阅读器顺手把下一节也预渲染了，截到的是后一份
    lines = group_lines(capture_glyphs(page))
    blocks = pre_render_blocks(page)
    if blocks and matches_screen(
        blocks, [line["text"] for line in lines], unit["title"], book_title
    ):
        paragraphs, images = blocks_to_part(blocks, unit["title"], nested=nested)
        if paragraphs or images:
            return paragraphs, images, False
    # 点目录里当前这一条不会重画，_goto_chapter 会借道目录第 1 条再跳回来，
    # 那一页的字可能混进抓取（整页版权信息重复出现在正文里）。看到桥接页的
    # 标题就重画一遍再取——reload 会停在当前这一节并整节重画。
    bridge = _bridge_index(unit["index"], len(titles))
    if bridge is not None:
        bridge_key = _squeeze(titles[bridge])
        if (
            bridge_key
            and bridge_key != _squeeze(unit["title"])
            and any(_squeeze(line["text"]) == bridge_key for line in lines)
        ):
            page.reload(wait_until="domcontentloaded")
            wait_for_reader(page)
            switch_to_scroll_mode(browser)
            _wait_drawn(page)
            lines = group_lines(capture_glyphs(page))

    clipped = is_clipped(lines, canvas_css_heights(page))
    paragraphs = to_paragraphs(strip_noise_lines(lines, book_title, unit["title"]))
    return paragraphs, collect_images(page), clipped


def _capture_paged(browser, book_title, titles, unit):
    """翻页模式下一屏一屏取完整个单元，返回 (段落, 图)。

    窄窗口下翻页模式是单栏一屏，翻一屏读一次抓取。这一节的屏不会画目录标题
    （首行就是正文），所以不能按「首行是别的标题」认结尾——按**地址**认：
    翻到下一节时阅读器会把地址换成那一节的 id。地址没变就继续翻；连翻两屏
    既没有新字也没有新图，说明翻到头了。

    整页都是图的屏一个字都没有，照样收图。同一张图别的节可能已经预加载进
    页面，按 ``src`` 去重，只收本屏范围里的。各行、各图的 y 坐标加一个基数，
    各屏的内容不会混到一起。
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

    # 翻页模式会停在这本书上次读到的位置，可能已经是本节的末尾。先跳到第 1 条目录
    # 再跳回来，阅读器才会把位置重置到本节第一屏（实测这样做才从节首开始）。
    # 跳回来之前清空抓取，留下的就都是本节第一屏的字。
    unit_url = page.url
    bridge = _bridge_index(unit["index"], len(titles))
    if bridge is not None:
        before = page.url
        if not jump_to_chapter(browser, titles[bridge], bridge):
            fail(
                "跳不到《%s》，没法把《%s》翻回节首。停下。"
                % (titles[bridge], unit["title"]),
                3,
            )
        if not _wait_url_change(page, before):
            fail(
                "点了《%s》地址没变，没法把《%s》翻回节首。停下。"
                % (titles[bridge], unit["title"]),
                3,
            )
        clear_capture(page)
        if not jump_to_chapter(browser, titles[unit["index"]], unit["index"]):
            fail("没能跳回《%s》。停下。" % unit["title"], 3)
        if not _wait_url(page, unit_url):
            fail("跳回《%s》后地址没换回来。停下。" % unit["title"], 3)

    # 确认真的在第一节：向右翻一屏再翻回来，回来的就是本节第一屏。
    # 一翻就出了本节，说明停在了末尾，宁可停下也不把后半段当成全部。
    clear_capture(page)
    turn_page(browser)
    browser.human_pause(*PAGE_PAUSE)
    if not _wait_page(page):
        fail("翻页后没有新内容，没法确认《%s》的节首。停下。" % unit["title"], 3)
    if page.url != unit_url:
        fail("《%s》一翻就出了本节，没能回到节首。停下。" % unit["title"], 3)
    clear_capture(page)
    turn_back_page(browser)
    browser.human_pause(*PAGE_PAUSE)

    paragraphs = []
    images = []
    seen = set()
    seen_images = set()
    y_base = 0
    unchanged = 0

    for page_no in range(MAX_PAGES):
        if not _wait_page(page):
            print("翻页后没有新内容，按本单元结束处理。", flush=True)
            break
        # 地址换成下一节了，这一节已经翻完；这一屏属于下一节，不收
        if page.url != unit_url:
            break
        # 第一屏只取最后一轮：跳转时前面可能还留着上一屏的重画
        segments = [capture_glyphs(page)] if page_no == 0 else capture_segments(page)
        page_height = max(canvas_css_heights(page) or [0])
        page_images = [
            image
            for image in collect_images(page)
            if 0 <= image["y"] <= page_height and image["src"] not in seen_images
        ]

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
            added = True

        for image in page_images:
            images.append(dict(image, y=image["y"] + y_base))
            seen_images.add(image["src"])
            added = True

        if added:
            y_base += PAGE_Y_BASE
            unchanged = 0
        else:
            unchanged += 1
            if unchanged >= 2:
                return paragraphs, images

        clear_capture(page)
        turn_page(browser)
        browser.human_pause(*PAGE_PAUSE)
    else:
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
        install_capture_hooks(browser)
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
                    browser, book_title, titles, unit, nested=bool(units)
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
