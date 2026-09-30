#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能自带的材料，过不过得了技能自己的规矩。

    python tests/test-case-design/test_example.py

`references/` 下那几份是填不准时照抄的东西——范本等于这套栏目的事实定义，模板等于
各栏的写法定义。它们自己要是跟自己定的规矩对不上，照抄的人就跟着错，而且错在技能
自己身上。八条：

1. 范本拆成七份产出，喂给 check_docs.py 要零错零提示；
2. 技能自己的文字里不许出现它自己列进「容易写成」右列的词；
3. 技能自己的文字里不许出现具体环境名（WSL2、Docker、本机 Windows）——六份通用稿
   不认任何一种具体环境，技能自己带头写，照抄的人就跟着写进产出；
4. 模板给出的评测用例 id 例子，check_landing.py 要认得出里面的用例编号；
5. 模板第十节里写的第七份契约（文件名、对账表标题与它的表头、方案节标记、三块的名字）
   与 check_docs.py 里认的那几个常量对得上；
6. 讲落盘的那两处正文不许让「选了哪个方案」进六份——方案名在六份里一律报错，正文
   写着让它进去，模型照做、终检又得删掉；
7. 第七份的「跑不了原样的那几条」：模板说了事实从哪来（随包那份《能力与边界》）、
   范本里有这一段——缺哪一份都不成；
8. skill-up 的参考文档按承诺随包：五个文件都在，上游那三份一字不改、自己写的两份
   标明了来路。
"""

import contextlib
import io
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent.parent / "plugin" / "skills" / "test-case-design"
sys.path.insert(0, str(SKILL / "scripts"))
import check_docs  # noqa: E402
import check_landing  # noqa: E402

EXAMPLE = SKILL / "references" / "文档示例.md"
TEMPLATE = SKILL / "references" / "文档模板.md"

# 这一支里的参考文档。技能自包含，写着「不要去翻本机那份 clone」——那就得真的
# 有一份在包里，五个文件一个不少。
VENDOR_DIR = SKILL / "references" / "评测方案" / "skill-up"
VENDOR_FILES = ("README.md", "capabilities-and-limits.md", "LICENSE",
                "writing-evals.md", "cli-reference.md")
# 哪几份是上游原文、哪几份是本技能自己写的。上游那三份一字不改，由
# `git diff --no-index` 比一遍（见本 Task 的 Step 5）；自己写的那两份顶上要写明，
# 不然读的人会当成上游原文，上游一改版就不知道该信谁。
VENDOR_UPSTREAM = ("LICENSE", "writing-evals.md", "cli-reference.md")
VENDOR_OURS = ("README.md", "capabilities-and-limits.md")
VENDOR_OURS_MARK = "本技能自己写"
# 钉住的那一个 commit。逐字节比对比不出来时也不静默放过：至少把出处这一行钉死。
VENDOR_PIN = "7f1ff9b8e2d7c654728de526867f2f7e7b78ea51"

# 范本里那一节 → 产出里的哪一份文档。顺序照范本，标题照 check_docs.DOCS。
SECTIONS = [
    ("## 一、测试模型规格说明", "Test Model Specification.md"),
    ("## 二、测试用例规格说明", "Test Case Specification.md"),
    ("## 三、测试规程规格说明", "Test Procedure Specification.md"),
    ("## 四、测试数据需求", "Test Data Requirements.md"),
    ("## 五、测试环境需求", "Test Environment Requirements.md"),
    ("## 六、决策依据", "Decision Basis.md"),
    ("## 七、实施方案规格说明", check_docs.IMPL_DOC),
]

# SKILL.md 的「必须照写的几个词」定了「测试项」，右列写着最容易顺手写成的那个。
# 技能自己的文字带头用右列的说法，照抄的人就跟着写，产出里要被 check_docs 报出来。
# 词表本身那一行不算——它正是把这两个说法摆出来对照的地方。
BANNED = "被测对象"
WORD_TABLE_ROW = "| 测试项 |"

# 六份通用稿是给代码与技能当测试依据用的，不认任何一种具体环境。这三个词是
# SKILL.md「六份里不许出现的东西」那一节列出来的；技能自己的文字带头用它们，
# 写产出的人就跟着写。摆出这些词的那一节本身除外——那正是拿出来对照的地方。
ENV_WORDS = ("WSL2", "Docker", "本机 Windows")
ENV_WORD_SECTION = "## 六份里不许出现的东西"

# references/评测方案/ 这一支不归本技能的用词纪律管：上游文档一字不改，本技能自己
# 写的那份讲的是那门方案自己的环境（哪台机器、哪个 shell），正该点名。
# 两份扫描都跳过它——上游 writing-evals.md 里带着 6 处 Docker，《能力与边界》里
# 写着 WSL2。
VENDORED = "references/评测方案/"

# 模板里讲评测用例 id 前缀的那一条。测试认死这句话：话没了，说明这一条被挪走或改写，
# 该回来看一眼它旁边那个例子还在不在。
ID_RULE = "用例 id 带上规程编号前缀"


def split_example(text):
    """把范本按六节的标题切开，返回 {文件名: 正文}。

    范本把六份文档收在一个文件里，拆出来的东西还原成真产出的样子，才谈得上「拿它
    喂自检脚本」：

    - 各份的小节标题跟着降了一级（正式文档里写 `## 用户决策`，范本里是
      `### 用户决策`），这一级还回去；
    - 范本开头说了「文中凡以「注：」起头的行，都是本文加的说明，不是文档内容」，
      这些行去掉——留着它们，检查脚本会把说明当正文读，比如成品落点那一块里那句
      解释提到了「还没落成」，脚本就认不出这一块其实填好了。
    """
    docs = {}
    for i, (head, name) in enumerate(SECTIONS):
        start = text.index(head) + len(head)
        end = text.index(SECTIONS[i + 1][0]) if i + 1 < len(SECTIONS) else len(text)
        body = text[start:end]
        body = re.sub(r"^#+ ", lambda m: m.group(0)[1:], body, flags=re.M)
        body = "\n".join(l for l in body.splitlines() if not l.startswith("注："))
        docs[name] = "# " + head[3:] + body
    return docs


def check_example():
    """范本拆成七份，喂给 check_docs.py。"""
    docs = split_example(EXAMPLE.read_text(encoding="utf-8"))
    root = Path(tempfile.mkdtemp(prefix="check-example-"))
    try:
        for name, body in docs.items():
            (root / name).write_text(body, encoding="utf-8")
        buf = io.StringIO()
        old = sys.argv
        sys.argv = ["check_docs.py", str(root)]
        try:
            with contextlib.redirect_stdout(buf):
                code = check_docs.main()
        finally:
            sys.argv = old
    finally:
        shutil.rmtree(root, ignore_errors=True)
    out = buf.getvalue()
    if code != 0:
        return ["退出码 %s，期望 0" % code, out]
    if "0 处错误" not in out or "0 处提示" not in out:
        return ["范本正文过不了自检：", out]
    return []


def check_banned_words():
    """技能自己的 .md 里不许出现它自己列进「容易写成」的词。"""
    hits = []
    for path in sorted(SKILL.rglob("*.md")):
        rel = path.relative_to(SKILL).as_posix()
        if rel.startswith(VENDORED):
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if BANNED in line and not line.startswith(WORD_TABLE_ROW):
                hits.append("%s:%d：%s" % (rel, n, line.strip()))
    if not hits:
        return []
    return ["技能自己的文字里出现了「%s」——它是词表里「容易写成」的那一个，"
            "要写「测试项」：" % BANNED] + hits


def check_no_env_names():
    """技能自己的 .md 里不出现具体环境名（摆出这些词的那一节、那一支参考文档除外）。

    六份通用稿要能原样拿去当代码或技能的测试依据，所以它们不认 WSL2 还是 Docker
    这类具体环境。技能自己的文字里写着它们，照抄的人就跟着写进产出，产出再喂给
    check_docs.py 就被报出来——错在技能自己身上。
    """
    hits = []
    for path in sorted(SKILL.rglob("*.md")):
        rel = path.relative_to(SKILL).as_posix()
        if rel.startswith(VENDORED):
            continue
        listed = False
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("## "):
                listed = line.startswith(ENV_WORD_SECTION)
            if listed:
                continue
            for w in ENV_WORDS:
                if w in line:
                    hits.append("%s:%d：%s" % (rel, n, line.strip()))
                    break  # 一行报一次就够——上面那句已经把要找的三个词都列出来了
    if not hits:
        return []
    return ["技能自己的文字里出现了具体环境名（%s）——六份通用稿不认任何一种具体"
            "环境，要写「默认就是本机」：" % "、".join(ENV_WORDS)] + hits


def check_id_example():
    """模板给的那个评测用例 id 例子，落成对照脚本要认得出里面的用例编号。"""
    line = next((l for l in TEMPLATE.read_text(encoding="utf-8").splitlines()
                 if ID_RULE in l), None)
    if line is None:
        return ["文档模板.md 里找不到讲「%s」的那一条" % ID_RULE]
    tokens = re.findall(r"`([^`]+)`", line)
    if not tokens:
        return ["「%s」那一条里没给例子" % ID_RULE]
    example = tokens[0]
    if not check_landing.id_pattern("TC-").search(example):
        return ["模板给的例子 %s 里，check_landing.py 认不出用例编号——照它写的编号，"
                "落成之后会被报成「成品里一处也没出现」" % example]
    if not check_docs.CASE_DIR_RE.fullmatch(example):
        return ["模板给的例子 %s 不合评测用例目录名的形制——照它写成的目录名会被"
                "check_docs.py 报「不合形制」。最后那一段是「英文名」栏里的名字，"
                "而英文名只收小写字母、数字与下划线（不含连字符）" % example]
    return []


def check_impl_contract():
    """模板第十节把第七份的契约定死，脚本按同一套查——两处不许分叉。

    这一条盯的是名字：文件名、对账表标题与它的表头、方案节的标记、三块的名字。模板里
    写的与 check_docs.py 里认的不是同一个，照模板写出来的第七份就会被判错。
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    if "## 十、实施方案规格说明" not in text:
        return ["文档模板.md 里没有第十节「实施方案规格说明」"]
    body = text.split("## 十、实施方案规格说明", 1)[1]
    want = [check_docs.IMPL_DOC, check_docs.IMPL_MAP_HEAD, check_docs.IMPL_SCHEME_MARK]
    want += list(check_docs.IMPL_BLOCKS)
    missing = [w for w in want if w not in body]
    if missing:
        return ["模板第十节里没写到这几样（脚本按它们查第七份）：%s" % "、".join(missing)]
    # 对账表的表头另拿脚本自己的认表器过一遍。光看那两列的字在不在第十节里不够——
    # 它们在下面讲各栏怎么填的条目里也出现，改了表头照样「查得到」，这一条就成了
    # 空转。认表器不认，照模板抄出来的对账表脚本也就不认。
    if not check_docs.pick_all(check_docs.tables(body), check_docs.IMPL_MAP_COLS):
        return ["模板第十节里没有一张对账表，表头恰好含这几格：%s——照它抄出来的"
                "对账表，check_docs.py 认不出来"
                % " | ".join(check_docs.IMPL_MAP_COLS)]
    return []


# 第 0 步那两处讲「往产出里落什么」的正文。方案的选择不许出现在这两处——方案名在
# 六份里一律报错（决策依据也不例外，见设计稿 D16），正文写着让它进去，模型照做、
# 终检又得删掉，丢的正是决策依据存在的理由。
SCHEME_ROW_ANCHOR = "| 0 | 定开工输入"
SCHEME_PARA_ANCHOR = "**定完判完都要落进产出**"


def check_scheme_not_in_six():
    """讲落盘的那两处正文里，不许让「选了哪个方案」进六份产出。

    第 0 步确实要问「用哪个测评方案」（那一行的中间几栏正该写这件事），但六份通用稿
    一个字都不提它：方案名与配置文件名在六份里一律报错，决策依据也不豁免。所以这两处
    ——第 0 步那一行的**最后一格**（「落盘」栏列的是往六份里落什么）、以及讲落盘的那
    一段——里不该有「测评方案」。方案的选择落在第七份的节名上（「<节号>、方案：
    <方案名>」），六份里不记。
    """
    lines = (SKILL / "SKILL.md").read_text(encoding="utf-8").splitlines()
    row = next((l for l in lines if l.startswith(SCHEME_ROW_ANCHOR)), None)
    if row is None:
        return ["SKILL.md 的步骤表里找不到第 0 步那一行（找的是以「%s」起头的）"
                % SCHEME_ROW_ANCHOR]
    para = next((l for l in lines if l.startswith(SCHEME_PARA_ANCHOR)), None)
    if para is None:
        return ["SKILL.md 的「第 0 步」里找不到讲落盘的那一段（找的是以「%s」起头的）"
                % SCHEME_PARA_ANCHOR]
    hits = []
    cell = [c for c in row.split("|") if c.strip()][-1].strip()
    if "测评方案" in cell:
        hits.append("第 0 步那一行的「落盘」栏：%s" % cell)
    if "测评方案" in para:
        hits.append("「第 0 步」讲落盘的那一段：%s" % para.strip())
    if not hits:
        return []
    return ["这两处列的是往六份产出里落什么，却把测评方案也列了进去——模型照它把"
            "「选了哪个方案」记进六份，第 7 步终检又必须把那条删掉："] + hits


# 第七份「说明」那一块里最要紧的一段：跑不了原样的那几条。随包的那份《能力与边界》
# 就是为它准备的——这一段缺了，随包就白随了；事实从哪来没写，写的人只能靠猜或实测。
IMPL_GAP_HEAD = "跑不了原样的那几条"
IMPL_FACTS_SRC = "capabilities-and-limits.md"


def check_impl_gap_section():
    """第七份的「跑不了原样的那几条」：模板说了事实从哪来，范本里有这一段。

    两份都得有，缺哪一份都不成：

    - **模板**是写法定义——不写明「事实从同目录的 `capabilities-and-limits.md` 里取、
      不靠实测」，写的人只能自己跑一遍去猜，而那一份随包正是为了让这件事有据可依；
    - **范本**是这套栏目的事实定义——缺了这一小节，照范本抄出来的第七份就没有那一段，
      而它正是拿判据的人分「这条判不过是环境摆法造成的、还是被测的东西真有问题」的地方。
    """
    problems = []
    body = TEMPLATE.read_text(encoding="utf-8").split("## 十、实施方案规格说明", 1)
    if len(body) < 2:
        return ["文档模板.md 里没有第十节「实施方案规格说明」"]
    line = next((l for l in body[1].splitlines() if IMPL_GAP_HEAD in l), None)
    if line is None:
        problems.append("文档模板.md 第十节里没有讲「%s」的那一条" % IMPL_GAP_HEAD)
    elif IMPL_FACTS_SRC not in line or "不靠实测" not in line:
        problems.append("模板第十节讲「%s」的那一条没写清事实从哪来——要写明从同目录的 "
                        "%s 里取、不靠实测，不然写的人只能自己猜或实测：%s"
                        % (IMPL_GAP_HEAD, IMPL_FACTS_SRC, line.strip()))
    example = EXAMPLE.read_text(encoding="utf-8").split("## 七、实施方案规格说明", 1)
    if len(example) < 2:
        return problems + ["文档示例.md 里没有第七节「实施方案规格说明」"]
    if IMPL_GAP_HEAD not in example[1]:
        problems.append("文档示例.md 第七节的「说明」里没有「%s」这一小节——范本等于"
                        "这套栏目的事实定义，缺一节，照它抄出来的第七份就没有那一段"
                        % IMPL_GAP_HEAD)
    return problems


def check_vendored():
    """skill-up 的参考文档五个文件都在；上游那三份一字不改，自己写的那两份标明了。"""
    if sorted(VENDOR_UPSTREAM + VENDOR_OURS) != sorted(VENDOR_FILES):
        return ["测试自己写错了：VENDOR_FILES 与「上游／自己写的」那两份名单对不上"
                "——一边加了文件，另一边没加"]
    if not VENDOR_DIR.is_dir():
        return ["没有 %s 这一目录——技能里说「读技能里这一份」，那就得真的有一份"
                % VENDOR_DIR.relative_to(SKILL).as_posix()]
    missing = [f for f in VENDOR_FILES if not (VENDOR_DIR / f).is_file()]
    if missing:
        return ["%s 下缺这几个文件：%s" % (VENDOR_DIR.relative_to(SKILL).as_posix(),
                                          "、".join(missing))]
    readme = (VENDOR_DIR / "README.md").read_text(encoding="utf-8")
    if VENDOR_PIN not in readme:
        return ["那目录的 README.md 里没钉住上游的 commit（%s）——上游改版之后，"
                "读的人只能靠这一行看出它旧了" % VENDOR_PIN]
    if "Apache" not in (VENDOR_DIR / "LICENSE").read_text(encoding="utf-8"):
        return ["LICENSE 不是 Apache License 的全文——再分发要随附许可全文"]
    for name in VENDOR_OURS:
        text = (VENDOR_DIR / name).read_text(encoding="utf-8")
        if VENDOR_OURS_MARK not in text:
            return ["%s 顶上没写明这一份不是上游原文（缺「%s」这句）——读的人会把它"
                    "当成上游的，上游改版时就不知道该信谁" % (name, VENDOR_OURS_MARK)]
    return []


def main():
    checks = [
        ("范本 `文档示例.md` 拆成七份，喂给 check_docs.py 零错零提示", check_example),
        ("技能自己的文字里没有「%s」" % BANNED, check_banned_words),
        ("技能自己的文字里没有具体环境名（%s）" % "、".join(ENV_WORDS), check_no_env_names),
        ("模板给的评测用例 id 例子，check_landing.py 认得出", check_id_example),
        ("模板第十节与脚本常量对得上：文件名、对账表、方案节、三块", check_impl_contract),
        ("讲落盘的正文没让「选了哪个方案」进六份", check_scheme_not_in_six),
        ("第七份的「跑不了原样的那几条」：模板说了事实从哪来、范本里有这一段",
         check_impl_gap_section),
        ("skill-up 的参考文档随包（五个文件都在，上游三份、自己写的两份各标明）", check_vendored),
    ]
    failed = 0
    for title, fn in checks:
        problems = fn()
        if problems:
            failed += 1
            print("[失败] %s" % title)
            for p in problems:
                print("       " + p)
        else:
            print("[通过] %s" % title)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
