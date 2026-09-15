# shared-skills

跨工程共享的 Agent Skill **集合**——一个仓库装多个互相独立的 skill，各工程按需取用其中的任意几个。

这里放的不是某一个 skill，而是一批：它们之间没有主题关系，唯一的共同点是**跟具体工程无关、拿到哪里都能用**。跟某个工程绑死的东西不收（公司专属风格、指向本机固定路径的文档索引等），留在那个工程自己的 `.claude/skills/` 下。

当前收录 **4** 个。

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
| `commit` | 提交本会话改动并推送：只 add 本会话改过的文件，生成中文提交信息，push 当前分支。 |
| `md-export` | 把 Markdown 导出为 PDF 或 HTML：表格、数学公式、本地图片都支持，样式对齐 Markdown Preview Enhanced 的预览主题。支持单文件与目录批量。只需一个 Chromium 浏览器。 |
| `whatis` | 快速了解一个对象（开源仓库、工具、概念、术语）：一段对话速览——是什么、能做什么、大概原理、什么场景用，末尾列出可直接回复字母继续追问的问题。 |

## 安装

本仓库同时是一个 Claude Code 插件，`skills/` 会被自动注册，SessionStart hook 会把
`plain-language` 的写作规则注入每个会话（`startup` / `clear` / `compact` 三种时机）。

```
/plugin marketplace add zhcmeng/shared-skills
/plugin install shared-skills@shared-skills
```

其它 agent 工具读 `~/.agents/skills/`，把 `skills/<名字>` 复制或链接过去即可；
两条路互不干扰。只要技能不要常驻注入，删掉 `hooks/` 即可，`skills/` 不受影响。

## 维护

- **新增一个 skill**：在 `skills/` 下建目录，写 `SKILL.md`，并在上方表格补一行
- **改 skill**：只改本仓库。各工程放的是指向这里的链接，不在工程内改副本
- **收录判据**：跟具体工程无关、别的工程拿去也能直接用。绑死某个工程的不收
- **改规则**：`skills/plain-language/rules.md` 是规则的唯一真相，改它同时改变 skill 行为和常驻注入。改完跑 `bash hooks/verify.sh` 确认注入没断
- **改 hook 脚本**：`hooks/run-hook.cmd` 里只能有 ASCII 字符，中文注释也不行。cmd.exe 读到中文会解析错位，
  而且不报错——会话照开。规则到没到却取决于崩在哪一步：实测两种都出现过，有时规则整段没进上下文
  （本机实测退出码 255），有时规则到了、却被一层 cmd 回显垃圾裹着（实测退出码 0）。改完跑一次
  `bash hooks/verify.sh`：在 Windows 上它会自动跑一遍 cmd.exe、比对输出。手工排查时再跑
  `cmd.exe /c "hooks\run-hook.cmd" session-start`，输出要和 `bash hooks/session-start` 一样。
  别只看退出码：写法不对时它也是 0（Git Bash 里要写成 `cmd.exe //c "hooks\run-hook.cmd" session-start`）

## 许可证

[MIT](./LICENSE) © 2026 zhcmeng

取用、修改、再分发都可以，保留版权声明即可。
