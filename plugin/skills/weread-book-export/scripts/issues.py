# -*- coding: utf-8 -*-
"""期刊各期：标题模板、缺号与清单渲染。不碰浏览器，纯逻辑。

为什么列全一个系列要逐期搜、而不是按「系列名 年份」搜一次：搜索页一次
最多回约 40 条，顺序不规则，还会把相关推荐混进来。用完整标题一期一期地
搜，每期结果都很少，天然绕开上限；再按标题**完全一致**比对，《第一财经》
这类名字里带相同字样的条目就挡在外面。
"""

import re

from matches import normalize_title

# 默认的标题写法，适用于《财经》《读者》这类按期号发行的杂志：
# 财经（2026年第5期）
DEFAULT_TEMPLATE = "{series}（{year}年第{n}期）"

_ISSUE_LIKE = re.compile(r"第\s*\d+\s*期")


def issue_title(template, series, year, n):
    """按模板拼出第 n 期的完整标题。"""
    return template.format(series=series, year=year, n=n)


def check_template(template):
    """确认模板能一期一期拼出不同标题；不能用就抛 ValueError。

    拿两个相邻期号各拼一次，比「模板里有没有 {n}」更可靠：`{n:02d}` 这种
    写法也带着 n，但没有 {n} 的字样。
    """
    try:
        first = issue_title(template, "示例", 2000, 1)
        second = issue_title(template, "示例", 2000, 2)
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError(
            "标题模板用不了（%s）。只能用 {series}、{year}、{n} 三个占位符，"
            "例如 %s。" % (exc, DEFAULT_TEMPLATE)
        ) from None
    if first == second:
        raise ValueError("标题模板里必须有 {n}，否则每一期搜的都是同一个标题。")
    return template


def gaps(issues):
    """从第 1 期到已找到的最大期号，缺了哪些号。

    最大期号以上不算缺号：那多半是还没出的期。
    """
    found = {item["n"] for item in issues}
    if not found:
        return []
    return [n for n in range(1, max(found) + 1) if n not in found]


def summary(issues):
    """一句话说清楚找全没有。"""
    if not issues:
        return "一期也没搜到。"
    top = max(item["n"] for item in issues)
    missing = gaps(issues)
    if not missing:
        return "第 1～%d 期都在，没有缺号。" % top
    return "第 1～%d 期里缺：%s。" % (top, "、".join("第 %d 期" % n for n in missing))


def pick_extras(hits, series, year, known_titles):
    """从一次普通搜索结果里挑出「另见」：年刊、专刊这类不按期号编的。

    条件：标题里同时有系列名和年份，又不是已经找到的那几期，也不像
    「第 N 期」的条目——那多半是名字里带相同字样的另一本杂志
    （《第一财经》《财经爆点》）。
    """
    known = {normalize_title(title) for title in known_titles}
    series_key = normalize_title(series)
    year_key = str(year)
    extras = []
    seen = set()
    for hit in hits:
        title = hit.get("title") or ""
        key = normalize_title(title)
        if series_key not in key or year_key not in key:
            continue
        if key in known or _ISSUE_LIKE.search(title):
            continue
        href = hit.get("href") or ""
        if not href or href in seen:
            continue
        seen.add(href)
        extras.append({"title": title, "url": href})
    return extras


def render_text(series, year, issues, extras=()):
    """给人看的清单：期号、标题、地址，末尾一句找全没有。"""
    lines = ["《%s》%s 年各期（共 %d 期）" % (series, year, len(issues)), ""]
    for item in issues:
        lines.append("%3d. %s" % (item["n"], item["title"]))
        for url in item["urls"]:
            lines.append("     %s" % url)
        if len(item["urls"]) > 1:
            lines.append("     （同名 %d 条，导出前先确认是哪一条）" % len(item["urls"]))
    lines.append("")
    lines.append(summary(issues))
    if extras:
        lines.append("")
        lines.append("另见（标题里有“%s”和“%s”，但不是按期号排的）：" % (series, year))
        for extra in extras:
            lines.append("  - %s" % extra["title"])
            lines.append("    %s" % extra["url"])
    return "\n".join(lines)


def _cell(text):
    """Markdown 表格里的一格：竖线要转义，否则会把表格切断。"""
    return (text or "").replace("|", "\\|")


def render_markdown(series, year, issues, extras=(), today=None):
    """写成 Markdown：一张期号表，另见条目单列一节。"""
    lines = ["# 《%s》%s 年各期" % (series, year), ""]
    lines.append("共 %d 期。" % len(issues) + ("截至 %s。" % today if today else ""))
    lines.append("")
    lines.append(summary(issues))
    lines.append("")
    if issues:
        lines.append("| 期 | 标题 | 阅读器地址 |")
        lines.append("|:--|:--|:--|")
        for item in issues:
            note = (
                "（同名 %d 条，需人工确认）" % len(item["urls"])
                if len(item["urls"]) > 1
                else ""
            )
            lines.append(
                "| %d | %s%s | %s |"
                % (item["n"], _cell(item["title"]), note, "<br>".join(item["urls"]))
            )
    if extras:
        lines.append("")
        lines.append("## 另见")
        lines.append("")
        lines.append(
            "标题里有“%s”和“%s”、但不是按期号排的条目"
            "（普通搜索顺带发现，受约 40 条上限影响，可能不全）：" % (series, year)
        )
        lines.append("")
        for extra in extras:
            lines.append("- %s — %s" % (extra["title"], extra["url"]))
    lines.append("")
    return "\n".join(lines)
