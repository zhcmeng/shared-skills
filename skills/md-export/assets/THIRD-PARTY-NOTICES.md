# 第三方组件声明

本 skill 的 `assets/` 下携带三份第三方资源。它们随 skill 一起分发，使导出过程不依赖网络，也不依赖任何本机已安装的编辑器。

## markdown-it

- 文件：`vendor/markdown-it.min.js`、`vendor/markdown-it.LICENSE`
- 版本：15.0.2
- 用途：把 Markdown 渲染为 HTML
- 许可证：MIT
- 来源：npm 包 `markdown-it` 的 `dist/browser/markdown-it.umd.min.js`

## KaTeX

- 文件：`vendor/katex.min.js`、`vendor/katex.min.css`、`vendor/katex.LICENSE`
- 版本：0.16.47
- 用途：数学公式排版
- 许可证：MIT，Copyright (c) 2013-2020 Khan Academy and other contributors
- 来源：npm 包 `katex` 的 `dist/`

`katex.min.css` 经过一次处理：把 20 个 `.woff2` 字体文件以 base64 data URI 内嵌进样式表，并删去 `.woff` / `.ttf` 回退项。这样做是为了让生成的 HTML 完全自包含——临时 HTML 会被写到 Markdown 同目录，不能再牵扯一套字体目录。Chromium 内核浏览器均支持 woff2，不影响渲染结果。

升级 KaTeX 时需重做这一步：取新版本 `dist/katex.min.css` 与 `dist/fonts/`，把每处

```
url(fonts/<名>.woff2) format("woff2"),url(fonts/<名>.woff) format("woff"),url(fonts/<名>.ttf) format("truetype")
```

替换为

```
url(data:font/woff2;base64,<该 woff2 的 base64>) format("woff2")
```

并确认样式表中不再残留 `url(fonts/...)`。

## 预览主题

- 文件：`themes/*.css`（18 个主题）、`themes/LICENSE-NCSA.md`
- 用途：PDF 的版式与配色；默认 `github-light.css`
- 许可证：University of Illinois/NCSA Open Source License，Copyright (c) 2017 Yiyi Wang
- 来源：Markdown Preview Enhanced（`shd101wyy.markdown-preview-enhanced`）的 `crossnote/styles/preview_theme/`

收录这些主题是为了让导出的 PDF 与 Markdown Preview Enhanced 里「导出 → Chrome (Puppeteer)」的观感一致。脚本复现了它的关键渲染开关：`breakOnSingleNewLine`（单换行渲染为换行）、`previewTheme`（默认 `github-light.css`）、`mathRenderingOption`（KaTeX）。
