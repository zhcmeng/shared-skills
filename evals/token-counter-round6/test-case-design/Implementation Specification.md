# 实施方案规格说明

这一份把同目录那六份通用设计稿落成能跑的东西。那六份说的是「要什么」——建哪些模型、要覆盖哪些项、跑哪些用例与规程；这一份说的是「用哪个、怎么摆」——这批用例交给哪套测评方案跑、每条编号落在盘上的哪个文件哪一段。**两边对同一件事的说法不一致时，以这一份为准**；不一致的地方写在对账表的说明栏与「跑不了原样的那几条」里。

方案按节分。这一份现在只有 skill-up 一个方案；将来要拿同一套通用稿比第二个方案，就在这一份里另起一节，六份一个字不用动。

## 一、通用稿的编号落到哪

下面这张表把六份里定义过的每一条编号对到本方案里的落点。落点写的是从**评测材料根**（`evals/token-counter-round6/`）算起的相对路径——产出目录是它底下的 `test-case-design/`，落成的东西与产出目录并列，不住在它里面。只有脚本批那一处落在评测材料之外（仓库根下的 `tests/token-counter/`），那一处单独注明。

| 通用稿的编号 | 本方案里落在哪 | 说明 |
|:---|:---|:---|
| TM-1、TM-3 | 两处：`tests/token-counter/test_count_tokens_round6.py` 的文件头分组说明，以及 `cases/` 与 `eval-clean-interpreter.yaml` 引用到的那几条用例配置里输入与判据上方的注释 | 模型是设计那一层的产物，这一套方案里没有对应的配置项，号靠覆盖项与用例的注释在盘上留痕。这两个模型导出的覆盖项两批都落到了：TM-1 的 TCOV-16、TCOV-17、TCOV-18、TCOV-19、TCOV-20 落评测批，其余落脚本批；TM-3 的 TCOV-30 两批各落一处，其余落脚本批 |
| TM-2 | `tests/token-counter/test_count_tokens_round6.py` 的文件头分组说明 | 这个模型导出的覆盖项整批在脚本批：三个有序集上的边界要在命令行那一层看，评测批一条也不落 |
| TM-4 | `cases/` 与 `eval-clean-interpreter.yaml` 引用到的那几条用例配置的注释 | 这个模型导出的是主场景与七条备选场景，整批落评测批——判据要读一轮模型的行为 |
| TCOV-1、TCOV-2、TCOV-3、TCOV-4、TCOV-5、TCOV-6、TCOV-7、TCOV-8、TCOV-9、TCOV-10、TCOV-11、TCOV-12、TCOV-13、TCOV-14、TCOV-15、TCOV-21、TCOV-22、TCOV-23、TCOV-25、TCOV-27、TCOV-28、TCOV-29、TCOV-31、TCOV-32 | `tests/token-counter/test_count_tokens_round6.py` 里覆盖它的那一条测试上方的注释 | 不在这套方案里：这一批判据落在命令、标准输出、退出码与盘上的文件上，按测试规程规格说明的「各批落到哪」归可跑测试那一批 |
| TCOV-16、TCOV-17、TCOV-18、TCOV-19、TCOV-20、TCOV-33、TCOV-34、TCOV-35、TCOV-36、TCOV-37、TCOV-38、TCOV-39、TCOV-40 | 覆盖它的那一条用例配置里，输入与判据上方那几行注释 | 一条覆盖项出现在覆盖它的每一条用例的配置里，对应关系照测试用例规格说明的对应表 |
| TCOV-30 | 两处：`tests/token-counter/test_count_tokens_round6.py` 里 TC-18 那一条测试上方的注释，以及 `cases/tp07-01-TC-27-first_run_installs_then_counts.yaml` 里判据上方的注释 | 这一条两批各落一处：脚本批看标准错误里那两句提示与退出码，评测批看技能那一轮里到底装没装 |
| TCOV-24、TCOV-26 | 盘上不出现 | 设计稿里判为不可行、已从分母里剔除（UTF-8 里造不出占 0 个字节与占 5 个字节的字符），落不成任何一条用例，落成时也不补一个空壳顶上 |
| TC-1、TC-2、TC-3、TC-4、TC-5、TC-6、TC-7、TC-8、TC-9、TC-10、TC-11、TC-12、TC-13、TC-14、TC-15、TC-16、TC-17、TC-18、TC-19、TC-20 | `tests/token-counter/test_count_tokens_round6.py`，一条用例一个测试函数 | 文件名与六份的「各批落到哪」写的一致，落成时不另改。那一条链上早前一轮的 `test_count_tokens.py` 与本轮同号不同义，两者不能并进一个文件 |
| TC-21、TC-22、TC-23、TC-24、TC-25、TC-26、TC-28 | `cases/` 下 7 个用例配置，一条用例一个文件 | 文件名照 `scripts/issue_ids.py --case-dirs` 打出来的那串加 `.yaml`：`tp05-01-TC-21-counting_request_main_scenario`、`tp05-02-TC-22-naming_other_model`、`tp05-03-TC-23-asks_api_cost`、`tp05-04-TC-24-tokens_only_request`、`tp06-01-TC-25-full_dialogue_assembled_first`、`tp06-02-TC-26-special_token_passed_through`、`tp07-02-TC-28-dead_end_route_reported`。执行位次就在文件名里（`tp05-01` 那一段），字母序等于执行顺序，不另外排 |
| TC-27 | `cases/tp07-01-TC-27-first_run_installs_then_counts.yaml`，由另一份配置 `eval-clean-interpreter.yaml` 收它 | **落点与六份写的不一样**：规程那一栏把它与 TC-28 排在同一条规程、同一批里，落成时它单拆一份配置。理由是「引擎在不在位」只能整批配一次，与常规批合在一份配置里，这一批七条用例每条都要先建一个没人用的空解释器 |
| TP-5、TP-6 | `eval.yaml` 的 `cases.files` 那一段 | 两条规程共 6 条用例，按规程内位次连排列在同一份配置里 |
| TP-7 | 两处：`eval.yaml`（TC-28）与 `eval-clean-interpreter.yaml`（TC-27） | **落点与六份写的不一样**，理由同上一条；两条用例互不依赖，分两次跑不影响各自的结论 |
| TP-1、TP-2、TP-3、TP-4 | `tests/token-counter/test_count_tokens_round6.py`，一条规程一组测试 | 不在这套方案里：这四条规程跑的是命令行那一层，判据落在命令、退出码与盘上的文件上 |
| DATA-1 | 三处：`tests/token-counter/test_count_tokens_round6.py` 里那六段字面量；`cases/tp05-01-TC-21-counting_request_main_scenario.yaml`、`cases/tp05-03-TC-23-asks_api_cost.yaml`、`cases/tp05-04-TC-24-tokens_only_request.yaml`、`cases/tp07-01-TC-27-first_run_installs_then_counts.yaml` 四条配置的 `input.prompt` 正文里（都取第 1 段） | 六段都直接接在请求或命令行参数上，没有做成夹具文件。第 3 段与第 6 段只有脚本批取用，评测批只取第 1 段 |
| DATA-2 | `tests/token-counter/test_count_tokens_round6.py` 里 TC-8 那一条测试的空串参数 | 不在这套方案里：空文本只在命令行那一层用得上 |
| DATA-3 | 两处：`cases/tp06-02-TC-26-special_token_passed_through.yaml` 的 `input.prompt` 正文，以及脚本批 TC-7 那一条测试的输入 | 那个特殊 token 的字面形照原样用，不转义、不拆开、不剥离；两处都照测试数据需求的正文写 |
| DATA-4 | `tests/token-counter/test_count_tokens_round6.py` 里 TC-2 那一条测试摆出的 `sample.md` | 不在这套方案里。正文照测试数据需求的表下正文写，字节按不带字节顺序标记的 UTF-8、末尾一个换行摆——整份 65 个字节。判据（13 个 token、25 个字符）就落在这份字节上，多一个或少一个数就变了 |
| DATA-5、DATA-7、DATA-8、DATA-10 | `tests/token-counter/test_count_tokens_round6.py` 里用到它的那一条测试的输入 | 不在这套方案里：空文件、带完整字节顺序标记的那份、标记后多一个字节的那份、按 GBK 写的那份，都只在命令行那一层用得上 |
| DATA-6 | `tests/token-counter/test_count_tokens_round6.py` 里 TC-3 那一条测试从标准输入喂进去的那两行 | 不在这套方案里：管道那条道在评测批里没有用例 |
| DATA-9 | `tests/token-counter/test_count_tokens_round6.py` 里 TC-14、TC-15 两条测试摆出的两样（一个不存在的名字、一个现建的目录） | 不在这套方案里。评测批 TC-28 只用它「路径不存在」那一半——那半不用摆东西，工作区里本来就没有那个文件 |
| DATA-11 | `cases/tp06-01-TC-25-full_dialogue_assembled_first.yaml` 的 `input.prompt` | 要当成一次完整对话请求来估的那段用户消息，原样写进请求 |
| DATA-12 | `tests/token-counter/test_count_tokens_round6.py` 里 TC-19、TC-20 两条测试现搭的技能副本 | 不在这套方案里。跑之前把技能目录复制到临时目录，把那份装不上的包写进副本的 `wheels/` 下，跑完连副本一起删 |
| ENV-1、ENV-2 | `eval.yaml` 与 `eval-clean-interpreter.yaml` 两份配置的 `environment.type` 取 `none` | 与设计稿一致：规程与本机那侧都在宿主机上跑，不起容器。脚本批那一份测试代码也在宿主机上直接跑，不另起环境 |
| ENV-3 | 两份配置的 `environment.setup_steps` 里那一条确认宿主机 CPython 的检查 | 版本不低于 3.9、且是 64 位；版本与位数由宿主机决定，配置里不写死。不满足时那一条命令退非零，整条用例当场报错，免得后面几条一个个报出看不懂的失败 |
| ENV-4 | `skills[].path` 指到 `../plugin/skills/token-counter`（两份配置都写） | 不写 `include`，整个技能目录装进工作区，官方词表与 `wheels/` 那两份跟着进去。脚本批那一份测试代码直接读仓库里那份技能目录，不经工作区 |
| ENV-5 | `eval.yaml` 的 `environment.setup_steps` 里那一条确认引擎已在位的检查 | 这一批不装也不卸引擎：不在位时那一条命令退非零，整条用例当场报错。`eval-clean-interpreter.yaml` 里**不写这一条**——那一批的前提正相反 |
| ENV-6 | `eval-clean-interpreter.yaml` 的 `environment.setup_steps` 里那一条现建空解释器的步骤 | 建在 `evals/token-counter-round6/.clean-venv/` 下，`--clear` 保证每次开跑前它都是空的；跑完整个目录删掉，不逐个卸包。那一条用例的消息里把这个解释器的绝对路径原样给被测那边——那是前置条件，不是叫它去装什么。项目 `.gitignore` 里那条 `evals/*/.clean-venv/` 已经盖住它 |
| ENV-7 | `tests/token-counter/test_count_tokens_round6.py` 里 TC-19、TC-20 两条测试现搭的两份副本 | 不在这套方案里。一份的 `wheels/` 下只留 DATA-12 那份装不上的包，另一份把 `wheels/` 清空；两份都放在系统临时目录下，跑完整个删掉，技能本体一个字节不动 |
| ENV-8 | **框架的默认行为，配置里一个字都不写** | 每条用例各起一个空的临时目录当工作区、跑完删掉，正是这一条要的。脚本批那边由测试代码自己现建、自己清 |
| ENV-9 | 上面 ENV-4 那一处 `skills` 落点的后半截 | 技能装到工作区的 `.claude/skills/token-counter/` 下，走的是本地技能那条道，按技能名唤起，带插件前缀的唤起名用不了 |
| ENV-10 | 不写进配置 | 脚本批 TC-19、TC-20 两条测试跑之前，确认宿主机连着包索引、钉住的版本装得上；不满足时那两条跑不了，其余各条不受影响。评测批不碰联网那条道 |

**编号在盘上怎么留痕，两处定死。**

- **用例配置的文件名**照 `scripts/issue_ids.py --case-dirs` 打出来的那串加 `.yaml`，一条一个文件，不重命名、不简写。
- **配置与测试代码里用注释带编号**：每条用例的输入上方、每条判据上方，写出它兑现的 `TP-`／`TC-`／`TCOV-`／`DATA-`／`ENV-` 号；脚本批那一份文件头写一组分组说明，每个测试函数上方写它兑现的那些号。连字符在注释里照写，写不成时换成下划线（`TC-21` 写成 `TC_21`），照抄编号，不补零、一条一个号、不写成范围。

**这一节只管把话写死，落成是另一步做的**——这一份里不贴配置。配置由落成那一步照这张对账表写进盘里。

## 二、方案：skill-up

### 2.1 说明

**1. 跑几次**

两次，都是这一份里的活：

- **运行一（常规批）**：`eval.yaml` 收 TP-5、TP-6 两条规程与 TP-7 的 TC-28，共 7 条用例（TC-21 至 TC-26、TC-28）。
- **运行二（干净解释器批）**：`eval-clean-interpreter.yaml` 收 TP-7 的 TC-27，一条用例。

TP-1 至 TP-4 那四条规程不在这两份配置里——它们的判据落在命令、退出码与盘上的文件上，归可跑测试那一批，落进 `tests/token-counter/test_count_tokens_round6.py`。分批准则见测试规程规格说明的「各批落到哪」：按判据落在哪一层分，脚本批那一批里一条判据都不读模型行为。

**为什么把 TP-7 拆成两次跑**：「引擎在不在位」只能整批配一次，配在 `environment` 那一层，一批里每条用例开跑前都走一遍。TC-27 要跑在一个没装引擎的解释器上，与常规批合在一份配置里，运行一那 7 条每条都要先建一个没人用的空解释器。分出来只建一次，代价是多敲一条命令行。两条用例互不依赖，先后不影响结论；要照规程的次序（TC-27 在 TC-28 之前），先把运行二跑掉再跑运行一。

**2. 工作区怎么来**

每条用例开跑前，skill-up 自己起一个空的临时目录当工作区，跑完删掉，配置里不写——ENV-8 要的就是这个，它是框架的默认行为。

这两批**没有一条用例要往工作区里铺夹具文件**：文本都接在 `input.prompt` 里。TC-28 那句指的是工作区里一个不存在的文件，什么都不用摆。

技能由 `skills[].path` 装进工作区的 `.claude/skills/token-counter/`，官方词表 `tokenizer.json` 与 `wheels/` 那两份跟着进去（ENV-4、ENV-9）。装技能时会无条件跳过 `evals/` 子树，而被测技能是 `plugin/skills/token-counter`，它底下本来就没有 `evals/`，不受影响。

**3. 字段的作用域**

`environment`（连同它底下的 `setup_steps`）、`skills`、`judge`、`cases.parallelism` 这几个字段**只认批次那一层**。配到一条用例那一层不会报错，是默默丢掉的——`validate` 照样报 valid。所以「只有某一条用例用得上」的准备动作一旦配在那一层，这一批里每条用例都会跟着做一遍。

运行一里要留神的是 `setup_steps` 里那两条确认（ENV-3、ENV-5）：它们只能整批配一次，7 条用例开跑前各走一遍。这一批 7 条的前提本来就一样——宿主机 CPython 合要求、引擎已在位——所以这处代价不产生。

运行二里那一步建空解释器（ENV-6）同理，只是那一批只有一条用例，批次级正好等于用例级。

**4. 这一批能不能并发**

- **运行一：能。** 7 条用例各起一个工作区，互相看不到对方；两两之间没有共用一处写死路径的地方，也没有哪一条会去改盘上的共用东西。共用的只有宿主机上那台已经装好引擎的解释器，而这一批里没有一条用例去动它——都是调它，不装也不卸。`cases.parallelism` 取一个大于 1 的值（4 上下），上限由本机与网关那边定，跑不顺就往下调。
- **运行二：只有一条用例，没有并发这回事**，`cases.parallelism` 写 1。

**5. 判据分几层、怎么落到这套方案的判官上**

- **机械层**：两份配置的 `cases.defaults.expect` 里都只卡 `exit_code: 0`——被测那边跑完这一轮不退非零。这两批没有一条判据落在能钉死的字串上：五条（TC-21、TC-22、TC-25、TC-26、TC-27）要看执行过程；另外三条（TC-23、TC-24、TC-28）判的是「说了什么、没说什么」，一个关键词管不住——TC-23 里的 8 与 TC-24 里的 8 混在散文里到处都是，拿它当门挡不住明显不对的，反倒容易把话说全了的判下去。所以机械层只挡「这一轮根本没跑完」，其余全交判官。
- **质量层**：8 条全交给 `judge.type: agent_judge`。每条用例的 `judge.criteria` 逐条照它「预期结果」那一栏写；`judge.model` 必填，配在批次那一层，用例那一层只写 `criteria` 与 `pass_threshold`。判据落在「要读执行过程」那五条（TC-21、TC-22、TC-25、TC-26、TC-27），靠 `judge.context` 的默认那一档——`final_message` 内联，`transcript` 与 `workspace_diff` 以文件引用给出，判官读得到那一轮里到底跑了哪几步、把什么交给了脚本、装的是哪一份引擎。

**6. 判据的通过口径**

一律取**「列出的判据全成立才算过」**——每条用例那一层都写 `judge.pass_threshold: 1.0`。不写时的默认是按条计分、过线比例另算，那不适合这两批：这 8 条用例的「预期结果」栏写的都是「这几样都要做到」。TC-23 要是报回了数、却没点明离线算不出缓存命中，那不算过；TC-26 要是数报对了、可那个字面形在交过去之前被转义了，也不算过。

**7. 消息与上下文怎么渲染**

全是单轮：用户那一侧只有 `input.prompt` 一段，按测试用例规格说明「输入」栏那句话原样写，要数的样本（DATA-1 第 1 段、DATA-3、DATA-11）按编号接在请求后面。技能按名唤起——它装在工作区的 `.claude/skills/token-counter/` 下，走的是本地技能那条道，不是插件那条，带插件前缀的唤起名用不了。

TC-27 那一条多一样东西：那个干净解释器的绝对路径要写在消息里。那个解释器没有别的办法指认——它由运行二那份配置的 `environment.setup_steps` 现建出来，路径写死在配置里；消息里把这个路径原样给被测那边，这是交代前置条件（在哪台解释器上跑），不是叫它去装什么——装不装、装哪一份，仍由它自己判。

**8. 跑不了原样的那几条**

一条一条对：

- **ENV-1、ENV-2（规程与被测那侧都在本机）**：与设计稿一致，没有出入——`type: none` 就是在宿主机上跑，被测那边的会话也在同一台机器上。
- **ENV-3、ENV-4、ENV-9（宿主机的 CPython、随技能分发的两份东西、技能装进工作区的位置）**：与设计稿一致，没有出入——整个技能目录装进工作区，官方词表与 `wheels/` 跟着进去，按技能名唤起。
- **ENV-8（每条用例各起一个空工作区）**：与设计稿一致——这是框架的默认行为，配置里一个字都不写。
- **ENV-5 那条「引擎已在位」的确认在运行二里不成立**，这是有意为之：运行二测的正是「引擎不在位时会怎样」。那一批的判据落在执行过程上，判官读 `transcript` 判得了它装的是哪一份。
- **判据落在「要读执行过程」那五条（TC-21、TC-22、TC-25、TC-26、TC-27）**：与设计稿一致，没有出入——`judge.context` 默认那一档就把 `transcript` 给了判官，「有没有真把计数脚本调起来、交给它的是不是原样的文本、装的是不是随技能打包的那一份」判得了。
- **规程「停止与结束」里那几条收尾动作**（确认技能目录里的文件一个字节没变、把工作区删掉）：**这一批不靠工作区差集判**，交给人照着规程那一栏看。这一套方案在工作区不是 git 仓库时会把差集静默省掉——不报错，报告里那一项空着，只在清单里留一行 `workspace_diff: omit`。设计稿本来也没把这些收尾动作写成用例判据，所以不算折扣。
- **钩子**：这一批没有一条判据要求靠钩子触发，与设计稿一致。skill-up 起被测那边时把钩子一律关掉，这是这套方案的固定行为，不是这一批的折扣。
- **多轮**：这两批 8 条全是单轮，不受「`input.turns` 只收 `user` 角色」这条限制，与设计稿一致。
- **相对路径的基准**：**有一处出入**——技能与评测材料不在一棵树里，skill-up 找不到技能根时会退一步，把基准落到配置文件的上一层，并打一条 `SKILL.md not found within 10 levels above …; falling back to …` 的警告。落成时按实际退让到的那一层算，所以 `skills[].path` 写 `../plugin/skills/token-counter`。那行警告是正常产物，不是错。
- **TP-7 拆成两次跑**：**有一处出入**——六份把 TC-27 与 TC-28 排在同一条规程、同一批里，这一份把它拆成运行二与运行一，理由写在上面第 1 小节。这一处只动落点与批次，用例、覆盖项、规程的次序与判据一条都没改。
- **报告末尾那行是三档**：`passed / failed / errors`。**ERROR 不是「被测那边没过」**，是被判官那一次意外拖住、整条用例没拿到结论（判官偶尔把结果写成代码围栏里的 JSON，或者回一段散文，skill-up 会重试一次，赶不上用例超时就报 ERROR），重跑一遍通常就有结论。读结论时三档分开看。
- **工作区里那一份技能，与插件缓存里那份全局的同名技能**：**待确认**——早前几轮跑下来记着被测那边实际读的可能是插件缓存里那份全局的，不是工作区里那份。两份此刻内容相同，结论照样成立；这一轮跑第一遍时核一次两边是不是同一版，两处分叉时这两批量的是全局那一份，而它一样带着官方词表与 `wheels/`。

**9. 这一块里不贴配置。** 配置长什么样、每个字段怎么写，由落成那一步照上面那张对账表与 `/skill-upper` 技能下那几份参考文档写进盘里；这一份只写落点、约定与折扣。

### 2.2 怎么跑、报告落在哪

两次跑测各取一个当场的时间戳目录，跑完一次再取下一次的，**两次不共用一个目录**（`--iteration N` 从 `iteration-1` 起排，两份配置落进同一个目录会互相盖）。先取的是运行二那次，照上面说的次序。

```text
$ts = Get-Date -Format "yyyy-MM-dd-HHmm"    # bash 上是 ts=$(date +%Y-%m-%d-%H%M)

skill-up run C:/Study/shared-skills/evals/token-counter-round6/eval-clean-interpreter.yaml --output-dir "C:/Study/shared-skills/evals/token-counter-round6/runs/$ts" --iteration 2
skill-up run C:/Study/shared-skills/evals/token-counter-round6/eval.yaml --output-dir "C:/Study/shared-skills/evals/token-counter-round6/runs/<另取的一个时间戳>" --iteration 2
```

落成之后、正式跑之前先过一遍这两条：

```text
skill-up validate C:/Study/shared-skills/evals/token-counter-round6/eval.yaml
skill-up list-cases C:/Study/shared-skills/evals/token-counter-round6/eval.yaml
```

`validate` 报的那句 `✓ eval.yaml is valid (loaded 7 case(s))` 里的条数应当是 7，对不上说明 `cases.files` 里有路径写错了；`eval-clean-interpreter.yaml` 那一份报的应当是 1。`list-cases` 打出来的顺序就是执行顺序，与各条规程的「有序执行测试用例」栏逐条对一遍。

**报告落在哪。** 两次跑测各落进 `runs/` 底下一个当场的时间戳目录，两次盖不着。底下 `iteration-1/`、`iteration-2/` 是 skill-up 自己追加的——这一次里跑的第几回就是几。**哪一次是哪一个，看目录里的用例目录名**：常规批那 7 个目录名以 `tp05`、`tp06`、`tp07` 打头，干净解释器批只有一个 `tp07-01`。下一批再跑另取一个时间戳，落进新目录，前几批的报告都留着。

**报告出哪两种格式。** 两份配置的 `report.formats` 那一栏都列 `json` 与 `html`。`json` 给机器读——每条判据过没过、每一步花了多久都在 `result.json` 里；`html` 给人看，一轮跑完直接翻 `report.html`。这一栏不列 `html` 就不出 HTML，事后要补得拿 `skill-up report` 从 `result.json` 另生成一份，补出来的与当场跑的混在一个目录里，分不清哪份是哪份。

**每一批至少跑两遍。** 上面两条命令里的 `--iteration 2` 就是干这个的：两遍落进各自时间戳目录下的 `iteration-1/` 与 `iteration-2/`，不必另起目录。跑第二遍不为核对结论，为的是看判据稳不稳——一轮过一轮不过的用例，终端末尾会标出来，毛病多半出在判据卡了那种可有可无、被测那边有时说有时不说的附带动作上。这一轮最该盯的是 TC-21 与 TC-22 那两条：它们的判据里各有一条「没有绕开脚本另找一个数顶上」「没有给出任何形式的近似值」这种否定式的要求，是最容易在这一处晃的。**两遍不一致的用例照实记下来**，连它是哪一条判据在来回摆一起记。

**跑过之后的结论记在哪。** 哪几条没过、为什么、下一轮改什么，记在两次跑测报告里的 `result.json` 与那两份 HTML 里，不另起一份，也不写回产出那几份文档。要留长期结论，就把要紧的几条抄进这一份的这一节。三档里 ERROR 的那几条另说一句「是被判官那一次拖住，还是被测那边真有问题」。

**不进 git。** 项目 `.gitignore` 里那条 `evals/*/runs/` 把整个 `runs/` 盖住了；运行二那个现建的空解释器由同一条表上的 `evals/*/.clean-venv/` 盖住。脚本批那几个现建的解释器与技能副本都在系统临时目录下，跑完就删，不进版本库。
