# skill-up 使用要点

**本技能自己写的**，不是上游原文。它收的是用这套方案时要注意的几处：**实际跑起来是什么样**、**做不到什么**、**哪里要挑**。配置字段怎么填、命令怎么用不在这里——那在 `/skill-upper` 技能里（它的 `SKILL.md` 与 `references/` 下那几份），**它没写到的几条收在第五节**。

**对着的版本：skill-up v0.14.0（2026-10-20）**

下面每一条要么来自 `/skill-upper` 的 `references/`（写文件名与小节名），要么来自 `skill-up` 命令的实跑输出（句末标日期与版本）。不引源码，不引公网文档站，也不引 GitHub 上的变更记录与发布页。

**本技能目前只支持 Claude Code（`engine.name: claude_code`）**；其他引擎不在支持范围内。

读这份文档前先跑一次 `skill-up --version`，与上面那行版本对一下：一致就照用；不一致就把本文当历史版本看，涉及运行时行为的结论在产出里标「待确认」。

## 一、一次运行里，被测那边是怎么起的

每条用例各起一轮会话，命令行是这一条（从会话记录里看得到）：

```
claude --settings '{"disableAllHooks":true}' --session-id <id> -p --permission-mode=bypassPermissions
```

要留意的地方：

- **钩子一律不生效**（`disableAllHooks` 置了 `true`）。探针在工作区里放了 `.claude/settings.json`、挂上 `SessionStart` 钩子去创建 `hook-fired.txt`，跑完没有这个文件（2026-11-04 实测，skill-up v0.14.0）。被测技能或项目里挂着钩子，评测时不会跑——通用稿里如果有哪一条要求靠钩子触发，落到这套方案上就跑不了原样。
- **钩子那条道断了，常驻上下文还能走工作区根目录的 `CLAUDE.md`**。被测那边是 Claude Code（`claude_code` 引擎），它起会话时会读工作区根目录的 `CLAUDE.md`；让 `environment.setup_steps` 在会话起来之前把文本写进去就有了（次序见第六节），不必靠钩子。**这条不是上游的说法，是 Claude Code 自己的行为**——上游只讲到钩子被关掉为止。
- **权限全开**：`claude_code` 引擎已经用 `--permission-mode=bypassPermissions` 起会话（`/skill-upper` 的 `eval-yaml.md` 的 `engine.kwargs` 段），被测那边不会停下来问权限。`engine.kwargs` 里那个 `bypass_sandbox` 对 `claude_code` 是空操作。
- **没有传额外参数的口子**：`engine.kwargs` 只认各引擎列出的键，`claude_code` 只有 `bypass_sandbox`，而且它是空操作（`/skill-upper` 的 `eval-yaml.md` 的 `engine.kwargs` 段）——`--append-system-prompt` 这类接不上去。要往被测那边多塞一点东西，只能用 `environment.setup_steps` 往工作区里摆（第六节），或者改 `input` 里的消息。
- **要把一段文本变成「会话开头就在那儿」的常驻上下文，道就这么几条**：钩子（上一条说了，一律不生效）；额外参数（上一条说了，接不上去）；`environment.setup_steps` 往工作区根写一份 Claude Code 会读的文件（上一条那条 `CLAUDE.md`，次序见第六节）——**只有这条同时满足「常驻」与「不进当轮消息」**。把文本接在用户消息前面也能让被测那边读到，但它就成了这一条消息里的内容，不再是常驻上下文；判「常驻之下的落笔」那种用例分不出这两者。

多轮会话用 `--resume <id>` 接着上一轮。

## 二、工作区

- 每条用例各起一个空的临时目录当工作区，跑完删掉；工作区由框架建，不由用例配置指定（要改用现成目录、或者跑完留着看，见第五节那两条 flag）。
- 上一轮留下的东西不进下一轮。
- **工作区不是 git 仓库时，`workspace_diff` 会被静默省掉**：不报错，报告里那一项空着，只在清单里留一行 `workspace_diff: omit`。要拿盘上改动作判据的用例，得让工作区先是 git 仓库，或者换一样判据。
- **夹具侧不用自己 commit。**差集由 skill-up 自己算——会话前后各拍一次快照，比到行，不靠 git 的历史。**也 commit 不了**：`setup_steps` 跑在铺夹具之前（次序见第六节），那时工作区里还没有东西。**但设计稿里写的「铺完夹具提交一次初始快照」不用去掉**：`context.git.init: true` 时 skill-up 在会话开始前自己提交一次 `skill-up-baseline`，把 `setup_steps` 建的、技能装载的与夹具铺的一并纳入——那一步由它自动兑现，落成的人不用自己做（2026-10-02 实测，skill-up v0.12.0）。
- **铺夹具是逐字节写、连源文件的权限位一起带**（`type: none` 那一档）。工作树里设成只读的样本，铺进工作区之后还是只读。反过来，**git 不存权限位**（它只存执行位）——重新克隆之后只读属性会丢，跑之前要在工作树里重设一次。
- **铺夹具会跳过名字以 `.` 开头的文件与目录。**夹具里的 `.claude/rules/` 连同同一批的 `pages/.gitkeep` 一起被跳过，一份都没铺进工作区（2026-10-02 实测，skill-up v0.12.0）。要让它们进去，只能走用例配置的 `context.files` 逐条写，不指夹具目录。
- **被测技能引用的工作区外文件，不会自己跟着来，得主动补。**落成时扫一遍被测技能文档里的引用路径（它的 `SKILL.md` 里写 `../../rules/…` 这类），逐个确认工作区里读得到；读不到的走 `context.files` 铺进去。**不补的代价是判据静默落空**：被测那边会如实报告「那个文件不存在」，而判据「照那份规则的格式标注」就没有可判的东西了（2026-10-02 实测，skill-up v0.12.0）。

## 三、技能是怎么装进去的

- 技能装到工作区的 `.claude/skills/<技能名>/` 下——**走的是本地技能那条道，不是插件那条**。带插件前缀的唤起名（`/插件名:技能名`）用不了，只能按技能名唤起。
- **装的时候无条件跳过 `evals/` 子树**：被测技能自己带着评测材料时，那部分不会跟着进工作区。探针技能里放了 `evals/marker.txt`，跑完工作区 `.claude/skills/probe-skill/` 下只有 `SKILL.md`，没有它（2026-11-04 实测，skill-up v0.14.0）；`/skill-upper` 的 `eval-yaml.md` 也写着 `evals/` 从不安装。
- **`skills` 只能配在 `eval.yaml` 那一层，一条用例一层没有这个字段**。要「同一批里有的用例装技能、有的不装」，只能拆成两份配置分两次跑。**配错位置不会有提示**：在用例那一层也写一段 `skills`，`validate` 照样报 valid（2026-11-04 实测，skill-up v0.14.0）——多出来的字段是默默丢掉的。
- **装进去不等于会被唤起。**被测那边是 Claude Code（`claude_code` 引擎），技能按名称与描述挂在它的技能清单里，用不用由它自己判——输入里没有与该技能描述对得上的触发词时，它可能整轮都不唤起技能，直接按普通任务处理。实测（2026-10-02，skill-up v0.12.0）：输入「帮我分析一下分众传媒的护城河」，被测那边下载了五份年报、写完一篇分析，全程 11 轮没提过技能覆盖的术语页与概念页。**判据要落在「技能自己的不适用判定」上的用例受这一处影响**——那一条判的会变成「不唤起时的自然行为」，不是技能的分流规则。

## 四、Windows

**skill-up 原生支持 Windows**，`skill-up.exe` 直接跑。`/skill-upper` 里那句「macOS and Linux only. Windows is not currently supported」管的是它自己 `install.sh` 那条安装道（只能 bash 跑），不是说整个工具——照那句判，会把环境白改成 WSL2。**`/skill-upper` 的 `references/install.md` 与本节冲突时，以本节为准**：那一句是照它自己的安装脚本写的，本节是实机跑出来的。

能用的：

- **`none` runtime**：命令在宿主机上跑。
- **`opensandbox` runtime**：不受宿主机系统影响，始终在 Linux 沙箱里执行。
- **script judge 按扩展名分派**：`.ps1` → PowerShell、`.cmd`／`.bat` → `cmd.exe`、`.sh` → bash。三种各写一个判官、放进同一个 `judges` 数组里跑，三条都判过了（2026-11-04 实测，skill-up v0.14.0）。
- **`environment.setup_steps` 的命令由 bash 跑**（`type: none` 下）：探针里用 `mkdir -p`、`printf` 往工作区里写文件，都照 bash 跑成了（2026-11-04 实测，skill-up v0.14.0）。要在会话起来之前往工作区里补文件（被测技能引用的工作区外文件、根目录的 `CLAUDE.md`），照 bash 写就行。

`.sh` 判官要一个 bash，Windows 上的查找顺序：`SKILL_UP_BASH` 环境变量 → `PATH` 里的 bash → `C:\Program Files\Git\bin\bash.exe` → `C:\Program Files (x86)\Git\bin\bash.exe`。**WSL 那个 `C:\Windows\System32\bash.exe` 三条都不认，会被跳过**——机器上只有它时，`.sh` 判官起不来；要走 WSL 的得自己把 `SKILL_UP_BASH` 指到非 WSL 的 bash，或者干脆在 WSL 里跑 skill-up。这一段的搜索顺序与 WSL 跳过是旧记录，2026-11-04 只确认了 `.sh` 判官在本机 Git Bash 下能跑，搜索顺序没有重跑，标「待确认」。

一个都没找着时退到 `cmd.exe`：`cat`、`>>` 这类写法不成立，命令里的 `%VAR%` 还会被 `cmd.exe` 自己展开。

做不到的：

- **机器上没备齐 bash 与 Node 时，起不了真实 agent**：那条路要用 bash 引导 Node／nvm。上游的建议是先把 Node 与命令行工具装好，装不好再改用 WSL2。**这一条不是「原生 Windows 上跑不了」，是「没备齐就跑不了」**——一台原生 Windows 11（没进 WSL）上备着 cygwin 的 `bash` 与 Node，`v0.12.0` 上一批用例（`claude_code` 引擎、`agent_judge` 判官）整批跑通（2026-10-01 实测，skill-up v0.12.0）。判成前者的代价写在明处：把环境白改成 WSL2，或者把一条本来能跑的路标成跑不了。
- **`.ps1` 判官只在 Windows 目标上支持**：runtime 是 POSIX（比如 opensandbox 的 Linux 沙箱）时只能用 `.sh`。

## 五、`/skill-upper` 的参考文档里没写的几条

`/skill-upper` 那几份覆盖了配置字段与命令参数，写第七份要用的它基本都有。下面这几条它没写全，或者只有实跑才看得清——写第七份时要知道有它们。

- **`--workspace <目录>`**：拿宿主机上一个现成目录当工作区用，跑完**不删**。`skill-up run --help` 上写着它要 `runtime none` 与 `parallelism 1`（2026-11-04 实测，skill-up v0.14.0）。
- **`--no-delete`**：跑完保留 skill-up 自己建的工作区或容器，便于调试。默认 `false`。与上一条不是一回事：这条留的是 skill-up 建的那个，上一条用的是你自己给的。**留下的工作区在系统临时目录里**（`skill-up-<随机数>` 那一层，2026-11-04 实测，skill-up v0.14.0）——跑完去那儿找，不用在仓库里翻。
- **并发的单位是「一条用例」，调度是补位式的。**一条用例内部按顺序走完（多轮也顺序），用例之间并行、各起独立的临时工作区；**哪条跑完就补起下一条，不按规程分波次**——完成顺序因此是乱的（2026-10-10 实测，skill-up v0.12.0）。`--parallelism` 与 `cases.parallelism` 取 1–256，命令行传的盖过配置值（`/skill-upper` 的 `cli.md` 与 `eval-yaml.md` 里有这两句）；**设得比用例数大没有额外效果，也不报错**：能并发的至多是用例数那么多，多出来的数空着不用，校验也不驳回（2026-10-10 实测，skill-up v0.12.0）。
- **`judge.context.profile`**：判官拿到哪几样材料由它定，默认 `standard`——`final_message` 内联，`transcript` 以文件引用给出；`workspace_diff` 在工作区是 git 仓库时给，不是 git 仓库时省略。`minimal` 只留截断后的 `final_message`，`transcript`、`workspace_diff`、`generated_files` 都省略（2026-11-04 实测，skill-up v0.14.0）。第二节那条「差集被静默省掉」说的就是这个 `workspace_diff`。
- **`judge.model` 或 `judge.engine` 必须有一个，两者互斥。**两个都写会被 `validate` 驳回：`judge.model and judge.engine are mutually exclusive`（2026-11-04 实测，skill-up v0.14.0）。`judge.engine` 用另一套引擎起判官，要 `name`、`model.provider`、`model.name` 三项；它不继承被测 agent 的 model、kwargs、version、连接与凭据（`/skill-upper` 的 `judge-types.md` 与 `eval-yaml.md` 的 `judge.engine` 段）。
- **`judges` 数组：一次 agent 执行、多个判官按顺序判。**它们共用同一个 runtime 与文件系统，前一个判官写的文件后面的看得见；每个 Agent 判官各起一个新会话；全部通过才算用例通过；`expect` 失败时全部跳过（`/skill-upper` 的 `judge-types.md` 的 `judges` 段）。`judge` 与 `judges` 不能同时写——`validate` 会驳回 `judge and judges cannot be configured together`（2026-11-04 实测，skill-up v0.14.0）。
- **`user_simulator`**：用例的 `input.turns[].respond` 要配 `user_simulator.scenario`；eval 层配 `provider`、`protocol`、`model`；需要能 resume 会话的引擎（`claude_code` 支持）；轮数上限走 `cases.defaults.max_turns` 或 `constraints.max_turns`（`/skill-upper` 的 `eval-yaml.md` 的 `user_simulator` 段、`case-yaml.md` 的模拟用户回话段）。配置能通过 `validate`（2026-11-04 实测，skill-up v0.14.0）；模拟会话本身这次没跑，标「待确认」。
- **MCP 工具名写 `server::tool`。**`tool_called`、`tool_called_in_turn`、`tool_not_called_in_turn` 的 `name` 照 `/skill-upper` 的例子写——`judge-types.md` 里是 `name: "github::create_pull_request"`，`github` 是 `mcp.servers` 里的 `name`；不是 `mcp__server__tool` 那种写法。转录里是不是也这么记，这次没有可用的 MCP 服务可跑，标「待确认」。
- **v0.14.0 的评分口径：`expect` 门控失败时，判官那条断言记 `skipped`、不得分。**探针里第二条用例的 `expect.must_contain` 故意写一个不会出现的词，结果里那条判官断言是 `"skipped": true`，理由是 `not evaluated: expect gate failed`（2026-11-04 实测，skill-up v0.14.0）。
- **判官整块写在一层。**要么全写在 `eval.yaml` 的 `judge` 里（对全批生效），要么全写在用例里（对这一条生效；`/skill-upper` 的 `judge-types.md` 的例子就是用例那一层）。把一个判官拆到两层——`type` 与 `model` 放一层、`criteria` 与 `pass_threshold` 放另一层——`validate` 会驳回，话是 `case <用例 id>: judge.criteria is required when judge.type is agent_judge`（2026-11-04 实测，skill-up v0.14.0）。
- **判据按条计分，`pass_threshold` 是过线的比例。**三条判据过了两条就是 66.7%（实测：第一轮里有一条判据写得过严，那条用例判 FAIL 66.7%）。要「每条判据都得成立」就显式写 `1.0`——不写时的默认值没试过。
- **报告格式要显式列。**`result.json` 一直会写；要 HTML 得在 `report.formats` 里把 `html` 列上，不列就不出。已经跑过的那几轮想补一份 HTML，用 `report` 子命令从 `result.json` 生成，不必重跑（2026-10-02 实测，skill-up v0.12.0）。
- **判官那次回话要能直接当 JSON 读，包在代码围栏里不算。**判官偶尔把结果写成 ` ```json ` 围起来的块，也有时干脆回一句中文散文（不吐 JSON）——两种情况都是第一次解析失败，话是 `invalid JSON response`，skill-up 会重试一次。重试过得去就没事；赶不上用例超时（`cases.defaults.timeout_seconds`，默认 300 秒）那一条就报 ERROR。**报告末尾那行是三档——`passed / failed / errors`——ERROR 不是「被测那边没过」**：被判官这一次意外拖住、整条用例拿不到结论而已，重跑一遍通常就有结论了（2026-10-02 实测，skill-up v0.12.0：头一轮里一条 ERROR、另有两条第一次失败而重试通过）。
- **`cases.defaults.timeout_seconds` 显式写大，取 1800。**技能用例一条要走完被测那边的整轮会话——多轮工具调用——再等判官判一次，判官第一次回话解析不成还要重试一次。不写就是吃默认值（上一条那个 300 秒），顶到超时那一条整条报 ERROR、拿不到结论，这一轮就白跑。
- **判官准备上下文那一步失败时（报错里的 `materialize context`），判官一次都不跑，整条用例记 ERROR。**报错原文是 `judge evaluation failed: agent_judge materialize context: judge context material path escapes context dir: "final_message.txt"`。这条在 `v0.12.0` 上撞见过：`--output-dir` 传相对路径时，判官那次的上下文路径算歪了；`--parallelism 1` 单跑照样复现，换成绝对路径就零 ERROR（2026-10-10 实测，skill-up v0.12.0）。**0.14.0 起相对路径已可用**：同一条 agent_judge 用例改用相对 `--output-dir` 跑，判分正常（2026-11-04 实测，skill-up v0.14.0）。落成时传绝对路径仍是个好习惯：报告落在哪儿一眼看得清，不用先算基准。
- **不传 `--output-dir` 时，报告落在技能根旁边的 `<技能名>-workspace/`，不在第七份约定的 `runs/` 里。**`skill-up run --help` 上写的就是这句（`Default: <skill-name>-workspace alongside the skill directory`）；技能根退让时（见第七节），落点是退让到的那一层旁边——实跑与 `--help` 对得上（2026-11-04 实测，skill-up v0.14.0）。这个目录**不在「盖得住 `runs/`」那条 `.gitignore` 规则里**，`git add` 会把它整份收进库，而里面装的是报告、`report.html` 与每条用例的会话记录。所以落成时**每一条 `run` 命令都要显式传 `--output-dir`**——落成约定里那条「一批跑测取一个当场的时间戳目录」正是为这个。顺带一笔对不上的：`/skill-upper` 的 `cli.md` 把这个默认值写成「`eval.yaml` 所在目录」，与 `--help` 和实跑都不是一回事——实跑落在技能根那一层旁边，不是 `cases/` 那一层（2026-11-04 实测，skill-up v0.14.0）。

## 六、`environment.setup_steps` 在 `type: none` 下照样跑

上游文档只在容器那两个 runtime 的例子底下写它，但它不是容器专属：`type: none` 下照样跑，命令由工作区那个 shell 跑（见第四节），一条退出码非 0 就整条用例报错（2026-11-04 实测，skill-up v0.14.0）。

**次序写死**：`setup_steps` → 装 agent（`none` 下跳过）→ preflight → 装 MCP → 装技能 → **铺夹具**。夹具排在最末，所以**夹具里放一份同名文件，会把 `setup_steps` 写下的那份盖掉**，反过来不会。探针用同名的 `same.txt` 验过：`setup_steps` 写 `setup`，夹具写 `fixture`，跑完工作区里是 `fixture`（2026-11-04 实测，skill-up v0.14.0）。要往工作区里放一样东西、又不许它被冲掉，就得算准这条次序。第一节那条常驻上下文的替代道写的是工作区根目录那份 `CLAUDE.md`——**夹具里就不许放同名的**，放一份会把注入冲掉。

**它是批次级的：一批里每条用例各跑一遍**（2026-10-02 实测，skill-up v0.12.0）。`setup_steps` 配在 `environment` 底下，一条用例那一层没有这个字段（同第三节那条 `skills`）。一批用例、`setup_steps` 里只写了一条 `python -m venv`，那一批跑下来每条各建了一次——所以「只有某一条用例用得上」的准备动作，代价是其余各条也要各做一遍。要它只落在一条用例上，只能拆成两份配置分两次跑，或者让那一步自己判该不该做。

**共用一处写死路径的用例不能并发跑。**一批里有用例要在「某样东西还没装」的状态下开跑时，并发会让别的用例先把那样东西装上去，那一条就白跑了。把 `cases.parallelism` 设成 `1`，这一批串着跑（2026-10-02 实测，skill-up v0.12.0：整批串行，那条用例拿到的确实是干净环境）。

## 七、路径怎么算、消息怎么拼

**相对路径的基准是「技能根」，技能根找不到时会退让一步。** 规则是「所有相对路径相对 `SKILL.md` 所在目录算」（`/skill-upper` 的 `eval-yaml.md` 也这么写）。实际跑起来：从 `eval.yaml` 所在目录起往上找带 `SKILL.md` 的目录，**最多 10 层**；一层都没找着就退到「`eval.yaml` 所在目录的上一层」，并打一条 `SKILL.md not found within 10 levels above …; falling back to …` 的警告（2026-11-04 实测，skill-up v0.14.0）。

评测材料和被测技能不在一棵树里时，这条退让每次都走——基准因此是 `eval.yaml` 所在目录的上一层，不是技能根。写落成配置的人要按**实际退让到的那一层**算相对路径，别按文档那句理想的算；那条警告是正常产物，不是错。

**多轮只收 `user` 角色。** `input.turns` 的每一条只能是用户消息——写一条 `role: assistant` 去跑 `validate`，会当场驳回：`input.turns[0].role must be "user", got "assistant"`（2026-11-04 实测，skill-up v0.14.0）。所以要拿「被测那边自己上一条回答」当输入的用例（让它读到对话历史里它上一轮说过的话），**塞不进去**：只能把那段的全文接在用户消息里，或者多起一轮让它自己先说一遍。前一条是一处保真度折扣，判据要跟着避开「那段话在对话历史里」这件事。
