"""纯文本处理：不碰网络、不碰文件、不读 token。

所有能单测的逻辑都集中在这里。
"""
import json
import re
import string
from dataclasses import dataclass

from lxml import html as lxml_html
from tabulate import tabulate

# 表格转 Markdown 时的中间记号。正文里出现这个形状，说明转换漏了东西，
# 宁可报错退出也不能把它落进正文。
_PLACEHOLDER = "\x00T{}\x00"
_PLACEHOLDER_RE = re.compile(r"\x00T\d+\x00")

_TABLE_OPEN = "<table"
_TABLE_CLOSE = "</table>"

# 折大小写时只折 ASCII。`str.lower()` 对 U+0130（İ）这类字符不保长（1 个码位
# 变 2），拿 lower 的下标去切**原文**就会错开。要认的两个标签都是纯 ASCII，
# 所以只折 ASCII 完全等价，而且一对一。
_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


class PlaceholderLeftover(Exception):
    """正文里出现了转换用的中间记号。"""


def _assert_no_placeholder(text):
    m = _PLACEHOLDER_RE.search(text)
    if m:
        raise PlaceholderLeftover(
            f"正文里出现了转换用的中间记号 {m.group(0)!r}，这次转换有东西没还原干净")


def _find_table_spans(text):
    """按出现顺序找出最外层 <table>…</table> 的区间（起、止，止不含）。

    认不出收尾的（没有 </table>）就当它不是表格，原样留着。
    """
    spans = []
    lower = text.translate(_ASCII_LOWER)
    pos = 0
    while True:
        start = lower.find(_TABLE_OPEN, pos)
        if start == -1:
            return spans
        depth = 0
        i = start
        end = -1
        while i < len(lower):
            nxt_open = lower.find(_TABLE_OPEN, i)
            nxt_close = lower.find(_TABLE_CLOSE, i)
            if nxt_close == -1:
                break
            if nxt_open != -1 and nxt_open < nxt_close:
                depth += 1
                i = nxt_open + len(_TABLE_OPEN)
            else:
                depth -= 1
                i = nxt_close + len(_TABLE_CLOSE)
                if depth == 0:
                    end = i
                    break
        if end == -1:
            # 这张认不出收尾，就当它不是表格、原样留着；但不能因此把后面
            # 格式正常的表也一起放弃——从它的开标签之后接着往下扫。
            pos = start + len(_TABLE_OPEN)
            continue
        spans.append((start, end))
        pos = end


def _cell_text(cell):
    """一个格子的文字：把嵌套标签摊平、空白归一、竖线转义。"""
    return " ".join("".join(cell.itertext()).split()).replace("|", "\\|")


# colspan/rowspan 写错、写成 0 或负数时按 1 算；上限只是防一份畸形 HTML
# 用一行 colspan="999999" 把内存撑爆，正常表格远到不了这个数。
_MAX_SPAN = 1000


def _span(cell, name):
    """取 colspan/rowspan 的整数，取不到就按 1 算。"""
    raw = cell.get(name)
    if raw is None:
        return 1
    try:
        value = int(raw.strip())
    except (AttributeError, ValueError):
        return 1
    return max(1, min(value, _MAX_SPAN))


def _table_grid(table):
    """把带 rowspan/colspan 的行展开成等宽的网格。

    合并单元格的文字只放在左上角那一格；被它盖住的格子填空字符串，但仍要
    占位，否则右边的列会往左挤。跨行的占位记在 pending 里，每过一行消耗
    一层——空行也要消耗，不然 rowspan=2 会盖住三行。

    展开后再交给 tabulate：Markdown 的管道表格没有合并单元格的写法，
    只能把合并还原成一格一格的空格子。
    """
    rows = []
    pending = {}       # 列号 → 还会盖住下面几行
    for tr in table.iter("tr"):
        # 只收属于这张表的行；内层表格的行归内层管
        nearest = tr.getparent()
        while nearest is not None and nearest.tag != "table":
            nearest = nearest.getparent()
        if nearest is not table:
            continue

        carried = set(pending)     # 这一行开始时就已被上面盖住的列
        row = []
        col = 0
        for cell in tr.xpath("./td | ./th"):
            while col in carried:
                row.append("")
                col += 1
            colspan = _span(cell, "colspan")
            rowspan = _span(cell, "rowspan")
            row.append(_cell_text(cell))
            row.extend([""] * (colspan - 1))
            if rowspan > 1:
                for c in range(col, col + colspan):
                    pending[c] = max(pending.get(c, 0), rowspan - 1)
            col += colspan

        # 这一行没轮到写出来的跨行占位也要消耗一层
        for c in carried:
            left = pending.get(c, 0) - 1
            if left > 0:
                pending[c] = left
            else:
                pending.pop(c, None)
        rows.append(row)

    width = max((len(row) for row in rows), default=0)
    if not width:
        return None
    return [row + [""] * (width - len(row)) for row in rows]


def _render_table(raw_html):
    """一张表的 HTML → Markdown 表格。认不出来就原样退回。"""
    try:
        doc = lxml_html.fragment_fromstring(raw_html, create_parent="div")
    except Exception:
        return raw_html
    tables = doc.xpath(".//table")
    if not tables:
        return raw_html
    table = tables[0]

    rows = _table_grid(table)
    if not rows:
        return raw_html
    # disable_numparse：格子里的字原样留着。默认会把「看着像数字」的整列右对齐，
    # 还会顺手改写数字的写法；PDF 里抠出来的字不该被这样动过。
    return tabulate(rows, headers="firstrow", tablefmt="pipe",
                    disable_numparse=True)


def convert_tables(text):
    """把正文里的 HTML 表格换成 Markdown 表格，只动 <table>，其余原样。"""
    _assert_no_placeholder(text)
    spans = _find_table_spans(text)
    if not spans:
        return text

    blocks = []
    pieces = []
    prev = 0
    for start, end in spans:
        pieces.append(text[prev:start])
        pieces.append(_PLACEHOLDER.format(len(blocks)))
        blocks.append(_render_table(text[start:end]))
        prev = end
    pieces.append(text[prev:])

    out = "".join(pieces)
    for i, block in enumerate(blocks):
        out = out.replace(_PLACEHOLDER.format(i), block)
    return out


# 只是包裹，本身不携带内容语义：拆掉标签、留下里面的东西
_WRAPPERS = {"div", "span", "center", "html", "body", "p", "font",
             "section", "article", "header", "footer", "main",
             "figure", "figcaption"}

# 本身有意义的标签：原样留着
_KEEP = {"table", "thead", "tbody", "tfoot", "tr", "td", "th",
         "img", "b", "i", "strong", "em", "code", "pre", "sub", "sup",
         "br", "a", "u", "s", "blockquote", "hr", "ul", "ol", "li"}

# 实测到的转换残留：裸的 <image>，没属性、没内容，跟文档内容无关。
# 只删光秃秃的标签——不能写成「不认识又没属性就删」：正文里
# `List<String>`、`x<y>z`、`<name>` 这种形状很常见，<String> 会被当成标签，
# 结果就是静默丢正文，比留着一个看得见的原始标签坏得多。
#
# 残标签按「整对」处理，配对按位置、不按名字：一份正文里可能既有裸 <image>，
# 又有带属性的 <image …></image>，按名字一锅端就会把后者也删掉一半。收尾标签
# 只认它前面那个还没闭合的开标签——开标签是光秃秃的（被删了）就跟着一起删，
# 开标签带属性（被留下了）就一起留；不然正文里会剩半个配不平的标签。
# 以后真见到别的残标签，加在这里。
_STRAY_TAGS = {"image"}

_TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:\s[^<>]*)?)(/?)>")


def strip_wrapper_tags(text):
    """拆掉包裹标签；已知的裸残标签整对去掉。

    三条规则：包裹名单里的拆掉标签留内容；保留名单里的原样不动；
    其余的——名字在残标签名单里的按位置配对，光秃秃的开标签整个去掉，
    跟它配上的那个收尾标签一起走；带属性的开标签不动，配上的收尾标签也留。
    剩下的一律原样留着。
    """
    # 每个残标签名字一个栈，记着还没闭合的开标签是不是光秃秃的。收尾标签只认
    # 栈顶那一个：栈顶是裸开标签（已经删了）就跟着删；栈顶带属性（留着了），
    # 或者压根没有开标签，都留着它——那种收尾标签的另一半带了属性，删了就剩半个。
    stacks = {}
    drop = []  # 要删掉的标签区间，按出现顺序
    for m in _TAG_RE.finditer(text):
        name = m.group(2).lower()
        bare = not m.group(3).strip()
        if name in _WRAPPERS:
            drop.append((m.start(), m.end()))
        elif name in _KEEP:
            continue
        elif name in _STRAY_TAGS:
            stack = stacks.setdefault(name, [])
            if not m.group(1):
                # 开标签：光秃秃的整个去掉；带属性的留着，但照样入栈——
                # 它后面那个收尾标签得知道它的另一半还在。
                stack.append(bare)
                if bare:
                    drop.append((m.start(), m.end()))
            elif stack and stack.pop():
                # 收尾标签，配上的那个开标签是光秃秃的、已经删了：一起走
                drop.append((m.start(), m.end()))
        # 其余的一律原样留着

    if not drop:
        return text
    pieces = []
    prev = 0
    for start, end in drop:
        pieces.append(text[prev:start])
        prev = end
    pieces.append(text[prev:])
    return "".join(pieces)


# 整行就是一个页码的几种写法。只用 ^…$ 卡死整行——页码在页脚是独立的一行，
# 夹在正文里的（「详见第 3 页」）分不出来是页码还是内容，一律不动。
_PAGE_MARKER_RES = (
    re.compile(r"^第\s*\d+\s*页\s*(?:[/，,（(]?\s*共\s*\d+\s*页\s*[)）]?)?$"),
    re.compile(r"^-\s*\d+\s*-$"),
    re.compile(r"^page\s+\d+(?:\s+of\s+\d+)?$", re.I),
)


def strip_page_markers(text):
    """整行就是一个页码标记的，去掉那一行。

    样例那份结果里没见着页码，但规则按「出现了就去掉」写，不按「不会出现」
    假设。收紧到整行匹配是有意的：放宽成「行里出现就删」会把「详见第 3 页」
    这种正文一起吃掉。

    去掉的那行留下一个空行，让前后的段落还是分开的；空行归一是后面
    normalize_blank_lines 的事。
    """
    kept = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and any(r.match(stripped) for r in _PAGE_MARKER_RES):
            kept.append("")
            continue
        kept.append(line)
    return "\n".join(kept)


def normalize_blank_lines(text):
    """行尾空白去掉，连续空行归成一个，首尾空行去掉。"""
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_IMG_TAG_RE = re.compile(r"<img\b[^>]*?\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.I)
_MD_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(\s+\"[^\"]*\")?\)")


def rewrite_image_refs(text, resolve):
    """把认得的图片引用改写成 `![](images/<本地名>)`。

    两种写法都认：HTML 的 `<img src="…">` 和 Markdown 的 `![](…)`。
    认不出的（远程网址、已经改好的相对路径）原样留着。
    """
    if resolve is None:
        return text

    def as_markdown(src):
        local = resolve(src)
        return f"![](images/{local})" if local else None

    def tag_repl(m):
        return as_markdown(m.group(1)) or m.group(0)

    def md_repl(m):
        return as_markdown(m.group(2)) or m.group(0)

    text = _IMG_TAG_RE.sub(tag_repl, text)
    return _MD_IMG_RE.sub(md_repl, text)


class JsonlLineError(Exception):
    """结果里的某一行没法用：自带错误码，或者形状不对。"""


@dataclass
class Page:
    index: int                 # 按行序、项序摊平后的页码，从 0 起
    text: str                  # 这一页的原始正文
    images: dict[str, str]     # 图片名（形如 imgs/xxx.jpg）→ 完整网址
    # 版面块 (label, (左, 上, 右, 下))，按服务给的顺序。判断表格是否跨页要用它。
    blocks: tuple = ()
    page_size: tuple | None = None   # 这一页的 (宽, 高)；服务没给就是 None


_NO_DEFAULT = object()


def _expect(value, want, what, lineno, empty=_NO_DEFAULT):
    """取来的字段形状不对就抛自己的异常类——调用方只接得住 JsonlLineError。

    `empty` 是「这个字段没给」时的兜底值，得由调用处显式给：给了它，`None` 就
    换成它（缺字段照常出页）；没给，`None` 也按形状不对报出来。

    除了 `None`，其余一律照 `isinstance` 判——`[]`、`{}`、`0`、`""` 这些假值
    也算「给了个不是那个形状的」，不能悄悄降级成空。降级了会把「服务改了结构」
    说成「你的文档是空的」，用户拿着一句「清理完什么都不剩」去查自己的 PDF。
    """
    if value is None and empty is not _NO_DEFAULT:
        value = empty
    if not isinstance(value, want):
        raise JsonlLineError(
            f"结果第 {lineno} 行的 {what} 不是 {want.__name__}，"
            f"是 {type(value).__name__}")
    return value


def _page_geometry(pruned):
    """从 prunedResult 里取版面块与页面尺寸。

    服务没给、或者形状不对的块直接跳过——这里只用来判断表格跨页，
    少一个块最多是少合一次，不该让整份转换失败。
    """
    blocks = []
    raw_blocks = pruned.get("parsing_res_list")
    if isinstance(raw_blocks, list):
        for b in raw_blocks:
            if not isinstance(b, dict):
                continue
            label = b.get("block_label")
            bbox = b.get("block_bbox")
            if not isinstance(label, str):
                continue
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            try:
                box = tuple(float(v) for v in bbox)
            except (TypeError, ValueError):
                continue
            blocks.append((label, box))
    width = pruned.get("width")
    height = pruned.get("height")
    size = None
    if isinstance(width, (int, float)) and isinstance(height, (int, float)):
        size = (float(width), float(height))
    return tuple(blocks), size


# 判断两张表是否跨页相连时的容差。实测第 75、76 页：表格底边占页高 0.902、
# 下一页表格顶边 0.085，左右边界差 2 像素（页宽 1191）。这几个值只能往严里调。
_EDGE_TOLERANCE_RATIO = 0.05
_EDGE_ALIGN_RATIO = 0.02
_PAGE_SIZE_TOLERANCE = 0.02

_HEADER_LABELS = {"header", "header_image"}
_FOOTER_LABELS = {"footer", "footer_image"}


def _content_blocks(page, ignore_labels):
    """去掉页眉、页码这类不占正文的块，留下判断页边界的块。"""
    ignored = set(ignore_labels or ())
    return [(label, box) for label, box in page.blocks if label not in ignored]


def _bottom_anchor(blocks):
    """上一页表格下方的参照：页码的顶边；没有页码就用页脚的顶边。

    有多个时取最靠上的那条顶边——阈值更低，判断更严，宁可漏合。
    """
    for labels in ({"number"}, _FOOTER_LABELS):
        tops = [box[1] for label, box in blocks if label in labels]
        if tops:
            return min(tops)
    return None


def _top_anchor(blocks):
    """下一页表格上方的参照：页眉的底边；多个时取最靠下的，判断更严。"""
    bottoms = [box[3] for label, box in blocks if label in _HEADER_LABELS]
    return max(bottoms) if bottoms else None


def _same_size(a, b):
    if not a or not b:
        return False
    return all(x and y and abs(x - y) <= _PAGE_SIZE_TOLERANCE * max(x, y)
               for x, y in zip(a, b))


def _table_columns(raw_html):
    """这张表展开 rowspan/colspan 后的网格宽度；认不出来就是 0。"""
    try:
        doc = lxml_html.fragment_fromstring(raw_html, create_parent="div")
    except Exception:
        return 0
    tables = doc.xpath(".//table")
    if not tables:
        return 0
    grid = _table_grid(tables[0])
    return len(grid[0]) if grid else 0


def _cross_page_table_pair(prev_page, next_page, ignore_labels):
    """判断上一页末尾的表和下一页开头的表是不是同一张被页边界切断的表。

    成立时返回两张表的 (起, 止) 区间；任何一条不成立都返回 None——
    漏合看得见，误合看不出来，所以判不准就不合。
    """
    if not _same_size(prev_page.page_size, next_page.page_size):
        return None

    prev_blocks = _content_blocks(prev_page, ignore_labels)
    next_blocks = _content_blocks(next_page, ignore_labels)
    if not prev_blocks or not next_blocks:
        return None
    if prev_blocks[-1][0] != "table" or next_blocks[0][0] != "table":
        return None

    prev_spans = _find_table_spans(prev_page.text)
    next_spans = _find_table_spans(next_page.text)
    if not prev_spans or not next_spans:
        return None
    # 正文里的表要和版面块里的表一一对上：对不上说明我认表的办法和服务
    # 给的结构不一致，宁可不合。
    if (len(prev_spans)
            != sum(1 for label, _ in prev_page.blocks if label == "table")
            or len(next_spans)
            != sum(1 for label, _ in next_page.blocks if label == "table")):
        return None

    prev_span = prev_spans[-1]
    next_span = next_spans[0]
    # 上一页正文在最后一张表之后不许再有东西；下一页正文在第一张表之前
    # 不许再有东西。表格另一侧的内容（标题、签名行）不影响判断。
    if prev_page.text[prev_span[1]:].strip():
        return None
    if next_page.text[:next_span[0]].strip():
        return None

    anchor = _bottom_anchor(prev_page.blocks)
    header = _top_anchor(next_page.blocks)
    if anchor is None or header is None:
        return None

    prev_box = prev_blocks[-1][1]
    next_box = next_blocks[0][1]
    height = prev_page.page_size[1]
    if prev_box[3] < anchor - _EDGE_TOLERANCE_RATIO * height:
        return None
    if next_box[1] > header + _EDGE_TOLERANCE_RATIO * height:
        return None

    width = prev_page.page_size[0]
    if abs(prev_box[0] - next_box[0]) > _EDGE_ALIGN_RATIO * width:
        return None
    if abs(prev_box[2] - next_box[2]) > _EDGE_ALIGN_RATIO * width:
        return None

    prev_cols = _table_columns(prev_page.text[prev_span[0]:prev_span[1]])
    next_cols = _table_columns(next_page.text[next_span[0]:next_span[1]])
    if not prev_cols or prev_cols != next_cols:
        return None

    return prev_span, next_span


def parse_jsonl(raw: str) -> list[Page]:
    """把结果 JSONL 摊成一份文档的页表。

    一份 PDF 通常是一行装 3 页，但这个数别写死：按行序、项序摊平，
    第 n 个就是第 n 页。结果里的页码标记（inputImage、图片网址里的
    markdown_N、dataInfo.numPages）全是行内的，靠不住，只能靠顺序。

    解析不了的输入一律抛 JsonlLineError，不把 JSONDecodeError、Python 读不了的
    超长数值、嵌套太深，或者压根不是文本的输入漏出去，形状不对（合法 JSON 但
    取出来的不是对象/列表/字符串）也一样：
    调用方（并发那层）只接得住这一个异常类，漏出去就不是「这一份失败」，
    而是整批跟着崩，用户看到的还是 Python 栈回溯。

    缺字段仍然按空处理——「没给」和「给了个不是那个形状的」是两回事，
    前者照常出页，后者才报错。
    """
    pages = []
    if not isinstance(raw, str):
        raise JsonlLineError(
            f"结果不是文本，是 {type(raw).__name__}——这一步该拿到 JSONL 正文")
    for lineno, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError, RecursionError) as exc:
            # ValueError 兜的是 Python 自己的整数位数上限（4300 位）——那份 JSON
            # 是合法的，是 Python 读不了那么长的数。RecursionError 兜的是嵌套
            # 太深，它不是 ValueError 的子类。三种都只该让这一份失败。
            raise JsonlLineError(
                f"结果第 {lineno} 行不是合法 JSON"
                f"（或者数值太大，Python 读不了）：{exc}") from exc
        obj = _expect(obj, dict, "顶层", lineno)
        if obj.get("errorCode"):
            raise JsonlLineError(
                f"结果第 {lineno} 行报错：{obj.get('errorMsg') or obj['errorCode']}")
        result = _expect(obj.get("result"), dict, "result", lineno, empty={})
        items = _expect(result.get("layoutParsingResults"),
                        list, "layoutParsingResults", lineno, empty=[])
        for n, item in enumerate(items, start=1):
            item = _expect(item, dict,
                           f"layoutParsingResults 里第 {n} 项", lineno)
            md = _expect(item.get("markdown"), dict, "markdown", lineno, empty={})
            images = _expect(md.get("images"), dict, "images", lineno, empty={})
            pruned = _expect(item.get("prunedResult"), dict, "prunedResult",
                             lineno, empty={})
            blocks, page_size = _page_geometry(pruned)
            pages.append(Page(
                index=len(pages),
                text=_expect(md.get("text"), str, "text", lineno, empty=""),
                images=dict(images),
                blocks=blocks,
                page_size=page_size,
            ))
    return pages


def _with_suffix(local, n):
    if "." in local:
        stem, _, ext = local.rpartition(".")
        return f"{stem}-{n}.{ext}"
    return f"{local}-{n}"


def allocate_names(pages):
    """给一份文档里的每张图定一个本地文件名。

    名字用接口给的那个（形如 img_in_image_box_1_2_3_4.jpg），不自己另起；
    只在两个不同网址落到同一个文件名时才加 -2、-3。作用域是**一份文档**，
    不跨文档共用名字表。

    契约：`pages` 的 `index` 是**一份文档内的唯一页码**。下面按「(页码, 图片名)」
    记账就指着这一条——页码撞了，两张不相干的图会被当成同一页上的同一个键。
    `Page` 现在只有 `parse_jsonl` 一条构造路径（`index=len(pages)`），天然满足。
    """
    by_url = {}    # 网址 → 本地文件名
    taken = {}     # 本地文件名 → 网址
    names = {}
    for page in pages:
        for src, url in page.images.items():
            if url in by_url:
                names[(page.index, src)] = by_url[url]
                continue
            local = src.rsplit("/", 1)[-1]
            if local in taken:
                n = 2
                while _with_suffix(local, n) in taken:
                    n += 1
                local = _with_suffix(local, n)
            taken[local] = url
            by_url[url] = local
            names[(page.index, src)] = local
    return names


def image_downloads(pages, names):
    """要下的图：[(本地文件名, 网址)]，按网址去重、保持出现顺序。"""
    seen = set()
    out = []
    for page in pages:
        for src, url in page.images.items():
            if url in seen:
                continue
            seen.add(url)
            out.append((names[(page.index, src)], url))
    return out


def clean_markdown(text, resolve):
    """一页正文的通用清理，按这个顺序跑：

    1. HTML 表格转 Markdown 表格
    2. 拆掉包裹标签
    3. 删掉整行只有页码的那些行
    4. 空行归一、行尾空白去掉
    5. 图片引用改写成 images/<本地名>
    """
    text = convert_tables(text)
    text = strip_wrapper_tags(text)
    text = strip_page_markers(text)
    text = normalize_blank_lines(text)
    text = rewrite_image_refs(text, resolve)
    _assert_no_placeholder(text)
    return text


def assemble(pages, names):
    """按页序清理、拼成一份文档。"""
    parts = []
    for page in pages:
        lookup = {}
        for (index, src), local in names.items():
            if index != page.index:
                continue
            lookup[src] = local
            lookup[src.rsplit("/", 1)[-1]] = local
        parts.append(clean_markdown(page.text, lookup.get))
    return "\n\n".join(parts)
