#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 test-case-design 产出的文档是否符合技能定下的契约。

用法：

    python check_docs.py <产出目录>
    python check_docs.py --rules        把「它会拒绝什么」打出来，不用产出目录

退出码：0 全过；1 有错；2 用法不对或读不到文件。

`--rules` 是给写产出的人看的一条命令：禁用词、认哪几栏、哪些取值写死了，一次打全
（内容按下面说的同一份来源现取，与检查时用的是一份）。**要确认它会拒绝什么，跑这条
命令就行，不必读这份脚本的源码**——读了也只是把这些常量与两张表再认一遍。

管的都是机械项：编号连不连续、栏目齐不齐、引用指不指得到、对应表有没有留空、
枚举出的英文名合不合形制、禁用词有没有漏进来。判断性的东西（模型建得对不对、
覆盖项取全没有、用例导得够不够、引的编号对不对得上内容、英文名取得准不准）
不在这里管——那是人看的，脚本报不了。

**分两组查。**六份通用稿是一组（`DOCS` 那份名单，缺一份就报错）；第七份《实施方案
规格说明》（`IMPL_DOC`）按需产出，产出目录里有它时才另起一组——查它的骨架（导语、
`方案：`节、节里的对账表、末尾的成品落点）、每个方案节里四块齐不齐与次序对不对、六类编号两个方向的
对账（`IMPL_CLASSES`：模型、覆盖项、用例、规程、数据项、环境项）。没有它整组跳过，连
提示都不报：分层之前留下的那几套产出不该因此多出一条错。

第七份里**不贴配置原文**（配置由落成那一步写进盘里；抄一份到文档里就是第二份会
漂移的副本），所以本模块不碰 YAML，也不依赖任何第三方库。

两条方向相反的引用检查：用例与规程里引了不存在的数据项或环境项，算错误（悬空）；
测试数据需求与测试环境需求里定义了、却没有任何用例与规程引用的编号，算提示（孤儿）
——某条数据或某项环境可能确实没有哪条用例直接引它。

契约不在这份脚本里另立一套，来源是技能自己的两份文件：

  - `references/文档模板.md`：产出各份的栏目、编号方案、两张对应表的格式，以及
    第七份的骨架契约（第十节）
  - `SKILL.md` 的两张词表：「必须照写的几个词」表的右列（最容易顺手写成的那个
    说法）、「六份里不许出现的东西」表的左列（方案名、配置文件名、具体环境名）

两张表改了，这里跟着变，不用两边各改一遍；解析不出来时直接报错退出，不拿一份空表
去判。

一条要紧的区分：**「提到过」不等于「定义过」**。对应表里引用了某条用例，不等于那条用例
真写出来了。所以每个对象都单独认「定义处」——章节标题、加粗的**唯一标识符**、或表里
以该编号打头的那一行；只在正文里被提及的，不算定义。
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_MD = HERE.parent / "SKILL.md"

# 六份产出的文件名。产出都用英文文件名，正文是中文——脚本读的只是文件名，
# 栏目、编号、禁用词那几项照旧按中文认。
MODEL_DOC = "Test Model Specification.md"
CASE_DOC = "Test Case Specification.md"
PROC_DOC = "Test Procedure Specification.md"
DATA_DOC = "Test Data Requirements.md"
ENV_DOC = "Test Environment Requirements.md"
DECISION_DOC = "Decision Basis.md"
DOCS = [MODEL_DOC, CASE_DOC, PROC_DOC, DATA_DOC, ENV_DOC, DECISION_DOC]

# 第七份：按需产出，不进 DOCS。它不定义任何编号（不参与发号），所以在产出目录里
# 找不到它时整组跳过——分层之前留下的那几套产出不该因此多出一条错。
IMPL_DOC = "Implementation Specification.md"

# 文档模板第六、七节：这两份的栏是写死的，正好几栏就是几栏。
# 这两组只做「认定义处」用，所以不含英文名——英文名另查，见下面 NAME_COL 那段说明。
DATA_COLS = ["唯一标识符", "描述", "重置需求"]
ENV_COLS = ["唯一标识符", "测试环境项", "描述"]
# 文档模板第八节的两张对应表
TRACE_COLS = ["依据的出处", "模型编号", "说明"]
MAP_COLS = ["覆盖项编号", "覆盖项描述", "覆盖它的用例编号"]
# 「覆盖它的用例编号」那一格：还等着补用例的留空（下面按留空报错），判为不可行、
# 已从分母里剔除的写这四个字（后面可以接一句原因）。两种「没有用例」意思不同——
# 一种是欠着的，一种是结清的——写成一个样子，读的人分不出来，脚本也分不出来。
INFEASIBLE = "不可行"
# 文档模板第四节：覆盖项清单四栏
COV_COLS = ["唯一标识符", "描述", "风险等级", "可追溯性"]
# 用例那几栏里必查的三栏。前置条件可以全篇统一说明一次，可追溯性由对应表承接，
# 风险等级是「需要时写」——按模板这三栏都不必逐条出现，故不列。
CASE_COLS = ["目标", "输入", "预期结果"]

# 文档模板第四节：用例表里那一栏「判据落在哪一层」——写这条用例的判据得看着什么才判得了。
# 写在用例上而不是规程上：同一条规程里两种都有是常事。这一栏决定用例落成什么形式，
# 也是「各批落到哪」分批的依据——落在输出上的归可跑测试，要读执行过程的归评测用例。
# 一栏漏了、取值写错，都不会有人喊：落成那一步才发现，那时候通用稿已经定了稿。
LAYER_COL = "判据落在哪一层"
LAYERS = ("落在输出上", "要读执行过程")
# 「执行器」栏与这一栏是同一件事的两面：脚本跑的规程，判据只能落在命令、退出码与盘上的
# 文件上；靠模型跑的那两种（控制器、子代理），判据要读一轮执行过程。对不上就是有一处
# 写错了，而分批正是按这两栏分的——错了会把一条要读过程的用例落成一段跑命令的代码。
EXECUTOR_LAYER = {"脚本": ("落在输出上",), "控制器": ("要读执行过程",),
                  "子代理": ("要读执行过程",)}

# 文档模板第九节：决策依据文档分两块写，一行一条决策，栏目写死。
# 第一块「用户决策」装「用户给的」那几条——用户拍板的，可以直接改；第二块「模型决策」
# 装其余几条——只增不改。块名由脚本认，所以在这里定死；这两块分得对不对是机械项：
# 「依据的来源」栏只填三个值之一，哪一行归哪一块判得了。
DEC_COLS = ["唯一标识符", "在哪一步", "决定", "考虑过的其他做法", "依据", "依据的来源"]
USER_HEAD = "用户决策"
MODEL_HEAD = "模型决策"
USER_SRC = "用户给的"

# 文档模板第四节：测试用例规格说明分四块写，第四块是「覆盖率自检」——一行一门
# 选定的技术，记这一门（这一档）识别的覆盖项条数 T、已被用例覆盖的条数 N、算出来
# 的覆盖率与完成准则的要求。
# 第 6 步自检的结论落在这一块，所以缺了报错；六栏写死，与模板一致。
COVER_HEAD = "覆盖率自检"
COVER_COLS = ["技术（档位）", "覆盖项编号", "覆盖项总数 T", "已被用例覆盖 N",
              "覆盖率 N÷T", "完成准则要求"]
# 覆盖项编号栏：`TCOV-3` 是单个，`TCOV-1～TCOV-4` 是范围（全角波浪号与半角都认）。
COVER_ID = re.compile(r"TCOV-(\d+)")
COVER_RANGE = re.compile(r"TCOV-(\d+)\s*[～~]\s*TCOV-(\d+)")
# 一段范围最多展开这么多条。`TCOV-1～TCOV-999999999` 这种少打或多打几位的笔误，
# 按「认不出」报就行，别真去铺一个十亿长的列表——那会把脚本拖死，一句话也报不出来。
# 一份产出里的覆盖项数远到不了这个量级，真到了也该拆表写。
COVER_SPAN_MAX = 10000
# 覆盖率栏：`8÷8＝100%`——全角除号与等号，一位小数或不带小数。
COVER_CELL = re.compile(r"(\d+)÷(\d+)＝(\d+(?:\.\d)?)%")

# 文档模板第十节：第七份每个方案节的最后一块「成品落点」——成品（落下来的测试代码、
# 评测用例）落在哪。设计的时候成品多半还没落，那一块写「还没落成」；落成之后回来把
# 表填上。
# 原先住在测试用例规格说明里（第五节），那样通用稿就带上了只有方案才知道的成品路径；
# 搬进第七份之后，落点与落成进度都只住在认方案的那一份文档里。
# 只有一栏。原先另有一栏「落的是哪些条目」，2026-10-02 砍掉：脚本一行都不读它
# （check_landing.py 只取 PLACE_COLS[0]，本文件只查那一格空没空），落成的人白填一格，
# 而它记的「哪些号落在这份成品里」check_landing.py 从成品里现读得出来。
# 表里的路径由 check_landing.py 拿去读成品，两处共用这一份定义。
PLACE_HEAD = "成品落点"
PLACE_COLS = ["成品"]
NOT_YET = "还没落成"

# 测试规程的两栏取值写死（文档模板第五节）。取值后面允许带一句括号说明，
# 所以按「起头」判，不按全等。
EXECUTORS = ("脚本", "控制器", "子代理")
CHANGES = ("只读", "会写")

# 文档模板第五节末：测试规程规格说明末尾另起一节，把这套规程按落点分批，
# 表里把每条规程列到。分得对不对（判据落在哪）是判断，脚本只核列全没有。
BATCH_HEAD = "各批落到哪"
BATCH_COLS = ["批次", "规程", "落到哪"]

# 同一张表里落成评测用例的那几行，另起一栏按执行顺序列该规程用例的目录名。
# 评测工具按目录名的字母序跑（`--case` 接的也是目录名），名字排成什么顺序就跑成
# 什么顺序——两段位次各定两位，字母序才等于「先规程号、再规程内位次」。
# 落成可跑测试的行（「执行器」栏是「脚本」）这一栏空着。
CASE_DIR_COL = "用例目录名"
EVAL_EXECUTORS = ("控制器", "子代理")

# SKILL.md 里「产出文档里只写测试内容，不把技能文件里的节号与出处带出去」点名的东西。
# 禁用词表本身从 SKILL.md 解析，不在这里再抄一份。
LEAKED = ["references/", "GB/T", "TD1", "TD2", "TD3", "TD4"]

# 第七份的骨架，照 references/文档模板.md 第十节：开头一句导语；每个方案一节，节里
# 四块，按下面的先后排——「通用稿的编号落到哪」的对账表、说明、怎么跑与报告落在哪、
# 成品落点。最后那一块落成之后才填得全，排在末尾，补写的人翻到文末就找着地方。
# 块按标题里的词认，不认死标题全文——「1.2 怎么跑、报告落在哪」这种写法要收得进来。
#
# **对账表在方案节里面查**：一张表对一个方案，将来第二套方案另有自己的一张；摆在
# 方案节外面时，两套方案的落点挤在同一张表里，或者后一套的落点没处放。
IMPL_MAP_HEAD = "通用稿的编号落到哪"
IMPL_MAP_COLS = ["通用稿的编号", "本方案里落在哪"]
IMPL_SCHEME_MARK = "方案："
IMPL_BLOCKS = ("编号落到哪", "说明", "怎么跑", "成品落点")

# 对账表六类都收（模板第十节）：六份里定义过的每一条编号，这一份里都要给个落点。
# 四类整批落在同一处是常事（一类一行、号列全），但「给了落点没有」这件事按号查，
# 所以六类走同一套判定，不因为「通常都落得到」就少查几类。
IMPL_CLASSES = [
    ("TM-", "模型"),
    ("TCOV-", "覆盖项"),
    ("TC-", "用例"),
    ("TP-", "规程"),
    ("DATA-", "数据项"),
    ("ENV-", "环境项"),
]

# 「英文名」这一栏：给下游把条目落成代码时照抄的名字核（模板第二节）。
# 六类条目都带它，决策依据那份不带——那份记的是过程，不落成任何对象。
#
# 认条目定义处用的那几组栏（COV_COLS、CASE_COLS、DATA_COLS、ENV_COLS、DEC_COLS）特意
# 不把这一栏并进去：并进去以后，技能改版前写下的产出目录会认不出自己的条目，
# issue_ids.py 就照着发重号。这一栏另查一遍即可，两边不搭着。
NAME_COL = "英文名"
# 小写字母起头，只含小写字母、数字、下划线
NAME_RE = re.compile(r"[a-z][a-z0-9_]*")
# 名字里不许拿编号起头：下游拼标识符时自己会带编号，带了就成 tcov_1_tcov_1_…
NAME_IS_ID = re.compile(r"(tm|tcov|tc|tp|data|env|dec)_?\d")
# 评测用例的目录名：tp<规程号两位>-<规程内执行位次两位>-TC-<用例编号>-<英文名>。
# 用例编号那段照「落成约定」不补零（`[1-9]\d*` 挡掉 `TC-01`），英文名那段与条目上
# 那一栏合同一个形制。
CASE_DIR_RE = re.compile(r"^tp(\d{2})-(\d{2})-TC-([1-9]\d*)-(" + NAME_RE.pattern + r")$")
# 模型与规程不写成宽表：模型用加粗字段，规程写在两列表里。两种写法都认。
NAME_BOLD = re.compile(r"^\*\*" + NAME_COL + r"\*\*[：:]\s*(.*?)\s*$", re.M)
NAME_ROW = re.compile(r"^\|\s*" + NAME_COL + r"\s*\|\s*([^|]*?)\s*\|\s*$", re.M)

# 这几个从「容易写成」一栏里解析出来，但不能按字面禁：
#   「测试用例」「测试数据」本身是技能要求的术语（测试用例规格说明、测试数据需求）；
#   「统写成「要」」是一条行文纪律，不是一个词。
NOT_BANNED = {"测试用例", "测试数据", "统写成「要」"}

# SKILL.md 里「六份里不许出现的东西」那一节列的词，脚本按它查，命中就报错。
# 范围分两档：方案名与它自己的配置文件名六份全查；具体环境名不查 DECISION_DOC——
# 那一份记的是过程，「当时定的是本机 Windows」是照实记，不是违规。
#
# 档位（哪几个词算环境名）写在脚本里，不塞进那张表的第三列：哪几个词是环境名是
# 一次判断，不是配置；摆在这儿一眼看得见。词本身照旧只写在 SKILL.md 里一处，
# 两处分叉由 test_check_docs.py 的 check_env_word_scope() 盯着。
ENV_WORDS = ("WSL2", "Docker", "本机 Windows")
SCHEME_WORDS_MIN = 6


def banned_words():
    """取 SKILL.md「必须照写的几个词」表右列，按顿号与斜杠拆开。"""
    if not SKILL_MD.is_file():
        return []
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.search(r"^## 必须照写的几个词\s*$(.*?)^## ", text, re.S | re.M)
    if not m:
        return []
    words = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] == "本技能要求":
            continue
        if set(cells[0]) <= set(":-"):  # 分隔行
            continue
        for w in re.split(r"[、／/]", cells[1]):
            w = w.strip()
            if w and w not in NOT_BANNED:
                words.append(w)
    return words


def scheme_words():
    """取 SKILL.md「六份里不许出现的东西」表左列，整词收，不拆。

    和 banned_words() 一个样子，只差一点：这一列不按顿号与斜杠拆开——拆了
    「本机 Windows」就成了「本机」和「Windows」，「Windows」这个词本身不该禁。
    """
    if not SKILL_MD.is_file():
        return []
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.search(r"^## 六份里不许出现的东西\s*$(.*?)^## ", text, re.S | re.M)
    if not m:
        return []
    words = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] == "词":
            continue
        if set(cells[0]) <= set(":-"):  # 分隔行
            continue
        words.append(cells[0])
    return words


def split_row(line):
    """把一行表格切成单元格：`\\|` 是转义的竖线，属于格里，不当分隔符。

    不认转义的话，一格里有 `\\|`（写命令行的地方常事，比如 `cat x \\| python y.py`），
    它后面那几栏整个往前错一位——`row[i]` 拿到的是隔壁栏的内容，读出来的是另一个
    意思，还不报错。这个错位一直躲着：以前按位置读的只有第一栏（编号）与第二栏
    （英文名），都在转义点的前面。
    """
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def tables(text):
    """切出 Markdown 表格，返回 [(表头, [数据行, ...]), ...]。

    连续以 | 开头的行算一张表；第二行不是 |---| 分隔行的，不是表格，丢掉。
    """
    blocks, cur = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|") and len(s) > 1:
            cur.append(s)
        else:
            if cur:
                blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)

    parsed = []
    for block in blocks:
        if len(block) < 2:
            continue
        rows = [split_row(r) for r in block]
        if not all(re.fullmatch(r":?-{2,}:?", c) for c in rows[1]):
            continue
        parsed.append((rows[0], rows[2:]))
    return parsed


def pick_all(parsed, cols):
    """表头含齐 cols 的**所有**表。"""
    return [(h, b) for h, b in parsed if all(c in h for c in cols)]


def pick(parsed, cols):
    found = pick_all(parsed, cols)
    return found[0] if found else (None, None)


def ids_from_text(text, prefix):
    """从章节标题、加粗标签、表首格里认定义处。返回 {编号: 出处说明}。"""
    out = {}
    for m in re.finditer(r"^#{1,6}\s*(.+)$", text, re.M):
        n = re.search(prefix + r"(\d+)", m.group(1))
        if n:
            out.setdefault(int(n.group(1)), "标题")
    for m in re.finditer(r"\*\*([^*\n]*?" + prefix + r"(\d+)[^*\n]*?)\*\*", text):
        out.setdefault(int(m.group(2)), "加粗标签「%s」" % m.group(1).strip())
    return out


def ids_from_rows(parsed, cols, prefix):
    """表头含齐 cols 的表里，首格恰好是 PREFIX-n 的那些行。"""
    out = {}
    for head, body in pick_all(parsed, cols):
        for row in body:
            if not row:
                continue
            m = re.fullmatch(prefix + r"(\d+)", row[0])
            if m:
                out.setdefault(int(m.group(1)), "表首格")
    return out


def defined(parsed, text, cols, prefix):
    out = ids_from_text(text, prefix)
    out.update(ids_from_rows(parsed, cols, prefix))
    return out


def check_name(value, rep, where, who):
    """一条「英文名」：不能空、要合形制、不许拿编号起头。

    判的是形制，不是名字取得好不好——名字取得准不准由人看。
    """
    if not value:
        rep.err(where, "%s 的「英文名」是空的——空着等于这个名字还是留给下游每次现取" % who)
        return
    if not NAME_RE.fullmatch(value):
        rep.err(where, "%s 的「英文名」不合形制：%s——应是小写字母起头，"
                       "只含小写字母、数字、下划线" % (who, value))
        return
    if NAME_IS_ID.match(value):
        rep.err(where, "%s 的「英文名」以编号起头：%s——编号由下游自己拼，"
                       "这一栏只写名字本身" % (who, value))


def check_name_col(head, body, rep, where, label):
    """宽表里的「英文名」栏：栏在不在、每一行的值合不合形制。"""
    if NAME_COL not in head:
        rep.err(where, "%s缺栏目：%s" % (label, NAME_COL))
        return
    i = head.index(NAME_COL)
    for row in body:
        if not row:
            continue
        check_name(row[i] if i < len(row) else "", rep, where, row[0])


def case_layers(parsed):
    """用例表里的 {用例号: 「判据落在哪一层」栏的值}。

    只认带这一栏的用例表；没有这一栏的表整个跳过。没有这一栏是「写产出的时候还没
    这一栏」还是「这一版漏了」，脚本分不出来，由 check_case 那一处按「全篇都没这一栏」
    报一条提示——产出是更早的版本上写的，照旧；新写的补上。
    """
    out = {}
    for head, body in pick_all(parsed, CASE_COLS):
        if LAYER_COL not in head:
            continue
        i = head.index(LAYER_COL)
        for row in body:
            if not row:
                continue
            m = re.fullmatch(r"TC-(\d+)", row[0])
            if m:
                out.setdefault(int(m.group(1)),
                               row[i].strip() if i < len(row) else "")
    return out


def case_names(parsed):
    """用例表里的 {用例号: 英文名}——评测用例的目录名最后一段要对得上它。

    栏在、值空的记成空串，好与「文档里根本没有这条用例」分开：前者是那一栏没填，
    后者是引了一条不存在的用例，两处该说的话不一样。
    """
    out = {}
    for head, body in pick_all(parsed, CASE_COLS):
        i = head.index(NAME_COL) if NAME_COL in head else None
        for row in body:
            if not row:
                continue
            m = re.fullmatch(r"TC-(\d+)", row[0])
            if m:
                out.setdefault(int(m.group(1)),
                               row[i].strip() if i is not None and i < len(row) else "")
    return out


def name_fields(text):
    """模型与规程的「英文名」：加粗字段与两列表行两种写法都收。"""
    return [m.strip() for m in NAME_BOLD.findall(text) + NAME_ROW.findall(text)]


def field_values(text, label):
    """某个栏目的取值：加粗字段与两列表行两种写法都收。

    规程的「执行器」「改动文件」用它。这两个名字特意不放进 check_proc 里那张
    粗查表——文末「各批落到哪」那张表的表头里有「执行器」三字，粗查会被它蒙混
    过去：一条规程都没填，也会判成「栏在」。
    """
    bold = re.compile(r"^\*\*" + label + r"\*\*[：:]\s*(.*?)\s*$", re.M)
    row = re.compile(r"^\|\s*" + label + r"\s*\|\s*([^|]*?)\s*\|\s*$", re.M)
    return [m.strip() for m in bold.findall(text) + row.findall(text)]


def referenced(text, prefix):
    """一份文档里出现的某个前缀的编号集合——出现过就算，不区分它在哪一栏。"""
    return {int(n) for n in re.findall(re.escape(prefix) + r"(\d+)", text)}


def check_refs(text, rep, name, known):
    """文档里出现的编号都要指得到定义处。

    known：{"DATA-": {编号}, "ENV-": {编号}}。用例与规程这两份都可能引到数据项
    与环境项，所以两个前缀都查。引了却不存在的，模型查不到就会编——算错误。
    """
    for prefix, ids in known.items():
        for n in sorted(referenced(text, prefix) - ids):
            rep.err(name, "引用了没有定义处的 %s%d" % (prefix, n))


def check_contiguous(nums, prefix):
    if not nums:
        return "一个 %s 编号都没有" % prefix
    want = list(range(1, len(nums) + 1))
    if nums != want:
        missing = [n for n in want if n not in nums]
        extra = [n for n in nums if n > len(nums)]
        parts = []
        if missing:
            parts.append("缺 %s" % "、".join("%s%d" % (prefix, n) for n in missing[:8]))
        if extra:
            parts.append("多出 %s" % "、".join("%s%d" % (prefix, n) for n in extra[:8]))
        return "编号不是从 1 起连续：" + "；".join(parts)
    return None


def brief(nums, prefix, limit=10):
    shown = "、".join("%s%d" % (prefix, n) for n in nums[:limit])
    return shown + ("…" if len(nums) > limit else "")


class Report:
    def __init__(self):
        self.errors = 0
        self.warns = 0

    def err(self, where, msg):
        self.errors += 1
        print("  [错误] %s：%s" % (where, msg))

    def warn(self, where, msg):
        self.warns += 1
        print("  [提示] %s：%s" % (where, msg))

    def ok(self, msg):
        print("  [通过] %s" % msg)


def check_model(text, rep):
    """测试模型规格说明：模型定义处编号连续；栏齐；末尾「依据 → 模型」表指得到每个模型。"""
    parsed = tables(text)
    tms = defined(parsed, text, [], "TM-")
    bad = check_contiguous(sorted(tms), "TM-")
    if bad:
        rep.err(MODEL_DOC, bad)
    else:
        rep.ok("模型 TM-1 至 TM-%d 都有定义处，编号连续" % len(tms))

    fields = ["唯一标识符", "英文名", "目标", "风险等级", "测试策略摘要", "测试模型"]
    missing = [f for f in fields if ("**%s**" % f) not in text and ("| %s |" % f) not in text]
    if missing:
        rep.err(MODEL_DOC, "模型缺栏目：%s" % "、".join(missing))

    # 一个模型一个英文名，只看数量对不对得上；哪一行配哪个模型由人看
    names = name_fields(text)
    if names and len(names) != len(tms):
        rep.err(MODEL_DOC, "%d 个模型，英文名写了 %d 个——每个模型都要有一个"
                % (len(tms), len(names)))
    for value in names:
        check_name(value, rep, MODEL_DOC, "模型")

    head, body = pick(parsed, TRACE_COLS)
    if head is None:
        rep.err(MODEL_DOC, "末尾没有「依据 → 模型」对应表（表头应为：%s）" % " | ".join(TRACE_COLS))
        return set(tms)

    listed = set()
    for row in body:
        if len(row) < len(TRACE_COLS):
            rep.err(MODEL_DOC, "对应表有一行栏数不够：%s" % " | ".join(row))
            continue
        # 一行可以挂多个模型（`TM-1、TM-2`）：只取第一个的话，后一个静默地丢了，
        # 下面那句「没进表」就把它报成漏——而它明明写在表里，照着报错去补会补出重复行。
        found = re.findall(r"TM-(\d+)", row[head.index("模型编号")])
        if found:
            listed.update(int(x) for x in found)
        else:
            rep.err(MODEL_DOC, "对应表有一行的「模型编号」栏不是 TM- 编号：%s" % row[0])
        for name in ("依据的出处", "说明"):
            if not row[head.index(name)]:
                rep.err(MODEL_DOC, "对应表有一行的「%s」是空的" % name)

    for n in sorted(set(tms) - listed):
        rep.err(MODEL_DOC, "TM-%d 没进「依据 → 模型」表，追溯断在这里" % n)
    for n in sorted(listed - set(tms)):
        rep.err(MODEL_DOC, "对应表里的 TM-%d 在正文里找不到定义处" % n)
    if tms and set(tms) == listed:
        rep.ok("每个模型都进了「依据 → 模型」表")
    return set(tms)


def infeasible_covs(text):
    """对应表里判为不可行、已从分母里剔除的覆盖项：{编号}。

    认法：那一格写着「不可行」，且一个 TC- 编号都没有。check_landing.py 也从这里取
    ——这些覆盖项不会有用例，成品里本来就不该出现，正向对照得先把它们摘出去。两边
    各认一份的话，迟早一边说「判过不可行了」、一边说「漏了」。
    """
    head, body = pick(tables(text), MAP_COLS)
    out = set()
    if head is None:
        return out
    for row in body:
        if len(row) < len(MAP_COLS):
            continue
        m = COVER_ID.fullmatch(row[head.index("覆盖项编号")].strip())
        if not m:
            continue
        cell = row[head.index("覆盖它的用例编号")]
        if INFEASIBLE in cell and not re.search(r"TC-\d+", cell):
            out.add(int(m.group(1)))
    return out


def check_case(text, rep, tms, datas, envs):
    """测试用例规格说明：覆盖项与用例各自的定义处、对应表、引用完整性。"""
    parsed = tables(text)

    # 用例的「输入」「前置条件」栏该写编号指代，所以要指得到定义处
    check_refs(text, rep, CASE_DOC, {"DATA-": datas, "ENV-": envs})

    tcovs = defined(parsed, text, COV_COLS, "TCOV-")
    bad = check_contiguous(sorted(tcovs), "TCOV-")
    if bad:
        rep.err(CASE_DOC, bad)
    elif tcovs:
        rep.ok("覆盖项 TCOV-1 至 TCOV-%d 都有定义处，编号连续" % len(tcovs))
    else:
        rep.warn(CASE_DOC, "没找到覆盖项清单表（表头应含 %s），逐条检查跳过" % "、".join(COV_COLS))

    # 覆盖项清单逐行：可追溯性不能空，指到的模型要存在
    for head, body in pick_all(parsed, COV_COLS):
        for row in body:
            if len(row) < len(COV_COLS):
                rep.err(CASE_DOC, "覆盖项有一行栏数不够：%s" % " | ".join(row))
                continue
            trace = row[head.index("可追溯性")]
            if not trace:
                rep.err(CASE_DOC, "覆盖项 %s 的「可追溯性」是空的" % row[0])
                continue
            if tms is not None:
                for n in re.findall(r"TM-(\d+)", trace):
                    if int(n) not in tms:
                        rep.err(CASE_DOC, "覆盖项 %s 追溯到 TM-%s，模型文档里没有这个模型"
                                % (row[0], n))

    # 用例定义处：宽表首格、加粗标签、标题，三种版面都认
    case_tables = pick_all(parsed, CASE_COLS)
    if not case_tables:
        rep.warn(CASE_DOC, "没找到用例表（表头应含 %s），用例定义处只按标题与加粗标签认"
                  % "、".join(CASE_COLS))
    wrong = sorted({head[0] for head, _ in case_tables if head[0] != "唯一标识符"})
    if wrong:
        # 一份文档里常有好几张用例表（按风险分组），同一条错误只报一次
        rep.err(CASE_DOC, "用例表首栏写的是「%s」，模板第四节这一栏叫「唯一标识符」"
                % "、".join(wrong))
    for head, body in pick_all(parsed, COV_COLS):
        check_name_col(head, body, rep, CASE_DOC, "覆盖项清单")
    for head, body in case_tables:
        check_name_col(head, body, rep, CASE_DOC, "用例表")
    # 用例表里那三栏逐行不能空。空着一格是静默的：读的人当它是「没写」，
    # 落成的人当它是「随便」，一条用例到落成那一步就散了。
    blanks = []
    for head, body in case_tables:
        for row in body:
            if len(row) < len(head):
                rep.err(CASE_DOC, "用例表有一行栏数不够：%s" % " | ".join(row))
                continue
            for col in CASE_COLS:
                if not row[head.index(col)]:
                    blanks.append((row[0], col))
    for name, col in sorted(blanks):
        rep.err(CASE_DOC, "用例 %s 的「%s」栏是空的——模板第四节里这三栏逐条都要写"
                % (name, col))
    tcs = defined(parsed, text, CASE_COLS, "TC-")
    bad = check_contiguous(sorted(tcs), "TC-")
    if bad:
        rep.err(CASE_DOC, bad)
    elif tcs:
        rep.ok("用例 TC-1 至 TC-%d 都有定义处，编号连续" % len(tcs))

    # 「判据落在哪一层」那一栏：栏在不在、取值对不对。取值写错是静默的——落成那一步
    # 才发现判据落错了地方，那时候通用稿已经定了稿。栏整个不在时只提示：更早的版本上
    # 没有这一栏，那时候写下的产出不该因此多出一条错。
    layers = case_layers(parsed)
    if any(LAYER_COL in head for head, _ in case_tables):
        wrong = {n: v for n, v in layers.items() if not v.startswith(LAYERS)}
        for n in sorted(wrong):
            rep.err(CASE_DOC, "用例 TC-%d 的「%s」栏取值不在给定的两个里：%s"
                              "——只能是 %s" % (n, LAYER_COL, wrong[n],
                                            "、".join(LAYERS)))
        blank = sorted(n for n, v in layers.items() if not v)
        for n in blank:
            rep.err(CASE_DOC, "用例 TC-%d 的「%s」栏是空的" % (n, LAYER_COL))
        if not wrong and not blank:
            rep.ok("「%s」栏 %d 条用例都填了，取值都在给定的两个里"
                   % (LAYER_COL, len(layers)))
    elif case_tables:
        rep.warn(CASE_DOC, "用例表里没有「%s」这一栏（模板第四节要这一栏）——"
                           "这一栏决定用例落成什么形式；产出是在更早的版本上写的就"
                           "照旧，新写的补上" % LAYER_COL)

    # 对应表
    head, body = pick(parsed, MAP_COLS)
    if head is None:
        rep.err(CASE_DOC, "末尾没有「覆盖项 ↔ 用例」对应表（表头应为：%s）" % " | ".join(MAP_COLS))
        return
    listed, empty, covered_ids = set(), [], set()
    infeasible = infeasible_covs(text)
    for row in body:
        if len(row) < len(MAP_COLS):
            rep.err(CASE_DOC, "对应表有一行栏数不够：%s" % " | ".join(row))
            continue
        m = re.fullmatch(r"TCOV-(\d+)", row[head.index("覆盖项编号")])
        if not m:
            rep.err(CASE_DOC, "对应表的覆盖项编号对不上格式：%s" % row[0])
            continue
        n = int(m.group(1))
        listed.add(n)
        if not row[head.index("覆盖项描述")]:
            rep.err(CASE_DOC, "TCOV-%d 那行的「覆盖项描述」是空的" % n)
        covered = row[head.index("覆盖它的用例编号")]
        if not covered:
            empty.append(n)
            continue
        if n in infeasible:
            continue          # 判过不可行了：不欠用例，原因写在「覆盖项描述」栏
        found = re.findall(r"TC-(\d+)", covered)
        if not found:
            # 既没有编号、也没写「不可行」：这一格谁也读不懂——是还欠着用例，还是
            # 判过不可行了？两种「没有用例」写成一个样子，读的人和脚本都分不出来。
            rep.err(CASE_DOC, "TCOV-%d 那行的「覆盖它的用例编号」没有 TC- 编号、也没写「%s」"
                              "——没有用例覆盖只有两种情形：判为不可行、已从分母里剔除的写"
                              "「%s」，还等着补用例的留空" % (n, INFEASIBLE, INFEASIBLE))
            continue
        for x in found:
            if int(x) not in tcs:
                rep.err(CASE_DOC, "TCOV-%d 引用了没有定义处的 TC-%s" % (n, x))
            covered_ids.add(int(x))

    if empty:
        rep.err(CASE_DOC, "对应表留空 %d 行：%s ——留空表示这条覆盖项还没有用例覆盖。"
                          "完成准则要求 100%% 时这里不该有空行，回第 4 步补用例；"
                          "准则更低、或者判为不可行已从分母里剔除的，写「%s」并说明为什么"
                % (len(empty), brief(empty, "TCOV-"), INFEASIBLE))
    for n in sorted(set(tcovs) - listed):
        rep.err(CASE_DOC, "TCOV-%d 没进对应表" % n)
    for n in sorted(listed - set(tcovs)):
        rep.err(CASE_DOC, "对应表里的 TCOV-%d 在覆盖项清单里找不到" % n)
    orphan = sorted(set(tcs) - covered_ids)
    if orphan:
        rep.err(CASE_DOC, "有定义处却没被任何覆盖项引用的用例：%s" % brief(orphan, "TC-"))
    if tcovs and set(tcovs) == listed and not empty and not orphan:
        rep.ok("对应表 %d 行：覆盖项一个不多一个不少、没有留空、没有孤儿用例" % len(body))
    return


def impl_place_block(body):
    """切出第七份某个方案节里的「成品落点」那一块；没有这一块时返回 None。

    切到下一个**同级或更高级**的小标题为止：起手收 `^#{3,}`（四级写的块也认），切尾
    就按那个标题自己的井号数切。写死 `^#{1,3}` 的话四级写的块切不动紧跟其后的
    `#### 1.5 …`，把那一节整段吞进来——它的表会被当成本块的表、它的话会被当成这一块
    里的话。这一块是方案节底下的小节，切到下一个 `##` 会把后面几个方案节一起吞进来，
    所以也不能放宽到顶。
    """
    m = re.search(r"^(#{3,})\s*[^\n]*" + PLACE_HEAD + r"[^\n]*$", body, re.M)
    if not m:
        return None
    rest = body[m.end():]
    nxt = re.search(r"^#{1,%d}\s" % len(m.group(1)), rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def without_notes(text):
    """去掉以「注：」起头的行——那些行是说明，不是文档内容。

    《文档示例.md》开头交代过这一条（「文中凡以「注：」起头的行，都是本文加的说明」），
    它的拆分脚本也照此剔除。自检脚本把说明当正文读会出岔子：第七份「成品落点」那一块
    底下正有这么一条注，讲的就是那四个字该怎么写——「注：成品还没落成就写「还没落成」」。
    留着它，整块就成了「写着还没落成」，一批压根没落成的产出被读成「落了一部分」，
    正向那几条降成提示、退 0，还报一句「编号在两边对得上」。
    """
    return "\n".join(l for l in text.splitlines() if not l.startswith("注："))


def batch_block(text):
    """切出测试规程规格说明里的「各批落到哪」那一块；没有这一块时返回 None。

    与 impl_place_block 一样按标题切到下一节为止，但认的块名与切法各是各的：
    那一个切的是第七份方案节里的「成品落点」，check_landing.py 也在用它，
    两处认的必须是同一块。
    """
    m = re.search(r"^#{2,}\s*[^\n]*" + BATCH_HEAD + r"[^\n]*$", text, re.M)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^##\s", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def coverage_block(text):
    """切出测试用例规格说明里的「覆盖率自检」那一块；没有这一块时返回 None。

    这一块是顶层小节，与别的块并列，所以切到下一个 `^##` 为止——同一份里还有别的
    块要切（见 impl_place_block、batch_block），各自认各自的块名，不并成一个。
    """
    m = re.search(r"^#{2,}\s*[^\n]*" + COVER_HEAD + r"[^\n]*$", text, re.M)
    if not m:
        return None
    rest = text[m.end():]
    nxt = re.search(r"^##\s", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def expand_cover_ids(cell):
    """「覆盖项编号」栏 → ([编号, ...], [认不出的段, ...])。

    一段一段分（顿号、半角与全角逗号都认）：`TCOV-3` 是单个，`TCOV-1～TCOV-4` 是
    范围。范围写反了（起点大于终点）算认不出；长过 `COVER_SPAN_MAX` 的也算——
    那必是笔误，照直展开会把脚本拖死。认不出的段原样带回去由调用方报错——
    这里不静默丢掉，丢掉了 T 就跟着算小。
    """
    nums, bad = [], []
    for part in re.split(r"[、,，]", cell):
        part = part.strip()
        if not part:
            continue
        m = COVER_RANGE.fullmatch(part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > b or b - a + 1 > COVER_SPAN_MAX:
                bad.append(part)
            else:
                nums.extend(range(a, b + 1))
            continue
        m = COVER_ID.fullmatch(part)
        if m:
            nums.append(int(m.group(1)))
            continue
        bad.append(part)
    return nums, bad


def check_case_dirs(head, body, rep, order, names):
    """「各批落到哪」表里落成评测用例的那几行：「用例目录名」栏与执行顺序对得上。

    判哪一行是评测批，看「执行器」栏（文档模板第五节：那一栏里的「控制器」与
    「子代理」都归落成评测用例的那一批）。落成可跑测试的行（执行器是「脚本」）
    这一栏不查；表里一行评测批都没有时不要求有这一栏——缺栏不报错。

    表里没有「执行器」栏时判不出哪几行是评测批，整块跳过，不猜——报一个「查过了」
    反而更坏。但跳过要留一句话：末尾照打「机械项全过」，不吭声的话读的人会以为这
    一栏查过了。所以跳过时走提示通道说一声，不加错。
    """
    if "执行器" not in head:
        rep.warn(PROC_DOC, "「%s」表里没有「执行器」栏，看不出哪几行落成评测用例——"
                           "「%s」这一栏这次没查" % (BATCH_HEAD, CASE_DIR_COL))
        return
    ei, pi = head.index("执行器"), head.index("规程")
    di = head.index(CASE_DIR_COL) if CASE_DIR_COL in head else None
    for row in body:
        val = row[ei] if ei < len(row) else ""
        if not val.startswith(EVAL_EXECUTORS):
            # 取值不在给定的几个里（写错字那种）也查不了，同样留一句话：
            # 「脚本」是正常的不查，别的都得说一声。
            if not val.startswith(EXECUTORS):
                rep.warn(PROC_DOC, "「%s」表里这一行的「执行器」栏是「%s」，不在给定的"
                                   "几个里——这一行的「%s」栏没查"
                        % (BATCH_HEAD, val, CASE_DIR_COL))
            continue
        proc = row[pi] if pi < len(row) else ""
        tps = sorted({int(n) for n in re.findall(r"TP-(\d+)", proc)})
        if len(tps) != 1:
            rep.err(PROC_DOC, "「%s」表里落成评测用例的行要一条规程一行——这一行的"
                              "「规程」栏写的是「%s」。一条规程一行，才看得出这一串"
                              "目录名属于哪条规程" % (BATCH_HEAD, proc))
            continue
        n = tps[0]
        cell = row[di] if di is not None and di < len(row) else ""
        if not cell.strip():
            rep.err(PROC_DOC, "「%s」表里 TP-%d 那一行的「%s」栏是空的——落成评测用例的"
                              "行要按执行顺序把该规程全部用例的目录名列全，顿号隔开"
                    % (BATCH_HEAD, n, CASE_DIR_COL))
            continue
        before = rep.errors
        want = order.get(n, [])
        seen = []
        for token in [x.strip() for x in re.split(r"[、,，]", cell) if x.strip()]:
            m = CASE_DIR_RE.fullmatch(token)
            if not m:
                rep.err(PROC_DOC, "这条目录名不合形制：%s——应写成 tp<规程号两位>-"
                                  "<规程内执行位次两位>-TC-<用例编号>-<英文名>，如 "
                                  "tp01-01-TC-1-fix_only_what_should_change" % token)
                continue
            tp, pos, tc, en = (int(m.group(1)), int(m.group(2)),
                               int(m.group(3)), m.group(4))
            if tp != n:
                rep.err(PROC_DOC, "这一行的「规程」栏写的是 TP-%d，目录名第一段却是 "
                                  "tp%02d：%s" % (n, tp, token))
            if tc not in names:
                rep.err(PROC_DOC, "目录名里的 TC-%d 在测试用例规格说明里没有定义处：%s"
                        % (tc, token))
            elif not names[tc]:
                rep.err(PROC_DOC, "TC-%d 没有「英文名」栏——目录名最后一段要从那一栏取：%s"
                        % (tc, token))
            elif names[tc] != en:
                rep.err(PROC_DOC, "目录名最后一段与用例表里的英文名对不上：写的是 %s，"
                                  "TC-%d 的英文名是 %s" % (token, tc, names[tc]))
            if tc in want and want.index(tc) + 1 != pos:
                rep.err(PROC_DOC, "目录名里的位次写的是 %02d，TC-%d 在 TP-%d 的"
                                  "「%s」栏里排第 %d：%s"
                        % (pos, tc, n, PROC_ORDER_FIELD, want.index(tc) + 1, token))
            seen.append(tc)
        dup = sorted({x for x in seen if seen.count(x) > 1})
        if dup:
            rep.err(PROC_DOC, "目录名清单里重复了：%s" % brief(dup, "TC-"))
        missing = [x for x in want if x not in seen]
        if missing:
            rep.err(PROC_DOC, "TP-%d 的「%s」栏排了这些用例，目录名清单里少：%s"
                    % (n, PROC_ORDER_FIELD, brief(missing, "TC-")))
        extra = sorted({x for x in seen if x not in want})
        if extra:
            rep.err(PROC_DOC, "目录名清单里多出 TP-%d 没排的用例：%s"
                    % (n, brief(extra, "TC-")))
        if rep.errors == before:
            rep.ok("TP-%d 的目录名清单 %d 条，与「%s」栏逐条对得上"
                   % (n, len(want), PROC_ORDER_FIELD))


def check_batches(text, rep, tps, order, names):
    """「各批落到哪」那一块：在不在；表里列出的规程是不是全部规程。

    只管机械项——分得对不对（判据落在哪、分界有没有劈开一条规程）是判断，
    脚本报不了。这里只保证「每条规程都被表列到」与「表里没有不存在的号」，
    有了这两条，人看那张表时才不至于漏看半套。

    order 与 names 从 proc_cases、case_names 取来，「用例目录名」那一栏靠它们对：
    order 给位次与集合，names 给英文名。
    """
    block = batch_block(text)
    if block is None:
        rep.err(PROC_DOC, "没有「%s」这一块——规程按落点分批，分法与各批落到哪"
                          "写在这里；只落一类也要写，表里一行" % BATCH_HEAD)
        return
    head, body = pick(tables(block), BATCH_COLS)
    if head is None:
        rep.err(PROC_DOC, "「%s」里没有那张表（表头至少要有：%s）"
                % (BATCH_HEAD, " | ".join(BATCH_COLS)))
        return
    if not body:
        rep.err(PROC_DOC, "「%s」表一行都没有——只落一类也要写一行，"
                          "写明全部规程落同一处" % BATCH_HEAD)
        return
    i = head.index("规程")
    listed = set()
    for row in body:
        if len(row) <= i or not row[i]:
            rep.err(PROC_DOC, "「%s」表有一行的「规程」栏是空的：%s"
                    % (BATCH_HEAD, " | ".join(row)))
            continue
        listed |= {int(n) for n in re.findall(r"TP-(\d+)", row[i])}
    missing = sorted(set(tps) - listed)
    if missing:
        rep.err(PROC_DOC, "这些规程没被「%s」那张表列到：%s"
                % (BATCH_HEAD, brief(missing, "TP-")))
    extra = sorted(listed - set(tps))
    if extra:
        rep.err(PROC_DOC, "「%s」那张表里列了不存在的规程：%s"
                % (BATCH_HEAD, brief(extra, "TP-")))
    if not missing and not extra:
        rep.ok("「%s」那张表把 %d 条规程都列到了" % (BATCH_HEAD, len(tps)))
    check_case_dirs(head, body, rep, order, names)


def check_place(body, rep, where):
    """第七份某个方案节里的「成品落点」那一块：在不在、表齐不齐。

    只管机械项——成品路径读不读得到、编号在成品里出没出现，归 check_landing.py。
    这一块落成之后才填得全，所以写成「还没落成」也算填了；分几批落成时两种写法并存
    （模板第十节）：列出来的那些行照旧逐行查，那句话交代剩下还没落的几处。
    """
    block = impl_place_block(body)
    if block is None:
        rep.err(IMPL_DOC, "%s 里没有「%s」这一块——这一批落了哪几号、成品落在哪个"
                          "路径，写在这一块里" % (where, PLACE_HEAD))
        return
    # 说明行先摘掉（见 without_notes）：「注：成品还没落成就写「还没落成」」这样一条
    # 讲写法的说明，会被下面几处 `NOT_YET in block` 读成「这一批还没落成」——表没写、
    # 一格没有，本该报的错都变成了「落成之后回来补上」。
    block = without_notes(block)
    # 那四个字得是这一块里的一句话，不能占「成品」那一栏：占了一栏，落成对照就把
    # 那一格当成一个成品路径去读，读不到退 2、只打一句「成品一份都没读到」——那句
    # 话指不到这儿来。在这一步拦住，报的话里写清该写成什么样。只认「成品」栏，
    # 与 place_paths 认的是同一格。这一段排在最前，与「这一块里有没有表」无关：
    # 落了一部分时两种写法并存，那句话在、表也在，占格子的那种错照样要拦。
    for head, rows in tables(block):
        if not all(c in head for c in PLACE_COLS):
            continue
        i = head.index(PLACE_COLS[0])
        bad = [row[i] for row in rows if len(row) > i and NOT_YET in row[i]]
        if bad:
            rep.err(IMPL_DOC, "%s 的「%s」表「%s」栏里写着「%s」——这四个字是那一块里"
                              "的一句话，不占表里的一格；这一栏写的是成品路径"
                    % (where, PLACE_HEAD, PLACE_COLS[0], NOT_YET))
            return
    head, rows = pick(tables(block), PLACE_COLS)
    if head is None:
        if NOT_YET in block:
            rep.ok("%s 的「%s」写着「%s」——落成之后回来把表填上，再跑一遍落成对照"
                   % (where, PLACE_HEAD, NOT_YET))
            return
        rep.err(IMPL_DOC, "%s 的「%s」里没有那张表（表头应为：%s）；成品还没落成的话，"
                          "那一块写「%s」"
                % (where, PLACE_HEAD, " | ".join(PLACE_COLS), NOT_YET))
        return
    if not rows:
        if NOT_YET in block:
            rep.ok("%s 的「%s」写着「%s」，一条都还没落成——落成之后回来把表填上，"
                   "再跑一遍落成对照" % (where, PLACE_HEAD, NOT_YET))
            return
        rep.err(IMPL_DOC, "%s 的「%s」表一行都没有——一份成品也要有一行；还没落成就写"
                          "「%s」" % (where, PLACE_HEAD, NOT_YET))
        return
    broken = 0
    for row in rows:
        if len(row) < len(PLACE_COLS) or not all(row[:len(PLACE_COLS)]):
            rep.err(IMPL_DOC, "%s 的「%s」表有一行有空栏：%s"
                    % (where, PLACE_HEAD, " | ".join(row)))
            broken += 1
    if not broken:
        if NOT_YET in block:
            rep.ok("%s 的成品落点表 %d 行；这一块里还写着「%s」——剩下那几处落成之后"
                   "回来补上" % (where, len(rows), NOT_YET))
        else:
            rep.ok("%s 的成品落点表 %d 行" % (where, len(rows)))


def check_coverage(text, rep):
    """「覆盖率自检」那一块：在不在、表齐不齐、数对不对得上。

    核的是机械项——T 等于那一栏列出来的条数、N 等于这些编号在对应表里非空的条数、
    覆盖率栏的算式算得对、引的编号都有定义处。T 该是几（那要拿各技术的算式核模型，
    模型是自由格式）、完成准则要求抄得对不对（那是散文），脚本核不了。
    """
    block = coverage_block(text)
    if block is None:
        rep.err(CASE_DOC, "没有「%s」这一块——第 6 步算出来的覆盖率连同 N、T 写在这一块里"
                % COVER_HEAD)
        return
    head, body = pick(tables(block), COVER_COLS)
    if head is None:
        rep.err(CASE_DOC, "「%s」里没有那张表（表头应为：%s）"
                % (COVER_HEAD, " | ".join(COVER_COLS)))
        return
    if not body:
        rep.err(CASE_DOC, "「%s」表一行都没有——一门选定的技术一行" % COVER_HEAD)
        return

    defined_cov = defined(tables(text), text, COV_COLS, "TCOV-")
    # 按表头名取栏，与 check_case 同一套。按位次取（row[0]、row[2]）的话，对应表
    # 前面多一栏——比如加一列「序号」——就会读错栏，报出「只有 0 条非空」这种假错。
    map_head, map_body = pick(tables(text), MAP_COLS)
    covered = {}
    for row in map_body or []:
        if not row or not map_head or len(row) < len(map_head):
            continue
        m = COVER_ID.fullmatch(row[map_head.index("覆盖项编号")].strip())
        if m:
            # 「已被用例覆盖」认的是编号，不是「这一格有没有字」：判为不可行的那一格
            # 写着「不可行」，有字，但它一条用例也没覆盖。
            covered[int(m.group(1))] = bool(
                re.search(r"TC-\d+", row[map_head.index("覆盖它的用例编号")]))

    listed, bad_rows = set(), 0
    for row in body:
        cells = list(row) + [""] * (len(COVER_COLS) - len(row))
        tech = cells[0]
        where = "「%s」表里%s那一行" % (COVER_HEAD, ("%s" % tech) if tech else "有一行")
        if not all(cells[:len(COVER_COLS)]):
            rep.err(CASE_DOC, "%s有空栏——六栏都要填" % where)
            bad_rows += 1
            continue
        nums, bad = expand_cover_ids(cells[1])
        if bad:
            rep.err(CASE_DOC, "%s的「覆盖项编号」栏认不出这几段：%s"
                              "（写成 TCOV-3 或 TCOV-1～TCOV-4；范围别写反、"
                              "一段别超过 %d 条）" % (where, "、".join(bad), COVER_SPAN_MAX))
            bad_rows += 1
            continue
        if not nums:
            rep.err(CASE_DOC, "%s的「覆盖项编号」栏一个编号都没有" % where)
            bad_rows += 1
            continue
        listed.update(nums)
        unknown = [n for n in nums if n not in defined_cov]
        if unknown:
            rep.err(CASE_DOC, "%s引的编号在覆盖项清单里没有定义处：%s"
                    % (where, brief(unknown, "TCOV-")))
            bad_rows += 1
            continue
        m = COVER_CELL.fullmatch(cells[4].replace(" ", ""))
        if not m:
            rep.err(CASE_DOC, "%s的「覆盖率」栏写成「%s」——照 N÷T＝xx.x%% 写"
                    % (where, cells[4]))
            bad_rows += 1
            continue
        t_raw, n_raw = cells[2], cells[3]
        # 用 isdecimal 不用 isdigit：`'²'.isdigit()` 是 True 而 `int('²')` 会抛，
        # 上标、圈号这类数字字符（从别处粘过来常带）会把整份报告打废。
        if not t_raw.isdecimal() or int(t_raw) != len(nums):
            rep.err(CASE_DOC, "%s的「覆盖项总数 T」写的是 %s，这一栏列了 %d 条覆盖项"
                    % (where, t_raw, len(nums)))
            bad_rows += 1
            continue
        if not n_raw.isdecimal() or int(n_raw) > int(t_raw):
            rep.err(CASE_DOC, "%s的「已被用例覆盖 N」写的是 %s，T 是 %s"
                    % (where, n_raw, t_raw))
            bad_rows += 1
            continue
        if (int(m.group(1)), int(m.group(2))) != (int(n_raw), int(t_raw)):
            rep.err(CASE_DOC, "%s的覆盖率栏写的是 %s÷%s，与 T、N 两栏（%s÷%s）对不上"
                    % (where, m.group(1), m.group(2), n_raw, t_raw))
            bad_rows += 1
            continue
        want = round(int(n_raw) * 100.0 / int(t_raw), 1)
        if abs(float(m.group(3)) - want) > 1e-9:
            rep.err(CASE_DOC, "%s的覆盖率写成 %s%%，按 %s÷%s 算应是 %s%%"
                    % (where, m.group(3), n_raw, t_raw, "%g" % want))
            bad_rows += 1
            continue
        real = sum(1 for n in nums if covered.get(n))
        if real != int(n_raw):
            rep.err(CASE_DOC, "%s写的是 %s 条已被用例覆盖，对应表里这些编号只有 %d 条非空"
                    % (where, n_raw, real))
            bad_rows += 1

    if bad_rows:
        # 有行报了错就先不报「这些编号没进任何一行」：那几行的编号可能压根没解析
        # 出来，报出去是假话——编号明明写在那一行里，读的人会照着去补重复的行。
        # 行里那些错改完，这一句自然就对了。
        return
    rep.ok("覆盖率自检 %d 行" % len(body))
    left = sorted(n for n in defined_cov if n not in listed)
    if left:
        rep.warn(CASE_DOC, "覆盖项清单里有 %d 条没进「%s」的任何一行：%s"
                          "（判为不可行、已剔除的不列，那是正常的；不是不可行就该列上）"
                 % (len(left), COVER_HEAD, brief(left, "TCOV-")))


# 规程排用例的那一栏。加粗字段与两列表行两种写法都收（范本用的是后者）。
PROC_ORDER_FIELD = "有序执行测试用例"
ORDER_BOLD = re.compile(r"^\*\*" + PROC_ORDER_FIELD + r"\*\*[：:]\s*(.*?)\s*$", re.M)
ORDER_ROW = re.compile(r"^\|\s*" + PROC_ORDER_FIELD + r"\s*\|\s*([^|]*?)\s*\|\s*$", re.M)


def proc_cases(text):
    """测试规程规格说明：每条规程排了哪些用例。返回 (order, mentioned, bad_head)。

    - `order`：{规程号: [用例号，按「有序执行测试用例」栏里的先后]}。位次按这一栏
      数，不按编号大小——按前置与后置条件排出来的次序与编号序本来就可以不一样。
    - `mentioned`：所有规程块里出现过的用例号，含「启动」「停止与结束」那几栏里
      顺带提到的。「每条用例都被某条规程排到」那条检查用它，判法照旧。
    - `bad_head`：标题没以编号起头、但标题里带着编号的那几块（「一、TP-1 主干」
      这种）。这时「一条也没排到」是这个格式问题造成的，得说准是哪一处。

    一条规程从它的标题到下一个标题算一块。标题必须以编号起头：认错了标题，块就切错，
    用例会算到别的规程头上。

    check_proc 与 issue_ids.py 的 --case-dirs 都用这一份：两边各写一份，迟早一边
    认得出、一边认不出。
    """
    order, mentioned, bad_head = {}, set(), []
    for block in re.split(r"^#{1,6}\s+", text, flags=re.M)[1:]:
        first = block.splitlines()[0].strip() if block.strip() else ""
        m = re.match(r"TP-(\d+)", first)
        if not m:
            if re.search(r"TP-\d+", first):
                bad_head.append(first)
            continue
        mentioned |= {int(n) for n in re.findall(r"TC-(\d+)", block)}
        found = ORDER_BOLD.findall(block) + ORDER_ROW.findall(block)
        order[int(m.group(1))] = [int(n) for n in
                                  re.findall(r"TC-(\d+)", found[0] if found else "")]
    return order, mentioned, bad_head


def check_proc(text, rep, tcs, datas, envs, names, layers=None):
    """测试规程规格说明：规程编号连续；栏齐；用例排得进去也排得全。

    names：从测试用例规格说明里取的 {用例号: 英文名}，转给 check_batches 对
    「用例目录名」那一栏的最后一段。
    layers：从同一份取来的 {用例号: 「判据落在哪一层」栏的值}，用来与「执行器」
    栏对——两栏分处两份文档，却是同一件事的两面，见 EXECUTOR_LAYER 那一段。
    """
    parsed = tables(text)

    # 规程的「启动」栏该写编号指代，所以要指得到定义处
    check_refs(text, rep, PROC_DOC, {"DATA-": datas, "ENV-": envs})
    tps = defined(parsed, text, [], "TP-")
    bad = check_contiguous(sorted(tps), "TP-")
    if bad:
        rep.err(PROC_DOC, bad)
    else:
        rep.ok("规程 TP-1 至 TP-%d 都有定义处，编号连续" % len(tps))

    fields = ["唯一标识符", "英文名", "目标", "启动", "有序执行测试用例",
              "与其他规程的关系", "停止与结束"]
    missing = [f for f in fields if ("**%s**" % f) not in text and ("| %s |" % f) not in text]
    if missing:
        rep.err(PROC_DOC, "规程缺栏目：%s" % "、".join(missing))

    # 规程自己的英文名，与上面那个 names 参数（用例的英文名）不是一回事，名字错开
    proc_names = name_fields(text)
    if proc_names and len(proc_names) != len(tps):
        rep.err(PROC_DOC, "%d 条规程，英文名写了 %d 个——每条规程都要有一个"
                % (len(tps), len(proc_names)))
    for value in proc_names:
        check_name(value, rep, PROC_DOC, "规程")

    executors = None
    for label, allowed in (("执行器", EXECUTORS), ("改动文件", CHANGES)):
        values = field_values(text, label)
        if len(values) != len(tps):
            rep.err(PROC_DOC, "%d 条规程，「%s」栏写了 %d 个——每条规程都要有这一栏"
                    % (len(tps), label, len(values)))
            continue
        surplus = [v for v in values if not v.startswith(allowed)]
        for value in surplus:
            rep.err(PROC_DOC, "「%s」栏的取值不在给定的几个里：%s——只能是 %s"
                    % (label, value, "、".join(allowed)))
        if not surplus:
            rep.ok("「%s」栏 %d 条规程都填了" % (label, len(values)))
            if label == "执行器":
                executors = values

    for n in sorted({int(m) for m in re.findall(r"TC-(\d+)", text)}):
        if n not in tcs:
            rep.err(PROC_DOC, "引用了没有定义处的 TC-%d" % n)

    if not tps:
        return
    # 切块这件事只留一份实现（proc_cases）：issue_ids.py 的 --case-dirs 也数同一栏，
    # 两边各写一份，迟早一边认得出、一边认不出。
    order, scheduled, bad_head = proc_cases(text)
    check_batches(text, rep, set(tps), order, names)

    # 「执行器」栏与用例那一栏「判据落在哪一层」对不对得上（见 EXECUTOR_LAYER）。
    # 两栏分处两份文档，说的却是同一件事的两面，而分批正是按这两栏分的：错了会把
    # 一条要读过程的用例落成一段跑命令的代码。
    #
    # 只查一个方向：脚本跑的规程，排的用例一条都不许是「要读执行过程」——脚本读不回
    # 「它跑起来一路做了什么」。反过来不查：控制器排的用例里混着「落在输出上」是常事
    # （一条用例被两条规程各排一次，两条的执行器可以不一样），且按分批的规矩，
    # 控制器与子代理本来就整条归评测用例那一批。
    if layers and executors:
        for tp, value in zip(sorted(tps), executors):
            if not value.startswith("脚本"):
                continue
            off = [tc for tc in order.get(tp, [])
                   if layers.get(tc) and not layers[tc].startswith("落在输出上")]
            if off:
                rep.err(PROC_DOC, "TP-%d 的「执行器」是「脚本」，它排的这几条用例"
                                  "「%s」栏写的却是「要读执行过程」：%s——脚本读不回"
                                  "「它跑起来一路做了什么」，这样的判据它判不了；"
                                  "要么把执行器改成控制器或子代理，要么把判据落到"
                                  "命令、退出码与盘上的文件上"
                        % (tp, LAYER_COL, brief(off, "TC-")))

    if bad_head:
        rep.err(PROC_DOC, "这些规程的标题没以编号起头，认不出规程的边界：%s"
                          "——标题写成「TP-N 目标」的样子（编号紧跟 # 之后，前头不加序号）"
                % "、".join("「%s」" % s for s in bad_head))
    if not scheduled:
        if not bad_head:
            rep.err(PROC_DOC, "每条规程都没排出用例（「有序执行测试用例」那栏是空的？）")
        return
    un = sorted(set(tcs) - scheduled)
    if un:
        rep.err(PROC_DOC, "这些用例没被任何一条规程排进去：%s" % brief(un, "TC-"))
    else:
        rep.ok("全部 %d 条用例都被规程排到了" % len(tcs))


def check_flat(text, rep, name, cols, prefix, used=None):
    """测试数据需求 / 测试环境需求：栏写死，编号连续且与行数对得上。

    used：用例与规程里出现过的编号集合。给了就顺带报孤儿；给 None 表示不判
    ——两份引用文档缺一份时，缺的那份已经有硬错误，这里再刷一屏提示没有用。
    """
    parsed = tables(text)
    nums = defined(parsed, text, cols, prefix)
    bad = check_contiguous(sorted(nums), prefix)
    if bad:
        rep.err(name, bad)
    else:
        rep.ok("%s1 至 %s%d 都有定义处，编号连续" % (prefix, prefix, len(nums)))

    if used is not None:
        idle = sorted(set(nums) - used)
        if idle:
            rep.warn(name, "这些编号定义了，但用例与规程里都没引用：%s"
                           "——确认是故意不引，还是漏了" % brief(idle, prefix))

    head, body = pick(parsed, cols)
    if head is None:
        rep.err(name, "没找到表头为「%s」的表" % " | ".join(cols))
        return
    # 「英文名」是模板给这两份加的栏（模板第二、六、七节），决策依据那份不走这里
    if NAME_COL not in head:
        rep.err(name, "缺栏目：%s" % NAME_COL)
    want = [c for c in cols + [NAME_COL] if c in head]
    extra = [c for c in head if c not in cols + [NAME_COL]]
    if extra:
        rep.err(name, "多出模板没有的栏：%s" % "、".join(extra))
    if len(body) != len(nums):
        rep.err(name, "表里 %d 行，编号有 %d 个，对不上" % (len(body), len(nums)))
    # 逐格按表头取，不按下标硬切：加了一栏之后位置全往后挪，按位置切会看错格子
    for row in body:
        if [c for c in want if head.index(c) >= len(row)]:
            rep.err(name, "有一行栏数不够：%s" % " | ".join(row))
            continue
        if [c for c in want if not row[head.index(c)]]:
            rep.err(name, "有一行有空栏：%s" % " | ".join(row))
    if NAME_COL in head:
        i = head.index(NAME_COL)
        for row in body:
            if len(row) > i:
                check_name(row[i], rep, name, row[0] if row else "?")


def sections(text):
    """按 `##` 标题切块，返回 [(标题, 正文), ...]。

    第一个标题之前的那一段，标题写 None。决策依据分两块写，两块各自的表要分开放、
    分开看，所以先按标题切开。
    """
    parts = re.split(r"^(##\s+[^\n]*)$", text, flags=re.M)
    out = [(None, parts[0])]
    for i in range(1, len(parts) - 1, 2):
        out.append((parts[i].strip(), parts[i + 1]))
    return out


def check_decision_blocks(text, rep):
    """两块分得对不对：用户拍板的单独在前一块，其余在后一块。

    分块是机械项——「依据的来源」栏只填 `技能定的`、`从测试项推的`、`用户给的` 之一，
    哪一行该归哪一块判得了。分开的意义在用处上：用户要能一眼看到自己拍板的那几条、
    随手改；混在一起，他就得逐行翻「依据的来源」栏才找得出来。
    """
    for title, body in sections(text):
        for head, rows in tables(body):
            if not all(c in head for c in DEC_COLS):
                continue
            i = head.index("依据的来源")
            src = [(r[0], r[i]) for r in rows if len(r) > i]
            if title is None or not (USER_HEAD in title or MODEL_HEAD in title):
                where = ("标题「%s」底下" % title) if title else "开头没有标题的那一段里"
                rep.err(DECISION_DOC, "%s有一张决策表，不在「%s」「%s」这两块里——"
                                      "这份分两块写：你拍板的那几条放「%s」，其余放「%s」"
                        % (where, USER_HEAD, MODEL_HEAD, USER_HEAD, MODEL_HEAD))
                continue
            if USER_HEAD in title:
                bad = ["%s（依据的来源写着「%s」）" % (dec, s) for dec, s in src
                       if s != USER_SRC]
                if bad:
                    rep.err(DECISION_DOC, "「%s」那一块只装「%s」那几条，这里混进了"
                                          "别的来源：%s"
                            % (USER_HEAD, USER_SRC, "、".join(bad)))
            else:
                bad = [dec for dec, s in src if s == USER_SRC]
                if bad:
                    rep.err(DECISION_DOC, "%s 的依据是「%s」，却写在「%s」那一块里——"
                                          "这几条要单独放在「%s」那一块，好让你一眼看到、"
                                          "随手就改"
                            % ("、".join(bad), USER_SRC, MODEL_HEAD, USER_HEAD))


def check_decision(text, rep):
    """决策依据文档：分两块写，一条决策一行，编号连续、栏目齐、不留空。

    这份文档编号只增不改，所以编号必须是 1 起连号。中间缺号、或者最大的号比行数大，
    都说明有旧条目被删掉或被改写过，单列出来报。
    """
    parsed = tables(text)
    nums = defined(parsed, text, DEC_COLS, "DEC-")
    bad = check_contiguous(sorted(nums), "DEC-")
    if bad:
        rep.err(DECISION_DOC, bad + "——这份只增不改，旧条目不该被删或被改写")
        return
    rep.ok("决策 DEC-1 至 DEC-%d 都有定义处，编号连续" % len(nums))

    blocks = pick_all(parsed, DEC_COLS)
    if not blocks:
        rep.err(DECISION_DOC, "没找到表头为「%s」的表" % " | ".join(DEC_COLS))
        return
    # 分成两块之后，一张表里只装一部分号，行数要按所有表合起来数
    rows = 0
    for head, body in blocks:
        extra = [c for c in head if c not in DEC_COLS]
        if extra:
            rep.err(DECISION_DOC, "多出模板没有的栏：%s" % "、".join(extra))
        rows += len(body)
        for row in body:
            if len(row) < len(DEC_COLS):
                rep.err(DECISION_DOC, "有一行栏数不够：%s" % " | ".join(row))
            elif not all(row[:len(DEC_COLS)]):
                rep.err(DECISION_DOC, "有一行有空栏：%s" % " | ".join(row))
    if rows != len(nums):
        rep.err(DECISION_DOC, "表里 %d 行，编号有 %d 个，对不上" % (rows, len(nums)))

    check_decision_blocks(text, rep)


def words_for(name, banned, scheme):
    """这一份要查哪些词。

    三处不一样：
    - 具体环境名不查 Decision Basis.md——那一份记的是过程，写了「当时定的是本机
      Windows」是照实记，不是违规；
    - 方案名与配置文件名六份全查，记过程也不例外；
    - LEAKED 那六个词（技能里的出处）照旧六份都查。第七份不走这一条路，它另查
      （见 check_impl）：方案名在那一份里正该出现。
    """
    out = list(banned)
    out += [w for w in scheme if w not in ENV_WORDS]
    if name != DECISION_DOC:
        out += [w for w in scheme if w in ENV_WORDS]
    return out + LEAKED


def check_words(texts, rep, banned, scheme):
    hits = {}
    for name, text in texts.items():
        for w in words_for(name, banned, scheme):
            if w in text:
                hits.setdefault(name, []).append(w)
    if not hits:
        rep.ok("六份文档没有禁用词，也没带技能的节号与出处")
        return
    for name, words in hits.items():
        rep.err(name, "出现不该出现的词：%s" % "、".join(sorted(set(words))))


def impl_scheme_sections(text):
    """切出 `## …、方案：…` 那些节，返回 [(标题, 正文), ...]。"""
    return [(h, b) for h, b in sections(text)
            if h and h.startswith("##") and IMPL_SCHEME_MARK in h]


def impl_block_heads(body):
    """取方案节里的小标题，先跳掉围栏里的内容。

    围栏里的一行 `### 甲` 是配置或注释，不是标题。不跳掉它，它会顶替掉真正的那一块
    ——两块按每个词第一次出现的位置排，落在围栏里的那个词就排错了队。
    """
    stripped = re.sub(r"^[ \t]*```.*?^[ \t]*```[ \t]*$", "", body, flags=re.S | re.M)
    return re.findall(r"^#{3,6}\s+(.+)$", stripped, re.M)


def check_impl(text, rep, ids):
    """实施方案规格说明（第七份，按需产出）：骨架、四块、编号对账、出处。

    这一份**不定义任何编号**，只引用前六份的，所以在 DOCS 之外单查一组。对账**六类
    都查**（模板第十节的对账表六类都收），每类两个方向：这一份里写的编号都要指得到
    通用稿里的定义处；通用稿里定义过的每一条，在这一份里都要查得到一个落点——用不上
    的要写一行说明为什么。

    对账表按方案各一张，**在方案节里面查**：表在节外面时，第二套方案起来就没处放。

    `ids` 是 {前缀: {号}}，六个前缀各定义过哪几号，由 main 从六份文档算好传进来。
    """
    # 导语：第一个 `##` 之前要有非标题、非空的行
    lead = [l for l in re.split(r"^## ", text, maxsplit=1, flags=re.M)[0].splitlines()
            if l.strip() and not l.startswith("#")]
    if not lead:
        rep.err(IMPL_DOC, "开头没有导语——先说清这一份是干什么的、与六份通用稿冲突时以谁为准")

    schemes = impl_scheme_sections(text)
    if not schemes:
        rep.err(IMPL_DOC, "没有一个「%s」节——方案按节分，将来比别的方案在同一份里"
                          "再起一节" % IMPL_SCHEME_MARK)
    for head, body in schemes:
        name = head.strip("# ").strip()
        subs = impl_block_heads(body)
        at = [next((i for i, s in enumerate(subs) if w in s), None) for w in IMPL_BLOCKS]
        # 「成品落点」缺了不进这张名单：check_place 单报一条，话更具体（说清这一块该
        # 写什么、成品路径写在哪儿）。两处都报，同一个问题占两条错误，错误数就虚了。
        missing = [w for w, i in zip(IMPL_BLOCKS, at) if i is None and w != PLACE_HEAD]
        # 算次序时把没找到的那几块摘掉：None 与数字比大小会报 TypeError。
        order = [i for i in at if i is not None]
        if missing:
            rep.err(IMPL_DOC, "%s 里缺这几块：%s" % (name, "、".join(missing)))
        elif order != sorted(order):
            rep.err(IMPL_DOC, "%s 里四块的次序不对——要照「%s」这个先后排（按每个词"
                              "第一次出现的小标题算）：现在 %s"
                    % (name, "」→「".join(IMPL_BLOCKS),
                       "、".join("%s 在第 %d 个" % (w, i + 1)
                                 for w, i in zip(IMPL_BLOCKS, at) if i is not None)))
        elif None not in at:
            # 「成品落点」缺了时不打这句：四块并不都在，那句通过语就成了假话。
            rep.ok("%s 里四块都在，次序也对" % name)
        else:
            rep.ok("%s 里四块都在，次序也对" % name)

        maps = pick_all(tables(body), IMPL_MAP_COLS)
        if not maps:
            rep.err(IMPL_DOC, "%s 里没有「%s」那张表（表头要含「%s」）——对账表按方案"
                              "各一张，放在方案节里"
                    % (name, IMPL_MAP_HEAD, " | ".join(IMPL_MAP_COLS)))
        else:
            rep.ok("%s 里的「%s」表在，%d 行"
                   % (name, IMPL_MAP_HEAD, sum(len(b) for _, b in maps)))

        check_place(body, rep, name)

    # 「成品落点」那一块不算落点：它记的是成品落在哪，行里顺带列到几个编号是常事，
    # 拿它当「这一号给了落点」，一套方案没在对账表里排到的编号就会一直不吭声。与
    # main 里算 DATA-/ENV- 有没有人用时摘掉那一块，是同一个道理。
    #
    # 只摘给「没给落点」那一个方向用；反方向（引了没有定义处的编号）照全文算：那一行
    # 是人手写的，写一个不存在的号（用例只到 TC-12、这里写了 TC-19）照样得报出来。
    bare = text
    for _, body in schemes:
        block = impl_place_block(body)
        if block:
            bare = bare.replace(block, "")

    dangling = []
    for prefix, label in IMPL_CLASSES:
        known = ids.get(prefix, set())
        if not known:
            continue
        quoted = {int(n) for n in re.findall(prefix + r"(\d+)", text)}
        bad = sorted(quoted - known)
        if bad:
            dangling.append("引了没有定义处的%s：%s" % (label, brief(bad, prefix)))
        used = {int(n) for n in re.findall(prefix + r"(\d+)", bare)}
        lost = sorted(known - used)
        if lost:
            dangling.append("通用稿里定义了、这一份里没给落点：%s——用不上的要写一行"
                            "说明为什么" % brief(lost, prefix))
    if dangling:
        for d in dangling:
            rep.err(IMPL_DOC, d)
    else:
        rep.ok("编号两个方向都对得上，六类都查过：这一份引的都指得到定义处，"
               "通用稿定义的都给了落点")

    hits = [w for w in LEAKED if w in text]
    if hits:
        rep.err(IMPL_DOC, "出现不该出现的词：%s" % "、".join(sorted(set(hits))))


def check_sections(texts, rep):
    """模板说测试用例规格说明分四块写。多出来的顶层小节只提示不判错——
    多一段算不算「多造」是人的判断，脚本不替人定。
    """
    heads = re.findall(r"^##\s+(.+)$", texts.get(CASE_DOC, ""), re.M)
    known = ("覆盖项", "测试用例", "对应表", COVER_HEAD)
    extra = [h for h in heads if not any(k in h for k in known)]
    if extra:
        rep.warn(CASE_DOC, "有模板四块之外的顶层小节：%s"
                           "（模板说这份分四块写；多出来的算不算多造，自己定）" % "、".join(extra))


def prefer_utf8(stream):
    """这一路输出被重定向走时，改成按 UTF-8 吐字节；真控制台不动。

    和 `issue_ids.py` 里那份是同一份逻辑——改就两处一起改，改岔了只会在其中一条
    路上出乱码。`check_landing.py` 用的是这一份，不用另改。Windows 中文版上标准流接的是管道时，Python 取的是区域
    编码 cp936：中文落成 GBK 字节，而接住它的一方（Claude Code 的任务窗口、编辑器
    里的输出面板）一律按 UTF-8 解，屏幕上就是「���」——自检的结论成了乱码，等于
    没报。真控制台不切：那里的编码是 Python 按终端挑好的，换掉反而会花屏。

    流不认得 reconfigure（比如测试里的 StringIO）就放过，不是报错。
    """
    if stream.isatty():
        return
    if (getattr(stream, "encoding", "") or "").lower().replace("-", "") == "utf8":
        return
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def print_rules():
    """把这份脚本会拒绝什么打出来——判据按它检查时用的同一份来源现取。

    这张清单是给写产出的人看的：想确认「哪些词不许写、认哪些节标题、认哪几栏、哪些
    取值写死了」，跑这一条就行，不必去读这份一千多行的脚本。**同一份来源**是要紧的
    ——两张词表现解析（与检查时调的是同一个函数），标题、栏位与取值直接引下面那些
    常量；表改了或常量改了，这里跟着变，不会打出一份与检查时对不上的说法。

    判断性的东西不在这里打：模型建得对不对、覆盖项取全没有、用例导得够不够，那是给
    人看的，脚本本来就不管。
    """
    banned = banned_words()
    scheme = scheme_words()
    if len(banned) < 5 or len(scheme) < SCHEME_WORDS_MIN:
        print("没能从 SKILL.md 的两张词表解析出禁用词（只拿到 %d 个与 %d 个）。"
              % (len(banned), len(scheme)))
        print("多半是那两张表的写法变了，去 %s 看一眼。" % SKILL_MD)
        return 2
    env = [w for w in scheme if w in ENV_WORDS]
    rest = [w for w in scheme if w not in ENV_WORDS]

    print("check_docs.py 会拒绝什么——下面是它检查时用的同一份来源，不必读它的源码。\n")

    print("【查哪几份】")
    print("  六份通用稿，缺一份报错：")
    for name in DOCS:
        print("    " + name)
    print("  第七份按需产出：产出目录里有 %s 才查它，没有整组跳过。\n" % IMPL_DOC)

    print("【禁用词】两张表都从 SKILL.md 现解析——改表就是改判据")
    print("  一、「必须照写的几个词」表右列，六份里出现即报错，%d 个：" % len(banned))
    print("     " + "、".join(banned))
    print("  二、「六份里不许出现的东西」表左列，分两档：")
    print("     六份全查，%d 个：%s" % (len(rest), "、".join(rest)))
    print("     除 %s 外查五份，%d 个：%s（那一份记的是过程，照实写环境名不算违规）"
          % (DECISION_DOC, len(env), "、".join(env)))
    print("  三、技能点名不许带出产出的，%d 个：%s\n" % (len(LEAKED), "、".join(LEAKED)))

    print("【认哪几栏】定义处 = 编号打头的那一行、加粗的 **唯一标识符**、或章节标题；")
    print("           只在正文里提一句不算定义。下面这些栏是脚本点名要有的")
    print("           （表里还可以有别的栏，比如编号、英文名、前置条件）：")
    for label, cols in [
        ("覆盖项", COV_COLS),
        ("用例", CASE_COLS),
        ("数据项", DATA_COLS),
        ("环境项", ENV_COLS),
        ("决策", DEC_COLS),
        ("模型的「依据 → 模型」表", TRACE_COLS),
        ("覆盖项 ↔ 用例对应表", MAP_COLS),
        ("覆盖率自检", COVER_COLS),
        ("各批落到哪", BATCH_COLS),
        ("第七份的对账表", IMPL_MAP_COLS),
        ("第七份方案节末尾的成品落点", PLACE_COLS),
    ]:
        print("  %s：%s" % (label, " | ".join(cols)))
    print("  测试模型、测试规程不写成宽表，所以没有固定栏：模型用加粗字段，规程写在两列表里。\n")

    print("【认哪些节标题】块是按标题认的：标题里没有这几个词，那一块就等于没写")
    print("  %s 分四块，顶层小节标题里要含：覆盖项、测试用例、对应表、%s"
          % (CASE_DOC, COVER_HEAD))
    print("    （四块之外的顶层小节只提示、不判错）")
    print("  %s 的方案节里另有一块：%s——栏：%s"
          % (IMPL_DOC, PLACE_HEAD, " | ".join(PLACE_COLS)))
    print("  %s 末尾另起一节：%s——栏：%s" % (PROC_DOC, BATCH_HEAD, " | ".join(BATCH_COLS)))
    print("    这一节里落成评测用例的行（「执行器」栏是 %s）另要一栏：%s"
          % ("、".join(EVAL_EXECUTORS), CASE_DIR_COL))
    print("  %s 分两块：%s | %s" % (DECISION_DOC, USER_HEAD, MODEL_HEAD))
    print("  模型的加粗字段、规程的两列表左栏：唯一标识符、%s、%s"
          % (NAME_COL, PROC_ORDER_FIELD))
    print("  第七份：每个方案一节，标题里含「%s」；每节四块，按这个先后排：%s"
          % (IMPL_SCHEME_MARK, "、".join(IMPL_BLOCKS)))
    print("    「%s」那张对账表在方案节里面（每套方案各一张）；六类都收：%s——两个"
          "方向都查（引的编号要指得到定义处，通用稿定义过的都要给落点）\n"
          % (IMPL_MAP_HEAD, "、".join(p for p, _ in IMPL_CLASSES)))

    print("【写死的取值与形制】")
    print("  「执行器」栏：%s——后面可以带一句括号说明" % " / ".join(EXECUTORS))
    print("  「改动文件」栏：%s" % " / ".join(CHANGES))
    print("  用例表的 %s 三栏逐行都要写：哪一格空着都报错——空着是静默的，读的人当它"
          "「没写」，落成的人当它「随便」" % " / ".join(CASE_COLS))
    print("  对应表的「%s」栏：有两种「没有用例」——判为不可行、已从分母里剔除的写「%s」，"
          "还等着补用例的留空（留空报错，因为它欠着）；既没编号也没写「%s」的报错，"
          "那一格读不出是两种里的哪一种" % (MAP_COLS[2], INFEASIBLE, INFEASIBLE))
    print("  「%s」栏：%s——栏在就逐条查取值；栏整个不在时只提示（更早的版本上没有"
          "这一栏）。「执行器」是「脚本」的规程排的用例一条都不许是「%s」"
          % (LAYER_COL, " / ".join(LAYERS), LAYERS[1]))
    print("  「英文名」栏：%s（小写字母起头，只含小写字母、数字、下划线；不许拿编号起头）"
          "；六类条目都要有这一栏，决策除外" % NAME_RE.pattern)
    print("  「用例目录名」栏：%s" % CASE_DIR_RE.pattern)
    print("  决策依据分两块：「%s」（可以直接改）与「%s」（只增不改）；「依据的来源」栏"
          "填「%s」的那几条归前一块" % (USER_HEAD, MODEL_HEAD, USER_SRC))
    print("  「成品落点」那一块：成品还没落成就写一句「%s」——是那一块里的一句话，"
          "不占表里的一格，也不许整块不写\n" % NOT_YET)

    print("【退出码】0 全过；1 有错；2 用法不对或读不到文件。")
    print("【其余判据】编号怎么编、各栏怎么填、各块什么次序：references/文档模板.md")
    print("【这里不管】模型建得对不对、覆盖项取全没有、用例导得够不够——那是人看的。")
    return 0


def main():
    # 在解析参数之前：用法写错、读不到目录时那几句提示也是中文
    prefer_utf8(sys.stdout)
    prefer_utf8(sys.stderr)
    if len(sys.argv) == 2 and sys.argv[1] == "--rules":
        return print_rules()
    if len(sys.argv) != 2:
        print("用法：python check_docs.py <产出目录>")
        print("      python check_docs.py --rules     把判据打出来（不用产出目录）")
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print("读不到目录：%s" % root)
        return 2

    banned = banned_words()
    if len(banned) < 5:
        print("没能从 SKILL.md 的「必须照写的几个词」表解析出禁用词（只拿到 %d 个）。" % len(banned))
        print("多半是那张表的写法变了，去 %s 看一眼。" % SKILL_MD)
        return 2

    scheme = scheme_words()
    if len(scheme) < SCHEME_WORDS_MIN:
        print("没能从 SKILL.md 的「六份里不许出现的东西」表解析出禁用词（只拿到 %d 个）。" % len(scheme))
        print("多半是那张表的写法变了，去 %s 看一眼。" % SKILL_MD)
        return 2

    rep = Report()
    print("检查目录：%s\n" % root)

    texts, missing = {}, []
    for name in DOCS:
        p = root / name
        if p.is_file():
            texts[name] = p.read_text(encoding="utf-8")
        else:
            missing.append(name)
    for name in missing:
        rep.err(name, "缺这份文档")
    if not texts:
        print("\n六份文档一份都没读到，先确认目录对不对。")
        return 1

    # 第七份按需产出。产出目录里没有它时整组跳过——连提示都不报（见 IMPL_DOC 那段）。
    impl_path = root / IMPL_DOC
    impl_text = impl_path.read_text(encoding="utf-8") if impl_path.is_file() else None

    # 用例与规程要跨文档查引用，所以定义处先都算出来，再逐份检查
    tcs = defined(tables(texts.get(CASE_DOC, "")), texts.get(CASE_DOC, ""), CASE_COLS, "TC-")
    tc_names = case_names(tables(texts.get(CASE_DOC, "")))
    tc_layers = case_layers(tables(texts.get(CASE_DOC, "")))
    tcovs = set(defined(tables(texts.get(CASE_DOC, "")), texts.get(CASE_DOC, ""),
                        COV_COLS, "TCOV-"))
    datas = set(defined(tables(texts.get(DATA_DOC, "")), texts.get(DATA_DOC, ""),
                        DATA_COLS, "DATA-"))
    envs = set(defined(tables(texts.get(ENV_DOC, "")), texts.get(ENV_DOC, ""),
                       ENV_COLS, "ENV-"))
    tps = set(defined(tables(texts.get(PROC_DOC, "")), texts.get(PROC_DOC, ""), [], "TP-"))

    tms = None
    if MODEL_DOC in texts:
        print("[%s]" % MODEL_DOC)
        tms = check_model(texts[MODEL_DOC], rep)

    if CASE_DOC in texts:
        print("\n[%s]" % CASE_DOC)
        check_case(texts[CASE_DOC], rep, tms, datas, envs)
        check_coverage(texts[CASE_DOC], rep)
        check_sections(texts, rep)

    if PROC_DOC in texts:
        print("\n[%s]" % PROC_DOC)
        check_proc(texts[PROC_DOC], rep, set(tcs), datas, envs, tc_names, tc_layers)

    # 数据项与环境项有没有人用——两份引用文档都在才判。
    used_data = used_env = None
    if CASE_DOC in texts and PROC_DOC in texts:
        case_text = texts[CASE_DOC]
        used_data = referenced(case_text, "DATA-") | referenced(texts[PROC_DOC], "DATA-")
        used_env = referenced(case_text, "ENV-") | referenced(texts[PROC_DOC], "ENV-")

    if DATA_DOC in texts:
        print("\n[%s]" % DATA_DOC)
        check_flat(texts[DATA_DOC], rep, DATA_DOC, DATA_COLS, "DATA-", used_data)
    if ENV_DOC in texts:
        print("\n[%s]" % ENV_DOC)
        check_flat(texts[ENV_DOC], rep, ENV_DOC, ENV_COLS, "ENV-", used_env)

    if DECISION_DOC in texts:
        print("\n[%s]" % DECISION_DOC)
        check_decision(texts[DECISION_DOC], rep)

    if impl_text is not None:
        print("\n[%s]" % IMPL_DOC)
        check_impl(impl_text, rep, {
            "TM-": set(tms or ()), "TCOV-": tcovs, "TC-": set(tcs),
            "TP-": tps, "DATA-": datas, "ENV-": envs,
        })

    print("\n[禁用词与出处]")
    check_words(texts, rep, banned, scheme)

    print("\n共 %d 处错误，%d 处提示。" % (rep.errors, rep.warns))
    if rep.errors == 0:
        print("机械项全过。判断性的东西（模型建得对不对、覆盖项取全没有）还得自己看。")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
