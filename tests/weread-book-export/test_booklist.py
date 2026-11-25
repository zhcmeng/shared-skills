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
    render_booklist,
    resolve_skill_version,
    sort_books,
    validate_picks,
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

    details = {
        "1": {"bookId": "1", "title": "书一", "author": "甲", "newRating": 902,
              "newRatingCount": 1234, "readerLink": "https://r/1", "intro": "简介一"},
        "2": {"bookId": "2", "title": "书二", "author": "乙", "newRating": 880,
              "newRatingCount": 20, "deepLink": "https://d/2", "intro": ""},
        "3": {"bookId": "3", "title": "书三", "author": "丙", "newRating": 850,
              "newRatingCount": None, "intro": "简介三"},
    }
    meta = {"title": "AI 的影响", "keywords": ["AI", "大模型"], "min_rating": 700,
            "unique_books": 941, "candidates": 323}

    good = {
        "kept": [
            {"bookId": "1", "theme": "组织", "summary": "一句话", "reason": "论述组织变革"},
            {"bookId": "2", "theme": "经济", "reason": "无简介但主题相关"},
            {"bookId": "3", "theme": "组织", "summary": "另一句", "reason": "社会影响"},
        ],
        "dropped": [{"bookId": "4", "reason": "教程"}],
    }
    validate_picks(good, {"1", "2", "3", "4"}, details)

    raises("未知 bookId", lambda: validate_picks(
        {"kept": [{"bookId": "9", "theme": "组织", "summary": "x", "reason": "x"}], "dropped": []},
        {"1"}, details), "未知")
    raises("缺 reason", lambda: validate_picks(
        {"kept": [{"bookId": "1", "theme": "组织", "summary": "x"}], "dropped": []},
        {"1"}, details), "reason")
    raises("缺 theme", lambda: validate_picks(
        {"kept": [{"bookId": "1", "summary": "x", "reason": "x"}], "dropped": []},
        {"1"}, details), "theme")
    raises("有简介却缺 summary", lambda: validate_picks(
        {"kept": [{"bookId": "1", "theme": "组织", "reason": "x"}], "dropped": []},
        {"1"}, details), "summary")

    text = render_booklist(meta, good, details, top=20)
    eq("有标题", "AI 的影响" in text, True)
    eq("有计数", "941" in text and "323" in text, True)
    eq("有排名", "1. **《书一》**" in text, True)
    eq("有推荐值", "90.2%" in text, True)
    eq("有人数标注", "少于 50 人评分" in text, True)
    eq("有 readerLink", "https://r/1" in text, True)
    eq("有 deepLink", "https://d/2" in text, True)
    eq("空简介写暂无简介", "暂无简介" in text, True)

    grouped = render_booklist(meta, good, details, top=20, group=True)
    eq("分组有组织小节", "### 组织" in grouped, True)
    eq("分组有经济小节", "### 经济" in grouped, True)

    trimmed = render_booklist(meta, good, details, top=2)
    eq("截断到前 2", "1. **《书一》**" in trimmed and "2. **《书二》**" in trimmed and "书三" not in trimmed, True)

    fix_details = {
        "1": {"bookId": "1", "title": "书一", "author": "甲", "newRating": 902,
              "newRatingCount": 100, "readerLink": "https://r/1", "intro": "简介一"},
        "2": {"bookId": "2", "title": "书二", "author": "乙", "newRating": 880,
              "newRatingCount": 20, "intro": ""},
        "3": {"bookId": "3", "title": "书三", "author": "丙", "newRating": 850,
              "newRatingCount": 100, "intro": "简介三"},
    }
    fix_meta = {"title": "测试", "keywords": ["AI"], "min_rating": 700,
                "unique_books": 10, "candidates": 5}
    fix_picks = {
        "kept": [
            {"bookId": "1", "theme": "组织", "secondary": ["提效"],
             "summary": "一句话", "reason": "r"},
            {"bookId": "2", "theme": "经济", "reason": "r"},
            {"bookId": "3", "theme": "组织", "summary": "另一句", "reason": "r"},
        ],
        "dropped": [{"bookId": "4", "reason": "d"}, {"bookId": "5", "reason": "d"}],
    }
    fix_text = render_booklist(fix_meta, fix_picks, fix_details, top=20, shortlist_dropped=7)
    eq("次主题标出", "次主题：提效" in fix_text, True)
    eq("初筛去掉数", "初筛去掉 7 本" in fix_text, True)
    eq("精筛去掉数", "精筛去掉 2 本" in fix_text, True)
    eq("标题按实际本数", "共 3 本" in fix_text, True)

    failed_text = render_booklist(fix_meta, fix_picks, fix_details, top=20, failed_ids={"1"})
    eq("失败详情标注", "简介获取失败" in failed_text, True)
    eq("失败不用编的简述", "一句话" not in failed_text, True)

    no_link_picks = {
        "kept": [{"bookId": "3", "theme": "组织", "summary": "x", "reason": "r"}],
        "dropped": [],
    }
    no_link_text = render_booklist(
        fix_meta, no_link_picks, {"3": fix_details["3"]}, top=20
    )
    eq(
        "没有链接就不写",
        "打开阅读" not in no_link_text and "查看详情" not in no_link_text,
        True,
    )

    empty_text = render_booklist(fix_meta, {"kept": [], "dropped": []}, fix_details, top=20)
    eq("空榜单不崩", "共 0 本" in empty_text, True)

    raises("条目不是对象", lambda: validate_picks(
        {"kept": ["x"], "dropped": []}, {"1"}, fix_details), "对象")
    raises("次主题不是数组", lambda: validate_picks(
        {"kept": [{"bookId": "1", "theme": "组织", "summary": "x", "reason": "r",
                   "secondary": "提效"}], "dropped": []},
        {"1"}, fix_details), "secondary")

    eq(
        "只认 frontmatter",
        parse_skill_version("version: 9.9.9\n---\nversion: 1.0.6\n---\n"),
        None,
    )

    md = merge_details([{"bookId": "1", "title": "书一"}], {"1": "x"})
    eq("详情不是对象就跳过", md["1"]["title"], "书一")
    eq(
        "合并时跳过非对象",
        [b["bookId"] for b in merge_books([("AI", [{"bookId": "1"}, "x"])])],
        ["1"],
    )

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
