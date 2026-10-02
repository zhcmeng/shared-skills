# 实施方案规格说明

这一份把前面六份通用设计稿落成能跑的东西：六份说的是「要什么」——模型、覆盖项、用例、规程、数据、环境；这一份说的是「用哪个、怎么摆」——这批用例交给哪套测评方案跑、每条编号落到盘上的哪个文件哪一段。**配置本身不抄进来**：它由落成那一步照这一份写进盘里，抄一份到文档里就是第二份会漂移的副本。**两边冲突时以这一份为准**：通用稿是按测试项写的、不认方案，落到具体方案上总有几处要偏，偏在哪写在下面每个方案的「说明」里。

方案按节分。眼下只有 skill-up 一节；将来换一套方案，在同一份里再起一节，六份通用稿一个字不用动。

## 一、通用稿的编号落到哪

落到盘上分两处：**批一（脚本批）**落成一份能直接跑的测试代码；**批二（模型批）**落成评测用例，分两个批次跑（常规那九条一批、干净机器那一条另起一批）。落点都从评测材料根 `evals/token-counter/` 算起；批一那一处例外——测试代码落在仓库根的 `tests/` 下，那条路径从仓库根算（技能仓库自己的约定，不在评测材料里）。

| 通用稿的编号 | 本方案里落在哪 | 说明 |
|:---|:---|:---|
| TM-1、TM-2、TM-3 | `tests/token-counter/test_count_tokens.py` 里，连同文件头的分组说明 | 脚本批那两条规程的用例由这三个模型导出，整批落在这一处。**这一处沿用上一轮那份的名字、整份覆盖它**：同目录那份 `test_count_tokens.py` 是上一轮落成的（它那一套的编号也从头起，与本轮对不上，两个方向都会认错），用户拍板覆盖它、只留这一份（决策依据 DEC-26）。落成之后照规矩回填测试用例规格说明的「成品落点」那一块 |
| TM-4 | `cases/` 下那十条用例配置 | 场景测试的模型只导出技能层那十条用例 |
| TCOV-1、TCOV-2、TCOV-3、TCOV-4、TCOV-5、TCOV-6、TCOV-7、TCOV-8、TCOV-9、TCOV-10、TCOV-11、TCOV-12、TCOV-13、TCOV-14、TCOV-15、TCOV-16、TCOV-17、TCOV-18、TCOV-19、TCOV-20、TCOV-21、TCOV-27、TCOV-29、TCOV-30、TCOV-32、TCOV-33、TCOV-34、TCOV-35、TCOV-38、TCOV-39、TCOV-40、TCOV-41、TCOV-43、TCOV-44、TCOV-45、TCOV-46 | `tests/token-counter/test_count_tokens.py` | 脚本批那 25 条用例覆盖的覆盖项 |
| TCOV-22、TCOV-23、TCOV-24、TCOV-25、TCOV-26、TCOV-47、TCOV-48、TCOV-49、TCOV-50、TCOV-51、TCOV-52、TCOV-53、TCOV-54 | `cases/` 下那十条用例配置 | 只有技能层用例覆盖的覆盖项 |
| TCOV-4、TCOV-6、TCOV-11、TCOV-15、TCOV-27 | 两处都有：测试代码那一份与用例配置那一批 | 这几条两批各判一遍——脚本层判一次行为、技能层再判一次整条链上的落笔 |
| TCOV-28、TCOV-31、TCOV-36、TCOV-37、TCOV-42 | 不落成 | 判为不可行、已从分母里剔除（原因在覆盖项清单的描述栏），落成时也不落它 |
| TC-1、TC-2、TC-3、TC-4、TC-5、TC-6、TC-7、TC-8、TC-9、TC-10、TC-11、TC-12、TC-13、TC-14、TC-15、TC-16、TC-17、TC-18、TC-19、TC-20、TC-21、TC-22、TC-23、TC-24、TC-25 | `tests/token-counter/test_count_tokens.py` | 批一：判据落在命令、退出码与盘上的文件上，一条一个函数 |
| TC-26、TC-27、TC-28、TC-29、TC-30、TC-31、TC-33、TC-34、TC-35 | `token-counter/cases/tp03-01-TC-26-skill_main_text_request.yaml`、`token-counter/cases/tp03-02-TC-27-skill_main_file_request.yaml`、`token-counter/cases/tp03-03-TC-28-skill_tokens_only_reply.yaml`、`token-counter/cases/tp03-04-TC-29-skill_other_model_declined.yaml`、`token-counter/cases/tp03-05-TC-30-skill_cost_caliber.yaml`、`token-counter/cases/tp03-06-TC-31-skill_full_request_assembled.yaml`、`token-counter/cases/tp03-07-TC-33-skill_special_token_kept.yaml`、`token-counter/cases/tp03-08-TC-34-skill_missing_path_reply.yaml`、`token-counter/cases/tp03-09-TC-35-skill_undecodable_file_reply.yaml` | 批二·第一轮：一条用例一份配置，文件名照「用例目录名」加 `.yaml` |
| TC-32 | `token-counter/cases/tp04-01-TC-32-skill_clean_machine.yaml` | 批二·第二轮：它要把会话里的解释器换成干净那个，单独一批跑 |
| TP-1、TP-2 | `tests/token-counter/test_count_tokens.py`（文件头把两条规程的分组写出来） | 判据落在输出上，归可跑测试这一边 |
| TP-3 | `eval.yaml`（它的 `cases.files` 列出上面那九份配置） | 技能层常规场景那一批 |
| TP-4 | `eval-clean-machine.yaml` | 干净机器那一条单独一份配置、单独一批 |
| DATA-1、DATA-3、DATA-4、DATA-5、DATA-6、DATA-7、DATA-8、DATA-9、DATA-10、DATA-11、DATA-12、DATA-13 | `tests/token-counter/test_count_tokens.py` 里就地造（字节照测试数据需求写死） | 脚本批不铺夹具，测试代码自己按编号造样本、摆在它建的临时目录里 |
| DATA-2 | 两处：批一那份测试代码里就地造；批二落 `fixtures/samples/` | TC-27、TC-28、TC-32 三条用例要靠它铺进工作区 |
| DATA-14 | `fixtures/samples/` | TC-35 用 |
| DATA-15、DATA-16、DATA-17、DATA-18、DATA-19、DATA-20、DATA-21、DATA-22、DATA-23 | 各条用例配置的 `input.prompt`（一条一个；正文照测试数据需求表下那九段抄） | 消息不再加工，原样发 |
| ENV-1、ENV-2 | `environment.type: none`——测试与评测都在跑 skill-up 这台机器上 | 默认口径（本机），不另换机器或容器 |
| ENV-3 | 批二：`skills` 那一段指向 `plugin/skills/token-counter`；批一：测试代码里那个技能目录常量 | 批二按技能形态装进工作区的 `.claude/skills/token-counter/`，按技能名唤起 |
| ENV-4 | 评测机上本机那个解释器（不进配置） | 落地时确认它能 `import tokenizers` 再开跑 |
| ENV-5 | `.clean-venv/` | 由 TP-4 那一批的 `environment.setup_steps` 建；批一那几条（TC-23 至 TC-25）由测试代码自己就地建。不进 git（项目 `.gitignore` 里 `evals/*/.clean-venv/` 那条盖着） |
| ENV-6 | 评测机联网（不进配置） | 落地时按 TC-24、TC-25 那两条的要求确认包索引取得到 0.22.2 |
| ENV-7 | `report.artifacts` 那一段取 `transcript`；各条用例的 `judge.context` 取默认的 standard | 判官拿得到当轮回复全文、执行过的命令与盘上的前后差别 |
| ENV-8 | 框架每条用例各建一个的空临时目录（批二）；批一那份测试代码自己建的临时目录 | 样本、拷贝都摆在这里，跑完就清 |

**编号在盘上怎么留痕**，落成那一步照这两条写死：

- **用例配置的文件名**照 `python scripts/issue_ids.py <产出目录> --case-dirs` 打出来的那串加 `.yaml`——上面那两行的十个名字就是照它抄的，一字不改。
- **配置里面用注释带编号**：每份用例配置的文件头按 `TP-`／`TC-`／`TM-`／`TCOV-`／`DATA-`／`ENV-` 六行列出它兑现的号（一条一个号、不写范围）；每条判据（`criteria` 那几条）上方再用注释带出它落的是哪条覆盖项。批一那份测试代码里同样办：每个测试函数上方用注释带出 `TP-`／`TC-` 号，编号照抄（代码里写不成连字符的地方换成下划线，如 `TC_26`）。

## 二、方案：skill-up

### 2.1 说明

**1. 跑几次**

脚本批不进这套配置：`tests/token-counter/test_count_tokens.py` 是一条能直接跑的命令，判据落在输出上，跑一遍就有结论。skill-up 管的是技能层那十条，分两个批次各跑一回：

- 批二·第一轮：`eval.yaml`，跑 TP-3 那九条（TC-26 至 TC-31、TC-33 至 TC-35）。
- 批二·第二轮：`eval-clean-machine.yaml`，跑 TP-4 那一条（TC-32）。它单独一批是因为它要把会话里的解释器换成没装引擎的那个，而 `environment` 那一层与 `skills`、`judge` 一样是批次级字段——混在同一批里会连累别的用例。

每一批至少跑两遍：第一条命令跑完，原样再跑一遍，第二遍自动落进 `iteration-2/`（`--iteration` 的默认行为就是接着最后一个 `iteration-N` 往后追加），两遍并排留着对。

**2. 工作区怎么来**

每条用例开跑前，框架自己在系统临时目录下新建一个空目录当工作区，跑完删掉。要用文件的那几条（TC-27、TC-28、TC-32、TC-35），`context.repo_fixture` 把 `fixtures/samples/` 铺进工作区——夹具是逐字节写、连源文件权限位一起带，原始夹具全程不动。批一那份测试代码不靠框架，自己在临时目录里按编号造样本。

**3. 字段的作用域**

`environment`、`skills`、`cases.parallelism`、`cases.defaults.*` 只认批次那一层；在一份用例配置顶上再写一遍这些，不报错，是默默丢掉的。反过来，`input`、`context`、`constraints`、`expect` 能配到单条用例上。判官（`judge`）整块写在用例那一层——`type`、`model`、`criteria`、`pass_threshold` 一起写全，批次那一层不写：原先记的是「批次那层写类型与模型、用例那层只写 `criteria`、`model` 跟着继承」，落成时实测不成立——批次那层只写 `type` 与 `model` 会被校验驳回（判官缺 `criteria`）；改成与 `evals/plain-language/` 那份配置相同的写法（用例那层整块写全）之后，两份批次配置的校验都过。只有某一条用例用得上的准备动作，配在批次那一层就是每条都跟着做一遍——这一批里没有这种动作；唯一那个「只有一条用得上」的东西（干净解释器）已经拆到单独一批里去了。

**4. 判据落在哪、怎么落到判官上**

批二那十条的判据全落在「要读执行过程」：判官按用例配置里那几条 `criteria` 逐条判——判的是当轮回复里说到没说到、以及过程记录里脚本被跑起来时交进去的是什么。十条的判官都取 `type: agent_judge`、整块写在用例那一层（第 3 条那段照落成时实测订正）；`expect.exit_code: 0` 作先筛，筛不过就不花判官那份钱。批一那 25 条不经过判官：测试代码自己比输出、退出码与盘上的文件。

**5. 判据的通过口径**

十条用例都取「列出的判据全成立才算过」：`judge.pass_threshold` 写 `1.0`。不写就是按条计分、过半数就算过——这几条的预期结果本来写的就是「这几样都要做到」，比如 TC-34 说了「说数不了」还报出一个数，那不算过。判据里凡「说清」「说明」这类，判的是那个意思有没有，不判原话怎么写的（各条配置的 `criteria` 里照抄测试用例规格说明的预期结果，不另加严）。

**6. 消息与上下文怎么渲染**

`input.prompt` 那段正文原样发进会话，不加工、不补话。技能由 `skills` 那一段按使用者机器上装好的样子装进工作区（在 `.claude/skills/token-counter/` 下），被测那边按技能名唤起——带插件前缀的唤起名用不了。`evals/` 子树不会跟着装，技能自己带着的评测材料不会进工作区。这一批不用钩子，也不靠常驻上下文：十条用例的判据都只看当轮。

**7. 这一批能不能并发**

- 批二·第一轮**可以并发**：每条用例各有各的工作区，都只读本机已经装好的引擎，互相不扰；落成时先按 `cases.parallelism: 1` 串着跑（报告好读），要提速再改大。
- 批二·第二轮必须取 1：这一条赌的就是「解释器里没装引擎」，并发起来别的用例可能先把引擎装上，那一条就白跑了。

**8. 跑不了原样的那几条**

逐条对了一遍通用稿：

- **TC-32（干净机器）**：评测机上引擎已经装着——「把会话里的解释器换成干净那个」这一步在 skill-up 里没有现成开关（它那几份字段说明与 usage-notes 都没写「让被测那边不用机器上默认的 python」）。落成时照有据可依的那条候选落了：这一批的 `environment.setup_steps` 建好干净解释器（ENV-5）之后，往工作区根写一份 `CLAUDE.md`，写明跑 Python 一律用干净那个解释器的绝对路径——把东西送进会话的道，usage-notes 里只写了这一条（常驻、且不进当轮消息），而 setup_steps 排在被铺夹具之前、夹具里又没有同名文件，写下的那份不会被盖掉。仍算**待确认**：那是提示、不是环境改造，被测那边照不照办没核过；第一次跑先验这一条。它单独一批（`eval-clean-machine.yaml`）就是给这一步留的位置。
- **DATA-16、DATA-17、DATA-23（DATA-22 同）那几条消息里的路径**：通用稿写的是「绝对路径」，落到这一套上，工作区路径开跑时才定得下来，配置里写不出——落成时写成工作区相对路径（`chinese_file`、`gbk_file`、`not_here.bin`），与 `evals/plain-language/` 那一批的先例一致：夹具铺在工作区根，消息里就用工作区里那份的相对路径。**待确认**：第一次跑先拿一条验一遍。
- **DATA-2 要铺进工作区**：走 `context.repo_fixture` 这条路，与设计稿一致。
- **脚本批那 25 条不进这套配置**：它们的判据落在输出上，归可跑测试那一边，跑法与设计稿一致，没有出入。
- 其余各条与设计稿一致，没有出入。

**9. 跑过之后结论记在哪**

哪几条没过、哪条判据没过、为什么、下一轮改什么，落在那一批报告里的 `result.json` 与 `report.html` 里，不另起一份、也不写回产出那几份文档。两遍结论不一致的用例照实记在同一批的报告里——一轮过一轮不过的，毛病多半出在判据卡了可有可无的附带动作，回头改配置里那一条 `criteria`。

### 2.2 怎么跑、报告落在哪

一批跑测共用一个时间戳目录：先取一次当前时刻，这一批的几条命令都拿它当 `--output-dir`。下面几条命令都在仓库根下跑，命令与报告目录里那些路径都从仓库根算。

```text
$ts = Get-Date -Format "yyyy-MM-dd-HHmm"    # bash 上是 ts=$(date +%Y-%m-%d-%H%M)

# 批二·第一轮（先校验，再跑）
skill-up validate evals/token-counter/eval.yaml
skill-up run evals/token-counter/eval.yaml --output-dir "evals/token-counter/runs/$ts"
skill-up run evals/token-counter/eval.yaml --output-dir "evals/token-counter/runs/$ts"   # 第二遍，落进 iteration-2/

# 批二·第二轮（另取一个时间戳，单独一个目录）
skill-up validate evals/token-counter/eval-clean-machine.yaml
skill-up run evals/token-counter/eval-clean-machine.yaml --output-dir "evals/token-counter/runs/$ts2"
skill-up run evals/token-counter/eval-clean-machine.yaml --output-dir "evals/token-counter/runs/$ts2"   # 第二遍
```

报告落在 `evals/token-counter/runs/<这批的时间戳>/`，底下 `iteration-1/`、`iteration-2/` 是 skill-up 自己追加的——这批里跑的第几回就是几。两批各用各的时间戳目录，盖不掉对方，前几批的报告都留着。

**报告出哪两种格式**：两份配置的 `report.formats` 那一栏都写 `json` 与 `html`——`result.json` 给机器读，`report.html` 给人看。只写一条命令行的补法：已经跑过的那些轮想补 HTML，用 `skill-up report <那份 result.json> --format html` 从 `result.json` 生成，不必重跑；补出来的是另存的那一份，别跟当场跑出来的混在一处。

**跑测时的两处确认**（属于开跑前的准备，不是配置里的事）：ENV-6——跑脚本批里 TC-24、TC-25 那两条之前，确认包索引取得到 0.22.2；ENV-4——批二开跑前，确认本机解释器 `import tokenizers` 成功。

**退出码**：`skill-up run` 退 0 表示这一批全过，退 1 表示有没过或报错的——批与批之间别用退出码短路，两批都要跑完再合起来看。

**哪些东西不进 git**：项目 `.gitignore` 里 `evals/*/runs/` 那条把整批报告盖住了；`evals/*/.clean-venv/` 那条把干净解释器盖住了。落成的那几份配置、用例与夹具照常进 git。
