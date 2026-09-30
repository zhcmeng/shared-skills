#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_docs.py 自己的测试。

    python tests/test-case-design/test_check_docs.py

先造一套最小但合规的产出，确认它判过；再一处一处地改坏，确认每一处都被逮住。
检查脚本自己判错了比没有更糟——放过去一处，后面所有产出都跟着错。
"""

import contextlib
import io
import os
import shutil
import subprocess
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
DECISION = check_docs.DECISION_DOC

MODEL_TEXT = """# 测试模型规格说明

## TM-1 示例模型

**唯一标识符**：TM-1

**英文名**：demo_model

**目标**：示例用的一小块。

**风险等级**：高。

**测试策略摘要**：等价类划分一门，覆盖率要求 100%。

**测试模型**：一段说明。

文档末尾的「依据 → 模型」对应表：

| 依据的出处 | 模型编号 | 说明 |
|:---|:---|:---|
| 需求 1 | TM-1 | 全部 |
"""

CASE_TEXT = """# 测试用例规格说明

## 一、测试覆盖项

| 唯一标识符 | 英文名 | 描述 | 风险等级 | 可追溯性 |
|:---|:---|:---|:---|:---|
| TCOV-1 | valid_class_a | 有效等价类：甲 | 高 | TM-1 |
| TCOV-2 | valid_class_b | 有效等价类：乙 | 高 | TM-1 |

## 二、测试用例

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|:---|
| TC-1 | verify_a | 验证甲 | 高 | 按 DATA-1 取一段文本 | 输出甲 |

## 三、覆盖项 ↔ 用例对应表

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 有效等价类：甲 | TC-1 |
| TCOV-2 | 有效等价类：乙 | TC-1 |

## 四、覆盖率自检

| 技术（档位） | 覆盖项编号 | 覆盖项总数 T | 已被用例覆盖 N | 覆盖率 N÷T | 完成准则要求 |
|:---|:---|:---|:---|:---|:---|
| 等价类划分 | TCOV-1～TCOV-2 | 2 | 2 | 2÷2＝100% | 100% |

## 五、成品落点

| 成品 | 落的是哪些条目 |
|:---|:---|
| `tests/demo/test_demo.py` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |
"""

PROC_TEXT = """# 测试规程规格说明

## TP-1 主干

**唯一标识符**：TP-1

**英文名**：main_path

**目标**：把用例跑一遍。

**风险等级**：高。

**执行器**：脚本。

**改动文件**：只读。

**启动**：ENV-1 就位。

**有序执行测试用例**：1. TC-1

**与其他规程的关系**：无。

**停止与结束**：无。

## 各批落到哪

| 批次 | 规程 | 执行器 | 落到哪 | 用例目录名 | 说明 |
|:---|:---|:---|:---|:---|:---|
| 脚本批 | TP-1 | 脚本 | `tests/demo/test_demo.py` |  | 判据落在命令与盘上的文件上 |
"""

DATA_TEXT = """# 测试数据需求

| 唯一标识符 | 英文名 | 描述 | 重置需求 |
|:---|:---|:---|:---|
| DATA-1 | demo_text | 一段文本 | 不需要 |
"""

ENV_TEXT = """# 测试环境需求

| 唯一标识符 | 英文名 | 测试环境项 | 描述 |
|:---|:---|:---|:---|
| ENV-1 | interpreter | 解释器 | Python 3 |
"""

DECISION_TEXT = """# 决策依据

## 用户决策

| 唯一标识符 | 在哪一步 | 决定 | 考虑过的其他做法 | 依据 | 依据的来源 |
|:---|:---|:---|:---|:---|:---|
| DEC-1 | 第 0 步 | 风险等级：取值分歧那一处判高，其余判中 | 一律判高；会让这一栏失去区分度 | 用户点名的那一处最怕出错 | 用户给的 |

## 模型决策

| 唯一标识符 | 在哪一步 | 决定 | 考虑过的其他做法 | 依据 | 依据的来源 |
|:---|:---|:---|:---|:---|:---|
| DEC-2 | 第 1 步 | 只选等价类划分一门 | 判定表测试；分叉少，建不出有意义的表 | 测试项只有一处取值分歧 | 从测试项推的 |
"""

BASE = {
    MODEL: MODEL_TEXT,
    CASE: CASE_TEXT,
    PROC: PROC_TEXT,
    DATA: DATA_TEXT,
    ENV: ENV_TEXT,
    DECISION: DECISION_TEXT,
}

# 「各批落到哪」那张表的两版：基线用落成可跑测试的一版（BATCH_SCRIPT，此刻就在
# PROC_TEXT 里）；下面那些例把它整个换成落成评测用例的一版（BATCH_MODEL），
# 试「用例目录名」这一栏。两版都带这一栏——基线那一行是脚本批，那一格空着。
BATCH_SCRIPT = """| 批次 | 规程 | 执行器 | 落到哪 | 用例目录名 | 说明 |
|:---|:---|:---|:---|:---|:---|
| 脚本批 | TP-1 | 脚本 | `tests/demo/test_demo.py` |  | 判据落在命令与盘上的文件上 |"""

BATCH_MODEL = """| 批次 | 规程 | 执行器 | 落到哪 | 用例目录名 | 说明 |
|:---|:---|:---|:---|:---|:---|
| 模型批 | TP-1 | 子代理 | `evals/demo/cases/` | tp01-01-TC-1-verify_a | 判据要读一轮模型的行为 |"""

# 「覆盖率自检」那一块的表行原文（基线里就这一行：一门技术，两条覆盖项都已被
# TC-1 覆盖）。下面那些例拿它改坏一处。
COVER_ROW = "| 等价类划分 | TCOV-1～TCOV-2 | 2 | 2 | 2÷2＝100% | 100% |"

# 每一例：说明、改哪儿（文件名, 把什么, 换成什么）、丢掉哪份、期望退出码、输出里该出现的话
# （这句话以 ! 开头就表示「不该出现」）
CASES = [
    ("基线：六份齐、编号连续、对应表不留空", None, (), 0, "机械项全过"),
    ("缺一份文档", None, (ENV,), 1, "缺这份文档"),
    ("覆盖项跳号", (CASE, "| TCOV-1 |", "| TCOV-2 |"), (), 1, "编号不是从 1 起连续"),
    ("对应表留空", (CASE, "| TCOV-1 | 有效等价类：甲 | TC-1 |",
                    "| TCOV-1 | 有效等价类：甲 |  |"), (), 1, "留空"),
    ("对应表引用了没写出来的用例",
     (CASE, "| TCOV-1 | 有效等价类：甲 | TC-1 |",
      "| TCOV-1 | 有效等价类：甲 | TC-9 |"), (), 1, "没有定义处"),
    ("有用例没被任何覆盖项引用",
     (CASE, "| TC-1 | verify_a | 验证甲 | 高 | 按 DATA-1 取一段文本 | 输出甲 |",
      "| TC-1 | verify_a | 验证甲 | 高 | 按 DATA-1 取一段文本 | 输出甲 |\n"
      "| TC-2 | verify_b | 验证乙 | 高 | 输入乙 | 输出乙 |"),
     (), 1, "没被任何覆盖项引用"),
    ("覆盖项追溯到一个不存在的模型",
     (CASE, "| TCOV-1 | valid_class_a | 有效等价类：甲 | 高 | TM-1 |",
      "| TCOV-1 | valid_class_a | 有效等价类：甲 | 高 | TM-9 |"), (), 1, "模型文档里没有这个模型"),
    ("模型没进「依据 → 模型」表",
     (MODEL, "| 需求 1 | TM-1 | 全部 |", ""), (), 1, "追溯断在这里"),
    ("用例表首栏改了名",
     (CASE, "| 唯一标识符 | 英文名 | 目标 | 风险等级 | 输入 | 预期结果 |",
      "| 用例编号 | 英文名 | 目标 | 风险等级 | 输入 | 预期结果 |"), (), 1, "唯一标识符"),
    ("测试数据需求多出一栏",
     (DATA, "| 唯一标识符 | 英文名 | 描述 | 重置需求 |",
      "| 唯一标识符 | 英文名 | 描述 | 重置需求 | 责任人 |"), (), 1, "多出模板没有的栏"),
    ("漏进一个禁用词",
     (ENV, "| ENV-1 | interpreter | 解释器 | Python 3 |",
      "| ENV-1 | interpreter | 解释器 | Python 3，测试脚本另行说明 |"), (), 1, "不该出现的词"),
    ("产出里还用旧栏位名「优先级」——既缺栏目又踩禁用词",
     (CASE, "| 唯一标识符 | 英文名 | 描述 | 风险等级 | 可追溯性 |",
      "| 唯一标识符 | 英文名 | 描述 | 优先级 | 可追溯性 |"), (), 1, "不该出现的词"),
    ("带出了技能里的出处",
     (DATA, "| DATA-1 | demo_text | 一段文本 |",
      "| DATA-1 | demo_text | 一段文本，见 references/文档模板.md |"),
     (), 1, "不该出现的词"),
    ("「重置需求」栏留空",
     (DATA, "| DATA-1 | demo_text | 一段文本 | 不需要 |", "| DATA-1 | demo_text | 一段文本 |  |"),
     (), 1, "有一行有空栏"),
    ("用例引用了没有定义处的数据项",
     (CASE, "按 DATA-1 取一段文本", "按 DATA-9 取一段文本"), (), 1, "引用了没有定义处的 DATA-9"),
    ("规程引用了没有定义处的环境项",
     (PROC, "ENV-1 就位", "ENV-9 就位"), (), 1, "引用了没有定义处的 ENV-9"),
    ("规程标题带了中文序号、没以编号起头——认不出这条规程从哪儿起，块自然切不出用例",
     (PROC, "## TP-1 主干", "## 一、TP-1 主干"), (), 1, "没以编号起头"),
    ("数据项有定义处却没人引用",
     (CASE, "按 DATA-1 取一段文本", "用一段文本作输入"), (), 0, "定义了，但用例与规程里都没引用：DATA-1"),
    ("环境项有定义处却没人引用",
     (PROC, "ENV-1 就位", "无"), (), 0, "定义了，但用例与规程里都没引用：ENV-1"),
    ("数据项用了项目自己的编号（文档模板第二节允许跟随惯例，脚本不认这个前缀——已知边界）",
     (DATA, "| DATA-1 | demo_text | 一段文本 | 不需要 |", "| DBR-1 | demo_text | 一段文本 | 不需要 |"),
     (), 1, "一个 DATA- 编号都没有"),
    ("引用的编号写在「预期结果」栏里，也算引用，不误报孤儿",
     (CASE, "| TC-1 | verify_a | 验证甲 | 高 | 按 DATA-1 取一段文本 | 输出甲 |",
      "| TC-1 | verify_a | 验证甲 | 高 | 用一段文本作输入 | 输出 DATA-1 的内容 |"),
     (), 0, "!定义了，但用例与规程里都没引用"),
    ("只写了规程、没写用例规格说明——两份引用文档缺一份，孤儿判定整块跳过，不刷屏",
     None, (CASE,), 1, "!定义了，但用例与规程里都没引用"),
    ("缺决策依据文档", None, (DECISION,), 1, "缺这份文档"),
    ("决策依据的头一条被删了或被改过号——这份只增不改，编号断了就是断在这儿",
     (DECISION, "| DEC-1 |", "| DEC-2 |"), (), 1, "只增不改"),
    ("决策依据有一行空栏——「考虑过的其他做法」留空等于没写过程",
     (DECISION, "| 从测试项推的 |", "|  |"), (), 1, "有一行有空栏"),
    ("决策依据多出一栏",
     (DECISION, "| 依据 | 依据的来源 |", "| 依据 | 依据的来源 | 备注 |"),
     (), 1, "多出模板没有的栏"),

    # 决策依据分两块：「用户决策」在前（用户拍的，可以直接改），「模型决策」在后（只增不改）。
    # 分块是机械项——「依据的来源」栏只填三个值之一，哪一行归哪一块脚本判得了。
    ("「用户决策」那一块里混进一条技能定的",
     (DECISION, "| 用户给的 |", "| 技能定的 |"), (), 1, "只装「用户给的」那几条"),
    ("用户拍板的那条留在「模型决策」块里",
     (DECISION, "| 从测试项推的 |", "| 用户给的 |"), (), 1, "要单独放在「用户决策」那一块"),
    ("决策表没放在这两块里——标题改了名就认不出",
     (DECISION, "## 用户决策", "## 用户拍板的"), (), 1, "「用户决策」「模型决策」这两块"),

    # 「英文名」这一栏：给下游落成代码时照抄的名字核。
    # 期望的话都带上文件名或条目号：光写「英文名」的话，隔壁那份文档报的同类错
    # 也会让这一例假过——这一栏刚加时就是这么假过了两例。
    ("数据需求缺「英文名」栏",
     (DATA, "| 唯一标识符 | 英文名 | 描述 | 重置需求 |", "| 唯一标识符 | 描述 | 重置需求 |"),
     (), 1, "Test Data Requirements.md：缺栏目：英文名"),
    ("覆盖项缺「英文名」栏",
     (CASE, "| 唯一标识符 | 英文名 | 描述 | 风险等级 | 可追溯性 |",
      "| 唯一标识符 | 描述 | 风险等级 | 可追溯性 |"), (), 1, "覆盖项清单缺栏目：英文名"),
    ("用例表缺「英文名」栏",
     (CASE, "| 唯一标识符 | 英文名 | 目标 |", "| 唯一标识符 | 目标 |"),
     (), 1, "用例表缺栏目：英文名"),
    ("规程的「英文名」没写",
     (PROC, "**英文名**：main_path\n\n", ""), (), 1, "规程缺栏目：英文名"),
    ("英文名留空",
     (DATA, "| DATA-1 | demo_text | 一段文本 | 不需要 |", "| DATA-1 |  | 一段文本 | 不需要 |"),
     (), 1, "DATA-1 的「英文名」是空的"),
    ("英文名写成中文",
     (ENV, "| ENV-1 | interpreter | 解释器 | Python 3 |",
      "| ENV-1 | 解释器 | 解释器 | Python 3 |"), (), 1, "ENV-1 的「英文名」不合形制"),
    ("英文名用了大写驼峰",
     (CASE, "| TC-1 | verify_a | 验证甲 |", "| TC-1 | VerifyA | 验证甲 |"),
     (), 1, "TC-1 的「英文名」不合形制"),
    ("英文名中间带空格",
     (ENV, "| ENV-1 | interpreter | 解释器 |", "| ENV-1 | python interpreter | 解释器 |"),
     (), 1, "ENV-1 的「英文名」不合形制"),
    ("英文名拿编号起头——下游再拼一次编号就成了 tcov_1_tcov_1_…",
     (CASE, "| TCOV-1 | valid_class_a | 有效等价类：甲 |",
      "| TCOV-1 | tcov_1_valid_class_a | 有效等价类：甲 |"), (), 1, "TCOV-1 的「英文名」以编号起头"),
    ("模型文档没写「英文名」——模型用加粗字段，写了几个要对得上模型数",
     (MODEL, "**英文名**：demo_model\n\n", ""), (), 1, "Model Specification.md：模型缺栏目：英文名"),
    ("决策依据也给加了英文名栏——它是过程记录，不给名字",
     (DECISION, "| 依据 | 依据的来源 |", "| 依据 | 依据的来源 | 英文名 |"),
     (), 1, "Decision Basis.md：多出模板没有的栏"),

    # 第五块「成品落点」：成品（落下来的代码与评测用例）落在哪、编号在成品里怎么出现。
    # 设计的时候成品多半还没落，写成「还没落成」也算填了——但这一块不能整个没有。
    ("没写「成品落点」这一块",
     (CASE, "## 五、成品落点\n\n| 成品 | 落的是哪些条目 |\n|:---|:---|\n"
      "| `tests/demo/test_demo.py` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |\n", ""),
     (), 1, "没有「成品落点」这一块"),
    ("成品落点表有一行空栏",
     (CASE, "| `tests/demo/test_demo.py` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |",
      "| `tests/demo/test_demo.py` |  |"), (), 1, "「成品落点」表有一行有空栏"),
    ("成品还没落成，落点那块写「还没落成」",
     (CASE, "| 成品 | 落的是哪些条目 |\n|:---|:---|\n"
      "| `tests/demo/test_demo.py` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |",
      "还没落成。"), (), 0, "落成之后回来把表填上"),

    # 「执行器」「改动文件」两栏：取值写死，每条规程都要有。
    ("规程缺「执行器」栏",
     (PROC, "**执行器**：脚本。\n\n", ""), (), 1, "「执行器」栏写了 0 个"),
    ("规程缺「改动文件」栏",
     (PROC, "**改动文件**：只读。\n\n", ""), (), 1, "「改动文件」栏写了 0 个"),
    ("执行器写成第四个取值",
     (PROC, "**执行器**：脚本。", "**执行器**：人手。"), (), 1,
     "「执行器」栏的取值不在给定的几个里：人手"),
    ("改动文件写成别的说法",
     (PROC, "**改动文件**：只读。", "**改动文件**：看情况。"), (), 1,
     "「改动文件」栏的取值不在给定的几个里：看情况"),
    ("取值后面带一句括号说明也判过",
     (PROC, "**执行器**：脚本。", "**执行器**：脚本（跑命令，比退出码与盘上的文件）。"),
     (), 0, "机械项全过"),
    ("执行器栏写成两列表行也认",
     (PROC,
      """**唯一标识符**：TP-1

**英文名**：main_path

**目标**：把用例跑一遍。

**风险等级**：高。

**执行器**：脚本。

**改动文件**：只读。

**启动**：ENV-1 就位。

**有序执行测试用例**：1. TC-1

**与其他规程的关系**：无。

**停止与结束**：无。""",
      """| 唯一标识符 | TP-1 |
|:---|:---|
| 英文名 | main_path |
| 目标 | 把用例跑一遍。 |
| 风险等级 | 高 |
| 执行器 | 脚本 |
| 改动文件 | 只读 |
| 启动 | ENV-1 就位。 |
| 有序执行测试用例 | 1. TC-1 |
| 与其他规程的关系 | 无。 |
| 停止与结束 | 无。 |"""),
     (), 0, "机械项全过"),

    # 文末「各批落到哪」：无条件要写；表里要把全部规程列到。
    # 查找串用 BATCH_SCRIPT 而不是照抄一遍表：那张表加过一栏，抄第二份迟早对不上。
    ("没有「各批落到哪」这一块",
     (PROC, "\n## 各批落到哪\n\n" + BATCH_SCRIPT + "\n", ""),
     (), 1, "没有「各批落到哪」这一块"),
    ("那一块里没有表（标题写了、表没写）",
     (PROC, BATCH_SCRIPT, "（待补）"), (), 1, "「各批落到哪」里没有那张表"),
    ("表里把规程栏写成用例编号",
     (PROC, "| 脚本批 | TP-1 | 脚本 |", "| 脚本批 | TC-1 | 脚本 |"), (), 1,
     "这些规程没被「各批落到哪」那张表列到：TP-1"),
    ("表里列了一个不存在的规程",
     (PROC, "| 脚本批 | TP-1 | 脚本 |", "| 脚本批 | TP-9 | 脚本 |"), (), 1,
     "那张表里列了不存在的规程：TP-9"),

    # 「用例目录名」这一栏：落成评测用例的那几行要按执行顺序列全该规程用例的目录名。
    # 评测工具按目录名的字母序跑，名字排成什么顺序就跑成什么顺序——两段位次各两位，
    # 字母序才等于「先规程号、再规程内位次」。
    ("落成评测用例的行填了「用例目录名」，与执行顺序对得上",
     (PROC, BATCH_SCRIPT, BATCH_MODEL), (), 0, "与「有序执行测试用例」栏逐条对得上"),
    ("目录名少一段（没写英文名那段）",
     (PROC, BATCH_SCRIPT, BATCH_MODEL.replace("tp01-01-TC-1-verify_a", "tp01-01-TC-1")),
     (), 1, "不合形制"),
    ("目录名里规程号那段位数不够",
     (PROC, BATCH_SCRIPT, BATCH_MODEL.replace("tp01-01-", "tp1-01-")), (), 1, "不合形制"),
    ("位次与「有序执行测试用例」栏对不上",
     (PROC, BATCH_SCRIPT, BATCH_MODEL.replace("tp01-01-", "tp01-02-")), (), 1, "排第 1"),
    ("第一段的规程号不是本行「规程」栏那条",
     (PROC, BATCH_SCRIPT, BATCH_MODEL.replace("tp01-01-", "tp02-01-")),
     (), 1, "「规程」栏写的是 TP-1"),
    ("第三段的用例号没有定义处",
     (PROC, BATCH_SCRIPT, BATCH_MODEL.replace("TC-1-verify_a", "TC-9-verify_a")),
     (), 1, "目录名里的 TC-9"),
    ("第四段的英文名与用例表里那一栏不一致",
     (PROC, BATCH_SCRIPT, BATCH_MODEL.replace("TC-1-verify_a", "TC-1-verify_b")),
     (), 1, "英文名对不上"),
    ("落成评测用例的那一行整栏空着",
     (PROC, BATCH_SCRIPT, BATCH_MODEL.replace("| tp01-01-TC-1-verify_a |", "|  |")),
     (), 1, "「用例目录名」栏是空的"),

    # 第四块「覆盖率自检」：一行一门选定的技术，记 T、N、C 与完成准则要求。
    # 第 6 步自检的结论落在这一块，所以缺了报错。脚本核的是机械项——T 等于那一栏
    # 列出来的条数、N 等于这些编号在对应表里非空的条数、覆盖率栏的算式算得对、
    # 引的编号都有定义处。T 该是几（那要拿各技术的算式核模型）脚本核不了。
    ("覆盖率自检那一块整个不在",
     (CASE, "## 四、覆盖率自检", "## 四、别的块"), (), 1, "没有「覆盖率自检」这一块"),
    ("覆盖率自检的表少一栏",
     (CASE, "| 技术（档位） | 覆盖项编号 | 覆盖项总数 T | 已被用例覆盖 N | 覆盖率 N÷T | 完成准则要求 |",
      "| 技术（档位） | 覆盖项编号 | 覆盖项总数 T | 已被用例覆盖 N | 覆盖率 N÷T |"), (), 1, "没有那张表"),
    ("覆盖项编号栏引了清单里没有的号",
     (CASE, COVER_ROW, COVER_ROW.replace("TCOV-1～TCOV-2", "TCOV-1～TCOV-9")),
     (), 1, "没有定义处"),
    ("覆盖项编号栏写了个认不出的段",
     (CASE, COVER_ROW, COVER_ROW.replace("TCOV-1～TCOV-2", "TCOV-1-2")),
     (), 1, "认不出这几段"),
    ("T 与那一栏列出的条数对不上",
     (CASE, COVER_ROW, COVER_ROW.replace("| 2 | 2 | 2÷2＝100% |", "| 3 | 2 | 3÷3＝100% |")),
     (), 1, "「覆盖项总数 T」写的是 3，这一栏列了 2 条"),
    ("N 比 T 还大",
     (CASE, COVER_ROW, COVER_ROW.replace("| 2 | 2 | 2÷2＝100% |", "| 2 | 3 | 3÷2＝150% |")),
     (), 1, "「已被用例覆盖 N」写的是 3"),
    ("N 与对应表里非空的行数对不上",
     (CASE, COVER_ROW, COVER_ROW.replace("| 2 | 2 | 2÷2＝100% |", "| 2 | 1 | 1÷2＝50% |")),
     (), 1, "对应表里这些编号只有 2 条非空"),
    ("覆盖率栏算错了",
     (CASE, COVER_ROW, COVER_ROW.replace("2÷2＝100%", "2÷2＝80%")),
     (), 1, "按 2÷2 算应是 100%"),
    ("覆盖率栏形制不对（写成小数）",
     (CASE, COVER_ROW, COVER_ROW.replace("2÷2＝100%", "1.0")),
     (), 1, "照 N÷T＝xx.x% 写"),
    ("完成准则要求那一栏空着",
     (CASE, COVER_ROW, COVER_ROW.replace("| 100% |", "|  |")), (), 1, "有空栏"),
    ("清单里有覆盖项没进这一块：报提示，不报错",
     (CASE, COVER_ROW, "| 等价类划分 | TCOV-1 | 1 | 1 | 1÷1＝100% | 100% |"),
     (), 0, "没进「覆盖率自检」的任何一行"),
]


# 打目录名要英文名，基线的用例表没有这一栏；这一份手写的规程文本配下面那份名字表，
# 用来试「清单漏一条 / 同一条写两遍 / 一条规程一行 / 没有执行器栏」——基线只有一条
# 规程、一条用例，这几种在那边造不出来。
PROC_TEXT_TWO = """# 测试规程规格说明

## TP-1 主干

**唯一标识符**：TP-1

**有序执行测试用例**：TC-1、TC-2

## 各批落到哪

| 批次 | 规程 | 执行器 | 落到哪 | 用例目录名 | 说明 |
|:---|:---|:---|:---|:---|:---|
| 模型批 | TP-1 | 子代理 | `evals/demo/cases/` | tp01-01-TC-1-verify_a、tp01-02-TC-2-verify_b | 判据要读一轮模型的行为 |
"""

CASE_NAMES_TWO = {1: "verify_a", 2: "verify_b"}


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


def check_pipe_utf8():
    """输出被重定向到管道时按 UTF-8 吐字节，中文交到下一环手上不是「���」。

    上面那些例走的是重定向到 StringIO，验的是判得对不对，验不到「字节按什么编码
    落下来」。这条真的开一个子进程、接一根管道，验拿回来的那串字节。

    PYTHONIOENCODING 特意设成 gbk——本机管道上默认就是它；不设的话管道编码本来
    就是 UTF-8，这条在哪台机器上都验不到东西。
    """
    root = Path(tempfile.mkdtemp(prefix="check-docs-utf8-"))
    try:
        make(root, None, ())
        proc = subprocess.run(
            [sys.executable, os.path.abspath(check_docs.__file__), str(root)],
            capture_output=True, env=dict(os.environ, PYTHONIOENCODING="gbk"))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if proc.returncode != 0:
        return ["退出码 %s，期望 0" % proc.returncode]
    try:
        text = proc.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        return ["吐出来的字节按 UTF-8 解不开：%s" % exc]
    if "检查目录：" not in text:
        return ["按 UTF-8 解出来的文本里找不到中文提示，实际开头是：%r" % text[:60]]
    return []


def check_field_values_forms():
    """「执行器」的两种写法都收：加粗字段、两列表行。

    上面那些例走的都是加粗字段。示例文档用的是两列表行（「| 执行器 | 脚本 |」），
    那种写法不认的话，照示例写的产出会被判成「一栏都没有」。

    field_values 还没写时返回一条毛病而不是抛 AttributeError——这条是「另起
    一条」，抛出去会把整个脚本打断，前面那些例的结论也跟着看不到。
    """
    if not hasattr(check_docs, "field_values"):
        return ["check_docs 里还没有 field_values()"]
    bold = "**执行器**：脚本。\n"
    row = ("| 唯一标识符 | TP-1 |\n|:---|:---|\n"
           "| 英文名 | main_path |\n| 执行器 | 控制器（照分流规则跑） |\n")
    problems = []
    got_bold = check_docs.field_values(bold, "执行器")
    if got_bold != ["脚本。"]:
        problems.append("加粗字段那种写法收成了 %r" % (got_bold,))
    got_row = check_docs.field_values(row, "执行器")
    if got_row != ["控制器（照分流规则跑）"]:
        problems.append("两列表行那种写法收成了 %r" % (got_row,))
    return problems


def check_batches_missing_tp():
    """两条规程、表里只列了一条：要把漏的那条点名报出来。

    上面那些例的基线只有一条规程，「漏一条」在那边造不出来，所以单起一条：
    不铺一整套产出，直接把一段规程文档喂给 check_batches，接住它打印的话。

    check_batches 还没写时返回一条毛病而不是抛 AttributeError——这条是「另起
    一条」，抛出去会把整个脚本打断，前面那些例的结论也跟着看不到。
    """
    if not hasattr(check_docs, "check_batches"):
        return ["check_docs 里还没有 check_batches()"]
    text = ("# 测试规程规格说明\n\n"
            "## TP-1 主干\n\n**唯一标识符**：TP-1\n\n**英文名**：main_path\n\n"
            "**执行器**：脚本。\n\n**改动文件**：只读。\n\n**有序执行测试用例**：1. TC-1\n\n"
            "## TP-2 收尾\n\n**唯一标识符**：TP-2\n\n**英文名**：tail\n\n"
            "**执行器**：脚本。\n\n**改动文件**：只读。\n\n**有序执行测试用例**：1. TC-1\n\n"
            "## 各批落到哪\n\n"
            "| 批次 | 规程 | 执行器 | 落到哪 | 说明 |\n|:---|:---|:---|:---|:---|\n"
            "| 脚本批 | TP-1 | 脚本 | `tests/demo/test_demo.py` | 判据落在命令上 |\n")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        check_docs.check_batches(text, check_docs.Report(), {1, 2},
                                 check_docs.proc_cases(text)[0], {})
    out = buf.getvalue()
    if "TP-2" not in out:
        return ["两条规程、表里只列了 TP-1，没报出漏掉的 TP-2；实际输出：%r" % out]
    return []


def check_case_dirs_list():
    """清单漏一条、同一条写两遍、一条规程一行、没有「执行器」栏：四种都要合规矩。

    上面那些例的基线只有一条规程、一条用例，这几种在那边造不出来，所以单起一条：
    直接把一段规程文本喂给 check_batches，接住它打印的话。

    check_batches 还没写时返回一条毛病而不是抛 AttributeError——这条是「另起
    一条」，抛出去会把整个脚本打断，前面那些例的结论也跟着看不到。
    """
    if not hasattr(check_docs, "check_batches"):
        return ["check_docs 里还没有 check_batches()"]
    # 表里没有「执行器」栏的那一版：判不出哪几行是评测批，整块跳过、不报错。
    # 「规程」栏跟着列全两条规程，好让 check_batches 自己那部分不报错——这一条
    # 单独看的就是「跳过时一处错也不报」，不是「报了个假错」。
    no_executor = (PROC_TEXT_TWO
                   .replace("| 批次 | 规程 | 执行器 | 落到哪 |",
                            "| 批次 | 规程 | 落到哪 |")
                   .replace("|:---|:---|:---|:---|:---|:---|",
                            "|:---|:---|:---|:---|:---|")
                   .replace("| 模型批 | TP-1 | 子代理 |", "| 模型批 | TP-1、TP-2 |"))
    order, _, _ = check_docs.proc_cases(PROC_TEXT_TWO)
    # 每一例：说明、喂进去的规程文本、喂给 check_batches 的规程集合、期望的报错处数、
    # 输出里该出现的话（没有就空串）。规程集合逐例给：表里只列 TP-1 的，就传 {1}，
    # 不然 check_batches 自己那条「漏列了 TP-2」会先报一处，把这一例的期望带偏。
    variants = [
        ("对得上时不该报错", PROC_TEXT_TWO, {1}, 0, ""),
        ("清单漏一条",
         PROC_TEXT_TWO.replace("tp01-01-TC-1-verify_a、tp01-02-TC-2-verify_b",
                               "tp01-01-TC-1-verify_a"),
         {1}, 1, "目录名清单里少"),
        ("清单里同一条写了两遍",
         PROC_TEXT_TWO.replace(
             "tp01-01-TC-1-verify_a、tp01-02-TC-2-verify_b",
             "tp01-01-TC-1-verify_a、tp01-02-TC-2-verify_b、tp01-02-TC-2-verify_b"),
         {1}, 1, "重复了"),
        ("一条规程一行：一格里写了两条规程",
         PROC_TEXT_TWO.replace("| 模型批 | TP-1 |", "| 模型批 | TP-1、TP-2 |"),
         {1, 2}, 1, "一条规程一行"),
        ("表里没有「执行器」栏：判不出哪几行是评测批，整块跳过，一处错也不报",
         no_executor, {1, 2}, 0, ""),
        # 跳过是可以的（不猜哪几行是评测批），但不能一声不吭：末尾照打「机械项全过」，
        # 读的人会以为「用例目录名」这一栏查过了。这两条钉的就是「跳过时留一句话」。
        ("表里没有「执行器」栏：跳过，但要说一声这一栏这次没查",
         no_executor, {1, 2}, 0, "没有「执行器」栏"),
        ("「执行器」那一格的取值不在给定的几个里：这一行查不了，要说一声",
         PROC_TEXT_TWO.replace("| 模型批 | TP-1 | 子代理 |", "| 模型批 | TP-1 | 自代理 |"),
         {1}, 0, "自代理"),
    ]
    problems = []
    for title, text, tps, want_errors, want in variants:
        rep = check_docs.Report()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            check_docs.check_batches(text, rep, tps, order, CASE_NAMES_TWO)
        out = buf.getvalue()
        if rep.errors != want_errors:
            problems.append("%s：报了 %d 处错，期望 %d 处；实际输出：%r"
                            % (title, rep.errors, want_errors, out))
        elif want and want not in out:
            problems.append("%s：输出里没有「%s」；实际输出：%r" % (title, want, out))
    return problems


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

    # 另起一条：上面那些都走 StringIO，编码不在这条路上
    print()
    title = "输出被重定向到管道时按 UTF-8 吐字节（把本机管道默认的 GBK 也设上了）"
    problems = check_pipe_utf8()
    if problems:
        bad += 1
        print("[失败] %s" % title)
        for p in problems:
            print("       %s" % p)
    else:
        print("[通过] %s" % title)

    print()
    title = "「执行器」的两种写法都收：加粗字段、两列表行"
    problems = check_field_values_forms()
    if problems:
        bad += 1
        print("[失败] %s" % title)
        for p in problems:
            print("       %s" % p)
    else:
        print("[通过] %s" % title)

    print()
    title = "两条规程、表里只列了一条：漏的那条要点名报出来"
    problems = check_batches_missing_tp()
    if problems:
        bad += 1
        print("[失败] %s" % title)
        for p in problems:
            print("       %s" % p)
    else:
        print("[通过] %s" % title)

    print()
    title = "目录名清单：漏一条、重复、一条规程一行、没有「执行器」栏，四种都合规矩"
    problems = check_case_dirs_list()
    if problems:
        bad += 1
        print("[失败] %s" % title)
        for p in problems:
            print("       %s" % p)
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
