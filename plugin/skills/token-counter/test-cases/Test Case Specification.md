# 测试用例规格说明

测试项：`skills/token-counter/scripts/count_tokens.py`（DeepSeek token 精确计数脚本）。

测试完成准则：各门技术识别出的测试覆盖项，100% 都要有测试用例覆盖。本文件末尾的「覆盖项 ↔ 用例」对应表里没有空行，即达到该准则。

**全篇共用的前置条件**（下面各条用例不再逐条重复）：

- 测试项脚本位于 `skills/token-counter/scripts/count_tokens.py`；`skills/token-counter/tokenizer.json` 在该脚本的上一级目录里，可读；引擎 `tokenizers` 0.22.2 已装（TC-22 至 TC-24 三条另有前置条件，见各自条目）。
- 命令行参数以参数列表的形式直接传给新起的进程，不经控制台代码页做编码转换——本机控制台默认代码页是 GBK，把 emoji、`｜`、`▁` 这类字符当命令行文本手敲进去会被改坏。
- 比对标准输出时按行比对，忽略行尾差异：Windows 上 Python 的文本模式会把 `\n` 输出成 `\r\n`。
- 每条用例执行前，`skills/token-counter/tokenizer.json` 的 sha256 应为 `89085f12ef79460ac5f66d1119325ddfc694b4ab209d80bbd81d35f081dc9614`（6 367 096 字节）。对不上就换回官方离线包里的那份，不必执行用例。

## 一、测试覆盖项

### 源自 TM-1（等价类划分）

| 唯一标识符 | 描述 | 优先级 | 可追溯性 |
|:---|:---|:---|:---|
| TCOV-1 | 有效等价类：命令行只给出 `--text`，其值为一个字符串 | 中 | TM-1 的 EP-S1 |
| TCOV-2 | 有效等价类：命令行给出一个位置参数，该路径存在且可读 | 中 | TM-1 的 EP-S2 |
| TCOV-3 | 有效等价类：命令行既不给 `--text` 也不给位置参数，标准输入中有数据 | 中 | TM-1 的 EP-S3 |
| TCOV-4 | 无效等价类：命令行同时给出 `--text` 与位置参数（用法说明未规定该组合） | 中 | TM-1 的 EP-S4 |
| TCOV-5 | 无效等价类：位置参数给出的路径不可读（不存在，或指向目录） | 中 | TM-1 的 EP-S5 |
| TCOV-6 | 无效等价类：参数形式不合命令行约定（多个位置参数，或未知选项） | 低 | TM-1 的 EP-S6 |
| TCOV-7 | 有效等价类：纯 ASCII 文本 | 中 | TM-1 的 EP-C1 |
| TCOV-8 | 有效等价类：纯中文文本 | 高 | TM-1 的 EP-C2 |
| TCOV-9 | 有效等价类：中英混排、含空格与换行、含首尾空白的文本 | 高 | TM-1 的 EP-C3 |
| TCOV-10 | 有效等价类：含基本平面外字符（emoji）的文本 | 中 | TM-1 的 EP-C4 |
| TCOV-11 | 有效等价类：含 DeepSeek 特殊 token 字面量的文本 | 高 | TM-1 的 EP-C5 |
| TCOV-12 | 有效等价类：空文本 | 高 | TM-1 的 EP-C6 |
| TCOV-13 | 有效等价类：字节来源的数据是合法 UTF-8，按 `utf-8-sig` 解码成功 | 中 | TM-1 的 EP-E1 |
| TCOV-14 | 无效等价类：字节来源的数据不是合法 UTF-8，解码抛异常 | 中 | TM-1 的 EP-E2 |
| TCOV-15 | 有效等价类：按 `tokenizer.json` 的规范语义计数，不经任何兼容转换层 | 高 | TM-1 的 EP-I1 |
| TCOV-16 | 有效等价类：文本中的 DeepSeek 特殊 token 字面量按官方词表算作一个特殊 token | 高 | TM-1 的 EP-I2 |
| TCOV-17 | 有效等价类：字符数算的是解码后文本的码点个数，不是 UTF-8 字节数 | 高 | TM-1 的 EP-H1 |
| TCOV-18 | 有效等价类：字节来源的 BOM 被解码环节剥除，不计入字符数 | 高 | TM-1 的 EP-H2 |
| TCOV-19 | 有效等价类：`--text` 的值不过解码环节，其中的 U+FEFF 计入字符数 | 高 | TM-1 的 EP-H3 |
| TCOV-20 | 有效等价类：标准输出打印 `tokens: N` 与 `chars: M` 两行 | 中 | TM-1 的 EP-O1 |
| TCOV-21 | 无效等价类：打印 `not valid UTF-8: <来源标识>` 并以状态码 1 退出，不打印结果 | 中 | TM-1 的 EP-O2 |
| TCOV-22 | 无效等价类：以未捕获的异常终止，不打印结果 | 中 | TM-1 的 EP-O3 |

### 源自 TM-2（组合测试，成对档）

| 唯一标识符 | 描述 | 优先级 | 可追溯性 |
|:---|:---|:---|:---|
| TCOV-23 | P-V 对成对组合：`--text` × 纯 ASCII | 中 | TM-2 的 PV-1、PV-4 |
| TCOV-24 | P-V 对成对组合：文件 × 纯 ASCII | 中 | TM-2 的 PV-2、PV-4 |
| TCOV-25 | P-V 对成对组合：标准输入 × 纯 ASCII | 中 | TM-2 的 PV-3、PV-4 |
| TCOV-26 | P-V 对成对组合：`--text` × 纯中文 | 高 | TM-2 的 PV-1、PV-5 |
| TCOV-27 | P-V 对成对组合：文件 × 纯中文 | 高 | TM-2 的 PV-2、PV-5 |
| TCOV-28 | P-V 对成对组合：标准输入 × 纯中文 | 高 | TM-2 的 PV-3、PV-5 |
| TCOV-29 | P-V 对成对组合：`--text` × 中英混排含空格与换行 | 高 | TM-2 的 PV-1、PV-6 |
| TCOV-30 | P-V 对成对组合：文件 × 中英混排含空格与换行 | 高 | TM-2 的 PV-2、PV-6 |
| TCOV-31 | P-V 对成对组合：标准输入 × 中英混排含空格与换行 | 高 | TM-2 的 PV-3、PV-6 |
| TCOV-32 | P-V 对成对组合：`--text` × 含基本平面外字符 | 中 | TM-2 的 PV-1、PV-7 |
| TCOV-33 | P-V 对成对组合：文件 × 含基本平面外字符 | 中 | TM-2 的 PV-2、PV-7 |
| TCOV-34 | P-V 对成对组合：标准输入 × 含基本平面外字符 | 中 | TM-2 的 PV-3、PV-7 |
| TCOV-35 | P-V 对成对组合：`--text` × 含特殊 token 字面量 | 高 | TM-2 的 PV-1、PV-8 |
| TCOV-36 | P-V 对成对组合：文件 × 含特殊 token 字面量 | 高 | TM-2 的 PV-2、PV-8 |
| TCOV-37 | P-V 对成对组合：标准输入 × 含特殊 token 字面量 | 高 | TM-2 的 PV-3、PV-8 |
| TCOV-38 | P-V 对成对组合：`--text` × 空文本 | 高 | TM-2 的 PV-1、PV-9 |
| TCOV-39 | P-V 对成对组合：文件 × 空文本 | 高 | TM-2 的 PV-2、PV-9 |
| TCOV-40 | P-V 对成对组合：标准输入 × 空文本 | 高 | TM-2 的 PV-3、PV-9 |
| TCOV-41 | P-V 对成对组合：`--text` × 无 BOM | 中 | TM-2 的 PV-1、PV-10 |
| TCOV-42 | P-V 对成对组合：`--text` × 带 BOM（字符串以 U+FEFF 开头） | 高 | TM-2 的 PV-1、PV-11 |
| TCOV-43 | P-V 对成对组合：文件 × 无 BOM | 中 | TM-2 的 PV-2、PV-10 |
| TCOV-44 | P-V 对成对组合：文件 × 带 BOM（字节以 `EF BB BF` 开头） | 高 | TM-2 的 PV-2、PV-11 |
| TCOV-45 | P-V 对成对组合：标准输入 × 无 BOM | 中 | TM-2 的 PV-3、PV-10 |
| TCOV-46 | P-V 对成对组合：标准输入 × 带 BOM（字节以 `EF BB BF` 开头） | 高 | TM-2 的 PV-3、PV-11 |
| TCOV-47 | P-V 对成对组合：纯 ASCII × 无 BOM | 中 | TM-2 的 PV-4、PV-10 |
| TCOV-48 | P-V 对成对组合：纯 ASCII × 带 BOM | 中 | TM-2 的 PV-4、PV-11 |
| TCOV-49 | P-V 对成对组合：纯中文 × 无 BOM | 高 | TM-2 的 PV-5、PV-10 |
| TCOV-50 | P-V 对成对组合：纯中文 × 带 BOM | 高 | TM-2 的 PV-5、PV-11 |
| TCOV-51 | P-V 对成对组合：中英混排 × 无 BOM | 高 | TM-2 的 PV-6、PV-10 |
| TCOV-52 | P-V 对成对组合：中英混排 × 带 BOM | 高 | TM-2 的 PV-6、PV-11 |
| TCOV-53 | P-V 对成对组合：含基本平面外字符 × 无 BOM | 中 | TM-2 的 PV-7、PV-10 |
| TCOV-54 | P-V 对成对组合：含基本平面外字符 × 带 BOM | 中 | TM-2 的 PV-7、PV-11 |
| TCOV-55 | P-V 对成对组合：含特殊 token 字面量 × 无 BOM | 高 | TM-2 的 PV-8、PV-10 |
| TCOV-56 | P-V 对成对组合：含特殊 token 字面量 × 带 BOM | 高 | TM-2 的 PV-8、PV-11 |
| TCOV-57 | P-V 对成对组合：空文本 × 无 BOM | 高 | TM-2 的 PV-9、PV-10 |
| TCOV-58 | P-V 对成对组合：空文本 × 带 BOM | 高 | TM-2 的 PV-9、PV-11 |

### 源自 TM-3（判定表测试）

| 唯一标识符 | 描述 | 优先级 | 可追溯性 |
|:---|:---|:---|:---|
| TCOV-59 | 可行判定规则 1：给了 `--text` → 取该值，打印两行，状态码 0（位置参数给不给都不影响） | 中 | TM-3 的规则 1 |
| TCOV-60 | 可行判定规则 2：没给 `--text`、给了位置参数、路径可读、解码成功 → 读文件，打印两行，状态码 0 | 中 | TM-3 的规则 2 |
| TCOV-61 | 可行判定规则 5：没给 `--text`、没给位置参数、解码成功 → 读标准输入，打印两行，状态码 0 | 中 | TM-3 的规则 5 |
| TCOV-62 | 可行判定规则 4：没给 `--text`、给了位置参数、路径不可读 → 读文件失败，以未捕获异常终止，状态码 1 | 中 | TM-3 的规则 4 |
| TCOV-63 | 可行判定规则 3：没给 `--text`、给了位置参数、路径可读、解码失败 → 打印 `not valid UTF-8: <文件路径>`，状态码 1 | 中 | TM-3 的规则 3 |
| TCOV-64 | 可行判定规则 6：没给 `--text`、没给位置参数、解码失败 → 打印 `not valid UTF-8: <stdin>`，状态码 1 | 中 | TM-3 的规则 6 |

### 源自 TM-4（场景测试）

| 唯一标识符 | 描述 | 优先级 | 可追溯性 |
|:---|:---|:---|:---|
| TCOV-65 | 主场景：给出一个 UTF-8 文本文件的路径，读到 `tokens` 与 `chars` 两行数值 | 高 | TM-4 的主场景 |
| TCOV-66 | 备选场景：用 `--text` 直接给出文本，读到两行数值 | 高 | TM-4 的「`--text` 直接给文本」 |
| TCOV-67 | 备选场景：把文本经管道送入标准输入，读到两行数值 | 高 | TM-4 的「管道送入标准输入」 |
| TCOV-68 | 备选场景：给出的文件路径不可读，看到的是一段调用栈而不是结果 | 中 | TM-4 的「文件路径不可读」 |
| TCOV-69 | 备选场景：文件不是合法 UTF-8，看到 `not valid UTF-8: <文件路径>`，看不到数值 | 中 | TM-4 的「文件不是合法 UTF-8」 |
| TCOV-70 | 备选场景：标准输入不是合法 UTF-8，看到 `not valid UTF-8: <stdin>`，看不到数值 | 中 | TM-4 的「标准输入不是合法 UTF-8」 |
| TCOV-71 | 备选场景：引擎未装、打包 wheel 可用——离线装上引擎后完成计数 | 低 | TM-4 的「装打包 wheel 后计数成功」 |
| TCOV-72 | 备选场景：引擎未装、打包 wheel 用不上——转联网安装后完成计数 | 低 | TM-4 的「转联网安装后计数成功」 |
| TCOV-73 | 备选场景：引擎未装、打包 wheel 用不上、联网也不通——看到的是一段调用栈 | 低 | TM-4 的「联网安装也失败」 |
| TCOV-74 | 备选场景：参数形式不合约定——打印用法说明与一行错误说明，状态码 2 | 低 | TM-4 的「参数形式不合约定」 |
| TCOV-75 | 备选场景：拿官方 API 返回的 `usage` 输入 token 数与脚本结果核对，两者一致 | 高 | TM-4 的「与线上口径核对」 |

## 二、测试用例

### 组合搭配（TC-1 至 TC-18）

这 18 条按成对档导出，一条用例覆盖三个 P-V 对成对组合，合起来覆盖 TM-2 全部 36 个覆盖项。

| 唯一标识符 | 目标 | 优先级 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|
| TC-1 | 验证 `--text` 传纯 ASCII、不带 BOM 时的两行数值 | 中 | `count_tokens.py --text "hello world"` | 标准输出 `tokens: 2`、`chars: 11`；标准错误为空；状态码 0 |
| TC-2 | 验证读一个带 BOM 的纯 ASCII 文件时 BOM 被剥掉 | 中 | `count_tokens.py <文件路径>`，文件字节为 `EF BB BF` 后接 `hello world` | 标准输出 `tokens: 2`、`chars: 11`；状态码 0 |
| TC-3 | 验证标准输入传纯 ASCII 时的两行数值 | 中 | `count_tokens.py`，标准输入为 `hello world` 的 UTF-8 字节，无 BOM | 标准输出 `tokens: 2`、`chars: 11`；状态码 0 |
| TC-4 | 验证 `--text` 的值以 U+FEFF 开头时该字符不被剥掉 | 高 | `count_tokens.py --text "﻿你好，世界"`（字符串以 U+FEFF 开头） | 标准输出 `tokens: 4`、`chars: 6`；状态码 0 |
| TC-5 | 验证读带 BOM 的纯中文文件时 BOM 被剥掉 | 高 | `count_tokens.py <文件路径>`，文件字节为 `EF BB BF` 后接 `你好，世界` | 标准输出 `tokens: 3`、`chars: 5`；状态码 0 |
| TC-6 | 验证标准输入传纯中文时的两行数值 | 高 | `count_tokens.py`，标准输入为 `你好，世界` 的 UTF-8 字节，无 BOM | 标准输出 `tokens: 3`、`chars: 5`；状态码 0 |
| TC-7 | 验证 `--text` 传中英混排、含首尾空白与换行的文本 | 高 | `count_tokens.py --text "  Hello 世界\n你好 world  "` | 标准输出 `tokens: 8`、`chars: 21`；状态码 0 |
| TC-8 | 验证读一份中英混排、无 BOM 的文件 | 高 | `count_tokens.py <文件路径>`，文件内容为 `  Hello 世界\n你好 world  `，UTF-8 编码、无 BOM | 标准输出 `tokens: 8`、`chars: 21`；状态码 0 |
| TC-9 | 验证标准输入传带 BOM 的中英混排文本 | 高 | `count_tokens.py`，标准输入为 `EF BB BF` 后接 `  Hello 世界\n你好 world  ` 的 UTF-8 字节 | 标准输出 `tokens: 8`、`chars: 21`；状态码 0 |
| TC-10 | 验证 `--text` 的值以 U+FEFF 开头、正文含 emoji 时该字符被计入 | 中 | `count_tokens.py --text "﻿ok 😀🎉 done"` | 标准输出 `tokens: 7`、`chars: 11`；状态码 0 |
| TC-11 | 验证读一个带 BOM、正文含 emoji 的文件 | 中 | `count_tokens.py <文件路径>`，文件字节为 `EF BB BF` 后接 `ok 😀🎉 done` | 标准输出 `tokens: 6`、`chars: 10`；状态码 0 |
| TC-12 | 验证标准输入传含 emoji 的文本 | 中 | `count_tokens.py`，标准输入为 `ok 😀🎉 done` 的 UTF-8 字节，无 BOM | 标准输出 `tokens: 6`、`chars: 10`；状态码 0 |
| TC-13 | 验证 `--text` 传 DeepSeek 特殊 token 的字面量时按官方词表算作一个 token | 高 | `count_tokens.py --text "<｜end▁of▁sentence｜>"` | 标准输出 `tokens: 1`、`chars: 19`；状态码 0 |
| TC-14 | 验证文件里的 DeepSeek 特殊 token 字面量同样算作一个 token | 高 | `count_tokens.py <文件路径>`，文件内容为 `<｜end▁of▁sentence｜>`，UTF-8 编码、无 BOM | 标准输出 `tokens: 1`、`chars: 19`；状态码 0 |
| TC-15 | 验证标准输入传带 BOM 的特殊 token 字面量 | 高 | `count_tokens.py`，标准输入为 `EF BB BF` 后接 `<｜end▁of▁sentence｜>` 的 UTF-8 字节 | 标准输出 `tokens: 1`、`chars: 19`；状态码 0 |
| TC-16 | 验证 `--text` 传空字符串时不会退回去读标准输入 | 高 | `count_tokens.py --text ""`，同时让标准输入有数据（如 `hello world`） | 标准输出 `tokens: 0`、`chars: 0`；状态码 0；标准输入的数据不被读取 |
| TC-17 | 验证一个只含 BOM、没有别的字节的文件被当作空文本 | 高 | `count_tokens.py <文件路径>`，文件字节恰为 `EF BB BF`（3 字节） | 标准输出 `tokens: 0`、`chars: 0`；状态码 0 |
| TC-18 | 验证标准输入只有 BOM 时被当作空文本 | 高 | `count_tokens.py`，标准输入恰为 `EF BB BF` 这 3 个字节 | 标准输出 `tokens: 0`、`chars: 0`；状态码 0 |

### 输入来源与报错（TC-19 至 TC-21、TC-31、TC-32）

| 唯一标识符 | 目标 | 优先级 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|
| TC-19 | 验证 `--text` 与位置参数同时给出时的处置（依据未规定的组合） | 中 | `count_tokens.py --text "hello world" <一个存在的文件路径>`，该文件内容为 `你好，世界` | 标准输出 `tokens: 2`、`chars: 11`——即 `--text` 优先、文件被忽略；状态码 0；标准错误为空。该优先级在用法说明里没有出处，执行后记为依据表述不完整 |
| TC-20 | 验证位置参数给出的路径不可读时的处置（依据未规定的组合） | 中 | 两次执行：一次给一个不存在的路径，一次给一个目录的路径 | 两次都不打印 `tokens` 与 `chars`；标准错误里是 Python 异常调用栈（`FileNotFoundError` 或 `IsADirectoryError`）；状态码 1。执行后记为依据未规定该情形 |
| TC-21 | 验证参数形式不合约定时的处置 | 低 | 两次执行：一次给两个位置参数，一次给一个未知选项 `--nope` | 两次都在标准错误打印用法说明 `usage: count_tokens.py [-h] [--text TEXT] [file]` 与一行 `error: unrecognized arguments: …`；标准输出为空；状态码 2 |
| TC-31 | 验证文件不是合法 UTF-8 时的报错与退出 | 中 | `count_tokens.py <文件路径>`；两次执行，一次文件字节为 `FF FE 41 42`，一次文件内容是 GBK 编码的 `你好，世界` | 两次都只打印 `not valid UTF-8: <该文件路径>`（路径原样带出）；不打印 `tokens` 与 `chars`；状态码 1 |
| TC-32 | 验证标准输入不是合法 UTF-8 时的报错与退出 | 中 | `count_tokens.py`，标准输入为 `FF FE 41 42` 这 4 个字节 | 只打印 `not valid UTF-8: <stdin>`（来源标识是 `<stdin>`，不是文件路径）；不打印 `tokens` 与 `chars`；状态码 1 |

### 引擎自动安装（TC-22 至 TC-24）

这三条各有独立的前置条件，不复用全篇共用的那条。

| 唯一标识符 | 目标 | 优先级 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|
| TC-22 | 验证目标机没装引擎时能用打包 wheel 离线装上 | 低 | 前置条件：新建一个没装 `tokenizers` 的干净虚拟环境，`wheels/` 下的 wheel 可读，全程断网。输入：在该环境里执行 `count_tokens.py`，标准输入为 `hello world` | 标准错误先出现一行 `Installing bundled tokenizers wheel (offline) ...`；随后标准输出 `tokens: 2`、`chars: 11`；状态码 0；执行完该环境里 `tokenizers` 版本为 0.22.2 |
| TC-23 | 验证打包 wheel 用不上时转联网安装 | 低 | 前置条件：干净虚拟环境，`wheels/` 目录下没有可用 wheel（或 wheel 安装失败），网络可达 PyPI。输入：在该环境里执行 `count_tokens.py`，标准输入为 `hello world` | 标准错误先出现打包 wheel 的安装提示，再出现一行 `Installing tokenizers==0.22.2 from PyPI ...`；随后标准输出 `tokens: 2`、`chars: 11`；状态码 0 |
| TC-24 | 验证两条安装路径都不通时的处置 | 低 | 前置条件：干净虚拟环境，`wheels/` 下没有可用 wheel，网络不通。输入：在该环境里执行 `count_tokens.py`，标准输入为 `hello world` | 不打印 `tokens` 与 `chars`；标准错误里是安装失败的异常调用栈；状态码非 0 |

### 高风险加导（TC-25 至 TC-30）

这几条覆盖的覆盖项 TC-1 至 TC-18 已经盖到，这里再导是为提高充分性，重点在风险信息点名的「数出来的 token 不准」。

| 唯一标识符 | 目标 | 优先级 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|
| TC-25 | 拿官方 API 返回的用量与脚本结果核对，验证数得准 | 高 | 前置条件：网络可达 DeepSeek API，持有可用凭据。输入：把 `你好，世界` 发给 API 并取出返回里的 `usage` 输入 token 数；再照 TC-1 的方式对本脚本执行 `--text "你好，世界"` | 标准输出 `tokens: 3`、`chars: 5`；状态码 0；`tokens` 的数值与 API 返回的输入 token 数一致。不一致时以线上 `usage` 为准，判本脚本的计数为不符 |
| TC-26 | 验证文档点名的易错形态：中文开头、含空格 | 高 | `count_tokens.py --text "  中文 开头 的文本 with spaces"` | 标准输出 `tokens: 9`、`chars: 23`；状态码 0。若得到 `tokens: 0` 或与字符数相等的结果，即为计数口径用错 |
| TC-27 | 验证 `chars` 报的不是 UTF-8 字节数 | 高 | `count_tokens.py --text "你好，世界"`（5 个字符，UTF-8 编码 15 字节） | 标准输出 `tokens: 3`、`chars: 5`——`chars` 是 5 不是 15；状态码 0 |
| TC-28 | 验证长文本下计数与字符数都对得上 | 中 | `count_tokens.py <文件路径>`，文件内容为 `你好，世界 hello world ` 重复 20000 遍（360000 字符、560000 字节） | 标准输出 `tokens: 120000`、`chars: 360000`；状态码 0；本例在实测机上约 1 秒内跑完，明显超出这个量级即记为运行行为异常 |
| TC-29 | 验证只含单个空白字符的输入 | 中 | 三次执行，`--text` 分别传一个空格、一个换行符、一个制表符 | 三次都是标准输出 `tokens: 1`、`chars: 1`；状态码 0 |
| TC-30 | 验证同一段文本换来源传入，结果完全一致 | 高 | 对 `你好，世界` 依次用三种来源执行：`--text`、一个 UTF-8 无 BOM 的文件、标准输入 | 三次都是 `tokens: 3`、`chars: 5`；状态码 0。三次中有任何一次不同，即判为来源影响了计数 |

## 三、覆盖项 ↔ 用例对应表

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 命令行只给出 `--text`，其值为一个字符串 | TC-1、TC-4、TC-7、TC-10、TC-13、TC-16、TC-19、TC-25、TC-26、TC-27、TC-28、TC-29、TC-30 |
| TCOV-2 | 命令行给出一个位置参数，该路径存在且可读 | TC-2、TC-5、TC-8、TC-11、TC-14、TC-17、TC-30 |
| TCOV-3 | 命令行既不给 `--text` 也不给位置参数，标准输入中有数据 | TC-3、TC-6、TC-9、TC-12、TC-15、TC-18、TC-22、TC-23、TC-24、TC-30 |
| TCOV-4 | 命令行同时给出 `--text` 与位置参数 | TC-19 |
| TCOV-5 | 位置参数给出的路径不可读（不存在，或指向目录） | TC-20 |
| TCOV-6 | 参数形式不合命令行约定（多个位置参数，或未知选项） | TC-21 |
| TCOV-7 | 纯 ASCII 文本 | TC-1、TC-2、TC-3、TC-30 |
| TCOV-8 | 纯中文文本 | TC-4、TC-5、TC-6、TC-25、TC-26、TC-27、TC-30 |
| TCOV-9 | 中英混排、含空格与换行、含首尾空白的文本 | TC-7、TC-8、TC-9、TC-26、TC-28 |
| TCOV-10 | 含基本平面外字符（emoji）的文本 | TC-10、TC-11、TC-12 |
| TCOV-11 | 含 DeepSeek 特殊 token 字面量的文本 | TC-13、TC-14、TC-15 |
| TCOV-12 | 空文本 | TC-16、TC-17、TC-18 |
| TCOV-13 | 字节来源的数据是合法 UTF-8，解码成功 | TC-2、TC-3、TC-5、TC-6、TC-8、TC-9、TC-11、TC-12、TC-14、TC-15、TC-17、TC-18、TC-22、TC-23、TC-24、TC-30 |
| TCOV-14 | 字节来源的数据不是合法 UTF-8，解码抛异常 | TC-31、TC-32 |
| TCOV-15 | 按 `tokenizer.json` 的规范语义计数，不经兼容转换层 | TC-1、TC-2、TC-3、TC-4、TC-5、TC-6、TC-7、TC-8、TC-9、TC-10、TC-11、TC-12、TC-13、TC-14、TC-15、TC-16、TC-17、TC-18、TC-19、TC-22、TC-23、TC-25、TC-26、TC-27、TC-28、TC-29、TC-30 |
| TCOV-16 | 特殊 token 字面量按官方词表算作一个特殊 token | TC-13、TC-14、TC-15 |
| TCOV-17 | 字符数算的是码点个数，不是 UTF-8 字节数 | TC-5、TC-6、TC-8、TC-9、TC-11、TC-12、TC-26、TC-27、TC-28 |
| TCOV-18 | 字节来源的 BOM 被剥除，不计入字符数 | TC-2、TC-5、TC-9、TC-11、TC-15、TC-17、TC-30 |
| TCOV-19 | `--text` 值中的 U+FEFF 计入字符数 | TC-4、TC-10 |
| TCOV-20 | 标准输出打印 `tokens: N` 与 `chars: M` 两行 | TC-1、TC-2、TC-3、TC-4、TC-5、TC-6、TC-7、TC-8、TC-9、TC-10、TC-11、TC-12、TC-13、TC-14、TC-15、TC-16、TC-17、TC-18、TC-19、TC-22、TC-23、TC-25、TC-26、TC-27、TC-28、TC-29、TC-30 |
| TCOV-21 | 打印 `not valid UTF-8: <来源标识>` 并以状态码 1 退出 | TC-31、TC-32 |
| TCOV-22 | 以未捕获的异常终止，不打印结果 | TC-20、TC-24 |
| TCOV-23 | `--text` × 纯 ASCII | TC-1 |
| TCOV-24 | 文件 × 纯 ASCII | TC-2 |
| TCOV-25 | 标准输入 × 纯 ASCII | TC-3 |
| TCOV-26 | `--text` × 纯中文 | TC-4 |
| TCOV-27 | 文件 × 纯中文 | TC-5 |
| TCOV-28 | 标准输入 × 纯中文 | TC-6 |
| TCOV-29 | `--text` × 中英混排含空格与换行 | TC-7 |
| TCOV-30 | 文件 × 中英混排含空格与换行 | TC-8 |
| TCOV-31 | 标准输入 × 中英混排含空格与换行 | TC-9 |
| TCOV-32 | `--text` × 含基本平面外字符 | TC-10 |
| TCOV-33 | 文件 × 含基本平面外字符 | TC-11 |
| TCOV-34 | 标准输入 × 含基本平面外字符 | TC-12 |
| TCOV-35 | `--text` × 含特殊 token 字面量 | TC-13 |
| TCOV-36 | 文件 × 含特殊 token 字面量 | TC-14 |
| TCOV-37 | 标准输入 × 含特殊 token 字面量 | TC-15 |
| TCOV-38 | `--text` × 空文本 | TC-16 |
| TCOV-39 | 文件 × 空文本 | TC-17 |
| TCOV-40 | 标准输入 × 空文本 | TC-18 |
| TCOV-41 | `--text` × 无 BOM | TC-1、TC-16 |
| TCOV-42 | `--text` × 带 BOM | TC-4、TC-10 |
| TCOV-43 | 文件 × 无 BOM | TC-8、TC-14 |
| TCOV-44 | 文件 × 带 BOM | TC-2、TC-5、TC-11、TC-17 |
| TCOV-45 | 标准输入 × 无 BOM | TC-3、TC-6、TC-12 |
| TCOV-46 | 标准输入 × 带 BOM | TC-9、TC-15、TC-18 |
| TCOV-47 | 纯 ASCII × 无 BOM | TC-1、TC-3、TC-30 |
| TCOV-48 | 纯 ASCII × 带 BOM | TC-2 |
| TCOV-49 | 纯中文 × 无 BOM | TC-6、TC-25、TC-27、TC-30 |
| TCOV-50 | 纯中文 × 带 BOM | TC-4、TC-5 |
| TCOV-51 | 中英混排 × 无 BOM | TC-7、TC-8、TC-26、TC-28 |
| TCOV-52 | 中英混排 × 带 BOM | TC-9 |
| TCOV-53 | 含基本平面外字符 × 无 BOM | TC-12 |
| TCOV-54 | 含基本平面外字符 × 带 BOM | TC-10、TC-11 |
| TCOV-55 | 含特殊 token 字面量 × 无 BOM | TC-13、TC-14 |
| TCOV-56 | 含特殊 token 字面量 × 带 BOM | TC-15 |
| TCOV-57 | 空文本 × 无 BOM | TC-16 |
| TCOV-58 | 空文本 × 带 BOM | TC-17、TC-18 |
| TCOV-59 | 判定规则 1：给了 `--text` → 取该值，打印两行，状态码 0 | TC-1、TC-19 |
| TCOV-60 | 判定规则 2：给了位置参数且路径可读、解码成功 → 读文件，打印两行 | TC-2 |
| TCOV-61 | 判定规则 5：不给任何文本来源参数、解码成功 → 读标准输入，打印两行 | TC-3 |
| TCOV-62 | 判定规则 4：给了位置参数但路径不可读 → 以未捕获异常终止 | TC-20 |
| TCOV-63 | 判定规则 3：给了位置参数、路径可读但解码失败 → 报 `not valid UTF-8: <文件路径>` | TC-31 |
| TCOV-64 | 判定规则 6：不给文本来源参数、解码失败 → 报 `not valid UTF-8: <stdin>` | TC-32 |
| TCOV-65 | 主场景：给出文件路径，读到两行数值 | TC-2、TC-5、TC-8、TC-11、TC-14、TC-17、TC-28、TC-30 |
| TCOV-66 | 备选场景：用 `--text` 直接给出文本，读到两行数值 | TC-1、TC-4、TC-7、TC-10、TC-13、TC-16、TC-19、TC-25、TC-26、TC-27、TC-29 |
| TCOV-67 | 备选场景：经管道送入标准输入，读到两行数值 | TC-3、TC-6、TC-9、TC-12、TC-15、TC-18、TC-30 |
| TCOV-68 | 备选场景：文件路径不可读，看到的是调用栈 | TC-20 |
| TCOV-69 | 备选场景：文件不是合法 UTF-8，看到 `not valid UTF-8: <文件路径>` | TC-31 |
| TCOV-70 | 备选场景：标准输入不是合法 UTF-8，看到 `not valid UTF-8: <stdin>` | TC-32 |
| TCOV-71 | 备选场景：离线装上打包 wheel 后完成计数 | TC-22 |
| TCOV-72 | 备选场景：转联网安装后完成计数 | TC-23 |
| TCOV-73 | 备选场景：两条安装路径都不通，看到的是调用栈 | TC-24 |
| TCOV-74 | 备选场景：参数形式不合约定，打印用法说明，状态码 2 | TC-21 |
| TCOV-75 | 备选场景：与官方 API 返回的用量核对，两者一致 | TC-25 |

## 四、覆盖率自检

| 技术 | 覆盖项总数 T | 已覆盖 N | 覆盖率 C | 要求 | 结论 |
|:---|:---|:---|:---|:---|:---|
| 等价类划分 | 22 | 22 | 100% | 100% | 达标 |
| 组合测试（成对档） | 36 | 36 | 100% | 100% | 达标 |
| 判定表测试 | 6 | 6 | 100% | 100% | 达标 |
| 场景测试 | 11 | 11 | 100% | 100% | 达标 |

四条技术的覆盖项全部被测试用例覆盖，对应表里没有留空的行，达到测试完成准则。没有需要剔除的不可行覆盖项。
