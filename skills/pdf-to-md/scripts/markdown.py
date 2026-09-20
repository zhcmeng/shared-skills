"""纯文本处理：不碰网络、不碰文件、不读 token。

所有能单测的逻辑都集中在这里。
"""
import json
import re
from dataclasses import dataclass

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


def _expect(value, want, what, lineno):
    """取来的字段形状不对就抛自己的异常类——调用方只接得住 JsonlLineError。

    缺字段/空值由调用处的 `or {}`、`or []` 兜成空，走不到这里；能走到这里的
    都是「有值、但值不是那个形状」，也就是网关回了个 null、[]、裸数字这种。
    """
    if not isinstance(value, want):
        raise JsonlLineError(
            f"结果第 {lineno} 行的 {what} 不是 {want.__name__}，"
            f"是 {type(value).__name__}")
    return value


def parse_jsonl(raw: str) -> list[Page]:
    """把结果 JSONL 摊成一份文档的页表。

    一份 PDF 通常是一行装 3 页，但这个数别写死：按行序、项序摊平，
    第 n 个就是第 n 页。结果里的页码标记（inputImage、图片网址里的
    markdown_N、dataInfo.numPages）全是行内的，靠不住，只能靠顺序。

    解析不了的输入一律抛 JsonlLineError，不把 JSONDecodeError 漏出去，
    形状不对（合法 JSON 但取出来的不是对象/列表/字符串）也一样：
    调用方（并发那层）只接得住这一个异常类，漏出去就不是「这一份失败」，
    而是整批跟着崩，用户看到的还是 Python 栈回溯。

    缺字段仍然按空处理——「没给」和「给了个不是那个形状的」是两回事，
    前者照常出页，后者才报错。
    """
    pages = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise JsonlLineError(f"结果第 {lineno} 行不是合法 JSON：{exc}") from exc
        obj = _expect(obj, dict, "顶层", lineno)
        if obj.get("errorCode"):
            raise JsonlLineError(
                f"结果第 {lineno} 行报错：{obj.get('errorMsg') or obj['errorCode']}")
        result = _expect(obj.get("result") or {}, dict, "result", lineno)
        items = _expect(result.get("layoutParsingResults") or [],
                        list, "layoutParsingResults", lineno)
        for item in items:
            item = _expect(item, dict, "layoutParsingResults 里的一项", lineno)
            md = _expect(item.get("markdown") or {}, dict, "markdown", lineno)
            images = _expect(md.get("images") or {}, dict, "images", lineno)
            pages.append(Page(
                index=len(pages),
                text=_expect(md.get("text") or "", str, "text", lineno),
                images=dict(images),
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
