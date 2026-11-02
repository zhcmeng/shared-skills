# -*- coding: utf-8 -*-
"""起一个看得见的浏览器，所有操作按真人的来。

两件事在这里落地：

1. **看得见**：``headless`` 默认给 ``False``。Playwright 自己的默认值是
   ``True``，不写就会起一个看不见的窗口，用户既没法扫码登录，也没法选书。
2. **像人**：点击先滚到视野里、光标分几步滑过去、按下与抬起之间留点时间；
   滚动前光标先停在页面中间；动作之间停一段随机的时长（默认 2～6 秒，
   逐章循环里用 1～2.5 秒）。
"""

import os
import random
import sys
import time
from pathlib import Path

DEFAULT_CHANNEL = "msedge" if sys.platform == "win32" else "chrome"

# 动作之间停多久：随机取区间内一个值，不固定
PAUSE_LOW = 2.0
PAUSE_HIGH = 6.0

# 鼠标移动插值出几条 mousemove；点击时按下与抬起之间隔多少毫秒
MOVE_STEPS = (8, 20)
CLICK_DELAY_MS = (50, 150)


class BrowserError(RuntimeError):
    """浏览器起不来、点不到、页面不对之类的问题，统一用它报。"""


def default_base_dir():
    """配置与状态的根目录。Windows 用 LOCALAPPDATA，其他系统用配置目录。"""
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        root = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(root) / "weread-book-export"


def default_profile_dir():
    """浏览器配置目录；里面装着登录态，所以放在仓库外。

    不要放进仓库的 ``.tmp/``：那里按仓库规矩任务做完要删，删了就得重新扫码。
    """
    return default_base_dir() / "browser-profile"


class Browser:
    """一个看得见的浏览器窗口。

    用 ``with Browser() as b:`` 起，出来时自动关。Playwright 的同步 API
    不是线程安全的，所有浏览器调用都留在创建它的那个线程里。
    """

    def __init__(self, profile_dir=None, channel=None, headless=False):
        self.profile_dir = str(profile_dir or default_profile_dir())
        self.channel = channel or DEFAULT_CHANNEL
        self.headless = headless
        self.context = None
        self.page = None
        self._playwright = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    # ---- 启停 ------------------------------------------------------

    def start(self):
        # playwright 只在真要开浏览器时才 import，纯逻辑模块和它们的测试不因此要求装它
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserError(
                "没装 playwright。这个技能要开浏览器取正文，命令得用 "
                "`uv run --with playwright` 跑。"
            ) from exc

        self._playwright = sync_playwright().start()
        try:
            self.context = self._playwright.chromium.launch_persistent_context(
                self.profile_dir,
                channel=self.channel,
                headless=self.headless,
                args=["--no-first-run", "--no-default-browser-check"],
            )
        except Exception as exc:
            self._playwright.stop()
            self._playwright = None
            raise BrowserError(self._launch_hint(exc)) from exc

        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    def _launch_hint(self, exc):
        text = str(exc)
        bits = ["打不开浏览器（配置目录：%s）。" % self.profile_dir]
        lowered = text.lower()
        if (
            "processsingleton" in lowered
            or "already in use" in lowered
            or "user data directory" in lowered
        ):
            bits.append(
                "这个配置目录已经被另一个浏览器占用了——先把开着同一个"
                "配置目录的 Edge/Chrome 窗口全部关掉，再重跑。"
            )
        bits.append(
            "默认用 %s；机器上没有这个浏览器时，用 --browser-channel 换一个，"
            "或者先跑 `uv run --with playwright playwright install chromium` "
            "再指定 --browser-channel chromium。" % self.channel
        )
        bits.append("Playwright 的原话：%s" % text)
        return "\n".join(bits)

    def close(self):
        if self.context is not None:
            try:
                self.context.close()
            except Exception:
                pass
            self.context = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    # ---- 拟人化动作 -------------------------------------------------

    def human_pause(self, low=PAUSE_LOW, high=PAUSE_HIGH):
        """故意停一下，做出人在读的节奏。

        这是**故意加的等待**，不是在等某个页面条件，所以用普通睡眠；
        等页面状态另有一套，一律走 ``wait_for_function`` 或 locator 自带的
        自动等待，绝不拿固定时长去等页面变化。也别用 ``page.wait_for_timeout``
        ——它在 Playwright 文档里标着 Deprecated，写着 "Never wait for timeout
        in production"。
        """
        time.sleep(random.uniform(low, high))

    def click_locator(self, locator):
        """像人一样点一个元素：先滚进视野，光标分几步滑过去，停顿，再按下抬起。"""
        locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
        if box is None:
            raise BrowserError("要点的东西没有可见区域，可能被遮住了，或者已经不在页面上。")
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        self.page.mouse.move(x, y, steps=random.randint(*MOVE_STEPS))
        time.sleep(random.uniform(0.08, 0.25))
        self.page.mouse.click(x, y, delay=random.randint(*CLICK_DELAY_MS))
