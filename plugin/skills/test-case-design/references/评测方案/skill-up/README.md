# skill-up 参考文档

这一目录下的文档是给写实施方案规格说明（第七份）的人用的。本技能随包带一份，读的人不必联网、也不必去翻本机那份 clone。

**目录里的东西分两半，来路不一样：**

| 文件 | 哪来的 | 管什么 |
|:---|:---|:---|
| `writing-evals.md` | 上游原文，一字不改 | 配置怎么写：`eval.yaml` 与 `case.yaml` 的字段、判官三型、工作区与夹具的摆法 |
| `cli-reference.md` | 上游原文，一字不改 | 命令怎么用：`run`／`validate`／`list-cases`／`report` 的参数、退出码、报告格式 |
| `LICENSE` | 上游仓库根那份（Apache License 2.0 全文） | 上面两份上游文档的许可 |
| `usage-notes.md` | **本技能自己写的** | 用这套方案要拿捏的几处：实际跑起来是什么样、做不到什么、判官与 engine 开关怎么挑——写第七份的「跑不了原样的那几条」时用它 |
| `README.md` | **本技能自己写的** | 你正在读的这份 |

**出处**：<https://github.com/zhcmeng/skill-up>，钉住的版本是 `main @ 7f1ff9b8e2d7c654728de526867f2f7e7b78ea51`（2026-09-29）。上游没有发布 tag，所以按 commit 钉。上面五份都对着这一个版本。

**怎么更新**：把上游那两份 guide 与 `LICENSE` 拿过来覆盖掉，一个字不改。`usage-notes.md` 不一样——它第一到五节是把上游源码读出来的结论重述了一遍，第六、七节照上游 `skills/skill-upper/references/` 下那两份参考写的，**都要照原处重核一遍再改**；上游改了实现或改了那两份参考，它不会自己报警，只会说错话。改完把钉的 commit 换成新那一个，两处都要换：这一节这一行、`usage-notes.md` 顶上。

**许可**：`writing-evals.md`、`cli-reference.md` 与 `LICENSE` 来自上游，适用本目录的 `LICENSE`（Apache License 2.0）。**`README.md` 与 `usage-notes.md` 是本技能自己写的，不适用这份许可**；插件整体的许可见仓库根。

上游没有 NOTICE 文件，所以这里不另附。两份上游文档一字未改，按 Apache-2.0 第 4 条不必另写「改过哪几处」那句声明。
