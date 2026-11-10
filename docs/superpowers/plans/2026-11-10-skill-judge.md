# skill-judge 技能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 发布一个自包含的技能，用于审查、创建和编辑 Agent Skill，输出带严重等级的问题清单。

**Architecture:** 单个 `SKILL.md`，判据、协议、严重等级、报告模板全部内嵌；不带脚本、不带 `references/`。三种用法共用一套判据。

**Tech Stack:** Markdown（Claude Code 插件技能）；仓库检查脚本 `checks/verify.sh`。

**Spec:** `docs/superpowers/specs/2026-11-10-skill-judge-design.md`

## Global Constraints

- 技能只有一个文件：`plugin/skills/skill-judge/SKILL.md`；不带 `scripts/`、`references/`、技能目录下的 `README.md`。
- 不新增 `evals/` 用例，不加 `checks/verify.d/` 模块。
- 自包含：正文不出现任何仓库的页面名、路径或规则名。示例用通用例子（文档处理、数据转换这类）。
- 正文用中文；不得出现码点大于 U+FFFF 的字符（emoji 等）。
- 文风按本仓库既有技能：表格、判据、为什么，少用比喻。
- 只列问题与严重等级；不评分、不给总等级、不判通过与否、不设 Top 3。
- 被评对象必须读全：`references/`、`assets/` 的文本与 `scripts/` 正文整份读，不抽样、不跳读。
- 版本号两处一起改成 `1.30.0`；根 `README.md` 技能表补一行，收录数改为 13。
- 所有命令在 `C:\Study\shared-skills` 下运行。

## Review Focus

1. **创建时没有文件可审**：创建触发后，技能要先按判据指导写法，草稿落盘后再自查；写成只在有文件时工作，创建阶段就用不上。对应 Task 1 Step 3 与 Task 3 Step 2。
2. **手动触发的技能被误判**：`disable-model-invocation: true` 时缺 WHEN 只能记中，不能记高。对应 Task 1 Step 5 与 Task 3 Step 2。
3. **缺席类问题没有行号**：缺完成判据、缺反向边界必须能用 `SKILL.md:1-<总行数>（全文无该节）` 写证据，否则会被「指不到就不报」吞掉。对应 Task 1 Step 7 与 Task 3 Step 2。
4. **被评对象读不全**：任何抽样、跳读都会漏问题；正文必须写明整份读。对应 Task 1 Step 7 与 Task 3 Step 2。
5. **报告混入评分或 Top 3**：报告模板只能有结论与高、中、低三节。对应 Task 1 Step 8 与 Task 3 Step 2。

---

### Task 1: 写出 SKILL.md

**Files:**
- Create: `plugin/skills/skill-judge/SKILL.md`

**Interfaces:**
- Consumes: 无。
- Produces: 技能文件。后续任务只做仓库登记与验证，不再改它的正文。

- [ ] **Step 1: 建目录与 frontmatter**

创建 `plugin/skills/skill-judge/SKILL.md`，开头写：

```yaml
---
name: skill-judge
description: "审查、创建或编辑 Agent Skill 时使用——按六个审查面加一组跨面检查逐条找问题，列全问题并标严重等级（高/中/低），每条给证据与改法。触发语：评一下这个技能、给这个技能挑问题、审一下 SKILL.md、新建一个技能、改一下这个技能。不评分、不跑实测；不用于判断技能里的领域知识是否正确。"
---
```

检查：`name` 与目录名一致；`description` 不超过 1024 字符。

- [ ] **Step 2: 写标题与边界**

正文开头：

```markdown
# 技能审查

这是静态审查：判的是「写得好不好」，不判「有没有用」。不评分，不给总等级，只列问题与严重等级。

评估模式只读，不改被评技能的任何文件；指导模式只按判据约束怎么写、怎么改，不替使用者决定技能要做什么。
```

检查：开头三句都在，且没有出现「打分」「评级」。

- [ ] **Step 3: 写三种用法**

写 `## 三种用法`，照 spec 的表写三行：

| 时刻 | 规则怎么用 | 产出 |
|:---|:---|:---|
| 创建新技能 | 写之前读一遍七个组的判据，按它定 description、流程、边界、完成标准、资产形态 | 草稿；草稿落盘后按评估流程自查 |
| 编辑已有技能 | 先读目标技能与判据；按判据改。改动前先出一次问题清单供挑，改完再复审 | 改前的问题清单；改后的剩余问题与这次改动新引入的问题 |
| 审查已有技能 | 直接按评估流程逐面检查 | 问题清单 |

表后写：「三种用法只有入口不同，判据是同一份。创建时还没有文件，第 0 步的定位先跳过，草稿落盘后再跑。」

检查：三行都在；创建那一行写明草稿落盘后自查。

- [ ] **Step 4: 写五条设计建议**

写 `## 对好技能的五条设计建议`，照 spec 的表逐行写全：按需加载、及早短路、优先脚本、尽量精简、职责清晰。每行含「含义」和「在哪个组查」。

表后写：「这五条是给被评技能的建议，不是本技能自己的运行原则。五条不单列一类，按所属组记进问题清单。」

检查：五条一条不少；职责清晰那一行写明面 1、面 4、面 6、组 7。

- [ ] **Step 5: 写七个审查组**

写 `## 审查什么`，下分七节：

- `### 面 1：触发`
- `### 面 2：知识差`
- `### 面 3：流程`
- `### 面 4：边界`
- `### 面 5：完成`
- `### 面 6：资产`
- `### 组 7：跨面`

每节照 spec 的「查什么」「什么算问题」逐条写全，不得省略。必须包含：

- 面 1 的 `disable-model-invocation: true` 规则：手动触发时缺 WHEN 记中，不记高；「该自动触发却设成手动」不判。
- 面 1 的 frontmatter、name 格式、description 长度、职责范围检查。
- 面 2 的 E/A/R 三类，以及「有 `model` 按 `model`，没有按当前模型」。
- 面 3 的及早短路检查，以及「前置条件不检查、出错还继续跑记高」。
- 面 4 的相邻技能界限，以及「把别的技能的职责抄进来记中」。
- 面 5 的完成判据、自验动作、结构化模板。
- 面 6 的按需加载、优先脚本、文件分工、整份读脚本、安全检查、孤儿引用、断链。
- 组 7 的职责清晰、尽量精简、一致、时效、默认方案、语气、流程图、结构。

检查：七节齐全；上述每一条都能在正文里找到。

- [ ] **Step 6: 写严重等级**

写 `## 严重等级`：高、中、低三档的判据与例子，照 spec 的表。表后写三条边界规则：

- 同一问题出现在多处，合成一条，列出各处行号，等级按最重的那处算。
- 拿不准是「中」还是「低」时，按「会不会让使用者做错一次」判：会，取中；不会，取低。
- 不把「写得不够漂亮」报成高。

检查：三档定义与三条规则都在。

- [ ] **Step 7: 写评估流程**

写 `## 怎么审`，六步：

1. **第 0 步：定位并校验**。技能的形状是一个目录加 `SKILL.md`；给名字就在 `plugin/skills/`、`.claude/skills/`、`~/.claude/skills/`、`~/.agents/skills/` 下找；给目录或 `SKILL.md` 路径就直接用；没有 `SKILL.md`、路径不存在、读不到就直说并停；没给参数就列出能找到的技能让使用者选；一次多个就逐个评，无效的单独说明；不合并、不排名。
2. **第 1 步：读包**。读完目标技能的 `SKILL.md`；`references/`、`assets/` 下的文本文件整份读；`scripts/` 下的脚本正文整份读，不执行、不抽样、不跳读，文件大就分多次读完；图片、字体只登记不读；读不完就停下，说明哪几份没读完，相关审查面不出结论，报告结论写明覆盖范围。
3. **第 2 步：逐面检查**。七个组按顺序过；评估时问「这里有没有可指出的问题」，创建和编辑时问「这一条定了没有、按什么定」；记下审查面、问题、证据、改法、严重等级。证据能指到行就指到行；缺席类问题按两种写法：有对应小节就指那一节的标题行，全文都没有就写 `SKILL.md:1-<总行数>（全文无该节）`。除这两种，指不到位置就不报。
4. **第 3 步：合并**。同一处的多个问题合成一条；同一类问题在多处出现合成一条，列出各处行号。
5. **第 4 步：排序**。按严重等级从高到低；同等级按触发、知识差、流程、边界、完成、资产、跨面。
6. **第 5 步：出报告**。按下一步的模板。

检查：六步齐全；第 1 步写明「整份读、不抽样」；第 2 步写明缺席证据的两种写法。

- [ ] **Step 8: 写报告模板与假阳性防线**

写 `## 报告长什么样`，照 spec 的模板写：`## 结论`、`## 高`、`## 中`、`## 低` 四节，每条问题写「审查面、问题、证据、改法」，编号跨等级连续。模板后写五条规则：

- 没有问题的等级不写；一个问题都没有时，只写「没发现问题」。
- 不写「总评几分」「是否通过」「Top 3」这类结论。
- 有文件没读完时，结论里写明哪些没覆盖，相关审查面不写「查过」。
- 缺席类问题的证据照第 2 步的格式写，例如 `SKILL.md:1-66（全文无完成判据）`。
- 报告在对话里出，不落盘。

写 `## 评估时不要做`，照 spec 的假阳性防线逐条写全，至少包含：

- 不因行数少判差，不因行数多判好。
- 不要求每个技能都有禁令清单、流程图、脚本、模板、`references/`。
- 不把「没写某一节」一律算问题。
- 不把给人看的说明文件算问题。
- 不报「没有评测用例」「没有测试」。
- 没读全就不出完整结论；读不到的文件不猜。
- 拿不准就不报；报了就必须能指到位置。

检查：报告模板只有结论与三档；不出现评分、总评、Top 3；假阳性防线逐条在。

- [ ] **Step 9: 机械检查**

运行：

```bash
cd /c/Study/shared-skills
grep -n "^## " plugin/skills/skill-judge/SKILL.md
grep -nE "pages/|techblog/|C:" plugin/skills/skill-judge/SKILL.md
grep -nP "[^\x00-\x{FFFF}]" plugin/skills/skill-judge/SKILL.md
wc -l plugin/skills/skill-judge/SKILL.md
```

预期：

- 第一条列出全部章节，含「三种用法」「对好技能的五条设计建议」「审查什么」「严重等级」「怎么审」「报告长什么样」「评估时不要做」。
- 第二条无输出（没有外部路径）。
- 第三条无输出（没有超出 BMP 的字符）。
- 行数不超过 500。

- [ ] **Step 10: 提交**

```bash
git add plugin/skills/skill-judge/SKILL.md
git commit -m "feat(skill-judge): 新增技能审查技能"
```

### Task 2: 登记到 README 并抬版本号

**Files:**
- Modify: `README.md`（技能表与收录数）
- Modify: `plugin/.claude-plugin/plugin.json`（`version`）
- Modify: `.claude-plugin/marketplace.json`（`version`）

**Interfaces:**
- Consumes: Task 1 产出的技能文件。
- Produces: 仓库登记与版本号，供发布使用。

- [ ] **Step 1: README 技能表加一行**

在 `skill-ledger` 那一行之后插入：

```markdown
| `skill-judge` | 审查、创建或编辑 Agent Skill 时用：按六个审查面加一组跨面检查逐条找问题，列全问题并标严重等级（高/中/低），每条给证据与改法。不评分、不跑实测，也不判断技能里的领域知识是否正确。 |
```

检查：`grep -n "skill-judge" README.md` 能命中。

- [ ] **Step 2: 改收录数**

把第 7 行的「当前收录 **11** 个。」改成「当前收录 **13** 个。」。表里原来有 12 行，数字本来就旧；加上本技能是 13 行。

检查：

```bash
sed -n '/^## 收录的 skill/,/^## 安装/p' README.md | grep -c '^| `'
```

预期输出 `13`。

- [ ] **Step 3: 两处版本号抬到 1.30.0**

`plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 的 `version` 都从 `1.29.4` 改成 `1.30.0`。

检查：`grep -n '"version"' plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json` 两条都是 `1.30.0`。

- [ ] **Step 4: 提交**

```bash
git add README.md plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "docs(skill-judge): 登记技能并抬版本号"
```

### Task 3: 验证

**Files:**
- Modify: `plugin/skills/skill-judge/SKILL.md`（仅当验证发现问题时）

**Interfaces:**
- Consumes: Task 1 与 Task 2 的产出。
- Produces: 可提交的最终状态。

- [ ] **Step 1: 跑仓库检查**

```bash
cd /c/Study/shared-skills
bash checks/verify.sh --changed
```

预期：通过。若报版本号未抬或两处不一致，按 Task 2 Step 3 修正后重跑。

- [ ] **Step 2: 自审技能本身**

读 `plugin/skills/skill-judge/SKILL.md`，逐条核对：

- `description` 覆盖审查、创建、编辑三个时刻。
- 正文有「三种用法」，创建时跳过第 0 步、草稿落盘后自查。
- 五条设计建议都在，且职责清晰映射到面 1、面 4、面 6、组 7。
- 面 1 写明手动触发时缺 WHEN 记中、不记高。
- 第 1 步写明 `references/`、`assets/` 文本与 `scripts/` 正文整份读，不抽样。
- 第 2 步写明缺席类问题的两种证据写法。
- 报告模板只有结论与高、中、低三节，没有评分、总评、Top 3。
- 假阳性防线逐条在。
- 没有外部路径，没有超出 BMP 的字符。

检查：以上每一条都能在文件里找到；找不到就回到 Task 1 对应步骤补。

- [ ] **Step 3: 冒烟检查**

用这个技能审 `plugin/skills/skill-ledger`。按技能里的报告模板输出一份清单，只检查输出形态：

- 结论一句，写明七个组查过哪些、有没有没读完的文件。
- 问题按高、中、低分节；没有问题的等级不出现。
- 每条有审查面、问题、证据、改法；证据指到 `SKILL.md` 的具体行，或缺席类的全文写法。
- 不出现分数、总等级、通过与否、Top 3。

**只审不改**：不改 `skill-ledger` 的任何文件。若输出形态不对，问题在 `skill-judge` 自身，回到 Task 1 修。

- [ ] **Step 4: 重跑检查**

修过 Task 1 的话，重跑：

```bash
bash checks/verify.sh --changed
```

预期：通过。

- [ ] **Step 5: 提交修复（如果有）**

```bash
git add plugin/skills/skill-judge/SKILL.md
git commit -m "fix(skill-judge): 按自审结果修正技能正文"
```

没有修改就跳过这一步。
