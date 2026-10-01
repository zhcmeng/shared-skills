# 测试用例规格说明

分五块写：测试覆盖项清单、测试用例、「覆盖项 ↔ 用例」对应表、覆盖率自检、成品落点。

## 测试覆盖项

四门技术各导出一组覆盖项。风险等级照开工输入的风险信息写：输入边界与异常那一处（TM-1、TM-2 两组）、首次运行自动装依赖那一处（TM-3 那一组）判高，其余判中。

| 唯一标识符 | 英文名 | 描述 | 风险等级 | 可追溯性 |
|:---|:---|:---|:---|:---|
| TCOV-1 | text_route_flag | 有效：在命令行上用 `--text` 直接给一段文本这条调用方式 | 高 | TM-1 的 PART-1 |
| TCOV-2 | file_route_path | 有效：给一个存在的 UTF-8 文本文件的路径 | 高 | TM-1 的 PART-2 |
| TCOV-3 | stdin_route_pipe | 有效：把要数的内容用管道从标准输入喂进来 | 高 | TM-1 的 PART-3 |
| TCOV-4 | missing_file_path | 无效：给的文件路径不存在 | 高 | TM-1 的 PART-4 |
| TCOV-5 | path_is_directory | 无效：给的路径指向一个目录 | 高 | TM-1 的 PART-5 |
| TCOV-6 | file_not_utf8 | 无效：文件在，但不是合法的 UTF-8 字节 | 高 | TM-1 的 PART-6 |
| TCOV-7 | ascii_text | 有效：纯 ASCII 文本 | 高 | TM-1 的 PART-7 |
| TCOV-8 | chinese_text | 有效：纯中文文本 | 高 | TM-1 的 PART-8 |
| TCOV-9 | mixed_text_spaces | 有效：中英混排、含空格与换行的文本 | 高 | TM-1 的 PART-9 |
| TCOV-10 | empty_text | 有效：一个字符都没有的空文本 | 高 | TM-1 的 PART-10 |
| TCOV-11 | bom_leading_text | 有效：开头带一个完整字节顺序标记的文本 | 高 | TM-1 的 PART-11 |
| TCOV-12 | special_token_literal | 特殊：含 DeepSeek 特殊 token 字面形的文本 | 高 | TM-1 的 PART-12 |
| TCOV-13 | spec_semantics_loading | 有效：按随技能分发那份词表的规范语义加载它 | 高 | TM-1 的 PART-13 |
| TCOV-14 | compat_path_loading | 无效功能：改用另一条兼容加载路径读同一份词表。那条路径会把以中文开头的文本编成空序列，数出来正是 0 | 高 | TM-1 的 PART-14 |
| TCOV-15 | two_line_output | 有效：报出 token 数与 UTF-8 字符数两行 | 高 | TM-1 的 PART-15 |
| TCOV-16 | tokens_only_answer | 有效：用户只要 token 量时，答话里报出 token 数 | 高 | TM-1 的 PART-16 |
| TCOV-17 | cost_answer_caveats | 有效：用户问调用成本时，点明离线算不出缓存命中、计费以接口返回的用量为准 | 高 | TM-1 的 PART-17 |
| TCOV-18 | other_model_not_covered | 有效：用户点名别的模型时，说明本技能不覆盖那个模型、不给近似数 | 高 | TM-1 的 PART-18 |
| TCOV-19 | other_model_approximation | 无效功能：绕开本技能另去找一个数顶上，给出别的模型的近似 token 数 | 高 | TM-1 的 PART-19 |
| TCOV-20 | full_request_assembled | 有效：要估一次完整对话请求时，先按对话模板把请求拼装起来再计数 | 高 | TM-1 的 PART-20 |
| TCOV-21 | char_count_zero | 字符个数＝0——有序集甲的下边界上的值 | 高 | TM-2 的甲、下边界 |
| TCOV-22 | char_count_one | 字符个数＝1——有序集甲的下边界外一个增量距离（增量 1 个字符） | 高 | TM-2 的甲、下边界 |
| TCOV-23 | char_one_byte | 一个字符占 1 个字节——有序集乙的下边界上的值 | 高 | TM-2 的乙、下边界 |
| TCOV-24 | char_zero_bytes | 一个字符占 0 个字节——有序集乙的下边界外一个增量距离 | 高 | TM-2 的乙、下边界 |
| TCOV-25 | char_four_bytes | 一个字符占 4 个字节——有序集乙的上边界上的值 | 高 | TM-2 的乙、上边界 |
| TCOV-26 | char_five_bytes | 一个字符占 5 个字节——有序集乙的上边界外一个增量距离 | 高 | TM-2 的乙、上边界 |
| TCOV-27 | bom_three_bytes | 文本开头属于字节顺序标记的字节数＝3，恰好是一个完整标记——有序集丙的上边界上的值 | 高 | TM-2 的丙、上边界 |
| TCOV-28 | bom_four_bytes | 文本开头属于字节顺序标记的字节数＝4，完整标记后面还接了一个字节——有序集丙的上边界外一个增量距离 | 高 | TM-2 的丙、上边界 |
| TCOV-29 | install_rule_engine_present | 判定规则 1：C1＝T，用现成的引擎，一个字节都不装 | 高 | TM-3 的规则 1 |
| TCOV-30 | install_rule_bundled_wheel | 判定规则 2：C1＝F、C2＝T、C3＝T，离线装上随技能打包的那份 | 高 | TM-3 的规则 2 |
| TCOV-31 | install_rule_wheel_unusable | 判定规则 3：C1＝F、C2＝T、C3＝F，打包那份装不上，改从包索引联网装钉住的版本 | 高 | TM-3 的规则 3 |
| TCOV-32 | install_rule_no_wheel | 判定规则 4：C1＝F、C2＝F，打包那份不在，直接走联网那条道 | 高 | TM-3 的规则 4 |
| TCOV-33 | main_scenario | 主场景：一次计数请求走完 | 中 | TM-4 的主场景 |
| TCOV-34 | other_model_scenario | 备选场景：点名的是别的模型 | 中 | TM-4 的备选场景 |
| TCOV-35 | cost_scenario | 备选场景：问的是调用成本 | 中 | TM-4 的备选场景 |
| TCOV-36 | full_request_scenario | 备选场景：文本要喂进一次完整对话请求 | 中 | TM-4 的备选场景 |
| TCOV-37 | first_run_scenario | 备选场景：目标机是干净的、没装引擎 | 中 | TM-4 的备选场景 |
| TCOV-38 | tokens_only_scenario | 备选场景：用户只要 token 量 | 中 | TM-4 的备选场景 |
| TCOV-39 | special_token_scenario | 备选场景：文本里含特殊 token 的字面形 | 中 | TM-4 的备选场景 |
| TCOV-40 | dead_end_scenario | 备选场景：用户给的输入走不通 | 中 | TM-4 的备选场景 |

TCOV-24 与 TCOV-26 判为不可行，已从分母里剔除：UTF-8 里最短的字符占 1 个字节、最长的占 4 个字节，占 0 个字节与占 5 个字节的字符在这套编码里造不出来，这两个覆盖项无法被执行。两条在对应表里写「不可行」，落成时也不落它们。

TCOV-4、TCOV-5、TCOV-6 这三条落在依据没写到的地方——依据只说了交过来的应当是 UTF-8 文本，没说走不通时该怎么办。它们的预期结果按「依据未规定这一处」记，后面附一句现状的照实记录，不写成依据撑不起的取值。

## 测试用例

无效输入与无效功能那几类走一对一方式，一条用例只覆盖一个类别，免得一个错误条件把别的遮住；有效那几类走最小化方式，一条用例尽量多盖几个。高风险那几处按需要多导：空文本这一处另走一遍文件那条道，判定规则 3 的两种成因各配一条用例。

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 前置条件 | 输入 | 预期结果 | 判据落在哪一层 |
|:---|:---|:---|:---|:---|:---|:---|:---|
| TC-1 | text_ascii_tokens_and_chars | 验证用命令行直接交一段纯 ASCII 文本时两行数报得对 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位 | 用 ENV-5 那个解释器把脚本调起来：`<技能目录>/scripts/count_tokens.py --text "DeepSeek tokenizer counts exactly."` | 标准输出恰好两行：`tokens: 8` 与 `chars: 34`；退出码 0 | 落在输出上 |
| TC-2 | file_markdown_path_counts | 验证给一个存在的 UTF-8 文件路径时两行数报得对 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-4 把那份样本摆成当前目录下的 `sample.md` | `<技能目录>/scripts/count_tokens.py ./sample.md` | 标准输出恰好两行：`tokens: 13` 与 `chars: 25`；退出码 0 | 落在输出上 |
| TC-3 | stdin_pipe_counts | 验证走管道那条道时两行数报得对 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-6 备好那两行文本 | 把 DATA-6 那两行连着中间那个换行用管道喂给脚本，命令行上不给文件、也不给 `--text`：`<技能目录>/scripts/count_tokens.py` | 标准输出恰好两行：`tokens: 8` 与 `chars: 16`；退出码 0 | 落在输出上 |
| TC-4 | chinese_text_counts | 验证纯中文文本照常数得出数 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-1 第 2 段备好那段文本 | `<技能目录>/scripts/count_tokens.py --text "你好，世界。这是一段中文文本。"` | 标准输出恰好两行：`tokens: 9` 与 `chars: 15`；退出码 0 | 落在输出上 |
| TC-5 | spec_semantics_not_compat_path | 验证词表是按规范语义加载的，没走那条会把中文开头编成空序列的兼容路径 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-1 第 4 段备好那段以中文开头、中间带一个空格的文本 | `<技能目录>/scripts/count_tokens.py --text "中文 开头"` | 标准输出恰好两行：`tokens: 3` 与 `chars: 5`；退出码 0。token 数不是 0——兼容路径会把这一段编成空序列、数出 0 来 | 落在输出上 |
| TC-6 | mixed_text_with_spaces_and_newlines | 验证中英混排、含空格与换行的文本两行数报得对 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-1 第 3 段备好那两行文本 | `<技能目录>/scripts/count_tokens.py --text "<DATA-1 第 3 段原样，含中间那个换行>"` | 标准输出恰好两行：`tokens: 18` 与 `chars: 39`；退出码 0 | 落在输出上 |
| TC-7 | special_token_literal_counts | 验证文本里那个特殊 token 的字面形按官方词表计入，不转义、不拆开、不剥离 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-3 备好那段文本 | `<技能目录>/scripts/count_tokens.py --text "请数这段：<｜end▁of▁sentence｜>"` | 标准输出恰好两行：`tokens: 5` 与 `chars: 24`；退出码 0。那个字面形单独占 1 个 token——把 `请数这段：` 单独数一次是 4 个 token，两个数之差正是它 | 落在输出上 |
| TC-8 | empty_text_zero | 验证一个字符都没有的空文本报 0 与 0 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-2 备好那个显式的空串 | `<技能目录>/scripts/count_tokens.py --text ""` | 标准输出恰好两行：`tokens: 0` 与 `chars: 0`；退出码 0。既不是报错收场，也不是一行都不打 | 落在输出上 |
| TC-9 | bom_complete_counts | 验证开头那 3 个字节的完整字节顺序标记被剥掉，不进两样数 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-7 摆出当前目录下的 `bom-complete.txt` | `<技能目录>/scripts/count_tokens.py ./bom-complete.txt` | 标准输出恰好两行：`tokens: 7` 与 `chars: 12`；退出码 0。字符数按剥掉那 3 个字节之后的正文算 | 落在输出上 |
| TC-10 | bom_plus_one_byte_counts | 验证标记后面紧跟的那一个字节按正文算，只剥标记那 3 个字节 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-8 摆出当前目录下的 `bom-plus-one.txt` | `<技能目录>/scripts/count_tokens.py ./bom-plus-one.txt` | 标准输出恰好两行：`tokens: 8` 与 `chars: 13`；退出码 0 | 落在输出上 |
| TC-11 | one_char_text_counts | 验证只有一个字符的文本报出 1 与 1 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-1 第 5 段备好那个单字符 | `<技能目录>/scripts/count_tokens.py --text "a"` | 标准输出恰好两行：`tokens: 1` 与 `chars: 1`；退出码 0 | 落在输出上 |
| TC-12 | four_byte_char_counts | 验证一个占 4 个字节的字符按 1 个字符算 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-1 第 6 段备好那个字符 | `<技能目录>/scripts/count_tokens.py --text "😀"` | 标准输出恰好两行：`tokens: 2` 与 `chars: 1`；退出码 0。`chars` 数的是字符个数，那一个字符在 UTF-8 里占 4 个字节 | 落在输出上 |
| TC-13 | empty_file_zero | 验证一个 0 字节的文件报 0 与 0 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-5 摆出当前目录下的 `empty.txt` | `<技能目录>/scripts/count_tokens.py ./empty.txt` | 标准输出恰好两行：`tokens: 0` 与 `chars: 0`；退出码 0 | 落在输出上 |
| TC-14 | missing_file_path | 验证路径不存在时照实收场，不报出一个数 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-9 确认当前目录下 `no-such-file.md` 不存在 | `<技能目录>/scripts/count_tokens.py ./no-such-file.md` | 依据未规定这一处。记下现状：退出码非零；标准输出里一行都不打——既不报 token 数，也不拿别的数顶上 | 落在输出上 |
| TC-15 | path_is_directory | 验证路径指向一个目录时照实收场，不报出一个数 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-9 在当前目录下建出 `a-directory/` | `<技能目录>/scripts/count_tokens.py ./a-directory` | 依据未规定这一处。记下现状：退出码非零；标准输出里一行都不打，不报出 token 数 | 落在输出上 |
| TC-16 | file_not_utf8 | 验证文件不是合法 UTF-8 字节时照实收场，不报出一个数 | 高 | ENV-1、ENV-2、ENV-4、ENV-5 就位；按 DATA-10 摆出当前目录下的 `gbk-sample.txt` | `<技能目录>/scripts/count_tokens.py ./gbk-sample.txt` | 依据未规定这一处。记下现状：退出码非零；标准输出里一行都不打，标准错误里有一条说明这个文件不是合法 UTF-8；不报出 token 数 | 落在输出上 |
| TC-17 | engine_present_installs_nothing | 验证引擎已在位时一个字节都不装 | 高 | ENV-5 就位（那个解释器里引擎已在位）；按 DATA-1 第 1 段备好那段文本 | 用 ENV-5 那个解释器把脚本调起来：`<技能目录>/scripts/count_tokens.py --text "DeepSeek tokenizer counts exactly."` | 标准输出恰好两行：`tokens: 8` 与 `chars: 34`；退出码 0；标准错误里一条安装提示都没有 | 落在输出上 |
| TC-18 | fresh_env_installs_bundled_wheel | 验证目标机上没装引擎时先离线装上随技能打包的那份 | 高 | 按 ENV-6 现建一个没装引擎的解释器；ENV-4 那两份东西在技能目录里 | 用那个解释器把技能目录下的脚本调起来：`<技能目录>/scripts/count_tokens.py --text "abc"` | 标准错误里先出现一句正在装上随技能打包那份的提示；随后标准输出报出 `tokens: 1` 与 `chars: 3`，退出码 0。全程不联网——把包索引关掉照样成 | 落在输出上 |
| TC-19 | unusable_wheel_falls_back_to_index | 验证打包那份装不上时改走包索引那条道 | 高 | 按 ENV-6 现建一个没装引擎的解释器；按 ENV-7 摆出一份技能副本，它的 `wheels/` 下只有 DATA-12 那份装不上的包；ENV-10 就位 | 用那个解释器把那份副本里的脚本调起来：`<副本目录>/scripts/count_tokens.py --text "abc"` | 标准错误里先出现一句正在装上随技能打包那份的提示、紧接着一句正在从包索引装钉住版本的提示；随后标准输出报出 `tokens: 1` 与 `chars: 3`，退出码 0 | 落在输出上 |
| TC-20 | no_wheel_falls_back_to_index | 验证打包那份不在时直接走包索引那条道 | 高 | 按 ENV-6 现建一个没装引擎的解释器；按 ENV-7 摆出另一份技能副本，它的 `wheels/` 是空的；ENV-10 就位 | 用那个解释器把那份副本里的脚本调起来：`<副本目录>/scripts/count_tokens.py --text "abc"` | 标准错误里只出现一句正在从包索引装钉住版本的提示——不出现装上打包那份那句；随后标准输出报出 `tokens: 1` 与 `chars: 3`，退出码 0 | 落在输出上 |
| TC-21 | counting_request_main_scenario | 验证一句请求整条道走完：技能定位到脚本目录、用绝对路径把它调起来、把那段文本原样交过去、把数报回 | 高 | ENV-9 按 ENV-8 起的空工作区，技能已装在工作区里；ENV-1、ENV-2、ENV-5 就位 | 按 DATA-1 第 1 段备好那段文本，向技能说一句：「帮我数一下这段话的 token：DeepSeek tokenizer counts exactly.」 | 答话里报出 `tokens: 8`；执行过程里技能真把脚本调起来跑了一遍，交给它的是那段原样的文本（没改写、没截断）；没有绕开脚本另找一个数顶上 | 要读执行过程 |
| TC-22 | naming_other_model | 验证点名别的模型时明说不覆盖、一个数都不给 | 高 | 同 TC-21 那份工作区与那几项环境 | 向技能说一句：「这段话用 Claude 算是多少 token：DeepSeek tokenizer counts exactly.」 | 答话里说明本技能只覆盖 DeepSeek 当前官方词表、不覆盖 Claude；没有给出任何形式、任何精度的 token 数或估算值；执行过程里没有绕开本技能另去找一个数顶上 | 要读执行过程 |
| TC-23 | asks_api_cost | 验证问调用成本时把两处口径点明 | 高 | 同 TC-21 那份工作区与那几项环境 | 向技能说一句：「这段话调 DeepSeek 接口大概花多少 token、多少预算？DeepSeek tokenizer counts exactly.」 | 答话里报出 `tokens: 8`；点明离线算不出缓存命中；点明计费以接口返回的用量为准 | 落在输出上 |
| TC-24 | tokens_only_request | 验证只要 token 量时答话里给出那个数 | 高 | 同 TC-21 那份工作区与那几项环境 | 向技能说一句：「这段话有多少 token？DeepSeek tokenizer counts exactly.」 | 答话里给出 `8` 这个 token 数 | 落在输出上 |
| TC-25 | full_dialogue_assembled_first | 验证要估一次完整对话请求时先把请求拼装起来再计数 | 高 | 同 TC-21 那份工作区与那几项环境；按 DATA-11 备好那段消息 | 向技能说一句：「把下面这段用户消息当成一次完整的对话请求来估，一共多少 token：请用一句话说明 DeepSeek 的 tokenizer 是离线可用的。」 | 执行过程里技能没有把那段正文原样交给脚本数完就当成了整次请求的用量——它先按对话模板把这一段拼装起来（补上角色标记与特殊 token 那一层）再交给脚本数，答话里报的是拼装后那一份的数 | 要读执行过程 |
| TC-26 | special_token_passed_through | 验证含特殊 token 字面形的那段文本原样交给脚本，不转义、不拆开、不剥离 | 中 | 同 TC-21 那份工作区与那几项环境；按 DATA-3 备好那段文本 | 向技能说一句：「帮我数一下这段的 token：请数这段：<｜end▁of▁sentence｜>」 | 执行过程里交给脚本的是原样的那段文本，那个字面形没有被转义、没有被拆开、也没有被剥掉；答话里报出 `tokens: 5` | 要读执行过程 |
| TC-27 | first_run_installs_then_counts | 验证目标机上没装引擎时先装上随技能打包的那份、再把数报回 | 高 | 按 ENV-6 现建一个没装引擎的解释器，被测那侧用的就是它；ENV-9 按 ENV-8 起的空工作区，技能已装在工作区里 | 向技能说一句：「帮我数一下这段的 token：DeepSeek tokenizer counts exactly.」 | 执行过程里看得到技能先装上了随技能打包的那一份（标准错误里那条提示）；随后答话里报出 `tokens: 8` | 要读执行过程 |
| TC-28 | dead_end_route_reported | 验证输入走不通时照实说、不报出一个数 | 中 | 同 TC-21 那份工作区与那几项环境；按 DATA-9 确认工作区里 `no-such-file.md` 不存在 | 向技能说一句：「帮我数一下 no-such-file.md 的 token」 | 答话里照实说明这个输入数不了；没有报出任何 token 数，也没有拿别的数顶上 | 落在输出上 |

## 覆盖项 ↔ 用例对应表

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 有效：在命令行上用 `--text` 直接给一段文本这条调用方式 | TC-1 |
| TCOV-2 | 有效：给一个存在的 UTF-8 文本文件的路径 | TC-2 |
| TCOV-3 | 有效：把要数的内容用管道从标准输入喂进来 | TC-3 |
| TCOV-4 | 无效：给的文件路径不存在 | TC-14 |
| TCOV-5 | 无效：给的路径指向一个目录 | TC-15 |
| TCOV-6 | 无效：文件在，但不是合法的 UTF-8 字节 | TC-16 |
| TCOV-7 | 有效：纯 ASCII 文本 | TC-1 |
| TCOV-8 | 有效：纯中文文本 | TC-4 |
| TCOV-9 | 有效：中英混排、含空格与换行的文本 | TC-6 |
| TCOV-10 | 有效：一个字符都没有的空文本 | TC-8、TC-13 |
| TCOV-11 | 有效：开头带一个完整字节顺序标记的文本 | TC-9 |
| TCOV-12 | 特殊：含 DeepSeek 特殊 token 字面形的文本 | TC-7 |
| TCOV-13 | 有效：按随技能分发那份词表的规范语义加载它 | TC-1、TC-4、TC-6 |
| TCOV-14 | 无效功能：改用另一条兼容加载路径读同一份词表 | TC-5 |
| TCOV-15 | 有效：报出 token 数与 UTF-8 字符数两行 | TC-1、TC-2、TC-3 |
| TCOV-16 | 有效：用户只要 token 量时，答话里报出 token 数 | TC-24 |
| TCOV-17 | 有效：用户问调用成本时，点明离线算不出缓存命中、计费以接口返回的用量为准 | TC-23 |
| TCOV-18 | 有效：用户点名别的模型时，说明本技能不覆盖那个模型、不给近似数 | TC-22 |
| TCOV-19 | 无效功能：绕开本技能另去找一个数顶上，给出别的模型的近似 token 数 | TC-22 |
| TCOV-20 | 有效：要估一次完整对话请求时，先按对话模板把请求拼装起来再计数 | TC-25 |
| TCOV-21 | 字符个数＝0——有序集甲的下边界上的值 | TC-8、TC-13 |
| TCOV-22 | 字符个数＝1——有序集甲的下边界外一个增量距离 | TC-11 |
| TCOV-23 | 一个字符占 1 个字节——有序集乙的下边界上的值 | TC-1、TC-11 |
| TCOV-24 | 一个字符占 0 个字节——有序集乙的下边界外一个增量距离 | 不可行：UTF-8 里最短的字符也占 1 个字节，占 0 个字节的字符造不出来，这一条无法被执行 |
| TCOV-25 | 一个字符占 4 个字节——有序集乙的上边界上的值 | TC-12 |
| TCOV-26 | 一个字符占 5 个字节——有序集乙的上边界外一个增量距离 | 不可行：UTF-8 里最长的字符占 4 个字节，占 5 个字节的字符造不出来，这一条无法被执行 |
| TCOV-27 | 文本开头属于字节顺序标记的字节数＝3，恰好是一个完整标记 | TC-9 |
| TCOV-28 | 文本开头属于字节顺序标记的字节数＝4，完整标记后面还接了一个字节 | TC-10 |
| TCOV-29 | 判定规则 1：C1＝T，用现成的引擎，一个字节都不装 | TC-17 |
| TCOV-30 | 判定规则 2：C1＝F、C2＝T、C3＝T，离线装上随技能打包的那份 | TC-18、TC-27 |
| TCOV-31 | 判定规则 3：C1＝F、C2＝T、C3＝F，打包那份装不上，改从包索引联网装钉住的版本 | TC-19 |
| TCOV-32 | 判定规则 4：C1＝F、C2＝F，打包那份不在，直接走联网那条道 | TC-20 |
| TCOV-33 | 主场景：一次计数请求走完 | TC-21 |
| TCOV-34 | 备选场景：点名的是别的模型 | TC-22 |
| TCOV-35 | 备选场景：问的是调用成本 | TC-23 |
| TCOV-36 | 备选场景：文本要喂进一次完整对话请求 | TC-25 |
| TCOV-37 | 备选场景：目标机是干净的、没装引擎 | TC-27 |
| TCOV-38 | 备选场景：用户只要 token 量 | TC-24 |
| TCOV-39 | 备选场景：文本里含特殊 token 的字面形 | TC-26 |
| TCOV-40 | 备选场景：用户给的输入走不通 | TC-28 |

## 覆盖率自检

| 技术（档位） | 覆盖项编号 | 覆盖项总数 T | 已被用例覆盖 N | 覆盖率 N÷T | 完成准则要求 |
|:---|:---|:---|:---|:---|:---|
| 等价类划分 | TCOV-1～TCOV-20 | 20 | 20 | 20÷20＝100% | 100% |
| 边界值分析（二值边界测试） | TCOV-21、TCOV-22、TCOV-23、TCOV-25、TCOV-27、TCOV-28 | 6 | 6 | 6÷6＝100% | 100% |
| 判定表测试 | TCOV-29～TCOV-32 | 4 | 4 | 4÷4＝100% | 100% |
| 场景测试 | TCOV-33～TCOV-40 | 8 | 8 | 8÷8＝100% | 100% |

四门的 T 都拿本门技术的算式核过：等价类划分数的是等价类的条数，清单里 20 条；边界值分析数的是边界值的条数，二值边界下甲 2 条、乙 4 条、丙 2 条共 8 条，减掉两条不可行的余 6 条；判定表测试数的是可行判定规则的条数，4 条；场景测试数的是主场景加备选场景的条数，1 加 7 共 8 条。TCOV-24 与 TCOV-26 已从分母里剔除，不出现在上表「覆盖项编号」那一栏里。

## 成品落点

| 成品 | 落的是哪些条目 |
|:---|:---|
| `evals/token-counter-round6/cases/` | 运行一与运行二落成的 8 条评测用例配置：TC-21 至 TC-28，连同 TM-4、TCOV-16 至 TCOV-20、TCOV-30、TCOV-33 至 TCOV-40、TP-5 至 TP-7，以及取用的 DATA-1、DATA-3、DATA-9、DATA-11 与 ENV-1 至 ENV-6、ENV-8、ENV-9 |

批次那一层那两份配置文件的名字是测评方案自己的约定，通用稿里不点名；它们落在哪儿，见实施方案规格说明那一份。

判据落在命令、退出码与盘上文件上的那一批（TC-1 至 TC-20，连同 TM-1 至 TM-3、TCOV-1 至 TCOV-15、TCOV-21 至 TCOV-23、TCOV-25、TCOV-27 至 TCOV-29、TCOV-31、TCOV-32、TP-1 至 TP-4、DATA-2、DATA-4 至 DATA-8、DATA-10、DATA-12、ENV-7、ENV-10）还没落成：它们落成能跑的测试代码，落点在 `tests/token-counter/test_count_tokens_round6.py`，这一批还没写那一份。
