# shared-skills

跨工程共享的 Agent Skill **集合**——一个仓库装多个互相独立的 skill，各工程按需取用其中的任意几个。

这里放的不是某一个 skill，而是一批：它们之间没有主题关系，唯一的共同点是**跟具体工程无关、拿到哪里都能用**。跟某个工程绑死的东西不收（公司专属风格、指向本机固定路径的文档索引等），留在那个工程自己的 `.claude/skills/` 下。

当前收录 **1** 个。

## 目录约定

```
skills/<skill 名>/SKILL.md      # 必需，一个子目录 = 一个独立 skill
skills/<skill 名>/<辅助文件>     # 可选：参考文档、脚本、模板
```

`skills/` 放在仓库根，与 `obra/superpowers` 的内部布局一致——将来若改用其它分发方式（`npx skills`、插件市场），目录无需重排。

## 收录的 skill

| skill | 用途 |
|:---|:---|
| `plain-language` | 回答或文档读不懂时用：黑话、无必要的中英文夹杂、英文没给中文翻译。无参数重说最近一条回答，给文档路径出问题清单。只读不改。 |

## 取用方式

**逐个 skill 取用，不是整仓库一起装。** 本仓库不发布到任何包管理器，用 git + 符号链接：克隆到固定位置，全局只此一份——

```bash
git clone https://github.com/zhcmeng/shared-skills.git
```

克隆到哪个目录由你决定，下文示例统一写作 `C:\path\to\shared-skills`。再把要用到的 skill 链接到目标位置（`<skill 名>` 换成上表里的名字，要几个就重复几次）：

```cmd
:: 工程级 —— 只有该工程可用
mklink /D "C:\path\to\project\.claude\skills\<skill 名>" "C:\path\to\shared-skills\skills\<skill 名>"

:: user 级 —— 本机所有工程可用
mklink /D "%USERPROFILE%\.claude\skills\<skill 名>" "C:\path\to\shared-skills\skills\<skill 名>"
```

例如把 `plain-language` 挂到 user 级：

```cmd
mklink /D "%USERPROFILE%\.claude\skills\plain-language" "C:\path\to\shared-skills\skills\plain-language"
```

链接指向同一份文件，不是副本：改仓库里的内容，所有工程立刻看到；更新只需 `git pull`。

> Windows 建目录符号链接需要管理员权限或开发者模式。PowerShell 等价命令是 `New-Item -ItemType SymbolicLink -Path <链接路径> -Target <目标路径>`。

## 维护

- **新增一个 skill**：在 `skills/` 下建目录，写 `SKILL.md`，并在上方表格补一行
- **改 skill**：只改本仓库。各工程放的是指向这里的链接，不在工程内改副本
- **收录判据**：跟具体工程无关、别的工程拿去也能直接用。绑死某个工程的不收

## 许可证

[MIT](./LICENSE) © 2026 zhcmeng

取用、修改、再分发都可以，保留版权声明即可。
