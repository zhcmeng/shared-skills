# shared-skills

跨工程共享的 Agent Skill 集合，同时是一个 Claude Code 插件。插件本体在 `plugin/` 下，只有它会被装到使用者机器上；`checks/`、`docs/`、`evals/`、`tests/` 这些开发用的东西在仓库根，不跟着发出去。`plugin/skills/` 会被自动注册，hook 会把 `plugin/rules/` 下的常驻规则与 `plugin/statusline/` 下的脚本同步到配置目录，并给上游 `i-have-adhd` 插件建上它的常驻标记文件（那条链子的开关与代价写在 README 的「常驻规则」一节）。

这个仓库的改动有四类各有讲究，下面一条管一类。每类的细则在 README 的「维护」一节——加技能、改规则、改状态栏、改通知都在里面；某个技能自己的脚本与素材怎么改，在那门技能目录下的 `README.md` 里。

- **改完自己跑检查，没有东西替你跑。** 这个仓库不装提交前钩子、也没有 CI——就是不让人每次提交都等两分钟。代价写在明处：忘跑就是没跑，没人会拦你。`bash checks/verify.sh <关键词>` 只跑文件名里带该词的模块——改动碰到哪一条链子就跑哪一条（改通知就跑 `verify.sh notify`），没碰到的不跑；懒得自己挑就用 `bash checks/verify.sh --changed`，它按工作区与暂存区一起挑（快得多）；`bash checks/verify.sh` 是不挑、跑全部（约两分钟）。它验的是哪些链子，看 `checks/verify.d/` 下各模块文件头的 `# watch:` 声明——那一行写着这块盯哪些路径，也就是「改了哪儿该跑哪一块」的答案；别在这儿另列一份（列过一份，落下了后加的 80、90 两块）。技能脚本自己的测试另有入口：`bash tests/run.sh [技能名]`，按需跑、不挂进 `verify.sh`（理由写在它的头注里）。
- **要抬版本号，交付前抬一次。** 改了 `plugin/skills/`、`plugin/rules/`、`plugin/statusline/`、`plugin/hooks/` 里的东西，在推到远端、要让别人（或你另一个会话）拿到这批内容之前，把 `plugin/.claude-plugin/plugin.json` 和 `.claude-plugin/marketplace.json` 里的版本号一起抬上去，两处必须一致；一批内容共用同一个号，中间的提交不必逐笔抬。插件按版本号分目录安装、内容一致就不重装——不抬版本号的效果是「仓库改了，别人跑的还是旧的」，全程不报错。抬哪一位：**新增功能才抬中间那位**——新增技能、新增 hook、状态栏新增功能；**对原有内容的修改一律抬最后那位**——技能的命令行接口或产出文件名变了、正文措辞、判据补充、示例、脚本内部修法、文档。判不准抬最后。
- **`plugin/` 下的东西都会发出去。** 插件安装是把 `plugin/` 整个目录拷到使用者机器上，没有排除机制。测试用例、设计稿、临时文件，只要放在 `plugin/skills/<某技能>/` 下面就跟着发给每个使用者。不想发的放 `plugin/` 外面。
- **每门技能自包含。** 改哪门就读它自己的 `SKILL.md`；同一目录下的 `README.md` 是写给人看的，技能运行时不会读它。

## Agent skills

### Issue tracker

issue 与需求写在仓库里的 `.scratch/<功能名>/` 下，一个功能一个目录的 markdown 文件；不在 GitHub 上开 issue。见 `docs/agents/issue-tracker.md`。

### Domain docs

单上下文布局：根目录一份 `CONTEXT.md`，决策记录放 `docs/adr/`。见 `docs/agents/domain.md`。
