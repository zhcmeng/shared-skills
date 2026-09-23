# shared-skills

跨工程共享的 Agent Skill 集合，同时是一个 Claude Code 插件。插件本体在 `plugin/` 下，只有它会被装到使用者机器上；`checks/`、`docs/` 这些开发用的东西在仓库根，不跟着发出去。`plugin/skills/` 会被自动注册，hook 会把 `plugin/rules/` 下的常驻规则与 `plugin/statusline/` 下的脚本同步到配置目录。

这个仓库的改动有四类各有讲究，下面一条管一类。每类的细则在 README 的「维护」一节——那里是唯一的清单，加技能、改规则、改状态栏、改通知都在里面。

- **改完自己跑检查，没有东西替你跑。** 这个仓库不装提交前钩子、也没有 CI——就是不让人每次提交都等两分钟。代价写在明处：忘跑就是没跑，没人会拦你。`bash checks/verify.sh` 跑全部（约两分钟）；`bash checks/verify.sh --changed` 只跑被本次改动影响到的模块（按暂存区挑，快得多）；`bash checks/verify.sh <关键词>` 只跑文件名里带该词的模块。它验的是 hook 接线、状态栏与常驻规则的同步、通知判定这几条链子；改动碰到这几处就跑一遍再收工。
- **要抬版本号。** 改了 `plugin/skills/`、`plugin/rules/`、`plugin/statusline/`、`plugin/hooks/` 里的东西，就把 `plugin/.claude-plugin/plugin.json` 和 `.claude-plugin/marketplace.json` 里的版本号一起抬上去，两处必须一致。插件按版本号分目录安装、内容一致就不重装——不抬版本号的效果是「仓库改了，别人跑的还是旧的」，全程不报错。
- **`plugin/` 下的东西都会发出去。** 插件安装是把 `plugin/` 整个目录拷到使用者机器上，没有排除机制。测试用例、设计稿、临时文件，只要放在 `plugin/skills/<某技能>/` 下面就跟着发给每个使用者。不想发的放 `plugin/` 外面。
- **每门技能自包含。** 改哪门就读它自己的 `SKILL.md`；同一目录下的 `README.md` 是写给人看的，技能运行时不会读它。
