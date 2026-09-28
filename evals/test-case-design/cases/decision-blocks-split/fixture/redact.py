"""把一段文本里指定的词遮掉。

用法：python redact.py "文本" "要遮的词"
"""
import sys


def redact(text: str, word: str) -> str:
    return text.replace(word, "*" * len(word))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit('用法：python redact.py "文本" "要遮的词"')
    print(redact(sys.argv[1], sys.argv[2]))
