"""去掉一段文本首尾的空白。

用法：python trim.py "文本"
"""
import sys


def trim(text: str) -> str:
    return text.strip()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('用法：python trim.py "文本"')
    print(trim(sys.argv[1]))
