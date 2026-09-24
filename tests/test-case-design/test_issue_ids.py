#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""issue_ids.py 自己的测试。

    python tests/test-case-design/test_issue_ids.py

发号发错了比不发更糟：号一旦写进产出文档就承担追溯，重号得一条条改回来。所以这里把
「基准从哪来」的几种情形都摆出来跑一遍：空目录、只写了一半、只被引用没有定义处、
前缀之间串不串号，外加用法不对时该不该退出码 2。

还钉着一件事：issue_ids 认「已定义的条目」用的判定是从 check_docs 直接调的，不是另抄
一份——两边看法一旦分叉，发出去的号就会撞上文档里已有的号。
"""

import contextlib
import io
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "plugin" / "skills" / "test-case-design" / "scripts"))
import check_docs  # noqa: E402
import issue_ids  # noqa: E402

CASE = check_docs.CASE_DOC
PROC = check_docs.PROC_DOC
DATA = check_docs.DATA_DOC
ENV = check_docs.ENV_DOC
MODEL = check_docs.MODEL_DOC
DECISION = check_docs.DECISION_DOC

MODEL_TEXT = """# 测试模型规格说明

## TM-1 甲模型

**唯一标识符**：TM-1
"""

CASE_TEXT = """# 测试用例规格说明

## 一、测试覆盖项

| 唯一标识符 | 描述 | 风险等级 | 可追溯性 |
|:---|:---|:---|:---|
| TCOV-1 | 有效等价类：甲 | 高 | TM-1 |
| TCOV-2 | 有效等价类：乙 | 高 | TM-1 |

## 二、测试用例

| 唯一标识符 | 目标 | 风险等级 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|
| TC-1 | 验证甲 | 高 | 输入甲 | 输出甲 |

## 三、覆盖项 ↔ 用例对应表

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 有效等价类：甲 | TC-1 |
| TCOV-2 | 有效等价类：乙 | TC-1 |
"""

# 对应表里引用了 TC-2，但正文里没有这条用例——只在引用里出现的号
CASE_TEXT_STRAY_REF = CASE_TEXT.replace("| TCOV-2 | 有效等价类：乙 | TC-1 |",
                                        "| TCOV-2 | 有效等价类：乙 | TC-2 |")

# 只有覆盖项、没有用例：用来验 TCOV- 那一串不会算进 TC- 的基准
COV_ONLY_TEXT = """# 测试用例规格说明

## 一、测试覆盖项

| 唯一标识符 | 描述 | 风险等级 | 可追溯性 |
|:---|:---|:---|:---|
| TCOV-1 | 有效等价类：甲 | 高 | TM-1 |
| TCOV-2 | 有效等价类：乙 | 高 | TM-1 |
"""

PROC_TEXT = """# 测试规程规格说明

## TP-1 主干

**唯一标识符**：TP-1

**有序执行测试用例**：1. TC-1
"""

DATA_TEXT = """# 测试数据需求

| 唯一标识符 | 描述 | 重置需求 |
|:---|:---|:---|
| DATA-1 | 一段文本 | 不需要 |
"""

ENV_TEXT = """# 测试环境需求

| 唯一标识符 | 测试环境项 | 描述 |
|:---|:---|:---|
| ENV-1 | 解释器 | Python 3 |
"""

DECISION_TEXT = """# 决策依据

| 唯一标识符 | 在哪一步 | 决定 | 考虑过的其他做法 | 依据 | 依据的来源 |
|:---|:---|:---|:---|:---|:---|
| DEC-1 | 第 1 步 | 只选等价类划分一门 | 判定表测试；分叉少 | 只有一处取值分歧 | 从测试项推的 |
| DEC-2 | 第 1 步 | 模型建到取值一级 | 建到语句一级；没必要 | 完成准则取 100% | 技能定的 |
"""

BASE = {
    MODEL: MODEL_TEXT,
    CASE: CASE_TEXT,
    PROC: PROC_TEXT,
    DATA: DATA_TEXT,
    ENV: ENV_TEXT,
    DECISION: DECISION_TEXT,
}

# 项目自己的编号惯例：不带 TM- 那一套，脚本按标题、加粗标签、表首格认
CUSTOM_TEXT = """# 测试用例规格说明

## Lid-1 盖板锁定

| 用例 | 目标 |
|:---|:---|
| Lid-2 | 验证解锁 |
"""

# 每一例：说明、往目录里写哪几份文档、命令行参数、期望退出码、
# 输出里该有哪些话 / 不该有哪些话（可选）、输出该正好是哪几行（可选）
CASES = [
    dict(
        name="空目录：七种编号都从 1 起",
        docs={},
        argv=["<目录>"],
        code=0,
        want=["| TM- | 无 | TM-1 |", "| TCOV- | 无 | TCOV-1 |", "| TC- | 无 | TC-1 |",
              "| TP- | 无 | TP-1 |", "| DATA- | 无 | DATA-1 |", "| ENV- | 无 | ENV-1 |",
              "| DEC- | 无 | DEC-1 |"],
        not_want=["提示"],
    ),
    dict(
        name="六份都在：总览报的是已经用到的最大号",
        docs=BASE,
        argv=["<目录>"],
        code=0,
        want=["| TM- | TM-1 | TM-2 |", "| TCOV- | TCOV-2 | TCOV-3 |", "| TC- | TC-1 | TC-2 |",
              "| TP- | TP-1 | TP-2 |", "| DATA- | DATA-1 | DATA-2 |", "| ENV- | ENV-1 | ENV-2 |",
              "| DEC- | DEC-2 | DEC-3 |"],
        not_want=["提示"],
    ),
    dict(
        name="只写了其中两份：其余三种仍从 1 起",
        docs={MODEL: MODEL_TEXT, CASE: CASE_TEXT},
        argv=["<目录>"],
        code=0,
        want=["| TC- | TC-1 | TC-2 |", "| TM- | TM-1 | TM-2 |", "| ENV- | 无 | ENV-1 |"],
        not_want=["提示"],
    ),
    dict(
        name="只有用例文档、模型文档还没落盘：引用到的 TM-1 报提示，号照发",
        docs={CASE: CASE_TEXT},
        argv=["<目录>", "TM-"],
        code=0,
        want=["TM-1", "提示"],
    ),
    dict(
        name="发号：接着盘上最大号、连号、一行一个",
        docs=BASE,
        argv=["<目录>", "TC-", "--count", "3"],
        code=0,
        lines=["TC-2", "TC-3", "TC-4"],
    ),
    dict(
        name="发号：不给 --count 就一个",
        docs=BASE,
        argv=["<目录>", "TC-"],
        code=0,
        lines=["TC-2"],
    ),
    dict(
        name="只在引用里出现、没有定义处的号不当基准，但要提示",
        docs={CASE: CASE_TEXT_STRAY_REF},
        argv=["<目录>", "TC-"],
        code=0,
        want=["TC-2", "提示"],
        not_want=["TC-3"],
    ),
    dict(
        name="前缀之间不串号：满盘 TCOV- 与 TM- 不动 TC- 的基准",
        docs={MODEL: MODEL_TEXT, CASE: COV_ONLY_TEXT},
        argv=["<目录>", "TC-"],
        code=0,
        lines=["TC-1"],
    ),
    dict(
        name="决策依据接着盘上往下发号",
        docs=BASE,
        argv=["<目录>", "DEC-", "--count", "2"],
        code=0,
        lines=["DEC-3", "DEC-4"],
    ),
    dict(
        name="项目自己的编号惯例照传",
        docs={CASE: CUSTOM_TEXT},
        argv=["<目录>", "Lid-", "--count", "2"],
        code=0,
        lines=["Lid-3", "Lid-4"],
    ),
    dict(
        name="前缀漏了结尾那一横：不发号，说穿",
        docs=BASE,
        argv=["<目录>", "TC", "--count", "2"],
        code=2,
        want=["TC-1", "漏了"],
        not_want=["TC1", "TC2"],
    ),
    dict(
        name="用法：一个参数都不给",
        docs={},
        argv=[],
        code=2,
        want=["用法"],
    ),
    dict(
        name="用法：--count 不带前缀",
        docs={},
        argv=["<目录>", "--count", "3"],
        code=2,
        want=["用法"],
    ),
    dict(
        name="用法：--count 不是正整数",
        docs={},
        argv=["<目录>", "TC-", "--count", "0"],
        code=2,
        want=["用法"],
    ),
    dict(
        name="用法：参数给多了",
        docs={},
        argv=["<目录>", "TC-", "TP-"],
        code=2,
        want=["用法"],
    ),
    dict(
        name="用法：不认识的选项",
        docs={},
        argv=["<目录>", "--prefix", "TC-"],
        code=2,
        want=["用法"],
    ),
    dict(
        name="目录不存在",
        docs={},
        argv=["<没有的目录>", "TC-"],
        code=2,
        want=["读不到目录"],
    ),
]


def run(argv, root):
    """跑一遍 issue_ids，返回（退出码, 输出）。"""
    subst = {
        "<目录>": str(root),
        "<没有的目录>": str(root / "没有这个目录"),
    }
    buf = io.StringIO()
    old = sys.argv
    sys.argv = ["issue_ids.py"] + [subst.get(a, a) for a in argv]
    try:
        with contextlib.redirect_stdout(buf):
            code = issue_ids.main()
    finally:
        sys.argv = old
    return code, buf.getvalue()


def check(case):
    root = Path(tempfile.mkdtemp(prefix="issue-ids-"))
    try:
        for name, text in case["docs"].items():
            (root / name).write_text(text, encoding="utf-8")
        code, out = run(case["argv"], root)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    problems = []
    if code != case["code"]:
        problems.append("退出码 %s，期望 %s" % (code, case["code"]))
    for want in case.get("want", []):
        if want not in out:
            problems.append("输出里没有「%s」" % want)
    for unwanted in case.get("not_want", []):
        if unwanted in out:
            problems.append("输出里不该有「%s」" % unwanted)
    if "lines" in case:
        got = [line.strip() for line in out.splitlines() if line.strip()]
        if got != case["lines"]:
            problems.append("打出来的不是那几行：期望 %s，实际 %s" % (case["lines"], got))
    return problems, out


def main():
    print("跑 %d 例\n" % len(CASES))
    bad = 0
    for case in CASES:
        problems, out = check(case)
        if problems:
            bad += 1
            print("[失败] %s" % case["name"])
            for p in problems:
                print("       %s" % p)
            print("       —— 实际输出 ——")
            for line in out.strip().splitlines():
                print("       " + line)
        else:
            print("[通过] %s" % case["name"])

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
