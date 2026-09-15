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
| 新增 | `hooks/verify.sh` | 跑 `session-start`、验 JSON 合法、断言注入文本的结尾与 `rules.md` 原文逐字一致、限定语块结尾结构完整且含关键词；再比对 `run-hook.cmd` 的输出与直接调用 `session-start` 一致 |
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

注入文本 = 一句限定语 + `rules.md` 原文。限定语已定稿（取证见下），**不含豁免句**，与 `hooks/session-start` 里 `context=` 那一行逐字一致：

```
<EXTREMELY_IMPORTANT>
你写给人看的文字，一律按下面这份规则来：回答、文档、说明、提交信息正文。
</EXTREMELY_IMPORTANT>

<rules.md 原文>
```

**定稿结论**：豁免句不写。`hooks/session-start` 第 26 行的 `context=` 就是上面这段，文件里不含「不在此列」这类措辞。

### 措辞实测结论

取样一律用一次性 subagent、每次全新上下文、每组 5 次，模型是 `deepseek-flash`
（`CLAUDE_CODE_SUBAGENT_MODEL`）。**下面每一条结论都只在这个模型上成立，不能外推到 Opus。**
原始输出随仓库提交：`docs/superpowers/plans/2026-09-15-ab-exemption.md`（A/B 两组全文）与
`docs/superpowers/plans/2026-09-15-green-injection.md`（GREEN 两轮全文）。

**一、豁免句 A/B：两组无差别，取更短的那版（不含豁免句）**

假设来自 `superpowers:writing-skills` 的断言（「'这条限制不适用于代码块' 仍然会抑制代码块，该改结构而非写豁免」）。
那是针对**现有 skill** 的断言，没有直接采信，做了对照实验：A 组限定语就是现在定稿这句，
B 组在这句后面多一句「代码、命令、路径、引用原文不在此列。」

- 跑在 `deepseek-flash` 上（`CLAUDE_CODE_SUBAGENT_MODEL`），不能外推到 Opus。
- 四个观测点上两组**逐点完全相同**，没有一个观测点偏向 B 组：
  - yaml 代码块被改写或抑制：A 组 0 / 5，B 组 0 / 5
  - `API` 被展开成中文释义：A 组 0 / 5（A5 写成「接口（API）」，缩写仍在），B 组 0 / 5
  - REST / GraphQL 被额外补中文说明：A 组 2 / 5（A1、A3），B 组 2 / 5（B4、B5）
  - QPS 被改写成中文表述：A 组 5 / 5，B 组 5 / 5
- 判据是「B 组的代码块完好率明显更高才采用 B」。两组没有差别，故取更短的那版：B 组比 A 组只多这一句
  （实验 prompt 2979 字节 vs 3033 字节，差的就是它），而它每开一次会话都进上下文。
- **这不等于「豁免句已被证伪」**：本实验没有观测到豁免句有害，只是没有观测到它有用。
  预期它冗余的理由是——那半句与 `rules.md` 的「保留」段重复：代码标识符、路径、命令名、
  引用原文的章节名本来就在「保留」里结构性豁免掉了，再写一句「不在此列」是同一件事说两遍。
- **混淆项**：任务文本自带一句「代码不用动，原样附在后面」，两组都带。这句话本身就在豁免代码，
  可能掩盖了 A 组把规则过度套用到代码上的倾向。所以本实验支持的是「两组无差别」，
  **不能用来支持「豁免句有害」**。

**二、GREEN：注入在「术语首次出现不解释」这一条上有效**

- 跑在 `deepseek-flash` 上（`CLAUDE_CODE_SUBAGENT_MODEL`），不能外推到 Opus。
- 任务逐字取自 Task 2 的 RED 基线（`docs/superpowers/plans/2026-09-15-baseline.md`）：
  给公司管理层写一段 300 字左右的缓存方案摘要。不带注入 5 次，带注入 5 次，逐条人工读。
- **出现未解释的术语：不带注入 5 / 5，带注入 0 / 5。** 不带注入组 5 个样本出现的**一次都没解释**的词（列代表性词，非穷举）：
  分布式缓存层（5 次）、主动失效机制（5）、缓存穿透（3）、灰度（3）、限流 / 降级（限流 2 次、降级 3 次）、回源（3）、
  雪崩（1）、旁路读模式（1）、键规范（1）、强一致（1）、降本增效（1）。这 11 项在带注入组一个都没出现。
- **「缓存」这个词本身：不带注入 0 / 5 就地解释，带注入 5 / 5 就地解释**
  （如「把刚查过的结果暂存下来的中间层」）。
- 自造压缩黑话：不带注入 1 / 5（「降本增效」），带注入 0 / 5。**但这一条不构成成效证据**：
  该类别基线为零（见 `docs/superpowers/plans/2026-09-15-baseline.md`），n=1，本来就没什么可下降的；
  且「降本增效」是现成的中文成语，是否算 `rules.md`「要改的」表里那种自造压缩黑话存疑。
- **英文夹杂两组都是 0 / 5，这一条没有观测空间**：Task 2 的 RED 基线已经显示模型本来就不夹英文，
  所以不能用它当成效证据（基线文件当时已写明要重点看「术语不解释」）。
- 判据后半条「代码标识符、路径、命令、公认缩写、专业术语未被改写」**本次没有覆盖**——
  这个写作任务里就没有这些内容。它们的保护靠 `rules.md` 的「保留」段，不是靠这次取样。

**三、顺带的发现：本次取样里，agent 会自己去读放在仓库里的规则文件**

- 跑在 `deepseek-flash` 上（`CLAUDE_CODE_SUBAGENT_MODEL`），不能外推到 Opus。
- GREEN **第一轮的 10 个样本全部作废**：对照组 5 / 5 的 subagent 自己打开并照着写了工作目录里的
  `skills/plain-language/rules.md`——4 个在回答里引用了它；第 5 个专门写了一段
  「需要上报的关键发现：本次会话没有收到规则注入」，并列出查证证据（`settings.json` 的
  `enabledPlugins` 只有 `superpowers@superpowers-dev`、`installed_plugins.json` 同样只有 superpowers、
  `known_marketplaces.json` 里没有 `shared-skills`、可用 skill 列表里没有 `plain-language`）。
  也就是说在**本仓库**里，「不带注入」这个对照条件根本不成立——规则正文就躺在工作目录里。
- 第二轮给两臂**同加**一句中性约束（「这是纯写作任务：直接凭你的知识写，不要读文件、不要使用任何工具。」），
  两臂工具调用均为 0 次，对照条件才成立；两轮里唯一的组间差别始终只有注入本身。
- 对读者的意义：规则文件放在 agent 读得到的地方，就等于多了一条不受控的注入通道。
  评估「没装插件会怎样」时不能假定 agent 看不到它。
- 这一污染不影响上面的 A/B 结论：A/B 两臂的 prompt 都内联了规则正文，且工具权限对两组等价。

**本次实测覆盖不到的**

- `superpowers:writing-skills` 的另一条断言——「要改的」本质是禁止清单，对「输出形状」类问题禁止式会反效果、该改用配方式——本次没有覆盖：A/B 只测了豁免句。这一条仍然是假设，没有证据。
- 只跑了同一个写作任务，换任务类型（代码注释、提交信息、长文档）没有验证。
- 「模型照着眼前的规则写」不等于「规则长期驻留上下文后仍然生效」：`compact` 之后还认不认，本实验覆盖不到。
- 端到端没验：没有真的装插件、让 SessionStart hook 开一次会话。

### 出错兜底

hook 绝不能让会话开不起来：读不到文件、JSON 转义失败、任何异常，一律 `exit 0` 且不输出内容
（静默不注入）。宁可少注入一次，不能挡住开会话。

### 测试计划

| # | 测什么 | 怎么测 | 通过标准 / 结论 |
|:---|:---|:---|:---|
| 1 | RED 基线：模型自然会写黑话吗 | 不带注入跑写作任务，5 次取样，逐条人工读 | 记录原话；若基线不犯，这功能就没有存在理由 |
| 2 | GREEN 注入有效吗 | 同样任务带注入跑，同样 5 次取样 | 黑话与英文夹杂的出现次数下降；代码标识符、路径、命令、公认缩写、专业术语未被改写。**已完成（`deepseek-flash`）：未解释的术语 5 / 5 → 0 / 5，见「措辞实测结论」二；英文夹杂两臂都是 0，没有观测空间；后半条本次未覆盖** |
| 3 | 方案乙的致命点：会不会读 `rules.md` | 带注入调用 plain-language skill | 确实读了 `rules.md` 并照它改，而不是只看 SKILL.md 就动手。**已完成（`deepseek-flash`）：5 个一次性 subagent 5 / 5 都读取了 `rules.md` 并照它改，改动理由引用的是规则表里的判据（例如「闭环保留：读者一次就能读懂」）；`skills/plain-language/SKILL.md` 自那次取样之后没有再改过，结论对当前产物仍然成立。本项只有结论、没有原始记录（取样时没落盘），第 1、2、4 项的原始输出都随仓库提交了。两条限定：一是取样 prompt 末尾要求 subagent「列出读过的文件」，而被测量的恰好就是「读没读 `rules.md`」，这让该行为变得显眼，属轻度干扰；二是 5 / 5 不能归因于指向句——见「措辞实测结论」三：本仓库里 agent 本来就会自己去读规则文件（Task 4 第一轮 GREEN 的对照组 5 / 5 自己读了 `rules.md`，那一轮因此作废重跑）。只在 `deepseek-flash` 上跑，不可外推到 Opus** |
| 4 | 豁免句到底管不管用 | 限定语写豁免句 vs 不写，两组对照 | 两组有差别才采用豁免句。**已完成（`deepseek-flash`）：四个观测点两组完全相同（代码块 0 / 5 vs 0 / 5、API 0 / 5 vs 0 / 5、REST / GraphQL 2 / 5 vs 2 / 5、QPS 5 / 5 vs 5 / 5），故不写豁免句，见「措辞实测结论」一** |
| 5 | hook 本身没坏 | `bash hooks/verify.sh` | 输出是合法 JSON、注入文本的结尾与 `rules.md` 原文逐字一致、限定语块结尾结构完整（`rules.md` 原文前紧接 `</EXTREMELY_IMPORTANT>` 加一个空行）、含关键词；`run-hook.cmd` 的输出与直接调用 `session-start` 一致 |

第 2、3、4 项已于 2026-09-15 完成——第 2、4 项的结论见上面的「措辞实测结论」，
第 3 项的结论见表中该行；三条结论都只跑在 `deepseek-flash`（`CLAUDE_CODE_SUBAGENT_MODEL`）上，
不能外推到 Opus。

取样一律用一次性 subagent，每次全新上下文，5 次以上，命中的样本逐条人工读——
自动计数会把模板回显和引用的反例也算成命中。

## 已知局限

- `CLAUDE_CODE_SUBAGENT_MODEL` 是 `deepseek-flash`，subagent 测试跑的是那个模型，
  **结论不能直接外推到 Opus**。报告里每一条结论都要标注这个局限
- 不安装插件，就无法做真实会话的端到端验证。`verify.sh` 只覆盖 hook 脚本本身，
  覆盖不到「Claude Code 确实读了 hooks.json 并执行了它」
