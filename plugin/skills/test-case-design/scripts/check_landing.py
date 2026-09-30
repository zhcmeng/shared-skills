#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核对产出文档里的编号，与成品（落下来的测试代码、评测用例）里的编号对不对得上。

用法：

    python check_landing.py <产出目录> [成品路径 ...]

    python check_landing.py evals/token-counter/test-case-design
    python check_landing.py evals/token-counter/test-case-design tests/ evals/token-counter/cases/

不给成品路径时，从测试用例规格说明的「成品落点」表里取（那种情况按跑命令时的当前目录
解路径）。成品路径给目录就整个目录走一遍，给文件就只看那一份。

退出码：0 全过；1 有错；2 用法不对、读不到产出目录，或成品还没落成。

两条方向相反的检查：

  - 产出里定义过的条目，在成品里都要找得到——**这是这一条要管的主要毛病**：文档里
    写了 TM-6、TCOV-47、ENV-12，成品里一处也没提，两边就各说各的，拿编号搜不过去。
    六类都查；决策（DEC-）不查这一条，它只在成品与产出有出入时才写，见下。
  - 成品里出现的编号，在产出里都要有定义处——引了一个不存在的号，读的人会以为漏看了
    哪一份文档，其实是那个号写错了。七类都查，含 DEC-。

怎么看出成品里「有」这个编号：编号照抄，代码里写不成连字符就换成下划线（`TC-30`
写成 `TC_30`），数字照原样、不补零（不写 `TC_030`、`TC_03`）。就这两种写法，别的一种不认
——认宽了，编号就成了「大概是这一条」，搜的时候还得猜是哪种写法。

判断性的东西这里不管：成品里那条测试测得对不对、编号标对没标对、名字与英文名是不是
同一个，都要人看。脚本只管「这个号在成品里出现过没有」「成品里的号有没有出处」。

契约不在这份脚本里另立一套：什么算定义处直接复用 check_docs.py 的判定，栏位也从它那里取
（两边一旦分叉，这边说「定义了」那边说「没有」，人就不知道该信谁）。成品落点表在哪一块，
见 `references/文档模板.md` 第四节。
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_docs  # noqa: E402  「什么是定义处」只有一份，见 check_docs.py

# 六类要正向查（定义了就得在成品里出现），各按自己那份文档的栏位认定义处。
# 认法必须与 issue_ids.py 的 PREFIXES 一致——它们查的是同一个对象。
CLASSES = [
    ("测试模型", "TM-", []),
    ("测试覆盖项", "TCOV-", check_docs.COV_COLS),
    ("测试用例", "TC-", check_docs.CASE_COLS),
    ("测试规程", "TP-", []),
    ("测试数据项", "DATA-", check_docs.DATA_COLS),
    ("测试环境项", "ENV-", check_docs.ENV_COLS),
]
# 决策只反查：它在成品里该不该出现，看这条成品与产出有没有出入，脚本判不了
DECISION = ("决策", "DEC-", check_docs.DEC_COLS)

# 成品落点表（测试用例规格说明的第五块）：表头与「还没落成」那句话的写法都在
# check_docs.py 里定，这里跟着用——两处各写一份，改了一处另一处就开始骗人。
PLACE_COLS = check_docs.PLACE_COLS
NOT_YET = check_docs.NOT_YET

def id_pattern(prefix):
    """认这个前缀的编号在成品里的写法：分隔符写连字符或下划线都算。

    传进来的前缀带着分隔符（`TM-`、`TC-`，项目自己的 `Lid-` 也一样），这里把它换成
    「连字符或下划线」那一格，别在它后面再接一个——接了就要求成品里写成 `TM--1`。

    数字不补零：`TC-1` 写成 `TC_1`，不写 `TC_01`——补了零，`TC-1` 就搜不到它了，
    而搜一下正是这张对照要管的事。数字后面也不许再接数字——不接的话 `TC-1` 会在
    `TC-15` 里命中。就这两种写法，不认第三种：认宽了，编号就成了「大概是这一条」。
    """
    base = prefix[:-1] if prefix.endswith("-") else prefix
    return re.compile(re.escape(base) + r"[-_](?!0)(\d+)(?!\d)")


# 超长的成品文件（打包进去的日志之类）不读，省得把内存和屏幕撑满
MAX_BYTES = 8 * 1024 * 1024


def read_docs(root):
    """读产出目录里那六份文档，返回 {文件名: 正文}；缺哪份都照样往下走。"""
    texts = {}
    for name in check_docs.DOCS:
        path = root / name
        if path.is_file():
            texts[name] = path.read_text(encoding="utf-8")
    return texts


def defined_ids(texts):
    """六类加决策，各自已定义的编号集合：{前缀: {编号}}。"""
    out = {}
    for _, prefix, cols in CLASSES + [DECISION]:
        ids = set()
        for text in texts.values():
            ids |= set(check_docs.defined(check_docs.tables(text), text, cols, prefix))
        out[prefix] = ids
    return out


def place_paths(texts):
    """从测试用例规格说明的「成品落点」表里取成品路径。

    返回 (路径列表, 说明)；表没见着、或者只写了「还没落成」时路径列表为空，
    说明里写清是哪一种。表里的路径按当前目录解——与命令行给路径时一样。
    """
    doc = texts.get(check_docs.CASE_DOC, "")
    block = check_docs.place_block(doc)
    if block is None:
        return [], "测试用例规格说明里没有「%s」这一块，也没在命令行上给成品路径" % check_docs.PLACE_HEAD

    paths = []
    for head, body in check_docs.tables(block):
        if not all(c in head for c in PLACE_COLS):
            continue
        i = head.index(PLACE_COLS[0])
        for row in body:
            if len(row) > i and row[i]:
                paths.append(row[i].strip("`").strip())
    if paths:
        return paths, ""
    if NOT_YET in block:
        return [], "成品落点表上写着「%s」" % NOT_YET
    return [], "「成品落点」那一块里没有成品落点表"


def scan(paths, root):
    """把成品读成一段文本。返回 (正文, 读到的份数, 跳过没读的说明, 读不到的路径, 排掉几份产出)。

    产出目录里那六份文档不算成品：不排掉的话，把产出目录整个当成品路径传进来，
    六份文档里什么编号都有，检查就白过了——那种「全过」比报错还会骗人。
    """
    parts, n, skipped, missing, dropped = [], 0, [], [], 0
    docs = {(root / name).resolve() for name in check_docs.DOCS}
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            missing.append(raw)
            continue
        files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file())
        for f in files:
            try:
                if f.resolve() in docs:
                    dropped += 1
                    continue
                if f.stat().st_size > MAX_BYTES:
                    skipped.append("%s（超过 %d MB）" % (f, MAX_BYTES // 1024 // 1024))
                    continue
                parts.append(f.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                # 二进制与不是 UTF-8 的样本文件：编号不会写在那里，跳过并说一声
                skipped.append(str(f))
                continue
            n += 1
    return "\n".join(parts), n, skipped, missing, dropped


def check_forward(blob, ids, rep):
    """六类：定义了、成品里却一个也没出现的编号。"""
    for label, prefix, _ in CLASSES:
        nums = ids.get(prefix, set())
        if not nums:
            continue
        seen = {int(m) for m in id_pattern(prefix).findall(blob)}
        miss = sorted(set(nums) - seen)
        if miss:
            rep.err(label, "这些条目定义了，成品里一处也没出现：%s"
                           "——编号在成品里照抄（`TC-30` 写成 `TC_30`），一条至少出现一次"
                    % check_docs.brief(miss, prefix))
        else:
            rep.ok("%s %d 条，成品里都找得到" % (label, len(nums)))


def check_backward(blob, ids, rep):
    """成品里出现的编号，在产出里都要有定义处。"""
    dangling = {}
    for label, prefix, _ in CLASSES + [DECISION]:
        seen = {int(m) for m in id_pattern(prefix).findall(blob)}
        miss = sorted(seen - ids.get(prefix, set()))
        if miss:
            dangling[label] = (prefix, miss)
    if not dangling:
        rep.ok("成品里出现的编号，产出里都有定义处")
        return
    for label, (prefix, miss) in dangling.items():
        rep.err(label, "成品里出现了产出里没有定义处的编号：%s——号写错了，或者产出里漏了这条"
                % check_docs.brief(miss, prefix))


def main():
    # 在解析参数之前：用法写错、读不到目录时那几句提示也是中文
    check_docs.prefer_utf8(sys.stdout)
    check_docs.prefer_utf8(sys.stderr)
    if len(sys.argv) < 2:
        print("用法：python check_landing.py <产出目录> [成品路径 ...]")
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print("读不到产出目录：%s" % root)
        return 2
    texts = read_docs(root)
    if not texts:
        print("产出目录里六份文档一份都没读到，先确认目录对不对：%s" % root)
        return 2

    paths = list(sys.argv[2:])
    reason = ""
    if not paths:
        paths, reason = place_paths(texts)
    if not paths:
        print("没拿到成品路径：%s。" % (reason or "命令行上没给，产出里也没写"))
        print("把成品路径写在命令后面，或者在测试用例规格说明的「成品落点」表里填上——"
              "两份都填了，就不用每次在命令行上抄一遍。")
        return 2

    ids = defined_ids(texts)
    total = sum(len(v) for prefix, v in ids.items() if prefix != DECISION[1])
    if total == 0:
        print("产出目录里一个条目都认不出来，先确认文档写没写、栏位对不对：%s" % root)
        return 2

    rep = check_docs.Report()
    print("产出目录：%s" % root)
    blob, n, skipped, missing, dropped = scan(paths, root)
    print("成品：读到 %d 份文件，共 %d 个字符\n" % (n, len(blob)))
    for raw in missing:
        rep.err("成品路径", "读不到：%s" % raw)
    if dropped:
        rep.warn("成品路径", "产出目录里那六份文档没算成品，跳过了 %d 份——"
                             "成品指落下来的代码与评测用例，文档自己不算" % dropped)
    if n == 0:
        print("成品一份都没读到，先确认路径对不对。")
        return 2
    if skipped:
        rep.warn("成品路径", "这些文件没读（二进制，或者不是 UTF-8）：%s"
                             % "、".join(skipped[:5]) + ("…" if len(skipped) > 5 else ""))

    check_forward(blob, ids, rep)
    print()
    check_backward(blob, ids, rep)

    print("\n共 %d 处错误，%d 处提示。" % (rep.errors, rep.warns))
    if rep.errors == 0:
        print("编号在两边对得上。成品里的测试测得对不对、号标对没标对，还得自己看。")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
