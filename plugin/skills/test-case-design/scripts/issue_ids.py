#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给六份文档里的条目发编号。

用法：

    python issue_ids.py <产出目录>                     总览：七种编号各用到几号、下一个可用几号
    python issue_ids.py <产出目录> TC- --count 8       发号：打 8 个号，一行一个（不给 --count 就是 1 个）

退出码：0 正常；2 用法不对、读不到目录，或前缀像是漏了分隔符。

编号不另存台账，基准就是产出目录里那六份文档：每次现读一遍，取已经定义过的条目里最大的
号加一。目录还是空的就从 1 起。号只往后加——删条目腾出来的号不回收。

「什么算一条已定义的条目」「什么算文档里出现过这个号」都不在这份脚本里另立一套，直接复用
check_docs.py 的判定（`defined` 与 `referenced`：章节标题里的号、加粗的唯一标识符、表首格是
编号的那一行算定义；正文里出现的号算出现过）。两边看法必须一致：这边认不出的号，
check_docs 也认不出，那种文档本来就过不了自检；反过来这边若认得比那边宽，发出去的号就
可能撞上文档里已有的号。

文档里出现过、但认不出定义处的号（例如对应表里引用了还没写出来的 TC-9），不当基准，只
提示一句——拿它当基准会让号凭空往前跳一大截、留个洞。

前缀漏了结尾那一横（盘上写的是 `TC-1`、传进来的是 `TC`）时不发号，只提示一句：照它发会
打出 `TC1` 这种编号，看着像对的，写进文档才发现对不上。
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_docs  # noqa: E402  「什么是定义处」只有一份，见 check_docs.py

# 七种编号，以及认定义处时要看哪几栏。栏位与 check_docs.py 查同一个对象时用的那几栏相同：
# TM 与 TP 不带栏位要求（标题、加粗标签、任何表的表首格都认），其余按各自那份文档的栏位认。
PREFIXES = [
    ("TM-", []),
    ("TCOV-", check_docs.COV_COLS),
    ("TC-", check_docs.CASE_COLS),
    ("TP-", []),
    ("DATA-", check_docs.DATA_COLS),
    ("ENV-", check_docs.ENV_COLS),
    ("DEC-", check_docs.DEC_COLS),
]
DEFAULT_COUNT = 1

USAGE = """用法：
    python issue_ids.py <产出目录>
        总览：七种编号各用到几号、下一个可用几号

    python issue_ids.py <产出目录> <前缀> [--count N]
        发号：打 N 个号，一行一个（默认 1 个）。前缀照写、含分隔符，如 TC-；
        项目自己的编号惯例照传，如 Lid-
"""


def cols_for(prefix):
    """认这个前缀的定义处要看哪几栏。六种之外的编号按标题、加粗标签、表首格认。"""
    for known, cols in PREFIXES:
        if known == prefix:
            return cols
    return []


def read_docs(root):
    """读产出目录里那六份文档，返回 {文件名: 正文}。

    缺哪份都不算错——步骤还没走到那儿、或者只补写其中一份，都是正常的。
    """
    texts = {}
    for name in check_docs.DOCS:
        path = root / name
        if path.is_file():
            texts[name] = path.read_text(encoding="utf-8")
    return texts


def max_defined(texts, prefix):
    """已经定义过的条目里最大的号；一条都没有就是 0。"""
    cols = cols_for(prefix)
    top = 0
    for text in texts.values():
        found = check_docs.defined(check_docs.tables(text), text, cols, re.escape(prefix))
        if found:
            top = max(top, max(found))
    return top


def max_seen(texts, prefix):
    """文档里出现过的最大的号，含只在引用里出现、没有定义处的。"""
    top = 0
    for text in texts.values():
        found = check_docs.referenced(text, prefix)
        if found:
            top = max(top, max(found))
    return top


def stray_hint(texts, prefix):
    """有号只出现在引用里、还比基准大时，提示一句；没有这种情况返回 None。"""
    seen, defined = max_seen(texts, prefix), max_defined(texts, prefix)
    if seen <= defined:
        return None
    return ("提示：文档里出现过 %s%d，但只有引用、没有定义处——多半是引用还没配上条目，"
            "或者编号写错了。发号只按定义处算，下一个可用是 %s%d。"
            % (prefix, seen, prefix, defined + 1))


def missing_dash_hint(texts, prefix):
    """前缀漏了结尾的分隔符时提示一句；没有这种情况返回 None。

    盘上写的是 `TC-1`，而传进来的是 `TC`——照它发号会打出 `TC1` 这种编号，看着像对的，
    写进文档才发现对不上。所以这一处不猜：认得出来就直接说穿、不发号。
    """
    if max_seen(texts, prefix) or not max_seen(texts, prefix + "-"):
        return None
    return ("提示：盘上用的是「%s-」这个前缀（%s-1 这样的写法）。你给的前缀是「%s」，"
            "是不是漏了结尾的 `-`？这次不发号。" % (prefix, prefix, prefix))


def overview(root, texts):
    print("产出目录：%s\n" % root)
    if not texts:
        print("目录里还没有六份文档，七种编号都从 1 起。\n")
    print("| 前缀 | 已用到 | 下一个可用 |")
    print("|:---|:---|:---|")
    for prefix, _ in PREFIXES:
        top = max_defined(texts, prefix)
        used = "%s%d" % (prefix, top) if top else "无"
        print("| %s | %s | %s%d |" % (prefix, used, prefix, top + 1))
    for prefix, _ in PREFIXES:
        hint = stray_hint(texts, prefix)
        if hint:
            print("\n" + hint)
    return 0


def issue(texts, prefix, count):
    dash = missing_dash_hint(texts, prefix)
    if dash:
        print(dash)
        return 2
    start = max_defined(texts, prefix) + 1
    for n in range(start, start + count):
        print("%s%d" % (prefix, n))
    hint = stray_hint(texts, prefix)
    if hint:
        print("\n" + hint)
    return 0


def parse_args(argv):
    """返回 (产出目录, 前缀 或 None, 个数)；用法不对返回 None。"""
    rest, count, count_given = [], DEFAULT_COUNT, False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--count":
            if i + 1 >= len(argv) or not argv[i + 1].isdigit() or int(argv[i + 1]) < 1:
                return None
            count, count_given = int(argv[i + 1]), True
            i += 2
            continue
        if arg.startswith("--"):
            return None
        rest.append(arg)
        i += 1
    if len(rest) not in (1, 2):
        return None
    prefix = rest[1] if len(rest) == 2 else None
    if count_given and prefix is None:
        return None
    return Path(rest[0]), prefix, count


def main():
    parsed = parse_args(sys.argv[1:])
    if parsed is None:
        print(USAGE)
        return 2
    root, prefix, count = parsed
    if not root.is_dir():
        print("读不到目录：%s" % root)
        return 2
    texts = read_docs(root)
    if prefix is None:
        return overview(root, texts)
    return issue(texts, prefix, count)


if __name__ == "__main__":
    sys.exit(main())
