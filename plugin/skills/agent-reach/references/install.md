# 装 agent-reach 命令行

命令能正常跑就不用读这份。只有在 `agent-reach` 报不存在（`command not found`，Windows 上 `where` 找不到）时才照着做，装完回到原来的任务继续。

## 1. 装本体

只跑这一条，别带 `--system`：

```bash
pipx install https://github.com/Panniantong/agent-reach/archive/main.zip
```

没有 pipx 就先 `python -m pip install --user pipx`，再 `python -m pipx ensurepath`，重开终端后跑上一条。

从 PyPI 装不到它——PyPI 上有个同名包，不是这个项目。

## 2. 只做只读体检

```bash
agent-reach install --env=auto
```

这条命令不改系统，只报告缺哪些工具（带 `--system` 才会真装）。

## 3. 缺的交给用户定

把上一步报出来的缺失项原样列给用户，问要不要装、装哪些渠道；用户点头后再跑：

```bash
agent-reach install --env=auto --system --channels=<用户要的渠道>
```

注意 `--system` 会顺手往 `~/.claude/skills/agent-reach/` 写一份它自己的技能副本，与插件里的本技能重复。
跑完补一条 `agent-reach skill --uninstall` 清掉那份副本（只删它写的那份，不动插件）。
