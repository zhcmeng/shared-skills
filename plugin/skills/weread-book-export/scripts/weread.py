# -*- coding: utf-8 -*-
"""微信读书网页阅读器：确认登录、按书名找书、等用户点进阅读器。

这一层全是浏览器上的动作，没有单测——每个行为都要连真站点才有意义。
验证靠探路脚本实跑（见实施计划 Task 7 Step 4）。
"""

import random
import time
from pathlib import Path
from urllib.parse import quote, urljoin

from layout import last_render

WEREAD_HOME = "https://weread.qq.com/"
SEARCH_URL = "https://weread.qq.com/web/search/books?keyword=%s"
READER_MARK = "/web/reader/"

# document.title 的固定尾巴：「书名 - 章节名 - 作者 - 微信读书」
TITLE_SUFFIX = "微信读书"

# 等用户点开一本书，默认给 5 分钟
READER_TIMEOUT = 300.0

# 搜索结果里每条书目的链接都带这个标记。按链接选，不按 CSS 类名选——
# 类名改版就会变，链接结构不会。
_SEARCH_JS = """() => [...document.querySelectorAll('a[href*="/web/reader/"]')].map(a => {
  const item = a.closest('li') || a.parentElement;
  const lines = (item ? item.innerText : '').split('\\n').map(s => s.trim()).filter(Boolean);
  return { title: lines[0] || '', author: lines[1] || '', href: a.getAttribute('href') };
})"""


def on_reader_page(page):
    """当前页面是不是某本书的阅读器。"""
    return READER_MARK in page.url


def open_weread(page):
    """进微信读书首页；页面上已经开着某本书就原地不动。

    返回「进来时是否已经开着书」。**不能无脑导航**：用户可能已经把书打开了，
    一导航就把书顶掉，还得重新找。
    """
    if on_reader_page(page):
        return True
    page.goto(WEREAD_HOME, wait_until="domcontentloaded")
    return False


def is_logged_out(page):
    """页面上有「登录」按钮、又看不到用户头像，就当没登录。

    拿不准时宁可返回 True：误报登录只是多扫一次码，漏报会让后面每一步都失败。
    """
    try:
        login = page.get_by_text("登录", exact=True)
        if login.count() == 0 or not login.first.is_visible():
            return False
        avatar = page.locator("[class*='avatar'], [class*='Avatar']")
        return avatar.count() == 0
    except Exception:
        return True


def search_books(page, title):
    """按书名搜索，返回候选 ``[{"title": str, "author": str, "href": str}, ...]``。

    同一本书在结果里往往有好几个链接（封面一个、标题一个），按 ``href`` 去重，
    顺序保持页面上的先后。**不替用户挑第一条**——同名书和不同版本会弄错。
    """
    page.goto(SEARCH_URL % quote(title), wait_until="domcontentloaded")
    try:
        page.wait_for_function(
            """() => document.querySelectorAll('a[href*="/web/reader/"]').length > 0""",
            timeout=30000,
        )
    except Exception:
        return []

    hits = []
    seen = set()
    for item in page.evaluate(_SEARCH_JS):
        href = (item.get("href") or "").strip()
        if not href or href in seen:
            continue
        seen.add(href)
        hits.append(
            {
                "title": item.get("title") or "",
                "author": item.get("author") or "",
                "href": urljoin(WEREAD_HOME, href),
            }
        )
    return hits


def _parse_title(title):
    """从 ``document.title`` 里拆出书名与作者。

    实测两种形状：
    ``书名 - 章名 - 作者 - 微信读书``（进了某一章），
    ``书名 - 作者 - 微信读书``（还没进章）。去掉尾巴后按段数分。
    段数不够就只用第一段当书名，作者留空——宁可少一项，不能张冠李戴。
    """
    parts = [part.strip() for part in (title or "").split(" - ")]
    if parts and parts[-1] == TITLE_SUFFIX:
        parts = parts[:-1]
    if len(parts) >= 3:
        return parts[0], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1]
    return (parts[0] if parts else ""), ""


def wait_for_reader(page, timeout=READER_TIMEOUT):
    """等用户把一本书点开，返回 ``{"book_id", "book_title", "author"}``；超时返回 None。

    挂的是「地址变成阅读器」这个事件，不是定时去问——人不点就一直等着，
    点了立刻往下走。
    """
    try:
        page.wait_for_url("**/web/reader/**", timeout=timeout * 1000)
    except Exception:
        return None

    tail = page.url.split(READER_MARK, 1)[1]
    book_id = tail.split("?", 1)[0].split("#", 1)[0].strip("/").split("/")[0]
    book_title, author = _parse_title(page.title())
    return {"book_id": book_id, "book_title": book_title, "author": author}


# 模式按钮是**切换**用的，类名跟着当前状态变：滚动态叫 isNormalReader，
# 翻页态叫 isHorizontalReader。两个都要匹配，否则换个状态就找不到按钮。
MODE_BUTTON = ".readerControls_item.isHorizontalReader, .readerControls_item.isNormalReader"
CATALOG_BUTTON = ".readerControls_item.catalog"
CATALOG_ITEM = ".readerCatalog li"

_CANVAS_HEIGHTS_JS = """() => [...document.querySelectorAll('.wr_canvasContainer canvas')]
    .map(c => c.height)"""

_CATALOG_JS = """() => [...document.querySelectorAll('.readerCatalog li')].map(li => {
  const titleEl = li.querySelector('.readerCatalog_list_item_title_text');
  const lines = (li.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean);
  const levelEl = li.querySelector('[class*="readerCatalog_list_item_level_"]');
  const fromClass = levelEl && String(levelEl.className).match(/readerCatalog_list_item_level_(\\d+)/);
  let depth = 0;
  let node = li;
  while (node.parentElement && node.parentElement.closest('li')) {
    depth += 1;
    node = node.parentElement.closest('li');
  }
  return {
    title: (titleEl ? titleEl.innerText : lines[0] || '').trim(),
    level: Math.max(fromClass ? parseInt(fromClass[1], 10) : 1, depth + 1),
  };
})"""

# 目录项的标题要取里面的 .readerCatalog_list_item_title_text：
# li 的 innerText 还会混进「当前读到 3%+书签」这类角标，拿它比对章节名会对不上
_CATALOG_TITLES_JS = """() => [...document.querySelectorAll('.readerCatalog li')].map(li => {
  const titleEl = li.querySelector('.readerCatalog_list_item_title_text');
  if (titleEl) return titleEl.innerText.trim();
  return ((li.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean))[0] || '';
})"""

_CATALOG_OPEN_JS = """() => { const el = document.querySelector('.readerCatalog');
    return !!el && getComputedStyle(el).display !== 'none'; }"""


def _canvas_heights(page):
    try:
        return page.evaluate(_CANVAS_HEIGHTS_JS)
    except Exception:
        return []


def canvas_height(page, timeout=30000):
    """主画布的高度。滚动模式下整章铺开，翻页模式下只有一屏高。"""
    try:
        page.wait_for_function(
            """() => document.querySelectorAll('.wr_canvasContainer canvas').length > 0""",
            timeout=timeout,
        )
    except Exception:
        return 0
    heights = _canvas_heights(page)
    return max(heights) if heights else 0


def reader_mode(page):
    """当前阅读模式：``"scroll"``（整章铺开）/ ``"horizontal"``（翻页）/ ``None``（认不出）。

    判据只能是模式按钮的类名，**不能拿画布高度当模式**：短章（实测附录整章只有
    476px）在滚动模式下也没多高，按高度判会被当成翻页态，于是反复点按钮切换。
    """
    button = page.locator(MODE_BUTTON)
    if button.count() == 0:
        return None
    klass = button.first.get_attribute("class") or ""
    if "isHorizontalReader" in klass:
        return "horizontal"
    if "isNormalReader" in klass:
        return "scroll"
    return None


def is_scroll_mode(page):
    """是不是滚动模式。"""
    return reader_mode(page) == "scroll"


def switch_to_scroll_mode(browser, timeout=20.0):
    """切到滚动模式，返回当前画布高度；切不过去返回 None。

    按钮是开关、点了偶尔被吞掉，所以边看类名边补点。已经处于滚动模式时**绝不补点**
    ——那一下会切到翻页态。切过去之后还要等画布真正建出来（刷新后有一两秒是空的），
    短章的画布本来就矮，所以「有了」就算成，不按高度卡。
    """
    page = browser.page
    deadline = time.monotonic() + timeout
    last_click = 0.0
    while time.monotonic() < deadline:
        mode = reader_mode(page)
        if mode == "scroll":
            height = canvas_height(page, timeout=3000)
            if height > 0:
                return height
        elif mode == "horizontal" and time.monotonic() - last_click > 2.0:
            try:
                browser.click_locator(page.locator(MODE_BUTTON).first)
                last_click = time.monotonic()
            except Exception:
                pass
        time.sleep(0.5)
    return None


def read_catalog(page):
    """读目录，按页面上的顺序返回 ``[{"title": str, "level": int}, ...]``。

    目录面板默认 ``display: none``，但条目已经在 DOM 里，不用点开就能读——
    读取不碰界面，少一次会被看见的操作。层级优先取类名里的
    ``readerCatalog_list_item_level_N``；平铺的书没有这个类，用 DOM 嵌套深度算。
    """
    try:
        page.wait_for_function(
            """() => document.querySelectorAll('.readerCatalog li').length > 0""",
            timeout=30000,
        )
    except Exception:
        return []
    return page.evaluate(_CATALOG_JS)


def _catalog_open(page):
    try:
        return bool(page.evaluate(_CATALOG_OPEN_JS))
    except Exception:
        return False


def _click_catalog_button(browser, tries=3):
    """点目录按钮。工具栏会重新渲染，偶尔点到已经脱离 DOM 的旧节点，所以要重试。"""
    page = browser.page
    for _ in range(tries):
        try:
            browser.click_locator(page.locator(CATALOG_BUTTON).first)
            return True
        except Exception:
            continue
    return False


def _open_catalog(browser, tries=3):
    page = browser.page
    for _ in range(tries):
        if _catalog_open(page):
            return True
        if not _click_catalog_button(browser):
            continue
        try:
            page.wait_for_function(_CATALOG_OPEN_JS, timeout=5000)
            return True
        except Exception:
            continue
    return False


def _close_catalog(browser):
    """目录面板留着会挡住后面的点击，用完就关。

    关法是再点一次目录按钮（按钮是开关）。实测点空白处和按 Esc 都关不掉，
    点遮罩也不行。
    """
    if _catalog_open(browser.page):
        _click_catalog_button(browser)


def jump_to_chapter(browser, title, index=None):
    """在目录里找到标题**完全相等**的那一条，点一下。点到返回 True。

    给了 ``index`` 就按目录位置点：同名章（如「附录」出现两次）只按标题找会
    一路点到第一条。位置对不上标题时退回按标题找。

    **这里不判断跳没跳成**：跳没跳成由调用方按屏幕上的字认（见
    ``layout.identify_chapter``）。拿标题判断不行——版权信息、扉页这类前置页的
    ``document.title`` 里没有章名；拿「抓到的字变多了」判断也不行——点目录里
    当前所在的那一章根本不会重画。
    """
    page = browser.page
    for _ in range(3):
        if not _open_catalog(browser):
            continue

        try:
            titles = page.evaluate(_CATALOG_TITLES_JS)
        except Exception:
            continue

        if index is not None and (not 0 <= index < len(titles) or titles[index] != title):
            index = None
            continue
        if index is None:
            if title not in titles:
                _close_catalog(browser)
                return False
            position = titles.index(title)
        else:
            position = index

        item = page.locator(CATALOG_ITEM).nth(position)
        try:
            browser.click_locator(item)
        except Exception:
            continue

        _close_catalog(browser)
        return True

    _close_catalog(browser)
    return False


# 挂在 CanvasRenderingContext2D.prototype.fillText 外面，把每次绘字记下来。
# 正文是画在 canvas 里的，DOM 里一个字都没有，这是拿原文的唯一口子。
GLYPH_HOOK = """(() => {
  const P = CanvasRenderingContext2D.prototype;
  if (P.__wereadHooked) return;
  P.__wereadHooked = true;
  const original = P.fillText;
  P.fillText = function (t, x, y, ...rest) {
    try {
      if (t && String(t).trim()) {
        (window.__wereadCap ||= []).push({ t: String(t), x, y, font: this.font });
      }
    } catch {}
    return original.call(this, t, x, y, ...rest);
  };
})();"""

# 一次取多少条记录。一章两三千条，整份一次取序列化后几百 KB，容易超时
CAPTURE_CHUNK = 2000


def install_glyph_hook(browser):
    """装上绘字钩子，并让当前这一章带着钩子重画一遍。

    钩子必须挂在 context 上，不能只 evaluate 一次：已经渲染好的章节滚动不会重绘，
    脚本装晚了就一个字都截不到。``context.add_init_script`` 的触发条件是「新建页面
    或任何一次导航」，执行时机是「document 已建、页面自己的脚本还没跑」。

    **代价**：末尾的 reload 会把阅读位置退回本章开头，所以必须在进书之后调用；
    调用完要重新确认还在阅读器里、还在滚动模式下。
    """
    browser.context.add_init_script(script=GLYPH_HOOK)
    browser.page.reload(wait_until="domcontentloaded")


def clear_capture(page):
    """清空已经截到的字形，准备截下一章。"""
    page.evaluate("() => { window.__wereadCap = []; }")


def wait_canvas_ready(page, timeout=30.0):
    """等这一章画完：画布高度连续两次一样，且已经截到字。"""
    deadline = time.monotonic() + timeout
    previous = -1
    while time.monotonic() < deadline:
        height = canvas_height(page, timeout=1000)
        captured = page.evaluate("() => (window.__wereadCap || []).length")
        if captured > 0 and height > 0 and height == previous:
            return True
        previous = height
        time.sleep(0.5)
    return False


def capture_glyphs(page):
    """把钩子记下的字形分片取回来，只留**最后一轮绘制**。

    分片取、不整份取：一章两三千条记录序列化后几百 KB，单次 evaluate 容易超时。
    翻章时阅读器会先把上一屏重画一遍再画目标那一章，两轮都记在这里，交给
    ``last_render`` 切掉前面那一轮（见 layout.last_render）。
    """
    total = page.evaluate("() => (window.__wereadCap || []).length")
    glyphs = []
    for start in range(0, total, CAPTURE_CHUNK):
        glyphs.extend(
            page.evaluate(
                "([from, count]) => (window.__wereadCap || []).slice(from, from + count)",
                [start, CAPTURE_CHUNK],
            )
        )
    return last_render(glyphs)


# 每次滚多少屏、滚几段：分段滚，像人在读，不一次跳到底
SCROLL_STEPS = (8, 15)
SCROLL_RANGE = (0.6, 1.0)

# 下图之间的间隔（秒）
IMAGE_PAUSE = (0.1, 0.3)
IMAGE_TIMEOUT = 60000
CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def scroll_through_chapter(browser):
    """把这一章从头滚到底，像人在读。

    滚一遍还有一个用处：让画布下方、一开始没进视野的插图也加载出来。
    """
    page = browser.page
    size = page.viewport_size
    if not size:
        size = page.evaluate("() => ({width: innerWidth, height: innerHeight})")
    viewport = size["height"] or 800

    for _ in range(random.randint(*SCROLL_STEPS)):
        browser.wheel(viewport * random.uniform(*SCROLL_RANGE))
        browser.human_pause()


def collect_images(page):
    """取本章插图，返回 ``[{"src": str, "y": float, "alt": str}, ...]``，按 src 去重。

    ``y`` 是图片相对主画布顶端的偏移：图和画布在同一个滚动容器里，
    滚不滚动这个差值都一样，正好和字形记录的坐标系对齐。
    """
    data = page.evaluate(
        """() => {
          const canvas = document.querySelector('.wr_canvasContainer canvas');
          const top = canvas ? canvas.getBoundingClientRect().top : 0;
          return [...document.querySelectorAll('.renderTargetContainer img')]
            .filter(img => img.src && img.src.indexOf('res.weread.qq.com') >= 0)
            .map(img => ({
              src: img.src,
              alt: img.alt || '',
              y: img.getBoundingClientRect().top - top,
            }));
        }"""
    )

    seen = set()
    images = []
    for item in data:
        if item["src"] in seen:
            continue
        seen.add(item["src"])
        images.append(item)
    return images


def download_images(browser, images, out_dir, prefix):
    """逐张下载，返回 ``[{"src": ..., "file_name": ...}]``。

    走 ``context.request``：它自带同一个浏览器的 Cookie，也默认跟随跳转，不用另装
    requests。**必须带 Referer**——不带会被 302 到空响应。扩展名按响应头定，
    CDN 地址的后缀不可靠。
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for index, image in enumerate(images, start=1):
        response = browser.context.request.get(
            image["src"], headers={"Referer": WEREAD_HOME}, timeout=IMAGE_TIMEOUT
        )
        if not response.ok:
            continue
        content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
        extension = CONTENT_TYPE_EXT.get(content_type, ".jpg")
        file_name = "%s-%03d%s" % (prefix, index, extension)
        (out_dir / file_name).write_bytes(response.body())
        saved.append({"src": image["src"], "file_name": file_name})
        time.sleep(random.uniform(*IMAGE_PAUSE))
    return saved
