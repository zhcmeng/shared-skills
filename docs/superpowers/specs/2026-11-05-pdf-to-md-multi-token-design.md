# pdf-to-md：支持多个 AI Studio KEY，按顺序消耗

## 背景

`pdf-to-md` 的本地 API 方式（`--backend api`）只认一个 token，从环境变量
`PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN` 读。AI Studio 的解析额度按账号算，每天
20000 页；额度用完后整批转换失败，要等到第二天才能继续。

用户有两个不同账号的 KEY，要求：第一个的额度用完后自动换第二个，不中断转换。

## 目标

1. `PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN` 支持逗号分隔的多个 KEY，按书写顺序使用。
2. 提交时遇到「这个 KEY 不能再用了」的响应，自动换下一个 KEY 重试同一份文件/同一页，
   不消耗该文件/该页原本的重试次数。
3. 日志打印切换到第几个 KEY，**任何情况下不打印 KEY 本身**。
4. 全部 KEY 都用完时，报错列出每个 KEY 各自的返回，已完成的不删。
5. 只有一个 KEY 时，行为与现在完全一致。

## 非目标

- 不做负载均衡或轮流使用：严格按顺序，前一个用完才用下一个。
- 不把「哪个 KEY 已用完」写进磁盘。额度按天重置，每次运行都从第一个 KEY 开始试。
- 不改官网方式（`--backend official-web`）。那条路用浏览器登录态，与 API KEY 无关。
- 不查询剩余额度，只根据提交的返回判断。
- 不把 KEY 写进代码、测试、文档、提交信息、日志或调试产物。

## 关键决定

### 1. 存储：环境变量多值

```text
PADDLEOCR_MCP_AISTUDIO_ACCESS_TOKEN=key1,key2,key3
```

- 逗号分隔，按书写顺序消耗。
- 每项去掉首尾空白；空项忽略。
- 单值完全照旧，不要求用户改写现有配置。
- 不新增凭据文件。KEY 只在这一个地方配，避免出现「文件和环境变量哪个生效」的歧义。

### 2. 取 KEY 的两个函数

`aistudio.py`：

- `get_tokens()`：解析环境变量，返回按顺序的 KEY 列表；一个都没有时报错，文案说明
  支持逗号分隔，并给出配置示例（不含真实值）。
- `get_token()`：保留，返回 `get_tokens()[0]`。给旧调用方和现有测试留兼容路径。

### 3. 什么时候换 KEY

官方文档对「额度用完」的返回有两套说法，互相冲突：

| 文档 | 额度用完 | 限流 |
|:---|:---|:---|
| 异步 API 使用说明（2026-02-04） | HTTP 403，`code` 12001 | HTTP 429，`code` 12002 |
| API 配额规则及错误码说明（2026-09-08，更新） | HTTP 429 | 未单列 |

两份文档都没给逐字的响应体样例，本机也从未触发过。因此判据按「响应体 `code` 优先，
HTTP 状态兜底」：

| 返回 | 判断 | 处理 |
|:---|:---|:---|
| `code` = 12001 | 已达每日页数上限 | 换下一个 KEY |
| `code` = 12002 | 请求频率过高（限流） | 不换 KEY，交给页级重试等待 |
| HTTP 401 | token 无效（实测：`code` 401、`msg` "Unauthorized"） | 换下一个 KEY |
| HTTP 403，且无上述 code | token 有效但无权限，或旧文档口径的配额用完 | 换下一个 KEY |
| HTTP 429，且无 `code` | 分不清是配额还是限流 | 先等 5 秒重试一次；仍 429 才换 KEY |
| 其他（400 文件格式、413 文件过大等） | 与 KEY 无关 | 不换，按原来的方式报错 |

为什么 429 无 code 时先等而不是直接换：误判「限流」为「配额」会白白消耗下一个账号的
额度，误判「配额」为「限流」只是多等 5 秒。并发页数调高时（`--page-jobs`）限流更容易
出现，这个方向的误判代价更大。

等待 5 秒做成模块常量，测试里替换掉，不让用例真的等。

**待实测**：实现时把完整响应体带进错误信息；第一次真实触发后按实际返回校正判据，并把
当时的状态码、`code`、`msg` 记进本文档。若额度用完走的是 HTTP 200 + 非 0 `code`，
判据同样按 `code` 识别。

### 4. 换 KEY 放在哪一层

放在 `aistudio.submit` 外面、调用方里，做成 `convert.py` 的一个小函数：

```text
_submit_with_pool(target, model, pool, optional_payload=None) -> (job_id, token)
```

流程：

1. 取当前 KEY，提交。
2. 成功：返回「任务号 + 这次用的 KEY」。
3. `code` 12001、HTTP 401 或 403：把这个 KEY 标记为用完，继续下一轮。
4. 429 无 `code`：等 5 秒重试同一 KEY；仍是 429 才标记用完、继续下一轮。
5. `code` 12002：不换 KEY，原样抛出，交给页级重试等待。
6. 池子空了：抛「所有 KEY 都用完」。

不放 `submit` 内部，理由：`aistudio.py` 的职责是「跟接口打交道」，它不需要知道
KEY 有几个；而且调用方需要拿到「最终提交成功的是哪个 KEY」，用来轮询。

### 5. 轮询必须用提交时的 KEY

`_submit_with_pool` 返回 `(job_id, token)`，后续 `poll` 用这个 token，不跟随切换。
理由：任务建在服务端、归属于提交它的 KEY；换一个 KEY 去查可能查不到。

### 6. 线程安全

转换是并发的：`run()` 按文件并发（`--jobs`），财报模式里还按页并发（`--page-jobs`）。

新增 `aistudio.TokenPool`：

- `current()`：返回当前该用的 KEY；全部用完时抛 `AllTokensExhausted`。
- `retire(token, reason)`：把 KEY 标记为用完，返回「这次是否真的往前挪了」。
  只有它仍是当前 KEY 时才前移，多个线程同时撞 429 时只切换一次；也只有真的前移
  才打印切换提示，避免并发下重复打印。
- `label(token)`：返回「KEY 1」「KEY 2」这样的名字给日志用，不暴露 KEY 值。

`AllTokensExhausted` 直接继承 `Exception`，**不继承 `JobFailed`**。理由：继承
`JobFailed` 的话，`_convert_one_page` 的页级重试会把它当成普通页失败再试三遍，
而所有 KEY 都用完时重试没有意义。直接继承 `Exception` 后：

- `_convert_one_page` 的捕获表不含它，原样冒出；
- `_convert_single_pages` 的 `work()` 只接 `PageFailed`，其他异常从
  `future.result()` 冒出；
- `convert_one` 的 `except Exception` 记完调试再抛；
- `run()` 的捕获表加一项 `aistudio.AllTokensExhausted`，让这一份失败、其余照跑。

消息里按 KEY 序号列出各自最后一次的返回。

### 7. 跨次运行不记状态

每次运行从第一个 KEY 开始。额度按天重置，前一天用尽的 KEY 第二天会恢复；不落盘就不会
出现「一直跳过第一个 KEY」的问题。当天第二次运行会先用已耗尽的 KEY 撞一次 429，
耗时在毫秒级，可以接受。

### 8. 日志

切换时打印一行，例如：

```text
KEY 1 额度不足，改用 KEY 2
```

只出现序号。所有异常消息、调试产物、进度行都不含 KEY。

### 9. doctor 体检

`doctor.py` 的 `check_token()` 改为解析多值：

- 至少一个非空 KEY 才算通过。
- 通过时提示「检测到 N 个 KEY，按顺序使用」。
- 有一个 KEY 带首尾空白时照旧提醒，并说明会被自动去掉。

### 10. 不带 KEY 值出现在任何地方

沿用现有约束：KEY 只从环境变量读，不写进代码、测试、文档、提交信息、调试目录。
错误信息里只允许出现序号。

## 改动文件

代码与文档都在 shared-skills 源码仓库 `C:/Study/shared-skills/`。下表路径相对这个目录。

| 文件 | 改动 |
|:---|:---|
| `plugin/skills/pdf-to-md/scripts/aistudio.py` | 新增 `get_tokens()`、`TokenPool`、`AllTokensExhausted`、`is_token_exhausted()`；`get_token()` 改为返回第一个 |
| `plugin/skills/pdf-to-md/scripts/convert.py` | 新增 `_submit_with_pool()`；`run()` 取 KEY 列表并建池；`convert_one()` 与 `_convert_single_pages()`、`_convert_one_page()` 改为接收池；两处提交点改走 `_submit_with_pool()`，轮询用返回的 token |
| `plugin/skills/pdf-to-md/scripts/doctor.py` | `check_token()` 解析多值并提示数量 |
| `plugin/skills/pdf-to-md/SKILL.md` | 说明多 KEY 格式、切换规则、日志只显示序号 |
| `tests/pdf-to-md/test_pdf_to_md.py` | 新增多 KEY 用例；把 mock `get_token` 的 run 测试改为 mock `get_tokens` |

## 数据来源与实测

| 事项 | 来源 | 状态 |
|:---|:---|:---|
| 额度按账号算，同账号的多个 token 共享 | 用户确认（2026-11-05） | 已确认 |
| 不同账号的额度互相独立 | 用户确认（2026-11-05） | 已确认 |
| 每天 20000 页 | 官方《[API 配额规则及错误码说明](https://ai.baidu.com/ai-doc/AISTUDIO/Xmjclapam)》（2026-09-08） | 文档口径；英文版仍写 3000 页，属旧口径 |
| 额度用完返回 403 + `code` 12001 | 官方《[异步 API 使用说明](https://ai.baidu.com/ai-doc/AISTUDIO/fml7mozw5)》（2026-02-04） | 文档口径，本机未复现 |
| 额度用完返回 429 | 官方《API 配额规则及错误码说明》（2026-09-08，更新） | 与上一行冲突，**待实测** |
| 限流返回 429 + `code` 12002 | 官方《异步 API 使用说明》 | 文档口径，本机未复现 |
| `msg` 的逐字原文 | 两份文档都没给响应体样例 | **待实测** |
| 配额重置的具体时刻与时区 | 文档只写「每日」，未写时刻与哪个时区 | **未查到** |
| 是否有查询剩余额度的接口 | 三个接口里没有额度或已用页数的查询 | 已查，无 |

### 开工前实测（2026-11-05）

用 GET 查一个不存在的任务号，不上传文件、不消耗解析页数：

| 探测项 | 结果 |
|:---|:---|
| KEY 1（本机已配） | HTTP 404，`code` 11001，`msg` "jobId 不存在"——有效 |
| KEY 2（备用） | 同上——有效 |
| 无效 token（查询） | HTTP 401，`code` 401，`msg` "Unauthorized" |
| 无效 token（提交） | HTTP 401，`code` 401，`msg` "Unauthorized"——提交和查询一样 |
| 响应体结构 | `{traceId, code, msg}`；成功响应另带 `data` |
| 当前本机配置 | `settings.json` 里只有 1 个 KEY（长度 40，无逗号），实施时要加上第二个 |
| 历史 429 / 12001 记录 | 本机产物里没有找到，额度耗尽的真实返回仍待实测 |

结论：

1. token 无效返回的是 401，不是文档写的 403。判据已按实测加上 401。
2. 响应体一定带 `code`，按 `code` 分类可行。
3. 两个 KEY 都能通过鉴权，且属于不同账号。

### 网络前提（实测）

未开 VPN 时，Python 的 `requests` 与 `urllib` 到 `paddleocr.aistudio-app.com` 都会在
TLS 阶段断连（`UNEXPECTED_EOF_WHILE_READING`），`curl` 正常；开 VPN 后 Python 恢复。
这是本机网络环境的问题，不是代码问题，但会让转换直接失败。跑转换或手工验收前先确认
VPN 已开。

额度耗尽后的真实返回两套文档互相冲突，实现按「`code` 优先、状态码兜底」；第一次真实
触发后按实际返回校正，不把推断写成定论。

## 测试计划

新增用例：

1. `get_tokens()`：单值、两个值、带空格、含空项、全空时报错且文案含变量名。
2. `get_token()` 返回第一个，保持旧行为。
3. `TokenPool`：按顺序返回；`retire` 后前移；两个线程同时 `retire` 同一个 KEY 只前移一次；全部用完抛 `AllTokensExhausted`；`label()` 不含 KEY 值。
4. `_submit_with_pool()`：
   - `code` 12001：换第二个并成功；
   - HTTP 401、无 code：换；
   - HTTP 403、无 code：换；
   - HTTP 429、无 code：先重试同一 KEY，第二次仍 429 才换；
   - `code` 12002：不换，直接抛；
   - HTTP 400：不换，直接抛；
   - 返回的 token 是提交成功的那个；
   - 测试里把 5 秒等待替换成 0，不让用例真的等。
5. 财报页级：第 1 页提交被拒后换 KEY，`poll` 用第二个 KEY。
6. 整本提交（general）：提交被拒后换 KEY，`poll` 用第二个 KEY。
7. 全部 KEY 用完：异常消息列出两个 KEY 的返回，且不含 KEY 值。
8. `run()`：从环境变量读到两个 KEY；全部文件已转换时不读 KEY。
9. `doctor.check_token()`：两个 KEY 通过并提示数量。

手工验收（真实 KEY、真实额度）：用两个不同账号的 KEY，把第一个的额度耗尽后跑一份
财报，确认自动切换、跑完、日志只有序号。

## 验收标准

1. 环境变量配两个 KEY，第一个额度耗尽时，转换自动切到第二个并跑完。
2. 日志出现「KEY 1 额度不足，改用 KEY 2」，任何输出、调试文件里都没有 KEY 值。
3. 只配一个 KEY 时，所有现有测试与行为不变。
4. 全部 KEY 用完时，退出码 1，错误信息列出每个 KEY 的返回。
5. 轮询始终用提交时的 KEY。
6. 限流（`code` 12002）不换 KEY。
7. 现有测试全部通过。

## 留给实现的人

- 判据的具体 code 值以第一次真实 429 的返回为准；实现时先记日志，再定规则。
- 打印切换提示用 `print`，在并发下保持单行完整。
- 不新建额外的状态文件。
