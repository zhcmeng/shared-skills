# 核对转出来的 Markdown 有没有丢字——归档要求逐字保真，转换脚本会改结构，
# 必须验一遍「源 HTML 的每个字都还在」。
#
# 做法：两边都只留有内容的字符（去掉标签、Markdown 记号、图片地址、全部空白），
# 再用带顺序的比对找出缺失片段。多出来的片段应当是 Markdown 记号本身
# （加粗的 *、引用的 >、表格分隔线的 -），出现别的字符就说明转换掺了东西。
#
# 用法：python verify_fidelity.py <content.html> <out.md>
# 退出码：0 无缺失；1 有缺失（会把片段和上下文打出来）

import difflib
import re
import sys

from bs4 import BeautifulSoup


def html_text(path):
    soup = BeautifulSoup(open(path, encoding="utf-8").read(), "lxml")
    for el in soup.find_all(["style", "script"]):
        el.decompose()
    return soup.get_text()


def md_text(path):
    md = open(path, encoding="utf-8").read()
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)       # 图片整段去掉
    md = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", md)   # 链接只留文字
    md = re.sub(r"^\s{0,3}#{1,6}\s*", "", md, flags=re.M)   # 标题记号
    md = re.sub(r"^\s*[-*+]\s+", "", md, flags=re.M)        # 列表记号
    md = re.sub(r"^\s*\|.*$", lambda m: m.group(0).replace("|", ""), md, flags=re.M)  # 表格竖线
    md = re.sub(r"^\s*```.*$", "", md, flags=re.M)          # 代码围栏
    return md.replace("**", "").replace("`", "")


def squash(s):
    return re.sub(r"\s+", "", s)


def main():
    if len(sys.argv) != 3:
        print("用法：python verify_fidelity.py <content.html> <out.md>", file=sys.stderr)
        return 1

    a, b = squash(html_text(sys.argv[1])), squash(md_text(sys.argv[2]))
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)

    lost, added = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace") and i2 - i1:
            lost.append((i1, a[i1:i2]))
        if tag in ("insert", "replace") and j2 - j1:
            added.append((j1, b[j1:j2]))

    print(f"源 HTML 字符 {len(a)} | Markdown 字符 {len(b)}")
    print(f"缺失片段 {len(lost)} 个，合计 {sum(len(t) for _, t in lost)} 字符")
    for pos, t in lost[:20]:
        print(f"  @{pos} ...{a[max(0, pos - 25):pos]}[{t[:80]}]{a[pos + len(t):pos + len(t) + 25]}...")

    extra_chars = sorted(set("".join(t for _, t in added)))
    print(f"多出片段 {len(added)} 个，合计 {sum(len(t) for _, t in added)} 字符；"
          f"多出的字符集：{''.join(extra_chars)[:60]}")

    if lost:
        print("\n有缺失——转换漏了内容，别归档，先改转换脚本。")
        return 1
    print("\n无缺失。多出的字符若只限 *（加粗）> （引用）-（表格分隔线）与有序列表的数字，即为正常。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
