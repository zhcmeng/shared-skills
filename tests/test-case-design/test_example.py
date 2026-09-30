#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能自带的材料，过不过得了技能自己的规矩。

    python tests/test-case-design/test_example.py

`references/` 下那几份是填不准时照抄的东西——范本等于这套栏目的事实定义，模板等于
各栏的写法定义。它们自己要是跟自己定的规矩对不上，照抄的人就跟着错，而且错在技能
自己身上。四条：

1. 范本拆成六份产出，喂给 check_docs.py 要零错零提示；
2. 技能自己的文字里不许出现它自己列进「容易写成」右列的词；
3. 技能自己的文字里不许出现具体环境名（WSL2、Docker、本机 Windows）——六份通用稿
   不认任何一种具体环境，技能自己带头写，照抄的人就跟着写进产出；
4. 模板给出的评测用例 id 例子，check_landing.py 要认得出里面的用例编号。
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

# 范本里那一节 → 产出里的哪一份文档。顺序照范本，标题照 check_docs.DOCS。
SECTIONS = [
    ("## 一、测试模型规格说明", "Test Model Specification.md"),
    ("## 二、测试用例规格说明", "Test Case Specification.md"),
    ("## 三、测试规程规格说明", "Test Procedure Specification.md"),
    ("## 四、测试数据需求", "Test Data Requirements.md"),
    ("## 五、测试环境需求", "Test Environment Requirements.md"),
    ("## 六、决策依据", "Decision Basis.md"),
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
    """范本拆成六份，喂给 check_docs.py。"""
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


def main():
    checks = [
        ("范本 `文档示例.md` 拆成六份，喂给 check_docs.py 零错零提示", check_example),
        ("技能自己的文字里没有「%s」" % BANNED, check_banned_words),
        ("技能自己的文字里没有具体环境名（%s）" % "、".join(ENV_WORDS), check_no_env_names),
        ("模板给的评测用例 id 例子，check_landing.py 认得出", check_id_example),
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
