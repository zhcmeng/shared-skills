# pdf-to-md：增加官网网页上传解析

## 背景

`pdf-to-md` 现在把 PDF 提交给 AI Studio 的异步解析接口（本地 API），整本多页提交时会把宽表少读几列。已实测分众传媒 2024 年年度报告：

- 第 81 页权益变动表：本地 API 整本提交只拿回 13 列，官网结果是 16 列。
- 第 162 页外币表：官网结果是 99 行 × 4 列的一张合表；本地 API 不合并，163～165 页也对不上。
- 官网下载的 JSON 与在实验目录里保存的官网结果逐字节相同：3,605,508 字节，SHA256 `32e369c8ae46e02f7524f3c0f1ffb0bdbf1e76b69fedb574c68376044d12cf9f`。

因此新增一条「官网网页上传解析」的路：在浏览器里把 PDF 上传到 `https://aistudio.baidu.com/paddleocr/task/new`，等官网解析完，下载官网生成的 JSON，再转成 Markdown 落盘。用户明确要求默认走这条路，不再默认用本地 API。

## 目标

1. 命令行新增 `--backend official-web` 和 `--backend api`，**默认 `official-web`**；`--source-type general` / `financial` 继续只对 `api` 生效。
2. 官网上传支持本地 PDF 和 PDF 公网网址；网址先下载到临时文件，再交给浏览器上传。
3. 用持久化的浏览器配置目录保存登录态：首次由用户在打开的浏览器窗口里手动登录；也可以把账号密码放在仓库外的本地凭据文件里，由脚本自动填写登录表单。
4. 解析完成后，优先用任务页的下载菜单下载 `JSON(文档解析)`；下载菜单取不到时，退回任务详情接口里的同一份 `parsingResult`。
5. 把官网 JSON 适配成现有的 `Page` 列表，复用现有的表格转换、清理、图片下载、跨页判断之外的落盘流程。
6. `--debug` 保存官网 JSON、任务 URL、任务详情、任务页截图与 HTML；不保存 cookie、账号、密码。
7. 纯逻辑写单元测试；浏览器流程用真实的 1 页样例做手动验收。

## 非目标

- 不自动处理验证码、短信验证、扫码登录；遇到这些情况就停下来等用户手动完成。
- 不把账号、密码写进代码、日志、提交、调试产物或仓库内任何文件。
- 不实现多个网页任务同时上传；官网方式一次处理一份 PDF。
- 不改变本地 API 的既有行为；`--backend api` 仍按原来的方式工作。
- 不在官网结果上再跑一次跨页表格合并。已用 197 页的官网结果验证：现有的 `merge_cross_page_tables` 跑完后 197 页没有任何一页变化。
- 不把官网 JSON 作为常规产物长期留在输出目录；只有 `--debug` 才留。

## 关键决定

### 1. 命令行形态

新增一个参数：

```text
--backend official-web|api     默认 official-web
```

理由：`--source-type` 现在的意思是「素材类型」（普通 / 财报），官网网页是「上传方式」，两者不是一回事。放在 `--backend` 里，`--source-type financial` 仍能按原来的方式选择本地 API 的逐页模式。

组合规则：

| 组合 | 行为 |
|:---|:---|
| `--backend official-web`（默认） | 走官网上传；`--source-type` 只能是 `general` |
| `--backend official-web --source-type financial` | 报错，提示官网方式由服务端整本解析并合并，财报逐页模式只属于本地 API |
| `--backend api` | 走原来的本地 API；`--source-type general` / `financial` 照旧 |
| `--backend official-web --model PP-StructureV3` | 报错，官网方式目前只按 `PaddleOCR-VL-1.6` 解析 |

`--jobs` 在官网方式下不生效：浏览器只有一个窗口，一次处理一份。给了大于 1 的值时打一行提示，不报错。`--page-jobs` 在官网方式下也不生效。

### 2. 浏览器与登录

- 用 Playwright 的 `launch_persistent_context` 启动一个可见的浏览器窗口，不是无头模式。
- Windows 默认用系统 Edge（`channel="msedge"`）；其他系统默认用 `chrome`。可用 `--browser-channel` 改。
- 配置目录默认：

  ```text
  Windows: %LOCALAPPDATA%\pdf-to-md\browser-profile
  其他:    ~/.config/pdf-to-md/browser-profile
  ```

  可用 `--browser-profile` 改。目录里是登录 cookie，不能提交、不能外传。
- 登录判断：上传页右上角有 `button.a-s-header-login-btn` 且可见，就是没登录。
- 没登录时：
  1. 先看本地凭据文件。文件默认在 `%LOCALAPPDATA%\pdf-to-md\credentials.json`（其他系统 `~/.config/pdf-to-md/credentials.json`），格式：

     ```json
     {
       "username": "手机号/用户名/邮箱",
       "password": "密码"
     }
     ```

  2. 有凭据就点右上角「登录」，填 `input[id$="__userName"]`、`input[id$="__password"]`，点 `input[id$="__submit"]`。
  3. 没凭据、或者自动登录后还需要验证码/短信，就在终端打印「请在浏览器窗口里完成登录」，然后每 2 秒检查一次，默认最多等 600 秒（`--login-timeout`）。
  4. 等到登录成功再上传；超时就报错退出，并给出配置目录和凭据文件路径。
- 凭据文件只在本地读，不进仓库；脚本不打印文件内容，也不把它写进调试目录。

### 3. 上传与等待

- 上传页有隐藏的 `input[type=file][multiple]`；用 `set_input_files()` 交给它。
- 上传后页面会跳到 `https://aistudio.baidu.com/paddleocr/task/file/<taskId>`；等 URL 变成这个形状就算上传完成。
- 等解析完成时轮询任务详情接口：

  ```text
  GET https://aistudio.baidu.com/paddlex/v3/ocr/tasks/<taskId>/detail?taskId=<taskId>
  ```

  用 Playwright 的 `context.request` 发，自动带上浏览器里的登录 cookie。

- 实测状态：

  | `taskStatus` | 含义 | 处理 |
  |:---|:---|:---|
  | `5` | 完成 | 进入下载 |
  | `4` | 解析中 | 继续等，报 `extractedPages` / `totalPages` |
  | `-5` | 解析失败 | 报错，带上任务页提示和任务 URL |
  | 其他非负值 | 排队或未知的进行中状态 | 继续等，直到 `--web-timeout` |

- `--web-timeout` 默认 3600 秒。197 页的官网任务实测约 3 分钟；1 页样例约 5 秒。
- 失败时页面会显示「发生解析错误，请重试」；错误信息里带上这句和任务 URL。

### 4. 下载官网 JSON

- 任务页结果区顶栏 `.parse-render-content-title-handle` 有 4 个图标按钮，第 4 个是下载下拉。
- 点开菜单，选包含 `JSON` 的那一项，用 `page.expect_download()` 接住下载。
- 下载失败时，退回轮询时拿到的 `result["parsingResult"]`。它是一段 JSON 字符串，内容是 `{"layoutParsingResults": [...], "preprocessedImages": ..., "dataInfo": ...}`；实测 197 项的 `markdown.text` 与下载文件逐项相同。
- 下载文件是顶层列表；详情接口是带 `layoutParsingResults` 的对象。适配器两种都接受。
- 下载的顶层列表项里，`prunedResult` **没有** `width` / `height`；详情接口的有。官网结果已经由服务端合并，不再需要页面尺寸做跨页判断，所以两种都能用。

### 5. 官网 JSON 适配

新增 `markdown.parse_official_json(raw: str) -> list[Page]`：

- 输入是文本。顶层是列表时，列表每一项就是一页；顶层是对象时，取 `layoutParsingResults`。
- 每一项复用现有的 `_page_geometry()`：读 `prunedResult.parsing_res_list`、`prunedResult.width` / `height`。
- `markdown.text` 原样作为页正文；`markdown.images` 原样作为图片表。
- 缺 `markdown` 按空正文处理；缺 `prunedResult` 按没有版面信息处理。
- 顶层不是对象/列表、某项不是对象、JSON 解析失败，抛新的 `OfficialJsonError`。`convert.py` 的捕获表接住它，只让这一份失败。
- 不跑 `merge_cross_page_tables`。实测官网结果已经合并。

### 6. 落盘与调试

常规产物与现在一样：

```text
<输出根>/<PDF 文件名>/<PDF 文件名>.md
<输出根>/<PDF 文件名>/images/<图片>
```

`--debug` 时多出：

```text
<输出根>/<PDF 文件名>/debug/<时间戳>/
├── task.json              输入、backend、模型、任务 URL、配置目录（不含凭据）
├── result.json            页数、耗时、缺图
├── error.txt              失败时的异常与栈
├── raw/official.json      官网 JSON（下载到的原文）
├── raw/task-detail.json   最后一次任务详情
├── web/task-page.png      任务页结果区的截图（不含页面顶部账号区）
└── web/task-page.html     任务页结果区的 HTML（不含页面顶部账号区）
```

不保存 cookie、`storage_state`、账号、密码，也不复制浏览器配置目录。

### 7. 依赖与体检

- 官网方式需要 `requests`、`lxml`、`tabulate`、`playwright`。
- 本地 API 仍只需要 `requests`、`lxml`、`tabulate`；财报模式另需 `pypdf`。
- 官网方式的运行命令：

  ```bash
  uv run --with requests --with lxml --with tabulate --with playwright \
    python <skill目录>/scripts/convert.py …
  ```

- `doctor.py` 增加 `--backend`，默认跟 `convert.py` 一样是 `official-web`：
  - 官网方式检查 uv、浏览器配置目录能不能写、本地凭据文件格式（有就查，没有只提示首次要手动登录），再真转一份 1 页样例。
  - 体检用的真转命令带 `--no-wait-login`：没登录就立刻报「浏览器没登录」，不会在体检里干等 600 秒。
  - `--backend api` 时仍检查 token，并按原来的方式真转样例。

## 数据来源与实测

| 事实 | 来源 |
|:---|:---|
| 上传页文件输入是隐藏的 `input[type=file][multiple]` | 实验与本次实测 |
| 上传后跳到 `/paddleocr/task/file/<taskId>` | 本次实测 |
| `taskStatus`：4 解析中、5 完成、-5 失败 | 本次实测（1 页样例；假 PDF 触发 -5） |
| 1 页样例约 5 秒 | 本次实测 |
| 197 页任务约 3 分钟 | 实验产物（16:40 上传，16:43 下载） |
| 下载菜单第 4 个按钮、`JSON(文档解析)` 项 | 实验与本次实测 |
| 官网下载 JSON 为顶层 197 项列表 | 实验产物 |
| 详情接口 `parsingResult.layoutParsingResults` 与下载 JSON 的 197 页正文逐项相同 | 本次实测 |
| 第 81 页 33 行 × 16 列；第 162 页含 99 行 × 4 列合表；163～165 页无表 | 实验产物 |
| 现有跨页合并跑官网 197 页结果没有任何一页变化 | 本次实测 |

## 测试计划

### 单元测试（不联网、不启动浏览器）

1. `parse_official_json`：
   - 顶层列表 → 页表，顺序与项序一致。
   - 顶层 `layoutParsingResults` 对象 → 同样结果。
   - `markdown.images` 被收集。
   - `prunedResult` 的 `width` / `height` 和 `parsing_res_list` 进入 `Page`。
   - 缺 `markdown`、缺 `prunedResult` 不失败。
   - 非法 JSON、顶层不是列表/对象、列表项不是对象 → `OfficialJsonError`。
   - 空列表 → 空页表（后续由 `EmptyDocument` 报“清理完什么都不剩”）。
2. 命令行：
   - 默认 `backend == "official-web"`。
   - `--backend api` 可用。
   - `--backend official-web --source-type financial` 报错。
   - `--backend official-web --model PP-StructureV3` 报错。
   - `--browser-profile`、`--browser-channel`、`--web-timeout`、`--login-timeout` 能解析。
3. 状态解释：
   - `5` 完成、`4` 继续、`-5` 失败、未知非负值继续；超时报错。
4. 凭据文件：
   - 文件不存在 → 返回 `None`。
   - 空字段 → 返回 `None`。
   - 合法 JSON → 返回用户名和密码。
   - 非法 JSON → 报错信息里有路径，没有文件内容。
5. `run_web` 的失败隔离：一份失败不影响下一份。

### 手动验收（真实网络）

1. 用 1 页样例 `assets/doctor-sample.pdf` 跑一遍官网方式，确认：
   - 首次弹出浏览器；未登录时停下等待手动登录。
   - 上传后任务页出现，进度能显示。
   - 输出目录里有 md 和 images/。
   - `--debug` 目录里有 official.json、task-detail.json、task-page.png/html。
2. 用整本 197 页 PDF 跑一遍，确认：
   - 第 81 页表格 16 列。
   - 第 162 页有 99 行 × 4 列合表。
   - 输出 md 与实验目录里的官网 JSON 转换结果一致。

## 验收标准

1. 不加 `--backend` 时走官网网页上传，输出 Markdown 落到 `<输出根>/<文件名>/<文件名>.md`。
2. `--backend api` 的原有行为、现有测试全部不变。
3. 官网上传支持本地 PDF 和公网 PDF 网址。
4. 首次运行能在浏览器里手动登录；登录态在后续运行中复用；凭据文件可选，且不在仓库内、不被打印、不被提交。
5. 解析失败、超时、下载失败都有中文错误信息，并指出任务 URL 或配置目录。
6. `--debug` 产物不含 cookie、账号、密码。
7. 新增单元测试全部通过；`bash tests/run.sh pdf-to-md` 与 `bash checks/verify.sh --changed` 通过。
8. 插件版本抬到 `1.28.0`，`plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 一致。

## 留给实现的人

- 浏览器流程没法用纯单元测试覆盖，必须用真实 1 页样例手动跑一次；不要用整本 197 页做第一次调试。
- Playwright 的同步 API 不是线程安全的。官网方式按顺序处理任务，所有浏览器调用都在主线程里；不要把它塞进现有的 `ThreadPoolExecutor`。
- 官网页面改版时最容易坏的是三个选择器：登录按钮 `button.a-s-header-login-btn`、下载区 `.parse-render-content-title-handle`、菜单项 `JSON(文档解析)`。把它们集中放在 `aistudio_web.py` 顶部，别散落在流程里。
- 官网 JSON 的图片地址带签名会过期。解析完要立刻下载图片，和现有 `_finish_document` 的时序一样。
- 不要为了“更完整”去保存浏览器的 `storage_state`；那里面就是登录 cookie。
