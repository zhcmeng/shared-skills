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
from browser import Browser  # noqa: E402
from markdown import render_book_chapter  # noqa: E402
import weread  # noqa: E402
from weread import (  # noqa: E402
    _hits_from_state,
    _logged_in,
    _logged_in_from_state,
    _parse_title,
    _search_state,
    attach_downloads,
    search_books_page,
    show_search_page,
    wait_for_login,
)


class _FakeResponse:
    def __init__(self, text="", ok=True):
        self._text = text
        self.ok = ok

    def text(self):
        return self._text


class _FakeRequest:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def get(self, url, timeout=None):
        if self.error is not None:
            raise self.error
        return self.response


class _FakeContext:
    def __init__(self, request, cookies=()):
        self.request = request
        self._cookies = list(cookies)

    def cookies(self, urls=None):
        return self._cookies


class FakePage:
    """只提供 search_books_page 和 wait_for_login 用到的几样。"""

    def __init__(
        self,
        response=None,
        error=None,
        dom_hits=None,
        login_states=(),
        cookies=(),
    ):
        self.context = _FakeContext(_FakeRequest(response, error), cookies)
        self.url = "about:blank"
        self.goto_urls = []
        self.dom_hits = dom_hits or []
        self.login_states = list(login_states)

    def goto(self, url, wait_until=None):
        self.goto_urls.append(url)
        self.url = url

    def wait_for_function(self, script, timeout=None):
        return True

    def evaluate(self, script):
        return self.dom_hits

    def wait_for_timeout(self, milliseconds):
        pass


def _state_html(module, user='{"skey":"k"}'):
    return (
        '<script>window.__INITIAL_STATE__={"user":%s,'
        '"searchBooksStoreModule":%s}</script>' % (user, module)
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

    browser = Browser(profile_dir="不存在的配置目录")
    eq(
        "配置目录被占用（退出码 21）时提示关掉别的实例",
        "占用了" in browser._launch_hint(RuntimeError("process did exit: exitCode=21, signal=null")),
        True,
    )
    eq(
        "普通启动失败不误报占用",
        "占用了" in browser._launch_hint(RuntimeError("browser crashed")),
        False,
    )

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

    html = (
        '<script>window.__INITIAL_STATE__={"user":{"skey":"k"},'
        '"searchBooksStoreModule":{"bookInfos":['
        '{"bookInfo":{"title":"估值","author":"甲","readerLink":"https://weread.qq.com/web/reader/x"}},'
        '{"bookInfo":{"title":"估值","author":"甲","readerLink":"https://weread.qq.com/web/reader/x"}}'
        '],"totalCount":48,"hasMore":true}}</script>'
    )
    state = _search_state(html)
    eq("从原始 HTML 读出搜索状态", state["searchBooksStoreModule"]["totalCount"], 48)
    eq(
        "状态里的书按地址去重",
        _hits_from_state(state),
        [
            {
                "title": "估值",
                "author": "甲",
                "href": "https://weread.qq.com/web/reader/x",
            }
        ],
    )
    eq("user 有 skey 算已登录", _logged_in_from_state(state), True)
    eq(
        "user 全空算未登录",
        _logged_in_from_state({"user": {"skey": "", "name": "", "avatar": ""}}),
        False,
    )
    eq("没有状态返回 None", _search_state("<html></html>"), None)
    eq("JSON 坏了返回 None", _search_state("window.__INITIAL_STATE__={bad"), None)

    eq(
        "bookInfos 不是列表时不崩",
        _hits_from_state({"searchBooksStoreModule": {"bookInfos": {"0": {}}}}),
        [],
    )
    eq("user 不是对象时算未登录", _logged_in_from_state({"user": "oops"}), False)
    eq(
        "状态里没登录但 cookie 有 skey 算登录",
        _logged_in(
            FakePage(cookies=[{"name": "wr_skey", "value": "k"}]),
            None,
        ),
        True,
    )
    eq(
        "状态里有登录也算登录",
        _logged_in(FakePage(), {"user": {"skey": "k"}}),
        True,
    )
    eq("cookie 空且状态空算未登录", _logged_in(FakePage(), None), False)

    wanted = "https://weread.qq.com/web/search/books?keyword="
    dom_hit = {"title": "估值", "author": "甲", "href": "/web/reader/x"}
    original_logged_out = weread.is_logged_out
    weread.is_logged_out = lambda page: False
    try:
        page = FakePage(
            response=_FakeResponse(
                _state_html(
                    '{"bookInfos":[{"bookInfo":{"title":"估值","author":"甲",'
                    '"readerLink":"https://x/1"}}],"totalCount":1,"hasMore":false}'
                )
            )
        )
        result = search_books_page(page, "估值")
        eq("状态正常时不导航", page.goto_urls, [])
        eq(
            "状态正常返回四个键",
            sorted(result),
            ["has_more", "hits", "logged_in", "total_count"],
        )
        eq("状态正常取到书", result["hits"][0]["href"], "https://x/1")

        no_state = FakePage(
            response=_FakeResponse("<html></html>"),
            dom_hits=[dom_hit],
            cookies=[{"name": "wr_skey", "value": "k"}],
        )
        result = search_books_page(no_state, "估值")
        eq("没有状态时回退 DOM", no_state.goto_urls[0].startswith(wanted), True)
        eq(
            "回退结果补全地址",
            result["hits"],
            [
                {
                    "title": "估值",
                    "author": "甲",
                    "href": "https://weread.qq.com/web/reader/x",
                }
            ],
        )
        eq("回退时登录状态取自页面", result["logged_in"], True)
        eq("回退时没有总数", result["total_count"], None)

        bad_json = FakePage(
            response=_FakeResponse("window.__INITIAL_STATE__={bad"),
            dom_hits=[dom_hit],
        )
        search_books_page(bad_json, "估值")
        eq("JSON 坏了也回退 DOM", len(bad_json.goto_urls), 1)

        broken = FakePage(
            response=_FakeResponse(_state_html('{"bookInfos":{"0":{}}}')),
            dom_hits=[dom_hit],
        )
        search_books_page(broken, "估值")
        eq("结构变了也回退 DOM", len(broken.goto_urls), 1)

        no_infos = FakePage(
            response=_FakeResponse(_state_html('{"totalCount":0}')),
            dom_hits=[dom_hit],
        )
        search_books_page(no_infos, "估值")
        eq("没有 bookInfos 也回退 DOM", len(no_infos.goto_urls), 1)
    finally:
        weread.is_logged_out = original_logged_out

    show_page = FakePage()
    show_search_page(show_page, "财经（2026年第5期）")
    eq(
        "显示搜索页的地址",
        show_page.goto_urls,
        [
            "https://weread.qq.com/web/search/books?keyword="
            "%E8%B4%A2%E7%BB%8F%EF%BC%882026%E5%B9%B4%E7%AC%AC5%E6%9C%9F%EF%BC%89"
        ],
    )

    original_logged_out = weread.is_logged_out
    try:

        def fake_logged_out(page):
            return page.login_states.pop(0) if page.login_states else False

        weread.is_logged_out = fake_logged_out
        login_page = FakePage(login_states=[False])
        eq("已登录不等待", wait_for_login(login_page, timeout=0), True)
        eq("登录前先开首页", login_page.goto_urls, ["https://weread.qq.com/"])

        login_page = FakePage(login_states=[True, True, False])
        eq("扫码后继续", wait_for_login(login_page, timeout=300), True)

        login_page = FakePage(login_states=[True])
        eq("等不到登录返回 False", wait_for_login(login_page, timeout=0), False)
    finally:
        weread.is_logged_out = original_logged_out

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
