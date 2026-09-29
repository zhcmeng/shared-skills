# 测试环境需求

执行三条测试规程所需的环境要素，逐项列出。ENV-1 至 ENV-4 是三条规程共用的；ENV-5 只在 TP-3 里用。ENV-6、ENV-7 是第 0 步定下的测试运行环境——规程在哪跑、被测代码在哪执行，三条规程都在这两处上跑。

| 唯一标识符 | 英文名 | 测试环境项 | 描述 |
|:---|:---|:---|:---|
| ENV-1 | skill_handed_over | 把技能整套当作已装技能交给的执行环境 | `plugin/skills/plain-language/` 整个目录（`SKILL.md` 与 `rules.md`）当作使用者机器上装好的这门技能交给 agent，与它平时装了这门技能时一样；工作目录设在本仓库根——样本文件的路径与技能目录的绝对路径都要指得到。这一层判的是 agent 手里的文字，不是哪个脚本的输出 |
| ENV-2 | reply_commands_and_files | 能取到 agent 当轮的回复、它执行的命令与文档跑前跑后的内容 | 判定看三样：回复里说了什么、给没给该给的那段正文；这一轮执行的命令是什么；被改动的那份文档在跑前跑后差在哪几处。只取第一条回复，它后面打算怎么做不算。「有没有动到不该动的」按盘上那份文档的前后差别判，不按 agent 自己在回复里怎么说判 |
| ENV-3 | graders_on_disk | 每条用例自己的判据文件 | 用例目录下 `graders/` 里那份判据：写明哪几件事做到算通过、哪几件事一出现就不通过。判定只看当轮产出与盘上的改动，不替 agent 补话，也不替它解释 |
| ENV-4 | writable_workspace | 一块可写的工作区 | 放各份样本的副本，跑完要能把副本复位成原样（TC-1、TC-2、TC-3、TC-6 会写它）。原始样本在用例目录的 `fixture/` 下，全程不动 |
| ENV-5 | ambient_rules_injected | 常驻注入的摆法 | 把 `plugin/skills/plain-language/rules.md` 的内容按 `plugin/hooks/session-start` 的做法作为 SessionStart 的 additionalContext 注入上下文。实测可用 `claude -p "<用户消息>" --append-system-prompt "$(cat plugin/skills/plain-language/rules.md)"`，照 `evals/rules/cases/full-paths-no-cd/` 那条先例的摆法。这一项只在 TP-3 里专门摆一次；其余两条规程跑的时候 `rules.md` 同样已经注入（每次会话都由那个 hook 注入），三条的差别只在用不用 skill |
| ENV-6 | procedure_run_environment | 跑测试规程的那处隔离环境 | WSL2 发行版里的一份工作目录：三条规程的会话都在这处起、在这处收，每跑一条之前把上一轮的会话与盘上改动清干净——这一处要能重来，同一档里 TC-1 与 TC-6 判的正是「改没改、改得对不对」，上一轮的残留会串进下一轮的判定。本仓库与各份样本副本按 WSL2 的挂载路径（`/mnt/c/...`）在这一处指得到；`claude -p` 那套（ENV-5 的摆法）就在这处跑。这一条来自第 0 步的开工输入（DEC-16） |
| ENV-7 | code_execution_environment | 被测代码执行的那处环境 | 本机 Windows。这门技能没有脚本——测试项是 agent 手里的文字（`SKILL.md` 与 `rules.md`），没有一段代码要跑起来；「本机 Windows」在这里落的是 agent 的会话与它对盘上文档的读写，样本副本（ENV-4）也在这一处。这一条来自第 0 步的开工输入（DEC-16）：被测代码不跟着进 ENV-6 那处隔离环境 |
