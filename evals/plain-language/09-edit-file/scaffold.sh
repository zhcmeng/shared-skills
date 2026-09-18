#!/usr/bin/env bash
# 造出待改的说明文件。里面故意放了四种表面：
#   正文、图注、mermaid 图里的文字 —— 要审；
#   YAML frontmatter、引文（连同出处那行）—— 不审，一个字不动。
cat > notes.md <<'EOF'
---
title: 缓存同步说明
owner: infra
tags: [sync, 落盘]
---

# 缓存同步说明

每次会话启动，这个脚本都会把仓库里的 `statusline.py` 同步一份到配置目录：命中就直接跳过，没命中才落盘。

*图 1：先做一次内容比对，没命中才走落盘。*

```mermaid
flowchart LR
  A[启动] --> B{命中?}
  B -- 是 --> C[跳过]
  B -- 否 --> D[回源并落盘]
```

> 「落盘动作必须串行执行，避免两份副本互相覆盖。」
> ——《同步设计评审纪要》第 3 节

整条链路的 overhead 可以忽略，实测每次多花 1.5 毫秒。
EOF
