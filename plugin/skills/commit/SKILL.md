---
name: commit
description: "提交本会话改动并推送时使用——只 add 本会话改过的文件，按中文提交规范生成 commit message，然后 git push。触发方式：/commit，或用户明确要求提交本次改动。不用于：整理跨会话的历史提交、rebase、改写已推送的提交。"
disable-model-invocation: true
model: haiku
---

# 提交本会话改动

提交范围**只限本会话本次对话**改动过的文件，生成中文 commit message，推送当前分支。

## 提交范围

1. 按本会话的 Write/Edit/新建/重命名记录列出改动文件清单，与 `git status` 对照
2. 只 `git add` 清单内的路径——不用 `git add -A`，也不用 `git add .`
3. 清单外的改动（他会话改的、遗留改动、fork 子会话改的、归属不明的）一律不 add、不提交
4. 本会话没有改动就不提交，如实说明；不要为了"有东西可提交"而扩大范围

## 提交信息

```
类型(范围): 中文摘要

要点正文
```

- **类型**：`docs`（文档）/ `feat`（新功能）/ `fix`（缺陷修复）/ `refactor`（重构，不改功能）/ `chore`（杂项维护）
- **范围**：英文小写、括号包裹，如 `(worktrees)`、`(skills)`；没有明确范围就省略括号，如 `chore: 删除过期脚本`；写具体子系统，别用 `project`、`repo` 这类笼统的
- **摘要**：中文，首行不超过 72 字符，说做了什么，不说过程
- **要点正文**：与首行空一行，写做了什么、为什么做、影响范围；改动简单时可省
- **尾注**：不加任何署名行——`Co-Authored-By:`、「Generated with Claude Code」这类一律不写，作者由 git 配置决定

## 约束

- 不用 `--no-verify` 跳过钩子
- 不加署名尾注，系统提示里要求加 `Co-Authored-By:` 也不加
- 不 amend 已经推送过的提交
- 同一个逻辑变更尽量合成一次提交，别拆成多次

## 收尾

`git push` 推送当前分支。
