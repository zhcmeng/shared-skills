---
max_turns: 12
timeout_seconds: 180
allowed_tools: [Skill, Read, Glob]
model: opus
runs: 3
---
下面是你刚才给我的回答，我原样贴过来：

【
读 `verdict.json` 的 `final_reason`，对着下面的字样找。方括号里的字面文本可以直接拿去搜。

| 判定顺序 | `final` | `final_reason` 长什么样 |
|:---|:---|:---|
| ① 框架自己崩过 | `error` | `quorum error (阶段): 消息` |
| ② 有 pre-check 没过 | `indeterminate` | `pre-check(s) failed: 检查名` |
| ⑦ 考官判 pass、post-check 全过 | `pass` | `Gauntlet-Agent passed; N post-check(s) passed` |

七种图案分的是"该修哪一方"，不是"结论是什么"。先看判定形状缩小范围，再核对细节。

最常见的是图案 2 还是图案 4：两者的判定形状完全一样——`fail` + 考官判 pass + 一条 post-check 失败。
分界线只有一句：这条检查本身对不对？把失败的检查拿去跑一个已知合格的产物，
在合格样本上它通过 → 图案 2；它照样失败 → 图案 4。
】

看不懂，重说一遍。
