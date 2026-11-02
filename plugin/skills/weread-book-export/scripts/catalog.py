# -*- coding: utf-8 -*-
"""把微信读书的目录拆成「一章一个文件」。

目录是树：章下面是节，带「部/篇」的书上面还有一层篇。导出按**章**拆文件，
章里的节写成章文件内的小标题，不单独成文件。

哪一层是章，看标题：带「第 X 章」的那一层。一层都没有（有的书用「壹」「一」
或不编号），就按最深的一层拆。上级目录作为小标题记在 ``parents`` 里，
写进目录页时不丢层级。
"""

import collections
import re

# Windows 与 POSIX 都不接受的路径字符
ILLEGAL_CHARS = '\\/:*?"<>|'

# 章节文件名里标题部分最长的字数
MAX_TITLE_LEN = 40

# 章标题里的编号：第1章、第 1 章、第一章、第十二章……
CHAPTER_NUMBER = re.compile(r"第\s*[0-9〇零一二三四五六七八九十百千两]+\s*章")


def chapter_level(items):
    """目录里哪一层是「章」。

    标题带「第 X 章」的条目最多落在哪一层，那一层就是章。并列时取更浅的一层
    （有的书在节标题里也会写「第 X 章」）。一条都没有，就取最深的一层。
    """
    levels = collections.Counter(
        item["level"] for item in items if CHAPTER_NUMBER.search(item.get("title") or "")
    )
    if levels:
        return max(levels.items(), key=lambda pair: (pair[1], -pair[0]))[0]
    return max((item["level"] for item in items), default=1)


def _parents_of(items, i):
    """第 i 条的上级标题，从外到内。"""
    parents = []
    want = items[i]["level"]
    for earlier in reversed(items[:i]):
        if earlier["level"] < want:
            parents.append(earlier["title"])
            want = earlier["level"]
    parents.reverse()
    return parents


def _has_children(items, i):
    """第 i 条后面紧跟着层级更深的条目，就说明它有子项。"""
    return i + 1 < len(items) and items[i + 1]["level"] > items[i]["level"]


def flatten_to_chapters(items):
    """把目录树按「章」切开。

    参数 ``items``：``[{"title": str, "level": int}, ...]``，按目录顺序
    返回：``[{"index": int, "title": str, "level": int,
    "parents": list[str], "parts": list[dict]}, ...]``

    ``index`` 是这一章在完整目录里的下标，跳章时按它点目录。
    ``parts`` 是章下面的节（``{"index", "title", "level"}``，按目录顺序）；
    节的内容写进同一个章文件，用二级标题分开。
    比章更浅、又没有子项的那几条（版权信息、推荐序这类前置页）也算单独一章。
    """
    level = chapter_level(items)
    chapters = []
    for i, item in enumerate(items):
        is_chapter = item["level"] == level
        # 部/篇那一层的无子项条目是前置页或后记，不能漏掉
        lone = item["level"] < level and not _has_children(items, i)
        if not is_chapter and not lone:
            continue

        parts = []
        if is_chapter:
            for k in range(i + 1, len(items)):
                if items[k]["level"] <= item["level"]:
                    break
                parts.append(
                    {"index": k, "title": items[k]["title"], "level": items[k]["level"]}
                )

        chapters.append(
            {
                "index": i,
                "title": item["title"],
                "level": item["level"],
                "parents": _parents_of(items, i),
                "parts": parts,
            }
        )
    return chapters


def chapter_file_name(index, total, title):
    """章节文件名：``序号-标题.md``。

    序号按总章节数补零，同一本书里按文件名排序就是目录顺序；
    标题里不能进文件名的字符换成 ``-``，连续空白与 ``-`` 压成一个，
    去掉首尾的 ``-``，过长截到 40 字。
    """
    number = str(index + 1).zfill(max(2, len(str(total))))
    for char in ILLEGAL_CHARS:
        title = title.replace(char, "-")
    title = re.sub(r"[\s\-]+", "-", title).strip("-")
    title = title[:MAX_TITLE_LEN].strip("-")
    return "%s-%s.md" % (number, title)
