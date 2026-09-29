# 测试数据需求

执行八条测试规程所需的数据，逐条列出。DATA-1 至 DATA-6 是样本：前四条是要交给技能改的文档，后两条是重说那一档要放进上下文的上一条回答。DATA-7 至 DATA-14 是八条用户消息，一条对一条用例（TC-7 那条走两轮，DATA-13 装的是两条消息，一轮一条）。DATA-15 也是样本，编号排在最后是为了不动 DATA-1 至 DATA-14 的号：TC-7 第二轮那份没有写权限的文档。

| 唯一标识符 | 英文名 | 描述 | 重置需求 |
|:---|:---|:---|:---|
| DATA-1 | mixed_document | 混合文档样本：一份 Markdown 文档，正文里依次放进下面这些，句子都写成像一份真文档。**要改的六处**：一句含自造压缩黑话（「上层认知扩口」「下层收割」这一类）；一句含生造词与直译词（「心智物理」「决策旅程」这一类）；一句把 pattern 说成「图案」、把 signature 说成「判定形状」（英文词直译成中文里另一个意思的现成词）；一句夹英文（「我们 align 一下这个 approach」）；一句把英文词当日常词用（「把这段注入 context」「查一下 memory」）；一个英文标题或英文短语直接上（`Asymmetric Information`）。**不能动的七处**：文中前面已经给出过定义的一个术语，后面再用一次；一个代码标识符（`main()`）；一条路径（`plugin/skills/plain-language/rules.md`）；一个命令名（`bash checks/verify.sh`）；一个产品名（`Claude Code`）；一个公认缩写（`UTF-8`）；一个已经进入中文日常用法的直译词（「护城河」「天花板」「赛道」这一类）。**另有平实的中文两三句**，不含上面任何一类。 | 跑完复位成原样（这条用例会改它） |
| DATA-2 | quote_document | 引文文档样本：一份 Markdown 文档，里面要有：一段成句成段的英文引文（三句以上，用引用块或引号标出），其中至少一句里带那几类问题（夹英文或生造词）；一个当标签用的英文标题或章节名；一处引文元数据（作者、出处、年份那一类，写成一行小字）。引文本身一个字不许改，里面那几类问题在引文外面补说明。 | 跑完复位成原样（这条用例会改它） |
| DATA-3 | scope_document | 审的范围文档样本：一份 Markdown 文档，里面要有：一处图注或脚注说明，里面带那几类问题（夹英文这一类）；一段 mermaid 图，图里的文字里带那几类问题；一段 YAML frontmatter（开头用三横线包起来那一段）；一个代码块，块内的中文注释或字符串里带那几类问题——这一处依据没有规定审不审，用例只记录实际行为。 | 跑完复位成原样（这条用例会改它） |
| DATA-4 | clean_document | 一处问题都没有的文档样本：一份 Markdown 文档，通篇平实的中文，没有黑话、没有生造词与直译词、没有夹英文、没有英文标题；里面可以有代码标识符、路径、命令名这类照原样写的那些（它们不算问题）。 | 跑完复位成原样（这条用例要核它逐字节没变） |
| DATA-5 | previous_answer_with_problems | 上一条回答的样本：一段两百字上下的文字，读起来像 agent 刚给出的一条回答；里面要带那几类问题——自造压缩黑话、生造词与直译词、夹英文各至少一处——另有一两处照原样写的那些（代码标识符或命令名）。这段文字按 TC-4 的前置条件作为 agent 的上一条回答放进上下文。 | 不需要（它只在上下文里，不落盘） |
| DATA-6 | previous_answer_clean | 上一条回答的样本：一段两百字上下的文字，读起来像 agent 刚给出的一条回答，通篇平实的中文，一处那几类问题都没有；里面可以有代码标识符、路径这类照原样写的那些。这段文字按 TC-5 的前置条件作为 agent 的上一条回答放进上下文。 | 不需要（同上） |
| DATA-7 | fix_request_mixed | 用户消息样本（TC-1）：`/shared-skills:plain-language 这份文档读着绕，帮我改一下：evals/plain-language/cases/tp01-01-TC-1-fix_only_what_should_change/fixture/样本.md` | 不需要 |
| DATA-8 | fix_request_quotes | 用户消息样本（TC-2）：`/shared-skills:plain-language 这份文档里引了几段英文，我看着费劲，帮我改一下：evals/plain-language/cases/tp02-01-TC-2-quotes_kept_and_glossed/fixture/样本.md` | 不需要 |
| DATA-9 | fix_request_scope | 用户消息样本（TC-3）：`/shared-skills:plain-language 帮我改一下这份文档：evals/plain-language/cases/tp03-01-TC-3-scope_of_review/fixture/样本.md` | 不需要 |
| DATA-10 | restate_request_with_problems | 用户消息样本（TC-4，不带参数）：`/shared-skills:plain-language 你上一条回答我读不懂，重讲一遍` | 不需要 |
| DATA-11 | restate_request_clean | 用户消息样本（TC-5，不带参数）：`/shared-skills:plain-language 这段我看不懂，重讲一遍` | 不需要 |
| DATA-12 | fix_request_clean | 用户消息样本（TC-6）：`/shared-skills:plain-language 帮我看看这份文档要不要改：evals/plain-language/cases/tp04-01-TC-6-file_nothing_to_fix/fixture/样本.md` | 不需要 |
| DATA-13 | fix_request_blocked | 用户消息样本（TC-7，两条一轮一条）：第一条 `/shared-skills:plain-language 帮我改一下这份文档：evals/plain-language/cases/tp05-01-TC-7-file_blocked_reports_where/fixture/不存在的文件.md`——这条路径本来就不存在，不用另摆；第二条 `/shared-skills:plain-language 那这份呢：evals/plain-language/cases/tp05-01-TC-7-file_blocked_reports_where/fixture/只读样本.md`——这份按 DATA-15 摆成没有写权限的样子 | 不需要 |
| DATA-14 | ambient_writing_request | 用户消息样本（TC-8，不带技能名——这一档不经 skill）：`帮我写一段两百字左右的说明，讲讲这个仓库的检查脚本是怎么跑的` | 不需要 |
| DATA-15 | readonly_document | 没有写权限的文档样本：一份 Markdown 文档，正文里放进两三处该改的（黑话、生造词、夹英文这一类），其余是平实的中文——用来判「读得到、有该改的、但写不进去」这一档：说清卡在哪、把改好的文本一并给出，两件都要判出来。这份文件的写权限要去掉（本机 Windows 上 `chmod 444` 就是把它设成只读），摆进工作区之后权限要跟原始样本一致；重新克隆仓库不会带上这个属性，跑之前要重新设一次 | 不需要（它没有写权限，改不动；跑完核对它逐字节没变） |
