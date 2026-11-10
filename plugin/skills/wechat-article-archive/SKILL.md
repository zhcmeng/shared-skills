---
name: wechat-article-archive
description: 使用时机：用户给出 mp.weixin.qq.com 链接，或说「下载这篇公众号文章」「把这篇文章归档」「微信文章存下来」时。也用于抓公众号正文却只拿到空壳——正文是空的、只剩「视频 小程序 赞 在看」这类零散字样，或页面标题是「环境异常」。
---

# 微信公众号文章归档

把一篇 mp.weixin.qq.com 的文章完整取下来：正文转 Markdown、图片存本地、逐字核对无缺失。

**产物落在调用方给的输出目录**，本技能只管取正文、转换、核对、图片本地化四步。目录怎么命名、正文文件头怎么写、要不要跑工程自己的检查，由调用方按自己的规则处理。

`<skill目录>` 就是本文件所在目录。命令里的 `python` 在只装了 `python3` 的机器上换成 `python3`；转换与核对脚本依赖 `beautifulsoup4`、`markdownify`、`lxml`。

```
<输出目录>/
├── article.content.html   # 第一步：渲染后的正文 HTML
├── article.meta.json      # 第一步：标题、公众号、作者、发布时间
├── body.md                # 第二步：转换后的正文
└── images/                # 第四步：本地图片
```

**核心问题**：公众号对非浏览器访问一律返回「环境异常」验证页，抓到的正文是**空壳**——只剩「视频 小程序 赞 在看」这类零散字样。curl、WebFetch、defuddle、无头 Chrome 全都一样，试到哪个都是空壳。**只有带调试端口的真实 Chrome 过得去**，所以取正文这步必须走 CDP，别在别的路上耗时间。

## 第一步：取正文

```bash
node <skill目录>/scripts/fetch_article.mjs "<url>" "<输出目录>"
```

脚本自己拉起 Chrome（专用 profile，登录态跨次复用）并轮询等正文渲染出来；输出目录不存在会自己建。产物：`article.content.html`、`article.meta.json`。

- **需要 Node 22 以上**：脚本靠 Node 内置的 `WebSocket` 连调试端口，不装任何依赖（该全局对象自 v22.0.0 起默认启用，见 https://nodejs.org/api/globals.html 的 `Class: WebSocket`）。
- **退出码 2** = 页面弹了验证。Chrome 窗口开着，请用户在里面过一下验证再重跑；脚本会一直等到超时。
- URL 里的 `poc_token` 会被去掉再访问——那是会过期的临时通行证，不入归档。
- **完成判据**：`article.meta.json` 的 `title` 与 `publishTime` 都有值，`article.content.html` 是几十万字节量级。

## 第二步：转 Markdown

```bash
python <skill目录>/scripts/wechat_to_md.py "<输出目录>/article.content.html" "<输出目录>/body.md"
```

**不要用 defuddle 或通用正文提取代替**：它们按网页正文打分，会把公众号里当内容用的元素当样板丢掉——实测一篇 21 张图的文章被吃掉 1 张，而那张正是列章节的清单图。归档要逐字保真，这个脚本针对微信排版自己转。

**完成判据**：打印的图片数等于源 HTML 里**带真实地址的** `<img>` 个数。直接数 `<img>` 会多算——微信会留一批既没 `src` 也没 `data-src` 的空占位，那不是图。HTML 还是单行，`grep -c` 数的是行数、只会返回 1，所以这样数：

```bash
grep -o 'data-src="[^"]*"' "<输出目录>/article.content.html" | wc -l
```

## 第三步：核对保真

```bash
python <skill目录>/scripts/verify_fidelity.py "<输出目录>/article.content.html" "<输出目录>/body.md"
```

**完成判据**：输出「缺失片段 0 个」，且多出的字符只限 `*`（加粗）、`>`（引用）、`-`（表格分隔线）、数字与 `.`（有序列表序号）。出现别的字符说明转换掺了东西。**有缺失就不要往下走**：停下来报告，不要继续归档；确认是转换脚本的问题后再改脚本。

## 第四步：图片本地化

用所装插件里的 `download-md-images` 技能处理 `<输出目录>/body.md`（作为 shared-skills 插件安装时，全名是 `shared-skills:download-md-images`），图会落到同目录的 `images/`，正文里的引用改写成相对路径。

**跑完必须核一遍真实格式**：微信 CDN 对 GIF 也返回 `.png` 结尾的地址，脚本按地址推断扩展名就会存成 `.png`。按文件头核（在输出目录下跑）：

```bash
python -c "import pathlib;[print(p.name, p.read_bytes()[:6]) for p in sorted(pathlib.Path('images').glob('*.png')) if p.read_bytes()[:6] not in (b'\x89PNG\r\n',)]"
```

列出的是 GIF 就把扩展名改成 `.gif`，并用 Edit 同步改正文里的那几处引用。

## 常见问题

| 现象 | 原因与处理 |
|:---|:---|
| 正文是空壳、只剩「赞 在看」 | 直接抓取撞上了验证页。走第一步的 CDP 路 |
| 退出码 2 | 页面要人工过验证。Chrome 窗口里点一下，然后重跑 |
| 退出码 2，且存下的 `article.failed-page.html` 里搜得到「参数错误」「该内容已被发布者删除」 | 不是验证问题，链接本身失效了，据实告诉用户，别当成技术故障去折腾。判断要搜正文——这种页面的标题只有「微信公众平台」几个字，看标题看不出来 |
| 找的 Chrome 不对 | 用 `CHROME_PATH` 环境变量指定；profile 目录可用 `WECHAT_ARCHIVE_PROFILE` 改 |
| 图片数对不上 | 多数是空占位被算进去了：微信会留既没 `src` 也没 `data-src` 的 `<img>`，按第二步只数带地址的那条命令重数。真丢了图才说明转换有问题 |
| 有 `.png` 其实是 GIF | 第四步没核格式。按文件头改扩展名并同步改引用 |
