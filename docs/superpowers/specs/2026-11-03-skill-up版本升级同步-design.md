# skill-up v0.14.0 升级后 test-case-design 的同步 — 设计文档

日期：2026-11-03
状态：待评审

这份把 `test-case-design` 技能下 `references/评测方案/skill-up/` 的两份文档，从对着 skill-up `v0.12.0` 同步到 `v0.14.0`。同步包括两件事：**内容对上 v0.14.0**（新增字段、改掉的旧结论、版本标记），**维护方式改成不读上游源码、不依赖公网也能判断是否一致**。删掉正文里的源码行号与公网链接，是第二件事的一部分。

## 1. 由头

本机装的 skill-up 是 `0.14.0`，仓库里这两份文档锁的仍是 `v0.12.0` / 源码 `7f1ff9b`。中间隔了 v0.13.0 与 v0.14.0 两个发布版。不同步的后果有三样：

- **新能力看不见。** `judge.engine`、`judges` 数组、`user_simulator` 这些写第七份会用到的字段，文档里没有。写第七份的人或模型只能照旧写法落配置。
- **旧结论把人带偏。** `--output-dir` 传相对路径在 0.14.0 上已经不再报错，文档还写着「一律写绝对路径」；`judge.model` 已经不是唯一必填，文档还写「必填」。
- **维护方式跟不上。** 现在要求读上游源码、按行号重核；维护者不读代码。而且上游一改，行号就漂——2026-11-03 核了一遍，7 处里 3 处已经对不上。

所以这次同步不能只补内容：维护方式不换，下次升级还是同样的局面。

### 1.1 核实到的事实

这张表记的是维护者核实用过的来源，给评审与重核看；它不随插件发出。写进 `usage-notes.md` 与 README 的内容按 4.2 的取材规则来，不照抄这里的公网出处。

| 事实 | 出处 |
|:---|:---|
| 仓库锁发布版 `v0.12.0` / 源码 `7f1ff9b`；本机装的是 `0.14.0` | 文档顶部；`skill-up --version` |
| v0.14.0 已接受相对 `--output-dir`，不再报 `escapes context dir` | 上游 CHANGELOG 0.14.0 的 Fixed 段 |
| v0.14.0 新增 `judge.engine` 与 `judges`；`judge.model` 不再是唯一必填 | 上游 `skills/skill-upper/references/judge-types.md`、`eval-yaml.md` |
| v0.13.0 新增 `user_simulator`；`tool_called` 按 `name` 匹配工具 | 本机 `~/.claude/skills/skill-upper/references/eval-yaml.md`、`case-yaml.md`、`judge-types.md` |
| v0.14.0 改了 `expect` 门控与 rule-based 的计分口径 | 上游 CHANGELOG 0.14.0 的 Changed 段 |
| 上游 CHANGELOG 只在仓库里，不随二进制或 `/skill-upper` 发出，文档站也没有 CHANGELOG 页 | 查 `~/.claude/skills/skill-upper/` 与上游 `docs/zh/` |
| 插件安装只拷贝 `plugin/`；`evals/`、`runs/`、`checks/`、`docs/` 都不随插件发出 | 本仓库 `CLAUDE.md` |
| `/skill-upper` 的 `references/` 不含 `cli-reference.md`、`writing-evals.md`、`windows.md`；这三份只在文档站与上游仓库 | `ls ~/.claude/skills/skill-upper/references/` |
| 文档里的 `runs\...`、`evals/business-term-builder/`、`xlsx/...`、`.claude/evals/...` 都是开发机上的历史产物 | 这些路径都在 `plugin/` 外 |
| 参考文档 `README.md` 写的是 `https://github.com/zhcmeng/skill-up`，与本机 origin（`alibaba/skill-up`）和文档站不一致 | `git remote -v`；上游 README |
| 「上游没有发布 tag」不成立：`v0.12.0` 标签创建于 2026-09-18，早于文档写作日 2026-09-29 | `git for-each-ref refs/tags` |
| `usage-notes.md` 正文有 7 处源码行号引用；3 处已漂 | 第 9、20、38、84、94、98 行；对照 v0.14.0 源码 |
| 文档自己写明「每条注了出处（源码文件与行号）」「换版本后按出处重核」「只有实测过的才写成事实」 | `usage-notes.md:5`、`:111` 到 `:113`、`:107` |
| 三份 `evals/*/eval.yaml` 在 0.14.0 下 `skill-up validate` 全部通过 | 2026-11-03 实跑 |
| 本机 `~/.claude/skills/skill-upper/` 与 v0.14.0 逐字一致（只差 CRLF）；比上游 HEAD 少 81 行，少的是 v0.14.0 之后的未发布提交 | 规范化换行后 `diff` 四个文件，差异均为 0 |
| 插件版本现为 `1.29.1` | `plugin/.claude-plugin/plugin.json:4`、`.claude-plugin/marketplace.json:9` |

## 2. 判据

**一、内容与 v0.14.0 一致。** 新增字段、改掉的旧结论、版本标记，三样都要对上。判定标准不是「像」，是照 `/skill-upper` 的参考文档或实跑结果能对上。

**二、依据不依赖上游源码、本机那份 skill-up 克隆，也不依赖公网。** 正文每条结论只留两类来源：随技能安装的 `/skill-upper` 参考文档、实跑看见过（`skill-up --help`、`validate`、`run` 的输出与报告）。上游源码的文件名、函数名、行号不写；`C:\Study\skill-up` 这类只有本机才有的路径不写；公网文档站的 URL、GitHub 上的 CHANGELOG 与 release 页也不写——使用者那边不保证能上外网，也不该为写第七份去翻发布说明。用户看得见的输出保留——报错原文、报告字段名、git 提交名、警告文字。

**三、版本不一致能被发现。** 文档顶部锁一个发布版；读文档前跑一次 `skill-up --version` 跟它比，不一致就把文档当历史版本用、涉及运行时行为的结论标「待确认」。不靠人读源码，也不靠翻公网文档，也不在 `checks/` 里另做自动比对。

**四、`usage-notes.md` 仍是补充，不是 `/skill-upper` 文档的副本。** `/skill-upper` 写过的只给文件名与段落名；这份文档只收它没写、或写得不够用的。

**五、不新增评测。** 不给 `test-case-design` 补评测套件；重核用的临时探针跑完即删，不入库。

**六、离开开发机也成立。** 插件只发 `plugin/`；正文不引用 `evals/`、`runs/`、`checks/`、`docs/` 下的路径，不写公网文档站与 GitHub 的 URL，不假设用户装的就是 v0.14.0。`/skill-upper` 是必需依赖：按插件方式安装的落点就是 `~/.claude/skills/skill-upper/`；先找现成的，找不到再问用户要不要帮装，默认装全局 `~/.claude/skills/skill-upper/`、不进项目目录，不退回公网文档。

**七、使用与维护分开，按目录分。** 维护者 = 本工程（这个仓库）下的作者；使用者 = 安装后的目录（插件分发出去的那份技能目录）里的人。使用者只能使用：读技能、产出六份与第七份、改自己的产出；不改技能目录里的任何文件（安装份只读），也不做回写、重核、版本号更新。维护只在仓库里做：改 `plugin/skills/test-case-design/`、跑 `checks/`、写 `docs/maintainers/`。`plugin/` 里出现的每一句话都只对使用者说；回写 `usage-notes.md`、按核验索引重核、升级后更新版本号、维护文件地图，这四件事只写在 `plugin/` 外的维护者文档里，不随插件发出。

## 3. 决策记录

### 3.1 依据怎么换：三个方案

| 方案 | 做法 | 取舍 |
|:---|:---|:---|
| A. 文件名 + 函数名 | 行号换函数名，如 `FindSkillDir`（`loader.go`） | 改动最小；仍以源码为依据，与「不读代码」相悖 |
| **B. `/skill-upper` 文档 / 实测 两类（选这个）** | 读源码才知道的条目，改成跑一遍能看见的行为；跑不出来又只是实现细节的，删掉 | 依据换掉了，不是藏起来；代价是要补几次探针 |
| C. 正文不写出处，末尾放索引 | 正文只写行为，文末一张重核表 | 维护成本没变，只是挪了位置；表照样会旧 |

选 B。它正面解决「使用不应该基于源码」：每条结论都能靠「`/skill-upper` 写过」或「跑一遍」站住。A 只把脆弱性藏起来；C 只是把同样的负担挪到文末。

### 3.2 版本自查放使用者侧，不做维护者侧的自动比对

维护者自己发起 skill-up 升级，本来就知道本机装的是哪一版；升级后文档没跟上，他自己清楚。再在 `checks/` 里加一段比对，红的还是他刚做过的事，价值低，还要多维护一段检查代码。**不做这个自动比对。**

使用者不知道文档对着哪一版，读之前自查才有价值。做法是在 `usage-notes.md` 顶部写清：先跑 `skill-up --version`，与顶部版本行一致就照用；不一致就把本文当历史版本看，涉及运行时行为的结论在产出里标「待确认」。`SKILL.md` 两处读 `usage-notes.md` 的地方、同目录 `skill-up/README.md` 的锁定版本一段，都指到这一步。

不把自查做成脚本：比较就是一条命令加一行文本，模型读文档时直接做；装机上多一个要 Python 的脚本，反而多一个失败点。

### 3.3 重核用的探针跑测：一次性、放 `.tmp/`、不入库

几条只有跑起来才看得见的结论（钩子不生效、装技能跳过 `evals/`、`setup_steps` 与夹具的先后），用一份临时配置一次跑完，`--no-delete` 留下工作区逐项看。配置放 `.tmp/skill-up-probe/`，核完删掉；不进 `evals/`，不算新评测。

### 3.4 `plugin/` 里一个字都不提维护

`plugin/` 下所有随插件发给使用者的文件，一个字都不提维护：不写「维护者」「回写」「重核」「版本更新」「文件地图」「怎么更新」，也不写「这份文档由维护者更新；使用者只读」这类说明。技能根 `README.md` 与 `skill-up/README.md` 只写是什么、给什么、产出什么、依赖什么、文件结构、脚本脾气；维护内容全部放 `plugin/` 外的 `docs/maintainers/test-case-design.md`。使用者不需要知道谁维护、怎么维护，只需要知道这份文档对着哪个版本、对不上时怎么用。

### 3.5 Python 3 只写进异常处理，不设前置条件

三个脚本要 Python 3。**不在 `SKILL.md` 单设「前置条件」一节**：单占一节会让模型把它当成每一步开头都要过的检查，本来能跑的一次流程也会先停下来查一遍。做法是：正常流程不提，只在「异常处理」表的「环境」两行里写——命令报找不到 `python`／`python3` 时依次试 `python3`、`python`、`py -3`（Windows）；一跑就报语法错（多半是 `python` 指到了 Python 2）也照此改试；都跑不起来，才告诉用户装 Python 3。技能根 `README.md` 照样写明这三个脚本要 Python 3，那是给读文档的人看的，不构成预检。

### 3.6 异常先在技能内处理，处理不了才告诉用户

`SKILL.md` 新增一节「异常处理」，把环境、依赖、输入、脚本四类异常汇总成一张表：先写自动尝试的修法，再写尝试过仍失败时告诉用户什么。**能自己修的不问用户**；只有修过一轮还失败，才把报错原文、已经试过的修法、还需要用户做什么一次说清。正常缺测试依据、缺风险信息不在此列——那是开工输入，只有用户知道，照旧只问缺的那几样。**不做预检**：异常处理是出错时的次序，不是每一步开头都跑一遍检查。

## 4. 设计

### 4.1 同步清单：v0.12.0 → v0.14.0

「原报告」一列沿用 2026-11-03 那轮对照报告的编号，方便回查。

| 上游变化 | 文档位置 | 改法 | 原报告 |
|:---|:---|:---|:---|
| 相对 `--output-dir` 已可用 | 第五节 | 那条改写：保留 `escapes context dir` 的现场作为历史记录，注明 0.14.0 起已修；「一律写绝对路径」从硬要求降为习惯 | 一（第 1 条） |
| `judge.model` 不再是唯一必填 | 第五节 | 改成「`judge.model` 或 `judge.engine` 必须有一个」，补两者互斥 | 一（第 2 条） |
| 新增 `judge.engine` | 第五节 | 补一条，见 4.3.1 | 二 |
| 新增 `judges` 数组 | 第五节 | 补一条，见 4.3.1 | 二 |
| 新增 `user_simulator` | 第五节 | 补一条，见 4.3.1 | 二 |
| MCP 工具名精确匹配 | 第五节 | 补一条，见 4.3.1 | 二 |
| 计分口径变化 | 第五节 | 补一条，见 4.3.1 | 二 |
| 有发布 tag，可锁发布版 | 顶部版本行、同目录 `README.md` 出处段 | 改锁 `v0.14.0`，删掉「上游没有发布 tag」与源码 commit | 五 |
| 源码行号会漂 | 全文 | 删除；按 4.2 换成 `/skill-upper` 文档／实测 | 三 |
| 本机 `skill-upper` 的版本 | 本机目录 | 核对结果：与 v0.14.0 逐字一致，不需要替换；按 4.8 验一次 | 六 |
| 只在开发机成立的引用（历史跑测、上游仓库路径、fork URL、Windows 专有路径） | 全文与同目录 `README.md` | 按 4.2.3 逐项替换或删除 | 七（本轮新增） |

表里没有 4.2.4 那四处——它们不是 v0.14.0 带来的变化，是按「装插件的用户」视角扫出来的同类问题，一并在这轮修掉。

### 4.2 取材规则

先定一条：**依据必须是离开本仓库之后、在使用者机器上就找得到的。** `C:\Study\skill-up` 是开发机上的克隆，装到别人机器上时不存在；公网文档站与 GitHub 也不保证能上，所以都不算。算数的只有两块：`/skill-upper` 装上的参考文档，和 `skill-up` 命令实跑出来的结果。

#### 4.2.1 使用者那边有什么

| 来源 | 离开本仓库还在吗 | 怎么引 |
|:---|:---|:---|
| `/skill-upper` 的 `references/*.md` | 装了 `/skill-upper` 就有，在 `~/.claude/skills/skill-upper/references/` | 文件名 + 小节名，例：「`judge-types.md` 的 `judge.engine` 段」 |
| `skill-up` 命令与 `--help` | 装了 CLI 就有 | 写命令，例：「`skill-up run --help`」 |
| 公网文档站与 GitHub 上的 CHANGELOG、release | 在，但使用者那边不依赖外网 | 不引，不写 URL |
| 本机的 skill-up 克隆 | 不在 | 不写 |
| 本机跑测的产物 | 不在 | 只写日期与版本，产物路径不写 |

公网文档站与 GitHub 上的 CHANGELOG、release 虽然离开本仓库还在，但使用者那边不依赖外网，所以也不算依据。只在公网文档里有的细节，按 4.2.2 的办法处置——先在 `/skill-upper` 的 `references/` 里找同主题的段落；找不到就跑一次 CLI 核出来；跑不出来、又不影响第七份写法的删掉。

#### 4.2.2 正文怎么写

- **随技能安装的 `/skill-upper` 文档**：写文件名与小节名。这是字段级细节的第一依据。
- **实测**：`skill-up --help`、`skill-up validate`、`skill-up run` 的输出与报告。统一写成 `（YYYY-MM-DD 实测，skill-up vX.Y.Z）`，并在 `docs/maintainers/test-case-design.md` 的核验索引登记一条对应的核验方式。
- **公网文档站、GitHub 上的 CHANGELOG 与 release 不引。** 只在公网文档里有的细节，按这个次序处置：先在 `/skill-upper` 的 `references/` 里找同主题的段落；找不到就跑一次 CLI 核出来；跑不出来、又不影响第七份写法的删掉，影响写法又核不出来的标「待确认」。

删除两类内容：

- 只是实现细节、对「怎么写第七份」没有影响的部分，例如「类型判断在哪个分支」「用哪个内部函数」。
- 无法用 CLI 看见、也不在 `/skill-upper` 文档里的结论——除非它改变了第七份的写法，那种走探针跑测补上。

#### 4.2.3 只在开发机成立的引用

按「装插件的用户」那边核了一遍，下面这些引用离开本仓库就找不到，要逐项处理：

| 引用 | 为什么用户那边没有 | 改成 |
|:---|:---|:---|
| `runs\2026-10-10-...` 等跑测目录 | `runs/` 在 `plugin/` 外，不随插件发出 | 「开发仓库里 2026-10-10 那批跑测」；路径删掉 |
| `evals/business-term-builder/`、`xlsx/公会系统/`、`game-design-xlsx-to-md/`、`.claude/evals/...` | 同上，都是开发机上的历史批次 | 同上，只留日期与结论，不留路径 |
| `docs/zh/guide/writing-evals.md`、`cli-reference.md`、`windows.md` | 只在 skill-up 克隆与公网文档站里，使用者那边不依赖 | 不引；同一事实在 `/skill-upper` 的 `references/` 里找对应段落，找不到就跑一次 `--help`／`validate`／`run` 核出来；核不出来又不影响第七份写法的删掉 |
| `https://github.com/zhcmeng/skill-up` 等公网 URL | 使用者不依赖外网 | 删掉 URL；只留项目名与版本（`skill-up v0.14.0`） |
| GitHub 上的 CHANGELOG 与 release | 使用者不依赖外网 | 不写链接；事实能跑出来的标实测，跑不出来又影响写法的标「待确认」 |
| `%TEMP%\skill-up-<随机数>`、`C:\Program Files\Git\...` | 只在 Windows 成立 | 写明「Windows 上是……」；通用处写「系统临时目录」 |
| `~/.claude/skills/skill-upper/` | 只有装了 `/skill-upper` 才有 | 写成必需依赖；先找现成的，找不到再问用户要不要帮装，默认装全局 `~/.claude/skills/skill-upper/`、不进项目目录，不退回公网文档 |
| `skill-up` 命令 | 用户可能没装，或装的是旧版 | 顶部写明：先跑 `skill-up --version`；不是 v0.14.0 就把文档当历史版本用、产出标「待确认」（逐条重核是维护者的事） |

前两条是「证据路径」，不是操作步骤。结论保留，路径去掉——用户不需要看开发机上的跑测目录，也不会去点它。

#### 4.2.4 装插件的用户那边：权限与依赖

**先确认一处，不算问题**：`/skill-upper` 按插件方式安装的落点就是 `~/.claude/skills/skill-upper/`，这个路径不改。`/skill-upper` 是必需依赖：先找现成的，找不到再问用户要不要帮装，默认装全局 `~/.claude/skills/skill-upper/`、不进项目目录，不退回公网文档。下面的四处才是要改的。

| 问题 | 位置 | 为什么装插件的用户会撞上 | 处理 |
|:---|:---|:---|:---|
| 回写 `usage-notes.md` 的指令指向只读的安装副本 | `SKILL.md:206`；`usage-notes.md` 的「落成时撞见的新折扣往哪儿写」整节；技能 `README.md:143` 已经写明「装机上那份是只读的」 | 插件装到使用者机器上的是按版本分的目录，升级会换一份，安装份只读。模型照 `SKILL.md` 做，会去改一个改不动、改了也会丢的文件 | 按 4.2.5 的使用者／维护者分界处理：`SKILL.md` 不再让模型回写，只让模型把偏离写进第七份的「说明」；回写、重核、版本更新的流程移到 `plugin/` 外的维护者文档。`usage-notes.md` 只留顶部版本行与使用者自查，不出现维护字样 |
| 「换版本之后怎么重核」整节是维护者流程，使用者那边没有自动的版本提醒 | `usage-notes.md:111` 到 `:125`；技能 `README.md:140`；`SKILL.md:178`、`:267` | 这一节让读者按出处重核、改文档、换版本号；插件用户没有源码、没有 `checks/`，读到这里就断了。另一头，模型读 `usage-notes.md` 时没有「先对版本」的指令，旧的结论会被当成事实 | 整节移到维护者文档；`usage-notes.md` 只在顶部留一句使用者自查（跑 `skill-up --version` 与顶部版本行比；不一致就把本文当历史版本看，产出里标「待确认」），不再留这一节。同时在 `SKILL.md` 读 usage-notes 的两处（`:178`、`:267`）加一句：先跑 `skill-up --version`，与顶部版本行不一致时，那几条标「待确认」，别当事实写 |
| 第一节只写了 `claude_code` 引擎，没写明支持范围 | `usage-notes.md:9` 到 `:23`、`:18`、`:40` | 本技能目前只支持 Claude Code（`engine.name: claude_code`）；第一节讲的命令行、钩子关闭、`CLAUDE.md` 常驻上下文、`--resume` 都是这一种引擎的行为。文档没写明，使用者会以为换 Codex、OpenCode 等引擎也照这套走 | 第一节开头写明「本技能目前只支持 Claude Code（`engine.name: claude_code`）；其他引擎不在支持范围内」。正文里「被测那边是 Claude Code」的两处补「（`claude_code` 引擎）」。不写其他引擎的适用范围，也不写「换引擎怎么办」——目前不支持 |
| 三个脚本要 Python 3，技能没写清跑不起来怎么办；也不该每次预检 | `SKILL.md:118`、`:196`、`:279`；技能 `README.md:155` | `check_docs.py` 是交付前的必跑项；用户机器上可能只有 `python3`，也可能没有 Python。现在的说明只讲了 `python` 与 `python3` 的写法，没讲跑不起来时怎么办 | **不单设「前置条件」一节**：那会引着模型在每一步开头先检查，正常能跑的一次流程也会停下。做法只写进「异常处理」表的「环境」两行——报找不到 `python`／`python3`，依次试 `python3`、`python`、`py -3`（Windows）；`python` 一跑就报语法错（多半指到了 Python 2）也照此改试；都跑不起来才告诉用户装 Python 3，装好继续，不跳过自检。`SKILL.md:279` 保持原样（只讲命令行怎么写，不是检查步骤）；`README.md:155` 补「要 Python 3」。 |

**查过但不改的两处**：

- `references/文档模板.md:347` 的 `tests/plain-language/`、`references/文档示例.md` 里的 `tests/login/` 与 `evals/login/`：都是示例表里的落点，不是证据路径；模板自己写着「上面的号只是示例，换一套产出就是另一批号」，读者不会把它们当成自己机器上该有的目录。
- `skill-up/README.md:18` 的「插件整体的许可见插件仓库的根」：插件目录里确实没有 `LICENSE`，但许可见仓库根是常规写法；这一轮不动。要改的话是把根目录的 `LICENSE` 复制一份到 `plugin/` 下，那是打包的事，不在这份设计里。

#### 4.2.5 使用者与维护者的权限边界

**维护者 = 本工程（仓库）下的作者；使用者 = 安装后的目录（插件分发出去的那份技能目录）。** 只有本技能的作者能维护。插件装到使用者机器上之后，技能目录是只读的，使用者只能使用，不能改技能文件，也不做回写、重核、版本号更新。使用者能改的只有自己的产出（六份通用稿加按需的第七份）——那是使用的一部分，不是维护技能。维护者改的只在本仓库里：`plugin/skills/test-case-design/`、`checks/`、`docs/maintainers/`。

| 角色 | 是谁 | 能做什么 | 不能做什么 |
|:---|:---|:---|:---|
| 使用者 | 装插件的人，拿到的是安装后的目录 | 读技能（含两份 `README.md`）、产出六份与第七份、改自己的产出、跑 `skill-up`、按 `usage-notes.md` 顶部的版本行判断这份说明还对不对 | 改技能文件（安装份只读）、回写 `usage-notes.md`、重核条目、更新版本号、维护文件地图 |
| 维护者 | 本工程（仓库）下的作者 | 改 `plugin/skills/test-case-design/` 下的文件、跑 `checks/`、按核验索引重核、回写 `usage-notes.md`、更新版本号、维护文件地图 | 不要求使用者做维护动作；不把维护流程写进 `plugin/` |

落在文档上：

- **`plugin/` 里不出现维护字样。** 「维护者」「回写」「重核」「版本更新」「核验索引」「文件地图」「怎么更新」都移到 `plugin/` 外的维护者文档 `docs/maintainers/test-case-design.md`；这份文档不随插件发出。
- **两份 `README.md` 都是使用者文档，且没有维护字样。** 技能根 `README.md` 与 `references/评测方案/skill-up/README.md` 的读者都是装插件的人；它们只写「是什么、给什么、产出什么、依赖什么、文件结构、脚本脾气」。文件地图、回写、重核、版本更新只写在 `docs/maintainers/test-case-design.md`。
- **`SKILL.md` 不再让模型回写 `usage-notes.md`。** 模型只把落成时撞见的偏离写进第七份方案节的「说明」；`SKILL.md` 里不出现「回写」「维护者」「维护文档」这类字样。
- **`usage-notes.md` 顶部不加维护说明。** 不写「这份文档由维护者更新；使用者只读」，也不写「维护者」「回写」「重核」。文末不留「已核过」清单、不留「换版本之后怎么重核」、不留「落成时撞见的新折扣往哪儿写」；使用者那一侧只留顶部版本行与一句自查（与 `skill-up --version` 不一致时按历史版本用、产出标「待确认」）。
- **技能根目录的 `README.md:123` 到 `:147` 的维护内容搬走**：「想改什么 → 动哪个文件」表、`usage-notes.md` 回填说明、文件改名与主流程表的维护经验，都移到 `docs/maintainers/test-case-design.md`；`README.md` 只留使用说明与文件结构树（树里 `skill-up/README.md` 那行的「怎么更新」删掉）。`SKILL.md` 那边只留「待确认的不写成事实」。
- **`plugin/` 里的文件不写 `docs/maintainers/` 这个路径，也不留「维护者看某处」的指路**——那对使用者不存在，维护者文档由维护者在本仓库里看。

#### 4.2.6 逐处清点：`plugin/` 里哪些话是维护者说的

按「装插件的使用者」扫了一遍，下面这些位置写的是维护动作（回写、重核、更新版本、维护文件地图），不是使用说明。扫下来 16 处，分四块：`usage-notes.md` 6 处、技能 `README.md` 6 处、`skill-up/README.md` 3 处、`SKILL.md` 1 处。逐项搬走或改写；`plugin/` 里只留使用者做得到的事。**这一轮不新增任何维护说明**：原先想加的「这份文档由维护者更新；使用者只读」不再加，`usage-notes.md` 与 `skill-up/README.md` 顶部都不出现维护字样。

| 位置 | 现在写的是什么 | 为什么不是使用者的事 | 处理 |
|:---|:---|:---|:---|
| `usage-notes.md:5` | 版本行后面写「第一到三节照上游源码写、每条注了出处；换版本之后要重核一遍」 | 让读者回源码重核、改这份文档；使用者没有源码，也改不动安装份 | 顶部版本行只留 `**对着的版本：skill-up v0.14.0（2026-10-20）**`；换版本的自查改成一句使用者能做的（对 `skill-up --version`，不一致按历史版本用、产出标「待确认」）；逐条重核移到维护者文档 |
| `usage-notes.md:62`、`:80` | 「这一节照文档站 `windows.md` 写的，不是从源码核的」「那几节是照上游源码读出来的」 | 记录维护者当时怎么写的、出处在哪 | 删掉；正文只留行为与实测标记 |
| `usage-notes.md:66` | 第五节说那几条「出自上游文档站那两份 guide」 | 引公网文档，且是维护者出处 | 删掉；`--workspace`、`--no-delete` 用 `run --help` 核，其余跑一次 |
| `usage-notes.md:100-109` | 整节「落成时撞见的新折扣往哪儿写」：写回对应节、补「已核过」清单、只有实测过的才写成事实 | 让落成的人改技能文档；使用者改不动，也不该改 | 整节移到维护者文档；`SKILL.md` 只让模型把偏离写进第七份「说明」 |
| `usage-notes.md:111-117` | 整节「换版本之后怎么重核」：按出处重看、改这一份、换版本号、同步 README | 维护者流程 | 整节移到维护者文档；`usage-notes.md` 不再有这一节 |
| `usage-notes.md:119-125` | 「已在 `v0.12.0` 上核过…」「2026-10-02 又核过三处…」那几段 | 维护者的核验台账 | 整块移到维护者文档的「核验索引」；`usage-notes.md` 里不留——使用者只需要知道整体对着哪个版本，不需要知道每条怎么核 |
| 技能 `README.md:123` | 「改做法细节不用回头改它…拿不准就把你改掉的说法在 README 里搜一遍」 | 教读者改技能文档 | 移到 `docs/maintainers/test-case-design.md` |
| 技能 `README.md:125-141` | 「想改什么 → 动哪个文件」表 | 维护者文件地图 | 同上；`README.md` 只留文件结构树 |
| 技能 `README.md:140` | 「前几节把上游源码读出来的结论重述了一遍…改完对着原处核一遍」 | 出处记录 + 重核 | 改成「本技能自己写的实际使用说明；对着的版本看它顶部」；删掉重核 |
| 技能 `README.md:143` | 「跑过一轮之后回来把实测结果补进那一份…回填的活是维护技能的人做的」 | 回写流程 | 移到维护者文档；`README.md` 只留「标了『待确认』的条目按待确认处理，不自行补写」 |
| 技能 `README.md:145` | 「改文件名时两种都要一起改…拿文件名全文搜一遍」 | 改文件名的维护动作 | 移到维护者文档 |
| 技能 `README.md:147` | 「主流程表『读哪份文件』一栏要列全（2026-10-02 实测）…」 | 写技能时的维护经验 | 移到维护者文档 |
| `skill-up/README.md:12` | 讲上游文档站那两份手册、哪几节照源码/文档站写的 | 公网出处 + 维护者写法记录 | 改成「字段细节以 `/skill-upper` 的 `references/` 为准」；删掉源码/文档站说法 |
| `skill-up/README.md:14` | URL、commit、「上游没有发布 tag」「两个号各走各的」 | 公网出处 + 版本维护细节 | 只留 `skill-up v0.14.0（2026-10-20）`；删 URL、commit |
| `skill-up/README.md:16` | 「怎么更新」整段：照源码/文档站重核、改两处版本号 | 维护者流程 | 整段移走；这份 README 不写怎么更新 |
| `SKILL.md:206` | 「usage-notes 里没有的折扣，一并回写进 usage-notes…补一笔」 | 让模型改只读安装份 | 删掉；只写第七份「说明」 |

**不搬的三类**（它们看着像维护，其实是使用）：

- **写产出前核对字段名**：`SKILL.md:192`、`references/文档模板.md:325` 的「照 `/skill-upper` 的 `references/` 核过再写」——核对的是 `/skill-upper` 的文档，不是改本技能。`SKILL.md:192` 的措辞改成「逐条核对（核对的是字段名，不是核对这份文档的版本）」，免得与维护动作混在一起。
- **用户改自己的产出**：技能 `README.md:57`、`references/文档模板.md:275`、`references/文档示例.md:21` 的「可以直接改」——改的是用户自己的决策依据，不是技能文件。
- **按 `usage-notes.md` 标「待确认」**：`SKILL.md:178`、`:267`、`references/文档模板.md:417`——这是读文档时的取材规矩，不是回写。
- **脚本脾气里的实现约束**：`README.md:157`、`:159`、`:161` 讲的是脚本按哪份来源判、哪些目录跳过、为什么写死；读者据此知道检查会报什么，不是被要求去改脚本。保留，但把「所以改那张表，脚本跟着变」改成「那张表改了，脚本跟着变」，把「这份判定不许在 `issue_ids.py` 里另写一份」改成「这份判定只在 `check_docs.py` 里有一份」——描述行为，不发维护指令。

**配套的使用者侧改动**：`SKILL.md:178`、`:267` 加「先跑 `skill-up --version`，与顶部版本行不一致就标『待确认』」。这一处不属于维护动作：让使用者知道哪些话不能当事实用。Python 3 不单设一节，跑不起来怎么修写进「异常处理」表（见 4.2.4）。

### 4.3 正文逐节怎么改

| 位置 | 改法 |
|:---|:---|
| 顶部版本行 | 只留 `**对着的版本：skill-up v0.14.0（2026-10-20）**`（使用者自查读这行）；紧跟的那段改成：结论来源只有 `/skill-upper` 的参考文档与实跑，不引源码、不引公网文档与 GitHub；换版本后只做一句使用者自查（对 `skill-up --version`，不一致按历史版本用、产出标「待确认」），逐条重核在维护者文档里。删掉源码 commit、「上游没有发布 tag」、「注了出处（源码文件与行号）」与「换版本之后要重核一遍，见文末」 |
| 第一节 | 删掉命令行拼法的源码引用；「权限全开」改引 `/skill-upper` 的 `eval-yaml.md` 的 `engine.kwargs` 段（`bypass_sandbox` 那行：`claude_code` 已用 `--permission-mode=bypassPermissions`）；「传不了额外参数」也按 `engine.kwargs` 段写——`engine.kwargs` 只认各引擎列出的键，`claude_code` 只有 `bypass_sandbox` 且是空操作，`--append-system-prompt` 这类接不上去；「钩子不生效」走探针跑测 |
| 第二节 | 删掉 `UploadDir` 这个内部名字，只写「铺夹具连权限位一起带」这一行为；其余实测条目保留 |
| 第三节 | 删掉 `skill.go:60`；「装技能跳过 `evals/`」走探针跑测；「`skills` 只能配 eval 层」「装进去不等于会唤起」保留（前者用 `validate` 核，后者原有实测） |
| 第四节 | 内容按新依据重写：`/skill-upper` 的 `install.md` 里那句「macOS and Linux only」管的是它自己的安装脚本；其余 Windows 行为（`SKILL_UP_BASH`、`.sh`／`.ps1`／`.cmd` 判官分派、`setup_steps` 走 bash、WSL 的 bash 被跳过）用本机实跑核。核不出来又不影响第七份写法的删掉，影响写法的标「待确认」；不再引公网 `windows.md` |
| 第五节 | 按 4.1 与 4.3.1 改两条、补五条；`--workspace`、`--no-delete` 用 `skill-up run --help` 核，`judge.context` 与并发语义跑一次核；不再引公网 `cli-reference.md`、`writing-evals.md` |
| 第六节 | 删掉 `evaluator.go` 那组行号；「`setup_steps` 顺序在夹具之前」走探针跑测；「批次级、每条各跑一遍」保留原有实测 |
| 第七节 | 删掉 `validator.go:130` 与 `schema.go:310`；两条结论都保留，依据改成 `validate` 的实跑（便宜，当场能核） |
| §「落成时撞见的新折扣往哪儿写」 | 整节移到 `docs/maintainers/test-case-design.md`；`usage-notes.md` 里不留这一节，也不留「回写」「维护者」字样 |
| 文末「换版本之后怎么重核」 | **整节删掉**；使用者那一侧只留顶部版本行与一句自查（跑 `skill-up --version` 与顶部版本行比，不一致就把本文当历史版本、产出标「待确认」）。维护者的逐条重核、版本号更新与「照 `windows.md`、`cli-reference.md`、`writing-evals.md` 重核」那几句一起移到 `docs/maintainers/test-case-design.md` 的 skill-up 一节 |
| 文末「已核过」清单 | **整块移走**，不放 `usage-notes.md`；到维护者文档里做成「核验索引」表：`条目 \| 核验方式 \| 上次核验`，旧的实测记录按日期并进「上次核验」一列，不丢历史。这张表只给维护者重核用，不随插件发出 |
| 第一节开头 | 写明「本技能目前只支持 Claude Code（`engine.name: claude_code`）；其他引擎不在支持范围内」；正文两处「被测那边是 Claude Code」补引擎限定 |
| `usage-notes.md` 顶部 | 不加维护说明，不出现「维护者」「回写」「重核」；只留版本行与使用者自查 |
| `SKILL.md` 的「读哪份文件」「只出实施方案那一份」「只做落成」 | `/skill-upper` 的路径按 `~/.claude/skills/skill-upper/` 判断（已确认）；先找这个路径，找不到再试 `skill-up --help`／`validate`，都没有才问用户要不要帮装，默认装全局 `~/.claude/skills/skill-upper/`、不进项目目录，不退回公网文档。回写那句删掉，只留「偏离写进第七份的说明」，不出现「维护者」「回写」 |
| `SKILL.md:178`、`:267` 读 usage-notes 的两处 | 加一句：先跑 `skill-up --version`，与顶部版本行不一致时，那几条标「待确认」，别当事实写 |
| 技能 `README.md`、同目录 `skill-up/README.md` 与 `references/文档模板.md` | 路径按 `~/.claude/skills/skill-upper/` 判断，先找现成的，找不到再问用户要不要帮装，默认装全局 `~/.claude/skills/skill-upper/`、不进项目目录；维护内容与文件地图移到 `docs/maintainers/test-case-design.md`，两份 README 只留使用说明；模板里那几处「照 `/skill-upper` 核对字段名再写」保留 |
| 技能根目录 `README.md:123` 到 `:147` | 维护内容搬走：「想改什么 → 动哪个文件」表、`usage-notes.md` 回填说明、文件改名与主流程表的维护经验，移到 `docs/maintainers/test-case-design.md`；`README.md` 只留使用说明与文件结构树（树里 `skill-up/README.md` 那行的「怎么更新」删掉；标题「文件结构：哪件事归哪个文件管」改成「文件结构」；`README.md:121` 的「改一门碰不到别的」改成「互不影响」） |
| 技能根目录 `README.md:157`、`:159` | 把「所以改那张表，脚本跟着变」改成「那张表改了，脚本跟着变」，把「这份判定不许在 `issue_ids.py` 里另写一份」改成「这份判定只在 `check_docs.py` 里有一份」——描述行为，不发维护指令 |
| 同目录 `skill-up/README.md` 的「怎么更新」 | 整段移到维护者文档；这份 README 不写维护者流程，只留项目名、锁定版本、依赖说明 |
| `SKILL.md:192` | 措辞改成「逐条核对（核对的是字段名，不是核对这份文档的版本）」，与维护动作分开 |
| `SKILL.md` 新增「异常处理」一节（放在「管到哪为止」之后、「主流程」之前） | 按 4.10 的表汇总环境、依赖、输入、脚本四类异常：先自动尝试，修不好才告诉用户；写清「缺测试依据/风险信息照旧只问缺的那几样」「退 3 不是错」「不预检」。**不另设「前置条件」一节**：Python 3 跑不起来时的处理在这张表的「环境」两行里 |
| 技能根目录 `README.md:155` | 「不依赖任何第三方库」改成「三个脚本要 Python 3，不依赖任何第三方库；命令里的 `python` 按机器上的写法来，只装了 Python 3 就写 `python3`」 |
| 新增 `docs/maintainers/test-case-design.md`（`plugin/` 外） | 独立一份长期维护文档，结构见 4.9：谁能维护、文件地图、skill-up 两份文档的回写/重核/版本更新/核验索引、`checks/` 与插件版本号规则。不随插件发出 |

### 4.3.1 第五节补的五条，各写到什么程度

只写「写第七份时怎么用」，`/skill-upper` 文档已经展开的细节只给文件名与段落名。

| 条目 | 写什么 | 依据 |
|:---|:---|:---|
| `judge.engine` | 与 `judge.model` 二选一、不能同时写；要 `name`、`model.provider`、`model.name`；不继承被测 agent 的 model、kwargs、version、连接与凭据 | `/skill-upper` 的 `judge-types.md` 的 `judge.engine` 段、`eval-yaml.md` 同段 |
| `judges` 数组 | 一次 agent 执行、多个判官按顺序判；共用同一个 runtime 与文件系统，前一个写的文件后面的看得见；每个 Agent 判官各起一个新会话；`expect` 失败时全部跳过；全部通过才算用例通过。case 级与 eval 级的覆盖关系、能不能同时写 `judge` 与 `judges`，各跑一次 `validate` 核；核不出来就删掉这两句 | `/skill-upper` 的 `judge-types.md` 的 `judges` 段；覆盖关系与互斥用 `skill-up validate` 实跑 |
| `user_simulator` | `input.turns[].respond` 要配 `user_simulator.scenario`；eval 层配 `provider`、`protocol`、`model`；需要能 resume 会话的引擎；轮数上限走 `cases.defaults.max_turns` 或 `constraints.max_turns` | `/skill-upper` 的 `eval-yaml.md` 的 `user_simulator` 段、`case-yaml.md` 的模拟用户回话段 |
| MCP 工具名 | `tool_called`、`tool_called_in_turn`、`tool_not_called_in_turn` 的 `name` 写法照 `/skill-upper` 的例子（`judge-types.md` 里是 `name: "github::create_pull_request"`，`github` 是 `mcp.servers` 里的 `name`）；跑一条 MCP 用例确认转录里的工具名与这个写法对得上，对不上就按实跑结果改并标「待确认」 | `/skill-upper` 的 `judge-types.md` 的 `tool_called` 例子、`case-yaml.md` 的 `tool_called_in_turn` 例子；一次实跑 |
| v0.14.0 评分口径 | `expect` 门控失败时，配置的断言记 `skipped`、不得分；同一批配置在 0.12 与 0.14 上的 benchmark 分数不可直接比——这半句 0.12 上没实测，核不出来就删掉 | 实跑：同一份 `expect` 必失败的配置跑一次，看 `result.json` 里那条断言的状态（2026-11-03 实测，v0.14.0） |

### 4.4 核验索引（放维护者文档，不随插件发出）

`usage-notes.md` 里不再有「已核过」清单，也不放核验方式——那是维护动作。整张表搬到 `docs/maintainers/test-case-design.md`，只有维护者用。每条「实测」结论配一行，第三列记版本与日期。核验方式只用 CLI：

| 条目 | 核验方式 | 上次核验 |
|:---|:---|:---|
| 路径退让与 `falling back` 警告 | 拿一份上方 10 层内没有 `SKILL.md` 的配置跑 `skill-up validate`，看警告 | 2026-11-03（v0.14.0） |
| 多轮只收 `user` 角色 | 拿一份 `role: assistant` 的用例跑 `skill-up validate`，看驳回 | 2026-11-03（v0.14.0） |
| `judge.model` / `judge.engine` 二选一与互斥 | 两种写法各跑一次 `skill-up validate`，看通过／驳回 | 2026-11-03（v0.14.0） |
| `report.formats` 不写就不出 HTML | 跑一条用例，看输出目录里有没有 `report.html` | 原有记录 |
| 钩子不生效、装技能跳过 `evals/`、`setup_steps` 与夹具次序 | 跑 `.tmp/skill-up-probe/` 那一批（`type: none`、`--no-delete`），看工作区里三样标记文件 | 2026-11-03（v0.14.0） |
| `--workspace`、`--no-delete`、`judge.context`、评分口径 | `--workspace` 与 `--no-delete` 看 `skill-up run --help`；`judge.context` 与评分口径各跑一条用例，看 `judge/context` 与 `result.json` | 2026-11-03（v0.14.0） |
| 其余已有实测条目 | 保留原来的核验方式，改成一句话，不写源码位置 | 保留原来的日期与版本 |

这张表里的核验方式都是维护者动作，不写进 `plugin/`。使用者那一侧只有 `usage-notes.md` 顶部的版本行与一句自查。

### 4.5 同目录 `README.md`

这份 `README.md` 的读者是使用者：只写项目名、锁定版本、依赖说明、字段细节去哪儿查；维护者怎么更新、怎么重核，不在这里。

- 「出处」那段：删掉 commit 与「没有发布 tag」，只留项目名与锁定版本 `v0.14.0（2026-10-20）`；URL 整段删掉——使用者那边不依赖公网。
- 「上游那两份手册」那句：整句删掉，改成「字段细节以 `/skill-upper` 的 `references/` 为准」；不写 `docs/zh/guide/` 路径，也不写公网 URL。
- 「怎么更新」那段：**整段删掉**；维护者的逐条重核与版本号更新移到 `docs/maintainers/test-case-design.md` 的 skill-up 一节。这份 README 不写维护者流程。
- 补一句依赖说明：字段细节以 `/skill-upper` 的 `references/` 为准；按插件方式安装的落点就是 `~/.claude/skills/skill-upper/`；先找现成的，找不到再问用户要不要帮装，默认装全局 `~/.claude/skills/skill-upper/`、不进项目目录，不退回公网文档，也不要去找本机的 skill-up 克隆。
- 顶部不加维护说明，不出现「维护者」「回写」「重核」；版本不一致时只写使用者能做的那一句：把这份当历史版本用，产出标「待确认」。
- 「落成时撞见的新折扣往哪儿写」那一节在 `usage-notes.md` 里，不在这份 README；整节移到 `docs/maintainers/test-case-design.md`（`plugin/` 外）的 skill-up 一节，这份 README 只留使用说明。

技能根目录的 `README.md:123` 到 `:147` 那几块维护内容也在这一轮搬走，见 4.2.6 与 4.3。

### 4.6 版本自查（使用者侧）

不写在 `checks/` 里：维护者自己发起升级，版本对不对他心里有数；自动比对只会在升级后红一次，提醒的还是他刚做过的事。使用者那边才需要一句明确的提法，写进三处文档：

- `usage-notes.md` 顶部版本行下面：读这份文档前跑一次 `skill-up --version`；与版本行一致就照用；不一致就把本文当历史版本看，涉及运行时行为的结论在产出里标「待确认」。
- `SKILL.md` 读 `usage-notes.md` 的两处：同样先跑 `skill-up --version`，不一致时那几条标「待确认」，别当事实写。
- 同目录 `skill-up/README.md`：锁定版本一段写同样的话。

`skill-up` 没装时，**第七份不写**：先停下，问用户要不要帮忙安装。用户同意就**默认按全局（用户级）装**：`skill-up` 是命令行工具，装到用户级可执行路径，不装进项目目录；`/skill-upper` 是技能，装到全局技能目录 `~/.claude/skills/skill-upper/`。具体安装命令按机器上可用的方式来（包管理器、Go 安装或用户给的安装包）。装完跑 `skill-up --version` 确认，再继续；用户不装或装不上，终止第七份，只保留六份通用稿。写通用稿不受影响。

不新增脚本：比较是一条命令加一行文本，模型读文档时直接做；多一个脚本就多一个要 Python 的失败点。

### 4.7 版本号

改动落在 `plugin/skills/test-case-design/` 与 `docs/maintainers/` 下。`plugin/` 有实际变动，按仓库规矩抬版本号：`plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 一起从 `1.29.1` 抬到 `1.29.2`（对原有内容的修改，抬最后一位）。`docs/maintainers/test-case-design.md` 是新增的独立维护者文档（结构见 4.9），在 `plugin/` 外，不随插件发出，也不参与插件版本号的内容判定。

### 4.8 本机 `skill-upper` 的核对

不做替换，只把「一致」这件事验一次：

```bash
for f in SKILL.md references/*.md; do
  diff <(git -C /c/Study/skill-up show v0.14.0:skills/skill-upper/"$f" | tr -d '\r') \
       <(tr -d '\r' < ~/.claude/skills/skill-upper/"$f")
done
```

四个文件（`SKILL.md`、`references/judge-types.md`、`references/eval-yaml.md`、`references/cli.md`）输出都为空，就说明本机副本与锁定的发布版一致。以后改钉 HEAD，再跑一次并按差异同步。

### 4.9 维护者文档：独立一份，长期使用

维护者文档不是这份设计文档的一节，也不是技能 `README.md` 的一节；它是 `docs/maintainers/test-case-design.md` 这一份独立文件，放在 `plugin/` 外，随仓库走、不随插件发出。两份 `README.md`（技能根与 `skill-up/` 下）的读者都是使用者；维护者文档是唯一一份维护者入口。

它和这份设计文档的分工：

- **这份设计文档**：一次性的评审材料，说明这次改什么、为什么改、怎么验收。
- **维护者文档**：长期放在仓库里的操作入口，下一次升级 skill-up、回写实测、抬插件版本时照它做。

内容按五块排：

1. **谁能维护**：维护者 = 本工程下的作者；使用者 = 安装后的目录；安装份只读；使用者能改的只有自己的产出。
2. **文件地图**：从技能 `README.md:123` 到 `:147` 搬来的「想改什么 → 动哪个文件」表，这里是这张表的唯一位置；README 复述别处事实时要跟着改；文件改名要同时改 Markdown 链接与反引号路径；主流程表「读哪份文件」一栏要列全。
3. **skill-up 两份文档**：来源只用 `/skill-upper` 的 `references/` 与实跑；落成时撞见的新折扣怎么回写；换版本之后怎么逐条重核；核验索引（条目、核验方式、上次核验）。
4. **检查与版本号**：`bash checks/verify.sh test-case-design`；升级 skill-up 后按核验索引重核并改 `usage-notes.md` 顶部版本行（版本自查在使用者侧，`checks/` 里不做比对）；插件 `plugin.json` 与 `marketplace.json` 同步抬版本。
5. **不随插件发出**：`docs/` 不在 `plugin/` 下；技能目录里的文件不写这个路径；使用者看不到它，也不需要。

不拆成多份的理由：这一份只服务 `test-case-design` 一个技能；内容够短，维护者查一处就够。将来别的技能也要维护者文档，就按 `docs/maintainers/<技能名>.md` 各起一份，不混在一起。

`plugin/` 里被搬走的维护说明全部由这一份接手：版本更新、回写、重核、核验索引、文件地图；`plugin/` 不再出现「维护者」「回写」「重核」「怎么更新」这些字样。

### 4.10 `SKILL.md` 的异常处理章节

放在「管到哪为止」之后、「主流程」之前，标题「异常处理」。先写总则，再一张表。

总则：

- **能自己修的先自己修，不问用户。**
- **同一处修过一轮还是失败，才告诉用户**；说清三样：报错原文、已经试过的修法、还需要用户做什么。
- **异常处理只在出错时走**，不是每一步开头预检。
- **缺测试依据、缺风险信息、用户还没说产出放哪儿是正常开工输入**，照旧只问缺的那几样；不要为了不问而编。用户给了路径但目录还不存在，不在此列——按表里「产出目录不存在」先建。
- **不删用户文件、不覆盖没读过的产出、不擅自换产出目录。**
- **外部依赖不自动安装**：`/skill-upper`、Python 3、`skill-up` 这类要装到用户机器上的东西，先找现成的、用已有命令兜底，不擅自装；找不到时告诉用户缺什么。**写第七份缺 `skill-up` 是硬停**：问用户要不要帮装，同意才装，默认装全局（用户级）、不进项目目录（`/skill-upper` 装到 `~/.claude/skills/skill-upper/`），装好 `skill-up --version` 确认后再继续；不装或装不上就终止第七份。

| 类别 | 撞见什么 | 先自动怎么修 | 修不好才告诉用户 |
|:---|:---|:---|:---|
| 环境 | 命令报找不到 `python`／`python3` | 依次试 `python3`、`python`、`py -3`（Windows）；哪个能跑用哪个 | 都跑不起来：请装 Python 3，装好告诉我 |
| 环境 | `python` 一跑就报语法错 | 多半是 `python` 指到了 Python 2；改试 `python3`、`py -3` | 同上 |
| 环境 | 产出目录不存在 | 建目录，包括需要的上级目录 | 建不了：给路径与报错，请换有写权限的目录 |
| 环境 | 产出目录不可写，或路径被同名文件占着 | 不可写先试在目录里写临时文件；被文件占着不删，改试同级另一个目录并说明 | 都不行：给路径与报错，请换目录或处理占位文件 |
| 环境 | 技能自己的 `references/` 文件缺失 | 先按文件名在技能目录里找；找不到就用同一份文档的其他节兜底 | 还是缺：说明安装可能不完整，请重装这个技能 |
| 依赖 | `/skill-upper` 没装 | 先找 `~/.claude/skills/skill-upper/`；再看 `skill-up` 命令在不在，用 `--help`／`validate` 核字段名 | 都没有：问用户要不要帮装，默认装全局 `~/.claude/skills/skill-upper/`、不进项目目录；装好告诉我；不要照印象写字段 |
| 依赖 | `/skill-upper` 的某个参考文件缺失 | 先在同目录找同主题的另一份；再用 `skill-up --help`／`validate` 核 | 核不出来：说明缺哪份文件、哪条字段，请重装 `/skill-upper` |
| 依赖 | `skill-up` 命令不在，`--version` 跑不了 | 先找 `~/.claude/skills/skill-upper/` 与 `command -v skill-up`；只写通用稿就照常写 | **写第七份或要跑测：停下**，问用户要不要帮装；同意就默认装全局（用户级）、不进项目目录（`/skill-upper` 装到 `~/.claude/skills/skill-upper/`），装完 `--version` 确认后继续；不装或装不上，**终止第七份** |
| 依赖 | `usage-notes.md` 顶部版本与 `skill-up --version` 对不上 | 把 `usage-notes.md` 当历史版本用；能跑 `skill-up` 核的当场核；拿不准的标「待确认」 | 核不出来又影响写法：把版本与条目告诉用户，让用户决定是否先升级 |
| 输入 | 测试依据的路径找不到或读不了 | 先按相对路径、常见扩展名、项目里同名文件找；还不行看对话里有没有原文 | 找不到：这是开工输入，照旧问用户要；不要编测试依据 |
| 输入 | 测试依据是 URL 且取不到 | 先看本地有没有同一份；没有就看对话里有没有原文 | 都没有：告诉用户取不到，请给本地路径或原文 |
| 输入 | 产出目录里已有旧文档 | 先读旧文档，接着编号与格式往下写；不推倒重来 | 旧文档读不懂或与当前模板冲突：把冲突处告诉用户 |
| 脚本 | `issue_ids.py` 报错 | 照报错改产出目录或参数，重跑；编号冲突照它打出来的号改 | 改不动：给命令、报错原文、产出目录 |
| 脚本 | `check_docs.py` 报错 | 照报错逐条改产出，改完重跑；`--rules` 打全部规则 | 同一处改过一轮还报：给报错原文与已改的地方 |
| 脚本 | `check_landing.py` 退 1 | 照差异改产出或成品，重跑 | 改不动：给差异清单 |
| 脚本 | `check_landing.py` 退 2 | 查用法与路径；成品路径按模板一条条点出来，重跑 | 还退 2：给命令与报错原文 |
| 脚本 | `check_landing.py` 退 3 | **不是错**：这一批还没落成，跳过 | 不用告诉用户 |
| 脚本 | `check_landing.py` 说某个文件不是 UTF-8、跳过了 | 不当错误；样本文件本来就可能不是 UTF-8 | 如果那正是成品：告诉用户哪份文件，请转成 UTF-8 |
| 脚本 | 脚本抛出 traceback | 先看是不是 Python 版本、路径、编码；改试 `python3`／`py -3`，重跑一次 | 还抛：给完整 traceback、命令、产出目录 |

**这一节不是新的流程步骤**：`SKILL.md` 的主流程照旧，异常处理只在撞见问题时查；不要把它当每一步开头的检查清单。

## 5. 验收判据

1. `grep -nE '\.go:[0-9]|internal/[a-z_]+/'` 扫 `usage-notes.md`，输出为空。
2. `bash checks/verify.sh test-case-design` 全绿。
3. 三份 `evals/*/eval.yaml` 在 0.14.0 下仍 `skill-up validate` 通过。
4. `usage-notes.md` 顶部、`SKILL.md` 读 `usage-notes.md` 的两处、同目录 `skill-up/README.md` 都写明：先跑 `skill-up --version`，与文档里的版本行不一致时把本文当历史版本用、涉及运行时行为的结论标「待确认」；`skill-up` 没装时第七份不写：先问用户要不要帮装，默认全局（用户级）安装、不进项目目录，装好并 `skill-up --version` 确认后才继续；不装或装不上就终止第七份，通用稿不受影响。
5. 随机抽五条正文结论，每条都能在正文里看见依据类别（`/skill-upper` 文档／实测）；实测条目的核验方式在 `docs/maintainers/test-case-design.md` 的核验索引里有对应行。
6. 本机 `skill-upper` 与 v0.14.0 的四个文件按 4.8 跑一遍，输出为空。
7. 第五节那两条改写与 4.3.1 的五条新增都在，且每条都标了依据。
8. `grep -nE '\.go:[0-9]|internal/[a-z_]+/|C:\\Study|runs\\|xlsx/|game-design-xlsx-to-md|\.claude/evals/|evals/(business-term-builder|plain-language|token-counter)|docs/zh/guide|zhcmeng|https?://|CHANGELOG|releases?'` 扫 `usage-notes.md` 与同目录 `README.md`，输出为空。第三节那句「装技能跳过 `evals/` 子树」讲的是被测技能的目录，不算开发机路径。
9. `%TEMP%`、`Program Files` 只允许出现在第四节 Windows 小节，且句子里写明「Windows」；其他小节用「系统临时目录」。
10. 文档顶部写明 `skill-up --version` 的自查方法，并写明 `/skill-upper` 是必需依赖；先找现成的，找不到再问用户要不要帮装，默认装全局 `~/.claude/skills/skill-upper/`、不进项目目录，不退回公网文档。
11. `/skill-upper` 的安装落点按 `~/.claude/skills/skill-upper/` 写；`SKILL.md` 与两份 README 写明先找这个落点，找不到再问用户要不要帮装、默认装全局 `~/.claude/skills/skill-upper/`，不退回公网文档。
12. `SKILL.md` 不再有回写 `usage-notes.md` 的指令，只让模型把偏离写进第七份；`usage-notes.md` 顶部不出现「维护者」「回写」「重核」，只留版本行与一句使用者自查；`usage-notes.md` 里没有「已核过」清单、「换版本之后怎么重核」、「落成时撞见的新折扣往哪儿写」；回写、重核、版本更新、核验索引与文件地图都在 `docs/maintainers/test-case-design.md`，该文件在 `plugin/` 外。
13. `usage-notes.md` 第一节开头写明「本技能目前只支持 Claude Code（`engine.name: claude_code`）；其他引擎不在支持范围内」；正文两处「被测那边是 Claude Code」补了引擎限定。
14. `SKILL.md` 不单设「前置条件」一节；Python 3 跑不起来时的处理写在「异常处理」表的「环境」两行（依次试 `python3`、`python`、`py -3`，都不行才告诉用户装），并写明**不预检**。技能根 `README.md` 的脚本说明写明这三个脚本要 Python 3，以及 `python`/`python3` 按机器写法。
15. `SKILL.md:178`、`:267` 读 `usage-notes.md` 的两处写了「先跑 `skill-up --version`；与顶部版本行不一致时标『待确认』」。
16. `docs/maintainers/test-case-design.md` 存在于 `plugin/` 外，按 4.9 的五块排：谁能维护；文件地图；skill-up 两份文档（含回写、重核、版本更新、核验索引）；`checks/` 与插件版本号；不随插件发出。`plugin/` 下不再有任何维护字样或维护流程。
17. `usage-notes.md` 与同目录 `README.md` 不依赖公网文档站与 GitHub 的 CHANGELOG、release；只在公网文档里有的细节，要么有实测依据，要么标「待确认」，要么已删。
18. `grep -nE '维护|回写|重核|已核过|怎么更新|对着原处核|跑过一轮之后回来|想改什么|改哪个文件'` 扫 `plugin/skills/test-case-design/`，输出为空。`核一遍`、`核过` 不在此列——它们也用于核对产出（`references/文档模板.md:152`）与核对 `/skill-upper` 字段名（`SKILL.md:192`），不属于维护动作。
19. 技能根 `README.md` 与 `skill-up/README.md` 的读者都是使用者：两份里只有使用说明（是什么、给什么、产出什么、依赖什么、文件结构、脚本脾气），没有「维护」「维护者」「回写」「重核」「怎么更新」等字样，也没有「想改什么 → 动哪个文件」表、回填说明、文件改名与主流程表的维护经验；这些都在 `docs/maintainers/test-case-design.md`。技能根 `README.md` 只留使用说明与文件结构树，树里不再有「怎么更新」。
20. 使用者改自己的产出仍被允许：技能 `README.md:57`、`references/文档模板.md:275`、`references/文档示例.md:21` 的「可以直接改」保留，没有被误当成维护动作删掉。
21. `plugin/` 下不出现 `docs/maintainers/` 路径；`docs/maintainers/test-case-design.md` 不在插件安装目录里。
22. `usage-notes.md` 全文不出现「维护」「维护者」「回写」「重核」「已核过」「补进」「改这一份」「更新版本号」；`skill-up/README.md` 不出现「维护」「维护者」「怎么更新」「照源码」「文档站」。
23. `SKILL.md` 在「管到哪为止」之后、「主流程」之前有一节「异常处理」：覆盖环境、依赖、输入、脚本四类；每类写明先自动怎么修、修不好才告诉用户什么；写明「缺测试依据/风险信息照旧只问缺的那几样」「退 3 不是错」「不预检」「外部依赖不自动安装」。

## 6. 不做的事

- 不给 `test-case-design` 新增评测套件。
- 不改 `evals/*/eval.yaml` 与用例配置。
- 不改上游文档，不向上游提 PR。
- 不动其他技能。
- 不保留「行号留着以备查」这种中间状态——要么换成别的依据，要么删。
- 不把维护者文档放进 `plugin/`；`plugin/` 里不出现任何维护字样（维护、维护者、回写、重核、版本更新、文件地图、怎么更新），也不留「维护者看某处」的指路——使用者点不到那个路径，也不需要知道。
- 不把「异常处理」当成每一步开头的预检清单；它只在出错时查。
- 不删使用者改自己产出的说明：决策依据的「可以直接改」、第七份「成品落点」的补表，都是使用，不是维护。
- 不把核验索引留给使用者：使用者只判断「这份说明对着的版本还对不对」，不逐条重核。

## 7. 已知的连带代价

- **探针要花几次真实 agent 跑测**（钩子、装技能跳过 `evals/`、`setup_steps` 次序、`judge.context`、评分口径），可能再加判官调用。这是把源码结论与公网文档结论变成实测结论的最低成本。
- **升级 skill-up 后没有自动提醒**：文档跟没跟上版本，靠维护者按核验索引自己重核；使用者读到的是顶部版本行与自查那一句。这是把检查从 `checks/` 拿掉的代价，换来的是不再维护一段只提醒维护者刚做过的事的代码。
- **少数只有源码才看得见的细节会被删掉**，文档会比现在短一些。删掉的是对「写第七份」没有影响的部分。
- **公网那份资料不再进正文**：文档站与 GitHub 上的 CHANGELOG、release 不引。只在公网文档里有的细节，要么实跑补上，要么标「待确认」，要么删掉；文档会比照公网文档写时少几条。
- **本机 `skill-upper` 这次不用动**：已经与 v0.14.0 一致。这份副本不在仓库里，换机器或重装时按 4.8 再核一次。以后改钉上游 HEAD，才需要同步 HEAD 的改动。
- **这轮会动到 `SKILL.md` 与两份 `README.md`**：4.2.4 那四处里有三处落在模型会直接读到的正文，不只是参考文档；`SKILL.md` 还会多一节——「异常处理」（各类异常先自动修，修不好才告诉用户）；技能根 `README.md` 还会瘦一圈（文件地图、回填说明、改名规矩搬走），并去掉所有维护字样。改的是判断方式、异常处理与回写范围，产出格式不变。
- **`SKILL.md` 会变长**：多出「异常处理」一节，是一张十几行的表。换来的是常见问题先在技能内解决，不再逐个问用户；正常流程不看这张表。
- **多出一份维护者文档**：`docs/maintainers/test-case-design.md` 在 `plugin/` 外，不随插件发出。使用者看不到它，也不需要——回写、重核、版本更新与文件地图本来就只有维护者做得了。
- **使用者那边不再有核验索引与重核方法**：版本不一致时只能按「历史版本」用、产出标「待确认」，不能自己逐条重核。这是有意的：重核是维护者的活，使用者没有源码、没有 `checks/`，也没有写权限。
- **维护者查文件地图要换地方**：技能 `README.md` 不再列「想改什么 → 动哪个文件」，改到 `docs/maintainers/test-case-design.md` 看。仓库里工作的人多一步，装插件的人少一堆做不了的说明。
