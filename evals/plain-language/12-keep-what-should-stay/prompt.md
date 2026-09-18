---
max_turns: 12
timeout_seconds: 180
allowed_tools: [Skill, Read, Glob]
model: opus
runs: 3
---
下面是你刚才给我的回答，我原样贴过来：

【
这个工具的天花板不高，但护城河是有的：它把每次会话的记忆写进 `.claude/memory/`，下次开会话再读回来。同类产品在这条赛道上还没解决「查 memory 要等多久」的问题。

对外接口是 REST API，返回的都是 JSON。行业报告说这块市场的规模占 GDP 的千分之几——具体怎么算的先别管，反正盘子不大。

这套机制的 overhead 主要在序列化上。
】

看不懂，重说一遍。
