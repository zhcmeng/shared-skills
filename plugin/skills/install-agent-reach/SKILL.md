---
name: install-agent-reach
description: "安装 agent-reach 命令行工具时用：先用 uv 装本体，再跑 setup 把技能副本放进 ~/.claude/skills/。已经装过只报版本，不重复下载。触发方式：/install-agent-reach。"
disable-model-invocation: true
---

# 安装 agent-reach

这次只做一件事：把 `agent-reach` 命令行装到本机，并把它的技能副本放好。

## 步骤

1. **先看装没装**：`command -v agent-reach`。
   有输出就查一下 `agent-reach --version` 报给用户，结束，不重装。

2. **看 uv 在不在**：`command -v uv`。
   没有就先装 uv（`python -m pip install --user uv`，或照 https://docs.astral.sh/uv/ 的安装方式），装完再往下走。

3. **装本体**：

   ```
   uv tool install https://github.com/Panniantong/Agent-Reach/releases/latest/download/agent-reach.zip
   ```

4. **放技能副本**：`agent-reach setup`。它会把技能写进 `~/.claude/skills/agent-reach/`，并开启默认渠道。

5. **确认 PATH**：`uv tool dir --bin` 拿到安装目录，看它在不在 `PATH` 里。不在就告诉用户把这个目录加进 PATH，然后重开会话。

## 注意

- **不要从 PyPI 装**：PyPI 上有个同名包，不是这个项目。
- **不要用 pipx**：上游已移除 pipx 支持，uv 是唯一支持的安装器。
- **`setup` 会装别的东西**：开启默认渠道可能顺带装 npm 上的工具。用户只想要本体时，跳过第 4 步，技能副本改由后续手工放。
- **技能下一个会话才生效**：本会话里 `/` 菜单还看不到 `agent-reach`。
