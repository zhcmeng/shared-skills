# -*- coding: utf-8 -*-
"""续跑状态：记下这本书记到第几章了。

状态文件不放产出目录里，免得跟着书一起进版本库；默认落在
``%LOCALAPPDATA%\\weread-book-export\\state\\<slug>.json``。

``done`` 里存的是目录里的**原始下标**（``Leaf["index"]``），不是「第几个叶子」。
目录里带「部/篇」时叶子下标是不连续的，存原始下标才能回查回这一章。
"""

import json
import os
from pathlib import Path


def load_state(path):
    """读状态文件；文件不存在、读不动、内容坏了，一律当作什么都没做过。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {"done": []}

    if not isinstance(data, dict) or not isinstance(data.get("done"), list):
        return {"done": []}

    done = []
    for item in data["done"]:
        # bool 是 int 的子类，JSON 里的 true 不能当章号
        if isinstance(item, int) and not isinstance(item, bool):
            done.append(item)
    return {"done": done}


def save_state(path, state):
    """写状态文件：先写 ``.tmp`` 再替换，避免写到一半断电留下半个文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def mark_done(state, index):
    """把一章记成已完成，返回新状态；原对象不动。"""
    done = list(state.get("done") or [])
    if index not in done:
        done.append(index)
    new_state = dict(state)
    new_state["done"] = done
    return new_state


def first_pending(leaves, state):
    """按目录顺序找第一个没做完的叶子，返回它的 ``index``；全做完返回 -1。

    只认目录里真实存在的叶子，状态文件里越界的章号（目录变短了）自然被忽略。
    """
    done = set(state.get("done") or [])
    for leaf in leaves:
        if leaf["index"] not in done:
            return leaf["index"]
    return -1
