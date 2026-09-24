# agent-reach

从互联网取内容：网页搜索，以及 Twitter、小红书、B站、Reddit、YouTube、GitHub、雪球等 16 个平台。

这份 README 是给人看的：Claude 跑这个技能时不读它，读的是 [SKILL.md](./SKILL.md)。

## 这个技能不是自己写的

`SKILL.md` 与 `references/` 复制自上游仓库，随插件一起分发。上游更新后照 [THIRD-PARTY-NOTICES.md](./THIRD-PARTY-NOTICES.md) 里的步骤重取一遍——那份文件记着来源、同步版本、许可证，以及哪几处是本地改的（重取时那几处要重做）。本地改动与同步步骤都以它为准，这里不另抄一份。

技能里的命令行工具本身也能自更新（`agent-reach check-update`），但那条路更新的是工具，不会动这个目录下的技能文件——技能文件要更新，走上面那条。
