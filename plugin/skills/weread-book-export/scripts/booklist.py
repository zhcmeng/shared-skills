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
    match = _VERSION_LINE.search(text or "")
    return match.group(1) if match else None


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
            book_id = (book or {}).get("bookId")
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
        book_id = (book or {}).get("bookId")
        if book_id:
            details[book_id] = dict(book)
    for book_id, info in (bookinfo or {}).items():
        item = details.setdefault(book_id, {"bookId": book_id})
        for key, value in (info or {}).items():
            if value not in (None, ""):
                item[key] = value
    return details
