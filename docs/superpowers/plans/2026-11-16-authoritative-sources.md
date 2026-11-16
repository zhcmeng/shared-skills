# 权威数据源技能（authoritative-sources）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 shared-skills 新增 `authoritative-sources` 技能与一条全局常驻检索强度规则，并把 investment 的 `source-classifier` 与 `检索强度规则` 的通用部分搬过去。

**Architecture:** 纯提示词交付，没有脚本。一个技能目录装四个文件：`SKILL.md` 做导航与检索纪律，`references/` 下放信源分级与两个行业数据源。另加一条约 20 行的常驻规则到 `plugin/rules/`，由插件同步到配置目录后对所有工程生效。investment 侧删掉被搬走的技能，改 17 处引用，规则文件只留本地素材层表。

**Tech Stack:** Markdown（YAML frontmatter + 正文）；校验用仓库自带的 `bash checks/verify.sh`。

**Spec:** `C:\Study\shared-skills\docs\superpowers\specs\2026-11-16-authoritative-sources-design.md`（附录 A、B 是数据源文件的实施输入）

## Global Constraints

- 所有正文用中文。不出现 emoji 这类非 BMP 字符（码点大于 U+FFFF）。
- 技能目录名 `authoritative-sources`，frontmatter 的 `name` 必须与目录名一致。
- 技能正文不出现 investment 的任何路径、目录名、规则文件名（`web-materials-md`、`research-reports-md`、`SOP.md`、`.report-index`、`.qmd`、`pages/` 等）。
- 不假定使用者做投资：不写「投资者」「估值」「买卖决策」这类词。信源分级里的「券商研报」「年报」「招股说明书」只作示例保留。
- 版本号：`plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 两处一起，`1.32.1` → `1.33.0`。
- 提交信息用中文，格式 `类型(范围): 描述`，末尾加 `Co-Authored-By: Claude <noreply@anthropic.com>`。
- 两个仓库分别提交：`C:\Study\shared-skills` 与 `C:\investment`。

## Review Focus

1. **触发词覆盖不全**：用户问「游戏行业的数据去哪找」「这个数字可信吗」时不触发技能。每个任务写完 description 后，用这三种问法各读一遍 description，确认都能命中。
2. **数据源 URL 失效**：附录里的 URL 是 2026-11-16 核实的，落盘前逐条确认格式可打开（至少确认不是空串、不含本机路径）。
3. **17 处引用改漏**：Task 7 结束时用 grep 查残留，输出必须为空。
4. **常驻规则过长**：`plugin/rules/检索强度.md` 超过 30 行就是失败，细节应留在技能里。
5. **技能正文混入工程路径**：Task 1-4 每个文件写完后用 grep 查一遍 `investment|web-materials|research-reports|SOP\.md|pages/`，输出必须为空。

---

### Task 1: 技能主体 `SKILL.md`

**Files:**
- Create: `plugin/skills/authoritative-sources/SKILL.md`

**Interfaces:**
- Produces: 技能名 `shared-skills:authoritative-sources`；正文里的数据源目录表指向 `references/信源分级.md`、`references/中国游戏行业.md`、`references/全球游戏市场.md` 三个文件（Task 2-4 创建）。

- [ ] **Step 1: 写 frontmatter**

```yaml
---
name: authoritative-sources
description: "检索行业或市场数据之前，先确认该去哪些权威来源、这些来源的口径差别、搜到什么程度算够。按行业挂载数据源清单（当前：中国游戏行业、全球游戏市场），问题落到哪个行业才读哪个文件。同时用于判断某个来源的权威等级与证据是否充分。不用于：下载入库、引用格式校验、替代实际检索。"
---
```

不加 `disable-model-invocation`——需要模型在检索前自动调用。

- [ ] **Step 2: 写第一节「什么时候用 / 不用」**

三行：
- 用：开始检索行业数据、市场数据、行业规模、公司经营数据之前；需要判断某个来源能不能当证据时；判断证据够不够时。
- 不用：具体下载与入库（交给调用方自己的流程）；引用格式校验；纯概念解释（「什么是 X」不需要检索）。
- 一句话原则：本技能给的是**判断与目录**，不代替打开页面核实。

- [ ] **Step 3: 写第二节「检索纪律」**

五个子节，内容按 spec「技能结构」第 2 条，依次为：

1. 先本地、后外部：所在工程有本地素材库或检索工具时先查本地；本技能管外部来源的选择。
2. 哪些回答必须实际检索：事实性数据、行业判断、公司信息、状态声明、对比判断。简单概念定义可以基于已有知识。
3. 搜多少算够，两档：单点事实写「1 个权威一手源，标到年份加章节或页码」；系统性整理写「至少 4 轮不同角度检索、6 个独立来源、3 个一级或二级来源、每个并列子主题各有专门信源、关键结论至少 2 个独立来源，单源标待复核」。
4. 什么主题找什么信源：表格四行——行业规模与格局找政府统计与行业协会；公司经营找年报与公告；宏观政策找央行、统计局、发改委；市场行情找交易所与官方数据。表下一句：媒体与自媒体只作辅助，不作关键结论的唯一依据。
5. 搜不到怎么办：先穷尽路径（换关键词、换语言、换角度）；如实标注缺口成因与已尝试范围；可以降级用次级信源但标明性质与局限；禁止用训练数据脑补、禁止把单一来源写成公认事实。

末尾加「自检」五条与「反模式」五条，各一行一条，从 spec 里压缩。

- [ ] **Step 4: 写第三节「数据源目录」**

```markdown
| 数据源 | 文件 | 什么时候读 |
|:---|:---|:---|
| 信源分级 | `references/信源分级.md` | 需要判断某个来源的等级、或判断证据够不够时 |
| 中国游戏行业 | `references/中国游戏行业.md` | 问题涉及中国游戏市场的规模、用户、版号、买量、公司经营 |
| 全球游戏市场 | `references/全球游戏市场.md` | 问题涉及全球或海外游戏市场，或需要与中国对比 |
```

表下一句：**只读当前问题落到的那一个文件，不要一次读完。**

- [ ] **Step 5: 写第四节「加新数据源」**

三行：在 `references/` 下按 `中国游戏行业.md` 的骨架写一个文件；目录表加一行；不修改其他文件。骨架的六节：核实日期、数据难点、按用途查源、口径陷阱、机构状态变化、交叉验证建议。

- [ ] **Step 6: 检查**

```bash
grep -nE 'investment|web-materials|research-reports|SOP\.md|pages/' C:/Study/shared-skills/plugin/skills/authoritative-sources/SKILL.md
wc -l C:/Study/shared-skills/plugin/skills/authoritative-sources/SKILL.md
```

预期：grep 无输出；行数在 60-100 之间（超过 100 说明把细节写进了主体，应移到 references）。

- [ ] **Step 7: 用三种问法读 description**

逐句读 `description`，确认下面三种问法都能命中：`游戏行业的收入数据去哪找`、`这个来源可靠吗`、`搜到什么程度算够`。命中不了就改 description 的措辞，不改触发词列表的长度。

- [ ] **Step 8: 提交**

```bash
git -C C:/Study/shared-skills add plugin/skills/authoritative-sources/SKILL.md
git -C C:/Study/shared-skills commit -m "feat(authoritative-sources): 新增技能主体与数据源目录"
```

### Task 2: `references/信源分级.md`

**Files:**
- Create: `plugin/skills/authoritative-sources/references/信源分级.md`
- Source: `C:\investment\.claude\skills\source-classifier\SKILL.md` 与 `references/standards.md`（合并）

**Interfaces:**
- Consumes: 无。
- Produces: 三级定义与判定顺序，Task 3、4 的「分级」列按这里的口径填。

- [ ] **Step 1: 合并两个源文件为一个**

节顺序：
1. 开头一句：把「在商业研究和投资分析中」改为「在研究与分析中」。
2. 判定顺序：四步，GitHub 黑名单优先，然后官方背景、专业深度加工、网络碎片。
3. 三级定义：每级写定义、特征、典型来源（各 3-4 条）、使用场景。
4. 易误判来源：百科与维基按三级；微信公众号除官方机构认证账号外按三级。
5. GitHub 黑名单：禁用作信源，唯一允许用途是作线索入口；无法回溯则该信息不进正文证据链。
6. 三级信源引用约束：不作孤证；引用处加引用块标注局限性（格式照原文）；要求向上溯源。
7. 证据支撑判断：至少 1 个一级，或 2 个互不相关的二级。
8. 交叉验证：高等级信源不等于绝对真理，不同等级、不同立场互验。

删除源文件里指向 `概念-CRAAP测试` 的链接，改成一句「可从时效、相关、权威、准确、目的五个维度辅助判断」，不写链接。

- [ ] **Step 2: 检查绑定**

```bash
grep -nE 'investment|pages/|CRAAP|\.md\)' C:/Study/shared-skills/plugin/skills/authoritative-sources/references/信源分级.md
```

预期：无输出（除本文件自身名称外）。若有 `pages/` 或 `CRAAP` 链接，删掉。

- [ ] **Step 3: 检查分级口径一致**

逐条读三级定义，确认：一级含「法律披露义务」；二级含「二次加工、深度分析」；三级含「仅用于发现线索」。这三句是 Task 3、4 分级列的依据。

- [ ] **Step 4: 提交**

```bash
git -C C:/Study/shared-skills add plugin/skills/authoritative-sources/references/信源分级.md
git -C C:/Study/shared-skills commit -m "feat(authoritative-sources): 迁入信源分级标准"
```

### Task 3: `references/中国游戏行业.md`

**Files:**
- Create: `plugin/skills/authoritative-sources/references/中国游戏行业.md`
- Source: spec 附录 A

**Interfaces:**
- Consumes: Task 2 的分级口径。
- Produces: 中国区 14 条数据源，每条含「要回答什么 / 首选源 / 分级 / 频率 / 是否免费 / URL / 核实状态」。

- [ ] **Step 1: 按骨架写六节**

1. 标题与「核实日期：2026-11-16」。
2. 一句提示：本文件是人工维护的清单，不是数据副本；超过 6 个月未核实，引用前重新确认发布频率与官网可用性。
3. 「这个行业的数据难点」：两三句。要点：官方只发审批明细不发汇总；市场收入与用户规模由行业协会发布，统计口径不公开；买量成本只有机构白皮书与媒体转述，没有连续年度序列。
4. 「按用途查源」：照抄 spec 附录 A 的表格（14 行）。
5. 「口径陷阱」：照抄附录 A 的五条。
6. 「机构状态变化」：伽马数据官网失效；data.ai 被 Sensor Tower 收购。
7. 「交叉验证建议」：写三条——市场收入与用户规模用游戏工委年度值，与半年度值跨年不要混；手游市场规模不同机构口径不同，同一张图只用一家的序列；买量成本必须注明是总支出还是单用户成本。

- [ ] **Step 2: 检查附录条目无遗漏**

```bash
grep -c '^|' C:/Study/shared-skills/plugin/skills/authoritative-sources/references/中国游戏行业.md
```

预期：表格行数不少于 16（14 条数据加表头与分隔行）。

- [ ] **Step 3: 检查 URL 无本机路径**

```bash
grep -nE 'C:\\|/Users/|file://' C:/Study/shared-skills/plugin/skills/authoritative-sources/references/中国游戏行业.md
```

预期：无输出。

- [ ] **Step 4: 提交**

```bash
git -C C:/Study/shared-skills add plugin/skills/authoritative-sources/references/中国游戏行业.md
git -C C:/Study/shared-skills commit -m "feat(authoritative-sources): 挂载中国游戏行业数据源"
```

### Task 4: `references/全球游戏市场.md`

**Files:**
- Create: `plugin/skills/authoritative-sources/references/全球游戏市场.md`
- Source: spec 附录 B

**Interfaces:**
- Consumes: Task 2 的分级口径。
- Produces: 全球区 19 条数据源，结构同 Task 3。

- [ ] **Step 1: 按同一骨架写六节**

「数据难点」要点：全球总量没有统一口径，各家模型覆盖范围不同；移动与主机分开统计；付费机构多，免费摘要少。

「按用途查源」照抄附录 B 表格；「口径陷阱」照抄五条；「机构状态变化」照抄四条。

「交叉验证建议」写三条：全球总量只用一家的模型，不跨机构相加；移动收入用 Sensor Tower 系，主机用公司财报；区域市场用当地协会（美国 Circana、欧洲 GSD、日本 Famitsu），不用全球模型下切。

- [ ] **Step 2: 检查条数与 URL**

```bash
grep -c '^|' C:/Study/shared-skills/plugin/skills/authoritative-sources/references/全球游戏市场.md
grep -nE 'C:\\|/Users/|file://' C:/Study/shared-skills/plugin/skills/authoritative-sources/references/全球游戏市场.md
```

预期：表格行数不少于 21（19 条加表头与分隔行）；第二条命令无输出。

- [ ] **Step 3: 提交**

```bash
git -C C:/Study/shared-skills add plugin/skills/authoritative-sources/references/全球游戏市场.md
git -C C:/Study/shared-skills commit -m "feat(authoritative-sources): 挂载全球游戏市场数据源"
```

### Task 5: 全局常驻规则 `plugin/rules/检索强度.md`

**Files:**
- Create: `plugin/rules/检索强度.md`

**Interfaces:**
- Consumes: 无。
- Produces: 一条对所有工程常驻生效的规则；技能 `SKILL.md` 的完整版与它口径一致。

- [ ] **Step 1: 写规则正文**

标题用与现有规则一致的两级标题（桌面文件都以 `##` 开头），正文不超过 25 行，包含：

1. 事实性内容不得仅凭训练数据作答：具体数字、行业判断、公司信息、状态声明、对比判断，必须实际检索。
2. 两档强度：单点事实 1 个权威一手源，标到年份加章节或页码；系统性整理至少 4 轮角度、6 个独立来源、3 个一级或二级来源，关键结论至少 2 个独立来源。
3. 证据原则：关键结论要有至少 1 个一级，或 2 个互不相关的二级；不足就标「待复核」。
4. 搜不到：如实标注缺口成因与已尝试范围，不用训练数据脑补，不把单一来源写成公认事实。
5. 一句指向：完整的信源分级与按行业数据源清单见 `shared-skills` 的 `authoritative-sources` 技能。

- [ ] **Step 2: 检查长度与无工程绑定**

```bash
wc -l C:/Study/shared-skills/plugin/rules/检索强度.md
grep -nE 'investment|web-materials|pages/|SOP\.md' C:/Study/shared-skills/plugin/rules/检索强度.md
```

预期：行数不超过 30；grep 无输出。

- [ ] **Step 3: 跑规则同步校验**

```bash
bash C:/Study/shared-skills/checks/verify.sh rules
```

预期：通过。该模块遍历 `plugin/rules/*.md`，新文件会自动纳入。

- [ ] **Step 4: 提交**

```bash
git -C C:/Study/shared-skills add plugin/rules/检索强度.md
git -C C:/Study/shared-skills commit -m "feat(rules): 新增全局检索强度规则"
```

### Task 6: README 两张表与版本号

**Files:**
- Modify: `README.md`「收录的 skill」表、「常驻规则」表、正文「十一条」
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

**Interfaces:**
- Consumes: Task 1-5 的产物。
- Produces: 分发信息与版本号一致。

- [ ] **Step 1: 补「收录的 skill」表一行**

按现有行文风格写：技能名 | 用途。用途要与 `SKILL.md` 的 description 一致，不夸大。参考：`检索行业或市场数据之前用：给出权威来源清单、判断来源等级、确定检索强度。数据源按行业分文件挂载，当前有中国游戏行业与全球游戏市场；加新行业只加一个文件。`

- [ ] **Step 2: 补「常驻规则」表一行**

```
| 检索强度（`plugin/rules/检索强度.md`） | 同步到配置目录的 `rules/` 下，由 Claude Code 自动加载 |
```

同时把该节开头的「十一条常驻规则」改为「十二条」。

- [ ] **Step 3: 抬版本号**

两个文件都把 `"version": "1.32.1"` 改为 `"version": "1.33.0"`。

- [ ] **Step 4: 检查一致性**

```bash
node -e "const a=require('C:/Study/shared-skills/plugin/.claude-plugin/plugin.json').version;const b=require('C:/Study/shared-skills/.claude-plugin/marketplace.json').plugins[0].version;console.log(a,b,a===b?'一致':'不一致')"
grep -n '十一条' C:/Study/shared-skills/README.md
```

预期：输出 `1.33.0 1.33.0 一致`；grep 无输出。

- [ ] **Step 5: 跑全量校验**

```bash
bash C:/Study/shared-skills/checks/verify.sh
```

预期：全部通过。

- [ ] **Step 6: 提交**

```bash
git -C C:/Study/shared-skills add README.md plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git -C C:/Study/shared-skills commit -m "docs: 收录权威数据源技能并抬版本号至 1.33.0"
```

### Task 7: investment 删除被搬走的技能并改 17 处引用

**Files:**
- Delete: `C:\investment\.claude\skills\source-classifier\`（整个目录，含 `scripts/classify.py`）
- Modify: 10 个文件，17 处
  - `.claude/skills/cite/SKILL.md`（5 处）
  - `.claude/skills/material-ingest/SKILL.md`（1 处）
  - `.claude/skills/stance-red-team/SKILL.md`（2 处）
  - `.claude/skills/evidence-review/references/scoring-rules.md`（1 处）
  - `.claude/skills/business-insight-builder/disciplines/collect.md`（1 处）
  - `.claude/skills/business-case-builder/references/skill-routing.md`（1 处）
  - `.claude/skills/business-case-builder/case-logic-coach-prompt.md`（1 处）
  - `.claude/skills/business-case-builder/case-evidence-builder-prompt.md`（1 处）
  - `.claude/commands/source-grounding.md`（3 处）
  - `.claude/rules/检索强度规则.md`（1 处）

**Interfaces:**
- Consumes: Task 1 的技能名 `shared-skills:authoritative-sources`。
- Produces: investment 仓内无 `source-classifier` 残留。

- [ ] **Step 1: 逐文件替换引用文字**

用 Edit 逐个改，不用脚本批量替换——17 处句子的上下文各不相同，批量替换会改坏语义。规则：
- 裸技能名 `source-classifier` → `shared-skills:authoritative-sources`
- 相对路径链接 `[source-classifier](../source-classifier/SKILL.md)` → 纯文字 `shared-skills:authoritative-sources`（跨仓库链接不可用）
- `cite/SKILL.md` 第 3 行 description 里的「内部编排 source-classifier（信源分级）」→「内部编排 shared-skills:authoritative-sources（信源分级）」

每个文件替换后，用 `grep -n 'source-classifier' <文件>` 确认归零。

- [ ] **Step 2: 删除目录**

```bash
rm -rf C:/investment/.claude/skills/source-classifier
```

- [ ] **Step 3: 全仓查残留**

```bash
grep -rn 'source-classifier' C:/investment/.claude
```

预期：无输出。有输出就回到 Step 1 补改。

- [ ] **Step 4: 抽查两处改后语境通顺**

读 `cite/SKILL.md` 第 36 行附近与 `source-grounding.md` 第 27 行附近，确认句子读得通、不是生硬替换（例如「调用 `/source-classifier` 定级」要变成「调用 `shared-skills:authoritative-sources` 定级」）。

- [ ] **Step 5: 提交**

```bash
git -C C:/investment add -A .claude
git -C C:/investment commit -m "refactor(skills): 信源分级迁移至 shared-skills 插件

删除本地 source-classifier，10 个文件 17 处引用改指 shared-skills:authoritative-sources。"
```

### Task 8: investment 拆分 `检索强度规则.md` 并补依赖说明

**Files:**
- Modify: `.claude/rules/检索强度规则.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: Task 5 的全局常驻规则。
- Produces: investment 规则文件只留本地素材层表；`CLAUDE.md` 写明插件依赖。

- [ ] **Step 1: 重写 `检索强度规则.md`**

保留：
- 标题与一句总述：本文件只管本地素材层的入口与本地检索工具；通用检索强度见全局规则 `plugin/rules/检索强度.md`（由 shared-skills 插件提供）。
- 本地素材层入口表全部 8 行，原样保留。
- 「检索一律走子代理」这条硬性要求。
- §4 的引用格式衔接（引用规则、素材保存建议、脚注标注）。
- 本地检索工具用法（qmd、query_reports.py）。

删除：检索强度底线、主题与信源对应、搜不到怎么办的完整流程、自检、反模式（这些已进全局规则与技能）。

- [ ] **Step 2: 在 `CLAUDE.md` 补依赖说明**

`CLAUDE.md` 现在只有标题。追加：

```markdown
## 插件依赖

本仓的信源分级与通用检索强度由 `shared-skills` 插件提供：
- 技能 `shared-skills:authoritative-sources`：分级判定、按行业数据源清单（当前有中国游戏行业、全球游戏市场）。
- 常驻规则 `plugin/rules/检索强度.md`：由插件同步到配置目录后自动加载。

插件未安装时，上述能力不可用；`cite`、`source-grounding` 等技能会提示找不到依赖。
```

- [ ] **Step 3: 检查规则文件不残留已删除内容**

```bash
grep -nE '4 轮|6 个独立来源|反模式|自检' C:/investment/.claude/rules/检索强度规则.md
```

预期：无输出（这些已搬到全局规则与技能）。若「自检」仍在，确认它是否属于本地规则的部分；属于就保留。

- [ ] **Step 4: 检查本地表 8 行仍在**

```bash
grep -c '^|' C:/investment/.claude/rules/检索强度规则.md
```

预期：不少于 10（8 行加表头与分隔行）。

- [ ] **Step 5: 提交**

```bash
git -C C:/investment add .claude/rules/检索强度规则.md CLAUDE.md
git -C C:/investment commit -m "refactor(rules): 通用检索强度迁至全局规则，本地只留素材层入口"
```

### Task 9: 全量校验

**Files:** 无改动。

- [ ] **Step 1: shared-skills 全量校验**

```bash
bash C:/Study/shared-skills/checks/verify.sh
```

预期：全部通过。

- [ ] **Step 2: 技能结构检查**

```bash
ls C:/Study/shared-skills/plugin/skills/authoritative-sources/references/
head -5 C:/Study/shared-skills/plugin/skills/authoritative-sources/SKILL.md
```

预期：三个 references 文件都在；frontmatter 的 `name` 是 `authoritative-sources`。

- [ ] **Step 3: investment 残留检查**

```bash
grep -rn 'source-classifier' C:/investment/.claude
ls C:/investment/.claude/skills/ | grep source
```

预期：两条命令都无输出。

- [ ] **Step 4: 全局生效检查**

在任意非 investment 的工程开新会话，确认：
- 项目指令里出现 `plugin/rules/检索强度.md` 的内容。
- 技能列表里有 `shared-skills:authoritative-sources`。

这一步需要人工开一个新会话确认，不能靠命令替代。若无法开新会话，记录为未验证，不写成通过。

- [ ] **Step 5: 提交收尾**

若前几步有修补，按修补内容提交；没有修补则跳过。
