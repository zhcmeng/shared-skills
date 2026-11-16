# 权威数据源技能（authoritative-sources）设计

2026-11-16

## 背景与目的

需要一个技能，在开始检索行业或市场数据之前给出指导：这个问题该去哪些权威来源找、这些来源的口径有什么差别、搜到什么程度算够。

现有的一手素材在 investment 仓库里：

- `source-classifier`：信源分级判定（一级官方 / 二级专业机构 / 三级碎片、GitHub 黑名单、证据原则）。
- `检索强度规则`：搜多少算够、什么主题找什么信源、搜不到怎么标缺口。
- 本次对游戏行业的实际检索（2026-11-16）：中国区与全球区各一路，逐条打开核实，得到一份可复用的来源清单与一批口径陷阱。

这三样合起来正是「搜索数据的指导」。但它们现在绑在 investment 的目录与规则上，别的工程用不上。本次把它们中通用的部分搬进 shared-skills，并加上按行业挂载的数据源目录。

迁移的含义按用户明确的口径：**搬走，investment 不再保留原文**。

## 目标

1. 一个技能 `authoritative-sources`，在开始检索行业或市场数据之前给出指导，回答三件事：去哪找、找到的算不算数、搜到什么程度算够。
2. **通用指导，不局限于投资。** 任何需要行业或市场数据的场景都适用——写行业分析、做商业研究、查市场数据、写报告。技能正文不假定使用者做投资，也不预设使用者的工作流程。
2. 数据源按行业分文件挂载，按需加载：`SKILL.md` 只保留目录，问题落到哪个行业才读哪个文件。
3. 加一个新行业 = 加一个 `references/<行业>.md` + 目录加一行，不动主体。
4. 信源分级与检索纪律写在技能自己的文件里，不引用任何仓库的页面或路径（沿用本仓 skill-judge 已确立的自包含原则）。
5. 首批挂载两个数据源：中国游戏行业、全球游戏市场，内容取自 2026-11-16 的实际核实结果，每条带核实日期。

## 非目标

- 不做下载与入库。素材怎么落盘、frontmatter 怎么写、索引与备份怎么跑，留在 investment 的 `material-ingest` 与 SOP。
- 不做引用格式校验。脚注格式、五章节结构、GB/T 7714 审计留在 investment 的 `cite`。
- 不替代实际检索。技能只给出该搜哪里与搜到什么程度，不能代替打开页面核实。
- 不做数据缓存或数据库。数据源文件是人工维护的清单，不是数据的副本。

## 约束

- **收录判据**：跟具体工程无关、别的工程拿去也能直接用。正文不出现任何仓库路径、私有目录名、本地文件结构。
- **不限于投资**：正文不写「投资者」「估值」「买卖决策」这类投资专属语境。信源分级里的「券商研报」「招股说明书」「年报」作为**示例**保留，但不写成投资专属——它们是任何商业研究都可能用到的来源。原 `source-classifier` 开头那句「在商业研究和投资分析中」改为「在研究与分析中」。
- **插件全部内容都会发出去**：数据源文件里不能写本机路径、内网地址、只有本人能访问的链接。
- 正文中文，不用 emoji 这类非 BMP 字符。
- 技能目录名英文（`authoritative-sources`），`references/` 下的文档名可用中文（本仓 `skill-ledger/references/上游台账机制.md` 已有先例）。
- 不依赖 superpowers 或其他插件技能。装不装都能用。
- 新增技能抬版本号中间位：`1.32.1` → `1.33.0`，`plugin.json` 与 `marketplace.json` 两处一致。

## 备选方案

**方案 A（已选）：一个新技能，三块内容合一。**
- `SKILL.md`：检索纪律 + 数据源目录。
- `references/信源分级.md`：三级标准与判定顺序。
- `references/中国游戏行业.md`、`references/全球游戏市场.md`：数据源清单。
- 理由：一次完整检索本来就是三步——先去哪找（目录）、找到的算不算数（分级）、搜到什么程度算够（纪律）。拆成两个技能，后两步要靠模型自己想起去读第二个，容易漏。本仓 `cite` 也是把分级、校验、修复编排在一个技能里。

**方案 B（未选）：拆成 `source-grading` 与 `authoritative-sources` 两个技能。**
- 好处是职责单一、分级可被别的场景单独调用。
- 不选的理由同上，且一次检索要触发两次，两个技能的触发词重叠。

## 落点清单

shared-skills 仓：

| 动作 | 路径 |
|:---|:---|
| 新建 | `plugin/skills/authoritative-sources/SKILL.md` |
| 新建 | `plugin/skills/authoritative-sources/references/信源分级.md` |
| 新建 | `plugin/skills/authoritative-sources/references/中国游戏行业.md` |
| 新建 | `plugin/skills/authoritative-sources/references/全球游戏市场.md` |
| 新建 | `plugin/rules/检索强度.md`（全局常驻规则，约 20 行） |
| 修改 | `README.md`「收录的 skill」表补一行 |
| 修改 | `README.md`「常驻规则」表补一行，正文「十一条」改「十二条」 |
| 修改 | `plugin/.claude-plugin/plugin.json` 版本号 `1.32.1` → `1.33.0` |
| 修改 | `.claude-plugin/marketplace.json` 版本号 `1.32.1` → `1.33.0` |

investment 仓：

| 动作 | 路径 |
|:---|:---|
| 删除 | `.claude/skills/source-classifier/`（整个目录，含 scripts/classify.py） |
| 修改 | 上节列出的 10 个文件 17 处引用 |
| 修改 | `.claude/rules/检索强度规则.md` 只留本地素材层表与指向，通用部分已进全局规则与技能 |
| 修改 | `CLAUDE.md` 补一条插件依赖说明 |

## 技能结构

### `SKILL.md`

四部分，按顺序：

1. **什么时候用 / 不用**。用：开始检索行业或市场数据之前、需要判断某个来源能不能当证据。不用：具体下载入库、引用格式校验、纯概念解释。
2. **检索纪律**（迁自 `检索强度规则` 的通用部分）：
   - 先本地、后外部：如果所在工程有本地素材库或检索工具，先查本地已有什么；本技能管的是外部来源的选择，不替代本地检索。
   - 哪些回答必须经过实际检索：事实性数据、行业判断、公司信息、状态声明、对比判断。
   - 搜多少算够，两档：单点事实（1 个权威一手源，标到年份加章节或页码）；系统性整理（至少 4 轮不同角度检索、6 个独立来源、3 个一级或二级来源、每个并列子主题各有专门信源、关键结论至少 2 个独立来源，单源标「待复核」）。
   - 什么主题找什么信源：行业规模与格局找政府统计与行业协会；公司经营找年报与公告；宏观政策找央行、统计局、发改委；市场行情找交易所与官方数据。媒体只能作辅助。
   - 搜不到怎么办：先穷尽路径（换关键词、换语言、换角度）；如实标注缺口成因；可以降级用次级信源但必须标明性质；禁止用训练数据脑补、禁止把单一来源写成公认事实。
   - 自检清单与反模式，从原规则压缩到各 5 条以内。
3. **数据源目录**（按需加载的入口）：

   | 数据源 | 文件 | 什么时候读 |
   |:---|:---|:---|
   | 信源分级 | `references/信源分级.md` | 需要判断某个来源的等级、或判断证据够不够时 |
   | 中国游戏行业 | `references/中国游戏行业.md` | 问题涉及中国游戏市场的规模、用户、版号、买量、公司经营 |
   | 全球游戏市场 | `references/全球游戏市场.md` | 问题涉及全球或海外游戏市场，或需要与中国对比 |

4. **加新数据源**：在 `references/` 下按统一结构写一个文件，目录表加一行。不修改其他文件。

### `references/信源分级.md`

合并 investment 的 `source-classifier/SKILL.md` 与 `references/standards.md`，去掉唯一一处工程绑定（指向 CRAAP 测试页面的链接）。保留：

- 判定顺序（GitHub 黑名单优先 → 官方背景 → 专业深度加工 → 网络碎片）。
- 三级完整定义、特征、典型来源、使用场景。
- 易误判来源（百科、微信公众号）。
- GitHub 黑名单及其「只作线索入口」的例外。
- 三级信源引用约束（不作孤证、标存疑表述、向上溯源）。
- 证据支撑判断（至少 1 个一级，或 2 个互不相关的二级）。

### `references/<行业>.md` 的统一结构

每个数据源文件按同一骨架写，便于以后新增行业时照着填：

```markdown
# <行业或市场名>

核实日期：YYYY-MM-DD

> 本文件是人工维护的来源清单，不是数据的副本。超过 6 个月未核实，引用前重新确认机构的发布频率与官网可用性。

## 这个行业的数据难点
两三句，说明哪些数据拿不到、哪些口径容易混。

## 按用途查源
| 要回答什么 | 首选源 | 分级 | 频率 | 是否免费 | URL |

## 口径陷阱
每个陷阱一段，写明「A 机构的 X 与 B 机构的 Y 为什么不能直接比较」。

## 机构状态变化
已停刊、被收购、官网失效、口径调整。

## 交叉验证建议
哪些结论必须两个源对上，哪些单源即可。
```

字段取值约束：

- 「分级」只填一级 / 二级 / 三级，口径与 `信源分级.md` 一致。
- 「频率」写实际发布节奏，不设固定枚举。单值或组合都行，例如「年度」「半年度」「年度+半年度」「月度」「季度」「周」「日」「实时」「不定期」。组合写法要能看出每个时点，如「年度（12 月）+ 半年度（7 月）」。
- 「是否免费」区分三种：免费、摘要免费全文付费、付费。
- 每条都要有可访问的 URL，不含本机路径。

### 两个首批数据源文件的内容范围

**中国游戏行业**（来自 2026-11-16 核实）：

- 一级：国家新闻出版署游戏审批结果页（版号）；巨潮资讯；香港交易所披露易。
- 二级：中国音数协游戏工委《中国游戏产业报告》（年度加半年度）；伽马数据月度报告；中国音数协电子竞技产业报告；DataEye、QuestMobile、艾瑞；点点数据、七麦、TapTap、Steam 榜单；Sensor Tower 中国站。
- 口径陷阱：游戏工委的市场实际销售收入不含海外；2026 年起新增桌游；三家机构 2025 年手游市场规模各不相同（2570.76 / 2693.4 / 2859.2 亿元）；Sensor Tower 只覆盖 App Store 与 Google Play，中国大陆仅 iOS；QuestMobile 的手游 App 月活不等于游戏用户规模。
- 机构状态：伽马数据官网失效；data.ai 已被 Sensor Tower 收购。

**全球游戏市场**（来自 2026-11-16 核实）：

- 一级：SEC EDGAR；索尼、任天堂、微软、Take-Two、育碧、Nexon、万代南梦宫、卡普空、Roblox 的投资者关系页；Valve Steam 官方统计。
- 二级：Newzoo；Sensor Tower；Circana；GSD（Video Games Europe 运营）；ESA；UKIE；Famitsu 周榜；SteamDB、SteamSpy；Niko Partners；IGDA。
- 付费二级：Ampere Analysis、Omdia、IDC、MIDiA、CESA、Media Create、角川 ASCII 综合研究所、AppMagic、VG Insights。
- 口径陷阱：Newzoo 全球全口径、Sensor Tower 只含移动与 Steam、Circana 只统计美国消费、GSD 依赖发行商报送，四者不能相加或互相验证。
- 机构状态：EA 于 2026 年 8 月私有化退市；微软取消原三大分部；CESA 白书改版；SteamDB 被 Chosen 收购；SteamSpy 对新作估算不可靠。

## investment 侧的搬走处理

搬走不是复制，investment 的原文要删。涉及五处：

1. **删除** `.claude/skills/source-classifier/` 整个目录，含 `SKILL.md`、`references/standards.md`、`scripts/classify.py`。`classify.py` 无其他文件引用，一并删。
2. **改引用**：全仓共 10 个文件、17 处指向本地技能，改为指向 `shared-skills:authoritative-sources`。
   - `.claude/skills/cite/SKILL.md`（5 处：description、生成流程的责任表两行、生成流程第 2 步、问题处置表）
   - `.claude/skills/material-ingest/SKILL.md`（1 处：`source_level` 字段说明，现有形式是相对路径链接，搬走后必然断）
   - `.claude/skills/stance-red-team/SKILL.md`（2 处：路由表、报告收尾）
   - `.claude/skills/evidence-review/references/scoring-rules.md`（1 处）
   - `.claude/skills/business-insight-builder/disciplines/collect.md`（1 处）
   - `.claude/skills/business-case-builder/references/skill-routing.md`（1 处）
   - `.claude/skills/business-case-builder/case-logic-coach-prompt.md`（1 处）
   - `.claude/skills/business-case-builder/case-evidence-builder-prompt.md`（1 处）
   - `.claude/commands/source-grounding.md`（3 处，其中第 27 行在「必加载」列表里，漏改会让该命令无法执行）
   - `.claude/rules/检索强度规则.md`（1 处链接）

   **验收时用 grep 查残留**：`grep -rn "source-classifier" C:\investment\.claude` 应无输出（`source-grounding.md` 若是例外，须写明理由）。
3. **拆 `检索强度规则.md`**：逐条归位，去向有三处。
   - **全局常驻规则** `plugin/rules/检索强度.md`（约 20 行）：哪些回答必须实际检索、两档强度底线、证据原则、搜不到时的缺口标注要求、一句指向技能看细节。所有工程每次会话都加载。
   - **技能完整版**：检索强度底线的完整表述、主题与信源对应、搜不到怎么办的完整流程、自检清单、反模式、「检索结果与训练数据不一致时以检索结果为准」。
   - **留在 investment**：§1 的本地素材层入口表全部 8 行（包括「行情/宏观结构化数据：无」与「pages：参考非信源」两行）；「检索一律走子代理」这条硬性要求（与 `plugin/rules/search-artifacts.md` 呼应，不重复写进新规则）；§4 的引用格式衔接（引用规则、素材保存建议、脚注标注）；本地检索工具的用法（qmd、query_reports.py）。
4. **`素材保存建议.md` 不动**：它绑死 investment 的素材目录，不在本次迁移范围。
5. **`引用规则.md` 不动**：引用格式与 migration 无关。

## 全局生效，不是本地减少

shared-skills 是全局插件：装到机器上后，`plugin/skills/` 下的技能对所有工程可用，`plugin/rules/` 下的规则由 Claude Code 在所有工程自动加载。所以迁移的实质是**把 investment 专有的能力升级为全局能力**，不是「investment 失去这些能力」。

三块内容的去向分别是：

| 内容 | 去向 | 对 investment 的影响 |
|:---|:---|:---|
| 信源分级（原 `source-classifier` 全部内容） | `authoritative-sources/references/信源分级.md` | 能力保留，调用名变成 `shared-skills:authoritative-sources`，17 处引用跟着改 |
| 检索纪律完整版 | `authoritative-sources/SKILL.md` | 按需触发，细节在这里 |
| 检索纪律常驻版（约 20 行） | 新增 `plugin/rules/检索强度.md` | **全局常驻**，所有工程每次会话都加载，比原来只覆盖 investment 更强 |
| 本地素材层入口表 | 留在 investment 的 `检索强度规则.md` | 只有这部分绑死本地目录，不迁移 |

因此：

- 不存在「常驻约束真空」。常驻部分从 investment 的 121 行规则，变成全局约 20 行规则加技能里的完整版；investment 的默认约束没有减少，还多了一层对所有工程都生效的规则。
- 不需要薄壳方案。investment 不保留任何分级内容，17 处引用直接指向插件技能。
- 新增的依赖只有一条：插件必须已安装。shared-skills 的其他技能本来就依赖同一前提，在 investment 的 `CLAUDE.md` 写明即可。
- README 的常驻规则表要从十一条变成十二条；`checks/verify.sh` 的 25-rules-sync 模块会校验新规则的同步。

## 验收标准

1. 在 shared-skills 仓问「做游戏行业研究该用哪些数据源」，技能能给出中国区与全球区两份，且每条带分级与 URL。
2. 问「这个来源可靠吗」，技能能按三级判定并给出证据是否充分的结论。
3. 问「搜到什么程度算够」，技能能区分单点事实与系统性整理两档。
4. 技能正文不出现任何 investment 的路径、目录名或规则文件名。
5. **全局生效验证**：在一个非 investment 的工程开新会话，`plugin/rules/检索强度.md` 的内容出现在项目指令里；技能列表里有 `shared-skills:authoritative-sources`。
6. `bash checks/verify.sh` 通过；`plugin.json` 与 `marketplace.json` 版本号一致为 `1.33.0`；README「收录的 skill」与「常驻规则」两张表都已更新，正文「十一条」改为「十二条」。
7. investment 仓内不再有 `source-classifier` 目录；`grep -rn "source-classifier" .claude` 无输出；检索强度规则只留本地素材层表，仍能指导本地检索。

## 附录 A：中国游戏行业数据源（2026-11-16 核实，实施输入）

每行都已实际打开核实。「核实状态」里的 403/429 是被反爬拒绝但经其他路径确认存在。

| 要回答什么 | 首选源 | 分级 | 频率 | 是否免费 | URL | 核实状态 |
|:---|:---|:---|:---|:---|:---|:---|
| 版号发了多少、发了什么 | 国家新闻出版署游戏审批结果 | 一级 | 月度 | 免费 | https://www.nppa.gov.cn/bsfw/jggs/yxspjg/ | 已打开，2026-10 国产 183 款、进口 12 款 |
| 国内市场收入、用户规模、细分结构 | 中国音数协游戏工委《中国游戏产业报告》 | 二级 | 年度（12 月）+ 半年度（7 月） | 摘要免费，完整报告付费 | https://www.cgigc.com.cn/report.html | 已打开，2025 年度 3507.89 亿元、6.83 亿用户；2026 上半年 1884.5 亿元、6.84 亿用户 |
| 月度收入 | 伽马数据《中国游戏产业月度报告》 | 二级 | 月度 | 摘要免费，数据服务付费 | 官网 joynews.cn 已 404 且证书异常，经微信公众号「游戏产业报告」或镜像 | 官网已失效 |
| 电竞收入与用户 | 中国音数协《中国电子竞技产业报告》 | 二级 | 年度 + 半年度 | 摘要免费 | https://www.cadpa.org.cn/3277/202512/41769.html | 已打开，2025 年 293.31 亿元、4.95 亿用户 |
| A 股公司经营 | 巨潮资讯 | 一级 | 按交易所日程 | 免费 | https://www.cninfo.com.cn/ | 已打开 |
| 港股公司经营 | 香港交易所披露易 | 一级 | 按交易所日程 | 免费 | https://www.hkexnews.hk/index_c.htm | 已打开 |
| 买量成本与素材量 | DataEye | 二级 | 半年度 + 年度 + 专题 | 报告页免费，数据平台付费 | https://www.dataeye.com/report.html | 已打开 |
| 小游戏月活与用户画像 | QuestMobile | 二级 | 半年度（游戏）+ 季度（大盘） | 摘要免费，全文授权 | https://www.questmobile.cn/research/report/2079409273000030210 | 已打开，2026 上半年手游 App 月活 6.72 亿、微信小游戏 6.54 亿 |
| 手游行业专题 | 艾瑞咨询 | 二级 | 不定期 | 全文付费，摘要免费 | https://www.iresearch.com.cn/ | 已打开 |
| 单款产品榜与收入预估 | 点点数据 | 二级 | 实时榜单 + 年度报告 | 基础榜单免费，明细付费 | https://www.diandian.com/ | 已打开 |
| App Store 榜单 | 七麦数据 | 二级 | 实时 + 月度报告 | 榜单免费，报告需登录 | https://www.qimai.cn/ | 已打开 |
| 中国手游发行商全球收入 | Sensor Tower 中国站 | 二级 | 月度 | 摘要免费，数据平台付费 | https://sensortower-china.com/zh-CN/blog/2026-10-publisher-ranking | 已打开 |
| 玩家社区热度 | TapTap | 二级 | 实时 | 免费 | https://www.taptap.cn/top/played | 已打开，平台内活跃不代表全市场 |
| PC 游戏热度 | Steam 官方榜单 | 二级 | 实时 + 周 + 月 | 免费 | https://store.steampowered.com/charts/ | 已打开，热销榜按收入含 DLC |

口径陷阱：

1. 游戏工委的市场实际销售收入是**国内**市场，不含海外，海外单列美元；2026 年起总额新增桌游。
2. 同为 2025 年手游市场：游戏工委 2570.76 亿元、艾瑞 2693.4 亿元、点点 2859.2 亿元，统计范围不同，不能混用。
3. Sensor Tower 只覆盖 App Store 与 Google Play，中国大陆仅 iOS，是预估不是财报收入。
4. QuestMobile 的手游 App 月活（6.72 亿）不等于游戏用户规模（6.83 亿）。
5. 国家新闻出版署只发审批明细，不发汇总数，版号数量要自己按公示表计数。

机构状态变化：伽马数据官网 joynews.cn 已失效；data.ai 于 2024-03-18 被 Sensor Tower 收购，不再独立发布。

## 附录 B：全球游戏市场数据源（2026-11-16 核实，实施输入）

| 要回答什么 | 首选源 | 分级 | 频率 | 是否免费 | URL | 核实状态 |
|:---|:---|:---|:---|:---|:---|:---|
| 全球全口径规模与玩家数 | Newzoo | 二级 | 年度 | 摘要免费，完整数据集付费 | https://newzoo.com/reports | 已打开，2026 版 2026-08-13 |
| 移动与 Steam 收入 | Sensor Tower | 二级 | 年度 + 月度榜单 | 报告免费注册，企业版付费 | https://sensortower.com/report/state-of-gaming-2026 | 中文镜像可读 |
| 美国消费支出 | Circana | 二级 | 月度 | Top 10 免费，全量付费 | https://www.circana.com/post/top-10-video-games | 页面标题已核实，月度数据经媒体转载 |
| 欧洲销量 | GSD（Video Games Europe 运营） | 二级 | 周 / 月 / 季 | 摘要免费 | https://videogameseurope.eu/data-and-key-facts/games-sales-data | 已打开，发行商面板报送 |
| 美国玩家人口与消费 | ESA | 二级 | 年度 | 免费 | https://www.theesa.com/resources/essential-facts-about-the-us-video-game-industry/2026-data/ | 已打开，2026 版 |
| 英国市场规模 | UKIE | 二级 | 年度 | 免费 | https://ukie.org.uk/ | 已打开，2025 年 87.6 亿英镑、增 7.4% |
| 日本周销量 | Famitsu（KADOKAWA Game Linkage） | 二级 | 周 | 文章免费，白书付费 | https://www.famitsu.com/ | 已打开 |
| 亚洲与中东市场模型 | Niko Partners | 二级 | 年度 | 摘要免费，完整报告付费 | https://nikopartners.com/asia-mena-market-model-2026/ | 已打开 |
| Steam 在线与价格史 | SteamDB | 二级 | 实时 | 免费 | https://steamdb.info/ | 403，经第三方确认；2026-09-02 被 Chosen 收购 |
| Steam 拥有量与销量估算 | SteamSpy | 二级 | 实时 | 免费 | https://steamspy.com/ | 403；2018 年后新作估算不可靠 |
| 美国上市公司原始披露 | SEC EDGAR | 一级 | 实时 | 免费 | https://www.sec.gov/edgar/searchedgar/companysearch | 已打开 |
| 日本公司经营 | 索尼、任天堂、卡普空、万代南梦宫、Nexon 的投资者关系页 | 一级 | 季度 | 免费 | 各公司 IR 页 | 部分 403，经官方财报链接确认 |
| 欧美公司经营 | 微软、Take-Two、育碧、Roblox 的投资者关系页 | 一级 | 季度 | 免费 | 各公司 IR 页 | 部分 429，经 8-K 与新闻稿确认 |
| 日本行业报告 | CESA《ゲーム産業レポート》 | 付费二级 | 年度 | 付费约 5.5 万日元 | https://www.cesa.or.jp/action/industry-research/ | 已打开，2026 版 12 月预定 |
| 日本市场年鉴 | Media Create《ゲーム産業白書》 | 付费二级 | 年度 | 付费约 6.38 万日元 | https://www.m-create.com/ | 已打开 |
| Steam 与 PC 收入估算 | VG Insights | 付费二级 | 持续 | 付费 | vginsights.com 已 301 至 app.sensortower.com/vgi/ | 已确认重定向 |
| 移动收入与下载估算 | AppMagic | 付费二级 | 持续 | 免费层 + 付费 | https://appmagic.rocks/ | 主页 JS 未取到，第三方评测确认 |
| 全球市场预测 | Ampere Analysis、Omdia、IDC、MIDiA | 付费二级 | 季度或年度 | 付费 | 各机构产品页 | 部分 403，经官方新闻稿确认 |
| 开发者调查 | IGDA | 二级 | 两年一次 | 部分免费 | https://igda.org/surveys-reports/ | 已打开，最新 2023 版 |

口径陷阱：

1. Newzoo 是全球全口径（移动 + PC + 主机），2026 年预测约 2139 亿美元，自上而下的模型。
2. Sensor Tower 2025 年约 940 亿美元，只含移动内购 820 亿 + Steam 买断 120 亿，不含主机与广告收入。
3. Circana 只统计美国消费者支出（内容 + 硬件 + 配件），2026 年约 628 亿美元。
4. GSD 依赖发行商面板报送，覆盖 50 个地区，以销量为主，不是全市场普查。
5. 四者不可相加，也不能互相验证；跨机构数字必须先对齐口径。

机构状态变化：EA 于 2026-08-04 完成私有化退市，不再有公开季报；微软 FY2027 Q1 起取消原三大分部，Xbox 归入 Devices and Consumer；CESA 白书 2023 年版后改为《CESA ゲーム産業レポート》；SteamDB 于 2026-09-02 被 Chosen 收购。

## 留给实现者的选择

- 数据源文件是否再加一列「最近核实日期」，还是只在文件头写一次。建议只在文件头写，减少每次维护的字段。
- 是否写一个校核脚本，检查目录表与 `references/` 下的文件是否一一对应。建议本次不写，文件只有三个，人工可核；等挂载到五个以上再加。
- `SKILL.md` 的 description 触发词怎么定，由实现者按本仓其他技能的行文习惯处理。参考草稿：`"检索行业或市场数据之前，先确认该去哪些权威来源、这些来源的口径差别、搜到什么程度算够。按行业挂载数据源清单（当前：中国游戏行业、全球游戏市场），问题落到哪个行业才读哪个文件。同时用于判断某个来源的权威等级与证据是否充分。不用于：下载入库、引用格式校验、替代实际检索。"`
- 两个数据源文件的内容以附录 A、附录 B 为准。附录里的条目已逐条打开核实，实施时不再重新检索；实施前若用户提供新结果，以新结果为准。
