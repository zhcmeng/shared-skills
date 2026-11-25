#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""weread_export.py 里等待绘制的测试。

    python -X utf8 tests/weread-book-export/test_weread_export.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
import weread_export  # noqa: E402
from weread_export import _identify, _page_hidden, _wait_drawn  # noqa: E402


class _FakePage:
    """只提供 _wait_drawn 用到的 evaluate 和 bring_to_front。"""

    def __init__(self, hidden, pre=None, cap=None, raise_on_visibility=False):
        self.hidden = hidden
        self.pre = list(pre or [])
        self.cap = list(cap or [])
        self.raise_on_visibility = raise_on_visibility
        self.brought = 0
        self.queries = []

    def evaluate(self, expr):
        self.queries.append(expr)
        if "visibilityState" in expr:
            if self.raise_on_visibility:
                raise RuntimeError("页面没了")
            return self.hidden
        for name, seq in (("__wereadPre", self.pre), ("__wereadCap", self.cap)):
            if name in expr:
                if not seq:
                    return 0
                # 最后一项一直返回，模拟数量稳定下来
                return seq.pop(0) if len(seq) > 1 else seq[0]
        raise AssertionError(expr)

    def bring_to_front(self):
        self.brought += 1


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

    old_interval = weread_export.RENDER_SAMPLE_INTERVAL
    weread_export.RENDER_SAMPLE_INTERVAL = 0.001
    try:
        eq("可见页面：hidden 为 False", _page_hidden(_FakePage(False)), False)
        eq("最小化页面：hidden 为 True", _page_hidden(_FakePage(True)), True)
        eq(
            "取不到 visibilityState 时按可见处理",
            _page_hidden(_FakePage(True, raise_on_visibility=True)),
            False,
        )

        page = _FakePage(False, cap=[1])
        eq("可见页面等字形画完", _wait_drawn(page, timeout=0.05), True)
        eq("可见页面不查预渲染", any("__wereadPre" in q for q in page.queries), False)
        eq("可见页面不把窗口叫回前台", page.brought, 0)

        page = _FakePage(True, pre=[1])
        eq("最小化页面等预渲染稳定", _wait_drawn(page, timeout=0.05), True)
        eq("最小化页面不查字形", any("__wereadCap" in q for q in page.queries), False)
        eq("有预渲染时不动窗口", page.brought, 0)

        page = _FakePage(True, pre=[0], cap=[1])
        eq("最小化且没有预渲染：叫回前台后等字形", _wait_drawn(page, timeout=0.05), True)
        eq("叫回前台一次", page.brought, 1)
        eq("叫回前台后查字形", any("__wereadCap" in q for q in page.queries), True)

        page = _FakePage(True, pre=[0], cap=[0])
        eq("最小化且一直等不到内容", _wait_drawn(page, timeout=0.05), False)
        eq("等不到内容也叫回前台一次", page.brought, 1)

        orig_hidden = weread_export._page_hidden
        orig_pre = weread_export.pre_render_blocks
        orig_glyph = weread_export.capture_glyphs
        try:
            weread_export._page_hidden = lambda p: True
            weread_export.capture_glyphs = lambda p: []
            weread_export.pre_render_blocks = lambda p: [
                {"kind": "heading", "text": "第二章 目标"},
                {"kind": "text", "text": "正文"},
            ]
            eq(
                "最小化时从预渲染开头认章",
                _identify(_FakePage(True), ["第一章", "第二章 目标"], 1),
                1,
            )
            weread_export.pre_render_blocks = lambda p: [
                {"kind": "heading", "text": "第一章"}
            ]
            eq(
                "预渲染还是上一章时认成上一章",
                _identify(_FakePage(True), ["第一章", "第二章 目标"], 1),
                0,
            )
            weread_export.pre_render_blocks = lambda p: None
            weread_export.capture_glyphs = lambda p: [
                {"t": "第一章", "x": 0, "y": 0, "font": "16px"}
            ]
            eq(
                "没有预渲染时退回屏幕字",
                _identify(_FakePage(True), ["第一章", "第二章 目标"], 1),
                0,
            )
        finally:
            weread_export._page_hidden = orig_hidden
            weread_export.pre_render_blocks = orig_pre
            weread_export.capture_glyphs = orig_glyph
    finally:
        weread_export.RENDER_SAMPLE_INTERVAL = old_interval

    print()
    if bad == 0:
        print("全部通过")
        return 0
    print("%d 项没过" % bad)
    return 1


if __name__ == "__main__":
    sys.exit(main())
