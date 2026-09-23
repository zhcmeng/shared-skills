# 测试数据需求

测试项：`skills/token-counter/scripts/count_tokens.py`（DeepSeek token 精确计数脚本）。

各数据项的预期值由官方词表 `tokenizer.json` 按规范语义算出，与测试项的写法无关；执行时拿实际输出与这里的预期值比对。

| 唯一标识符 | 描述 |
|:---|:---|
| DATA-1 | 纯 ASCII 文本：`hello world`。11 个字符，UTF-8 编码 11 字节。预期 `tokens: 2`、`chars: 11` |
| DATA-2 | 纯中文文本：`你好，世界`。5 个字符，UTF-8 编码 15 字节。预期 `tokens: 3`、`chars: 5` |
| DATA-3 | 中英混排文本：`  Hello 世界` + 换行符 + `你好 world  `（开头两个空格、结尾两个空格、中间一个换行符）。21 个字符，UTF-8 编码 29 字节。预期 `tokens: 8`、`chars: 21` |
| DATA-4 | 含基本平面外字符的文本：`ok 😀🎉 done`（两只 emoji 都是 U+1F600 以上，UTF-8 编码各占 4 字节）。10 个字符，UTF-8 编码 16 字节。预期 `tokens: 6`、`chars: 10` |
| DATA-5 | 含 DeepSeek 特殊 token 字面量的文本：`<｜end▁of▁sentence｜>`。开头与结尾是 U+FF5C 全角竖线，中间的分隔符是 U+2581 下八分之一块，不要写成半角竖线或下划线。19 个字符，UTF-8 编码 27 字节。预期 `tokens: 1`、`chars: 19` |
| DATA-6 | 空文本：0 个字符、0 字节。预期 `tokens: 0`、`chars: 0` |
| DATA-7 | 中文开头且含空格的文本：`  中文 开头 的文本 with spaces`（开头两个空格）。23 个字符，UTF-8 编码 37 字节。预期 `tokens: 9`、`chars: 23` |
| DATA-8 | 长文本：把 `你好，世界 hello world ` 重复 20000 遍。360000 个字符，UTF-8 编码 560000 字节。预期 `tokens: 120000`、`chars: 360000` |
| DATA-9 | 单个空白字符文本三份：一个空格（U+0020）、一个换行符（U+000A）、一个制表符（U+0009）。各 1 个字符、1 字节。预期各为 `tokens: 1`、`chars: 1` |
| DATA-10 | DATA-2 与 DATA-4 的「带 U+FEFF 前缀」变体，供 `--text` 用：字符串以 U+FEFF 开头再接正文。`你好，世界` 那一份预期 `tokens: 4`、`chars: 6`；`ok 😀🎉 done` 那一份预期 `tokens: 7`、`chars: 11` |
| DATA-11 | DATA-1 至 DATA-9 的「带 BOM 字节前缀」变体，供文件与标准输入用：UTF-8 字节以 `EF BB BF` 开头再接正文，解码后 BOM 被剥掉，预期值与不带前缀时相同。其中另需单独一份「只有 `EF BB BF` 三个字节、没有正文」的数据，预期 `tokens: 0`、`chars: 0` |
| DATA-12 | 不是合法 UTF-8 的字节串两份：其一为 `FF FE 41 42`（4 字节，含非法起始字节）；其二为 GBK 编码的 `你好，世界`（10 字节）。两份都应触发 `not valid UTF-8` 报错 |
| DATA-13 | 不可读的位置两个：一个不存在的文件路径；一个目录的路径。两个都不要指向真实可读的普通文件 |
| DATA-14 | 官方词表文件 `skills/token-counter/tokenizer.json`：6 367 096 字节，sha256 为 `89085f12ef79460ac5f66d1119325ddfc694b4ab209d80bbd81d35f081dc9614`，词表规模 129280。这个值必须与官方离线包里那份逐字节一致；对不上时全部计数用例的预期值都不可信 |
| DATA-15 | 打包的计数引擎：`skills/token-counter/wheels/tokenizers-0.22.2-cp39-abi3-win_amd64.whl`。供 TC-22、TC-23 使用 |
| DATA-16 | 口径核对用的线上用量：把 DATA-2 的 `你好，世界` 发给 DeepSeek API 后，从返回的 `usage` 里取输入 token 数，预期为 3。供 TC-25 使用 |
