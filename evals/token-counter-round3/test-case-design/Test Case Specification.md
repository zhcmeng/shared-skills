# 测试用例规格说明

## 测试覆盖项

| 唯一标识符 | 英文名 | 描述 | 风险等级 | 可追溯性 |
|:---|:---|:---|:---|:---|
| TCOV-1 | text_input_path | 有效来路：用 `--text` 直接给一段文本（PART-1） | 中 | TM-1 的 PART-1 |
| TCOV-2 | file_input_path | 有效来路：用一个位置参数给一个文件的路径（PART-2） | 中 | TM-1 的 PART-2 |
| TCOV-3 | stdin_input_path | 有效来路：从标准输入读（PART-3） | 中 | TM-1 的 PART-3 |
| TCOV-4 | no_input_source | 未规定：三种来路都不给、标准输入也为空（PART-4） | 中 | TM-1 的 PART-4 |
| TCOV-5 | utf8_without_bom | 有效取值：不带字节顺序标记的 UTF-8 文件（PART-5） | 中 | TM-1 的 PART-5 |
| TCOV-6 | utf8_with_bom | 有效取值：带字节顺序标记的 UTF-8 文件（PART-6） | 中 | TM-1 的 PART-6 |
| TCOV-7 | non_utf8_bytes | 未规定：文件不是 UTF-8 的字节序列（PART-7） | 中 | TM-1 的 PART-7 |
| TCOV-8 | ascii_text | 有效取值：纯 ASCII 字符的内容（PART-8） | 中 | TM-1 的 PART-8 |
| TCOV-9 | chinese_text | 有效取值：纯中文的内容（PART-9） | 中 | TM-1 的 PART-9 |
| TCOV-10 | astral_chars | 有效取值：含基本平面之外字符的内容（PART-10） | 中 | TM-1 的 PART-10 |
| TCOV-11 | special_token_literal | 有效取值：含 DeepSeek 特殊 token 字面量的内容（PART-11） | 中 | TM-1 的 PART-11 |
| TCOV-12 | whitespace_only | 有效取值：只由空白字符组成的内容（PART-12） | 中 | TM-1 的 PART-12 |
| TCOV-13 | empty_text | 有效取值：零字符的空文本（PART-13） | 中 | TM-1 的 PART-13 |
| TCOV-14 | two_line_output | 有效输出：标准输出打印 `tokens:` 与 `chars:` 两行，两个前缀各在一行的行首（PART-14） | 中 | TM-1 的 PART-14 |
| TCOV-15 | error_output_unspecified | 未规定：不打印这两行时，标准输出与退出码各是什么样（PART-15） | 中 | TM-1 的 PART-15 |
| TCOV-16 | zero_byte_file | 边界值：文件字节数为 0（BVA-1 边界上的取值） | 高 | TM-2 的 BVA-1 |
| TCOV-17 | one_byte_file | 边界值：文件字节数为 1（BVA-1 边界另一侧） | 高 | TM-2 的 BVA-1 |
| TCOV-18 | zero_char_text | 边界值：文本字符数为 0（BVA-2 边界上的取值） | 高 | TM-2 的 BVA-2 |
| TCOV-19 | one_char_text | 边界值：文本字符数为 1（BVA-2 边界另一侧） | 高 | TM-2 的 BVA-2 |
| TCOV-20 | rule_engine_present | 判定规则 R1：解释器里已装引擎，直接跑，不装 | 高 | TM-3 的 R1 |
| TCOV-21 | rule_offline_wheel | 判定规则 R2：没装引擎、随包的 wheel 在且平台相符，离线装打包 wheel | 高 | TM-3 的 R2 |
| TCOV-22 | rule_network_fallback | 判定规则 R3：没装引擎、走不到 wheel 那一步，联网 `pip install tokenizers==0.22.2` | 高 | TM-3 的 R3 |
| TCOV-23 | scenario_main_count | 主场景 S0：用户给出文本或文件路径并问 token 数，技能跑脚本、回话里报出那个数 | 高 | TM-4 的 S0 |
| TCOV-24 | scenario_tokens_only | 场景 S1：用户只问 token 量 | 高 | TM-4 的 S1 |
| TCOV-25 | scenario_other_model | 场景 S2：用户点名别的模型 | 高 | TM-4 的 S2 |
| TCOV-26 | scenario_api_cost | 场景 S3：用户要估算调用成本 | 高 | TM-4 的 S3 |
| TCOV-27 | scenario_special_token | 场景 S4：文本里带特殊标记 | 高 | TM-4 的 S4 |
| TCOV-28 | scenario_full_dialogue | 场景 S5：用户要给一整轮对话估 token | 高 | TM-4 的 S5 |
| TCOV-29 | scenario_undecodable | 场景 S6：输入没法解码 | 高 | TM-4 的 S6 |
| TCOV-30 | scenario_multiple_files | 场景 S7：一次给多个文件问合计 | 高 | TM-4 的 S7 |
| TCOV-31 | scenario_first_run | 场景 S8：首次运行，引擎还没装 | 高 | TM-4 的 S8 |

## 测试用例

一行一条用例：

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 前置条件 | 输入 | 预期结果 | 判据落在哪一层 |
|:---|:---|:---|:---|:---|:---|:---|:---|
| TC-1 | text_input_chinese | 验证 `--text` 这条来路能把一段中文的 token 数与字符数报出来 | 中 | ENV-1、ENV-2、ENV-3 就位；DATA-1 那段正文在手 | 跑 `python <技能目录>/scripts/count_tokens.py --text "你好，世界"` | 标准输出第一行是 `tokens: 3`；第二行是 `chars: 5` | 落在输出上 |
| TC-2 | file_input_utf8 | 验证文件参数这条来路能读一个不带标记的 UTF-8 文件并报数 | 中 | ENV-1、ENV-2、ENV-3 就位；DATA-2 那个文件已按原样放在盘上 | 跑 `python <技能目录>/scripts/count_tokens.py <DATA-2 的路径>` | 标准输出第一行是 `tokens: 3`；第二行是 `chars: 5` | 落在输出上 |
| TC-3 | stdin_input_ascii | 验证管道这条来路能读标准输入并把 ASCII 内容的数报出来 | 中 | ENV-1、ENV-2、ENV-3 就位；DATA-3 那段正文在手 | 跑 `printf '%s' "Hello, world" \| python <技能目录>/scripts/count_tokens.py` | 标准输出第一行是 `tokens: 3`；第二行是 `chars: 12` | 落在输出上 |
| TC-4 | no_input_source | 记下三种来路都不给、标准输入也为空时的实际情况 | 中 | ENV-1、ENV-2、ENV-3 就位 | 不给位置参数、不给 `--text`，把标准输入立刻关掉，跑 `python <技能目录>/scripts/count_tokens.py < /dev/null` | 依据未规定这一处：来路一个都不给时该输出什么、算不算错，依据里一个字没写，所以这一条不写预期的取值——只要求把实际跑出来的标准输出与退出码照实记下，按「未规定功能」记一笔 | 落在输出上 |
| TC-5 | file_with_bom | 验证带字节顺序标记的 UTF-8 文件读得进、按官方词表计数 | 中 | ENV-1、ENV-2、ENV-3 就位；DATA-4 那个文件已按原样放在盘上 | 跑 `python <技能目录>/scripts/count_tokens.py <DATA-4 的路径>` | 脚本不因开头那个标记报错；标准输出第一行是 `tokens: 3`。标记算不算进字符数，依据没写——第二行报出什么照实记下，不当判据（取舍见决策依据） | 落在输出上 |
| TC-6 | file_not_utf8 | 验证文件不是 UTF-8 时脚本不把它当成算出了数 | 中 | ENV-1、ENV-2、ENV-3 就位；DATA-5 那个文件已按原样放在盘上 | 跑 `python <技能目录>/scripts/count_tokens.py <DATA-5 的路径>` | 依据未规定这一处：输入解不了码时该输出什么、算不算错，依据没写，所以不写预期的取值。这一条判的是：脚本把解不了码这件事报了出来，并且报的话里指认了是哪个文件——不打印 `tokens:` 那一行、不拿 0 或者别的数把这一段糊过去 | 落在输出上 |
| TC-7 | text_emoji | 验证含基本平面之外字符的文本按官方词表计数 | 中 | ENV-1、ENV-2、ENV-3 就位 | 跑 `python <技能目录>/scripts/count_tokens.py --text "🚀"` | 标准输出第一行是 `tokens: 2`；第二行是 `chars: 1` | 落在输出上 |
| TC-8 | text_special_token | 验证文本里的 DeepSeek 特殊 token 字面量按官方词表计入 | 中 | ENV-1、ENV-2、ENV-3 就位；DATA-7 那段正文在手 | 跑 `python <技能目录>/scripts/count_tokens.py --text "<｜end▁of▁sentence｜>"` | 标准输出第一行是 `tokens: 1`；第二行是 `chars: 19` | 落在输出上 |
| TC-9 | text_whitespace_only | 验证只由空白字符组成的文本照常计数，不被当成空文本 | 中 | ENV-1、ENV-2、ENV-3 就位；DATA-8 那段正文在手 | 跑 `python <技能目录>/scripts/count_tokens.py --text "   "`（三个空格） | 标准输出第一行是 `tokens: 1`；第二行是 `chars: 3` | 落在输出上 |
| TC-10 | text_empty | 验证零字符的空文本报出 0 与 0，而不是报错 | 高 | ENV-1、ENV-2、ENV-3 就位；DATA-9 那段正文在手 | 跑 `python <技能目录>/scripts/count_tokens.py --text ""` | 标准输出第一行是 `tokens: 0`；第二行是 `chars: 0`；两行都打印出来，脚本不报错 | 落在输出上 |
| TC-11 | file_empty | 验证 0 字节的空文件报出 0 与 0 | 高 | ENV-1、ENV-2、ENV-3 就位；DATA-10 那个文件已按原样放在盘上 | 跑 `python <技能目录>/scripts/count_tokens.py <DATA-10 的路径>` | 标准输出第一行是 `tokens: 0`；第二行是 `chars: 0` | 落在输出上 |
| TC-12 | file_one_byte | 验证 1 字节的文件按官方词表计数 | 高 | ENV-1、ENV-2、ENV-3 就位；DATA-11 那个文件已按原样放在盘上 | 跑 `python <技能目录>/scripts/count_tokens.py <DATA-11 的路径>` | 标准输出第一行是 `tokens: 1`；第二行是 `chars: 1` | 落在输出上 |
| TC-13 | text_one_char | 验证 1 个字符的文本按官方词表计数 | 高 | ENV-1、ENV-2、ENV-3 就位；DATA-12 那段正文在手 | 跑 `python <技能目录>/scripts/count_tokens.py --text "a"` | 标准输出第一行是 `tokens: 1`；第二行是 `chars: 1` | 落在输出上 |
| TC-14 | engine_already_present | 验证解释器里已有引擎时直接跑、不重复安装 | 高 | ENV-4 就位——那个解释器里引擎已装好；DATA-1 那段正文在手 | 用 ENV-4 那个解释器跑 `python <技能目录>/scripts/count_tokens.py --text "你好，世界"` | 标准输出第一行是 `tokens: 3`；第二行是 `chars: 5`；这一次运行没有往标准错误或标准输出里打印任何安装动作的信息 | 落在输出上 |
| TC-15 | engine_offline_wheel | 验证没装引擎、随包 wheel 在时走离线装 wheel 那条路 | 高 | ENV-5 那个干净解释器就位——里面没装引擎；DATA-1 那段正文在手 | 用 ENV-5 那个解释器跑 `python <技能目录>/scripts/count_tokens.py --text "你好，世界"` | 脚本先打印一句说明它正在装随包的引擎（离线），装完之后标准输出第一行是 `tokens: 3`、第二行是 `chars: 5`；这一次运行没有联网去取引擎 | 落在输出上 |
| TC-16 | engine_network_fallback | 验证走不到 wheel 那一步时改走联网兜底那条路 | 高 | ENV-5 那个干净解释器就位；ENV-6 网络出口可用；按 DATA-6 在临时目录摆一份不含 wheel 的测试项副本，DATA-1 那段正文在手 | 用 ENV-5 那个解释器跑 `python <副本目录>/scripts/count_tokens.py --text "你好，世界"` | 脚本先打印一句说明它正在从 PyPI 装 `tokenizers==0.22.2`，装完之后标准输出第一行是 `tokens: 3`、第二行是 `chars: 5` | 落在输出上 |
| TC-17 | scenario_main_count | 验证用户给出文本问 token 数时，技能真去跑脚本并报出那个数 | 高 | ENV-1、ENV-2、ENV-7 就位；技能已装进被测那侧；DATA-1 那段正文在手 | 对被测那侧说：`帮我算一下「你好，世界」这句话有多少 token` | 回话里报出 3 这个数；执行过程里能读到它跑过一次 `count_tokens.py`，跑的那一次给的正是这一段文本——不是凭印象报的数 | 要读执行过程 |
| TC-18 | scenario_tokens_only | 验证用户只问 token 量时技能把那个数报出来 | 高 | ENV-1、ENV-2、ENV-7 就位；DATA-2 那个文件已放在盘上 | 对被测那侧说：`这个文件有多少 token？（文件：<DATA-2 的路径>）` | 回话里报出 3 这个数；执行过程里能读到它跑过一次 `count_tokens.py`，跑的那一次给的正是这个文件 | 要读执行过程 |
| TC-19 | scenario_other_model | 验证用户点名别的模型时技能说明自己不覆盖，不拿别的数顶替 | 高 | ENV-1、ENV-2、ENV-7 就位；DATA-1 那段正文在手 | 对被测那侧说：`帮我算一下「你好，世界」在 Claude 上是多少 token` | 回话里说明本技能只覆盖 DeepSeek 的官方词表、覆盖不了 Claude；不给出一个当作答案的近似数，也不拿 DeepSeek 的数顶替 Claude 的数 | 要读执行过程 |
| TC-20 | scenario_api_cost | 验证用户要估算成本时技能给出数并说明缓存命中那部分算不出来 | 高 | ENV-1、ENV-2、ENV-7 就位；DATA-1 那段正文在手 | 对被测那侧说：`这段文本调一次 API 大概多少钱？（文本：你好，世界）` | 回话里给出这次调用的 token 数 3；并说明离线算不出缓存命中的那部分（`prompt_cache_hit_tokens` 取决于服务端的缓存状态）；执行过程里能读到它跑过一次 `count_tokens.py` | 要读执行过程 |
| TC-21 | scenario_special_token | 验证文本里带特殊标记时技能按官方词表把它计进去 | 高 | ENV-1、ENV-2、ENV-7 就位；DATA-7 那段正文在手 | 对被测那侧说：`算一下这段有多少 token：<｜end▁of▁sentence｜>` | 回话里报出 1 这个数；执行过程里能读到它跑过一次 `count_tokens.py`，给的正是这段带特殊标记的文本 | 要读执行过程 |
| TC-22 | scenario_full_dialogue | 验证用户要给一整轮对话估 token 时技能说明得先按对话模板拼装再计数 | 高 | ENV-1、ENV-2、ENV-7 就位；DATA-13 那段对话正文在手 | 对被测那侧说：`帮我把这一轮对话估一下 token（对话正文：<DATA-13 的正文>）` | 回话里说明光算消息正文不够、得先按对话模板把这一轮拼装成请求再计数；不把「只算这段正文」得出的数当成整轮请求的 token 数报出来 | 要读执行过程 |
| TC-23 | scenario_undecodable | 验证输入没法解码时技能把这一情况报出来、指认是哪个文件 | 高 | ENV-1、ENV-2、ENV-7 就位；DATA-5 那个文件已放在盘上 | 对被测那侧说：`这个文件有多少 token？（文件：<DATA-5 的路径>）` | 回话里说明这个文件解不了码、并指认是哪个文件；不报出一个当作答案的 token 数 | 要读执行过程 |
| TC-24 | scenario_multiple_files | 验证一次给多个文件时技能逐个报出并给出合计 | 高 | ENV-1、ENV-2、ENV-7 就位；DATA-2 与 DATA-11 两个文件已放在盘上 | 对被测那侧说：`这两个文件加起来多少 token？（文件：<DATA-2 的路径>、<DATA-11 的路径>）` | 回话里两个文件各自的 token 数都在：DATA-2 那个是 3、DATA-11 那个是 1；并给出合计 4 | 要读执行过程 |
| TC-25 | scenario_first_run | 验证引擎还没装的机器上技能自行把引擎装好，不要求用户额外动手 | 高 | ENV-5 那个干净解释器就位——里面没装引擎；技能已装进被测那侧，且这一轮指定用它跑；ENV-6 网络出口可用；DATA-1 那段正文在手 | 对被测那侧说：`帮我算一下「你好，世界」这句话有多少 token（用这个解释器跑：<ENV-5 的解释器路径>）` | 回话里报出 3 这个数；执行过程里能读到它跑过一次 `count_tokens.py`，跑的时候脚本自己把引擎装好了；回话里没有要求用户先去装引擎、也没有因为缺引擎就改口说算不了 | 要读执行过程 |

注：TC-4 与 TC-6 两条判的是「依据未规定这一处」该怎么落。依据里没写这两种情形下该输出什么，所以这两条的「预期结果」栏不写预期的取值，只写它能被判的那一部分——TC-4 判「有没有把实际情况如实记下」，TC-6 判「有没有把解不了码这件事报出来并指认文件」。给这两条硬编一个预期值，就是拿依据没写的东西当依据。

## 对应表

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 有效来路：`--text` 直接给文本 | TC-1 |
| TCOV-2 | 有效来路：位置参数给文件路径 | TC-2 |
| TCOV-3 | 有效来路：从标准输入读 | TC-3 |
| TCOV-4 | 未规定：三种来路都不给 | TC-4 |
| TCOV-5 | 不带字节顺序标记的 UTF-8 文件 | TC-2 |
| TCOV-6 | 带字节顺序标记的 UTF-8 文件 | TC-5 |
| TCOV-7 | 未规定：文件不是 UTF-8 | TC-6 |
| TCOV-8 | 纯 ASCII 的内容 | TC-3 |
| TCOV-9 | 纯中文的内容 | TC-1 |
| TCOV-10 | 含基本平面之外字符的内容 | TC-7 |
| TCOV-11 | 含 DeepSeek 特殊 token 字面量的内容 | TC-8 |
| TCOV-12 | 只由空白字符组成的内容 | TC-9 |
| TCOV-13 | 零字符的空文本 | TC-10 |
| TCOV-14 | 两行输出，两个前缀各在一行的行首 | TC-1、TC-2、TC-3 |
| TCOV-15 | 未规定：不打印这两行时输出成什么样 | TC-6 |
| TCOV-16 | 文件字节数为 0 | TC-11 |
| TCOV-17 | 文件字节数为 1 | TC-12 |
| TCOV-18 | 文本字符数为 0 | TC-10 |
| TCOV-19 | 文本字符数为 1 | TC-13 |
| TCOV-20 | 判定规则 R1：已装引擎，直接跑 | TC-14 |
| TCOV-21 | 判定规则 R2：离线装随包 wheel | TC-15 |
| TCOV-22 | 判定规则 R3：联网装 `tokenizers==0.22.2` | TC-16 |
| TCOV-23 | 场景 S0：主场景，问一段文本或文件的 token 数 | TC-17 |
| TCOV-24 | 场景 S1：只问 token 量 | TC-18 |
| TCOV-25 | 场景 S2：问别的模型的 token 数 | TC-19 |
| TCOV-26 | 场景 S3：要估算调用成本 | TC-20 |
| TCOV-27 | 场景 S4：文本里带特殊标记 | TC-21 |
| TCOV-28 | 场景 S5：算一整轮对话请求 | TC-22 |
| TCOV-29 | 场景 S6：输入没法解码 | TC-23 |
| TCOV-30 | 场景 S7：一次给多个文件 | TC-24 |
| TCOV-31 | 场景 S8：首次运行，引擎还没装 | TC-25 |

注：「覆盖它的用例编号」这一栏留空表示这条覆盖项还没有任何用例覆盖。这份里 31 条覆盖项都已有用例，所以看不到留空的行。

## 覆盖率自检

| 技术（档位） | 覆盖项编号 | 覆盖项总数 T | 已被用例覆盖 N | 覆盖率 N÷T | 完成准则要求 |
|:---|:---|:---|:---|:---|:---|
| 等价类划分 | TCOV-1～TCOV-15 | 15 | 15 | 15÷15＝100% | 100% |
| 边界值分析（二值） | TCOV-16～TCOV-19 | 4 | 4 | 4÷4＝100% | 100% |
| 判定表测试 | TCOV-20～TCOV-22 | 3 | 3 | 3÷3＝100% | 100% |
| 场景测试 | TCOV-23～TCOV-31 | 9 | 9 | 9÷9＝100% | 100% |

注：T 按各门技术的算式核过——等价类划分数的是等价类，四组共 15 个（来路 4、编码 3、内容 6、输出 2）；边界值分析是两处边界各取二值，2×2＝4；判定表数是规则，三条；场景测试数的是场景，一条主场景加八条备选场景共 9 条。四门合起来 31 条覆盖项、25 条用例。

## 成品落点

| 成品 | 落的是哪些条目 |
|:---|:---|
| `evals/token-counter-round3/` | TC-17～TC-25 与它们的覆盖项（TCOV-23～TCOV-31）、TM-4、TP-3、DATA-1、DATA-2、DATA-5、DATA-7、DATA-11、DATA-13、ENV-1、ENV-2、ENV-7 |

这一处的成品是一个目录：里面一份配置（这一套评测跑哪些用例、判官怎么配、报告出成什么）加一个放用例正文的目录，一条用例一份。配置的文件名与放用例正文的目录名是那一套方案自己的约定，不在这份里点名；落成的人照实施方案规格说明那一份的写法取名即可。

还没落成：批一那两条规程（TP-1、TP-2）与它们排的 TC-1～TC-16 还没落成，落的是能跑的测试代码，不是评测用例；它们的覆盖项是 TCOV-1～TCOV-22，数据项是 DATA-1～DATA-12，环境项是 ENV-1～ENV-6。
