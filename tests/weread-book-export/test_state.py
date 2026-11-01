#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""state.py 自己的测试。

    python -X utf8 tests/weread-book-export/test_state.py
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
from state import first_pending, load_state, mark_done, save_state  # noqa: E402


def leaves(n):
    return [{"index": i, "title": "章%d" % i, "parents": []} for i in range(n)]


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

    with tempfile.TemporaryDirectory() as d:
        eq("文件不存在时当作什么都没做", load_state(Path(d) / "nope.json"), {"done": []})

        p = Path(d) / "deep" / "state.json"
        save_state(p, {"done": [0, 1]})
        eq("存了能读回来", load_state(p), {"done": [0, 1]})
        eq("父目录不存在会自动建", p.exists(), True)

        Path(d, "broken.json").write_text("{ 这不是 json", encoding="utf-8")
        eq("文件内容坏了当作没做过，不抛错", load_state(Path(d, "broken.json")), {"done": []})

    before = {"done": [0]}
    after = mark_done(before, 2)
    eq("mark_done 不改原对象", before["done"], [0])
    eq("mark_done 加上新章号", after["done"], [0, 2])

    eq("first_pending 跳过已完成，中间有洞也能找回来",
       first_pending(leaves(5), {"done": [0, 1, 3]}), 2)
    eq("目录变短、余下的章号越界时忽略，不崩",
       first_pending(leaves(3), {"done": [0, 1, 2, 7, 8]}), -1)
    eq("全部做完返回 -1", first_pending(leaves(2), {"done": [0, 1]}), -1)

    print()
    if bad:
        print("%d 例没过" % bad)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
