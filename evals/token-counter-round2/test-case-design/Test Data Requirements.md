# 测试数据需求

执行测试规程所需的样本，逐条列出。凡是被用例的「输入」栏按编号指到的，都在这里定义。

| 唯一标识符 | 英文名 | 描述 | 重置需求 |
|:---|:---|:---|:---|
| DATA-1 | ascii_text | 纯 ASCII 文本样本：`hello`，5 个字符、5 个字节 | 不需要 |
| DATA-2 | cjk_text | 纯中文文本样本：`你好，世界`，5 个字符、15 个字节——字符数与字节数在这一条上分得开 | 不需要 |
| DATA-3 | non_bmp_text | 基本平面之外的字符样本：`😀`，1 个字符 | 不需要 |
| DATA-4 | whitespace_text | 只由空白组成的样本：3 个半角空格 | 不需要 |
| DATA-5 | special_token_text | 含 DeepSeek 特殊 token 字面量的样本：`<｜end▁of▁sentence｜>` | 不需要 |
| DATA-6 | plain_utf8_file | 不带字节顺序标记的 UTF-8 文件 `sample.txt`，正文与 DATA-2 相同 | 不需要 |
| DATA-7 | bom_file | 带字节顺序标记的 UTF-8 文件，标记之后正文与 DATA-2 相同 | 不需要 |
| DATA-8 | zero_byte_file | 0 字节的空文件 | 不需要 |
| DATA-9 | one_byte_file | 1 个字节的文件，内容是 `a` | 不需要 |
| DATA-10 | bom_only_file | 只有 3 个字节顺序标记、标记之后没有正文的文件 | 不需要 |
| DATA-11 | bom_plus_one_char_file | 3 个标记字节之后跟一个 `a` 的文件 | 不需要 |
| DATA-12 | not_utf8_file | 含非 UTF-8 字节的文件 `broken.txt`：写入 `0xFF 0xFE` 两个字节，再跟一段正常 UTF-8 正文 | 不需要 |
| DATA-13 | multi_file_samples | 两个文件：`a.txt` 正文与 DATA-2 相同；`b.txt` 是 0 字节空文件 | 不需要 |
| DATA-14 | chat_turn_text | 一整轮对话的正文，三条消息：system 一条、user 一条、assistant 一条，各带角色前缀。正文见下面 | 不需要 |
| DATA-15 | stdin_text | 管道输入的内容，与 DATA-2 相同 | 不需要 |

**DATA-14 的正文**：

```text
system: 你是一个简洁的助手。
user: 你好
assistant: 你好，有什么可以帮你的？
```

**样本文件按上面写明的字节造**：DATA-6 至 DATA-13 是文件类样本，落成夹具时按描述栏写明的字节逐一写出，不按语义改写。DATA-12 那一处尤其不能「写成合法 UTF-8」——它要的就是解不了码。

**这些样本都不改测试项的状态**：它们是被读进去的输入，跑完之后原样留着即可，没有复位动作。
