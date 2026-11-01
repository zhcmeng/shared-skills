# -*- coding: utf-8 -*-
"""把画布上的逐字记录还原成行。

微信读书把整页正文画在 canvas 上，DOM 里一个字都没有。给
``CanvasRenderingContext2D.prototype.fillText`` 挂钩子后，每次绘字都能记下
文本、x、y 与字体；同一基线的字 y 相同、从左到右 x 递增，于是按 y 归簇、
簇内按 x 排序拼起来就是一整行，与屏幕上的一字不差。
"""

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
