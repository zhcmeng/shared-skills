# 实测：Windows 上 Claude Code 到底跑 `run-hook.cmd` 的哪个分支

**结论：跑的是批处理分支（第 2-31 行），bash 分支不执行。**
也就是说，`run-hook.cmd` 的批处理段是 Windows 上的**生产路径**，不是兜底。

这条结论支撑两个判断：
- R8（把 4 行中文 `REM` 注释改成 ASCII）是必要的，不是洁癖
- Task 5 评审的 Critical 成立：README 把读者指向 `bash hooks/verify.sh`，
  而那个检查走的是 bash 分支，**结构上看不到批处理段坏掉**

## 为什么需要实测

两份材料互相矛盾，谁也不能直接采信：

| 来源 | 说法 |
|:---|:---|
| `hooks/run-hook.cmd` 里的注释 | 「On Windows: cmd.exe runs the batch portion」 |
| superpowers `docs/windows/polyglot-hooks.md` | 「Windows with Git Bash installed: **Git Bash**」「`"shell": "bash"` … **forces the Git Bash route**」 |
| Claude Code 二进制里的字符串 | `defaultShell` 的说明是「Defaults to 'bash' on all platforms」 |
| 二进制里的 Windows 探测 | `return r.endsWith(".sh") ? \`bash ${e}\` : e` —— 只对 `.sh` 前置 bash |

文档说 Git Bash，注释说 cmd.exe。实测是唯一出路。

## 方法（可复现）

1. 把仓库的插件结构复制到临时目录：`.claude-plugin/`、`hooks/`、`skills/`
2. 给副本的 `run-hook.cmd` **两个分支各埋一个标记**，与原件的差异只有这两行：
   - 批处理分支，紧跟 `@echo off`：
     `>"C:\...\tmp\marker-batch.txt" echo BATCH_RAN`
   - bash 分支，紧跟 `SCRIPT_DIR=...`：
     `echo BASH_RAN >> "/c/.../tmp/marker-bash.txt"`
3. 起一个真实会话跑它：
   `claude --plugin-dir <副本> -p "只回复两个字：收到" --debug-file <日志>`
4. 看哪个标记文件出现

用 `--plugin-dir` 而不是装插件，是为了**完全不碰用户已装的任何东西**。

## 结果

```
批处理分支 执行了: BATCH_RAN
bash 分支 未执行（无 marker-bash.txt）
```

会话日志（`--debug-file`）里的对应证据：

```
[DEBUG] Read hooks.json for plugin shared-skills (enabled=true): ...\plugintest\hooks\hooks.json
[DEBUG] Loading hooks from plugin: shared-skills
[DEBUG] Registered 2 hooks from 2 plugins
[DEBUG] Hook SessionStart ("${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" session-start)
        provided additionalContext (980 chars)
```

- 注入**成功**了：980 字符，与直接 `bash hooks/session-start` 量到的字符数一致
- 注入内容含限定语与 `rules.md` 全文（`要改的` / `保留` / `护城河` 三个特征词各命中 1 次）
- 同一次会话也注册了**已安装的** superpowers 的 hook，它的 `hooks.json` 与我们的逐字节相同，
  走的是同一条执行路径

## 环境

- Windows 11 Pro 10.0.22631
- Claude Code 2.1.269
- Git Bash 装在 `C:\Program Files\Git\bin\bash.exe`（批处理分支的第一候选）

## 副作用

无。副本放在临时目录里，仓库与已装插件都没被改动。
`--plugin-dir` 只对那一个会话生效。

## 已知局限

`hooks/verify.sh` 只覆盖 bash 分支。**批处理分支——Windows 上的生产路径——没有任何自动检查**，
它坏了 `verify.sh` 照样打印「全部通过」。

Task 3 的修复轮裁定**不加**自动的 cmd.exe 检查，理由是「从 bash 引 cmd.exe 的引号与换行处理很脆，
一个会误报的健康检查比没有更糟」。这条分支随后被确认是 Windows 上的生产路径，风险敞口比当时
估计的大。目前覆盖它的唯一手段是 README「维护」节里那条人工步骤：在 cmd.exe 或 PowerShell 里
跑一次 `run-hook.cmd`，比对输出与 `bash hooks/session-start` 是否一致。

---

## 附：cmd.exe 调用写法的实测（给 README 用）

同一个 `cmd.exe /c "hooks\run-hook.cmd" session-start`，从**不同 shell** 里敲效果完全不同。
四种写法逐个实测，基准是 `bash hooks/session-start`（2449 字节，sha256 `7d3c2427646dac0…`）：

| # | 在哪敲 | 命令 | 结果 |
|:--|:---|:---|:---|
| A | PowerShell / cmd.exe | `cmd.exe /c "hooks\run-hook.cmd" session-start` | **2449 字节，与基准逐字节相同** ✓ |
| B | Git Bash | `cmd.exe /c "hooks\run-hook.cmd session-start"` | **109 字节**（只有 cmd 横幅和提示符）✗ |
| C | Git Bash | `cmd.exe /c 'hooks\run-hook.cmd session-start'` | **109 字节**，同上 ✗ |
| D | Git Bash | `cmd //c "hooks\run-hook.cmd session-start"` | **2449 字节，逐字节相同** ✓ |
| E | Git Bash | `MSYS_NO_PATHCONV=1 cmd.exe /c 'hooks\run-hook.cmd session-start'` | **2449 字节，逐字节相同** ✓ |

从 Git Bash 敲 B/C 时 bash 会先吃掉反斜杠、MSYS 又转换路径，cmd.exe 收到的是残缺的命令，
于是**进了交互模式**，输出一屏横幅就退出。

**要命的细节：B 和 C 的退出码都是 0。** 只看退出码会判成「通过」——
正是这个仓库要消灭的那种虚假的安心。所以 README 里必须写「**比对输出**」，不能写「看退出码」。
