"""pdf-to-md 的命令行入口：参数、任务池、进度条、跳过判断、落盘。"""
import argparse
import importlib.util
import os
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import aistudio
import markdown as md_utils

REQUIRED = ("requests", "lxml", "tabulate")
_INSTALL_HINT = "uv run --with requests --with lxml --with tabulate"


def missing_dependencies(names=REQUIRED):
    """哪些依赖没装。"""
    return [name for name in names if importlib.util.find_spec(name) is None]


def check_dependencies(names=REQUIRED):
    """缺依赖就报错退出，报清楚缺哪个、怎么补。

    这个检查非做不可：缺 lxml/tabulate 时导入会直接炸（这是好事），
    但炸出来的是裸的 ModuleNotFoundError，看不出该拿哪条命令去跑。
    """
    missing = missing_dependencies(names)
    if missing:
        raise SystemExit(
            f"缺依赖：{'、'.join(missing)}。\n"
            f"不用改环境，这条命令会把它们临时装好再跑：\n"
            f"  {_INSTALL_HINT} python <本脚本> …")


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
    parser.add_argument("--model", default=aistudio.DEFAULT_MODEL,
                        help=f"接口认的模型名，默认 {aistudio.DEFAULT_MODEL}")
    parser.add_argument("--force", action="store_true",
                        help="已转过的也重转")
    parser.add_argument("--jobs", type=int, default=4,
                        help="同时最多几个文件在转，默认 4")
    args = parser.parse_args(argv)

    if args.jobs < 1:
        parser.error(f"--jobs 至少是 1，给的是 {args.jobs}")

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
    """一份 PDF 一页都没解析出来。"""


@dataclass
class Result:
    name: str
    pages: int
    seconds: float
    missing_images: list
    note: str = ""


def already_done(out_root, name):
    """输出目录里有那份 md 就算转过了。

    只看 md 在不在，**不看源文件的修改时间**——省掉记账。代价是源 PDF
    更新过之后要自己加 --force，这条记在方案的「已知局限」里。
    """
    return os.path.isfile(os.path.join(out_root, name, f"{name}.md"))


def convert_one(task, out_root, model, token, on_pages=None):
    """一份 PDF 走完全程：提交 → 轮询 → 取结果 → 取图 → 落盘。"""
    t0 = time.time()
    job_id = aistudio.submit(task.target, model, token)
    jsonl_url = aistudio.poll(job_id, token, on_progress=on_pages)
    raw = aistudio.fetch_jsonl(jsonl_url)

    pages = md_utils.parse_jsonl(raw)
    if not pages:
        raise EmptyDocument(
            f"{task.origin} 一页都没解析出来。服务收下了这份文件，"
            f"但结果里没有任何页面——多半是空文档或整份都读不出内容。")

    names = md_utils.allocate_names(pages)
    document = md_utils.assemble(pages, names)

    out_dir = os.path.join(out_root, task.name)
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    # 取图要紧跟解析：网址带签名有有效期，不能先存着回头再取
    missing = []
    for local, url in md_utils.image_downloads(pages, names):
        try:
            blob = aistudio.fetch_image(url)
        except (aistudio.NetworkError, aistudio.JobFailed):
            missing.append(local)
            continue
        with open(os.path.join(img_dir, local), "wb") as f:
            f.write(blob)

    with open(os.path.join(out_dir, f"{task.name}.md"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(document + "\n")

    return Result(name=task.name, pages=len(pages),
                  seconds=time.time() - t0, missing_images=missing)


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
        pad = " " * max(0, self._width - _display_width(line))
        self._width = _display_width(line)
        self.stream.write("\r" + line + pad)
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
        if result.note:
            bits.append(result.note)
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

    # token 在这里拿，不在工作线程里拿：拿不到时抛的 SystemExit 得冒到 main，
    # 才能变成退出码和一句提示，而不是烂在某个线程里。
    # 全部文件都已转过时不必拿——那一趟根本不用 token。
    # 写成 aistudio.get_token() 而不是 from aistudio import get_token：本模块
    # 通篇用的是 aistudio.xxx，而且测试是把 aistudio.get_token 换掉的，
    # 提前绑进来的名字换不掉。
    token = aistudio.get_token() if todo else None

    def work(task):
        progress.add(task.name)
        return convert_one(
            task, args.output, args.model, token,
            on_pages=lambda d, t, n=task.name: progress.pages(n, d, t))

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(work, t): t for t in todo}
        for future in as_completed(futures):
            task = futures[future]
            try:
                result = future.result()
            except (aistudio.SubmitRejected, aistudio.JobFailed,
                    aistudio.NetworkError, EmptyDocument,
                    md_utils.JsonlLineError, OSError) as exc:
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


def main(argv=None):
    args = parse_args(argv)
    try:
        check_dependencies()
        tasks = collect_inputs(args.inputs)
        return run(tasks, args)
    except SystemExit as exc:      # 缺依赖、目录里没有 PDF、缺 token
        if exc.code and not isinstance(exc.code, int):
            print(exc.code, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
