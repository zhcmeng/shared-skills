# -*- coding: utf-8 -*-
"""微信读书网页阅读器：确认登录、按书名找书、等用户点进阅读器。

这一层全是浏览器上的动作，没有单测——每个行为都要连真站点才有意义。
验证靠探路脚本实跑（见实施计划 Task 7 Step 4）。
"""

from urllib.parse import quote, urljoin

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
    """从 ``书名 - 章节名 - 作者 - 微信读书`` 里拆出书名与作者。

    段数不够就只用第一段当书名，作者留空——宁可少一项，不能张冠李戴。
    """
    parts = [part.strip() for part in (title or "").split(" - ")]
    if parts and parts[-1] == TITLE_SUFFIX:
        parts = parts[:-1]
    if len(parts) >= 3:
        return parts[0], parts[2]
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
