"""跟 AI Studio 的异步解析接口打交道：提交、轮询、取结果、取图。

这里是整个 skill 唯一发 HTTP 请求的地方。
"""
import json
import os
import time

import requests

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
DEFAULT_MODEL = "PaddleOCR-VL-1.6"
TOKEN_ENV = "PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN"

UPLOAD_TIMEOUT = 900.0
SMALL_TIMEOUT = 60.0
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2.0
POLL_INTERVAL = 3.0

# 三个开关照官方示例给 False，也不给使用者开口子——本机没试过打开的效果
OPTIONAL_PAYLOAD = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}


class SubmitRejected(Exception):
    """服务用非 200、或者非 0 的 code 拒了这次请求。

    提交和轮询都可能走到这里，所以消息里那个 what 是传入的——轮询失败时
    说「服务拒了这次提交」是错的，用户会以为卡在提交那一步。
    """

    def __init__(self, status, code=None, msg="", trace_id=None, what="请求"):
        self.status = status
        self.code = code
        self.msg = msg
        self.trace_id = trace_id
        bits = [f"服务拒了这次{what}：HTTP {status}"]
        if code is not None:
            bits.append(f"code={code}")
        if msg:
            bits.append(msg)
        if trace_id:
            bits.append(f"traceId={trace_id}")
        super().__init__("  ".join(bits))


class JobFailed(Exception):
    """任务跑起来之后失败了。"""


class NetworkError(Exception):
    """连不上服务，或者连着失败太多次。"""


def get_token():
    token = os.environ.get(TOKEN_ENV)
    if not token:
        raise SystemExit(
            f"环境里没有 {TOKEN_ENV}。\n"
            f"它是这个 skill 唯一认的 token 来源，在 ~/.claude/settings.json 的 "
            f"env 段里设一次即可：\n"
            f'  {{"env": {{"{TOKEN_ENV}": "<你的 token>"}}}}'
        )
    return token


def _retry(fn, what, attempts=None, delay=None):
    """网络类错误重试；HTTP 状态码的错误不在这里管。"""
    attempts = RETRY_ATTEMPTS if attempts is None else attempts
    delay = RETRY_DELAY if delay is None else delay
    last = None
    for i in range(attempts):
        try:
            return fn()
        except requests.RequestException as exc:
            last = exc
            if i + 1 < attempts:
                time.sleep(delay * (i + 1))
    raise NetworkError(f"{what}连不上服务，试了 {attempts} 次：{last}") from last


def _body_of(resp):
    """取响应体。网关返回 HTML 错误页时 resp.json() 会抛，一律退回空字典。"""
    try:
        body = resp.json()
    except (ValueError, requests.RequestException):
        body = None
    return body if isinstance(body, dict) else {}


def _text_of(resp):
    """取响应正文。压缩体坏掉时 resp.text 也会抛（ContentDecodingError）。"""
    try:
        return resp.text
    except requests.RequestException:
        return ""


def _data_of(body):
    """取信封里的 data。不是对象就退回空字典（`data` 是列表时 .get 会炸）。"""
    data = body.get("data")
    return data if isinstance(data, dict) else {}


def _rejected_from(resp, what="请求"):
    """把失败的响应变成异常。响应体不是 JSON 时也不能崩在解码上。"""
    body = _body_of(resp)
    return SubmitRejected(
        status=resp.status_code,
        code=body.get("code"),
        msg=body.get("msg") or _text_of(resp)[:300],
        trace_id=body.get("traceId"),
        what=what,
    )


def submit(target, model, token):
    """提交一份 PDF（本地路径或公网网址），返回 jobId。

    服务与网络这两条路上，它只往外抛 SubmitRejected 和 NetworkError，调用方
    （并发那层）接得住这两种。所以「服务说成功却没给任务号」也按提交被拒办——
    拿不到任务号走不下去，而 _rejected_from 会把原始响应体带进 msg，用户看得
    见服务到底回了什么。

    本地文件读不出来（不存在、没权限）时抛的是 OSError，**不包成
    SubmitRejected**：那是本机的问题，说成「服务拒了这次提交」是编瞎话；也不
    包成 NetworkError——那会白白重试三次。Task 12 的捕获表里带着 OSError，
    一样只让这一份失败。
    """
    headers = {"Authorization": f"bearer {token}"}

    def once():
        if target.startswith("http"):
            h = dict(headers, **{"Content-Type": "application/json"})
            return requests.post(JOB_URL, headers=h, timeout=SMALL_TIMEOUT, json={
                "fileUrl": target,
                "model": model,
                "optionalPayload": OPTIONAL_PAYLOAD,
            })
        with open(os.path.abspath(target), "rb") as f:
            return requests.post(
                JOB_URL, headers=headers, timeout=UPLOAD_TIMEOUT,
                data={"model": model,
                      "optionalPayload": json.dumps(OPTIONAL_PAYLOAD)},
                files={"file": f})

    resp = _retry(once, "提交")
    body = _body_of(resp)
    job_id = _data_of(body).get("jobId")
    if resp.status_code != 200 or body.get("code") or not job_id:
        raise _rejected_from(resp, "提交")
    return job_id


_KNOWN_STATES = ("pending", "running", "done", "failed")


def poll(job_id, token, on_progress=None):
    """反复问任务状态，直到完成或失败。返回结果 JSONL 的地址。

    **没有总超时**——这是不用 paddleocr-mcp 库的主要理由之一：那个库把
    轮询超时写死 600 秒，超了就扔异常，而任务在服务端还在跑。
    """
    headers = {"Authorization": f"bearer {token}"}
    while True:
        resp = _retry(
            lambda: requests.get(f"{JOB_URL}/{job_id}", headers=headers,
                                 timeout=SMALL_TIMEOUT),
            "轮询")
        body = _body_of(resp)
        if resp.status_code != 200 or not body:
            raise _rejected_from(resp, "轮询")
        data = _data_of(body)
        state = data.get("state")

        if state == "failed":
            raise JobFailed(f"任务失败：{data.get('errorMsg') or '服务没说原因'}")
        if state == "done":
            url = (data.get("resultUrl") or {}).get("jsonUrl")
            if not url:
                raise JobFailed("任务说完成了，但没给结果地址")
            return url
        if state not in _KNOWN_STATES:
            raise JobFailed(f"没见过的任务状态：{state!r}")
        if state == "running" and on_progress:
            prog = data.get("extractProgress")
            if prog:
                on_progress(prog.get("extractedPages"), prog.get("totalPages"))
        time.sleep(POLL_INTERVAL)
