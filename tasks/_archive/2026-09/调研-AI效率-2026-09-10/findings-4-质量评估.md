# 调研笔记 4：AI 产出质量的度量与回归（质量评估方向）

> 调研日期：2026-09-10　｜　方式：纯联网调研，中英文各检索多轮，权威文章 WebFetch 读原文，GitHub 指标用 `curl -s https://api.github.com/repos/<owner>/<repo>` 实测
> 面向对象：中文全栈/AI 开发者，个人项目（FastAPI + React 量化系统等），**免费/开源自托管优先**，商业方案作对照
> 一句话结论：**离线评测用 promptfoo / DeepEval（免费、MIT/Apache），线上观测用 Langfuse 自托管（MIT，免费），主观质量用 LLM-as-judge 但要防偏差，编码质量靠 CI 硬门禁 + 变异测试而非覆盖率**

---

## 0. TL;DR（先看这个）

| 需求 | 免费推荐 | 商业对照 |
|---|---|---|
| Prompt/多模型对比、红队 | **promptfoo**（MIT，CLI+YAML） | promptfoo Enterprise |
| 写进 pytest 的质量门禁 | **DeepEval**（Apache-2.0） | Confident AI 云（$99–499/月） |
| RAG 检索质量 | **Ragas**（Apache-2.0） | Ragas + Langfuse 云 |
| 线上追踪/成本/评测一体化 | **Langfuse 自托管**（MIT） | LangSmith（闭源，$39/人/月） |
| 本地/Notebook 评估与漂移 | **Arize Phoenix**（开源） | Arize AX（企业版） |
| 主观打分 | LLM-as-judge（用免费模型当裁判） | Braintrust、Confident AI |

**个人项目最小闭环**：`promptfoo`（prompt A/B + 回归） + `DeepEval`（3~5 条 pytest 断言） + `Langfuse` 自托管（线上追踪） + 通用 CI 里的 SAST/变异测试。全部可零成本跑通，唯一开销是裁判模型的 API 费用（可用本地 Ollama 模型替掉）。

---

## 1. 提示词/LLM 评测框架对比（≥3 个，相互对比）

### 1.1 定位速览

| 维度 | **promptfoo** | **DeepEval** | **Ragas** | **OpenAI Evals** | **TruLens** |
|---|---|---|---|---|---|
| 主语言/形态 | Node CLI + YAML | Python（pytest 原生） | Python 库 | Python 库/平台 | Python 库 |
| 最擅长 | 多模型/prompt 横向对比、**红队** | 写进 CI 的质量门禁、通用指标 | **RAG 专用**指标 | OpenAI 官方基准/简单评测 | 链式应用可观测+评估 |
| 指标/断言 | 50+ 断言、40+ 红队类别 | 14+ 指标（幻觉/偏见/毒性/RAG/G-Eval） | 8 个核心 RAG 指标 | 基础评测 + 模型分级 | groundedness/上下文相关等 |
| CI 集成 | 好（GitHub Actions） | **最好**（pytest 直接失败构建） | 中等 | 一般 | 中等 |
| 配置方式 | YAML | Python | Python | YAML+Python | Python |
| 许可证 | MIT | Apache-2.0 | Apache-2.0 | 见实测 | MIT |
| 上手时间 | 30–60 分钟 | 1–2 小时 | 1–2 小时 | 30 分钟+ | 1–2 小时 |

### 1.2 各自画像（含 WebFetch 原文结论）

**promptfoo —— CLI 优先、把"哪个 prompt/模型该上线"变成矩阵**
- 一个 YAML 里声明 `providers`（模型）、`prompts`、`tests`（用例+assert），`promptfoo eval` 跑出"prompt × 模型 × 用例"矩阵，`promptfoo view` 看通过率/延迟/成本对比。
- 断言分三层：确定性（`contains`/`regex`/`is-json`/`latency`/`cost`，免费可复现）、LLM 裁判（`llm-rubric`）、自定义 JS。
- 2026 的看家本领是**红队**（`promptfoo redteam init/run/report`），自动生成越狱/注入/PII 泄露等对抗输入，覆盖 40+ 攻击类别。
- 短板：非 Python 原生，自定义指标要写 JS；**没有原生 RAG 指标**。
- 来源：https://genai.qa/blog/promptfoo-vs-deepeval-vs-ragas/ ；https://qaskills.sh/blog/promptfoo-vs-deepeval-vs-ragas-2026

**DeepEval —— "Pytest for LLMs"，把质量做成 CI 门禁**
- `pip install -U deepeval`，写 `test_*.py`、构造 `LLMTestCase`、选指标、`assert_test`，跑 `deepeval test run` 或直接 `pytest`；指标低于阈值即让构建失败。
- 指标含 `AnswerRelevancyMetric`、`FaithfulnessMetric`、`HallucinationMetric`、`BiasMetric`、`ToxicityMetric`、`SummarizationMetric`，以及用自然语言定义评分标准的 **G-Eval** 自定义指标。
- 与 Ragas 是**互补**非替代：DeepEval 覆盖广，Ragas 覆盖 RAG 深；成熟团队常两者并用（同一 CI 流水线里）。
- 来源：https://aicoolies.com/comparisons/deepeval-vs-promptfoo ；https://machinelearningmastery.com/llm-evaluation-frameworks-compared-how-to-actually-measure-what-your-model-does/

**Ragas —— RAG 领域的"显微镜"**
- 五个已成事实标准的指标：Faithfulness（答案是否被检索上下文支撑）、Answer Relevancy（是否答到点上）、Context Precision（检索到的上下文是否都是相关的）、Context Recall（该检索的是否都检索到了）、Answer Correctness。
- 优点：指标背后有论文/学术方法论，不是厂商内部启发式；缺点：**仅限检索+生成评分**，不含生产监控/协作层。
- 适合"答案是错的，但不知道是 prompt 坏还是检索坏"时用它做定位。
- 来源：https://www.knovo.dev/guides/ai-evaluation-frameworks ；https://docs.ragas.io

**OpenAI Evals**：官方基准与注册表，适合做模型分级/学术向基准，**不面向应用级回归**，社区活跃度已明显下降（见下节 pushed_at 2026-04）。
- 来源：https://github.com/openai/evals

**TruLens**：偏"链式/Agent 应用的可观测+评估"（RAG triad 早期实现者之一），在 DeepEval/Ragas 崛起后声量下降，仍可作轻量备选。
- 来源：https://github.com/truera/trulens

### 1.3 选型决策（原文共识）

> 判断"该用哪个"的关键不是看指标新旧（大家实现的是同一批指标思想：faithfulness / relevancy / correctness / 一致性 / 成本 / 延迟），而是**工作流契合度**：指标怎么被触发、结果去哪、以及**是否阻断部署**。

| 你的问题 | 选 |
|---|---|
| 哪个 prompt/模型更好，怎么防红队 | promptfoo |
| 这次改动有没有让质量回退（要卡 CI） | DeepEval |
| RAG 检索/生成到底哪一环坏了 | Ragas |
| 线上跑起来之后持续监控 | Langfuse / Arize Phoenix |

多数生产团队**跑两个**：一个轻量框架做 CI 门禁 + 一个平台做持续监控与人工复核。
- 来源：https://machinelearningmastery.com/llm-evaluation-frameworks-compared-how-to-actually-measure-what-your-model-does/ ；https://aiml.qa/llm-evaluation-framework-benchmark-2026/

---

## 2. GitHub 实测（`curl -s https://api.github.com/repos/<owner>/<repo>`，2026-09-10）

| 仓库 | Stars | License | Last push (pushed_at) |
|---|---:|---|---|
| promptfoo/promptfoo | **24,982** | MIT | 2026-09-10T03:35:51Z |
| openai/evals | 19,418 | NOASSERTION* | 2026-04-14T15:29:57Z |
| confident-ai/deepeval | 18,196 | Apache-2.0 | 2026-09-08T07:08:59Z |
| **vibrantlabsai/ragas**（原 explodinggradients/ragas） | 15,693 | Apache-2.0 | 2026-02-24T07:47:19Z |
| truera/trulens | 3,544 | MIT | 2026-09-09T15:52:38Z |
| langfuse/langfuse | **34,413** | NOASSERTION* | 2026-09-10T02:47:10Z |
| Arize-ai/phoenix | 11,399 | NOASSERTION* | 2026-09-10T03:20:50Z |
| langchain-ai/langsmith-sdk | 1,048 | MIT | 2026-09-09T23:52:06Z |
| Helicone/helicone | 6,141 | Apache-2.0 | 2026-08-31T05:02:00Z |

> 实测说明：
> - `ragas` 仓库已**迁移**：`explodinggradients/ragas` 返回 `301 Moved Permanently`，跟随重定向后为 **`vibrantlabsai/ragas`**（故改用 `curl -sL` 拿到实测值）。注意其 pushed_at 停在 **2026-02**，是上表中最"久未更新"的项目之一，选用前值得留意 release 节奏。
> - `NOASSERTION` 表示 GitHub 无法自动归类 License（多为自定义/多许可声明）：OpenAI Evals 为 MIT 风格自定义声明；Langfuse 官网明确为 **MIT license（全产品特性 MIT）**；Phoenix 主体为开源许可（含部分 ELv2 组件），以仓库 LICENSE 为准。
> - **`langchain-ai/langsmith-sdk` 只有 SDK 是 MIT，LangSmith 平台本身闭源**，不能自托管（企业版除外）。不要被该仓库 star 数误导为"平台开源"。

---

## 3. LLM-as-judge：用法与已知偏差（≥3 条，带来源）

### 3.1 三种主流用法

| 模式 | 做法 | 成本 | 适用 | 缺点 |
|---|---|---|---|---|
| **Pointwise 点分制** | 单条输出按维度打分（1–5 或 pass/fail） | 1× | 批量筛选、看板、回归跟踪 | 绝对分会跨运行漂移 |
| **Pairwise 两两比较** | 同输入 A/B 两条，判谁赢 | 2×（双向） | A/B 测试、小规模排序 | 批量时成本平方增长 |
| **Reference-based 参考答案对照** | 与已知正确答案比对 | 1×+ | 有黄金答案的评测集 | 无唯一答案的任务不可用 |

> 生产管线常**三者混用**：点分制跑夜间看板，两两比较做发布门禁，参考答案对照用于有黄金数据的场景。
> 来源：https://ima.qq.com/wiki/?shareId=07dd357d2983e5e8fe6c0407e2203a60ec7683e69ad6342ea82041fc00bdc238（SurePrompts 指南摘要）

### 3.2 已知偏差清单（均带来源）

**① 位置偏差 Position Bias**
- 定义：裁判系统性偏爱排在前面（或特定位置）的回答；**交换 A/B 顺序后裁决会翻转**，且与内容质量无关。
- 量级：早期研究（2023）显示 GPT-4 双向保持一致判决的比例仅约 **2/3**；IJCNLP 2025 系统研究覆盖 15 个裁判、约 15 万条评估，确认效应普遍存在；另有汇总给出 **5–15%** 的量级。
- 缓解：**A→B 与 B→A 各跑一次取平均，只有两次都选同一答案才算赢**；位置交换 + 多次多数投票被证实有效。
- 来源：https://llm-judge-bias.github.io/ ；https://van.tdn.gtranslate.net/wiki/LLM-as-a-Judge ；https://ima.qq.com/wiki/?shareId=f2ba1a8795c8c54d39dc5b21553b758a4670088df34004a4ff73378f44f7cd5f

**② 冗长偏差 Verbosity Bias**
- 定义：**更长的回答即使增加的内容不含信息也被打更高分**；把同一答案只是改写得更长，Claude/GPT-3.5 仍有 **>90%** 概率选更长者。
- 交叉验证（arXiv 2604.23178）：长度感知测量下**并非所有模型都是冗长偏差**——Gemini Pro/Flash、Llama 偏长（+0.24~+0.44），**Claude Sonnet 4 反而偏爱简洁（−0.12）**，GPT-4o 基本中性（−0.04）；但在"截断对照"下所有模型都能正确偏好完整答案（0.88–1.00 准确率）。
- 缓解：Rubric 里写明"**长度本身不加分，信噪比才加分**"；或用 AlpacaEval 2.0 的 **LC-WinRate（长度控制胜率）** 抵消。
- 来源：https://van.tdn.gtranslate.net/wiki/LLM-as-a-Judge ；https://arxiv.org/abs/2604.23178

**③ 自我偏好 Self-Preference / 自我增强偏差**
- 定义：裁判给自己或同家族模型的输出打更高分（俗称 "LLM narcissism"）。GPT-4、Claude 均被观察到偏好自家输出。
- 量级：汇总表给出 **10–25%**。注意有害的版本特指"**裁判没能惩罚自家模型的错误**"，而非单纯的分数高低。
- 缓解：**用与被评模型不同家族的模型做裁判**；条件允许时多裁判取平均/多数投票。
- 来源：https://llm-judge-bias.github.io/ ；https://machinelearningmastery.com/llm-evaluation-frameworks-compared-how-to-actually-measure-what-your-model-does/

**④ 风格偏差 Style Bias（2026 新发现，最被忽视）**
- 定义：偏好 markdown、加粗、列表等"看起来专业"的排版，**即使内容并无更好**。
- 量级：arXiv 2604.23178 测得**这是最主要的偏差（0.10–0.76），远超位置偏差（≤0.04）**，却研究最少。含义：裁判可能只因为 A 用了标题/列表就判 A 赢 —— 你的 prompt 改动可能"赢"在排版而非质量。
- 缓解：位置镜像（position-mirrored）对照；打分前做格式归一化；rubric 里显式声明格式不计分。
- 来源：https://arxiv.org/abs/2604.23178

**⑤ 指令泄漏 / 鲁棒性与复现性**
- 指令泄漏：把评分 rubric 暴露给裁判可能被"rubric-hacking"——reward 高但实际不好；缓解是"对评分标准盲评"或分步评分。
- 复现性：生成有随机性，同一输入重复跑分数会变；prompt 措辞微改也会扰动判决；**闭源 API 版本更新**会让复现失效。
- 校准：GPT-4o、DeepSeek-R1 等被报告**校准差**（expressed confidence 高于实际准确度，用 ECE/Brier 衡量）；JudgeBench 上"二选一、其中一条客观正确"的任务里，裁判仅略高于随机。
- 缓解：**pin 住裁判模型版本**、用容差带（tolerance band）而非精确阈值、对裁判本身做与人类的一致性校验（如 alt-test）。
- 来源：https://van.tdn.gtranslate.net/wiki/LLM-as-a-Judge ；https://ima.qq.com/wiki/?shareId=f2ba1a8795c8c54d39dc5b21553b758a4670088df34004a4ff73378f44f7cd5f

**⑥ 对"80% 人类一致率"的警示**
- 常被引用的 MT-Bench "LLM 裁判与人类约 80% 一致"是**宽泛基准上的平均**，**不代表在你的任务/你的裁判模型上可靠**。把它当作"上线就绪保证"是错误用法。
- 有研究给出 12 类偏差分类法（CALM 框架）；也有版本发现旧结论不再成立（如位置偏差在部分新模型上已可忽略）。**结论：偏差会随模型版本漂移，必须定期重新审计，而不是一次性相信。**
- 来源：https://machinelearningmastery.com/llm-evaluation-frameworks-compared-how-to-actually-measure-what-your-model-does/ ；https://llm-judge-bias.github.io/

### 3.3 去偏实操（成本友好）
- 位置交换取平均（成本 +1× 调用）；
- 用**异家族裁判**（同时解决自我偏好）；
- 多裁判多数投票（成本更高，最稳）；
- rubric + 参考答案引导（reference-guided judging）；
- 分开推理步骤（CoT）让判决可审计；
- **先用人审样本给裁判做"体检"，再放权**。
- 关键数据点：arXiv 2604.23178 发现 **"中端模型 + 正确去偏"可超过顶级裁判**——Gemini 2.5 Flash + Combined Budget 达到 71.0% 一致率（κ=0.549），单次约 **$0.001**，比 Claude Sonnet 4（69.5%，$0.015）**便宜约 15×**。对个人项目很有指导意义：**不必用最贵模型当裁判**。
- 来源：https://arxiv.org/abs/2604.23178

---

## 4. 可观测平台对比（开源 vs 商业）

| 维度 | **Langfuse** | **LangSmith** | **Arize Phoenix** | Helicone |
|---|---|---|---|---|
| 重心 | 开源 tracing 优先 | LangChain/LangGraph 原生托管 | **评估优先**、ML 级监控 | 代理式（proxy）接入 |
| 是否开源 | **是，MIT，全功能自托管** | **否（平台闭源）**，仅 SDK 开源 | 是（OTel/OpenInference 原生，可本地跑） | 是（Apache-2.0） |
| 部署 | 自托管（Postgres+ClickHouse）/云 | 云 / BYOC / 企业自托管 | 本地 container / Notebook / 云 | 自托管 / 云 |
| Tracing | 是 | 是 | 是 | 是 |
| Prompt 管理 | **是** | 是 | 有限 | 有限 |
| LLM-as-judge 评估 | 是 | 是 | **是（强）** | 无 |
| Datasets/实验 | 是 | 是 | 是 | 无 |
| 人工标注队列 | 是 | 是 | 否 | 否 |
| 成本追踪 | 是 | 是 | 是 | 是 |
| OTel 原生 / 框架无关 | 是 / 是 | 是 / 偏 LangChain | 是 / 是 | 否 / 否 |
| 免费额度 | 自托管免费；云 5 万 units/月 | 5,000 traces/月 | 自托管免费 | 10,000 请求/月 |
| 付费起价 | 云 $29/月 | **$39/人/月** | 云按量 | 按量 |
| 短板 | 自托管需运维 DB | 闭源、按 trace 计费易贵、非 LangChain 体验弱 | OTel 学习曲线（生产部署约 2–4 周）、偏 Notebook | 方向单一（仅追踪）、代理加 50–80ms 延迟 |

> 实测补充：`langfuse/langfuse` **34.4k stars**、pushed 2026-09-10、官网声明全产品 MIT；`Arize-ai/phoenix` 11.4k stars、pushed 2026-09-10；`langchain-ai/langsmith-sdk` 仅 SDK（1.0k stars）。
> 结论（对个人项目）：
> - **首选 Langfuse 自托管**——MIT、可免费跑、Docker Compose 一把梭、OTel 原生不锁框架；缺点是自托管要维护 Postgres+ClickHouse（个人项目可用其云免费档或轻量 Docker）。
> - 若栈就是 LangChain/LangGraph，LangSmith 零配置接入最省事，但**闭源 + $39/人/月**。
> - 若重 RAG 评估/漂移分析且喜欢 Notebook，选 Phoenix。
> - **反模式提醒**：高流量别全量追踪，采样 10% 即可；接入可观测 ≠ 质量变好，质量提升来自对 trace 的分析和基于评估的迭代。
> 来源：https://aiwiki.ai/wiki/langfuse ；https://seodatapulse.com/comparisons/best-ai-llm-observability-langsmith-vs-langfuse-vs-phoenix-2026 ；https://learnagent.wiki/agent/cards/langsmith ；https://langfuse.com

---

## 5. 编码场景下的质量守护（CI 中的 AI 代码审查 & 覆盖率）

### 5.1 为什么旧门禁失效（关键数据）
- **规模变化是算术问题**：Faros AI 对 10,000+ 开发者、1,255 个团队的分析显示，AI 采纳后**平均 PR 体积增长 154%**——"逐行人工 review"这条路直接失效，评审疲劳必然漏 bug。
- **漏洞密度更高**：AI 生成代码的漏洞密度约为人工代码的 **1.88 倍**；单一 SAST 工具对 AI 代码漏洞的识别率**低于 22%**（国内汇总口径给出 45%–72% 的区间，需多工具叠加）。
- METR 研究：有经验的开发者在成熟项目上用 AI，**反而慢 19%** —— 说明"上 AI"不等于"更快更好"，门禁与流程才是关键。
- 来源：https://www.twocents.software/blog/how-to-test-ai-generated-code-the-right-way ；https://totalshiftleft.ai/blog/testing-ai-generated-code ；https://blog.csdn.net/u013970991/article/details/162537921

### 5.2 覆盖率 vs 变异测试：本方向最重要的一个纠正
- **行覆盖率本身是弱信号**：AI 很会生成"调用了函数但不做任何断言"的测试——覆盖率漂亮，却抓不到任何缺陷。
- **变异测试（mutation testing）才是正确答案**：它回答的是"如果这行代码被改错，测试套件会不会发现？"——这才是你以为覆盖率在回答的问题。
- 实操：`mutmut`（Python）/ Stryker（JS）等，**只对变更文件跑**以控成本，门槛设为变异分 ≥60%（可用脚本解析报告卡 CI）。
- **衍生风险**：不要让同一个模型既写实现又写测试（"两边都由 AI 写"会自我确认错误）。
- 来源：https://totalshiftleft.ai/blog/testing-ai-generated-code ；https://www.victorsaisse.com/blog/ai-coding-guide-2026

### 5.3 可落地的 CI 硬门禁（个人项目可直接抄）
| 门禁 | 工具（免费） | 建议阈值 | 为什么对 AI 代码重要 |
|---|---|---|---|
| 圈复杂度 | lizard / radon / eslint complexity | 单函数 CCN ≤ 15 | AI 爱写 120 行、15 层嵌套的函数 |
| 契约不静默变更 | oasdiff / 契约测试 | breaking 变更即 fail | AI"加个分页"会顺手改响应结构 |
| **变异分**（非覆盖率） | mutmut / Stryker | ≥60%（变更文件） | AI 生成的测试常只"跑过"不断言 |
| 依赖审查 | pip-audit / npm audit / Dependabot | 高危即阻断 | AI 会随口引入可疑/废弃/仿冒包 |
| 密钥扫描 | gitleaks / trufflehog | 0 容忍 | AI 示例代码常含"像真的"凭据 |
| SAST | semgrep / SonarQube / CodeQL | 高危即阻断 | AI 代码漏洞密度更高、单工具覆盖低 |
| N+1 / 并发 | 查询计数中间件 / hypothesis / fast-check | 每请求 >15 查询告警 | AI 常写 `for x: db.query(...)` 和裸 `await` |
- 来源：https://www.victorsaisse.com/blog/ai-coding-guide-2026 ；https://totalshiftleft.ai/blog/testing-ai-generated-code

### 5.4 AI 代码审查工具（CI 中"用 AI 审 AI"）
- 国际：Snyk（SAST+SCA，~65%）、GitLab Duo（~70%，$39/月）、GitHub Advanced Security（~68%，$49/月）、SonarQube（免费开源，~45% 但够用）、CodeQL（免费公开仓库，需自定义规则）、Veracode（~72%，定制报价）。
- 面向 AI 代码的专用审查：**CodeRabbit** 等，常与生成工具形成"生成→自动审"闭环以拉齐质量。
- 关键建议：**至少叠加 2 款工具**（单一工具覆盖率太低）；**AI 审查 + 人工复核**组合（纯 AI 审查漏报率约 30%）；安全关键代码（认证/授权/支付/加密）**禁止纯 AI 生成**，必须人工逐行 + 双人复核。
- 人工 review 的精力应聚焦机器判断不了的：架构匹配度、复杂业务边界（资金/状态流转/并发）、性能与资源、权限与合规。低风险纯工具代码走快速通道，核心模块走资深二次复核——**分层审查**，避免"一刀切"拖慢 50%。
- 来源：https://blog.csdn.net/u013970991/article/details/162537921 ；https://www.twocents.software/blog/how-to-test-ai-generated-code-the-right-way

### 5.5 一个正反馈数据点
- Qodo 调研：不用 AI 做测试的开发者仅 **27%** 对测试套件有信心；用 AI 做测试的**升至 61%**。差距来自"更多用例、更全边界"，但需配合变异测试纠正"数量≠质量"。
- 来源：https://www.twocents.software/blog/how-to-test-ai-generated-code-the-right-way

---

## 6. 给个人项目的最小可落地评估方案（FastAPI + React 量化系统）

> 目标：**零成本起步、半天内跑通、能卡住回归**。核心思路——确定性断言优先，LLM 裁判只用在主观项，且必须防偏差。

### 阶段一（半天，0 成本）：promptfoo 离线回归
1. `npx promptfoo@latest init`，把量化系统里**最值钱的 AI 调用**（如"自然语言→策略参数 JSON"、"行情解读"、"风险提示生成"）各建 3–5 条用例。
2. 断言优先用**确定性**的：`is-json`、`contains-json`（校验字段/枚举）、`javascript`（数值区间、无禁止词）、`latency`、`cost`——免费、可复现、不引入偏差。
3. 主观项（解读是否专业、风险提示是否到位）才用 `llm-rubric`；**裁判模型选便宜的**（本地 Ollama qwen 或 gpt-4o-mini），并在 rubric 里注明"长度/格式不加分"。
4. 接 GitHub Actions：`promptfoo eval` 通过率低于基线即 fail，作为 prompt 变更的体检。

### 阶段二（半天，0 成本）：DeepEval 进 pytest
1. 在 FastAPI 项目里 `pip install deepeval`，写 `tests/test_ai_quality.py`。
2. 选 **3–5 条**最关键断言：如 `AnswerRelevancyMetric` + `HallucinationMetric`（防止行情解读编造数据）+ 一条 G-Eval 自定义"MUST NOT 给出具体买卖建议"。
3. `pytest` 即可跑，指标低于阈值直接让构建失败——**这就把"AI 输出质量"变成了可回归的测试**。

### 阶段三（半天，0 成本）：Langfuse 自托管上线观测
1. Docker Compose 起 Langfuse，FastAPI 侧用其 Python SDK/OTel 埋点，记录每次 LLM 调用的输入输出、token、成本、延迟。
2. 配采样（如 10%），别全量；把线上低分 trace 沉淀成 golden dataset，回流到阶段一/二的门禁用例。

### 阶段四：编码质量（通用 CI，与 AI 无关但更该有）
- 在 CI 里加：圈复杂度、`oasdiff` 契约检查、**变异测试（变更文件 ≥60%）**、`pip-audit` + `npm audit`、`gitleaks`、`semgrep`。
- 针对量化系统特别加：**N+1 查询计数**（每请求 >15 告警）、**资金不变量/并发属性测试**（hypothesis，`balance >= 0` 之类），因为 AI 极易写出"开发 10 行数据没问题、生产 1 万行就死"的代码。
- 交易/资金/权限相关代码**禁止纯 AI 生成**，强制人工逐行 + 双人复核。

### 阶段五：防偏差纪律（长期）
- 裁判模型 **pin 版本**；位置交换双跑取一致；用异家族裁判；定期（每季度/每次换模型）用几十条人工标注做**裁判体检**（一致性/翻转率）。
- 用**容差带**而非精确阈值，避免 LLM 非确定性导致 CI 抖动。

### 商业方案对照（个人项目通常用不上，供决策）
| 场景 | 商业选项 | 价格参考 |
|---|---|---|
| 评测+看板托管 | Confident AI（DeepEval 官方云） | Starter $99–200/月；Pro/Team $499–2000/月 |
| 观测+评测平台 | LangSmith | $39/人/月 |
| 评估平台 | Braintrust | 定制 |
| 企业 ML/LLM 监控 | Arize AX | 定制 |
| AI 代码审查 | Snyk / GitLab Duo / GHA Security | $39–57/人/月 |
> 结论：个人/小团队用 **promptfoo + DeepEval + Langfuse 自托管** 即可覆盖 90% 需求，省下上述全部月费；唯一持续成本是裁判 API token（可用本地模型压到接近 0）。

---

## 7. 主要来源 URL 汇总

**评测框架**
- https://genai.qa/blog/promptfoo-vs-deepeval-vs-ragas/ （三框架深度对比）
- https://qaskills.sh/blog/promptfoo-vs-deepeval-vs-ragas-2026
- https://aiml.qa/llm-evaluation-framework-benchmark-2026/ （8 框架基准）
- https://machinelearningmastery.com/llm-evaluation-frameworks-compared-how-to-actually-measure-what-your-model-does/
- https://www.knovo.dev/guides/ai-evaluation-frameworks
- https://aicoolies.com/comparisons/deepeval-vs-promptfoo
- https://blog.csdn.net/qq_34319145/article/details/161516334 （中文选型）
- https://docs.ragas.io

**LLM-as-judge 与偏差**
- https://llm-judge-bias.github.io/ （CALM：12 类偏差）
- https://arxiv.org/abs/2604.23178 （TMLR 2026：9 种去偏策略实测）
- https://van.tdn.gtranslate.net/wiki/LLM-as-a-Judge （偏差综述）
- https://ima.qq.com/wiki/?shareId=07dd357d2983e5e8fe6c0407e2203a60ec7683e69ad6342ea82041fc00bdc238 （三种裁判模式）

**可观测平台**
- https://langfuse.com
- https://aiwiki.ai/wiki/langfuse （Langfuse vs LangSmith vs Helicone vs Phoenix 对照表）
- https://seodatapulse.com/comparisons/best-ai-llm-observability-langsmith-vs-langfuse-vs-phoenix-2026
- https://learnagent.wiki/agent/cards/langsmith （中文对照）

**编码质量守护**
- https://totalshiftleft.ai/blog/testing-ai-generated-code （变异测试 > 覆盖率）
- https://www.victorsaisse.com/blog/ai-coding-guide-2026 （7 道 CI 门禁）
- https://www.twocents.software/blog/how-to-test-ai-generated-code-the-right-way （Faros AI 154%、Qodo 27%→61%）
- https://blog.csdn.net/u013970991/article/details/162537921 （中文 AICodeReview 三层流程）

**GitHub 实测**
- https://api.github.com/repos/promptfoo/promptfoo 、/confident-ai/deepeval 、/openai/evals 、/vibrantlabsai/ragas 、/langfuse/langfuse 、/langchain-ai/langsmith-sdk 、/Arize-ai/phoenix 、/truera/trulens 、/Helicone/helicone

---

## 8. 遗留问题 / 待验证
1. 各框架**真实跑一遍**的体验到目前仅基于二手资料，建议下一步在量化项目里做"promptfoo 3 用例 + DeepEval 3 断言"的 PoC 验证成本与抖动。
2. Langfuse 自托管的资源占用（Postgres+ClickHouse）在小服务器上的实际表现需实测。
3. 裁判模型用**本地 Ollama** 的一致性/翻转率尚无本地实测数据，需按阶段五做体检。
4. `openai/evals` 的 NOASSERTION 许可需读 LICENSE 原文确认是否 MIT。
