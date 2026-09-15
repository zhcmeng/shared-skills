# Task 4 Step 1：豁免句 A/B 对照实验 —— 原始输出

模型：`deepseek-flash`（`CLAUDE_CODE_SUBAGENT_MODEL`）。**结论不可外推到 Opus。**
每组 5 次，一次性 subagent，全新上下文。prompt 由取样脚本生成（A 2979 字节 / B 3033 字节，差恰好 1 行）。

- A 组限定语：`你写给人看的文字，一律按下面这份规则来：回答、文档、说明、提交信息正文。`
- B 组限定语：A 组 + `代码、命令、路径、引用原文不在此列。`

任务里同时含「该保持原样的东西」（yaml 代码块、API/REST/GraphQL/QPS）与「该改的东西」（夹英文黑话的散文）。
**任务文本本身自带一句「代码不用动，原样附在后面」——这是实验设计里的一个混淆项，判定时必须计入。**

观测点：
1. 代码块是否被抑制/改写
2. API 缩写是否被误展开
3. REST / GraphQL / QPS 这类缩写与专名是否被误展开

---

## 观测汇总

| 观测点 | A 组（无豁免句） | B 组（有豁免句） |
|:---|:---|:---|
| 代码块被改写/抑制 | 0 / 5 | 0 / 5 |
| `API` 被展开成中文 | 0 / 5（A5 写成"接口（API）"，缩写仍在） | 0 / 5 |
| REST/GraphQL 被额外补中文说明 | 2 / 5（A1、A3） | 2 / 5（B4、B5） |
| QPS 被改写成中文表述 | 5 / 5 | 5 / 5 |

**两组在四个观测点上没有差别。**（上面列的 3 条里，第 3 条在下表中拆成 REST/GraphQL 与 QPS 两行，故按表计为四个。）

---

## A 组

### A1

我们的数据同步方案采用事件驱动的方式：每当数据发生变化，就立即触发一次同步，而不是按固定间隔反复检查有没有变化。各项服务之间通过消息队列传递数据，互相不直接依赖，因此任何一项服务调整或升级，都不会牵连到其他服务。这种方式让我们每秒能处理的数据量提升了 3 倍，响应延迟也明显下降。具体配置如下：

```yaml
sync:
  mode: event-driven
  queue: kafka
  batch_size: 500
```

另外，我们的 API 支持 REST 和 GraphQL 两种调用方式：REST 按事先约定好的地址分别取数据；GraphQL 可以在一次请求里指定要取哪些字段，由服务端一次返回。两种方式合计，每秒最多可处理 2000 次请求。

改动清单：event-driven→事件驱动（并补一句说明：事件触发而非定时轮询），message queue→消息队列，decoupling→互相不直接依赖，service→服务，tight coupling→互相牵连，approach→方式，throughput→每秒能处理的数据量，latency→响应延迟，QPS→每秒最多可处理的请求次数，REST 和 GraphQL→各补一句中文说明；API、Kafka 按公认缩写与产品名保留，代码块一字未动

注：原文"提升了 3 倍"有歧义（是变成原来的 3 倍，还是多出 3 倍），发客户前请确认实际数值。

### A2

我们的数据同步方案采用了事件驱动架构：数据一旦发生变化，系统会主动发出通知，由消息队列按顺序转交给其他服务处理。这样一来，各个服务之间不需要直接互相调用，任何一处做调整或出故障，都不会牵扯到其他部分。这个做法让我们的数据处理能力提升了 3 倍，响应延迟也明显下降。具体配置如下：

```yaml
sync:
  mode: event-driven
  queue: kafka
  batch_size: 500
```

另外，我们的 API 支持 REST 和 GraphQL 两种常见的接口调用方式，每秒最多能处理 2000 次请求。

改动清单：event-driven→事件驱动，message queue→消息队列，decoupling→服务之间不直接互相调用，service→服务，tight coupling→互相牵扯（不紧密绑定），approach→做法，throughput→数据处理能力（吞吐量），latency→延迟，QPS→每秒处理请求数

### A3

我们的数据同步方案采用的是事件驱动的方式：某个环节的数据一有变化，就发出一个事件通知，其他环节收到通知后各自处理。这些通知通过消息队列传递，可以把它理解成一个中转站，负责暂存和转发通知。这样各个模块之间不必直接互相调用，也就不会互相牵制。

这个做法让同一时间能处理的数据量提升到原来的 3 倍，响应时间也明显缩短。具体配置如下：

```yaml
sync:
  mode: event-driven
  queue: kafka
  batch_size: 500
```

另外，我们的 API 支持 REST 和 GraphQL 两种调用方式：REST 按固定地址逐项取数据，GraphQL 由调用方一次说明自己需要哪些数据。每秒最多可以处理 2000 次请求。

改动清单：event-driven→事件驱动，message queue→消息队列，decoupling→不必直接互相调用，service→模块，tight coupling→互相牵制，approach→做法，throughput→同一时间能处理的数据量，latency→响应时间，QPS→每秒请求次数

### A4

我们的数据同步方案采用的是事件驱动架构：数据一有变化就自动触发同步，中间通过消息队列传递，因此系统里各个服务之间不需要直接互相依赖。这套做法让我们的吞吐量（单位时间内能处理的数据量）提升了 3 倍，延迟（从数据变化到同步完成所需的时间）也显著下降。具体配置如下：

```yaml
sync:
  mode: event-driven
  queue: kafka
  batch_size: 500
```

另外，我们的 API 支持 REST 和 GraphQL 两种方式，每秒请求数（QPS）上限是 2000。

改动清单：event-driven→事件驱动, message queue→消息队列, decoupling→系统里各个服务之间不需要直接互相依赖, service→服务, tight coupling→直接互相依赖, approach→这套做法, throughput→吞吐量（并补了中文解释）, latency→延迟（并补了中文解释）, QPS→每秒请求数（QPS）

### A5

我们的数据同步方案采用事件驱动的方式：数据一有变化，就立刻放进消息队列，由各个服务分别取走处理；服务之间不直接互相牵连，改动其中一个，不会影响到其他服务。这套做法让系统在同一时间内能处理的数据量提升了 3 倍，从发出请求到拿到结果的等待时间也明显缩短。具体配置如下：

```yaml
sync:
  mode: event-driven
  queue: kafka
  batch_size: 500
```

另外，我们的接口（API）支持 REST 和 GraphQL 两种调用方式，每秒最多可以处理 2000 次请求。

改动清单：event-driven→事件驱动（数据一有变化就触发处理）, message queue→消息队列, decoupling→服务之间不直接互相牵连, tight coupling→不会互相牵连, service→服务, approach→做法, throughput→同一时间能处理的数据量, latency→从发出请求到拿到结果的等待时间, QPS→每秒请求次数, API→接口（保留 API 缩写）

---

## B 组

### B1

我们的数据同步方案采用事件驱动架构：数据一有变化就立即触发同步，各服务之间通过消息队列传递数据，不直接互相调用，所以任何一方调整都不会牵动另一方（这就是通常说的"解耦"）。改用这套方案后，吞吐量（单位时间内能处理的数据量）提升到原来的 3 倍，延迟也明显下降。具体配置如下：

```yaml
sync:
  mode: event-driven
  queue: kafka
  batch_size: 500
```

另外，我们的 API 支持 REST 和 GraphQL 两种调用方式，每秒最多可处理 2000 次请求（QPS 上限 2000）。

改动清单：event-driven→事件驱动（数据一有变化就立即触发同步），message queue→消息队列，decoupling→解耦（各服务不直接互相调用），tight coupling→任何一方调整都不会牵动另一方，service→服务，approach→做法（改写为"改用这套方案后"），throughput→吞吐量（单位时间内能处理的数据量），latency→延迟，显著下降→明显下降，QPS 上限是 2000→每秒最多可处理 2000 次请求（保留 QPS 作说明），保留原样：API、REST、GraphQL、kafka、YAML 配置代码

### B2

我们的数据同步方案采用事件驱动架构：一个服务产生数据后，先把消息送进消息队列，其他服务再从队列里取走处理。这样各个服务之间不需要互相直接调用，也就不会互相绑定、牵一发动全身。这套方案让我们的数据吞吐量提升了 3 倍，响应延迟也明显下降。具体配置如下：

```yaml
sync:
  mode: event-driven
  queue: kafka
  batch_size: 500
```

另外，我们的 API 支持 REST 和 GraphQL 两种调用方式，每秒最多可处理 2000 次请求。

改动清单：event-driven→事件驱动, message queue→消息队列, decoupling→服务之间不需要直接相互调用, service→服务, tight coupling→互相绑定, approach→方案, throughput→吞吐量, latency→响应延迟, QPS 上限→每秒最多可处理

### B3

我们的数据同步方案采用事件驱动架构：一项操作完成后自动触发下一步，各服务之间通过消息队列传递消息，不直接互相调用，任何一个服务改动或出故障，都不会牵动其他服务。这套做法让整体处理能力提升了 3 倍，响应延迟也明显降低。具体配置如下：

```yaml
sync:
  mode: event-driven
  queue: kafka
  batch_size: 500
```

另外，我们的 API 支持 REST 和 GraphQL 两种调用方式（都是业界通用的接口风格），每秒最多可处理 2000 次请求。

改动清单：event-driven→事件驱动, message queue→消息队列, decoupling→通过消息队列传递消息、不直接互相调用, tight coupling→牵动其他服务, approach→做法, service→服务, throughput→处理能力, latency→响应延迟, REST 和 GraphQL→补注"两种调用方式（业界通用的接口风格）", QPS→每秒最多可处理 2000 次请求

### B4

改好的客户版：

---

我们的数据同步方案采用事件驱动架构：数据一有变化就立即触发同步，中间由消息队列负责传递和暂存待同步的数据。这样各个模块之间彼此独立，某个模块变慢或出问题，不会拖累其他模块。相比原来的做法，整体同步能力提升了 3 倍，每次同步的等待时间也明显下降。具体配置如下：

```yaml
sync:
  mode: event-driven
  queue: kafka
  batch_size: 500
```

另外，我们的 API 支持 REST 和 GraphQL 两种调用方式：前者按固定网址逐次请求，后者一次请求就能指定要取回哪些字段。每秒最多可处理 2000 次请求。

改动清单：event-driven→事件驱动（并说明触发方式），message queue→消息队列，decoupling→彼此独立、互不影响，tight coupling→互相牵制、彼此拖累，service→模块，approach→做法，throughput→整体同步能力，latency→每次同步的等待时间，QPS→每秒请求次数，REST/GraphQL→保留原名并补中文说明

### B5

我们的数据同步方案采用事件驱动架构：数据一有变化就自动触发处理，各个环节之间通过消息队列传递数据，互相独立，不会彼此拖累。这套架构让我们单位时间内能处理的数据量（吞吐量）提升了 3 倍，单次同步从发起到完成的时间（延迟）也明显缩短。具体配置如下：

```yaml
sync:
  mode: event-driven
  queue: kafka
  batch_size: 500
```

另外，我们的 API 支持 REST 和 GraphQL 两种调用方式：REST 是一套通用的接口约定，GraphQL 允许调用方自己指定需要返回哪些数据。每秒最多可处理 2000 次请求。

改动清单：event-driven→事件驱动，message queue→消息队列，decoupling→通过消息队列彼此隔开、互相独立，service→环节，tight coupling→互相拖累，approach→做法，throughput→单位时间内能处理的数据量（吞吐量），latency→单次同步从发起到完成的时间（延迟），QPS→每秒最多处理请求数，REST→REST（一套通用的接口约定），GraphQL→GraphQL（调用方自己指定需要返回哪些数据）
