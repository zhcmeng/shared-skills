# 测试数据需求

这几条数据项供测试规程执行时取用。前五条是一段文字而不是文件，正文写在表下面；其余是文件样本，按描述栏写明的字节造。

| 唯一标识符 | 英文名 | 描述 | 重置需求 |
|:---|:---|:---|:---|
| DATA-1 | data_ascii_single_char | 一段文本，内容是 1 个 ASCII 字符；正文见下面 | 不需要 |
| DATA-2 | data_cjk_five_chars | 一段文本，内容是 5 个中文字符；正文见下面 | 不需要 |
| DATA-3 | data_astral_emoji | 一段文本，内容是 1 个基本平面之外的字符；正文见下面 | 不需要 |
| DATA-4 | data_three_spaces | 一段文本，内容是 3 个半角空格；正文见下面 | 不需要 |
| DATA-5 | data_special_token_literal | 一段文本，内容是 DeepSeek 特殊 token 的字面量；正文见下面 | 不需要 |
| DATA-6 | data_file_plain_utf8 | 一个样本文件，内容为 DATA-2 那段文本按 UTF-8 编码的字节，共 15 字节，开头不带字节顺序标记 | 不需要 |
| DATA-7 | data_file_utf8_with_bom | 一个样本文件，内容为 DATA-6 的字节前面加上三个字节的字节顺序标记（`EF BB BF`），共 18 字节 | 不需要 |
| DATA-8 | data_file_zero_bytes | 一个样本文件，内容为空，共 0 字节 | 不需要 |
| DATA-9 | data_file_one_byte | 一个样本文件，内容为 1 个 ASCII 字符，共 1 字节 | 不需要 |
| DATA-10 | data_file_bom_only | 一个样本文件，内容只有三个字节的字节顺序标记（`EF BB BF`），共 3 字节 | 不需要 |
| DATA-11 | data_file_bom_plus_one_byte | 一个样本文件，内容为三个字节的字节顺序标记后面跟 1 个 ASCII 字符，共 4 字节 | 不需要 |
| DATA-12 | data_file_not_utf8 | 一个样本文件，内容是「你好」两个中文字符按 GBK 编码的字节（`C4 E3 BA C3`），共 4 字节；这串字节按 UTF-8 解不开 | 不需要 |
| DATA-13 | data_path_missing | 一个文件路径，指向盘上不存在的位置 | 不需要 |
| DATA-14 | data_path_is_dir | 一个目录路径，取技能目录本身 | 不需要 |
| DATA-15 | data_fake_wheel | 一个假的引擎 wheel：文件名与随技能打包的那个真 wheel 同名同版本，但平台标记改成与当前平台不匹配（例如把平台标记那段改成另一套平台的写法）；照它的文件名造一个空文件即可 | 要复位：跑完把 `wheels/` 恢复成原样——假 wheel 拿掉，原来那个真 wheel 放回去 |

DATA-1 的正文：

```
a
```

DATA-2 的正文：

```
你好，世界
```

DATA-3 的正文：

```
😀
```

DATA-4 的正文：3 个半角空格字符（Unicode 码位 U+0020），逐个字节就是 `20 20 20`。这一条不写成代码块——代码块里的空格读不出个数，照上面这串码位取。

DATA-5 的正文：

```
<｜end▁of▁sentence｜>
```
