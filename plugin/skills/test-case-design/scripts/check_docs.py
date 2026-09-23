#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 test-case-design 产出的五份规格说明是否符合技能定下的契约。

用法：

    python check_docs.py <产出目录>

退出码：0 全过；1 有错；2 用法不对或读不到文件。

管的都是机械项：编号连不连续、栏目齐不齐、引用指不指得到、对应表有没有留空、
禁用词有没有漏进来。判断性的东西（模型建得对不对、覆盖项取全没有、用例导得够不够、
引的编号对不对得上内容）不在这里管——那是人看的，脚本报不了。

两条方向相反的引用检查：用例与规程里引了不存在的数据项或环境项，算错误（悬空）；
测试数据需求与测试环境需求里定义了、却没有任何用例与规程引用的编号，算提示（孤儿）
——某条数据或某项环境可能确实没有哪条用例直接引它。

契约不在这份脚本里另立一套，来源是技能自己的两份文件：

  - `references/文档模板.md`：五份文档的栏目、编号方案、两张对应表的格式
  - `SKILL.md` 的「必须照写的几个词」表：禁用词

那份表改了，这里跟着变，不用两边各改一遍。

一条要紧的区分：**「提到过」不等于「定义过」**。对应表里引用了某条用例，不等于那条用例
真写出来了。所以每个对象都单独认「定义处」——章节标题、加粗的**唯一标识符**、或表里
以该编号打头的那一行；只在正文里被提及的，不算定义。
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_MD = HERE.parent / "SKILL.md"

# 五份产出的文件名。产出都用英文文件名，正文是中文——脚本读的只是文件名，
# 栏目、编号、禁用词那几项照旧按中文认。
MODEL_DOC = "Test Model Specification.md"
CASE_DOC = "Test Case Specification.md"
PROC_DOC = "Test Procedure Specification.md"
DATA_DOC = "Test Data Requirements.md"
ENV_DOC = "Test Environment Requirements.md"
DOCS = [MODEL_DOC, CASE_DOC, PROC_DOC, DATA_DOC, ENV_DOC]

# 文档模板第六、七节：这两份的栏是写死的，正好几栏就是几栏
DATA_COLS = ["唯一标识符", "描述", "重置需求"]
ENV_COLS = ["唯一标识符", "测试环境项", "描述"]
# 文档模板第八节的两张对应表
TRACE_COLS = ["依据的出处", "模型编号", "说明"]
MAP_COLS = ["覆盖项编号", "覆盖项描述", "覆盖它的用例编号"]
# 文档模板第四节：覆盖项清单四栏
COV_COLS = ["唯一标识符", "描述", "优先级", "可追溯性"]
# 用例那几栏里必查的三栏。前置条件可以全篇统一说明一次，可追溯性由对应表承接，
# 优先级是「需要时写」——按模板这三栏都不必逐条出现，故不列。
CASE_COLS = ["目标", "输入", "预期结果"]

# SKILL.md 里「产出文档里只写测试内容，不把技能文件里的节号与出处带出去」点名的东西。
# 禁用词表本身从 SKILL.md 解析，不在这里再抄一份。
LEAKED = ["references/", "GB/T", "TD1", "TD2", "TD3", "TD4"]

# 这几个从「容易写成」一栏里解析出来，但不能按字面禁：
#   「测试用例」「测试数据」本身是技能要求的术语（测试用例规格说明、测试数据需求）；
#   「统写成「要」」是一条行文纪律，不是一个词。
NOT_BANNED = {"测试用例", "测试数据", "统写成「要」"}


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
        rows = [[c.strip() for c in r.strip("|").split("|")] for r in block]
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

    fields = ["唯一标识符", "目标", "优先级", "测试策略摘要", "测试模型"]
    missing = [f for f in fields if ("**%s**" % f) not in text and ("| %s |" % f) not in text]
    if missing:
        rep.err(MODEL_DOC, "模型缺栏目：%s" % "、".join(missing))

    head, body = pick(parsed, TRACE_COLS)
    if head is None:
        rep.err(MODEL_DOC, "末尾没有「依据 → 模型」对应表（表头应为：%s）" % " | ".join(TRACE_COLS))
        return set(tms)

    listed = set()
    for row in body:
        if len(row) < len(TRACE_COLS):
            rep.err(MODEL_DOC, "对应表有一行栏数不够：%s" % " | ".join(row))
            continue
        n = re.search(r"TM-(\d+)", row[head.index("模型编号")])
        if n:
            listed.add(int(n.group(1)))
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
    tcs = defined(parsed, text, CASE_COLS, "TC-")
    bad = check_contiguous(sorted(tcs), "TC-")
    if bad:
        rep.err(CASE_DOC, bad)
    elif tcs:
        rep.ok("用例 TC-1 至 TC-%d 都有定义处，编号连续" % len(tcs))

    # 对应表
    head, body = pick(parsed, MAP_COLS)
    if head is None:
        rep.err(CASE_DOC, "末尾没有「覆盖项 ↔ 用例」对应表（表头应为：%s）" % " | ".join(MAP_COLS))
        return
    listed, empty, covered_ids = set(), [], set()
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
        for x in re.findall(r"TC-(\d+)", covered):
            if int(x) not in tcs:
                rep.err(CASE_DOC, "TCOV-%d 引用了没有定义处的 TC-%s" % (n, x))
            covered_ids.add(int(x))

    if empty:
        rep.err(CASE_DOC, "对应表留空 %d 行：%s ——留空表示这条覆盖项没有用例覆盖。"
                          "完成准则要求 100%% 时这里不该有空行；准则更低时也要写明为什么留着"
                % (len(empty), brief(empty, "TCOV-")))
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


def check_proc(text, rep, tcs, datas, envs):
    """测试规程规格说明：规程编号连续；栏齐；用例排得进去也排得全。"""
    parsed = tables(text)

    # 规程的「启动」栏该写编号指代，所以要指得到定义处
    check_refs(text, rep, PROC_DOC, {"DATA-": datas, "ENV-": envs})
    tps = defined(parsed, text, [], "TP-")
    bad = check_contiguous(sorted(tps), "TP-")
    if bad:
        rep.err(PROC_DOC, bad)
    else:
        rep.ok("规程 TP-1 至 TP-%d 都有定义处，编号连续" % len(tps))

    fields = ["唯一标识符", "目标", "启动", "有序执行测试用例", "与其他规程的关系", "停止与结束"]
    missing = [f for f in fields if ("**%s**" % f) not in text and ("| %s |" % f) not in text]
    if missing:
        rep.err(PROC_DOC, "规程缺栏目：%s" % "、".join(missing))

    for n in sorted({int(m) for m in re.findall(r"TC-(\d+)", text)}):
        if n not in tcs:
            rep.err(PROC_DOC, "引用了没有定义处的 TC-%d" % n)

    if not tps:
        return
    # 一条规程从它的标题到下一个标题算一块，块里出现过的用例就是这条规程排进去的
    scheduled = set()
    for block in re.split(r"^#{1,6}\s+", text, flags=re.M)[1:]:
        first = block.splitlines()[0] if block.strip() else ""
        if not re.match(r"TP-\d+", first.strip()):
            continue
        scheduled |= {int(m) for m in re.findall(r"TC-(\d+)", block)}
    if not scheduled:
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
    extra = [c for c in head if c not in cols]
    if extra:
        rep.err(name, "多出模板没有的栏：%s" % "、".join(extra))
    if len(body) != len(nums):
        rep.err(name, "表里 %d 行，编号有 %d 个，对不上" % (len(body), len(nums)))
    for row in body:
        if len(row) < len(cols):
            rep.err(name, "有一行栏数不够：%s" % " | ".join(row))
        elif not all(row[:len(cols)]):
            rep.err(name, "有一行有空栏：%s" % " | ".join(row))


def check_words(texts, rep, banned):
    hits = {}
    for name, text in texts.items():
        for w in banned + LEAKED:
            if w in text:
                hits.setdefault(name, []).append(w)
    if not hits:
        rep.ok("五份文档没有禁用词，也没带技能的节号与出处")
        return
    for name, words in hits.items():
        rep.err(name, "出现不该出现的词：%s" % "、".join(sorted(set(words))))


def check_sections(texts, rep):
    """模板说测试用例规格说明分三块写。多出来的顶层小节只提示不判错——
    多一段算不算「多造」是人的判断，脚本不替人定。"""
    heads = re.findall(r"^##\s+(.+)$", texts.get(CASE_DOC, ""), re.M)
    known = ("覆盖项", "测试用例", "对应表")
    extra = [h for h in heads if not any(k in h for k in known)]
    if extra:
        rep.warn(CASE_DOC, "有模板三块之外的顶层小节：%s"
                           "（模板说这份分三块写；多出来的算不算多造，自己定）" % "、".join(extra))


def main():
    if len(sys.argv) != 2:
        print("用法：python check_docs.py <产出目录>")
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
        print("\n五份文档一份都没读到，先确认目录对不对。")
        return 1

    # 用例与规程要跨文档查引用，所以定义处先都算出来，再逐份检查
    tcs = defined(tables(texts.get(CASE_DOC, "")), texts.get(CASE_DOC, ""), CASE_COLS, "TC-")
    datas = set(defined(tables(texts.get(DATA_DOC, "")), texts.get(DATA_DOC, ""),
                        DATA_COLS, "DATA-"))
    envs = set(defined(tables(texts.get(ENV_DOC, "")), texts.get(ENV_DOC, ""),
                       ENV_COLS, "ENV-"))

    tms = None
    if MODEL_DOC in texts:
        print("[%s]" % MODEL_DOC)
        tms = check_model(texts[MODEL_DOC], rep)

    if CASE_DOC in texts:
        print("\n[%s]" % CASE_DOC)
        check_case(texts[CASE_DOC], rep, tms, datas, envs)
        check_sections(texts, rep)

    if PROC_DOC in texts:
        print("\n[%s]" % PROC_DOC)
        check_proc(texts[PROC_DOC], rep, set(tcs), datas, envs)

    # 数据项与环境项有没有人用——两份引用文档都在才判
    used_data = used_env = None
    if CASE_DOC in texts and PROC_DOC in texts:
        used_data = referenced(texts[CASE_DOC], "DATA-") | referenced(texts[PROC_DOC], "DATA-")
        used_env = referenced(texts[CASE_DOC], "ENV-") | referenced(texts[PROC_DOC], "ENV-")

    if DATA_DOC in texts:
        print("\n[%s]" % DATA_DOC)
        check_flat(texts[DATA_DOC], rep, DATA_DOC, DATA_COLS, "DATA-", used_data)
    if ENV_DOC in texts:
        print("\n[%s]" % ENV_DOC)
        check_flat(texts[ENV_DOC], rep, ENV_DOC, ENV_COLS, "ENV-", used_env)

    print("\n[禁用词与出处]")
    check_words(texts, rep, banned)

    print("\n共 %d 处错误，%d 处提示。" % (rep.errors, rep.warns))
    if rep.errors == 0:
        print("机械项全过。判断性的东西（模型建得对不对、覆盖项取全没有）还得自己看。")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
