# plain-language 规则常驻注入 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `shared-skills` 仓库自身成为 Claude Code 插件，并在每个会话启动时把 plain-language 的写作规则注入上下文。

**Architecture:** 仓库根加 `.claude-plugin/` 与 `hooks/`，`skills/` 原地不动。规则抽成 `skills/plain-language/rules.md` 作为唯一真相，`SKILL.md` 改为指向它；SessionStart hook 读取 `rules.md`，转义成 JSON 后经 `hookSpecificOutput.additionalContext` 注入。hook 任何异常都静默退出，绝不阻塞会话。

**Tech Stack:** Bash（Git Bash 5.3）、Node 24（仅测试脚本用）、Claude Code 插件协议。

**Spec:** `docs/superpowers/specs/2026-09-15-plain-language-sessionstart-injection-design.md`

## Global Constraints

- 仓库许可证 MIT，版权人 `zhcmeng`（见 `LICENSE`）
- 插件名 `shared-skills`，版本 `1.0.0`
- SessionStart matcher 必须是 `startup|clear|compact`（`compact` 不可省，否则上下文压缩后约束丢失）
- hook 遇到任何异常一律 `exit 0` 且不输出内容，绝不阻塞会话
- 不执行 `/plugin marketplace add` 与 `/plugin install`（spec 非目标）
- 不恢复 `~/.agents/skills/` 下已删的 4 份副本（spec 非目标）
- 测试的 subagent 跑在 `deepseek-flash` 上，结论不得外推到 Opus，每条结论都要标注这一点

---

### Task 1: 插件骨架

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`

**Interfaces:**
- Consumes: 无
- Produces: 插件名 `shared-skills`、版本 `1.0.0`——Task 5 的 README 安装说明要引用这两个值

- [ ] **Step 1: 写一个会失败的测试**

没有校验脚本，就用一次性命令当测试。先跑它，确认现在失败：

```bash
cd /c/work/shared-skills
node -e "
const p=require('./.claude-plugin/plugin.json');
const m=require('./.claude-plugin/marketplace.json');
if(p.name!=='shared-skills') throw new Error('plugin name');
if(p.version!=='1.0.0') throw new Error('version');
if(m.plugins[0].name!=='shared-skills') throw new Error('marketplace entry');
console.log('OK');
"
```

Expected: FAIL — `Cannot find module './.claude-plugin/plugin.json'`

- [ ] **Step 2: 写 `plugin.json`**

```json
{
  "name": "shared-skills",
  "description": "跨工程共享的 Agent Skill 集合：说人话规则（会话启动时常驻注入）、提交、Markdown 导出、快速了解一个对象",
  "version": "1.0.0",
  "author": { "name": "zhcmeng" },
  "homepage": "https://github.com/zhcmeng/shared-skills",
  "repository": "https://github.com/zhcmeng/shared-skills",
  "license": "MIT",
  "keywords": ["skills", "plain-language", "chinese", "markdown", "commit"]
}
```

- [ ] **Step 3: 写 `marketplace.json`**

```json
{
  "name": "shared-skills",
  "description": "跨工程共享的 Agent Skill 集合",
  "owner": { "name": "zhcmeng" },
  "plugins": [
    {
      "name": "shared-skills",
      "description": "跨工程共享的 Agent Skill 集合：说人话规则（会话启动时常驻注入）、提交、Markdown 导出、快速了解一个对象",
      "version": "1.0.0",
      "source": "./",
      "author": { "name": "zhcmeng" }
    }
  ]
}
```

- [ ] **Step 4: 重跑测试，确认通过**

Run: Step 1 的同一条命令
Expected: `OK`

- [ ] **Step 5: 提交**

```bash
git add .claude-plugin/
git commit -m "feat(plugin): 仓库改为 Claude Code 插件"
```

---

### Task 2: 抽出 rules.md，SKILL.md 改为指向它

**Files:**
- Create: `skills/plain-language/rules.md`
- Modify: `skills/plain-language/SKILL.md`

**Interfaces:**
- Consumes: 无
- Produces: 文件 `skills/plain-language/rules.md`，路径固定——Task 3 的 hook 按这个路径读它

- [ ] **Step 1: RED —— 基线取样，确认模型确实会写黑话**

这一步是 writing-skills 的硬要求：改 skill 前必须先看到失败。不写任何文件，先取证。

用一个一次性 subagent（全新上下文）跑下面这个 prompt，跑 5 次：

```
写一段 300 字左右的技术方案摘要，主题：给内部工具加一层缓存。
面向不懂技术的产品经理。要求写得专业。
```

逐条人工读输出，记录：出现了哪些黑话、生造词、无必要的英文夹杂。把 5 次的原话追加到 `docs/superpowers/plans/2026-09-15-baseline.md`。

**通过的判据**：若 5 次里基线几乎不犯，说明这个功能没有存在理由——停下来告诉人，不要继续 Task 3。

- [ ] **Step 2: 写 `rules.md`**

内容是从 `SKILL.md` 原样搬来的三段，只做两处中性化（因为要脱离 skill 语境常驻注入）：`被审页面解释过某个同类词` → `同一篇里解释过某个同类词`；`读者是谁` 那句去掉「重说回答时 / 审文档时」的场景前缀。

```markdown
**不了解这个主题的读者，能不能一次读懂这句话？** 读不懂就是没写明白，不是读者的问题。

判断一个词要不要换，问两句：

- 读者**要不要懂英文**才读得懂？要就换。公认缩写（GDP、API）不用换；同一篇里解释过某个同类词，其他同类词就得解释
- 读者**要不要回看上文**才接得上？要就把指代展开成明确的话

读者是谁：写东西时是提问的那个人——他关心这个话题，但不懂里面的行话，也不该被要求回看前文；写给别人看的文档，读者是将来打开那个页面的人，看不到写它时的对话。

## 要改的

改法只有一种：换成读者不用自己解码的说法。

| 类型 | 例 |
|:---|:---|
| 自造压缩黑话 | "上层认知扩口、下层收割"、"品→效" |
| 生造词、直译词 | "心智物理"、"决策旅程"、"截胡自然流量" |
| 元标注黑话 | "对冲句" |
| 术语首次出现不解释 | "信任品"、"ROAS" |
| 术语名与解释对不上 | 名字叫"稀缺"、例子讲的是时间限制——按解释重译（"紧迫感"） |
| 无必要的英文夹杂 | "align 一下这个 approach"；英文词当日常词用（注入 context、查 memory）也算 |
| 英文没给中文 | "asymmetric information"、英文标题；给了中文解释和给译名一样算过关（`performance-based` 写成"按点击、销售、分成计费"就行，不必强求译名） |
| 指代不明 | "它""那条"接不上前文 |
| 同一个东西两种叫法 | 读者会当成两件事 |
| 标签没说清 | 小标题自己没说清指什么 |

## 保留

文中已给出定义的术语（前提是名字与解释对得上）、引用原文的章节名与报告用语、代码标识符、路径、命令名、产品名、公认缩写、已经进入中文日常用法的直译词（护城河、天花板、赛道这类读者一次就读得懂的保留；"决策旅程""对齐颗粒度"这种生硬直译要换）、当机制名或目录名用的英文（`.claude/memory/` 是路径，保留；同页"查 memory"说的是记忆，要换）。
```

- [ ] **Step 3: 改 `SKILL.md`**

三段规则（判据、要改的、保留）整段删除，其余保留。改动共四处：

1. 正文第一行插入强指令（这是方案乙最可能失效的地方，措辞必须是命令句，不能是「可参考」）：

```markdown
**动手前先读同目录的 `rules.md`**——判据、要改的、保留全在那里，那是本 skill 仅有的规则。下面只讲怎么用，不重复规则。
```

2. `## 判据` 整节、「要改的」整节、「保留」整节删除。

3. 把原来夹在判据节里的「审到哪」一段挪到「两种用法」节末尾（它讲的是审文档的范围，属于用法不讲规则）：

```markdown
审到哪：正文、图注与脚注说明、mermaid 图里的文字。YAML frontmatter 和引文元数据不审。引文本身一个字不动——引文里的问题在引文外面补一句说明。
```

4. 修一处会断掉的交叉引用：清单模板里原本写 `类型：<上表的类型名；…>`，「上表」指的是已搬走的规则表，改为：

```markdown
  - 类型：<`rules.md` 里那张表的类型名；归不进的自起一个，说清是什么问题>
```

最终 `SKILL.md` 的结构应为：frontmatter → `# 说人话` → 强指令 → `## 两种用法`（表格 + 只读不改 + 审到哪）→ `## 输出`（重说 + 清单）。

- [ ] **Step 4: GREEN —— 验证模型真的会去读 rules.md**

这测的是方案乙的致命点。用一次性 subagent 跑，把新 `SKILL.md` 的内容作为 skill 正文给它，再给一个触发场景：

```
[新 SKILL.md 全文]

用户说：「这段我看不懂」，然后贴了一段夹英文黑话的文字。
按 skill 处理。
```

**通过判据**：subagent 明确读取了 `rules.md`（有读取动作，或输出中体现了表里的具体类型名与例子），而不是只看 `SKILL.md` 就动手。

**若不通过**：说明指向句不够强，改措辞（例如把读取动作写进「两种用法」的表里）后重测，直到通过为止。

- [ ] **Step 5: 提交**

```bash
git add skills/plain-language/
git commit -m "refactor(plain-language): 规则抽成 rules.md 作唯一真相"
```

---

### Task 3: SessionStart hook 与校验脚本

**Files:**
- Create: `hooks/hooks.json`
- Create: `hooks/run-hook.cmd`
- Create: `hooks/session-start`
- Create: `hooks/verify.sh`

**Interfaces:**
- Consumes: `skills/plain-language/rules.md`（Task 2 产出，路径固定）
- Produces: `bash hooks/session-start` 输出一行 JSON，形如 `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"…"}}`；Task 4 靠它取注入文本

- [ ] **Step 1: 写会失败的测试 `hooks/verify.sh`**

```bash
#!/usr/bin/env bash
# 校验 SessionStart hook：输出必须是合法 JSON，且注入文本非空、含规则关键词。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fails=0
fail() { echo "FAIL: $1" >&2; fails=$((fails + 1)); }

out="$(bash "${SCRIPT_DIR}/session-start" 2>/dev/null)"
if [ -z "$out" ]; then
  fail "session-start 没有输出（应为一行 JSON）"
  echo "1 项失败" >&2
  exit 1
fi

ctx="$(printf '%s' "$out" | node -e '
let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{
  let j;try{j=JSON.parse(s)}catch(e){console.error("JSON 解析失败: "+e.message);process.exit(2)}
  const c=j&&j.hookSpecificOutput&&j.hookSpecificOutput.additionalContext;
  if(typeof c!=="string"){console.error("缺 hookSpecificOutput.additionalContext");process.exit(3)}
  if(j.hookSpecificOutput.hookEventName!=="SessionStart"){console.error("hookEventName 不是 SessionStart");process.exit(4)}
  process.stdout.write(c);
});' 2>&1)" || fail "输出不是合法 JSON 或缺字段：${ctx}"

if [ -z "${ctx:-}" ]; then
  fail "注入文本为空"
else
  printf '%s' "$ctx" | grep -q '要改的' || fail "注入文本里没有「要改的」小节"
  printf '%s' "$ctx" | grep -q '保留'   || fail "注入文本里没有「保留」小节"
  printf '%s' "$ctx" | grep -q '护城河' || fail "注入文本里没有规则表的例句（疑似读到了空文件）"
fi

if [ "$fails" -eq 0 ]; then
  echo "全部通过"
else
  echo "${fails} 项失败" >&2
  exit 1
fi
```

- [ ] **Step 2: 跑测试，确认失败**

```bash
bash hooks/verify.sh
```

Expected: FAIL — `session-start 没有输出（应为一行 JSON）`

- [ ] **Step 3: 写 `hooks/session-start`**

```bash
#!/usr/bin/env bash
# SessionStart hook：把 plain-language 的写作规则注入上下文。
# 任何异常都静默退出——绝不阻塞会话。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RULES_FILE="${PLUGIN_ROOT}/skills/plain-language/rules.md"

[ -f "$RULES_FILE" ] || exit 0
rules_content="$(cat "$RULES_FILE" 2>/dev/null)" || exit 0
[ -n "$rules_content" ] || exit 0

# 单次参数替换转义，比逐字符循环快几个数量级
escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

rules_escaped="$(escape_for_json "$rules_content")"
context="<EXTREMELY_IMPORTANT>\n你写给人看的文字，一律按下面这份规则来：回答、文档、说明、提交信息正文。\n</EXTREMELY_IMPORTANT>\n\n${rules_escaped}"

printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "$context"

exit 0
```

- [ ] **Step 4: 写 `hooks/run-hook.cmd`**

跨平台 polyglot 包装，改写自 `obra/superpowers`（MIT）。Windows 上 cmd.exe 走批处理分支去找 bash，Unix 上 shell 把开头当空操作、直接执行末尾的 bash 分支。

```
: << 'CMDBLOCK'
@echo off
REM 改写自 obra/superpowers (MIT)。hook 脚本故意不带 .sh 后缀，
REM 免得 Claude Code 在 Windows 上自动往命令前面塞 "bash"。
REM 用法: run-hook.cmd <script-name> [args...]

if "%~1"=="" (
    echo run-hook.cmd: missing script name >&2
    exit /b 1
)

set "HOOK_DIR=%~dp0"

if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
    "C:\Program Files (x86)\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

where bash >nul 2>nul
if %ERRORLEVEL% equ 0 (
    bash "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM 找不到 bash 就静默退出，插件照常可用，只是没有注入
exit /b 0
CMDBLOCK

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="$1"
shift
exec bash "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"
```

- [ ] **Step 5: 写 `hooks/hooks.json`**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
            "shell": "bash",
            "async": false
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 6: 跑测试，确认通过**

```bash
bash hooks/verify.sh
```

Expected: `全部通过`

- [ ] **Step 7: 验兜底路径**

把 rules.md 临时改名为不存在的路径，跑 hook，应该没有任何输出且退出码为 0：

```bash
mv skills/plain-language/rules.md "$CLAUDE_JOB_DIR/tmp/rules.md.bak"
bash hooks/session-start; echo "exit=$?"
mv "$CLAUDE_JOB_DIR/tmp/rules.md.bak" skills/plain-language/rules.md
```

Expected: 无输出，`exit=0`

- [ ] **Step 8: 提交**

```bash
git add hooks/
git commit -m "feat(hooks): SessionStart 注入 plain-language 规则"
```

---

### Task 4: 注入措辞定稿

**Files:**
- Modify: `hooks/session-start`（只改 `context=` 那一行的限定语部分）

**Interfaces:**
- Consumes: Task 3 的 `hooks/session-start`、Task 2 的 `rules.md`
- Produces: 定稿的注入文本；结论写回 spec 的「待定项」

- [ ] **Step 1: 取证 —— 豁免句到底管不管用**

`superpowers:writing-skills` 断言豁免句不起作用（「这条限制不适用于代码块」仍然会抑制代码块）。这是针对**现有 skill** 的断言，不擅自采信，用对照实验验。

两组，各跑 5 次一次性 subagent，任务里同时含「该保持原样的东西」（一段代码、一个 API 缩写）和「该改的东西」（一段夹英文黑话的说明文）：
- A 组限定语：`你写给人看的文字，一律按下面这份规则来：回答、文档、说明、提交信息正文。`
- B 组限定语：A 组 + 一句豁免：`代码、命令、路径、引用原文不在此列。`

**判据**：比较两组在「代码块是否被抑制/改写」「API 缩写是否被误展开」上的表现。若 B 组的代码块完好率明显更高，豁免句有效，采用 B；若两组无差别或 B 更差，采用 A，并把结论写进 spec。

- [ ] **Step 2: 定稿限定语**

按 Step 1 的结论选定 A 或 B，写进 `hooks/session-start` 的 `context=` 行。

- [ ] **Step 3: 验证注入有效（GREEN）**

同一写作任务，不带注入跑 5 次、带注入跑 5 次，逐条人工读。

**判据**：带注入组的黑话与英文夹杂出现次数下降；代码标识符、路径、命令、公认缩写、专业术语未被改写。

- [ ] **Step 4: 把结论写回 spec**

更新 `docs/superpowers/specs/2026-09-15-plain-language-sessionstart-injection-design.md` 的「待定项」，写明实测结论与依据。每条结论都要标注「跑在 deepseek-flash 上，不能外推到 Opus」。

- [ ] **Step 5: 提交**

```bash
git add hooks/session-start docs/superpowers/specs/
git commit -m "test: 注入措辞定稿，豁免句结论写回 spec"
```

---

### Task 5: README 更新

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1 的插件名与版本、Task 3 的 hook 行为
- Produces: 无

- [ ] **Step 1: 加安装章节**

在「收录的 skill」表之后、「维护」之前插入：

````markdown
## 安装

本仓库同时是一个 Claude Code 插件，`skills/` 会被自动注册，SessionStart hook 会把
`plain-language` 的写作规则注入每个会话（`startup` / `clear` / `compact` 三种时机）。

```
/plugin marketplace add zhcmeng/shared-skills
/plugin install shared-skills@shared-skills
```

其它 agent 工具读 `~/.agents/skills/`，把 `skills/<名字>` 复制或链接过去即可；
两条路互不干扰。只要技能不要常驻注入，删掉 `hooks/` 即可，`skills/` 不受影响。
````

- [ ] **Step 2: 维护节补一条**

在「维护」列表末尾加：

```markdown
- **改规则**：`skills/plain-language/rules.md` 是规则的唯一真相，改它同时改变 skill 行为和常驻注入。改完跑 `bash hooks/verify.sh` 确认注入没断
```

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs(readme): 补插件安装方式与规则维护说明"
```

---

## 自检结果

- **spec 覆盖**：文件清单 9 项全部落到 Task 1/2/3/5；测试计划 5 项落到 Task 2 Step 1（测试 1）、Task 2 Step 4（测试 3）、Task 3 Step 1-6（测试 5）、Task 4 Step 1（测试 4）、Task 4 Step 3（测试 2）；出错兜底落到 Task 3 Step 7；已知局限落到 Global Constraints
- **占位符**：无 TBD / TODO；每个代码步骤都有可直接粘贴的内容
- **类型一致性**：`rules.md` 路径在 Task 2 产出、Task 3 消费，均为 `skills/plain-language/rules.md`；hook 输出结构在 Task 3 定义、Task 4 消费，均为 `hookSpecificOutput.additionalContext`
