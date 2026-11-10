# skill-judge

静态审查 Agent Skill 的技能。技能本体与判据在 [SKILL.md](./SKILL.md)；这份说明只记维护时要知道的事。

## 本地链接检查

`scripts/check_links.py` 在审查时查技能包里的本地链接目标：给技能目录就递归扫 `.md` / `.markdown`，给单个文件就只查那一份。用法、占位符规则、输出格式与退出码都在脚本说明里：

```bash
python scripts/check_links.py --help
```

脚本没有第三方依赖，Python 3 即可。测试在仓库根的 `tests/skill-judge/test_check_links.py`，跑 `bash tests/run.sh skill-judge`。

## 改这个技能

- 只改本仓库的 `plugin/skills/skill-judge/`；各工程放的是指向这里的链接，不在工程内改副本。
- 改完跑 `bash checks/verify.sh --changed`；动了 `plugin/` 时，推远端前把 `plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 的版本号一起抬上去。
