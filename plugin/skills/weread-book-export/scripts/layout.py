# -*- coding: utf-8 -*-
"""把画布上的逐字记录还原成行。

微信读书把整页正文画在 canvas 上，DOM 里一个字都没有。给
``CanvasRenderingContext2D.prototype.fillText`` 挂钩子后，每次绘字都能记下
文本、x、y 与字体；同一基线的字 y 相同、从左到右 x 递增，于是按 y 归簇、
簇内按 x 排序拼起来就是一整行，与屏幕上的一字不差。
"""

import collections
import re

# 同一行里不同字体的基线可能差一点点，2px 之内算同一行
BASELINE_TOLERANCE = 2.0

_FONT_SIZE = re.compile(r"(\d+(?:\.\d+)?)px")


def font_size(font):
    """从 canvas 的 font 字符串里取字号（"bold 20px/1.5 serif" → 20），取不到返回 0。"""
    m = _FONT_SIZE.search(font or "")
    return float(m.group(1)) if m else 0.0


def group_lines(glyphs):
    """把逐字记录还原成行，按 y 升序返回。

    参数 ``glyphs``：``[{"t": str, "x": float, "y": float, "font": str}, ...]``
    返回：``[{"y": float, "x": float, "text": str, "font_size": float}, ...]``

    ``y`` 取该行最小的基线，``x`` 取行内最左，``font_size`` 取行内最大字号。
    """
    clusters = []
    for glyph in sorted(glyphs, key=lambda g: g["y"]):
        for cluster in clusters:
            if abs(glyph["y"] - cluster[0]["y"]) <= BASELINE_TOLERANCE:
                cluster.append(glyph)
                break
        else:
            clusters.append([glyph])

    lines = []
    for cluster in clusters:
        cluster.sort(key=lambda g: g["x"])
        lines.append(
            {
                "y": cluster[0]["y"],
                "x": cluster[0]["x"],
                "text": "".join(g["t"] for g in cluster),
                "font_size": max(font_size(g.get("font")) for g in cluster),
            }
        )
    lines.sort(key=lambda line: line["y"])
    return lines


# 测量字体的串：整行只有 ASCII 字母数字，长度达到这个数才当噪声
MEASUREMENT_MIN_LEN = 20

# 字号达到正文的这么多倍，认作标题
HEADING_RATIO = 1.2

# 断段阈值：
# - 与上一行 y 差超过行高的 LINE_GAP_RATIO 倍。实测正文行距 41px、段间 62px，
#   1.5 倍（61.5）只差 0.5px 就判错，所以放到 1.3（53.3），两头都留出余量
# - x 比左边界右移超过字号的 INDENT_RATIO 倍
# - 上一行右边界不足本章最宽行的 SHORT_TAIL_RATIO 倍。中文按标点断行，
#   满行之间能差好几个字（实测 588～693px），按"差两个字"判会把每行都当段尾
LINE_GAP_RATIO = 1.3
INDENT_RATIO = 1.5
SHORT_TAIL_RATIO = 0.8


def _is_measurement_line(text):
    return len(text) >= MEASUREMENT_MIN_LEN and text.isascii() and text.isalnum()


def strip_noise_lines(lines, book_title, chapter_title):
    """剔掉画在画布上、但不是正文的行。

    判据都从严，宁可留下也不误删正文：

    - 测量字体用的字母数字串：整行只有 ASCII 字母数字且长度 >= 20
    - 章首的书名/章名：只看第一行，且必须整行完全相等
    - 页眉页脚：整行等于书名或章名，且在本章出现 >= 3 次。
      只出现一两次的保留——那可能是正文里真的提到了书名
    """
    titles = {t.strip() for t in (book_title, chapter_title) if t and t.strip()}

    kept = [line for line in lines if not _is_measurement_line(line["text"])]
    # 先数次数再删首行，免得首行本身被删掉后页眉行就差一次数
    counts = collections.Counter(line["text"].strip() for line in kept)

    if kept and kept[0]["text"].strip() in titles:
        kept = kept[1:]

    return [
        line
        for line in kept
        if not (line["text"].strip() in titles and counts[line["text"].strip()] >= 3)
    ]


# 一段绘制少于这么多个字，就不当成完整的一轮（多半是收尾的一笔重绘）
MIN_RENDER_GLYPHS = 50


def last_render(glyphs, min_glyphs=MIN_RENDER_GLYPHS):
    """只留最后一轮绘制。

    翻章时阅读器会**先把上一屏重画一遍再画目标那一章**，两轮都记进同一个抓取里
    （实测某章抓到的 5576 个字里，前 3442 个属于上一屏，两次都从画布顶端 y=20 开始）。
    按 y 归行会把两轮并排拼成一句句乱码，所以先按**绘制顺序**切开：y 往回跳就是
    新的一轮开始。屏幕上留下的是最后一轮，就取它。

    末尾如果只有零星几笔重绘（比如一根下划线），够不上 ``min_glyphs``，跳过它、
    用前面那一轮；整章都短到够不上，那就还是用最后这一段。
    """
    segments = []
    start = 0
    for i in range(len(glyphs) - 1):
        if glyphs[i + 1]["y"] < glyphs[i]["y"] - 1:
            segments.append(glyphs[start : i + 1])
            start = i + 1
    segments.append(glyphs[start:])

    for segment in reversed(segments):
        if len(segment) >= min_glyphs:
            return segment
    return segments[-1]


def _body_font_size(lines):
    """正文字号：按字（不是按行）统计出现最多的字号，并列取大的。

    按字数而不是按行数，是因为一页里标题和正文往往各占一行，
    按行数会打平；按字数，正文一占就是几十上百个字，稳。
    """
    weight = collections.Counter()
    for line in lines:
        weight[line["font_size"]] += len(line["text"])
    if not weight:
        return 0.0
    return max(weight.items(), key=lambda item: (item[1], item[0]))[0]


def _line_height(lines, fallback):
    """行高：相邻两行 y 差里最常见的那个，并列取小的。"""
    diffs = collections.Counter()
    for prev, cur in zip(lines, lines[1:]):
        diff = cur["y"] - prev["y"]
        if diff > 0:
            diffs[round(diff, 2)] += 1
    if not diffs:
        return fallback
    return min(diffs.items(), key=lambda item: (-item[1], item[0]))[0]


def to_paragraphs(lines):
    """把行拼成段落，字号明显大的行认作标题。

    返回 ``[{"kind": "heading"|"text", "level": int, "text": str, "y": float}, ...]``，
    正文段落的 ``level`` 为 0；标题按字号从大到小依次是 1、2、3，超过 3 种一律 3。

    正文对齐基准取自正文行：左边界是正文行 ``x`` 的最小值，右边界按
    ``x + len(text) * font_size`` 估。断段三条，任一成立即新起一段。
    """
    if not lines:
        return []

    base = _body_font_size(lines)

    def is_heading(line):
        return base > 0 and line["font_size"] >= base * HEADING_RATIO

    heading_sizes = sorted({l["font_size"] for l in lines if is_heading(l)}, reverse=True)

    body = [line for line in lines if not is_heading(line)]
    left = min((line["x"] for line in body), default=min(line["x"] for line in lines))
    max_right = max(
        (line["x"] + len(line["text"]) * line["font_size"] for line in body), default=0.0
    )
    line_height = _line_height(lines, base * 1.5)

    paragraphs = []
    current = None
    prev = None
    for line in lines:
        if is_heading(line):
            if current is not None:
                paragraphs.append(current)
                current = None
            prev = None
            level = min(heading_sizes.index(line["font_size"]) + 1, 3)
            paragraphs.append(
                {"kind": "heading", "level": level, "text": line["text"], "y": line["y"]}
            )
            continue

        prev_right = 0.0 if prev is None else prev["x"] + len(prev["text"]) * prev["font_size"]
        starts_new = (
            current is None
            or prev is None
            or (line["y"] - prev["y"]) > LINE_GAP_RATIO * line_height
            or (line["x"] - left) >= INDENT_RATIO * base
            or prev_right < max_right * SHORT_TAIL_RATIO
        )
        if starts_new:
            if current is not None:
                paragraphs.append(current)
            current = {"kind": "text", "level": 0, "text": line["text"], "y": line["y"]}
        else:
            current["text"] += line["text"]
        prev = line

    if current is not None:
        paragraphs.append(current)
    return paragraphs


# 认章只看屏幕头几行；章名总在第一行，多看几行是给前置页留余量
IDENTIFY_LINES = 6


def _squeeze(text):
    """去掉所有空白。目录里写「推荐序 我们向…」，画到画布上可能没有那个空格。"""
    return re.sub(r"\s+", "", text or "")


def identify_chapter(lines, titles, expected=None):
    """在屏幕头几行里认出这是哪一章，返回 ``titles`` 的下标；认不出返回 ``None``。

    每章渲染出来的第一行就是它的章名——这是唯一在所有页面类型上都成立的信号：
    ``document.title`` 对版权信息、扉页这类前置页不带章名；画布高度对短章不可靠；
    「抓到的字变多了」在点目录里当前所在的那一章时不成立，因为根本不会重画。

    同名章（如「附录」出现两次）优先认 ``expected`` 那一条，认不到再按顺序找。
    """
    head = {_squeeze(line["text"]) for line in lines[:IDENTIFY_LINES]}

    if expected is not None and 0 <= expected < len(titles):
        if _squeeze(titles[expected]) in head:
            return expected

    for index, title in enumerate(titles):
        key = _squeeze(title)
        if key and key in head:
            return index
    return None


def extract_chapter(glyphs, book_title, chapter_title):
    """逐字记录 → 段落列表：还原成行、剔噪声、拼段。"""
    lines = group_lines(glyphs)
    return to_paragraphs(strip_noise_lines(lines, book_title, chapter_title))
