# -*- coding: utf-8 -*-
"""把微信读书的目录拆成「一章一个文件」。

目录是树：一本带「部/篇」的书，上层是篇，下层才是章。导出按**最末级条目**
拆文件——目录里没有子项的条目各自成一个文件，一层目录的书按章拆，
带部/篇的书按最细一级拆，一套逻辑管两种。上级目录作为小标题记在
``parents`` 里，写进目录页时不丢层级。
"""

import re

# Windows 与 POSIX 都不接受的路径字符
ILLEGAL_CHARS = '\\/:*?"<>|'

# 章节文件名里标题部分最长的字数
MAX_TITLE_LEN = 40


def flatten_to_leaves(items):
    """把目录树摊平成叶子列表。

    参数 ``items``：``[{"title": str, "level": int}, ...]``，按目录顺序
    返回：``[{"index": int, "title": str, "parents": list[str]}, ...]``

    一个条目是叶子，当且仅当它后面紧邻的条目层级不比它更深（或它已是最后一条）。
    ``parents`` 是从外到内、层级逐级递减的那些条目标题。
    """
    leaves = []
    for i, item in enumerate(items):
        following = items[i + 1] if i + 1 < len(items) else None
        if following is not None and following["level"] > item["level"]:
            continue

        parents = []
        want = item["level"]
        for earlier in reversed(items[:i]):
            if earlier["level"] < want:
                parents.append(earlier["title"])
                want = earlier["level"]
        parents.reverse()

        leaves.append({"index": i, "title": item["title"], "parents": parents})
    return leaves


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
