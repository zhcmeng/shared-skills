# 测试用例规格说明

测试项是 `plugin/skills/token-counter/` 整门技能：一份技能正文加一支计数脚本。例行按四门技术导出：等价类划分（TM-1）导出输入道与文本内容的覆盖项，边界值分析（TM-2）以三值边界导出字节层面的覆盖项，判定表测试（TM-3）导出首次运行装依赖的四条规则，场景测试（TM-4）导出八个场景。

用例分两批：**脚本这一批**（TC-1 至 TC-25）判的是命令行跑出来的东西——输出、退出码、盘上落下的文件；**技能这一批**（TC-26 至 TC-35）把整条链（技能被唤起、模型照正文调用脚本、把结果答回）串起来跑，判的是模型跑起来一路做了什么。两批的判据落在哪一层分别统一填「落在输出上」与「要读执行过程」（理由见决策依据）。

用例表里的写法约定：`<技能目录>` 指 ENV-3 那份技能副本的目录；`python` 指 ENV-4 那个解释器（另写明用 ENV-5 的除外）；样本与用户消息按 `DATA-` 编号从测试数据需求取，不在本表重述内容。

## 一、测试覆盖项

对照 TM-1 至 TM-4，四门技术各导出一组覆盖项：

| 唯一标识符 | 英文名 | 描述 | 风险等级 | 可追溯性 |
|:---|:---|:---|:---|:---|
| TCOV-1 | text_via_option | 有效：在命令行上用 `--text` 直接给一段文本这条道（PART-1） | 中 | TM-1 的 PART-1 |
| TCOV-2 | text_via_file | 有效：给一个存在的 UTF-8 文本文件的路径这条道（PART-2） | 中 | TM-1 的 PART-2 |
| TCOV-3 | text_via_stdin | 有效：把内容从标准输入喂进去这条道（PART-3） | 中 | TM-1 的 PART-3 |
| TCOV-4 | path_not_found | 无效：给的文件路径不存在（PART-4） | 中 | TM-1 的 PART-4 |
| TCOV-5 | path_is_directory | 无效：给的路径指向一个目录（PART-5） | 中 | TM-1 的 PART-5 |
| TCOV-6 | malformed_utf8_bytes | 无效：字节序列的形状不合法（截断的多字节序列、非法首字节、孤立续字节），解不了码（PART-6） | 高 | TM-1 的 PART-6 |
| TCOV-7 | invalid_semantics_bytes | 无效：字节序列的形状合法但语义非法（过长编码、代理区码点、超出 U+10FFFF），解不了码（PART-7） | 高 | TM-1 的 PART-7 |
| TCOV-8 | text_option_with_file | 未规定：`--text` 与文件路径同时给时数哪一个（PART-8） | 中 | TM-1 的 PART-8 |
| TCOV-9 | ascii_text | 有效：纯 ASCII 文本（PART-9） | 高 | TM-1 的 PART-9 |
| TCOV-10 | chinese_text | 有效：纯中文文本（PART-10） | 高 | TM-1 的 PART-10 |
| TCOV-11 | mixed_text | 有效：中英混排、含空格与换行的文本（PART-11） | 高 | TM-1 的 PART-11 |
| TCOV-12 | empty_text | 有效：一个字符都没有的空文本（PART-12） | 高 | TM-1 的 PART-12 |
| TCOV-13 | bom_stripped_from_file | 有效：文件或管道的内容以完整的字节顺序标记开头——那 3 个字节被剥掉（PART-13） | 高 | TM-1 的 PART-13 |
| TCOV-14 | bom_kept_in_text_option | 有效：`--text` 直接给的文本以字节顺序标记那个字符开头——不经解码、不被剥掉（PART-14） | 高 | TM-1 的 PART-14 |
| TCOV-15 | special_token_literal | 有效：含 DeepSeek 特殊 token 的字面形，如 `<｜end▁of▁sentence｜>`（PART-15） | 高 | TM-1 的 PART-15 |
| TCOV-16 | control_characters | 有效：含控制字符（NUL、退格这一类）（PART-16） | 高 | TM-1 的 PART-16 |
| TCOV-17 | zero_width_characters | 有效：含零宽字符与不可见格式字符（零宽空格、文本中间的标记字符）（PART-17） | 高 | TM-1 的 PART-17 |
| TCOV-18 | replacement_and_noncharacters | 有效：含替换字符或非字符码点（U+FFFD、U+FFFE 这一类）（PART-18） | 高 | TM-1 的 PART-18 |
| TCOV-19 | spec_semantics_loading | 有效：按随技能分发那份词表的规范语义加载它（PART-19） | 高 | TM-1 的 PART-19 |
| TCOV-20 | incompatible_loader_avoided | 无效功能：改用另一条兼容加载路径读同一份词表——不许这么做（PART-20） | 高 | TM-1 的 PART-20 |
| TCOV-21 | two_line_output | 有效：报出 token 数与字符数两行（PART-21） | 中 | TM-1 的 PART-21 |
| TCOV-22 | tokens_only_answer | 有效：用户只要 token 量时，答话里报出 token 数（PART-22） | 中 | TM-1 的 PART-22 |
| TCOV-23 | cost_caliber_stated | 有效：用户问调用成本时，点明离线算不出缓存命中、计费以接口返回的用量为准（PART-23） | 中 | TM-1 的 PART-23 |
| TCOV-24 | other_model_declined | 有效：用户点名别的模型时，说明本技能不覆盖那个模型、不给近似数（PART-24） | 中 | TM-1 的 PART-24 |
| TCOV-25 | no_borrowed_estimate | 无效功能：绕开本技能另去找一个数顶上、冒充那个模型的数——不许这么做（PART-25） | 中 | TM-1 的 PART-25 |
| TCOV-26 | full_request_assembled | 有效：要估一次完整对话请求时，先按对话模板把请求拼装起来再计数（PART-26） | 中 | TM-1 的 PART-26 |
| TCOV-27 | undocumented_failure_wind_down | 未规定：输入走不通时（路径不存在、路径是目录、解不了码、给了两个文件）以什么方式收场（PART-27） | 中 | TM-1 的 PART-27 |
| TCOV-28 | char_count_negative | 甲·下边界外邻值：一次调用交过去的字符个数为 -1——UTF-8 里造不出负数字符。判为不可行，已从分母里剔除 | — | TM-2 的甲·下边界外的邻值 |
| TCOV-29 | char_count_zero | 甲·下边界：0 个字符（空文本） | 高 | TM-2 的甲·下边界 |
| TCOV-30 | char_count_one | 甲·下边界上方邻值：1 个字符 | 高 | TM-2 的甲·下边界上方的邻值 |
| TCOV-31 | char_bytes_zero | 乙·下边界外邻值：一个字符占 0 个字节——UTF-8 里没有占 0 字节的字符。判为不可行，已从分母里剔除 | — | TM-2 的乙·下边界外的邻值 |
| TCOV-32 | char_bytes_one | 乙·下边界：一个字符占 1 个字节（ASCII） | 高 | TM-2 的乙·下边界 |
| TCOV-33 | char_bytes_two | 乙·区间中：一个字符占 2 个字节 | 高 | TM-2 的乙·区间中的取值 |
| TCOV-34 | char_bytes_three | 乙·区间中：一个字符占 3 个字节 | 高 | TM-2 的乙·区间中的取值 |
| TCOV-35 | char_bytes_four | 乙·上边界：一个字符占 4 个字节 | 高 | TM-2 的乙·上边界 |
| TCOV-36 | char_bytes_five | 乙·上边界外邻值：一个字符占 5 个字节——UTF-8 单字符最长 4 个字节。判为不可行，已从分母里剔除 | — | TM-2 的乙·上边界外的邻值 |
| TCOV-37 | bom_bytes_negative | 丙·下边界外邻值：开头属于字节顺序标记的字节数为 -1——字节数造不出负的。判为不可行，已从分母里剔除 | — | TM-2 的丙·下边界外的邻值 |
| TCOV-38 | bom_bytes_zero | 丙·下边界：开头 0 个字节属于字节顺序标记（不带标记的文本） | 高 | TM-2 的丙·下边界 |
| TCOV-39 | bom_bytes_one | 丙·区间中：开头 1 个字节属于标记的残缺形态（`EF`） | 高 | TM-2 的丙·区间中的取值 |
| TCOV-40 | bom_bytes_two | 丙·区间中：开头 2 个字节属于标记的残缺形态（`EF BB`） | 高 | TM-2 的丙·区间中的取值 |
| TCOV-41 | bom_bytes_three | 丙·上边界：开头 3 个字节属于标记的完整形态（`EF BB BF`） | 高 | TM-2 的丙·上边界 |
| TCOV-42 | bom_bytes_four | 丙·上边界外邻值：开头 4 个字节属于字节顺序标记——标记恰好 3 个字节，第 4 个字节不再属于它。判为不可行，已从分母里剔除 | — | TM-2 的丙·上边界外的邻值 |
| TCOV-43 | reuse_installed_engine | 规则 1：目标解释器里已经能导入那份引擎——直接用现成的，一个字节都不装 | 中 | TM-3 的规则 1 |
| TCOV-44 | install_bundled_wheel | 规则 2：没装、打包那份在、装得上——先装随技能打包的那份（离线、不带依赖） | 中 | TM-3 的规则 2 |
| TCOV-45 | fallback_online_install | 规则 3：没装、打包那份在、可它装不上——改从包索引联网装钉住的 0.22.2 | 中 | TM-3 的规则 3 |
| TCOV-46 | online_install_without_bundle | 规则 4：没装、打包那份压根不在——直接走联网那条道装钉住的 0.22.2 | 中 | TM-3 的规则 4 |
| TCOV-47 | scenario_main_counting | 主场景：一次计数请求走完（唤起、定位、交给脚本、计数、报回） | 中 | TM-4 的主场景 |
| TCOV-48 | scenario_other_model | 备选场景：点名的是别的模型 | 中 | TM-4 的备选场景「点名的是别的模型」 |
| TCOV-49 | scenario_cost_question | 备选场景：问的是调用成本 | 中 | TM-4 的备选场景「问的是调用成本」 |
| TCOV-50 | scenario_full_request | 备选场景：文本要喂进一次完整对话请求 | 中 | TM-4 的备选场景「文本要喂进一次完整对话请求」 |
| TCOV-51 | scenario_clean_machine | 备选场景：目标机是干净的、没装引擎 | 中 | TM-4 的备选场景「目标机是干净的、没装引擎」 |
| TCOV-52 | scenario_tokens_only | 备选场景：用户只要 token 量 | 中 | TM-4 的备选场景「用户只要 token 量」 |
| TCOV-53 | scenario_special_token | 备选场景：文本里含特殊 token 的字面形 | 中 | TM-4 的备选场景「文本里含特殊 token 的字面形」 |
| TCOV-54 | scenario_bad_input | 备选场景：用户给的输入走不通 | 中 | TM-4 的备选场景「用户给的输入走不通」 |

注：TCOV-28、TCOV-31、TCOV-36、TCOV-37、TCOV-42 这五条判为不可行，原因写在各自的描述栏里（取值在 UTF-8 里造不出来），已从覆盖率分母里剔除；对应表里也照此写「不可行」。

注：TCOV-8 与 TCOV-27 是依据没有规定的两处——两条道同时给时数哪一份、走不通时以什么方式收场。这两处造得出来、也比得出来，用例把实际行为记下来报给用户定口径。

## 二、测试用例

一行一条用例；前 25 条是脚本这一批，后 10 条是技能这一批：

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 前置条件 | 输入 | 预期结果 | 判据落在哪一层 |
|:---|:---|:---|:---|:---|:---|:---|:---|
| TC-1 | text_option_chinese | 验证 `--text` 这条道能数纯中文文本：按规范语义加载词表、报出两行 | 高 | ENV-1、ENV-2 就位；ENV-3 的技能副本摆好；解释器取 ENV-4 | `python <技能目录>/scripts/count_tokens.py --text "你好，世界"` | 退出码 0；标准输出两行——`tokens: 3`、`chars: 5`；标准错误为空 | 落在输出上 |
| TC-2 | file_route_ascii | 验证文件这条道，收尾换行也算进字符数 | 高 | 在 TC-1 的前提上；DATA-1 的文件摆在工作区 | `python <技能目录>/scripts/count_tokens.py <DATA-1 的路径>` | 退出码 0；标准输出 `tokens: 3`、`chars: 12`——`hello world` 十一个字符加收尾换行一个；标准错误为空 | 落在输出上 |
| TC-3 | stdin_route_mixed | 验证标准输入这条道，混排文本数得对 | 高 | 在 TC-1 的前提上；DATA-12 的文件摆在工作区 | 把 DATA-12 的字节接到标准输入上再跑：`python <技能目录>/scripts/count_tokens.py < <DATA-12 的路径>` | 退出码 0；标准输出 `tokens: 5`、`chars: 12`——`你好 world 世界` 十一个字符加收尾换行一个 | 落在输出上 |
| TC-4 | empty_text_counts_zero | 验证空文本数出两个 0（甲下边界） | 高 | 在 TC-1 的前提上 | `python <技能目录>/scripts/count_tokens.py --text ""` | 退出码 0；标准输出 `tokens: 0`、`chars: 0`；标准错误为空 | 落在输出上 |
| TC-5 | one_ascii_char | 验证 1 个字符（甲下边界上方邻值）、占 1 个字节（乙下边界）时的计数 | 高 | 在 TC-1 的前提上 | `python <技能目录>/scripts/count_tokens.py --text "<DATA-11 里的 a>"` | 退出码 0；标准输出 `tokens: 1`、`chars: 1` | 落在输出上 |
| TC-6 | one_two_byte_char | 验证一个字符占 2 个字节时的计数 | 高 | 在 TC-1 的前提上 | `python <技能目录>/scripts/count_tokens.py --text "<DATA-11 里的 é>"` | 退出码 0；标准输出 `tokens: 1`、`chars: 1` | 落在输出上 |
| TC-7 | one_three_byte_char | 验证一个字符占 3 个字节时的计数 | 高 | 在 TC-1 的前提上 | `python <技能目录>/scripts/count_tokens.py --text "<DATA-11 里的 中>"` | 退出码 0；标准输出 `tokens: 1`、`chars: 1` | 落在输出上 |
| TC-8 | one_four_byte_char | 验证一个字符占 4 个字节（乙上边界）时的计数 | 高 | 在 TC-1 的前提上 | `python <技能目录>/scripts/count_tokens.py --text "<DATA-11 里的 😀>"` | 退出码 0；标准输出 `tokens: 2`、`chars: 1`——一个字符编成了两个 token | 落在输出上 |
| TC-9 | complete_bom_stripped | 验证文件开头完整的字节顺序标记（丙上边界）被剥掉 | 高 | 在 TC-1 的前提上；DATA-3 的文件摆在工作区 | `python <技能目录>/scripts/count_tokens.py <DATA-3 的路径>` | 退出码 0；标准输出 `tokens: 1`、`chars: 2`——文件里是标记加 `你好` 两个字符，开头那 3 个字节没算进字符数 | 落在输出上 |
| TC-10 | truncated_one_bom_byte | 验证开头只有 1 个字节的残缺形态（丙区间中）以非零退出码收场 | 高 | 在 TC-1 的前提上；DATA-4 的文件摆在工作区 | `python <技能目录>/scripts/count_tokens.py <DATA-4 的路径>` | 退出码非 0（实测 1）；标准输出一个字符都没有；标准错误给出 `not valid UTF-8: ` 加 DATA-4 的路径 | 落在输出上 |
| TC-11 | truncated_two_bom_bytes | 验证开头 2 个字节的残缺形态（丙区间中）以非零退出码收场 | 高 | 在 TC-1 的前提上；DATA-5 的文件摆在工作区 | `python <技能目录>/scripts/count_tokens.py <DATA-5 的路径>` | 退出码非 0（实测 1）；标准输出一个字符都没有；标准错误给出 `not valid UTF-8: ` 加 DATA-5 的路径 | 落在输出上 |
| TC-12 | surrogate_bytes_rejected | 验证形状合法但语义非法的字节序列（代理区编码）同样以非零退出码收场 | 高 | 在 TC-1 的前提上；DATA-6 的文件摆在工作区 | `python <技能目录>/scripts/count_tokens.py <DATA-6 的路径>` | 退出码非 0（实测 1）；标准输出一个字符都没有；标准错误给出 `not valid UTF-8: ` 加 DATA-6 的路径 | 落在输出上 |
| TC-13 | bom_char_kept_in_option | 验证 `--text` 开头那个标记字符不被剥、照常计数 | 高 | 在 TC-1 的前提上 | `python <技能目录>/scripts/count_tokens.py --text "<DATA-10 的文本>"`（U+FEFF 加 `你好`） | 退出码 0；标准输出 `tokens: 2`、`chars: 3`——三个字符（标记、你、好），标记与后头的文本分成两个 token | 落在输出上 |
| TC-14 | special_token_counted | 验证特殊 token 的字面形按词表计入 | 高 | 在 TC-1 的前提上 | `python <技能目录>/scripts/count_tokens.py --text "<DATA-8 的文本>"`（原样给，不转义） | 退出码 0；标准输出 `tokens: 1`、`chars: 19`——整串算一个 token | 落在输出上 |
| TC-15 | control_chars_in_file | 验证控制字符照常计数（NUL 进不了命令行，走文件道） | 高 | 在 TC-1 的前提上；DATA-7 的文件摆在工作区 | `python <技能目录>/scripts/count_tokens.py <DATA-7 的路径>` | 退出码 0；标准输出 `tokens: 3`、`chars: 3`——`a`、NUL、`b` 三个字符各算一个 token | 落在输出上 |
| TC-16 | zero_width_in_option | 验证零宽字符照常计数 | 高 | 在 TC-1 的前提上 | `python <技能目录>/scripts/count_tokens.py --text "<DATA-9 的文本>"`（`a`、U+200B、`b`） | 退出码 0；标准输出 `tokens: 3`、`chars: 3` | 落在输出上 |
| TC-17 | replacement_and_noncharacter_file | 验证替换字符与非字符码点照常计数 | 高 | 在 TC-1 的前提上；DATA-13 的文件摆在工作区 | `python <技能目录>/scripts/count_tokens.py <DATA-13 的路径>` | 退出码 0；标准输出 `tokens: 3`、`chars: 2`——替换字符一个 token、非字符两个 | 落在输出上 |
| TC-18 | option_beats_file | 记下两条道同时给时数的是哪一份（依据未规定这一处） | 中 | 在 TC-1 的前提上；DATA-2 的文件摆在工作区 | `python <技能目录>/scripts/count_tokens.py <DATA-2 的路径> --text "hello"` | 退出码 0；标准输出 `tokens: 1`、`chars: 5`——数的是 `--text` 那份（`hello`），文件那份没被读；这一条记的是实际行为，报给用户定口径 | 落在输出上 |
| TC-19 | missing_path_wind_down | 记下路径不存在时怎么收场（依据未规定这一处） | 中 | 在 TC-1 的前提上；确认工作区里没有 `not_here.bin` 这个文件 | `python <技能目录>/scripts/count_tokens.py <工作区>/not_here.bin` | 退出码非 0（实测 1）；标准输出一个字符都没有；标准错误是一段报错回溯，末行点名 `FileNotFoundError` 与那个路径 | 落在输出上 |
| TC-20 | directory_path_wind_down | 记下路径是目录时怎么收场（依据未规定这一处） | 中 | 在 TC-1 的前提上；用工作区目录本身当路径 | `python <技能目录>/scripts/count_tokens.py <工作区目录>` | 退出码非 0（实测 1）；标准输出一个字符都没有；标准错误是一段报错回溯，末行点名 `Errno 13` 的 `PermissionError` 与那个路径 | 落在输出上 |
| TC-21 | two_files_wind_down | 记下给了两个文件时怎么收场（依据未规定这一处） | 中 | 在 TC-1 的前提上；DATA-1、DATA-2 的文件摆在工作区 | `python <技能目录>/scripts/count_tokens.py <DATA-1 的路径> <DATA-2 的路径>` | 退出码 2；标准输出一个字符都没有；标准错误是命令行用法提示——`unrecognized arguments` 加第二个路径 | 落在输出上 |
| TC-22 | no_install_when_engine_present | 验证引擎已在位时一个字节都不装 | 中 | ENV-4 的解释器里已装那份引擎 | `python <技能目录>/scripts/count_tokens.py --text "你好"` | 退出码 0；标准错误为空——没有任何安装动作的痕迹；标准输出 `tokens: 1`、`chars: 2` | 落在输出上 |
| TC-23 | first_run_installs_bundled_wheel | 验证干净机器上首次运行装的是随技能打包的那份 | 中 | ENV-5 的干净解释器（先确认它导不进那份引擎）；ENV-3 的副本原样未动；DATA-1 的文件摆在工作区 | 用 ENV-5 的解释器跑：`python <技能目录>/scripts/count_tokens.py <DATA-1 的路径>` | 退出码 0；标准输出 `tokens: 3`、`chars: 12`；装在 ENV-5 上的引擎版本为 0.22.2，装在它上面的来源记录指向技能副本 `wheels/` 里那份包文件——是离线装的，没走包索引 | 落在输出上 |
| TC-24 | broken_wheel_falls_back_online | 验证打包那份装不上时改走联网那条道 | 中 | 把 ENV-3 的副本复制到 ENV-8，把副本 `wheels/` 里那份包文件换成同名的坏文件；ENV-5 的干净解释器；ENV-6 包索引可达 | 用 ENV-5 的解释器跑副本里的脚本：`python <副本>/scripts/count_tokens.py --text "你好"` | 退出码 0；标准输出 `tokens: 1`、`chars: 2`；装在 ENV-5 上的引擎版本为 0.22.2，装在它上面的来源记录为空——是从包索引取的，不是本地那份坏文件 | 落在输出上 |
| TC-25 | no_bundle_goes_online | 验证打包那份不在时直接走联网那条道 | 中 | 把 ENV-3 的副本复制到 ENV-8，删掉副本里 `wheels/` 整个目录；ENV-5 的干净解释器；ENV-6 包索引可达 | 用 ENV-5 的解释器跑副本里的脚本：`python <副本>/scripts/count_tokens.py --text "你好"` | 退出码 0；标准输出 `tokens: 1`、`chars: 2`；装在 ENV-5 上的引擎版本为 0.22.2，装在它上面的来源记录为空——直接来自包索引 | 落在输出上 |
| TC-26 | skill_main_text_request | 验证一句数文本的请求走完整条链，答话里报出 token 数 | 中 | ENV-3 的技能按使用者机器上装好的样子在一个会话里就位（ENV-1、ENV-2）；ENV-7 的过程记录开着 | 把 DATA-15 那条消息原样发进会话：`数一下冒号后面这一整行的 token：你好 world 世界` | 答话里报出 token 数 4——冒号后那一行 11 个字符、4 个 token；过程记录里脚本被跑了起来，交进去的是那一行文本 | 要读执行过程 |
| TC-27 | skill_main_file_request | 验证一句数文件的请求走完整条链 | 中 | 在 TC-26 的前提上；DATA-2 的文件摆在工作区 | 把 DATA-16 那条消息原样发进会话：`算一下这个文件的 token：<DATA-2 的绝对路径>` | 答话里报出 token 数 3；过程记录里脚本被跑了起来，交进去的是那份文件的路径 | 要读执行过程 |
| TC-28 | skill_tokens_only_reply | 验证用户只要 token 量时，答话里报出 token 数 | 中 | 在 TC-26 的前提上；DATA-2 的文件摆在工作区 | 把 DATA-17 那条消息原样发进会话：`这个文件有多少个 token：<DATA-2 的绝对路径>` | 答话里报出 token 数 3 | 要读执行过程 |
| TC-29 | skill_other_model_declined | 验证点名别的模型时说明不覆盖、不给近似数 | 中 | 在 TC-26 的前提上 | 把 DATA-18 那条消息原样发进会话：`数一下冒号后面这一整行文本在 Claude 上大概是多少 token：你好，世界` | 答话里明确说明本技能不覆盖那个模型（Claude）；没有出现以那个模型为名的 token 数；没有绕开本技能从别处拿一个估算数冒充 | 要读执行过程 |
| TC-30 | skill_cost_caliber | 验证问调用成本时报出数、并点明口径 | 中 | 在 TC-26 的前提上 | 把 DATA-19 那条消息原样发进会话：`数一下冒号后面这一整行，顺便看看发到 DeepSeek 上大概要花多少钱：你好，世界` | 答话里报出 token 数 3；并点明两处口径——离线算不出缓存命中（它取决于服务端缓存状态）、计费以接口返回的用量为准 | 要读执行过程 |
| TC-31 | skill_full_request_assembled | 验证估完整对话请求时先拼装再计数 | 中 | 在 TC-26 的前提上 | 把 DATA-20 那条消息原样发进会话：`我要把冒号后面这一整行作为 system 提示发给 DeepSeek，后面再接一句用户消息「今天天气怎么样」，估一下这次请求一共多少 token：你好，世界` | 过程记录里交进脚本的是按对话模板拼装后的整段请求（带消息结构），不是那一行原文；答话里报出的数比那一行原文单算的数（3）大 | 要读执行过程 |
| TC-32 | skill_clean_machine | 验证目标机干净时，首次运行照常把整条链走完 | 中 | ENV-5 的干净解释器在会话里可用（先确认它导不进那份引擎）；DATA-2 的文件摆在工作区；ENV-7 的过程记录开着 | 把 DATA-16 那条消息原样发进会话：`算一下这个文件的 token：<DATA-2 的绝对路径>` | 答话里报出 token 数 3；过程记录里能看到首次运行先把引擎装上（装的是技能副本 `wheels/` 里那份包、离线），随后脚本报数 | 要读执行过程 |
| TC-33 | skill_special_token_kept | 验证含特殊 token 的文本原样交进去、按词表计入 | 中 | 在 TC-26 的前提上 | 把 DATA-21 那条消息原样发进会话：`数一下冒号后面这一整行里有多少 token：<｜end▁of▁sentence｜>` | 答话里报出 token 数 1；过程记录里交进脚本的是原样的那一行——那个标记没被转义、没被拆开、也没被剥离 | 要读执行过程 |
| TC-34 | skill_missing_path_reply | 验证文件不存在时照实说数不了 | 中 | 在 TC-26 的前提上；确认工作区里没有 `not_here.bin` 这个文件 | 把 DATA-22 那条消息原样发进会话：`数一下这个文件的 token：<工作区>/not_here.bin` | 答话里照实说明这个输入数不了（路径不存在）；没有报出任何 token 数；没有拿别处的数顶上 | 要读执行过程 |
| TC-35 | skill_undecodable_file_reply | 验证文件解不了码时照实说数不了 | 中 | 在 TC-26 的前提上；DATA-14 的文件摆在工作区 | 把 DATA-23 那条消息原样发进会话：`数一下这个文件的 token：<DATA-14 的绝对路径>` | 答话里照实说明那份文件的内容不是 UTF-8、数不了；没有报出任何 token 数 | 要读执行过程 |

注：TC-10、TC-11、TC-12 的「退出码非 0」后面带了个实测值，是给读的人一个准头；判的时候只看非 0，运行时真改了收场方式（比如统一成一个退出码），这一条仍算过——依据里没说走不通时必须用哪个码。

注：技能这一批（TC-26 至 TC-35）的判据不钉措辞——「说明不覆盖那个模型」「说数不了」这类，判的是那个意思有没有，不判原话怎么写的。

注：TC-31 不判拼装出来的字节与哪份模板逐字相同，也不写死拼装后的 token 数——依据点名的那份模板文件不随技能分发，拼出来的形态各处不一致（理由见决策依据）。

## 三、覆盖项 ↔ 用例对应表

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 有效：在命令行上用 `--text` 直接给一段文本这条道 | TC-1 |
| TCOV-2 | 有效：给一个存在的 UTF-8 文本文件的路径这条道 | TC-2 |
| TCOV-3 | 有效：把内容从标准输入喂进去这条道 | TC-3 |
| TCOV-4 | 无效：给的文件路径不存在 | TC-19、TC-34 |
| TCOV-5 | 无效：给的路径指向一个目录 | TC-20 |
| TCOV-6 | 无效：形状不合法的字节序列，解不了码 | TC-10、TC-11、TC-35 |
| TCOV-7 | 无效：形状合法但语义非法的字节序列，解不了码 | TC-12 |
| TCOV-8 | 未规定：`--text` 与文件路径同时给时数哪一个 | TC-18 |
| TCOV-9 | 有效：纯 ASCII 文本 | TC-2 |
| TCOV-10 | 有效：纯中文文本 | TC-1 |
| TCOV-11 | 有效：中英混排、含空格与换行的文本 | TC-3、TC-26 |
| TCOV-12 | 有效：空文本 | TC-4 |
| TCOV-13 | 有效：文件或管道的内容以完整字节顺序标记开头，那 3 个字节被剥掉 | TC-9 |
| TCOV-14 | 有效：`--text` 给的文本以标记那个字符开头，不被剥掉 | TC-13 |
| TCOV-15 | 有效：含特殊 token 的字面形 | TC-14、TC-33 |
| TCOV-16 | 有效：含控制字符 | TC-15 |
| TCOV-17 | 有效：含零宽字符与不可见格式字符 | TC-16 |
| TCOV-18 | 有效：含替换字符或非字符码点 | TC-17 |
| TCOV-19 | 有效：按随技能分发那份词表的规范语义加载它 | TC-1 |
| TCOV-20 | 无效功能：改用另一条兼容加载路径读同一份词表 | TC-1 |
| TCOV-21 | 有效：报出 token 数与字符数两行 | TC-1 |
| TCOV-22 | 有效：用户只要 token 量时，答话里报出 token 数 | TC-28 |
| TCOV-23 | 有效：用户问调用成本时，点明离线算不出缓存命中、计费以接口返回的用量为准 | TC-30 |
| TCOV-24 | 有效：用户点名别的模型时，说明不覆盖、不给近似数 | TC-29 |
| TCOV-25 | 无效功能：绕开本技能另找一个数顶上、冒充那个模型的数 | TC-29 |
| TCOV-26 | 有效：估一次完整对话请求时，先按对话模板拼装起来再计数 | TC-31 |
| TCOV-27 | 未规定：输入走不通时以什么方式收场 | TC-19、TC-20、TC-21、TC-34、TC-35 |
| TCOV-28 | 甲·下边界外邻值：字符个数为 -1 | 不可行：UTF-8 里造不出负数字符 |
| TCOV-29 | 甲·下边界：0 个字符 | TC-4 |
| TCOV-30 | 甲·下边界上方邻值：1 个字符 | TC-5 |
| TCOV-31 | 乙·下边界外邻值：一个字符占 0 个字节 | 不可行：UTF-8 里没有占 0 字节的字符 |
| TCOV-32 | 乙·下边界：一个字符占 1 个字节 | TC-5 |
| TCOV-33 | 乙·区间中：一个字符占 2 个字节 | TC-6 |
| TCOV-34 | 乙·区间中：一个字符占 3 个字节 | TC-7 |
| TCOV-35 | 乙·上边界：一个字符占 4 个字节 | TC-8 |
| TCOV-36 | 乙·上边界外邻值：一个字符占 5 个字节 | 不可行：UTF-8 单字符最长 4 个字节 |
| TCOV-37 | 丙·下边界外邻值：开头属于标记的字节数为 -1 | 不可行：字节数造不出负的 |
| TCOV-38 | 丙·下边界：开头 0 个字节属于标记 | TC-1 |
| TCOV-39 | 丙·区间中：开头 1 个字节属于标记的残缺形态 | TC-10 |
| TCOV-40 | 丙·区间中：开头 2 个字节属于标记的残缺形态 | TC-11 |
| TCOV-41 | 丙·上边界：开头 3 个字节属于标记的完整形态 | TC-9 |
| TCOV-42 | 丙·上边界外邻值：开头 4 个字节属于标记 | 不可行：标记恰好 3 个字节，第 4 个字节不再属于它 |
| TCOV-43 | 规则 1：解释器里已经能导入那份引擎——直接用现成的 | TC-22 |
| TCOV-44 | 规则 2：没装、打包那份在、装得上——先装打包那份 | TC-23 |
| TCOV-45 | 规则 3：没装、打包那份在、可它装不上——改从包索引联网装 | TC-24 |
| TCOV-46 | 规则 4：没装、打包那份压根不在——直接走联网那条道 | TC-25 |
| TCOV-47 | 主场景：一次计数请求走完 | TC-26、TC-27、TC-32 |
| TCOV-48 | 备选场景：点名的是别的模型 | TC-29 |
| TCOV-49 | 备选场景：问的是调用成本 | TC-30 |
| TCOV-50 | 备选场景：文本要喂进一次完整对话请求 | TC-31 |
| TCOV-51 | 备选场景：目标机是干净的、没装引擎 | TC-32 |
| TCOV-52 | 备选场景：用户只要 token 量 | TC-28 |
| TCOV-53 | 备选场景：文本里含特殊 token 的字面形 | TC-33 |
| TCOV-54 | 备选场景：用户给的输入走不通 | TC-34、TC-35 |

注：这一栏列的是**以这一条为验证对象**的用例——目标栏指着它、预期结果栏为它写死了取值的那几条。一批用例顺带共用的东西（两行输出这个形态、退出码 0、样本从哪条道进来）不在每条里各列一遍，只在指着它的那一条上列。

## 四、覆盖率自检

| 技术（档位） | 覆盖项编号 | 覆盖项总数 T | 已被用例覆盖 N | 覆盖率 N÷T | 完成准则要求 |
|:---|:---|:---|:---|:---|:---|
| 等价类划分 | TCOV-1～TCOV-27 | 27 | 27 | 27÷27＝100% | 100% |
| 边界值分析（三值边界） | TCOV-29、TCOV-30、TCOV-32～TCOV-35、TCOV-38～TCOV-41 | 10 | 10 | 10÷10＝100% | 100% |
| 判定表测试 | TCOV-43～TCOV-46 | 4 | 4 | 4÷4＝100% | 100% |
| 场景测试 | TCOV-47～TCOV-54 | 8 | 8 | 8÷8＝100% | 100% |

注：边界值分析那一行按三值边界识别的边界值共 15 条，其中 5 条判为不可行、已剔除——分母是 10 条，全部有对应用例。上表四门合计覆盖 27＋10＋4＋8＝49 条覆盖项。

注：T 按各门技术的算式核过——等价类划分＝等价类的条数（TM-1 数出 27 条）；边界值分析＝识别出的边界值条数减不可行的（15−5＝10）；判定表测试＝可行判定规则的条数（4 条规则都可）；场景测试＝主场景加备选场景（1＋7＝8）。四门都核得上。

## 五、成品落点

| 成品 | 落的是哪些条目 |
|:---|:---|
| `tests/token-counter/test_count_tokens.py` | TM-1、TM-2、TM-3；TP-1、TP-2；TC-1 至 TC-25；TCOV-1 至 TCOV-21、TCOV-27、TCOV-29、TCOV-30、TCOV-32 至 TCOV-35、TCOV-38 至 TCOV-41、TCOV-43 至 TCOV-46；DATA-1 至 DATA-13；ENV-1 至 ENV-6、ENV-8 |
| `evals/token-counter/cases/` | TM-4；TP-3、TP-4；TC-26 至 TC-35；TCOV-22 至 TCOV-26、TCOV-47 至 TCOV-54；DATA-2、DATA-14 至 DATA-23；ENV-1、ENV-2、ENV-3、ENV-7、ENV-8 |
| `evals/token-counter/fixtures/samples/` | DATA-2、DATA-14 摆成的夹具文件（`chinese_file`、`gbk_file`） |

批二那两批用例跑起来用的两份批次配置住在评测材料根上、与用例目录同一层；它们的名字带测评方案自己的词，这张表里写不了——它们不新编编号，落成对照不经过它们。
