# 调研笔记 ①：提升 AI 工作效率与质量的个人方法论

> 范围：上下文工程 / 提示词模式 / Agent 记忆系统 / 官方厂商指南 / 高质量 awesome 清单
> 划界说明：本笔记**不覆盖**"模型路由与网关"与"Token 缓存 / 上下文分层压缩成本"两个话题（今日另有专项）。仅在必要处一句话引用：上下文压缩的**成本视角**已由另一份笔记承接，本文只谈"如何组织上下文以提升质量"的方法论视角。
> 检索语言：中英文各 ≥1 轮（"context engineering best practices 2026"、"AI 编码效率 提示词工程 方法论"、"agent memory best practices"、"plan then execute agent"、"Google prompt engineering guide 官方"）。
> 检索日期：2026-09-10

---

## 一、有出处的核心要点（每条附来源 URL）

### 1. 把上下文当"有限资源"：目标是"最小高信号 token 集合"
Anthropic 官方工程博客将上下文工程定义为提示工程的演进：核心问题从"词句怎么写"变成"什么样的上下文配置最可能产生期望行为"。关键机制是 **context rot（上下文衰减）**——上下文窗口内 token 越多，模型准确召回信息的能力越低；Transformer 的 n² 成对关系与训练中短序列偏多共同导致"注意力预算"被摊薄。因此核心原则是：**找到最小的高信号 token 集合，以最大化期望结果的概率**（最小 ≠ 短，高信号才是标准）。
- 来源：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- 中文编译可对照：https://blog.csdn.net/qq_39903567/article/details/162908450

### 2. 系统提示词要落在"正确的高度"（right altitude）
Anthropic 指出要避开两个极端：**过低**（硬编码 if-else 式脆弱逻辑）与**过高**（模糊笼统、缺乏具体信号、错误假设共享上下文）。最佳高度=既具体到能引导行为，又灵活到能提供强启发式。建议用结构化分区（`<background_information>`、`<instructions>`、`## Tool guidance`、`## Output description`）或 XML 标签 / Markdown 标题划分；先用最优模型测极简提示，再按失败模式补指令与示例。
- 来源：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### 3. 工具（Tools）设计 = 与信息/行动空间的"契约"，宁少勿滥
工具必须**自包含、容错、用途明确**，参数应描述性强、无歧义。最常见失败模式是**工具集臃肿、功能重叠**，制造"该用哪个工具"的模糊决策点。判据：如果一个人类工程师都无法判断该用哪个工具，就不能指望 Agent 判断得更好。策展"最小可用工具集"更利于长期维护与上下文修剪。
- 来源：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### 4. Just-in-time（按需）检索 + 渐进式披露，优于"全部前置塞入"
趋势从"预推理嵌入全部数据"转向**即时检索**：Agent 只维护轻量标识符（文件路径、查询、链接），运行时用工具动态加载；文件名/目录层级/命名/时间戳等**元数据本身就是强信号**。配套手段是**渐进式披露（progressive disclosure）**——探索中逐层构建理解，只把必要内容留在工作记忆。混合策略（少量预加载 + 按需自主探索，如 CLAUDE.md + glob/grep）兼顾速度与灵活性。
- 来源：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### 5. 长任务的三种上下文工程手段：压缩 / 结构化笔记 / 子代理
- **Compaction（压缩）**：接近窗口上限时总结并重开窗口，保留架构决策、未解 bug、实现细节，丢弃冗余工具输出；调优顺序是"先最大化召回率，再提精度"。最安全轻量的形式是**工具结果清理（tool result clearing）**。
- **结构化笔记（agentic memory）**：Agent 定期把笔记持久化到窗口之外，之后再拉回；极低开销提供跨数十/千步的持久记忆（Claude 玩 Pokémon 案例）。
- **子代理架构**：主代理规划协调，子代理用干净上下文做深度探索，可能烧数万 token 但**只回传 1000–2000 token 的浓缩结论**。
选型：需要大量来回对话→压缩；有清晰里程碑的迭代开发→笔记；并行探索→多代理。
- 来源：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- 平台侧三种能力区分与 API 支持：https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools

### 6. Claude 5 新规则：删掉 80% 系统提示词，"规则"让位于"判断"
Anthropic 官方博客（2026-07）披露：为 Claude Opus 5 / Fable 5 重构 Claude Code 系统提示时**删除了 80%+ 内容且编码评测无可测量损失**，并把六条旧"最佳实践"列为已过时的迷思：①规则→判断（"写出与周围代码风格一致的代码"取代"绝不写注释"）；②给示例→设计接口（示例反而收窄探索空间，改在工具参数枚举上下功夫）；③全部前置→渐进式披露（拆 Skills、工具延迟加载）；④重复强调→简洁工具描述（去重）；⑤CLAUDE.md 手动记忆→自动记忆；⑥简单规格→丰富引用（HTML artifact、测试即 spec、rubrics）。
- 来源：https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models
- 第三方梳理（含落地到 CLAUDE.md 的建议）：https://www.developersdigest.tech/blog/context-engineering-claude-5-new-rules-2026

### 7. 官方工作流：先探索 → 再规划 → 再编码 → 提交（plan-then-execute）
Claude Code 官方最佳实践把"把研究和规划与实现分开"列为核心模式：**Plan Mode 先只读探索、再产出实现计划、经人批准后才写代码**，避免"解决了错误的问题"。官方还强调**给 Claude 可运行的验证闭环**（测试/构建/截图），让"看起来完成"变成可判定的 pass/fail；并提倡让 Claude **出示证据而非声称成功**。CLAUDE.md 要"精简到每一行都值得留"，判断标准是"删掉这行 Claude 会犯错吗？"不会就删。
- 来源：https://code.claude.com/docs/zh-CN/best-practices
- 四阶段工作流讲解：https://academy.claude.com/courses/claude-code-101/the-explore-plan-code-commit-workflow

### 8. Google 官方提示工程白皮书：10 条最佳实践
Google 68 页白皮书（Lee Boonstra，2025-02）给出可直接复用的十条：**给示例（few-shot）、保持简洁、具体化、指令优于约束（"告诉模型做什么"而非"不要做什么"）、控制 max token、用变量复用、试验不同写作风格、分类任务里混合类别、结构化输出（JSON）、以及 CoT/ToT/step-back/ReAct 等推理技巧**。同时区分 system prompt（大图景）与 context prompt（具体背景）。
- 来源（官方 API 文档）：https://googledevai-dot-devsite-v2-prod-3p.appspot.com/gemini-api/docs/prompting-strategies
- 中文全文：https://www.cnblogs.com/Chary/articles/19037230
- 10 点导读：https://www.yugatech.com/ar/news/google-publishes-10-step-prompt-engineering-guide-for-mastering-gemini-and-beyond/

### 9. 提示词模式的"有效性证据"：CoT 该用在哪、few-shot 为什么强
对开发者的实证总结：**few-shot 是"被低估的超能力"**——一个精心挑选的示例能同时传达格式、命名、详细度、异常处理等难以枚举的隐式约束；**CoT 应只用于真正多步的复杂问题**，Wharton 2025 研究显示显式 CoT 比直接请求慢 35%–600%，对默认已推理的模型增益有限；**任务分解 + 结构化 CoT（按顺序/分支/循环组织推理）** 对代码生成尤其有效。
- 来源：https://www.twocents.software/blog/prompt-engineering-for-developers

### 10. 个人 Agent 记忆系统：三层存储 + 写回循环 + 遗忘机制
工程实践共识是**记忆不是一个库，而是三类**：Profile（用户档案，KV，常驻提示）、Episodic（历史事件，向量检索 top-K）、Semantic（提炼事实/偏好，tag/graph）。**难点在写（何时记什么），不在读**：内联轻量抽取 + 异步整会话合并（write-back loop）；检索要叠加**时效衰减 + 多样性(MMR) + tag 过滤 + 相关性闸门**，而非裸余弦相似度；**遗忘是特性**（TTL、软删 30 天、按 tenant/user 命名空间隔离），跨租户泄漏必须在查询层强制。
- 来源：https://langchain-ai.github.io/langmem/concepts/conceptual_guide/
- 生产清单与失败模式：https://www.aiwisdom.dev/articles/agentic-systems/long-term-memory
- 中文三步自测/七步落地（LOCOMO 自测、TTL、命名空间隔离、记忆投毒防护）：https://ima.qq.com/wiki/?shareId=cfa978dc64382bd7a5a352007757d2870df7910632d432e3804d6ab8d2957f3f

### 11.（中文实践）四要素提示词 + 小步快跑 + 先想清楚再让 AI 写
中文社区高传播度的实践总结：提示词四黄金要素=**角色定位 / 完整上下文与硬约束 / 强制结构化输出 / 验收标准与"死亡红线"**；粒度铁律=**小步快跑**（宁写十个各产 150–300 行的小 Prompt，也不写一个产 5000 行需全重写的大 Prompt）；第一原则=**自己先想清楚再让 AI 写**，人始终是架构师+Review 组长+测试负责人。
- 来源：https://cloud.tencent.com/developer/article/2659177

### 12.（中文实践）Spec Coding 与"渐进式复杂度"
阿里系实践分享提出：**No Spec, No Code / Spec is Truth / Reverse Sync** 三条铁律；核心是**渐进式复杂度**——70% 是 ≤5 人日小需求，简单需求不应承担完整 spec+拆 tasks 的流程成本；用 `rules/`（常驻）+ `knowledge/`（按需加载索引）+ `changes/`（模板可迭代）组织上下文，并把 prompt/模板本身纳入 Git 版本迭代形成"知识飞轮"。
- 来源：https://cloud.tencent.com/developer/article/2659177 关联阿里妹导读分享（原文为公众号转载，此处为二手来源，建议以官方仓库/文档为准）

---

## 二、GitHub 高质量方法论/清单仓库（`curl https://api.github.com/repos/<owner>/<repo>` 实测）

实测命令：`curl -s https://api.github.com/repos/<owner>/<repo> | grep -E '"spdx_id"|"stargazers_count"|"pushed_at"|"archived"'`
（首次即成功，无需重试；`archived` 均为 `false`）

| 仓库 | stargazers_count | license (SPDX) | pushed_at | 定位 |
|---|---|---|---|---|
| dair-ai/Prompt-Engineering-Guide | **78,155** | MIT | 2026-03-11 | 提示工程/上下文工程最权威的社区教程清单（含 CoT、few-shot、RAG、Agent） |
| obra/superpowers | **284,110** | MIT | 2026-09-08 | Agent"技能/工作流"框架：把 brainstorming、writing-plans、executing-plans、requesting-code-review 做成**强制工作流**而非建议 |
| gsd-build/get-shit-done | **64,566** | MIT | 2026-05-31 | 严格 XML 标签结构化提示 + 强制流程的 Agent 框架 |
| coleam00/context-engineering-intro | **13,827** | MIT | 2026-03-16 | 面向 AI 辅助开发的上下文工程入门/编排模板（rules + 模板 + 多步特性开发） |
| Meirtz/Awesome-Context-Engineering | **3,298** | MIT | 2026-05-28 | arXiv《A Survey of Context Engineering for LLMs》配套清单（1400+ 论文分类） |
| natnew/Awesome-Prompt-Engineering | **109** | MIT | 2026-07-27 | 个人维护的提示/上下文工程资源合集（体量小、更新较勤） |

> 交叉验证：arXiv 综述正文本身列出了配套代码库 `https://github.com/Meirtz/Awesome-Context-Engineering`（来源：https://arxiv.org/html/2507.13334v1）。

---

## 三、共识做法 vs 营销话术

### ✅ 跨来源反复出现、可复现的"共识做法"
1. **上下文是有限的注意力预算**，"最小高信号 token"是统一目标（Anthropic、Claude Docs、Google、中文实践均指向此）。
2. **结构化输出 + few-shot + 显式约束**是提示层最稳定的增益项（Google 白皮书、Anthropic、实证文章一致）。
3. **先规划后执行（plan-then-execute / explore→plan→code→commit）**：官方文档、Claude Academy、中文 Spec Coding 都强调"先想清楚/先写 spec，再写代码"。
4. **给 Agent 一个可判定的验证闭环**（测试/构建/截图/exit code），把"看起来完成"变成 pass/fail。
5. **系统提示/CLAUDE.md 要精简**，"删掉这行会不会让模型犯错"是通用判据；规则让位于判断是 2026 年的明确趋势。
6. **记忆分层（profile/episodic/semantic）+ 按需检索 + 遗忘机制**是生产级 Agent 的共识架构。
7. **CoT 只用于真正多步的复杂任务**，对简单任务/已默认推理的模型可能只增成本（有 Wharton 等实证支撑）。

### ⚠️ 需要打折扣的"营销话术 / 未经证实断言"
1. **具体倍数承诺**：如"3×–5× 效率""10x better output""一个人干 3–5 个人的活"——无对照实验，属营销修辞，读者应只取方法、不信数字。
2. **夸大 star 数**：有二手文章称 obra/superpowers "接近 10 万 star"、get-shit-done "36,000+"，而 GitHub API 实测分别为 **284,110** 与 **64,566**（数值差异极大）。**凡涉及 star/热度，一律以 API 实测为准**，勿引用二次转述。
3. **人格化堆砌**：如"你是 12 年+ 前字节/阿里架构师 + 极致性能追求者"这类长人设，实证文章指出**上下文/约束比 persona 更能提升结果**，persona 更多是心理安慰而非稳定增益。
4. **"必须用某框架/某工具"的排他表述**：官方与严肃文章均主张"**做能起作用的最简单的事**"，先最小可用再按失败模式加机制；把可选流程当成强制前提属于过度工程。
5. **只讲收益不讲成本的清单**：如把"上三层记忆""上多代理"当默认动作，忽略其协调成本与存储浪费；理性做法是先自测痛点（记忆类可用 LOCOMO 风格问题自测），不合格才引入。
6. **把"压缩/更少 token"等同于"更好"**：Anthropic 明确指出目标不是"短"而是"高信号"，盲目压缩会丢微妙信息、降低准确率。

---

## 四、给中文全栈/AI 开发者的落地清单（基于上述共识，非营销）

1. **提示层**：默认采用"角色 + 完整上下文/硬约束 + 强制结构化输出 + 验收标准"四要素；只对多步复杂任务显式要求 CoT；优先用 1 个高质量示例而非大段规则。
2. **上下文层**：system prompt 落在"正确高度"，用分区标签；CLAUDE.md/规则文件保持精简，专业流程拆成按需加载的 Skill/文件树；工具集宁少勿滥、参数自解释。
3. **流程层**：一律走 explore→plan→code→commit；为每个任务定义可判定的验证标准，让 Agent 自证（出示测试/构建/截图证据）。
4. **记忆层**：先把 profile/episodic/semantic 分开；先跑通一个语义层，按真实指标再补；从第一天设计 TTL 与命名空间隔离。
5. **长任务**：对话密集用 compaction，里程碑清晰用结构化笔记，需并行探索用子代理（子代理只回传浓缩结论）。
6. **验证方法**：不迷信 star/倍数，用"任务成功率、可复现性、错误类型"三类指标衡量，而非 token 数或工具热度。

---

## 五、关键来源汇总（URL）

- Anthropic《Effective context engineering for AI agents》：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic《The new rules of context engineering for Claude 5》：https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models
- Anthropic Platform Cookbook（memory vs compaction vs tool clearing）：https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools
- Claude Code 官方最佳实践（中文）：https://code.claude.com/docs/zh-CN/best-practices
- Claude Academy 四阶段工作流：https://academy.claude.com/courses/claude-code-101/the-explore-plan-code-commit-workflow
- Google Gemini API 提示设计策略：https://googledevai-dot-devsite-v2-prod-3p.appspot.com/gemini-api/docs/prompting-strategies
- Google 提示工程白皮书（中文全文）：https://www.cnblogs.com/Chary/articles/19037230
- LangMem 长期记忆概念指南：https://langchain-ai.github.io/langmem/concepts/conceptual_guide/
- 生产级 Agent 长期记忆清单：https://www.aiwisdom.dev/articles/agentic-systems/long-term-memory
- 面向开发者的提示工程实证总结：https://www.twocents.software/blog/prompt-engineering-for-developers
- arXiv《A Survey of Context Engineering for LLMs》：https://arxiv.org/html/2507.13334v1
- 中文实践（AI 辅助编程指南）：https://cloud.tencent.com/developer/article/2659177

> OpenAlex / OpenAI 官方提示指南页面在本次检索中因 Cloudflare 拦截未能读取，故 OpenAI 侧以 Google/Anthropic 官方指南 + 实证二方文章替代；如需 OpenAI 一手文档，建议后续用可绕过的来源或 API 文档镜像补齐。
