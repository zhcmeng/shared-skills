# 测试用例规格说明

这份文档分五块：测试覆盖项清单、测试用例、「覆盖项 ↔ 用例」对应表、覆盖率自检、成品落点。覆盖项按 TM-1 至 TM-4 四个模型分别导出，用例按 TM-1 的取值分组、TM-2 的三个有序集、TM-3 的三条规则、TM-4 的九条场景导出。

脚本一律按技能目录下的 `scripts/count_tokens.py` 调用；下文的 `<技能目录>` 指这个技能在盘上的那个目录。

## 测试覆盖项清单

四门技术各自导出的覆盖项合在一张表里，按模型相邻排列；「可追溯性」栏写到模型里的哪个元素。

| 唯一标识符 | 英文名 | 描述 | 风险等级 | 可追溯性 |
|:---|:---|:---|:---|:---|
| TCOV-1 | text_arg_nonempty | 由 `--text` 给出非空文本这条来路 | 中 | TM-1 的 E1 |
| TCOV-2 | file_path_exists | 由文件路径给出这段文本这条来路 | 中 | TM-1 的 E2 |
| TCOV-3 | stdin_nonempty | 由标准输入给出非空数据这条来路 | 中 | TM-1 的 E3 |
| TCOV-4 | no_source_at_all | 三种来路都不给，标准输入也为空——依据未规定这一处 | 高 | TM-1 的 E4 |
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
| TCOV-26 | rule_offline_wheel_install | 判定规则 2：引擎不可导入、打包 wheel 可用，离线装打包的 wheel | 高 | TM-3 的规则 2 |
| TCOV-27 | rule_networked_install | 判定规则 3：引擎不可导入、打包 wheel 也不可用，联网装写死版本 | 高 | TM-3 的规则 3 |
| TCOV-28 | scenario_count_text_or_file | 主场景：用户要算一段文本或一个文件的 token 量，技能跑出数并报回来 | 中 | TM-4 的主场景 |
| TCOV-29 | scenario_token_only_answer | 备选场景：用户只问 token 量，技能报出 token 数 | 中 | TM-4 的备选场景 1 |
| TCOV-30 | scenario_other_model_declined | 备选场景：用户点名别的模型，技能说明不覆盖且不给近似数 | 中 | TM-4 的备选场景 2 |
| TCOV-31 | scenario_cost_estimate_caveat | 备选场景：用户要估算调用成本，技能补一句缓存命中离线算不出来 | 中 | TM-4 的备选场景 3 |
| TCOV-32 | scenario_special_token_counted | 备选场景：文本里带特殊 token 的字面量，技能按官方词表计入 | 中 | TM-4 的备选场景 4 |
| TCOV-33 | scenario_full_chat_request | 备选场景：用户要算一整轮对话请求，技能说明得先按对话模板拼装 | 中 | TM-4 的备选场景 5 |
| TCOV-34 | scenario_undecodable_input | 备选场景：输入没法按 UTF-8 解码，技能把这一情况报出来 | 中 | TM-4 的备选场景 6 |
| TCOV-35 | scenario_multiple_files_total | 备选场景：一次给多个文件，技能逐个报出并给合计 | 中 | TM-4 的备选场景 7 |
| TCOV-36 | scenario_first_run_installs | 备选场景：目标机上还没装引擎，脚本自行装好，技能不要求用户额外动手 | 中 | TM-4 的备选场景 8 |

## 测试用例

分两组：TC-1 至 TC-23 的判据落在命令、退出码与盘上的文件上；TC-24 至 TC-32 的判据要读一轮技能被调用时的表现。输入栏里凡是按编号指的样本，都在测试数据需求里定义。

### 脚本层：取值、边界与引擎获取

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 前置条件 | 输入 | 预期结果 | 判据落在哪一层 |
|:---|:---|:---|:---|:---|:---|:---|:---|
| TC-1 | text_ascii_counts | 验证 `--text` 给一段纯 ASCII 文本时的两行输出 | 中 | ENV-1、ENV-3、ENV-4 就位 | 按 DATA-1 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "hello"` | 标准输出第一行是 `tokens: 1`；第二行是 `chars: 5`；退出码 0 | 落在输出上 |
| TC-2 | text_cjk_counts_exactly | 验证一段中文的计数，并钉住 `chars` 数的是字符数而不是字节数 | 中 | 同 TC-1 | 按 DATA-2 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "你好，世界"` | 标准输出第一行是 `tokens: 3`；第二行是 `chars: 5`——这一段 5 个字符、15 个字节，报 5 才算数的是字符数；退出码 0 | 落在输出上 |
| TC-3 | text_non_bmp_counts | 验证基本平面之外的字符的计数 | 中 | 同 TC-1 | 按 DATA-3 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "😀"` | 标准输出第一行是 `tokens: 2`；第二行是 `chars: 1`；退出码 0 | 落在输出上 |
| TC-4 | text_special_token_counted | 验证特殊 token 的字面量按官方词表计入，算作一个 token | 中 | 同 TC-1 | 按 DATA-5 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "<｜end▁of▁sentence｜>"` | 标准输出第一行是 `tokens: 1`；退出码 0 | 落在输出上 |
| TC-5 | text_whitespace_only_counts | 验证只由空白字符组成的文本的计数 | 中 | 同 TC-1 | 按 DATA-4 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "   "` | 标准输出第一行是 `tokens: 1`；第二行是 `chars: 3`；退出码 0 | 落在输出上 |
| TC-6 | text_empty_counts_zero | 验证零字符这条边界——`--text` 给了，内容是零个字符 | 高 | 同 TC-1 | 跑 `python <技能目录>/scripts/count_tokens.py --text ""` | 标准输出第一行是 `tokens: 0`；第二行是 `chars: 0`；退出码 0 | 落在输出上 |
| TC-7 | text_one_char_counts_one | 验证一个字符这条边界 | 高 | 同 TC-1 | 跑 `python <技能目录>/scripts/count_tokens.py --text "a"` | 标准输出第一行是 `tokens: 1`；第二行是 `chars: 1`；退出码 0 | 落在输出上 |
| TC-8 | file_plain_utf8_counts | 验证由文件路径给出文本这条来路 | 中 | 同 TC-1 | 按 DATA-6 备好样本，跑 `python <技能目录>/scripts/count_tokens.py <样本文件>` | 标准输出第一行是 `tokens: 3`；第二行是 `chars: 5`；退出码 0 | 落在输出上 |
| TC-9 | file_bom_stripped | 验证带字节顺序标记的文件被正常读取，标记不算进正文 | 中 | 同 TC-1 | 按 DATA-7 备好样本，跑 `python <技能目录>/scripts/count_tokens.py <样本文件>` | 标准输出第一行是 `tokens: 3`；第二行是 `chars: 5`——与 TC-8 同值，说明那三个标记字节既没算成字符也没算进 token；退出码 0 | 落在输出上 |
| TC-10 | file_zero_bytes_counts_zero | 验证零字节文件这条边界 | 高 | 同 TC-1 | 按 DATA-8 备好空文件，跑 `python <技能目录>/scripts/count_tokens.py <空文件>` | 标准输出第一行是 `tokens: 0`；第二行是 `chars: 0`；退出码 0 | 落在输出上 |
| TC-11 | file_one_byte_counts_one | 验证单字节文件这条边界 | 高 | 同 TC-1 | 按 DATA-9 备好单字节文件，跑 `python <技能目录>/scripts/count_tokens.py <单字节文件>` | 标准输出第一行是 `tokens: 1`；第二行是 `chars: 1`；退出码 0 | 落在输出上 |
| TC-12 | file_bom_only_counts_zero | 验证整个文件只有那三个标记字节这条边界 | 高 | 同 TC-1 | 按 DATA-10 备好文件，跑 `python <技能目录>/scripts/count_tokens.py <文件>` | 标准输出第一行是 `tokens: 0`；第二行是 `chars: 0`——标记被剥掉之后正文是零个字符；退出码 0 | 落在输出上 |
| TC-13 | file_bom_plus_one_char | 验证标记之后只有一个字符这条边界 | 高 | 同 TC-1 | 按 DATA-11 备好文件，跑 `python <技能目录>/scripts/count_tokens.py <文件>` | 标准输出第一行是 `tokens: 1`；第二行是 `chars: 1`；退出码 0 | 落在输出上 |
| TC-14 | stdin_nonempty_counts | 验证标准输入这条来路 | 中 | 同 TC-1 | 按 DATA-15 备好内容，跑 `cat <内容文件> \| python <技能目录>/scripts/count_tokens.py` | 标准输出第一行是 `tokens: 3`；第二行是 `chars: 5`；退出码 0 | 落在输出上 |
| TC-15 | no_source_at_all | 验证三种来路都不给这一情形——依据未规定这一处，把实现当下的行为记下来 | 高 | 同 TC-1 | 跑 `python <技能目录>/scripts/count_tokens.py`，标准输入接空 | 依据推不出预期结果：三种来路都不给这一情形，依据里没有写。按实现记下来的行为是——当成零字符的空文本处理，标准输出第一行是 `tokens: 0`；第二行是 `chars: 0`；退出码 0，没有任何提示说没收到输入。依据补齐之后这一条要重判 | 落在输出上 |
| TC-16 | file_path_missing_exits_nonzero | 验证路径不存在时以非零退出码结束 | 高 | 同 TC-1 | 跑 `python <技能目录>/scripts/count_tokens.py ./不存在的文件.md` | 标准输出里没有 `tokens:` 开头的行；退出码非 0 | 落在输出上 |
| TC-17 | file_path_is_dir_exits_nonzero | 验证路径指向目录时以非零退出码结束 | 高 | 同 TC-1 | 跑 `python <技能目录>/scripts/count_tokens.py ./fixtures` | 标准输出里没有 `tokens:` 开头的行；退出码非 0 | 落在输出上 |
| TC-18 | text_arg_and_file_both | 验证两种来路同时给出时的取舍——依据未规定，钉住实际行为 | 高 | 同 TC-1 | 按 DATA-6 备好样本，跑 `python <技能目录>/scripts/count_tokens.py --text "你好，世界" <样本文件>` | 标准输出第一行是 `tokens: 3`，第二行是 `chars: 5`；退出码 0——两个输入这一段的值恰好相同，判的是它没报错、也没把两次输入拼起来数 | 落在输出上 |
| TC-19 | file_not_utf8_reports | 验证非 UTF-8 文件被解出来时报错而不是给一个数 | 高 | 同 TC-1 | 按 DATA-12 备好文件，跑 `python <技能目录>/scripts/count_tokens.py <文件>` | 标准输出里没有 `tokens:` 开头的行；退出码非 0 | 落在输出上 |
| TC-20 | engine_already_importable | 验证规则 1：引擎已可导入时直接用，不装任何东西 | 高 | ENV-1、ENV-4 就位；ENV-3 那台解释器里已装好引擎 | 按 DATA-2 取文本，跑 `python <技能目录>/scripts/count_tokens.py --text "你好，世界"` | 标准输出第一行是 `tokens: 3`；退出码 0；ENV-3 那台解释器的已装包清单在跑前跑后一致 | 落在输出上 |
| TC-21 | offline_wheel_install | 验证规则 2：引擎不可导入、打包 wheel 可用时离线装 wheel | 高 | ENV-1、ENV-5 就位；ENV-3 那个干净解释器里没有引擎 | 在那个干净解释器里跑 `python <技能目录>/scripts/count_tokens.py --text "你好，世界"` | 标准输出第一行是 `tokens: 3`；退出码 0；那个干净解释器里此后能导入 `tokenizers`，且装的是随包分发的那个版本 | 落在输出上 |
| TC-22 | offline_install_without_network | 验证规则 2 在断网时照样成立——「首次运行无需联网」这句承诺 | 高 | 同 TC-21，另加 ENV-6 断网 | 同 TC-21，且在断网状态下跑 | 标准输出第一行是 `tokens: 3`；退出码 0 | 落在输出上 |
| TC-23 | network_fallback_install | 验证规则 3：打包 wheel 不可用时联网装写死版本 | 高 | ENV-1、ENV-2、ENV-5 就位；那个干净解释器里没有引擎；打包的 wheel 已被挪开 | 按 DATA-12 之外任一样本，在那个干净解释器里跑 `python <技能目录>/scripts/count_tokens.py --text "你好，世界"` | 标准输出第一行是 `tokens: 3`；退出码 0；那个干净解释器里装上的引擎版本是依据写死的那个 | 落在输出上 |

### 技能被调用时：交互序列

这一组九条用例的输入都是用户会说的那句话，一个字不改；判据是回话里说了什么。

| 唯一标识符 | 英文名 | 目标 | 风险等级 | 前置条件 | 输入 | 预期结果 | 判据落在哪一层 |
|:---|:---|:---|:---|:---|:---|:---|:---|
| TC-24 | usage_count_file_tokens | 验证主场景：给了文件路径，技能跑出数并报回来 | 中 | ENV-1、ENV-3、ENV-4、ENV-7、ENV-8 就位；技能已装好 | 按 DATA-6 把样本摆进工作区，用户说：「帮我算一下 ./sample.txt 里有多少 token」 | 回话里给出的 token 数与脚本那一行的数一致（这个样本是 3）；回话里没有凭空给一个数、也没有说自己没跑 | 要读执行过程 |
| TC-25 | usage_report_tokens_only | 验证只问 token 量时，回话给出 token 数 | 中 | 同 TC-24 | 用户说：「算一下 "你好，世界" 有几个 token」 | 回话里给出了 token 数（3） | 要读执行过程 |
| TC-26 | usage_other_model_declined | 验证点名别的模型时，技能说明不覆盖且不给近似数 | 中 | 同 TC-24 | 用户说：「帮我算算『你好，世界』这段话在 Claude 里有多少 token」 | 回话里明确说出本技能不覆盖那个模型；没有给出近似数、也没有拿 DeepSeek 的数顶替 | 要读执行过程 |
| TC-27 | usage_cost_estimate_caveat | 验证估算成本时补上缓存命中那一句 | 中 | 同 TC-24 | 用户说：「按『你好，世界』这段文本，估一下调 API 大概要多少钱？」 | 回话里给出了 token 数，并说明缓存命中那部分离线算不出来；没有把估算说成就是账单上的数 | 要读执行过程 |
| TC-28 | usage_special_token_counted | 验证回话里的数把那一个特殊标记计了进去 | 中 | 同 TC-24 | 用户说：「<｜end▁of▁sentence｜> 这一个标记算几个 token？」 | 回话里报回来的是 1；没有把那个字面量拆成若干普通字符来数 | 要读执行过程 |
| TC-29 | usage_full_chat_request | 验证要算一整轮对话时说明得先拼装 | 中 | 同 TC-24 | 按 DATA-14 取那一轮对话的正文，用户说：「我要给一整轮对话估 token，就是 system 加 user 加 assistant 三条消息那种」 | 回话里说明光算消息正文不够、得先按对话模板把消息拼装成请求再计数；给出的计数办法里包含拼装这一步；没有只把消息正文一数就交差 | 要读执行过程 |
| TC-30 | usage_undecodable_input | 验证解不了码时把这一情况报出来 | 中 | 同 TC-24；按 DATA-12 把那个样本摆进工作区 | 用户说：「算一下 ./broken.txt 的 token 数」 | 回话里报出这个文件解不了码，并指认是哪个文件；没有把它当成 0、也没有跳过不提 | 要读执行过程 |
| TC-31 | usage_multiple_files_total | 验证一次给多个文件时逐个报出并给合计 | 中 | 同 TC-24；按 DATA-13 把两个样本摆进工作区 | 用户说：「./a.txt 和 ./b.txt 加起来一共多少 token？」 | 回话里两个文件各自的数都报了出来（3 与 0），并给出了合计 3；没有只报其中某一个 | 要读执行过程 |
| TC-32 | usage_first_run_no_extra_step | 验证首次运行时技能自己装好引擎，不把安装推给用户 | 中 | 同 TC-24，但 ENV-5 那个干净解释器里没有引擎 | 用户说：「算一下 "你好，世界" 有几个 token」（用户不知道这台机器还没装引擎） | 回话里报回来的 token 数与脚本那一行的数一致（3）；话里没有要求用户先去装什么、也没有把安装动作推给用户 | 要读执行过程 |

## 覆盖项 ↔ 用例对应表

| 覆盖项编号 | 覆盖项描述 | 覆盖它的用例编号 |
|:---|:---|:---|
| TCOV-1 | 由 `--text` 给出非空文本这条来路 | TC-1、TC-2、TC-3、TC-4、TC-5、TC-6、TC-7 |
| TCOV-2 | 由文件路径给出这段文本这条来路 | TC-8、TC-9、TC-10、TC-11、TC-12、TC-13、TC-19 |
| TCOV-3 | 由标准输入给出非空数据这条来路 | TC-14 |
| TCOV-4 | 三种来路都不给，标准输入也为空 | TC-15 |
| TCOV-5 | 文件路径在盘上不存在 | TC-16 |
| TCOV-6 | 文件路径指向一个目录 | TC-17 |
| TCOV-7 | `--text` 与文件路径同时给出，依据未规定听谁的 | TC-18 |
| TCOV-8 | 文件是不带字节顺序标记的 UTF-8 | TC-8、TC-10、TC-11 |
| TCOV-9 | 文件是带字节顺序标记的 UTF-8 | TC-9、TC-12、TC-13 |
| TCOV-10 | 文件不是 UTF-8 的字节序列 | TC-19 |
| TCOV-11 | 文本是纯 ASCII 字符 | TC-1 |
| TCOV-12 | 文本是纯中文 | TC-2 |
| TCOV-13 | 文本含基本平面之外的字符 | TC-3 |
| TCOV-14 | 文本含 DeepSeek 特殊 token 的字面量 | TC-4 |
| TCOV-15 | 文本只由空白字符组成 | TC-5 |
| TCOV-16 | 文本是零字符的空文本 | TC-6 |
| TCOV-17 | 标准输出打印 `tokens:` 与 `chars:` 两行，退出码为 0 | TC-1 |
| TCOV-18 | 不打印这两行，以非零退出码结束 | TC-16、TC-17、TC-19 |
| TCOV-19 | 文本字符数为 0——有序集 A 下边界上的值 | TC-6 |
| TCOV-20 | 文本字符数为 1——有序集 A 边界内侧紧挨着的值 | TC-7 |
| TCOV-21 | 文件字节数为 0——有序集 B 下边界上的值 | TC-10 |
| TCOV-22 | 文件字节数为 1——有序集 B 边界内侧紧挨着的值 | TC-11 |
| TCOV-23 | 带标记文件里标记之后的字符数为 0——有序集 C 下边界上的值 | TC-12 |
| TCOV-24 | 带标记文件里标记之后的字符数为 1——有序集 C 边界内侧紧挨着的值 | TC-13 |
| TCOV-25 | 判定规则 1：引擎已可导入，直接用已装的引擎，不装任何东西 | TC-20 |
| TCOV-26 | 判定规则 2：引擎不可导入、打包 wheel 可用，离线装打包的 wheel | TC-21、TC-22 |
| TCOV-27 | 判定规则 3：引擎不可导入、打包 wheel 也不可用，联网装写死版本 | TC-23 |
| TCOV-28 | 主场景：用户要算一段文本或一个文件的 token 量，技能跑出数并报回来 | TC-24 |
| TCOV-29 | 备选场景：用户只问 token 量，技能报出 token 数 | TC-25 |
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

四门技术的 T 各拿本门的算式核过：等价类 18 条（四个环节各自的有效类、无效类与未规定类相加）、边界值 6 条（三个有序集各取两个值）、判定规则 3 条（三条全可行）、场景 9 条（1 条主场景加 8 条备选场景）。对应表 36 行没有留空，没有不可行项，没有回第 4 步补用例。

## 成品落点

| 成品 | 落的是哪些条目 |
|:---|:---|
| `evals/token-counter-round2/cases/` | 批二（TP-3）落成的九条用例配置：TC-24 至 TC-32，连同它们覆盖的 TCOV-28 至 TCOV-36、TM-4 与 TP-3，以及它们取用的 DATA-2、DATA-5、DATA-6、DATA-12、DATA-13、DATA-14 与 ENV-1、ENV-3、ENV-4、ENV-5、ENV-7、ENV-8 |
| `evals/token-counter-round2/fixtures/` | 三条用例各自的夹具：DATA-6、DATA-12、DATA-13 那几份样本按字节落在这里，夹具目录名跟着用例走 |

**批一（TP-1、TP-2）落成的可跑测试还没落成**：TC-1 至 TC-23，连同它们覆盖的 TCOV-1 至 TCOV-27 与 TM-1 至 TM-3，以及只被那一批取用的 DATA-1、DATA-3、DATA-4、DATA-7、DATA-8、DATA-9、DATA-10、DATA-11、DATA-15 与 ENV-2、ENV-6。

批次那一层的那一份配置放在 `evals/token-counter-round2/` 下、与 `cases/` 并列，它兑现的那几个环境项在每条用例配置的注释里也标了一遍——落成对照照上面那两行查得到。
