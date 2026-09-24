# download-md-images

把 Markdown 里还指向远程网址的图片存到本地：下载进 md 同目录的 `images/` 并改写为相对路径。

这份 README 是给人看的：Claude 跑这个技能时不读它，读的是 [SKILL.md](./SKILL.md)。

## 文件结构

```text
skills/download-md-images/
├── README.md    你正在读的这份（Claude 不读）
├── SKILL.md     主流程
└── scripts/     两个脚本：认引用、下图
```

两个脚本的测试不在这里，在仓库根的 `tests/download-md-images/` 下。

## 改脚本

改 `scripts/` 下的两个脚本，改完在仓库根跑：

```
python tests/download-md-images/test_download_md_images.py
```

它验三件事：

- 两种图片引用都认得出——Markdown 的 `![]()` 与 HTML 的 `<img>`
- 扩展名推断对不对——带查询串的网址怎么取、没有扩展名时默认 `.png`
- frontmatter 里的 `source_url` 有没有被取出来当 Referer
