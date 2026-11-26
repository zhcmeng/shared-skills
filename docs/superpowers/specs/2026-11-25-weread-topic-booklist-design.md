# weread-book-export：按主题与推荐度筛书单

日期：2026-11-25
状态：已确认（2026-11-25）

## 背景

用户会反复提出同一类需求：在微信读书里按若干主题找书，只要推荐值 70% 以上的，按推荐值排名取前 20 本，每本给一句简述。2026-11-25 这次的主题是 AI 对组织、提效、变革、经济和社会的影响。

现在的 `weread-book-export` 只能按书名搜：`weread_search.py` 走搜索页，一页最多 40 条，结果里没有推荐值，也没有简介。要按推荐值筛一批书，缺两样东西：推荐值字段和可翻页的批量结果。

微信读书官方 Agent API 的 `/store/search` 和 `/book/info` 有这两样：`newRating`、`newRatingCount`、`intro`。官方 `weread-skills` 技能封装了这套接口，但它由安装器管理，升级会覆盖目录，所以这次不改它。本技能只读它的 `SKILL.md` 取版本号，接口参数以它的 `search.md`、`book.md` 为准。

## 目标

- 新增「按主题筛书单」：多关键词检索、去重、按推荐值过滤、模型筛相关性、拉详情、排序输出。
- 参数包括：主题关键词、推荐值下限、数量、是否按主题分组、评分人数下限。
- 输出包括：排名、书名链接、作者、推荐值、评分人数、主题标签、一句话简述，以及本次检索与筛选的计数。
- 机械部分交给脚本：检索、翻页、去重、过滤、拉详情、排序、渲染。
- 判断部分交给模型：主题相关性、主题标签、一句话简述。
- 与现有导出、搜索页三种模式共存；它们的行为不变。

## 非目标

- 不改官方 `weread-skills`，不复制它的接口文档。
- 不做向量语义检索；主题扩展靠模型生成关键词。
- 不导出正文；书单里的书要看正文，仍走导出模式。
- 不建全库索引，不维护跨主题的长期数据库。
- 不替用户在同名书里挑一本（沿用既有约定）。
- 不给官方文档的 `newRating` 口径错误提修改请求；只在本技能里按实测口径写明。

## 反目标

出现下面任意一种，这次改动就算失败：

- 把搜索结果说成全量，用「共有」「一共」暗示没有遗漏。
- 评分口径用错：把 902 当 902%，或按 0-100 过滤。
- 把技术教程、工具手册、案例集、传记、变现书混进主题书单，还当成主题相关的书。
- 推荐值低、或评分人数只有个位数的书排在前面，却没有任何标注。
- 为了多拿结果绕过限流、伪造分页参数。
- 简介没拉到就编一句话简述。

## 约束

- 需要环境变量 `WEREAD_API_KEY`；官方技能也用同一个 Key。
- 每次请求 body 必须带 `skill_version`，值从官方 `SKILL.md` 的 `version` 读。
- 搜索回包要扁平化：`results[].books` 可能有多个分组，每组可能只有一本书。
- `intro` 在搜索结果里没有；`category`、`publisher` 也没有。搜索结果只有书名、作者、译者、评分、评分人数、链接、上下架状态；初筛只能用这些字段，分类、出版方、简介留到拉详情后。
- `newRating` 实测是 0-1000，字段位置在 `results[].books[].bookInfo` 下；官方 `search.md` 写成 0-100、写在 `books[]` 顶层，与实测不符。
- 中文关键词必须用 UTF-8 请求体；Git Bash 里直接 `-d "中文"` 会拿到空结果。
- 连续快速请求约 20 个关键词后会出现 HTTP 499；词间要留间隔并做失败重试。
- 缓存和成品写在 `%LOCALAPPDATA%\weread-book-export\booklist\<主题>\`，不往当前项目目录里写；`--out`、`--cache-dir` 可改。
- 仓库规则：`plugin/` 下的改动要抬版本号；这次是给现有技能加一种用法，属于对原有内容的修改，抬最后一位，从 1.35.2 到 1.35.3；测试放 `tests/weread-book-export/`；改完跑 `bash tests/run.sh weread-book-export` 和 `bash checks/verify.sh`。

## 方案选择

### 方案 A：在 weread-book-export 里加一个走 Agent API 的书单脚本（采用）

- 新增 `scripts/weread_booklist.py`（命令行、HTTP、缓存）和 `scripts/booklist.py`（纯逻辑）。
- `SKILL.md` 加一节「按主题筛书单」，`README.md` 加一节给人看的说明。
- 好处：和「找书」同处一个技能，模型按描述选择模式；机械部分可复现，筛选判据写在技能里。
- 代价：技能多一个前置条件（API Key），多一条数据来源；文档要写清两种搜法的分工。

### 方案 B：新建一个独立技能（不采用）

- 好处：不碰现有技能，官方 API 与搜索页分开。
- 不采用：用户要求改 `weread-book-export`；而且「按主题找书」已经在它的触发词里，再建一个会让模型选错。

### 方案 C：只写提示词，不加脚本（不采用）

- 好处：不新增代码。
- 不采用：约 100 次请求全靠模型逐次发，间隔、重试、翻页、去重容易走样，几百本书靠人工核对容易漏。

## 关键决定

### 1. 两种搜法分工

- 找具体某本书、确认有没有、拿阅读器地址：走 `weread_search.py` 的搜索页。
- 按主题筛一批、要推荐值排名：走 `weread_booklist.py` 的 Agent API。
- 整本导出正文：走 `weread_export.py`。
- `SKILL.md` 的描述和正文都要写这三句，避免模型混用。

### 2. 评分口径按实测

- `newRating` 是 0-1000，`>= 700` 即推荐值 70% 以上。
- 字段在 `results[].books[].bookInfo` 下；如果某天回包把字段提到 `books[]` 顶层，脚本两处都读。
- 展示时除以 10，写成 `90.2%`；同时展示 `newRatingCount`。
- 本技能不按 0-100 过滤，也不把 902 当 902%。

### 3. 两段筛选

1. `search`：批量搜、去重、按推荐值过滤，产出 `candidates.json`。
2. 模型按书名、作者初筛（搜索回包只有这些字段；副标题通常并进书名），产出 `shortlist.json`（留下的 bookId、理由，以及不留的理由）。
3. `info`：只给 shortlist 拉 `/book/info`，产出 `bookinfo.json`；失败的书记进 `failed_info.txt`。
4. 模型结合分类、出版方、简介精筛，标主题、写一句话，产出 `picks.json`。
5. `render`：合并详情与 picks，排序、取前 N、渲染 Markdown。

初筛后才拉详情，避免拉几百本；脚本不判断主题相关性。

### 4. 关键词由模型展开

- 脚本不内置词表。主题不同，词表不同；模型按用户给的主题生成 12-15 个词，用户说「尽量全」时扩到 30 个以上。
- 关键词通过 `--keywords-file` 传入（UTF-8，一行一个）或 `--keywords` 逗号分隔；Windows 上中文长列表优先用文件，避开引号问题。
- 多主题时，词表按主题分组传入；脚本只负责把每本书命中的词记下来，主题归属由模型判断。

### 5. 相关性判据

- 分两段判断：初筛只看书名与作者（搜索回包没有分类、出版方、简介）；精筛看分类、出版方、简介。标题只作初判，简介可以推翻。
- 初筛宁松勿紧：短名单按目标数量（默认 20）的 2-3 倍留，给精筛留余量。
- 排除：技术教程与编程入门、工具操作手册（提示词、办公软件操作）、案例集、人物传记与访谈、副业变现、轻商业与短篇轻读物。
- 「不要实例」按「排除案例集」处理：书名或副标题带「案例」「实战案例」「XX 个案例」，或简介说明是案例汇编的，不留。
- 留下：论述 AI 对组织、工作方式、经济、社会影响的非虚构书；行业研究、思想随笔也可以留。
- 每本记一句留或不留的理由，写进 `shortlist.json` / `picks.json`；输出时能交代初筛、精筛各去掉多少。

### 6. 主题标签与分组

- 模型在精筛时给每本书 1 个主主题、0-2 个次主题，主题名用用户给的说法（如「组织」「提效」「变革」「经济」「社会影响」）。
- 默认合并成一个榜单，每本标主题；`--group` 时按主主题分小节，次主题在条目里标出。

### 7. 排序与数量

- 按 `newRating` 从高到低；同分按 `newRatingCount` 从多到少；再同则按书名。
- 默认取前 20，`--top` 可改。
- 相关性只用于过滤，不参与排序；用户要的是「按推荐值排名」。

### 8. 评分人数不设门槛，只标注

- 2026-11-25 实测：`newRating >= 700` 的 323 本里，评分人数中位数 53，最少 20。设门槛会砍掉大量书。
- 默认全部保留；评分人数少于 50 的在输出里标「少于 50 人评分」。
- 需要收紧时用 `--min-ratings`。

### 9. 缓存与产物

缓存根：`%LOCALAPPDATA%\weread-book-export\booklist\<主题>\`，和现有登录态、断点文件同一个地方。

- `raw/<关键词哈希>.json`：每个关键词的原始扁平结果；同主题重跑时，有这份文件就跳过该词。
- `search_meta.json`：本次检索的元数据，含主题显示名、关键词列表、推荐值下限、每页条数、页数、去重数、过线数；`render` 用它写标题和计数行。
- `all_books.json`：全部去重后的书。
- `candidates.json`：过推荐值线的书。
- `shortlist.json`、`bookinfo.json`、`picks.json`：模型与脚本之间的交接文件。
- `failed.txt`：重试后仍失败的关键词。
- `failed_info.txt`：详情重试后仍失败的 bookId。
- `booklist-<YYYY-MM-DD>.md`：成品；`--out` 改路径。

`--refresh` 忽略 raw 缓存，重搜所有词；`--cache-dir` 改缓存根。成品同时发在对话里，并告知文件路径。

### 10. 限流、翻页、重试

- 每页 50 条，每个词最多 3 页；翻页用「已取页数 × 每页条数」作 `maxIdx`：0、50、100。回包的 `searchIdx` 是页号，不是游标；按它推进只前进一步，三页会大量重复（实测同一关键词 150 条里只有 52 本不重复）。`hasMore=1` 才继续。
- 词间停 2 秒，加 0-0.5 秒随机；页间停 0.5 秒。
- HTTP 499、网络错误、`errcode` 非 0 都重试 2 次，退避 10 秒、30 秒。
- 重试后仍失败的关键词写 `failed.txt`，其它词照常跑完；脚本报告哪些词没跑成。

### 11. 版本号与官方升级适配

版本号取值顺序：

1. `--skill-version` 参数；
2. `WEREAD_SKILL_VERSION` 环境变量；
3. `~/.agents/skills/weread-skills/SKILL.md` 的 `version`；
4. `~/.claude/skills/weread-skills/SKILL.md` 的 `version`。

四步都拿不到就退出 1，提示用户设 `WEREAD_SKILL_VERSION`。脚本每次运行都打印用了哪个版本、从哪读到的。

`check` 子命令：检查 API Key、版本号、`/store/search` 与 `/book/info` 是否可用。官方升级后先跑它；接口参数或回包字段变了，只改 `weread_booklist.py` 和 `SKILL.md` 的书单一节。

### 12. 输出格式

标题和计数行从 `search_meta.json` 读，先写一行检索说明，再写榜单：

```markdown
## AI 对组织、经济与社会的影响：推荐值 70% 以上的前 20 本

检索 38 个关键词，去重 941 本；推荐值 70% 以上 323 本；按书名与简介筛掉教程、案例集、传记等，取前 20，按推荐值排序。

1. **《书名》** 作者 · 推荐值 90.2% · 1,234 人评分 · 主题：组织
   [打开阅读](readerLink)
   一句话简述。
```

- 评分人数少于 50 的，在推荐值后面标「少于 50 人评分」。
- 没有 `readerLink` 时不拼链接，按官方规则只用回包里给的。
- 结语写「本次检索到」，不写「共有」「一共」。
- 简述只根据 `intro` 写，不补充接口没给的信息。

### 13. 退出码

沿用技能现有约定，按 API 场景补一条：

- 0：跑完，结果已写。
- 2：需要用户操作，当前是没设 `WEREAD_API_KEY`。
- 3：部分关键词或部分详情重试后仍失败，结果不完整；把失败的词或 bookId 转告用户。
- 1：参数错误、版本号读不到、脚本内部错误。

### 14. `/book/info` 失败与空简介

- 某本书的 `/book/info` 重试后仍失败：写进 `failed_info.txt`，不编简介。它仍可以进榜单，字段用搜索回包里的书名、作者、评分、评分人数、链接，简介位置写「简介获取失败」。
- `intro` 为空：保留这本书，简介位置写「暂无简介」，`picks.json` 的 `summary` 可以省略。
- 只有 `intro` 非空时才要求写 `summary`；脚本按这个规则校验。
- 有书失败时脚本退出 3，报告失败的 bookId；一本书都没成功时退出 1。

## 接口与交接文件

命令行：

```bash
python "<skill目录>/scripts/weread_booklist.py" check
python "<skill目录>/scripts/weread_booklist.py" search --topic <主题短名> --title "<主题显示名>" --context "<用户原话>" --keywords-file <文件>
python "<skill目录>/scripts/weread_booklist.py" info --topic <主题短名> --shortlist <文件>
python "<skill目录>/scripts/weread_booklist.py" render --topic <主题短名> --picks <文件> [--group] [--top 20]
```

`search` 的常用参数：`--min-rating 700`、`--pages 3`、`--count 50`、`--interval 2`、`--retries 2`、`--refresh`。`search` 写 `search_meta.json`；`render` 从它读标题和计数。
`render` 的常用参数：`--top 20`、`--group`、`--min-ratings 0`、`--out`。

交接文件（JSON，UTF-8）：

- `search_meta.json`：`{"topic": "...", "title": "主题显示名", "keywords": ["..."], "min_rating": 700, "pages": 3, "count": 50, "unique_books": 941, "candidates": 323}`
- `shortlist.json`：`{"kept": [{"bookId": "...", "reason": "..."}], "dropped": [{"bookId": "...", "reason": "..."}]}`
- `picks.json`：`{"kept": [{"bookId": "...", "theme": "组织", "secondary": ["提效"], "summary": "一句话", "reason": "..."}], "dropped": [{"bookId": "...", "reason": "..."}]}`

脚本校验：bookId 必须能在 `bookinfo.json` 或 `candidates.json` 里找到；`kept` 和 `dropped` 的每一本都要有 `reason`；`theme` 必填；`summary` 只在简介非空时必填；缺字段时报错，不猜。

## 改动文件

- `plugin/skills/weread-book-export/scripts/weread_booklist.py`（新）：命令行、HTTP、缓存读写。
- `plugin/skills/weread-book-export/scripts/booklist.py`（新）：纯逻辑，可单独测试。
- `plugin/skills/weread-book-export/SKILL.md`：描述加触发；正文加「按主题筛书单」一节；补退出码、完成判据。
- `plugin/skills/weread-book-export/README.md`：加一节给人看的说明。
- `README.md`（仓库根）：技能索引那一行补书单能力。
- `tests/weread-book-export/test_booklist.py`（新）：纯逻辑测试。
- `tests/weread-book-export/test_booklist_cli.py`（新）：参数与子命令测试。
- `plugin/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`：版本 1.35.2 到 1.35.3。

## 数据来源与实测

2026-11-25，Windows 11，Python 3，直接调 `https://i.weread.qq.com/api/agent/gateway`。

- 38 个关键词，每个发 3 页、每页 50 条，去重后 941 本。这次用的是旧翻页写法（用最后一条的 `searchIdx` 作 `maxIdx`），三页之间大量重复：单个关键词 150 条里只有 52 本不重复。按「页数 × 每页条数」翻页，同一个词三页能拿到更多不重复的书；941 这个数只作参考，实施后按正确翻页重测。
- `newRating >= 700` 的 323 本；评分人数中位数 53，最少 20。
- `newRating` 实测范围 57-941；字段在 `bookInfo` 下，`books[]` 顶层没有。
- 941 本的搜索结果里 `intro` 全部为空；`/book/info` 回包含 `intro`、`newRating`、`newRatingCount`、`readerLink`。
- 连续快速请求约 20 个关键词后出现 HTTP 499；本次脚本用 1.2-3 秒间隔加失败重试跑完。
- 2026-11-25 复测 `maxIdx`：不传取第 1-20 条；`maxIdx=20` 与第一页只有 3 条重叠；`maxIdx=50` 与第一页 0 条重叠；`maxIdx=1` 与第一页 16 条重叠，说明按 `searchIdx` 推进只前进一步。
- 中文关键词用 `json.dumps(..., ensure_ascii=False).encode("utf-8")` 发；Git Bash 直接 `-d "中文"` 会返回空结果。
- 本次成品只在对话里发过，没有落盘；本设计把落盘补上。

## 测试计划

纯逻辑（不联网）：

- 版本号：四个来源的优先级、读不到时报错。
- 关键词文件：一行一个、空行、重复词、UTF-8。
- 去重：同一 bookId 出现在多个关键词结果里，合并 `keywords`。
- 翻页：`maxIdx = 页数 × count`；`searchIdx` 只作页号校验；`hasMore=0` 停；某页为空停。
- 详情失败：写 `failed_info.txt`、退出 3；一本书都没成功退出 1。
- 空简介：允许省略 summary，渲染写「暂无简介」。
- `search_meta.json`：关键词、阈值、计数写入与读取。
- 评分过滤：700 边界、`newRating` 缺失、字段在 `bookInfo` 与顶层的两种情况。
- 排序：同分按评分人数，再按书名；`--top` 截断。
- 标注：评分人数少于 50 的标记。
- 渲染：合并、分组、空 picks、缺字段报错。
- 交接文件：`shortlist.json`、`picks.json` 的合法与非法输入。

命令行（不联网）：

- `check` 在缺 Key、缺版本号时的退出码与提示。
- `search` / `info` / `render` 的必填参数、互斥参数、`--refresh`。
- `--out`、`--cache-dir` 的落点。

手动实测（联网，小规模）：

- 3-5 个关键词跑一遍，核对去重数、过线数、失败词。
- 同主题重跑，确认 raw 缓存被复用。
- 对一本文本核对：推荐值、评分人数、简介与线上一致。

## 验收标准

- 用一组真实关键词能跑通 search → shortlist → info → picks → render，产出榜单。
- 计数自洽：去重数、过线数、初筛与精筛的去掉数对得上。
- 翻页按「页数 × 每页条数」推进，三页之间没有成片重复。
- 详情失败的书有明确标注，不编简介。
- 输出里每本书的推荐值、评分人数、链接都来自回包，简述来自简介。
- 题目要求的排除类型不会出现在最终榜单里；留下的每本都有理由。
- 官方 `weread-skills` 没有任何改动。
- `bash tests/run.sh weread-book-export` 全过。
- `bash checks/verify.sh --changed` 全过。
- `git diff --check` 干净；新增文件里没有非 BMP 字符。
- `plugin/` 下没有测试文件、缓存文件或 `__pycache__`。

## 交付

- 版本号两处一起抬到 `1.35.3`。
- 提交信息：`feat(skills): weread-book-export 支持按主题与推荐度筛书单`。
- 不删除 `%LOCALAPPDATA%\weread-book-export\browser-profile`。
- 实测用的小规模缓存留在 `%LOCALAPPDATA%\weread-book-export\booklist\` 下，交付前清掉测试主题目录。

## 留给实现的人

- 纯逻辑放 `booklist.py`，命令行与 HTTP 放 `weread_booklist.py`；测试主要测前者，HTTP 用假响应注入。
- 搜索回包没有分类、出版方、简介；初筛指令只用书名和作者，不要把这三样写进初筛。
- 翻页不要用 `searchIdx` 当游标；它是页号，`maxIdx` 是已取条数。
- 官方回包的字段位置以实测为准；`newRating`、`newRatingCount` 先读 `bookInfo`，再退回 `books[]` 顶层。
- 模型筛选这一段写进 `SKILL.md`，不要塞进脚本；脚本只校验交接文件，不判断主题。
- 官方升级后先跑 `check`；接口字段变了，改脚本和 `SKILL.md` 里那一节，不改官方技能。
- 如果以后要支持「按主题分组导出清单」，在 `render --group` 的基础上加，不动搜索部分。
