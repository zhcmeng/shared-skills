# pdf-to-md 移除官网方式入口 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删掉 pdf-to-md 的命令行与体检入口里所有官网方式相关的东西，`aistudio_web.py` 等实现代码原样保留。

**Architecture:** 只改调用面：`convert.py` 去掉六个官网参数与相关校验，`doctor.py` 去掉 `--backend` 并固定查接口链路；文档与技能描述改为接口方式直述。已无入口调用的模块与函数一律保留，成为残留代码。

**Tech Stack:** Python 3、unittest、argparse、Playwright（残留代码仍 import，但入口不再要求安装）。

**Spec:** `docs/superpowers/specs/2026-11-25-pdf-to-md-remove-web-entry-design.md`

## Global Constraints

- 只删入口，不删实现：`scripts/aistudio_web.py`、`convert.run_web`、`convert_one(backend=…, web_session=…)`、`markdown.parse_official_json`、`doctor.check_profile_dir`、`doctor.check_credentials` 全部保留。
- `--backend` 参数整个删掉，不是只删 `official-web` 选项；旧命令带 `--backend api` 会得到 argparse 的「unrecognized arguments」。
- `--jobs` 默认值恢复为 4。
- 版本号只抬最后一位：`1.35.4` → `1.35.5`，`plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 两处一致。
- 正文中文、文件名英文；提交信息不加任何 AI 署名行。
- 测试入口：`bash tests/run.sh pdf-to-md`；仓库检查：`bash checks/verify.sh --changed`。

## Review Focus

- 旧笔记或脚本里还写着 `--backend api`：`convert.py` 与 `doctor.py` 必须明确报参数不认，不能静默忽略。Task 1、2 的参数拒绝测试钉这一点。
- `--help` 与 SKILL.md 残留官网措辞：参数删了、帮助文本还提浏览器，会让读文档的人以为有第二条路。Task 1、3 的 grep 验收钉这一点。
- `--jobs` 从 1 变回 4：批量转换会同时提交 4 份，这是加官网之前的行为；Task 1 的默认值测试钉这一点。
- 体检仍然必须真转一份样例：只查环境变量不算通过。Task 2 保留 `check_smoke` 与其产物断言。
- 残留代码不得拖累接口方式：`convert.py` 仍 `import aistudio_web`，但接口方式不需要 playwright；Task 1 依赖检查只查 `REQUIRED`/`FINANCIAL_REQUIRED`。

---

### Task 1: 移除 convert.py 的官网参数

**Files:**
- Modify: `tests/pdf-to-md/test_pdf_to_md.py:2227-2352`（`TestParseArgs` 的默认值与财报用例、整个 `TestParseArgsBackend`）
- Modify: `plugin/skills/pdf-to-md/scripts/convert.py:78-161`（`parse_args`）
- Modify: `plugin/skills/pdf-to-md/scripts/convert.py:1001-1020`（`main`）

**Interfaces:**
- Consumes: 无（本任务最先做）。
- Produces: `convert.parse_args(argv) -> Namespace`，其字段不再包含 `backend`、`browser_profile`、`browser_channel`、`web_timeout`、`login_timeout`、`no_wait_login`；`jobs` 默认 `4`。`convert.run_web(tasks, args)` 与 `convert_one(..., backend="api", web_session=None)` 签名不变，供残留代码与既有测试使用。

- [ ] **Step 1: 改测试，先让它们红**

`TestParseArgs.test_defaults`（约 2227 行）把 jobs 断言改成 4：

```python
    def test_defaults(self):
        args = convert.parse_args(["a.pdf", "--output", self.output()])
        self.assertEqual(args.model, aistudio.DEFAULT_MODEL)
        self.assertEqual(args.jobs, 4)
        self.assertEqual(args.page_jobs, 4)
        self.assertEqual(args.source_type, "general")
        self.assertFalse(args.force)
        self.assertFalse(args.debug)
```

`TestParseArgs` 里两处 `test_financial_mode_*` 的 `"--backend", "api",` 两行删掉，其余不动。

把整个 `TestParseArgsBackend` 类（2292-2352 行）替换为：

```python
class TestWebEntryIsGone(unittest.TestCase):
    def parse(self, *extra):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return convert.parse_args(
            ["a.pdf", "--output", os.path.join(tmp.name, "out"), *extra])

    def test_web_options_are_not_accepted(self):
        for option, value in (
                ("--backend", "api"),
                ("--browser-profile", "p"),
                ("--browser-channel", "chrome"),
                ("--web-timeout", "60"),
                ("--login-timeout", "30")):
            err = io.StringIO()
            with mock.patch.object(sys, "stderr", err), \
                 self.assertRaises(SystemExit) as ctx:
                self.parse(option, value)
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn(option, err.getvalue())

    def test_no_wait_login_is_not_accepted(self):
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err), \
             self.assertRaises(SystemExit) as ctx:
            self.parse("--no-wait-login")
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("--no-wait-login", err.getvalue())

    def test_jobs_defaults_to_four(self):
        self.assertEqual(self.parse().jobs, 4)

    def test_another_model_is_still_accepted(self):
        self.assertEqual(
            self.parse("--model", "PP-StructureV3").model, "PP-StructureV3")


class TestMainDependencies(unittest.TestCase):
    def test_main_checks_only_the_api_dependencies(self):
        """接口方式不需要 playwright；官网那套依赖不该再被查。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = os.path.join(tmp.name, "out")
        with mock.patch.object(convert, "check_dependencies") as check, \
             mock.patch.object(convert, "collect_inputs", return_value=[]), \
             mock.patch.object(convert, "run", return_value=0):
            self.assertEqual(convert.main(["--output", out, "a.pdf"]), 0)
        self.assertEqual(check.call_args.args, (convert.REQUIRED,))
```

- [ ] **Step 2: 跑测试，确认红**

Run: `bash tests/run.sh pdf-to-md`
Expected: FAIL；`TestParseArgs.test_defaults` 报 `1 != 4`，`TestWebEntryIsGone` 的参数用例报 `SystemExit` 没抛（argparse 仍认这些参数）。

- [ ] **Step 3: 改 `convert.py` 的参数定义**

在 `parse_args` 中：

1. 删掉 `--backend`、`--browser-profile`、`--browser-channel`、`--web-timeout`、`--login-timeout`、`--no-wait-login` 六个 `add_argument`。
2. `--jobs` 改为 `default=4`，help 改成「同时最多几个文件在转，默认 4」；删掉 `if args.jobs is None:` 那三行。
3. `--model` help 里删掉「官网方式只能用 {aistudio.DEFAULT_MODEL}；」。
4. `--source-type` help 里删掉「只对 --backend api 有效」。
5. `--debug` help 里删掉「官网方式还留官网 JSON、任务详情与任务页截图。」。
6. 删掉 `--web-timeout`、`--login-timeout` 的两个正整数校验。
7. 把 `if args.backend == "official-web": ... elif args.source_type == "financial":` 整段换成只有财报分支：

```python
    if args.source_type == "financial":
        if args.model not in (aistudio.DEFAULT_MODEL, aistudio.FINANCIAL_MODEL):
            parser.error(
                f"财报模式固定用 {aistudio.FINANCIAL_MODEL}，"
                f"--model 给的是 {args.model}。要去掉 --model，"
                f"或者改用 --source-type general。")
        args.model = aistudio.FINANCIAL_MODEL
```

- [ ] **Step 4: 改 `convert.py` 的 `main`**

```python
def main(argv=None):
    # 在 parse_args 之前：参数写错时 argparse 那句提示也是中文
    prefer_utf8(sys.stdout)
    prefer_utf8(sys.stderr)
    args = parse_args(argv)
    try:
        check_dependencies(
            FINANCIAL_REQUIRED if args.source_type == "financial"
            else REQUIRED)
        tasks = collect_inputs(args.inputs)
        return run(tasks, args)
    except SystemExit as exc:      # 缺依赖、目录里没有 PDF、缺 token
        if exc.code and not isinstance(exc.code, int):
            print(exc.code, file=sys.stderr)
        return 2
```

`WEB_REQUIRED`、`_WEB_INSTALL_HINT`、`import aistudio_web`、`run_web` 都保留不动。

- [ ] **Step 5: 跑测试，确认绿**

Run: `bash tests/run.sh pdf-to-md`
Expected: PASS（`TestRunWeb`、`TestConvertOneWeb` 仍应通过——`run_web` 与 `convert_one` 没动）。

- [ ] **Step 6: 查帮助文本**

Run: `python plugin/skills/pdf-to-md/scripts/convert.py --help`
Expected: 输出里没有 `--backend`、`--browser`、`--web-timeout`、`--login-timeout`、`--no-wait-login`，也没有「官网」「浏览器」。

- [ ] **Step 7: 提交**

```bash
git add tests/pdf-to-md/test_pdf_to_md.py plugin/skills/pdf-to-md/scripts/convert.py
git commit -m "refactor(pdf-to-md): 移除 convert.py 的官网方式命令行参数"
```

---

### Task 2: 移除 doctor.py 的官网体检入口

**Files:**
- Modify: `tests/pdf-to-md/test_pdf_to_md.py:3918-3925`（api 命令断言）、`3988-4117`（`TestDoctorMain` 的相关用例）
- Modify: `plugin/skills/pdf-to-md/scripts/doctor.py:236-246`（`smoke_command`）、`323-333`（`parse_args`）、`347-363`（`main`）

**Interfaces:**
- Consumes: Task 1 的 `convert.py` 不再接受 `--backend`，所以体检 smoke 命令必须同步去掉它。
- Produces: `doctor.check_smoke(backend=None, runner=None)` 签名不变（默认仍是残留的 `"official-web"`）；`doctor.smoke_command("api", out)` 返回的命令不含 `--backend`。`main` 固定调用 `check_smoke("api")`。

- [ ] **Step 1: 改测试，先让它们红**

`TestDoctorSmokeCheck.test_the_api_command_keeps_the_old_arguments` 改为：

```python
    def test_the_api_command_keeps_the_old_arguments(self):
        cmd = doctor.smoke_command("api", "OUT")
        self.assertEqual(cmd[:1], ["uv"])
        for package in ("requests", "lxml", "tabulate", "pypdf"):
            self.assertIn(package, cmd)
        self.assertNotIn("playwright", cmd)
        self.assertNotIn("--backend", cmd)
        self.assertNotIn("--no-wait-login", cmd)
```

`TestDoctorMain` 里替换以下用例：

```python
    def test_the_token_check_runs_and_the_browser_checks_do_not(self):
        mocks = self._patch()
        self.assertEqual(doctor.main([]), 0)
        self.assertEqual(mocks["token"].call_count, 1)
        self.assertEqual(mocks["profile_dir"].call_count, 0)
        self.assertEqual(mocks["credentials"].call_count, 0)

    def test_a_missing_token_stops_with_exit_2(self):
        mocks = self._patch(token=False)
        self.assertEqual(doctor.main([]), 2)
        self.assertEqual(mocks["token"].call_count, 1)
        self.assertIn("环境里没有它。", self.out.getvalue())

    def test_the_smoke_step_always_gets_the_api_backend(self):
        mocks = self._patch()
        doctor.main([])
        self.assertEqual(mocks["smoke"].call_args.args, ("api",))
```

`test_a_local_failure_stops_before_the_smoke_step` 把 `credential=False` 改成 `token=False`。

`test_every_local_check_runs_so_all_the_problems_show_at_once` 改为：

```python
    def test_every_local_check_runs_so_all_the_problems_show_at_once(self):
        """本机那几项一次全跑完：让人修一个跑一次太折腾。"""
        mocks = self._patch(uv=False, token=False)
        self.assertEqual(doctor.main([]), 2)
        self.assertEqual(mocks["uv"].call_count, 1)
        self.assertEqual(mocks["token"].call_count, 1)
        self.assertEqual(mocks["profile_dir"].call_count, 0)
        self.assertEqual(mocks["credentials"].call_count, 0)
        text = self.out.getvalue()
        self.assertIn("找不到 uv。", text)
        self.assertIn("环境里没有它。", text)
```

`test_an_empty_machine_gets_a_report_not_a_traceback` 删掉结尾那段 `proc = run("--backend", "api")`，并把首段断言改成：

```python
        self.assertIn(doctor.TOKEN_ENV, text)
        self.assertNotIn("浏览器配置目录", text)
```

删掉 `test_the_web_backend_does_not_need_a_token`、`test_the_api_backend_checks_the_token_instead`、`test_the_smoke_step_gets_the_selected_backend` 三个用例（已被上面的新用例取代）。

`TestDoctorSmokeCheck` 里 `test_the_official_web_command_is_the_one_the_skill_documents` 与 `test_the_web_smoke_allows_time_for_the_browser` 保留：它们测的是残留函数 `smoke_command("official-web")` / `check_smoke("official-web")`，代码没删，测试照跑。把前者的 docstring 第一行改成「残留的官网命令：入口已移除，这里只钉住这个函数当前的样子。」。

再加一个参数拒绝用例（放在 `TestDoctorMain` 之前）：

```python
class TestDoctorArgs(unittest.TestCase):
    def test_backend_is_not_accepted(self):
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err), \
             self.assertRaises(SystemExit) as ctx:
            doctor.parse_args(["--backend", "api"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("--backend", err.getvalue())
```

- [ ] **Step 2: 跑测试，确认红**

Run: `bash tests/run.sh pdf-to-md`
Expected: FAIL；`test_the_api_command_keeps_the_old_arguments` 报 `--backend` 仍在命令里；`TestDoctorArgs` 报 `SystemExit` 没抛（此时 `--backend` 还认）；`TestDoctorMain` 的 token 用例报 `token` 调用 0 次、`profile_dir` 被调用。

- [ ] **Step 3: 改 `doctor.py`**

1. `smoke_command` 的 api 分支去掉 `"--backend", "api",` 两个元素；`official-web` 分支原样保留。
2. `parse_args` 删掉 `--backend` 那个 `add_argument`。
3. `main` 改为：

```python
    args = parse_args(argv)

    # 前面几项查的都是本机，免费，一次全跑完——把毛病一次说清，别让人
    # 修一个跑一次。最后那项要花配额、要等十几秒，前面全绿了才跑。
    checks = [check_uv(), check_token()]
    if args.output:
        checks.append(check_output_dir(args.output))
    local_ok = all(check.ok for check in checks)
    if local_ok:
        checks.append(check_smoke("api"))
```

`check_profile_dir`、`check_credentials`、`default_base_dir`、`WEB_SMOKE_TIMEOUT` 全部保留不动。

- [ ] **Step 4: 跑测试，确认绿**

Run: `bash tests/run.sh pdf-to-md`
Expected: PASS。

- [ ] **Step 5: 查帮助文本**

Run: `python plugin/skills/pdf-to-md/scripts/doctor.py --help`
Expected: 输出里没有 `--backend`，也没有「浏览器」「登录」。

- [ ] **Step 6: 提交**

```bash
git add tests/pdf-to-md/test_pdf_to_md.py plugin/skills/pdf-to-md/scripts/doctor.py
git commit -m "refactor(pdf-to-md): 体检只查接口链路，去掉 --backend"
```

---

### Task 3: 重写 SKILL.md 与技能 README

**Files:**
- Modify: `plugin/skills/pdf-to-md/SKILL.md`
- Modify: `plugin/skills/pdf-to-md/README.md`

**Interfaces:**
- Consumes: Task 1、2 定下的命令行形状：只有接口方式，无 `--backend`。
- Produces: 只描述接口方式的技能文档；后续任务不改文档内容。

- [ ] **Step 1: 改 SKILL.md 的 frontmatter**

`description` 整行换成：

```yaml
description: "把 PDF 转成 Markdown 写到磁盘时使用——本地脚本带 AI Studio token 调云端解析接口，正文里的图片一并下载到本地并改写成相对路径。支持单个文件、整个目录批量，以及 PDF 的公网网址；财报加 --source-type financial 逐页提交。另带一条体检命令，查这台机器现在能不能转。触发词：PDF 转 Markdown、pdf to markdown、解析 PDF、PDF 提取正文、扫描件转文字、PDF 转文本、PDF 转换体检。不用于：把 Markdown 导出成 PDF（那是 md-export 的活）、把网页抓成 Markdown。"
```

`argument-hint` 换成：

```yaml
argument-hint: "<PDF 路径 / 目录 / PDF 网址…> --output <输出根目录> [--source-type financial]"
```

- [ ] **Step 2: 改 SKILL.md 正文**

按下面删改，没提到的段落原样保留：

1. 开头第 9～15 行那段「默认走官网」的说明换成：

```markdown
把 PDF 解析成 Markdown 写到磁盘。脚本带着 AI Studio 的 token，把整份 PDF 提交给异步解析接口，按任务号轮询到完成，取回结果在本机转成 Markdown。

这是**云端服务，整份 PDF 会上传到 AI Studio 的服务器**。

正文里引用到的图片会一并下载到本地，引用改写成相对路径。**转换过程不进对话**，正文多长都不占上下文。
```

2. 删掉整节「## 前置：官网方式第一次要登录」和「### 本地凭据文件（可选）」。
3. 把「### 本地 API 的 token」这一节（含 `--backend api` 的说明）提为「## 前置：token」；正文里「只有 `--backend api` 需要」「只对 `--backend api` 生效；官网方式不读这个环境变量」两句删掉，其余（环境变量名、多 KEY、版本要求、限流行为）保留。
4. 「## 怎么调」只留一条命令：

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python <skill目录>/scripts/convert.py <输入…> --output <输出根目录>
```

删掉「### 官网方式（默认）」与「### 本地 API（`--backend api`）」两个小标题，只留上面这条。
5. 参数表删掉 `--backend`、`--browser-profile`、`--browser-channel`、`--web-timeout`、`--login-timeout`、`--no-wait-login` 六行，并删掉「哪种方式」整列。`--model` 说明改为「接口认的模型名，默认 `PaddleOCR-VL-1.6`；普通模式可换 `PP-StructureV3`；财报模式固定用它」。`--jobs` 改为「同时最多几个文件在转，默认 4」。`--debug` 删掉「官网 JSON、任务详情、网页截图」这几样，只留服务原始结果、单页 PDF、合并前后页表、图片对照和失败原因。
6. 删掉整节「## 官网方式怎么跑」。
7. 财报一节（原「## 财报：逐页提交（只属于 `--backend api`）」）标题改成「## 财报：逐页提交」，并删掉最后一段「**官网方式没有这个模式**：……」。
8. 「## 调试：保留完整过程」的目录树删掉 `raw/official.json`、`raw/task-detail.json`、`web/` 三项（含 `task-page.png`、`task-page.html`）；正文里「官网方式还会在失败时截一张任务页」删掉。
9. 「## 出问题先体检」：命令改成 `python <skill目录>/scripts/doctor.py [--output <输出根目录>]`；删掉「默认查的是官网方式：」这句；检查表改为四行：uv、token 环境变量（含多个 KEY 的提示）、`--output` 目录、真转一份自带样例；删掉「加 `--backend api` 时，第二、三项换成……」整段。这一节末尾的配额说明改为「最后一项要花配额（本地 API 是每天 20000 页里扣 1 页）、要等十几秒到几十秒，只有前面全部通过才跑」。样例那一行改为「**真转一份自带的 1 页样例**：用接口方式提交，没配 token 时会先在这一步之前报出来」。
10. 「## 两个模型怎么挑（只对 `--backend api` 有效）」标题改成「## 两个模型怎么挑」，并删掉「官网方式固定按 `PaddleOCR-VL-1.6` 解析，不能换模型。」这一句。
11. 「## 配额与错误」删掉「**官网方式**：配额以官网页面上的提示为准……」「官网方式下载菜单取不到 JSON 时……」两条。
12. 「## 已知局限」删掉五条官网条目：可见浏览器窗口、第一次要登录、不能换模型与财报、官网结果服务端合并、网址那条里「官网方式也一样，只是先在本地把网址下载成文件」。网址那条保留「只支持直接指向 PDF 的公网地址」这半句，去掉官网那半句。

- [ ] **Step 3: 改技能 README**

1. 文件结构里 `aistudio_web.py` 一行改成：

```text
│   ├── aistudio_web.py 浏览器：登录、上传官网、等任务、下载官网 JSON（残留：入口已移除，不再被调用）
```

2. 删掉整节「## 官网流程要真跑一遍」。
3. 其余（测试命令、三条容易出错的注意事项）保留。

- [ ] **Step 4: 查残留措辞**

Run:

```bash
grep -n "官网\|浏览器\|登录\|playwright\|browser-profile\|credentials\|--backend" plugin/skills/pdf-to-md/SKILL.md
```

Expected: 无输出。README 里只有 `aistudio_web.py` 那一行和「照抄 aistudio_web.py」的说明可以出现「官网／浏览器」字样：

```bash
grep -n "官网\|浏览器" plugin/skills/pdf-to-md/README.md
```

Expected: 只命中残留说明与「照抄 `aistudio_web.py`」那一条。

- [ ] **Step 5: 提交**

```bash
git add plugin/skills/pdf-to-md/SKILL.md plugin/skills/pdf-to-md/README.md
git commit -m "docs(pdf-to-md): 技能文档只讲接口方式"
```

---

### Task 4: 抬版本号并跑全套检查

**Files:**
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

**Interfaces:**
- Consumes: Task 1～3 的全部改动。
- Produces: 一致的版本号 `1.35.5`。

- [ ] **Step 1: 改两处版本号**

`plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 里所有 `"version": "1.35.4"` 改成 `"1.35.5"`。

- [ ] **Step 2: 跑技能测试**

Run: `bash tests/run.sh pdf-to-md`
Expected: PASS。

- [ ] **Step 3: 跑仓库检查**

Run: `bash checks/verify.sh --changed`
Expected: 全部通过，退出码 0（版本一致性模块会核对两处版本号）。

- [ ] **Step 4: 提交**

```bash
git add plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore(release): 抬版本号至 1.35.5"
```
