# skill-up 使用要点

**本技能自己写的**，不是上游原文。它收的是用这套方案时要拿捏的几处：**实际跑起来是什么样**、**做不到什么**、**哪里要挑**。配置字段怎么填、命令怎么用不在这里——那在 `/skill-upper` 技能里（它的 `SKILL.md` 与 `references/` 下那几份），**它没写到的几条收在第五节**。

对着的版本：上游**源码** `main @ 7f1ff9b`（2026-09-29）、机器上装的**发布版** `v0.12.0`（2026-09-18）——上游没有发布 tag，源码按 commit 钉、二进制按发布号钉，两个都写在这儿。第一到三节、第六节与第七节照上游**源码**写，每条注了出处（源码文件与行号）；第四节照上游文档站的 `docs/zh/guide/windows.md`、第五节照同站那两份 guide 写，没从源码核。第一节里那条 `CLAUDE.md` 是 Claude Code 自己的行为，上游没写它。**换版本之后要重核一遍**，见文末。

## 一、一次运行里，被测那边是怎么起的

每条用例各起一轮会话，命令是这么拼的（`internal/agent/claude_code.go:322`）：

```
claude --settings '{"disableAllHooks":true}' --session-id <id> -p --permission-mode=bypassPermissions
```

四处要留意：

- **钩子一律不生效**（`disableAllHooks` 置了 `true`）。被测技能或项目里挂着钩子，评测时不会跑——通用稿里如果有哪一条要求靠钩子触发，落到这套方案上就跑不了原样。
- **钩子那条道断了，常驻上下文还能走工作区根目录的 `CLAUDE.md`**。被测那边是 Claude Code，它起会话时会读工作区根目录的 `CLAUDE.md`；让 `environment.setup_steps` 在会话起来之前把文本写进去就有了（次序见第六节），不必靠钩子。**这条不是上游的说法，是 Claude Code 自己的行为**——上游只讲到钩子被关掉为止。
- **权限全开**（`--permission-mode=bypassPermissions`）。被测那边不会停下来问权限。
- **命令行是拼死的，没有传额外参数的口子**（`buildClaudePrintCmd`，`internal/agent/claude_code.go:321`）：除了会话号、模型与那条指令，拼不出别的参数——`--append-system-prompt` 这类接不上去。要往被测那边多塞一点东西，只能用 `environment.setup_steps` 往工作区里摆（第六节），或者改 `input` 里的消息。
- **要把一段文本变成「会话开头就在那儿」的常驻上下文，道就这么几条**：钩子（上一条说了，一律不生效）；额外参数（上一条说了，接不上去）；`environment.setup_steps` 往工作区根写一份 Claude Code 会读的文件（上一条那条 `CLAUDE.md`，次序见第六节）——**只有这条同时满足「常驻」与「不进当轮消息」**。把文本接在用户消息前面也能让被测那边读到，但它就成了这一条消息里的内容，不再是常驻上下文；判「常驻之下的落笔」那种用例分不出这两者。

多轮会话用 `--resume <id>` 接着上一轮（`:341`）。

## 二、工作区

- 每条用例各起一个空的临时目录当工作区，跑完删掉；工作区由框架建，不由用例配置指定（要改用现成目录、或者跑完留着看，见第五节那两条 flag）。
- 上一轮留下的东西不进下一轮。
- **工作区不是 git 仓库时，`workspace_diff` 会被静默省掉**：不报错，报告里那一项空着，只在清单里留一行 `workspace_diff: omit`。要拿盘上改动作判据的用例，得让工作区先是 git 仓库，或者换一样判据。
- **铺夹具是逐字节写、连源文件的权限位一起带**（`type: none` 那一档，`UploadDir` 保留 mode）。工作树里设成只读的样本，铺进工作区之后还是只读。反过来，**git 不存权限位**（它只存执行位）——重新克隆之后只读属性会丢，跑之前要在工作树里重设一次。

## 三、技能是怎么装进去的

- 技能装到工作区的 `.claude/skills/<技能名>/` 下——**走的是本地技能那条道，不是插件那条**。带插件前缀的唤起名（`/插件名:技能名`）用不了，只能按技能名唤起。
- **装的时候无条件跳过 `evals/` 子树**（`internal/agent/skill.go:60`）：被测技能自己带着评测材料时，那部分不会跟着进工作区。
- **`skills` 只能配在 `eval.yaml` 那一层，一条用例一层没有这个字段**。要「同一批里有的用例装技能、有的不装」，只能拆成两份配置分两次跑。**配错位置不会有提示**：在用例那一层也写一段 `skills`，`validate` 照样报 valid（实测，`v0.12.0`）——多出来的字段是默默丢掉的。

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

第一到三节、第六节与第七节的东西它同样没写——那几节是照上游**源码**读出来的，本来就哪份文档都没有；第四节出自上游文档站的 `windows.md`，那一页也不随技能发。

## 六、`environment.setup_steps` 在 `type: none` 下照样跑

上游文档只在容器那两个 runtime 的例子底下写它，但它不是容器专属：`internal/evaluator/evaluator.go:1172` 那个循环没有类型判断（类型判断在 `:1182`，只管装不装 agent）。命令由工作区那个 shell 跑（见第四节），一条退出码非 0 就整条用例报错。

**次序写死**，同一个函数里排下来：`setup_steps` → 装 agent（`none` 下跳过）→ preflight → 装 MCP → 装技能 → **铺夹具**（`:1206`）。夹具排在最末，所以**夹具里放一份同名文件，会把 `setup_steps` 写下的那份盖掉**，反过来不会。要往工作区里放一样东西、又不许它被冲掉，就得算准这条次序。第一节那条常驻上下文的替代道写的是工作区根目录那份 `CLAUDE.md`——**夹具里就不许放同名的**，放一份会把注入冲掉。

## 七、路径怎么算、消息怎么拼

**相对路径的基准是「技能根」，技能根找不到时会退让一步。** 文档里的规则是「所有相对路径相对 `SKILL.md` 所在目录算」（`/skill-upper` 的 `eval-yaml.md` 也这么写）。实际实现是（`internal/config/loader.go:214` 的 `FindSkillDir`）：从 `eval.yaml` 所在目录起往上找带 `SKILL.md` 的目录，**最多 10 层**（`:17`）；一层都没找着就退到「`eval.yaml` 所在目录的上一层」，并打一条 `SKILL.md not found within 10 levels above …; falling back to …` 的警告（`:52`）。

评测材料和被测技能不在一棵树里时，这条退让每次都走——基准因此是 `eval.yaml` 的上一层，不是技能根。写落成配置的人要按**实际退让到的那一层**算相对路径，别按文档那句理想的算；那条警告是正常产物，不是错。

**多轮只收 `user` 角色。** `input.turns` 的每一条只能是用户消息——校验器写死（`internal/config/validator.go:130`，`role must be "user"`），配置结构里那个字段的注释也标着 `// user`（`internal/config/schema.go:310`）。所以要拿「被测那边自己上一条回答」当输入的用例（让它读到对话历史里它上一轮说过的话），**塞不进去**：只能把那段的全文接在用户消息里，或者多起一轮让它自己先说一遍。前一条是一处保真度折扣，判据要跟着避开「那段话在对话历史里」这件事。

## 换版本之后怎么重核

上面每条都注了出处。上游动过之后，按出处那几处重新看一眼；对不上的就改这一份，改完把顶上钉的版本换成新的，并同步改同目录 `README.md` 里那一行。

**源码那个号和发布那个号会各走各的**——发布不等于 `main` 的头。这一份的结论大多读自源码，所以先看一眼装的是哪个发布版，别当成对得上。

第四节没注源码出处，照上游文档站的 `docs/zh/guide/windows.md` 核；第五节照同站的 `cli-reference.md` 与 `writing-evals.md` 核；第一节那条 `CLAUDE.md` 不是上游的说法，照 Claude Code 自己的行为核。第七节那两处有个便宜的核法：路径退让在任一份**找不到技能根**的配置上跑一遍 `skill-up validate`，屏幕上就会打出那条 `falling back` 的警告；只收 `user` 角色拿一份 `role: assistant` 的用例跑 `validate`，会被当场驳回。

**已经在装着的 `v0.12.0` 上核过三处**：第七节那两处（上面那两个便宜的核法，各跑一次就对上了），以及第三节那条「用例那一层写了 `skills` 也不报错」。其余各条只在源码那一版上读过，还没在二进制上逐条核。
