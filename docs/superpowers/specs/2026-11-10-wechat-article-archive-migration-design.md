# 微信公众号文章归档 skill 迁移到 shared-skills

日期：2026-11-10
状态：已批准

## 要做什么

把 `wechat-article-archive` 从 `C:\Study\work\.claude\skills\` 迁移到本仓库的
`plugin/skills/wechat-article-archive/`，成为插件的一部分，供所有工程使用。

## 为什么

这个 skill 的四步主体（取正文、转 Markdown、核对保真、图片本地化）跟工程无关；
现在放在 work 仓库里，别的工程用不到。本仓库 README 的收录标准是「跟具体工程无关、
别的工程拿去也能直接用」，它符合其中四步，不符合剩下的落盘约定。

## 目标

- 插件里有一门通用的 `wechat-article-archive`：输入公众号链接与输出目录，产出
  `<输出目录>/body.md` 与 `<输出目录>/images/`，正文逐字保真、图片全部落到本地。
- work 的归档约定（目录命名、文件头、仓库检查）仍留在 work，不随插件外发。
- 迁移后 work 里只保留编排说明所需的最小内容，原 skill 目录删除。

## 非目标

- 不新增或重写脚本逻辑；三个脚本原样搬运，只改 SKILL.md 里的调用路径。
- 不为脚本新写测试（本仓库也不是每门技能都有测试）。
- 不改 `download-md-images`、`pdf-to-md` 等其他技能。

## 现状里绑死 work 的三处

1. 产物固定存进 `techblog/`，按 work 的《知识库结构》§4.3 建同名子目录。
2. 正文文件头五行（标题 / 来源 / 作者 / 原文链接 / 存档日期）只写在 SKILL.md 里。
3. 收尾跑 `C:/Study/work/checks/check_repo.py`。

三个脚本里没有写死 work 的路径，可以直接搬。

## 方案（用户已选定）

**通用化拆分**：插件的 skill 只做四步，落盘约定归调用方。

另两种做法已排除：

- 原样搬：与收录标准冲突，别的工程拿去用不了，work 路径一变还要改插件。
- 拆成「通用取文 + work 包装技能」：多一门技能，work 编排本来就写在工程规则里，
  不需要再包一层。

## 迁移后的职责划分

**插件的 skill**

| 步骤 | 做什么 | 完成判据 |
|:---|:---|:---|
| 一 | CDP 取正文 | `article.meta.json` 的 `title`、`publishTime` 都有值，HTML 是几十万字节 |
| 二 | 转 Markdown | 打印的图片数等于带真实地址的 `<img>` 个数 |
| 三 | 核对保真 | 「缺失片段 0 个」，多出的字符只限规定的几种 |
| 四 | 图片本地化 | 图落到 `<输出目录>/images/`，按文件头把实为 GIF 的 `.png` 改回 `.gif` 并同步改引用 |

- 输出目录调用时给，skill 自己不知道 `techblog/` 这种约定。
- 不写文件头、不写 README、不跑任何工程的检查脚本。
- 调用本插件里的 `download-md-images` 做图片本地化。

**work 里的编排**（写在规则里，不在 skill 里）

1. 调插件 skill，给一个临时输出目录，得到 `body.md` 与 `images/`。
2. 照《知识库结构》§4.3 建 `techblog/<YYYY-MM-DD-标题>/`，正文改成同名。
3. 按 §4.3 新增的文件头格式拼出正文。
4. 写子目录 `README.md`。
5. 跑 `python C:/Study/work/checks/check_repo.py`。

## work 侧改动

只改 `.claude/rules/知识库结构.md` §4.3：

- 新增一段「正文文件头」，写死五行的格式（来源一行对公众号就是
  `微信公众号「<公众号名>」`），含结尾的 `---` 与日期格式。
- 新增一段「一次归档的流程」：临时目录、建归档目录、拼文件头、写 README、
  清临时目录并跑检查。这一段把技能与 work 的落盘约定接起来。
- 子目录 README 的字段补齐三项：来源、发布日期、正文文件名。

另有三处已经归档的 `techblog/*/README.md` 指向旧 skill 路径，改为指向插件技能。

以下内容本来就在 work，不动：

- 目录命名与结构：§4.3。
- 收尾跑 `check_repo.py`：`CLAUDE.md` 的「格式规则」。
- 删除 `.claude/skills/wechat-article-archive/`。

## shared-skills 侧改动

1. 新建 `plugin/skills/wechat-article-archive/`，放 `SKILL.md` 与三个脚本。
2. SKILL.md 的调用路径由 `C:/Study/work/.claude/skills/...` 改为 `<skill目录>/scripts/...`；
   删掉 techblog 落盘、§4.3、`check_repo.py` 三处；description 里去掉「存进 techblog/」。
3. README「收录的 skill」表加一行。
4. 版本号 1.30.1 → 1.31.0（新增技能抬中间位），
   `plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 两处一致。

## 验证

- shared-skills：`bash checks/verify.sh --changed` 通过；`python` 语法检查三个脚本能导入
  （`fetch_article.mjs` 用 `node --check`）。
- 版本号一致性由 `checks/verify.sh` 的版本模块覆盖。
- work：`python "C:/Study/work/checks/check_repo.py"` 通过。
- 端到端跑真实文章不在本次范围内（用户决定移除）。

## 留给执行者

- SKILL.md 正文的句子组织。
- 短设计文档与计划的提交时机（按用户要求，不由本流程自动提交）。
