# 评测用例：审哪些地方、不审哪些地方

## 这条用例防的是什么

`SKILL.md` 把「审到哪」写成一行：正文、图注与脚注说明、mermaid 图里的文字——这三处审；YAML frontmatter 和引文元数据——不审。这条划线不写清楚，agent 有两种走偏的方式：只审正文，图注、脚注、mermaid 里的问题原样留着（读者照样读不懂）；或者审过了头，把 frontmatter 里的字段名也「翻译」一遍，那是给机器看的，改了会坏事。

另外还有一处**依据里没写**：代码块里的中文——注释、字符串。这一处不判对错，只要求 agent 把实际行为记下来报给用户，由用户定口径。真要防的是「什么也没说」。

这一条钉三件事：该审的三处都审到、frontmatter 一个字没动、代码块那一处的实际行为被记下来报了。

## 怎么跑

1. 按 ENV-1 把 `plugin/skills/plain-language/` 整套（`SKILL.md` 与 `rules.md`）当作使用者机器上装好的这门技能交给 agent。本批用的是 skill-up：它把技能装到工作区的 `.claude/skills/plain-language/`，工作区根就是 ENV-6 那处临时目录。
2. 样本按 DATA-3 摆在工作区里 `evals/plain-language/cases/tp03-01-TC-3-scope_of_review/fixture/样本.md`（ENV-4）。这份文档里有一处图注、一处脚注说明、一个 mermaid 图、一段 YAML frontmatter、一个带中文注释的代码块。原始样本在仓库里同一个路径下，全程不动。
3. 发下面这条用户消息（DATA-9）。
4. 按 ENV-2 取这一轮的回复，以及那份样本在跑前跑后的差别；按 `graders/scope-respected.md` 与 `graders/code-block-unspecified.md`（ENV-3）判——**两条都要过**才算这一条用例过。

用户消息（DATA-9。规格里写的是 `/shared-skills:plain-language`，真跑时渲染成 `/plain-language`——skill-up 只把技能装到 `.claude/skills/` 下，没有装插件那条道，带插件前缀唤起不来。见实施方案 2.1 第 5 小节第 1 条）：

```
/plain-language 帮我改一下这份文档：evals/plain-language/cases/tp03-01-TC-3-scope_of_review/fixture/样本.md
```

## 基线证据

跑过两次（2026-09-29）：**2 次 2 过**，但第一次那过不算数（判据当时是空的），收紧判据后重跑的那次才算。

1. 第一次（`batch3-full` 运行一）：判 8/8。该审的三处改对了、frontmatter 没动——盘上 `workspace.diff` 3 处替换：mermaid 节点 `B{先做一次认知对齐}`→`B{先核对表结构}`；图注 `先跟源库 align 一下 schema`→`先跟源库核对一下表结构（schema）`；脚注 `服务器换了 region 之后`→`服务器换到别的区域（region）之后`。回复原话：「改好了：`evals/plain-language/cases/tp03-01-TC-3-scope_of_review/fixture/样本.md`。」
2. **但这一过里代码块那条判据没判住。** YAML 原来写「把实际行为记下来……报给用户定口径，不判对错……唯独不许不记这一处」，判官读成「判官自己记下来」，于是在**回复里一个字没提代码块**的情况下判了这条过——它自己的证据里明写着「末轮回复只有一句『改好了：…』，没有提到这一处是改了还是留了」。规格（`Test Case Specification.md:68` 第 ④ 条）要的是「报给用户定口径」，判据收紧了，改成「这条只看回复里有没有说清 agent 对那一处做了什么……唯独回复里对这一处一个字不提……算不过」。
3. 收紧后重跑（`tc03-rerun`）：判 8/8，这次**判据真判住了**。回复原话：「改好了，共三处：流程图里的文字、图注、脚注；代码块与 frontmatter 不在审核范围，未动。」判官把「代码块……未动」那句引进了证据里。
4. 顺带记一笔：这一条的行为本来是抖的——同样一份料，第一次一个字没提代码块，第二次主动交代了。收紧之后，第一次那种写法会被判掉。

实际行为留个档：两轮里代码块都一个字没动，块内的「先把两边的心智模型对齐」「schema 对不上」原样留着。

## 规格说明里的对应

用例 TC-3（高风险；覆盖项 TCOV-16 至 TCOV-18、TCOV-20、TCOV-23，对应 TM-1 的 Q3 与 TM-2 的处置规则 1、TM-3 的产出规则 6），排在规程 TP-3 里；用户消息是 DATA-9，样本按 DATA-3 造。规格说明在 `evals/plain-language/test-case-design/` 下。
