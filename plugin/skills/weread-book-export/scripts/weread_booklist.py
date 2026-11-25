#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按主题与推荐度筛微信读书书单的命令行入口。

走微信读书 Agent API：``/store/search`` 批量搜、``/book/info`` 拉详情。
机械活（翻页、去重、过滤、缓存、渲染）在这里；主题相关性由模型判断。

    python weread_booklist.py check
    python weread_booklist.py search --topic ai --title "AI 的影响" \
        --context "找 AI 相关的书" --keywords-file words.txt
    python weread_booklist.py info --topic ai --shortlist shortlist.json
    python weread_booklist.py render --topic ai --picks picks.json
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from booklist import (
    cache_dir,
    filter_by_rating,
    flatten_books,
    merge_books,
    page_offset,
    parse_keywords,
    raw_cache_path,
    read_json,
    resolve_skill_version,
    write_json,
)

API = "https://i.weread.qq.com/api/agent/gateway"
# 被限流时的退避秒数；测试会把它 monkeypatch 成 0
RETRY_DELAYS = (10, 30)
PAGE_PAUSE = 0.5
INFO_PAUSE = 1.0


class ApiError(RuntimeError):
    """接口报错：HTTP 状态码、错误文本、回包里的 errcode。"""

    def __init__(self, status, message, errcode=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.errcode = errcode


def prefer_utf8(stream):
    """这一路输出被重定向走时，改成按 UTF-8 吐字节；真控制台不动。"""
    if stream.isatty():
        return
    if (getattr(stream, "encoding", "") or "").lower().replace("-", "") == "utf8":
        return
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


class _ArgumentParser(argparse.ArgumentParser):
    """参数写错按 1 退出。

    argparse 默认按 2 退出，这里的 2 留给了「要人来操作」（没设 Key），
    两者混在一起会让人把打错参数当成没配 Key。
    """

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, "%s: 参数错误：%s\n" % (self.prog, message))


def call_api(body, api_key, opener=urllib.request.urlopen, timeout=30):
    """调一次 Agent API，返回解析后的 JSON。"""
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(API, data=data, method="POST")
    request.add_header("Authorization", "Bearer " + api_key)
    request.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:
            pass
        raise ApiError(exc.code, detail or str(exc))
    except urllib.error.URLError as exc:
        raise ApiError(None, str(getattr(exc, "reason", exc)))
    errcode = payload.get("errcode")
    if errcode:
        raise ApiError(None, payload.get("errmsg") or str(errcode), errcode)
    return payload


def api_with_retry(body, api_key, retries=2, delays=None, **kwargs):
    """对限流（499）、网络错误、errcode 非 0 的情况重试。"""
    delays = RETRY_DELAYS if delays is None else delays
    last = None
    for attempt in range(retries + 1):
        try:
            return call_api(body, api_key, **kwargs)
        except ApiError as exc:
            retryable = exc.status == 499 or exc.status is None or bool(exc.errcode)
            if not retryable:
                raise
            last = exc
            if attempt < retries:
                pause = delays[attempt] if attempt < len(delays) else delays[-1]
                time.sleep(pause)
    raise last


def official_skill_paths():
    """官方 weread-skills 的 SKILL.md 可能在哪。"""
    home = Path.home()
    return [
        home / ".agents" / "skills" / "weread-skills" / "SKILL.md",
        home / ".claude" / "skills" / "weread-skills" / "SKILL.md",
    ]


def run_check(args):
    """检查 API Key、版本号与两个接口能不能用。"""
    api_key = os.environ.get("WEREAD_API_KEY")
    if not api_key:
        print("没设置 WEREAD_API_KEY；先设置环境变量再跑。")
        return 2
    try:
        version, source = resolve_skill_version(
            args.skill_version,
            os.environ.get("WEREAD_SKILL_VERSION"),
            official_skill_paths(),
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("skill_version：%s（来源：%s）" % (version, source))
    try:
        search = call_api(
            {
                "api_name": "/store/search",
                "keyword": "测试",
                "context": "检查接口可用性",
                "scope": 10,
                "count": 1,
                "skill_version": version,
            },
            api_key,
        )
        print("搜索接口：可用")
        books = flatten_books(search.get("results"))
        if books:
            call_api(
                {
                    "api_name": "/book/info",
                    "bookId": books[0]["bookId"],
                    "skill_version": version,
                },
                api_key,
            )
            print("详情接口：可用")
        else:
            print("详情接口：跳过（搜索结果里没有 bookId）")
    except ApiError as exc:
        print("接口不可用：%s" % exc, file=sys.stderr)
        return 1
    return 0


def run_search(args):
    """按关键词批量搜、翻页、去重、按推荐值过滤，写缓存与候选。"""
    api_key = os.environ.get("WEREAD_API_KEY")
    if not api_key:
        print("没设置 WEREAD_API_KEY；先设置环境变量再跑。")
        return 2
    try:
        version, _source = resolve_skill_version(
            args.skill_version,
            os.environ.get("WEREAD_SKILL_VERSION"),
            official_skill_paths(),
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        cache = cache_dir(args.topic, args.cache_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        text = Path(args.keywords_file).read_text(encoding="utf-8")
    except OSError as exc:
        print("读不了关键词文件：%s" % exc, file=sys.stderr)
        return 1
    keywords = parse_keywords(text)
    if not keywords:
        print("关键词文件里没有词。", file=sys.stderr)
        return 1

    per_keyword = []
    failed = []
    for keyword in keywords:
        path = raw_cache_path(cache, keyword)
        books = None
        if path.exists() and not args.refresh:
            books = read_json(path, None)
        if books is None:
            books = []
            try:
                for page in range(args.pages):
                    body = {
                        "api_name": "/store/search",
                        "keyword": keyword,
                        "context": args.context,
                        "scope": 10,
                        "count": args.count,
                        "skill_version": version,
                    }
                    offset = page_offset(page, args.count)
                    if offset:
                        body["maxIdx"] = offset
                    payload = api_with_retry(
                        body,
                        api_key,
                        retries=args.retries,
                        delays=RETRY_DELAYS,
                    )
                    books.extend(flatten_books(payload.get("results")))
                    if payload.get("hasMore") != 1:
                        break
                    time.sleep(PAGE_PAUSE)
            except ApiError as exc:
                failed.append(keyword)
                print("关键词「%s」失败：%s" % (keyword, exc), file=sys.stderr)
                continue
            write_json(path, books)
        per_keyword.append((keyword, books))
        time.sleep(args.interval)

    merged = merge_books(per_keyword)
    candidates = filter_by_rating(merged, args.min_rating)
    write_json(cache / "all_books.json", merged)
    write_json(cache / "candidates.json", candidates)
    meta = {
        "topic": args.topic,
        "title": args.title,
        "keywords": keywords,
        "min_rating": args.min_rating,
        "pages": args.pages,
        "count": args.count,
        "unique_books": len(merged),
        "candidates": len(candidates),
        "skill_version": version,
    }
    write_json(cache / "search_meta.json", meta)

    if failed:
        (cache / "failed.txt").write_text(
            "\n".join(failed) + "\n", encoding="utf-8"
        )
        print("有 %d 个关键词没搜成，结果不完整。" % len(failed))
        return 3
    failed_path = cache / "failed.txt"
    if failed_path.exists():
        failed_path.unlink()
    if not candidates:
        print("本次没有过线的书。")
    print(
        "检索 %d 个关键词，去重 %d 本；推荐值 %d%% 以上 %d 本。"
        % (len(keywords), len(merged), args.min_rating // 10, len(candidates))
    )
    return 0


def parse_args(argv=None):
    parser = _ArgumentParser(
        prog="weread_booklist.py",
        description="按主题与推荐度筛微信读书书单",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="检查 Key、版本号与接口可用性")
    check.add_argument("--skill-version", default=None)

    search = sub.add_parser("search", help="批量搜索、去重、按推荐值过滤")
    search.add_argument("--topic", required=True)
    search.add_argument("--title", required=True)
    search.add_argument("--context", required=True)
    search.add_argument("--keywords-file", required=True)
    search.add_argument("--min-rating", type=int, default=700)
    search.add_argument("--pages", type=int, default=3)
    search.add_argument("--count", type=int, default=50)
    search.add_argument("--interval", type=float, default=2.0)
    search.add_argument("--retries", type=int, default=2)
    search.add_argument("--refresh", action="store_true")
    search.add_argument("--cache-dir", default=None)
    search.add_argument("--skill-version", default=None)

    info = sub.add_parser("info", help="给初筛后的书拉详情")
    info.add_argument("--topic", required=True)
    info.add_argument("--shortlist", required=True)
    info.add_argument("--refresh", action="store_true")
    info.add_argument("--cache-dir", default=None)
    info.add_argument("--skill-version", default=None)

    render = sub.add_parser("render", help="渲染并落盘书单")
    render.add_argument("--topic", required=True)
    render.add_argument("--picks", required=True)
    render.add_argument("--top", type=int, default=20)
    render.add_argument("--group", action="store_true")
    render.add_argument("--min-ratings", type=int, default=0)
    render.add_argument("--out", default=None)
    render.add_argument("--cache-dir", default=None)

    return parser.parse_args(argv)


def main(argv=None):
    prefer_utf8(sys.stdout)
    prefer_utf8(sys.stderr)
    args = parse_args(argv)
    if args.command == "check":
        return run_check(args)
    if args.command == "search":
        return run_search(args)
    if args.command == "info":
        return run_info(args)
    return run_render(args)


if __name__ == "__main__":
    sys.exit(main())
