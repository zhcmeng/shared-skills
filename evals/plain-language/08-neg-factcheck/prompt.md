---
max_turns: 12
timeout_seconds: 180
allowed_tools: [Skill, Read, Glob]
model: opus
runs: 3
---
帮我核对一下，这几个数对不对？

我们的结论：A 方案比 B 方案快 40%，内存少用 25%，迁移窗口只要 15 分钟。

原始数据：
- A 方案 12 秒，B 方案 20 秒
- A 方案峰值内存 600MB，B 方案 800MB
- 迁移窗口 45 分钟
