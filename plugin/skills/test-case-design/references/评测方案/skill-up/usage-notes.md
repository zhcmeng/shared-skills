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
- **夹具侧不用自己 commit。**差集由 skill-up 自己算——会话前后各拍一次快照，比到行，不靠 git 的历史。**也 commit 不了**：`setup_steps` 跑在铺夹具之前（次序见第六节），那时工作区里还没有东西。**但设计稿里写的「铺完夹具提交一次初始快照」不用去掉**：`context.git.init: true` 时 skill-up 在会话开始前自己提交一次 `skill-up-baseline`，把 `setup_steps` 建的、技能装载的与夹具铺的一并纳入——那一步由它自动兑现，落成的人不用自己做（2026-10-02 实测，`v0.12.0`）。
- **铺夹具是逐字节写、连源文件的权限位一起带**（`type: none` 那一档，`UploadDir` 保留 mode）。工作树里设成只读的样本，铺进工作区之后还是只读。反过来，**git 不存权限位**（它只存执行位）——重新克隆之后只读属性会丢，跑之前要在工作树里重设一次。
- **铺夹具会跳过名字以 `.` 开头的文件与目录。**夹具里的 `.claude/rules/` 连同同一批的 `pages/.gitkeep` 一起被跳过，一份都没铺进工作区（2026-10-02 实测）。要让它们进去，只能走用例配置的 `context.files` 逐条写，不指夹具目录。
- **被测技能引用的工作区外文件，不会自己跟着来，得主动补。**落成时扫一遍被测技能文档里的引用路径（它的 `SKILL.md` 里写 `../../rules/…` 这类），逐个确认工作区里读得到；读不到的走 `context.files` 铺进去。**不补的代价是判据静默落空**：被测那边会如实报告「那个文件不存在」，而判据「照那份规则的格式标注」就没有可判的东西了（2026-10-02 实测）。

## 三、技能是怎么装进去的

- 技能装到工作区的 `.claude/skills/<技能名>/` 下——**走的是本地技能那条道，不是插件那条**。带插件前缀的唤起名（`/插件名:技能名`）用不了，只能按技能名唤起。
- **装的时候无条件跳过 `evals/` 子树**（`internal/agent/skill.go:60`）：被测技能自己带着评测材料时，那部分不会跟着进工作区。
- **`skills` 只能配在 `eval.yaml` 那一层，一条用例一层没有这个字段**。要「同一批里有的用例装技能、有的不装」，只能拆成两份配置分两次跑。**配错位置不会有提示**：在用例那一层也写一段 `skills`，`validate` 照样报 valid（实测，`v0.12.0`）——多出来的字段是默默丢掉的。
- **装进去不等于会被唤起。**被测那边是 Claude Code，技能按名称与描述挂在它的技能清单里，用不用由它自己判——输入里没有与该技能描述对得上的触发词时，它可能整轮都不唤起技能，直接按普通任务处理。实测（2026-10-02，`v0.12.0`）：输入「帮我分析一下分众传媒的护城河」，被测那边下载了五份年报、写完一篇分析，全程 11 轮没提过技能覆盖的术语页与概念页。**判据要落在「技能自己的不适用判定」上的用例受这一处影响**——那一条判的会变成「不唤起时的自然行为」，不是技能的分流规则。

## 四、Windows

**skill-up 原生支持 Windows**，`skill-up.exe` 直接跑。`/skill-upper` 里那句「macOS and Linux only. Windows is not currently supported」管的是它自己 `install.sh` 那条安装道（只能 bash 跑），不是说整个工具——照那句判，会把环境白改成 WSL2。**`/skill-upper` 的 `references/install.md` 与本节冲突时，以本节为准**：那一句是照它自己的安装脚本写的，本节是实机跑出来的。

能用的：

- **`none` runtime**：命令在宿主机上跑。
- **`opensandbox` runtime**：不受宿主机系统影响，始终在 Linux 沙箱里执行。
- **script judge 按扩展名分派**：`.ps1` → PowerShell、`.cmd`／`.bat` → `cmd.exe`、`.sh` → bash。
- **`environment.setup_steps` 的命令由 bash 跑**（`type: none` 下）：`mkdir -p`、`cp`、中文路径都能用——要在会话起来之前往工作区里补文件（被测技能引用的工作区外文件、根目录的 `CLAUDE.md`），照 bash 写就行（2026-10-02 实测，`v0.12.0`）。

`.sh` 判官要一个 bash，找的顺序：`SKILL_UP_BASH` 环境变量 → `PATH` 里的 bash → `C:\Program Files\Git\bin\bash.exe` → `C:\Program Files (x86)\Git\bin\bash.exe`。**WSL 那个 `C:\Windows\System32\bash.exe` 三条都不认，会被跳过**——机器上只有它时，`.sh` 判官起不来；要走 WSL 的得自己把 `SKILL_UP_BASH` 指到非 WSL 的 bash，或者干脆在 WSL 里跑 skill-up。

一个都没找着时退到 `cmd.exe`：`cat`、`>>` 这类写法不成立，命令里的 `%VAR%` 还会被 `cmd.exe` 自己展开。

做不到的：

- **机器上没备齐 bash 与 Node 时，起不了真实 agent**：那条路要用 bash 引导 Node／nvm。上游的建议是先把 Node 与命令行工具装好，装不好再改用 WSL2。**这一条不是「原生 Windows 上跑不了」，是「没备齐就跑不了」**——一台原生 Windows 11（没进 WSL）上备着 cygwin 的 `bash` 与 Node，`v0.12.0` 上一批用例（`claude_code` 引擎、`agent_judge` 判官）整批跑通（2026-10-01 实测）。判成前者的代价写在明处：把环境白改成 WSL2，或者把一条本来能跑的路标成跑不了。
- **`.ps1` 判官只在 Windows 目标上支持**：runtime 是 POSIX（比如 opensandbox 的 Linux 沙箱）时只能用 `.sh`。

（这一节照上游 `docs/zh/guide/windows.md` 写的，不是从源码核的；上面那条「备齐就跑得起来」是实跑核过的，出处见文末。）

## 五、`/skill-upper` 的参考文档里没写的几条

`/skill-upper` 那几份覆盖了配置字段与命令参数，写第七份要用的它基本都有。下面这几条它没写，出自上游文档站那两份 guide（`cli-reference.md` 与 `writing-evals.md`）——写第七份时要知道有它们。

- **`--workspace <目录>`**：拿宿主机上一个现成目录当工作区用，跑完**不删**。只在 `environment.type: none`、`cases.parallelism: 1`、benchmark 关掉时能用。
- **`--no-delete`**：跑完保留 skill-up 自己建的工作区或容器，便于调试。默认 `false`。与上一条不是一回事：这条留的是 skill-up 建的那个，上一条用的是你自己给的。**留下的工作区落在 `%TEMP%\skill-up-<随机数>`**（2026-10-02 实测）——跑完去那儿找，不用在仓库里翻。
- **并发的单位是「一条用例」，调度是补位式的。**一条用例内部按顺序走完（多轮也顺序），用例之间并行、各起独立的临时工作区；**哪条跑完就补起下一条，不按规程分波次**——完成顺序因此是乱的（实测：`runs\2026-10-10-1602-tp12\` 那批 11 条、并行度 4，先跑完的是第 8、10、6、11 条）。`--parallelism` 与 `cases.parallelism` 取 1–256，命令行传的盖过配置值（这两句上游的 `cli.md` 与 `eval-yaml.md` 里有，这里补的是实测）；**设得比用例数大没有额外效果，也不报错**：能并发的至多是用例数那么多，多出来的数空着不用，校验也不驳回（30 条用例上取 30、取 255 都试过，没报错）（2026-10-10 实测，`v0.12.0`）。
- **`judge.context`**：判官拿到哪几样材料由它定，默认 `standard`——`final_message` 内联，`transcript` 与 `workspace_diff` 以文件引用给出；另有 `minimal`（省掉 transcript 与 diff、截断 final_message）。第二节那条「差集被静默省掉」说的就是这个 `workspace_diff`。
- **`judge.type: agent_judge` 时 `judge.model` 必填。**不写会当场被驳回，话是 `judge.model is required when judge.type is agent_judge`——这一句 `judge-types.md` 的例子底下没写，只列了字段。**判官整块写在用例那一层**：`type`、`model`、`criteria`、`pass_threshold` 一起写全；批次那一层不写。这一条原先记成「写在批次那一层就够、用例级只写 `criteria`」，2026-10-02 实测把它推翻：批次那层写 `type` 与 `model`、用例那层写 `criteria` 与 `pass_threshold` 时整批被驳回，话是 `case <用例 id>: judge.criteria is required when judge.type is agent_judge`——用例那层写的 `criteria` 不算数。用例那层整块写全、批次那层不写，校验通过（本仓库 `evals/plain-language/` 与 `evals/token-counter/` 两批都按这个写法落，都在 `v0.12.0` 上过了）。
- **判据按条计分，`pass_threshold` 是过线的比例。**三条判据过了两条就是 66.7%（实测：第一轮里有一条判据写得过严，那条用例判 FAIL 66.7%）。要「每条判据都得成立」就显式写 `1.0`——不写时的默认值没试过。
- **报告格式要显式列。**`result.json` 一直会写；要 HTML 得在 `report.formats` 里把 `html` 列上，不列就不出。已经跑过的那几轮想补一份 HTML，用 `report` 子命令从 `result.json` 生成，不必重跑（实测，`v0.12.0`）。
- **判官那次回话要能直接当 JSON 读，包在代码围栏里不算。**判官偶尔把结果写成 ` ```json ` 围起来的块，也有时干脆回一句中文散文（不吐 JSON）——两种情况都是第一次解析失败，话是 `invalid JSON response`，skill-up 会重试一次。重试过得去就没事；赶不上用例超时（`cases.defaults.timeout_seconds`，默认 300 秒）那一条就报 ERROR。**报告末尾那行是三档——`passed / failed / errors`——ERROR 不是「被测那边没过」**：被判官这一次意外拖住、整条用例拿不到结论而已，重跑一遍通常就有结论了（实测，`v0.12.0`：头一轮里一条 ERROR、另有两条第一次失败而重试通过）。
- **`cases.defaults.timeout_seconds` 显式写大，取 1800。**技能用例一条要走完被测那边的整轮会话——多轮工具调用——再等判官判一次，判官第一次回话解析不成还要重试一次。不写就是吃默认值（上一条那个 300 秒），顶到超时那一条整条报 ERROR、拿不到结论，这一轮就白跑。
- **判官准备上下文那一步失败时（报错里的 `materialize context`），判官一次都不跑，整条用例记 ERROR。**报错原文：`judge evaluation failed: agent_judge materialize context: judge context material path escapes context dir: "final_message.txt"`。现场是 `judge/context` 与 `judge/run` 两个目录留着、里面空的，判官一份产物都没有；**用例自己那轮会话是跑完了的**（`outputs/response.md` 在）。**与并发无关**：`--parallelism 1` 单跑照样复现（`runs\2026-10-10-1720-tc7-solo\`）。**疑与 `--output-dir` 传相对路径有关**：绝对路径的批次（`runs\2026-10-10-1602-tp12\`、`...1636-tp12-changed\`、`...1636-e2e-changed\`）零 ERROR，传相对路径的两批（`...1650-tc15\`、`...1720-tc7-solo\`，各 1 条）都是 ERROR——**这层因果还没定论（待确认）**；所以落成时 `--output-dir` 一律写绝对路径——绝对路径的批次至今没撞上过它（2026-10-10 实测，`v0.12.0`）。
- **不传 `--output-dir` 时，报告落在技能根旁边的 `<技能名>-workspace/`，不在第七份约定的 `runs/` 里。**`skill-up run --help` 上写的就是这句（`Default: <skill-name>-workspace alongside the skill directory`）；技能根退让时（见第七节），落点是**退让到的那一层**——实跑留下过 `.claude/evals/game-design-xlsx-to-md-workspace/`（`eval.yaml` 在 `game-design-xlsx-to-md/cases/` 下，退让出来的技能根是 `.claude/evals/`）。这个目录**不在「盖得住 `runs/`」那条 `.gitignore` 规则里**，`git add` 会把它整份收进库，而里面装的是报告、`report.html` 与每条用例的会话记录。所以落成时**每一条 `run` 命令都要显式传 `--output-dir`**——落成约定里那条「一批跑测取一个当场的时间戳目录」正是为这个。顺带一笔对不上的：`/skill-upper` 的 `cli.md` 把这个默认值写成「`eval.yaml` 所在目录」（第 21 行），与 `--help` 和实跑都不是一回事——实跑落在技能根那一层，不是 `cases/` 那一层（2026-10-10 实测，`v0.12.0`）。

第一到三节、第六节与第七节的东西它同样没写——那几节是照上游**源码**读出来的，本来就哪份文档都没有；第四节出自上游文档站的 `windows.md`。

## 六、`environment.setup_steps` 在 `type: none` 下照样跑

上游文档只在容器那两个 runtime 的例子底下写它，但它不是容器专属：`internal/evaluator/evaluator.go:1172` 那个循环没有类型判断（类型判断在 `:1182`，只管装不装 agent）。命令由工作区那个 shell 跑（见第四节），一条退出码非 0 就整条用例报错。

**次序写死**，同一个函数里排下来：`setup_steps` → 装 agent（`none` 下跳过）→ preflight → 装 MCP → 装技能 → **铺夹具**（`:1206`）。夹具排在最末，所以**夹具里放一份同名文件，会把 `setup_steps` 写下的那份盖掉**，反过来不会。要往工作区里放一样东西、又不许它被冲掉，就得算准这条次序。第一节那条常驻上下文的替代道写的是工作区根目录那份 `CLAUDE.md`——**夹具里就不许放同名的**，放一份会把注入冲掉。

**它是批次级的：一批里每条用例各跑一遍**（实测，`v0.12.0`）。`setup_steps` 配在 `environment` 底下，一条用例那一层没有这个字段（同第三节那条 `skills`）。一批用例、`setup_steps` 里只写了一条 `python -m venv`，那一批跑下来每条各建了一次——所以「只有某一条用例用得上」的准备动作，代价是其余各条白做一遍。要它只落在一条用例上，只能拆成两份配置分两次跑，或者让那一步自己判该不该做。

**共用一处写死路径的用例不能并发跑。**一批里有用例要在「某样东西还没装」的状态下开跑时，并发会让别的用例先把那样东西装上去，那一条就白跑了。把 `cases.parallelism` 设成 `1`，这一批串着跑（实测：整批串行，那条用例拿到的确实是干净环境）。

## 七、路径怎么算、消息怎么拼

**相对路径的基准是「技能根」，技能根找不到时会退让一步。** 文档里的规则是「所有相对路径相对 `SKILL.md` 所在目录算」（`/skill-upper` 的 `eval-yaml.md` 也这么写）。实际实现是（`internal/config/loader.go:214` 的 `FindSkillDir`）：从 `eval.yaml` 所在目录起往上找带 `SKILL.md` 的目录，**最多 10 层**（`:17`）；一层都没找着就退到「`eval.yaml` 所在目录的上一层」，并打一条 `SKILL.md not found within 10 levels above …; falling back to …` 的警告（`:52`）。

评测材料和被测技能不在一棵树里时，这条退让每次都走——基准因此是 `eval.yaml` 的上一层，不是技能根。写落成配置的人要按**实际退让到的那一层**算相对路径，别按文档那句理想的算；那条警告是正常产物，不是错。

**多轮只收 `user` 角色。** `input.turns` 的每一条只能是用户消息——校验器写死（`internal/config/validator.go:130`，`role must be "user"`），配置结构里那个字段的注释也标着 `// user`（`internal/config/schema.go:310`）。所以要拿「被测那边自己上一条回答」当输入的用例（让它读到对话历史里它上一轮说过的话），**塞不进去**：只能把那段的全文接在用户消息里，或者多起一轮让它自己先说一遍。前一条是一处保真度折扣，判据要跟着避开「那段话在对话历史里」这件事。

## 落成时撞见的新折扣往哪儿写

落成那一步撞见的、这一份里没写的折扣（哪一样铺不进去、哪一处路径算歪了、哪一条其实落不成原样），照下面写回来：

- **写进对应那一节**，不另起一节：工作区与夹具的事写第二节，命令与字段的事写第五节，Windows 的事写第四节。
- **句末标实测日期与版本**，体例照这一份现有的：`（2026-10-02 实测，v0.12.0）`。
- **在文末那张「已核过」清单里补一笔**——哪一条、什么时候、在哪个版本上核的。
- **只有实测过的才写成事实**。没实测的标「待确认」——这一份旧了不会报错，只会说错话。

写回之后，第七份「说明」那一块里引到这一份的话跟着核一遍：那里写着「与设计稿一致，没有出入」的条目，可能已经不是了。

## 换版本之后怎么重核

上面每条都注了出处。上游动过之后，按出处那几处重新看一眼；对不上的就改这一份，改完把顶上钉的版本换成新的，并同步改同目录 `README.md` 里那一行。

**源码那个号和发布那个号会各走各的**——发布不等于 `main` 的头。这一份的结论大多读自源码，所以先看一眼装的是哪个发布版，别当成对得上。

第四节没注源码出处，照上游文档站的 `docs/zh/guide/windows.md` 核；第五节照同站的 `cli-reference.md` 与 `writing-evals.md` 核；第一节那条 `CLAUDE.md` 不是上游的说法，照 Claude Code 自己的行为核。第七节那两处有个便宜的核法：路径退让在任一份**找不到技能根**的配置上跑一遍 `skill-up validate`，屏幕上就会打出那条 `falling back` 的警告；只收 `user` 角色拿一份 `role: assistant` 的用例跑 `validate`，会被当场驳回。

**已经在装着的 `v0.12.0` 上核过这几处**：第七节那两处（上面那两个便宜的核法，各跑一次就对上了）、第三节那条「用例那一层写了 `skills` 也不报错」、第四节那条「备齐 bash 与 Node 就起得来真实 agent」（2026-10-01，在原生 Windows 上整批跑通）、第五节那几条（`judge.model` 必填、`report.formats` 不写就不出 HTML；判官整块写在用例那一层那条 2026-10-02 在二进制上重核过，推翻了原先「批次那层写了就够」的记法）、第六节那两条（`setup_steps` 是批次级、每条用例各跑一遍；`cases.parallelism: 1` 串着跑）。其余各条只在源码那一版上读过，还没在二进制上逐条核。

**2026-10-02 又核过三处**（都在 `v0.12.0` 上）：第二节那条 skill-up 自己提交 `skill-up-baseline`、第三节那条装进去不等于会被唤起、第四节那条 `setup_steps` 由 bash 跑——出处是 `evals/business-term-builder/` 那一批的落成与探针跑测。

**2026-10-10 又核过一处**（`v0.12.0` 上）：第五节那条「不传 `--output-dir` 时落在哪」——跑第一批时有几条命令漏传，`<技能名>-workspace/` 直接落在评测材料根旁边，与 `--help` 上那句对得上。出处是 `xlsx/公会系统/` 那一批的落成与首轮回归。

**2026-10-10 又核过两处**（都在 `v0.12.0` 上）：第五节那条并行度语义（并发以一条用例为单位、补位式调度、设得比用例数大没有额外效果也不报错）；第五节那条判官准备上下文失败时报 ERROR（报错原文与空目录现场、`--parallelism 1` 单跑复现；相对路径与绝对路径两批的对照只是相关，因果未定论，已标「待确认」）——出处是 `game-design-xlsx-to-md/` 那一批的落成与跑测（`.claude/evals/` 下）。
