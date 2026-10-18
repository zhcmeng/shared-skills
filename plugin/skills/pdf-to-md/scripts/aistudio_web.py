"""跟 AI Studio 官网的网页解析打交道：登录、上传、等任务、下载 JSON。

这个模块顶层不 import playwright——只有真要开浏览器时才在函数里 import。
这样 `--backend api` 和跑测试都不需要装 playwright。
"""
import json
import os
import re
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass

import requests

NEW_TASK_URL = "https://aistudio.baidu.com/paddleocr/task/new"
TASK_URL_MARKER = "/paddleocr/task/file/"
DETAIL_URL = ("https://aistudio.baidu.com/paddlex/v3/ocr/tasks/{task_id}/detail"
              "?taskId={task_id}")

# 实测：4 是解析中，5 是完成，-5 是失败（假 PDF 触发过）。负数是失败，
# 其余非负值都按「还在跑」处理，直到超时。
DONE_STATUS = 5

DEFAULT_CHANNEL = "msedge" if sys.platform == "win32" else "chrome"

DEFAULT_WEB_TIMEOUT = 3600.0
DEFAULT_LOGIN_TIMEOUT = 600.0
DEFAULT_UPLOAD_TIMEOUT = 900.0
POLL_INTERVAL = 2.0
DETAIL_RETRY_ATTEMPTS = 3

# 官网页面上的选择器。页面改版时先来这里改，别去流程里翻。
LOGIN_BUTTON = "button.a-s-header-login-btn"
LOGIN_USER = 'input[id$="__userName"]'
LOGIN_PASSWORD = 'input[id$="__password"]'
LOGIN_SUBMIT = 'input[id$="__submit"]'
FILE_INPUT = "input[type=file][multiple]"
DOWNLOAD_HANDLE = ".parse-render-content-title-handle"
DOWNLOAD_ITEM = ".ant-dropdown-menu-item"
RESULT_AREA = ".parse-render-content"

# 官网自述的上传上限：200MB、1000 页。页数没法在下载前知道，先卡大小。
UPLOAD_MAX_BYTES = 200 * 1024 * 1024



class OfficialWebError(Exception):
    """官网方式出了问题；只该让当前这一份失败。"""


class BrowserError(OfficialWebError):
    """浏览器起不来，或者浏览器配置目录不能用。"""


class LoginRequired(OfficialWebError):
    """等不到登录。"""


class TaskFailed(OfficialWebError):
    """官网上传或解析失败。"""


class DownloadFailed(OfficialWebError):
    """官网结果下载不下来，详情接口里也没有可用的 JSON。"""


def default_base_dir():
    """配置与凭据的根目录。Windows 用 LOCALAPPDATA，其他系统用配置目录。"""
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        root = (os.environ.get("XDG_CONFIG_HOME")
                or os.path.expanduser("~/.config"))
    return os.path.join(root, "pdf-to-md")


def default_profile_dir():
    """浏览器配置目录；里面是登录 cookie，不能提交、不能外传。"""
    return os.path.join(default_base_dir(), "browser-profile")


def default_credentials_path():
    """本地凭据文件；仓库外，不参与 git。"""
    return os.path.join(default_base_dir(), "credentials.json")


def load_credentials(path=None):
    """读本地凭据文件，返回 {"username", "password"}；没有或没填全返回 None。

    文件里是明文账号密码，所以这里只报「哪一行/哪个文件有问题」，
    不把内容带进异常消息——异常消息会被打印到终端、写进日志。
    """
    path = default_credentials_path() if path is None else path
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise BrowserError(
            f"凭据文件读不了：{path}（{exc.__class__.__name__}）。"
            f"它应该是一个 JSON 对象，里面有两个字符串字段 username 和 "
            f"password；把密码写错、或者文件不是 UTF-8，都会这样。") from exc
    if not isinstance(data, dict):
        raise BrowserError(
            f"凭据文件 {path} 顶层不是 JSON 对象，"
            f"是 {type(data).__name__}；它应该是 "
            f'{{"username": "…", "password": "…"}} 这样的对象。')
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        raise BrowserError(
            f"凭据文件 {path} 里的 username 和 password 都得是字符串。")
    username = username.strip()
    password = password.strip()
    if not username or not password:
        return None
    return {"username": username, "password": password}


def task_id_from_url(url):
    """从任务页网址里取任务号；不是任务页就返回 None。"""
    if not isinstance(url, str) or TASK_URL_MARKER not in url:
        return None
    tail = url.split(TASK_URL_MARKER, 1)[1]
    tail = tail.split("?", 1)[0].split("#", 1)[0].strip("/")
    return tail or None


def _task_progress(result):
    return result.get("extractedPages"), result.get("totalPages")


def poll_task(fetch_detail, task_url, timeout, interval=POLL_INTERVAL,
              on_progress=None, clock=time.monotonic, sleep=time.sleep):
    """反复问任务详情，直到完成、失败或超时。

    `fetch_detail()` 返回详情接口的顶层 JSON 对象。返回完成时的 `result`
    字典。`clock` 和 `sleep` 是为了测试能不走真实时间。
    """
    started = clock()
    last_status = None
    while True:
        body = fetch_detail()
        if not isinstance(body, dict):
            raise TaskFailed(
                f"任务详情接口返回的不是对象，是 {type(body).__name__}；"
                f"任务页：{task_url}")
        if body.get("errorCode"):
            raise TaskFailed(
                f"任务详情接口报错：{body.get('errorMsg') or body['errorCode']}；"
                f"任务页：{task_url}")
        result = body.get("result")
        if not isinstance(result, dict):
            raise TaskFailed(
                f"任务详情里没有 result；任务页：{task_url}")

        status = result.get("taskStatus")
        last_status = status
        if status == DONE_STATUS:
            if on_progress:
                done, total = _task_progress(result)
                if done is not None or total is not None:
                    on_progress(done, total)
            return result
        if isinstance(status, int) and status < 0:
            raise TaskFailed(
                f"官网解析失败（taskStatus={status}）："
                f"任务页提示「发生解析错误，请重试」。任务页：{task_url}")

        if on_progress:
            done, total = _task_progress(result)
            if done is not None or total is not None:
                on_progress(done, total)

        if clock() - started > timeout:
            raise TaskFailed(
                f"等了 {int(timeout)} 秒还没解析完"
                f"（最后状态 {last_status!r}）。任务页：{task_url}")
        sleep(interval)


def official_json_from_detail(detail):
    """从任务详情里取 parsingResult。下载菜单取不到时用它兜底。"""
    result = detail.get("result") if isinstance(detail, dict) else None
    raw = result.get("parsingResult") if isinstance(result, dict) else None
    if not isinstance(raw, str) or not raw.strip():
        raise DownloadFailed(
            "官网任务完成了，但下载菜单没取到 JSON，"
            "任务详情里也没有 parsingResult。")
    return raw


@dataclass
class WebOutcome:
    """一次官网解析拿回来的东西。"""
    json_text: str
    task_id: str
    task_url: str
    detail: dict


def _safe_name(name):
    name = os.path.basename(name or "").strip()
    return name or "document"


class WebSession:
    """一个可见的浏览器窗口，负责登录、上传、等结果、下载 JSON。

    用 `with WebSession(...) as session:` 起。Playwright 的同步 API 不是
    线程安全的，所有浏览器调用都留在创建它的那个线程里。
    """

    def __init__(self, profile_dir=None, channel=None,
                 login_timeout=DEFAULT_LOGIN_TIMEOUT,
                 upload_timeout=DEFAULT_UPLOAD_TIMEOUT,
                 web_timeout=DEFAULT_WEB_TIMEOUT,
                 allow_manual_login=True, credentials_path=None,
                 interval=POLL_INTERVAL):
        self.profile_dir = profile_dir or default_profile_dir()
        self.channel = channel or DEFAULT_CHANNEL
        self.login_timeout = login_timeout
        self.upload_timeout = upload_timeout
        self.web_timeout = web_timeout
        self.allow_manual_login = allow_manual_login
        self.credentials_path = credentials_path or default_credentials_path()
        self.interval = interval
        self.page = None
        self._playwright = None
        self._context = None
        self._temp_dirs = []

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    # ---- 生命周期 -------------------------------------------------

    def start(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserError(
                "没装 playwright。官网方式要开浏览器，转换命令里得带 "
                "--with playwright。") from exc

        self._playwright = sync_playwright().start()
        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                self.profile_dir, channel=self.channel, headless=False,
                args=["--no-first-run", "--no-default-browser-check"])
        except Exception as exc:
            self._playwright.stop()
            self._playwright = None
            raise BrowserError(self._launch_hint(exc)) from exc
        self.page = (self._context.pages[0] if self._context.pages
                     else self._context.new_page())

    def _launch_hint(self, exc):
        text = str(exc)
        bits = [f"打不开浏览器（配置目录：{self.profile_dir}）。"]
        lowered = text.lower()
        if ("processsingleton" in lowered or "already in use" in lowered
                or "user data directory" in lowered):
            bits.append(
                "这个配置目录已经被另一个浏览器占用了——先把开着同一个"
                "配置目录的 Edge/Chrome 窗口全部关掉，再重跑。")
        bits.append(
            f"默认用 {self.channel}；机器上没有这个浏览器时，"
            f"用 --browser-channel 换一个，或者先跑 "
            f"`uv run --with playwright playwright install chromium` "
            f"再指定 --browser-channel chromium。")
        bits.append(f"Playwright 的原话：{text}")
        return "\n".join(bits)

    def close(self):
        for path in self._temp_dirs:
            shutil.rmtree(path, ignore_errors=True)
        self._temp_dirs = []
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        self.page = None

    def _require_page(self):
        if self.page is None:
            raise BrowserError("浏览器还没启动。先用 with WebSession(...) 起一个。")
        return self.page

    def _goto(self, url):
        try:
            self._require_page().goto(url, wait_until="domcontentloaded",
                                      timeout=60000)
        except OfficialWebError:
            raise
        except Exception as exc:
            raise BrowserError(f"打不开页面 {url}：{exc}") from exc

    # ---- 登录 -----------------------------------------------------

    def _logged_in(self, page):
        button = page.locator(LOGIN_BUTTON)
        return button.count() == 0 or not button.first.is_visible()

    def _auto_login(self, page, credentials):
        """用本地凭据填登录表单。只填，不打印任何字段。"""
        button = page.locator(LOGIN_BUTTON)
        if button.count() == 0:
            return
        button.first.click()
        user = page.locator(LOGIN_USER)
        user.wait_for(state="visible", timeout=30000)
        user.fill(credentials["username"])
        page.locator(LOGIN_PASSWORD).fill(credentials["password"])
        page.locator(LOGIN_SUBMIT).click()
        # 自动登录可能还要过验证码；这里只等一会儿，后面统一按手动登录继续等。
        try:
            page.locator(LOGIN_BUTTON).first.wait_for(state="hidden",
                                                      timeout=30000)
        except Exception:
            pass

    def ensure_login(self):
        page = self._require_page()
        self._goto(NEW_TASK_URL)
        # 等头部或上传框至少出现一个：页面还在渲染时，登录按钮可能还没进
        # DOM，这时候数不到按钮会被误判成「已经登录」。
        try:
            page.wait_for_selector(f"{LOGIN_BUTTON}, {FILE_INPUT}",
                                   state="attached", timeout=30000)
        except Exception as exc:
            raise BrowserError(
                f"上传页没加载出来（配置目录：{self.profile_dir}）：{exc}") from exc
        if self._logged_in(page):
            return

        credentials = load_credentials(self.credentials_path)
        if credentials:
            try:
                self._auto_login(page, credentials)
            except Exception:
                # 自动登录失败不直接判死：可能只是要验证码，交给下面的人工等待。
                pass

        if self._logged_in(page):
            page.keyboard.press("Escape")
            return

        if not self.allow_manual_login:
            raise LoginRequired(
                f"浏览器没登录，而且这次不让等（--no-wait-login）。"
                f"先跑一次转换，在打开的浏览器里手动登录；"
                f"登录状态会留在 {self.profile_dir}。")

        print("请在打开的浏览器窗口里完成登录（有验证码就在这里完成）；"
              "登录后脚本会自动继续。", file=sys.stderr)

        deadline = time.monotonic() + self.login_timeout
        while True:
            if self._logged_in(page):
                page.keyboard.press("Escape")
                return
            if time.monotonic() >= deadline:
                raise LoginRequired(
                    f"等了 {int(self.login_timeout)} 秒还没登录。"
                    f"请在浏览器窗口里完成登录后重跑；登录状态会留在 "
                    f"{self.profile_dir}。也可以把账号密码写进 "
                    f"{self.credentials_path}（仓库外，不会提交）。")
            time.sleep(self.interval)

    # ---- 输入 -----------------------------------------------------

    def materialize(self, target, name="document"):
        """本地路径原样返回；网址先下载到临时文件。"""
        if not target.startswith(("http://", "https://")):
            path = os.path.abspath(target)
            if not os.path.isfile(path):
                raise OfficialWebError(f"找不到：{target}")
            return path
        return self._download_pdf(target, name)

    def _download_pdf(self, url, name):
        tmp = tempfile.mkdtemp(prefix="pdf-to-md-web-")
        self._temp_dirs.append(tmp)
        path = os.path.join(tmp, _safe_name(name) + ".pdf")
        try:
            resp = requests.get(url, stream=True, timeout=(30, 300))
        except requests.RequestException as exc:
            raise OfficialWebError(
                f"下载网址失败：{url}（{exc}）") from exc
        with resp:
            if resp.status_code != 200:
                raise OfficialWebError(
                    f"下载网址失败：{url} 返回 HTTP {resp.status_code}。"
                    f"官网方式只支持公网可直接下载的 PDF 地址。")

            content_type = resp.headers.get("Content-Type", "")
            first = b""
            size = 0
            try:
                with open(path, "wb") as f:
                    for chunk in resp.iter_content(1024 * 256):
                        if not chunk:
                            continue
                        if not first:
                            first = chunk[:1024]
                        size += len(chunk)
                        if size > UPLOAD_MAX_BYTES:
                            raise OfficialWebError(
                                f"网址下载下来的文件超过 200MB，官网不收：{url}")
                        f.write(chunk)
            except requests.RequestException as exc:
                raise OfficialWebError(
                    f"下载网址中途断了：{url}（{exc}）") from exc

        if not first.lstrip().startswith(b"%PDF"):
            raise OfficialWebError(
                f"网址返回的不是 PDF（Content-Type: {content_type or '没给'}，"
                f"开头不是 %PDF）：{url}。要登录、要 referer、有反爬的站点，"
                f"这里取不到；先把 PDF 存到本地再转。")
        return path

    # ---- 上传与等结果 ---------------------------------------------

    def _upload(self, local_path):
        page = self._require_page()
        self._goto(NEW_TASK_URL)
        file_input = page.locator(FILE_INPUT).first
        try:
            file_input.wait_for(state="attached", timeout=30000)
            file_input.set_input_files(local_path)
            page.wait_for_url(re.compile(re.escape(TASK_URL_MARKER)),
                              timeout=self.upload_timeout * 1000)
        except Exception as exc:
            raise OfficialWebError(
                f"上传后没有跳到任务页（等了 {int(self.upload_timeout)} 秒）。"
                f"页面提示：{self._upload_hint()}") from exc
        return page.url

    def _upload_hint(self):
        """只认几种常见原因，不把整页文字打出来——页面顶部有账号区。"""
        try:
            text = self.page.inner_text("body")
        except Exception:
            return "读不到页面文字"
        if "超过" in text or "200MB" in text:
            return "文件超过官网的大小上限（200MB）"
        if "格式" in text or "不支持" in text:
            return "官网不支持这个文件格式"
        if "失败" in text:
            return "页面上写着上传失败"
        return "页面上没有明确原因，打开浏览器窗口看一眼"

    def _fetch_detail(self, task_id):
        url = DETAIL_URL.format(task_id=task_id)
        last = None
        for attempt in range(DETAIL_RETRY_ATTEMPTS):
            try:
                resp = self._context.request.get(url, timeout=30000)
            except Exception as exc:
                last = exc
            else:
                if resp.status == 200:
                    try:
                        return resp.json()
                    except Exception as exc:
                        last = exc
                else:
                    last = f"HTTP {resp.status}"
            if attempt + 1 < DETAIL_RETRY_ATTEMPTS:
                time.sleep(1.0)
        raise OfficialWebError(f"任务详情接口连不上：{last}")

    def _wait_for_download_button(self):
        page = self._require_page()
        handle = page.locator(DOWNLOAD_HANDLE).first
        handle.wait_for(state="visible", timeout=60000)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            buttons = handle.locator("button")
            if buttons.count() >= 4:
                button = buttons.nth(3)
                try:
                    if button.is_visible() and not button.is_disabled():
                        return button
                except Exception:
                    pass
            time.sleep(1.0)
        raise DownloadFailed("任务页上没有出现可用的下载按钮。")

    def _download_from_menu(self, task_url):
        page = self._require_page()
        if task_url not in page.url:
            self._goto(task_url)
        button = self._wait_for_download_button()
        button.click()
        item = page.locator(DOWNLOAD_ITEM).filter(has_text="JSON").first
        item.wait_for(state="visible", timeout=30000)
        with page.expect_download(timeout=120000) as info:
            item.click()
        download = info.value

        tmp = tempfile.mkdtemp(prefix="pdf-to-md-web-json-")
        self._temp_dirs.append(tmp)
        path = os.path.join(tmp, "official.json")
        download.save_as(path)
        with open(path, encoding="utf-8-sig") as f:
            return f.read()

    def _download_json(self, detail, task_url):
        try:
            return self._download_from_menu(task_url)
        except Exception as exc:
            # 菜单改版、下载按钮没出现、浏览器那边报错，都退到任务详情。
            # 详情里是同一份 parsingResult，不能让整个任务因为下载菜单白跑。
            print(f"提示：下载菜单没取到 JSON（{exc}），"
                  f"改用任务详情里的同一份结果。", file=sys.stderr)
            return official_json_from_detail(detail)

    def parse(self, target, name="document", on_progress=None,
              debug_dir=None):
        """走完一次官网解析，返回 JSON 正文与任务信息。"""
        try:
            local = self.materialize(target, name)
            task_url = self._upload(local)
            task_id = task_id_from_url(task_url)
            if not task_id:
                raise OfficialWebError(
                    f"上传后跳到了 {task_url}，但里面没有任务号。")
            detail = poll_task(
                lambda: self._fetch_detail(task_id),
                task_url, self.web_timeout,
                interval=self.interval, on_progress=on_progress)
            json_text = self._download_json(detail, task_url)
            self.snapshot(debug_dir)
            return WebOutcome(json_text=json_text, task_id=task_id,
                              task_url=task_url, detail=detail)
        except Exception:
            self.snapshot(debug_dir)
            raise

    # ---- 调试 -----------------------------------------------------

    def snapshot(self, debug_dir):
        """存任务页结果区的截图与 HTML；取不到就算了，不能把主流程带崩。"""
        if not debug_dir or self.page is None:
            return
        try:
            target = self.page.locator(RESULT_AREA).first
            if target.count() == 0:
                target = self.page.locator("body")
            web_dir = os.path.join(debug_dir, "web")
            os.makedirs(web_dir, exist_ok=True)
            target.screenshot(path=os.path.join(web_dir, "task-page.png"))
            with open(os.path.join(web_dir, "task-page.html"), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(target.inner_html())
        except Exception:
            pass

