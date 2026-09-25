# 测试数据需求

执行四条测试规程所需的数据，逐条列出。样本里的字符数与 token 数都按 ENV-2 那份随包词表算出来，用例里的预期值以这两栏为准。

| 唯一标识符 | 英文名 | 描述 | 重置需求 |
|:---|:---|:---|:---|
| DATA-1 | cjk_literal | 正文样本：`你好，世界`。5 个字符，按 UTF-8 编码占 15 字节；按随包词表算出 3 个 token | 不需要 |
| DATA-2 | ascii_words | 正文样本：`The quick brown fox jumps over the lazy dog`。43 个字符、43 字节、9 个 token | 不需要 |
| DATA-3 | mixed_cjk_ascii | 正文样本：`中文和 English 混排`。14 个字符、24 字节、6 个 token | 不需要 |
| DATA-4 | official_special_token | 正文样本：`<｜end▁of▁sentence｜>`。19 个字符、27 字节、1 个 token——这是官方词表里的特殊 token，整体算一个 | 不需要 |
| DATA-5 | whitespace_only | 正文样本：3 个空格、1 个换行、1 个制表符、1 个换行、2 个空格。8 个字符、8 字节、3 个 token。里面的换行与制表符要真的传进去：交给 `--text` 时照 `--text "$(printf '   \n\t\n  ')"` 这样生成——外壳里直接写 `\n`、`\t` 是两个反斜杠开头的字面字符，不是换行与制表符，照抄会数出 `tokens: 6`、`chars: 11` | 不需要 |
| DATA-6 | code_text | 正文样本（代码）：一行 `def add(a, b):`，接着一行缩进 4 格的 `return a + b`，两行都以换行收尾。32 个字符、32 字节、12 个 token | 不需要 |
| DATA-7 | astral_plane_text | 正文样本：`emoji 😀 与中文混排`。13 个字符，按 UTF-8 编码占 26 字节（那个 emoji 占 4 字节）；9 个 token | 不需要 |
| DATA-8 | padded_spaces | 正文样本：` hello world `，首尾各一个空格。13 个字符、13 字节、3 个 token | 不需要 |
| DATA-9 | markdown_file | Markdown 文件样本：依次是一行 `# 标题 Demo`、一个空行、一行 `The quick brown fox jumps over the lazy dog`、一行 `你好，世界`，末尾再一个换行；行尾都是 LF。61 个字符、75 字节、19 个 token | 不需要 |
| DATA-10 | bom_file | 带编码标记的文件样本：开头 3 个字节 0xEF 0xBB 0xBF，后面接「中文测试」这 4 个字符的 UTF-8 字节，共 15 字节。读进来去掉开头 3 个字节之后是 4 个字符、2 个 token | 不需要 |
| DATA-11 | not_utf8_bytes | 字节不是合法 UTF-8 的样本：「中文测试」的 GBK 编码，8 个字节：0xD6 0xD0 0xCE 0xC4 0xB2 0xE2 0xCA 0xD4。同一份字节既当文件样本，也当标准输入样本用 | 不需要 |
| DATA-12 | empty_file | 空文件样本：0 字节 | 不需要 |
| DATA-13 | bom_only_file | 只有编码标记的文件样本：3 个字节 0xEF 0xBB 0xBF | 不需要 |
| DATA-14 | truncated_bom_file | 截断的编码标记样本：2 个字节 0xEF 0xBB | 不需要 |
| DATA-15 | bom_plus_one_byte_file | 编码标记后接一个字节的文件样本：4 个字节 0xEF 0xBB 0xBF 0x61（最后一个字节是小写字母 a）。读进来去掉开头 3 个字节之后是 1 个字符、1 个 token | 不需要 |
| DATA-16 | single_cjk_char | 正文样本：`中`。1 个字符，按 UTF-8 编码占 3 字节；1 个 token | 不需要 |
| DATA-17 | literal_bom_text | 正文样本（字面文本）：以 U+FEFF 开头，后面接「中文测试」，共 5 个字符；按 UTF-8 编码占 15 字节，与 DATA-10 那个文件的字节序列完全相同。交给 `--text` 时开头那个字符要真的生成出来，照 `--text "$(printf '\xef\xbb\xbf')中文测试"` 这样写。`--text` 给什么就数什么，`utf-8-sig` 只在读文件那一路上生效，所以开头的 U+FEFF 会算进正文——按随包词表是 3 个 token。这比 DATA-10 走文件通道得到的 2 个 token 多，两处的分歧见 TC-15 | 不需要 |
