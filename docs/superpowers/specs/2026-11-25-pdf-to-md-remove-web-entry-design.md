# pdf-to-md：拆掉官网方式的入口，代码保留

## 背景

pdf-to-md 现在对外有两条路：默认走浏览器，把 PDF 上传到 AI Studio 官网、登录后等它解析、从下载菜单取 JSON；另一条是本地脚本带 token 调 AI Studio 的异步解析接口。官网方式要维护登录、凭据文件、浏览器配置目录、页面选择器，用户决定不再对外提供。

用户明确要求：**保留代码，移除入口和技能描述，允许残留。** 即删掉调用面，`aistudio_web.py` 等实现留着不删。

## 目标

- 技能描述与文档只讲接口方式：不开浏览器、不登录、不上传官网、不下载官网 JSON。
- 命令行与体检不再接受官网相关参数；默认参数回到加官网之前的形状。
- 现有测试全部通过；残留代码的单元测试保留并继续通过。

## 非目标

- 不删除 `scripts/aistudio_web.py`、`convert.py` 的 `run_web`、`convert_one` 的 `backend`/`web_session` 参数、`markdown.parse_official_json`。
- 不改 `doctor.py` 里的 `check_profile_dir`、`check_credentials` 函数体。
- 不改动 `docs/superpowers/` 下的历史设计与计划文档。
- 不改变接口方式本身的行为（提交、轮询、取图、落盘、财报逐页、多 KEY）。

## 关键决定

**入口边界**：入口是命令行参数、体检选项、`SKILL.md` 与技能 `README.md` 的描述。实现代码不算入口。

**删掉 `--backend` 参数，而不是只删 `official-web` 选项。** 加官网方式之前（提交 49fcc69 之前）`convert.py` 没有这个参数；删掉后命令行回到那一版形状。旧命令里带 `--backend api` 会直接报参数错误，这是有意为之。

**`--jobs` 默认恢复成 4**（加官网时为了浏览器一次一份改成了按后端取值）。

**体检固定接口链路**：`doctor.py` 删 `--backend`，只查 uv、token、输出目录，再真转一份样例。官网相关检查函数留着但不再调用。

**测试按「代码还在不在」取舍**：断言官网参数、官网默认后端的用例删掉或改成断言参数不存在；`aistudio_web` 模块单测、`convert_one(backend="official-web")` 的用例保留。

## 改动文件

| 文件 | 改什么 |
|:---|:---|
| `plugin/skills/pdf-to-md/scripts/convert.py` | 删六个参数及校验；`main` 只走 `run`；`run_web`、`import aistudio_web`、`WEB_REQUIRED` 等留着 |
| `plugin/skills/pdf-to-md/scripts/doctor.py` | 删 `--backend`；体检只跑接口链路；官网检查函数留着 |
| `plugin/skills/pdf-to-md/SKILL.md` | 重写技能描述与正文：删官网三节、参数六项、debug 里的官网产物、局限里的官网条目 |
| `plugin/skills/pdf-to-md/README.md` | 文件结构标注 `aistudio_web.py` 为残留；删「官网流程要真跑一遍」 |
| `tests/pdf-to-md/test_pdf_to_md.py` | 删/改官网参数与默认后端的用例，其余保留 |
| `plugin/.claude-plugin/plugin.json`、`.claude-plugin/marketplace.json` | 版本号 1.35.4 → 1.35.5 |

仓库根 `README.md` 的技能表已经写的是接口方式，不动。

## 测试计划

- 跑 `bash tests/run.sh pdf-to-md`，全绿。
- 手动确认 `convert.py --help` 不再出现六个官网参数，`--jobs` 默认 4。
- 手动确认 `doctor.py --help` 没有 `--backend`。
- 在 SKILL.md 与技能 README 里 grep「官网」「浏览器」「登录」「playwright」「browser-profile」「credentials」，只剩说明残留的地方。

## 验收标准

- 技能文档里不再教任何人登录官网或走浏览器。
- 命令行不接受官网参数，报错清楚（argparse 的「unrecognized arguments」）。
- 残留代码不被调用、不阻碍接口方式运行；相关单测照常通过。
- 版本号两处一致。

## 留给实现的人

- `SKILL.md` 里「原来的接口还能用，加 --backend api」这类对比句要改成直述，不能留下「默认是官网」的暗示。
- `convert.py` 里 `run(tasks, args)` 用 `getattr(args, "backend", "api")` 取值，删参数后仍返回 `"api"`，可以原样保留。
- 测试里若有用例导入 `aistudio_web` 或调 `convert_one(backend="official-web")`，保留；只改断言参数与默认值的那些。
