# pdf-to-md 多 KEY 依次消耗 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `pdf-to-md` 的本地 API 方式支持环境变量里配多个 AI Studio KEY，额度用完自动换下一个。

**Architecture:** 在 `aistudio.py` 里加 KEY 列表解析、线程安全的 KEY 池和「被拒原因分类」；在 `convert.py` 里加一个提交函数，额度类拒绝就换 KEY，轮询绑定提交成功的那个 KEY。只有提交这一层知道 KEY 有几个，`submit`/`poll` 仍只收单个 token。

**Tech Stack:** Python 3 标准库 + `requests`；测试用 `unittest`。

**Spec:** `docs/superpowers/specs/2026-11-05-pdf-to-md-multi-token-design.md`

## Global Constraints

- KEY 只从 `PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN` 读（本机配在 `~/.claude/settings.json` 的 `env` 段）。
- KEY 不得出现在代码、测试、文档、提交信息、日志、异常消息、调试产物里；日志只允许出现「KEY 1」这样的序号。
- 单 KEY 时行为与改动前完全一致。
- 只改 `--backend api`；`--backend official-web` 不动。
- 不落盘记录哪个 KEY 已用完。
- 判据按响应体 `code` 优先、HTTP 状态兜底：`code` 12001 = 配额用完；12002 = 限流；401 = token 无效（2026-11-05 实测）；403 无 code = 无权限或旧文档口径的配额；429 无 code = 分不清，先等 5 秒再判。
- 本机未开 VPN 时 Python 到 `paddleocr.aistudio-app.com` 的 TLS 连接会断；跑任何真实请求（手工验收）前先确认 VPN 已开。单元测试不发请求，不受影响。
- 代码与测试都在 shared-skills 插件仓库 `C:/Study/shared-skills/`；下文的相对路径都相对这个目录，提交也在那个仓库做。
- 测试命令：`uv run --with requests --with lxml --with tabulate --with pypdf python C:/Study/shared-skills/tests/pdf-to-md/test_pdf_to_md.py`
- 测试不发真实请求，全部用假响应。

## Review Focus

- 并发页级提交同时撞上额度不足：只能前进一个 KEY，不能跳过中间那个。测试放在 Task 2。
- KEY 值泄露：异常消息、切换日志、`AllTokensExhausted` 文本里只能有序号。测试放在 Task 2、Task 4。
- 限流（`code` 12002）被误判成配额，白白消耗下一个账号的额度。测试放在 Task 3。
- 单 KEY 用户的行为回归：`convert_one(task, root, "m", "t")` 仍按单 KEY 正常工作。测试放在 Task 5。
- 轮询拿错 KEY：提交成功后必须用提交时那个 KEY 查任务，不能跟着池子的当前值走。测试放在 Task 5、Task 6。

---

### Task 1: 解析环境变量里的多个 KEY

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/aistudio.py:13`、`92-101`
- Test: `tests/pdf-to-md/test_pdf_to_md.py:1465`（`TestGetToken`）

**Interfaces:**
- Consumes: 现有 `TOKEN_ENV`
- Produces: `aistudio.TOKEN_SEPARATOR`、`aistudio.get_tokens() -> list[str]`；`aistudio.get_token() -> str` 保留，返回 `get_tokens()[0]`

- [ ] **Step 1: 写失败的测试**

在 `TestGetToken` 里加：

```python
def test_reads_several_tokens_in_order(self):
    with mock.patch.dict(os.environ, {aistudio.TOKEN_ENV: "a,b"}, clear=False):
        self.assertEqual(aistudio.get_tokens(), ["a", "b"])

def test_trims_spaces_and_drops_empty_items(self):
    with mock.patch.dict(os.environ, {aistudio.TOKEN_ENV: " a , , b ,"}, clear=False):
        self.assertEqual(aistudio.get_tokens(), ["a", "b"])

def test_get_token_still_returns_the_first(self):
    with mock.patch.dict(os.environ, {aistudio.TOKEN_ENV: "a,b"}, clear=False):
        self.assertEqual(aistudio.get_token(), "a")

def test_missing_tokens_mentions_the_comma_syntax(self):
    with mock.patch.dict(os.environ, {}, clear=True):
        with self.assertRaises(SystemExit) as ctx:
            aistudio.get_tokens()
    self.assertIn(aistudio.TOKEN_ENV, str(ctx.exception))
    self.assertIn(",", str(ctx.exception))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run --with requests --with lxml --with tabulate --with pypdf python C:/Study/shared-skills/tests/pdf-to-md/test_pdf_to_md.py`
Expected: `AttributeError: module 'aistudio' has no attribute 'get_tokens'`

- [ ] **Step 3: 实现**

`aistudio.py` 顶部常量区加 `TOKEN_SEPARATOR = ","`。

把 `get_token()` 换成：

```python
def get_tokens():
    raw = os.environ.get(TOKEN_ENV, "")
    tokens = [part.strip() for part in raw.split(TOKEN_SEPARATOR)]
    tokens = [part for part in tokens if part]
    if not tokens:
        raise SystemExit(
            f"环境里没有 {TOKEN_ENV}。\n"
            f"它是这个 skill 唯一认的 token 来源，在 ~/.claude/settings.json 的 "
            f"env 段里设一次即可；多个账号的 token 用英文逗号隔开：\n"
            f'  {{"env": {{"{TOKEN_ENV}": "<token1>,<token2>"}}}}'
        )
    return tokens

def get_token():
    """兼容旧调用：返回第一个 token。"""
    return get_tokens()[0]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run --with requests --with lxml --with tabulate --with pypdf python C:/Study/shared-skills/tests/pdf-to-md/test_pdf_to_md.py`
Expected: 全绿

- [ ] **Step 5: 提交**

```bash
git add tests/pdf-to-md/test_pdf_to_md.py plugin/skills/pdf-to-md/scripts/aistudio.py
git commit -m "feat(pdf-to-md): 解析逗号分隔的多个 AI Studio KEY"
```

---

### Task 2: 线程安全的 KEY 池

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/aistudio.py`（新增 `threading` 导入与两个类）
- Test: `tests/pdf-to-md/test_pdf_to_md.py`（新增 `TestTokenPool`，放在 `TestGetToken` 后面）

**Interfaces:**
- Consumes: `SubmitRejected`
- Produces:
  - `aistudio.AllTokensExhausted(Exception)`，构造参数 `reasons: dict[int, SubmitRejected]`
  - `aistudio.TokenPool(tokens: list[str])`，方法：
    - `current() -> str`，池空时抛 `AllTokensExhausted`
    - `retire(token: str, reason: SubmitRejected) -> bool`，这次是否真的前移
    - `label(token: str) -> str`，如 `"KEY 1"`

- [ ] **Step 1: 写失败的测试**

新增 `class TestTokenPool(unittest.TestCase)`：

```python
def test_hands_tokens_out_in_order(self):
    pool = aistudio.TokenPool(["a", "b"])
    self.assertEqual(pool.current(), "a")
    pool.retire("a", SubmitRejected(429, code=12001))
    self.assertEqual(pool.current(), "b")

def test_retire_returns_false_when_it_is_not_current(self):
    pool = aistudio.TokenPool(["a", "b"])
    self.assertFalse(pool.retire("b", SubmitRejected(429, code=12001)))
    self.assertEqual(pool.current(), "a")

def test_two_threads_retiring_the_same_token_move_once(self):
    pool = aistudio.TokenPool(["a", "b", "c"])
    moves = []
    def retire():
        moves.append(pool.retire("a", SubmitRejected(429, code=12001)))
    threads = [threading.Thread(target=retire) for _ in range(2)]
    for t in threads: t.start()
    for t in threads: t.join()
    self.assertEqual(moves.count(True), 1)
    self.assertEqual(pool.current(), "b")

def test_all_exhausted_lists_each_key_without_the_value(self):
    pool = aistudio.TokenPool(["secret-a", "secret-b"])
    pool.retire("secret-a", SubmitRejected(403, code=12001))
    pool.retire("secret-b", SubmitRejected(429, code=12001))
    with self.assertRaises(aistudio.AllTokensExhausted) as ctx:
        pool.current()
    text = str(ctx.exception)
    self.assertIn("KEY 1", text)
    self.assertIn("KEY 2", text)
    self.assertNotIn("secret-a", text)
    self.assertNotIn("secret-b", text)

def test_label_never_shows_the_token(self):
    pool = aistudio.TokenPool(["secret-a"])
    self.assertEqual(pool.label("secret-a"), "KEY 1")
    self.assertNotIn("secret", pool.label("secret-a"))
```

- [ ] **Step 2: 跑测试确认失败**

Expected: `AttributeError: module 'aistudio' has no attribute 'TokenPool'`

- [ ] **Step 3: 实现**

`aistudio.py` 加 `import threading`，在 `SubmitRejected` 后面加：

```python
class AllTokensExhausted(Exception):
    """所有 KEY 都用完了。消息里只出现序号，不出现 KEY 值。"""

    def __init__(self, reasons):
        lines = ["所有 KEY 都用完了："]
        for index in sorted(reasons):
            lines.append(f"  KEY {index + 1}：{reasons[index]}")
        super().__init__("\n".join(lines))


class TokenPool:
    """按顺序消耗的 KEY 池，线程安全。"""

    def __init__(self, tokens):
        self._tokens = list(tokens)
        self._index = 0
        self._reasons = {}
        self._lock = threading.Lock()

    def current(self):
        with self._lock:
            if self._index >= len(self._tokens):
                raise AllTokensExhausted(dict(self._reasons))
            return self._tokens[self._index]

    def retire(self, token, reason):
        with self._lock:
            if (self._index >= len(self._tokens)
                    or self._tokens[self._index] != token):
                return False
            self._reasons[self._index] = reason
            self._index += 1
            if self._index < len(self._tokens):
                print(f"KEY {self._index} 额度不足，改用 KEY {self._index + 1}")
            else:
                print(f"KEY {self._index} 额度不足，没有更多 KEY 了")
            return True

    def label(self, token):
        with self._lock:
            try:
                return f"KEY {self._tokens.index(token) + 1}"
            except ValueError:
                return "KEY"
```

注意：`print` 放在锁里，保证并发下切换提示不交错。

- [ ] **Step 4: 跑测试确认通过**

Expected: 全绿

- [ ] **Step 5: 提交**

```bash
git add tests/pdf-to-md/test_pdf_to_md.py plugin/skills/pdf-to-md/scripts/aistudio.py
git commit -m "feat(pdf-to-md): 新增线程安全的 KEY 池"
```

---

### Task 3: 把提交被拒分成五类

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/aistudio.py`（`SubmitRejected` 后面）
- Test: `tests/pdf-to-md/test_pdf_to_md.py`（新增 `TestClassifyRejection`）

**Interfaces:**
- Consumes: `SubmitRejected(status, code, msg, trace_id, what)`
- Produces:
  - 常量 `REJECTION_QUOTA`、`REJECTION_KEY_DEAD`、`REJECTION_RATE_LIMITED`、`REJECTION_UNKNOWN_429`、`REJECTION_OTHER`
  - `aistudio.classify_rejection(exc: SubmitRejected) -> str`

- [ ] **Step 1: 写失败的测试**

```python
class TestClassifyRejection(unittest.TestCase):
    def test_code_12001_is_quota(self):
        self.assertEqual(aistudio.classify_rejection(
            SubmitRejected(403, code=12001)), aistudio.REJECTION_QUOTA)

    def test_code_12002_is_rate_limited(self):
        self.assertEqual(aistudio.classify_rejection(
            SubmitRejected(429, code=12002)), aistudio.REJECTION_RATE_LIMITED)

    def test_403_without_code_is_key_dead(self):
        self.assertEqual(aistudio.classify_rejection(
            SubmitRejected(403)), aistudio.REJECTION_KEY_DEAD)

    def test_401_is_key_dead(self):
        # 2026-11-05 实测：无效 token 返回 HTTP 401 + code 401
        self.assertEqual(aistudio.classify_rejection(
            SubmitRejected(401, code=401)), aistudio.REJECTION_KEY_DEAD)

    def test_429_without_code_is_unknown(self):
        self.assertEqual(aistudio.classify_rejection(
            SubmitRejected(429)), aistudio.REJECTION_UNKNOWN_429)

    def test_400_is_other(self):
        self.assertEqual(aistudio.classify_rejection(
            SubmitRejected(400, code=10004)), aistudio.REJECTION_OTHER)
```

- [ ] **Step 2: 跑测试确认失败**

Expected: `AttributeError: module 'aistudio' has no attribute 'classify_rejection'`

- [ ] **Step 3: 实现**

```python
REJECTION_QUOTA = "quota"
REJECTION_KEY_DEAD = "key_dead"
REJECTION_RATE_LIMITED = "rate_limited"
REJECTION_UNKNOWN_429 = "unknown_429"
REJECTION_OTHER = "other"


def classify_rejection(exc):
    """判断一次提交被拒该不该换 KEY。

    官方两份文档对「额度用完」的状态码说法不一致：异步接口文档写 403 +
    code 12001，通用配额文档写 429。2026-11-05 实测：无效 token 返回
    401 + code 401。所以按 code 优先、状态码兜底，429 且没有 code 时
    归到 unknown_429。
    """
    if exc.code == 12001:
        return REJECTION_QUOTA
    if exc.code == 12002:
        return REJECTION_RATE_LIMITED
    if exc.status in (401, 403):
        return REJECTION_KEY_DEAD
    if exc.status == 429:
        return REJECTION_UNKNOWN_429
    return REJECTION_OTHER
```

- [ ] **Step 4: 跑测试确认通过**

- [ ] **Step 5: 提交**

```bash
git commit -m "feat(pdf-to-md): 区分额度用完与限流"
```

---

### Task 4: 提交时换 KEY

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/convert.py`（模块常量区与 `_convert_one_page` 之前）
- Test: `tests/pdf-to-md/test_pdf_to_md.py`（新增 `TestSubmitWithPool`）

**Interfaces:**
- Consumes: `aistudio.TokenPool`、`aistudio.classify_rejection`、四个 `REJECTION_*` 常量
- Produces:
  - `convert.UNKNOWN_429_WAIT = 5.0`
  - `convert._submit_with_pool(target, model, pool, optional_payload=None) -> tuple[str, str]`，返回 `(job_id, 提交成功的 token)`

- [ ] **Step 1: 写失败的测试**

```python
class TestSubmitWithPool(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(convert, "UNKNOWN_429_WAIT", 0)
        patcher.start()
        self.addCleanup(patcher.stop)

    def submit(self, responses):
        """按顺序把 responses 交给假 submit。"""
        seq = iter(responses)
        calls = []
        def fake(target, model, token, optional_payload=None):
            calls.append(token)
            item = next(seq)
            if isinstance(item, Exception):
                raise item
            return item
        return fake, calls

    def test_quota_rejection_switches_and_returns_the_new_token(self):
        fake, calls = self.submit([SubmitRejected(403, code=12001), "j1"])
        pool = aistudio.TokenPool(["a", "b"])
        with mock.patch.object(aistudio, "submit", fake):
            self.assertEqual(convert._submit_with_pool("x.pdf", "m", pool), ("j1", "b"))
        self.assertEqual(calls, ["a", "b"])

    def test_dead_key_is_switched_too(self):
        # 2026-11-05 实测：无效 token 返回 401 + code 401
        fake, calls = self.submit([SubmitRejected(401, code=401), "j1"])
        pool = aistudio.TokenPool(["a", "b"])
        with mock.patch.object(aistudio, "submit", fake):
            self.assertEqual(convert._submit_with_pool("x.pdf", "m", pool), ("j1", "b"))
        self.assertEqual(calls, ["a", "b"])

    def test_rate_limit_is_raised_without_switching(self):
        fake, calls = self.submit([SubmitRejected(429, code=12002)])
        pool = aistudio.TokenPool(["a", "b"])
        with mock.patch.object(aistudio, "submit", fake):
            with self.assertRaises(SubmitRejected):
                convert._submit_with_pool("x.pdf", "m", pool)
        self.assertEqual(calls, ["a"])

    def test_unknown_429_is_retried_once_on_the_same_token(self):
        fake, calls = self.submit([SubmitRejected(429), "j1"])
        pool = aistudio.TokenPool(["a", "b"])
        with mock.patch.object(aistudio, "submit", fake):
            self.assertEqual(convert._submit_with_pool("x.pdf", "m", pool), ("j1", "a"))
        self.assertEqual(calls, ["a", "a"])

    def test_two_unknown_429s_switch(self):
        fake, calls = self.submit([SubmitRejected(429), SubmitRejected(429), "j1"])
        pool = aistudio.TokenPool(["a", "b"])
        with mock.patch.object(aistudio, "submit", fake):
            self.assertEqual(convert._submit_with_pool("x.pdf", "m", pool), ("j1", "b"))
        self.assertEqual(calls, ["a", "a", "b"])

    def test_other_rejection_is_raised_without_switching(self):
        fake, calls = self.submit([SubmitRejected(400, code=10004)])
        pool = aistudio.TokenPool(["a", "b"])
        with mock.patch.object(aistudio, "submit", fake):
            with self.assertRaises(SubmitRejected):
                convert._submit_with_pool("x.pdf", "m", pool)
        self.assertEqual(calls, ["a"])

    def test_all_keys_gone_raises_all_exhausted(self):
        fake, calls = self.submit([
            SubmitRejected(403, code=12001),
            SubmitRejected(403, code=12001),
        ])
        pool = aistudio.TokenPool(["a", "b"])
        with mock.patch.object(aistudio, "submit", fake):
            with self.assertRaises(aistudio.AllTokensExhausted):
                convert._submit_with_pool("x.pdf", "m", pool)
```

- [ ] **Step 2: 跑测试确认失败**

Expected: `AttributeError: module 'convert' has no attribute '_submit_with_pool'`

- [ ] **Step 3: 实现**

`convert.py` 常量区加 `UNKNOWN_429_WAIT = 5.0`（注释写明：官方文档分不清配额与限流时先等一次）。

在 `_convert_one_page` 之前加：

```python
def _submit_with_pool(target, model, pool, optional_payload=None):
    """按池里的顺序提交，额度类拒绝就换下一个 KEY。

    返回 `(job_id, 提交成功的那个 token)`：调用方要用这个 token 轮询，
    不能再用池子的当前值——池子可能已经往前走了。
    """
    while True:
        token = pool.current()
        try:
            job_id = aistudio.submit(target, model, token, optional_payload)
            return job_id, token
        except aistudio.SubmitRejected as exc:
            kind = aistudio.classify_rejection(exc)
            if kind == aistudio.REJECTION_UNKNOWN_429:
                time.sleep(UNKNOWN_429_WAIT)
                try:
                    job_id = aistudio.submit(target, model, token, optional_payload)
                    return job_id, token
                except aistudio.SubmitRejected as again:
                    if aistudio.classify_rejection(again) != aistudio.REJECTION_UNKNOWN_429:
                        raise
                    exc = again
            elif kind not in (aistudio.REJECTION_QUOTA,
                              aistudio.REJECTION_KEY_DEAD):
                raise
            pool.retire(token, exc)
```

- [ ] **Step 4: 跑测试确认通过**

- [ ] **Step 5: 提交**

```bash
git commit -m "feat(pdf-to-md): 提交遇到额度不足时换下一个 KEY"
```

---

### Task 5: 财报逐页模式接入 KEY 池

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/convert.py:389-426`（`_convert_one_page`）、`454-512`（`_convert_single_pages`）、`583-654`（`convert_one`）
- Test: `tests/pdf-to-md/test_pdf_to_md.py:2497`（`TestFinancialSinglePage`）

**Interfaces:**
- Consumes: `convert._submit_with_pool`、`aistudio.TokenPool`
- Produces: `convert_one(task, out_root, model, token, ...)` 的第四个参数接受 `str` 或 `TokenPool`；字符串按单元素池处理

- [ ] **Step 1: 写失败的测试**

在 `TestFinancialSinglePage` 加一条，验证「第一页第一个 KEY 额度不足，换第二个 KEY 提交，轮询用第二个 KEY」：

```python
def test_quota_rejection_switches_key_and_polls_with_it(self):
    seen = []
    def fake_submit(target, model, token, optional_payload=None):
        if token == "a":
            raise SubmitRejected(403, code=12001)
        seen.append(("submit", token))
        return "j1"
    def fake_poll(job_id, token, on_progress=None):
        seen.append(("poll", token))
        return "http://x/result.jsonl"
    pool = aistudio.TokenPool(["a", "b"])
    with mock.patch.object(aistudio, "submit", fake_submit), \
         mock.patch.object(aistudio, "poll", fake_poll), \
         mock.patch.object(aistudio, "fetch_jsonl", lambda url: "{}"), \
         mock.patch.object(convert.md_utils, "parse_jsonl",
                           lambda raw: [Page(index=0, text="p", images={})]):
        convert._convert_one_page("x.pdf", 1, "m", pool)
    self.assertEqual(seen, [("submit", "b"), ("poll", "b")])
```

（以现有测试的夹具为准调整假返回；关键是断言提交和轮询都用 `"b"`。）

- [ ] **Step 2: 跑测试确认失败**

Expected: `TypeError`，因为 `_convert_one_page` 把池子当成 token 传给了 `submit`

- [ ] **Step 3: 实现**

- `_convert_one_page(path, page_no, model, pool, debug_dir=None)`：
  - `job_id, token = _submit_with_pool(path, model, pool, aistudio.FINANCIAL_OPTIONAL_PAYLOAD)`
  - `jsonl_url = aistudio.poll(job_id, token)`
  - 其余不变
- `_convert_single_pages(task, model, pool, ...)`：把 `token` 改名 `pool`，调用 `_convert_one_page(..., pool, ...)`
- `convert_one` 开头把第四参数转成池：

```python
pool = token if isinstance(token, aistudio.TokenPool) else aistudio.TokenPool(
    [token] if token else [])
```

  财报复用分支传 `pool`。

- [ ] **Step 4: 跑测试确认通过**

Run: 全量测试。Expected: 全绿，包括原有的 `convert_one(task, root, "m", "t")` 单 KEY 用例

- [ ] **Step 5: 提交**

```bash
git commit -m "feat(pdf-to-md): 财报逐页模式按页切换 KEY"
```

---

### Task 6: 整本提交与 run() 接入 KEY 池

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/convert.py:655-665`（general 分支）、`776-850`（`run()`）
- Test: `tests/pdf-to-md/test_pdf_to_md.py:2277`（`TestConvertOne`）、`2903`（`TestRun`）

**Interfaces:**
- Consumes: `aistudio.get_tokens()`、`aistudio.TokenPool`、`convert._submit_with_pool`
- Produces: `run()` 在 `--backend api` 且有文件要转时创建池；`AllTokensExhausted` 让单份失败、其余照跑

- [ ] **Step 1: 写失败的测试**

`TestConvertOne` 加：

```python
def test_general_submit_switches_key_and_polls_with_it(self):
    seen = []
    def fake_submit(target, model, token, optional_payload=None):
        if token == "a":
            raise SubmitRejected(403, code=12001)
        seen.append(("submit", token))
        return "j1"
    def fake_poll(job_id, token, on_progress=None):
        seen.append(("poll", token))
        return "http://x/result.jsonl"
    task = convert.Task(target="/tmp/a.pdf", name="a", origin="a")
    with mock.patch.object(aistudio, "submit", fake_submit), \
         mock.patch.object(aistudio, "poll", fake_poll), \
         mock.patch.object(aistudio, "fetch_jsonl", lambda url: "{}"), \
         mock.patch.object(convert.md_utils, "parse_jsonl",
                           lambda raw: [Page(index=0, text="p", images={})]):
        convert.convert_one(task, self.root, "m", aistudio.TokenPool(["a", "b"]))
    self.assertEqual(seen, [("submit", "b"), ("poll", "b")])
```

`TestRun`：
- `setUp` 里的 `mock.patch.object(aistudio, "get_token", lambda: "t")` 改成 `"get_tokens", lambda: ["t"]`
- 新增：

```python
def test_reads_all_tokens_from_the_environment(self):
    seen = {}
    def fake(task, out, model, pool, **kw):
        seen["pool"] = pool
        return convert.Result("a", 1, 0.1, [])
    tasks = [convert.Task(target="/tmp/a.pdf", name="a", origin="a")]
    with mock.patch.object(aistudio, "get_tokens", lambda: ["a", "b"]), \
         mock.patch.object(convert, "convert_one", fake):
        convert.run(tasks, self.args())
    self.assertEqual(seen["pool"].current(), "a")

def test_all_tokens_exhausted_fails_only_that_file(self):
    tasks = [convert.Task(target="/tmp/a.pdf", name="a", origin="a"),
             convert.Task(target="/tmp/b.pdf", name="b", origin="b")]
    def fake(task, out, model, pool, **kw):
        if task.name == "a":
            raise aistudio.AllTokensExhausted({0: SubmitRejected(403, code=12001)})
        return convert.Result("b", 1, 0.1, [])
    with mock.patch.object(convert, "convert_one", fake):
        self.assertEqual(convert.run(tasks, self.args()), 1)
    self.assertIn("1/2 完成", self.out.getvalue())
```

把 `test_an_all_skipped_run_never_asks_for_a_token` 里的 `get_token` 改成 `get_tokens`。

- [ ] **Step 2: 跑测试确认失败**

Expected: `AttributeError`/断言失败

- [ ] **Step 3: 实现**

- general 分支：

```python
job_id, used_token = _submit_with_pool(task.target, model, pool)
jsonl_url = aistudio.poll(job_id, used_token, on_progress=on_pages)
```

- `run()`：

```python
tokens = aistudio.get_tokens() if todo and backend == "api" else None
pool = aistudio.TokenPool(tokens) if tokens else None
```

  `work()` 把 `pool` 作为第四个位置参数传给 `convert_one`。
- `run()` 的捕获表加 `aistudio.AllTokensExhausted`。

- [ ] **Step 4: 跑测试确认通过**

- [ ] **Step 5: 提交**

```bash
git commit -m "feat(pdf-to-md): 整本提交与批次运行接入 KEY 池"
```

---

### Task 7: 体检支持多个 KEY

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/doctor.py:63-74`
- Test: `tests/pdf-to-md/test_pdf_to_md.py:3392`（`TestDoctorChecks`）

**Interfaces:**
- Consumes: `TOKEN_ENV`
- Produces: `doctor.check_token()` 对多 KEY 通过并提示数量

- [ ] **Step 1: 写失败的测试**

```python
def test_two_tokens_pass_and_report_the_count(self):
    with mock.patch.dict(os.environ, {doctor.TOKEN_ENV: "a,b"}, clear=False):
        check = doctor.check_token()
    self.assertTrue(check.ok)
    self.assertIn("2", check.detail)

def test_empty_items_are_ignored(self):
    with mock.patch.dict(os.environ, {doctor.TOKEN_ENV: "a,, ,b"}, clear=False):
        check = doctor.check_token()
    self.assertTrue(check.ok)
    self.assertIn("2", check.detail)
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现**

`check_token()` 按逗号切分、去空白、丢空项；数量 ≥ 1 通过；`len > 1` 时在 `note` 里写「检测到 N 个 KEY，按顺序使用」；任一原始项有首尾空白时保留原来的提醒。全空时的提示补一句「多个账号用英文逗号隔开」。

- [ ] **Step 4: 跑测试确认通过**

- [ ] **Step 5: 提交**

```bash
git commit -m "feat(pdf-to-md): 体检识别多个 KEY"
```

---

### Task 8: 更新技能文档

**Files:**
- Modify: `plugin/skills/pdf-to-md/SKILL.md`（「本地 API 的 token」一节）

**Interfaces:**
- Consumes: 无
- Produces: 用户可照着配多 KEY

- [ ] **Step 1: 改文档**

在 `PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN` 的配置示例后补：

- 多个账号的 KEY 用英文逗号隔开，按书写顺序使用。
- 前一个额度用完会自动换下一个；日志显示「KEY 1 额度不足，改用 KEY 2」。
- 限流（`code` 12002）不换 KEY，等一会儿重试。
- 每次运行都从第一个 KEY 开始，不记录哪个已用完。
- 只对 `--backend api` 生效。

- [ ] **Step 2: 检查文档里没有真实 KEY**

Run: `grep -nE "[0-9a-f]{32,}" plugin/skills/pdf-to-md/SKILL.md`
Expected: 无输出

- [ ] **Step 3: 提交**

```bash
git commit -m "docs(pdf-to-md): 说明多个 KEY 的配置与切换规则"
```

---

## 手工验收（留给用户）

第一个 KEY 的额度真正用完时，用两个账号的 KEY 跑一份财报。跑之前先确认三件事：

1. `~/.claude/settings.json` 的 `PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN` 已改成两个 KEY 用逗号隔开。
2. **重开一个 Claude Code 会话**：环境变量在会话启动时注入，改完设置当前会话读不到新值。
3. VPN 已开——未开 VPN 时 Python 到接口的 TLS 连接会断，与 KEY 无关。

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python C:/Study/shared-skills/plugin/skills/pdf-to-md/scripts/convert.py <一份财报.pdf> \
  --output <输出根> --backend api --source-type financial
```

确认三件事：

1. 日志出现「KEY 1 额度不足，改用 KEY 2」。
2. 文件完整转完，没有缺页。
3. 把这行日志和第一个 KEY 当时的完整响应体（状态码、`code`、`msg`）记回设计文档的「数据来源与实测」表。
