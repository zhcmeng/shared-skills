# skill-up 的能力与边界

**本技能自己写的**，不是上游原文——上游 `docs/zh/guide/` 下没有这一份。它只收一件事：这套方案**能做到什么、做不到什么**。配置怎么写、命令怎么用不在这里，见同目录的 `writing-evals.md` 与 `cli-reference.md`。

对着的版本与它们相同：`main @ 7f1ff9b`（2026-09-29）。下面每条都注了出处（源码文件与行号，按那一个版本）。**换版本之后要重核一遍**，见文末。

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

## 换版本之后怎么重核

上面每条都注了出处。上游动过之后，按出处那几处重新看一眼；对不上的就改这一份，改完把顶上钉的版本换成新的，并同步改同目录 `README.md` 里那一行。

第四节没注源码出处，照上游的 `docs/zh/guide/windows.md` 核。
