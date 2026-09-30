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

# 「成品落点」是模板第四节的第五块：落成之后回来填。{ART} 由 make() 换成临时成品路径
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

## 四、成品落点

| 成品 | 落的是哪些条目 |
|:---|:---|
| `{ART}` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |
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
| DATA-1 | demo_text | 一段文本 | 不需要 |
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
# 定义过的每一条 `ENV-…`／`DATA-…` 都列出来一次——于是它跟那六份一样，是个「什么
# 编号都有」的文本。它有时也在产出目录里，所以「产出目录不算成品」那份名单里也得有它。
IMPL_TEXT = """# 实施方案规格说明

这一份把六份通用稿落成能跑的东西。

## 一、通用稿的编号落到哪

| 通用稿的编号 | 本方案里落在哪 | 说明 |
|:---|:---|:---|
| ENV-1 | `eval.yaml` 里装技能那一段 | 装技能那一条 |
| DATA-1 | `cases/tp01-01-TC-1-verify_a.yaml` 的提示词 | 那段文本 |

## 二、方案：skill-up

### 2.1 说明

一条用例一轮，判据交给判官。

### 2.2 可跑配置（YAML 原文）

```yaml
engine: claude
```

### 2.3 怎么跑、报告落在哪

```bash
skill-up run eval.yaml
```
"""

# 最小的一份成品：六类编号各出现一次。名字写成真测试的样子，看它认不认得住
ART_TEXT = """# -*- coding: utf-8 -*-
\"\"\"假的成品：编号照抄进来的样子。\"\"\"


def test_TC_1_verify_a():
    \"\"\"TCOV-1：TM-1 里的有效等价类。跑 TP-1 那条规程，按 DATA-1 取文本，ENV-1 就位。\"\"\"
"""

# 每一例：说明、改产出哪儿（文件名, 把什么, 换成什么）、改成品哪儿（把什么, 换成什么）、
# 期望退出码、输出里该出现的话（以 ! 开头表示「不该出现」）
CASES = [
    ("基线：六类编号在成品里都找得到", None, None, 0, "编号在两边对得上"),
    ("成品里漏了模型编号 TM-1", None, ("TM-1 里的", "模型里的"), 1, "测试模型：这些条目定义了"),
    ("成品里漏了覆盖项编号 TCOV-1", None, ("\"\"\"TCOV-1：", "\"\"\""), 1, "测试覆盖项：这些条目定义了"),
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
    """造一套产出与一份成品，返回成品路径。"""
    art = root / "假成品.py"
    art.write_text(ART_TEXT, encoding="utf-8")
    docs = dict(BASE)
    if tweak:
        name, old, new = tweak
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
    """命令行上不给成品路径时，从产出里的「成品落点」表取。

    这条走的是另一条入口：表里的路径能不能被认出来、能不能照着读成品。
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
    """落点表上写着「还没落成」，命令行上也没给路径——说清楚，别当成「对得上」。"""
    root = Path(tempfile.mkdtemp(prefix="check-landing-notyet-"))
    try:
        make(root, (CASE, "| 成品 | 落的是哪些条目 |\n|:---|:---|\n| `{ART}` | TC-1 与它的覆盖项、TM-1、TP-1、DATA-1、ENV-1 |",
                    "还没落成。"), None)
        code, out = run_landing(root, [])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 2:
        return ["退出码 %s，期望 2" % code]
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
        (root / check_docs.IMPL_DOC).write_text(IMPL_TEXT, encoding="utf-8")
        code, out = run_landing(root, [root])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if code != 2:
        return ["退出码 %s，期望 2" % code]
    for want in ("产出目录里那几份文档没算成品", "成品一份都没读到"):
        if want not in out:
            return ["输出里没有「%s」：%s" % (want, out.strip()[:300])]
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


def main():
    print("跑 %d 例，另加 8 条单独走的\n" % len(CASES))
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
        ("落点表写着「还没落成」、命令行也没给路径", check_not_yet),
        ("命令行给的成品路径读不到", check_paths_missing),
        ("产出目录读不到", check_root_missing),
        ("成品目录里不是 UTF-8 的文件跳过并说一声", check_binary_skipped),
        ("把产出目录当成品路径传：文档不算成品，不报假的全过", check_root_not_counted),
        ("产出目录里那份第七份也不算成品（它对账表里什么编号都有）", check_impl_not_counted),
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
