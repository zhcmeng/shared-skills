# 跨页表格合并 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 财报单页模式下，把被页边界切断的同一张表接成一张，表头只出现一次。

**Architecture:** `parse_jsonl` 把服务返回的版面坐标装进 `Page`；`markdown.py` 新增纯函数 `merge_cross_page_tables`，按「块顺序 + 位置 + 列数 + 第一行内容」判断，在 HTML 上把下一页的表格行接到上一页的表格里；`convert.py` 只在财报单页路径上调用它。

**Tech Stack:** Python 3、lxml、tabulate、pypdf（仅财报切页）、unittest。

**Spec:** `docs/superpowers/specs/2026-10-18-pdf-to-md-cross-page-table-merge-design.md`

## Global Constraints

- 只改 `plugin/skills/pdf-to-md`、`tests/pdf-to-md`、文档；不动 `C:\investment` 下的知识库内容。
- 合并只在财报单页模式调用；普通模式产物必须与改动前逐字节相同。
- 不新增依赖；不用 pdfplumber，不自己解析 PDF 的线条。
- 判断不确定时不合并：可见的漏合优于隐蔽的误合。
- 不把 token 写进任何文件、日志、提交。
- 文件名用英文；正文、注释、提交信息用中文。
- 改文件用 Read/Edit/Write；命令里的路径写全；等待挂事件，不用 sleep。
- 每条提交信息末尾加 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`。
- 测试不发真实请求；真实素材只在 Task 5 的验收步骤里手工跑。
- 插件版本号抬最后一位（1.26.44 → 1.26.45），`plugin/.claude-plugin/plugin.json` 与根 `.claude-plugin/marketplace.json` 两处一致。

**聚焦测试的跑法**（下文统一写成 `<聚焦测试>`）：

```bash
uv run --with requests --with lxml --with tabulate --with pypdf \
  python C:/Study/shared-skills/tests/pdf-to-md/test_pdf_to_md.py <Class.test> -v
```

全量测试：`bash C:/Study/shared-skills/tests/run.sh pdf-to-md`

## Review Focus

1. 上一页表格在页面中间结束、下面留白，下一页开头是另一张表 → 必须不合并。
2. 续表重复多行表头，或表头里有 `colspan` → 表头只留一次，数据行不能误删。
3. 一页里既有上一张表的结尾、又有下一张表的开头 → 两条链各接各的，不能串。
4. 要接的表里有 `<img>` → 不合并，否则图片引用会落到别的页。
5. 缺页眉或页码坐标、两页尺寸不同 → 不合并。

---

### Task 1: 把版面坐标装进 Page

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/markdown.py`（`Page`、`parse_jsonl`、新增 `_page_geometry`）
- Modify: `plugin/skills/pdf-to-md/scripts/convert.py:366-372`（`_convert_single_pages` 重建 `Page`）
- Test: `tests/pdf-to-md/test_pdf_to_md.py`（`jsonl_line`、`TestParseJsonl`）

**Interfaces:**
- Consumes: 无。
- Produces:
  - `Page.blocks: tuple[tuple[str, tuple[float, float, float, float]], ...]`，默认 `()`；
  - `Page.page_size: tuple[float, float] | None`，默认 `None`；
  - `parse_jsonl(raw: str) -> list[Page]` 填这两个字段；
  - `_page_geometry(pruned: dict) -> tuple[tuple, tuple | None]`。

- [ ] **Step 0: 先把设计与计划提交**

```bash
git -C C:/Study/shared-skills add docs/superpowers/specs/2026-10-18-pdf-to-md-cross-page-table-merge-design.md docs/superpowers/plans/2026-10-18-pdf-to-md-cross-page-table-merge.md
git -C C:/Study/shared-skills commit -m "docs: 落定跨页表格合并的设计与实施计划" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 1: 写失败的测试**

在 `jsonl_line` 上加可选参数 `pruned=None`：给了就按页附上 `prunedResult`。

```python
def test_blocks_and_page_size_are_read(self):
    pruned = {"width": 1191, "height": 1685, "parsing_res_list": [
        {"block_label": "header", "block_bbox": [650, 86, 1081, 108]},
        {"block_label": "table", "block_bbox": [112, 231, 1081, 1520]}]}
    raw = jsonl_line([("正文", {})], pruned=[pruned])
    page = parse_jsonl(raw)[0]
    self.assertEqual(page.page_size, (1191.0, 1685.0))
    self.assertEqual(page.blocks,
                     (("header", (650.0, 86.0, 1081.0, 108.0)),
                      ("table", (112.0, 231.0, 1081.0, 1520.0))))

def test_no_pruned_result_gives_empty_geometry(self):
    page = parse_jsonl(jsonl_line([("正文", {})]))[0]
    self.assertEqual(page.blocks, ())
    self.assertIsNone(page.page_size)

def test_malformed_blocks_are_skipped(self):
    pruned = {"width": 1191, "height": 1685, "parsing_res_list": [
        {"block_label": "table", "block_bbox": [1, 2, 3]},
        {"block_label": "table", "block_bbox": "x"},
        {"block_label": 7, "block_bbox": [1, 2, 3, 4]},
        {"block_label": "table", "block_bbox": [1, 2, 3, 4]}]}
    page = parse_jsonl(jsonl_line([("正文", {})], pruned=[pruned]))[0]
    self.assertEqual(page.blocks, (("table", (1.0, 2.0, 3.0, 4.0)),))
```

- [ ] **Step 2: 跑测试，确认它真的在看这两个字段**

Run: `<聚焦测试>` 指向 `TestParseJsonl.test_blocks_and_page_size_are_read`

工作区里已有试验性的 `Page.blocks`、`_page_geometry` 实现，测试可能直接通过。为确认测试不是空转，临时把 `parse_jsonl` 里的 `blocks=blocks` 去掉，再跑一次，**必须变红**；然后恢复。

- [ ] **Step 3: 实现并透传**

- `Page` 增加 `blocks`、`page_size` 两个带默认值的字段；
- `_page_geometry` 从 `prunedResult` 取 `width`、`height`、`parsing_res_list`；形状不对的块跳过（不是表格字段，坏了不该让整份失败）；
- `parse_jsonl` 把两者填进 `Page`；
- `_convert_single_pages` 重建 `Page` 时带上 `blocks=page.blocks, page_size=page.page_size`。

- [ ] **Step 4: 跑测试确认通过**

Run: `bash C:/Study/shared-skills/tests/run.sh pdf-to-md`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git -C C:/Study/shared-skills add plugin/skills/pdf-to-md/scripts/markdown.py plugin/skills/pdf-to-md/scripts/convert.py tests/pdf-to-md/test_pdf_to_md.py
git -C C:/Study/shared-skills commit -m "feat(pdf-to-md): 保留每页的版面块坐标" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: 判断两张表该不该接

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/markdown.py`
- Test: `tests/pdf-to-md/test_pdf_to_md.py`（新增 `TestCrossPageTablePair`）

**Interfaces:**
- Consumes: `Page.blocks`、`Page.page_size`（Task 1）。
- Produces:
  - `_cross_page_table_pair(prev_page, next_page, ignore_labels) -> tuple[tuple[int, int], tuple[int, int]] | None`：返回两张表的 `(起, 止)` 区间；不该接就 `None`；
  - 常量 `_EDGE_TOLERANCE_RATIO = 0.05`、`_EDGE_ALIGN_RATIO = 0.02`、`_PAGE_SIZE_TOLERANCE = 0.02`。

- [ ] **Step 1: 写失败的测试**

测试辅助：

```python
BOTTOM_BLOCKS = (("header", (650, 86, 1081, 108)),
                 ("table", (112, 231, 1081, 1520)),
                 ("number", (1057, 1566, 1081, 1586)))
TOP_BLOCKS = (("header", (650, 86, 1082, 108)),
              ("table", (110, 143, 1082, 1500)),
              ("number", (1057, 1566, 1081, 1586)))

def make_page(text, blocks, size=(1191, 1685), index=0):
    return Page(index=index, text=text, images={}, blocks=blocks, page_size=size)
```

要覆盖的断言：

```python
def test_a_table_at_the_page_bottom_and_top_is_a_continuation(self)   # 不是 None
def test_a_table_that_stops_mid_page_is_not_a_continuation(self)      # 底边改 1200 → None
def test_a_table_that_starts_low_on_the_next_page_is_not(self)        # 顶边改 300 → None
def test_misaligned_left_or_right_edge_blocks_the_merge(self)         # 左边改 200 → None
def test_different_page_sizes_block_the_merge(self)                   # 1000×1685 → None
def test_missing_header_or_number_anchor_blocks_the_merge(self)       # 去掉任一 → None
def test_different_column_counts_block_the_merge(self)                # 3 列 vs 2 列 → None
def test_a_paragraph_before_or_after_the_table_blocks_the_merge(self) # 块顺序 → None
def test_text_before_or_after_the_table_blocks_the_merge(self)        # 正文顺序 → None
```

前两页的正文分别用 3 列的 HTML 表：上一页以表结尾，下一页以表开头。

- [ ] **Step 2: 跑测试确认失败**

Run: `<聚焦测试>` 指向 `TestCrossPageTablePair`

Expected: FAIL，`_cross_page_table_pair` 不存在

- [ ] **Step 3: 实现判断**

在 `markdown.py` 实现 `_cross_page_table_pair`：

- 两页都要有 `page_size`，宽、高相差不超过 2%；
- 用 `ignore_labels` 过滤后的内容块：上一页最后一个是 `table`，下一页第一个是 `table`；
- 两页正文里的 `<table>` 块数要与版面块里的 `table` 数一致，否则 `None`；
- 上一页正文以表格结尾、下一页正文以表格开头（用 `_find_table_spans` 取第一个/最后一个区间，区间外只允许空白）；
- 锚点：页眉取 `header`/`header_image` 里底边最大的；页码取 `number`，没有就取 `footer`/`footer_image` 顶边最小的；缺任一 → `None`；
- 上一页表格底边 ≥ 页码顶边 − 5% 页高；下一页表格顶边 ≤ 页眉底边 + 5% 页高；
- 左右边界各相差 ≤ 2% 页宽；
- `_table_grid` 的网格宽度相同。

- [ ] **Step 4: 跑测试确认通过**

Run: `bash C:/Study/shared-skills/tests/run.sh pdf-to-md`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git -C C:/Study/shared-skills add plugin/skills/pdf-to-md/scripts/markdown.py tests/pdf-to-md/test_pdf_to_md.py
git -C C:/Study/shared-skills commit -m "feat(pdf-to-md): 判断两张表是否跨页相连" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: 在 HTML 上接表格

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/markdown.py`
- Test: `tests/pdf-to-md/test_pdf_to_md.py`（新增 `TestMergeCrossPageTables`）

**Interfaces:**
- Consumes: `_cross_page_table_pair`（Task 2）。
- Produces: `merge_cross_page_tables(pages, ignore_labels=()) -> list[Page]`，返回新页表，不就地改原对象。

- [ ] **Step 1: 写失败的测试**

用 `make_page` 造页，表格用 HTML。要覆盖：

```python
def test_rows_are_appended_and_the_header_appears_once(self)
def test_a_repeated_header_row_is_dropped(self)
def test_a_repeated_multi_row_header_is_dropped(self)
def test_a_colspan_header_is_not_mistaken_for_data(self)      # 不合并
def test_a_data_first_row_is_kept(self)                        # 「流动负债：」保留
def test_a_new_table_header_blocks_the_merge(self)             # 不合并
def test_three_pages_form_one_table(self)                      # 表链
def test_two_chains_on_one_page_do_not_cross(self)             # 两条链各接各的
def test_a_table_with_an_image_is_not_merged(self)             # 不合并
def test_text_after_the_next_table_is_preserved(self)          # 签名行还在
```

断言用渲染后的 Markdown，例如：

```python
merged = merge_cross_page_tables([prev, nxt], ignore_labels={"header", "number"})
md = clean_markdown(merged[0].text, None)
self.assertEqual(md.count("| 项目"), 1)
self.assertIn("| 资产总计", md)
self.assertIn("| 流动负债：", md)
self.assertEqual(clean_markdown(merged[1].text, None).strip(), "法定代表人：江南春")
```

其余几条的关键断言：

```python
# 重复表头：表头文字只出现一次
self.assertEqual(md.count("| 项目"), 1)
self.assertEqual(md.count("| 流动负债："), 1)

# 多行表头：两行表头都只出现一次
self.assertEqual(md.count("| 项目"), 1)
self.assertEqual(md.count("| 期末余额"), 1)

# colspan 表头、正文像新表头、表里有图：都不合并，第二页的表还在
merged = merge_cross_page_tables([prev, nxt], ignore_labels={"header", "number"})
md2 = clean_markdown(merged[1].text, None)
self.assertTrue(md2.lstrip().startswith("|"))

# 三页链：三页的数据行都在同一张表里，表头只出现一次
merged = merge_cross_page_tables([p1, p2, p3], ignore_labels={"header", "number"})
md = clean_markdown(merged[0].text, None)
self.assertEqual(md.count("| 项目"), 1)
for row in ("| 第一页数据", "| 第二页数据", "| 第三页数据"):
    self.assertIn(row, md)

# 两条链：第三页的行只能跟在第二页那张表后面
md1 = clean_markdown(merged[0].text, None)
md2 = clean_markdown(merged[1].text, None)
self.assertIn("| A2", md1)
self.assertNotIn("| C", md1)
self.assertIn("| B2", md2)
self.assertIn("| C", md2)
```

三页链的断言：三页各自的唯一数据行都在同一张表里，表头只出现一次。两条链的断言：第三页的行只能出现在第二页那张表后面，不能出现在第一页那张表里。

- [ ] **Step 2: 跑测试确认失败**

Run: `<聚焦测试>` 指向 `TestMergeCrossPageTables`

Expected: FAIL，`merge_cross_page_tables` 不存在

- [ ] **Step 3: 实现合并**

`merge_cross_page_tables` 的做法（这是本计划唯一需要按算法写的地方）：

1. 少于两页直接返回。
2. 每页取第一个和最后一个表格区间；只有一个表格时两者相同。
3. 按页序逐对判断：用 `_cross_page_table_pair` 找出「上页最后一张表 ← 下页第一张表」的链接。
4. 表头处理：把下页表的开头几行，与链接目标所在那条链的**根表**开头几行逐行比；相同的整段删掉，最多 5 行。一行都对不上时，若下页第一行有空单元格或含数字就保留；否则不建链接。表里有 `<img>` 也不建链接。
5. 建链：`root_of[目标]` 记根表；`source → (target, drop)` 记链接。单表连跨三页时，同一个表格实例可以既是上一段的结尾、又是下一段的开头。
6. 从每个根表出发按链接顺序收行：根表的行 + 每个下页表删掉 `drop` 行后的行；把根表的区间替换成新 `<table>`，其余区间从各自页面的正文里删掉。
7. 用 `dataclasses.replace` 生成新 `Page`，正文改完之后返回；`images`、`blocks`、`page_size` 原样保留。

- [ ] **Step 4: 跑测试确认通过**

Run: `bash C:/Study/shared-skills/tests/run.sh pdf-to-md`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git -C C:/Study/shared-skills add plugin/skills/pdf-to-md/scripts/markdown.py tests/pdf-to-md/test_pdf_to_md.py
git -C C:/Study/shared-skills commit -m "feat(pdf-to-md): 把跨页的表格接成一张" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: 接进财报单页路径

**Files:**
- Modify: `plugin/skills/pdf-to-md/scripts/convert.py:428-435`
- Test: `tests/pdf-to-md/test_pdf_to_md.py`（`TestFinancialSinglePage`）

**Interfaces:**
- Consumes: `merge_cross_page_tables`、`Page.blocks`、`Page.page_size`。
- Produces: 财报单页输出里跨页表格已合并；普通模式不变。

- [ ] **Step 1: 写失败的测试**

给 `TestFinancialSinglePage.fake_api` 加 `pruned=None` 参数，按页把几何附到 `jsonl_line` 上。新增：

```python
def test_pages_whose_tables_line_up_are_stitched(self)
def test_pages_without_geometry_stay_split(self)
```

第一条：两页的正文各是一张 3 列的 HTML 表，`pruned` 用 Task 2 的 `BOTTOM_BLOCKS` / `TOP_BLOCKS`；转完读 md，断言 `| 项目` 只出现一次，且 `| 流动负债` 在里面。

第二条：不给 `pruned`，断言正文里两张表各自保留表头。

- [ ] **Step 2: 跑测试确认失败**

Run: `<聚焦测试>` 指向 `TestFinancialSinglePage.test_pages_whose_tables_line_up_are_stitched`

Expected: FAIL，输出里有两张表

- [ ] **Step 3: 实现接线**

- `_convert_single_pages` 重建 `Page` 时带上 `blocks`、`page_size`（Task 1 已改；确认没漏）；
- `convert_one` 的财报分支，在 `_convert_single_pages` 之后、`_finish_document` 之前调用：

```python
pages = md_utils.merge_cross_page_tables(
    pages,
    ignore_labels=aistudio.FINANCIAL_OPTIONAL_PAYLOAD["markdownIgnoreLabels"])
```

- [ ] **Step 4: 跑测试确认通过**

Run: `bash C:/Study/shared-skills/tests/run.sh pdf-to-md`
Expected: 全部通过；普通模式的既有测试不变

- [ ] **Step 5: 提交**

```bash
git -C C:/Study/shared-skills add plugin/skills/pdf-to-md/scripts/convert.py tests/pdf-to-md/test_pdf_to_md.py
git -C C:/Study/shared-skills commit -m "feat(pdf-to-md): 财报路径合并跨页表格" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: 文档、版本与真实素材验收

**Files:**
- Modify: `plugin/skills/pdf-to-md/SKILL.md`
- Modify: `docs/superpowers/specs/2026-09-20-pdf-to-md-design.md`（已知局限里跨页表格那条）
- Modify: `docs/superpowers/specs/2026-10-18-pdf-to-md-cross-page-table-merge-design.md`（状态改为「已实现」）
- Modify: `plugin/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json`
- Test: 手工验收

- [ ] **Step 1: 更新文档**

- `SKILL.md` 的「财报：逐页提交」加一句：跨页的表格会按版面坐标判断，能确认是同一张就接成一张、表头只留一次；判断不了就保持两张。
- 旧设计文档的「已知局限」里，「跨页的表格会断成两截」改成：财报单页模式在有足够坐标证据时会接回去；普通模式仍然按页断开。
- 新设计文档状态改为「已实现」。

- [ ] **Step 2: 抬版本号**

两个文件都从 `1.26.44` 改成 `1.26.45`。

- [ ] **Step 3: 跑测试与仓库检查**

Run: `bash C:/Study/shared-skills/tests/run.sh pdf-to-md`
Expected: 全部通过

Run: `bash C:/Study/shared-skills/checks/verify.sh --changed`
Expected: 全部通过

- [ ] **Step 4: 真实素材验收**

从 `C:\investment\financial-reports\2025-04-29-分众传媒_2024年年度报告.pdf` 取第 75、76 页做成临时 PDF，用财报模式转一遍（会花 2 页配额）：

```bash
python -c "
from pypdf import PdfReader, PdfWriter
r = PdfReader(r'C:/investment/financial-reports/2025-04-29-分众传媒_2024年年度报告.pdf')
w = PdfWriter(); w.add_page(r.pages[74]); w.add_page(r.pages[75])
with open(r'C:/Users/Administrator/.claude/jobs/4ad92316/tmp/parent-bs-pages-75-76.pdf', 'wb') as f:
    w.write(f)
"
```

Expected（读转出来的 md）：

- 只有一张表，3 列；
- `| 项目` 只出现一次，`| 流动负债：` 作为数据行保留；
- `资产总计 56,214,418,816.41`、`负债和所有者权益总计 56,214,418,816.41` 与 PDF 原文一致；
- 「法定代表人：江南春」等签名行还在。

- [ ] **Step 5: 提交**

```bash
git -C C:/Study/shared-skills add plugin/skills/pdf-to-md/SKILL.md docs/superpowers/specs/2026-09-20-pdf-to-md-design.md docs/superpowers/specs/2026-10-18-pdf-to-md-cross-page-table-merge-design.md plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git -C C:/Study/shared-skills commit -m "docs(pdf-to-md): 补跨页表格合并说明并抬版本号" -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-Review

- Spec coverage：目标、四条判断、合并规则、表链、图片护栏、位置锚点、测试计划、验收标准，分别落在 Task 1–5。
- 类型一致：`Page.blocks`、`Page.page_size`、`_page_geometry`、`_cross_page_table_pair`、`merge_cross_page_tables` 在所有任务里写法一致。
- 测试与 Review Focus 对应：留白、缺锚点、尺寸不同在 Task 2；多行表头/`colspan`、两条链、图片、签名行在 Task 3。
- 未覆盖：真实素材的端到端结果只在 Task 5 手工验收，单元测试不联网。
