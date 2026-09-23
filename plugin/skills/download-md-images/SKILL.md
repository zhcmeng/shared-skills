---
name: download-md-images
description: "Markdown 里的图片还指向远程网址、要存到本地时使用——下载到 md 同目录的 images/ 下并改写为相对路径，正文的 ![](http…) 与 HTML img 标签两种引用都认；多文件批量按目录去重，同一张图只下一次。触发词：图片下载、图片本地化、download images、image download、defuddle 后处理。不用于：把网页抓成 Markdown（那是 defuddle 的活）、把 Markdown 导出成 PDF（用 md-export）。"
argument-hint: "<md 文件路径…> 或 <网页 URL>"
---

# Markdown 图片本地化

把 Markdown 里还指向远程网址的图片下载到本地：存进 md 文件所在目录的 `images/`，引用改写为相对路径。正文里的 `![](http...)` 和 HTML `<img src="http...">` 两种写法都认。

`defuddle parse` 只产出正文文本，图片引用仍指着原网址；网页存档、素材落盘也会留下这类远程图片。跑一遍这个脚本，图片就跟着文档走，断网也看得到。

## 使用

脚本在本 skill 目录的 `scripts/` 下；先定位到该目录，再用绝对路径调用。

### 本地化已有 Markdown 的图片（单文件 / 多文件批量）

```bash
python <skill目录>/scripts/download_md_images.py <md文件路径> [更多md文件...]
```

### 下载网页并一步本地化（defuddle + 图片本地化）

```bash
python <skill目录>/scripts/web_download.py <url> -o <out.md>
```

等价于先跑 `defuddle parse <url> --markdown -o <out.md>`，再对其产物执行上面的本地化，故需 `defuddle` 在 PATH（检查：`command -v defuddle`）。只想要 defuddle 原文、暂不下载图片：加 `--no-images`。

## 行为

- 同时识别 markdown `![](http...)` 与 HTML `<img src="http...">` 两种远程图片引用；HTML `<img>` 整标签改写为 markdown `![](...)` 语法
- 图片保存为 `<md所在目录>/images/image_NNN.ext`，引用统一改写为相对路径 `images/<本地文件名>`
- **同目录全局去重**：同目录多文件共享图片计数器与网址→文件名映射——相同网址跨文件、同文件内均只下载一次；序号按目录已有最大编号续接，互不覆盖
- 单张下载失败：保留原引用不动，仅追加注释 `<!-- REMOTE_IMAGE:下载失败 -->`，继续处理其余图片
- 结束输出 `Done: N images downloaded`（N = 本轮新下载数）。无远程图片的文件不改写、输出 `no remote images:` 提示；单张失败输出 `FAIL` 行（stderr）

## 自检

测试与样例素材在本 skill 目录的 `tests/` 下：

```bash
python <skill目录>/tests/test_download_md_images.py
```

覆盖两种引用的识别、扩展名推断（带查询串的网址、无扩展名默认 `.png`）、frontmatter 里 `source_url` 取作 Referer。
