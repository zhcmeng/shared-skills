# -*- coding: utf-8 -*-
"""把预渲染 HTML 拆出的块整理成段落与图片。

阅读器把整章正文解密后放进隐藏的预渲染容器，画布只画其中一部分。这里处理
从那份 HTML 里按文档顺序取出的块：把空白归一、把 HTML 标题折算成
Markdown 标题层级、给图和段落排一个先后位置。

块由页面里的脚本产出，形如 ``{"kind": "text"|"heading"|"image", ...}``；
``y`` 只用来表达先后：同一节内按块的出现顺序编号，渲染时按它把图插到段间。
"""

import re

# HTML 标题的层级折算成 Markdown 层级：h1～h3 算一级标题（渲染成 ``##``），
# h4 起往下顺延。实测一章的节标题是 h3，偶尔有 h4（同一节里再分小层）。
# 章里还分节时（``nested``），节标题自己已经占了一级，节内的标题都再降一级
HEADING_SHIFT = 2
MAX_HEADING_LEVEL = 3

# 每个块占这么多个 y 单位，图放在块号之间（+0.5 个块）
BLOCK_Y = 1000.0

# 拿屏幕上画出的行去核预渲染 HTML：太短的行（页眉、页码）不拿来比，
# 取每行前 20 个字，头三行里有一行对得上就算同一节
SCREEN_SAMPLE_MIN = 6
SCREEN_SAMPLE_CHARS = 20
SCREEN_SAMPLE_LINES = 3


def normalize_text(text):
    """把 HTML 里取出的文字收拾成正文：去掉零宽空格，一串空白并成一个空格。

    HTML 里汉字逐字包在 span 里，字符之间没有空白；出现的空白都是排版有意的
    分隔（如「摄影者　地点」「壹　大碰撞」），所以只归一、不删。全角空格是
    空白的一种，一并换成普通空格。零宽空格（U+200B）是阅读器排版插入的，
    屏幕上看不见，留着会让搜索和比对对不上，去掉。
    """
    return re.sub(r"\s+", " ", (text or "").replace("​", "")).strip()


def _squeeze(text):
    """去掉所有空白，用来比较标题。"""
    return "".join((text or "").split())


def matches_screen(blocks, line_texts, unit_title, book_title):
    """预渲染 HTML 是不是屏幕上正在画的这一节。

    阅读器可能在画完这一节之后接着预渲染下一节，截到的是最后一份。用屏幕上
    已经画出来的几行正文去核：一行都对不上，说明截到的不是这一节。屏幕上
    只有标题、或 HTML 整节都是图时无从比对，按对得上处理。
    """
    text = _squeeze(
        "".join(block.get("text") or "" for block in blocks if block["kind"] != "image")
    )
    if not text:
        return True
    skip = {_squeeze(unit_title), _squeeze(book_title)}
    samples = []
    for line in line_texts:
        key = _squeeze(line)
        if len(key) < SCREEN_SAMPLE_MIN or key in skip:
            continue
        samples.append(key[:SCREEN_SAMPLE_CHARS])
        if len(samples) >= SCREEN_SAMPLE_LINES:
            break
    if not samples:
        return True
    return any(sample in text for sample in samples)


def blocks_to_part(blocks, unit_title, nested=False):
    """块列表 → ``(paragraphs, images)``。

    段落的 ``y`` 是块在文档里的序号乘 ``BLOCK_Y``，图的 ``y`` 落在相邻两块
    之间；``markdown`` 按 ``y`` 把图插到它前面那段之后。空文本块丢掉；
    开头若有一块标题就是本节的标题，去掉——渲染时已经把它写成小节标题了。
    ``nested`` 表示这一节上面还有「章名 → 节名」那一层，节内标题再降一级。
    """
    extra = 1 if nested else 0
    paragraphs = []
    images = []
    for index, block in enumerate(blocks):
        y = index * BLOCK_Y
        if block["kind"] == "image":
            images.append({"src": block["src"], "alt": block.get("alt", ""), "y": y + BLOCK_Y / 2})
            continue
        text = normalize_text(block.get("text"))
        if not text:
            continue
        if block["kind"] == "heading":
            level = max(1, min(block["level"] - HEADING_SHIFT + extra, MAX_HEADING_LEVEL))
            paragraphs.append({"kind": "heading", "level": level, "text": text, "y": y})
        else:
            paragraphs.append({"kind": "text", "level": 0, "text": text, "y": y})

    if paragraphs and paragraphs[0]["kind"] == "heading":
        if _squeeze(paragraphs[0]["text"]) == _squeeze(unit_title):
            paragraphs.pop(0)
    return paragraphs, images
