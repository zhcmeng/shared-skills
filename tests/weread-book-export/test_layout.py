#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""layout.py 自己的测试。

    python -X utf8 tests/weread-book-export/test_layout.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
from layout import (  # noqa: E402
    extract_chapter,
    group_lines,
    identify_chapter,
    is_clipped,
    last_render,
    split_renders,
    strip_noise_lines,
    to_paragraphs,
)


def g(t, x, y, px=16):
    return {"t": t, "x": x, "y": y, "font": "%dpx serif" % px}


def main():
    bad = 0

    def eq(name, got, want):
        nonlocal bad
        if got != want:
            bad += 1
            print("[失败] %s" % name)
            print("       实际: %r" % (got,))
            print("       期望: %r" % (want,))
        else:
            print("[通过] %s" % name)

    eq(
        "同一基线的字按 x 从左到右拼成一行",
        group_lines([g("眠", 116, 500), g("春", 100, 500)]),
        [{"y": 500, "x": 100, "text": "春眠", "font_size": 16}],
    )

    lines = group_lines([g("春", 100, 500), g("眠", 116, 501)])
    eq("基线差 1px 仍算同一行", (len(lines), lines[0]["text"]), (1, "春眠"))

    eq(
        "行按 y 升序输出，与输入顺序无关",
        [l["text"] for l in group_lines([g("晓", 100, 580), g("春", 100, 500), g("眠", 100, 540)])],
        ["春", "眠", "晓"],
    )

    line = group_lines([g("春", 100, 500, 16), g("眠", 132, 500, 24)])[0]
    eq("行内字号取最大值", line["font_size"], 24)
    eq("x 取行内最小者", line["x"], 100)

    line = group_lines([{"t": "春", "x": 100, "y": 500, "font": "bold 20px/1.5 sans-serif"}])[0]
    eq("font 带前缀也能取到字号", line["font_size"], 20)

    def line(text, x=100, y=500, px=16):
        return {"x": x, "y": y, "text": text, "font_size": px}

    kept = strip_noise_lines(
        [line("abcdefghijklmnopqrstuvwxyz0123456789", y=480), line("正文", y=500)],
        "某书", "第一章",
    )
    eq("开头那串测量字体的字母数字被剔除", [l["text"] for l in kept], ["正文"])

    kept = strip_noise_lines(
        [line("abcdefghijklmnopqrstuvwxyz0123456789`~!@#$%^&*()_+[]{}|;:',<.>/?", y=480),
         line("正文", y=500)],
        "某书", "第一章",
    )
    eq("带标点的测量字符串也剔除", [l["text"] for l in kept], ["正文"])

    kept = strip_noise_lines(
        [line("推荐序我们向江南春学什么", y=460), line("正文", y=500)],
        "抢占心智", "推荐序 我们向江南春学什么",
    )
    eq(
        "目录标题带空格、画布上不带，也认得出是同一条并剔除",
        [l["text"] for l in kept],
        ["正文"],
    )

    kept = strip_noise_lines(
        [line("第一章 打造企业的护城河", y=460),
         line("第一章 打造企业的护城河是本书的核心", y=500)],
        "某书", "第一章 打造企业的护城河",
    )
    eq("章首的章名被剔除，正文里同名的句子保留",
       [l["text"] for l in kept], ["第一章 打造企业的护城河是本书的核心"])

    kept = strip_noise_lines(
        [line("抢占心智"), line("正文一"), line("抢占心智"), line("正文二"), line("抢占心智")],
        "抢占心智", "第一章",
    )
    eq("书名在章内重复三次以上才当页眉剔除",
       [l["text"] for l in kept], ["正文一", "正文二"])

    kept = strip_noise_lines(
        [line("正文一"), line("抢占心智"), line("正文二")], "抢占心智", "第一章"
    )
    eq("只出现一次的书名不动",
       [l["text"] for l in kept], ["正文一", "抢占心智", "正文二"])

    eq(
        "首行缩进断开新段落",
        [p["text"] for p in to_paragraphs([
            line("第一段第一行", y=500),
            line("第一段第二行", y=540),
            line("第二段第一行", x=132, y=580),
        ])],
        ["第一段第一行第一段第二行", "第二段第一行"],
    )

    eq(
        "行距超过一个半行高断开新段落",
        [p["text"] for p in to_paragraphs([line("甲", y=500), line("乙", y=540), line("丙", y=620)])],
        ["甲乙", "丙"],
    )

    eq(
        "上一行没写满就断开新段落",
        [p["text"] for p in to_paragraphs([
            line("短"),
            line("这一行写得满满的占了整行宽度", y=540),
            line("下一段", y=580),
        ])],
        ["短", "这一行写得满满的占了整行宽度下一段"],
    )

    eq(
        "字号大的行成为标题，级别按字号从大到小排",
        to_paragraphs([
            line("第一章", y=460, px=24),
            line("第一节", y=500, px=20),
            line("正文从这里开始", y=540),
        ]),
        [
            {"kind": "heading", "level": 1, "text": "第一章", "y": 460},
            {"kind": "heading", "level": 2, "text": "第一节", "y": 500},
            {"kind": "text", "level": 0, "text": "正文从这里开始", "y": 540},
        ],
    )

    eq(
        "extract_chapter 把三步串起来",
        extract_chapter(
            [g("abcdefghijklmnopqrstuvwxyz0123", 100, 460), g("正文", 100, 500)],
            "某书", "第一章",
        ),
        [{"kind": "text", "level": 0, "text": "正文", "y": 500}],
    )

    def run(text, start_y, count=6):
        return [g(text, 0, start_y + 40 * i) for i in range(count)]

    one = run("上一章", 20)
    two = run("这一章", 20)
    eq("一段画到底原样返回", last_render(one, min_glyphs=1), one)
    eq("y 往回跳就是重画了一轮，只留最后一轮", last_render(one + two, min_glyphs=1), two)

    tail = [g("重画的一笔", 0, 20), g("又一笔", 0, 60)]
    eq("末尾那一小截不算一轮，跳过它", last_render(one + two + tail, min_glyphs=5), two)

    eq("按绘制顺序把每一轮都切出来", split_renders(one + two), [one, two])
    eq("末尾那一小截也单独成一段，去留交给调用方", split_renders(one + two + tail), [one, two, tail])

    body_60 = run("正文", 20, count=60)
    noise = [
        g(ch, 0, 20)
        for ch in "abcdefghijklmnopqrstuvwxyz0123456789`~!@#$%^&*()_+[]{}|;:',<.>/?`"
    ]
    eq(
        "末尾只剩测量字体那一行时，跳过它取前面那一屏",
        last_render(body_60 + noise, min_glyphs=50),
        body_60,
    )

    eq(
        "最后一块画布画满了、末行贴到底边，就是被截断了",
        is_clipped([line("上一行", y=7930), line("末行", y=7976)], [3993, 3976]),
        True,
    )
    eq(
        "最后一块画布没画满，不算截断",
        is_clipped([line("上一行", y=6750), line("末行", y=6800)], [3976, 2843]),
        False,
    )
    eq(
        "短页只有一块矮画布，末行贴底也不算截断",
        is_clipped([line("上一行", y=360), line("末行", y=380)], [394]),
        False,
    )
    eq("一行都没画时不判截断", is_clipped([], [3993, 3976]), False)

    eq(
        "屏幕第一行就是章名，认得出来",
        identify_chapter([line("版权信息", y=20), line("书名：抢占心智", y=60)], ["版权信息", "推荐序"]),
        0,
    )

    eq(
        "目录里带空格、画布上不带，也要认得出",
        identify_chapter(
            [line("推荐序我们向江南春学什么", y=20)],
            ["版权信息", "推荐序 我们向江南春学什么"],
        ),
        1,
    )

    eq(
        "头几行一个都对不上就返回 None",
        identify_chapter([line("书名：抢占心智", y=20)], ["版权信息", "推荐序"]),
        None,
    )

    eq(
        "同名章优先认调用方期望的那一条",
        identify_chapter([line("附录", y=20)], ["附录", "正文", "附录"], expected=2),
        2,
    )

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
