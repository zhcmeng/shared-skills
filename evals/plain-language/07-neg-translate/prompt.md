---
max_turns: 12
timeout_seconds: 180
allowed_tools: [Skill, Read, Glob]
model: opus
runs: 3
---
帮我把下面这段翻成中文，客户那边要看，翻得准一点。

The connection pool reuses idle sockets for up to 30 seconds. If all sockets are busy, new requests wait in a queue; when the queue is full, the request fails immediately instead of blocking.
