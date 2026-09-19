# 第三方组件声明

本 skill 的 `SKILL.md` 与 `references/` 复制自上游仓库，随插件一起分发——这样装上插件就有这个技能，不必再去上游取一遍。

## Agent-Reach 技能

- 文件：`SKILL.md`，以及 `references/` 下的 7 个文件（`search.md`、`social.md`、`career.md`、`dev.md`、`web.md`、`video.md`、`finance.md`）
- 用途：告诉 Agent 该怎么调用 `agent-reach` 命令行去访问那 16 个平台
- 许可证：MIT，Copyright (c) 2025 Agent Eyes
- 来源：https://github.com/Panniantong/Agent-Reach 的 `agent_reach/skill/` 目录
- 同步版本：commit `a19a171fa980a0785849596492e0af4db800c82f`（`main` 分支，2026-09-19 取）

## 本地改动

上游的 7 个 reference 文件逐字未动。另外**新增**了 `references/install.md`，`SKILL.md` 改了两处：

1. **新增**「命令行工具没装时」一节，指向 `references/install.md`。上游假定命令行工具已经装好，这节补上装法：只装本体，再跑一次只读体检，把还缺的工具列出来交给用户决定装不装。安装步骤放在单独文件里，SKILL.md 里不写「开工前先检查」这类动作——命令在不在由失败本身暴露，正常路径下不必空跑一次检查。
2. **改写**上游「环境检查」一节。原文说的是上游作者本机的约定（「本机 Python 环境默认是 conda `dl`」），换台机器读会误导；改成不带这层假设的「体检」一节，其中的 `agent-reach doctor --json` 命令保留。

## 与上游更新提示的关系

`SKILL.md` 的常驻规则第 5 条会让 Agent 跑 `agent-reach check-update`，发现新版时提示你按上游的 `docs/update.md` 更新。那条路径更新的是命令行工具本体，不会动这份复制进来的技能文件——技能文件要更新，走下一步。

## 同步上游

上游改了 `agent_reach/skill/` 之后，在 `skills/agent-reach/` 目录下重新复制一遍：

```bash
SHA=$(curl -s https://api.github.com/repos/Panniantong/agent-reach/commits/main | grep -m1 '"sha"' | cut -d'"' -f4)
curl -sL "https://raw.githubusercontent.com/Panniantong/agent-reach/$SHA/agent_reach/skill/SKILL.md" -o SKILL.md
for f in career dev finance search social video web; do
  curl -sL "https://raw.githubusercontent.com/Panniantong/agent-reach/$SHA/agent_reach/skill/references/$f.md" -o "references/$f.md"
done
```

复制完做两件事：把上面「同步版本」的 commit 和日期换成新的；重做「本地改动」里那两处——`SKILL.md` 会被整份覆盖，「命令行工具没装时」那节和删掉的 conda 说明都得再补一遍。（`references/install.md` 是本地新增的文件，复制不会动它。）
