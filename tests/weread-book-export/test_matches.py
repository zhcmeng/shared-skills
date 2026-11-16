#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""matches.py 的测试：标题归一化、精确匹配、模糊匹配、相关词合并与渲染。

    python -X utf8 tests/weread-book-export/test_matches.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
from matches import (  # noqa: E402
    exact_hits,
    fuzzy_hits,
    merge_hits,
    normalize_title,
    parse_terms,
    render_exact,
    render_fuzzy,
    render_semantic,
    term_hits,
)


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

    def raises(name, func, needle):
        nonlocal bad
        try:
            func()
        except Exception as exc:
            if needle not in str(exc):
                bad += 1
                print("[失败] %s" % name)
                print("       报错里没有 %r：%s" % (needle, exc))
            else:
                print("[通过] %s" % name)
        else:
            bad += 1
            print("[失败] %s：没有报错" % name)

    eq(
        "全角半角与空白不影响比对",
        normalize_title("财经 (2026 年第 5 期）"),
        normalize_title("财经（2026年第5期）"),
    )
    eq("大小写不影响比对", normalize_title("AI 入门"), normalize_title("ai入门"))
    eq(
        "精确只认全等，大小写不敏感",
        [
            hit["href"]
            for hit in exact_hits(
                [
                    {"title": "ai 入门", "href": "a"},
                    {"title": "AI 入门指南", "href": "b"},
                ],
                "AI 入门",
            )
        ],
        ["a"],
    )
    eq(
        "第一财经挡在外面",
        [
            hit["href"]
            for hit in exact_hits(
                [
                    {"title": "第一财经（2026年第5期）", "href": "y"},
                    {"title": "财经（2026年第5期）", "href": "a"},
                ],
                "财经（2026年第5期）",
            )
        ],
        ["a"],
    )
    eq(
        "半角括号也能认出来",
        [
            hit["href"]
            for hit in exact_hits(
                [{"title": "财经(2026年第5期)", "href": "c"}],
                "财经（2026年第5期）",
            )
        ],
        ["c"],
    )

    hits = [
        {"title": "估值：难点、解决方案", "href": "a"},
        {"title": "价值投资入门", "href": "b"},
        {"title": "财报分析", "href": "c"},
    ]
    eq(
        "模糊档任意一个词出现就算命中",
        [hit["href"] for hit in fuzzy_hits(hits, "估值 价值投资")],
        ["a", "b"],
    )
    eq(
        "两个词都不出现才排除",
        "c" in [hit["href"] for hit in fuzzy_hits(hits, "估值 价值投资")],
        False,
    )
    eq(
        "模糊档大小写不敏感",
        [hit["href"] for hit in fuzzy_hits([{"title": "AI 入门", "href": "x"}], "ai")],
        ["x"],
    )
    eq("相关词自动带上概念并去重", parse_terms("AI", "人工智能, 大模型，人工智能"), ["AI", "人工智能", "大模型"])
    eq(
        "单个词内部要求所有分词都在",
        [
            hit["href"]
            for hit in term_hits(
                [
                    {"title": "large language model 实战", "href": "a"},
                    {"title": "language model", "href": "b"},
                ],
                "large language model",
            )
        ],
        ["a"],
    )

    per_term = [
        {
            "term": "AI",
            "hits": [
                {"title": "AI 时代", "author": "甲", "href": "a"},
                {"title": "人工智能导论", "author": "乙", "href": "b"},
            ],
            "capped": False,
        },
        {
            "term": "人工智能",
            "hits": [
                {"title": "人工智能导论", "author": "乙", "href": "b"},
                {"title": "大模型时代", "author": "丙", "href": "c"},
            ],
            "capped": False,
        },
    ]
    merged = merge_hits(per_term)
    eq("按 href 去重", [item["href"] for item in merged], ["b", "a", "c"])
    eq("命中词数多的排前面", [len(item["terms"]) for item in merged], [2, 1, 1])
    eq("同数按首次出现", merged[1]["href"], "a")
    eq("记录命中的词", merged[0]["terms"], ["AI", "人工智能"])

    exact_text = render_exact(
        "同名",
        [
            {"title": "同名", "author": "甲", "href": "https://a"},
            {"title": "同名", "author": "乙", "href": "https://b"},
        ],
        [],
    )
    eq(
        "精确档同名多本全部列出",
        "https://a" in exact_text and "https://b" in exact_text and "未替你挑" in exact_text,
        True,
    )
    eq(
        "精确档没有同名时标明不是同名",
        "不是同名"
        in render_exact(
            "没有的书",
            [],
            [{"title": "别的书", "author": "甲", "href": "https://x"}],
        ),
        True,
    )

    fuzzy_text = render_fuzzy(
        "估值 价值投资", [{"title": "估值", "author": "甲", "href": "https://a"}], True
    )
    eq(
        "模糊档标题写成或",
        "或" in fuzzy_text and "估值" in fuzzy_text and "价值投资" in fuzzy_text,
        True,
    )
    eq("模糊档满页提示", "40 条" in fuzzy_text, True)

    semantic_text = render_semantic(
        ["AI", "人工智能", "大模型"],
        per_term + [{"term": "大模型", "hits": [], "capped": False}],
        merged,
    )
    eq(
        "语义档列出命中词",
        "命中 2 词" in semantic_text and "人工智能" in semantic_text,
        True,
    )
    eq(
        "语义档标 0 条词",
        "大模型：0 条" in semantic_text
        and "（0 条，换个词）" in semantic_text,
        True,
    )

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
