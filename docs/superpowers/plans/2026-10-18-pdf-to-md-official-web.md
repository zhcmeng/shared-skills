# pdf-to-md 官网网页上传解析 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `pdf-to-md` 增加官网网页上传解析，并让它成为默认方式；本地 API 仍可用 `--backend api` 选择。

**Architecture:** 新增 `aistudio_web.py` 管浏览器（登录、上传、轮询任务、下载 JSON），`markdown.py` 新增官网 JSON 适配器把结果变成现有 `Page` 列表，`convert.py` 用 `--backend` 分流并复用原来的清理、取图、落盘流程。官网结果已经由服务端合并跨页表格，不再跑现有合并逻辑。

**Tech Stack:** Python 3、Playwright（同步 API）、requests、lxml、tabulate、unittest。

**Spec:** `docs/superpowers/specs/2026-10-18-pdf-to-md-official-web-design.md`

## Global Constraints

- 默认 `--backend official-web`；`--backend api` 保持原有行为。
- `--source-type financial` 只对 `--backend api` 有效；官网方式给 `financial` 要报错。
- 账号、密码、cookie 不写进仓库、日志、提交、调试产物；凭据文件在仓库外。
- 正文、注释、错误信息写中文；新增脚本与测试文件名用英文。
- 改文件用 Read / Edit / Write，不用 Bash 重写文件。
- 脚本内部的轮询间隔可以用固定秒数；跑命令时不用 `sleep` 等结果。
- 插件版本在交付时抬到 `1.28.0`，两处版本文件一致。
- 不推送远端，除非用户明确同意。

**测试命令：**

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python tests/pdf-to-md/test_pdf_to_md.py
```

**检查命令：**

```bash
bash tests/run.sh pdf-to-md
bash checks/verify.sh --changed
```

## Review Focus

- 浏览器配置目录被另一个 Edge 占用时，必须说清「先关掉那个浏览器」，不能只抛 Playwright 原文。
- 未登录且没有凭据文件时，脚本要停下来等人，并在超时后报出配置目录；不能无限等。
- 下载菜单改版时，必须退回任务详情里的 `parsingResult`，不能整份失败。
- 官网图片地址带签名会过期，解析完要立刻下载，不能先存 JSON 回头再取图。
- 网址输入下载回来的是登录页或错误页时，要报「不是 PDF」，不能把 HTML 当 PDF 上传。

---

### Task 1: 官网 JSON 适配器

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/markdown.py`
- Test: `tests/pdf-to-md/test_pdf_to_md.py`

**Interfaces:**
- Produces: `markdown.OfficialJsonError`（异常类）
- Produces: `markdown.parse_official_json(raw: str) -> list[Page]`
- 复用：`markdown._page_geometry(pruned: dict) -> (blocks, page_size, tables)`
- 复用：`markdown.Page`

- [ ] **Step 1: Write the failing tests**

在 `tests/pdf-to-md/test_pdf_to_md.py` 的 `TestParseJsonl` 后面加：

```python
class TestParseOfficialJson(unittest.TestCase):
    def item(self, text="正文", images=None, width=None, height=None,
             blocks=None):
        pruned = {"parsing_res_list": blocks or []}
        if width is not None:
            pruned["width"] = width
        if height is not None:
            pruned["height"] = height
        return {"markdown": {"text": text, "images": images or {}},
                "prunedResult": pruned}

    def test_a_top_level_list_is_one_page_per_item(self):
        raw = json.dumps([self.item("a"), self.item("b")])
        pages = markdown.parse_official_json(raw)
        self.assertEqual([p.text for p in pages], ["a", "b"])
        self.assertEqual([p.index for p in pages], [0, 1])

    def test_a_layout_parsing_results_object_is_accepted(self):
        raw = json.dumps({"layoutParsingResults": [self.item("a")]})
        pages = markdown.parse_official_json(raw)
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].text, "a")

    def test_images_and_geometry_are_collected(self):
        raw = json.dumps([self.item(
            images={"imgs/a.jpg": "https://example.com/a.jpg"},
            width=1191, height=1685,
            blocks=[{"block_label": "table", "block_bbox": [1, 2, 3, 4],
                     "block_content": "<table><tr><td>x</td></tr></table>"}])])
        page = markdown.parse_official_json(raw)[0]
        self.assertEqual(page.images,
                         {"imgs/a.jpg": "https://example.com/a.jpg"})
        self.assertEqual(page.page_size, (1191.0, 1685.0))
        self.assertEqual(page.blocks, (("table", (1.0, 2.0, 3.0, 4.0)),))
        self.assertEqual(len(page.tables), 1)

    def test_missing_markdown_and_pruned_result_are_tolerated(self):
        raw = json.dumps([{}])
        page = markdown.parse_official_json(raw)[0]
        self.assertEqual(page.text, "")
        self.assertEqual(page.images, {})
        self.assertEqual(page.blocks, ())
        self.assertIsNone(page.page_size)

    def test_downloaded_items_without_width_and_height_still_parse(self):
        raw = json.dumps([self.item("a")])
        self.assertIsNone(markdown.parse_official_json(raw)[0].page_size)

    def test_invalid_json_raises_official_json_error(self):
        with self.assertRaises(markdown.OfficialJsonError):
            markdown.parse_official_json("{not json")

    def test_a_non_list_non_object_top_level_raises(self):
        with self.assertRaises(markdown.OfficialJsonError):
            markdown.parse_official_json("42")

    def test_a_non_object_item_raises(self):
        with self.assertRaises(markdown.OfficialJsonError):
            markdown.parse_official_json(json.dumps([1]))

    def test_an_empty_list_gives_no_pages(self):
        self.assertEqual(markdown.parse_official_json("[]"), [])
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python tests/pdf-to-md/test_pdf_to_md.py TestParseOfficialJson
```

Expected: FAIL，`AttributeError: module 'markdown' has no attribute 'parse_official_json'`。

- [ ] **Step 3: Implement the adapter**

在 `markdown.py` 的 `JsonlLineError` 旁边加：

```python
class OfficialJsonError(Exception):
    """官网下载的 JSON 没法用：不是合法 JSON，或者结构不对。"""
```

在 `parse_jsonl` 后面加：

```python
def _official_items(raw):
    """把顶层列表或 layoutParsingResults 对象摊成每页一项的列表。"""


def parse_official_json(raw: str) -> list[Page]:
    """把官网下载的 JSON 摊成页表。"""
```

实现要点：

- `raw` 不是 `str` 抛 `OfficialJsonError`。
- `json.loads` 的 `JSONDecodeError`、`ValueError`、`RecursionError` 都包成 `OfficialJsonError`。
- 顶层是 `dict` 时：`errorCode` 非 0 抛错；`layoutParsingResults` 必须是列表。
- 顶层是 `list` 时直接当项列表。
- 其他类型抛错。
- 每一项必须是 `dict`。
- `markdown` 缺失按 `{}`；`text` 缺失或 `None` 按 `""`，不是字符串就抛错。
- `images` 缺失按 `{}`；不是字典就抛错，然后 `dict(images)`。
- `prunedResult` 缺失或不是字典按 `{}`；交给 `_page_geometry`。
- 页码从 0 起，按项序。

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python tests/pdf-to-md/test_pdf_to_md.py TestParseOfficialJson
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/pdf-to-md/scripts/markdown.py tests/pdf-to-md/test_pdf_to_md.py
git commit -m "feat(pdf-to-md): 适配官网下载的 JSON"
```

---

### Task 2: 官网模块的纯逻辑

**Files:**
- Create: `plugin/skills/pdf-to-md/scripts/aistudio_web.py`
- Test: `tests/pdf-to-md/test_pdf_to_md.py`

**Interfaces:**
- Produces: `aistudio_web.default_profile_dir() -> str`
- Produces: `aistudio_web.default_credentials_path() -> str`
- Produces: `aistudio_web.load_credentials(path: str | None = None) -> dict | None`，返回 `{"username": str, "password": str}` 或 `None`
- Produces: `aistudio_web.task_id_from_url(url: str) -> str | None`
- Produces: `aistudio_web.poll_task(fetch_detail, task_url: str, timeout: float, interval: float = 2.0, on_progress=None, clock=time.monotonic, sleep=time.sleep) -> dict`
- Produces: `aistudio_web.official_json_from_detail(detail: dict) -> str`
- Produces: 异常 `OfficialWebError`、`BrowserError`、`LoginRequired`、`TaskFailed`、`DownloadFailed`
- 约束：模块顶层**不 import playwright**，只在启动浏览器时在函数里 import。

- [ ] **Step 1: Write the failing tests**

在测试文件里加：

```python
class TestOfficialWebPaths(unittest.TestCase):
    def test_profile_and_credentials_live_under_one_directory(self):
        profile = aistudio_web.default_profile_dir()
        cred = aistudio_web.default_credentials_path()
        self.assertTrue(profile.endswith("browser-profile"))
        self.assertTrue(cred.endswith("credentials.json"))
        self.assertEqual(os.path.dirname(os.path.dirname(profile)),
                         os.path.dirname(cred))


class TestLoadCredentials(unittest.TestCase):
    def write(self, data):
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                        encoding="utf-8")
        self.addCleanup(os.remove, f.name)
        f.write(data)
        f.close()
        return f.name

    def test_a_missing_file_gives_none(self):
        self.assertIsNone(aistudio_web.load_credentials(
            os.path.join(tempfile.gettempdir(), "没有这个文件.json")))

    def test_empty_fields_give_none(self):
        path = self.write('{"username": "", "password": ""}')
        self.assertIsNone(aistudio_web.load_credentials(path))

    def test_a_complete_file_gives_both_fields(self):
        path = self.write('{"username": "u", "password": "p"}')
        self.assertEqual(aistudio_web.load_credentials(path),
                         {"username": "u", "password": "p"})

    def test_bad_json_names_the_path_but_not_the_contents(self):
        path = self.write("{oops")
        with self.assertRaises(aistudio_web.BrowserError) as ctx:
            aistudio_web.load_credentials(path)
        self.assertIn(path, str(ctx.exception))
        self.assertNotIn("oops", str(ctx.exception))


class TestTaskIdFromUrl(unittest.TestCase):
    def test_a_task_url_gives_the_id(self):
        self.assertEqual(
            aistudio_web.task_id_from_url(
                "https://aistudio.baidu.com/paddleocr/task/file/t-abc123"),
            "t-abc123")

    def test_other_urls_give_none(self):
        self.assertIsNone(aistudio_web.task_id_from_url(
            "https://aistudio.baidu.com/paddleocr/task/new"))


class TestPollTask(unittest.TestCase):
    def clock(self, step=1.0):
        state = {"t": 0.0}
        return (lambda: state["t"],
                lambda seconds: state.__setitem__("t", state["t"] + seconds),
                lambda: state.__setitem__("t", state["t"] + step))

    def detail(self, status, extracted=None, total=None, error_code=0,
               error_msg="Success", parsed=None):
        result = {"taskStatus": status}
        if extracted is not None:
            result["extractedPages"] = extracted
        if total is not None:
            result["totalPages"] = total
        if parsed is not None:
            result["parsingResult"] = parsed
        return {"errorCode": error_code, "errorMsg": error_msg,
                "result": result}

    def test_status_five_is_done(self):
        now, _, tick = self.clock()
        calls = [self.detail(5, 3, 3, parsed="{}")]
        seen = []
        got = aistudio_web.poll_task(
            lambda: calls.pop(0),
            "https://aistudio.baidu.com/paddleocr/task/file/t-1",
            timeout=10, clock=now, sleep=tick)
        self.assertEqual(got["taskStatus"], 5)

    def test_progress_is_reported(self):
        now, _, tick = self.clock()
        calls = [self.detail(4, 1, 3), self.detail(5, 3, 3)]
        seen = []
        aistudio_web.poll_task(
            lambda: calls.pop(0), "u", timeout=10,
            on_progress=lambda d, t: seen.append((d, t)),
            clock=now, sleep=tick)
        self.assertIn((1, 3), seen)
        self.assertIn((3, 3), seen)

    def test_a_negative_status_fails(self):
        now, _, tick = self.clock()
        with self.assertRaises(aistudio_web.TaskFailed):
            aistudio_web.poll_task(lambda: self.detail(-5), "u", timeout=10,
                                   clock=now, sleep=tick)

    def test_an_unknown_non_negative_status_keeps_waiting(self):
        now, _, tick = self.clock()
        calls = [self.detail(3), self.detail(5)]
        got = aistudio_web.poll_task(lambda: calls.pop(0), "u", timeout=10,
                                     clock=now, sleep=tick)
        self.assertEqual(got["taskStatus"], 5)

    def test_timeout_names_the_task_url(self):
        now, _, tick = self.clock()
        with self.assertRaises(aistudio_web.TaskFailed) as ctx:
            aistudio_web.poll_task(lambda: self.detail(4, 1, 3),
                                   "https://example.com/task", timeout=3,
                                   clock=now, sleep=tick)
        self.assertIn("https://example.com/task", str(ctx.exception))


class TestOfficialJsonFromDetail(unittest.TestCase):
    def test_parsing_result_is_returned_verbatim(self):
        detail = {"result": {"parsingResult": '{"layoutParsingResults": []}'}}
        self.assertEqual(aistudio_web.official_json_from_detail(detail),
                         '{"layoutParsingResults": []}')

    def test_a_missing_result_raises(self):
        with self.assertRaises(aistudio_web.TaskFailed):
            aistudio_web.official_json_from_detail({"result": {}})
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python tests/pdf-to-md/test_pdf_to_md.py TestOfficialWebPaths TestLoadCredentials TestTaskIdFromUrl TestPollTask TestOfficialJsonFromDetail
```

Expected: FAIL，`ModuleNotFoundError: No module named 'aistudio_web'`。

- [ ] **Step 3: Implement the pure logic in `aistudio_web.py`**

实现要点：

- 顶部只 import：`json`、`os`、`sys`、`tempfile`、`time`、`dataclasses`、`threading`（如需）。
- `default_base_dir()`：Windows 用 `LOCALAPPDATA`，否则 `XDG_CONFIG_HOME` 或 `~/.config`，再拼 `pdf-to-md`。
- `default_profile_dir()`：`base/browser-profile`。
- `default_credentials_path()`：`base/credentials.json`。
- `load_credentials(path=None)`：文件不存在返回 `None`；`json.load` 失败或不是对象抛 `BrowserError`，消息里带路径、不带文件内容；`username` / `password` 去空白后都非空才返回。
- `task_id_from_url(url)`：找 `/paddleocr/task/file/`，取最后一段；不是这个形状返回 `None`。
- `poll_task`：
  - 每次 `fetch_detail()` 拿顶层字典。
  - `errorCode` 非 0 → `TaskFailed`，带上 `errorMsg`。
  - `result` 不是字典 → `TaskFailed`。
  - `taskStatus == 5` → 返回 `result`。
  - `taskStatus < 0` → `TaskFailed`，消息带状态和任务 URL。
  - 其余非负状态 → 有 `extractedPages` / `totalPages` 就调 `on_progress`；继续。
  - `clock() - started > timeout` → `TaskFailed`，消息带最后状态、进度、任务 URL。
  - 每次等待 `sleep(interval)`。
- `official_json_from_detail(detail)`：取 `result["parsingResult"]`；不是非空字符串就抛 `TaskFailed`。
- 异常类都继承 `OfficialWebError`。

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python tests/pdf-to-md/test_pdf_to_md.py TestOfficialWebPaths TestLoadCredentials TestTaskIdFromUrl TestPollTask TestOfficialJsonFromDetail
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/pdf-to-md/scripts/aistudio_web.py tests/pdf-to-md/test_pdf_to_md.py
git commit -m "feat(pdf-to-md): 加官网模块的路径、凭据与状态轮询"
```

---

### Task 3: 浏览器流程

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/aistudio_web.py`

**Interfaces:**
- Produces: `aistudio_web.WebOutcome`（dataclass：`json_text: str`、`task_id: str`、`task_url: str`、`detail: dict`）
- Produces: `aistudio_web.WebSession(...)`，方法：
  - `start() -> None`
  - `ensure_login() -> None`
  - `materialize(target: str, name: str) -> str`（本地路径原样返回；网址下载到临时文件）
  - `parse(target: str, on_progress=None, debug_dir: str | None = None) -> WebOutcome`
  - `snapshot(debug_dir: str) -> None`
  - `close() -> None`
  - 支持 `with WebSession(...) as session:`

- [ ] **Step 1: Implement `WebSession.start()` and login**

- 在函数里 `from playwright.sync_api import sync_playwright, Error`，顶层不 import。
- `start()`：
  - `self._playwright = sync_playwright().start()`
  - `self._context = self._playwright.chromium.launch_persistent_context(
      self.profile_dir, channel=self.channel, headless=False,
      args=["--no-first-run", "--no-default-browser-check"])`
  - `self.page = self._context.pages[0] if self._context.pages else self._context.new_page()`
  - 启动失败时抛 `BrowserError`，消息里带：配置目录、`--browser-channel` 的改法、如果提示 profile 被占用就让人先关掉开着同一个配置目录的浏览器。
- `channel` 默认：`sys.platform == "win32"` 时 `"msedge"`，否则 `"chrome"`。
- `ensure_login()`：
  - `goto(NEW_TASK_URL, wait_until="domcontentloaded", timeout=60000)`。
  - `_logged_in(page)`：`page.locator("button.a-s-header-login-btn")` 不存在或不可见。
  - 已登录直接返回。
  - 读凭据；有凭据：点登录按钮，等 `input[id$="__userName"]` 可见，填用户名密码，点 `input[id$="__submit"]`。只填，不打印。
  - 打印「请在打开的浏览器窗口里完成登录（有验证码就在这里完成）；登录后脚本会自动继续」。
  - 每 2 秒检查一次，直到 `login_timeout`；超时抛 `LoginRequired`，消息带配置目录。
  - 关掉可能还开着的登录弹窗（按 Escape）。

- [ ] **Step 2: Implement `materialize()`**

- 本地路径：`os.path.abspath(target)`，存在就返回。
- 网址：
  - `requests.get(url, stream=True, timeout=(30, 300))`，`raise_for_status()` 失败包成 `OfficialWebError`。
  - 读前 1024 字节，`lstrip()` 后不以 `%PDF` 开头 → 抛 `OfficialWebError`，消息带 `Content-Type` 和 HTTP 状态，说明「网址返回的不是 PDF」。
  - 写进 `tempfile.mkdtemp(prefix="pdf-to-md-web-")` 下的 `<name>.pdf`；逐块写入，超过 200MB 报错并删文件。
  - 临时目录记在 `self._temp_dirs`，`close()` 时 `shutil.rmtree`。
- 本地文件不存在抛 `OfficialWebError`（或让 `set_input_files` 抛，包一层更清楚）。

- [ ] **Step 3: Implement upload, poll, download**

- `_upload(local_path)`：
  - `goto(NEW_TASK_URL)`。
  - 等 `input[type=file][multiple]` 出现（30 秒）。
  - `set_input_files(local_path)`。
  - 等 URL 含 `/paddleocr/task/file/`（`upload_timeout` 默认 900 秒）。
  - 取 `task_id`；取不到抛 `OfficialWebError`。
  - 返回 `task_url`。
- `_fetch_detail(task_id)`：`self._context.request.get(url, timeout=30000)`，返回 `resp.json()`；网络错误重试 3 次，仍失败抛 `OfficialWebError`。
- `_poll(task_id, task_url, on_progress)`：调用 Task 2 的 `poll_task(self._fetch_detail(task_id), task_url, self.web_timeout, on_progress=on_progress)`。
- `_download_json(detail)`：
  - 等 `.parse-render-content-title-handle` 可见（60 秒）。
  - 取它下面的 `button`；等到至少 4 个且第 4 个可用。
  - 点第 4 个；等 `.ant-dropdown-menu-item` 里含 `JSON` 的那项可见。
  - `with self.page.expect_download(timeout=120000) as info: item.click()`。
  - `download.save_as()` 到临时文件；按 UTF-8（`utf-8-sig`）读文本返回。
  - 任何一步失败：`official_json_from_detail(detail)` 兜底，并打印一行提示「下载菜单没取到，改用任务详情里的 JSON」。
- `parse()` 串起来：`materialize` → `_upload` → `_poll` → `_download_json` → 返回 `WebOutcome`。
- `snapshot(debug_dir)`：
  - 目标选择器 `.parse-render-content`（没有就退回 `body`）。
  - 截图存 `web/task-page.png`；元素 `inner_html()` 存 `web/task-page.html`。
  - 失败不抛（调试信息取不到不能把主流程带崩）。

- [ ] **Step 4: Manual smoke test with the 1-page sample**

用临时输出目录跑：

```bash
uv run --with requests --with lxml --with tabulate --with playwright \
  python plugin/skills/pdf-to-md/scripts/convert.py \
  plugin/skills/pdf-to-md/assets/doctor-sample.pdf \
  --output <临时目录> --debug
```

Expected：浏览器打开；已登录时直接上传；输出目录有 `doctor-sample/doctor-sample.md`；`debug/<时间戳>/raw/official.json` 存在；`web/task-page.png` 与 `.html` 存在。

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/pdf-to-md/scripts/aistudio_web.py
git commit -m "feat(pdf-to-md): 加官网上传、轮询与下载流程"
```

---

### Task 4: 命令行与流程分流

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/convert.py`
- Test: `tests/pdf-to-md/test_pdf_to_md.py`

**Interfaces:**
- Produces: `convert.parse_args(argv=None)` 里的 `args.backend`、`args.browser_profile`、`args.browser_channel`、`args.web_timeout`、`args.login_timeout`、`args.no_wait_login`
- Produces: `convert.run_web(tasks, args) -> int`
- Modify: `convert.convert_one(..., backend: str = "api", web_session=None)`；`backend == "official-web"` 时走 `web_session`
- 复用：`convert.Progress`、`convert.Result`、`convert._finish_document`、`convert.already_done`

- [ ] **Step 1: Write the failing tests**

```python
class TestParseArgsBackend(unittest.TestCase):
    def parse(self, *extra):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return convert.parse_args(
            ["a.pdf", "--output", os.path.join(tmp.name, "out"), *extra])

    def test_official_web_is_the_default(self):
        args = self.parse()
        self.assertEqual(args.backend, "official-web")
        self.assertEqual(args.source_type, "general")

    def test_api_can_be_selected(self):
        self.assertEqual(self.parse("--backend", "api").backend, "api")

    def test_financial_is_only_for_the_api_backend(self):
        with self.assertRaises(SystemExit):
            self.parse("--backend", "official-web",
                       "--source-type", "financial")

    def test_a_different_model_is_rejected_for_the_web_backend(self):
        with self.assertRaises(SystemExit):
            self.parse("--model", "PP-StructureV3")

    def test_web_options_are_parsed(self):
        args = self.parse("--browser-profile", "p",
                          "--browser-channel", "chrome",
                          "--web-timeout", "60", "--login-timeout", "30",
                          "--no-wait-login")
        self.assertEqual(args.browser_profile, "p")
        self.assertEqual(args.browser_channel, "chrome")
        self.assertEqual(args.web_timeout, 60)
        self.assertEqual(args.login_timeout, 30)
        self.assertTrue(args.no_wait_login)


class TestRunWeb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = io.StringIO()
        for name in ("stdout", "stderr"):
            p = mock.patch("sys." + name, self.out)
            p.start()
            self.addCleanup(p.stop)

    def args(self, **kw):
        base = dict(output=self.tmp.name, backend="official-web",
                    source_type="general", jobs=1, page_jobs=1,
                    model=aistudio.DEFAULT_MODEL, force=False, debug=False,
                    browser_profile=None, browser_channel=None,
                    web_timeout=60, login_timeout=30, no_wait_login=False)
        base.update(kw)
        return argparse.Namespace(**base)

    def test_a_failing_file_does_not_stop_the_next_one(self):
        tasks = [convert.Task("/tmp/a.pdf", "a", "a"),
                 convert.Task("/tmp/b.pdf", "b", "b")]

        class FakeSession:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def ensure_login(self, *a, **k): pass
            def close(self): pass

        def fake(task, *a, **k):
            if task.name == "a":
                raise aistudio_web.TaskFailed("坏了")
            return convert.Result("b", 1, 0.1, [])

        with mock.patch.object(aistudio_web, "WebSession", FakeSession), \
             mock.patch.object(convert, "convert_one", fake):
            self.assertEqual(convert.run_web(tasks, self.args()), 1)
        self.assertIn("\n  a：坏了", self.out.getvalue())

    def test_web_does_not_fetch_the_api_token(self):
        tasks = [convert.Task("/tmp/a.pdf", "a", "a")]
        with mock.patch.object(aistudio, "get_token",
                               side_effect=AssertionError("不该拿 token")), \
             mock.patch.object(aistudio_web, "WebSession"), \
             mock.patch.object(convert, "convert_one",
                               lambda *a, **k: convert.Result("a", 1, 0.1, [])):
            self.assertEqual(convert.run_web(tasks, self.args()), 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python tests/pdf-to-md/test_pdf_to_md.py TestParseArgsBackend TestRunWeb
```

Expected: FAIL，`SystemExit` 或 `AttributeError`。

- [ ] **Step 3: Implement CLI and dispatch**

- `parse_args`：
  - `--backend`，`choices=("official-web", "api")`，`default="official-web"`。
  - `--browser-profile`、`--browser-channel`、`--web-timeout`（默认 3600）、`--login-timeout`（默认 600）、`--no-wait-login`。
  - 校验：
    - `official-web` + `financial` → `parser.error(...)`。
    - `official-web` + `--model` 不是 `PaddleOCR-VL-1.6` → `parser.error(...)`。
    - `web-timeout`、`login-timeout` 至少 1。
  - `--model` 默认值仍按 `aistudio.DEFAULT_MODEL`；官网方式下它就是 `PaddleOCR-VL-1.6`。
- `main`：依赖检查按 backend 选列表；`official-web` 的 hint 带 `--with playwright`；构造 tasks 后 `return run_web(tasks, args)` 或 `return run(tasks, args)`。
- `run`：`backend = getattr(args, "backend", "api")`；`token = aistudio.get_token() if todo and backend == "api" else None`；`convert_one(..., backend=backend)`。
- `convert_one`：
  - 新参数 `backend="api"`、`web_session=None`。
  - `backend == "official-web"`：
    - `outcome = web_session.parse(task.target, on_progress=on_pages, debug_dir=debug_dir)`
    - debug 写 `raw/official.json`、`raw/task-detail.json`、`web/task.json`。
    - `pages = md_utils.parse_official_json(outcome.json_text)`
    - `_finish_document(task, out_root, pages, t0, debug_dir=debug_dir)`
  - 失败时 `web_session.snapshot(debug_dir)` 后再抛（`debug_dir` 存在时）。
- `run_web`：
  - 先按 `already_done` 挑 todo；全跳过就直接返回 0。
  - 构造 `WebSession(profile_dir=args.browser_profile, channel=args.browser_channel, login_timeout=args.login_timeout, web_timeout=args.web_timeout, allow_manual_login=not args.no_wait_login)`。
  - `with session:` 里 `session.ensure_login()`，然后按顺序对每个 task 调 `convert_one`。
  - 捕获 `(aistudio_web.OfficialWebError, EmptyDocument, md_utils.OfficialJsonError, OSError)`，一份失败不影响下一份。
  - 进度用 `Progress`；`on_pages` 接到 `progress.pages(task.name, d, t)`。
  - `--jobs > 1` 时打一行「官网方式一次处理一份，--jobs 不生效」。
- `convert_one` 的 `backend` 默认保持 `"api"`，避免现有测试和直接调用被改道。

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python tests/pdf-to-md/test_pdf_to_md.py TestParseArgsBackend TestRunWeb
```

Expected: PASS。

- [ ] **Step 5: Run the whole pdf-to-md test file**

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python tests/pdf-to-md/test_pdf_to_md.py
```

Expected: 全部 PASS（原有测试不改）。

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/pdf-to-md/scripts/convert.py tests/pdf-to-md/test_pdf_to_md.py
git commit -m "feat(pdf-to-md): 默认走官网上传，本地 API 用 --backend api"
```

---

### Task 5: 体检跟上新默认

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/doctor.py`
- Test: `tests/pdf-to-md/test_pdf_to_md.py`

**Interfaces:**
- Produces: `doctor.parse_args` 的 `args.backend`（默认 `official-web`）
- Modify: `doctor.smoke_command(backend, out_dir)`
- Modify: `doctor.check_smoke(backend=None, runner=None)`
- Produces: `doctor.check_profile_dir(path=None)`、`doctor.check_credentials(path=None)`

- [ ] **Step 1: Update the doctor tests**

在现有 `TestDoctor` 里：

- 默认 backend 是 `official-web`。
- 官网方式不再要求 token；`--backend api` 才跑 `check_token`。
- `smoke_command("official-web", out)` 里要有 `--with playwright`、`--backend official-web`、`--no-wait-login`。
- `smoke_command("api", out)` 里要有 `--with pypdf`、`--backend api`，没有 `--with playwright`。
- 凭据文件不存在时只提示，不算不通过。
- 凭据文件存在但 JSON 坏了，报不通过并给出路径。

- [ ] **Step 2: Run the doctor tests to verify they fail**

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python tests/pdf-to-md/test_pdf_to_md.py TestDoctor
```

Expected: FAIL。

- [ ] **Step 3: Implement the doctor changes**

- `parse_args` 加 `--backend`，默认 `official-web`。
- `main`：
  - 官网方式：`checks = [check_uv(), check_profile_dir(), check_credentials()]`，`--output` 时加 `check_output_dir`。
  - API 方式：原来的 `[check_uv(), check_token()]`。
  - 全绿后跑 `check_smoke(backend)`。
- `smoke_command(backend, out_dir)` 按 backend 返回不同列表。
- `check_profile_dir`：对配置目录最近的已存在上级调 `_probe_writable`。
- `check_credentials`：文件不存在 → `Check(..., True, "没有凭据文件；第一次会在浏览器里让你手动登录。")`；存在但解析失败 → 不通过，fix 写清文件路径和正确格式；字段不全 → 不通过。
- 官网方式的 smoke 超时放宽到 600 秒（要开浏览器、等上传）。

- [ ] **Step 4: Run the doctor tests to verify they pass**

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python tests/pdf-to-md/test_pdf_to_md.py TestDoctor
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/pdf-to-md/scripts/doctor.py tests/pdf-to-md/test_pdf_to_md.py
git commit -m "feat(pdf-to-md): 体检支持官网方式"
```

---

### Task 6: 文档、版本与完整验收

**Files:**
- Modify: `plugin/skills/pdf-to-md/SKILL.md`
- Modify: `plugin/skills/pdf-to-md/README.md`
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Update `SKILL.md`**

改写这几节：

- 开头：默认走官网网页上传；本地 API 用 `--backend api`。
- 「前置」：官网方式第一次要登录；本地 API 才需要 token。
- 「怎么调」：命令加 `--with playwright`；参数表加 `--backend`、`--browser-profile`、`--browser-channel`、`--web-timeout`、`--login-timeout`、`--no-wait-login`。
- 新增「官网方式：第一次先登录」：配置目录、凭据文件格式与路径、手动登录提示、验证码要手动完成。
- 「财报：逐页提交」：标明只属于 `--backend api`。
- 「调试：保留完整过程」：加 `raw/official.json`、`raw/task-detail.json`、`web/task-page.png`、`web/task-page.html`，并写明不保存 cookie/账号/密码。
- 「出问题先体检」：体检默认查官网方式，`--backend api` 查本地 API。
- 「配额与错误」：本地 API 每天 20000 页；官网配额以页面提示为准；状态 4/5/-5 的人话解释。
- 「已知局限」：官网方式要开浏览器、一次一份、首次要登录；本地 API 的宽表降级保留说明；官网结果不再跑跨页合并。

- [ ] **Step 2: Update `README.md`**

文件结构加 `aistudio_web.py`；「改脚本」补一句官网流程要真实 1 页样例手动验收。

- [ ] **Step 3: Bump versions**

`plugin/.claude-plugin/plugin.json` 和 `.claude-plugin/marketplace.json` 都改成 `1.28.0`。

- [ ] **Step 4: Run the full tests and checks**

```bash
bash tests/run.sh pdf-to-md
bash checks/verify.sh --changed
```

Expected: 两份都通过。

- [ ] **Step 5: Manual 1-page web acceptance**

```bash
uv run --with requests --with lxml --with tabulate --with playwright \
  python plugin/skills/pdf-to-md/scripts/convert.py \
  plugin/skills/pdf-to-md/assets/doctor-sample.pdf \
  --output <临时目录> --debug
```

检查：

- md 里有 `DOCTOR-SAMPLE-8642`。
- `debug/<时间戳>/raw/official.json` 是 1 项列表。
- `web/task-page.png` 与 `.html` 存在。
- 产物里 grep 不到密码、cookie。

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/pdf-to-md/SKILL.md plugin/skills/pdf-to-md/README.md \
        plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "docs(pdf-to-md): 说明官网网页上传并抬版本到 1.28.0"
```
