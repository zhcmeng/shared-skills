# 微信公众号正文转 Markdown。输入是 fetch_article.mjs 取到的 article.content.html。
#
# 为什么不用 defuddle / 通用正文提取：它们按网页正文打分，会把公众号里当内容用的
# 元素当样板丢掉——实测一篇 21 张图的文章被吃掉 1 张（章节清单图），而那张图就是正文。
# 归档要求逐字保真，所以针对微信的排版习惯自己转。
#
# 微信排版的两个特点：
#   - <section> 既当块容器用（包一段文字、一张图），也当行内包裹用，要分开处理
#   - 图片真实地址在 data-src，src 可能是懒加载占位图
#
# 用法：python wechat_to_md.py <content.html> <out.md>

import re
import sys

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter


class WeChatConverter(MarkdownConverter):
    def convert_img(self, el, text, parent_tags):
        # 真实地址在 data-src；#imgIndex=N 是页面内的锚点，不属于资源本身
        src = (el.get("data-src") or el.get("src") or "").split("#")[0]
        if not src:
            return ""
        return f"\n\n![{el.get('alt') or '图片'}]({src})\n\n"

    def convert_pre(self, el, text, parent_tags):
        # 代码块里的内容原样保留，不按 Markdown 解析
        code = el.get_text().strip("\n")
        return f"\n\n```\n{code}\n```\n\n"


# 含这些子元素就说明这个 <section> 是块容器，不是行内包裹
BLOCK_CHILDREN = ["p", "ul", "ol", "table", "pre", "blockquote",
                  "h1", "h2", "h3", "h4", "h5", "h6", "div", "figure", "hr"]


def normalize_sections(root):
    """把 <section> 统一成可预测的标签，让每行文字各自成段。

    从最深层往外处理：含块级子元素的脱掉外壳（保留子元素），
    只含行内内容的降级成 <p>。反过来处理会把已经降级的 <p> 当成块级子元素，判断就乱了。
    """
    for sec in reversed(root.find_all("section")):
        if sec.find(BLOCK_CHILDREN):
            sec.unwrap()
        else:
            sec.name = "p"
    return root


def drop_empty(root):
    """去掉既没文字也没图片的段落，避免留下成片空行。"""
    for el in root.find_all(["p", "li", "section"]):
        if not el.get_text(strip=True) and not el.find("img"):
            el.decompose()
    return root


def convert(content_html: str) -> str:
    soup = BeautifulSoup(content_html, "lxml")
    root = soup.find(id="js_content") or soup.body or soup
    root.name = "div"
    root.attrs = {}

    normalize_sections(root)
    drop_empty(root)

    md = WeChatConverter(
        heading_style="ATX",
        bullets="-",
        strong_em_symbol="*",
        newline_style="SPACES",
        escape_asterisks=False,
        escape_underscores=False,
        escape_misc=False,
    ).convert_soup(root)

    md = re.sub(r"[ \t]+\n", "\n", md)
    return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


def main():
    if len(sys.argv) != 3:
        print("用法：python wechat_to_md.py <content.html> <out.md>", file=sys.stderr)
        return 1
    src, dst = sys.argv[1], sys.argv[2]
    md = convert(open(src, encoding="utf-8").read())
    open(dst, "w", encoding="utf-8", newline="\n").write(md)
    imgs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md)
    print(f"图片 {len(imgs)} 张 | 字符 {len(md)} | 表格行 {md.count('|')} -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
