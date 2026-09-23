#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_docs.py 自己的测试。

    python tests/test-case-design/test_check_docs.py

先造一套最小但合规的产出，确认它判过；再一处一处地改坏，确认每一处都被逮住。
检查脚本自己判错了比没有更糟——放过去一处，后面所有产出都跟着错。
"""

import contextlib
import io
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本还在 plugin/skills/ 里，所以往上两层
sys.path.insert(0, str(HERE.parent.parent / "plugin" / "skills" / "test-case-design" / "scripts"))
import check_docs  # noqa: E402

MODEL = check_docs.MODEL_DOC
CASE = check_docs.CASE_DOC
PROC = check_docs.PROC_DOC
DATA = check_docs.DATA_DOC
ENV = check_docs.ENV_DOC

MODEL_TEXT = """# 测试模型规格说明

## TM-1 示例模型

**唯一标识符**：TM-1

**目标**：示例用的一小块。

**优先级**：高。

**测试策略摘要**：等价类划分一门，覆盖率要求 100%。

**测试模型**：一段说明。

文档末尾的「依据 → 模型」对应表：

| 依据的出处 | 模型编号 | 说明 |
|:---|:---|:---|
| 需求 1 | TM-1 | 全部 |
"""

CASE_TEXT = """# 测试用例规格说明

## 一、测试覆盖项

| 唯一标识符 | 描述 | 优先级 | 可追溯性 |
|:---|:---|:---|:---|
| TCOV-1 | 有效等价类：甲 | 高 | TM-1 |

## 二、测试用例

| 唯一标识符 | 目标 | 优先级 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|
| TC-1 | 验证甲 | 高 | 按 DATA-1 取一段文本 | 输出甲 |

## 三、覆盖项 ↔ 用例对应表

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 有效等价类：甲 | TC-1 |
"""

PROC_TEXT = """# 测试规程规格说明

## TP-1 主干

**唯一标识符**：TP-1

**目标**：把用例跑一遍。

**优先级**：高。

**启动**：ENV-1 就位。

**有序执行测试用例**：1. TC-1

**与其他规程的关系**：无。

**停止与结束**：无。
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

BASE = {
    MODEL: MODEL_TEXT,
    CASE: CASE_TEXT,
    PROC: PROC_TEXT,
    DATA: DATA_TEXT,
    ENV: ENV_TEXT,
}

# 每一例：说明、改哪儿（文件名, 把什么, 换成什么）、丢掉哪份、期望退出码、输出里该出现的话
# （这句话以 ! 开头就表示「不该出现」）
CASES = [
    ("基线：五份齐、编号连续、对应表不留空", None, (), 0, "机械项全过"),
    ("缺一份文档", None, (ENV,), 1, "缺这份文档"),
    ("覆盖项跳号", (CASE, "| TCOV-1 |", "| TCOV-2 |"), (), 1, "编号不是从 1 起连续"),
    ("对应表留空", (CASE, "| TCOV-1 | 有效等价类：甲 | TC-1 |",
                    "| TCOV-1 | 有效等价类：甲 |  |"), (), 1, "留空"),
    ("对应表引用了没写出来的用例",
     (CASE, "| TCOV-1 | 有效等价类：甲 | TC-1 |",
      "| TCOV-1 | 有效等价类：甲 | TC-9 |"), (), 1, "没有定义处"),
    ("有用例没被任何覆盖项引用",
     (CASE, "| TC-1 | 验证甲 | 高 | 按 DATA-1 取一段文本 | 输出甲 |",
      "| TC-1 | 验证甲 | 高 | 按 DATA-1 取一段文本 | 输出甲 |\n| TC-2 | 验证乙 | 高 | 输入乙 | 输出乙 |"),
     (), 1, "没被任何覆盖项引用"),
    ("覆盖项追溯到一个不存在的模型",
     (CASE, "| TCOV-1 | 有效等价类：甲 | 高 | TM-1 |",
      "| TCOV-1 | 有效等价类：甲 | 高 | TM-9 |"), (), 1, "模型文档里没有这个模型"),
    ("模型没进「依据 → 模型」表",
     (MODEL, "| 需求 1 | TM-1 | 全部 |", ""), (), 1, "追溯断在这里"),
    ("用例表首栏改了名",
     (CASE, "| 唯一标识符 | 目标 | 优先级 | 输入 | 预期结果 |",
      "| 用例编号 | 目标 | 优先级 | 输入 | 预期结果 |"), (), 1, "唯一标识符"),
    ("测试数据需求多出一栏",
     (DATA, "| 唯一标识符 | 描述 | 重置需求 |", "| 唯一标识符 | 描述 | 重置需求 | 责任人 |"), (), 1, "多出模板没有的栏"),
    ("漏进一个禁用词",
     (ENV, "| ENV-1 | 解释器 | Python 3 |",
      "| ENV-1 | 解释器 | Python 3，测试脚本另行说明 |"), (), 1, "不该出现的词"),
    ("带出了技能里的出处",
     (DATA, "| DATA-1 | 一段文本 |", "| DATA-1 | 一段文本，见 references/文档模板.md |"),
     (), 1, "不该出现的词"),
    ("「重置需求」栏留空",
     (DATA, "| DATA-1 | 一段文本 | 不需要 |", "| DATA-1 | 一段文本 |  |"), (), 1, "有一行有空栏"),
    ("用例引用了没有定义处的数据项",
     (CASE, "按 DATA-1 取一段文本", "按 DATA-9 取一段文本"), (), 1, "引用了没有定义处的 DATA-9"),
    ("规程引用了没有定义处的环境项",
     (PROC, "ENV-1 就位", "ENV-9 就位"), (), 1, "引用了没有定义处的 ENV-9"),
    ("数据项有定义处却没人引用",
     (CASE, "按 DATA-1 取一段文本", "用一段文本作输入"), (), 0, "定义了，但用例与规程里都没引用：DATA-1"),
    ("环境项有定义处却没人引用",
     (PROC, "ENV-1 就位", "无"), (), 0, "定义了，但用例与规程里都没引用：ENV-1"),
    ("数据项用了项目自己的编号（文档模板第二节允许跟随惯例，脚本不认这个前缀——已知边界）",
     (DATA, "| DATA-1 | 一段文本 | 不需要 |", "| DBR-1 | 一段文本 | 不需要 |"), (), 1, "一个 DATA- 编号都没有"),
    ("引用的编号写在「预期结果」栏里，也算引用，不误报孤儿",
     (CASE, "| TC-1 | 验证甲 | 高 | 按 DATA-1 取一段文本 | 输出甲 |",
      "| TC-1 | 验证甲 | 高 | 用一段文本作输入 | 输出 DATA-1 的内容 |"),
     (), 0, "!定义了，但用例与规程里都没引用"),
    ("只写了规程、没写用例规格说明——两份引用文档缺一份，孤儿判定整块跳过，不刷屏",
     None, (CASE,), 1, "!定义了，但用例与规程里都没引用"),
]


def run_check(root):
    """跑一遍 check_docs，返回（退出码, 输出）。"""
    buf = io.StringIO()
    old = sys.argv
    sys.argv = ["check_docs.py", str(root)]
    try:
        with contextlib.redirect_stdout(buf):
            code = check_docs.main()
    finally:
        sys.argv = old
    return code, buf.getvalue()


def make(root, tweak, drop):
    docs = dict(BASE)
    if tweak:
        name, old, new = tweak
        if old not in docs[name]:
            raise AssertionError("测试自己写错了：%s 里找不到要替换的那段" % name)
        docs[name] = docs[name].replace(old, new)
    for name, text in docs.items():
        if name in drop:
            continue
        (root / name).write_text(text, encoding="utf-8")


def main():
    print("跑 %d 例\n" % len(CASES))
    bad = 0
    for title, tweak, drop, want_code, want_text in CASES:
        root = Path(tempfile.mkdtemp(prefix="check-docs-"))
        try:
            make(root, tweak, drop)
            code, out = run_check(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        problems = []
        if code != want_code:
            problems.append("退出码 %s，期望 %s" % (code, want_code))
        if want_text.startswith("!"):
            if want_text[1:] in out:
                problems.append("输出里不该有「%s」" % want_text[1:])
        elif want_text not in out:
            problems.append("输出里没有「%s」" % want_text)
        if problems:
            bad += 1
            print("[失败] %s" % title)
            for p in problems:
                print("       %s" % p)
            print("       —— 实际输出 ——")
            for line in out.strip().splitlines():
                print("       " + line)
        else:
            print("[通过] %s" % title)

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
