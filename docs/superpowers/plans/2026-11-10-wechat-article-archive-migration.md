# 微信公众号文章归档 skill 迁移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `wechat-article-archive` 从 `C:\Study\work\.claude\skills\` 搬进 shared-skills 插件，并把它与 work 知识库绑定的落盘约定留在 work 的规则里。

**Architecture:** 插件的 skill 只做四步（取正文、转 Markdown、核对保真、图片本地化），产物落到调用方给的输出目录；work 侧只改 `.claude/rules/知识库结构.md` §4.3，补文件头格式与 README 字段，然后删掉原 skill 目录。

**Tech Stack:** Node 22（取正文，走 CDP）、Python 3（转换与核对）、Bash（校验与仓库检查）。

**Spec:** `docs/superpowers/specs/2026-11-10-wechat-article-archive-migration-design.md`

## Global Constraints

- 三个脚本**一行不改**，只搬位置。
- SKILL.md 里的脚本路径一律写 `<skill目录>/scripts/<文件名>`，不出现任何工程的绝对路径。
- 版本号从 `1.30.1` 抬到 `1.31.0`，`plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json` 两处必须一致。
- 不自动提交；每个提交步骤都要先得到用户同意。
- 转换与核对脚本的判据不放松：缺失片段必须为 0。

## Review Focus

- **SKILL.md 里还留着 work 专属内容**：出现 `techblog`、`check_repo`、`知识库` 或 `C:/Study` 任何一处，这个技能在别的工程里就跑不通。由 Task 2 Step 2 的 grep 钉住。
- **脚本路径写成了绝对路径**：插件安装到哪儿由版本决定，写死路径必断。由 Task 2 Step 3 的 grep 钉住。
- **版本号两处不一致**：只改一处，插件按旧版本安装，改动静默不生效。由 Task 3 Step 3 的 `verify.sh` 钉住。
- **删了 work 的旧目录还留着引用**：由 Task 4 Step 4 的 grep 钉住。
- **§4.3 的改动没有自动检查**：`check_repo.py` 只管 `pages/`、`techblog/`、`news/`、`claude-code-changelog/`、`ui/` 五个目录，规则文件改漏不会报错。由 Task 4 Step 2 之后的 diff 复核钉住。

---

### Task 1: 把三个脚本搬进插件技能目录

**Files:**
- Create: `C:/Study/shared-skills/plugin/skills/wechat-article-archive/scripts/fetch_article.mjs`
- Create: `C:/Study/shared-skills/plugin/skills/wechat-article-archive/scripts/wechat_to_md.py`
- Create: `C:/Study/shared-skills/plugin/skills/wechat-article-archive/scripts/verify_fidelity.py`

**Interfaces:**
- Produces: 三个脚本的调用签名，Task 2 的 SKILL.md 照抄这三条：
  - `node <skill目录>/scripts/fetch_article.mjs "<url>" "<临时目录>"`
  - `python <skill目录>/scripts/wechat_to_md.py "<html>" "<body.md>"`
  - `python <skill目录>/scripts/verify_fidelity.py "<html>" "<body.md>"`

- [ ] **Step 1: 建目录并复制三个脚本**

```bash
mkdir -p "C:/Study/shared-skills/plugin/skills/wechat-article-archive/scripts"
cp "C:/Study/work/.claude/skills/wechat-article-archive/scripts/fetch_article.mjs" \
   "C:/Study/work/.claude/skills/wechat-article-archive/scripts/wechat_to_md.py" \
   "C:/Study/work/.claude/skills/wechat-article-archive/scripts/verify_fidelity.py" \
   "C:/Study/shared-skills/plugin/skills/wechat-article-archive/scripts/"
```

- [ ] **Step 2: 确认文件逐字节一致**

Run:
```bash
for f in fetch_article.mjs wechat_to_md.py verify_fidelity.py; do
  cmp "C:/Study/work/.claude/skills/wechat-article-archive/scripts/$f" \
      "C:/Study/shared-skills/plugin/skills/wechat-article-archive/scripts/$f" && echo "OK $f"
done
```
Expected: 三行 `OK`，无差异输出。

- [ ] **Step 3: 确认脚本能解析**

Run:
```bash
node --check "C:/Study/shared-skills/plugin/skills/wechat-article-archive/scripts/fetch_article.mjs"
python -m py_compile "C:/Study/shared-skills/plugin/skills/wechat-article-archive/scripts/wechat_to_md.py" "C:/Study/shared-skills/plugin/skills/wechat-article-archive/scripts/verify_fidelity.py"
```
Expected: 两条命令退出码 0，无输出。

---

### Task 2: 写通用化的 SKILL.md

**Files:**
- Create: `C:/Study/shared-skills/plugin/skills/wechat-article-archive/SKILL.md`

**Interfaces:**
- Consumes: Task 1 的三条命令。
- Produces: 技能被调用时给两样输入——公众号链接、输出目录；输出 `<输出目录>/body.md` 与 `<输出目录>/images/`。

- [ ] **Step 1: 写 SKILL.md**

必须包含的部分（句子自己组织）：

1. frontmatter：`name: wechat-article-archive`；`description` 说明使用时机（给出 mp.weixin.qq.com 链接、要求下载/归档公众号文章、抓到空壳或「环境异常」页），**不提 techblog**。
2. 开头一段说明：本技能取正文、转 Markdown、核保真、图片本地化，输出到调用方给的目录；目录结构、文件头、工程检查由调用方按自己的规则处理。
3. 核心问题：非浏览器访问一律返回「环境异常」验证页，只有带调试端口的真实 Chrome 过得去，所以必须走 CDP。
4. 四步，每步给命令与完成判据：
   - 第一步：`fetch_article.mjs`。Node 22 以上；退出码 2 = 需要人工过验证，过了重跑；`poc_token` 去掉再访问；判据是 `article.meta.json` 的 `title` 与 `publishTime` 都有值、HTML 是几十万字节量级。
   - 第二步：`wechat_to_md.py`。不要用 defuddle 或通用正文提取替代；判据是图片数等于 `grep -o 'data-src="[^"]*"' "<html>" | wc -l`。
   - 第三步：`verify_fidelity.py`。判据是「缺失片段 0 个」，多出的字符只限 `*`、`>`、`-`、数字与 `.`；有缺失就不要往下走。
   - 第四步：用 `shared-skills:download-md-images` 处理 `<输出目录>/body.md`，图落到同目录 `images/`；然后按文件头核一遍，命令如下（在输出目录下跑），列出的是 GIF 就把扩展名改成 `.gif` 并用 Edit 同步改正文里的引用：

     ```bash
     python -c "import pathlib;[print(p.name, p.read_bytes()[:6]) for p in sorted(pathlib.Path('images').glob('*.png')) if p.read_bytes()[:6] not in (b'\x89PNG\r\n',)]"
     ```
5. 常见问题表：照原表，删掉与技术无关的落盘条目，保留空壳、退出码 2、链接失效、Chrome 路径、图片数对不上、GIF 假扩展名。

- [ ] **Step 2: 检查没有 work 专属内容残留**

Run:
```bash
grep -n "techblog\|check_repo\|知识库\|C:/Study\|C:\\\\Study" "C:/Study/shared-skills/plugin/skills/wechat-article-archive/SKILL.md"
```
Expected: 无输出。

- [ ] **Step 3: 检查脚本路径写法**

Run:
```bash
grep -n "scripts/" "C:/Study/shared-skills/plugin/skills/wechat-article-archive/SKILL.md"
```
Expected: 三条命令都写成 `<skill目录>/scripts/<文件名>`，没有别的路径形式。

- [ ] **Step 4: 检查 frontmatter 能被解析**

Run:
```bash
python -c "import pathlib,re;p=pathlib.Path(r'C:/Study/shared-skills/plugin/skills/wechat-article-archive/SKILL.md');t=p.read_text(encoding='utf-8');m=re.match(r'^---\r?\n(.*?)\r?\n---',t,re.S);print('OK' if m and 'name: wechat-article-archive' in m.group(1) else 'FAIL')"
```
Expected: `OK`。

---

### Task 3: README 收录表与版本号

**Files:**
- Modify: `C:/Study/shared-skills/README.md`（「收录的 skill」表）
- Modify: `C:/Study/shared-skills/plugin/.claude-plugin/plugin.json`（`version` 与 `description`）
- Modify: `C:/Study/shared-skills/.claude-plugin/marketplace.json`（`version` 与 `description`）

- [ ] **Step 1: README 表格加一行**

在「收录的 skill」表末尾加：

```markdown
| `wechat-article-archive` | 把一篇微信公众号文章完整取下来：走带调试端口的真实 Chrome 过「环境异常」验证页，正文转 Markdown、图片存本地、逐字核对无缺失。输出到一个指定目录（`body.md` 与 `images/`），目录怎么命名、文件头怎么写由调用方决定。 |
```

- [ ] **Step 2: 两处版本号与描述同步**

`plugin/.claude-plugin/plugin.json` 与 `.claude-plugin/marketplace.json`：
- `version` 由 `1.30.1` 改为 `1.31.0`。
- 两处 `description` 的技能清单里补「公众号文章归档」，保证两处文字一致。

- [ ] **Step 3: 跑仓库检查**

Run:
```bash
bash "C:/Study/shared-skills/checks/verify.sh" --changed
```
Expected: 全部 PASS；版本一致性模块不报「内容动过、版本号还没抬」。
若 `--changed` 没有挑到版本模块，改跑全量：`bash "C:/Study/shared-skills/checks/verify.sh"`。

- [ ] **Step 4: 提交（先征得用户同意）**

```bash
git -C "C:/Study/shared-skills" add plugin/skills/wechat-article-archive README.md plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json docs/superpowers/specs/2026-11-10-wechat-article-archive-migration-design.md docs/superpowers/plans/2026-11-10-wechat-article-archive-migration.md
```
提交信息用中文，按仓库「提交规则」的 heredoc 写法。

---

### Task 4: work 侧规则改动与旧目录删除

**Files:**
- Modify: `C:/Study/work/.claude/rules/知识库结构.md` §4.3
- Delete: `C:/Study/work/.claude/skills/wechat-article-archive/`（整个目录）

**Interfaces:**
- Consumes: Task 2 产出的技能，调用时给出输出目录。
- Produces: work 归档流程里要用的文件头格式与 README 字段。

- [ ] **Step 1: §4.3 增加「正文文件头」一段**

在 §4.3 的目录结构说明之后加：

```markdown
**正文文件头**——所有从外部归档的单篇文章，正文开头照这个格式写（第一行是文章标题）：

```markdown
# <标题>

**来源**: <来源，公众号写 微信公众号「<公众号名>」>

**作者**: <作者>

**原文链接**: <去掉临时参数的规范链接>

**存档日期**: <今天>（原文发布于 YYYY-MM-DD HH:MM）
```

日期取原文的发布时间，不拿抓取时间或页面里的其他时间戳推算。
```

- [ ] **Step 2: 子目录 README 字段补齐**

把 §4.3 里「索引：中文标题、源地址、抓取日期、转换方式、图片张数」改成
「索引：中文标题、来源、源地址、发布日期、抓取日期、正文文件名、转换方式、图片张数」。

- [ ] **Step 2b: 复核规则文件的改动**

Run:
```bash
git -C "C:/Study/work" diff -- .claude/rules/知识库结构.md
```
Expected: 只有两处改动——新增「正文文件头」一段、README 字段列表多了三项。

- [ ] **Step 3: 删除旧的 skill 目录**

```bash
rm -rf "C:/Study/work/.claude/skills/wechat-article-archive"
```

删除前确认该目录里只有 `SKILL.md` 与 `scripts/` 下的三个文件。

- [ ] **Step 4: 确认没有指向已删路径的引用**

Run（扫全仓，别漏 `techblog/` 里指向旧路径的说明）:
```bash
grep -rn "\.claude/skills/wechat-article-archive" "C:/Study/work" --include="*.md" 2>/dev/null | grep -v "/\.git/\|/\.superpowers/\|/\.tmp/"
```
Expected: 无输出。有输出就逐条改成指向 shared-skills 插件的 `wechat-article-archive` 技能。

- [ ] **Step 5: 跑 work 的仓库检查**

Run:
```bash
python "C:/Study/work/checks/check_repo.py"
```
Expected: 通过。

- [ ] **Step 6: 提交（先征得用户同意）**

```bash
git -C "C:/Study/work" add .claude/rules/知识库结构.md .claude/skills/wechat-article-archive
```
提交信息用中文，按 work 仓库「提交规则」的 heredoc 写法。

