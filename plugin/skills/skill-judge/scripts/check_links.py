#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查一个技能目录或 Markdown 文件里的本地链接目标是否存在。

用法：

    python check_links.py <技能目录或 Markdown 文件>
    python check_links.py --help        把这份说明打出来

给目录就递归扫目录下所有 `.md` / `.markdown`；给文件就只查那一份。
查的是内联写法 `[文字](目标)` 与 `![说明](目标)`；参考式链接
（`[文字][标记]` 加 `[标记]: 目标`）不在检查范围。

跳过这些目标（它们不是本地相对链接）：

- 带 scheme 的地址（`http://`、`https://`、`mailto:` 等），以及盘符路径
  （以字母加冒号开头的路径）、以 `/` 或 `\\` 开头的绝对路径、以 `//` 开头的协议相对地址；
- 纯锚点 `#...`；
- 空目标。

代码块（``` / ~~~ 围起来的部分）与行内代码（反引号里的内容）里的链接
不算——那是示例，不是真链接。

## 占位符

目标不存在时，先看它是不是模板里的占位符。是就单独列出来、不算坏链；
列出来是为了不静默放过：规则万一误判，人一眼能看见。占位符指下面任一条：

1. 目标里带模板符号 `{`、`}`、`<`、`>`、`*`；
2. 任一路径段的文件名主干以 `-x` 或 `-X` 结尾，如 `概念-x.md`；
3. 任一路径段的文件名主干是下面这些通用名之一：
   `路径`、`相对路径`、`路径名`、`页面名`、`文件名`、`目录名`、
   `文档名称`、`名称`、`标题`、`标题名`。

不在上面三条里的，一律按坏链报出来——拿不准时宁可供人判断，不静默放过。

输出：

    <文件>:<行号>: <链接目标>                坏链
    占位符（跳过） <文件>:<行号>: <链接目标>  占位符
    最后一行是统计

退出码：0 没有坏链；1 有坏链；2 用法不对、路径不存在或文件读不了。
"""

import re
import sys
from pathlib import Path
from urllib.parse import unquote

MARKDOWN_SUFFIXES = {".md", ".markdown"}

# 模板里的通用名，不是某个具体文件的名字。只收能确定是占位符的那几个；
# 拿不准的（如 xxx.md）不收，宁可当坏链报出来让人判断。
GENERIC_STEMS = {
    "路径",
    "相对路径",
    "路径名",
    "页面名",
    "文件名",
    "目录名",
    "文档名称",
    "名称",
    "标题",
    "标题名",
}

# 围栏代码块的开头标记，以及「这个地址带 scheme」的判断。盘符路径（以字母加冒号开头的路径）
# 也会被 scheme 那条认出来，一并跳过——它不是本地相对链接。
FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


def prefer_utf8(stream):
    """这一路输出被重定向走时，改成按 UTF-8 吐字节；真控制台不动。

    和仓库里其他技能脚本那份是同一套判断：Windows 中文版上标准流接的是
    管道时，Python 取的是区域编码 cp936，中文落成 GBK 字节，而接住它的一方
    一律按 UTF-8 解，屏幕上就是乱码。真控制台不切，那里的编码是 Python 按
    终端挑好的。流不认得 reconfigure（比如测试里的 StringIO）就放过。
    """
    if stream.isatty():
        return
    if (getattr(stream, "encoding", "") or "").lower().replace("-", "") == "utf8":
        return
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def strip_inline_code(line):
    """去掉行内代码，免得把文档里当示例写的链接当成真链接。

    反引号要成对、且两边的反引号个数一样才算一段代码（CommonMark 的规矩）。
    找不到配对的那一段原样留着——宁可多查，不静默漏掉。
    """
    out = []
    i = 0
    while i < len(line):
        if line[i] != "`":
            out.append(line[i])
            i += 1
            continue
        j = i
        while j < len(line) and line[j] == "`":
            j += 1
        width = j - i
        closing = _find_backtick_run(line, j, width)
        if closing is None:
            out.append(line[i:])
            break
        i = closing
    return "".join(out)


def _find_backtick_run(line, start, width):
    """找一段恰好 width 个反引号，返回它之后的位置；找不到返回 None。"""
    i = start
    while i < len(line):
        if line[i] != "`":
            i += 1
            continue
        j = i
        while j < len(line) and line[j] == "`":
            j += 1
        if j - i == width:
            return j
        i = j
    return None


def parse_link(line, marker):
    """解析 `](` 后面的目标，返回 (目标, 右括号之后的位置)；不像链接就返回 None。

    目标可以写成 `<带 空格.md>`；目标后面可以带标题（引号或圆括号包着）。
    目标里的圆括号允许成对出现（如 `foo(1).md`）。写不成形的目标不算链接——
    Markdown 渲染器也不会把它当链接。
    """
    n = len(line)
    i = marker + 2
    while i < n and line[i] in " \t":
        i += 1
    if i >= n:
        return None

    if line[i] == "<":
        close = line.find(">", i + 1)
        if close == -1:
            return None
        target = line[i + 1:close]
        i = close + 1
    else:
        begin = i
        depth = 0
        while i < n:
            ch = line[i]
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            elif ch in " \t" and depth == 0:
                break
            i += 1
        if i == begin:
            return None
        target = line[begin:i]

    j = i
    while j < n and line[j] in " \t":
        j += 1
    if j < n and line[j] in "\"'":
        close = line.find(line[j], j + 1)
        if close == -1:
            return None
        j = close + 1
    elif j < n and line[j] == "(":
        close = line.find(")", j + 1)
        if close == -1:
            return None
        j = close + 1
    while j < n and line[j] in " \t":
        j += 1
    if j >= n or line[j] != ")":
        return None
    return target, j + 1


def iter_links(text):
    """按行产出 (行号, 链接目标)，跳过围栏代码块里的内容。"""
    fence = None
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.lstrip(" ")
        indent = len(raw) - len(stripped)
        match = FENCE_RE.match(stripped)

        if fence is not None:
            if (match and match.group(1)[0] == fence[0]
                    and len(match.group(1)) >= fence[1]):
                fence = None
            continue

        if match and indent <= 3:
            fence = (match.group(1)[0], len(match.group(1)))
            continue

        line = strip_inline_code(raw)
        i = 0
        while True:
            marker = line.find("](", i)
            if marker == -1:
                break
            if marker > 0 and line[marker - 1] == "\\":
                i = marker + 2
                continue
            parsed = parse_link(line, marker)
            if parsed is None:
                i = marker + 2
                continue
            target, i = parsed
            if target:
                yield number, target


def is_non_local(target):
    """这个目标是不是根本不在本地相对路径的范围内。"""
    if not target:
        return True
    if target.startswith("#"):
        return True
    if target.startswith(("/", "\\")):
        return True
    if SCHEME_RE.match(target):
        return True
    return False


def is_placeholder(target):
    """目标是不是模板里的占位符。只看写法，不看文件在不在。"""
    path = target.split("#", 1)[0]
    if not path:
        return False
    if any(ch in path for ch in "{}<>*"):
        return True

    for segment in path.replace("\\", "/").split("/"):
        if segment in ("", ".", ".."):
            continue
        stem = segment
        dot = stem.rfind(".")
        if dot > 0:
            stem = stem[:dot]
        if stem in GENERIC_STEMS:
            return True
        if len(stem) > 2 and stem[-2:] in ("-x", "-X"):
            return True
    return False


def target_exists(base, local):
    """按 Markdown 文件所在目录解析相对路径；百分号编码的再解一次。"""
    candidates = [local]
    decoded = unquote(local)
    if decoded != local:
        candidates.append(decoded)
    return any((base / candidate).exists() for candidate in candidates)


def check_file(path):
    """查一份 Markdown，返回 (检查的链接数, 坏链, 占位符)。"""
    text = path.read_text(encoding="utf-8-sig")
    bad = []
    placeholders = []
    checked = 0
    base = path.parent

    for number, target in iter_links(text):
        if is_non_local(target):
            continue
        checked += 1
        local = target.split("#", 1)[0]
        if not local or target_exists(base, local):
            continue
        if is_placeholder(target):
            placeholders.append((path, number, target))
        else:
            bad.append((path, number, target))

    return checked, bad, placeholders


def collect_markdown(root):
    return sorted(
        (path for path in root.rglob("*")
         if path.is_file() and path.suffix.lower() in MARKDOWN_SUFFIXES),
        key=lambda path: str(path).lower(),
    )


def main(argv):
    if len(argv) == 1 and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    if len(argv) != 1:
        print("用法：python check_links.py <技能目录或 Markdown 文件>", file=sys.stderr)
        return 2

    root = Path(argv[0])
    if not root.exists():
        print("路径不存在：%s" % root, file=sys.stderr)
        return 2

    if root.is_file():
        if root.suffix.lower() not in MARKDOWN_SUFFIXES:
            print("不是 Markdown 文件：%s" % root, file=sys.stderr)
            return 2
        files = [root]
    else:
        files = collect_markdown(root)
        if not files:
            print("目录下没有 Markdown 文件：%s" % root, file=sys.stderr)
            return 2

    bad = []
    placeholders = []
    checked = 0
    read_failed = 0

    for path in files:
        try:
            count, file_bad, file_placeholders = check_file(path)
        except UnicodeDecodeError:
            print("读不了（不是 UTF-8）：%s" % path, file=sys.stderr)
            read_failed += 1
            continue
        except OSError as error:
            print("读不了：%s（%s）" % (path, error), file=sys.stderr)
            read_failed += 1
            continue
        checked += count
        bad.extend(file_bad)
        placeholders.extend(file_placeholders)

    for path, number, target in bad:
        print("%s:%d: %s" % (path, number, target))
    for path, number, target in placeholders:
        print("占位符（跳过） %s:%d: %s" % (path, number, target))

    if bad:
        print("检查了 %d 个 Markdown 文件、%d 条本地链接：%d 条坏链，%d 条占位符（跳过）。"
              % (len(files), checked, len(bad), len(placeholders)))
    else:
        print("检查了 %d 个 Markdown 文件、%d 条本地链接：没有坏链，%d 条占位符（跳过）。"
              % (len(files), checked, len(placeholders)))

    if read_failed:
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    prefer_utf8(sys.stdout)
    prefer_utf8(sys.stderr)
    sys.exit(main(sys.argv[1:]))
