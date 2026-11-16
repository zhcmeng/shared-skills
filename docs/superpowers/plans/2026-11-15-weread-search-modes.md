# 微信读书三种搜书方式 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `weread_search.py` 增加精确、模糊、语义三种搜书方式，并把搜索改成读服务端状态。

**Architecture:** 纯匹配、合并、渲染逻辑放进新模块 `matches.py`；`weread.py` 新增 `search_books_page()` 读搜索页服务端 `__INITIAL_STATE__`，保留 DOM 回退；`weread_search.py` 只做参数校验、模式分发和输出。

**Tech Stack:** Python 3、Playwright 浏览器上下文、仓库现有的 `tests/run.sh` 纯 Python 测试。

**Spec:** `docs/superpowers/specs/2026-11-15-weread-search-modes-design.md`

## Global Constraints

- 搜索默认无头；正文导出仍必须真浏览器。
- 同一个 browser-profile 不能并发；不删除 `%LOCALAPPDATA%\weread-book-export\browser-profile`。
- 退出码：0 有结果；2 一条也没匹配上且没登录；3 一条也没匹配上但不是登录问题；1 参数或其它错误。
- 同名多本全部列出，不替用户挑。
- 不加批量导出入口；批量导出仍按 `--series` 清单串行跑。
- 文件、测试名用英文；正文和注释用中文；不出现非 BMP 字符。
- 临时文件放仓库根 `.tmp/`，交付前清掉。
- 每个任务结束跑 `python -X utf8 tests/weread-book-export/<test>.py`；全部改完跑 `bash tests/run.sh weread-book-export` 和 `bash checks/verify.sh --changed`。
- 提交前先确认使用者要求提交；没确认就停在测试通过，把改动留在工作区。提交信息末尾加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。

## Review Focus

1. 空串或全空白查询：`--exact ""`、`--fuzzy "  "`、`--semantic ""` 应退出 1，不能拿空串去搜。测试放在 Task 5。
2. 模糊档多词是「或」：标题只含其中一个词也必须列出；两个都不含才排除。测试放在 Task 2。
3. 精确档同名多本：两条同名不同地址都要列出，不能只取第一条。测试放在 Task 3。
4. 语义档某个词 0 条：继续跑其余词，输出里标 0 条，不能整批失败。测试放在 Task 3。
5. 服务端状态缺失或 JSON 坏了：解析返回 `None`，`search_books_page()` 回退 DOM，不抛异常。测试放在 Task 4；回退路径在 Task 9 实测。

---

### Task 1: 把书名匹配移到 `matches.py`，加大小写折叠

**Files:**
- Create: `plugin/skills/weread-book-export/scripts/matches.py`
- Modify: `plugin/skills/weread-book-export/scripts/issues.py`
- Create: `tests/weread-book-export/test_matches.py`
- Modify: `tests/weread-book-export/test_issues.py`

**Interfaces:**
- Produces: `normalize_title(text: str) -> str`；`exact_hits(hits: list[dict], title: str) -> list[dict]`。
- `issues.py` 从 `matches` 导入 `normalize_title`；不再定义 `normalize_title`、`exact_hits`。

- [ ] **Step 1: 写失败的测试**

按 `tests/weread-book-export/test_issues.py` 的骨架新建 `test_matches.py`（`eq`/`raises` 两个助手、`main()`、退出码）。导入：

```python
from matches import exact_hits, normalize_title
```

在 `main()` 里加：

```python
eq("全角半角与空白不影响比对",
   normalize_title("财经 (2026 年第 5 期）"),
   normalize_title("财经（2026年第5期）"))
eq("大小写不影响比对", normalize_title("AI 入门"), normalize_title("ai入门"))
eq("精确只认全等，大小写不敏感",
   [hit["href"] for hit in exact_hits(
       [{"title": "ai 入门", "href": "a"},
        {"title": "AI 入门指南", "href": "b"}],
       "AI 入门")],
   ["a"])
eq("第一财经挡在外面",
   [hit["href"] for hit in exact_hits(
       [{"title": "第一财经（2026年第5期）", "href": "y"},
        {"title": "财经（2026年第5期）", "href": "a"}],
       "财经（2026年第5期）")],
   ["a"])
eq("半角括号也能认出来",
   [hit["href"] for hit in exact_hits(
       [{"title": "财经(2026年第5期)", "href": "c"}],
       "财经（2026年第5期）")],
   ["c"])
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_matches.py`
Expected: `ModuleNotFoundError: No module named 'matches'`。

- [ ] **Step 3: 实现 `matches.py`，改 `issues.py`**

`matches.py`：

```python
def normalize_title(text: str) -> str:
    """比对用的标题：NFKC、去空白、大小写折叠。"""

def exact_hits(hits: list[dict], title: str) -> list[dict]:
    """标题归一化后与 title 完全一致的所有条目。"""
```

`normalize_title` 用 `unicodedata.normalize("NFKC", text or "")`、`re.sub(r"\s+", "", ...)`、`.casefold()`。

`issues.py`：删掉 `normalize_title` 和 `exact_hits` 的定义，改成 `from matches import normalize_title`；`exact_hits` 不再从 `issues` 导出。`pick_extras` 继续用 `normalize_title`。

`test_issues.py`：从导入里去掉 `exact_hits`、`normalize_title`，删掉「全角半角与空白不影响比对」「只认完全一致，第一财经挡在外面」「半角括号也能认出来」三段；保留 `pick_extras` 和清单渲染测试。

- [ ] **Step 4: 跑两个测试文件**

Run:
```bash
python -X utf8 tests/weread-book-export/test_matches.py
python -X utf8 tests/weread-book-export/test_issues.py
```
Expected: 两个都打印「全部通过」。

- [ ] **Step 5: 提交（经使用者同意后）**

```bash
git add plugin/skills/weread-book-export/scripts/matches.py \
        plugin/skills/weread-book-export/scripts/issues.py \
        tests/weread-book-export/test_matches.py \
        tests/weread-book-export/test_issues.py
git commit -m "refactor(skills): 书名匹配移到 matches.py 并支持大小写折叠" \
           -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: 模糊匹配与相关词解析

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/matches.py`
- Modify: `tests/weread-book-export/test_matches.py`

**Interfaces:**
- Produces:
  - `split_tokens(query: str) -> list[str]`
  - `fuzzy_hits(hits: list[dict], query: str) -> list[dict]`：任意一个词出现在归一化标题里就算命中。
  - `parse_terms(concept: str, raw_terms: str | None) -> list[str]`：概念本身 + 逗号拆出的词，按归一化去重，保留第一次的写法。
  - `term_hits(hits: list[dict], term: str) -> list[dict]`：标题同时含该词的所有分词。

- [ ] **Step 1: 写失败的测试**

在 `test_matches.py` 里导入新增函数，加：

```python
hits = [
    {"title": "估值：难点、解决方案", "href": "a"},
    {"title": "价值投资入门", "href": "b"},
    {"title": "财报分析", "href": "c"},
]
eq("模糊档任意一个词出现就算命中",
   [hit["href"] for hit in fuzzy_hits(hits, "估值 价值投资")], ["a", "b"])
eq("两个词都不出现才排除",
   "c" in [hit["href"] for hit in fuzzy_hits(hits, "估值 价值投资")], False)
eq("模糊档大小写不敏感",
   [hit["href"] for hit in fuzzy_hits([{"title": "AI 入门", "href": "x"}], "ai")], ["x"])
eq("相关词自动带上概念并去重",
   parse_terms("AI", "人工智能, 大模型，人工智能"), ["AI", "人工智能", "大模型"])
eq("单个词内部要求所有分词都在",
   [hit["href"] for hit in term_hits(
       [{"title": "large language model 实战", "href": "a"},
        {"title": "language model", "href": "b"}],
       "large language model")],
   ["a"])
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_matches.py`
Expected: `ImportError` 或 `NameError`，提示 `fuzzy_hits`、`parse_terms`、`term_hits` 不存在。

- [ ] **Step 3: 实现四个函数**

- `split_tokens`：`query.split()` 后逐个 `normalize_title`，去掉空串。
- `fuzzy_hits`：`any(token in normalize_title(hit.get("title")) for token in tokens)`；没有词返回 `[]`。
- `parse_terms`：概念放最前；`raw_terms` 用 `re.split(r"[,，]", ...)` 拆；strip；按 `normalize_title` 去重；跳过归一化后为空的词。
- `term_hits`：`all(token in normalize_title(hit.get("title")) for token in tokens)`；没有词返回 `[]`。

- [ ] **Step 4: 跑测试**

Run: `python -X utf8 tests/weread-book-export/test_matches.py`
Expected: 「全部通过」。

- [ ] **Step 5: 提交（经使用者同意后）**

```bash
git add plugin/skills/weread-book-export/scripts/matches.py \
        tests/weread-book-export/test_matches.py
git commit -m "feat(skills): 模糊匹配与相关词解析" \
           -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: 合并、排序与三种模式的文字输出

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/matches.py`
- Modify: `tests/weread-book-export/test_matches.py`

**Interfaces:**
- Produces:
  - `merge_hits(per_term: list[dict]) -> list[dict]`
    - 输入每项 `{"term": str, "hits": list[dict]}`。
    - 输出每项 `{"title", "author", "href", "terms": list[str], "order": tuple[int, int]}`。
    - 按 `href` 去重；按 `(-len(terms), order)` 排序。
  - `render_exact(query: str, hits: list[dict], fallback: list[dict]) -> str`
  - `render_fuzzy(query: str, hits: list[dict], capped: bool) -> str`
  - `render_semantic(terms: list[str], per_term: list[dict], merged: list[dict]) -> str`
    - `per_term` 每项 `{"term": str, "hits": list[dict], "capped": bool}`。

- [ ] **Step 1: 写失败的测试**

```python
per_term = [
    {"term": "AI", "hits": [
        {"title": "AI 时代", "author": "甲", "href": "a"},
        {"title": "人工智能导论", "author": "乙", "href": "b"},
    ], "capped": False},
    {"term": "人工智能", "hits": [
        {"title": "人工智能导论", "author": "乙", "href": "b"},
        {"title": "大模型时代", "author": "丙", "href": "c"},
    ], "capped": False},
]
merged = merge_hits(per_term)
eq("按 href 去重", [item["href"] for item in merged], ["b", "a", "c"])
eq("命中词数多的排前面", [len(item["terms"]) for item in merged], [2, 1, 1])
eq("同数按首次出现", merged[1]["href"], "a")
eq("记录命中的词", merged[0]["terms"], ["AI", "人工智能"])

exact_text = render_exact("同名", [
    {"title": "同名", "author": "甲", "href": "https://a"},
    {"title": "同名", "author": "乙", "href": "https://b"},
], [])
eq("精确档同名多本全部列出",
   "https://a" in exact_text and "https://b" in exact_text and "未替你挑" in exact_text, True)
eq("精确档没有同名时标明不是同名",
   "不是同名" in render_exact("没有的书", [], [{"title": "别的书", "author": "甲", "href": "https://x"}]), True)

fuzzy_text = render_fuzzy("估值 价值投资", [{"title": "估值", "author": "甲", "href": "https://a"}], True)
eq("模糊档标题写成或", "或" in fuzzy_text and "估值" in fuzzy_text and "价值投资" in fuzzy_text, True)
eq("模糊档满页提示", "40 条" in fuzzy_text, True)

semantic_text = render_semantic(["AI", "人工智能", "大模型"], per_term + [
    {"term": "大模型", "hits": [], "capped": False},
], merged)
eq("语义档列出命中词", "命中 2 词" in semantic_text and "人工智能" in semantic_text, True)
eq("语义档标 0 条词", "0 条" in semantic_text, True)
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_matches.py`
Expected: 提示 `merge_hits`、`render_exact`、`render_fuzzy`、`render_semantic` 不存在。

- [ ] **Step 3: 实现合并与渲染**

`merge_hits`：

- 按 `per_term` 顺序遍历；每条的 `order = (term_index, hit_index)`。
- 新 `href` 建一项，`terms` 只放当前词；已存在就追加未出现过的词。
- 最后 `sorted(..., key=lambda item: (-len(item["terms"]), item["order"]))`。

`render_exact`：

- 有命中：第一行「书名完全相同的 N 本：」；N > 1 时改成「（同名多本，未替你挑）」；每本两行：`%3d. 标题 — 作者`、地址。
- 没命中：第一行「没有书名完全相同的「query」。」；fallback 非空时加「搜索页返回的下面这些不是同名，供核对（最多 5 条）：」，最多列 5 条，超过时说「……还有 N 条没列。」。

`render_fuzzy`：

- 单个词：`标题含「估值」的 N 本（页面顺序）：`；多个词：`标题含「估值」或「价值投资」的 N 本（页面顺序）：`。
- 每本两行：`%3d. 标题 — 作者`、地址。
- `capped` 为真时末尾加空行和「搜索页一页最多 40 条，可能还有；要更多用 --semantic 给一组相关词。」。

`render_semantic`：

- 第一行「相关词 N 个：词1、词2……」。
- 第二行「各词命中合计 X 条（每词最多 40 条），去重后 Y 本。」。
- 只有概念一个词时加提示：「只搜了「AI」本身。要覆盖同义词，用 --terms 给一组相关词，例如：」和 `  --terms "人工智能,大模型,机器学习"`。
- 有合并结果：每本两行 `命中 k 词（词1、词2）  标题 — 作者`、地址。
- 没有合并结果：列出所有词，说「这些词都没有搜到标题含它的书：……。换一组相关词再试；或者用 --fuzzy 直接搜一个词。」。
- 最后「按词看：」，每词一行 `  词：N 条`；`hits` 为空标「（0 条，换个词）」，`capped` 为真标「（满页，可能还有）」。

- [ ] **Step 4: 跑测试**

Run: `python -X utf8 tests/weread-book-export/test_matches.py`
Expected: 「全部通过」。

- [ ] **Step 5: 提交（经使用者同意后）**

```bash
git add plugin/skills/weread-book-export/scripts/matches.py \
        tests/weread-book-export/test_matches.py
git commit -m "feat(skills): 搜索结果的合并、排序与渲染" \
           -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `weread.py` 读服务端搜索状态

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/weread.py`
- Modify: `tests/weread-book-export/test_weread.py`

**Interfaces:**
- Produces:
  - `search_books_page(page, title) -> dict`，键 `hits`、`total_count`、`has_more`、`logged_in`。
  - `search_books(page, title) -> list[dict]`，返回 `search_books_page(...)["hits"]`。
  - `_search_state(html: str) -> dict | None`
  - `_hits_from_state(state: dict) -> list[dict]`
  - `_logged_in_from_state(state: dict) -> bool`

- [ ] **Step 1: 写失败的测试**

在 `test_weread.py` 的导入里加 `_search_state`、`_hits_from_state`、`_logged_in_from_state`，在 `main()` 里加：

```python
html = (
    '<script>window.__INITIAL_STATE__={"user":{"skey":"k"},'
    '"searchBooksStoreModule":{"bookInfos":['
    '{"bookInfo":{"title":"估值","author":"甲","readerLink":"https://weread.qq.com/web/reader/x"}},'
    '{"bookInfo":{"title":"估值","author":"甲","readerLink":"https://weread.qq.com/web/reader/x"}}'
    '],"totalCount":48,"hasMore":true}}</script>'
)
state = _search_state(html)
eq("从原始 HTML 读出搜索状态", state["searchBooksStoreModule"]["totalCount"], 48)
eq("状态里的书按地址去重", _hits_from_state(state),
   [{"title": "估值", "author": "甲", "href": "https://weread.qq.com/web/reader/x"}])
eq("user 有 skey 算已登录", _logged_in_from_state(state), True)
eq("user 全空算未登录",
   _logged_in_from_state({"user": {"skey": "", "name": "", "avatar": ""}}), False)
eq("没有状态返回 None", _search_state("<html></html>"), None)
eq("JSON 坏了返回 None", _search_state("window.__INITIAL_STATE__={bad"), None)
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_weread.py`
Expected: `ImportError`，提示这三个函数不存在。

- [ ] **Step 3: 实现状态解析与 `search_books_page()`**

`weread.py` 顶部加 `import json`、`import re`。

```python
def _search_state(html):
    """从搜索页原始 HTML 里取出 __INITIAL_STATE__；拿不到返回 None。"""

def _hits_from_state(state):
    """从 searchBooksStoreModule.bookInfos 取标题、作者、readerLink，按地址去重。"""

def _logged_in_from_state(state):
    """user 的 skey、name、avatar 有一个非空就算已登录。"""

def search_books_page(page, title):
    """搜索书名，返回结果与页面状态。

    先读服务端 __INITIAL_STATE__；没有就退回等页面渲染。
    """

def search_books(page, title):
    """按书名搜索，返回候选列表；保持原来的接口。"""
```

`_search_state`：

- 用 `re.search(r"window\\.__INITIAL_STATE__\\s*=\\s*", html or "")` 找起点，找不到返回 `None`。
- `json.JSONDecoder().raw_decode(html[match.end():])`；`ValueError` 返回 `None`。

`_hits_from_state`：

- `module = (state or {}).get("searchBooksStoreModule") or {}`。
- 遍历 `module.get("bookInfos") or []`；取 `item.get("bookInfo") or {}` 的 `title`、`author`、`readerLink`。
- `readerLink` 为空或重复的跳过。

`search_books_page`：

- 先 `page.context.request.get(SEARCH_URL % quote(title), timeout=30000)`。
- `response.ok` 且 `_search_state(response.text())` 里有 `searchBooksStoreModule` 时返回状态结果；`total_count = module.get("totalCount")`、`has_more = module.get("hasMore")`、`logged_in = _logged_in_from_state(state)`。
- 请求或解析失败、或模块不存在时，走原来的 DOM 路径：`page.goto`、等待阅读器链接、`page.evaluate(_SEARCH_JS)`、`urljoin`、按 `href` 去重；返回 `total_count=None`、`has_more=None`、`logged_in=not is_logged_out(page)`。
- 等待超时返回空 `hits`，其余键同上。

`search_books` 直接 `return search_books_page(page, title)["hits"]`。

- [ ] **Step 4: 跑测试**

Run: `python -X utf8 tests/weread-book-export/test_weread.py`
Expected: 「全部通过」。

- [ ] **Step 5: 提交（经使用者同意后）**

```bash
git add plugin/skills/weread-book-export/scripts/weread.py \
        tests/weread-book-export/test_weread.py
git commit -m "feat(skills): 搜索读服务端状态，保留 DOM 回退" \
           -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: 命令行加精确、模糊两档

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/weread_search.py`
- Create: `tests/weread-book-export/test_search_cli.py`

**Interfaces:**
- Produces:
  - `parse_args(argv=None) -> argparse.Namespace`
  - `check_args(args) -> str`，返回 `"exact"`、`"fuzzy"`、`"semantic"`、`"series"` 之一。
  - `run_exact(browser, args) -> int`
  - `run_fuzzy(browser, args) -> int`

- [ ] **Step 1: 写失败的测试**

按 `test_issues.py` 的骨架新建 `test_search_cli.py`，导入：

```python
import argparse
from issues import DEFAULT_TEMPLATE
from weread_search import check_args
```

加一个构造参数的助手：

```python
def args(**overrides):
    data = dict(exact=None, fuzzy=None, semantic=None, terms=None, series=None,
                year=None, max=None, template=None, out=None,
                show=False, profile=None, channel=None)
    data.update(overrides)
    return argparse.Namespace(**data)
```

在 `main()` 里加：

```python
eq("精确模式", check_args(args(exact="书名")), "exact")
eq("模糊模式", check_args(args(fuzzy="估值")), "fuzzy")
eq("语义模式", check_args(args(semantic="AI", terms="人工智能,大模型")), "semantic")

series_args = args(series="财经", year=2026)
eq("系列模式", check_args(series_args), "series")
eq("系列模式默认 max", series_args.max, 60)
eq("系列模式默认模板", series_args.template, DEFAULT_TEMPLATE)

raises("两种模式不能一起给",
       lambda: check_args(args(exact="x", fuzzy="y")), "只能给一个")
raises("精确模式不能给 --out",
       lambda: check_args(args(exact="x", out="f.md")), "只和")
raises("--terms 只能配语义模式",
       lambda: check_args(args(fuzzy="x", terms="a,b")), "--terms")
raises("空书名要报错",
       lambda: check_args(args(exact="  ")), "不能是空串")
raises("系列模式缺年份",
       lambda: check_args(args(series="财经")), "同时给")
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_search_cli.py`
Expected: `ImportError` 或 `AttributeError`，提示 `check_args` 不存在或参数不认识。

- [ ] **Step 3: 改参数与 `check_args`，加两个 `run_*`**

参数：

- 加 `--exact`、`--fuzzy`、`--semantic`、`--terms`。
- 删除 `--keyword`。
- `--max`、`--template` 的 `default` 改成 `None`。
- `--out` 的帮助文字补「只和 `--series` 一起用」。

`check_args` 的顺序：

1. 统计四种模式（用 `is not None`，不用 `bool`）：等于 0 时，给了 `--year` 报「给 `--year` 时也要给 `--series`。」，什么都没给报「要给 `--exact`、`--fuzzy`、`--semantic` 或 `--series` 之一。」；大于 1 报「`--exact`、`--fuzzy`、`--semantic`、`--series` 只能给一个。」。
2. 排除零模式和多模式后，继续检查单项模式。
3. `--terms is not None` 且不是语义模式：报「`--terms` 只能和 `--semantic` 一起用。」。
4. 非系列模式给了 `--year`、`--max`、`--template`、`--out` 任意一个：报「`--<名字>` 只和 `--series` 一起用。」。
5. 精确模式空串：报「`--exact` 给一个完整书名，不能是空串。」。
6. 模糊模式空串：报「`--fuzzy` 给一个关键词，不能是空串。」。
7. 语义模式空串：报「`--semantic` 给一个概念，不能是空串。」。
8. 系列模式：`--series` 或 `--year` 缺一个报「系列模式要同时给 `--series` 和 `--year`。」；年份不在 1000～9999 报「`--year` 给四位数年份，如 2026。」；`if args.max is None: args.max = 60`、`if args.template is None: args.template = DEFAULT_TEMPLATE`；`max < 1` 报「`--max` 至少是 1。」。

`run_exact`：

```python
result = search_books_page(browser.page, args.exact)
hits = exact_hits(result["hits"], args.exact)
if hits:
    print(render_exact(args.exact, hits, []))
    return 0
print(render_exact(args.exact, [], result["hits"]), file=sys.stderr)
if result["logged_in"] is False:
    print("现在没登录。书名确认没错的话，加 --show 登录后再试。", file=sys.stderr)
    return 2
return 3
```

`run_fuzzy`：

```python
result = search_books_page(browser.page, args.fuzzy)
hits = fuzzy_hits(result["hits"], args.fuzzy)
if not hits:
    if result["logged_in"] is False:
        print("标题里一个都没含这些词，而且现在没登录。加 --show 登录后重跑。", file=sys.stderr)
        return 2
    print("标题里一个都没含这些词：%s。换个词，或用 --semantic 给一组相关词。" % args.fuzzy,
          file=sys.stderr)
    return 3
capped = result["has_more"] is True or len(result["hits"]) >= 40
print(render_fuzzy(args.fuzzy, hits, capped))
return 0
```

`main` 的分发：`exact`、`fuzzy`、`series`；`semantic` 先打印「语义模式还没接上」并返回 1，Task 6 再换成 `run_semantic`。删掉 `run_keyword` 和 `is_logged_out` 的导入。导入改为：

```python
from issues import DEFAULT_TEMPLATE, check_template, issue_title, pick_extras, render_markdown, render_text
from matches import exact_hits, fuzzy_hits, render_exact, render_fuzzy
from weread import search_books_page
```

- [ ] **Step 4: 跑测试**

Run: `python -X utf8 tests/weread-book-export/test_search_cli.py`
Expected: 「全部通过」。

- [ ] **Step 5: 提交（经使用者同意后）**

```bash
git add plugin/skills/weread-book-export/scripts/weread_search.py \
        tests/weread-book-export/test_search_cli.py
git commit -m "feat(skills): 搜索命令行支持精确与模糊两档" \
           -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: 命令行加语义档

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/weread_search.py`
- Modify: `tests/weread-book-export/test_search_cli.py`

**Interfaces:**
- Produces: `run_semantic(browser, args) -> int`。
- 使用 Task 2 的 `parse_terms`、`term_hits`，Task 3 的 `merge_hits`、`render_semantic`。

- [ ] **Step 1: 写失败的测试**

在 `test_search_cli.py` 里加：

```python
eq("语义模式没有 --terms 也行", check_args(args(semantic="AI")), "semantic")
raises("语义模式不能给 --out",
       lambda: check_args(args(semantic="AI", out="f.md")), "只和")
raises("空概念要报错",
       lambda: check_args(args(semantic="  ")), "不能是空串")
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -X utf8 tests/weread-book-export/test_search_cli.py`
Expected: `ImportError` 或断言失败，提示 `run_semantic` 或 `parse_terms` 不存在。

- [ ] **Step 3: 实现 `run_semantic`**

```python
def run_semantic(browser, args):
    terms = parse_terms(args.semantic, args.terms)
    per_term = []
    for index, term in enumerate(terms, 1):
        result = search_books_page(browser.page, term)
        hits = term_hits(result["hits"], term)
        per_term.append({
            "term": term,
            "hits": hits,
            "capped": result["has_more"] is True or len(result["hits"]) >= 40,
            "logged_in": result["logged_in"],
        })
        print("搜第 %d/%d 个词：%s，%d 条" % (index, len(terms), term, len(hits)), flush=True)
        if index < len(terms):
            browser.human_pause(*SEARCH_PAUSE)

    merged = merge_hits(per_term)
    print(render_semantic(terms, per_term, merged))
    if merged:
        return 0
    if any(item["logged_in"] is False for item in per_term):
        print("这些词一个也没搜到，而且现在没登录。加 --show 登录后重跑。", file=sys.stderr)
        return 2
    return 3
```

`main` 的分发把 `semantic` 换成 `return run_semantic(browser, args)`；导入补 `merge_hits`、`parse_terms`、`render_semantic`、`term_hits`。

说明：`render_semantic` 用 `len(terms) > 1` 判断有没有额外相关词；`parse_terms` 已经把概念放在第一个。只有概念时打印补词提示。

- [ ] **Step 4: 跑测试**

Run: `python -X utf8 tests/weread-book-export/test_search_cli.py`
Expected: 「全部通过」。

- [ ] **Step 5: 提交（经使用者同意后）**

```bash
git add plugin/skills/weread-book-export/scripts/weread_search.py \
        tests/weread-book-export/test_search_cli.py
git commit -m "feat(skills): 搜索命令行支持语义扩展" \
           -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: 系列模式接上新的搜索函数

**Files:**
- Modify: `plugin/skills/weread-book-export/scripts/weread_search.py`

**Interfaces:**
- `find_issues(browser, args) -> tuple[list[dict], bool | None]`：第二个值是最后一次搜索的 `logged_in`。
- `run_series` 用 `search_books_page()` 取 `hits` 和登录信息。

- [ ] **Step 1: 改 `find_issues` 与 `run_series`**

`find_issues`：

- 每次 `result = search_books_page(browser.page, title)`；`logged_in = result["logged_in"]`。
- 用 `exact_hits(result["hits"], title)` 过滤。
- 返回 `issues, logged_in`。

`run_series`：

```python
issues, logged_in = find_issues(browser, args)
if not issues:
    if logged_in is False:
        print("一期也没搜到，而且现在没登录。加 --show 打开窗口登录后重跑。", file=sys.stderr)
        return 2
    print("一期也没搜到：确认 --series 写的是书名里的系列名；标题格式不同时用 --template 改。",
          file=sys.stderr)
    return 3

extras_result = search_books_page(browser.page, "%s %s" % (args.series, args.year))
extras = pick_extras(extras_result["hits"], args.series, args.year,
                     [item["title"] for item in issues])
```

去掉 `is_logged_out`、`search_books` 的导入。

- [ ] **Step 2: 跑现有测试**

Run: `bash tests/run.sh weread-book-export`
Expected: 全部通过。

- [ ] **Step 3: 提交（经使用者同意后）**

```bash
git add plugin/skills/weread-book-export/scripts/weread_search.py
git commit -m "refactor(skills): 系列模式改用新的搜索状态" \
           -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: 文档与版本号

**Files:**
- Modify: `plugin/skills/weread-book-export/SKILL.md`
- Modify: `plugin/skills/weread-book-export/README.md`
- Modify: `README.md`
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

**Interfaces:** 无代码接口；文档要与实际参数一致。

- [ ] **Step 1: 改 `SKILL.md`**

- description 里把「搜索能按关键词列结果，也能按「系列名 + 年份」逐期查全」改成三种搜法，并加触发词「按主题找书、找和 AI 相关的书」。保持一整行，不超过 1024 字符。
- 把「搜索与列全各期」的命令块改成：

```bash
# 精确：知道完整书名
uv run --with playwright python "<skill目录>/scripts/weread_search.py" \
    --exact "财经（2026年第5期）"

# 模糊：标题含任意一个关键词
uv run --with playwright python "<skill目录>/scripts/weread_search.py" \
    --fuzzy "估值 价值投资"

# 语义：概念 + 相关词，逐个搜、合并去重
uv run --with playwright python "<skill目录>/scripts/weread_search.py" \
    --semantic "AI" --terms "人工智能,大模型,机器学习,AIGC,ChatGPT"
```

- 补下面几条，替换原来的 `--keyword` 说明：
  - 精确档按书名全等比对；同名多本全列出，不替你挑；找不到时列最多 5 条非同名结果供核对。
  - 模糊档给多个词时，标题含任意一个就算命中；范围变宽，不是变窄。
  - 语义档的相关词由模型生成并先打印；`--terms` 可覆盖；脚本不内置词表；不传时只搜概念本身并提示补词。
  - 搜索页一页最多 40 条；模糊档满页会提示；要更多用语义档给一组相关词。语义档是相关词展开，不是向量语义，标题里一个相关词都没有的书找不到。
  - 批量导出仍按 `--series` 清单逐条跑，不拿模糊/语义结果凑。
- 退出码那段改成：搜索三种模式与系列模式共用 `0/2/3/1`；`2` 是一条也没匹配上且没登录；`3` 是没匹配上但不是登录问题。
- 完成判据补：跑完报共几条、有没有满页、命中词数最多的前几条、哪些词 0 条。

- [ ] **Step 2: 改技能 `README.md`**

- 「搜书与列各期」的命令块换成上面三种；保留系列命令。
- 说明精确、模糊（或）、语义（相关词展开、合并去重）的区别。
- 脚本分工表：
  - `weread_search.py` 改成「搜索命令行入口：精确、模糊、语义、按系列逐期列全」。
  - `issues.py` 改成「期刊各期的纯逻辑：标题模板、缺号、清单渲染」。
  - 加一行 `matches.py`：「搜书的纯逻辑：标题归一化、精确/模糊匹配、相关词合并排序、文字输出」。
- 最后一句「只有 … 有单元测试」把 `matches.py` 加进去。

- [ ] **Step 3: 改仓库根 `README.md`**

`weread-book-export` 那一行末尾改成：

```
另有搜索入口：按完整书名精确找，按标题关键词模糊找（多个词任意一个命中），或按一组相关词做语义扩展、合并去重；也能按「系列名 + 年份」逐期精确搜索列全某杂志各期，绕开搜索页约 40 条的上限。
```

- [ ] **Step 4: 版本号**

先看两处当前版本：

```bash
grep '"version"' C:/Study/shared-skills/plugin/.claude-plugin/plugin.json
grep '"version"' C:/Study/shared-skills/.claude-plugin/marketplace.json
```

- 如果上一批搜索改动还没单独交付、与本批一起提交：两处保持 `1.31.7`。
- 如果上一批已经单独提交并交付：两处都改成 `1.31.8`。
- 两处必须一致。

- [ ] **Step 5: 跑测试与检查**

```bash
bash tests/run.sh weread-book-export
bash checks/verify.sh --changed
git diff --check
grep -nP '[^\x00-\x{FFFF}]' \
  C:/Study/shared-skills/plugin/skills/weread-book-export/SKILL.md \
  C:/Study/shared-skills/plugin/skills/weread-book-export/README.md \
  C:/Study/shared-skills/README.md \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/matches.py \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/weread.py \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/weread_search.py \
  C:/Study/shared-skills/docs/superpowers/specs/2026-11-15-weread-search-modes-design.md \
  C:/Study/shared-skills/docs/superpowers/plans/2026-11-15-weread-search-modes.md
find C:/Study/shared-skills/plugin -name __pycache__ -o -name '*.pyc'
```

Expected: 测试与检查全过；非 BMP 扫描无输出；`find` 无输出。

- [ ] **Step 6: 提交（经使用者同意后）**

```bash
git add plugin/skills/weread-book-export/SKILL.md \
        plugin/skills/weread-book-export/README.md \
        README.md \
        plugin/.claude-plugin/plugin.json \
        .claude-plugin/marketplace.json \
        docs/superpowers/specs/2026-11-15-weread-search-modes-design.md \
        docs/superpowers/plans/2026-11-15-weread-search-modes.md
git commit -m "docs(skills): weread-book-export 三种搜书方式" \
           -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: 浏览器实测与收尾

**Files:** 不改代码；实测，必要时修。

- [ ] **Step 1: 准备临时配置目录**

用 `C:/Study/shared-skills/.tmp/weread-issues/profile`（前面探路用过的匿名目录）。不碰 `%LOCALAPPDATA%\weread-book-export\browser-profile`。

- [ ] **Step 2: 精确档**

```bash
cd C:/Study/shared-skills
PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 uv run --with playwright python \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/weread_search.py \
  --exact "财经（2026年第5期）" \
  --profile C:/Study/shared-skills/.tmp/weread-issues/profile
```

Expected: 1 本，标题《财经（2026年第5期）》，地址 `https://weread.qq.com/web/reader/7e232100813abb368g01640b`；退出码 0。

再跑一个明知不对的：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 uv run --with playwright python \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/weread_search.py \
  --exact "第一财经（2026年第5期）" \
  --profile C:/Study/shared-skills/.tmp/weread-issues/profile
```

Expected: 没有同名；最多 5 条非同名，其中一条是《财经（2026年第5期）》；匿名目录退出码 2。

- [ ] **Step 3: 模糊档**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 uv run --with playwright python \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/weread_search.py \
  --fuzzy "估值" \
  --profile C:/Study/shared-skills/.tmp/weread-issues/profile
```

Expected: 40 条，每条标题都含「估值」，末尾有满页提示；退出码 0。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 uv run --with playwright python \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/weread_search.py \
  --fuzzy "估值 价值投资" \
  --profile C:/Study/shared-skills/.tmp/weread-issues/profile
```

Expected: 每条标题至少含其中一个词；不要求比单搜「估值」多（页面仍受 40 条上限影响）。

- [ ] **Step 4: 语义档**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 uv run --with playwright python \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/weread_search.py \
  --semantic "AI" --terms "人工智能,大模型,机器学习,深度学习,AIGC,ChatGPT,智能体" \
  --profile C:/Study/shared-skills/.tmp/weread-issues/profile
```

Expected: 打印 8 个词；每个词一行进度和条数；合并结果按命中词数从多到少；末尾按词统计，0 条和满页都有标记；退出码 0。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 uv run --with playwright python \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/weread_search.py \
  --semantic "AI" \
  --profile C:/Study/shared-skills/.tmp/weread-issues/profile
```

Expected: 只搜「AI」；打印补相关词的提示。

- [ ] **Step 5: 系列档**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 uv run --with playwright python \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/weread_search.py \
  --series 财经 --year 2026 --max 60 \
  --profile C:/Study/shared-skills/.tmp/weread-issues/profile
```

Expected: 23 期，第 1～23 期都在，没有缺号；「另见」有年刊；跑完不再为第 24～60 期各等 30 秒。

- [ ] **Step 6: 参数与退出码**

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with playwright python \
  C:/Study/shared-skills/plugin/skills/weread-book-export/scripts/weread_search.py \
  --exact "x" --fuzzy "y"
```

Expected: 退出码 1，打印「只能给一个」。

- [ ] **Step 7: 记录结果、清理临时目录**

把每条命令的条数、退出码、异常记下来。确认没有要保留的探路文件后：

```bash
cd C:/Study/shared-skills
rm -rf C:/Study/shared-skills/.tmp/weread-issues
```

如果删除被安全策略拦住，把目录路径报给使用者，让使用者删或批准。

---

## Self-Review

**1. Spec coverage:**
- 精确档：Task 1、Task 3、Task 5、Task 9。
- 模糊档（或）：Task 2、Task 3、Task 5、Task 9。
- 语义档（相关词、合并、排序）：Task 2、Task 3、Task 6、Task 9。
- 服务端状态与 DOM 回退：Task 4、Task 7、Task 9。
- 大小写折叠：Task 1。
- 参数与退出码：Task 5、Task 6、Task 9。
- 移除 `--keyword`：Task 5、Task 8。
- 文档与版本：Task 8。
- 测试与检查：每个任务的测试步骤，Task 8 的全量检查，Task 9 的实测。

**2. Step scan:** 每一步都有可检查的结果（测试失败/通过、命令输出、提交）。没有「处理边缘情况」这类空话。

**3. Type consistency:**
- `search_books_page` 返回 `hits`、`total_count`、`has_more`、`logged_in`，全计划一致。
- `per_term` 在 Task 3 和 Task 6 都用 `term`、`hits`、`capped`；Task 6 多一个 `logged_in`，只给 `run_semantic` 用，`render_semantic` 不读它。
- `merge_hits` 输出 `title`、`author`、`href`、`terms`、`order`，Task 3 和 Task 6 一致。
- `check_args` 返回 `"exact"`、`"fuzzy"`、`"semantic"`、`"series"`，Task 5 和 Task 6 一致。

**4. Review Focus:** 五条都在对应任务里有测试；第 5 条的回退路径在 Task 9 实测。

**5. Proportion:** 计划比设计长，但主要是测试断言和命令；没有把实现函数体全文抄进来。
