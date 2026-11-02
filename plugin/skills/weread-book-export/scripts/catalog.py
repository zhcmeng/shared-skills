# -*- coding: utf-8 -*-
"""把微信读书的目录拆成「一章一个文件」。

目录是树，层级由条目自己的 ``level`` 给出。导出按**最上层**的条目拆文件：
最浅那一层的每一条是一章，比它深的条目按目录顺序收进所属章的 ``parts``，
写成章文件里的二级标题。不按标题猜哪一层是章——有的书用「第 X 章」，有的用
「壹」「一」，还有根本不编号的书；层数才是目录本身给出的结构。
"""

import re

# Windows 与 POSIX 都不接受的路径字符
ILLEGAL_CHARS = '\\/:*?"<>|'

# 章节文件名里标题部分最长的字数
MAX_TITLE_LEN = 40


def flatten_to_chapters(items):
    """把目录按最上层条目切开。

    参数 ``items``：``[{"title": str, "level": int}, ...]``，按目录顺序
    返回：``[{"index": int, "title": str, "level": int,
    "parents": list[str], "parts": list[dict]}, ...]``

    ``index`` 是这一章在完整目录里的下标，跳章时按它点目录。
    ``parts`` 是最上层条目下面所有更深的条目（``{"index", "title", "level"}``，
    按目录顺序），内容写进同一个章文件。
    最上层的每一条都算一章，不管它叫「第2章」还是「第一级阶梯」；出现在第一条
    上层条目之前的更深条目没有归属，跳过。
    """
    top = min((item["level"] for item in items), default=1)
    chapters = []
    for i, item in enumerate(items):
        if item["level"] == top:
            chapters.append(
                {
                    "index": i,
                    "title": item["title"],
                    "level": item["level"],
                    "parents": [],
                    "parts": [],
                }
            )
        elif chapters:
            chapters[-1]["parts"].append(
                {"index": i, "title": item["title"], "level": item["level"]}
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
