"""把一段标题转成 URL 短名（slug）。

用法：python slugify.py "标题文本"
"""
import re
import sys


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^\w\-]", "", text, flags=re.UNICODE)
    return text


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('用法：python slugify.py "标题文本"')
    print(slugify(sys.argv[1]))
