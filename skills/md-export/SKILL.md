---
name: md-export
description: "把 Markdown 导出成 PDF（或 HTML）时使用——按 Markdown Preview Enhanced 的预览主题渲染，支持表格、数学公式、代码块与本地图片，产出样式与编辑器里手动导出的一致。触发词：导出 PDF、转 PDF、生成 PDF、打印这份文档、导出成 HTML、md 转 pdf。不用于：PDF 转 Markdown（用 pdf-to-md）、抓取网页正文（用 defuddle）、生成图表（用 chart-generator）。"
argument-hint: "<Markdown 文件或目录路径> [-Theme 主题] [-Paper letter|a4] [-Out 输出路径] [-Html]"
---

# Markdown 导出 PDF

把一份或多份 Markdown 导出为 PDF。渲染在浏览器里完成，产出默认落在 Markdown 同目录、同名 `.pdf`。

## 依赖

**只有一个：Chromium 内核浏览器。** Chrome 优先，没有则用 Edge（Windows 自带）。

不需要 Node、Python、pandoc，也不需要安装任何 npm 包，全程不联网。渲染器、公式排版、主题样式都随本 skill 携带在 `assets/` 下。

## 用法

```powershell
# 单个文件（输出到同目录同名 .pdf）
scripts/export.ps1 <Markdown 路径>

# 整个目录（递归导出其中所有 .md）
scripts/export.ps1 <目录路径>

# 指定主题与纸张
scripts/export.ps1 <路径> -Theme newsprint -Paper a4

# 只出 HTML，不打印 PDF
scripts/export.ps1 <路径> -Html

# 指定输出路径（仅单文件）
scripts/export.ps1 <路径> -Out D:\out\手册.pdf
```

| 参数 | 默认 | 说明 |
|:---|:---|:---|
| `-Path` | 必填 | Markdown 文件或目录；目录会递归处理所有 `.md` |
| `-Theme` | `github-light` | 主题名，对应 `assets/themes/<名>.css`，共 18 个可选 |
| `-Paper` | `letter` | `letter` 或 `a4` |
| `-Out` | 同目录同名 | 输出路径，仅单文件时可用 |
| `-Html` | 关 | 只生成 HTML，不打印 PDF |

批量导出时，脚本逐个文件输出 `✓/✗` 与页数，最后汇总成功数。约 2 秒一个文件。

## 渲染口径

导出结果对齐 Markdown Preview Enhanced 的默认行为，这样产出与编辑器里「导出 → Chrome (Puppeteer)」一致：

| 项 | 取值 | 说明 |
|:---|:---|:---|
| 渲染器 | markdown-it，`breaks: true` | 对应 MPE 的 `breakOnSingleNewLine`：单换行渲染为换行，不是空格 |
| 主题 | `github-light.css` | 对应 MPE 的 `previewTheme` 默认值 |
| 公式 | KaTeX | 对应 MPE 的 `mathRenderingOption` 默认值 |

**数学公式的处理**：公式在交给 Markdown 渲染器之前先被抽成占位符，渲染完成后再换回 KaTeX 的排版结果。这一步是必需的——`$a_1 + a_2$` 这类公式里的 `_`、`^`、`\` 会被 Markdown 当成强调与转义语法吃掉。文档里没有公式时，KaTeX 的样式与脚本不会写进 HTML。

**图片**：临时 HTML 写在 Markdown 同目录，因此文档里的相对图片路径按原样解析。导出结束后临时文件被删除，正常情况不会留下痕迹。

## 已知边界

以下语法本轮不处理，遇到会按普通文本或原始代码显示：

- **mermaid 图表**——` ```mermaid ` 代码块会原样显示为代码，不渲染成图
- **`[[wiki 链接]]`**——按普通文本处理
- **`[TOC]`**——不展开为目录
- **代码高亮**——代码块有等宽字体与底色，但不做语法着色
- **MPE 扩展语法**——admonition、`==高亮==` 等

## 目录结构

```
SKILL.md
scripts/export.ps1              编排：参数 → 组装 HTML → 浏览器打印
assets/vendor/                  渲染器与公式库（随 skill 携带）
assets/themes/                  18 个预览主题
assets/THIRD-PARTY-NOTICES.md   第三方组件来源与许可证
```
