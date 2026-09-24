# 技能台账技能（skill-ledger）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 shared-skills 仓里新增一个只允许手动触发的技能 `skill-ledger`——拿到一个技能，判它该不该配台账，并给出「改哪几处、怎么改」的建议清单。

**Architecture:** 纯提示词交付，没有脚本、没有测试框架。一个 `SKILL.md` 装主流程（判据 → 六件事 → 四处落点 → 清单格式），一个 `references/上游台账机制.md` 装不常用的上游对照与版本出处。收尾按本仓 README「维护」节抬版本号并跑校验。

**Tech Stack:** Markdown（YAML frontmatter ＋ 正文）；校验用仓库自带的 `bash checks/verify.sh`。

**Spec:** `docs/superpowers/specs/2026-09-24-skill-ledger-design.md`

## Global Constraints

- 技能名固定 `skill-ledger`（spec D6），frontmatter 的 `name` 与目录名必须一致。
- frontmatter 必须含 `disable-model-invocation: true`（spec D2）——模型不自动调，只有人打 `/skill-ledger` 能触发。
- 产出是**建议清单，不直接改目标技能的文件**（spec D1）。技能正文里不许出现「改这个文件」这类执行指令。
- 正文讲的是通用机制，**不写死本仓的维护规矩**（spec D7）：不出现 `checks/verify.sh`、不出现 README 补表、不出现抬版本号。「改完跑什么检查」交给目标技能所在仓库自己的规矩。
- 技能文件里**不建公共台账脚本**（spec 第 1 节「明确不是目标」第四条）。
- **不依赖 superpowers**（spec 第 1 节）：正文不许出现「去读上游的 SKILL.md」「先装 superpowers」这类要求——上游只作版本化出处出现在 `references/` 里，装不装都能用。
- 所有正文用中文。按用户常驻规则写：不用行话、不自造压缩词，非用不可的英文就地给中文。
- README 收录表里的那一行必须与 `SKILL.md` 的能力描述一致，不许夸大（比如不许写「自动加上台账」）。
- 抬版本号：`plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 两处一起，`1.16.2` → `1.17.0`（多一个能力，抬中间那位）。
- 本次不动任何现有技能本体。

## Review Focus

下面四类输入，spec 没有明说技能该怎么应对，但真给到时会出问题。每条都落到 Task 1 的某一步里，写成正文里的一句话。

1. **给的不是技能**——收到的是一个普通 Markdown 文件、一个目录、或者不存在的路径。行为预期：技能先确认「拿到的是技能」再往下走，认不出来就直说，不硬产出清单。
2. **目标技能已经有状态文件或台账**——比如仓库里已经有一份进度文件。行为预期：清单要说清「已有那份够不够用」，而不是建议再加一份。
3. **四条信号一条都不中**——比如 `token-counter` 这种一次跑完的技能。行为预期：结论敢写「不该配」，不为了显得有用而硬加。
4. **目标技能的正文不是中文**——行为预期：给出的建议清单用跟用户对话的语言写（默认中文），不跟着目标技能的语言跑。

---

### Task 1: 技能主体 `SKILL.md` 与 README 收录

**Files:**
- Create: `plugin/skills/skill-ledger/SKILL.md`
- Modify: `README.md`（「收录的 skill」表格末尾补一行）

**Interfaces:**
- Consumes: 无（本任务是第一份产出）
- Produces: 技能名 `skill-ledger`；`SKILL.md` 里四个标题 `## 第 1 步：判该不该配`、`## 第 2 步：六件事`、`## 第 3 步：落到哪几处`、`## 第 4 步：出清单`；正文末尾指向 `references/上游台账机制.md` 的一句指针（Task 2 要建这个文件）

- [ ] **Step 1: 建目录，逐字写 frontmatter**

创建 `plugin/skills/skill-ledger/SKILL.md`，开头逐字写这五行：

```markdown
---
name: skill-ledger
description: "给某个技能加台账、或检查已有台账够不够用时使用——先判该不该配，再给出改哪几处、怎么改的建议清单，不直接改文件。触发方式：/skill-ledger <技能名或路径>，不带参数时只给判据与清单当参考。不用于：改技能提示词的其余问题、替技能写台账内容本身。"
argument-hint: "<技能名或路径，可省略>"
disable-model-invocation: true
---
```

- [ ] **Step 2: 写开头与第 0 步（先确认拿到的是技能）**

标题下先用两三句说清这个技能干什么、产出长什么样。然后写 `## 第 0 步：先确认拿到的是技能`，内容必须包含：

- 一个技能的样子：一个目录，里面有 `SKILL.md`，开头是 `---` 包起来的 frontmatter
- 拿到普通 Markdown、拿到目录、拿到不存在的路径时怎么办：**直说这不是技能，停下**，不硬产出清单
- 没给参数时的走法：跳过第 0 步，直接给判据与清单当参考

- [ ] **Step 3: 写第 1 步（判该不该配）**

写 `## 第 1 步：判该不该配`，含两张表（问法与结论照 spec §3 写）：

四条信号，中两条以上才配——跨上下文边界、重做代价高、中途要做决定、同一套流程连着跑多轮。每条给一个「问法」，不给结论。

不该配的三类，各带实例——一次调用几分钟跑完丢了重跑便宜；状态已经在产出里；状态已经在 git 历史或 issue tracker 里。

本节末尾必须写死一句：**四条一条都不中时，结论直接写「不该配」，并说清为什么。**（Review Focus 第 3 条）

- [ ] **Step 4: 写第 2 步（六件事）与第 3 步（落到哪几处）**

写 `## 第 2 步：六件事`，一张三列表（事 / 做法 / 为什么），六行照 spec §4 抄全：身份行、位置、行格式、可核断言、读者、闸门与收尾。**「为什么」那列不许省**——这一节的全部价值在道理上，只有模板没有道理，模型遇到不认识的技能就改不动。

写 `## 第 3 步：落到哪几处`，一张两列表（时机 / 写什么），四行：开工、每完成一件事、恢复、收尾。

本节必须写进一句（Review Focus 第 2 条）：**目标技能已经有状态文件时，清单要说的是「已有那份够不够用」，不是建议再加一份。**

- [ ] **Step 5: 写第 4 步（出清单），四节格式逐字写**

写 `## 第 4 步：出清单`，把下面这段逐字放进正文的代码块里：

````markdown
```
## 结论
该配 / 不该配 + 一句为什么

## 建议改动
| 改哪处 | 现在是什么 | 建议改成什么 | 为什么 |
（「改哪处」要指到 SKILL.md 的章节名或行号）

## 台账设计草案
身份行 / 位置 / 事件类型与行格式 / 读者 / 闸门与收尾
（每项按这个技能的实际活来写，不套模板）

## 建议里不含的
（明确列出没建议做的，免得读的人以为漏了）
```
````

代码块后面补两句：判「不该配」时第一、四节照写，中间两节省掉；清单用跟用户对话的语言写（默认中文），不跟着目标技能正文的语言跑。（Review Focus 第 4 条）

- [ ] **Step 6: 写结尾的出处指针**

正文最后写一节 `## 上游出处`，两三句：机制提取自 `obra/superpowers` v6.4.1，逐条对照、版本头、以后怎么核对上游更新，见 `references/上游台账机制.md`。**不把上游细节抄进 `SKILL.md`。**

- [ ] **Step 7: 自查正文**

Run: `grep -n "^## \|^name:\|^disable-model-invocation:\|^argument-hint:" plugin/skills/skill-ledger/SKILL.md`

Expected: 出现六行标题——`## 第 0 步：先确认拿到的是技能`、`## 第 1 步：判该不该配`、`## 第 2 步：六件事`、`## 第 3 步：落到哪几处`、`## 第 4 步：出清单`、`## 上游出处`；以及 `name: skill-ledger`、`disable-model-invocation: true`、`argument-hint: ...` 三行。

再 Run: `grep -n "checks/verify.sh\|README\|版本号" plugin/skills/skill-ledger/SKILL.md`

Expected: **无输出**（Global Constraints 要求不写死本仓维护规矩）。

再 Run: `grep -n "superpowers\|上游" plugin/skills/skill-ledger/SKILL.md`

Expected: 只命中 Step 6 写的「上游出处」那一节（标题行与那两三句）。**其余位置不出现**——正文不许要求读者去读上游文件或先装上游。

- [ ] **Step 8: README 收录表补一行**

在 `README.md` 的「收录的 skill」表格末尾（`test-case-design` 那行之后）加一行：

```markdown
| `skill-ledger` | 给某个技能加台账、或检查已有台账够不够用时用：先判该不该配，再给出改哪几处、怎么改的建议清单，不直接改文件。不带参数时只给判据与清单当参考。 |
```

Run: `grep -n "skill-ledger" README.md`
Expected: 恰好一行命中。

- [ ] **Step 9: Commit**

```bash
git add plugin/skills/skill-ledger/SKILL.md README.md
git commit -F - <<'EOF'
feat(skill-ledger): 新增技能台账建议技能

- 先判该不该配（四条信号 / 不该配三类），再给改哪几处的建议清单
- 只产建议不改文件；机制出处与上游对照留到 references/
- README 收录表补一行
EOF
```

---

### Task 2: 上游对照 `references/上游台账机制.md`

**Files:**
- Create: `plugin/skills/skill-ledger/references/上游台账机制.md`

**Interfaces:**
- Consumes: Task 1 在 `SKILL.md` 末尾写的指针，指向本文件的相对路径 `references/上游台账机制.md`
- Produces: 版本头三项（仓库 / 版本 / commit）；一张上游文件对照表；核对步骤

- [ ] **Step 1: 写版本头，逐字写**

创建 `plugin/skills/skill-ledger/references/上游台账机制.md`，开头逐字写：

```markdown
# 上游台账机制（obra/superpowers）

- 仓库：`https://github.com/obra/superpowers`
- 版本：v6.4.1
- commit：`5bf4e78011075bcfc0dc295f0724994cd123ee71`
- 日期：2026-09-18
```

- [ ] **Step 2: 写逐条对照**

一节 `## 六件事在上游怎么落`，把 spec §4 那张表的六行展开，每行给出上游的原始写法与文件位置——六件事是：身份行、位置、行格式、可核断言、读者、闸门与收尾。

必须写进去的具体事实（照抄，不许改写数字）：

- 身份行：首行写成 `# SDD ledger — plan: <计划文件路径>`；上游基线实验 **25 次**，读到别的计划的台账会照它跳过已完成的任务
- 位置：上游 `scripts/sdd-workspace` 解析出一次活一个目录；早先放在 `.git/` 下，而 `.git/` 是运行环境保护的路径，子代理写报告被拒（上游 #1780）
- 行格式：完成行是 `Task <N>: complete (commits <base7>..<head7>, ...)`；恢复契约就是一句 grep，有这行的算已完成、不重派
- 可核断言：每行带提交 SHA；上游基线实验里哈希对不上的台账会被拒收
- 读者：上游三个读者——恢复的自己、最终整支复核、用户；原话「没人读的汇总等于静默丢弃」
- 闸门与收尾：`task-done` 脚本真跑测试、过了才写完成行；最终复核干净后 `rm -rf` 整个目录

- [ ] **Step 3: 写上游文件对照表**

一节 `## 机制落在上游哪几个文件`，逐字放这张表：

```markdown
| 文件 | 装什么 |
|:---|:---|
| `skills/subagent-driven-development/SKILL.md` | 台账的身份行、恢复契约、行格式、用后即删 |
| `skills/subagent-driven-development/scripts/sdd-workspace` | 目录怎么定、为什么放工作区不放 `.git/` |
| `skills/subagent-driven-development/scripts/task-brief`、`review-package` | 台账的邻居：任务简报与复核包 |
| `skills/executing-plans/SKILL.md` | 写入闸门（`task-done` 跑过测试才写完成行） |
| `docs/superpowers/specs/2026-07-06-sdd-plan-scoped-workspace.md` | 为什么改成一次活一个目录、为什么要身份行 |
```

- [ ] **Step 4: 写演进史与核对步骤**

一节 `## 机制演进史`，四行表：

```markdown
| 版本 | 变了什么 |
|:---|:---|
| v6.0.0（#994） | 台账引入，首次让丢上下文的控制器能续跑 |
| v6.0.3（#1780） | 从 `.git/sdd/` 搬到工作区的 `.superpowers/sdd/` |
| v6.2.0 | 改成一次活一个目录 ＋ 首行写身份 ＋ 用后即删 |
| v6.4.1（#2138） | 同名计划不再共用一个目录 |
```

再写一节 `## 上游更新了怎么核对`，三步：拉上游 release notes；看上一节表里那五个文件路径有没有条目；有就更新本文件的版本头与对照内容，`SKILL.md` 不动。

- [ ] **Step 5: 自查**

Run: `grep -n "v6.4.1\|5bf4e78011075bcfc0dc295f0724994cd123ee71\|2026-09-18" plugin/skills/skill-ledger/references/上游台账机制.md`

Expected: 三行都命中。

Run: `grep -c "^| \`skills/\|^| \`docs/" plugin/skills/skill-ledger/references/上游台账机制.md`

Expected: `5`（对照表五行都在）。

- [ ] **Step 6: 确认 SKILL.md 的指针指得对**

Run: `ls plugin/skills/skill-ledger/references/上游台账机制.md`

Expected: 文件存在（`SKILL.md` 里那句指针指向的相对路径能落地）。

- [ ] **Step 7: Commit**

```bash
git add plugin/skills/skill-ledger/references/上游台账机制.md
git commit -F - <<'EOF'
docs(skill-ledger): 补上游台账机制对照与版本出处

- 六件事逐条对到上游写法与文件
- 记下版本头（v6.4.1 / 5bf4e78 / 2026-09-18）与演进史
- 写上「上游更新了怎么核对」三步
EOF
```

---

### Task 3: 抬版本号并跑仓内校验

**Files:**
- Modify: `plugin/.claude-plugin/plugin.json`（`version`）
- Modify: `.claude-plugin/marketplace.json`（`plugins.0.version`）

**Interfaces:**
- Consumes: Task 1 与 Task 2 建好的两个文件（校验脚本会把 `plugin/` 当成发布内容检查）
- Produces: 两处版本号一致的 1.17.0

- [ ] **Step 1: 改两处版本号**

`plugin/.claude-plugin/plugin.json` 里的 `"version": "1.16.2"` 改成 `"version": "1.17.0"`；`.claude-plugin/marketplace.json` 里 `plugins` 数组第一项的 `"version": "1.16.2"` 同样改成 `"1.17.0"`。

**不动**两个文件里那段罗列能力的 `description`：本仓既有做法并不逐技能维护它（`test-case-design` 就不在里面），这次跟着不维护。

Run: `grep -rn '"version"' plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json`

Expected: 两行都是 `1.17.0`，没有残留的 `1.16.2`。

- [ ] **Step 2: 跑仓内校验**

Run: `bash checks/verify.sh`

Expected: 全部通过。其中「版本号一致」那个模块（`70-版本号一致`）必须过——两处不一致时它会报错。

- [ ] **Step 3: 通读 SKILL.md**

从头读一遍 `plugin/skills/skill-ledger/SKILL.md`，逐条对 Global Constraints：

- 正文里没有「改这个文件」这类执行指令（产出只是建议）
- 正文里没有 `checks/verify.sh` / README 补表 / 抬版本号
- 六件事那张表的「为什么」列六行都非空

Expected: 三条都成立。任一条不成立就回去改 Task 1 的产物。

- [ ] **Step 4: Commit**

```bash
git add plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -F - <<'EOF'
chore(skill-ledger): 抬插件版本号到 1.17.0

多一个技能，按本仓规矩抬中间那位；两处版本号已一致。
EOF
```

---

## 完成判据

三个任务全做完时，下面每条都成立：

1. `plugin/skills/skill-ledger/SKILL.md` 与 `plugin/skills/skill-ledger/references/上游台账机制.md` 存在
2. `SKILL.md` 的 frontmatter 含 `disable-model-invocation: true`，`name` 是 `skill-ledger`
3. `README.md` 收录表里有 `skill-ledger` 那一行
4. 两处版本号都是 `1.17.0`，`bash checks/verify.sh` 通过
5. 现有技能本体一个字节都没动

## 没做到的

- 技能内容对不对**不跑模型验**（spec 第 9 节：不做实跑验证）。机械能验的只有接线与版本号一致，其余靠人读
- 不建台账读写的公共脚本；不改任何现有技能
