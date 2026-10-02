# test-case-design 落成环节的问题清单

来源：2026-10-02，在 `C:\investment\.claude\evals\business-term-builder\` 拿本技能的产出（六份通用稿＋第七份实施方案规格说明）落成 skill-up 评测配置，并准备跑测。下面六条是这次撞到的问题，附实测证据与落点建议。

现场材料（只读，不要改）：`C:\investment\.claude\evals\business-term-builder\`

- 七份设计稿在 `test-case-design\`
- 落成的成品在 `eval.yaml`、`cases\`、`fixtures\`

用户说这批产出只是测试用的、会删掉重试，所以不要修它们。

---

## 问题 1：落成的人拿不到落成指南

**现象**：落成的人手上只有第七份。第七份的「成品落点」块说「落成之后回来把这张表补上」，但没说落成要读哪些文件、跑哪些脚本。落成的人不知道这个技能还有 `SKILL.md`，也不知道有 `references/评测方案/skill-up/usage-notes.md`。

**代价（实测）**：为摸清 skill-up 的机制跑了 5 次探测会话。其中 3 次是 usage-notes 已经写明的：

| 实测摸出来的 | usage-notes 里早有 |
|:---|:---|
| eval.yaml 不在技能根下时，相对路径退让到上一层（validate 跑了 3 次才对） | 第七节 |
| `setup_steps` 跑在装技能与铺夹具之前（2 次会话） | 第六节，写了「次序写死」 |
| 差集怎么算、夹具侧要不要自己 commit（2 次会话） | 第二节 |

**要改的地方**：

- `references/文档模板.md` 第十节末尾那句「落成那一步读哪三样……见 `SKILL.md` 的某一节」——它确实指了，但落成的人手上没有技能本体的路径，指过去也找不到。改成带技能名的直指。
- `SKILL.md` 的「落成那一步手上要有哪三样」（现第 166 行）——现在是三样，加第四样：`references/评测方案/skill-up/usage-notes.md`。理由：那三样讲「要什么」，usage-notes 讲「实际跑起来是什么样」，后者正是落成时会撞上的。

## 问题 2：技能没有「只做落成」这个入口

**现象**：`SKILL.md` 有两个补做入口——「手上已经有一组用例、不是从零设计时」（现第 174 行，补覆盖项与用例）与「只出实施方案那一份」（现第 178 行，补第七份）。没有「七份都在手上，只做落成」这一条。

**代价**：落成的人只能自己拼流程，于是漏掉了技能自带的两个校验脚本（见问题 3）。

**要改的地方**：`SKILL.md` 加一节「只做落成」，与另两个入口并列。内容大致是：读哪几样（含 usage-notes）→ 照第七份摆文件 → 补「成品落点」表 → 跑 `check_docs.py` 与 `check_landing.py` → 报差异。

## 问题 3：两个校验脚本没进落成流程

**现象 1**：`check_docs.py` 抓到了补上去的落点表形制错误。但没人说「落成改了第七份之后要重跑它」——`SKILL.md` 只在设计阶段的第 6、7 步提它。

**现象 2**：「成品落点与落成对照」一节里，「成品写在住着别的东西的那一层上时，命令上把成品路径一条条点出来」这句没有例子。评测材料根那一层通常住着 `runs\`（跑测产物），正是这种情形。

**要改的地方**：

- `SKILL.md` 的「成品落点与落成对照」（现第 152 行）里，把验收写成两条命令、都要跑：`check_docs.py <产出目录>`（补完落点表后必跑）与 `check_landing.py <产出目录> <成品路径...>`。
- `references/文档模板.md` 第十节补一句：落点表的单元格只写路径，说明文字挪到表下——脚本会把整格当路径读，带说明就读不到。（实测：`` `cases/`（13 个 `.yaml`） `` 整格读不到，报「读不到：cases/`（13 个 `.yaml`）」）
- 同上，补一个「成品路径一条条点出来」的例子。

## 问题 4：usage-notes 缺两条这次实测出来的要点

**要点 1**：铺夹具会跳过名字以 `.` 开头的文件与目录。`fixtures\` 里的 `.claude/rules/` 连同 `pages/.gitkeep` 一起被跳过，一份都没铺进工作区。要铺只能走用例配置的 `context.files` 逐条写。usage-notes 第二节只讲了「夹具排在最末、会盖掉 `setup_steps` 写下的东西」，没讲这条过滤。

**要点 2**：被测技能引用的工作区外文件要主动补。这次被测技能的 `SKILL.md` 引用 `../../rules/数据支撑规则.md` 等三份规则，工作区里一份都读不到——技能跑起来会如实报告「规则文件不存在」，而判据「按数据支撑规则的引用块格式标注缺口」就成了死判据。落成时要扫一遍被测技能文档里的引用路径，逐个确认工作区里可达；不可达的走 `context.files` 铺。

**要改的地方**：`references/评测方案/skill-up/usage-notes.md` 第二节补要点 1；要点 2 新增一条（或并入第六节），并写成可执行的动作——扫 SKILL.md 的引用路径，逐个确认工作区可达。

## 问题 5：`/skill-upper` 的 install.md 与本技能的 usage-notes 打架

**现象**：`/skill-upper/references/install.md` 第 10 行写 `Platforms: macOS and Linux only. Windows is not currently supported.`；本技能的 usage-notes 第四节写「skill-up 原生支持 Windows……照那句判，会把环境白改成 WSL2」。

**后果**：落成的人读的是 `/skill-upper`（落成清单里的第三样），读不到本技能 usage-notes 里的纠正。

**要改的地方（注意约束）**：`/skill-upper` 是第三方技能，**不改它**。改法是在我们自己的技能里写明：**两边冲突时以 usage-notes 为准**。落点两处，建议都写：

- `SKILL.md` 的「落成那一步手上要有哪三样」第 3 条（讲 `/skill-upper` references 那句）后面加一句：它没写到、或与 `references/评测方案/skill-up/usage-notes.md` 冲突的，以 usage-notes 为准。
- `references/评测方案/skill-up/usage-notes.md` 第四节补一句：`/skill-upper` 的 install.md 与本节冲突时以本节为准。

## 问题 6：落成时的新发现没有回流路径

**现象**：usage-notes 末尾有「换版本之后怎么重核」，管的是 skill-up 版本变更。没有「落成时撞见的新折扣怎么回写」。

**要改的地方**：`SKILL.md` 新增的「只做落成」一节末尾加一步：落成时撞见的、usage-notes 里没有的折扣，回写进 usage-notes，照它现有体例标注实测日期与版本。

---

## 顺带记下的两条小项

- **`--no-delete` 保留的工作区落在哪，usage-notes 没写**。实测落在 `%TEMP%\skill-up-<随机数>`。
- **设计稿 ENV-3 的「铺完夹具后提交一次初始快照」与实况不符**。skill-up 自己在会话前后拍快照算差集（精确到行），夹具侧不用 commit；也 commit 不了——`setup_steps` 跑在铺夹具之前，那时工作区还是空的。这条要落到 usage-notes 第二节。
