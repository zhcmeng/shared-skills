# 测试数据需求

| 唯一标识符 | 英文名 | 描述 | 重置需求 |
|:---|:---|:---|:---|
| DATA-1 | text_chinese | 一段纯中文文本，五个字符。正文见下面。 | 不需要 |
| DATA-2 | file_utf8_no_bom | 文件样本 `sample_utf8_no_bom.txt`，放在被测那侧读得到的工作目录里。内容是 DATA-1 那段正文，按不带字节顺序标记的 UTF-8 存，文件 15 字节。 | 不需要 |
| DATA-3 | text_ascii | 一段纯 ASCII 文本，十二个字符，中间有一个逗号和一个空格。正文见下面。 | 不需要 |
| DATA-4 | file_utf8_with_bom | 文件样本 `sample_utf8_bom.txt`，放在被测那侧读得到的工作目录里。内容是 DATA-1 那段正文，前面带一个 UTF-8 的字节顺序标记（三个字节 `EF BB BF`），文件 18 字节。 | 不需要 |
| DATA-5 | file_not_utf8 | 文件样本 `sample_not_utf8.bin`，放在被测那侧读得到的工作目录里。内容是一段不是合法 UTF-8 的字节序列：先写 `abc` 三个字节，再写一个孤立的 `0xFF` 字节，最后写一个 `0xFE` 字节，共 5 字节。这个字节序列在任何位置都解不成 UTF-8 字符。 | 不需要 |
| DATA-6 | skill_copy_without_wheel | 测试项的一份副本，摆在临时目录里：除了 `wheels/` 目录留空之外，其余文件与技能目录逐字节一致（`scripts/count_tokens.py`、`tokenizer.json` 都在）。给 TC-16 用——这一条要的是「走不到随包 wheel 那一步」这个情形。 | 每次跑之前重建：跑完删掉，下次跑重新从技能目录拷一份、把 `wheels/` 清空 |
| DATA-7 | text_special_token | 一段只由一个 DeepSeek 特殊 token 字面量组成的文本，十九个字符。正文见下面。 | 不需要 |
| DATA-8 | text_whitespace_only | 一段只由三个半角空格组成的文本，没有别的字符。正文见下面。 | 不需要 |
| DATA-9 | text_empty | 一段零字符的空文本，里面一个字符都没有。正文见下面。 | 不需要 |
| DATA-10 | file_empty | 文件样本 `sample_empty.txt`，放在被测那侧读得到的工作目录里。0 字节，里面什么都没有。 | 不需要 |
| DATA-11 | file_one_byte | 文件样本 `sample_one_byte.txt`，放在被测那侧读得到的工作目录里。1 字节，内容是半角小写字母 `a`，没有换行。 | 不需要 |
| DATA-12 | text_one_char | 一段只有一个字符的文本，内容是半角小写字母 `a`。正文见下面。 | 不需要 |
| DATA-13 | dialogue_round | 一整轮对话的消息正文，两条用户消息夹一条助手回话。给 TC-22 用。正文见下面。 | 不需要 |

下面这几段是正文，落成的时候照抄，不要改写：

**DATA-1**（五个字符，纯中文）

```
你好，世界
```

**DATA-3**（十二个字符，纯 ASCII）

```
Hello, world
```

**DATA-7**（十九个字符，一个特殊 token 字面量）

```
<｜end▁of▁sentence｜>
```

**DATA-8**（三个半角空格）

```
   
```

**DATA-9**（零字符）

```
```

**DATA-12**（一个字符）

```
a
```

**DATA-13**（一整轮对话的消息正文）

```
user: 帮我看下这段循环有没有问题
assistant: 贴出来看看
user: for i in range(10): print(i)
```

注：这几个正文块外面那两行三个反引号是标记，不属于正文——DATA-8 那一段正文就是三个空格，DATA-9 那一段正文一个字符都没有。凡是逐字比对字符数的用例（TC-1、TC-3、TC-8、TC-9、TC-10、TC-13），落成时按这一段给的内容原样摆，不要在末尾添换行。
