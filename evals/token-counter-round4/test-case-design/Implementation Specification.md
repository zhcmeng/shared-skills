# 实施方案规格说明

这一份把同目录那六份通用设计稿落成能跑的东西。那六份说的是「要什么」——要建哪些模型、要覆盖哪些项、要跑哪些用例与规程；这一份说的是「用哪个测评方案、怎么摆」——这些用例落成哪种能跑的形式、落在盘上哪个路径、编号在盘上怎么留痕。**两边对同一件事的说法不一致时，以这一份为准。**

方案按节分。这一份现在只有 skill-up 一个方案；将来要拿同一套通用稿比第二个方案，就在这一份里另起一节，六份一个字不用动。

## 一、通用稿的编号落到哪

下面这张表把六份里定义过的每一条编号对到本方案里的具体落点。落点写的是从**评测材料根**（`evals/token-counter-round4/`）算起的相对路径——产出目录是它底下的 `test-case-design/`，落成的东西与产出目录并列，不住在它里面。

| 通用稿的编号 | 本方案里落在哪 | 说明 |
|:---|:---|:---|
| TM-1、TM-2、TM-3 | 不落成盘上能跑的东西；靠它们导出的覆盖项号在盘上留痕 | 模型是设计那一层的产物，这一套方案里没有对应的配置项。三门技术各建一个模型，导出的覆盖项落在下一行那些注释里 |
| TCOV-1、TCOV-2、TCOV-3、TCOV-4、TCOV-5、TCOV-6、TCOV-7、TCOV-8、TCOV-9、TCOV-10、TCOV-11、TCOV-12、TCOV-13、TCOV-14、TCOV-15、TCOV-16、TCOV-17、TCOV-18、TCOV-19、TCOV-20、TCOV-21、TCOV-22、TCOV-23、TCOV-24、TCOV-25、TCOV-26、TCOV-27、TCOV-28、TCOV-29、TCOV-30、TCOV-31、TCOV-32、TCOV-33、TCOV-34 | `cases/` 下覆盖它的那几条用例配置里，输入与判据上方那几行注释 | 一条覆盖项出现在覆盖它的每一条用例的配置里，对应关系照 `Test Case Specification.md` 的对应表。**TCOV-16 判为不可行，盘上一个字都不出现**——设计稿里就写着从分母里剔除，不是落的时候漏了 |
| TC-1、TC-2、TC-3、TC-4、TC-5、TC-6、TC-7、TC-8、TC-9、TC-10、TC-11、TC-12、TC-13、TC-14、TC-15、TC-16 | `cases/` 下 16 个用例配置，一条用例一个文件 | 文件名照 `scripts/issue_ids.py --case-dirs` 打出来的那串加 `.yaml`。执行位次就在文件名里（`tp01-01` 那一段），字母序等于执行顺序，不另外排 |
| TP-1、TP-2、TP-3 | 常规批那一份批次配置 `eval.yaml` 的 `cases.files` 那一段 | 三条规程共 15 条用例，按规程内位次连排列在同一份配置里，不再分段——一份配置就是一批 |
| TP-4 | 干净解释器批那一份批次配置 `eval-clean-interpreter.yaml` | 单独一份。它要一个没装引擎的解释器，而「装不装引擎」只能整批配一次，与其余三条规程合不进同一批 |
| DATA-1 | `cases/` 下用到它的那几条用例配置的 `input.prompt` 里，四段文本按编号原样接在请求后面 | 没有做成夹具文件——四段都是直接接在用户那句话里的。第 1 段进 TC-1、TC-9、TC-10、TC-11，第 2 段进 TC-2、TC-16，第 3 段进 TC-3，第 4 段（空串）进 TC-6；空的那一段在消息里写成「就是 0 个字符的那一段」 |
| DATA-2 | `cases/tp01-07-TC-7-special_token_literal.yaml` 的 `input.prompt` | 那段含特殊 token 字面形的文本原样接在请求后面 |
| DATA-3 | 那份 .md 样本走 `cases/tp01-04-TC-4-file_markdown_path.yaml` 里的 `context.files` | 正文三段照测试数据需求的表下正文写进配置，工作区根下就是 `sample.md`。字节按不带字节顺序标记的 UTF-8、末尾一个换行摆 |
| DATA-4 | 那段要喂进管道的样本走 `cases/tp01-05-TC-5-stdin_route.yaml` 里的 `context.files` | 先在工作区里存成一个文件，`input.prompt` 里说清是喂进去、不是把路径当参数传 |
| DATA-5 | `cases/tp02-01-TC-8-text_for_full_dialogue.yaml` 的 `input.prompt` | 要估的那段用户消息原样写进请求 |
| DATA-6 | 三条走不通的路径分两处：不存在的那条路径写在 `cases/tp03-01-TC-12-no_route_given.yaml` 之外的 `cases/tp03-02-TC-13-file_missing.yaml` 的消息里；目录与那份 GBK 文件由 `fixtures/samples/` 铺进工作区 | 走 `context.repo_fixture` 指到 `fixtures/samples`，里面摆 `a-directory/`（带一个占位文件，好让这一层目录进得去版本库）与 `gbk-sample.txt`（那五个字按 GBK 编出的十个字节，有意不存成 UTF-8）。TC-14 指那个目录，TC-15 指那份文件 |
| DATA-7 | `eval-clean-interpreter.yaml` 里 `environment.setup_steps` 那一条建出来的那个解释器 | 配在批次那一层，而这一批只有一条用例，批次级等于用例级。复位按设计稿：跑完把 `evals/token-counter-round4/.clean-venv/` 整个删掉，不逐个卸包——那个目录在 `.gitignore` 里，不进版本库。常规批里不出现这一条 |
| ENV-1 | `environment.type` 取 `none`——命令在宿主机上跑，不起容器 | 与设计稿一致：规程在本机跑 |
| ENV-2 | 同上，两条落在同一处 | 两条指的是同一台机器：被测那边也是本机的 Claude Code，由这一份配置起的会话就在宿主机上 |
| ENV-3 | 宿主机的 CPython：常规批直接用，干净解释器批由 `setup_steps` 里的 `python -m venv` 照它现建一个空的 | 版本与位数由宿主机决定，配置里不写死；跑之前确认一次宿主机的 CPython 版本不低于 3.9、是 64 位 |
| ENV-4 | 两份批次配置里的 `skills[].path` 指到 `../plugin/skills/token-counter` | 不写 `include`，整个技能目录都装进工作区的 `.claude/skills/token-counter/`，词表与 `wheels/` 那两份跟着进去 |
| ENV-5 | `eval-clean-interpreter.yaml` 里 `environment.setup_steps` 建出来的那个空解释器 | 里面不装引擎，靠被测那边首次运行时自己装。建它的那一步带 `--clear`，重跑时先把上一回装进去的引擎清掉 |
| ENV-6 | 常规批直接用宿主机上已经装好引擎的那个解释器 | 配置里不写安装步骤；`setup_steps` 里只放一条确认（`python -c "import tokenizers"`），引擎不在位时那一条命令退非零，整条用例当场报错，免得后面十几条一个个报出看不懂的失败 |
| ENV-7 | **框架的默认行为，配置里一个字都不写** | skill-up 每条用例各起一个空的临时目录当工作区、跑完删掉，正是这一条要的。夹具在 `setup_steps` 之后铺，铺的也是各条用例自己的那个工作区 |

**编号在盘上怎么留痕，两处定死。**

- **用例配置的文件名**照 `scripts/issue_ids.py --case-dirs` 打出来的那串加 `.yaml`，一条一个文件，不重命名、不简写。
- **配置里面用注释带编号**：每条用例的输入上方、每条判据上方，写出它兑现的 `TP-`／`TC-`／`TCOV-`／`DATA-`／`ENV-` 号。连字符在注释里照写；落到代码里写不成连字符时换成下划线，不补零，一条一个号、不写成范围。

**这一节只管把话写死，落成是另一步做的**——这一份里不贴配置。配置由落成那一步照这张对账表写进盘里。

## 二、方案：skill-up

### 2.1 说明

**1. 跑几次**

两批，两份批次配置，分两次跑：

- **常规批**跑 TP-1、TP-2、TP-3 三条规程、共 15 条用例，落在 `eval.yaml`。
- **干净解释器批**跑 TP-4 那一条规程、就 TC-16 一条用例，落在 `eval-clean-interpreter.yaml`。

分两批不是按判据分的，是按解释器的状态分的。「装不装引擎」只能整批配一次，配在 `environment` 那一层；一批里每条用例开跑前都会走一遍那几步。两条相反的初始状态——一条要「里面已经有引擎」，另一条要「里面什么都没有」——合不进同一批。

**2. 工作区怎么来**

每条用例开跑前，skill-up 自己起一个空的临时目录当工作区，跑完删掉，配置里不用写——ENV-7 要的就是这个，它是框架的默认行为。

夹具分两样铺法：

- 能用文字直接写出来的（DATA-3 那份 .md、DATA-4 那段样本）走用例配置里的 `context.files`，写进工作区根目录。
- 要按字节摆的、要建出目录的（DATA-6 那份 GBK 文件与那个目录）走 `context.repo_fixture`，指到 `fixtures/samples/`，它整个铺进工作区根。

两样都由框架在会话起来之前铺好，跑完随工作区一起删掉，原始夹具不动。

**3. 字段的作用域**

`environment`（连着它底下的 `setup_steps`）、`skills`、`judge`、`cases.parallelism` 这几个字段**只认批次那一层**。配到一条用例那一层不会报错，是默默丢掉的——`validate` 照样报 valid。所以「只有某一条用例用得上」的准备动作一旦配在那一层，这一批里每条用例都会跟着做一遍。

这一批里要留神的是 DATA-7 那个干净解释器：它靠 `environment.setup_steps` 建，只能整批配一次。干净解释器批里只有一条用例，批次级正好等于用例级，这条代价不产生；常规批根本不配那一步，也不产生。

**4. 这一批能不能并发**

**常规批能并发。**15 条用例各起一个工作区，夹具各铺各的；两批之间共用的只有宿主机上那台已经装好引擎的解释器，而这一批里没有一条用例会去动它——都是读它、调它，不装也不卸。判据落在各条用例自己的回话与执行过程上，互相看不到对方。`cases.parallelism` 取一个大于 1 的值（4 上下），上限由本机与网关那边定，跑不顺就往下调。

**干净解释器批只有一条用例，没有并发这回事。**

**5. 判据分几层、怎么落到这套方案的判官上**

- **机械层**：`cases.defaults.expect` 里只卡 `exit_code: 0`——被测那边跑完这一轮不退非零。这一批的判据不落在某个固定的字串上（没有一句话能判出「走的是哪条加载路径」），所以机械层只卡这一条，能在花判官的钱之前先把明显不对的挡掉。
- **质量层**：全部交给 `judge.type: agent_judge`。每条用例的 `judge.criteria` 逐条照它「预期结果」那一栏写；判据落在「要读执行过程」那一层的那些条（TC-1、TC-4、TC-5、TC-12、TC-13、TC-14、TC-15、TC-16），靠 `judge.context` 的默认那一档——`final_message` 内联，`transcript` 与 `workspace_diff` 以文件引用给出，判官读得到那一轮里到底跑了哪几步。`judge.model` 必填，两份配置都写在批次那一层，用例那一层只写 `criteria`。

**6. 判据的通过口径**

一律取**「列出的判据全成立才算过」**——`judge.pass_threshold` 写 `1.0`。不写时的默认值是按条计分、过线比例另算，那不适合这一批：这几条用例的「预期结果」栏写的都是「这几样都要做到」。TC-1 要是数对了、可它还顺手跑了一遍安装，那不算过；TC-9 要是说明了不覆盖、可又给了一个近似数，也不算过。

**7. 消息与上下文怎么渲染**

全是单轮：用户那一侧只有 `input.prompt` 一段，按测试用例规格说明「输入」栏那句话原样写，样本（DATA-1 至 DATA-5）按编号接在后面。

技能装进工作区的 `.claude/skills/token-counter/`，**走的是本地技能那条道，不是插件那条**——按技能名唤起，带插件前缀的唤起名用不了。这一批的消息都是按技能名唤起，与设计稿一致。

**8. 跑不了原样的那几条**

一条一条对：

- **ENV-1、ENV-2（规程与被测那侧都在本机）**：与设计稿一致，没有出入——`type: none` 就是在宿主机上跑，被测那边的会话也在同一台机器上。
- **ENV-5、ENV-7、DATA-7（干净解释器那一套）**：**有一处出入**——`environment.setup_steps` 是批次级的，一批里每条用例开跑前都会走一遍，设计稿要的是「只有 TC-16 那一条落在没装引擎的状态上」。这一批只装了一条用例，批次级正好等于用例级，代价不产生；将来要是把别的用例并进这一批，它们开跑前也会撞上一个被 `--clear` 重建过的空解释器。
- **ENV-6（常规批的解释器里已经有引擎）**：与设计稿一致，没有出入——常规批不写任何安装步骤，`setup_steps` 里只放一条确认引擎在位的检查。
- **判据落在「要读执行过程」那一层的八条**：与设计稿一致，没有出入——`judge.context` 默认那一档就把 `transcript` 给了判官，判「有没有真去跑脚本、跑的是哪条道」判得了。
- **规程的「停止与结束」里那几条收尾动作**（确认技能目录里的文件一个字节没变、把走不通的路径清掉）：**这一批不靠工作区差集判**，交给人照着规程那一栏看。原因是这一套方案在工作区不是 git 仓库时，会把差集静默省掉——不报错，报告里那一项空着，只在清单里留一行 `workspace_diff: omit`。设计稿里本来也没把这些动作写成用例判据，所以不算折扣。
- **钩子**：**这一批没有一条判据要求靠钩子触发**，与设计稿一致。skill-up 起被测那边时把钩子一律关掉，这是这套方案的固定行为，不是这一批的折扣。
- **多轮**：这一批全是单轮，不受「`input.turns` 只收 `user` 角色」这条限制，与设计稿一致。
- **ENV-4（词表与 wheels 随技能分发）**：与设计稿一致。装技能时会无条件跳过 `evals/` 子树，而被测技能是 `plugin/skills/token-counter`，它底下本来就没有 `evals/`，不受影响。**但有一条要记下**：工作区里装的那一份是 `.claude/skills/token-counter/`，机器上插件缓存里还装着同名技能的全局一份，两份都读得到；两遍跑下来被测那边实际读的是**全局那一份**（执行过程里出现的是 `plugins/cache/…/skills/token-counter/` 下的路径），不是工作区那一份。两份此刻出自同一份仓库的同一版、内容一模一样，结论照样成立；将来两处分叉时，这一批量的就是全局那一份——读结论前先核一遍两边是不是同一版。
- **相对路径的基准**：**有一处出入**——技能与评测材料不在一棵树里，skill-up 找不到技能根时会退一步，把基准落到配置文件的上一层，并打一条 `SKILL.md not found within 10 levels above …; falling back to …` 的警告。落成时按实际退让到的那一层（`evals/`）算，所以 `skills[].path` 写 `../plugin/skills/token-counter`。那行警告是正常产物，不是错。
- **报告末尾那行是三档**：`passed / failed / errors`。**ERROR 不是「被测那边没过」**，是被判官那一次意外拖住、整条用例没拿到结论（判官偶尔把结果写成代码围栏里的 JSON，或者干脆回一段散文，skill-up 会重试一次，赶不上用例超时那一条就报 ERROR）。读结论时三档分开看。

**9. 这一块里不贴配置。**配置长什么样，由落成那一步照上面那张对账表写进盘里。

### 2.2 怎么跑、报告落在哪

两批各取一个当场的时间戳目录，各自落进 `runs/` 底下。跑完一批再取下一批的，别两批共用一个。

```text
$ts = Get-Date -Format "yyyy-MM-dd-HHmm"    # bash 上是 ts=$(date +%Y-%m-%d-%H%M)

skill-up run C:/Study/shared-skills/evals/token-counter-round4/eval.yaml --output-dir "C:/Study/shared-skills/evals/token-counter-round4/runs/$ts" --iteration 2

skill-up run C:/Study/shared-skills/evals/token-counter-round4/eval-clean-interpreter.yaml --output-dir "C:/Study/shared-skills/evals/token-counter-round4/runs/<另取的一个时间戳>" --iteration 2
```

落成之后、正式跑之前，先过一遍这两条：

```text
skill-up validate C:/Study/shared-skills/evals/token-counter-round4/eval.yaml
skill-up list-cases C:/Study/shared-skills/evals/token-counter-round4/eval.yaml
```

`validate` 报的那句 `✓ eval.yaml is valid (loaded 15 case(s))` 里的条数应当是 15（干净解释器批那份是 1），对不上说明 `cases.files` 里有路径写错了。`list-cases` 打出来的顺序就是执行顺序，与规程的「有序执行测试用例」栏逐条对一遍。

**报告落在哪。**常规批落进 `runs/<这一批的时间戳>/`，干净解释器批落进另一个时间戳目录，两下盖不着。底下 `iteration-1/`、`iteration-2/` 是 skill-up 自己追加的——这一批里跑的第几回就是几。**哪一批是哪一个看目录里的用例目录名**：常规批那 15 个目录名以 `tp01`、`tp02`、`tp03` 打头，干净解释器批只有一个 `tp04-01`。下一批再跑另取时间戳，落进新目录，前几批的报告都留着。

**报告出哪两种格式。**两份配置的 `report.formats` 都列着 `json` 与 `html`。`json` 给机器读——每条判据过没过、每一步花了多久都在 `result.json` 里；`html` 给人看，一轮跑完直接翻 `report.html`。这一栏不列 `html` 就不出 HTML，事后要补得拿 `skill-up report` 从 `result.json` 另生成一份，补出来的与当场跑的混在一个目录里，分不清哪份是哪份。

**同一批跑两遍。**上面两条命令里的 `--iteration 2` 就是干这个的：两遍落进同一个时间戳目录下的 `iteration-1/` 与 `iteration-2/`，不必另起目录。跑第二遍不为核对结论，为的是看判据稳不稳——一轮过一轮不过的用例，终端末尾会标出来，毛病多半出在判据卡了那种可有可无、被测那边有时说有时不说的附带动作上。**两遍不一致的用例照实记下来**，连它是哪一条判据在来回摆一起记。

**跑过之后的结论记在哪。**哪几条没过、为什么、下一轮改什么，记在这一批报告里的 `result.json` 与那份 HTML 里，不另起一份，也不写回产出那六份文档。要留长期结论，就把要紧的几条抄进这一份的这一节。三档里 ERROR 的那几条另说一句「是被判官那一次拖住，还是被测那边真有问题」。

**不进 git。**项目 `.gitignore` 里那条 `evals/*/runs/` 把整个 `runs/` 盖住了；干净解释器批建的那个 `.clean-venv/` 由同一条规则旁边的 `evals/*/.clean-venv/` 盖住。两样都不进版本库。
