# -*- coding: utf-8 -*-
"""书单的纯逻辑：版本号、关键词、缓存路径。不碰网络，也不碰浏览器。

与官方 ``weread-skills`` 的约定：

- ``skill_version`` 从它的 ``SKILL.md`` frontmatter 里读，官方升级后自动跟上；
- 书单缓存放在 ``%LOCALAPPDATA%\\weread-book-export\\booklist\\<主题>\\``；
- 关键词文件一行一个，也接受中英文逗号分隔。
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

_VERSION_LINE = re.compile(r"^version:\s*(\S+)", re.MULTILINE)
_BOM = "﻿"


def parse_skill_version(text):
    """从官方 SKILL.md 的 frontmatter 里读 version；读不到返回 None。"""
    lines = (text or "").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = _VERSION_LINE.match(line)
        if match:
            return match.group(1)
    return None


def resolve_skill_version(cli_value, env_value, paths):
    """按参数、环境变量、文件顺序取版本号，返回 ``(版本, 来源)``。"""
    if cli_value:
        return cli_value, "参数"
    if env_value:
        return env_value, "环境变量"
    for path in paths or []:
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        version = parse_skill_version(text)
        if version:
            return version, str(path)
    raise ValueError(
        "找不到官方 weread-skills 的版本号；"
        "用 --skill-version 或环境变量 WEREAD_SKILL_VERSION 指定"
    )


def parse_keywords(text):
    """关键词文件：去 BOM，按行和逗号拆，trim、去空、按原样去重。"""
    text = (text or "").lstrip(_BOM)
    result = []
    for line in text.splitlines():
        for part in re.split(r"[,，]", line):
            part = part.strip()
            if part and part not in result:
                result.append(part)
    return result


def default_base_dir(env=None, platform_name=None):
    """配置与状态的根目录，和 ``browser.py`` 保持一致。"""
    env = os.environ if env is None else env
    platform_name = sys.platform if platform_name is None else platform_name
    if platform_name == "win32":
        root = env.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        root = env.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(root) / "weread-book-export"


def cache_dir(topic, base=None):
    """某个主题的缓存目录；主题必须是单层短名。"""
    topic = (topic or "").strip()
    if not topic or "/" in topic or "\\" in topic:
        raise ValueError("主题不能为空，也不能带斜杠")
    root = Path(base) if base else default_base_dir()
    return root / "booklist" / topic


def raw_cache_path(cache, keyword):
    """一个关键词的原始结果缓存路径。"""
    digest = hashlib.sha1((keyword or "").encode("utf-8")).hexdigest()[:16]
    return Path(cache) / "raw" / (digest + ".json")


def read_json(path, default):
    """读 JSON；不存在、读不动、坏 JSON 都返回 ``default``。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    """原子写 JSON：先写 ``.tmp`` 再替换。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def flatten_books(results):
    """把 ``/store/search`` 的 ``results`` 分组扁平化成书籍数组。

    评分与评分人数先读 ``bookInfo``，为空再读条目顶层；``intro`` 不保留，
    搜索结果里本来也没有。
    """
    books = []
    for group in results or []:
        for item in (group or {}).get("books") or []:
            info = item.get("bookInfo") or {}
            book_id = info.get("bookId")
            if not book_id:
                continue
            rating = info.get("newRating")
            if rating is None:
                rating = item.get("newRating")
            rating_count = info.get("newRatingCount")
            if rating_count is None:
                rating_count = item.get("newRatingCount")
            books.append(
                {
                    "bookId": book_id,
                    "title": info.get("title"),
                    "author": info.get("author"),
                    "translator": info.get("translator"),
                    "deepLink": info.get("deepLink"),
                    "readerLink": info.get("readerLink"),
                    "newRating": rating,
                    "newRatingCount": rating_count,
                    "soldout": info.get("soldout"),
                }
            )
    return books


def merge_books(per_keyword):
    """按 ``bookId`` 合并多个关键词的结果，保留首次出现顺序。

    ``per_keyword`` 是 ``[(keyword, books), ...]``；每本书记下命中的词，
    后面写主题标签时用得上。
    """
    by_id = {}
    order = []
    for keyword, books in per_keyword or []:
        for book in books or []:
            if not isinstance(book, dict):
                continue
            book_id = book.get("bookId")
            if not book_id:
                continue
            item = by_id.get(book_id)
            if item is None:
                item = dict(book)
                item["keywords"] = [keyword] if keyword else []
                by_id[book_id] = item
                order.append(book_id)
            elif keyword and keyword not in item["keywords"]:
                item["keywords"].append(keyword)
    return [by_id[book_id] for book_id in order]


def filter_by_rating(books, min_rating):
    """留下推荐值达到 ``min_rating`` 的书；没有评分的丢掉。"""
    return [
        book
        for book in books or []
        if book.get("newRating") is not None and book["newRating"] >= min_rating
    ]


def sort_books(books):
    """按推荐值、评分人数、书名排序。"""
    return sorted(
        books or [],
        key=lambda book: (
            -(book.get("newRating") or 0),
            -(book.get("newRatingCount") or 0),
            book.get("title") or "",
        ),
    )


def format_rating(value):
    """把 0-1000 的推荐值写成 ``90.2%``；0 或缺失当没有评分。"""
    if value is None or value == 0:
        return "暂无评分"
    return "%.1f%%" % (value / 10)


def rating_count_note(count):
    """评分人数少于 50 或未知时给一句标注，否则空串。"""
    if count is None:
        return "评分人数未知"
    if count < 50:
        return "少于 50 人评分"
    return ""


def page_offset(page_index, count):
    """第几页（从 0 起）对应的 ``maxIdx``。"""
    return page_index * count


def merge_details(candidates, bookinfo):
    """把候选书与 ``/book/info`` 的详情合成一张 ``bookId -> 书`` 的表。

    详情里的非空字段覆盖候选书的同名字段；只有详情、没有候选的书也保留。
    """
    details = {}
    for book in candidates or []:
        if not isinstance(book, dict):
            continue
        book_id = book.get("bookId")
        if book_id:
            details[book_id] = dict(book)
    if not isinstance(bookinfo, dict):
        bookinfo = {}
    for book_id, info in bookinfo.items():
        if not isinstance(info, dict):
            continue
        item = details.setdefault(book_id, {"bookId": book_id})
        for key, value in info.items():
            if value not in (None, ""):
                item[key] = value
    return details


def validate_picks(picks, known_ids, details):
    """校验 ``picks.json``；不合法时抛 ``ValueError``，报错里带字段名。"""
    if not isinstance(picks, dict):
        raise ValueError("picks.json 必须是对象")
    kept = picks.get("kept")
    dropped = picks.get("dropped") or []
    if not isinstance(kept, list) or not isinstance(dropped, list):
        raise ValueError("picks.json 的 kept 与 dropped 必须是数组")

    def check_entry(entry, group):
        if not isinstance(entry, dict):
            raise ValueError("%s 里的条目必须是对象" % group)
        book_id = entry.get("bookId")
        if not book_id:
            raise ValueError("%s 里有条目缺 bookId" % group)
        if book_id not in known_ids:
            raise ValueError("%s 里有未知 bookId：%s" % (group, book_id))
        return book_id

    for entry in kept:
        book_id = check_entry(entry, "kept")
        if not (entry.get("theme") or "").strip():
            raise ValueError("kept 里的 %s 缺 theme" % book_id)
        secondary = entry.get("secondary")
        if secondary is not None:
            if not isinstance(secondary, list) or any(
                not isinstance(word, str) for word in secondary
            ):
                raise ValueError(
                    "kept 里的 %s 的 secondary 必须是字符串数组" % book_id
                )
        if not (entry.get("reason") or "").strip():
            raise ValueError("kept 里的 %s 缺 reason" % book_id)
        intro = (details.get(book_id) or {}).get("intro")
        if intro and not (entry.get("summary") or "").strip():
            raise ValueError("kept 里的 %s 有简介却缺 summary" % book_id)

    for entry in dropped:
        book_id = check_entry(entry, "dropped")
        if not (entry.get("reason") or "").strip():
            raise ValueError("dropped 里的 %s 缺 reason" % book_id)


def format_threshold(value):
    """把推荐值下限写成 ``70%`` 或 ``70.6%``。"""
    text = "%.1f" % ((value if value is not None else 700) / 10)
    if text.endswith(".0"):
        text = text[:-2]
    return text + "%"


def _render_entry(index, entry, book, failed=False):
    """渲染榜单里的一条。"""
    title = book.get("title") or "书名缺失"
    author = book.get("author") or "作者未知"
    rating = format_rating(book.get("newRating"))
    count = book.get("newRatingCount")
    if count is None:
        count_text = "评分人数未知"
    else:
        count_text = "%s 人评分" % format(count, ",")
        note = rating_count_note(count)
        if note:
            rating = "%s（%s）" % (rating, note)
    theme = (entry.get("theme") or "未分类").strip() or "未分类"
    theme_text = "主题：%s" % theme
    secondary = entry.get("secondary")
    if isinstance(secondary, list) and secondary:
        theme_text += "；次主题：%s" % "、".join(secondary)
    lines = [
        "%d. **《%s》** %s · 推荐值 %s · %s · %s"
        % (index, title, author, rating, count_text, theme_text)
    ]
    if book.get("readerLink"):
        lines.append("[打开阅读](%s)" % book["readerLink"])
    elif book.get("deepLink"):
        lines.append("[查看详情](%s)" % book["deepLink"])
    if failed:
        lines.append("简介获取失败")
    else:
        summary = (entry.get("summary") or "").strip()
        lines.append(summary or "暂无简介")
    return lines


def render_booklist(
    meta,
    picks,
    details,
    top=20,
    group=False,
    failed_ids=None,
    shortlist_dropped=None,
):
    """把 ``picks`` 与详情渲染成 Markdown 榜单。"""
    meta = meta or {}
    failed_ids = set(failed_ids or [])
    all_kept = []
    for entry in (picks or {}).get("kept") or []:
        book = details.get(entry.get("bookId")) or {}
        all_kept.append((entry, book))
    all_kept.sort(
        key=lambda pair: (
            -(pair[1].get("newRating") or 0),
            -(pair[1].get("newRatingCount") or 0),
            pair[1].get("title") or "",
        )
    )
    shown = min(top, len(all_kept))
    rows = all_kept[:top]

    min_rating = meta.get("min_rating")
    if min_rating is None:
        min_rating = 700
    title = meta.get("title") or meta.get("topic") or "主题书单"
    scope = ("共 %d 本" % shown) if shown < top else ("前 %d 本" % top)
    lines = [
        "## %s：推荐值 %s 以上的%s"
        % (title, format_threshold(min_rating), scope),
        "",
    ]
    parts = [
        "检索 %d 个关键词" % len(meta.get("keywords") or []),
        "去重 %d 本" % (meta.get("unique_books") or 0),
        "推荐值 %s 以上 %d 本"
        % (format_threshold(min_rating), meta.get("candidates") or 0),
    ]
    count_line = "，".join(parts) + "；按书名与简介筛掉教程、案例集、传记等；"
    if shortlist_dropped is not None:
        count_line += "初筛去掉 %d 本，" % shortlist_dropped
    count_line += "精筛去掉 %d 本；留下 %d 本，按推荐值排序。" % (
        len((picks or {}).get("dropped") or []),
        len(rows),
    )
    lines.append(count_line)
    lines.append("")

    if group:
        themes = []
        buckets = {}
        for entry, book in rows:
            theme = (entry.get("theme") or "未分类").strip() or "未分类"
            if theme not in buckets:
                buckets[theme] = []
                themes.append(theme)
            buckets[theme].append((entry, book))
        for theme in themes:
            lines.append("### %s" % theme)
            lines.append("")
            for index, (entry, book) in enumerate(buckets[theme], 1):
                lines.extend(
                    _render_entry(
                        index, entry, book, entry.get("bookId") in failed_ids
                    )
                )
                lines.append("")
    else:
        for index, (entry, book) in enumerate(rows, 1):
            lines.extend(
                _render_entry(index, entry, book, entry.get("bookId") in failed_ids)
            )
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
