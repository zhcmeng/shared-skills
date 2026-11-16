# -*- coding: utf-8 -*-
"""搜书的纯逻辑：标题归一化、匹配、相关词合并与文字输出。不碰浏览器。

精确匹配不能用「包含」：搜「财经（2026年第5期）」时，《第一财经（2026年第5期）》
也包含这串字，会被误认成同一本。标题先做 NFKC、去空白、大小写折叠，再全等比较。
"""

import re
import unicodedata

_SPACES = re.compile(r"\s+")


def normalize_title(text):
    """比对用的标题：全角半角统一（NFKC）、空白全去掉、大小写折叠。"""
    return _SPACES.sub("", unicodedata.normalize("NFKC", text or "")).casefold()


def exact_hits(hits, title):
    """返回标题与 title 完全一致的所有条目。"""
    want = normalize_title(title)
    return [hit for hit in hits if normalize_title(hit.get("title")) == want]


def split_tokens(query):
    """按空白把查询拆成用于比对的词，丢弃归一化后为空的。"""
    parts = (query or "").split()
    return [token for token in (normalize_title(part) for part in parts) if token]


def fuzzy_hits(hits, query):
    """模糊档：标题里出现查询中任意一个词就算命中。"""
    tokens = split_tokens(query)
    if not tokens:
        return []
    return [
        hit
        for hit in hits
        if any(token in normalize_title(hit.get("title")) for token in tokens)
    ]


def parse_terms(concept, raw_terms):
    """语义档的词表：概念本身放最前，再按逗号拆相关词，按归一化去重。

    保留第一次出现的写法，输出里显示的就是使用者熟悉的那串字。
    """
    terms = [concept] + re.split(r"[,，]", raw_terms or "")
    seen = set()
    result = []
    for term in terms:
        term = (term or "").strip()
        key = normalize_title(term)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(term)
    return result


def term_hits(hits, term):
    """语义档的单个词：标题同时含这个词的所有分词才算命中。

    带空格的概念（large language model）拆开后要求每个词都在。
    """
    tokens = split_tokens(term)
    if not tokens:
        return []
    return [
        hit
        for hit in hits
        if all(token in normalize_title(hit.get("title")) for token in tokens)
    ]


def merge_hits(per_term):
    """语义档：把每个词的结果按 href 合并，命中词多的排前面。

    order 记（第几个词，该词结果里的第几条）；命中词数相同时按它排序，
    也就是先出现的排前面。
    """
    by_href = {}
    for term_index, entry in enumerate(per_term):
        term = entry.get("term") or ""
        for hit_index, hit in enumerate(entry.get("hits") or []):
            href = hit.get("href") or ""
            if not href:
                continue
            item = by_href.get(href)
            if item is None:
                item = {
                    "title": hit.get("title") or "",
                    "author": hit.get("author") or "",
                    "href": href,
                    "terms": [],
                    "order": (term_index, hit_index),
                }
                by_href[href] = item
            if term and term not in item["terms"]:
                item["terms"].append(term)
    return sorted(
        by_href.values(), key=lambda item: (-len(item["terms"]), item["order"])
    )


def render_exact(query, hits, fallback):
    """精确档的文字结果：同名几本全部列出，不替使用者挑。"""
    if hits:
        note = "（同名多本，未替你挑）" if len(hits) > 1 else ""
        lines = ["书名完全相同的 %d 本%s：" % (len(hits), note)]
        for index, hit in enumerate(hits, 1):
            lines.append(_line(index, hit))
        return "\n".join(lines)

    lines = ["没有书名完全相同的「%s」。" % query]
    if fallback:
        lines.append("")
        lines.append("搜索页返回的下面这些不是同名，供核对（最多 5 条）：")
        for hit in fallback[:5]:
            lines.append(_line(None, hit, indent="  - "))
        if len(fallback) > 5:
            lines.append("  ……还有 %d 条没列。" % (len(fallback) - 5))
    return "\n".join(lines)


def render_fuzzy(query, hits, capped):
    """模糊档的文字结果：标题含任意一个词的书，按页面顺序。"""
    tokens = (query or "").split()
    if len(tokens) == 1:
        what = "标题含「%s」的 %d 本" % (tokens[0], len(hits))
    else:
        what = "标题含%s的 %d 本" % (
            "或".join("「%s」" % token for token in tokens),
            len(hits),
        )
    lines = [what + "（页面顺序）："]
    for index, hit in enumerate(hits, 1):
        lines.append(_line(index, hit))
    if capped:
        lines.append("")
        lines.append("搜索页一页最多 40 条，可能还有；要更多用 --semantic 给一组相关词。")
    return "\n".join(lines)


def render_semantic(terms, per_term, merged):
    """语义档的文字结果：先按书合并列出，再按词报数量。"""
    total = sum(len(entry.get("hits") or []) for entry in per_term)
    lines = [
        "相关词 %d 个：%s" % (len(terms), "、".join(terms)),
        "各词命中合计 %d 条（每词最多 40 条），去重后 %d 本。" % (total, len(merged)),
    ]
    if len(terms) == 1:
        lines.append("")
        lines.append(
            "只搜了「%s」本身。要覆盖同义词，用 --terms 给一组相关词，例如：" % terms[0]
        )
        lines.append('  --terms "人工智能,大模型,机器学习"')
    if merged:
        lines.append("")
        for index, item in enumerate(merged, 1):
            lines.append(
                "%3d. 命中 %d 词（%s）  %s — %s"
                % (
                    index,
                    len(item["terms"]),
                    "、".join(item["terms"]),
                    item.get("title") or "",
                    item.get("author") or "作者未知",
                )
            )
            lines.append("     %s" % (item.get("href") or ""))
    else:
        lines.append("")
        lines.append(
            "这些词都没有搜到标题含它的书：%s。换一组相关词再试；"
            "或者用 --fuzzy 直接搜一个词。" % "、".join(terms)
        )
    lines.append("")
    lines.append("按词看：")
    for entry in per_term:
        hits = entry.get("hits") or []
        if not hits:
            note = "（0 条，换个词）"
        elif entry.get("capped"):
            note = "（满页，可能还有）"
        else:
            note = ""
        lines.append("  %s：%d 条%s" % (entry.get("term") or "", len(hits), note))
    return "\n".join(lines)


def _line(index, hit, indent=""):
    """一条结果占两行：标题 — 作者、阅读器地址。"""
    if index is None:
        head = "%s%s — %s" % (indent, hit.get("title") or "", hit.get("author") or "作者未知")
        tail = "%s    %s" % (indent, hit.get("href") or "")
    else:
        head = "%3d. %s — %s" % (index, hit.get("title") or "", hit.get("author") or "作者未知")
        tail = "     %s" % (hit.get("href") or "")
    return head + "\n" + tail
