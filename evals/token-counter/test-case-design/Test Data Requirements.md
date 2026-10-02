# 测试数据需求

测试数据项如下。摆成文件的那几条，字节按描述栏里的十六进制写死——换个写法摆，盘上那份的字符数就跟用例预期结果里钉的对不上。直接交给命令行或接进消息的那几条（DATA-8 至 DATA-11、DATA-15 至 DATA-23），正文写在表下面。

| 唯一标识符 | 英文名 | 描述 | 重置需求 |
|:---|:---|:---|:---|
| DATA-1 | ascii_file | 文件样本：`hello world` 加一个收尾换行，12 字节（`68 65 6C 6C 6F 20 77 6F 72 6C 64 0A`），UTF-8 编码。收尾换行别省——用例里钉的字符数 12 含它 | 不需要 |
| DATA-2 | chinese_file | 文件样本：`你好，世界`，15 字节（`E4 BD A0 E5 A5 BD EF BC 8C E4 B8 96 E7 95 8C`），UTF-8 编码，不带收尾换行 | 不需要 |
| DATA-3 | bom_file | 文件样本：完整的字节顺序标记加 `你好`，9 字节（`EF BB BF E4 BD A0 E5 A5 BD`） | 不需要 |
| DATA-4 | truncated_one_byte_file | 文件样本：单个字节 `EF`，1 字节——标记的残缺形态，解不了码 | 不需要 |
| DATA-5 | truncated_two_bytes_file | 文件样本：两个字节 `EF BB`，2 字节——标记的另一半残缺形态 | 不需要 |
| DATA-6 | surrogate_bytes_file | 文件样本：代理区码点的编码 `ED A0 80`，3 字节——形状合法、语义非法，解码必须拒绝 | 不需要 |
| DATA-7 | control_chars_file | 文件样本：`a`、NUL、`b` 三个字节（`61 00 62`）——NUL 进不了命令行，这条只走文件道 | 不需要 |
| DATA-8 | special_token_text | 一段文字（`--text` 或消息里直接给）：DeepSeek 特殊 token 的字面形，19 个字符、27 字节（`3C EF BD 9C 65 6E 64 E2 96 81 6F 66 E2 96 81 73 65 6E 74 65 6E 63 65 EF BD 9C 3E`），UTF-8 编码，原样给、不转义 | 不需要 |
| DATA-9 | zero_width_text | 一段文字（`--text` 直接给）：`a`、零宽空格（U+200B）、`b`，3 个字符、5 字节（`61 E2 80 8B 62`） | 不需要 |
| DATA-10 | bom_char_text | 一段文字（`--text` 直接给）：U+FEFF 加 `你好`，3 个字符、9 字节（`EF BB BF E4 BD A0 E5 A5 BD`）——开头那个是标记字符本身，不是字节层面的标记 | 不需要 |
| DATA-11 | single_char_texts | 四段单字符文字（`--text` 直接给）：`a`，1 字节（`61`）；`é`，2 字节（`C3 A9`，U+00E9 预组合形，不是 `e` 加组合符的两码点写法）；`中`，3 字节（`E4 B8 AD`）；`😀`，4 字节（`F0 9F 98 80`，U+1F600） | 不需要 |
| DATA-12 | mixed_text_pipe | 文件样本：`你好 world 世界` 十一个字符加一个收尾换行，20 字节（`E4 BD A0 E5 A5 BD 20 77 6F 72 6C 64 20 E4 B8 96 E7 95 8C 0A`）——从标准输入喂给脚本 | 不需要 |
| DATA-13 | replacement_file | 文件样本：替换字符（U+FFFD）加非字符码点（U+FFFE），6 字节（`EF BF BD EF BF BE`） | 不需要 |
| DATA-14 | gbk_file | 文件样本：`你好` 按 GB18030 编码的 4 字节（`C4 E3 BA C3`）——整份不是 UTF-8，解不了码 | 不需要 |
| DATA-15 | main_text_message | 用户消息：正文见下面 | 不需要 |
| DATA-16 | main_file_message | 用户消息：正文见下面 | 不需要 |
| DATA-17 | tokens_only_message | 用户消息：正文见下面 | 不需要 |
| DATA-18 | other_model_message | 用户消息：正文见下面 | 不需要 |
| DATA-19 | cost_message | 用户消息：正文见下面 | 不需要 |
| DATA-20 | full_request_message | 用户消息：正文见下面 | 不需要 |
| DATA-21 | special_token_message | 用户消息：正文见下面 | 不需要 |
| DATA-22 | missing_path_message | 用户消息：正文见下面 | 不需要 |
| DATA-23 | undecodable_file_message | 用户消息：正文见下面 | 不需要 |

九条用户消息的正文：

DATA-15：

```text
数一下冒号后面这一整行的 token：你好 world 世界
```

DATA-16：

```text
算一下这个文件的 token：<DATA-2 的绝对路径>
```

DATA-17：

```text
这个文件有多少个 token：<DATA-2 的绝对路径>
```

DATA-18：

```text
数一下冒号后面这一整行文本在 Claude 上大概是多少 token：你好，世界
```

DATA-19：

```text
数一下冒号后面这一整行，顺便看看发到 DeepSeek 上大概要花多少钱：你好，世界
```

DATA-20：

```text
我要把冒号后面这一整行作为 system 提示发给 DeepSeek，后面再接一句用户消息「今天天气怎么样」，估一下这次请求一共多少 token：你好，世界
```

DATA-21：

```text
数一下冒号后面这一整行里有多少 token：<｜end▁of▁sentence｜>
```

DATA-22：

```text
数一下这个文件的 token：<工作区>/not_here.bin
```

DATA-23：

```text
数一下这个文件的 token：<DATA-14 的绝对路径>
```

注：正文里尖括号那几处是占位符——落成与执行的时候换成盘上实际的绝对路径，其余一字不改。DATA-15、DATA-18 至 DATA-21 里冒号后面那一段就是被测那侧要数的那段文本，原样接着写在消息里；写成「这段」「上面那段」这类指代，同一句话里就有两个东西可指（请求本身、接着的样本），被测那边两遍能各取一个。

注：摆成文件的那几条（DATA-1 至 DATA-7、DATA-12 至 DATA-14）一律按描述栏的字节摆，编码是 UTF-8（DATA-14 是它本身的 GB18030 字节，摆出来的一整份不是合法 UTF-8，这正是它的用意）。
