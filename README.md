# shared-skills

跨工程共享的 Agent Skill **集合**——一个仓库装多个互相独立的 skill，各工程按需取用其中的任意几个。

这里放的不是某一个 skill，而是一批：它们之间没有主题关系，唯一的共同点是**跟具体工程无关、拿到哪里都能用**。跟某个工程绑死的东西不收（公司专属风格、指向本机固定路径的文档索引等），留在那个工程自己的 `.claude/skills/` 下。

当前收录 **4** 个。

## 目录约定

```
skills/<skill 名>/SKILL.md      # 必需，一个子目录 = 一个独立 skill
skills/<skill 名>/<辅助文件>     # 可选：参考文档、脚本、模板
statusline/<脚本名>.py          # 状态栏脚本，会被同步到配置目录，见下方「状态栏」
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
`plain-language` 的写作规则注入每个会话（`startup` / `clear` / `compact` 三种时机），
同一个 hook 还会把 `statusline/` 下的脚本同步到配置目录（见下方「状态栏」）。
插件另外挂了四个通知 hook，后台会话需要你时弹 Windows 通知（见下方「通知」）。

```
/plugin marketplace add zhcmeng/shared-skills
/plugin install shared-skills@shared-skills
```

其它 agent 工具读 `~/.agents/skills/`，把 `skills/<名字>` 复制或链接过去即可；
两条路互不干扰。只要技能不要常驻注入，删掉 `hooks/` 即可，`skills/` 不受影响
（代价是状态栏脚本也不再同步，那种情况下得自己把 `statusline/` 下的脚本拷到配置目录）。

## 状态栏

插件带两个状态栏脚本，SessionStart 时自动同步到配置目录（设了 `CLAUDE_CONFIG_DIR`
就是它，没设就是 `~/.claude`）：

| 脚本 | 显示什么 |
|:---|:---|
| `statusline.py` | 主状态栏：本会话累计 token、缓存命中率、费用（按高峰/空闲分别计价）、已运行多久 |
| `subagent-statusline.py` | 子代理面板每一行：那个子代理自己的费用、缓存命中率、token、已运行多久 |

两个都是 Python 3 脚本，命令里的 `python` 要在 PATH 上。出来是这样：

```
本会话 ¥1.50(峰) · 缓存命中 79.1% · 总token 2.46M · 42m
```

### 时长怎么算

两边算法一致，都算**挂钟时间**——等模型、等你、暂停都算在里面。

| 哪一行 | 起点 | 终点 |
|:---|:---|:---|
| 主状态栏 | 会话开始 | 现在。由 Claude Code 的 `cost.total_duration_ms` 直接给出 |
| 子代理（还在跑） | 任务行里的 `startTime` | 现在 |
| 子代理（已结束） | 同上 | 它末条用量记录的时刻 |

已结束的子代理不按「现在」算，是因为任务行里只有 `startTime`、没有结束时刻；用「现在」
的话，跑完的行会一直往上涨。

两个脚本守同一条规矩：**算不出就不显示这一截，不编个数顶上**。会走到这一步的有：喂进来的数据里没有 `cost`、`startTime` 是 0（这套数据里 0 表示「还没填」，不是 1970 年）、压根没有
起点、已结束但记录读不到。显示格式为 `45s` / `12m` / `2h05m` / `1d02h`。

### 为什么要复制，而不是让 settings.json 直接指向插件目录

插件安装目录带版本号（`.../cache/shared-skills/shared-skills/<版本号>/`），升级后旧目录就没了；
而 `statusLine` 命令里**拿不到** `CLAUDE_PLUGIN_ROOT`——官方列举的占位符解析位置
（skill/agent 正文、hook 命令、MCP 配置、LSP 配置）不含 statusLine。
两条加起来，指向插件目录的写法升级一次就失效。所以脚本得落到一个与版本无关的固定路径。

### 为什么不顺便把 settings.json 也写了

插件系统不允许。插件根目录的 `settings.json` 官方只支持 `agent` 和 `subagentStatusLine`
两个键，其他键静默忽略，`statusLine` 不在其中（[issue #65513](https://github.com/anthropics/claude-code/issues/65513)
请求扩容，已关成 not planned）。所以这一项得自己配，路径按自己机器上的来：

```json
"statusLine": {
  "type": "command",
  "command": "python C:/Users/<你的用户名>/.claude/statusline.py"
},
"subagentStatusLine": {
  "type": "command",
  "command": "python C:/Users/<你的用户名>/.claude/subagent-statusline.py"
}
```

### 幂等与覆盖

同步是「内容一致就不动文件」，所以每次会话都跑一遍没有代价（实测增量约 1.5 毫秒，
整个 hook 的耗时量不出差别）。**仓库是唯一真相**：配置目录里的那两个脚本会被仓库版本
覆盖，改脚本请改仓库里的 `statusline/`，别改副本。

## 通知

后台会话需要你的时候弹一条 Windows 通知，提醒你切过去。**当前会话不弹**——你正看着它，
用不着提醒。

| 什么时候 | 弹出来的正文 |
|:---|:---|
| 后台会话答完一轮 | `答完了：` 加上它最后那句话的开头 |
| 后台会话弹出选择题等你选 | `等你选：` 加上问题原文 |
| 后台会话要你批准某个操作 | `要批准：` 加上提示语 |

「当前会话」= **你最后一次敲过字的那个会话**。判定不看窗口焦点：多个会话常常共用一个终端
窗口（Windows Terminal 的多标签页就是），看窗口分不出你在哪个标签；而「最后在哪个会话敲
过字」是每个会话自己的属性，分得清，也不用调任何窗口接口。

只算你自己敲的那句。Claude Code 还会借同一个事件把会话叫醒——最常见的是后台任务跑完，
它替你往那个会话里投一条提示词，让会话接着干。那种不算「你在用这个会话」：算了的话，后台
任务一跑完就把记号挪到它自己身上，你正看着的那个反倒成了「后台」，通知就开始乱弹。斜杠
命令和 `!` 命令是你敲的，照常算数。

通知是**常驻**的：不点掉就一直留在屏幕上，不会几秒后自己消失。每条通知底下带一个「知道了」
按钮，点它就是关掉这条。这个按钮不是装饰——系统对「常驻」那一档的要求正是「你处理它才走」，
没有可点的东西它就按普通通知对待，25 秒后自己消失（这个坑踩过：只声明常驻、不给按钮，
系统不报错但也不理会，通知照旧 25 秒没了）。

每条通知都会自己撤掉，多数时候不用你去点：**你在那个会话里一动手，它的通知就撤**。什么算
动手——你敲了字，或者它的工具又跑起来了（你刚点掉的那道选择题、刚批准的那个权限，都算）。
不撤的话，你答完那道选择题，「等你选」就一直挂在屏幕上——明明已经处理完了。

「切到那个窗口」这个动作本身撤不了，因为看不到。Claude Code 不把终端焦点告诉 hook：它自己
确实知道你在不在终端前面，但那份信息只在它内部用（发「客户端在线」心跳、判断要不要跳过它
自己那条通知），没有对外的口子。所以插件拿不到「你切过去了」这个信号，只能认你在那个会话
里做了什么。切过去只是看一眼、什么都没动，通知会留着。

同一个会话再出事，新通知顶掉旧的，不会堆成一串。

几个会话同时有事时，屏幕上会同时挂着好几条，各是各的——实测两条并排堆在右下角。排不排队
是系统自己的事，不是我们控制的。

（这条以前写的是「一次只显示一条，点掉一条下一条才顶上来」。那是通知还是普通通知时候的
样子；真变成常驻之后就不再排队了。）

标题排成「应用名 · 项目名 · 会话名」：

    Claude Code · investment · 优化 business-insight-builder

会话名的取用顺序跟 Claude Code 自己显示会话名时一致：你 `/rename` 改的名优先，其次是系统
自动生成的标题，所以弹窗上的名字和你在会话列表里看到的是同一个。两样都取不到（会话刚开始、
记录里还没写标题）就只留项目名那一段。

标题不会因为太长被砍掉——实测它会自动换行（80 个字符排两行仍然全部可读），代价是名字长了
通知会高一点，但名字都能看全。

### 依赖

- **只在 Windows 上生效**，别的平台静默什么都不做
- 需要 **jq** 来解析 hook 数据。PATH 上没有时，会按 WinGet、Chocolatey、Scoop 的常见安装
  位置再找一遍。注意：**刚装完 jq 要重启 Claude Code**——hook 是 Claude Code 的子进程，
  继承的是它启动那一刻的 PATH，不重启就找不到
- 弹通知用 Windows 自带的 PowerShell 5.1，不用额外装东西。PowerShell 7 调不了这套系统通知
  接口（实测那个类型加载不出来），所以脚本里是写死调 5.1 的

### 怎么关掉

只删 `hooks/hooks.json` 里 `UserPromptSubmit`、`Stop`、`PreToolUse`、`Notification` 这四段，
`skills/` 和状态栏都不受影响。

## 维护

- **校验脚本**：`bash hooks/verify.sh` 跑全部，`bash hooks/verify.sh notify` 只跑文件名含该关键词的模块。
  脚本拆在 `hooks/verify.d/` 下，一个模块管一件事，入口只负责按序加载和汇总：
  `10-session-start`（注入文本、polyglot 两个分支）、`20-statusline-sync`、`30-statusline-smoke`、
  `40-notify`（判定）、`50-notify-render`、`60-wiring`（hooks.json 接线）。加校验就加模块，别往入口里塞
- **新增一个 skill**：在 `skills/` 下建目录，写 `SKILL.md`，并在上方表格补一行
- **改 skill**：只改本仓库。各工程放的是指向这里的链接，不在工程内改副本
- **收录判据**：跟具体工程无关、别的工程拿去也能直接用。绑死某个工程的不收
- **改规则**：`skills/plain-language/rules.md` 是规则的唯一真相，改它同时改变 skill 行为和常驻注入。改完跑 `bash hooks/verify.sh` 确认注入没断
- **改状态栏脚本**：只改 `statusline/` 下的。配置目录里的副本每次会话都会被覆盖回去，改了不作数。
  改完跑 `bash hooks/verify.sh`：它会校验同步有没有断（内容一致时不重写、被改坏能修回、
  `CLAUDE_CONFIG_DIR` 优先于 `HOME`）。校验全程在临时目录里跑，不会动你真实的配置目录
- **改通知判定**：改 `hooks/notify`。它是纯逻辑、不碰界面，`verify.sh` 里那批断言把「标记写的
  是谁 × 事件来自谁」的组合都覆盖了
- **改通知渲染**：改 `hooks/notify.ps1`，它**必须存成带 UTF-8 BOM 的 UTF-8**。PowerShell 5.1
  只在有 BOM 时按 UTF-8 解析，没有就按 GBK 解——里面的中文注释会字节错位、连带把换行吞掉，
  脚本解析失败。而这个失败是静默的：通知再也不弹，会话照开。改完跑 `bash hooks/verify.sh`，
  它会查 BOM，也会真跑一次 PowerShell 把全文解析一遍
- **改 hook 脚本**：`hooks/run-hook.cmd` 里只能有 ASCII 字符，中文注释也不行。cmd.exe 读到中文会解析错位，
  而且不报错——会话照开。规则到没到却取决于崩在哪一步：实测两种都出现过，有时规则整段没进上下文
  （本机实测退出码 255），有时规则到了、却被一层 cmd 回显垃圾裹着（实测退出码 0）。改完跑一次
  `bash hooks/verify.sh`：在 Windows 上它会自动跑一遍 cmd.exe、比对输出。手工排查时再跑
  `cmd.exe /c "hooks\run-hook.cmd" session-start`，输出要和 `bash hooks/session-start` 一样。
  别只看退出码：写法不对时它也是 0（Git Bash 里要写成 `cmd.exe //c "hooks\run-hook.cmd" session-start`）

## 许可证

[MIT](./LICENSE) © 2026 zhcmeng

取用、修改、再分发都可以，保留版权声明即可。
