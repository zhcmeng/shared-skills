"""纯文本处理：不碰网络、不碰文件、不读 token。

所有能单测的逻辑都集中在这里。
"""
import re

from lxml import html as lxml_html
from tabulate import tabulate

# 表格转 Markdown 时的中间记号。正文里出现这个形状，说明转换漏了东西，
# 宁可报错退出也不能把它落进正文。
_PLACEHOLDER = "\x00T{}\x00"
_PLACEHOLDER_RE = re.compile(r"\x00T\d+\x00")

_TABLE_OPEN = "<table"
_TABLE_CLOSE = "</table>"


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
    lower = text.lower()
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

    rows = []
    for tr in table.iter("tr"):
        # 只收属于这张表的行；内层表格的行归内层管
        nearest = tr.getparent()
        while nearest is not None and nearest.tag != "table":
            nearest = nearest.getparent()
        if nearest is not table:
            continue
        cells = tr.xpath("./td | ./th")
        if cells:
            rows.append([_cell_text(c) for c in cells])

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
# 只删光秃秃的开标签——不能写成「不认识又没属性就删」：正文里
# `List<String>`、`x<y>z`、`<name>` 这种形状很常见，<String> 会被当成标签，
# 结果就是静默丢正文，比留着一个看得见的原始标签坏得多。
# 收尾标签也不删：带属性的 `<image …>` 留着的时候，把它配对的那半删掉
# 会留下个配不平的标签，那是另一种删错。要么整对留着，要么整对处理。
# 以后真见到别的残标签，加在这里。
_STRAY_TAGS = {"image"}

_TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:\s[^<>]*)?)(/?)>")


def strip_wrapper_tags(text):
    """拆掉包裹标签；已知的裸残标签整个去掉。

    三条规则：包裹名单里的拆掉标签留内容；保留名单里的原样不动；
    其余的——只有名字在残标签名单里、没属性、又不是收尾标签的才去掉，
    剩下的一律原样留着。
    """
    def repl(m):
        name = m.group(2).lower()
        if name in _WRAPPERS:
            return ""
        if name in _KEEP:
            return m.group(0)
        if name in _STRAY_TAGS and not m.group(1) and not m.group(3).strip():
            return ""
        return m.group(0)

    return _TAG_RE.sub(repl, text)


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
