# 测试环境需求

执行五条测试规程所需的环境要素，逐项列出。ENV-1 至 ENV-9 是脚本层那四条规程要摆的条件；ENV-10 至 ENV-13 是本体层那条规程要摆的——技能怎么交出去、回复与命令怎么取、没装引擎的机器、判据文件在哪。

| 唯一标识符 | 英文名 | 测试环境项 | 描述 |
|:---|:---|:---|:---|
| ENV-1 | python_and_platform | Python 解释器与平台 | CPython 3.9 及以上、Windows x64——随包的 wheel 只覆盖这个平台，离线安装那条路只有在这类机器上才走得通。本次执行用的机器是 CPython 3.13、Windows x64，引擎已经装好。与运行环境的偏离有两处：非 Windows 或 CPython 3.8 的机器不在本次环境内，平台不符那一条路用改 wheel 文件名标签的方式模拟（见 TC-23 的前置条件与输入） |
| ENV-2 | bundled_vocab_file | 随包的官方词表文件 | 技能目录下的 `tokenizer.json`，与官方离线包里那一份同源。全部用例的预期值都以这份文件的规范语义为准 |
| ENV-3 | bundled_wheel | 随包的引擎 wheel | `wheels/tokenizers-0.22.2-cp39-abi3-win_amd64.whl`，放在技能目录的 `wheels/` 下 |
| ENV-4 | writable_workspace | 一块可写的工作区 | 放技能目录的副本与各样本文本文件。要能按字节逐一构造文件（0 字节、2 字节、3 字节、4 字节这几个样本都得造得出来），也要能改动或移走副本 `wheels/` 下的 wheel。原始技能目录不动 |
| ENV-5 | clean_environments | 可以反复新建的干净环境 | 没有装 `tokenizers` 的 Python 环境，临时虚拟环境即可；涉及安装的那几条用例各要新起一个，不共用同一次安装的结果 |
| ENV-6 | network_to_pypi | 能连到软件源的网络出口 | 能连到 PyPI，供联网安装那条路用 |
| ENV-7 | no_network | 完全不能对外联网的运行条件 | 用本来就没有网络出口的环境，或在运行期间切断网络来造 |
| ENV-8 | command_shell | 命令行外壳 | 能接管道与重定向——三条输入通道里的标准输入通道靠它 |
| ENV-9 | three_outputs | 能分别取到标准输出、标准错误与退出码的执行方式 | 多条用例的判定要看这三样：标准输出上的两行、标准错误上有没有安装或报错提示、进程以什么状态结束 |
| ENV-10 | skill_handed_over | 把技能整套当作已装技能交给的执行环境 | `plugin/skills/token-counter/` 整个目录（`SKILL.md`、`scripts/count_tokens.py`、`tokenizer.json`、`wheels/`）当作使用者机器上装好的这门技能交给 agent，与它平时装了这门技能时一样；工作目录设在本仓库根——样本文件的路径与技能目录的绝对路径都要指得到。这一层判的是 agent 的应答与动作，不是脚本单独的运行结果 |
| ENV-11 | reply_and_commands_captured | 能取到 agent 当轮回复与它执行的命令的执行方式 | 判定看两样：回复里说了哪几句、给没给数；这一轮执行的命令是什么（主场景与给文件那两条要看命令里指没指到技能目录下的脚本）。只取第一条回复，它后面打算怎么做不算 |
| ENV-12 | machine_without_engine | 一台没装引擎、也没有网络出口的机器 | `tokenizers` 不可导入、对外没有网络出口——首次使用那条用例要的机器状态。造法同 ENV-5 与 ENV-7；区别在于这一项说的是 agent 所在的那台机器在那一轮会话里的状态 |
| ENV-13 | graders_on_disk | 每条用例自己的判据文件 | 用例目录下 `graders/` 里那份判据：写明哪几件事说到算通过、哪几件事一出现就不通过。判定只看当轮回复与执行过的命令，不替 agent 补话，也不替它解释 |
