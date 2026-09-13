# shared-skills

跨工程共享的 Agent Skill 集合。一个仓库装多个 skill，各工程按需取用。

## 目录约定

```
skills/<skill 名>/SKILL.md      # 必需
skills/<skill 名>/<辅助文件>     # 可选：参考文档、脚本、模板
```

`skills/` 放在仓库根，与 `obra/superpowers` 的内部布局一致——将来若改用其它分发方式（`npx skills`、插件市场），目录无需重排。

## 现有 skill

| skill | 用途 |
|:---|:---|
| `plain-language` | 回答或文档读不懂时用：黑话、无必要的中英文夹杂、英文没给中文翻译。无参数重说最近一条回答，给文档路径出问题清单。只读不改。 |

## 取用方式

本仓库不发布到任何包管理器，用 git + 符号链接取用。克隆到固定位置，全局只此一份：

```bash
git clone https://github.com/zhcmeng/shared-skills.git
```

再把需要的 skill 链接到目标位置：

```cmd
:: 工程级 —— 只有该工程可用
mklink /D "C:\path\to\project\.claude\skills\plain-language" "C:\work\shared-skills\skills\plain-language"

:: user 级 —— 本机所有工程可用
mklink /D "%USERPROFILE%\.claude\skills\plain-language" "C:\work\shared-skills\skills\plain-language"
```

链接指向同一份文件，不是副本：改仓库里的内容，所有工程立刻看到；更新只需 `git pull`。

> Windows 建目录符号链接需要管理员权限或开发者模式（本机未开开发者模式，管理员会话下可建）。PowerShell 等价命令是 `New-Item -ItemType SymbolicLink -Path <链接路径> -Target <目标路径>`。

## 维护

- **新增 skill**：在 `skills/` 下建目录，写 `SKILL.md`，并更新上方清单
- **改 skill**：只改本仓库。各工程放的是指向这里的链接，不在工程内改副本
