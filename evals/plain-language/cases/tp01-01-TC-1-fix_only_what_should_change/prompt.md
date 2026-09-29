# 评测用例：一份文档里既有该改的、也有不该动的，只动该动的

## 这条用例防的是什么

`SKILL.md` 把「只动该动的」写在正文里：只改 `rules.md` 那几类问题所在的句子，其余一字不动。难的地方不在改，在**不改**——一份真文档里，代码标识符、路径、命令名、产品名、缩写、已经进入日常用法的直译词、文中已经给出过定义的术语，这七类看起来都能「更中文一点」，动了就错。

`rules.md` 把两组分得很清楚：六类要改的（自造压缩黑话；生造词与直译词；英文词直译成中文里另一个意思的现成词；夹英文；英文词当日常词用；英文标题直接上），七类照原样写的。两组必须在同一份文档里同时在场，「只动该动的」才判得出来；拆成几条只是把同一份文档跑几遍。

这一条钉两件事：六处该改的都换成了按字面就懂的中文说法，七处不该动的一个字没动。

## 怎么跑

1. 按 ENV-1 把 `plugin/skills/plain-language/` 整套（`SKILL.md` 与 `rules.md`）当作使用者机器上装好的这门技能交给 agent。本批用的是 skill-up：它把技能装到工作区的 `.claude/skills/plain-language/`，工作区根就是 ENV-6 那处临时目录。
2. 样本按 DATA-1 摆在工作区里 `evals/plain-language/cases/tp01-01-TC-1-fix_only_what_should_change/fixture/样本.md`（ENV-4）。这份文档里六处该改、七处不该动，另有两三句平实的中文。原始样本在仓库里同一个路径下，全程不动。
3. 发下面这条用户消息（DATA-7）。
4. 按 ENV-2 取这一轮的回复，以及那份样本在跑前跑后的差别；按 `graders/only-problems-touched.md`（ENV-3）判。

用户消息（DATA-7。规格里写的是 `/shared-skills:plain-language`，真跑时渲染成 `/plain-language`——skill-up 只把技能装到 `.claude/skills/` 下，没有装插件那条道，带插件前缀唤起不来。见实施方案 2.1 第 5 小节第 1 条）：

```
/plain-language 这份文档读着绕，帮我改一下：evals/plain-language/cases/tp01-01-TC-1-fix_only_what_should_change/fixture/样本.md
```

## 基线证据

跑过一次（`batch3-full` 运行一，2026-09-29）：**1 次 1 过**（判 8/8）。

回复原话：「改好了：夹的英文和黑话都换成了中文说法，其他内容一字未动。」

盘上的改动对得上——`workspace.diff` 共 6 处替换，正是该改的那六处：「上层认知扩口、下层收割」→「先让读者意识到问题，再给出我们的方案」；「心智物理」那半句→「读者脑子里那个想法有没有被说动」；`align 一下这个 approach`→「统一口径」；`图案的复用`／`判定形状`→「同一段描述尽量只写一次」／「输入输出也要写全」；`## 五、Asymmetric Information`→`## 五、信息不对称`；`注入 context`／`memory`→「写进对话上下文」／「记忆」。七处不该动的一个没动：定义在前的「先给结论」及其复用、`main()`、`plugin/skills/plain-language/rules.md`、`bash checks/verify.sh`、`Claude Code`、`UTF-8`、护城河／天花板／赛道。

判官另外核了「别的文件没被动过」：工作区里 `.claude/skills/plain-language/` 那两条删除，它自己认出是框架干的，没算到这一条头上——探路那轮留下的 Ruling 在这里得到验证，不用补说明。

## 规格说明里的对应

用例 TC-1（高风险；覆盖项 TCOV-1 至 TCOV-13、TCOV-21、TCOV-22、TCOV-25 至 TCOV-27、TCOV-32、TCOV-35，对应 TM-1 的 F 组与 K 组、TM-2 的处置规则 3 至 5、TM-3 的产出规则 5、TM-4 的备选场景 1），排在规程 TP-1 里；用户消息是 DATA-7，样本按 DATA-1 造。规格说明在 `evals/plain-language/test-case-design/` 下。
