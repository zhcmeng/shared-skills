#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""weread_booklist.py 的命令行测试：check 与参数解析。

    python -X utf8 tests/weread-book-export/test_booklist_cli.py
"""

import argparse
import contextlib
import io
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 测试在仓库根 tests/ 下，脚本在 plugin/skills 里，所以往上两层
sys.path.insert(
    0,
    str(HERE.parent.parent / "plugin" / "skills" / "weread-book-export" / "scripts"),
)
import weread_booklist  # noqa: E402


def fake_payload(**overrides):
    data = {
        "results": [{"books": [{"bookInfo": {"bookId": "1", "title": "书"}}]}],
        "hasMore": 0,
    }
    data.update(overrides)
    return data


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

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
