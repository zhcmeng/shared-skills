# test-case-design 主文件压缩实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `plugin/skills/test-case-design/SKILL.md` 从 45.9KB 压到 30KB 以内，行为不变。

**Architecture:** 先整节搬运到两份新参考文件，再替换入口与压缩重复段落，最后改交叉引用并终检。搬运阶段逐行核对原文；压缩阶段只删重复句，不改规则的含义。

**Tech Stack:** Markdown、Python 3（测试与一次性核对脚本）、Git。

**Spec:** `docs/superpowers/specs/2026-11-04-test-case-design-slimming-design.md`

## Global Constraints

- 产出契约不变：六份通用稿，按需加第七份。
- 不改 `check_docs.py`、`check_landing.py`、`issue_ids.py`。
- `SKILL.md` 的「必须照写的几个词」「六份里不许出现的东西」两节原地不动。
- 新文件里不出现「被测对象」、`WSL2`、`Docker`、`本机 Windows`。
- 主流程表的八行与「读哪份文件」一栏不动；表后补两句指向句（撞见报错、第七份与落成）。
- `references/实施方案与落成.md` 固定五节（一~五）；所有「第X节」的指向必须能在新文件里找到对应标题。
- 提交只在用户明确要求时做。
- 临时文件放 `.tmp/test-case-design-slimming/`，任务结束删掉。

## Review Focus

按最可能先出问题的顺序排；每条都在对应任务的检查里钉住。

1. **指向新文件的句子不在主流程表下面，Claude 找不到** —— 维护者文档记着 Claude 把「读哪份文件」一栏当穷举清单、不跟文内交叉引用；表下面那段是实测能读到的位置。钉在 Task 1、Task 2 的表后句与 Task 6 的人工通读。
2. **交叉引用指向已删除的节名** —— `文档模板.md` 与维护者文档里还写着「见 `SKILL.md` 的『只做落成』」。钉在 Task 5 的全文搜索。
3. **两张词表被顺带改动** —— `check_docs.py` 靠它们解析禁用词，少一条就少查一类。钉在 Task 6 的 `--rules` 条数（17／4／3／6）。
4. **新文件里出现具体环境名** —— 测试会扫技能自己的 `.md`。钉在 Task 1、Task 2、Task 3 后的 `test_example.py`。
5. **旧说法「第 0 步答了『要出实施测评方案』」残留** —— 第 0 步已经不问了。钉在 Task 3 的全文搜索。
6. **节号写错，入口指向空处** —— 新文件固定五节，`文档模板.md`、维护者文档与 `异常处理.md` 都按节号指过去。钉在 Task 5 的节号检查。

---

## Task 0：准备基线与核对脚本

**Files:**
- Modify: `.gitignore`
- Create: `.tmp/test-case-design-slimming/audit_move.py`

**Interfaces:**
- Produces: `.tmp/test-case-design-slimming/base.txt`（基线提交哈希）；`audit_move.py <目标文件> <节标题...>`，退出码 0 表示该节每一行都在目标文件里。

- [ ] **Step 1: 让 `.tmp/` 不进 git**

确认 `.gitignore` 里有 `.tmp/` 这一行；没有就加在 `__pycache__/` 那一行下面。

- [ ] **Step 2: 记下基线**

```bash
cd C:/Study/shared-skills && mkdir -p .tmp/test-case-design-slimming && git rev-parse HEAD > .tmp/test-case-design-slimming/base.txt
```

期望：`base.txt` 里是一个 40 位的提交哈希；`git show <哈希>:plugin/skills/test-case-design/SKILL.md` 能打出改动前的主文件。

- [ ] **Step 3: 写核对脚本**

`.tmp/test-case-design-slimming/audit_move.py`：

```python
#!/usr/bin/env python3
"""核对被搬走的节：基线 SKILL.md 里那一节的每一行，都还在目标文件里（忽略空白）。"""
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = (root / ".tmp" / "test-case-design-slimming" / "base.txt").read_text(encoding="utf-8").strip()
src = subprocess.run(
    ["git", "-C", str(root), "show", f"{base}:plugin/skills/test-case-design/SKILL.md"],
    capture_output=True, text=True, encoding="utf-8", check=True,
).stdout
target_path, *headings = sys.argv[1:]
target = Path(target_path).read_text(encoding="utf-8")
norm = lambda s: re.sub(r"\s+", "", s)
flat = norm(target)
missing = []
for h in headings:
    m = re.search(r"(?m)^" + re.escape(h) + r"\s*$(.*?)(?=^#{2,3} |\Z)", src, re.S)
    if not m:
        missing.append("找不到节：" + h)
        continue
    body = m.group(1)
    if norm(body) in flat:
        continue
    missing.append("节「%s」整段没有原样出现在目标文件里" % h)
    for line in body.splitlines():
        line = line.strip()
        if line and norm(line) not in flat:
            missing.append("  缺：" + line[:120])
if missing:
    print("以下内容在新文件里找不到：")
    for x in missing:
        print("  " + x)
    sys.exit(1)
print("OK：被搬的节逐行都在目标文件里")
```

- [ ] **Step 4: 自检脚本**

```bash
python C:/Study/shared-skills/.tmp/test-case-design-slimming/audit_move.py C:/Study/shared-skills/plugin/skills/test-case-design/SKILL.md "## 异常处理"
```

期望：`OK：被搬的节逐行都在目标文件里`。

---

## Task 1：搬异常处理表

**Files:**
- Create: `plugin/skills/test-case-design/references/异常处理.md`
- Modify: `plugin/skills/test-case-design/SKILL.md`（`## 异常处理` 节与 `## 主流程` 表后）

**Interfaces:**
- Consumes: Task 0 的 `audit_move.py`。
- Produces: `references/异常处理.md`；`SKILL.md` 主流程表后的第一句指向句。

- [ ] **Step 1: 建新文件并原样搬入**

把 `SKILL.md` 的 `## 异常处理` 整节（全部要点、整张表、结尾那句「这一节不是新的流程步骤」）复制到 `references/异常处理.md`，一级标题写 `# 异常处理`，正文不动。

- [ ] **Step 2: 核对搬运没漏**

```bash
python C:/Study/shared-skills/.tmp/test-case-design-slimming/audit_move.py C:/Study/shared-skills/plugin/skills/test-case-design/references/异常处理.md "## 异常处理"
```

期望：`OK`。

- [ ] **Step 3: 替换 `SKILL.md` 里的原节**

把 `## 异常处理` 到 `## 主流程` 之前的内容整段替换为：

```markdown
## 撞见问题怎么办

**先自己修，不问用户。**同一处修过一轮还是失败，才告诉用户；说清三样：报错原文、已经试过的修法、还需要用户做什么。

**不删用户文件、不覆盖没读过的产出、不擅自换产出目录；外部依赖不自动安装**——`/skill-upper`、Python 3、`skill-up` 这类要装到用户机器上的东西，先找现成的、用已有命令兜底；找不到时告诉用户缺什么。缺测试依据、缺风险信息、用户还没说产出放哪儿，是正常的开工输入，照旧只问缺的那几样。

具体哪种报错先怎么修、修不好怎么交代，见 `references/异常处理.md`——**只在撞见问题时读**，不是每一步开头的检查清单。
```

- [ ] **Step 4: 在主流程表后补一句指向**

在 `## 主流程` 的表格最后一行之后、`**每步的完成标准：...**` 那一段之前，插入一段：

```markdown
**撞见报错时读 `references/异常处理.md`。**
```

这一句是给从表出发的读者看的：维护者文档记着 Claude 把「读哪份文件」一栏当穷举清单，表下面那段是实测能读到的位置。`## 撞见问题怎么办` 里那一句指向保留，两处都指向同一份文件。

- [ ] **Step 5: 跑测试**

```bash
cd C:/Study/shared-skills && bash checks/verify.sh test-case-design
```

期望：`全部通过`。

---

## Task 2：搬第七份与落成

**Files:**
- Create: `plugin/skills/test-case-design/references/实施方案与落成.md`
- Modify: `plugin/skills/test-case-design/SKILL.md`（四节与 `## 主流程` 表后）

**Interfaces:**
- Consumes: Task 0 的 `audit_move.py`；Task 1 的 `references/异常处理.md` 与表后第一句。
- Produces: `references/实施方案与落成.md`，节名为 `## 一、只出实施方案那一份`、`## 二、落成那一步手上要有哪四样`、`## 三、只做落成`、`## 四、成品落点与落成对照`、`## 五、skill-up 装不上、跑不了时`；`SKILL.md` 新增 `## 第七份与落成` 与表后第二句。

- [ ] **Step 1: 建新文件，原样搬入四节**

新文件开头写：

```markdown
# 实施方案与落成

**什么时候读这一份**：用户点名要实施方案规格说明（第七份）时；或七份都在手上、只做落成时。六份通用稿的设计不走这一份。
```

然后按下面顺序放四节，正文从 `SKILL.md` 原样复制：

| 新文件节标题 | 从 `SKILL.md` 复制的节 |
|:---|:---|
| `## 一、只出实施方案那一份` | `## 只出实施方案那一份` |
| `## 二、落成那一步手上要有哪四样` | `### 落成那一步手上要有哪四样` |
| `## 三、只做落成` | `## 只做落成` |
| `## 四、成品落点与落成对照` | `### 成品落点与落成对照` |

最后加第五节：

```markdown
## 五、skill-up 装不上、跑不了时

**写第七份缺 `skill-up` 是硬停**：先找 `~/.claude/skills/skill-upper/`，再看 `skill-up --version` 能不能跑；都没有就问用户要不要帮装，默认装全局（用户级）、不进项目目录，装好 `skill-up --version` 确认后再继续。**不装或装不上就终止第七份**，通用稿不受影响。

装好之后，版本与 `usage-notes.md` 顶部对不上时，把那一份当历史版本用：能跑 `skill-up` 核的当场核，拿不准的标「待确认」，别当事实写。照第一节的核法走。
```

- [ ] **Step 2: 核对搬运没漏（改指针之前）**

```bash
python C:/Study/shared-skills/.tmp/test-case-design-slimming/audit_move.py C:/Study/shared-skills/plugin/skills/test-case-design/references/实施方案与落成.md "## 只出实施方案那一份" "### 落成那一步手上要有哪四样" "## 只做落成" "### 成品落点与落成对照"
```

期望：`OK`。

- [ ] **Step 3: 改新文件里的内部指向**

只改这五处，其余一字不动：

| 原句 | 改成 |
|:---|:---|
| `照「异常处理」问用户要不要帮装` | `照 \`references/异常处理.md\` 问用户要不要帮装` |
| `（见「只出实施方案那一份」）` | `（见第一节）` |
| `（见「只做落成」）` | `（见第三节）` |
| `见上文「落成那一步手上要有哪四样」` | `见第二节` |
| `见上文「成品落点与落成对照」` | `见第四节` |

- [ ] **Step 4: 替换 `SKILL.md` 里的四节**

删掉 `## 只出实施方案那一份`、`## 只做落成`、`### 成品落点与落成对照`、`### 落成那一步手上要有哪四样`；在原来 `## 只出实施方案那一份` 的位置写：

```markdown
## 第七份与落成

第七份（`Implementation Specification.md`，实施方案规格说明）**只在用户点名要的时候出**：可以跟六份一起要，也可以手上已有六份、这次只要这一份。它只对技能、提示词这类靠模型跑的对象有用——一段脚本、一个函数、一个库用不上，用户点名要也照实说，产出仍是那六份。第 0 步不问这件事，也不提它。

**落成（把文档里的设计变成盘上能跑的评测配置）排在文档之后，只摆配置、不跑测。**跑起来看结果、照结论改判据是 `/skill-upper` 的活。用户直接点名要能跑的用例、手上还没有文档时，照旧先把六份出完（点名要第七份的也一并出），再落成。

**两条入口怎么走、落成要读哪四样、摆什么、补哪张表、跑哪个对照，都在 `references/实施方案与落成.md` 里。**写第七份之前先确认 `/skill-upper` 装着（`~/.claude/skills/skill-upper/`）；没装照 `references/异常处理.md` 问用户要不要帮装，装不上就终止第七份。**配置原文不抄进第七份**，由落成那一步照它写进盘里。
```

- [ ] **Step 5: 改 `SKILL.md` 里指向旧节的八处**

按句子搜，不要按行号——Task 1 之后行号已经变了。

| 原句 | 在哪一段 | 改成 |
|:---|:---|:---|
| `走法见下文「只出实施方案那一份」` | 开头「这门技能做什么」 | `走法见 \`references/实施方案与落成.md\` 第一节` |
| `（见下文「成品落点与落成对照」）` | 开头「这门技能做什么」 | `（见 \`references/实施方案与落成.md\` 第四节）` |
| `见下文「只出实施方案那一份」` | 「管到哪为止」 | `见 \`references/实施方案与落成.md\` 第一节` |
| `（见下文「成品落点与落成对照」）` | 「管到哪为止」 | `（见 \`references/实施方案与落成.md\` 第四节）` |
| `再照下文「只做落成」那一节落` | 「管到哪为止」 | `再照 \`references/实施方案与落成.md\` 第三节落` |
| `走法照下文「只做落成」` | 主流程表后的进度段 | `走法照 \`references/实施方案与落成.md\` 第三节` |
| `走法见下文「只出实施方案那一份」` | 第 0 步（Task 4 会整段替换；替换文本里保留这一句） | `走法见 \`references/实施方案与落成.md\` 第一节` |
| `见下文「成品落点与落成对照」` | 第 7 步 | `见 \`references/实施方案与落成.md\` 第四节` |

- [ ] **Step 6: 在主流程表后补第二句指向**

在 Task 1 加的「撞见报错时读 `references/异常处理.md`。」那一段之后、`**每步的完成标准：...**` 之前，插入一段：

```markdown
**用户点名要第七份、或七份都在手上只做落成时，读 `references/实施方案与落成.md`。**
```

- [ ] **Step 7: 跑测试**

```bash
cd C:/Study/shared-skills && bash checks/verify.sh test-case-design
```

期望：`全部通过`。

---

## Task 3：换读文件指南

**Files:**
- Modify: `plugin/skills/test-case-design/SKILL.md`（删除 `## 什么时候读哪份文件`，新增 `## 参考文件怎么读`）

**Interfaces:**
- Consumes: 无。
- Produces: `SKILL.md` 末尾的 `## 参考文件怎么读`，替代原来 4KB 的读文件指南。

- [ ] **Step 1: 删掉旧节**

删除 `## 什么时候读哪份文件` 整节（现在从该标题到文件末尾）。这一节里有第 298 行的旧说法「第 0 步答了『要出实施测评方案』的」，随它一起删除。

- [ ] **Step 2: 新增一节**

在该位置写：

```markdown
## 参考文件怎么读

**按节读，不整份读**——要用的节，主流程表「读哪份文件」一栏与表后那两句已经指出。另外三处每步都可能用到：写决策依据时读 `references/文档模板.md` 第九节；拿不准该填成什么样时读 `references/文档示例.md`；技术文件的第五节是算例，拿不准再读。

七门技术的文件在 `references/技术/` 下，文件名与技术名相同：等价类划分、分类树方法、边界值分析、组合测试、判定表测试、状态转移测试、场景测试（用例测试归在这门里）。

`scripts/` 下那三个脚本（`check_docs.py`、`check_landing.py`、`issue_ids.py`）**按命令行用就行，不用读它们的内容**。命令里的 `python` 按你机器上的写法来——只装了 Python 3、没给 `python` 这个名字的（不少 Linux 与 macOS 上就是），写成 `python3`。
```

- [ ] **Step 3: 确认旧说法没了**

```bash
grep -n "第 0 步答了" C:/Study/shared-skills/plugin/skills/test-case-design/SKILL.md
```

期望：没有输出。

- [ ] **Step 4: 跑测试**

```bash
cd C:/Study/shared-skills && bash checks/verify.sh test-case-design
```

期望：`全部通过`。

---

## Task 4：压缩重复段落

**Files:**
- Modify: `plugin/skills/test-case-design/SKILL.md`

**Interfaces:**
- Consumes: 无。
- Produces: `SKILL.md` 不超过 30,000 字节。

- [ ] **Step 1: 并掉第 0 步里重复的四段**

删掉这四段：`**测评方案的事一个字都不问。**` 那一段、`**第七份不跟六份绑在一起。**` 那一段、`**用哪个方案不进六份。**` 那一段、`**只问缺的开工输入，别的都不问。**` 那一段；在 `**测评方案的事一个字都不问。**` 原来的位置换成下面这一段：

```markdown
**只问缺的开工输入，别的都不问。**第 0 步要问的就三样：测试依据、风险信息、没给的产出目录——**没有第四样**。**产出形式不问**：出六份还是只出某一份、生成什么形式、交到哪一步、要不要顺便落成能跑的用例，这类都不问，也不摆成选项让用户挑——产出就是那六份，用户另外点名要实施方案规格说明的才加第七份（走法见 `references/实施方案与落成.md` 第一节）。**测评方案的事一个字都不问**：第七份只在用户点名时出，第 0 步既不判测试项是不是靠模型跑的东西，也不问要不要一并出；用哪个方案不进六份，落在第七份的节名上（「<节号>、方案：<方案名>」），决策依据里也不记；没有第七份时，它哪儿都不落。技能自己那几条入口（从零设计、手上已有一组用例、只出实施方案、只做落成）走哪条，由你判，不问用户。第 1 步那四个决定同理：材料可以讲清楚，选择不摆成菜单。
```

中间的 `**定完判完都要落进产出**` 那一段原地不动。Task 2 Step 5 在第 0 步加的指向句并进了「才加第七份」后面的括号，别删掉。

- [ ] **Step 2: 压缩「管到哪为止」里的落成两段**

把从 `**落成（把文档里的设计变成盘上能跑的评测配置）排在文档之后。**` 起、到 `不在这门技能里。` 止的两段替换为：

```markdown
**落成排在文档之后，只摆配置、不跑测**：照第七份把配置与夹具摆到盘上，回来补「成品落点」表，再跑一遍落成对照。跑起来看结果、照结论改判据是 `/skill-upper` 的活。用户直接点名要能跑的用例、手上还没有文档时，照旧先把六份出完（点名要第七份的也一并出），再落成。走法见 `references/实施方案与落成.md`。
```

- [ ] **Step 3: 压缩第 7 步里的落成一句**

把 `成品已经落成的，终检时还要跑一遍落成对照把账对上（表在第七份的方案节里）——命令、退出码、分几批落成时怎么算，见下文「成品落点与落成对照」。` 替换为：

```markdown
成品已经落成的，终检时还要跑一遍落成对照把账对上——命令、退出码、分几批落成时怎么算，见 `references/实施方案与落成.md` 第四节。
```

- [ ] **Step 4: 收紧主流程表后的两段（只在超长时做）**

先量：

```bash
wc -c C:/Study/shared-skills/plugin/skills/test-case-design/SKILL.md
```

- 不超过 30,000：跳过这一步。
- 超过 30,000：先删开头与 `## 第七份与落成` 里重复的「第 0 步不问、不提」，只留第 0 步一处（约省 50 字节）；还不够，再把 `**进度摆给用户看**` 与 `**决策依据随做随记**` 两段各收紧，删掉重复的解释性句子，**规则一条不删**：八步一行一步、用工具列、完成一步才标、回走重标、落成单列、另三条入口不套八步；决策依据随做随记、只在几种做法里挑时才记、先记再做、只有一种做法不记、用户给的放前块可改、其余放后块只增不改、旧条目原样留着、写成过程不是结论。

- [ ] **Step 5: 确认大小**

```bash
wc -c C:/Study/shared-skills/plugin/skills/test-case-design/SKILL.md
```

期望：数字不超过 `30000`。

- [ ] **Step 6: 跑测试**

```bash
cd C:/Study/shared-skills && bash checks/verify.sh test-case-design
```

期望：`全部通过`。

---

## Task 5：改外部交叉引用与文档

**Files:**
- Modify: `plugin/skills/test-case-design/references/文档模板.md:97,316,382`
- Modify: `plugin/skills/test-case-design/references/异常处理.md`（依赖表第 1、3 行）
- Modify: `docs/maintainers/test-case-design.md:27,28,31`
- Modify: `plugin/skills/test-case-design/README.md`（文件结构）

**Interfaces:**
- Consumes: Task 1 的 `references/异常处理.md`；Task 2 的 `references/实施方案与落成.md` 与节号。
- Produces: 全仓不再有指向已删除节名的引用。

- [ ] **Step 1: 改 `文档模板.md` 三处**

| 行 | 原句 | 改成 |
|:---|:---|:---|
| 97 | `再跑一遍落成对照（命令见 `SKILL.md`）` | `再跑一遍落成对照（命令见 `references/实施方案与落成.md` 第四节）` |
| 316 | `两种入口，见 `SKILL.md` 的「只出实施方案那一份」` | `两种入口，见 `references/实施方案与落成.md` 第一节` |
| 382 | `见 `test-case-design` 技能的 `SKILL.md`「只做落成」与「落成那一步手上要有哪四样」那两节` | `见 `test-case-design` 技能的 `references/实施方案与落成.md` 第二、三节` |

- [ ] **Step 2: 改 `异常处理.md` 依赖表两行**

把「`/skill-upper` 没装」与「`skill-up` 命令不在，`--version` 跑不了」两行的最后一格，换成：

```markdown
照 `references/实施方案与落成.md` 第五节处理
```

前一格（「先自动怎么修」）保留原文的检查动作。

- [ ] **Step 3: 改维护者文档**

| 行 | 原句里要换掉的那一段 | 改成 |
|:---|:---|:---|
| 27 | 最后一格：`SKILL.md` 的「只出实施方案那一份」 | `references/实施方案与落成.md` 第一节 |
| 28 | 最后一格：`SKILL.md` 的「只做落成」＋「成品落点与落成对照」＋「落成那一步手上要有哪四样」 | `references/实施方案与落成.md` 第二、三、四节 |
| 31 | `这条写在 SKILL.md 的「只出实施方案那一份」里` | `这条写在 references/实施方案与落成.md 第一节里` |

并在文件地图里加一行：

```markdown
| 撞见报错先怎么修、修不好怎么交代 | `references/异常处理.md` |
```

- [ ] **Step 4: 改 README 文件结构**

在 `references/` 那一棵树的 `流程.md` 之前或之后补两行（按现有缩进与写法）：

```text
│   ├── 异常处理.md             出错时先怎么修、修不好怎么交代
│   ├── 实施方案与落成.md        第七份怎么出、落成怎么摆、成品落点怎么对账
```

- [ ] **Step 5: 全仓搜索旧节名**

```bash
cd C:/Study/shared-skills && grep -rn "只出实施方案那一份\|只做落成\|成品落点与落成对照\|落成那一步手上要有哪四样\|什么时候读哪份文件" --include="*.md" plugin/skills/test-case-design docs/maintainers
```

期望：剩下的命中只在 `references/实施方案与落成.md` 里（新文件自己的节名与正文），以及 `docs/superpowers/` 下的历史设计稿与计划稿。技能目录里不再有指向 `SKILL.md` 旧节的句子。

- [ ] **Step 6: 检查所有 `references/...md` 路径存在**

```bash
cd C:/Study/shared-skills && python - <<'EOF'
import re
from pathlib import Path
root = Path("plugin/skills/test-case-design")
bad = []
for p in root.rglob("*.md"):
    for m in re.finditer(r"`(references/[^`]+?\.md)`", p.read_text(encoding="utf-8")):
        rel = m.group(1)
        if "<" in rel or "*" in rel:
            continue
        if not (root / rel).is_file():
            bad.append(f"{p.relative_to(root)} -> {rel}")
print("\n".join(bad) if bad else "OK：所有 references 路径都存在")
EOF
```

期望：`OK：所有 references 路径都存在`。

- [ ] **Step 7: 确认所有节号都能对上**

```bash
cd C:/Study/shared-skills && python - <<'EOF'
import re
from pathlib import Path

CN = {"1": "一", "2": "二", "3": "三", "4": "四", "5": "五"}
skill = Path("plugin/skills/test-case-design")
target = skill / "references" / "实施方案与落成.md"
have = set(re.findall(r"(?m)^## ([一二三四五])、", target.read_text(encoding="utf-8")))
bad = ["新文件缺节：第%s节" % n for n in "一二三四五" if n not in have]
for root in (skill, Path("docs/maintainers")):
    for p in sorted(root.rglob("*.md")):
        if p == target:
            continue
        for line_no, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in re.finditer(r"实施方案与落成\.md`?\s*第([一二三四五1-5](?:、[一二三四五1-5])*)节", line):
                for n in m.group(1).split("、"):
                    n = CN.get(n, n)
                    if n not in have:
                        bad.append("%s:%d -> 第%s节" % (p.as_posix(), line_no, n))
print("\n".join(bad) if bad else "OK：五个节标题都在，所有节号都能对上")
EOF
```

期望：`OK：五个节标题都在，所有节号都能对上`。

- [ ] **Step 8: 跑测试**

```bash
cd C:/Study/shared-skills && bash checks/verify.sh test-case-design
```

期望：`全部通过`。

---

## Task 6：终检

**Files:**
- 不新增文件；按检查结果回到前面任务修改。

**Interfaces:**
- Consumes: Task 1–5 的全部产出。
- Produces: 一份可以交付的改动。

- [ ] **Step 1: 跑完整检查**

```bash
cd C:/Study/shared-skills && bash checks/verify.sh test-case-design
```

期望：`全部通过`。`tcd_run` 成功时不打印子测试的输出；想逐项看，直接跑：

```bash
for t in C:/Study/shared-skills/tests/test-case-design/test_*.py; do python "$t"; done
```

- [ ] **Step 2: 确认两张词表没被改动**

```bash
python C:/Study/shared-skills/plugin/skills/test-case-design/scripts/check_docs.py --rules | head -20
```

期望：仍然写着「17 个」「4 个」「3 个」「6 个」，词条与改动前一致。

- [ ] **Step 3: 确认大小**

```bash
wc -c C:/Study/shared-skills/plugin/skills/test-case-design/SKILL.md
```

期望：不超过 `30000`。

- [ ] **Step 4: 人工通读**

读一遍新的 `SKILL.md` 与两份新文件，逐条核对：

- 主流程表后面有两句指向句：一句是撞见报错读 `references/异常处理.md`，一句是用户点名要第七份或只做落成读 `references/实施方案与落成.md`。
- 正常出六份的路径上，每步要读的文件都能在「读哪份文件」一栏、表后那两句或紧挨着的段落里找到。
- 用户点名要第七份时，主文件指向 `references/实施方案与落成.md` 第一节；只做落成时指向第二、三、四节。所有「第X节」的指向都能在新文件里找到对应标题（Task 5 Step 7 已用脚本查过）。
- 第 0 步仍然只问三样，`**定完判完都要落进产出**` 那段还在。
- `## 必须照写的几个词`、`## 六份里不许出现的东西` 两节与改动前逐字一致。

- [ ] **Step 5: 看差异**

```bash
cd C:/Study/shared-skills && git status --short && git diff --stat && git diff -- plugin/skills/test-case-design/SKILL.md | head -120
```

期望：`SKILL.md` 减少约 16KB；两份新文件出现在 `git status` 里；没有预期之外的文件被改。

- [ ] **Step 6: 是否交付**

问用户是否现在提交或推送。

- 不提交：到此为止，把 `.tmp/test-case-design-slimming/` 删掉。
- 提交：把 `plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 的版本号从 `1.29.2` 抬到 `1.29.3`（两处必须一致），再按用户要求提交。

---

## 自检记录

- **规格覆盖**：设计稿的每一节都对应到任务——新增两份参考文件（Task 1、2）、主流程表后两句指向句（Task 1、2）、替换读文件指南（Task 3）、压缩四处（Task 4）、改外部指针与节号检查（Task 5）、验证五步（Task 6）。
- **步骤扫描**：每个任务都有可执行的命令与期望输出；未写「适当处理」这类空话。
- **类型与名称**：新文件的节号在 Task 2 定义，Task 5 引用同一组节号，Task 5 Step 7 逐个核对。
- **Review Focus**：六条都钉在具体任务的检查里。
- **本轮审核修正**：表后两句指向句（Task 1 Step 4、Task 2 Step 6）、Task 4 保留第 0 步指向、Task 5 Step 7 的节号检查。
- **比例**：计划约 570 行，设计稿约 180 行；多出来的部分是新写的入口文本与核对命令，被搬的 9KB 正文没有重抄。
