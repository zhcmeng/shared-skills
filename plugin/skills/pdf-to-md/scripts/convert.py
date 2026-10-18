"""pdf-to-md 的命令行入口：参数、任务池、进度条、跳过判断、落盘。"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import aistudio
import aistudio_web
import markdown as md_utils

REQUIRED = ("requests", "lxml", "tabulate")
# 财报单页模式要拿 pypdf 把 PDF 切成单页；研报/网页用不上它。
FINANCIAL_REQUIRED = REQUIRED + ("pypdf",)
# 官网方式要开浏览器；playwright 只在走官网时才查。
WEB_REQUIRED = REQUIRED + ("playwright",)
_INSTALL_HINT = ("uv run --with requests --with lxml --with tabulate "
                 "--with pypdf")
_WEB_INSTALL_HINT = ("uv run --with requests --with lxml --with tabulate "
                     "--with playwright")

# 一页重试几次（含第一次）。服务偶尔会把某一页判失败，重试通常就好了；
# 一直失败就报出页码，不静默缺页。
FINANCIAL_PAGE_ATTEMPTS = 3
FINANCIAL_PAGE_RETRY_DELAY = 2.0


def missing_dependencies(names=REQUIRED):
    """哪些依赖没装。"""
    return [name for name in names if importlib.util.find_spec(name) is None]


def check_dependencies(names=REQUIRED, hint=_INSTALL_HINT):
    """缺依赖就报错退出，报清楚缺哪个、怎么补。

    这个检查非做不可：缺 lxml/tabulate 时导入会直接炸（这是好事），
    但炸出来的是裸的 ModuleNotFoundError，看不出该拿哪条命令去跑。
    """
    missing = missing_dependencies(names)
    if missing:
        raise SystemExit(
            f"缺依赖：{'、'.join(missing)}。\n"
            f"不用改环境，这条命令会把它们临时装好再跑：\n"
            f"  {hint} python <本脚本> …")


@dataclass
class Task:
    target: str     # 本地路径或网址，原样交给 aistudio.submit
    name: str       # 输出目录名
    origin: str     # 给人看的来源写法


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="convert.py",
        description="把 PDF 转成 Markdown，正文引用的图片一并落到本地")
    parser.add_argument("inputs", nargs="+",
                        help="PDF 文件、装着 PDF 的目录，或 PDF 的公网网址")
    parser.add_argument("--output", required=True,
                        help="输出根目录（必填）")
    parser.add_argument("--model", default=None,
                        help=f"接口认的模型名，默认 {aistudio.DEFAULT_MODEL}；"
                             f"官网方式只能用 {aistudio.DEFAULT_MODEL}；"
                             f"财报模式固定用 {aistudio.FINANCIAL_MODEL}")
    parser.add_argument("--force", action="store_true",
                        help="已转过的也重转")
    parser.add_argument("--jobs", type=int, default=None,
                        help="同时最多几个文件在转。api 方式默认 4；"
                             "官网方式一次只能处理一份，默认 1")
    parser.add_argument("--source-type", choices=("general", "financial"),
                        default="general",
                        help="素材类型。financial 表示财报：逐页切分单独提交，"
                             f"避免整本多页解析把宽表降级；模型固定为 "
                             f"{aistudio.FINANCIAL_MODEL}。默认 general；"
                             f"只对 --backend api 有效")
    parser.add_argument("--page-jobs", type=int, default=4,
                        help="财报单页模式下，一份 PDF 里同时最多几页在转，"
                             "默认 4")
    parser.add_argument("--debug", action="store_true",
                        help="保留完整过程：服务原始结果、切出来的单页 PDF、"
                             "合并前后的页表、图片对照和失败原因；官网方式"
                             "还留官网 JSON、任务详情与任务页截图。放在"
                             "输出目录的 debug/ 下，每次运行一个带时间戳的子目录")
    parser.add_argument("--backend", choices=("official-web", "api"),
                        default="official-web",
                        help="解析走哪条路。official-web（默认）在浏览器里"
                             "上传到 PaddleOCR 官网；api 走 AI Studio 的异步"
                             "解析接口")
    parser.add_argument("--browser-profile", default=None,
                        help="官网方式的浏览器配置目录；里面是登录 cookie。"
                             "默认放在用户缓存目录下的 pdf-to-md/browser-profile")
    parser.add_argument("--browser-channel", default=None,
                        help="官网方式用哪个浏览器。Windows 默认 msedge，"
                             "其他系统默认 chrome")
    parser.add_argument("--web-timeout", type=float,
                        default=aistudio_web.DEFAULT_WEB_TIMEOUT,
                        help="官网方式等解析完成最多多少秒，默认 3600")
    parser.add_argument("--login-timeout", type=float,
                        default=aistudio_web.DEFAULT_LOGIN_TIMEOUT,
                        help="官网方式等手动登录最多多少秒，默认 600")
    parser.add_argument("--no-wait-login", action="store_true",
                        help="官网方式没登录就立刻报错，不等人。体检用")
    args = parser.parse_args(argv)

    # 官网方式只有一个浏览器窗口，一次只能跑一份；api 方式沿用原来的 4。
    if args.jobs is None:
        args.jobs = 1 if args.backend == "official-web" else 4

    if args.jobs < 1:
        parser.error(f"--jobs 至少是 1，给的是 {args.jobs}")
    if args.page_jobs < 1:
        parser.error(f"--page-jobs 至少是 1，给的是 {args.page_jobs}")
    if args.web_timeout < 1:
        parser.error(f"--web-timeout 至少是 1，给的是 {args.web_timeout}")
    if args.login_timeout < 1:
        parser.error(f"--login-timeout 至少是 1，给的是 {args.login_timeout}")

    # --model 不给时用接口的默认模型。官网方式只按 1.6 解析；财报模式再把它
    # 钉死到 1.6：调用方可能还带着清单里的 PP-StructureV3，静默换掉会让人
    # 以为跑的是自己指定的那个；直接报错，让调用方改参数。
    if args.model is None:
        args.model = aistudio.DEFAULT_MODEL
    if args.backend == "official-web":
        if args.source_type == "financial":
            parser.error(
                "官网方式由服务端整本解析并合并表格，不支持 "
                "--source-type financial；财报逐页模式请用 --backend api。")
        if args.model != aistudio.DEFAULT_MODEL:
            parser.error(
                f"官网方式目前只按 {aistudio.DEFAULT_MODEL} 解析，"
                f"--model 给的是 {args.model}。去掉 --model，"
                f"或者改用 --backend api。")
    elif args.source_type == "financial":
        if args.model not in (aistudio.DEFAULT_MODEL, aistudio.FINANCIAL_MODEL):
            parser.error(
                f"财报模式固定用 {aistudio.FINANCIAL_MODEL}，"
                f"--model 给的是 {args.model}。要去掉 --model，"
                f"或者改用 --source-type general。")
        args.model = aistudio.FINANCIAL_MODEL

    if os.path.isfile(args.output):
        parser.error(f"--output 得是个目录，但 {args.output} 已经是个文件了")

    return args


def _is_url(raw):
    """网址只有这两种写法。

    别写成 `startswith("http")`——那会把一个真名叫 `http_notes.pdf` 的本地
    文件也认成网址，`isfile` 那一步根本轮不到，那个相对路径会被当成网址
    丢给服务端。
    """
    return raw.startswith(("http://", "https://"))


def output_dir_name(target):
    """从输入推一个输出目录名。"""
    if _is_url(target):
        path = urlparse(target).path
        last = path.rstrip("/").rsplit("/", 1)[-1]
        if not last:
            last = urlparse(target).netloc or "document"
        stem = last.rsplit(".", 1)[0] if "." in last else last
        return stem or "document"
    return os.path.splitext(os.path.basename(target))[0]


def collect_inputs(raw_inputs):
    """把命令行给的东西摊成任务表：去重、去同名撞车。"""
    targets = []
    for raw in raw_inputs:
        if _is_url(raw):
            targets.append(raw)
            continue
        path = os.path.abspath(raw)
        if os.path.isdir(path):
            found = sorted(str(p) for p in Path(path).rglob("*.pdf")
                           if p.is_file())
            targets.extend(found)
        elif os.path.isfile(path):
            targets.append(path)
        else:
            raise SystemExit(f"找不到：{raw}")

    # 同一份输入给了两次，只算一次
    seen = set()
    unique = []
    for t in targets:
        key = t if _is_url(t) else os.path.normcase(os.path.abspath(t))
        if key in seen:
            continue
        seen.add(key)
        unique.append(t)

    if not unique:
        raise SystemExit("没找到任何 PDF。给目录时会递归找 *.pdf，"
                         "目录里没有就什么都不会转。")

    # 两份不同路径的同名 PDF 会抢同一个输出目录，错开
    tasks = []
    taken = set()
    for t in unique:
        name = output_dir_name(t)
        if name in taken:
            n = 2
            while f"{name}-{n}" in taken:
                n += 1
            print(f"提示：{t} 与前面某份同名，输出目录改成 {name}-{n}/",
                  file=sys.stderr)
            name = f"{name}-{n}"
        taken.add(name)
        tasks.append(Task(target=t, name=name, origin=t))
    return tasks


class EmptyDocument(Exception):
    """这份 PDF 清理完一页能用的正文都没有。"""


class FinancialSplitError(Exception):
    """财报的 PDF 切不成单页。"""


class PageFailed(aistudio.JobFailed):
    """财报单页模式下某一页重试完仍然失败。

    继承 JobFailed，是为了让 run() 那张「只让这一份失败」的捕获表
    天然接得住它；页码放在消息里，用户知道是哪一页。
    """

    def __init__(self, page, cause):
        self.page = page
        self.cause = cause
        super().__init__(
            f"第 {page} 页失败（试了 {FINANCIAL_PAGE_ATTEMPTS} 次）：{cause}")


class _EmptyPage(Exception):
    """服务收下了这一页，却一页解析结果都没返回。"""


@dataclass
class Result:
    name: str
    pages: int
    seconds: float
    missing_images: list


def already_done(out_root, name):
    """输出目录里有那份 md 就算转过了。

    只看 md 在不在，**不看源文件的修改时间**——省掉记账。代价是源 PDF
    更新过之后要自己加 --force，这条记在方案的「已知局限」里。
    """
    return os.path.isfile(os.path.join(out_root, name, f"{name}.md"))


def split_pdf_pages(path, work_dir):
    """把一份 PDF 切成单页文件，按原页序返回路径。

    多页整本提交时，服务会把宽表降级（实测分众 2024 年报第 81 页的权益
    变动表只剩 13 列）；同一页切成单页再提交，能拿回完整的 16 列。

    pypdf 延迟导入：只有财报模式用它，研报/网页路径不该因为缺它跑不起来。
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise SystemExit(
            f"财报单页模式需要 pypdf。\n"
            f"不用改环境，这条命令会把它临时装好再跑：\n"
            f"  {_INSTALL_HINT} python <本脚本> …") from exc

    try:
        src = open(path, "rb")
    except OSError as exc:
        raise FinancialSplitError(f"读不了这份 PDF：{exc}") from exc

    with src:
        try:
            reader = PdfReader(src)
            total = len(reader.pages)
        except Exception as exc:
            raise FinancialSplitError(f"读不了这份 PDF：{exc}") from exc
        if total < 1:
            raise FinancialSplitError("这份 PDF 一页都没有，切不出单页")

        paths = []
        for i in range(total):
            writer = PdfWriter()
            try:
                writer.add_page(reader.pages[i])
            except Exception as exc:
                raise FinancialSplitError(
                    f"切第 {i + 1} 页时失败：{exc}") from exc
            page_path = os.path.join(work_dir, f"page-{i + 1:04d}.pdf")
            with open(page_path, "wb") as f:
                writer.write(f)
            paths.append(page_path)
    return paths


def _write_text_file(path, text):
    """按 UTF-8、LF 写文件；缺的目录一并建出来。"""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _new_debug_dir(task, out_root, started):
    """给这一次转换建一个带时间戳的调试目录。

    同一份 PDF 重跑几次就留几份，后一次不覆盖前一次——排查时最需要的
    往往正是失败那一趟的过程。
    """
    root = os.path.join(out_root, task.name, "debug")
    base = time.strftime("%Y%m%d-%H%M%S", time.localtime(started))
    path = os.path.join(root, base)
    n = 1
    while os.path.exists(path):
        n += 1
        path = os.path.join(root, f"{base}-{n}")
    os.makedirs(os.path.join(path, "raw"), exist_ok=True)
    return path


def _debug_write(debug_dir, name, text):
    """往调试目录写一份文本；没开调试时什么都不做。"""
    if not debug_dir:
        return
    _write_text_file(os.path.join(debug_dir, name), text)


def _debug_json(debug_dir, name, data):
    """往调试目录写一份 JSON；没开调试时什么都不做。"""
    if not debug_dir:
        return
    _debug_write(debug_dir, name,
                 json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _debug_pages(debug_dir, stage, pages):
    """把解析后的页表写成 JSONL。

    正文的原始 HTML、图片网址、版面坐标、页面尺寸全在里面——合并为什么
    没发生、表为什么接错，都能拿这一份重新跑判断，不必再花配额取一次。
    """
    if not debug_dir:
        return
    lines = [json.dumps({
        "index": page.index,
        "text": page.text,
        "images": page.images,
        "blocks": page.blocks,
        "page_size": page.page_size,
    }, ensure_ascii=False) for page in pages]
    _debug_write(debug_dir, os.path.join("parsed", f"{stage}.jsonl"),
                 "\n".join(lines) + ("\n" if lines else ""))


def _debug_error(debug_dir):
    """把当前异常连同栈写进 error.txt；已经失败时它不能再挡路。"""
    if not debug_dir:
        return
    try:
        _write_text_file(os.path.join(debug_dir, "error.txt"),
                         traceback.format_exc())
    except OSError:
        pass


def _convert_one_page(path, page_no, model, token, debug_dir=None):
    """提交一页，失败重试；重试完仍失败就带着页码抛 PageFailed。"""
    last = None
    for attempt in range(1, FINANCIAL_PAGE_ATTEMPTS + 1):
        meta = {"page": page_no, "attempt": attempt}
        meta_path = os.path.join(
            "raw", f"page-{page_no:04d}-attempt-{attempt}.json")
        try:
            job_id = aistudio.submit(
                path, model, token,
                optional_payload=aistudio.FINANCIAL_OPTIONAL_PAYLOAD)
            meta["job_id"] = job_id
            jsonl_url = aistudio.poll(job_id, token)
            meta["jsonl_url"] = jsonl_url
            raw = aistudio.fetch_jsonl(jsonl_url)
            # 先落原始结果再解析：解析炸了，这一份也在
            _debug_write(
                debug_dir,
                os.path.join("raw",
                             f"page-{page_no:04d}-attempt-{attempt}.jsonl"),
                raw)
            pages = md_utils.parse_jsonl(raw)
            if not pages:
                raise _EmptyPage("服务没返回这一页的解析结果")
            _debug_json(debug_dir, meta_path, meta)
            return pages
        except (aistudio.SubmitRejected, aistudio.JobFailed,
                aistudio.NetworkError, md_utils.JsonlLineError,
                _EmptyPage) as exc:
            last = exc
            meta["error"] = f"{type(exc).__name__}: {exc}"
            try:
                _debug_json(debug_dir, meta_path, meta)
            except OSError:
                pass
            if attempt < FINANCIAL_PAGE_ATTEMPTS:
                time.sleep(FINANCIAL_PAGE_RETRY_DELAY * attempt)
    raise PageFailed(page_no, last)


def _cache_images(pages, image_dir, fetched, failed, lock):
    """把这一页结果里的图立刻取到临时目录。

    图片网址带签名会过期，不能等整本 197 页都解析完再取——第一页的结果
    可能已经等了半小时。按网址去重；临时文件名用网址的哈希。
    """
    for page in pages:
        for url in page.images.values():
            with lock:
                if url in fetched or url in failed:
                    continue
            try:
                blob = aistudio.fetch_image(url)
            except (aistudio.NetworkError, aistudio.JobFailed):
                with lock:
                    failed.add(url)
                continue
            path = os.path.join(
                image_dir, hashlib.sha1(url.encode("utf-8")).hexdigest())
            with open(path, "wb") as f:
                f.write(blob)
            with lock:
                fetched[url] = path


def _convert_single_pages(task, model, token, page_jobs, image_dir,
                          on_pages=None, debug_dir=None):
    """财报模式：切单页、逐页提交、按原页序摊平。

    返回 `(pages, fetched, failed)`：`fetched` 是「网址 → 临时图片路径」，
    `failed` 是取不回来的网址集合。临时图片目录由调用方保管，落盘时还要用。
    开了调试时，切出来的单页 PDF 留在调试目录里，不随临时目录删掉。
    """
    if _is_url(task.target):
        raise FinancialSplitError(
            "财报单页模式只支持本地 PDF：要先把网址下载成文件再转。")
    if page_jobs < 1:
        page_jobs = 1

    page_dir_ctx = (
        nullcontext(os.path.join(debug_dir, "pages")) if debug_dir
        else tempfile.TemporaryDirectory(prefix="pdf-to-md-pages-"))
    with page_dir_ctx as page_dir:
        if debug_dir:
            os.makedirs(page_dir, exist_ok=True)
        page_files = split_pdf_pages(task.target, page_dir)
        total = len(page_files)
        if on_pages:
            on_pages(0, total)

        results = [None] * total
        errors = []
        fetched = {}
        failed = set()
        done = 0
        lock = threading.Lock()

        def work(index, path):
            nonlocal done
            try:
                pages = _convert_one_page(path, index + 1, model, token,
                                          debug_dir=debug_dir)
            except PageFailed as exc:
                with lock:
                    errors.append(exc)
                return
            results[index] = pages
            _cache_images(pages, image_dir, fetched, failed, lock)
            with lock:
                done += 1
                if on_pages:
                    on_pages(done, total)

        with ThreadPoolExecutor(max_workers=min(page_jobs, total)) as pool:
            futures = [pool.submit(work, i, p)
                       for i, p in enumerate(page_files)]
            for future in as_completed(futures):
                # work 只接 PageFailed；其余异常（本机读文件失败等）让它
                # 从 future.result() 冒出去，由 run() 的捕获表处理。
                future.result()

        if errors:
            errors.sort(key=lambda exc: exc.page)
            raise errors[0]

    pages = []
    for chunk in results:
        for page in chunk:
            pages.append(md_utils.Page(index=len(pages),
                                       text=page.text,
                                       images=page.images,
                                       blocks=page.blocks,
                                       page_size=page.page_size,
                                       tables=page.tables))
    return pages, fetched, failed


def _finish_document(task, out_root, pages, t0, prefetched=None,
                     failed_urls=None, debug_dir=None):
    """把页表清理、拼装、取图、落盘。财报模式的图已经提前取好，直接复制。"""
    prefetched = prefetched or {}
    failed_urls = failed_urls or set()

    names = md_utils.allocate_names(pages)
    downloads = list(md_utils.image_downloads(pages, names))
    document = md_utils.assemble(pages, names)

    # 守门看的是**清理之后**要落盘的那份东西，不是解析出来的原文：清理前每页都空
    # 的，清理后必然也空，所以这一道覆盖了旧的「一页都没有」和「一页正文都没有」
    # ——整项空、markdown 空、每页只剩页码标记，落下来都是一个只有换行的 md。
    # 报失败比静默交一个空文件好；整份都是空白页的 PDF 也就跟着判失败了。
    if not document.strip():
        raise EmptyDocument(
            f"{task.origin} 清理完什么都不剩。服务收下了这份文件，"
            f"但结果里没有一页能用的正文——可能是空文档、整份都读不出内容，"
            f"也可能是取回来的每页只剩页码这类清理时要删掉的东西。")

    out_dir = os.path.join(out_root, task.name)
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    # 取图要紧跟解析：网址带签名有有效期，不能先存着回头再取。
    # 财报模式在每页解析完时已经取到临时目录了，这里只复制。
    missing = []
    for local, url in downloads:
        if url in failed_urls:
            missing.append(local)
            continue
        if url in prefetched:
            shutil.copyfile(prefetched[url], os.path.join(img_dir, local))
            continue
        try:
            blob = aistudio.fetch_image(url)
        except (aistudio.NetworkError, aistudio.JobFailed):
            missing.append(local)
            continue
        with open(os.path.join(img_dir, local), "wb") as f:
            f.write(blob)

    if debug_dir:
        missing_set = set(missing)
        _debug_json(debug_dir, "images.json", [
            {"local": local, "url": url,
             "status": "missing" if local in missing_set else "ok"}
            for local, url in downloads])

    with open(os.path.join(out_dir, f"{task.name}.md"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(document + "\n")

    return Result(name=task.name, pages=len(pages),
                  seconds=time.time() - t0, missing_images=missing)


def convert_one(task, out_root, model, token, on_pages=None,
                source_type="general", page_jobs=4, debug=False,
                backend="api", web_session=None):
    """一份 PDF 走完全程：提交 → 轮询 → 取结果 → 取图 → 落盘。

    开了 debug 时，沿途的原始结果、切页文件、合并前后的页表和最终结果
    都写进 `<输出根>/<任务名>/debug/<时间戳>/`，成功失败都留。

    `backend="api"` 是默认值，直接调这个函数的老代码不受影响；命令行
    的默认是 `official-web`，那边会把浏览器会话传进来。
    """
    t0 = time.time()
    if source_type == "financial":
        model = aistudio.FINANCIAL_MODEL

    debug_dir = None
    if debug:
        debug_dir = _new_debug_dir(task, out_root, t0)
        task_meta = {
            "origin": task.origin,
            "target": task.target,
            "name": task.name,
            "model": model,
            "backend": backend,
            "source_type": source_type,
            "page_jobs": page_jobs,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime(t0)),
        }
        if source_type == "financial":
            task_meta["optional_payload"] = (
                aistudio.FINANCIAL_OPTIONAL_PAYLOAD)
        _debug_json(debug_dir, "task.json", task_meta)

    try:
        if backend == "official-web":
            if web_session is None:
                raise aistudio_web.BrowserError(
                    "官网方式没有浏览器会话——这是调用方接错了，不是环境问题。")
            outcome = web_session.parse(
                task.target, name=task.name, on_progress=on_pages,
                debug_dir=debug_dir)
            _debug_write(debug_dir, os.path.join("raw", "official.json"),
                         outcome.json_text)
            _debug_json(debug_dir, os.path.join("raw", "task-detail.json"),
                        outcome.detail)
            _debug_json(debug_dir, os.path.join("web", "task.json"), {
                "task_id": outcome.task_id,
                "task_url": outcome.task_url,
                "backend": backend,
                "profile": getattr(web_session, "profile_dir", ""),
            })
            pages = md_utils.parse_official_json(outcome.json_text)
            _debug_pages(debug_dir, "pages", pages)
            result = _finish_document(task, out_root, pages, t0,
                                      debug_dir=debug_dir)
        elif source_type == "financial":
            with tempfile.TemporaryDirectory(
                    prefix="pdf-to-md-images-") as image_tmp:
                pages, fetched, failed = _convert_single_pages(
                    task, model, token, page_jobs, image_tmp, on_pages,
                    debug_dir=debug_dir)
                _debug_pages(debug_dir, "before-merge", pages)
                pages = md_utils.merge_cross_page_tables(
                    pages,
                    ignore_labels=aistudio.FINANCIAL_OPTIONAL_PAYLOAD[
                        "markdownIgnoreLabels"])
                _debug_pages(debug_dir, "after-merge", pages)
                result = _finish_document(task, out_root, pages, t0,
                                          prefetched=fetched,
                                          failed_urls=failed,
                                          debug_dir=debug_dir)
        else:
            job_id = aistudio.submit(task.target, model, token)
            jsonl_url = aistudio.poll(job_id, token, on_progress=on_pages)
            raw = aistudio.fetch_jsonl(jsonl_url)
            _debug_write(debug_dir, os.path.join("raw", "result.jsonl"), raw)
            _debug_json(debug_dir, os.path.join("raw", "job.json"),
                        {"job_id": job_id, "jsonl_url": jsonl_url})
            pages = md_utils.parse_jsonl(raw)
            _debug_pages(debug_dir, "pages", pages)
            result = _finish_document(task, out_root, pages, t0,
                                      debug_dir=debug_dir)
    except Exception:
        if backend == "official-web" and web_session is not None:
            web_session.snapshot(debug_dir)
        _debug_error(debug_dir)
        raise

    _debug_json(debug_dir, "result.json", {
        "pages": result.pages,
        "seconds": round(result.seconds, 3),
        "missing_images": result.missing_images,
    })
    return result


def format_duration(seconds):
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _display_width(text):
    """终端里的显示宽度：中日韩字符占两格。"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1
               for ch in text)


class Progress:
    """一行动态进度 + 每个文件一行永久记录。

    好几个任务会同时想改那一行动态行，所以每次重画都加锁——不加会串字符。
    """

    def __init__(self, total, stream=None):
        self.total = total
        self.done = 0
        self.failed = 0
        self.skipped = 0
        self.inflight = {}          # 名字 → (已解析页数, 总页数)，总页数可能还不知道
        self.lock = threading.Lock()
        self.t0 = time.time()
        self.stream = stream if stream is not None else sys.stderr
        self._width = 0

    def _render_locked(self):
        elapsed = time.time() - self.t0
        bits = [f"{self.done}/{self.total} 完成"]
        if self.skipped:
            bits.append(f"跳过 {self.skipped}")
        if self.failed:
            bits.append(f"失败 {self.failed}")
        if self.inflight:
            running = "、".join(
                f"{name} {d}/{t} 页" if t else f"{name} …"
                for name, (d, t) in self.inflight.items())
            bits.append(f"进行中 {running}")
        bits.append(f"已用 {format_duration(elapsed)}")
        left = self.total - self.done - self.failed - self.skipped
        if self.done and left > 0:
            eta = elapsed / self.done * left
            bits.append(f"预计剩余 {format_duration(eta)}")
        line = "  ".join(bits)
        # 盖掉上一行的是 _clear_locked——它按记下来的宽度打一串空格。这里
        # 不用再补：三个调用点（add / pages / note）都先调了它，进来时
        # self._width 一定是 0，补出来永远是空串。
        self._width = _display_width(line)
        self.stream.write("\r" + line)
        self.stream.flush()

    def _clear_locked(self):
        if self._width:
            self.stream.write("\r" + " " * self._width + "\r")
            self._width = 0

    def add(self, name):
        with self.lock:
            self.inflight[name] = (None, None)
            self._clear_locked()
            self._render_locked()

    def pages(self, name, done, total):
        with self.lock:
            if name in self.inflight:
                self.inflight[name] = (done, total)
                self._clear_locked()
                self._render_locked()

    def note(self, text):
        """在动态行上方留一行永久的记录。"""
        with self.lock:
            self._clear_locked()
            self.stream.write(text + "\n")
            self._render_locked()

    def done_line(self, result):
        bits = [f"{result.name}  {result.pages} 页  "
                f"{format_duration(result.seconds)}"]
        if result.missing_images:
            bits.append(f"缺 {len(result.missing_images)} 张图："
                        + "、".join(result.missing_images))
        self.note("  ".join(bits))

    def close(self):
        with self.lock:
            self._clear_locked()
            self.stream.flush()


def run(tasks, args):
    """并发跑一批，返回退出码。一份失败不影响别的。"""
    progress = Progress(len(tasks))
    todo = []
    for task in tasks:
        if not args.force and already_done(args.output, task.name):
            progress.skipped += 1
            progress.note(f"跳过 {task.origin}（已经转过，要重转加 --force）")
            continue
        todo.append(task)

    failures = []
    missing = []

    source_type = getattr(args, "source_type", "general")
    backend = getattr(args, "backend", "api")
    page_jobs = getattr(args, "page_jobs", getattr(args, "jobs", 4))
    model = (aistudio.FINANCIAL_MODEL if source_type == "financial"
             else getattr(args, "model", aistudio.DEFAULT_MODEL))

    # token 在这里拿，不在工作线程里拿：拿不到时抛的 SystemExit 得冒到 main，
    # 才能变成退出码和一句提示，而不是烂在某个线程里。
    # 全部文件都已转过时不必拿——那一趟根本不用 token。
    # 官网方式不用 API token，也不该因为没配 token 就报错。
    # 写成 aistudio.get_token() 而不是 from aistudio import get_token：本模块
    # 通篇用的是 aistudio.xxx，而且测试是把 aistudio.get_token 换掉的，
    # 提前绑进来的名字换不掉。
    token = aistudio.get_token() if todo and backend == "api" else None

    def work(task):
        progress.add(task.name)
        return convert_one(
            task, args.output, model, token,
            on_pages=lambda d, t, n=task.name: progress.pages(n, d, t),
            source_type=source_type, page_jobs=page_jobs,
            debug=getattr(args, "debug", False), backend=backend)

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(work, t): t for t in todo}
        for future in as_completed(futures):
            task = futures[future]
            try:
                result = future.result()
            except (aistudio.SubmitRejected, aistudio.JobFailed,
                    aistudio.NetworkError, EmptyDocument,
                    md_utils.JsonlLineError, FinancialSplitError,
                    OSError) as exc:
                # OSError 是本机的问题（文件读不出来、目录建不了、盘写满了），
                # 不是服务那边的事。它照样只该让这一份失败——`submit` 读本地
                # 文件时 open() 抛的就是它，漏出去就是整批跟着崩。
                failures.append((task.origin, exc))
                with progress.lock:
                    progress.inflight.pop(task.name, None)
                    progress.failed += 1
                progress.note(f"失败 {task.origin}：{exc}")
                continue
            with progress.lock:
                progress.inflight.pop(task.name, None)
                progress.done += 1
            progress.done_line(result)
            if result.missing_images:
                missing.append(result)

    progress.close()

    if missing:
        print("\n有图没取回来（正文照常，只是那几张是坏图）：")
        for result in missing:
            print(f"  {result.name}：{'、'.join(result.missing_images)}")
    if failures:
        print(f"\n{len(failures)} 份失败：")
        for origin, exc in failures:
            print(f"  {origin}：{exc}")
        return 1
    return 0


def run_web(tasks, args):
    """官网方式：整个批次共用一个浏览器，按顺序一份一份跑。

    Playwright 的同步 API 不是线程安全的，所以这里不用 ThreadPoolExecutor。
    解析在服务端，本机只是上传和等结果；顺序跑不会多占多少时间。
    """
    progress = Progress(len(tasks))
    todo = []
    for task in tasks:
        if not args.force and already_done(args.output, task.name):
            progress.skipped += 1
            progress.note(f"跳过 {task.origin}（已经转过，要重转加 --force）")
            continue
        todo.append(task)

    if not todo:
        progress.close()
        return 0

    if getattr(args, "jobs", 1) > 1:
        progress.note("官网方式一次处理一份文件，--jobs 不生效")

    failures = []
    missing = []
    session_kwargs = dict(
        profile_dir=getattr(args, "browser_profile", None),
        channel=getattr(args, "browser_channel", None),
        login_timeout=getattr(args, "login_timeout",
                              aistudio_web.DEFAULT_LOGIN_TIMEOUT),
        web_timeout=getattr(args, "web_timeout",
                            aistudio_web.DEFAULT_WEB_TIMEOUT),
        allow_manual_login=not getattr(args, "no_wait_login", False),
    )
    try:
        with aistudio_web.WebSession(**session_kwargs) as session:
            session.ensure_login()
            for task in todo:
                progress.add(task.name)
                try:
                    result = convert_one(
                        task, args.output, args.model, None,
                        on_pages=lambda d, t, n=task.name:
                            progress.pages(n, d, t),
                        source_type=getattr(args, "source_type", "general"),
                        page_jobs=getattr(args, "page_jobs", 1),
                        debug=getattr(args, "debug", False),
                        backend="official-web", web_session=session)
                except (aistudio_web.OfficialWebError, EmptyDocument,
                        md_utils.OfficialJsonError, OSError) as exc:
                    # 浏览器起不来、登录等不到、下载失败、JSON 形状不对，
                    # 都只让这一份失败；下一份照跑。
                    failures.append((task.origin, exc))
                    with progress.lock:
                        progress.inflight.pop(task.name, None)
                        progress.failed += 1
                    progress.note(f"失败 {task.origin}：{exc}")
                    continue
                with progress.lock:
                    progress.inflight.pop(task.name, None)
                    progress.done += 1
                progress.done_line(result)
                if result.missing_images:
                    missing.append(result)
    except aistudio_web.OfficialWebError as exc:
        # 浏览器本身起不来、或者登录等不到：整批都跑不了，一次说清。
        failures.append(("浏览器/登录", exc))
    finally:
        progress.close()

    if missing:
        print("\n有图没取回来（正文照常，只是那几张是坏图）：")
        for result in missing:
            print(f"  {result.name}：{'、'.join(result.missing_images)}")
    if failures:
        print(f"\n{len(failures)} 份失败：")
        for origin, exc in failures:
            print(f"  {origin}：{exc}")
        return 1
    return 0


def prefer_utf8(stream):
    """这一路输出被重定向走时，改成按 UTF-8 吐字节；真控制台不动。

    Windows 中文版上标准流接的是管道时，Python 取的是区域编码
    cp936：中文进度落成 GBK 字节，而接住它的一方（Claude Code 的任务窗口、
    编辑器里的输出面板）一律按 UTF-8 解，屏幕上就是「���」。
    UTF-8 是重定向场合的通行默认（Python 自己的 UTF-8 模式也是这个取向），
    所以判断只看「是不是被重定向」，不看对方是谁。

    真控制台不切：那里的编码是 Python 按终端挑好的——Windows 上走
    WriteConsoleW，本来就是 UTF-8；别的平台是 locale 编码，都对得上终端，
    换掉反而会花屏。

    流不认得 reconfigure（比如测试里的 StringIO）就放过，不是报错。
    """
    if stream.isatty():
        return
    if (getattr(stream, "encoding", "") or "").lower().replace("-", "") == "utf8":
        return
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def main(argv=None):
    # 在 parse_args 之前：参数写错时 argparse 那句提示也是中文
    prefer_utf8(sys.stdout)
    prefer_utf8(sys.stderr)
    args = parse_args(argv)
    try:
        if args.backend == "official-web":
            check_dependencies(WEB_REQUIRED, _WEB_INSTALL_HINT)
        else:
            check_dependencies(
                FINANCIAL_REQUIRED if args.source_type == "financial"
                else REQUIRED)
        tasks = collect_inputs(args.inputs)
        if args.backend == "official-web":
            return run_web(tasks, args)
        return run(tasks, args)
    except SystemExit as exc:      # 缺依赖、目录里没有 PDF、缺 token
        if exc.code and not isinstance(exc.code, int):
            print(exc.code, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
