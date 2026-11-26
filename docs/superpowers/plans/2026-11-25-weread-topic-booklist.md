# weread-book-export 主题书单 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `weread-book-export` 加一条走微信读书 Agent API 的「按主题与推荐度筛书单」能力：脚本做检索、翻页、去重、过滤、拉详情、排序、渲染，模型做主题相关性判断、主题标签和一句话简述。

**Architecture:** 新增 `scripts/booklist.py`（纯逻辑，可单测）和 `scripts/weread_booklist.py`（命令行、HTTP、缓存）。命令行分 `check`、`search`、`info`、`render` 四步，中间产物是 JSON 交接文件。官方 `weread-skills` 一个字不动，只读它的 `SKILL.md` 取版本号。

**Tech Stack:** Python 3 标准库（`urllib`、`json`、`hashlib`、`argparse`）；沿用技能现有的脚本与测试写法，不引入 Playwright、不引入 pytest。

**Spec:** `docs/superpowers/specs/2026-11-25-weread-topic-booklist-design.md`

## Global Constraints

- 新建脚本只用 Python 标准库；不 import `browser.py`（那会拉起 Playwright）。
- 官方 `~/.agents/skills/weread-skills/` 与 `~/.claude/skills/weread-skills/` 一个字不改。
- 每次请求 body 必须带 `skill_version`，值按「`--skill-version` → `WEREAD_SKILL_VERSION` → 官方 `SKILL.md` 的 `version`」顺序取；都取不到时退出 1。
- `newRating` 是 0-1000，`>= 700` 是推荐值 70%；字段先读 `bookInfo`，再退回条目顶层。
- 翻页 `maxIdx = 页数 × count`（0、50、100），不用 `searchIdx` 当游标。
- 搜索结果没有 `category`、`publisher`、`intro`；初筛只用书名和作者，分类、出版方、简介在拉详情后用。
- 缓存与成品写在 `%LOCALAPPDATA%\weread-book-export\booklist\<主题>\`；`--cache-dir`、`--out` 可改。
- 退出码：0 跑完；2 没设 `WEREAD_API_KEY`；3 部分失败、结果不完整；1 参数或内部错误。
- 新增文件不含非 BMP 字符（emoji、补充平面汉字等）。
- 提交信息用中文；不加 `Co-Authored-By` 或「Generated with」这类署名。
- 版本号两处（`plugin/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`）一起抬到 `1.35.3`，只在最后一个任务抬。
- 测试放 `tests/weread-book-export/`，不在 `plugin/` 下留测试文件、缓存或 `__pycache__`。

## Review Focus

- **HTTP 499（限流）后能否继续。** 用户连续刷很多关键词时会被限流；脚本要退避重试，重试后仍失败的词记下来，其余词照常跑完，退出 3。测试放在 Task 5。
- **缓存文件坏了。** 上次运行写到一半、或换了格式；`read_json` 读不动时要当作没有缓存，重搜这个词，不能整条命令崩掉。测试放在 Task 5。
- **关键词文件带 BOM 或 CRLF。** Windows 记事本存出来的文件很常见；解析时要去 BOM、去 `\r`，否则第一个词会带不可见字符、搜不到。测试放在 Task 1。
- **没有 `readerLink`。** 回包可能只给 `deepLink` 或两个都不给；渲染时不能自己拼链接，也不能留空括号。测试放在 Task 3。
- **一本书也没过推荐值线。** 搜到书了但都低于 700；要正常退出 0，打印「本次没有过线的书」，不能报错、也不能写半份榜单。测试放在 Task 5。

---

### Task 1: 纯逻辑：版本号、关键词、缓存路径

**Files:**
- Create: `plugin/skills/weread-book-export/scripts/booklist.py`
- Test: `tests/weread-book-export/test_booklist.py`

**Interfaces:**
- Consumes: 无。
- Produces:
  - `parse_skill_version(text: str) -> str | None`
  - `resolve_skill_version(cli_value, env_value, paths) -> tuple[str, str]`
  - `parse_keywords(text: str) -> list[str]`
  - `default_base_dir(env=None, platform_name=None) -> Path`
  - `cache_dir(topic: str, base=None) -> Path`
  - `raw_cache_path(cache: Path, keyword: str) -> Path`
  - `read_json(path: Path, default)` -> 解析结果；读不动或不存在时返回 `default`
  - `write_json(path: Path, data) -> None`（先写 `.tmp` 再 `os.replace`）

- [ ] **Step 1: 写失败的测试**

新建 `tests/weread-book-export/test_booklist.py`，照 `test_matches.py` 的写法：自己写 `eq` / `raises`，末尾 `main()` 返回 0 或 1。先只放这一组：

```python
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
        default_base_dir(env={"LOCALAPPDATA": "C:/Users/x/AppData/Local"}, platform_name="win32"),
        Path("C:/Users/x/AppData/Local") / "weread-book-export",
    )
    eq(
        "其他系统根目录",
        default_base_dir(env={"XDG_CONFIG_HOME": "/home/x/.config"}, platform_name="linux"),
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
```

文件顶部要导入 `tempfile`、`Path`、`sys`，并把 `plugin/skills/weread-book-export/scripts` 加进 `sys.path`，写法照 `test_search_cli.py`。

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_booklist.py`
Expected: FAIL，`ModuleNotFoundError: No module named 'booklist'`

- [ ] **Step 3: 实现 `booklist.py`**

- `parse_skill_version`：用正则 `^version:\s*(\S+)` 按行匹配，只认 frontmatter 里的那一行；找不到返回 `None`。
- `resolve_skill_version`：按参数、环境变量、文件路径顺序取；文件用 `parse_skill_version` 读；都取不到抛 `ValueError`，报错里带 `WEREAD_SKILL_VERSION`。
- `parse_keywords`：先 `lstrip("\ufeff")`；按行拆，再按中英文逗号拆；`strip()` 后丢空串；按原样去重、保留首次出现的顺序。
- `default_base_dir`：照 `browser.py` 的逻辑复制一份（不能 import，会拉起 Playwright）；`env`、`platform_name` 可注入，默认取 `os.environ`、`sys.platform`。
- `cache_dir`：`(base or default_base_dir()) / "booklist" / topic`；主题为空或含 `/`、`\` 时抛 `ValueError`。
- `raw_cache_path`：`cache / "raw" / (sha1(keyword.encode("utf-8")).hexdigest()[:16] + ".json")`。
- `read_json`：读不动、不存在、不是合法 JSON，都返回 `default`。
- `write_json`：建父目录，先写 `path.name + ".tmp"`，再 `os.replace`。

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -X utf8 tests/weread-book-export/test_booklist.py`
Expected: `全部通过`

- [ ] **Step 5: 提交**

```bash
git add plugin/skills/weread-book-export/scripts/booklist.py tests/weread-book-export/test_booklist.py
git commit -m "feat(weread): 新增书单纯逻辑的版本号、关键词与缓存路径"
```

---

### Task 2: 纯逻辑：搜索回包整理

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/booklist.py`
- Test: `tests/weread-book-export/test_booklist.py`

**Interfaces:**
- Consumes: Task 1 的模块。
- Produces:
  - `flatten_books(results) -> list[dict]`，每项键：`bookId`、`title`、`author`、`translator`、`deepLink`、`readerLink`、`newRating`、`newRatingCount`、`soldout`
  - `merge_books(per_keyword) -> list[dict]`，`per_keyword` 是 `[(keyword, books), ...]`；按 `bookId` 合并，加 `keywords` 列表
  - `filter_by_rating(books, min_rating) -> list[dict]`
  - `sort_books(books) -> list[dict]`
  - `format_rating(value) -> str`
  - `rating_count_note(count) -> str`
  - `page_offset(page_index, count) -> int`
  - `merge_details(candidates, bookinfo) -> dict[str, dict]`

- [ ] **Step 1: 写失败的测试**

在 `test_booklist.py` 的 `main()` 里、`print()` 汇总之前加：

```python
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
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_booklist.py`
Expected: FAIL，`NameError: name 'flatten_books' is not defined`

- [ ] **Step 3: 实现**

- `flatten_books`：遍历 `results` 的每个分组，再遍历 `books`；取 `bookInfo`；没有 `bookId` 的条目丢掉。评分先读 `bookInfo.newRating`，为空再读条目顶层；评分人数同理。`intro` 不保留。
- `merge_books`：按 `bookId` 建索引；第一次出现的书复制一份并加 `keywords: [keyword]`；再次出现时只把新词追加进 `keywords`，其它字段不动。
- `filter_by_rating`：`newRating is not None and newRating >= min_rating`；没有评分的丢掉。
- `sort_books`：键 `(-(newRating or 0), -(newRatingCount or 0), title or "")`。
- `format_rating`：`None` 或 `0` 返回 `"暂无评分"`；否则 `"%.1f%%" % (value / 10)`。
- `rating_count_note`：`None` 返回 `"评分人数未知"`；`< 50` 返回 `"少于 50 人评分"`；否则空串。
- `page_offset`：`page_index * count`。
- `merge_details`：先用 `candidates` 建 `bookId -> dict`；再把 `bookinfo` 里的非空字段覆盖进去；只有详情、没有候选的书也保留。

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -X utf8 tests/weread-book-export/test_booklist.py`
Expected: `全部通过`

- [ ] **Step 5: 提交**

```bash
git add plugin/skills/weread-book-export/scripts/booklist.py tests/weread-book-export/test_booklist.py
git commit -m "feat(weread): 书单整理支持扁平化、去重、评分过滤与排序"
```

---

### Task 3: 纯逻辑：交接文件校验与榜单渲染

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/booklist.py`
- Test: `tests/weread-book-export/test_booklist.py`

**Interfaces:**
- Consumes: Task 1、Task 2 的函数。
- Produces:
  - `validate_picks(picks, known_ids, details) -> None`，不合法时抛 `ValueError`
  - `render_booklist(meta, picks, details, top=20, group=False) -> str`

- [ ] **Step 1: 写失败的测试**

在 `test_booklist.py` 的 `main()` 里加：

```python
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
```

注意：`dropped` 里的 `4` 不在 `details` 里，`validate_picks` 允许去掉的书只在 `known_ids` 里、不必有详情；这条要写进实现与测试。

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_booklist.py`
Expected: FAIL，`NameError: name 'validate_picks' is not defined`

- [ ] **Step 3: 实现**

- `validate_picks`：`picks` 必须是字典，含 `kept`、`dropped` 两个列表；`kept` 每项要有非空 `bookId`、`theme`、`reason`，有简介时还要有非空 `summary`；`dropped` 每项要有 `bookId`、`reason`；所有 `bookId` 必须在 `known_ids` 里。报错信息里带字段名或 `未知`。
- `render_booklist`：
  - 取 `picks["kept"]`，按 `details[bookId]` 的评分、人数、书名排序，取前 `top`。
  - 第一行 `## {meta['title']}：推荐值 {meta['min_rating'] / 10:.0f}% 以上的前 {top} 本`。
  - 第二行写计数：`检索 N 个关键词，去重 M 本；推荐值 X% 以上 K 本；按书名与简介筛掉教程、案例集、传记等，取前 T，按推荐值排序。`
  - 每条：`N. **《书名》** 作者 · 推荐值 90.2% · 1,234 人评分 · 主题：组织`；人数少于 50 或未知时，在推荐值后加括号标注；下一行有 `readerLink` 就写 `[打开阅读](...)`，否则有 `deepLink` 写 `[查看详情](...)`，两个都没有就不写；再下一行写 `summary`，没有简介来源时写 `暂无简介`。
  - `group=True` 时按主主题分 `###` 小节，节内仍按评分排序；主题出现顺序按第一次出现。
  - 不写「共有」「一共」。

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -X utf8 tests/weread-book-export/test_booklist.py`
Expected: `全部通过`

- [ ] **Step 5: 提交**

```bash
git add plugin/skills/weread-book-export/scripts/booklist.py tests/weread-book-export/test_booklist.py
git commit -m "feat(weread): 书单交接文件校验与榜单渲染"
```

---

### Task 4: 命令行骨架与 `check`

**Files:**
- Create: `plugin/skills/weread-book-export/scripts/weread_booklist.py`
- Create: `tests/weread-book-export/test_booklist_cli.py`

**Interfaces:**
- Consumes: `booklist.py` 的全部函数。
- Produces:
  - `ApiError(Exception)`，带 `status`、`message`、`errcode`
  - `call_api(body, api_key, opener=urllib.request.urlopen, timeout=30) -> dict`
  - `api_with_retry(body, api_key, retries=2, delays=RETRY_DELAYS, **kwargs) -> dict`
  - `run_check(args) -> int`
  - `main(argv=None) -> int`
  - `parse_args(argv=None) -> argparse.Namespace`

- [ ] **Step 1: 写失败的测试**

新建 `test_booklist_cli.py`，照 `test_search_cli.py` 的写法（自写 `eq` / `raises`，`sys.path` 指向 scripts 目录）。先测 `check`：

```python
def fake_payload(**overrides):
    data = {"results": [{"books": [{"bookInfo": {"bookId": "1", "title": "书"}}]}], "hasMore": 0}
    data.update(overrides)
    return data


def main():
    bad = 0
    # eq / raises 同 test_booklist.py

    original = weread_booklist.call_api
    original_env = os.environ.pop("WEREAD_API_KEY", None)
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = weread_booklist.run_check(argparse.Namespace(skill_version="1.0.6"))
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
            code = weread_booklist.run_check(argparse.Namespace(skill_version="1.0.6"))
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
            code = weread_booklist.run_check(argparse.Namespace(skill_version=None))
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
            code = weread_booklist.run_check(argparse.Namespace(skill_version="1.0.6"))
        eq("接口不可用退出 1", code, 1)
        eq("报告接口错误", "499" in err.getvalue() or "限流" in err.getvalue(), True)
    finally:
        os.environ.pop("WEREAD_API_KEY", None)
        weread_booklist.call_api = original
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_booklist_cli.py`
Expected: FAIL，`ModuleNotFoundError: No module named 'weread_booklist'`

- [ ] **Step 3: 实现**

- 复制 `prefer_utf8` 与 `_ArgumentParser`（按 1 退出）的写法；`main` 开头对 stdout/stderr 调 `prefer_utf8`。
- `parse_args`：用 `add_subparsers(dest="command", required=True)`，四个子命令；`--skill-version` 每个子命令都收；`search` 收 `--topic`、`--title`、`--context`、`--keywords-file`、`--min-rating 700`、`--pages 3`、`--count 50`、`--interval 2.0`、`--retries 2`、`--refresh`、`--cache-dir`；`info` 收 `--topic`、`--shortlist`、`--refresh`、`--cache-dir`；`render` 收 `--topic`、`--picks`、`--top 20`、`--group`、`--min-ratings 0`、`--out`、`--cache-dir`。
- `call_api`：UTF-8 JSON body，`Authorization: Bearer`，`Content-Type: application/json; charset=utf-8`；`HTTPError` 转 `ApiError(code, ...)`；`URLError` 转 `ApiError(None, ...)`；回包 `errcode` 非 0 转 `ApiError(None, message, errcode)`。
- `api_with_retry`：对 `status == 499`、`status is None`、`errcode` 非 0 的情况重试；每次间隔取 `delays[attempt]`；重试完抛出最后一个错误。
- `run_check`：缺 `WEREAD_API_KEY` 时打印提示、返回 2；版本号取不到时打印、返回 1；调一次 `/store/search`（`keyword="测试"`、`scope=10`、`count=1`、`context="检查接口可用性"`），再调一次 `/book/info`（用搜索结果第一本的 bookId；没有结果就跳过并说明）；打印版本来源与两个接口的结果；接口报错打印并返回 1。
- `main`：分发四个子命令；参数错误由 `_ArgumentParser` 按 1 退出。

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -X utf8 tests/weread-book-export/test_booklist_cli.py`
Expected: `全部通过`

- [ ] **Step 5: 提交**

```bash
git add plugin/skills/weread-book-export/scripts/weread_booklist.py tests/weread-book-export/test_booklist_cli.py
git commit -m "feat(weread): 书单命令行骨架与接口自检"
```

---

### Task 5: `search` 子命令

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/weread_booklist.py`
- Modify: `tests/weread-book-export/test_booklist_cli.py`

**Interfaces:**
- Consumes: Task 4 的 `call_api`、`api_with_retry`；Task 1、2、3 的纯逻辑。
- Produces: `run_search(args) -> int`；缓存文件 `raw/*.json`、`all_books.json`、`candidates.json`、`search_meta.json`、`failed.txt`。

- [ ] **Step 1: 写失败的测试**

在 `test_booklist_cli.py` 里用 `tempfile.TemporaryDirectory()`，把 `call_api` 换成按请求 body 返回不同页的假函数：

```python
def make_search_api(pages):
    calls = []

    def fake(body, key, **kw):
        calls.append(dict(body))
        page = (body.get("maxIdx") or 0) // body["count"]
        return {"results": [{"books": [
            {"bookInfo": {"bookId": "%s-%d-%d" % (body["keyword"], page, i),
                          "title": "%s 第 %d 页第 %d 本" % (body["keyword"], page, i),
                          "newRating": 800 if i == 0 else 699,
                          "newRatingCount": 100}}
            for i in range(pages[page])
        ]}], "hasMore": 1 if page + 1 < len(pages) else 0}

    return fake, calls
```

测试开头把 `weread_booklist.RETRY_DELAYS`、`weread_booklist.PAGE_PAUSE` 都 monkeypatch 成 0，`run_search` 的 `args.interval` 传 0，避免真等。测试里的 Namespace 带 `skill_version="1.0.6"`、`cache_dir=tmp`、`topic="t"`、`title="测试主题"`、`context="测试"`、`keywords_file=<临时文件>`，环境变量 `WEREAD_API_KEY="wrk-test"` 设上。

断言：

- 第 1 页请求的 body 没有 `maxIdx`；第 2 页是 `maxIdx=2`（测试里 `count=2`）；第 3 页是 `4`。
- 两页各 2 本、bookId 不同：`all_books.json` 4 本；只有评分 800 的 2 本进 `candidates.json`。
- `search_meta.json` 的 `keywords`、`min_rating`、`unique_books=4`、`candidates=2`。
- 同一主题再跑一次，`call_api` 调用次数不增加（缓存复用）。
- 加 `--refresh` 再跑，调用次数增加。
- 某个词第一次返回 499、第二次成功：把 `RETRY_DELAYS` 设成 `(0, 0)`，断言最终成功。
- 某个词两次都 499：`failed.txt` 有它，退出 3，其它词的结果仍在。
- 所有词都搜到但都低于 700：退出 0，打印「本次没有过线的书」，`candidates.json` 是空列表。
- `raw/` 下放一个坏 JSON：这个位置上的词会被重搜（断言调用次数增加）。

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_booklist_cli.py`
Expected: FAIL，`NameError: name 'run_search' is not defined`

- [ ] **Step 3: 实现**

- 解析 keywords 文件；版本号按 `resolve_skill_version` 取；缓存目录按 `cache_dir(topic, args.cache_dir)`。
- 每个词：有 `raw/<hash>.json` 且没 `--refresh` 时，用 `read_json(path, None)` 读；返回 `None`（文件坏了）就重搜，返回列表（包括空列表）就用缓存；否则逐页请求，`maxIdx = page_offset(page, count)`，第 0 页不传 `maxIdx`；每页之间停 0.5 秒；`hasMore != 1` 就停；每页的 `results` 用 `flatten_books` 扁平化；整词结果用 `write_json` 写缓存。
- 词与词之间停 `args.interval` 秒（加 0 到 0.5 秒随机也可，测试用假 sleep）。
- 所有词跑完后 `merge_books`、`filter_by_rating`、写 `all_books.json`、`candidates.json`、`search_meta.json`。
- 失败词写 `failed.txt`，有失败返回 3；没有失败就删掉旧的 `failed.txt`；没有候选时打印「本次没有过线的书」并返回 0。
- 版本号缺失返回 1；缺 Key 返回 2。
- 为了让测试不需要真等待，模块里定义 `RETRY_DELAYS = (10, 30)` 和 `PAGE_PAUSE = 0.5`，测试 monkeypatch 成 0。

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -X utf8 tests/weread-book-export/test_booklist_cli.py`
Expected: `全部通过`

- [ ] **Step 5: 提交**

```bash
git add plugin/skills/weread-book-export/scripts/weread_booklist.py tests/weread-book-export/test_booklist_cli.py
git commit -m "feat(weread): 书单检索支持正确翻页、缓存与限流重试"
```

---

### Task 6: `info` 子命令

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/weread_booklist.py`
- Modify: `tests/weread-book-export/test_booklist_cli.py`

**Interfaces:**
- Consumes: 缓存里的 `shortlist.json`、`search_meta.json`；`call_api`。
- Produces: `run_info(args) -> int`；`bookinfo.json`、`failed_info.txt`；更新 `search_meta.json` 的 `info_ok`、`info_failed`。

- [ ] **Step 1: 写失败的测试**

用临时目录预置 `shortlist.json` 和 `search_meta.json`（`{"title": "测试", "keywords": ["AI"], "min_rating": 700, "unique_books": 1, "candidates": 2}`），`shortlist.json` 内容：

```python
{"kept": [{"bookId": "1", "reason": "相关"}, {"bookId": "2", "reason": "相关"}],
 "dropped": []}
```

测试的 Namespace 带 `skill_version="1.0.6"`、`cache_dir=tmp`、`topic="t"`，环境变量 `WEREAD_API_KEY` 设上，`INFO_PAUSE` 设 0。

假 `call_api` 按 `body["bookId"]` 返回：`1` 有 `intro`、`newRating`、`readerLink`；`2` 抛 `ApiError(499, "限流")`。

断言：

- `bookinfo.json` 里有 `1`，没有 `2`。
- `failed_info.txt` 里有 `2`。
- `search_meta.json` 的 `info_ok=1`、`info_failed=1`。
- 退出 3。
- 第二次跑时，`1` 不重复请求（缓存）；`2` 会重试。
- 两本都失败：退出 1。
- `intro` 是空串：`bookinfo.json` 保留该条，`intro` 为空。

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_booklist_cli.py`
Expected: FAIL，`NameError: name 'run_info' is not defined`

- [ ] **Step 3: 实现**

- 读 `shortlist.json`，只取 `kept` 的 `bookId`。
- 读已有的 `bookinfo.json`，已成功且没 `--refresh` 的跳过。
- 每本调 `/book/info`，只保留 `title`、`author`、`translator`、`intro`、`category`、`publisher`、`newRating`、`newRatingCount`、`readerLink`、`deepLink`；成功后立刻 `write_json`，便于中断续跑。
- 失败的 bookId 写 `failed_info.txt`；更新 `search_meta.json` 的 `info_ok`、`info_failed`。
- 有失败且至少一本成功返回 3；一本都没成功返回 1；全成功返回 0。
- 每本之间停 1 秒（`INFO_PAUSE`，测试 monkeypatch 成 0）。

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -X utf8 tests/weread-book-export/test_booklist_cli.py`
Expected: `全部通过`

- [ ] **Step 5: 提交**

```bash
git add plugin/skills/weread-book-export/scripts/weread_booklist.py tests/weread-book-export/test_booklist_cli.py
git commit -m "feat(weread): 书单详情拉取支持缓存与失败记录"
```

---

### Task 7: `render` 子命令

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/weread_booklist.py`
- Modify: `tests/weread-book-export/test_booklist_cli.py`

**Interfaces:**
- Consumes: Task 3 的 `validate_picks`、`render_booklist`、`merge_details`；缓存里的 `search_meta.json`、`candidates.json`、`bookinfo.json`、`picks.json`。
- Produces: `run_render(args) -> int`；成品 `booklist-<YYYY-MM-DD>.md` 或 `--out` 指定路径。

- [ ] **Step 1: 写失败的测试**

在临时目录预置四个文件，跑 `run_render`；测试的 Namespace 带 `cache_dir=tmp`、`topic="t"`、`picks=<临时文件>`、`top=20`、`group=False`、`min_ratings=0`、`out=None`。

- 正常：退出 0，成品文件存在，含标题、计数、排名、推荐值、链接、主题、简述。
- `--out` 指到临时目录外：文件写在那里。
- `--min-ratings 100`：评分人数 20 的那本被去掉。
- `--group`：输出含 `###` 小节。
- `picks.json` 缺 `reason`：退出 1，stderr 有 `reason`。
- `picks.json` 里的 bookId 不在 `candidates.json`：退出 1，stderr 有 `未知`。
- `intro` 为空且没写 `summary`：退出 0，成品里写「暂无简介」。

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_booklist_cli.py`
Expected: FAIL，`NameError: name 'run_render' is not defined`

- [ ] **Step 3: 实现**

- 读 `search_meta.json`、`candidates.json`、`bookinfo.json`、`picks.json`；用 `merge_details` 合成详情。
- `validate_picks(picks, set(details), details)`；`ValueError` 打印到 stderr、返回 1。
- `--min-ratings` 大于 0 时，先过滤掉 `newRatingCount` 低于它的 `kept`。
- 默认输出路径 `cache / ("booklist-%s.md" % datetime.date.today())`；`--out` 优先；写文件后打印绝对路径。
- 同时把榜单正文打印到 stdout，方便模型直接转述。

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -X utf8 tests/weread-book-export/test_booklist_cli.py`
Expected: `全部通过`

- [ ] **Step 5: 提交**

```bash
git add plugin/skills/weread-book-export/scripts/weread_booklist.py tests/weread-book-export/test_booklist_cli.py
git commit -m "feat(weread): 书单渲染与成品落盘"
```

---

### Task 8: 技能文档

**Files:**
- Modify: `plugin/skills/weread-book-export/SKILL.md`
- Modify: `plugin/skills/weread-book-export/README.md`
- Modify: `README.md`（仓库根）

**Interfaces:**
- Consumes: Task 4 至 Task 7 的命令行接口。
- Produces: 模型能读懂并照着跑的书单流程说明。

- [ ] **Step 1: 改 `SKILL.md`**

- 描述里加触发：`按主题筛书单`、`推荐度 70% 以上的前 20 本`、`列一个 XX 主题书单`；补一句「需要 `WEREAD_API_KEY`」。
- 正文加一节「按主题筛书单」，写清：
  - 与另外两件事的分工：找具体某本走 `weread_search.py`，导正文走 `weread_export.py`，按主题筛一批走 `weread_booklist.py`。
  - 前置条件：`WEREAD_API_KEY`；版本号由脚本自己读官方 `SKILL.md`。
  - 四步命令：`check` → `search` → `info` → `render`，参数照设计稿。
  - 模型要做的事：展开 12-15 个关键词（「尽量全」时 30 个以上）；初筛只看书名和作者；精筛看分类、出版方、简介；主题标签与一句话简述。
  - 筛选判据：排除技术教程、工具手册、案例集、传记、变现、轻读物；「不要实例」= 案例集。
  - 输出格式与退出码；`search` 退出 3 时要把失败词转告用户。
  - 官方升级后先跑 `check`。

- [ ] **Step 2: 改两个 README**

- 技能 `README.md` 加一节「按主题筛书单（需要 API Key）」：命令示例、缓存位置、成品位置、测试命令；「脚本分工」表加两行：`booklist.py`（书单纯逻辑）、`weread_booklist.py`（书单命令行入口）。
- 仓库根 `README.md` 的 `weread-book-export` 那一行，在搜索入口后补一句：能按主题与推荐值筛书单，按推荐值排名，需要 Agent API Key。

- [ ] **Step 3: 检查文档**

Run:

```bash
grep -n "WEREAD_API_KEY\|weread_booklist.py\|按主题筛书单" plugin/skills/weread-book-export/SKILL.md plugin/skills/weread-book-export/README.md README.md
```

Expected: 三份文件都能看到对应字样；`SKILL.md` 有四个子命令的完整命令。

- [ ] **Step 4: 提交**

```bash
git add plugin/skills/weread-book-export/SKILL.md plugin/skills/weread-book-export/README.md README.md
git commit -m "docs(weread): 补充按主题筛书单的用法与判据"
```

---

### Task 9: 版本号与全量验证

**Files:**
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

**Interfaces:**
- Consumes: 前八个任务的全部改动。
- Produces: 可交付的版本 1.35.3。

- [ ] **Step 1: 抬版本号**

两处都从 `1.35.2` 改成 `1.35.3`（对原有技能的修改，抬最后一位）。

- [ ] **Step 2: 跑技能测试**

Run: `bash tests/run.sh weread-book-export`
Expected: `全部通过`

- [ ] **Step 3: 跑仓库检查**

Run: `bash checks/verify.sh --changed`
Expected: 全部通过；版本一致性检查显示 `OK 1.35.3`。

- [ ] **Step 4: 检查空白字符与非 BMP 字符**

Run:

```bash
git diff --check
python -I -c "
import pathlib
bad = []
for p in pathlib.Path('plugin/skills/weread-book-export').rglob('*'):
    if p.is_file() and p.suffix in {'.py', '.md'}:
        text = p.read_text(encoding='utf-8', errors='ignore')
        if any(ord(c) > 0xFFFF for c in text):
            bad.append(str(p))
print('非 BMP:', bad)
"
```

Expected: `git diff --check` 无输出；非 BMP 列表为空。

- [ ] **Step 5: 确认 `plugin/` 下没有测试或缓存文件**

Run:

```bash
find plugin/skills/weread-book-export \( -name "__pycache__" -o -name "test_*.py" -o -name "*.json" \)
```

Expected: 无输出；有 `__pycache__` 就删掉再提交。

- [ ] **Step 6: 提交**

```bash
git add plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore(release): 抬版本号至 1.35.3"
```

---

## 自查记录

- **规格覆盖**：设计稿的 14 条关键决定分别落在 Task 1（版本号、缓存）、Task 2（字段位置、去重、排序）、Task 3（输出、主题、人数标注）、Task 4（退出码、接口）、Task 5（翻页、限流、缓存、零候选）、Task 6（详情失败、空简介）、Task 7（渲染、分组、`--min-ratings`）、Task 8（文档）、Task 9（版本与交付）。
- **步骤粒度**：每个任务都是「写失败测试 → 跑失败 → 实现 → 跑通过 → 提交」，没有 TBD 或「处理边界情况」这类空话。
- **类型与命名**：`cache_dir`、`raw_cache_path`、`flatten_books`、`merge_books`、`filter_by_rating`、`sort_books`、`merge_details`、`validate_picks`、`render_booklist`、`run_check`、`run_search`、`run_info`、`run_render` 在前后任务里同名同参数。
- **Review Focus**：五条都在对应任务的测试里钉住：限流重试与坏缓存（Task 5）、BOM/CRLF（Task 1）、缺链接（Task 3）、零候选（Task 5）。
- **比例**：计划描述接口与测试断言，不抄实现正文。
