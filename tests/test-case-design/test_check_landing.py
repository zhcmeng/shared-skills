#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_landing.py 自己的测试。

    python tests/test-case-design/test_check_landing.py

先造一套最小但合规的产出与成品，确认它判过；再一处一处地改坏，确认每一处都被逮住。
这份脚本管的是「产出里的编号与成品里的编号对不对得上」，它判错了比不判更糟——
放过去一处，成品与文档就此各说各的，拿编号再也搜不过去。
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
import check_landing  # noqa: E402

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

| 依据的出处 | 模型编号 | 说明 |
|:---|:---|:---|
| 需求 1 | TM-1 | 全部 |
"""

CASE_TEXT = """# 测试用例规格说明

## 一、测试覆盖项

| 唯一标识符 | 英文名 | 描述 | 风险等级 | 可追溯性 |
|:---|:---|:---|:---|:---|
| TCOV-1 | valid_class_a | 有效等价类：甲 | 高 | TM-1 |

## 二、测试用例

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|:---|
| TC-1 | verify_a | 验证甲 | 高 | 按 DATA-1 取一段文本 | 输出甲 |

## 三、覆盖项 ↔ 用例对应表

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 有效等价类：甲 | TC-1 |
"""

PROC_TEXT = """# 测试规程规格说明

## TP-1 主干

**唯一标识符**：TP-1

**英文名**：main_path

**目标**：把用例跑一遍。

**风险等级**：高。

**启动**：ENV-1 就位。

**有序执行测试用例**：1. TC-1

**与其他规程的关系**：无。

**停止与结束**：无。
"""

DATA_TEXT = """# 测试数据需求

| 唯一标识符 | 英文名 | 描述 | 重置需求 |
|:---|:---|:---|:---|
| DATA-1 | demo_text | 一段文本，正文见实施方案规格说明 1.2 第 5 小节 | 不需要 |
"""

ENV_TEXT = """# 测试环境需求

| 唯一标识符 | 英文名 | 测试环境项 | 描述 |
|:---|:---|:---|:---|
| ENV-1 | interpreter | 解释器 | Python 3 |
"""

DECISION_TEXT = """# 决策依据

| 唯一标识符 | 在哪一步 | 决定 | 考虑过的其他做法 | 依据 | 依据的来源 |
|:---|:---|:---|:---|:---|:---|
| DEC-1 | 第 1 步 | 只选等价类划分一门 | 判定表测试；分叉少，建不出有意义的表 | 测试项只有一处取值分歧 | 从测试项推的 |
"""

BASE = {
    MODEL: MODEL_TEXT,
    CASE: CASE_TEXT,
    PROC: PROC_TEXT,
    DATA: DATA_TEXT,
    ENV: ENV_TEXT,
    DECISION: DECISION_TEXT,
}

# 第七份（实施方案规格说明）按需产出，不在 DOCS 里。它的对账表按契约要求把通用稿里
# 定义过的每一条编号都列出来一次（六类都收）——于是它跟那六份一样，是个「什么编号
# 都有」的文本。它一般也在产出目录里（落成之后就有），所以 make() 也把它写进去，
# 「产出目录不算成品」那份名单里同样得算上它。
# 末尾那一块「成品落点」是取成品路径的地方（模板第十节）；{ART} 由 make() 换成临时
# 成品路径——与六份通用稿一样走那一次替换，make() 不用为它单开一路。
IMPL_TEXT = """# 实施方案规格说明

这一份把同目录那六份通用稿落成 skill-up 这一套里能跑的东西。

## 一、方案：skill-up

### 1.1 通用稿的编号落到哪

| 通用稿的编号 | 本方案里落在哪 | 说明 |
|:---|:---|:---|
| TM-1；TCOV-1；TC-1；TP-1 | `tests/demo/test_demo.py` 那一份测试代码 | 这一批判据落在盘上的文件上，整批落在一处 |
| ENV-1 | `eval.yaml` 里装技能那一段 | 装技能那一条 |
| DATA-1 | `cases/tp01-01-TC-1-verify_a.yaml` 的提示词 | 那段文本 |

### 1.2 说明

一条用例一轮，判据交给判官。

**1. 跑几次**

一条用例一轮。

**2. 工作区怎么来**

一条一个新建的空目录。

**3. 判据怎么落**

判据交给判官，那处折扣见第 4 小节第 1 条。

**4. 消息怎么渲染**

**第 1 条：技能怎么被唤起。**消息里的技能名渲染成短名。

**第 2 条：样本路径。**按工作区里的相对路径原样给。

**5. 跑不了原样的那几条**

无。

### 1.3 怎么跑、报告落在哪

```bash
skill-up run eval.yaml
```

### 1.4 成品落点

| 成品 | 落的是哪些条目 |
|:---|:---|
| `{ART}` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |
"""

# 最小的一份成品：六类编号各出现一次，另带一处引第七份小节号的地方。名字写成真测试
# 的样子，看它认不认得住
ART_TEXT = """# -*- coding: utf-8 -*-
\"\"\"假的成品：编号照抄进来的样子。\"\"\"


def test_TC_1_verify_a():
    \"\"\"TCOV-1：TM-1 里的有效等价类。跑 TP-1 那条规程，按 DATA-1 取文本，ENV-1 就位。
    摆法见 1.2 第 4 小节第 2 条。\"\"\"
"""

# 每一例：说明、改产出哪儿（文件名, 把什么, 换成什么）、改成品哪儿（把什么, 换成什么）、
# 期望退出码、输出里该出现的话（以 ! 开头表示「不该出现」）
CASES = [
    ("基线：六类编号在成品里都找得到", None, None, 0, "编号在两边对得上"),
    ("成品里漏了模型编号 TM-1", None, ("TM-1 里的", "模型里的"), 1, "测试模型：这些条目定义了"),
    ("成品里漏了覆盖项编号 TCOV-1", None, ("\"\"\"TCOV-1：", "\"\"\""), 1, "测试覆盖项：这些条目定义了"),
    ("判为不可行的覆盖项：成品里一处也不出现，也不算漏——它没有用例，本来就不落",
     [(CASE, "| TCOV-1 | valid_class_a | 有效等价类：甲 | 高 | TM-1 |",
       "| TCOV-1 | valid_class_a | 有效等价类：甲 | 高 | TM-1 |\n"
       "| TCOV-2 | valid_class_b | 有效等价类：乙 | 高 | TM-1 |"),
      (CASE, "| TCOV-1 | 有效等价类：甲 | TC-1 |",
       "| TCOV-1 | 有效等价类：甲 | TC-1 |\n"
       "| TCOV-2 | 有效等价类：乙 | 不可行，未导出用例 |")],
     None, 0, "判为不可行的覆盖项 1 条"),
    ("成品里漏了数据项编号 DATA-1", None, ("按 DATA-1 取", "按那段文本取"), 1, "测试数据项：这些条目定义了"),
    ("成品里漏了环境项编号 ENV-1", None, ("ENV-1 就位", "环境就位"), 1, "测试环境项：这些条目定义了"),
    ("成品里漏了规程编号 TP-1", None, ("跑 TP-1 那条规程", "跑那条规程"), 1, "测试规程：这些条目定义了"),
    ("编号写成短横也算数：代码里两种写法是一个意思",
     None, ("按 DATA-1 取", "按 DATA-1 取，见 TC-1"), 0, "编号在两边对得上"),
    ("编号补了零：`TC_01` 不算 `TC-1`——补了零，照编号就搜不到它",
     None, ("test_TC_1_verify_a", "test_TC_01_verify_a"), 1, "测试用例：这些条目定义了，成品里一处也没出现：TC-1"),
    ("编号后面接数字不算数：`TC_15` 里没有 `TC-1`",
     None, ("test_TC_1_verify_a", "test_TC_15_verify_a"), 1, "一处也没出现：TC-1"),
    ("成品里出现了产出里没有的用例编号",
     None, ("def test_TC_1_verify_a", "def test_TC_9_verify_a"), 1,
     "成品里出现了产出里没有定义处的编号：TC-9"),
    ("成品里写了某条决策的编号——产出里有定义，配对（决策只在成品与产出有出入时写，所以不正向要求）",
     None, ("\"\"\"TCOV-1：", "\"\"\"DEC-1：TCOV-1："), 0, "编号在两边对得上"),
    ("成品里写了一条产出里没有的决策编号",
     None, ("\"\"\"TCOV-1：", "\"\"\"DEC-9：TCOV-1："), 1,
     "成品里出现了产出里没有定义处的编号：DEC-9"),
    ("成品里一处编号都没有——该报的都报出来，不是只报一类",
     None, (ART_TEXT, "def test_verify_a():\n    pass\n"), 1, "测试用例：这些条目定义了"),

    # 引第七份（实施方案规格说明）小节号：第七份一重编小节号，这些引用就整片指错地方，
    # 而指错了不报的话，读的人照着号翻过去，翻到的是另一条。
    ("引的第七份小节号都指得到：成品一处、产出文档一处、第七份自己一处",
     None, None, 0, "引的第七份小节号，3 处都指得到"),
    ("引的第七份小节号指不到：小节号写错了",
     None, ("1.2 第 4 小节第 2 条", "1.2 第 9 小节"), 1,
     "成品：引的第七份小节号 `1.2 第 9 小节` 指不到——1.2 底下只有第 1 至第 5 小节"),
    ("引的第七份小节号指不到：条号写错了",
     None, ("1.2 第 4 小节第 2 条", "1.2 第 4 小节第 9 条"), 1,
     "成品：引的第七份小节号 `1.2 第 4 小节第 9 条` 指不到——"
     "1.2 第 4 小节（消息怎么渲染）底下只有第 1 至第 2 条"),
    ("引的第七份小节号指不到：整节都没有",
     None, ("1.2 第 4 小节第 2 条", "1.9 第 1 小节"), 1,
     "成品：引的第七份小节号 `1.9 第 1 小节` 指不到——第七份里没有 1.9 这一节"),
    ("产出文档里引的第七份小节号也查，报出来时带上文件名",
     (DATA, "实施方案规格说明 1.2 第 5 小节", "实施方案规格说明 1.2 第 8 小节"), None, 1,
     "Test Data Requirements.md：引的第七份小节号 `1.2 第 8 小节` 指不到"),
    ("第七份自己里面不带节号那种写法也查：认它落在哪个 ### 底下",
     (check_docs.IMPL_DOC, "见第 4 小节第 1 条", "见第 4 小节第 9 条"), None, 1,
     "Implementation Specification.md：引的第七份小节号 `第 4 小节第 9 条` 指不到——"
     "1.2 第 4 小节（消息怎么渲染）底下只有第 1 至第 2 条"),

    # 命令行上给了路径时，文档那边坏不坏都不影响这一遍：路径不从文档取，
    # 分批降级也只看文档里有没有那句话
    ("命令行给了路径时，第七份里那一块坏了也照跑",
     (check_docs.IMPL_DOC, "### 1.4 成品落点", "### 1.4 收尾"), None, 0, "编号在两边对得上"),
]


def run_landing(root, paths):
    """跑一遍 check_landing，返回（退出码, 输出）。"""
    buf = io.StringIO()
    old = sys.argv
    sys.argv = ["check_landing.py", str(root)] + [str(p) for p in paths]
    try:
        with contextlib.redirect_stdout(buf):
            code = check_landing.main()
    finally:
        sys.argv = old
    return code, buf.getvalue()


def make(root, tweak, art_tweak):
    """造一套产出与一份成品，返回成品路径。

    产出里带第七份——落成之后它就在，引小节号那一条检查要它才跑得起来。
    """
    art = root / "假成品.py"
    art.write_text(ART_TEXT, encoding="utf-8")
    docs = dict(BASE)
    docs[check_docs.IMPL_DOC] = IMPL_TEXT
    if tweak:
        # 一例要改两处时就传一列三元组；只改一处仍传那一个三元组本身
        for name, old, new in ([tweak] if isinstance(tweak, tuple) else tweak):
            if old not in docs[name]:
                raise AssertionError("测试自己写错了：%s 里找不到要替换的那段" % name)
            docs[name] = docs[name].replace(old, new)
    for name, text in docs.items():
        (root / name).write_text(text.replace("{ART}", art.as_posix()), encoding="utf-8")
    art.write_text((ART_TEXT.replace(*art_tweak) if art_tweak else ART_TEXT), encoding="utf-8")
    return art


def one(title, tweak, art_tweak, want_code, want_text):
    """跑一例，返回哪儿不对（对上了就是空表）。"""
    root = Path(tempfile.mkdtemp(prefix="check-landing-"))
    try:
        art = make(root, tweak, art_tweak)
        code, out = run_landing(root, [art])
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
    return problems, out


def check_from_place_table():
    """命令行上不给成品路径时，从第七份方案节末尾的「成品落点」表里取。

    这条走的是另一条入口：表里的路径能不能被认出来、能不能照着读成品。那一块原先住
    在用例那份里，搬进第七份之后这份脚本也跟着换数据源——取错了文档，路径一处也读
    不到，而报出来的是「成品一份都没读到」，指不到病根。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-place-"))
    try:
        art = make(root, None, None)
        code, out = run_landing(root, [])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 0:
        return ["退出码 %s，期望 0；输出：%s" % (code, out.strip()[:200])]
    if "编号在两边对得上" not in out:
        return ["输出里没有「编号在两边对得上」：%s" % out.strip()[:200]]
    return []


def check_not_yet():
    """落点表上写着「还没落成」，命令行上也没给路径——说清楚，别当成「对得上」。

    退出码是 3，与 2 分开：2 管的是「用法不对、读不到东西」，那是调用方自己用错了；
    「还没落成」是产出的正常状态，只是没有可对照的成品。两件事挤在同一个码上时，
    调用方分不出是自己用错了还是这批本来就没落成，只能去读脚本才知道——所以分开。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-notyet-"))
    try:
        make(root, (check_docs.IMPL_DOC, "| 成品 | 落的是哪些条目 |\n|:---|:---|\n"
                          "| `{ART}` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |",
                    "还没落成。"), None)
        code, out = run_landing(root, [])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 3:
        return ["退出码 %s，期望 3" % code]
    if "还没落成" not in out:
        return ["输出里没提「还没落成」：%s" % out.strip()[:200]]
    return []


def check_not_yet_in_cell():
    """「还没落成」被写进「成品」栏了——照样按「还没落成」报，别拿它当路径去读。

    模板说这四个字是那一块里的一句话、不占格子，check_docs 也会拦这一种；但这一份
    脚本单跑时也得说得出话：当成路径去读只会得到一句「成品一份都没读到」，那句话
    指不到病根，写的人只能去翻脚本才知道错在哪儿——正是要避免的那一步。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-cell-"))
    try:
        make(root, (check_docs.IMPL_DOC,
                    "| `{ART}` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |",
                    "| 还没落成 | —— |"), None)
        code, out = run_landing(root, [])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 3:
        return ["退出码 %s，期望 3；输出：%s" % (code, out.strip()[:200])]
    if "还没落成" not in out:
        return ["输出里没提「还没落成」：%s" % out.strip()[:200]]
    return []


def check_paths_missing():
    """命令行上给的成品路径读不到——报出来，别当成「成品里没有那些号」。

    一份也读不到时退出码是 2（这次没得可查），不是 1（产出没错）。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-miss-"))
    try:
        make(root, None, None)
        code, out = run_landing(root, [root / "没有这份.py"])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 2:
        return ["退出码 %s，期望 2" % code]
    for want in ("读不到：", "成品一份都没读到"):
        if want not in out:
            return ["输出里没有「%s」：%s" % (want, out.strip()[:200])]
    return []


def check_root_missing():
    """产出目录读不到——退出码 2，不是 1（这是用法不对，不是产出有错）。"""
    code, out = run_landing(Path("没有这个目录-9f3a"), [])
    if code != 2:
        return ["退出码 %s，期望 2" % code]
    if "读不到产出目录" not in out:
        return ["输出里没有「读不到产出目录」：%s" % out.strip()[:200]]
    return []


def check_binary_skipped():
    """成品目录里那份不是 UTF-8 的样本文件：跳过、说一声，不因此判错。

    样本文件是测试数据，编号不会写在它的字节里；读不动就报错的话，谁都得在
    命令上把样本一份份挑出去——挑漏一份就红一次。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-bin-"))
    try:
        make(root, None, None)
        samples = root / "样本"
        samples.mkdir()
        (samples / "非UTF8样本.md").write_bytes("中文测试".encode("gbk"))
        code, out = run_landing(root, [root / "假成品.py", samples])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 0:
        return ["退出码 %s，期望 0；输出：%s" % (code, out.strip()[:300])]
    if "这些文件没读" not in out or "非UTF8样本.md" not in out:
        return ["输出里没提跳过的那份文件：%s" % out.strip()[:300]]
    return []


def check_root_not_counted():
    """把产出目录整个当成品路径传进来：那六份文档不算成品。

    不给这一条，传错路径时六份文档里什么编号都有，检查会报「全过」——那种全过
    比报错还会骗人。这里把假成品挪走，只留六份文档，传的就是产出目录自己。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-self-"))
    try:
        art = make(root, None, None)
        art.unlink()
        code, out = run_landing(root, [root])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 2:
        return ["退出码 %s，期望 2" % code]
    for want in ("产出目录里那几份文档没算成品", "成品一份都没读到"):
        if want not in out:
            return ["输出里没有「%s」：%s" % (want, out.strip()[:300])]
    return []


def check_impl_not_counted():
    """产出目录里那份第七份也不算成品——它对账表里什么编号都有。

    第七份的契约要求「通用稿里定义过的每一条 ENV-…／DATA-… 都要在对账表里出现
    一次」，所以它跟那六份一样，是个「什么编号都有」的文本。不排掉的话，把产出目录
    当成品路径传进来，它会把那几类编号全顶过去，报出「对得上」——那种全过比报错还会
    骗人，而且正是这段防线写出来要挡的那种用法（按契约，成品就摆在产出目录的上一级，
    传评测材料根是常事）。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-impl-"))
    try:
        art = make(root, None, None)
        art.unlink()
        code, out = run_landing(root, [root])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 2:
        return ["退出码 %s，期望 2" % code]
    for want in ("产出目录里那几份文档没算成品", "成品一份都没读到"):
        if want not in out:
            return ["输出里没有「%s」：%s" % (want, out.strip()[:300])]
    return []


def check_impl_missing():
    """产出目录里没有第七份，成品却引了它的小节号——报出来，别当成「指得到」。

    第七份是按需产出的，这批没写就真的不在盘上。那时成品里那句「见 1.2 第 4 小节」
    谁也翻不过去，读的人只会以为漏看了哪一份文档。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-noimpl-"))
    try:
        art = make(root, None, None)
        (root / check_docs.IMPL_DOC).unlink()
        code, out = run_landing(root, [art])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 1:
        return ["退出码 %s，期望 1；输出：%s" % (code, out.strip()[:300])]
    for want in ("成品：引的第七份小节号 `1.2 第 4 小节第 2 条` 指不到",
                 "产出目录里没有第七份"):
        if want not in out:
            return ["输出里没有「%s」：%s" % (want, out.strip()[:300])]
    return []


def check_no_impl_doc():
    """产出里没有第七份、命令行上也没给路径——退 3，不是报错。

    第七份按需产出：没答「要一并出实施测评方案」的批就没有它，也就没有落成可言。
    「第七份不在」与「那一块写着还没落成」对下游是同一件事，所以共用一个退出码；
    报成 2（用法不对）的话，调用方会当成自己用错了。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-noimpl-place-"))
    try:
        make(root, None, None)
        (root / check_docs.IMPL_DOC).unlink()
        code, out = run_landing(root, [])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 3:
        return ["退出码 %s，期望 3；输出：%s" % (code, out.strip()[:300])]
    if "没有实施方案规格说明" not in out:
        return ["输出里没点出「没有实施方案规格说明」：%s" % out.strip()[:300]]
    return []


def check_note_not_not_yet():
    """那一块里以「注：」起头的说明行提到「还没落成」，不算这一批还没落成。

    范本《文档示例.md》那一块底下正有这么一条注，讲的就是这四个字怎么写。照它判，
    一批压根没落成的产出会被读成「落了一部分」：正向那几条全降成提示、退 0，还报一句
    「编号在两边对得上」——正是这套检查要防的那种假绿灯。范本开头交代过「文中凡以
    「注：」起头的行，都是本文加的说明，不是文档内容」，脚本按同一条读。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-note-"))
    try:
        art = make(root, (check_docs.IMPL_DOC,
                          "| `{ART}` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |",
                          "| `{ART}` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |\n\n"
                          "注：成品还没落成就写「还没落成」——写成这一块里的一句话。"),
                   ("TCOV-1：TM-1 里的有效等价类。跑 TP-1 那条规程，按 DATA-1 取文本，ENV-1 就位。",
                    "TCOV-1：有效等价类。"))
        code, out = run_landing(root, [])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 1:
        return ["退出码 %s，期望 1——注里那几个字不该把这一批读成「落了一部分」；"
                "输出：%s" % (code, out.strip()[:300])]
    if "还写着「%s」" % check_docs.NOT_YET in out:
        return ["按「落了一部分」查了，可这一批一处也没落成：%s" % out.strip()[:300]]
    return []


def check_two_sections_merged():
    """两个方案节：一节那一格写坏了，另一节列着的成品路径照旧要收进来。

    模板第十节说「成品」那一格写的是成品路径；「还没落成」写进格子是文档错，check_docs
    报它。可写坏一节不该把整批丢掉：各节的成品路径要合起来（设计稿 D16）。丢掉的表现
    是退 3，调用方当成「这一批还没落成」跳过——一批真有成品的产出就这么没了对账。
    """
    two = IMPL_TEXT.replace(
        "| `{ART}` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |",
        "| 还没落成 | —— |") + """
## 二、方案：另一套

### 2.1 通用稿的编号落到哪

| 通用稿的编号 | 本方案里落在哪 | 说明 |
|:---|:---|:---|
| TM-1；TCOV-1；TC-1；TP-1 | `tests/demo/test_demo.py` 那一份测试代码 | 整批落在一处 |
| ENV-1 | `eval.yaml` 里装技能那一段 | 装技能那一条 |
| DATA-1 | `cases/tp01-01-TC-1-verify_a.yaml` 的提示词 | 那段文本 |

### 2.2 说明

另一套的说明。

### 2.3 怎么跑、报告落在哪

另一套的跑法。

### 2.4 成品落点

| 成品 | 落的是哪些条目 |
|:---|:---|
| `{ART}` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |
"""
    root = Path(tempfile.mkdtemp(prefix="check-landing-twosect-"))
    try:
        art = make(root, (check_docs.IMPL_DOC, IMPL_TEXT, two), None)
        code, out = run_landing(root, [])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 0:
        return ["退出码 %s，期望 0——第二节列着成品路径，不该整批跳过；输出：%s"
                % (code, out.strip()[:300])]
    if "编号在两边对得上" not in out:
        return ["输出里没有「编号在两边对得上」：%s" % out.strip()[:300]]
    return []


def check_place_block_missing():
    """第七份在、可那一块没写——退 2：路径本来该从那儿取，取不到是该补的东西缺了。

    与上一条分开：3 是「本来就没得对」，2 是「该有的缺了一块」。混成一个码，调用方
    就分不出「这批还没落成」与「第七份少写一块」。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-noblock-"))
    try:
        make(root, (check_docs.IMPL_DOC, "### 1.4 成品落点", "### 1.4 收尾"), None)
        code, out = run_landing(root, [])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 2:
        return ["退出码 %s，期望 2；输出：%s" % (code, out.strip()[:300])]
    if "没有「%s」这一块" % check_docs.PLACE_HEAD not in out:
        return ["输出里没提那一块没写：%s" % out.strip()[:300]]
    return []


def check_pipe_utf8():
    """输出被重定向到管道时按 UTF-8 吐字节，中文交到下一环手上不是「���」。

    上面那些例走的是重定向到 StringIO，验的是判得对不对，验不到「字节按什么编码
    落下来」。这条真的开一个子进程、接一根管道，验拿回来的那串字节。

    PYTHONIOENCODING 特意设成 gbk——本机管道上默认就是它；不设的话管道编码本来
    就是 UTF-8，这条在哪台机器上都验不到东西。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-utf8-"))
    try:
        art = make(root, None, None)
        proc = subprocess.run(
            [sys.executable, os.path.abspath(check_landing.__file__), str(root), str(art)],
            capture_output=True, env=dict(os.environ, PYTHONIOENCODING="gbk"))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if proc.returncode != 0:
        return ["退出码 %s，期望 0" % proc.returncode]
    try:
        text = proc.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        return ["吐出来的字节按 UTF-8 解不开：%s" % exc]
    if "产出目录：" not in text:
        return ["按 UTF-8 解出来的文本里找不到中文提示，实际开头是：%r" % text[:60]]
    return []


def check_partial_landing():
    """分几批落成：表里列了已落成的、那句话交代还没落的——照查，正向漏号降成提示。

    模板第四节允许这两种写法并存。要防的是「逼人一次填全」：还没落的那几处本来就查
    不到，报成错的话，分批落成就等于每批都得把表编全；降成提示，落一批查一批，已经
    落成的那一处真漏了照样看得见——同一套产出，把那句话拿掉就该照旧报错。
    """
    # 成品里只留 TC-1 与 TCOV-1，其余四类一处不出现——正是「还没落成」要解释的缺口
    drop = ("TCOV-1：TM-1 里的有效等价类。跑 TP-1 那条规程，按 DATA-1 取文本，ENV-1 就位。",
            "TCOV-1：有效等价类。")
    table = ("| 成品 | 落的是哪些条目 |\n|:---|:---|\n| `{ART}` | TC-1 |")

    def run(block, with_path=False):
        root = Path(tempfile.mkdtemp(prefix="check-landing-partial-"))
        try:
            art = make(root, (check_docs.IMPL_DOC, "| 成品 | 落的是哪些条目 |\n|:---|:---|\n"
                                     "| `{ART}` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |",
                                     block), drop)
            return run_landing(root, [art] if with_path else [])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    problems = []
    code, out = run(table + "\n\nTM-1、TP-1、DATA-1、ENV-1 那几处还没落成。")
    if code != 0:
        problems.append("写着「还没落成」时退出码 %s，期望 0；输出：%s"
                        % (code, out.strip()[:300]))
    for want in ("还写着「还没落成」", "只算提示"):
        if want not in out:
            problems.append("输出里没有「%s」：%s" % (want, out.strip()[:300]))

    # 命令行上把成品路径一条条点出来，也得走同一条降级。模板要求这样做——成品写在
    # 上一层目录时（而上一层住着报告目录、虚拟环境、缓存），别把整个上一层指过去，
    # 那条命令上一条条点出来；那正是分批落成时的常规写法。早先这条路把降级整个绕掉
    # 了：`partial` 只在「命令行没给路径」时才从产出里读，于是照模板写的那条命令反而
    # 把还没落成的那几处按错报，返回来逼人一次把表填全——正是这套降级要避免的。
    code, out = run(table + "\n\nTM-1、TP-1、DATA-1、ENV-1 那几处还没落成。", with_path=True)
    if code != 0:
        problems.append("命令行上点了成品路径时退出码 %s，期望 0；输出：%s"
                        % (code, out.strip()[:300]))
    for want in ("还写着「还没落成」", "只算提示"):
        if want not in out:
            problems.append("命令行上点了成品路径时，输出里没有「%s」：%s"
                            % (want, out.strip()[:300]))

    code, out = run(table)
    if code != 1:
        problems.append("没写「还没落成」时退出码 %s，期望 1——漏了就是漏了；输出：%s"
                        % (code, out.strip()[:300]))
    return problems


def check_dot_dirs_skipped():
    """名字以 `.` 开头的目录不往下走：上一层住着 .git、虚拟环境、缓存，都不是成品。

    模板第十节让人把成品写到上一层、命令上再一条条点出来（避不开那层里别的东西时）；
    这一条是兜底——真把上一层点给脚本时，那些目录不该被读进来。读得慢是小事，读进一堆
    环境自带的编号才是真麻烦：一个 .venv 里什么号都能撞上。
    """
    root = Path(tempfile.mkdtemp(prefix="check-landing-dot-"))
    try:
        make(root, None, None)
        top = root / "上一层"
        top.mkdir()
        (top / "成品.py").write_text(ART_TEXT, encoding="utf-8")
        hidden = top / ".venv"
        hidden.mkdir()
        (hidden / "junk.py").write_text(
            "# TM-9、TCOV-9、TC-9、TP-9、DATA-9、ENV-9 都是成品里没有的号\n", encoding="utf-8")
        code, out = run_landing(root, [top])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    problems = []
    if code != 0:
        problems.append("退出码 %s，期望 0；输出：%s" % (code, out.strip()[:300]))
    if "TM-9" in out:
        problems.append("点开头的目录被读进去了：%s" % out.strip()[:300])
    if "读到 1 份文件" not in out:
        problems.append("只该读到那一份成品：%s" % out.strip()[:300])
    return problems


def check_block_level_four():
    """块标题写成四级时，切尾按它自己的级数切——后面那个四级小节里的表不是这一块的。

    起手认 `^#{3,}`（收得进四级），切尾只认 `^#{1,3}`（切不动四级），于是后面那一节
    整段被吞进这一块。这一块里的表是拿来取成品路径的，被吞进来的那张表里的名字会被
    当成成品去读——读不到就退 2，报一句「读不到」，指不到真病根。
    """
    four = IMPL_TEXT.replace("### 1.4 成品落点", "#### 1.4 成品落点") + """
#### 1.5 收尾

| 成品 | 落的是哪些条目 |
|:---|:---|
| `没有这一份/成品.py` | 这一节不是成品落点，随便举了个名字 |
"""
    root = Path(tempfile.mkdtemp(prefix="check-landing-level4-"))
    try:
        art = make(root, (check_docs.IMPL_DOC, IMPL_TEXT, four), None)
        code, out = run_landing(root, [])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 0:
        return ["退出码 %s，期望 0——后面那一节里那张表不是这一块的，不该当成品去读；"
                "输出：%s" % (code, out.strip()[:300])]
    if "编号在两边对得上" not in out:
        return ["输出里没有「编号在两边对得上」：%s" % out.strip()[:300]]
    return []


def main():
    print("跑 %d 例，另加 17 条单独走的\n" % len(CASES))
    bad = 0
    for title, tweak, art_tweak, want_code, want_text in CASES:
        problems, out = one(title, tweak, art_tweak, want_code, want_text)
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
    for title, fn in [
        ("不给成品路径时，从「成品落点」表里取", check_from_place_table),
        ("产出里没有第七份、命令行也没给路径：退 3，不是报错", check_no_impl_doc),
        ("第七份在、那一块没写：退 2——该有的缺了一块", check_place_block_missing),
        ("那一块里以「注：」起头的行提到「还没落成」，不算这一批没落成",
         check_note_not_not_yet),
        ("两个方案节：一节那一格写坏了，另一节的成品路径照旧收进来",
         check_two_sections_merged),
        ("块写成四级标题：后面那个四级小节里的表不算这一块的",
         check_block_level_four),
        ("落点表写着「还没落成」、命令行也没给路径", check_not_yet),
        ("「还没落成」写成表里的一格，照样按「还没落成」报", check_not_yet_in_cell),
        ("分几批落成：列了已落成的、那句话交代还没落的，正向漏号降成提示",
         check_partial_landing),
        ("名字以 `.` 开头的目录不往下走", check_dot_dirs_skipped),
        ("命令行给的成品路径读不到", check_paths_missing),
        ("产出目录读不到", check_root_missing),
        ("成品目录里不是 UTF-8 的文件跳过并说一声", check_binary_skipped),
        ("把产出目录当成品路径传：文档不算成品，不报假的全过", check_root_not_counted),
        ("产出目录里那份第七份也不算成品（它对账表里什么编号都有）", check_impl_not_counted),
        ("产出目录里没有第七份，成品却引了它的小节号", check_impl_missing),
        ("输出被重定向到管道时按 UTF-8 吐字节（把本机管道默认的 GBK 也设上了）", check_pipe_utf8),
    ]:
        problems = fn()
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
