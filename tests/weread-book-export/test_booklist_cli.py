#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""weread_booklist.py 的命令行测试：check 与参数解析。

    python -X utf8 tests/weread-book-export/test_booklist_cli.py
"""

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
import weread_booklist  # noqa: E402
from booklist import cache_dir, raw_cache_path  # noqa: E402


def fake_payload(**overrides):
    data = {
        "results": [{"books": [{"bookInfo": {"bookId": "1", "title": "书"}}]}],
        "hasMore": 0,
    }
    data.update(overrides)
    return data


def make_search_api(pages):
    calls = []

    def fake(body, key, **kw):
        calls.append(dict(body))
        page = (body.get("maxIdx") or 0) // body["count"]
        return {
            "results": [
                {
                    "books": [
                        {
                            "bookInfo": {
                                "bookId": "%s-%d-%d" % (body["keyword"], page, i),
                                "title": "%s 第 %d 页第 %d 本"
                                % (body["keyword"], page, i),
                                "newRating": 800 if i == 0 else 699,
                                "newRatingCount": 100,
                            }
                        }
                        for i in range(pages[page])
                    ]
                }
            ],
            "hasMore": 1 if page + 1 < len(pages) else 0,
        }

    return fake, calls


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

    original = weread_booklist.call_api
    original_env = os.environ.pop("WEREAD_API_KEY", None)
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = weread_booklist.run_check(
                argparse.Namespace(skill_version="1.0.6")
            )
        eq("缺 Key 退出 2", code, 2)
        eq("缺 Key 有提示", "WEREAD_API_KEY" in out.getvalue(), True)
    finally:
        if original_env is not None:
            os.environ["WEREAD_API_KEY"] = original_env

    os.environ["WEREAD_API_KEY"] = "wrk-test"
    try:
        weread_booklist.call_api = lambda body, key, **kw: fake_payload()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = weread_booklist.run_check(
                argparse.Namespace(skill_version="1.0.6")
            )
        eq("check 成功退出 0", code, 0)
        text = out.getvalue()
        eq("打印版本", "1.0.6" in text, True)
        eq("打印搜索可用", "搜索" in text, True)
        eq("打印详情可用", "详情" in text, True)

        original_resolve = weread_booklist.resolve_skill_version
        weread_booklist.resolve_skill_version = lambda *a: (_ for _ in ()).throw(
            ValueError("找不到版本号")
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = weread_booklist.run_check(
                argparse.Namespace(skill_version=None)
            )
        eq("版本号取不到退出 1", code, 1)
        eq(
            "报告版本号问题",
            "版本" in err.getvalue() or "WEREAD_SKILL_VERSION" in err.getvalue(),
            True,
        )
        weread_booklist.resolve_skill_version = original_resolve

        weread_booklist.call_api = lambda body, key, **kw: (_ for _ in ()).throw(
            weread_booklist.ApiError(499, "限流")
        )
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = weread_booklist.run_check(
                argparse.Namespace(skill_version="1.0.6")
            )
        eq("接口不可用退出 1", code, 1)
        eq("报告接口错误", "499" in err.getvalue() or "限流" in err.getvalue(), True)
    finally:
        os.environ.pop("WEREAD_API_KEY", None)
        weread_booklist.call_api = original

    with tempfile.TemporaryDirectory() as tmp:
        words = Path(tmp) / "words.txt"
        words.write_text("AI\n", encoding="utf-8")
        search_args = argparse.Namespace(
            topic="t",
            title="测试主题",
            context="测试",
            keywords_file=str(words),
            min_rating=700,
            pages=2,
            count=2,
            interval=0,
            retries=2,
            refresh=False,
            cache_dir=tmp,
            skill_version="1.0.6",
        )
        cache = cache_dir("t", base=tmp)
        old_pause = weread_booklist.PAGE_PAUSE
        old_delays = weread_booklist.RETRY_DELAYS
        weread_booklist.PAGE_PAUSE = 0
        os.environ["WEREAD_API_KEY"] = "wrk-test"
        try:
            fake, calls = make_search_api([2, 2])
            weread_booklist.call_api = fake
            code = weread_booklist.run_search(search_args)
            eq("search 成功退出 0", code, 0)
            eq("翻页请求次数", len(calls), 2)
            eq("第一页不带 maxIdx", "maxIdx" in calls[0], False)
            eq("第二页 maxIdx=2", calls[1].get("maxIdx"), 2)

            all_books = json.loads(
                (cache / "all_books.json").read_text(encoding="utf-8")
            )
            candidates = json.loads(
                (cache / "candidates.json").read_text(encoding="utf-8")
            )
            meta = json.loads(
                (cache / "search_meta.json").read_text(encoding="utf-8")
            )
            eq("去重后 4 本", len(all_books), 4)
            eq("过线 2 本", len(candidates), 2)
            eq("meta 关键词", meta["keywords"], ["AI"])
            eq("meta 去重数", meta["unique_books"], 4)
            eq("meta 过线数", meta["candidates"], 2)

            before = len(calls)
            code = weread_booklist.run_search(search_args)
            eq("缓存复用不重复请求", len(calls), before)
            eq("缓存复用仍退出 0", code, 0)

            search_args.refresh = True
            code = weread_booklist.run_search(search_args)
            eq("--refresh 会重搜", len(calls) > before, True)
            search_args.refresh = False

            state = {"n": 0}
            base, _ = make_search_api([2, 2])

            def flaky(body, key, **kw):
                if state["n"] == 0:
                    state["n"] += 1
                    raise weread_booklist.ApiError(499, "限流")
                return base(body, key, **kw)

            weread_booklist.call_api = flaky
            weread_booklist.RETRY_DELAYS = (0, 0)
            search_args.refresh = True
            code = weread_booklist.run_search(search_args)
            eq("499 重试后成功", code, 0)
            search_args.refresh = False

            def always_499(body, key, **kw):
                raise weread_booklist.ApiError(499, "限流")

            weread_booklist.call_api = always_499
            search_args.refresh = True
            code = weread_booklist.run_search(search_args)
            eq("全部失败退出 3", code, 3)
            eq(
                "failed.txt 有词",
                "AI" in (cache / "failed.txt").read_text(encoding="utf-8"),
                True,
            )
            search_args.refresh = False
            weread_booklist.RETRY_DELAYS = old_delays

            def low(body, key, **kw):
                return {
                    "results": [
                        {
                            "books": [
                                {
                                    "bookInfo": {
                                        "bookId": "x",
                                        "title": "低分",
                                        "newRating": 699,
                                        "newRatingCount": 10,
                                    }
                                }
                            ]
                        }
                    ],
                    "hasMore": 0,
                }

            weread_booklist.call_api = low
            search_args.refresh = True
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = weread_booklist.run_search(search_args)
            eq("零候选退出 0", code, 0)
            eq("零候选有提示", "本次没有过线的书" in out.getvalue(), True)
            eq(
                "零候选空列表",
                json.loads(
                    (cache / "candidates.json").read_text(encoding="utf-8")
                ),
                [],
            )
            search_args.refresh = False

            fake2, calls2 = make_search_api([2, 2])
            weread_booklist.call_api = fake2
            bad_path = raw_cache_path(cache, "AI")
            bad_path.parent.mkdir(parents=True, exist_ok=True)
            bad_path.write_text("{坏", encoding="utf-8")
            code = weread_booklist.run_search(search_args)
            eq("坏缓存会重搜", len(calls2) > 0, True)

            os.environ.pop("WEREAD_API_KEY", None)
            code = weread_booklist.run_search(search_args)
            eq("search 缺 Key 退出 2", code, 2)
            os.environ["WEREAD_API_KEY"] = "wrk-test"

            original_resolve = weread_booklist.resolve_skill_version
            weread_booklist.resolve_skill_version = lambda *a: (_ for _ in ()).throw(
                ValueError("找不到版本号")
            )
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = weread_booklist.run_search(search_args)
            eq("search 缺版本号退出 1", code, 1)
            weread_booklist.resolve_skill_version = original_resolve
        finally:
            os.environ.pop("WEREAD_API_KEY", None)
            weread_booklist.call_api = original
            weread_booklist.PAGE_PAUSE = old_pause
            weread_booklist.RETRY_DELAYS = old_delays

    with tempfile.TemporaryDirectory() as tmp:
        cache = cache_dir("t", base=tmp)
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "shortlist.json").write_text(
            json.dumps(
                {
                    "kept": [
                        {"bookId": "1", "reason": "相关"},
                        {"bookId": "2", "reason": "相关"},
                    ],
                    "dropped": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (cache / "search_meta.json").write_text(
            json.dumps(
                {
                    "title": "测试",
                    "keywords": ["AI"],
                    "min_rating": 700,
                    "unique_books": 1,
                    "candidates": 2,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        info_args = argparse.Namespace(
            topic="t",
            shortlist=str(cache / "shortlist.json"),
            refresh=False,
            cache_dir=tmp,
            skill_version="1.0.6",
        )
        old_pause = weread_booklist.INFO_PAUSE
        old_delays = weread_booklist.RETRY_DELAYS
        weread_booklist.INFO_PAUSE = 0
        weread_booklist.RETRY_DELAYS = (0, 0)
        os.environ["WEREAD_API_KEY"] = "wrk-test"
        try:
            calls = []

            def fake_info(body, key, **kw):
                calls.append(body["bookId"])
                if body["bookId"] == "1":
                    return {
                        "bookId": "1",
                        "title": "书一",
                        "author": "甲",
                        "intro": "简介",
                        "newRating": 900,
                        "newRatingCount": 100,
                        "readerLink": "https://r/1",
                    }
                raise weread_booklist.ApiError(499, "限流")

            weread_booklist.call_api = fake_info
            code = weread_booklist.run_info(info_args)
            eq("info 部分失败退出 3", code, 3)
            bookinfo = json.loads(
                (cache / "bookinfo.json").read_text(encoding="utf-8")
            )
            eq("成功的一本在", "1" in bookinfo, True)
            eq("失败的一本不在", "2" in bookinfo, False)
            eq(
                "failed_info 有 2",
                "2" in (cache / "failed_info.txt").read_text(encoding="utf-8"),
                True,
            )
            meta = json.loads(
                (cache / "search_meta.json").read_text(encoding="utf-8")
            )
            eq("meta info_ok", meta["info_ok"], 1)
            eq("meta info_failed", meta["info_failed"], 1)

            before = len(calls)
            code = weread_booklist.run_info(info_args)
            eq("第二次仍退出 3", code, 3)
            eq("已成功的不再请求", "1" not in calls[before:], True)
            eq("失败的会重试", "2" in calls[before:], True)

            with tempfile.TemporaryDirectory() as tmp2:
                cache2 = cache_dir("t", base=tmp2)
                cache2.mkdir(parents=True, exist_ok=True)
                (cache2 / "shortlist.json").write_text(
                    json.dumps(
                        {
                            "kept": [
                                {"bookId": "1", "reason": "x"},
                                {"bookId": "2", "reason": "x"},
                            ],
                            "dropped": [],
                        }
                    ),
                    encoding="utf-8",
                )
                (cache2 / "search_meta.json").write_text(
                    json.dumps({"title": "测试"}), encoding="utf-8"
                )
                args2 = argparse.Namespace(
                    topic="t",
                    shortlist=str(cache2 / "shortlist.json"),
                    refresh=False,
                    cache_dir=tmp2,
                    skill_version="1.0.6",
                )

                def always_fail(body, key, **kw):
                    raise weread_booklist.ApiError(499, "限流")

                weread_booklist.call_api = always_fail
                code = weread_booklist.run_info(args2)
                eq("全部失败退出 1", code, 1)

            with tempfile.TemporaryDirectory() as tmp3:
                cache3 = cache_dir("t", base=tmp3)
                cache3.mkdir(parents=True, exist_ok=True)
                (cache3 / "shortlist.json").write_text(
                    json.dumps(
                        {"kept": [{"bookId": "1", "reason": "x"}], "dropped": []}
                    ),
                    encoding="utf-8",
                )
                (cache3 / "search_meta.json").write_text(
                    json.dumps({"title": "测试"}), encoding="utf-8"
                )
                args3 = argparse.Namespace(
                    topic="t",
                    shortlist=str(cache3 / "shortlist.json"),
                    refresh=False,
                    cache_dir=tmp3,
                    skill_version="1.0.6",
                )

                def empty_intro(body, key, **kw):
                    return {"bookId": "1", "title": "书一", "intro": ""}

                weread_booklist.call_api = empty_intro
                code = weread_booklist.run_info(args3)
                eq("空简介退出 0", code, 0)
                info3 = json.loads(
                    (cache3 / "bookinfo.json").read_text(encoding="utf-8")
                )
                eq("空简介保留", info3["1"]["intro"], "")
        finally:
            os.environ.pop("WEREAD_API_KEY", None)
            weread_booklist.call_api = original
            weread_booklist.INFO_PAUSE = old_pause
            weread_booklist.RETRY_DELAYS = old_delays

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
