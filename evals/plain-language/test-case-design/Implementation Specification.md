# 实施方案规格说明

这份把六份通用设计稿落成能跑的东西。六份说的是「要什么」，这份说的是「用哪个、怎么摆」；两边冲突时，以这份为准。

方案按节分。本次只有 skill-up 一节（第二节）。将来比别的评测方案，在那后面另起一节，六份通用稿一个字不用动。

凡是能写成配置的，这份都以 YAML 原文贴出来，不是散文化地写「应该配什么」——把 2.2 那几块拷到它标注的路径上，就能跑。

## 一、通用稿的编号落到哪

改通用稿的时候对着这张表看：哪一条加了要求，这一节就要跟着补一个落点。

| 通用稿的编号 | 本方案里落在哪 | 说明 |
|:---|:---|:---|
| ENV-1 | `skill-up/eval.yaml` 的 `skills[].path` | 指向 `../../plugin/skills/plain-language`，`include` 只装 `SKILL.md` 与 `rules.md` |
| ENV-2 | `skill-up/eval.yaml` 的 `report.artifacts` 与各条 `judge.context` | 回复看 `final_message`，盘上改动看 `workspace_diff`（standard 档默认 `file_ref`） |
| ENV-3 | `skill-up/cases/<目录名>.yaml` 的 `judge.criteria` | 各条用例「预期结果」栏的散文压成条目 |
| ENV-4 | 夹具 `evals/plain-language/fixtures/repos/subject/` | 每条用例各把这个目录的内容铺进自己那份临时工作区；原始夹具全程不动。五份样本就摆在这棵树里，铺进去之后权限跟原始样本一致（TC-7 那份是只读的） |
| ENV-5 | 两次运行的 `environment.setup_steps`——从绝对路径读 `rules.md` 写进工作区的 `CLAUDE.md`；见 2.1 第 5 小节第 4 条 | 钩子那条道在本方案里走不通：skill-up 起 claude 时带 `--settings '{"disableAllHooks":true}'`，钩子一律不生效 |
| ENV-6 | skill-up 每条用例各建一个的临时工作区 | 见 2.1 第 3 小节：跑完就删，重试与迭代各起一个。ENV-6 要的「每跑一条之前清干净」由框架自己保证 |
| ENV-7 | 同上那一个临时工作区 | 被测那侧就是建这个目录的机器（本机 Windows）；样本副本也在这一处 |
| DATA-1 | `fixtures/repos/subject/evals/plain-language/cases/tp01-01-TC-1-fix_only_what_should_change/fixture/样本.md` | 混合文档样本；路径的基准见 2.2 开头 |
| DATA-2 | `fixtures/repos/subject/evals/plain-language/cases/tp02-01-TC-2-quotes_kept_and_glossed/fixture/样本.md` | 引文文档样本；同上 |
| DATA-3 | `fixtures/repos/subject/evals/plain-language/cases/tp03-01-TC-3-scope_of_review/fixture/样本.md` | 审的范围文档样本；同上 |
| DATA-4 | `fixtures/repos/subject/evals/plain-language/cases/tp04-01-TC-6-file_nothing_to_fix/fixture/样本.md` | 一处问题都没有的文档样本；同上 |
| DATA-5 | `skill-up/cases/tp06-01-TC-4-restate_whole_answer.yaml` 的 `input.prompt` 正文 | 接在用户消息前面，见 2.1 第 5 小节第 3 条 |
| DATA-6 | `skill-up/cases/tp07-01-TC-5-restate_nothing_to_fix.yaml` 的 `input.prompt` 正文 | 同上 |
| DATA-7 | `skill-up/cases/tp01-01-TC-1-fix_only_what_should_change.yaml` 的 `input.prompt` | 一条对一条 |
| DATA-8 | `skill-up/cases/tp02-01-TC-2-quotes_kept_and_glossed.yaml` 的 `input.prompt` | 同上 |
| DATA-9 | `skill-up/cases/tp03-01-TC-3-scope_of_review.yaml` 的 `input.prompt` | 同上 |
| DATA-10 | `skill-up/cases/tp06-01-TC-4-restate_whole_answer.yaml` 的 `input.prompt` | 同上（同一条 YAML 里另有 DATA-5） |
| DATA-11 | `skill-up/cases/tp07-01-TC-5-restate_nothing_to_fix.yaml` 的 `input.prompt` | 同上（同一条 YAML 里另有 DATA-6） |
| DATA-12 | `skill-up/cases/tp04-01-TC-6-file_nothing_to_fix.yaml` 的 `input.prompt` | 同上 |
| DATA-13 | `skill-up/cases/tp05-01-TC-7-file_blocked_reports_where.yaml` 的 `input.turns` | 同上；这一条装的是两条消息，一轮一条 |
| DATA-14 | `skill-up/cases/tp08-01-TC-8-ambient_writing_stays_plain.yaml` 的 `input.prompt` | 同上 |
| DATA-15 | `fixtures/repos/subject/evals/plain-language/cases/tp05-01-TC-7-file_blocked_reports_where/fixture/只读样本.md` | 没有写权限的文档样本；权限靠工作树带过去，**git 不存这个属性**，重新克隆之后要在工作树里重设一次（`chmod 444`），见 2.1 第 3 小节 |

## 二、方案：skill-up

### 2.1 说明

**1. 这份管什么**

把六份通用设计稿落成 skill-up 跑得起来的东西。八条测试规程（TP-1 至 TP-8）落成八个用例目录与八条用例配置，技能本身一个字不改。

**2. 跑几次、每次跑哪几条**

两次。

- **运行一**：装技能，跑 TP-1 至 TP-7（TC-1 至 TC-7），配置是 `eval.yaml`。
- **运行二**：不装技能，跑 TP-8（TC-8），配置是 `eval-no-skill.yaml`。

分两次的理由：技能配在 `eval.yaml` 这一层，一条用例一层配不了——skill-up 的用例配置里没有按用例的 `skills` 字段。TC-8 那一档要的正是「`rules.md` 已经在上下文里、但技能没被唤起」，装不装技能是两次运行的分别。

**3. 工作区怎么来**

不用 `--workspace` 了。每条用例开跑前，skill-up 自己在系统临时目录下新建一个空的 `skill-up-<随机数>` 当工作区，跑完删掉；重试与迭代各起一个。ENV-6 要的「能重来、能隔离」由框架自己保证，不靠人记得重建。

这个空目录里只进三样东西，一样都不来自本仓库的工作树：

1. **常驻注入**：第 5 小节第 4 条那条 `setup_steps`，最先跑。
2. **技能**：随后装到 `.claude/skills/plain-language/`，照 `include` 只装 `SKILL.md` 与 `rules.md`（运行二不装这一档）。
3. **夹具**：最后把 `evals/plain-language/fixtures/repos/subject/` 这棵子树的**内容**铺到工作区根上，由 `context.repo_fixture: fixtures/repos/subject` 指定。五份样本摆在这棵树里，位置照 DATA-7 至 DATA-14 那几条消息写的。

顺序是实测的：`setup_steps` 跑在夹具铺进来**之前**。所以夹具里不许有 `CLAUDE.md`——放了会把注入冲掉。

**只读那份样本的权限靠工作树带过去。** skill-up 铺夹具是逐字节写文件、连原文件的权限一起带上（`none` 这一档的 `UploadDir` 保留源文件的模式位），所以 DATA-15 在工作树里设成只读，铺进工作区之后还是只读——TC-7 判据⑤要的「写不进去」这个前提才成立。**git 不存这个属性**（它只存执行位），重新克隆仓库之后那份文件又变回可写的，跑之前要在工作树里重设一次：

```bash
chmod 444 "C:/work/shared-skills/evals/plain-language/fixtures/repos/subject/evals/plain-language/cases/tp05-01-TC-7-file_blocked_reports_where/fixture/只读样本.md"
```

没设成只读就跑，agent 会把它改掉，判据⑤判不过，屏幕上看不出是环境没摆对——所以这条要在跑之前自己核一眼。

**差集要开 `context.git.init`。** 工作区是新建的空目录，不是 git 仓库。skill-up 拍基线之前先探一下这里是不是 git 仓库，不是就**把差集静默关掉**——不报错、不中断，只在判官材料的清单里留一行 `workspace_diff: omit`，屏幕上什么也看不出来。开了 `git.init: true`，它就在工作区里 `git init`，把当时盘上所有文件 `git add --all` 提交成一条基线；这条基线是在夹具与注入都到位之后拍的，所以差集里只剩被测 agent 改的东西。用到 `workspace_diff` 的五条（TC-1、TC-2、TC-3、TC-6、TC-7）都带这一项；另外三条不带，因为它们的判据不看盘上改动，带了也是白拍。

**判据进不来。** skill-up 装技能时无条件跳过 `evals/` 这棵子树（`internal/agent/skill.go` 里写死的那条），与 `include`、`exclude` 无关；工作区又是个新建的空目录，不是仓库副本。判据、六份设计稿、技能源码一个字节都到不了被测 agent 手里。

**为什么不再拿仓库副本当工作区。** 那时候要副本，是为了让样本路径指得到。现在这个目的由夹具顶上，而夹具只带样本、不带别的，代价小得多——先前那份副本把判据也一并带进了被测 agent 的视野。

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
| TC-6 | 退出码 0；同上三个词 | 那份文件逐字节没变、回复说出了「这份没有需要改的地方」这个意思、没有硬凑 |
| TC-7 | 退出码 0 | 第一轮说清是哪个路径读不到、为什么；第二轮说清卡在哪、把改好的文本一并给出；两轮都没有凭空说已经改好了；盘上那份只读样本逐字节没变 |
| TC-4 | 退出码 0 | 重讲的正文里那几类问题不再出现、信息不增不减、只给正文 |
| TC-5 | 退出码 0 | 说出了「这段没有需要改的地方」这个意思、没有硬凑 |
| TC-8 | 退出码 0 | 英文词都就地给了中文、没有自造压缩黑话与生造词、没有夹英文的句子 |

**两处不拿 `must_contain` 卡原话**：TC-6、TC-5 要的「这段没有需要改的地方」，用例规格说明的「预期结果」栏写的是「说出了……这个意思」——措辞不限，判的是那件事有没有做到。拿原文卡会造出一个假的闸门：话换个说法说对了，闸门照样拦下来。这一处交给语义层判。

`criteria` 的第一条对每一条都一样，写死：「只看这一轮的产出与盘上的改动；不替 agent 补话，也不替它解释。」这一句来自 ENV-3。

**5. 消息与上下文怎么渲染**

**第 1 条：技能怎么被唤起。** 消息里的 `/shared-skills:plain-language` 渲染成 `/plain-language`。skill-up 只把技能目录装到 `.claude/skills/<技能名>/`，没有装插件这条道，带插件前缀唤起不来。

**第 2 条：样本路径。** 按工作区里的相对路径原样给（`evals/plain-language/cases/<目录名>/fixture/样本.md`）。这个路径在新工作区里指得到，靠的是夹具照同一串路径把样本摆进去，不再靠「工作区是本仓库的副本」。

**第 3 条：TC-4、TC-5 的「上一条回答」。** 按甲路径渲染——把 DATA-5、DATA-6 的全文接在用户消息前面，写成「你上一条回答我读不懂：<那段全文>。重讲一遍」。

这里有一处**保真度折扣**，读判据的时候要知道：真跑时那段文字是对话历史里的一条独立消息；渲染之后，它变成同一条用户消息里的一段引用。原因是 skill-up 的多轮对话只收 `user` 角色，塞不进一条 assistant 消息。受影响的是「上一条回答在哪」这件事——判据里不要写它；不受影响的是「重讲的那段正文」——判据里判的正是这个，照旧。

**备选（丁）**：这两条本方案不跑，等 skill-up 支持注入 assistant 轮次再补。

**第 4 条：ENV-5 的注入怎么摆。** 走「项目根目录的 `CLAUDE.md`」这条道，写进两次运行各自的 `environment.setup_steps`——一条 `cat "<绝对路径>" >> CLAUDE.md`。Claude Code 起会话时会读项目根目录的 `CLAUDE.md`，它与 SessionStart 钩子一样，是会话开头的常驻上下文。

**两次运行开跑前都会接**，因为只给运行二接会让运行一那七条没有常驻注入——与测试环境需求里「其余七条规程跑的时候 `rules.md` 同样已经注入」对不上，也与真实用法对不上（真实使用者那里规则本来就常驻，技能另外也在）。两次都接，八条的差别才回到「用不用 skill」这一件事上。

命令里那条路径是**绝对路径，写死在本机**，换机器要改。相对路径在这里用不了：`setup_steps` 在工作区里跑，而那个时刻工作区还是个空目录，没有可作基准的东西。命令由 skill-up 自己找的 Git Bash 跑（`internal/platform/shell_windows.go`）；机器上没有 Git Bash 会退到 cmd.exe，那条命令里的 `cat` 与 `>>` 就不成立了。

- **为什么不用钩子**：skill-up 拼的命令带 `--settings '{"disableAllHooks":true}'`，钩子一律不生效。
- **为什么不用 `claude -p --append-system-prompt`**：skill-up 没有传额外参数的口子，这条命令行它拼不出来；实测能跑的是钩子那条原路，而钩子被关了。
- **为什么不用「把 `rules.md` 接在用户消息前面」**：那样它就成了这一条消息里的内容，不再是被测的那个常驻注入，而 TC-8 判的正是常驻注入之下的落笔。
- **为什么不用「放一份 `rules.md` 在夹具里，命名成 `CLAUDE.md`」**：那一份会跟真仓库那份各自漂移；改了 `rules.md` 忘了同步夹具，跑出来的结论就不作数。从绝对路径读真仓库那份，只有一份源。

**第 5 条：TC-7 的两轮怎么发。** 这一条用 `input.turns` 发两条用户消息，一轮一条（其余七条用 `input.prompt` 发一条）。skill-up 接着同一个会话跑第二轮（`claude_code` 这一档支持按会话 ID 接着跑），所以第二轮里 agent 还记得第一轮给过什么。判据按轮分开写：判官拿到的材料是完整 transcript 加上最后一条回复，第一轮那条回复要从 transcript 里取——判据第一条明写了这件事。

**6. 跑不了原样的那几条**

- TC-4、TC-5：第 5 小节第 3 条那处折扣。其余四条（TC-1、TC-2、TC-3、TC-6）与设计稿一致，没有出入。
- TC-7：**这一条走两轮**，其余七条一轮。第一轮那个路径本来就不存在（与设计稿一致，不用另摆什么）；第二轮那份只读样本按 DATA-15 摆在工作树里，权限靠工作树带过去（见第 3 小节）。两轮合在一条用例里，是因为两路的触发方式与失败形状相同，分开只是把同一条链再走一遍。这条用例的前身在实测里暴露过一次口径问题：那一轮给的是不存在的路径，判据却要求「回复里把改好的文本一并给出」——那份文档不存在，没有正文可附，判据必然判不过。拆成两轮正是为了把这个口径钉死：读不到那一档只判「说清是哪个路径」，给正文那一档才判「把改好的文本一并给出」。
- TC-8：这一档不经 skill，跑法与其余七条不同——不装技能，只靠常驻注入的那份 `rules.md`。这是设计稿里就写着的，不是折扣。

### 2.2 可跑配置（YAML 原文）

**相对路径的基准是 `evals/plain-language/`。** skill-up 找技能根的办法是：从 `eval.yaml` 所在目录往上找带 `SKILL.md` 的目录；找不到就退到「`eval.yaml` 所在目录的上一层」。配置文件放在 `evals/plain-language/skill-up/` 下，上一层正好是 `evals/plain-language/`，所以 `skills[].path` 写成 `../../plugin/skills/plain-language`、`cases.files` 写成 `skill-up/cases/...`。

**第 1 块：运行一的 `eval.yaml`，落到 `evals/plain-language/skill-up/eval.yaml`**

```yaml
# 运行一：装技能，跑 TP-1 至 TP-7（TC-1 至 TC-7）。
# 相对路径的基准是 evals/plain-language/。改这一份之前先看实施方案 2.1 第 3 小节。
# ENV-5 的注入由下面 setup_steps 那条命令做：从绝对路径读真仓库那份 rules.md，写进工作区的
# CLAUDE.md。那条路径写死在本机，换机器要改。见实施方案 2.1 第 5 小节第 4 条。
schema_version: v1alpha1

environment:
  type: none
  setup_steps:
    - run: cat "C:/work/shared-skills/plugin/skills/plain-language/rules.md" >> CLAUDE.md

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

`parallelism: 1` 与 `retry_policy.max_retries: 0` 不再是硬要求——那两条是 `--workspace` 带出来的，`--workspace` 不用了。留着 1 与 0 是因为八条一跑就是八轮模型调用，先串行跑；每条用例各一个干净工作区，重试在盘上是安全的，要并行、要重试随时可以调。`benchmark` 也留着关：开着是把同一批重复跑若干轮比稳定性，不是这里要的。

**第 2 块：运行二的 `eval-no-skill.yaml`，落到 `evals/plain-language/skill-up/eval-no-skill.yaml`**

```yaml
# 运行二：不装技能，只跑 TP-8（TC-8）。
# 这一档判的是「rules.md 注进上下文之后，落笔时按不按它写」；技能会不会被唤起不在这批用例里判。
# ENV-5 的注入由下面 setup_steps 那条命令做，与运行一同一条道；见 2.1 第 5 小节第 4 条。
schema_version: v1alpha1

environment:
  type: none
  setup_steps:
    - run: cat "C:/work/shared-skills/plugin/skills/plain-language/rules.md" >> CLAUDE.md

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

八块都带 `context.repo_fixture: fixtures/repos/subject`（夹具，见 2.1 第 3 小节）。其中用到 `workspace_diff` 的五块（TC-1、TC-2、TC-3、TC-6、TC-7）还带 `context.git.init: true`——不开这一项，差集会被静默关掉。

TC-4、TC-5 那两块多一段：`input.prompt` 的前头接着 DATA-5、DATA-6 的全文，见 2.1 第 5 小节第 3 条。

```yaml
# 落到 evals/plain-language/skill-up/cases/tp01-01-TC-1-fix_only_what_should_change.yaml
# TP-1 / TC-1（高风险；覆盖项 TCOV-1 至 TCOV-13、TCOV-21、TCOV-22、TCOV-25 至 TCOV-27、TCOV-32、TCOV-35）
id: tp01-01-TC-1-fix_only_what_should_change
title: 该改的改掉、不该动的一个字没动
description: 给一份混合文档的路径，逐句审并直接改原文件；改完该改的都改了、照原样写的那些一个字没动

input:
  prompt: |
    /plain-language 这份文档读着绕，帮我改一下：evals/plain-language/cases/tp01-01-TC-1-fix_only_what_should_change/fixture/样本.md

context:
  repo_fixture: fixtures/repos/subject
  # 差集要它：工作区是新建的空目录，不开这一项 skill-up 会把差集静默关掉。见实施方案 2.1 第 3 小节。
  git:
    init: true

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
    - "那份文档副本之外的任何文件都没被动过。"
  pass_threshold: 0.7
  context:
    profile: standard
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

context:
  repo_fixture: fixtures/repos/subject
  # 差集要它：工作区是新建的空目录，不开这一项 skill-up 会把差集静默关掉。见实施方案 2.1 第 3 小节。
  git:
    init: true

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
    - "那份文档副本之外的任何文件都没被动过。"
  pass_threshold: 0.7
  context:
    profile: standard
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

context:
  repo_fixture: fixtures/repos/subject
  # 差集要它：工作区是新建的空目录，不开这一项 skill-up 会把差集静默关掉。见实施方案 2.1 第 3 小节。
  git:
    init: true

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
    - "代码块那一处——块内的中文注释或字符串——依据没有规定审不审：这条只看回复里有没有说清 agent 对那一处做了什么（动了还是没动、动成了什么样），好让用户定口径。改了算过、没改也算过，唯独回复里对这一处一个字不提、用户看不出它现在是什么状态，算不过。动了没动以盘上改动为准。"
    - "那份文档副本之外的任何文件都没被动过。"
  pass_threshold: 0.7
  context:
    profile: standard
```

```yaml
# 落到 evals/plain-language/skill-up/cases/tp04-01-TC-6-file_nothing_to_fix.yaml
# TP-4 / TC-6（高风险；覆盖项 TCOV-31、TCOV-36）
id: tp04-01-TC-6-file_nothing_to_fix
title: 一处问题都没有的文件，一个字不动
description: 给一份通篇平实中文的文档的路径；跑完那份文件逐字节没变，回复里说「这段没有需要改的地方」

input:
  prompt: |
    /plain-language 帮我看看这份文档要不要改：evals/plain-language/cases/tp04-01-TC-6-file_nothing_to_fix/fixture/样本.md

context:
  repo_fixture: fixtures/repos/subject
  # 差集要它：工作区是新建的空目录，不开这一项 skill-up 会把差集静默关掉。见实施方案 2.1 第 3 小节。
  git:
    init: true

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
    - "那份文件跑完与跑前逐字节相同。"
    - "回复里说出了「这段没有需要改的地方」这个意思，措辞不限：说出了一个意思就行，不要求原话。"
    - "没有为了显得干了活而改一处本来没问题的地方，也没有把原文换一种说法重抄一遍。"
    - "那份文档副本之外的任何文件都没被动过。"
  pass_threshold: 0.7
  context:
    profile: standard
```

```yaml
# 落到 evals/plain-language/skill-up/cases/tp05-01-TC-7-file_blocked_reports_where.yaml
# TP-5 / TC-7（中风险；覆盖项 TCOV-30、TCOV-33、TCOV-37）
# 两轮一条用例：第一轮那个路径本来就不存在，第二轮那份没有写权限（见 DATA-15）。
id: tp05-01-TC-7-file_blocked_reports_where
title: 改不动的文件：读不到的说清路径，写不进去的说清卡在哪
description: 两轮：第一轮给一个本来就不存在的路径，回复里说清是哪个路径读不到；第二轮给一份没有写权限的样本，说清卡在哪、把改好的文本一并给出

input:
  turns:
    - role: user
      content: |
        /plain-language 帮我改一下这份文档：evals/plain-language/cases/tp05-01-TC-7-file_blocked_reports_where/fixture/不存在的文件.md
    - role: user
      content: |
        /plain-language 那这份呢：evals/plain-language/cases/tp05-01-TC-7-file_blocked_reports_where/fixture/只读样本.md

context:
  repo_fixture: fixtures/repos/subject
  # 差集要它：工作区是新建的空目录，不开这一项 skill-up 会把差集静默关掉。见实施方案 2.1 第 3 小节。
  git:
    init: true

constraints:
  timeout_seconds: 600
  max_turns: 12

expect:
  exit_code: 0

judge:
  type: agent_judge
  model: anthropic/claude-sonnet-4-6
  criteria:
    - "两轮分开判：第一轮按 transcript 里第一轮的那条回复判，第二轮按最后一条回复判。只看这两轮的产出与盘上的改动；不替 agent 补话，也不替它解释。"
    - "第一轮：回复里说清了是哪个路径读不到、为什么，措辞不限。"
    - "第二轮：回复里说清了卡在哪——那份文件没有写权限这一类原因，说出一个就行，措辞不限。"
    - "第二轮：回复里把改好的文本一并给出；那段正文是从那份文件改出来的，不是凭空造的。"
    - "两轮都没有凭空说「已经改好了」，也没有把改不动的文件说成改好了、报出一个并不存在的成功结果。"
    - "盘上那份没有写权限的样本跑完与跑前逐字节相同，别的文件也没被动过。"
  pass_threshold: 0.7
  context:
    profile: standard
```

```yaml
# 落到 evals/plain-language/skill-up/cases/tp06-01-TC-4-restate_whole_answer.yaml
# TP-6 / TC-4（高风险；覆盖项 TCOV-28、TCOV-34）
# DATA-5 的全文接在用户消息里：skill-up 的多轮只收 user 角色，塞不进一条 assistant 消息。
# 这里有一处保真度折扣，见实施方案 2.1 第 5 小节第 3 条。
id: tp06-01-TC-4-restate_whole_answer
title: 无参数时把上一条回答整条重讲
description: 上一条回答里有那几类问题；重讲的那段正文里不再出现，信息不增不减，只给正文

input:
  prompt: |
    /plain-language 你上一条回答我读不懂：

    我把这次改动梳理了一下。整件事的思路是上层认知扩口、下层收割：先让读者知道现在这套检查有个盲区，再给出补上的办法。

    具体做法是在 `checks/verify.d/` 下面加一个模块，名字叫 `30-tables.sh`。这个模块的心智物理很简单：把文档里所有表格的行列数对一遍，对不上的就报出来。这样整条链路的 decision journey 会更顺一些。

    另外我们 align 一下这个 approach 的边界：新模块只管表格，链接和标题层级还是原来的 `10-links.sh` 与 `20-headings.sh` 管。跑的时候用 `bash checks/verify.sh`，一次全跑。

    重讲一遍

context:
  repo_fixture: fixtures/repos/subject

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
# DATA-6 的全文接在用户消息里：skill-up 的多轮只收 user 角色，塞不进一条 assistant 消息。
# 这里有一处保真度折扣，见实施方案 2.1 第 5 小节第 3 条。
id: tp07-01-TC-5-restate_nothing_to_fix
title: 上一条回答没毛病时不硬凑
description: 上一条回答一处问题都没有；说出「这段没有需要改的地方」，不为了显得干了活而改一处

input:
  prompt: |
    /plain-language 这段我看不懂：

    这次改动我梳理了一下。

    现在这套检查有个盲区：文档里的表格没人管。链接对不对、标题层级顺不顺，`10-links.sh` 与 `20-headings.sh` 各管一样，但表格的行列数对不上，整套检查跑完也不会报。

    补的办法是在 `checks/verify.d/` 下面加一个模块，名字叫 `30-tables.sh`，文件名的数字决定它排在最后跑。这个模块只做一件事：把每张表的行列数数一遍，对不上的报出来。

    新模块的边界也说清楚：它只管表格。链接和标题层级仍旧由原来那两个模块管，不要重复检查。

    写完跑一次 `bash checks/verify.sh`，输出的最后一行会列出这次一共跑了几个模块。看到三个，就说明新模块被认出来了。

    重讲一遍

context:
  repo_fixture: fixtures/repos/subject

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
# TP-8 / TC-8（中风险；覆盖项 TCOV-38）
# 这一条跑在运行二：不装技能，只把 rules.md 注进上下文。
id: tp08-01-TC-8-ambient_writing_stays_plain
title: 常驻注入之下直接写东西
description: 不经 skill，直接发一条写作请求；产出里那几类形态不出现

input:
  prompt: |
    帮我写一段两百字左右的说明，讲讲这个仓库的检查脚本是怎么跑的

context:
  repo_fixture: fixtures/repos/subject

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
C:/Study/skill-up/bin/skill-up.exe run C:/work/shared-skills/evals/plain-language/skill-up/eval.yaml --output-dir C:/work/plain-language-eval-results
```

```bash
C:/Study/skill-up/bin/skill-up.exe run C:/work/shared-skills/evals/plain-language/skill-up/eval-no-skill.yaml --output-dir C:/work/plain-language-eval-results
```

跑之前不用手工摆任何东西：工作区由 skill-up 新建，夹具与 `rules.md` 的注入由配置里的 `context.repo_fixture` 与 `environment.setup_steps` 各做各的（2.1 第 3 小节、第 5 小节第 4 条）。两次运行之间也不用复位——它们的工作区是两个互不相干的临时目录。

`--output-dir` 落在仓库外面，报告与事件日志不进 git。想留着跑完的工作区看个究竟，加 `--no-delete`，它会把路径打进日志。

跑之前先解析一遍，确认配置本身没写错：

```bash
C:/Study/skill-up/bin/skill-up.exe validate C:/work/shared-skills/evals/plain-language/skill-up/eval.yaml
```

```bash
C:/Study/skill-up/bin/skill-up.exe validate C:/work/shared-skills/evals/plain-language/skill-up/eval-no-skill.yaml
```

报告落在 `--output-dir` 里，不进 git。本仓库的 `.gitignore` 有一条 `evals/*/results/`，本方案把报告放在仓库外面，那一条用不上，留着不管。
