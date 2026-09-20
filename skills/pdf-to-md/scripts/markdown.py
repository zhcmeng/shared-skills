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
            return spans
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
