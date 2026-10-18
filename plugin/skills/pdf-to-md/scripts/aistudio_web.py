"""跟 AI Studio 官网的网页解析打交道：登录、上传、等任务、下载 JSON。

这个模块顶层不 import playwright——只有真要开浏览器时才在函数里 import。
这样 `--backend api` 和跑测试都不需要装 playwright。
"""
import json
import os
import sys
import time

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
POLL_INTERVAL = 2.0
IMAGE_RETRY_ATTEMPTS = 3


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
