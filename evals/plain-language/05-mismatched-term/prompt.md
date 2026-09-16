---
max_turns: 12
timeout_seconds: 180
allowed_tools: [Skill, Read, Glob]
model: opus
runs: 3
---
下面是你刚才给我的回答，我原样贴过来：

【
这套机制内部叫「缓存预热」，做法是给每个请求打一个时间戳，按时间窗口把请求切成一批一批，窗口之外的请求直接丢掉。好处是内存占用稳定，不会随着流量上涨而线性增长。
】

重说一遍。
