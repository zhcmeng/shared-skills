# 评测用例：给文件路径要 token 数时，把路径交给脚本、报准数

## 这条用例防的是什么

用户指的是一个文件。这时容易走成两条歪路：把文件读进上下文自己数；或者读完之后只把正文贴给脚本——文件那条通道就这么让开了。技能正文的「用法」里三条通道（字面文本、文件路径、管道）是并列的，文件那条就是把路径交给脚本，脚本自己按 `utf-8-sig` 读，开头若有编码标记它会去掉。

判两件事：命令里把那个文件路径交给了技能目录下的脚本；报回来的数与脚本对这份文件算出来的一致。

## 怎么跑

1. 把 `plugin/skills/token-counter/` 整套当作使用者机器上装好的这门技能交给 agent（ENV-10），与它平时装了这门技能时一样。工作目录设在本仓库根——样本文件的路径从这儿写起。
2. 发下面这条用户消息。样本文件在 `evals/token-counter/cases/tp05-07-TC-35-file_request_counts_exactly/fixture/样本.md`，内容是 DATA-9 那段（含中文与英文的 Markdown），脚本对它报 `tokens: 19`、`chars: 61`。
3. 只取第一条回复（ENV-11），连同它这一轮执行的命令，按 `graders/file-channel-count.md`（ENV-13）判。

用户消息：

```
/shared-skills:token-counter 这个文件有多少 token？evals/token-counter/cases/tp05-07-TC-35-file_request_counts_exactly/fixture/样本.md
```

## 基线证据

还没跑。这一条是刚写出来的设计与判据，跑第一遍之后把结果补到这里：跑了几次、几次过、坏的那几次原话是什么。

## 规格说明里的对应

用例 TC-35（模型 TM-7 的备选场景「用户指一个文件」，排在规程 TP-5 里），覆盖项 TCOV-52（备选场景：用户指一个文件）；用户消息是 DATA-23，样本文件按 DATA-9 的字节造。两份规格说明在 `evals/token-counter/test-case-design/` 下。
