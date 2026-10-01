# skill-up 使用要点

**本技能自己写的**，不是上游原文。它收的是用这套方案时要拿捏的几处：**实际跑起来是什么样**、**做不到什么**、**哪里要挑**。配置字段怎么填、命令怎么用不在这里——那在 `/skill-upper` 技能里（它的 `SKILL.md` 与 `references/` 下那几份），**它没写到的几条收在第五节**。

对着的版本：`main @ 7f1ff9b`（2026-09-29）。第一到三节与第六节照上游**源码**写，每条注了出处（源码文件与行号）；第四节照上游文档站的 `docs/zh/guide/windows.md`、第五节照同站那两份 guide 写，没从源码核。第一节里那条 `CLAUDE.md` 是 Claude Code 自己的行为，上游没写它。**换版本之后要重核一遍**，见文末。

## 一、一次运行里，被测那边是怎么起的

每条用例各起一轮会话，命令是这么拼的（`internal/agent/claude_code.go:322`）：

```
claude --settings '{"disableAllHooks":true}' --session-id <id> -p --permission-mode=bypassPermissions
```

三处要留意：

- **钩子一律不生效**（`disableAllHooks` 置了 `true`）。被测技能或项目里挂着钩子，评测时不会跑——通用稿里如果有哪一条要求靠钩子触发，落到这套方案上就跑不了原样。
- **钩子那条道断了，常驻上下文还能走工作区根目录的 `CLAUDE.md`**。被测那边是 Claude Code，它起会话时会读工作区根目录的 `CLAUDE.md`；让 `environment.setup_steps` 在会话起来之前把文本写进去就有了（次序见第六节），不必靠钩子。**这条不是上游的说法，是 Claude Code 自己的行为**——上游只讲到钩子被关掉为止。
- **权限全开**（`--permission-mode=bypassPermissions`）。被测那边不会停下来问权限。

多轮会话用 `--resume <id>` 接着上一轮（`:341`）。

## 二、工作区

- 每条用例各起一个空的临时目录当工作区，跑完删掉；工作区由框架建，不由用例配置指定（要改用现成目录、或者跑完留着看，见第五节那两条 flag）。
- 上一轮留下的东西不进下一轮。
- **工作区不是 git 仓库时，`workspace_diff` 会被静默省掉**：不报错，报告里那一项空着，只在清单里留一行 `workspace_diff: omit`。要拿盘上改动作判据的用例，得让工作区先是 git 仓库，或者换一样判据。

## 三、技能是怎么装进去的

- 技能装到工作区的 `.claude/skills/<技能名>/` 下——**走的是本地技能那条道，不是插件那条**。带插件前缀的唤起名（`/插件名:技能名`）用不了，只能按技能名唤起。
- **装的时候无条件跳过 `evals/` 子树**（`internal/agent/skill.go:60`）：被测技能自己带着评测材料时，那部分不会跟着进工作区。

## 四、Windows

**skill-up 原生支持 Windows**，`skill-up.exe` 直接跑。`/skill-upper` 里那句「macOS and Linux only. Windows is not currently supported」管的是它自己 `install.sh` 那条安装道（只能 bash 跑），不是说整个工具——照那句判，会把环境白改成 WSL2。

能用的：

- **`none` runtime**：命令在宿主机上跑。
- **`opensandbox` runtime**：不受宿主机系统影响，始终在 Linux 沙箱里执行。
- **script judge 按扩展名分派**：`.ps1` → PowerShell、`.cmd`／`.bat` → `cmd.exe`、`.sh` → bash。

`.sh` 判官要一个 bash，找的顺序：`SKILL_UP_BASH` 环境变量 → `PATH` 里的 bash → `C:\Program Files\Git\bin\bash.exe` → `C:\Program Files (x86)\Git\bin\bash.exe`。**WSL 那个 `C:\Windows\System32\bash.exe` 三条都不认，会被跳过**——机器上只有它时，`.sh` 判官起不来；要走 WSL 的得自己把 `SKILL_UP_BASH` 指到非 WSL 的 bash，或者干脆在 WSL 里跑 skill-up。

一个都没找着时退到 `cmd.exe`：`cat`、`>>` 这类写法不成立，命令里的 `%VAR%` 还会被 `cmd.exe` 自己展开。

做不到的：

- **原生 Windows 上跑不了完整的模型**：起真实 agent 那条路要用 bash 引导 Node／nvm。上游的建议是改用 WSL2，或者先把 Node 与命令行工具装好。
- **`.ps1` 判官只在 Windows 目标上支持**：runtime 是 POSIX（比如 opensandbox 的 Linux 沙箱）时只能用 `.sh`。

（这一节是照上游 `docs/zh/guide/windows.md` 写的，不是从源码核的。）

## 五、`/skill-upper` 的参考文档里没写的几条

`/skill-upper` 那几份覆盖了配置字段与命令参数，写第七份要用的它基本都有。下面这几条它没写，出自上游文档站那两份 guide（`cli-reference.md` 与 `writing-evals.md`，不随技能发）——写第七份时要知道有它们。

- **`--workspace <目录>`**：拿宿主机上一个现成目录当工作区用，跑完**不删**。只在 `environment.type: none`、`cases.parallelism: 1`、benchmark 关掉时能用。
- **`--no-delete`**：跑完保留 skill-up 自己建的工作区或容器，便于调试。默认 `false`。与上一条不是一回事：这条留的是 skill-up 建的那个，上一条用的是你自己给的。
- **`judge.context`**：判官拿到哪几样材料由它定，默认 `standard`——`final_message` 内联，`transcript` 与 `workspace_diff` 以文件引用给出；另有 `minimal`（省掉 transcript 与 diff、截断 final_message）。第二节那条「差集被静默省掉」说的就是这个 `workspace_diff`。

第一到三节与第六节的东西它同样没写——那几节是照上游**源码**读出来的，本来就哪份文档都没有；第四节出自上游文档站的 `windows.md`，那一页也不随技能发。

## 六、`environment.setup_steps` 在 `type: none` 下照样跑

上游文档只在容器那两个 runtime 的例子底下写它，但它不是容器专属：`internal/evaluator/evaluator.go:1172` 那个循环没有类型判断（类型判断在 `:1182`，只管装不装 agent）。命令由工作区那个 shell 跑（见第四节），一条退出码非 0 就整条用例报错。

**次序写死**，同一个函数里排下来：`setup_steps` → 装 agent（`none` 下跳过）→ preflight → 装 MCP → 装技能 → **铺夹具**（`:1206`）。夹具排在最末，所以**夹具里放一份同名文件，会把 `setup_steps` 写下的那份盖掉**，反过来不会。要往工作区里放一样东西、又不许它被冲掉，就得算准这条次序；第一节那条常驻上下文的替代道正落在这一条上。

## 换版本之后怎么重核

上面每条都注了出处。上游动过之后，按出处那几处重新看一眼；对不上的就改这一份，改完把顶上钉的版本换成新的，并同步改同目录 `README.md` 里那一行。

第四节没注源码出处，照上游文档站的 `docs/zh/guide/windows.md` 核；第五节照同站的 `cli-reference.md` 与 `writing-evals.md` 核；第一节那条 `CLAUDE.md` 不是上游的说法，照 Claude Code 自己的行为核。
