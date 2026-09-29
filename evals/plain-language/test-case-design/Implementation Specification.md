# 实施方案规格说明

这份把六份通用设计稿落成能跑的东西。六份说的是「要什么」，这份说的是「用哪个、怎么摆」；两边冲突时，以这份为准。

方案按节分。本次只有 skill-up 一节（第二节）。将来比别的评测方案，在那后面另起一节，六份通用稿一个字不用动。

凡是能写成配置的，这份都以 YAML 原文贴出来，不是散文化地写「应该配什么」——把 2.2 那几块拷到它标注的路径上，就能跑。

## 一、通用稿的编号落到哪

改通用稿的时候对着这张表看：哪一条加了要求，这一节就要跟着补一个落点。

| 通用稿的编号 | 本方案里落在哪 | 说明 |
|:---|:---|:---|
| ENV-1 | `skill-up/eval.yaml` 的 `skills[].path` | 指向 `../../plugin/skills/plain-language`，`include` 只装 `SKILL.md` 与 `rules.md` |
| ENV-2 | `skill-up/eval.yaml` 的 `report.artifacts` 与各条 `judge.context` | 回复看 `final_message`，盘上改动看 `workspace_diff: file_ref` |
| ENV-3 | `skill-up/cases/<目录名>.yaml` 的 `judge.criteria` | 各条用例「预期结果」栏的散文压成条目 |
| ENV-4 | 工作区副本 `C:\work\plain-language-eval-workspace` | 一份仓库副本，每次运行前整份重建 |
| ENV-5 | 运行二的工作区里那份 `CLAUDE.md`——把 `rules.md` 的内容接在它末尾；见 2.1 第 5 小节 | 钩子那条道在本方案里走不通：skill-up 起 claude 时带 `--settings '{"disableAllHooks":true}'`，钩子一律不生效 |
| ENV-6 | `--workspace C:\work\plain-language-eval-workspace` | 见 2.1 第 3 小节：一份目录，每次运行前重建 |
| ENV-7 | 同上那一份目录 | 被测那侧就是这份副本所在的机器（本机 Windows） |
| DATA-1 | `evals/plain-language/cases/tp01-01-TC-1-fix_only_what_should_change/fixture/样本.md` | 混合文档样本 |
| DATA-2 | `evals/plain-language/cases/tp02-01-TC-2-quotes_kept_and_glossed/fixture/样本.md` | 引文文档样本 |
| DATA-3 | `evals/plain-language/cases/tp03-01-TC-3-scope_of_review/fixture/样本.md` | 审的范围文档样本 |
| DATA-4 | `evals/plain-language/cases/tp04-01-TC-6-file_nothing_to_fix/fixture/样本.md` | 一处问题都没有的文档样本 |
| DATA-5 | `skill-up/cases/tp06-01-TC-4-restate_whole_answer.yaml` 的 `input.prompt` 正文 | 接在用户消息前面，见 2.1 第 5 小节第 3 条 |
| DATA-6 | `skill-up/cases/tp07-01-TC-5-restate_nothing_to_fix.yaml` 的 `input.prompt` 正文 | 同上 |
| DATA-7 | `skill-up/cases/tp01-01-TC-1-fix_only_what_should_change.yaml` 的 `input.prompt` | 一条对一条 |
| DATA-8 | `skill-up/cases/tp02-01-TC-2-quotes_kept_and_glossed.yaml` 的 `input.prompt` | 同上 |
| DATA-9 | `skill-up/cases/tp03-01-TC-3-scope_of_review.yaml` 的 `input.prompt` | 同上 |
| DATA-10 | `skill-up/cases/tp06-01-TC-4-restate_whole_answer.yaml` 的 `input.prompt` | 同上（同一条 YAML 里另有 DATA-5） |
| DATA-11 | `skill-up/cases/tp07-01-TC-5-restate_nothing_to_fix.yaml` 的 `input.prompt` | 同上（同一条 YAML 里另有 DATA-6） |
| DATA-12 | `skill-up/cases/tp04-01-TC-6-file_nothing_to_fix.yaml` 的 `input.prompt` | 同上 |
| DATA-13 | `skill-up/cases/tp05-01-TC-7-file_blocked_reports_where.yaml` 的 `input.prompt` | 同上 |
| DATA-14 | `skill-up/cases/tp08-01-TC-8-ambient_writing_stays_plain.yaml` 的 `input.prompt` | 同上 |

## 二、方案：skill-up

### 2.1 说明

**1. 这份管什么**

把六份通用设计稿落成 skill-up 跑得起来的东西。八条测试规程（TP-1 至 TP-8）落成八个用例目录与八条用例配置，技能本身一个字不改。

**2. 跑几次、每次跑哪几条**

两次。

- **运行一**：装技能，跑 TP-1 至 TP-7（TC-1 至 TC-7），配置是 `eval.yaml`。
- **运行二**：不装技能，跑 TP-8（TC-8），配置是 `eval-no-skill.yaml`。

分两次的理由：技能配在 `eval.yaml` 这一层，一条用例一层配不了——skill-up 的用例配置里没有按用例的 `skills` 字段。TC-8 那一档要的正是「`rules.md` 已经在上下文里、但技能没被唤起」，装不装技能是两次运行的分别。

**3. 工作区怎么摆与复位**

`--workspace` 指 `C:\work\plain-language-eval-workspace`，一份本仓库的副本。

**每次运行前把这一份整份重建。** 同一批用例、重试、迭代串行复用这一个目录，配置里的准备动作、夹具、技能安装与 agent 的改动都会传到后面几条，而 skill-up 永远不会删这个目录。重试次数设成 0（`retry_policy.max_retries: 0`），否则失败的那条会在同一个脏目录里重跑。

判「有没有动到不该动的」按**本条用例自己的差集**判，不按整个工作区的差集判：运行一里七条串行跑，前面几条改过的文件会留在盘上。skill-up 跑 `agent_judge` 之前会在工作区的 `.git` 里提交一份基线，`workspace_diff` 是拿这条用例开跑时的状态比的，所以每条用例的 `workspace_diff` 只含它自己改的东西。TC-1 的判据⑤（那份文档副本之外的任何文件都没被动过）就靠这一条成立。

**4. 判据两层怎么落**

通用稿的判据分两层：机械一层、语义一层。在本方案里，两层的落点是：

- **机械层**用 `expect` 门槛。它是零花费的前置闸门，不过就不跑判官。
- **语义层**用 `judge`（`agent_judge`）。八条都用它。

八条都用 `agent_judge`，没有一条改用 `rule_based` 或 `script`：判的都是「改了哪几处、哪几处一个字没动、回复里说了什么」，落不到命令、退出码或盘上文件上。

逐条看：

| 用例 | 机械层（`expect`） | 语义层（`judge.criteria` 判什么） |
|:---|:---|:---|
| TC-1 | 退出码 0；回复里不出现「我无法」「我没有权限」「路径不存在」 | 该改的六类都改了、K 组七类一个字没动、本来没问题的句子没动、回复只一句话交代、副本之外没动过 |
| TC-2 | 退出码 0；同上三个词 | 引文逐句对照、标签式标题后面有中文指认、引文里的问题在引文外面说明、引文元数据没动 |
| TC-3 | 退出码 0；同上三个词 | 图注与脚注说明改了、mermaid 里的文字改了、frontmatter 没动、代码块那一处只记实际行为不判对错 |
| TC-6 | 退出码 0；同上三个词 | 那份文件逐字节没变、回复说出了「这段没有需要改的地方」这个意思、没有硬凑 |
| TC-7 | 退出码 0 | 说清卡在哪、把改好的文本一并给出、没有凭空说已经改好了 |
| TC-4 | 退出码 0 | 重讲的正文里那几类问题不再出现、信息不增不减、只给正文 |
| TC-5 | 退出码 0 | 说出了「这段没有需要改的地方」这个意思、没有硬凑 |
| TC-8 | 退出码 0 | 英文词都就地给了中文、没有自造压缩黑话与生造词、没有夹英文的句子 |

**两处不拿 `must_contain` 卡原话**：TC-6、TC-5 要的「这段没有需要改的地方」，用例规格说明的「预期结果」栏写的是「说出了……这个意思」——措辞不限，判的是那件事有没有做到。拿原文卡会造出一个假的闸门：话换个说法说对了，闸门照样拦下来。这一处交给语义层判。

`criteria` 的第一条对每一条都一样，写死：「只看这一轮的产出与盘上的改动；不替 agent 补话，也不替它解释。」这一句来自 ENV-3。

**5. 消息与上下文怎么渲染**

**第 1 条：技能怎么被唤起。** 消息里的 `/shared-skills:plain-language` 渲染成 `/plain-language`。skill-up 只把技能目录装到 `.claude/skills/<技能名>/`，没有装插件这条道，带插件前缀唤起不来。

**第 2 条：样本路径。** 按工作区里的相对路径原样给（`evals/plain-language/cases/<目录名>/fixture/样本.md`）。工作区就是一份本仓库的副本，这个路径指得到。

**第 3 条：TC-4、TC-5 的「上一条回答」。** 按甲路径渲染——把 DATA-5、DATA-6 的全文接在用户消息前面，写成「你上一条回答我读不懂：<那段全文>。重讲一遍」。

这里有一处**保真度折扣**，读判据的时候要知道：真跑时那段文字是对话历史里的一条独立消息；渲染之后，它变成同一条用户消息里的一段引用。原因是 skill-up 的多轮对话只收 `user` 角色，塞不进一条 assistant 消息。受影响的是「上一条回答在哪」这件事——判据里不要写它；不受影响的是「重讲的那段正文」——判据里判的正是这个，照旧。

**备选（丁）**：这两条本方案不跑，等 skill-up 支持注入 assistant 轮次再补。

**第 4 条：ENV-5 的注入怎么摆。** 走「项目根目录的 `CLAUDE.md`」这条道：运行二开跑前，把 `rules.md` 的全文接在工作区那份 `CLAUDE.md` 的末尾（只往后接，原有内容一个字不动）。Claude Code 起会话时会读项目根目录的 `CLAUDE.md`，它与 SessionStart 钩子一样是会话开头的常驻上下文。

- **为什么不用钩子**：skill-up 拼的命令带 `--settings '{"disableAllHooks":true}'`，钩子一律不生效。
- **为什么不用 `claude -p --append-system-prompt`**：skill-up 没有传额外参数的口子，这条命令行它拼不出来；实测能跑的是钩子那条原路，而钩子被关了。
- **为什么不用「把 `rules.md` 接在用户消息前面」**：那样它就成了这一条消息里的内容，不再是被测的那个常驻注入，而 TC-8 判的正是常驻注入之下的落笔。

**6. 跑不了原样的那几条**

- TC-4、TC-5：第 5 小节第 3 条那处折扣。其余五条与设计稿一致，没有出入。
- TC-7：数据项里指的路径本来就不存在，不用另摆什么，与设计稿一致。
- TC-8：这一档不经 skill，跑法与其余七条不同——不装技能、只把 `rules.md` 注进去，这是设计稿里就写着的，不是折扣。

### 2.2 可跑配置（YAML 原文）

**相对路径的基准是 `evals/plain-language/`。** skill-up 找技能根的办法是：从 `eval.yaml` 所在目录往上找带 `SKILL.md` 的目录；找不到就退到「`eval.yaml` 所在目录的上一层」。配置文件放在 `evals/plain-language/skill-up/` 下，上一层正好是 `evals/plain-language/`，所以 `skills[].path` 写成 `../../plugin/skills/plain-language`、`cases.files` 写成 `skill-up/cases/...`。

**第 1 块：运行一的 `eval.yaml`，落到 `evals/plain-language/skill-up/eval.yaml`**

```yaml
# 运行一：装技能，跑 TP-1 至 TP-7（TC-1 至 TC-7）。
# 相对路径的基准是 evals/plain-language/。改这一份之前先看实施方案 2.1 第 3 小节。
schema_version: v1alpha1

environment:
  type: none

mcp:
  servers: []

skills:
  - source: local_path
    path: ../../plugin/skills/plain-language
    include:
      - SKILL.md
      - rules.md

engine:
  name: claude_code

cases:
  files:
    - skill-up/cases/tp01-01-TC-1-fix_only_what_should_change.yaml
    - skill-up/cases/tp02-01-TC-2-quotes_kept_and_glossed.yaml
    - skill-up/cases/tp03-01-TC-3-scope_of_review.yaml
    - skill-up/cases/tp04-01-TC-6-file_nothing_to_fix.yaml
    - skill-up/cases/tp05-01-TC-7-file_blocked_reports_where.yaml
    - skill-up/cases/tp06-01-TC-4-restate_whole_answer.yaml
    - skill-up/cases/tp07-01-TC-5-restate_nothing_to_fix.yaml
  defaults:
    timeout_seconds: 600
    max_turns: 12
    expect:
      exit_code: 0
  parallelism: 1
  retry_policy:
    max_retries: 0

benchmark:
  enabled: false

report:
  formats: [json, html]
  artifacts: [transcript]
```

TC-1 排在最前：它的判据⑤是「那份文档副本之外的任何文件都没被动过」，先跑它，后面几条改的文件才不会混进它的差集。

`parallelism: 1` 与 `retry_policy.max_retries: 0` 是 `--workspace` 的硬要求与配套：`--workspace` 只支持 `environment.type: none`、`cases.parallelism: 1`，并且 benchmark 必须关着。

**第 2 块：运行二的 `eval-no-skill.yaml`，落到 `evals/plain-language/skill-up/eval-no-skill.yaml`**

```yaml
# 运行二：不装技能，只跑 TP-8（TC-8）。
# 这一档判的是「rules.md 注进上下文之后，落笔时按不按它写」；技能会不会被唤起不在这批用例里判。
# ENV-5 的注入不落在这一份里：开跑前把 rules.md 接到工作区那份 CLAUDE.md 末尾，见 2.1 第 5 小节第 4 条。
schema_version: v1alpha1

environment:
  type: none

mcp:
  servers: []

engine:
  name: claude_code

cases:
  files:
    - skill-up/cases/tp08-01-TC-8-ambient_writing_stays_plain.yaml
  defaults:
    timeout_seconds: 600
    max_turns: 12
    expect:
      exit_code: 0
  parallelism: 1
  retry_policy:
    max_retries: 0

benchmark:
  enabled: false

report:
  formats: [json, html]
  artifacts: [transcript]
```

**这里没有 `skills:` 段**——这正是分两次跑的理由。

**第 3 块：八条用例配置，落到 `evals/plain-language/skill-up/cases/<目录名>.yaml`**

八块。每块的 `title` 照该条用例的目标写，`input.prompt` 照 DATA-7 至 DATA-14 抄（`/shared-skills:` 换成 `/`），`judge.criteria` 照测试用例规格说明该条「预期结果」栏压成条目。

TC-4、TC-5 那两块多一段：`input.prompt` 的前头接着 DATA-5、DATA-6 的全文，见 2.1 第 5 小节第 3 条。

```yaml
# 落到 evals/plain-language/skill-up/cases/tp01-01-TC-1-fix_only_what_should_change.yaml
# TP-1 / TC-1（高风险；覆盖项 TCOV-1 至 TCOV-13、TCOV-21、TCOV-22、TCOV-25 至 TCOV-27、TCOV-30、TCOV-33）
id: tp01-01-TC-1-fix_only_what_should_change
title: 该改的改掉、不该动的一个字没动
description: 给一份混合文档的路径，逐句审并直接改原文件；改完该改的都改了、照原样写的那些一个字没动

input:
  prompt: |
    /plain-language 这份文档读着绕，帮我改一下：evals/plain-language/cases/tp01-01-TC-1-fix_only_what_should_change/fixture/样本.md

constraints:
  timeout_seconds: 600
  max_turns: 12

expect:
  exit_code: 0
  must_not_contain:
    - "我无法"
    - "我没有权限"
    - "路径不存在"

judge:
  type: agent_judge
  model: anthropic/claude-sonnet-4-6
  criteria:
    - "只看这一轮的产出与盘上的改动；不替 agent 补话，也不替它解释。"
    - "属于那几类问题的那几处都换成了按字面就懂的中文说法，各处的原词都不再出现。"
    - "文中已给出定义的术语、代码标识符、路径、命令名、产品名、公认缩写、已经进入中文日常用法的直译词，这七类一个字没动。"
    - "文档里本来就没问题的句子一个字没动。"
    - "回复里一句话交代了结果，没有逐处解释改了什么、为什么改；做到算过，逐处解释算不过。"
    - "那份文档副本之外的任何文件都没被动过——按本条用例自己的 workspace_diff 判，不含同一批里前面几条改过的东西。"
  pass_threshold: 0.7
  context:
    profile: standard
    workspace_diff: file_ref
```

```yaml
# 落到 evals/plain-language/skill-up/cases/tp02-01-TC-2-quotes_kept_and_glossed.yaml
# TP-2 / TC-2（高风险；覆盖项 TCOV-14、TCOV-15、TCOV-19、TCOV-24）
id: tp02-01-TC-2-quotes_kept_and_glossed
title: 引文原样留着，后面补中文
description: 给一份引文文档的路径；引文本身一字不动，每句原句后面补该句的中文

input:
  prompt: |
    /plain-language 这份文档里引了几段英文，我看着费劲，帮我改一下：evals/plain-language/cases/tp02-01-TC-2-quotes_kept_and_glossed/fixture/样本.md

constraints:
  timeout_seconds: 600
  max_turns: 12

expect:
  exit_code: 0
  must_not_contain:
    - "我无法"
    - "我没有权限"
    - "路径不存在"

judge:
  type: agent_judge
  model: anthropic/claude-sonnet-4-6
  criteria:
    - "只看这一轮的产出与盘上的改动；不替 agent 补话，也不替它解释。"
    - "成句成段的引文，每一句原句后面紧跟着该句的中文，原句本身一个字没改。"
    - "当标签用的标题或章节名，本身没动，后面有一个中文短语指认它说的是什么。"
    - "引文里面如果有那几类问题，没有在引文里面改，而是在引文外面补了说明。"
    - "引文元数据（作者、出处、年份那一类）一个字没动。"
    - "那份文档副本之外的任何文件都没被动过——按本条用例自己的 workspace_diff 判。"
  pass_threshold: 0.7
  context:
    profile: standard
    workspace_diff: file_ref
```

```yaml
# 落到 evals/plain-language/skill-up/cases/tp03-01-TC-3-scope_of_review.yaml
# TP-3 / TC-3（高风险；覆盖项 TCOV-16 至 TCOV-18、TCOV-20、TCOV-23）
id: tp03-01-TC-3-scope_of_review
title: 图注、脚注、mermaid 里的文字要审，frontmatter 不审
description: 给一份审的范围文档的路径；要审的两处改掉、不审的一处没动，代码块那一处只记实际行为

input:
  prompt: |
    /plain-language 帮我改一下这份文档：evals/plain-language/cases/tp03-01-TC-3-scope_of_review/fixture/样本.md

constraints:
  timeout_seconds: 600
  max_turns: 12

expect:
  exit_code: 0
  must_not_contain:
    - "我无法"
    - "我没有权限"
    - "路径不存在"

judge:
  type: agent_judge
  model: anthropic/claude-sonnet-4-6
  criteria:
    - "只看这一轮的产出与盘上的改动；不替 agent 补话，也不替它解释。"
    - "图注与脚注说明里那几类问题被改掉。"
    - "mermaid 图里的文字里那几类问题被改掉。"
    - "YAML frontmatter 一个字没动。"
    - "代码块那一处——块内的中文注释或字符串——依据没有规定审不审：把实际行为记下来（动没动、动成了什么样），报给用户定口径，不判对错。改了算过、没改也算过，唯独不许不记这一处。"
    - "那份文档副本之外的任何文件都没被动过——按本条用例自己的 workspace_diff 判。"
  pass_threshold: 0.7
  context:
    profile: standard
    workspace_diff: file_ref
```

```yaml
# 落到 evals/plain-language/skill-up/cases/tp04-01-TC-6-file_nothing_to_fix.yaml
# TP-4 / TC-6（高风险；覆盖项 TCOV-34）
id: tp04-01-TC-6-file_nothing_to_fix
title: 一处问题都没有的文件，一个字不动
description: 给一份通篇平实中文的文档的路径；跑完那份文件逐字节没变，回复里说「这段没有需要改的地方」

input:
  prompt: |
    /plain-language 帮我看看这份文档要不要改：evals/plain-language/cases/tp04-01-TC-6-file_nothing_to_fix/fixture/样本.md

constraints:
  timeout_seconds: 600
  max_turns: 12

expect:
  exit_code: 0
  must_not_contain:
    - "我无法"
    - "我没有权限"
    - "路径不存在"

judge:
  type: agent_judge
  model: anthropic/claude-sonnet-4-6
  criteria:
    - "只看这一轮的产出与盘上的改动；不替 agent 补话，也不替它解释。"
    - "那份文件跑完与跑前逐字节相同——workspace_diff 里这一处没有改动。措辞不限：说出了一个意思就行，不要求原话。"
    - "回复里说出了「这段没有需要改的地方」这个意思。"
    - "没有为了显得干了活而改一处本来没问题的地方，也没有把原文换一种说法重抄一遍。"
    - "那份文档副本之外的任何文件都没被动过——按本条用例自己的 workspace_diff 判。"
  pass_threshold: 0.7
  context:
    profile: standard
    workspace_diff: file_ref
```

```yaml
# 落到 evals/plain-language/skill-up/cases/tp05-01-TC-7-file_blocked_reports_where.yaml
# TP-5 / TC-7（中风险；覆盖项 TCOV-31、TCOV-35）
id: tp05-01-TC-7-file_blocked_reports_where
title: 改不动的文件：说清卡在哪
description: 给一个本来就不存在的路径；回复里说清卡在哪，把改好的文本一并给出

input:
  prompt: |
    /plain-language 帮我改一下这份文档：evals/plain-language/cases/tp05-01-TC-7-file_blocked_reports_where/fixture/不存在的文件.md

constraints:
  timeout_seconds: 600
  max_turns: 12

expect:
  exit_code: 0

judge:
  type: agent_judge
  model: anthropic/claude-sonnet-4-6
  criteria:
    - "只看这一轮的产出与盘上的改动；不替 agent 补话，也不替它解释。"
    - "回复里说清了卡在哪——路径不存在、读不进来、没有写权限这一类原因，说出一个就行，措辞不限。"
    - "回复里把改好的文本一并给出。"
    - "没有凭空说「已经改好了」，也没有报出一个并不存在的成功结果。"
    - "这一条不要求盘上有任何改动：那个路径本来就不存在。"
  pass_threshold: 0.7
  context:
    profile: standard
    workspace_diff: file_ref
```

```yaml
# 落到 evals/plain-language/skill-up/cases/tp06-01-TC-4-restate_whole_answer.yaml
# TP-6 / TC-4（高风险；覆盖项 TCOV-28、TCOV-32）
# input.prompt 的前头接着 DATA-5 的全文，见实施方案 2.1 第 5 小节第 3 条。
id: tp06-01-TC-4-restate_whole_answer
title: 无参数时把上一条回答整条重讲
description: 上一条回答里有那几类问题；重讲的那段正文里不再出现，信息不增不减，只给正文

input:
  prompt: |
    /plain-language 你上一条回答我读不懂，重讲一遍
    （这一行的前头要接上 DATA-5 的全文，写成「你上一条回答我读不懂：<那段全文>。重讲一遍」）

constraints:
  timeout_seconds: 600
  max_turns: 12

expect:
  exit_code: 0

judge:
  type: agent_judge
  model: anthropic/claude-sonnet-4-6
  criteria:
    - "只看这一轮的产出与盘上的改动；不替 agent 补话，也不替它解释。"
    - "重讲的那段正文里，那几类问题都不再出现。"
    - "信息不增不减——没有加原文没有的判断，也没有漏原文有的内容。"
    - "只给了重讲的那段正文，没有附改动说明、没有列出拿不准的地方。"
    - "不判「上一条回答在哪」这件事：它的摆法带一处保真度折扣，见实施方案 2.1 第 5 小节第 3 条。"
  pass_threshold: 0.7
  context:
    profile: standard
```

```yaml
# 落到 evals/plain-language/skill-up/cases/tp07-01-TC-5-restate_nothing_to_fix.yaml
# TP-7 / TC-5（高风险；覆盖项 TCOV-29）
# input.prompt 的前头接着 DATA-6 的全文，见实施方案 2.1 第 5 小节第 3 条。
id: tp07-01-TC-5-restate_nothing_to_fix
title: 上一条回答没毛病时不硬凑
description: 上一条回答一处问题都没有；说出「这段没有需要改的地方」，不为了显得干了活而改一处

input:
  prompt: |
    /plain-language 这段我看不懂，重讲一遍
    （这一行的前头要接上 DATA-6 的全文，见实施方案 2.1 第 5 小节第 3 条）

constraints:
  timeout_seconds: 600
  max_turns: 12

expect:
  exit_code: 0

judge:
  type: agent_judge
  model: anthropic/claude-sonnet-4-6
  criteria:
    - "只看这一轮的产出与盘上的改动；不替 agent 补话，也不替它解释。"
    - "回复里说出了「这段没有需要改的地方」这个意思。措辞不限：说出了一个意思就行，不要求原话。"
    - "没有为了显得干了活而改一处本来没问题的地方。"
    - "没有把原文换一种说法重抄一遍当成重讲。"
    - "不判「上一条回答在哪」这件事：它的摆法带一处保真度折扣，见实施方案 2.1 第 5 小节第 3 条。"
  pass_threshold: 0.7
  context:
    profile: standard
```

```yaml
# 落到 evals/plain-language/skill-up/cases/tp08-01-TC-8-ambient_writing_stays_plain.yaml
# TP-8 / TC-8（中风险；覆盖项 TCOV-36）
# 这一条跑在运行二：不装技能，只把 rules.md 注进上下文。
id: tp08-01-TC-8-ambient_writing_stays_plain
title: 常驻注入之下直接写东西
description: 不经 skill，直接发一条写作请求；产出里那几类形态不出现

input:
  prompt: |
    帮我写一段两百字左右的说明，讲讲这个仓库的检查脚本是怎么跑的

constraints:
  timeout_seconds: 600
  max_turns: 12

expect:
  exit_code: 0

judge:
  type: agent_judge
  model: anthropic/claude-sonnet-4-6
  criteria:
    - "只看这一轮的产出与盘上的改动；不替 agent 补话，也不替它解释。"
    - "产出里出现的每一个英文词，都在当地给了中文——给中文解释或给译名都算。"
    - "产出里没有出现自造压缩黑话、生造词与直译词。"
    - "产出里没有出现夹英文的句子。"
    - "这一条判的是落笔时按不按 rules.md 写，不判技能有没有被唤起。"
  pass_threshold: 0.7
  context:
    profile: standard
```

### 2.3 怎么跑、报告落在哪

两条命令。路径写全，在哪儿跑都是同一句：

```bash
C:/Study/skill-up/bin/skill-up.exe run C:/work/shared-skills/evals/plain-language/skill-up/eval.yaml --workspace C:/work/plain-language-eval-workspace --output-dir C:/work/plain-language-eval-results
```

```bash
C:/Study/skill-up/bin/skill-up.exe run C:/work/shared-skills/evals/plain-language/skill-up/eval-no-skill.yaml --workspace C:/work/plain-language-eval-workspace --output-dir C:/work/plain-language-eval-results
```

两次运行之间，把工作区那份副本整份重建成原样（2.1 第 3 小节）。运行二开跑前，另外把 `rules.md` 接到工作区那份 `CLAUDE.md` 末尾（2.1 第 5 小节第 4 条）。

`--output-dir` 必须在工作区之外——报告与事件日志不能落进 `--workspace` 那个目录，这是 skill-up 的硬要求。

跑之前先解析一遍，确认配置本身没写错：

```bash
C:/Study/skill-up/bin/skill-up.exe validate C:/work/shared-skills/evals/plain-language/skill-up/eval.yaml
```

```bash
C:/Study/skill-up/bin/skill-up.exe validate C:/work/shared-skills/evals/plain-language/skill-up/eval-no-skill.yaml
```

报告落在 `--output-dir` 里，不进 git。本仓库的 `.gitignore` 有一条 `evals/*/results/`，本方案把报告放在仓库外面，那一条用不上，留着不管。
