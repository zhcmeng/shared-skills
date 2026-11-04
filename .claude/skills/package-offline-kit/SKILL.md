---
name: package-offline-kit
description: '把本仓库的 shared-skills 插件打成离线安装包（shared-skills.zip），放进指定目录；不给目录就放 C:\Study\offline-kit\skills。用户说「打包插件」「做个离线安装包」「更新 offline-kit 里的包」「给另一台机器装插件」时用。'
argument-hint: '[输出目录；不给就用默认目录]'
---

# 打包离线安装包

把本仓库的插件打成一个 zip，放进指定目录。另一台机器解压这个包，按本地市场装上插件，不用连 GitHub。

## 用法

```
bash scripts/package.sh [输出目录]
```

- **输出目录可以不给**，不给就用 `C:\Study\offline-kit\skills`。
- 路径按 Windows 写法给也行（`C:\...`），脚本会换成正斜杠再处理。
- 输出目录不存在会建；路径被一个文件占着就停。
- 包名固定 `shared-skills.zip`，同名的旧包会被覆盖；输出目录里的其它文件不动。
- 脚本要用 `git`、`unzip` 与 Python 3；缺了会直接说缺什么。

## 它做什么

1. **只取已提交的内容。** `.claude-plugin/` 与 `plugin/` 这两处有未提交的改动时，它把这些改动列出来并停下——先提交，再打包。包只从仓库最近一次提交（`HEAD`）取，工作区里没提交的东西不会进包。
2. **核对两份清单的版本号。** `.claude-plugin/marketplace.json` 与 `plugin/.claude-plugin/plugin.json` 里的版本号不一致就停。
3. **打包。** 顶层是 `shared-skills/`，里面只有 `.claude-plugin/` 与 `plugin/`。
4. **核对包里的东西。** 顶层只有一个 `shared-skills/`；`checks/`、`docs/`、`evals/`、`tests/` 一个没进；`SKILL.md` 的份数与仓库里一致；包内两份清单的版本号与仓库一致。
5. **再验一遍清单。** 机器上有 `claude` 命令时，跑一次 `claude plugin validate`。
6. **核对都过了才落盘。** 中途失败不会在输出目录留下半个包。

## 打完之后

告诉用户三样：**包在哪、版本号是几、技能有几个。**

另一台机器的安装方法：

1. 解压 `shared-skills.zip`，得到一个 `shared-skills/` 文件夹。
2. 在 Claude Code 里执行：

   ```
   /plugin marketplace add <解压后的 shared-skills 文件夹路径>
   /plugin install shared-skills@shared-skills
   ```

## 边界

- **不改版本号。** 抬版本号是交付前的另一件事，见仓库 `README.md` 的「维护」一节；这个技能只管打包。
- **不碰 `plugin/`。** 这个技能住在 `.claude/skills/` 下，是给本仓库维护者用的，不随插件发出去。
- **不把开发目录打进包。** 包只含 `.claude-plugin/` 与 `plugin/`；`checks/`、`docs/`、`evals/`、`tests/` 都不进。
- **失败就停。** 清单版本不一致、有未提交改动、包里的东西对不上，都直接报错退出；不猜、不凑一个包。
