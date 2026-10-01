# 测试用例规格说明

分五块写：测试覆盖项、测试用例、覆盖项与用例的对应表、覆盖率自检、成品落点。

## 测试覆盖项

对 TM-1、TM-2、TM-3、TM-4 四个模型套用各自的技术，导出下面这些覆盖项。风险等级照第 0 步判下来的两档写。

| 唯一标识符 | 英文名 | 描述 | 风险等级 | 可追溯性 |
|:---|:---|:---|:---|:---|
| TCOV-1 | text_argument_route | 命令行上直接给一段文本这条调用方式（PART-1） | 高 | TM-1 的 PART-1 |
| TCOV-2 | file_path_route | 给一个存在的 UTF-8 文本文件路径这条调用方式（PART-2） | 高 | TM-1 的 PART-2 |
| TCOV-3 | stdin_route | 把内容用管道从标准输入喂进来这条调用方式（PART-3） | 高 | TM-1 的 PART-3 |
| TCOV-4 | no_route_given | 三条调用方式一条都没给（PART-4） | 高 | TM-1 的 PART-4 |
| TCOV-5 | file_missing | 给的文件路径不存在（PART-5） | 高 | TM-1 的 PART-5 |
| TCOV-6 | path_is_directory | 给的路径指向一个目录（PART-6） | 高 | TM-1 的 PART-6 |
| TCOV-7 | file_not_utf8 | 文件存在，但不是 UTF-8 文本（PART-7） | 高 | TM-1 的 PART-7 |
| TCOV-8 | ascii_text | 纯 ASCII 文本（PART-8） | 中 | TM-1 的 PART-8 |
| TCOV-9 | chinese_text | 含中文的文本（PART-9） | 中 | TM-1 的 PART-9 |
| TCOV-10 | mixed_text_with_newlines | 中英混排、含空格与换行的文本（PART-10） | 中 | TM-1 的 PART-10 |
| TCOV-11 | empty_text | 0 个字符的空文本（PART-11） | 高 | TM-1 的 PART-11 |
| TCOV-12 | file_leading_bom | 文件开头带字节顺序标记，那 3 个字节不计入两样数（PART-12） | 高 | TM-1 的 PART-12 |
| TCOV-13 | special_token_literal | 含特殊 token 字面形的文本（PART-13） | 中 | TM-1 的 PART-13 |
| TCOV-14 | spec_semantics_load | 按官方词表的规范语义加载随技能分发的那份词表（PART-14） | 中 | TM-1 的 PART-14 |
| TCOV-15 | compat_loader_avoided | 不得改用另一条兼容加载路径读同一份词表（PART-15，无效功能） | 中 | TM-1 的 PART-15 |
| TCOV-16 | both_counts_reported | 报出 token 数与 UTF-8 字符数两样（PART-16） | 中 | TM-1 的 PART-16 |
| TCOV-17 | tokens_only_answer | 用户只要 token 量时报出 token 数（PART-17；多报一样字符数不算没做到） | 中 | TM-1 的 PART-17 |
| TCOV-18 | cache_hit_caveat | 用户问调用成本时点明离线算不出缓存命中、计费以接口返回的用量为准（PART-18） | 中 | TM-1 的 PART-18 |
| TCOV-19 | other_model_disclaimed | 用户点名别的模型时明确说明不覆盖（PART-19） | 中 | TM-1 的 PART-19 |
| TCOV-20 | no_approximation | 不得给出别的模型的近似 token 数（PART-20，无效功能） | 中 | TM-1 的 PART-20 |
| TCOV-21 | full_dialogue_assembled | 要估完整对话请求时先按对话模板拼装再计数（PART-21） | 中 | TM-1 的 PART-21 |
| TCOV-22 | char_count_zero | 交过去的文本字符个数 = 0（有序集甲的下边界上的值） | 高 | TM-2 的有序集甲 |
| TCOV-23 | char_count_one | 交过去的文本字符个数 = 1（有序集甲的下边界外一个增量距离的值） | 高 | TM-2 的有序集甲 |
| TCOV-24 | leading_marker_three_bytes | 文件开头正好 3 个字节、构成一个完整的字节顺序标记（有序集丙的上边界上的值） | 高 | TM-2 的有序集丙 |
| TCOV-25 | leading_two_bytes | 文件开头 2 个字节、凑不满一个标记（有序集丙的上边界外一个增量距离的值） | 高 | TM-2 的有序集丙 |
| TCOV-26 | char_width_one_byte | 一个字符在 UTF-8 里占 1 个字节（有序集乙的下边界上的值） | 高 | TM-2 的有序集乙 |
| TCOV-27 | char_width_four_bytes | 一个字符在 UTF-8 里占 4 个字节（有序集乙的上边界上的值） | 高 | TM-2 的有序集乙 |
| TCOV-28 | char_width_zero_bytes | 一个字符在 UTF-8 里占 0 个字节（有序集乙的下边界外一个增量距离的值）——不可行 | 高 | TM-2 的有序集乙 |
| TCOV-29 | char_width_five_bytes | 一个字符在 UTF-8 里占 5 个字节（有序集乙的上边界外一个增量距离的值）——不可行 | 高 | TM-2 的有序集乙 |
| TCOV-30 | engine_already_importable | 判定规则 1：目标解释器里已经能导入那份引擎——直接用现成的，一个字节都不装 | 高 | TM-3 的规则 1 |
| TCOV-31 | bundled_wheel_installed | 判定规则 2：没有引擎、随技能打包的那份装得上——先装上打包的那份，全程不联网 | 高 | TM-3 的规则 2 |
| TCOV-32 | pinned_version_from_index | 判定规则 3：没有引擎、打包的那份装不上——改从包索引联网装钉住的版本 | 高 | TM-3 的规则 3 |
| TCOV-33 | scenario_counting_request | 主场景：一次计数请求走完 | 中 | TM-4 的「一次计数请求走完」 |
| TCOV-34 | scenario_other_model | 备选场景：点名的是别的模型，序列在读到那一条规矩处分岔 | 中 | TM-4 的「点名的是别的模型」 |
| TCOV-35 | scenario_cost_question | 备选场景：问的是调用成本，报数之外多点明一句 | 中 | TM-4 的「问的是调用成本」 |
| TCOV-36 | scenario_full_dialogue | 备选场景：文本要喂进完整对话请求，交过去之前先拼装 | 中 | TM-4 的「文本要喂进完整对话请求」 |
| TCOV-37 | scenario_first_run | 备选场景：目标机是干净的、没装引擎，脚本先装上再计数 | 高 | TM-4 的「目标机是干净的、没装引擎」 |
| TCOV-38 | scenario_tokens_only | 备选场景：用户只要 token 量，只把 token 数报回 | 中 | TM-4 的「用户只要 token 量」 |
| TCOV-39 | scenario_special_token | 备选场景：文本里含特殊 token 的字面形，原样交过去 | 中 | TM-4 的「文本里含特殊 token 的字面形」 |
| TCOV-40 | scenario_no_countable_input | 备选场景：用户那侧没给出可数的东西，只把这件事照实说回 | 高 | TM-4 的「用户给的输入走不通」 |

**TCOV-28 与 TCOV-29 判为不可行，已从分母里剔除**，原因写在这一栏里：

- TCOV-28 要有「一个占 0 个字节的字符」。UTF-8 编码里任何一个字符都至少占 1 个字节，不存在这样的字符，也就造不出执行它的输入。
- TCOV-29 要有「一个占 5 个字节的字符」。UTF-8 最宽的一个字符占 4 个字节（补充平面的那些），5 个字节的情形编码里没有，同样造不出输入。

两条不可行的都是「这个数据类型自身容不下这个值」，不是被测那边做不到。剔除的是这两条覆盖项，不是这一门技术——边界值分析这一门其余 6 条照旧全部覆盖。

## 测试用例

一条用例一行。交过去的东西按调用方式写：脚本那一批把命令行原样写出来，模型那一批把用户会说的那句话原样写出来。

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 前置条件 | 输入 | 预期结果 | 判据落在哪一层 |
|:---|:---|:---|:---|:---|:---|:---|:---|
| TC-1 | text_ascii_both_counts | 验证命令行上直接给一段纯 ASCII 文本时两行数都报对，且全程没有触发安装 | 高 | ENV-1、ENV-2 就位；ENV-8 那个解释器里引擎已在位；ENV-4 的词表与打包的引擎包随技能目录在位；按 DATA-1 第 1 段备好那段文本 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py --text "DeepSeek tokenizer counts exactly."`——引号里就是 DATA-1 第 1 段的原文 | 退出码 0；标准输出两行，先 `tokens: 8`、后 `chars: 34`；标准错误里一个字节都不出现——一旦出现装引擎那两句话里任何一句，这条就没做到 | 落在输出上 |
| TC-2 | file_markdown_both_counts | 验证给一个存在的 UTF-8 文本文件路径时走的是文件那条道，报出的数按文件内容算 | 高 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-4 把那份文件摆在当前目录下的 `sample.md` | 命令行原样是：`python <技能目录>/scripts/count_tokens.py sample.md`——`sample.md` 就是按 DATA-4 摆出来的那份文件 | 退出码 0；标准输出两行 `tokens: 13`、`chars: 25`——这两个数是那份文件的内容在官方词表与 UTF-8 口径下的值，不是那个路径字符串的值 | 落在输出上 |
| TC-3 | stdin_route_both_counts | 验证把内容用管道从标准输入喂进来时走的是标准输入那条道，不是文件那条道 | 高 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-5 备好那段正文 | 命令行原样是：`printf '第一行 stdin\n第二行 管道' \| python <技能目录>/scripts/count_tokens.py`——那段正文照原样喂进标准输入，不作为参数传 | 退出码 0；标准输出两行 `tokens: 8`、`chars: 16` | 落在输出上 |
| TC-4 | file_missing | 验证路径不存在时不报出一个数 | 高 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-6 第 1 样确认那个文件路径在当前目录下仍然不存在 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py no-such-file.md`——路径名取自 DATA-6 第 1 样 | 标准输出里 `tokens:` 那一行不出现、`chars:` 那一行也不出现；退出码非 0。标准错误里具体说什么由实现定，照实记下；判据只到这一步：不报出一个数 | 落在输出上 |
| TC-5 | path_is_directory | 验证路径指向目录时不报出一个数 | 高 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-6 第 2 样在当前目录下建出那个目录 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py a-directory`——路径取的就是 DATA-6 第 2 样建出来的那个目录 | 标准输出里 `tokens:` 那一行不出现、`chars:` 那一行也不出现；退出码非 0。标准错误里具体说什么由实现定，照实记下；判据只到这一步：不报出一个数 | 落在输出上 |
| TC-6 | file_not_utf8 | 验证内容不是 UTF-8 时以非零退出码收场，并且说清是这一件事 | 高 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-6 第 3 样的字节在当前目录下写出那份文件 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py gbk-sample.txt`——那份文件的字节取自 DATA-6 第 3 样 | 标准输出一行都不出现——`tokens:` 与 `chars:` 都不打；标准错误里出现 `not valid UTF-8:` 这几个字，后面跟着那个文件名；退出码非 0 | 落在输出上 |
| TC-7 | text_empty_zero_chars | 验证 0 个字符的空文本报出 0 而不是报错或跳过 | 高 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-2 备好那个空文本 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py --text ""`——引号里什么都不写，交过去的就是 DATA-2 那个 0 个字符的文本 | 退出码 0；标准输出两行 `tokens: 0`、`chars: 0`；不报错、不跳过不答 | 落在输出上 |
| TC-8 | file_leading_bom_stripped | 验证文件开头那 3 个字节的字节顺序标记被剥掉，两样数都不把它算进去 | 高 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-7 的字节在当前目录下写出那份文件 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py bom-sample.txt`——那份文件开头 3 个字节是 `EF BB BF`，字节取自 DATA-7 | 退出码 0；标准输出两行 `tokens: 7`、`chars: 12`——12 是剥掉标记之后正文的字符数；标记那 3 个字节既不算字符，也不算进 token 数 | 落在输出上 |
| TC-9 | text_special_token_literal | 验证文本里含特殊 token 的字面形时按官方词表把它计入 | 中 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-3 备好那段文本 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py --text "请数这段：<｜end▁of▁sentence｜>"`——引号里就是 DATA-3 的原文，那个字面形照原样交过去 | 退出码 0；标准输出两行 `tokens: 5`、`chars: 24`——那个字面形在官方词表里是一个特殊 token，数出来算一个，不是按它的字符数另算 | 落在输出上 |
| TC-10 | cjk_leading_spec_semantics | 验证纯中文开头的文本数出来的 token 数不为 0，也就是走的是规范语义那条加载路径 | 中 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-1 第 2 段备好那段文本 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py --text "你好，世界。这是一段中文文本。"`——引号里就是 DATA-1 第 2 段的原文 | 退出码 0；标准输出两行 `tokens: 9`、`chars: 15`；token 数不是 0——改用另一条兼容加载路径读这份词表时，纯中文开头的文本会被编成空序列，数出来正是 0 | 落在输出上 |
| TC-11 | text_single_ascii_char | 验证只有一个 ASCII 字符的文本，两行都报 1 | 高 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-1 第 4 段备好那一个字符 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py --text "a"`——引号里就是 DATA-1 第 4 段那一个 ASCII 字符 | 退出码 0；标准输出两行 `tokens: 1`、`chars: 1` | 落在输出上 |
| TC-12 | file_starts_with_two_byte_char | 验证文件开头那一段只有 2 个字节、凑不满一个标记时照常解成一个字符，不误剥前缀 | 高 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-8 的字节在当前目录下写出那份文件 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py two-byte-sample.txt`——那份文件开头 2 个字节是一个两字节宽度的字符，字节取自 DATA-8 | 退出码 0；标准输出两行 `tokens: 8`、`chars: 12`——开头那 2 个字节被当成一个字符解码出来，没有被当成半截标记剥掉 | 落在输出上 |
| TC-13 | text_leading_four_byte_char | 验证一个字符占 4 个字节时字符数按字符算，不按字节算 | 高 | ENV-1、ENV-2、ENV-8、ENV-4 就位；按 DATA-9 备好那段文本 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py --text "😀 这个字符占四个字节。"`——引号里就是 DATA-9 的原文 | 退出码 0；标准输出两行 `tokens: 9`、`chars: 12`——`chars:` 报的是 12（这段文本 12 个字符），不是按字节算出来的 35；那一个四字节字符算 1 个字符 | 落在输出上 |
| TC-14 | engine_already_present | 验证引擎已在位时一个字节都不装，直接出数 | 高 | ENV-1、ENV-2 就位；ENV-8 那个解释器里引擎已在位；ENV-4 在位；按 DATA-1 第 4 段备好那一个字符 | 命令行原样是：`python <技能目录>/scripts/count_tokens.py --text "a"` | 退出码 0；标准输出两行 `tokens: 1`、`chars: 1`；标准错误里一个字节都不出现——既没有装打包那份的那句话，也没有从包索引装的那句话 | 落在输出上 |
| TC-15 | first_run_installs_bundled_wheel | 验证目标机是干净的、没装引擎时先装上随技能打包的那一份，再照常出数 | 高 | ENV-1、ENV-2 就位；ENV-5 那个解释器里确认没有装引擎；ENV-4 在位；按 DATA-1 第 1 段备好那段文本 | 命令行原样是：`"<ENV-5 那个解释器的可执行文件>" <技能目录>/scripts/count_tokens.py --text "DeepSeek tokenizer counts exactly."`——用 ENV-5 那个解释器跑，不是 ENV-8 那个 | 退出码 0；标准错误里出现 `Installing bundled tokenizers wheel (offline) ...` 这一句，且不出现从包索引装的那一句；标准输出两行 `tokens: 8`、`chars: 34`；装完之后照常计数，不需要再跑一遍；此后 ENV-5 那个解释器里能导入引擎 | 落在输出上 |
| TC-16 | wheel_unusable_network_fallback | 验证打包的那份装不上时改从包索引联网装钉住的版本 | 高 | ENV-1、ENV-2、ENV-6 就位——那个解释器里没有引擎，那份技能副本的 `wheels/` 是空目录；ENV-9 那条联网道走得通；按 DATA-1 第 1 段备好那段文本 | 命令行原样是：`"<ENV-6 那个解释器的可执行文件>" <ENV-6 那份技能副本>/scripts/count_tokens.py --text "DeepSeek tokenizer counts exactly."` | 退出码 0；标准错误里出现 `Installing tokenizers==0.22.2 from PyPI ...` 这一句——钉住的版本号照原样写出来；标准输出两行 `tokens: 8`、`chars: 34` | 落在输出上 |
| TC-17 | counting_request_main_scenario | 验证一次计数请求从进来到结果报回整个走完，报出来的数拿的是脚本算出来的那一个 | 中 | ENV-1、ENV-2、ENV-3、ENV-4、ENV-8 就位；ENV-7 的工作区已建好，按 DATA-4 把那份文件铺在工作区根下的 `sample.md` | 一句话：「数一下这个文件有多少 token、多少字符：sample.md」——`sample.md` 就是工作区根下按 DATA-4 铺好的那份文件 | 报回的 token 数是 13、字符数是 25；执行过程里看得到技能真把计数脚本调起来跑了一遍（运行记录里有那条脚本命令），报回的两个数就是脚本那两行里的数，不是另找来的 | 要读执行过程 |
| TC-18 | naming_other_model | 验证点名别的模型时明确说明不覆盖，且一个近似数都不给 | 中 | ENV-1、ENV-2、ENV-3、ENV-4、ENV-8 就位；ENV-7 的工作区已建好 | 一句话：「用 Claude 的 tokenizer 算一下这段有多少 token：DeepSeek tokenizer counts exactly.」——冒号后面那段就是 DATA-1 第 1 段的原文，原样接在这句话后面 | 明确说明当前这一套只覆盖 DeepSeek 的官方词表、算不了别的模型；不给近似数、不给估算区间、也不拿别的数顶上 | 落在输出上 |
| TC-19 | asks_api_cost | 验证问调用成本时报出数并点明缓存命中那件事 | 中 | ENV-1、ENV-2、ENV-3、ENV-4、ENV-8 就位；ENV-7 的工作区已建好 | 一句话：「这段调一次 API 大概多少 token、多少预算？DeepSeek tokenizer counts exactly.」——问号后面那段就是 DATA-1 第 1 段的原文，原样接在这句话后面 | 报回 token 数 8；点明离线算不出缓存命中（缓存命中量取决于服务端状态）；说明计费以接口返回的用量为准 | 落在输出上 |
| TC-20 | tokens_only_request | 验证只要 token 量时把 token 数报回 | 中 | ENV-1、ENV-2、ENV-3、ENV-4、ENV-8 就位；ENV-7 的工作区已建好 | 一句话：「这段有多少 token？DeepSeek tokenizer counts exactly.」——问号后面那段就是 DATA-1 第 1 段的原文，原样接在这句话后面 | 报回 token 数 8——顺带报了字符数不算没做到，依据那句「报告 N 即可」是允许，不是只许报 N | 落在输出上 |
| TC-21 | text_for_full_dialogue | 验证用户要把一段文本当成一次完整对话请求来估算时，不把裸文本的数当成整次请求的数报出去 | 中 | ENV-1、ENV-2、ENV-3、ENV-4、ENV-8 就位；ENV-7 的工作区已建好 | 一句话：「我要把这一段当作用户消息发一次请求，帮我估一下这次请求要多少 token：请用一句话说明 DeepSeek 的 tokenizer 是离线可用的。」——冒号后面那段就是 DATA-10 的原文 | 依据未规定这一处，不写成预期的取值——依据说「若估算完整对话请求，需自行按对话模板拼装后再计数」，但没说这句话是说给谁听的，对话模板那份配置也没有随技能分发。照实记下被测那边的实际回应；判据只到这一步：不得把这段裸文本的数当成一次完整请求的数报出去，也不得假称自己已经按对话模板拼好了 | 要读执行过程 |
| TC-22 | dead_end_route_reported | 验证一句请求里没给出可数的东西时照实说回，不凭空报一个数 | 高 | ENV-1、ENV-2、ENV-3、ENV-4、ENV-8 就位；ENV-7 的工作区已建好 | 一句话：「帮我数一下有多少 token」——不给文本、不给文件路径、也不喂标准输入 | 依据未规定这一处，不写成预期的取值——依据只列了三条调用方式，没写一条都不给时算什么。照实记下被测那边的实际回应；判据只到这一步：不得凭空取一段文本算出一个数来，也不得把「多少 token」当成已经知道要数什么 | 要读执行过程 |
| TC-23 | special_token_passed_through | 验证含特殊 token 字面形的文本原样交过去，不转义、不拆开、不剥离 | 中 | ENV-1、ENV-2、ENV-3、ENV-4、ENV-8 就位；ENV-7 的工作区已建好 | 一句话：「这一段里带一个特殊 token，照样帮我数一下有多少 token、多少字符：请数这段：<｜end▁of▁sentence｜>」——最后一个冒号后面就是 DATA-3 的原文，原样接在这句话后面 | 报回的 token 数是 5、字符数是 24；执行过程里看得到交给脚本的是原样的文本——那个字面形没被转义、没被拆开、也没被剥掉 | 要读执行过程 |

## 对应表

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 命令行上直接给一段文本这条调用方式 | TC-1 |
| TCOV-2 | 给一个存在的 UTF-8 文本文件路径这条调用方式 | TC-2、TC-17 |
| TCOV-3 | 把内容用管道从标准输入喂进来这条调用方式 | TC-3 |
| TCOV-4 | 三条调用方式一条都没给 | TC-22 |
| TCOV-5 | 给的文件路径不存在 | TC-4 |
| TCOV-6 | 给的路径指向一个目录 | TC-5 |
| TCOV-7 | 文件存在，但不是 UTF-8 文本 | TC-6 |
| TCOV-8 | 纯 ASCII 文本 | TC-1 |
| TCOV-9 | 含中文的文本 | TC-2 |
| TCOV-10 | 中英混排、含空格与换行的文本 | TC-3 |
| TCOV-11 | 0 个字符的空文本 | TC-7 |
| TCOV-12 | 文件开头带字节顺序标记，那 3 个字节不计入两样数 | TC-8 |
| TCOV-13 | 含特殊 token 字面形的文本 | TC-9 |
| TCOV-14 | 按官方词表的规范语义加载词表 | TC-1、TC-2、TC-3、TC-8、TC-9、TC-10 |
| TCOV-15 | 不得改用另一条兼容加载路径读同一份词表 | TC-10 |
| TCOV-16 | 报出 token 数与 UTF-8 字符数两样 | TC-1、TC-2、TC-3、TC-7、TC-8、TC-9 |
| TCOV-17 | 用户只要 token 量时报出 token 数 | TC-20 |
| TCOV-18 | 用户问调用成本时点明离线算不出缓存命中 | TC-19 |
| TCOV-19 | 用户点名别的模型时明确说明不覆盖 | TC-18 |
| TCOV-20 | 不得给出别的模型的近似 token 数 | TC-18 |
| TCOV-21 | 要估完整对话请求时先按对话模板拼装再计数 | TC-21 |
| TCOV-22 | 交过去的文本字符个数 = 0 | TC-7 |
| TCOV-23 | 交过去的文本字符个数 = 1 | TC-11 |
| TCOV-24 | 文件开头正好 3 个字节、构成一个完整的字节顺序标记 | TC-8 |
| TCOV-25 | 文件开头 2 个字节、凑不满一个标记 | TC-12 |
| TCOV-26 | 一个字符在 UTF-8 里占 1 个字节 | TC-11 |
| TCOV-27 | 一个字符在 UTF-8 里占 4 个字节 | TC-13 |
| TCOV-28 | 一个字符在 UTF-8 里占 0 个字节 | 不可行——UTF-8 里任何一个字符都至少占 1 个字节，造不出这样的字符 |
| TCOV-29 | 一个字符在 UTF-8 里占 5 个字节 | 不可行——UTF-8 最宽的一个字符占 4 个字节，造不出这样的字符 |
| TCOV-30 | 判定规则 1：引擎已在位——直接用现成的，一个字节都不装 | TC-14 |
| TCOV-31 | 判定规则 2：打包的那份装得上——先装上打包的那份，全程不联网 | TC-15 |
| TCOV-32 | 判定规则 3：打包的那份装不上——改从包索引联网装钉住的版本 | TC-16 |
| TCOV-33 | 主场景：一次计数请求走完 | TC-17 |
| TCOV-34 | 备选场景：点名的是别的模型 | TC-18 |
| TCOV-35 | 备选场景：问的是调用成本 | TC-19 |
| TCOV-36 | 备选场景：文本要喂进完整对话请求 | TC-21 |
| TCOV-37 | 备选场景：目标机是干净的、没装引擎 | TC-15 |
| TCOV-38 | 备选场景：用户只要 token 量 | TC-20 |
| TCOV-39 | 备选场景：文本里含特殊 token 的字面形 | TC-23 |
| TCOV-40 | 备选场景：用户那侧没给出可数的东西 | TC-22 |

TCOV-28 与 TCOV-29 那两格写的是「不可行」，不是留空。留空的意思是「这条还欠着用例、要去补」，而那两条不是待补，是已经证明执行不了、从分母里减掉了；两种情形写成一个样子，读的人分不出来。

TCOV-16 那一行三个数、六个用例都报两样，是因为其中 TC-7、TC-8、TC-9 各自还担着别的覆盖项，顺带把这一条也覆盖了。一条用例覆盖多条覆盖项是常见的，不等于漏了哪一条。

## 覆盖率自检

| 技术（档位） | 覆盖项编号 | 覆盖项总数 T | 已被用例覆盖 N | 覆盖率 N÷T | 完成准则要求 |
|:---|:---|:---|:---|:---|:---|
| 等价类划分 | TCOV-1～TCOV-21 | 21 | 21 | 21÷21＝100% | 100% |
| 边界值分析（二值边界） | TCOV-22～TCOV-27 | 6 | 6 | 6÷6＝100% | 100% |
| 判定表测试 | TCOV-30～TCOV-32 | 3 | 3 | 3÷3＝100% | 100% |
| 场景测试 | TCOV-33～TCOV-40 | 8 | 8 | 8÷8＝100% | 100% |

四个分母都拿各门技术的算式核过一遍：

- 等价类划分数的是等价类的条数。TM-1 识别出 21 条，21 条全部可行，得 21，与清单里列出来的一样多。
- 边界值分析数的是边界值的条数，判为不可行的减掉。TM-2 三个有序集按二值边界测试各识别两个覆盖项，共识别 8 条——有序集甲 2 条、乙 4 条、丙 2 条；减去判为不可行的 TCOV-28、TCOV-29 两条，得 6。
- 判定表测试数的是可行判定规则的条数。TM-3 那张表一共 3 列，3 条规则都可行，得 3。
- 场景测试数的是主场景加备选场景的条数。TM-4 是 1 个主场景加 7 个备选场景，得 8。

四门都到了完成准则要求的 100%，对应表里没有留空的格子。

## 成品落点

还没落成。

这批用例按判据落在哪分两处落：判据落在命令、退出码与盘上文件上的那批（TC-1 至 TC-16）落成能跑的测试代码；判据要读一轮模型行为的那批（TC-17 至 TC-23）落成评测用例。两处各自的具体路径、批号与编号在盘上怎么留痕，落成那一步照实施方案规格说明那一份写。
