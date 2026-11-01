# -*- coding: utf-8 -*-
"""把一章的段落与图片拼成 Markdown，再拼出一本书的目录页。

注意：这个文件名与 PyPI 上的 ``markdown`` 包同名。技能目录排在
``sys.path`` 最前，取到的是这一份；不要把文件改名，也不要在脚本里
``import markdown`` 之外的用法上依赖那个第三方包。
"""

# 章名是文档里最外一层标题，章内标题依次往下降一级
CHAPTER_HEADING_LEVEL = 1


def _render_paragraph(paragraph):
    if paragraph["kind"] == "heading":
        return "%s %s" % (
            "#" * (paragraph["level"] + CHAPTER_HEADING_LEVEL),
            paragraph["text"],
        )
    return paragraph["text"]


def _render_image(image):
    return "![%s](images/%s)" % (image["alt"], image["file_name"])


def render_chapter(title, paragraphs, images):
    """一章一个 Markdown 文档。

    章名作一级标题；章内标题按 ``level`` 降一级，``level`` 1 是二级标题。
    每张图归到「最后一个 ``y`` 不大于图本身 ``y`` 的段落」之后；
    这样的段落一个都没有，就排在标题之后、所有段落之前。
    块与块之间空一行，文档以单个换行结尾。
    """
    blocks = ["# %s" % title]

    # 下标 i 的位置表示「第 i 段之后」，0 表示所有段落之前
    slots = [[] for _ in range(len(paragraphs) + 1)]
    for image in sorted(images, key=lambda img: img["y"]):
        slot = 0
        for i, paragraph in enumerate(paragraphs):
            if paragraph["y"] <= image["y"]:
                slot = i + 1
        slots[slot].append(_render_image(image))

    for i, paragraph in enumerate(paragraphs):
        blocks.extend(slots[i])
        blocks.append(_render_paragraph(paragraph))
    blocks.extend(slots[-1])

    return "\n\n".join(blocks) + "\n"


def render_readme(book_title, author, source_url, export_date, chapters):
    """一本书的目录页：书名、作者、来源、导出日期，然后按顺序链到每一章。

    ``parents`` 变了就插一行 ``### <最内层父级>``——带「部/篇」的书分成几节，
    层级的归属不丢。
    """
    blocks = [
        "# %s" % book_title,
        "作者：%s" % author,
        "来源：%s" % source_url,
        "导出日期：%s" % export_date,
        "## 目录",
    ]

    current_parent = None
    for chapter in chapters:
        parents = chapter.get("parents") or []
        parent = parents[-1] if parents else None
        if parent != current_parent:
            if parent is not None:
                blocks.append("### %s" % parent)
            current_parent = parent
        blocks.append("- [%s](./%s)" % (chapter["title"], chapter["file_name"]))

    return "\n\n".join(blocks) + "\n"
