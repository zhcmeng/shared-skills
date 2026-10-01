# 测试环境需求

头两条是测试运行环境：测试规程在哪儿跑、被测那侧在哪儿执行，两条都取本机。其余各条按用例与规程的需要往外补。

| 唯一标识符 | 英文名 | 测试环境项 | 描述 |
|:---|:---|:---|:---|
| ENV-1 | where_procedures_run | 测试规程在哪儿跑 | 本机。测试规程与它跑的命令都在本机执行，不换到别的机器或容器里 |
| ENV-2 | where_subject_runs | 被测那侧在哪儿执行 | 本机。被测的脚本与技能都在本机执行，与 ENV-1 是同一台机器 |
| ENV-3 | python_interpreter | CPython 解释器 | 本机装的那个 CPython 3.13.7；脚本与测试都按它跑。这个版本高于打包 wheel 要求的 3.9，落在匹配范围内 |
| ENV-4 | engine_installed | 已装好的引擎 | 本机环境里 `tokenizers` 0.22.2 已经装好、可以导入。TC-20 要在这一条上跑，并核对跑前跑后版本号与安装位置没变 |
| ENV-5 | clean_python_env | 一个干净的 Python 环境 | 用 `python -m venv` 现建一个虚拟环境，里面没有装引擎。TC-21 至 TC-23 与 TC-32 要在这个环境里跑；用完可以删掉 |
| ENV-6 | network_reachable | 到包索引站点的网络 | 能连到 PyPI。只有回落那一条用例（TC-22）用得上；其余用例都不依赖它 |
| ENV-7 | bundled_assets | 随技能打包的两样东西就位 | 技能目录下的官方词表 `tokenizer.json` 与 `wheels/` 目录都在；`wheels/` 里那个引擎 wheel 名里带平台标记 `cp39-abi3-win_amd64`，与 ENV-3 那个解释器匹配 |
| ENV-8 | command_runner | 能起子进程并读回结果的执行环境 | 一个能跑到命令、并能把命令的标准输出与退出码读回来的执行环境。技能被调用那一批用例（TC-24 至 TC-32）要在它下面跑，判据才读得到 |
