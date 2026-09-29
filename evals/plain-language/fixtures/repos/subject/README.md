# docs-site

一份文档站的内容仓库。文章按主题分目录放，每篇一份 Markdown。

## 目录

- `checks/` —— 提交前跑的自查脚本，见下

## 自查脚本

`checks/verify.sh` 是入口，按文件名顺序跑 `checks/verify.d/` 下的每个模块，模块名前面的数字只用来定顺序。一个模块一件事，各跑各的，谁也不依赖谁。

```bash
bash checks/verify.sh          # 跑全部
bash checks/verify.sh links    # 只跑文件名里带 links 的模块
```

脚本只读文章，不改文章。发现问题就打印一行，末尾汇总。
