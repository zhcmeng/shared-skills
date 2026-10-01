#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核对产出文档里的编号，与成品（落下来的测试代码、评测用例）里的编号对不对得上。

用法：

    python check_landing.py <产出目录> <成品目录> [<成品目录> ...]

不给成品路径时，从测试用例规格说明的「成品落点」表里取（那种情况按跑命令时的当前目录
解路径）。成品路径给目录就整个目录走一遍，给文件就只看那一份。

退出码：0 全过；1 有错；2 用法不对或读不到产出目录；3 产出里写着「还没落成」，
没有可对照的成品——那不是错，是这一批还没落成，调用方跳过就行。3 与 2 分开，是为了
让调用方不用读这份脚本就知道遇上的是哪一种：2 是自己用错了，3 是本来就没得对。

**分几批落成时照查。**那一块里既列了已经落成的表、又写着「还没落成」交代剩下的几处
（模板第四节），这一遍按「部分落成」查：路径照样读、两向对照照样跑，只有「定义了却
没在成品里出现」那一条降成提示——还没落的那几处本来就查不到，报成错只会逼人把表
一次填全，那就没有分批了。已经落成的那一处漏了，提示里说得出是它。

两条方向相反的检查，外加一条引用检查：

  - 产出里定义过的条目，在成品里都要找得到——**这是这一条要管的主要毛病**：文档里
    写了 TM-6、TCOV-47、ENV-12，成品里一处也没提，两边就各说各的，拿编号搜不过去。
    六类都查；决策（DEC-）不查这一条，它只在成品与产出有出入时才写，见下。判为不可行、
    已从分母里剔除的覆盖项也不查——它们不会有用例，本来就不落。
  - 成品里出现的编号，在产出里都要有定义处——引了一个不存在的号，读的人会以为漏看了
    哪一份文档，其实是那个号写错了。七类都查，含 DEC-。
  - 引第七份（实施方案规格说明）的小节号，要指得到——`见 2.1 第 4 小节第 3 条` 这种话
    在成品与产出里都有，第七份一重编小节号，它们就整片指错地方；指错了不报，读的人
    照着号翻过去，翻到的是另一条，还看不出来翻错了。第七份自己里面还有「第 4 小节
    第 3 条」这种不带节号的写法，只在那里面查得到，见 scan_refs。

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


def read_impl(root):
    """读产出目录里的第七份（实施方案规格说明）；没产出就返回空串。

    它按需产出，不在那六份里，所以 check_docs.DOCS 里也没有它。
    """
    path = root / check_docs.IMPL_DOC
    return path.read_text(encoding="utf-8") if path.is_file() else ""


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

    返回 (路径列表, 说明, 是不是「还没落成」, 是不是落了一部分)。表没见着、只写了
    「还没落成」，或者把这四个字写进了「成品」栏（该写成那一块里的一句话），路径
    列表都为空，说明里写清是哪一种。第三个元素单独回一个标志，因为「还没落成」与
    另外两种「没拿到路径」不是一回事：它的退出码不一样（3 对 2，见 main）——调用方
    只看码就该知道该跳过还是该报错，不必去认说明那句话。

    第四个元素管的是分几批落成（模板第四节）：已经落成的列成表、那句话交代还没落的
    那几处，这时路径拿得到、账也该查，只是「定义了却没在成品里出现」那一条要降成
    提示——还没落的那几处本来就查不到，报成错只会逼人把表一次填全，那就没有分批了。

    表里的路径按当前目录解——与命令行给路径时一样。
    """
    doc = texts.get(check_docs.CASE_DOC, "")
    block = check_docs.place_block(doc)
    if block is None:
        return [], "测试用例规格说明里没有「%s」这一块，也没在命令行上给成品路径" % check_docs.PLACE_HEAD, False, False

    paths = []
    for head, body in check_docs.tables(block):
        if not all(c in head for c in PLACE_COLS):
            continue
        i = head.index(PLACE_COLS[0])
        for row in body:
            if len(row) > i and row[i]:
                cell = row[i].strip("`").strip()
                # 「还没落成」被写进「成品」栏了：它是那一块里的一句话，不占格子
                # （模板第四节）。当成路径去读只会得到一句「成品一份都没读到」，
                # 那句话指不到病根，写的人只能去翻这份脚本才知道错在哪儿；这儿认
                # 出来，照「还没落成」那一种报。check_docs 也拦这一种，但这份脚本
                # 单跑时也得说得出话。
                if NOT_YET in cell:
                    return [], "成品落点表上写着「%s」" % NOT_YET, True, False
                paths.append(cell)
    if paths:
        return paths, "", False, NOT_YET in block
    if NOT_YET in block:
        return [], "成品落点表上写着「%s」" % NOT_YET, True, False
    return [], "「成品落点」那一块里没有成品落点表", False, False


def scan(paths, root):
    """把成品读成一段文本。返回 (正文, 读到的份数, 跳过没读的说明, 读不到的路径, 排掉几份产出)。

    产出目录里那几份文档不算成品——六份通用稿，加上按需产出的第七份（实施方案规格
    说明）。不排掉的话，把产出目录整个当成品路径传进来，文档里什么编号都有，检查就
    白过了——那种「全过」比报错还会骗人。第七份尤其要排：它的对账表按契约要求把通用稿
    里定义过的每一条编号都列一次，成品里没有的编号它也有。而按契约，成品就摆在产出
    目录的上一级，传评测材料根是常事。

    **名字以 `.` 开头的目录不往下走**：上一层住着 `.git`、虚拟环境（`.venv`、
    `.clean-venv` 这类）与各种缓存，一个都不是成品，走一遍既慢又可能读进一堆环境
    自己带的编号。想读哪一个就把它写全在命令行上（那样按文件收，不看这一条）。
    """
    parts, n, skipped, missing, dropped = [], 0, [], [], 0
    docs = {(root / name).resolve()
            for name in list(check_docs.DOCS) + [check_docs.IMPL_DOC]}
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            missing.append(raw)
            continue
        files = [p] if p.is_file() else sorted(
            f for f in p.rglob("*")
            if f.is_file()
            and not any(seg.startswith(".") for seg in f.relative_to(p).parts))
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


def check_forward(blob, ids, rep, partial=False, infeasible=()):
    """六类：定义了、成品里却一个也没出现的编号。

    `partial` 是分几批落成、这一块里还写着「还没落成」（见 place_paths）：这一条降成
    提示——还没落的那几处本来就查不到，报成错只会逼人把表一次填全，那就没有分批了。
    已经落成的那几处要是也落在这儿，就是真漏了，提示里说清这一点。

    `infeasible` 是判为不可行、已从分母里剔除的覆盖项编号（check_docs.infeasible_covs）：
    它们不会有用例，成品里本来就不该出现，不查这一条。
    """
    for label, prefix, _ in CLASSES:
        nums = set(ids.get(prefix, set()))
        if prefix == "TCOV-":
            nums -= set(infeasible)
        if not nums:
            continue
        seen = {int(m) for m in id_pattern(prefix).findall(blob)}
        miss = sorted(set(nums) - seen)
        if miss:
            head = "这些条目定义了，成品里一处也没出现：%s" % check_docs.brief(miss, prefix)
            if partial:
                rep.warn(label, head + "——这一块里还写着「%s」，还没落成的那几处不算错；"
                                       "已经落成的那几处要是也在这儿，那就是漏了"
                         % NOT_YET)
            else:
                rep.err(label, head + "——编号在成品里照抄（`TC-30` 写成 `TC_30`），"
                                      "一条至少出现一次")
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


# 第七份（实施方案规格说明）的结构，就认这三种写法：`### 2.1 说明` 是小节，它底下
# `**1. …**` 是「第 N 小节」、`**第 3 条：…**` 是第 N 小节里的第 M 条。别的一概不认——
# 认宽了，就分不清哪一行是标题、哪一行是正好长成那样的正文，`2.1 第 4 小节` 指到哪儿
# 又得猜，而这一条检查要防的正是「猜」。
SEC_XY = re.compile(r"^###\s+(\d+\.\d+)\s*(.*?)\s*$")
SUB_N = re.compile(r"^\*\*(\d+)\.\s*(.+?)\*\*")
ITEM_N = re.compile(r"^\*\*第\s*(\d+)\s*条：\s*(.+?)\*\*")
# 引用：`2.1 第 4 小节第 3 条`、`2.1 第 4 小节`；条号可以不带。不带节号那种见 scan_refs。
REF_FULL = re.compile(r"(\d+\.\d+)\s*第\s*(\d+)\s*小节(?:\s*第\s*(\d+)\s*条)?")
REF_BARE = re.compile(r"第\s*(\d+)\s*小节(?:\s*第\s*(\d+)\s*条)?")

NO_IMPL = "产出目录里没有第七份（`%s`），这个号指不到东西" % check_docs.IMPL_DOC


def parse_impl_sections(impl):
    """读出第七份各小节与条，返回 {小节号: {"title":…, "subs": {小节号: 标题}, "items": {小节号: {条号: 标题}}}}。

    小节与条都只在某一节的底下才认，所以是先记下当前落在哪一节、哪一小节，再往上挂。
    """
    out, xy, sub = {}, None, None
    for line in impl.splitlines():
        m = SEC_XY.match(line)
        if m:
            xy, sub = m.group(1), None
            out.setdefault(xy, {"title": m.group(2), "subs": {}, "items": {}})
            continue
        if line.startswith("##"):
            xy, sub = None, None      # 出了这一节，后面再写小节号就得自己带上节号了
            continue
        if xy is None:
            continue
        m = SUB_N.match(line)
        if m:
            sub = int(m.group(1))
            out[xy]["subs"][sub] = m.group(2)
            continue
        m = ITEM_N.match(line)
        if m:
            out[xy]["items"].setdefault(sub, {})[int(m.group(1))] = m.group(2)
    return out


def scan_refs(text, with_bare=False):
    """扫一段文本里引第七份小节号的地方，返回 [(原文, 节号, 小节号, 条号或 None)]。

    带节号的写法哪儿都认。不带节号的只有在 `with_bare` 时才认，而且得落在某个
    `### 2.1` 底下才知道说的是哪一节——认不出是哪一节的，节号记成 None，调用那边
    跳过不查（只写「第 4 小节」指不到哪一份，本来也不该那么写）。

    先找带节号的、把它们从这行里划掉再找不带节号的：`2.1 第 4 小节第 3 条` 里也含着
    一段「第 4 小节第 3 条」，不划掉会被当成两处引用数进去。
    """
    out, xy = [], None
    for line in text.splitlines():
        m = SEC_XY.match(line)
        if m:
            xy = m.group(1)
            continue
        if line.startswith("##"):
            xy = None
            continue
        for m in REF_FULL.finditer(line):
            out.append((m.group(0), m.group(1), int(m.group(2)),
                        int(m.group(3)) if m.group(3) else None))
        if with_bare:
            for m in REF_BARE.finditer(REF_FULL.sub("", line)):
                out.append((m.group(0), xy, int(m.group(1)),
                            int(m.group(2)) if m.group(2) else None))
    return out


def span(nums):
    """一串号写成「第 1 至第 5」；断了就一个个列出来。"""
    nums = sorted(nums)
    if len(nums) > 1 and nums == list(range(nums[0], nums[-1] + 1)):
        return "第 %d 至第 %d" % (nums[0], nums[-1])
    return "、".join("第 %d" % n for n in nums)


def resolve_ref(struct, xy, sub_n, item_n):
    """这处引用指得到吗：指得到返回空串，指不到返回一句为什么。"""
    if xy is None:
        return ""
    sec = struct.get(xy)
    if sec is None:
        return "第七份里没有 %s 这一节" % xy
    if not sec["subs"]:
        return "%s（%s）底下没有编号的小节" % (xy, sec["title"])
    if sub_n not in sec["subs"]:
        return "%s 底下只有%s 小节" % (xy, span(sec["subs"]))
    if item_n is None:
        return ""
    items, title = sec["items"].get(sub_n, {}), sec["subs"][sub_n]
    if not items:
        return "%s 第 %d 小节（%s）底下没有编号的条" % (xy, sub_n, title)
    if item_n not in items:
        return "%s 第 %d 小节（%s）底下只有%s 条" % (xy, sub_n, title, span(items))
    return ""


def check_impl_refs(impl, sources, rep):
    """引第七份的小节号，要指得到。

    第七份按需产出，落成之后还会一通重编——整节整条地插、删、挪，小节号跟着全变。
    通用稿与成品里那些「见 2.1 第 4 小节第 3 条」是手抄过去的，重编一轮就得一份份
    跟着改；漏下一处，读的人照着号翻过去，翻到的是另一条，而且看不出来翻错了，比
    指着一处空白还难发现。这一条查的就是这个：指不到就报错。

    `sources` 是 [(哪儿, 正文, 认不认不带节号的写法)]：那六份与成品各一条，
    第七份自己一条（只有它认不带节号那种写法，见 scan_refs）。
    """
    struct = parse_impl_sections(impl)
    bad, total = {}, 0
    for where, text, bare_ok in sources:
        for raw, xy, sub_n, item_n in scan_refs(text, bare_ok):
            total += 1
            why = NO_IMPL if not impl else resolve_ref(struct, xy, sub_n, item_n)
            if why:
                bad.setdefault(where, []).append((raw, why))
    if bad:
        for where, hits in bad.items():
            # 同一条引用出现多次是常事——那句话抄在几条用例配置里，一处指不到就处处
            # 指不到。一次一次列出来只会把屏幕刷满，按引用归并、带上出现几处。
            count = {}
            for raw, why in hits:
                count[(raw, why)] = count.get((raw, why), 0) + 1
            msgs = []
            for (raw, why), n in count.items():
                if n > 1:
                    msgs.append("`%s`（%d 处）指不到——%s" % (raw, n, why))
                else:
                    msgs.append("`%s` 指不到——%s" % (raw, why))
            rep.err(where, "引的第七份小节号 " + "；".join(msgs))
    elif total:
        rep.ok("引的第七份小节号，%d 处都指得到" % total)


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
    impl = read_impl(root)

    # place_paths 一律跑一遍，哪怕命令行上给了成品路径：`partial` 说的是「成品落点」
    # 那一块里还写着「还没落成」——这一批只落了一部分，与路径从哪儿来不是一回事。
    # 模板要求成品写在上一层目录时把成品路径在本命令上一条条点出来，而那正是分批
    # 落成时的常规写法：只看「命令行给没给路径」，这条常规写法就把降级整个绕掉了，
    # 还没落成的那几处照样按错报。
    table_paths, reason, not_yet, partial = place_paths(texts)
    paths = list(sys.argv[2:]) or table_paths
    if not paths:
        print("没拿到成品路径：%s。" % (reason or "命令行上没给，产出里也没写"))
        if not_yet:
            # 这不是错：产出可以先于成品进版本库（技能允许先出六份，落成是后来的事）。
            # 单独给一个退出码，调用方不用读这份脚本就知道该跳过。
            print("这一批的成品还没落成，没有可对照的东西——落成之后回来把那张表填上，再跑一遍。")
            return 3
        print("把成品路径写在命令后面，或者在测试用例规格说明的「成品落点」表里填上——"
              "两份都填了，就不用每次在命令行上抄一遍。")
        return 2

    ids = defined_ids(texts)
    # 判为不可行的覆盖项不会有用例，成品里本来就不该出现，正向对照要把它摘出去——
    # 不摘的话它每一轮都报一条假错，而「这一条为什么不在成品里」产出里已经写清楚了
    # （模板第八节给这一格定的写法：写「不可行」）。只影响正向那一条：反查照旧，
    # 成品里真提到了它，产出里仍有定义处。认法只有一份，见 check_docs。
    infeasible = check_docs.infeasible_covs(texts.get(check_docs.CASE_DOC, ""))
    total = sum(len(v) for prefix, v in ids.items() if prefix != DECISION[1])
    if total == 0:
        print("产出目录里一个条目都认不出来，先确认文档写没写、栏位对不对：%s" % root)
        return 2

    rep = check_docs.Report()
    print("产出目录：%s" % root)
    blob, n, skipped, missing, dropped = scan(paths, root)
    print("成品：读到 %d 份文件，共 %d 个字符\n" % (n, len(blob)))
    if partial:
        print("「成品落点」那一块里还写着「%s」——这一遍按分批落成查：编号在成品里"
              "找不到的只算提示，已经落成的那一处漏了才要改。\n" % NOT_YET)
    if infeasible:
        print("对应表里判为不可行的覆盖项 %d 条（%s）：它们没有用例，本来就不落，"
              "这一遍不查在不在成品里。\n"
              % (len(infeasible), check_docs.brief(sorted(infeasible), "TCOV-")))
    for raw in missing:
        rep.err("成品路径", "读不到：%s" % raw)
    if dropped:
        rep.warn("成品路径", "产出目录里那几份文档没算成品，跳过了 %d 份——"
                             "成品指落下来的代码与评测用例，文档自己不算" % dropped)
    if n == 0:
        print("成品一份都没读到，先确认路径对不对。")
        return 2
    if skipped:
        rep.warn("成品路径", "这些文件没读（二进制，或者不是 UTF-8）：%s"
                             % "、".join(skipped[:5]) + ("…" if len(skipped) > 5 else ""))

    check_forward(blob, ids, rep, partial, infeasible)
    print()
    check_backward(blob, ids, rep)

    print()
    sources = [(name, text, False) for name, text in texts.items()]
    sources.append(("成品", blob, False))
    if impl:
        sources.append((check_docs.IMPL_DOC, impl, True))
    check_impl_refs(impl, sources, rep)

    print("\n共 %d 处错误，%d 处提示。" % (rep.errors, rep.warns))
    if rep.errors == 0:
        print("编号在两边对得上。成品里的测试测得对不对、号标对没标对，还得自己看。")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
