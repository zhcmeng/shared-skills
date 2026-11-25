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
    filter_by_rating,
    flatten_books,
    format_rating,
    merge_books,
    merge_details,
    page_offset,
    parse_keywords,
    parse_skill_version,
    rating_count_note,
    raw_cache_path,
    read_json,
    resolve_skill_version,
    sort_books,
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

    raw = [
        {"books": [
            {"bookInfo": {"bookId": "1", "title": "书一", "author": "甲", "newRating": 802, "newRatingCount": 100}},
            {"bookInfo": {"bookId": "2", "title": "书二", "author": "乙", "intro": None}},
        ]},
        {"books": [
            {"bookInfo": {"bookId": "3", "title": "书三"}, "newRating": 905, "newRatingCount": 7},
        ]},
    ]
    flat = flatten_books(raw)
    eq("扁平化条数", len(flat), 3)
    eq("评分在 bookInfo", flat[0]["newRating"], 802)
    eq("缺 bookInfo 评分时读顶层", flat[2]["newRating"], 905)
    eq("顶层评分人数", flat[2]["newRatingCount"], 7)
    eq("没有 bookId 的条目丢掉", len(flatten_books([{"books": [{"bookInfo": {}}]}])), 0)
    eq("空回包", flatten_books([]), [])

    merged = merge_books([("人工智能", flat[:2]), ("大模型", [flat[1], flat[2]])])
    eq("按 bookId 去重", len(merged), 3)
    eq("保留首次出现顺序", [b["bookId"] for b in merged], ["1", "2", "3"])
    eq("记录命中词", merged[1]["keywords"], ["人工智能", "大模型"])

    edge = [
        {"bookId": "a", "newRating": 699},
        {"bookId": "b", "newRating": 700},
        {"bookId": "c", "newRating": 701},
        {"bookId": "d"},
    ]
    eq("过线边界 700", [b["bookId"] for b in filter_by_rating(edge, 700)], ["b", "c"])
    eq("没有评分的丢掉", filter_by_rating([{"bookId": "x"}], 700), [])

    same = [
        {"bookId": "a", "title": "乙", "newRating": 800, "newRatingCount": 10},
        {"bookId": "b", "title": "甲", "newRating": 900, "newRatingCount": 5},
        {"bookId": "c", "title": "丙", "newRating": 900, "newRatingCount": 20},
    ]
    eq("按评分、人数、书名排序", [b["bookId"] for b in sort_books(same)], ["c", "b", "a"])

    eq("推荐值格式", format_rating(902), "90.2%")
    eq("0 分当没有评分", format_rating(0), "暂无评分")
    eq("None 当没有评分", format_rating(None), "暂无评分")
    eq("少于 50 人", rating_count_note(49), "少于 50 人评分")
    eq("刚好 50 人", rating_count_note(50), "")
    eq("人数未知", rating_count_note(None), "评分人数未知")

    eq("第一页偏移", page_offset(0, 50), 0)
    eq("第二页偏移", page_offset(1, 50), 50)
    eq("第三页偏移", page_offset(2, 50), 100)

    details = merge_details(
        [{"bookId": "1", "title": "书一", "newRating": 802}],
        {"1": {"intro": "简介", "category": "经济"}, "2": {"title": "书二"}},
    )
    eq("详情覆盖标题", details["1"]["title"], "书一")
    eq("详情补简介", details["1"]["intro"], "简介")
    eq("只有详情也保留", details["2"]["title"], "书二")

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
