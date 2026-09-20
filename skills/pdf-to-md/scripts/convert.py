"""pdf-to-md 的命令行入口：参数、任务池、进度条、跳过判断、落盘。"""
import argparse
import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import aistudio

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


def output_dir_name(target):
    """从输入推一个输出目录名。"""
    if target.startswith("http"):
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
        if raw.startswith("http"):
            targets.append(raw)
            continue
        path = os.path.abspath(raw)
        if os.path.isdir(path):
            found = sorted(str(p) for p in Path(path).rglob("*.pdf"))
            targets.extend(found)
        elif os.path.isfile(path):
            targets.append(path)
        else:
            raise SystemExit(f"找不到：{raw}")

    # 同一份输入给了两次，只算一次
    seen = set()
    unique = []
    for t in targets:
        key = t if t.startswith("http") else os.path.normcase(os.path.abspath(t))
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
