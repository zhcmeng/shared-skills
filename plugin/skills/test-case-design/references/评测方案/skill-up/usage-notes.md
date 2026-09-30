# skill-up 使用要点

**本技能自己写的**，不是上游原文——上游 `docs/zh/guide/` 下没有这一份。它收的是用这套方案时要拿捏的几处：**实际跑起来是什么样**、**做不到什么**、**哪里要挑**（判官三型、engine 开关）。配置字段怎么填、命令怎么用不在这里，见同目录的 `writing-evals.md` 与 `cli-reference.md`。

对着的版本与它们相同：`main @ 7f1ff9b`（2026-09-29）。第一到五节照上游源码写，每条注了出处（源码文件与行号）；第六、七节照上游那份给 agent 看的参考写（`skills/skill-upper/references/` 下那两份），没从源码核。**换版本之后要重核一遍**，见文末。

## 一、一次运行里，被测那边是怎么起的

每条用例各起一轮会话，命令是这么拼的（`internal/agent/claude_code.go:322`）：

```
claude --settings '{"disableAllHooks":true}' --session-id <id> -p --permission-mode=bypassPermissions
```

两处要留意：

- **钩子一律不生效**（`disableAllHooks` 置了 `true`）。被测技能或项目里挂着钩子，评测时不会跑——通用稿里如果有哪一条要求靠钩子触发，落到这套方案上就跑不了原样。
- **权限全开**（`--permission-mode=bypassPermissions`）。被测那边不会停下来问权限。

多轮会话用 `--resume <id>` 接着上一轮（`:341`）。

## 二、工作区

- 每条用例各起一个空的临时目录当工作区，跑完删掉；工作区由框架建，不由用例配置指定（见 `cli-reference.md` 里 `--workspace`／`--no-delete` 两条）。
- 上一轮留下的东西不进下一轮。
- **工作区不是 git 仓库时，`workspace_diff` 会被静默省掉**：不报错，报告里那一项空着，只在清单里留一行 `workspace_diff: omit`。要拿盘上改动作判据的用例，得让工作区先是 git 仓库，或者换一样判据。

## 三、技能是怎么装进去的

- 技能装到工作区的 `.claude/skills/<技能名>/` 下——**走的是本地技能那条道，不是插件那条**。带插件前缀的唤起名（`/插件名:技能名`）用不了，只能按技能名唤起。
- **装的时候无条件跳过 `evals/` 子树**（`internal/agent/skill.go:60`）：被测技能自己带着评测材料时，那部分不会跟着进工作区。

## 四、工作区里跑命令用哪个 shell（Windows）

- 找 bash 的顺序：`SKILL_UP_BASH` 环境变量 → `PATH` 里的 bash → `C:\Program Files\Git\bin\bash.exe` → `C:\Program Files (x86)\Git\bin\bash.exe`。
- **WSL 那个 `C:\Windows\System32\bash.exe` 三条都不认，会被跳过**——机器上只有它时，`.sh` 判官起不来。
- 一个都没找着时退到 `cmd.exe`：`cat`、`>>` 这类写法不成立，命令里的 `%VAR%` 还会被 `cmd.exe` 自己展开。

（这一节是照上游 `docs/zh/guide/windows.md` 写的，不是从源码核的。）

## 五、做不到的

- **原生 Windows 上跑不了完整的模型**：起真实 agent 那条路要用 bash 引导 Node／nvm；上游的建议是改用 WSL2，或者先把 Node 与命令行工具装好。
- `.ps1` 判官只在 Windows 目标上支持，别的目标上不能用。

## 六、判官三型怎么挑

一条用例只能挑一型（`judge.type`）。往下问三层：

1. 关键词、盘上的文件、退出码、调了哪个工具能定成败？→ `rule_based`，最便宜，也是默认那型。
2. 产出是结构化的，要自己写个检查？→ `script`。
3. 要读懂意思才判得了？→ `agent_judge`，最贵。

`expect` 排在判官前面，零成本：它不过，判官根本不跑。能用 `expect` 说清的，别留给判官。

| 判什么 | 花多少 | 什么时候用 |
|:---|:---|:---|
| `expect` | 不花 | 第一道门槛 |
| `rule_based` | 极低 | 默认 |
| `script` | 低，看脚本自己 | 自定义检查 |
| `agent_judge` | 高 | 要语义判断 |

（这一节照上游 `skills/skill-upper/references/judge-types.md` 写的，不是从源码核的。）

## 七、engine.kwargs：各引擎只认自己那几个开关

`engine.kwargs` 是一张字符串键值表。各引擎只认自己认识的键，不认识的忽略掉，只在 `-v` 的 debug 日志里留一行——拼错字（`bypas_sandbox`）就是靠那一行发现的。命令行上的等价写法是可重复的 `--engine-kwarg key=value`（简写 `--ek`），优先级：命令行 > `engine.kwargs` > 默认值。

| 键 | 引擎 | 置 `"true"` 会怎样 | 默认／置假 |
|:---|:---|:---|:---|
| `bypass_sandbox` | `codex` | 强制加 `--dangerously-bypass-approvals-and-sandbox`，盖掉按运行时推出来的那个沙箱开关；宿主机内核不支持 Landlock（某些 CI 容器）时用得上 | `none` 下用 `--sandbox workspace-write`；别的运行时本来就绕过沙箱 |
| `bypass_sandbox` | `claude_code` | 空操作——它本来就走 `--permission-mode=bypassPermissions`（见第一节） | 空操作 |
| `bypass_sandbox` | `qodercli` | 空操作——它没有对应的开关 | 空操作 |

（这一节照上游 `skills/skill-upper/references/eval-yaml.md` 写的，不是从源码核的。）

## 换版本之后怎么重核

上面每条都注了出处。上游动过之后，按出处那几处重新看一眼；对不上的就改这一份，改完把顶上钉的版本换成新的，并同步改同目录 `README.md` 里那一行。

第四节没注源码出处，照上游的 `docs/zh/guide/windows.md` 核；第六、七节照上游 `skills/skill-upper/references/judge-types.md` 与 `eval-yaml.md` 核。
