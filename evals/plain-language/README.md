# plain-language 用例套件

这套用例测的是 `skills/plain-language` 这个 skill——把读不懂的话重讲成读得懂的话。

判断标准只有一条：读者不知道里面的行话、也没看过上文，能不能一次读懂。

## 怎么跑

在仓库根目录：

```
claude plugin eval --eval-dir evals/plain-language
```

`--eval-dir` 别省。结果按它落到 `evals/plain-language/results/<时间戳>/`——一个 skill 一个目录；不传的话默认目录是 `evals/`，所有 skill 的报告会堆进同一个 `evals/results/` 里，分不出是哪套用例跑的。放在 skill 目录下还有一层好处：`.gitignore` 里的 `evals/*/results/` 正好盖住它，跑出来的记录不会进 git（堆在 `evals/results/` 就不是了，框架会一条条往 `.gitignore` 里补路径）。

常用参数：

| 参数 | 作用 |
|:---|:---|
| `--runs 3` | 每个用例跑几遍（默认写着 3 遍，但实测不传就只跑 1 遍——显式传更保险） |
| `--threshold 1` | 通过线（默认 1.0，即每条判据都得过） |
| `--case "01-*"` | 只跑匹配的用例（glob 只认 `*`，`1[45]-*` 这种字符组匹配不到东西） |
| `--no-publish` | 报告只留在本地 `results/`，不发到 claude.ai |
| `--allow-tools Edit Write` | 允许这次评测使用改文件的工具（见下面 09 那条） |
| `--scaffold` | 允许用例在跑之前先造文件 |

### 09-edit-file 要带两个额外参数

```
claude plugin eval --eval-dir evals/plain-language --case 09-edit-file --scaffold --allow-tools Edit Write
```

这个用例测的是"给个路径，直接改原文件"：跑之前要先在工作目录里放一份 `notes.md`，跑的时候 agent 要真的把它改掉。这两件事默认都不开。

改文件的工具要两层都写，照框架自己的告警来做：

> add Write (or Edit / Bash) to the case's allowed_tools and grant it with --allow-tools

也就是：

1. 用例头部声明——`09-edit-file/prompt.md` 里的 `allowed_tools` 写上 `Edit`、`Write`（这个字段不限取值，写什么收什么；`Read`、`Glob`、`Skill` 这类免授权的工具不写也照样能用）；
2. 命令行再授一次——`--allow-tools Edit Write`。

第 2 层不能省：用例声明了、命令行没授，跑的时候会打印 `not granted (missing --allow-tools grant, or a malformed entry)`，那个工具就当没有。造文件那件事同理，`--scaffold` 不开就没有 `notes.md`。

## 两臂跑

套件默认按 `with-without` 跑两臂：一臂装插件，一臂不装，报告里给两者的分差。不装插件那臂是基准线，用来看分数是不是插件带来的。

`tool_used: Skill` 这类判据默认不计分——不装插件那臂里它永远过不了。它只在报告里当"插件有没有被调用"的指示灯。要让它在两臂都计分，在判据里写 `arm: both`。

正例（01～06、09～15）里的 `skill-fired.md` 就是这个指示灯，故意不计分；反例（07、08）里的 `skill-not-fired.md` 写了 `arm: both`，计分——"这个 skill 不该被调用"是这两条用例要断言的。

## 用例清单

| 用例 | 测什么 |
|:---|:---|
| 01-jargon-identifiers | 一段行话夹英文的话，要求重讲。正文不许留行话、要是能从头读到尾的一整段（不是逐条点评），代码名和路径原样保留，四件事都得在 |
| 02-numbers | 一段带八个数字的方案对比。八个数字一个不少、归属对，`benchmark` 换成中文，结论仍是方案 B 且那个代价还在 |
| 03-already-clear | 一段本来就说得清楚的文字。结论得是"不用改"，最多一两处小改动——不能成片重写 |
| 04-quotation | 一段里有引用原文，也有用户自己写的结论。引文一个字不动，引号外面要把"决策旅程"讲清楚，结论重讲后意思不变 |
| 05-mismatched-term | 名字和做法对不上的术语（叫"缓存预热"，做的却是按时间窗口分批限流）。名字要么换掉、要么当场说明名不副实 |
| 06-bare-trigger | 只有一句"看不懂"，没有别的交代。得直接给出重讲的文字，反问用户算挂；也不能替原文把没交代的补上 |
| 07-neg-translate | 反例：用户要的是翻译，不是重讲。译文要覆盖四个要点，不能写成审读报告或逐句点评 |
| 08-neg-factcheck | 反例：用户要的是核对数字。前两个数确认对，第三个数指出不对，不能顺手重写一遍 |
| 09-edit-file | 文件模式：给一个路径，直接改。只动正文里的行话；YAML 表头和引文一个字不动，引文里的行话在引号外解释；改完一句话交代 |
| 10-edit-file-missing | 文件模式的反例：提示词给了路径，文件却不存在（文字直接贴在提示词里）。要说清卡在哪、把改好的文字给出来，不能凭空造出文件 |
| 11-meta-and-reference | 一段集中四种毛病的话：元标注黑话（"对冲句"）、指代不明（"它"）、同一个东西两种叫法（"灰度窗口"/"切换期"）、小标题看不出讲什么（"**补充**"） |
| 12-keep-what-should-stay | 一段里既有该换的也有不该换的：天花板/护城河/赛道要留，`.claude/memory/` 要留、"查 memory"要换，REST API / JSON / GDP 要留，`overhead` 要换 |
| 13-metaphor-for-mechanism | 一段把结论的算法说成"形状"的话（八条路、六个口子、数一数这张表）：比方要换掉，机制改成一件事一件事按顺序直说；六种情况落到"没测成"、只有两种给 pass 或 fail 这件事不能丢 |
| 14-calque-wrong-sense | 一段把 Pattern 直译成"图案"、Signature 直译成"判定形状"的话，外加一句让人去"方括号里"找文本（表里根本没有方括号，`阶段`、`消息` 还是占位）。两个直译词都得换成按字面就懂的说法，找文本那句得说清对着哪一段找、哪些字是占位 |
| 15-terms-and-register | 一段要打印出来单独用的参考页摘录：别处定义过的"考官""六道闸门"这一页没解释，"考官 fail"和"考官判 fail"混着用，"被试的锅""大体干净"这类口语混在书面语里。术语要就地解释或换成直说，判定说法要统一，口语要换书面说法 |

## 有段话是逐字复制的，改一处要全改

框架不支持判据共用片段，所以同一段话在多个文件里各存了一份。每个这样的文件末尾都挂了一行维护提示，指回这里。

### 公共前言（46 份）

出现在 `type: llm` 判据的正文开头：

> 看的是重说出来的那段正文——读者会从头读到尾的那段连续文字。回答里如果还另附了改动清单或拿不准清单，这一条不判它们：只拿正文判，那些附加内容里出现的词句不算正文里的。

分布：

- 01：`body-has-no-jargon`、`body-is-full-rewrite`、`code-names-kept`、`keeps-four-points`、`no-invented-content`
- 02：`all-eight-numbers`、`body-has-no-english`、`conclusion-unchanged`、`no-invented-content`
- 03：`at-most-one-change`、`concludes-no-changes`
- 04：`explains-quotation-word`、`numbers-kept`、`own-words-kept`
- 05：`benefit-kept`、`mechanism-clear`、`name-fixed-or-flagged`、`no-invented-content`
- 06：`answers-instead-of-asking`、`body-has-no-jargon`、`keeps-all-elements`、`no-invented-content`
- 11：`keeps-all-points`、`label-says-what-it-is`、`no-invented-content`、`no-meta-label`、`one-name-per-thing`、`references-resolved`
- 12：`abbreviations-kept`、`jargon-changed`、`keeps-all-points`、`no-invented-content`、`path-kept-term-changed`、`plain-metaphors-kept`
- 13：`keeps-all-points`、`metaphor-gone`、`no-invented-content`
- 14：`calque-gone`、`keeps-all-points`、`no-invented-content`、`reference-findable`
- 15：`keeps-all-points`、`no-invented-content`、`one-name-per-verdict`、`register-consistent`、`undefined-terms-explained`

### body-only（11 份，整份文件逐字相同）

01、02、03、04、05、06、11、12、13、14、15 各有一份 `graders/body-only.md`，内容完全一样。

## 别被 results/ 里的旧记录带偏

`results/` 下按时间戳一次一目录。2026-09-16 那批是用例还直接放在 `evals/` 底下时跑的，里面的路径写的是 `evals/01-jargon-identifiers` 这种，跟现在的目录对不上；那些目录后来也一起搬到了这里。要能看的记录，重新跑一遍。
