# shared-skills

跨工程共享的 Agent Skill 集合，同时是一个 Claude Code 插件。插件本体在 `plugin/` 下，只有它会被装到使用者机器上；`checks/`、`docs/`、`evals/`、`tests/` 这些开发用的东西在仓库根，不跟着发出去。`plugin/skills/` 会被自动注册，hook 会把 `plugin/rules/` 下的常驻规则与 `plugin/statusline/` 下的脚本同步到配置目录，并给上游 `i-have-adhd` 插件建上它的常驻标记文件（那条链子的开关与代价写在 README 的「常驻规则」一节）。

这个仓库的改动有五类各有讲究，下面一条管一类。每类的细则在 README 的「维护」一节——加技能、改规则、改状态栏、改通知都在里面；某个技能自己的脚本与素材怎么改，在那门技能目录下的 `README.md` 里。

- **改完自己跑检查，没有东西替你跑。** 这个仓库不装提交前钩子、也没有 CI——就是不让人每次提交都等两分钟。代价写在明处：忘跑就是没跑，没人会拦你。`bash checks/verify.sh <关键词>` 只跑文件名里带该词的模块——改动碰到哪一条链子就跑哪一条（改通知就跑 `verify.sh notify`），没碰到的不跑；懒得自己挑就用 `bash checks/verify.sh --changed`，它按暂存区挑（快得多）；`bash checks/verify.sh` 是不挑、跑全部（约两分钟）。它验的是 hook 接线、状态栏与常驻规则的同步、通知判定这几条链子。
- **要抬版本号。** 改了 `plugin/skills/`、`plugin/rules/`、`plugin/statusline/`、`plugin/hooks/` 里的东西，就把 `plugin/.claude-plugin/plugin.json` 和 `.claude-plugin/marketplace.json` 里的版本号一起抬上去，两处必须一致。插件按版本号分目录安装、内容一致就不重装——不抬版本号的效果是「仓库改了，别人跑的还是旧的」，全程不报错。抬哪一位：`feat`／`refactor` 抬中间那位，`fix`／`docs`／`chore` 抬最后那位；判不准就看这次改的是「多了一个能力」还是「把已有的改对了」。
- **`plugin/` 下的东西都会发出去。** 插件安装是把 `plugin/` 整个目录拷到使用者机器上，没有排除机制。测试用例、设计稿、临时文件，只要放在 `plugin/skills/<某技能>/` 下面就跟着发给每个使用者。不想发的放 `plugin/` 外面。
- **一个技能两层测试，都放仓库根，都不跟着发出去。** 脚本层：`plugin/skills/<技能名>/scripts/` 下的代码，测试放 `tests/<技能名>/`，文件名 `test_<脚本名>.py`，一眼看得出谁测谁；改完跑 `bash tests/run.sh <技能名>`——这一份不挂在 verify.sh 里：挂着的话，改任何一门技能都会把这门的测试带着跑一遍。本体层：技能这套提示词本身（`SKILL.md` 加 `references/`），评测材料放 `evals/<被评测的技能名>/`，没特别说就默认落这儿；三样分开——按产出它的技能再分一层目录（目录名就是那门技能的名字），装那门技能产出的整套文档；脚本层与本体层合成**一套**写，不按层拆成两套（脚本层那些用例要注明对应 `tests/<技能名>/` 下哪一条）；`cases/` 是评测用例，一条一个目录：`prompt.md` 加 `graders/*.md`；`results/` 是跑出来的报告，评测框架自己写、不进 git。
- **每门技能自包含。** 改哪门就读它自己的 `SKILL.md`；同一目录下的 `README.md` 是写给人看的，技能运行时不会读它。

## Agent skills

### Issue tracker

issue 与需求写在仓库里的 `.scratch/<功能名>/` 下，一个功能一个目录的 markdown 文件；不在 GitHub 上开 issue。见 `docs/agents/issue-tracker.md`。

### Domain docs

单上下文布局：根目录一份 `CONTEXT.md`，决策记录放 `docs/adr/`。见 `docs/agents/domain.md`。
