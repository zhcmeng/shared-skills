---
name: token-counter
description: 当用户需要精确计算 DeepSeek 文本或文件的 token 数量时使用（触发词：算token、token量、token数、token计数、几个token、DeepSeek 计费/API 预算、这个文件多少token）。支持两种输入：一段文本、一个文件（.md/.txt/代码等 UTF-8 文本）。只精确覆盖 DeepSeek 官方 tokenizer（当前 V4），不覆盖 Claude 等其他模型。
---

# DeepSeek Token 精确计数

用 DeepSeek 官方 tokenizer（离线 tokenizer.json）精确计算一段文本或一个文件的 token 数，用于 API 调用前的预算估算。

## 用法

脚本位置：`scripts/count_tokens.py`（在本 skill 目录下；先定位到该目录，脚本用绝对路径调用）。

```bash
# 一段文本
python <skill目录>/scripts/count_tokens.py --text "你好，世界"
# 一个文件
python <skill目录>/scripts/count_tokens.py ./pages/某页面.md
# 管道输入
cat file.txt | python <skill目录>/scripts/count_tokens.py
```

输出两行：`tokens: N`（DeepSeek token 精确数）与 `chars: M`（UTF-8 字符数）。用户只问 token 量时，报告 `N` 即可。

skill 完全自包含，首次运行无需联网：官方词表已入库（`tokenizer.json`，随 skill 分发），引擎 wheel 已打包（`wheels/`）。目标机未装 `tokenizers` 时脚本自动安装：优先装打包 wheel（离线、`--no-deps`——该引擎从本地文件加载不 import `huggingface_hub`，已在无该库的干净 venv 实测通过），仅当平台不符（非 Windows x64 / CPython <3.9）才联网 `pip install tokenizers==0.22.2` 兜底。

## 口径与边界（务必遵守）

- **口径 = tokenizer.json 规范语义**（`tokenizers.Tokenizer.from_file` 引擎），与官方文档下载的 tokenizer 包一致。**不要**改用 `transformers.AutoTokenizer` 加载（其 legacy 兼容路径在含空格/中文文本上与规范语义不一致，纯中文开头甚至会编出空序列）。
- **计费以 API 返回的 `usage` 为准**（官方文档口径）。离线计数用于事前估算；若与账单有出入，以线上 `usage` 为准。
- **离线无法计算缓存命中**：`prompt_cache_hit_tokens` 取决于服务端缓存状态，估算 API 成本时须向用户说明这一点。
- 只覆盖 DeepSeek 当前官方 tokenizer。涉及 Claude 等其他模型时，明确说明本 skill 不覆盖（Anthropic 无公开离线 tokenizer，不提供近似估算误导用户）。
- 文本中的 DeepSeek 特殊 token（如 `<｜end▁of▁sentence｜>`）按官方词表计入；若估算完整对话请求，需自行按 `tokenizer_config.json` 的 chat_template 拼装后再计数。

## 官方换版时的维护

官方词表随 skill 分发（不再走首次下载），引擎 wheel 随 skill 打包。官方更新 tokenizer（文件名含版本号）后：

1. 从官方离线包解出新的 `tokenizer.json`，替换 skill 根目录同名文件（保持 sha256 与官方 zip 一致）；
2. 引擎升版时：从 PyPI 下载新版 wheel 放入 `wheels/`（替换旧的），并把脚本中 `PINNED` 改为对应版本号（联网兜底安装用）；已装的旧版引擎不强制升级。

来源：官方离线 tokenizer 说明见 https://api-docs.deepseek.com/quick_start/token_usage/（Calculate token usage offline）。
