#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""content.py 自己的测试。

    python -X utf8 tests/weread-book-export/test_content.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
from content import blocks_to_part, matches_screen, normalize_text  # noqa: E402


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

    eq("换行并成一个空格", normalize_text("温度越来越\n高，水汽"), "温度越来越 高，水汽")
    eq("全角空格改成普通空格，不删", normalize_text("贰　高原“风机”"), "贰 高原“风机”")
    eq("连着几个空白并成一个", normalize_text("摄影：陈俊杰　　华北平原"), "摄影：陈俊杰 华北平原")
    eq("零宽空格去掉", normalize_text("“死亡地带”​。"), "“死亡地带”。")
    eq("英文单词之间的空格留着", normalize_text("in China"), "in China")
    eq("首尾空白去掉", normalize_text("  正文  "), "正文")
    eq("空串不炸", normalize_text(None), "")

    blocks = [
        {"kind": "heading", "level": 3, "text": "壹 大碰撞"},
        {"kind": "text", "level": 0, "text": "第一段"},
        {"kind": "image", "src": "https://x/1.jpg", "alt": ""},
        {"kind": "text", "level": 0, "text": "第二段"},
        {"kind": "heading", "level": 4, "text": "更深 标题"},
        {"kind": "text", "level": 0, "text": ""},
    ]
    paragraphs, images = blocks_to_part(blocks, "中国从哪里来？")
    eq(
        "h3 是一级标题，h4 降一级，空段落丢掉",
        paragraphs,
        [
            {"kind": "heading", "level": 1, "text": "壹 大碰撞", "y": 0.0},
            {"kind": "text", "level": 0, "text": "第一段", "y": 1000.0},
            {"kind": "text", "level": 0, "text": "第二段", "y": 3000.0},
            {"kind": "heading", "level": 2, "text": "更深 标题", "y": 4000.0},
        ],
    )
    eq(
        "图落在前后两段之间",
        images,
        [{"src": "https://x/1.jpg", "alt": "", "y": 2500.0}],
    )

    paragraphs, images = blocks_to_part(
        [
            {"kind": "heading", "level": 3, "text": "九寨沟：毁灭与创造"},
            {"kind": "text", "level": 0, "text": "正文"},
        ],
        "九寨沟：毁灭与创造",
    )
    eq(
        "开头的本节标题不重复写",
        paragraphs,
        [{"kind": "text", "level": 0, "text": "正文", "y": 1000.0}],
    )
    eq("没有图时返回空列表", images, [])

    paragraphs, _ = blocks_to_part(
        [{"kind": "heading", "level": 3, "text": "壹 大碰撞"}],
        "中国从哪里来？",
        nested=True,
    )
    eq(
        "章里再分节时，节内标题再降一级",
        paragraphs,
        [{"kind": "heading", "level": 2, "text": "壹 大碰撞", "y": 0.0}],
    )

    html = [
        {"kind": "text", "level": 0, "text": "温度越来越高，水汽也越来越不易凝结。"},
        {"kind": "image", "src": "https://x/1.jpg", "alt": ""},
    ]
    eq(
        "屏幕上的正文能在 HTML 里找到",
        matches_screen(html, ["这里是中国", "温度越来越高，水汽也越来越不易凝结。"], "中国从哪里来？", "这里是中国"),
        True,
    )
    eq(
        "HTML 是别的节时对不上",
        matches_screen(html, ["这里是中国", "九寨沟的湖泊坝体坍塌，湖水瞬间下泄。"], "九寨沟", "这里是中国"),
        False,
    )
    eq(
        "屏幕只有标题时比不了，按对得上处理",
        matches_screen(html, ["中国从哪里来？"], "中国从哪里来？", "这里是中国"),
        True,
    )
    eq(
        "HTML 里只有图时按对得上处理",
        matches_screen(
            [{"kind": "image", "src": "https://x/1.jpg", "alt": ""}],
            ["九寨沟的湖泊坝体坍塌，湖水瞬间下泄。"],
            "九寨沟",
            "这里是中国",
        ),
        True,
    )

    print()
    if bad == 0:
        print("全部通过")
        return 0
    print("%d 项没过" % bad)
    return 1


if __name__ == "__main__":
    sys.exit(main())
