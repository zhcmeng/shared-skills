#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""booklist.py 的测试：版本号、关键词、缓存路径。

    python -X utf8 tests/weread-book-export/test_booklist.py
"""

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
from booklist import (  # noqa: E402
    cache_dir,
    default_base_dir,
    parse_keywords,
    parse_skill_version,
    raw_cache_path,
    read_json,
    resolve_skill_version,
    write_json,
)


def main():
    bad = 0

    def eq(name, got, want):
        nonlocal bad
        if got != want:
            bad += 1
            print("[失败] %s" % name)
            print("       实际: %r" % (got,))
            print("       期望: %r" % (want,))
        else:
            print("[通过] %s" % name)

    def raises(name, func, needle):
        nonlocal bad
        try:
            func()
        except Exception as exc:
            if needle not in str(exc):
                bad += 1
                print("[失败] %s" % name)
                print("       报错里没有 %r：%s" % (needle, exc))
            else:
                print("[通过] %s" % name)
        else:
            bad += 1
            print("[失败] %s：没有报错" % name)

    eq("读版本号", parse_skill_version("---\nname: x\nversion: 1.0.6\n---\n"), "1.0.6")
    eq("没有版本号", parse_skill_version("---\nname: x\n---\n"), None)
    eq("空文本", parse_skill_version(""), None)

    eq(
        "参数优先",
        resolve_skill_version("9.9.9", "1.0.6", []),
        ("9.9.9", "参数"),
    )
    eq(
        "环境变量第二",
        resolve_skill_version(None, "1.0.6", []),
        ("1.0.6", "环境变量"),
    )

    tmp = Path(tempfile.mkdtemp())
    official = tmp / "SKILL.md"
    official.write_text("---\nversion: 1.0.7\n---\n", encoding="utf-8")
    eq(
        "读官方文件",
        resolve_skill_version(None, None, [tmp / "missing.md", official]),
        ("1.0.7", str(official)),
    )
    raises(
        "都取不到",
        lambda: resolve_skill_version(None, None, []),
        "WEREAD_SKILL_VERSION",
    )

    eq("一行一个词", parse_keywords("人工智能\n大模型\n"), ["人工智能", "大模型"])
    eq("逗号也拆", parse_keywords("人工智能,大模型，AI"), ["人工智能", "大模型", "AI"])
    eq("去空行去重", parse_keywords("\n人工智能\n\n人工智能\n大模型\n"), ["人工智能", "大模型"])
    eq("去 BOM 与回车", parse_keywords("\ufeff人工智能\r\n大模型\r\n"), ["人工智能", "大模型"])

    eq(
        "Windows 根目录",
        default_base_dir(
            env={"LOCALAPPDATA": "C:/Users/x/AppData/Local"}, platform_name="win32"
        ),
        Path("C:/Users/x/AppData/Local") / "weread-book-export",
    )
    eq(
        "其他系统根目录",
        default_base_dir(
            env={"XDG_CONFIG_HOME": "/home/x/.config"}, platform_name="linux"
        ),
        Path("/home/x/.config") / "weread-book-export",
    )
    eq(
        "主题目录",
        cache_dir("ai-impact", base=tmp),
        tmp / "booklist" / "ai-impact",
    )
    raises("空主题", lambda: cache_dir("  ", base=tmp), "主题")
    raises("主题带斜杠", lambda: cache_dir("a/b", base=tmp), "主题")

    p1 = raw_cache_path(tmp, "人工智能")
    p2 = raw_cache_path(tmp, "人工智能")
    p3 = raw_cache_path(tmp, "大模型")
    eq("同一词同一路径", p1, p2)
    eq("不同词不同路径", p1 == p3, False)
    eq("后缀是 json", p1.suffix, ".json")

    data = {"a": 1, "中文": "值"}
    target = tmp / "sub" / "x.json"
    write_json(target, data)
    eq("写读往返", read_json(target, None), data)
    eq("文件不存在", read_json(tmp / "none.json", {"d": 1}), {"d": 1})
    target.write_text("{坏", encoding="utf-8")
    eq("文件坏了", read_json(target, {"d": 2}), {"d": 2})

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
