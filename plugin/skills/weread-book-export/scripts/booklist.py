# -*- coding: utf-8 -*-
"""书单的纯逻辑：版本号、关键词、缓存路径。不碰网络，也不碰浏览器。

与官方 ``weread-skills`` 的约定：

- ``skill_version`` 从它的 ``SKILL.md`` frontmatter 里读，官方升级后自动跟上；
- 书单缓存放在 ``%LOCALAPPDATA%\\weread-book-export\\booklist\\<主题>\\``；
- 关键词文件一行一个，也接受中英文逗号分隔。
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

_VERSION_LINE = re.compile(r"^version:\s*(\S+)", re.MULTILINE)
_BOM = "﻿"


def parse_skill_version(text):
    """从官方 SKILL.md 的 frontmatter 里读 version；读不到返回 None。"""
    match = _VERSION_LINE.search(text or "")
    return match.group(1) if match else None


def resolve_skill_version(cli_value, env_value, paths):
    """按参数、环境变量、文件顺序取版本号，返回 ``(版本, 来源)``。"""
    if cli_value:
        return cli_value, "参数"
    if env_value:
        return env_value, "环境变量"
    for path in paths or []:
        path = Path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        version = parse_skill_version(text)
        if version:
            return version, str(path)
    raise ValueError(
        "找不到官方 weread-skills 的版本号；"
        "用 --skill-version 或环境变量 WEREAD_SKILL_VERSION 指定"
    )


def parse_keywords(text):
    """关键词文件：去 BOM，按行和逗号拆，trim、去空、按原样去重。"""
    text = (text or "").lstrip(_BOM)
    result = []
    for line in text.splitlines():
        for part in re.split(r"[,，]", line):
            part = part.strip()
            if part and part not in result:
                result.append(part)
    return result


def default_base_dir(env=None, platform_name=None):
    """配置与状态的根目录，和 ``browser.py`` 保持一致。"""
    env = os.environ if env is None else env
    platform_name = sys.platform if platform_name is None else platform_name
    if platform_name == "win32":
        root = env.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        root = env.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(root) / "weread-book-export"


def cache_dir(topic, base=None):
    """某个主题的缓存目录；主题必须是单层短名。"""
    topic = (topic or "").strip()
    if not topic or "/" in topic or "\\" in topic:
        raise ValueError("主题不能为空，也不能带斜杠")
    root = Path(base) if base else default_base_dir()
    return root / "booklist" / topic


def raw_cache_path(cache, keyword):
    """一个关键词的原始结果缓存路径。"""
    digest = hashlib.sha1((keyword or "").encode("utf-8")).hexdigest()[:16]
    return Path(cache) / "raw" / (digest + ".json")


def read_json(path, default):
    """读 JSON；不存在、读不动、坏 JSON 都返回 ``default``。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    """原子写 JSON：先写 ``.tmp`` 再替换。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
