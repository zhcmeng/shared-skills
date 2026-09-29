#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给六份文档里的条目发编号。

用法：

    python issue_ids.py <产出目录>                     总览：七种编号各用到几号、下一个可用几号
    python issue_ids.py <产出目录> TC- --count 8       发号：打 8 个号，一行一个（不给 --count 就是 1 个）
    python issue_ids.py <产出目录> --case-dirs [TP-n]  打评测用例的目录名：一条规程一行，
                                                      照抄进「各批落到哪」的「用例目录名」栏

退出码：0 正常；2 用法不对、读不到目录，前缀像是漏了分隔符，或目录名打不全（有的规程
没写「有序执行测试用例」栏、栏里引的用例查不到定义处或没有英文名）。

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

    python issue_ids.py <产出目录> --case-dirs [TP-n]
        打评测用例的目录名：一条规程一行，照抄进「各批落到哪」的「用例目录名」栏。
        位次照「有序执行测试用例」栏数，不靠手数；给了 TP-n 就只打那一条规程。
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


def case_dirs(texts, only):
    """打评测用例的目录名：一条规程一行，照抄进「各批落到哪」的「用例目录名」栏。

    位次照「有序执行测试用例」栏数一遍——手数「排第几」是这条链上唯一一处会数错的
    地方。规程号、用例号、英文名都从盘上那两份文档取。`only` 给了就只打那一条规程。

    脚本只读不写：打出来的东西由模型抄进产出。哪一处对不上就整条不发——只发一半，
    照抄的人多半会把那一半当成全部。

    切规程块、认英文名都调 check_docs 的那两份判定，不在这里另立一套：两边一旦分叉，
    打出来的名字就会与自检认的不是同一批。
    """
    proc = texts.get(check_docs.PROC_DOC)
    if proc is None:
        print("读不到 %s——先确认文件名对不对、目录对不对。" % check_docs.PROC_DOC)
        return 2
    order, _, bad_head = check_docs.proc_cases(proc)
    if bad_head:
        print("这些规程的标题没以编号起头，认不出规程的边界：%s——标题写成「TP-N 目标」"
              "的样子（编号紧跟 # 之后，前头不加序号），再跑一次。"
              % "、".join("「%s」" % s for s in bad_head))
        return 2
    if only is not None and only not in order:
        print("盘上没有 TP-%d 这条规程——先看它写出来了没有。" % only)
        return 2
    picking = [only] if only is not None else sorted(order)
    if not picking:
        print("测试规程规格说明里一条规程都没有——先写规程，再跑这一条。")
        return 2

    names = check_docs.case_names(check_docs.tables(texts.get(check_docs.CASE_DOC, "")))
    lines, problems = [], []
    for n in picking:
        seq = order[n]
        if not seq:
            problems.append("TP-%d 还没写「有序执行测试用例」栏——先写这一栏，再跑这一条。"
                            % n)
            continue
        if n > 99:
            problems.append("规程号 TP-%d 到了三位数——目录名里规程号那段两位装不下，"
                            "整套一起改成三位（见 references/文档模板.md 第五节）。" % n)
            continue
        if len(seq) > 99:
            problems.append("TP-%d 排了 %d 条用例，位次两位装不下——整套一起改成三位"
                            "（见 references/文档模板.md 第五节）。" % (n, len(seq)))
            continue
        got = []
        for k, tc in enumerate(seq, 1):
            if tc not in names:
                problems.append("TP-%d 的「有序执行测试用例」栏引了 TC-%d，"
                                "测试用例规格说明里查不到这条。" % (n, tc))
                continue
            if not names[tc]:
                problems.append("TC-%d 没有「英文名」栏——目录名最后一段要从那一栏取，"
                                "它是必填的。" % tc)
                continue
            got.append("tp%02d-%02d-TC-%d-%s" % (n, k, tc, names[tc]))
        if len(got) == len(seq):
            lines.append("TP-%d：%s" % (n, "、".join(got)))
    if problems:
        for msg in problems:
            print(msg)
        return 2
    for line in lines:
        print(line)
    return 0


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
    """返回 (产出目录, 要做的事, 前缀, 个数, 规程号)；用法不对返回 None。

    要做的事三种：`overview`（总览）、`issue`（发号）、`case_dirs`（打目录名）。
    规程号只在那一种里用得上，别的时候是 None。
    """
    rest, count, count_given, mode, only = [], DEFAULT_COUNT, False, "overview", None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--count":
            if i + 1 >= len(argv) or not argv[i + 1].isdigit() or int(argv[i + 1]) < 1:
                return None
            count, count_given = int(argv[i + 1]), True
            i += 2
            continue
        if arg == "--case-dirs":
            if mode != "overview":
                return None
            mode = "case_dirs"
            i += 1
            # 后面紧跟的那一个若不是选项，就是「只打这一条」的规程号
            if i < len(argv) and not argv[i].startswith("--"):
                m = re.fullmatch(r"TP-(\d+)", argv[i])
                if not m:
                    return None
                only = int(m.group(1))
                i += 1
            continue
        if arg.startswith("--"):
            return None
        rest.append(arg)
        i += 1
    if mode == "case_dirs":
        # 这一种只接产出目录：前缀与它不同用，--count 也不搭
        if len(rest) != 1 or count_given:
            return None
        return Path(rest[0]), mode, None, count, only
    if len(rest) not in (1, 2):
        return None
    prefix = rest[1] if len(rest) == 2 else None
    if count_given and prefix is None:
        return None
    if prefix is None:
        return Path(rest[0]), "overview", None, count, None
    return Path(rest[0]), "issue", prefix, count, None


def prefer_utf8(stream):
    """这一路输出被重定向走时，改成按 UTF-8 吐字节；真控制台不动。

    和 pdf-to-md 那边的 `convert.prefer_utf8` 同一份逻辑，抄过来的（那边 doctor.py
    里也是抄的）。本机（Windows 中文版）上标准流接的是管道时，Python 取的是区域
    编码 cp936：中文落成 GBK 字节，而接住它的一方（Claude Code 的任务窗口、编辑器
    里的输出面板）一律按 UTF-8 解，屏幕上就是「���」——发出去的号成了乱码，写进
    文档就跟着错。真控制台不切：那里的编码是 Python 按终端挑好的，换掉反而会花屏。

    流不认得 reconfigure（比如测试里的 StringIO）就放过，不是报错。
    """
    if stream.isatty():
        return
    if (getattr(stream, "encoding", "") or "").lower().replace("-", "") == "utf8":
        return
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def main():
    # 在解析参数之前：用法写错、读不到目录时那几句提示也是中文
    prefer_utf8(sys.stdout)
    prefer_utf8(sys.stderr)
    parsed = parse_args(sys.argv[1:])
    if parsed is None:
        print(USAGE)
        return 2
    root, mode, prefix, count, only = parsed
    if not root.is_dir():
        print("读不到目录：%s" % root)
        return 2
    texts = read_docs(root)
    if mode == "case_dirs":
        return case_dirs(texts, only)
    if mode == "overview":
        return overview(root, texts)
    return issue(texts, prefix, count)


if __name__ == "__main__":
    sys.exit(main())
