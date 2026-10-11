# 实施方案规格说明

这一份把同目录那六份通用设计稿落成 **skill-up** 这一套测评方案里能跑的东西。六份说的是「要什么」——模型、覆盖项、用例、规程、数据、环境；这一份说的是「用哪个、怎么摆」——这批用例交给 skill-up 怎么跑、每条编号落到盘上的哪个文件哪一段。**往下这一节说的都是 skill-up，连节里那张编号对账表也是**；将来比别的方案，在同一份里另起一节，六份那几份一个字不用动。

**配置本身不抄进来**：它由落成那一步照这一份写进盘里，抄一份到文档里就是第二份会漂移的副本，盘上那份一改，两边看着都像真的。**两边冲突时以这一份为准**：通用稿是按测试项写的、不认方案，落到具体方案上总有几处要偏，偏在哪写在方案节的「说明」里。

## 一、方案：skill-up

### 1.1 通用稿的编号落到哪

| 通用稿的编号 | 本方案里落在哪 | 说明 |
|:---|:---|:---|
| TM-1、TM-2、TM-3 | `cases/` 下那十份用例配置，连同每份文件头那一列编号 | 三个模型不单独落成文件；它们导出的覆盖项由用例配置里的判据兑现，哪几号归哪一批见测试规程规格说明的「各批落到哪」 |
| TCOV-1、TCOV-2、TCOV-3、TCOV-4、TCOV-5、TCOV-6、TCOV-7、TCOV-8、TCOV-9、TCOV-10、TCOV-11、TCOV-12、TCOV-13、TCOV-14、TCOV-15、TCOV-16、TCOV-17、TCOV-18、TCOV-19、TCOV-20、TCOV-21、TCOV-22、TCOV-23、TCOV-24、TCOV-25、TCOV-26、TCOV-27、TCOV-28、TCOV-29、TCOV-30、TCOV-31、TCOV-32、TCOV-33、TCOV-34、TCOV-35、TCOV-36、TCOV-37、TCOV-38、TCOV-39、TCOV-40、TCOV-41、TCOV-42、TCOV-43 | 同上，`cases/` 下那十份用例配置的 `judge.criteria` 里 | 一条覆盖项压成一条判据（或并进同一条判据），判据上方用注释带出它兑现的号；TCOV-20 至 TCOV-24、TCOV-36 那几条依据未规定的写成「记实际行为、不判对错」 |
| TC-1、TC-2、TC-3、TC-4、TC-5、TC-6、TC-7、TC-8、TC-9、TC-10 | 各落一处：`cases/tp01-01-TC-1-single_file_all_elements.yaml`、`cases/tp01-02-TC-2-code_and_diagrams_intact.yaml`、`cases/tp01-03-TC-3-no_frontmatter_document.yaml`、`cases/tp02-01-TC-4-directory_skips_translated.yaml`、`cases/tp02-02-TC-5-directory_all_translated.yaml`、`cases/tp02-03-TC-6-no_target_reports_error.yaml`、`cases/tp02-04-TC-7-missing_path_reports_error.yaml`、`cases/tp02-05-TC-8-skill_name_located.yaml`、`cases/tp02-06-TC-9-force_retranslate.yaml`、`cases/tp02-07-TC-10-single_file_existing_unspecified.yaml` | 一条用例一份配置，文件名照测试规程规格说明「各批落到哪」那一栏的用例目录名逐个加 `.yaml` |
| TP-1、TP-2 | `eval.yaml` 的 `cases.files` 那一段，两条规程的十条用例都列在同一份里 | 两条规程同一次跑完，不拆批（理由见测试规程规格说明的「各批落到哪」） |
| DATA-1、DATA-2、DATA-3、DATA-4、DATA-5、DATA-6 | `fixtures/repos/subject/` 下那几份样本 | 逐条见下面那张摆法表 |
| ENV-1、ENV-2 | `eval.yaml` 的 `environment.type: none` | 规程与那侧在同一台机器上跑，都是本机 |
| ENV-3 | `eval.yaml` 的 `report.formats` 与 `report.artifacts`，加上各条用例的判官上下文（不写时就是默认档）与 `context.git.init: true` | 会话记录进报告供判官读；盘上跑前跑后的差别由差集给出，产出全文在差集里 |
| ENV-4 | 框架为每条用例各新建的那一个空工作区（跑完就删） | 样本按 `context.repo_fixture` 铺进去；原始件在仓库里全程不动 |
| ENV-5 | `eval.yaml` 的 `skills` 第一项，指向 `plugin/skills/translate-docs` | 整套技能按使用者机器上装好的样子进工作区 |
| ENV-6 | `eval.yaml` 的 `skills` 第二项，指向 `translate-docs/fixtures/skills/changelog-polish` | TC-8 的目标就是它（技能名在用例配置里写死）；偏在哪见 1.2 第 8 小节 |

样本逐条摆在哪：

| 数据项 | 摆在哪 | 说明 |
|:---|:---|:---|
| DATA-1 | `fixtures/repos/subject/widget-guide.md` | 铺进工作区之后就在工作区根；正文与字节照测试数据需求 |
| DATA-2 | `fixtures/repos/subject/pipeline-diagram.md` | 同上 |
| DATA-3 | `fixtures/repos/subject/release-notes.md` | 同上 |
| DATA-4 | `fixtures/repos/subject/handbook.md` 与 `fixtures/repos/subject/handbook-中文版.md` | 一对，摆在同一个目录里 |
| DATA-5 | `fixtures/repos/subject/mixed/` 这个目录（里面四份） | 目录名照数据需求写死是 `mixed` |
| DATA-6 | `fixtures/repos/subject/translated/` 这个目录（里面四份） | 目录名是 `translated` |

编号在盘上怎么留痕：用例配置的文件名照测试规程规格说明「各批落到哪」那一栏的用例目录名逐个加 `.yaml`；配置里面，每条用例的输入上方、每条判据上方用注释带出它兑现的 `TP-`／`TC-`／`TCOV-`／`DATA-`／`ENV-` 号——一条一个号、不写成范围、数字不补零。

### 1.2 说明

**1. 跑几次**

一次。两条规程（TP-1、TP-2）的十条用例全落成评测用例，装在同一份 `eval.yaml` 里一次跑完。理由写在设计稿里：「各批落到哪」那一块说这批用例没有一条的判据落在命令、退出码与盘上文件上就能有结论，十条都要读一轮被测那侧的行为，本来就归同一处，不分批。

**2. 工作区怎么来**

每条用例开跑前，skill-up 自己在系统临时目录下新建一个空目录当工作区，跑完删掉（留着看加 `--no-delete`，工作区落在 `%TEMP%\skill-up-<随机数>`）。样本由用例配置里的 `context.repo_fixture` 指向 `fixtures/repos/subject` 铺进工作区根，**夹具的原始件在仓库里全程不动**——每条用例拿到的是自己那份副本，十条各用各的，互不串，这正是 ENV-4 说的「各备一份可写的副本」。样本铺好之后不清理、不复位：skill-up 每次跑都用新工作区，上一轮的产出不会带进下一轮，测试数据需求里那几条「跑完复位成原样」由这件事自动兑现。

`context.git.init: true` 写在十条用例上：skill-up 在会话起来之前先把当时的盘面提交成一条基线，跑完拿它与当轮比，差集里看得出多出了哪份中文版、哪份文件被动过。不开这一项，工作区不是 git 仓库，差集会被静默省掉（报告里那一项空着），靠「盘上其他文件跑完与跑前逐字节相同」的那几条判据就没有可判的东西了。

**3. 哪些字段配在批次那一层**

`skills`、`environment.setup_steps`、`cases.parallelism`、`cases.defaults` 只认批次那一层；配到一条用例那一层不会报错，是默默丢掉的。`judge` 反过来：`type`、`model`、`criteria`、`pass_threshold` 整块写在用例那一层，批次那一层不写。所以 ENV-6 那条「另装一个技能」只能配在批次那一层——那个技能十条用例每条都会装上，只有 TC-8 用它，其余九条的判据都不碰它，代价是那九条的技能清单里多一项。这一批没有要用 `setup_steps` 的地方：技能由 `skills` 那一段交出去，不需要往工作区里另外写什么。

**4. 这一批能不能并发**

能，取 `cases.parallelism: 4`。十条用例互不相扰：各起独立工作区、各铺一份夹具副本，没有哪两条共用一处写死的路径、共用一个环境或共用一份夹具——TC-4 与 TC-9 都用 `mixed` 这个目录，但各拿各的副本，一条跳过已有中文版、一条覆盖重译，互不干扰。取 4 是兼顾时间与这台机器扛得住的档；要提速在命令行上加 `--parallelism`（传得比用例数大没有额外效果，也不报错），不必改配置。

**5. 判据分几层、怎么落到这套方案的判官上**

两层。第一层是 `expect` 那几个便宜的门槛，不过就跳过判官、不花判官那份钱：十条都要求 `exit_code: 0`（被测那侧这一轮正常收场），TC-1 至 TC-4、TC-9 另加 `files_exist` 点名该出现的产出文件（那几条的产出文件名是提前定得下来的），TC-5 至 TC-8、TC-10 不加——那几条要么不该产出文件、要么产出落到哪儿跑之前定不下来。第二层是 `judge.type: agent_judge`，`model: anthropic/claude-sonnet-4-6`。判据从测试用例规格说明的「预期结果」栏逐条压出来，一条判据写一小段、上方用注释带出它兑现的号。判官拿到的材料用默认档：当轮的回复内联给出，过程记录与盘上跑前跑后的差别以文件引用给出——TC-1 与 TC-4 那两条要读执行过程的判据（派没派子代理、是不是一条消息同时派出去、产出之后做没做校验）从过程记录里读，其余判据盘上比得出来。

`report.artifacts` 取 `transcript`：不取就没有过程记录，那几条判据落空。各条用例的会话记录里，框架自己往 `.claude/skills/` 里装技能、写基线这些动作不是被测那侧干的，判据里都写明不要算到「盘上其他文件被动过」头上。

**6. 判据的通过口径**

十条都取「列出的判据全成立才算过」，`pass_threshold: 1.0`。通用稿的「预期结果」栏本来写的就是「这几样都要做到」，少一样不算过。

**依据未规定的那几处是例外**：图片的 alt 与目标地址、文档里的 HTML 注释、frontmatter 里取技术关键字值的字段（`context: fork`）、什么算「技术术语」、原文没有 frontmatter 时说明句插在哪、单文件模式遇到已有中文版——这几处依据本就没规定该怎么办，判据只要求把实际行为记下来、报给用户定口径，**不判对错，也不构成不通过的理由**。写法上照旧列进 `criteria`，措辞里写明「这一处不判对错」。

**7. 消息与上下文怎么渲染**

每条用例一条用户消息（`input.prompt`），正文照测试用例规格说明的「输入」栏，只把里面那个占位的样本路径换成本方案上算得出的路径。技能本身不进消息：`skills` 那一项把 `plugin/skills/translate-docs/` 整套装到工作区的 `.claude/skills/translate-docs/` 下，被测那侧从自己的技能清单里按描述里的触发语唤起它——十条消息里都带着「翻译」这类触发词。**带插件前缀的写法在这一套上不成立**（装进去的是本地技能那条道），要按名字唤起就只能写技能名本身。

**8. 跑不了原样的那几条**

- **输入里的路径**：设计稿的「输入」栏写的是样本副本的**绝对路径**；这一套方案上工作区是当轮现建的临时目录，跑之前定不下来，十条一律改成从工作区根算的相对路径（`widget-guide.md`、`mixed` 这样）。判据不受影响——判的是产出落在原文同目录、文件名加 `-中文版`。
- **TC-8 的目标技能名**：设计稿举例写的是 `superpowers:brainstorming`（带插件前缀）；这一套方案上带前缀的名字用不了，ENV-6 本来就写着「技能名照跑测机器上实际装着的取，落成时在用例配置里写死」。**这一处比 ENV-6 多偏一步**：这台机器上装着的技能都是中文的（拿中文文档当翻译目标，判不出「该译的译了、该留的没动」），而且装着的技能随机器变、跑测复现不了；落成时改成由夹具里那份英文 `SKILL.md`（`fixtures/skills/changelog-polish/`）装成一个技能，名字取 `changelog-polish`，写死在 TC-8 那条里。ENV-6 管的两件事照旧兑现：它是个按名字定位得到的技能，它的 `SKILL.md` 与所在目录有写权限。产出因此落在 `.claude/skills/changelog-polish/SKILL.md-中文版.md`，比通用稿里那处多一层 `.claude`；判据照旧（同目录、文件名加 `-中文版`、原文一字未动）。
- **ENV-6 那个技能是整批在场的**：`skills` 只能配在批次那一层，见第 3 小节。
- **TC-9 判「有没有真重译」**：那一对里已有中文版的那份，重译之后可能与旧的只差几处，盘上比不出来时以过程记录为凭——看得出为它单独派了子代理、写了这一份，也算达成。
- **要读执行过程的两条**（TC-1、TC-4）靠 `transcript`；取不到过程记录时那几条判据没有可判的东西，报告里会看得出。落成之前先确认这一档开着。
- **钩子不在这条链上**：这一套跑起来时钩子一律不生效，通用稿里也没有哪一条要求靠钩子触发，不算折扣。
- 其余部分与设计稿一致，没有出入：ENV-1 与 ENV-2 都是本机；ENV-3 要的三样（会话记录、盘上跑前跑后的完整内容、产出全文）在这一套上分别是 `transcript`、`context.git.init: true` 带来的差集、差集里那几份新增文件的全文；ENV-4 与 ENV-5 照第 2、第 3 小节摆。TC-6、TC-7 那两条本来就不产出文件、本来就不装额外的东西，没有折扣。

### 1.3 怎么跑、报告落在哪

一批跑测共用一个时间戳目录。先取一次当前时刻，这一批的几条命令都拿它当输出目录；**输出目录写绝对路径**——传相对路径时判官准备上下文那一步会失败、整条用例记 ERROR，拿不到结论：

```text
$ts = Get-Date -Format "yyyy-MM-dd-HHmm"    # bash 上是 ts=$(date +%Y-%m-%d-%H%M)
skill-up run "C:/Study/shared-skills/evals/translate-docs/eval.yaml" --output-dir "C:/Study/shared-skills/evals/translate-docs/runs/$ts"
```

落成之后先跑一次 `skill-up validate` 把配置读一遍，再跑上面那条。报告落在 `C:/Study/shared-skills/evals/translate-docs/runs/<这批的时间戳>/`，底下 `iteration-1/` 由 skill-up 自己追加——这一批里跑的第几回就是几。下一批另取一个时间戳，落进新目录，盖不掉这一批。

**报告出哪两种格式**：配置里 `report.formats` 那一栏列的是 `json` 与 `html`。`json` 给机器读——每条判据过没过、每一步花了多久都在 `result.json` 里；`html` 给人看，一轮跑完直接翻 `report.html`。这一栏不列 `html` 就不出 HTML，事后要补得拿 `skill-up report` 子命令从 `result.json` 另生成一份，补出来的与当场跑的混在一个目录里，分不清哪份是哪份。

**同一批默认跑一遍。**要的是确定性——一条用例要么过要么不过；「跑两遍过一遍」这种通过率说明不了被测那边怎么样，只说明这条判据还没定下来。不过的照实记下来，下一轮回来查是不是判据卡了可有可无的附带动作（被测那边有时顺带说一句、有时不说，卡上去这条用例就一轮一个样），或者夹具与输入没摆对；改完重跑一遍看改对没有，那是第二遍唯一的用处。

**跑过之后的结论记在哪**：这一批哪几条没过、为什么、下一轮改什么，记在这一批报告的 `result.json` 与 `report.html` 里，不另起一份、也不写回产出那六份文档。报告本身不进 git——仓库 `.gitignore` 里那条 `evals/*/runs/` 把整个 `runs/` 盖住了，产出目录在它旁边，照旧提交。

### 1.4 成品落点

| 成品 |
|:---|
| `eval.yaml` |
| `cases/` |
| `fixtures/` |

这一批全落成了：`cases/` 下十份 `.yaml`，一份用例一份，文件名照测试规程规格说明「各批落到哪」那一栏的用例目录名逐个加 `.yaml`；样本在 `fixtures/repos/subject/` 下（十二份文件，含 `mixed/` 与 `translated/` 两个目录样本，正文与数据需求逐字节相同）；ENV-6 那个技能在 `fixtures/skills/changelog-polish/` 下。

上面三条路径按跑检查时的当前目录算——落成对照就在 `evals/translate-docs/` 那一层下命令（成品与产出目录都在这一层下，`runs/` 也住在这儿，所以要一样一样点出来，别把这一层整个指过去）：

```text
python "C:/Study/shared-skills/plugin/skills/test-case-design/scripts/check_landing.py" "C:/Study/shared-skills/evals/translate-docs/test-case-design" eval.yaml cases fixtures
```
