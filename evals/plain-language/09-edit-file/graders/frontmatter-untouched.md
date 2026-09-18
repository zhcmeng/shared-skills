---
type: llm
focus: { source: file, path: notes.md }
---
通过的条件：文件开头的 YAML frontmatter 原样没动——title、owner、tags 三行还是原来的内容，tags 里的"落盘"也照旧留着。

frontmatter 不审：里面的词要读者解码也不改。动了其中任何一个字，就不通过。
