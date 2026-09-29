# 评测用例：一处问题都没有的文件，一个字不动

## 这条用例防的是什么

`SKILL.md` 的「改文件」那张表里有一档：**读得到、一处问题都没有 → 不改，回复里说「这份没有需要改的地方」**。这一档单独摆一条用例，是因为它跟别档的失败方式不一样——别的档是「该改的没改」，这一档是**改了不该改的**。

agent 拿到一份通篇平实中文的文档、被要求「帮我看看要不要改」时，有一种很自然的走偏：总得做点什么。于是把某句话换个说法、把某段顺序调一下、把词汇润色一遍——都是「没问题」的地方，动一处就错。这一档要的是**敢说不用改**。

这一条钉三件事：那份文件跑完与跑前逐字节相同、回复里说出了「没有需要改的地方」这个意思、没有为了显得干了活而改一处。

## 怎么跑

1. 按 ENV-1 把 `plugin/skills/plain-language/` 整套（`SKILL.md` 与 `rules.md`）当作使用者机器上装好的这门技能交给 agent。本批用的是 skill-up：它把技能装到工作区的 `.claude/skills/plain-language/`，工作区根就是 ENV-6 那处临时目录。
2. 样本按 DATA-4 摆在工作区里 `evals/plain-language/cases/tp04-01-TC-6-file_nothing_to_fix/fixture/样本.md`（ENV-4）。这份文档通篇平实的中文，里面另有代码标识符、路径、命令名这类照原样写的——它们不算问题。原始样本在仓库里同一个路径下，全程不动。
3. 发下面这条用户消息（DATA-12）。
4. 按 ENV-2 取这一轮的回复，以及那份样本在跑前跑后的差别；按 `graders/file-untouched.md`（ENV-3）判。

用户消息（DATA-12。规格里写的是 `/shared-skills:plain-language`，真跑时渲染成 `/plain-language`——skill-up 只把技能装到 `.claude/skills/` 下，没有装插件那条道，带插件前缀唤起不来。见实施方案 2.1 第 5 小节第 1 条）：

```
/plain-language 帮我看看这份文档要不要改：evals/plain-language/cases/tp04-01-TC-6-file_nothing_to_fix/fixture/样本.md
```

## 基线证据

跑过两次（2026-09-29）：**2 次 2 过**。

1. 探路（`--include-case-name "tp04-*"`）：判 PASS（100%）。
2. `batch3-full` 运行一：判 7/7。回复原话一行：「这份没有需要改的地方。」

盘上那份文件逐字节没变——判官不是靠说的，是拿 `git diff --exit-code HEAD` 退出码 0，加文件哈希 `122bf04a…` 与 HEAD 里那个 blob 的哈希比对，两样都对上；它还核了 mtime 从检出一路没变、transcript 里 agent 没有任何 Edit／Write／Bash 调用。**「敢说不用改」这一档立住了。**

另：探路那一次顺带确认了 `/plain-language` 会展开成技能——transcript 里能看到 `<command-name>/plain-language</command-name>` 后面跟着整段 `SKILL.md`（「说人话」正文）。

## 规格说明里的对应

用例 TC-6（高风险；覆盖项 TCOV-31、TCOV-36，对应 TM-3 的产出规则 1 与 TM-4 的备选场景 2），排在规程 TP-4 里；用户消息是 DATA-12，样本按 DATA-4 造。规格说明在 `evals/plain-language/test-case-design/` 下。
