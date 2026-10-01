# 测试用例规格说明

这份文档分五块：测试覆盖项清单、测试用例、「覆盖项 ↔ 用例」对应表、覆盖率自检、成品落点。覆盖项按 TM-1 至 TM-4 四个模型分别导出，用例按 TM-1 与 TM-2 的取值分组、TM-3 的判定规则、TM-4 的交互序列导出。

## 测试覆盖项清单

四门技术各自导出的覆盖项合在一张表里，按模型相邻排列；「可追溯性」栏写到模型里的哪个元素。

| 唯一标识符 | 英文名 | 描述 | 风险等级 | 可追溯性 |
|:---|:---|:---|:---|:---|
| TCOV-1 | text_arg_nonempty | 由 `--text` 给出非空文本这条来路 | 中 | TM-1 的 E1 |
| TCOV-2 | file_path_exists | 由文件路径给出这段文本这条来路 | 中 | TM-1 的 E2 |
| TCOV-3 | stdin_nonempty | 由标准输入给出非空数据这条来路 | 中 | TM-1 的 E3 |
| TCOV-4 | no_source_at_all | 三种来路都不给，标准输入也为空 | 高 | TM-1 的 E4 |
| TCOV-5 | file_path_missing | 文件路径在盘上不存在 | 高 | TM-1 的 E5 |
| TCOV-6 | file_path_is_dir | 文件路径指向一个目录 | 高 | TM-1 的 E6 |
| TCOV-7 | text_arg_and_file_both | `--text` 与文件路径同时给出，依据未规定听谁的 | 高 | TM-1 的 E7 |
| TCOV-8 | encoding_plain_utf8 | 文件是不带字节顺序标记的 UTF-8 | 中 | TM-1 的 E8 |
| TCOV-9 | encoding_utf8_bom | 文件是带字节顺序标记的 UTF-8 | 中 | TM-1 的 E9 |
| TCOV-10 | encoding_not_utf8 | 文件不是 UTF-8 的字节序列 | 高 | TM-1 的 E10 |
| TCOV-11 | content_ascii | 文本是纯 ASCII 字符 | 中 | TM-1 的 E11 |
| TCOV-12 | content_cjk | 文本是纯中文 | 中 | TM-1 的 E12 |
| TCOV-13 | content_non_bmp | 文本含基本平面之外的字符 | 中 | TM-1 的 E13 |
| TCOV-14 | content_special_token | 文本含 DeepSeek 特殊 token 的字面量 | 中 | TM-1 的 E14 |
| TCOV-15 | content_whitespace_only | 文本只由空白字符组成 | 中 | TM-1 的 E15 |
| TCOV-16 | content_empty | 文本是零字符的空文本 | 中 | TM-1 的 E16 |
| TCOV-17 | output_two_lines_rc0 | 标准输出打印 `tokens:` 与 `chars:` 两行，退出码为 0 | 中 | TM-1 的 E17 |
| TCOV-18 | output_no_lines_rc_nonzero | 不打印这两行，以非零退出码结束 | 高 | TM-1 的 E18 |
| TCOV-19 | size_text_chars_zero | 文本字符数为 0——有序集 A 下边界上的值 | 高 | TM-2 的有序集 A，边界上的值 |
| TCOV-20 | size_text_chars_one | 文本字符数为 1——有序集 A 边界内侧紧挨着的值 | 高 | TM-2 的有序集 A，相邻类里的值 |
| TCOV-21 | size_file_bytes_zero | 文件字节数为 0——有序集 B 下边界上的值 | 高 | TM-2 的有序集 B，边界上的值 |
| TCOV-22 | size_file_bytes_one | 文件字节数为 1——有序集 B 边界内侧紧挨着的值 | 高 | TM-2 的有序集 B，相邻类里的值 |
| TCOV-23 | size_after_bom_chars_zero | 带标记文件里标记之后的字符数为 0——有序集 C 下边界上的值 | 高 | TM-2 的有序集 C，边界上的值 |
| TCOV-24 | size_after_bom_chars_one | 带标记文件里标记之后的字符数为 1——有序集 C 边界内侧紧挨着的值 | 高 | TM-2 的有序集 C，相邻类里的值 |
| TCOV-25 | rule_engine_already_importable | 判定规则 1：引擎已可导入，直接用已装的引擎，不装任何东西 | 高 | TM-3 的规则 1 |
| TCOV-26 | rule_offline_wheel_install | 判定规则 2：引擎不可导入、打包 wheel 可用，离线安装打包的 wheel | 高 | TM-3 的规则 2 |
| TCOV-27 | rule_networked_install | 判定规则 3：引擎不可导入、打包 wheel 也不可用，联网安装写死版本 | 高 | TM-3 的规则 3 |
| TCOV-28 | scenario_count_text_or_file | 主场景：用户要算一段文本或一个文件的 token 量，技能跑出数并报回来 | 中 | TM-4 的主场景 |
| TCOV-29 | scenario_token_only_answer | 备选场景：用户只问 token 量，技能只报 token 数 | 中 | TM-4 的备选场景 1 |
| TCOV-30 | scenario_other_model_declined | 备选场景：用户点名别的模型，技能说明不覆盖且不给近似数 | 中 | TM-4 的备选场景 2 |
| TCOV-31 | scenario_cost_estimate_caveat | 备选场景：用户要估算调用成本，技能补一句缓存命中离线算不出来 | 中 | TM-4 的备选场景 3 |
| TCOV-32 | scenario_special_token_counted | 备选场景：文本里带特殊 token 的字面量，技能按官方词表计入 | 中 | TM-4 的备选场景 4 |
| TCOV-33 | scenario_full_chat_request | 备选场景：用户要算一整轮对话请求，技能说明得先按对话模板拼装 | 中 | TM-4 的备选场景 5 |
| TCOV-34 | scenario_undecodable_input | 备选场景：输入没法按 UTF-8 解码，技能把这一情况报出来 | 中 | TM-4 的备选场景 6 |
| TCOV-35 | scenario_multiple_files_total | 备选场景：一次给多个文件，技能逐个报出并给合计 | 中 | TM-4 的备选场景 7 |
| TCOV-36 | scenario_first_run_installs | 备选场景：目标机上还没装引擎，脚本自行装好，技能不要求用户额外动手 | 中 | TM-4 的备选场景 8 |

## 测试用例

分三组：前两组判据落在命令、退出码与盘上的文件上，第三组判据要读一轮技能被调用时的表现。脚本一律按技能目录下的 `scripts/count_tokens.py` 调用；`<技能目录>` 指 `plugin/skills/token-counter/`。

### 脚本层的常规路径

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 前置条件 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|:---|:---|
| TC-1 | text_single_ascii_char | 验证 `--text` 给出一个 ASCII 字符时的计数 | 中 | ENV-1、ENV-3、ENV-4、ENV-7 就位 | 按 DATA-1 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "a"` | 标准输出第一行 `tokens: 1`，第二行 `chars: 1`；退出码 0 |
| TC-2 | text_cjk_counts_exactly | 验证一段中文的计数，并钉住 `chars` 那一行数的是字符数而不是字节数 | 中 | 同 TC-1 | 按 DATA-2 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "你好，世界"` | 标准输出第一行 `tokens: 3`，第二行 `chars: 5`——这一段是 5 个字符、15 个字节，`chars` 报 5 说明数的是字符数；退出码 0 |
| TC-3 | text_astral_emoji | 验证基本平面之外的字符的计数 | 中 | 同 TC-1 | 按 DATA-3 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "😀"` | 标准输出第一行 `tokens: 2`，第二行 `chars: 1`；退出码 0 |
| TC-4 | text_whitespace_only | 验证只由空白字符组成的文本的计数 | 中 | 同 TC-1 | 按 DATA-4 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "   "` | 标准输出第一行 `tokens: 1`，第二行 `chars: 3`；退出码 0 |
| TC-5 | text_special_token_literal | 验证特殊 token 字面量按官方词表计入，被当作一个 token | 中 | 同 TC-1 | 按 DATA-5 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "<｜end▁of▁sentence｜>"` | 标准输出第一行 `tokens: 1`；退出码 0 |
| TC-6 | text_empty_string | 验证空文本这条边界，`--text` 给了但内容是零字符 | 中 | 同 TC-1 | 跑 `python <技能目录>/scripts/count_tokens.py --text ""` | 标准输出第一行 `tokens: 0`，第二行 `chars: 0`；退出码 0 |
| TC-7 | file_plain_utf8 | 验证由文件路径给出文本这条来路，文件是不带标记的 UTF-8 | 中 | 同 TC-1 | 按 DATA-6 备好样本文件，跑 `python <技能目录>/scripts/count_tokens.py <样本文件>` | 标准输出第一行 `tokens: 3`，第二行 `chars: 5`；退出码 0 |
| TC-8 | file_utf8_with_bom | 验证带字节顺序标记的文件被正常读取，标记不算进正文 | 中 | 同 TC-1 | 按 DATA-7 备好样本文件，跑 `python <技能目录>/scripts/count_tokens.py <样本文件>` | 标准输出第一行 `tokens: 3`，第二行 `chars: 5`——与 TC-7 同值，说明那三个字节的标记既没被当成字符也没被算进 token；退出码 0 |
| TC-9 | file_zero_bytes | 验证零字节文件这条边界 | 高 | 同 TC-1 | 按 DATA-8 备好空文件，跑 `python <技能目录>/scripts/count_tokens.py <空文件>` | 标准输出第一行 `tokens: 0`，第二行 `chars: 0`；退出码 0 |
| TC-10 | file_one_byte | 验证单字节文件这条边界 | 高 | 同 TC-1 | 按 DATA-9 备好单字节文件，跑 `python <技能目录>/scripts/count_tokens.py <单字节文件>` | 标准输出第一行 `tokens: 1`，第二行 `chars: 1`；退出码 0 |
| TC-11 | file_bom_only | 验证整个文件只有那三个标记字节这条边界 | 高 | 同 TC-1 | 按 DATA-10 备好文件，跑 `python <技能目录>/scripts/count_tokens.py <文件>` | 标准输出第一行 `tokens: 0`，第二行 `chars: 0`——标记被剥掉后正文是零字符；退出码 0 |
| TC-12 | file_bom_plus_one_char | 验证标记之后只有一个字符这条边界 | 高 | 同 TC-1 | 按 DATA-11 备好文件，跑 `python <技能目录>/scripts/count_tokens.py <文件>` | 标准输出第一行 `tokens: 1`，第二行 `chars: 1`；退出码 0 |
| TC-13 | stdin_pipe_cjk | 验证由标准输入给出文本这条来路 | 中 | 同 TC-1 | 把 DATA-2 的文本按 UTF-8 编码接进管道，跑 `<管道> \| python <技能目录>/scripts/count_tokens.py` | 标准输出第一行 `tokens: 3`，第二行 `chars: 5`；退出码 0 |
| TC-14 | no_source_at_all | 验证三种来路都不给、标准输入也为空的情形 | 高 | 同 TC-1 | 不给 `--text`、不给文件路径，把空输入接进管道，跑 `python <技能目录>/scripts/count_tokens.py` | 标准输出第一行 `tokens: 0`，第二行 `chars: 0`；退出码 0——依据没有把这一情形定成错误，脚本按空文本处理 |
| TC-15 | file_path_missing | 验证文件路径不存在的情形 | 高 | 同 TC-1 | 按 DATA-13 取一个盘上不存在的路径，跑 `python <技能目录>/scripts/count_tokens.py <不存在的路径>` | 标准输出上没有 `tokens:` 那一行；退出码非 0 |
| TC-16 | file_path_is_directory | 验证文件路径指向目录的情形 | 高 | 同 TC-1 | 按 DATA-14 取一个目录路径，跑 `python <技能目录>/scripts/count_tokens.py <目录路径>` | 标准输出上没有 `tokens:` 那一行；退出码非 0 |
| TC-17 | input_file_not_utf8 | 验证文件不是 UTF-8 时的报错，且报错要指认是哪个输入 | 高 | 同 TC-1 | 按 DATA-12 备好样本文件，跑 `python <技能目录>/scripts/count_tokens.py <样本文件>` | 标准输出上没有 `tokens:` 那一行；报错信息里出现 `not valid UTF-8:`，后面跟上这个样本文件的路径；退出码非 0 |
| TC-18 | text_arg_beats_file | 验证 `--text` 与文件路径同时给出时听谁的——依据未规定这一处，本用例只把实现的行为记下来 | 高 | 同 TC-1 | 按 DATA-6 备好样本文件，跑 `python <技能目录>/scripts/count_tokens.py <样本文件> --text "a"` | 依据推不出预期结果：两种来路同时给出这一情形，依据里没有写。按实现记下来的行为是——`--text` 胜出、文件被静默忽略，标准输出第一行 `tokens: 1`、第二行 `chars: 1`，与只给 `--text "a"` 时一样，没有任何提示说文件被忽略了。依据补齐后这一条要重判 |
| TC-19 | input_stdin_not_utf8 | 验证标准输入不是 UTF-8 时的报错——与 TC-17 是同一覆盖项的另一条失败路子，报错里指认的输入不一样 | 高 | 同 TC-1 | 把 DATA-12 那串字节原样接进管道，跑 `<管道> \| python <技能目录>/scripts/count_tokens.py` | 标准输出上没有 `tokens:` 那一行；报错信息里出现 `not valid UTF-8:`，后面跟的是标准输入的记号而不是文件路径；退出码非 0 |

### 引擎获取路径

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 前置条件 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|:---|:---|
| TC-20 | engine_already_present | 验证判定规则 1：引擎已可导入时不做任何安装 | 高 | ENV-1、ENV-3、ENV-4、ENV-7 就位；先记下 ENV-4 那个环境里引擎的版本号与它的安装位置 | 在这个环境里跑 `python <技能目录>/scripts/count_tokens.py --text "a"` | 标准输出第一行 `tokens: 1`，第二行 `chars: 1`；退出码 0；跑完之后再核一遍引擎的版本号与安装位置，与跑之前一模一样；跑的过程中没有任何安装动作发生 |
| TC-21 | clean_env_installs_bundled_wheel | 验证判定规则 2：引擎不可导入、打包 wheel 可用时，离线装上那个 wheel | 高 | ENV-1、ENV-3、ENV-7 就位；按 ENV-5 现建一个干净环境，确认它里面导入不了引擎 | 用 ENV-5 那个环境的解释器跑 `<干净环境的解释器> <技能目录>/scripts/count_tokens.py --text "a"` | 标准输出第一行 `tokens: 1`，第二行 `chars: 1`；退出码 0；跑完之后那个干净环境里能导入引擎，装上的版本与 `wheels/` 里那个 wheel 同名同版本 |
| TC-22 | incompatible_wheel_falls_back_to_network | 验证判定规则 3：打包 wheel 不可用时回落到联网安装写死版本 | 高 | ENV-1、ENV-3、ENV-6、ENV-7 就位；按 ENV-5 现建一个干净环境；按 DATA-15 备好那个平台标记不匹配的假 wheel，先放在外面 | 第一步，把 DATA-15 那个假 wheel 放进 `wheels/`、并把真的那个暂时挪出这个目录；第二步，用 ENV-5 那个环境的解释器跑 `<干净环境的解释器> <技能目录>/scripts/count_tokens.py --text "a"`；第三步，按 DATA-15 的重置需求把 `wheels/` 恢复原样 | 标准输出第一行 `tokens: 1`，第二行 `chars: 1`；退出码 0；跑完之后那个干净环境里能导入引擎；安装动作走的是联网那一路（假 wheel 装不上，脚本要接着往下走而不是停在那里）；第三步做完之后 `wheels/` 与第一步之前一模一样 |
| TC-23 | clean_env_offline_install | 验证判定规则 2 的离线性质——同一覆盖项的另一条检查：断网也装得成 | 高 | ENV-1、ENV-3、ENV-7 就位；按 ENV-5 现建一个干净环境，确认它里面导入不了引擎；把这一条用例执行期间的网络出口断掉 | 用 ENV-5 那个环境的解释器跑 `<干净环境的解释器> <技能目录>/scripts/count_tokens.py --text "a"` | 标准输出第一行 `tokens: 1`，第二行 `chars: 1`；退出码 0——断网也装得成，说明走的是随技能打包的 wheel，不是联网那一路 |

### 技能被调用时的用法场景

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 前置条件 | 输入 | 预期结果 |
|:---|:---|:---|:---|:---|:---|:---|
| TC-24 | usage_count_file_tokens | 验证主场景：用户要算一个文件的 token 量，技能跑出数并报回来 | 中 | ENV-1、ENV-2、ENV-3、ENV-4、ENV-7、ENV-8 就位；按 DATA-6 备好样本文件 | 用户提出：算一下这个文件有多少 token，文件是 DATA-6 那个 | 技能定位到本技能目录下的脚本并把它跑起来；报回来的 token 数与脚本那一行的数一致（这个样本是 3）；没有凭空给数 |
| TC-25 | usage_report_tokens_only | 验证用户只问 token 量时只报这一项 | 中 | 同 TC-24 | 用户提出：这个文件有多少 token？文件是 DATA-6 那个 | 报回来的话里给出了 token 数；没有把字符数一并端出来当答案 |
| TC-26 | usage_other_model_declined | 验证别的模型问上门来时明确说明不覆盖 | 中 | ENV-1、ENV-2、ENV-8 就位 | 用户提出：帮我算一下这段话在另一个厂家的模型上要花多少 token | 技能明确说出本技能不覆盖那个模型；没有给出任何近似数、也没有拿 DeepSeek 的数顶替；没有绕开这一条去跑脚本交差 |
| TC-27 | usage_cost_estimate_caveat | 验证估算调用成本时补上缓存命中那一句说明 | 中 | 同 TC-24 | 用户提出：按 DATA-6 那个文件的量估算一下调 API 要花多少钱 | 话里给出了 token 数，并说明缓存命中的那部分离线算不出来；没有把估算说成就是账单上的数 |
| TC-28 | usage_special_token_counted | 验证特殊 token 的字面量照官方词表计入 | 中 | 同 TC-24 | 用户提出：按 DATA-5 那段文本算一下，那段里有个特殊标记，算几个 token | 报回来的是 1，与按官方词表计入的结果一致；没有把那个字面量拆成若干普通字符来数 |
| TC-29 | usage_full_chat_request | 验证要算一整轮对话请求时说清拼装那一步 | 中 | ENV-1、ENV-2、ENV-8 就位 | 用户提出：帮我算一整轮对话请求要多少 token，消息我贴在下面了 | 技能说明光算消息正文不够，得先按对话模板把消息拼装成请求再计数；给出的计数办法里包含拼装这一步；没有只把消息正文一数就交差 |
| TC-30 | usage_undecodable_input | 验证解码失败时把这一情况报出来，不编数 | 中 | 同 TC-24；按 DATA-12 备好样本文件 | 用户提出：算一下这个文件的 token，文件是 DATA-12 那个 | 技能报出这个文件解不了码这一情况，并指认是哪个文件；没有给出任何 token 数；没有把这个文件当成 0 或跳过不提 |
| TC-31 | usage_multiple_files_total | 验证一次给多个文件时逐个报出并给合计 | 中 | 同 TC-24；按 DATA-6 与 DATA-8 各备好一个文件 | 用户提出：这两个文件加起来多少 token？文件是 DATA-6 与 DATA-8 那两个 | 两个文件各自的数都报了出来（3 与 0），并给出合计 3；没有只报其中某一个 |
| TC-32 | usage_first_run_no_extra_step | 验证目标机上还没装引擎时，用户不必额外动手 | 中 | ENV-1、ENV-2、ENV-3、ENV-7、ENV-8 就位；按 ENV-5 现建一个干净环境，确认它里面导入不了引擎 | 用户提出：算一下 DATA-1 那个文本有多少 token（照常在干净环境里提出这一要求） | 技能报回来的 token 数与脚本那一行的数一致（1）；话里没有要求用户先去装什么、也没有把安装动作推给用户；脚本自己把引擎装好了 |

## 覆盖项 ↔ 用例对应表

一条覆盖项一行；「覆盖它的用例编号」栏空着的行就是还没有用例覆盖的覆盖项。

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 由 `--text` 给出非空文本这条来路 | TC-1 |
| TCOV-2 | 由文件路径给出这段文本这条来路 | TC-7 |
| TCOV-3 | 由标准输入给出非空数据这条来路 | TC-13 |
| TCOV-4 | 三种来路都不给，标准输入也为空 | TC-14 |
| TCOV-5 | 文件路径在盘上不存在 | TC-15 |
| TCOV-6 | 文件路径指向一个目录 | TC-16 |
| TCOV-7 | `--text` 与文件路径同时给出，依据未规定听谁的 | TC-18 |
| TCOV-8 | 文件是不带字节顺序标记的 UTF-8 | TC-7 |
| TCOV-9 | 文件是带字节顺序标记的 UTF-8 | TC-8 |
| TCOV-10 | 文件不是 UTF-8 的字节序列 | TC-17、TC-19 |
| TCOV-11 | 文本是纯 ASCII 字符 | TC-1 |
| TCOV-12 | 文本是纯中文 | TC-2、TC-13 |
| TCOV-13 | 文本含基本平面之外的字符 | TC-3 |
| TCOV-14 | 文本含 DeepSeek 特殊 token 的字面量 | TC-5 |
| TCOV-15 | 文本只由空白字符组成 | TC-4 |
| TCOV-16 | 文本是零字符的空文本 | TC-6 |
| TCOV-17 | 标准输出打印 `tokens:` 与 `chars:` 两行，退出码为 0 | TC-1、TC-2、TC-3、TC-4、TC-5、TC-6、TC-7、TC-8、TC-9、TC-10、TC-11、TC-12、TC-13、TC-14 |
| TCOV-18 | 不打印这两行，以非零退出码结束 | TC-15、TC-16、TC-17、TC-19 |
| TCOV-19 | 文本字符数为 0——有序集 A 下边界上的值 | TC-6 |
| TCOV-20 | 文本字符数为 1——有序集 A 边界内侧紧挨着的值 | TC-1 |
| TCOV-21 | 文件字节数为 0——有序集 B 下边界上的值 | TC-9 |
| TCOV-22 | 文件字节数为 1——有序集 B 边界内侧紧挨着的值 | TC-10 |
| TCOV-23 | 带标记文件里标记之后的字符数为 0——有序集 C 下边界上的值 | TC-11 |
| TCOV-24 | 带标记文件里标记之后的字符数为 1——有序集 C 边界内侧紧挨着的值 | TC-12 |
| TCOV-25 | 判定规则 1：引擎已可导入，直接用已装的引擎，不装任何东西 | TC-20 |
| TCOV-26 | 判定规则 2：引擎不可导入、打包 wheel 可用，离线安装打包的 wheel | TC-21、TC-23 |
| TCOV-27 | 判定规则 3：引擎不可导入、打包 wheel 也不可用，联网安装写死版本 | TC-22 |
| TCOV-28 | 主场景：用户要算一段文本或一个文件的 token 量，技能跑出数并报回来 | TC-24 |
| TCOV-29 | 备选场景：用户只问 token 量，技能只报 token 数 | TC-25 |
| TCOV-30 | 备选场景：用户点名别的模型，技能说明不覆盖且不给近似数 | TC-26 |
| TCOV-31 | 备选场景：用户要估算调用成本，技能补一句缓存命中离线算不出来 | TC-27 |
| TCOV-32 | 备选场景：文本里带特殊 token 的字面量，技能按官方词表计入 | TC-28 |
| TCOV-33 | 备选场景：用户要算一整轮对话请求，技能说明得先按对话模板拼装 | TC-29 |
| TCOV-34 | 备选场景：输入没法按 UTF-8 解码，技能把这一情况报出来 | TC-30 |
| TCOV-35 | 备选场景：一次给多个文件，技能逐个报出并给合计 | TC-31 |
| TCOV-36 | 备选场景：目标机上还没装引擎，脚本自行装好，技能不要求用户额外动手 | TC-32 |

## 覆盖率自检

| 技术（档位） | 覆盖项编号 | 覆盖项总数 T | 已被用例覆盖 N | 覆盖率 N÷T | 完成准则要求 |
|:---|:---|:---|:---|:---|:---|
| 等价类划分 | TCOV-1～TCOV-18 | 18 | 18 | 18÷18＝100% | 100% |
| 边界值分析 | TCOV-19～TCOV-24 | 6 | 6 | 6÷6＝100% | 100% |
| 判定表测试 | TCOV-25～TCOV-27 | 3 | 3 | 3÷3＝100% | 100% |
| 场景测试 | TCOV-28～TCOV-36 | 9 | 9 | 9÷9＝100% | 100% |

四门的 T 各自拿本门的算式核过：等价类划分数的是等价类的条数，TM-1 里识别出 18 条；边界值分析数的是边界值的条数，3 处边界各取 2 个值，共 6 条；判定表测试数的是可行判定规则的条数，TM-3 里 3 条规则全部可行；场景测试数的是主场景加备选场景的条数，1 加 8 共 9 条。四门都没有判为不可行而剔除的覆盖项。

## 成品落点

还没落成。
