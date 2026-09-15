# plain-language 规则常驻注入设计

日期：2026-09-15
状态：待评审

## 背景

`skills/plain-language/SKILL.md` 是一份「说人话」规则，目前只在用户主动喊「看不懂」时才被调用。
目标是**每个会话开始时把规则注入上下文**，让模型默认就按这套规则写字，而不是等用户抱怨了再改。

参考实现：`obra/superpowers` 插件的 SessionStart hook（`hooks/hooks.json` → `run-hook.cmd` → `session-start`）。

## 目标

- 会话启动、`/clear`、上下文压缩后，规则仍然常驻在上下文里
- 只注入「限定模型输出」所需的部分，不注入 skill 的路由表与输出模板
- 规则只有一份真相，不会因为两处维护而漂移
- hook 出任何问题都不能挡住开会话

## 非目标

- 不改 plain-language 的规则内容本身（仅为适配常驻语境做措辞中性化）
- 不执行安装。本设计只产出仓库内的文件，`/plugin marketplace add` 与 `/plugin install` 由用户自己执行
- 不恢复 `~/.agents/skills/` 下被删的 4 份副本

## 决策记录

| 决策 | 选了什么 | 为什么 |
|:---|:---|:---|
| 载体 | 仓库自身变成 Claude Code 插件 | `skills/` 布局早就为插件留好；一份真相；免写绝对路径 |
| 注入内容 | 只注入写作规则 | 输出格式与用法路由是「被调用时」才需要的，常驻是浪费 |
| 规则存放 | 抽成 `rules.md`，SKILL.md 指向它 | 用户否决了在 SKILL.md 里加 `<!-- always-on -->` 标记——对 skill 正文是噪音；也否决了复制两份——会漂移 |
| 技能副本 | 插件为唯一来源 | 用户已删除 `~/.claude/skills` 软链与 `~/.agents/skills` 副本 |
| 校验 | 加 `hooks/verify.sh` | 以后改完 skill 能立刻知道注入有没有断 |

## 设计

### 文件清单

| 动作 | 路径 | 说明 |
|:---|:---|:---|
| 新增 | `.claude-plugin/plugin.json` | 插件清单：name `shared-skills`、version `1.0.0`、license MIT |
| 新增 | `.claude-plugin/marketplace.json` | 让仓库可被 `/plugin marketplace add` 直接装 |
| 新增 | `hooks/hooks.json` | 声明 SessionStart |
| 新增 | `hooks/run-hook.cmd` | 跨平台包装，照抄 superpowers 的 polyglot 写法 |
| 新增 | `hooks/session-start` | 读 `rules.md` → 转义成 JSON → `hookSpecificOutput.additionalContext` |
| 新增 | `hooks/verify.sh` | 跑 hook 脚本、验 JSON 合法、断言规则文字非空且含关键词 |
| 新增 | `skills/plain-language/rules.md` | 规则唯一真相 |
| 改动 | `skills/plain-language/SKILL.md` | 规则段移走，开头加指向 `rules.md` 的强指令 |
| 改动 | `README.md` | 安装方式改为插件；维护节补一条「改 rules.md 即改注入」 |

### 内容切分

`rules.md` 收：判据、要改的、保留。措辞改为两种语境（skill 正文 / 常驻注入）都成立——
「被审页面」「重说回答时」这类审稿专属说法换成中性表达。

`SKILL.md` 留：YAML frontmatter、指向 `rules.md` 的指令、两种用法表、只读不改、审到哪、两套输出格式。

指向句必须是强指令（例如「先读同目录 `rules.md`，那是本 skill 的全部规则」），
不能写成「可参考」。**这是本方案最可能失效的地方**，验收靠第五节的第 3 项测试。

### 注入形态

`hooks/hooks.json` 的 matcher 用 `startup|clear|compact`。
`compact` 必须带——否则上下文一压缩，约束就丢了。

注入文本 = 一句限定语 + `rules.md` 原文。下面是**不含豁免句的草稿版**，最终版由第五节第 4 项测试决定：

```
<EXTREMELY_IMPORTANT>
你写给人看的文字，一律按下面这份规则来：回答、文档、说明、提交信息正文。
</EXTREMELY_IMPORTANT>

<rules.md 原文>
```

**待定项**：限定语要不要写「代码、命令、路径、引用原文不在此列」这类豁免句。
`superpowers:writing-skills` 明确说豁免句不起作用（「'这条限制不适用于代码块' 仍然会抑制代码块」，
该改结构而非写豁免）。同一份 skill 还指出，「要改的」本质是禁止清单，对「输出形状」类问题
禁止式会反效果、该用配方式。
这两条都是针对**现有 skill** 的，而现有 skill 是用测试驱动精简过的，所以不擅自改，
列为第五节第 4 项测试要验证的假设，拿证据说话。

### 出错兜底

hook 绝不能让会话开不起来：读不到文件、JSON 转义失败、任何异常，一律 `exit 0` 且不输出内容
（静默不注入）。宁可少注入一次，不能挡住开会话。

### 测试计划

| # | 测什么 | 怎么测 | 通过标准 |
|:---|:---|:---|:---|
| 1 | RED 基线：模型自然会写黑话吗 | 不带注入跑写作任务，5 次取样，逐条人工读 | 记录原话；若基线不犯，这功能就没有存在理由 |
| 2 | GREEN 注入有效吗 | 同样任务带注入跑，同样 5 次取样 | 黑话与英文夹杂的出现次数下降；代码标识符、路径、命令、公认缩写、专业术语未被改写 |
| 3 | 方案乙的致命点：会不会读 `rules.md` | 带注入调用 plain-language skill | 确实读了 `rules.md` 并照它改，而不是只看 SKILL.md 就动手 |
| 4 | 豁免句到底管不管用 | 限定语写豁免句 vs 不写，两组对照 | 若确如 writing-skills 所说，改成结构性方案并把结论写回本文件 |
| 5 | hook 本身没坏 | `bash hooks/verify.sh` | 输出是合法 JSON、规则文字非空、含关键词 |

取样一律用一次性 subagent，每次全新上下文，5 次以上，命中的样本逐条人工读——
自动计数会把模板回显和引用的反例也算成命中。

## 已知局限

- `CLAUDE_CODE_SUBAGENT_MODEL` 是 `deepseek-flash`，subagent 测试跑的是那个模型，
  **结论不能直接外推到 Opus**。报告里每一条结论都要标注这个局限
- 不安装插件，就无法做真实会话的端到端验证。`verify.sh` 只覆盖 hook 脚本本身，
  覆盖不到「Claude Code 确实读了 hooks.json 并执行了它」
