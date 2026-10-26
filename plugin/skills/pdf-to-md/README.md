# pdf-to-md

把 PDF 转成 Markdown 写到磁盘——正文引用的图片一并下载到本地并改成相对路径。支持单个文件、目录批量，以及 PDF 的公网网址。

这份 README 是给人看的：Claude 跑这个技能时不读它，读的是 [SKILL.md](./SKILL.md)。技能怎么用、要什么输入，那里写着；这里只写**改它的时候要看什么**。

## 文件结构

```text
skills/pdf-to-md/
├── README.md          你正在读的这份（Claude 不读）
├── SKILL.md           主流程
├── scripts/
│   ├── markdown.py    纯文本处理，不联网
│   ├── aistudio.py    网络：提交、轮询、取结果、下图（--backend api）
│   ├── aistudio_web.py 浏览器：登录、上传官网、等任务、下载官网 JSON
│   ├── convert.py     主流程：认任务、调上面三个、写文件
│   └── doctor.py      体检：回答「这台机器现在能不能转」
└── assets/
    ├── doctor-sample.html   体检样例（源）
    └── doctor-sample.pdf    上面那份打印出来的，体检时真转它
```

五个脚本的测试不在这里，在开发这个技能的仓库的 `tests/pdf-to-md/` 下。装着技能发出去的东西里不含测试。

## 改脚本

改 `scripts/` 下任一脚本，改完在开发仓库的根下跑：

```
uv run --with requests --with lxml --with tabulate --with pypdf python tests/pdf-to-md/test_pdf_to_md.py
```

全部测试都不发真实请求，网络那一段用假响应喂进去。接口和返回结构的实测结论记在 `docs/superpowers/specs/2026-09-20-pdf-to-md-design.md` 的「验过什么、还没验什么」一节。

三条容易出错的：

- **`doctor.py` 只用标准库，别让它 import 另外四个。** 那四个缺依赖时它得能跑起来——体检的意义正是在依赖没装好时告诉你差什么。测试里有一条在 `python -S`（不加载第三方包）下真跑它。官网方式的路径与凭据校验是照抄 `aistudio_web.py` 的一份，测试里直接比对两边，抄错会红。
- **`pypdf` 只有财报单页模式用，导入要留在 `split_pdf_pages` 里面。** 挪到文件开头的话，没装 pypdf 的机器连普通模式都跑不起来。测试里有几条会真的切 PDF，所以跑测试时也要带 `--with pypdf`。
- **改体检样例要重新打印。** `assets/doctor-sample.html` 改完，得拿 Chromium 重新打印成 `doctor-sample.pdf`（命令写在 HTML 开头的注释里）。HTML 里那句「校验标记」和 `doctor.py` 的 `SAMPLE_MARKER` 必须一致——对不上时，体检会把好环境报成坏的。

## 官网流程要真跑一遍

`aistudio_web.py` 里的页面选择器、登录判断、上传跳转、下载菜单，测试都碰不到——它们要真开浏览器。改了这一段，用 1 页样例手动验收一次：

```bash
uv run --with requests --with lxml --with tabulate --with playwright \
  python plugin/skills/pdf-to-md/scripts/convert.py \
  plugin/skills/pdf-to-md/assets/doctor-sample.pdf \
  --output <临时目录> --debug
```

它会打开浏览器、把样例上传到 AI Studio 官网（花 1 页配额）。浏览器要先登录；第一次跑会停下来让你登。跑完检查：md 里有 `DOCTOR-SAMPLE-8642`，`debug/<时间戳>/raw/official.json` 是 1 项列表，`web/task-page.png` 与 `.html` 都在，产物里 grep 不到账号、密码、cookie。
