# 调研笔记 3：AI 效率的工作流编排实践（实操向）

- 调研日期：2026-09-10
- 调研人：调研子代理
- 交付物：本文件（纯调研笔记，不含代码）
- **划界**：本笔记只谈"个人/团队层面的工作流实操与实证效果"。**不涉及**编排平台市场格局、产品对比、模型路由/供应商选型（该部分由今日另一份调研覆盖）。
- 检索轮次：中文 2 轮 + 英文 6 轮；权威原文用 WebFetch 读取（GitHub Blog、Anthropic 官方文档、METR 原始博客、DORA 官方洞察页、arXiv 摘要页、agents.md 官网、Kiro 官方/Builder Center）。

## 证据强度标注约定

| 标记 | 含义 |
|---|---|
| 【RCT】 | 随机对照试验，实测行为数据 —— 目前最硬的证据 |
| 【基准实测】 | 在受控基准（benchmark）上跑出来的可复现数据 |
| 【大样本自评】 | 数千人问卷，测的是**感知**而非实测耗时 |
| 【官方推荐】 | 工具厂商/项目官方给的最佳实践，**属于观点，未被独立验证** |
| 【实践观点】 | 一线开发者/技术博客的个案经验，n=1 居多 |
| 【反例】 | 明确与主流叙事相悖的证据 |

---

## 0. 一句话速览

1. **规格先行（SDD）与计划模式是当前最被主流采纳的编排骨架**，但其收益几乎全是"厂商/社区推荐"级别，**没有 RCT 级证据**证明它比"直接让 AI 写代码"更快。
2. **上下文文件（AGENTS.md/CLAUDE.md）被首次严格实证检验，结论与社区共识相反**：LLM 自动生成的上下文文件**平均降低任务成功率、并把推理成本抬高 20%+**；人类手写的仅有约 +4 个百分点的微弱提升，同时成本也涨约 19%。【基准实测】
3. **"AI 提速"的自我感知与实测严重脱节**：METR 的 RCT 里资深开发者实测**慢 19%**，但事前预测快 24%、事后仍认为快 20%。【RCT】
4. **2026 年 2 月 METR 更新了自己的结论**：新版实验因严重选择偏差"信号不可靠"，作者认为现在**很可能**已转为提速，但**证据很弱**，且该实验设计已被 METR 自己弃用。引用 METR 时必须带上这一条，否则是误读。
5. **真正被反复验证有效的工作流要素，是"闭环验证"而不是"生成更快"**：Anthropic 官方把"给 Claude 一个能产生 pass/fail 的检查"列为**第一实践**；DORA 则把代价说得很清楚——省下的写作时间被"验证税"重新花掉。

---

## 1. 规格驱动开发（Spec-Driven Development）

### 1.1 GitHub Spec Kit —— 最主流的开源骨架

来源：GitHub 官方博客（2025-01）
https://github.blog/2025-01-21-spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit
（中文全文译版见搜索结果转载；项目仓库 github.com/github/spec-kit）

- 官方定性（【官方推荐】原话）："我们不该把 coding agent 当搜索引擎，而该把它们当成**字面主义（literal-minded）的结对程序员**。它们擅长模式识别，但仍需要无歧义的指令。"
- 四阶段 + 阶段间检查点（上一个阶段验证通过才进入下一个）：
  1. **Specify**：只讲 what / why（用户旅程、成功标准），不讲技术栈 → 生成规格
  2. **Plan**：注入技术栈、架构、合规、性能约束 → 生成技术计划（可要求多套方案对比）
  3. **Tasks**：拆成"小的、可独立实现并测试"的单元，例如把"构建认证"拆成"创建校验 email 格式的注册端点"
  4. **Implement**：逐个（或并行）执行；开发者审**小而聚焦的 diff**，而不是上千行代码倾倒
- 配套 CLI：`uvx --from git+https://github.com/github/spec-kit.git specify init <PROJECT_NAME>`；Agent 内用 `/specify`、`/plan`、`/tasks` 驱动。
- 官方给的适用场景：绿地项目、存量项目加功能（N→N+1）、遗留系统现代化。
- 社区侧补充（【实践观点】，cnblogs / 腾讯云开发者社区文章）：后续版本增加了 `/speckit.constitution`（项目"宪法"）、`/speckit.clarify`、`/speckit.checklist`、`/speckit.analyze`、`/speckit.converge` 等命令，兼容 20+ 至 30+ 款 Agent。
  - 来源：https://www.cnblogs.com/erikqin/articles/22504222 ；https://cloud.tencent.com/developer/article/2656315
- **注意**：上述"错误率降低最高 50%"之类的数字来自二手文章转述的 arXiv 论文，本次未追溯到原始论文，**不作为证据引用**。

### 1.2 Kiro（AWS）—— 把"规格"做成 IDE 的一等公民

来源：Kiro 官网 https://kiro.dev/ ；AWS Builder Center https://builder.aws.com/content/3GW3k3TdjL0Uy5iV3fYt4NWgfTV/7-things-you-didnt-know-about-amazon-kiro ；AWS 官方案例 https://aws.amazon.com/blogs/industries/from-spec-to-production-a-three-week-drug-discovery-agent-using-kiro/

- 三段式产物（【官方推荐】，均为 Markdown，落盘在 `.kiro/specs/`）：
  - `requirements.md`：用户故事 + **EARS 记法**验收标准（`WHEN 条件 THE SYSTEM SHALL 响应`）→ 可机器读、可直接转成测试
  - `design.md`：时序图、数据模型/接口定义、DB schema 变更、错误处理策略、测试策略
  - `tasks.md`：带依赖标注的可执行任务表；Kiro 由依赖图自动识别**可并行任务**并分组并发执行
- **阶段间强制人工审批关卡**：需求关（以产品负责人视角审）、设计关（技术负责人视角）、任务关（项目经理视角）。这是"计划先行"里少见的、被产品化强制化的做法。
- `bugfix` 规格的三段式（对"回归防护"很有参考价值，【官方推荐】）：
  - 当前行为（缺陷）→ 期望行为（修复目标）→ **不变行为（回归护栏，`SHALL CONTINUE TO`）**
  - 决策规则简单：这个修复会不会弄坏别的东西？会，就必须写"不变行为"
- `steering files`（`.kiro/steering/`：product.md / tech.md / structure.md）回答"我们在建什么 / 用什么工具 / 代码怎么组织"，随 Git 走，等价于"上下文即代码 + 新人 onboarding as code"。
- AWS 官方给的落地案例（【实践观点/厂商案例】，**无独立复核**）：
  - 药物靶点识别 Agent：3 名开发者 3 周做到生产可用
  - 转述 Rackspace 案例：52 周预估工作量压缩到 3 周，效率 +90%
  - **这类数字是厂商案例，不能当实证证据使用。**

### 1.3 SDD 的已知代价与失败模式（反证）

来源：Agent Patterns https://agentpatterns.ai/workflows/spec-driven-development/

【实践观点】该文同时给出 SDD 的结构性风险，值得记录：

- **"写规格可能比直接写代码更难"**：把需求写到 Agent 能用的精度，本身就可能是主要工作量。
- **编译随规格增长而变慢**：大规格文件吃上下文窗口，需要拆成按子系统划分的多文件。
- **规格漂移是首要失败模式**：静态规格与代码脱同步后，**Agent 会自信地按过时计划执行且不会报警**，比误导人类更危险（引 Augment Code, 2026）。
- **JSON 比 Markdown 更适合做机器可读的状态跟踪**：转述 Anthropic harness 研究称模型更不容易错误修改 JSON。
- 适用性判断：SDD 在"需求复杂到中途丢上下文是主要失败模式"的项目上收益最大，简单任务上是纯开销。

---

## 2. 项目级上下文文件约定（AGENTS.md / CLAUDE.md / .cursorrules）

### 2.1 AGENTS.md —— 跨工具的事实标准

来源：官网 https://agents.md/ ；Red Hat Developer https://developers.redhat.com/articles/2026/07/27/standardize-project-context-agentsmd-and-agent-skills

- 【事实（官网自述）】已被 **60,000+ 开源项目**采用；由 OpenAI Codex、Amp、Google Jules、Cursor、Factory 等协作发起，现由 **Linux Foundation 下的 Agentic AI Foundation** 托管。
- 定位：**"给 Agent 看的 README"**，与 README.md 分工——README 给人，AGENTS.md 给 Agent（构建步骤、测试命令、约定、坑点）。
- 关键机制：
  - **嵌套就近优先**：Monorepo 里每个子包可放自己的 AGENTS.md，Agent 读**目录树上最近的那个**，就近文件覆盖上层；用户聊天中的显式指令覆盖一切。
  - 文中示例：OpenAI 主仓库有 **88 个** AGENTS.md 文件。
  - Aider 配置：`.aider.conf.yml` 里 `read: AGENTS.md`；Gemini CLI：`.gemini/settings.json` 里 `{"context": {"fileName": "AGENTS.md"}}`。
  - Claude Code 不原生读 AGENTS.md，**变通办法**：建 `CLAUDE.md`，内容只写一行 `@AGENTS.md`，再在下方追加 Claude 专属指令。
- 官方不要求必填字段：就是普通 Markdown，任意标题都可。

### 2.2 CLAUDE.md —— 官方口径是"越短越好"

来源：Anthropic 官方 Claude Code Best Practices（经重定向）https://code.claude.com/docs/en/best-practices

- 【官方推荐】直引："对每一行问自己：**删掉它会导致 Claude 犯错吗？**如果不会，就删掉。臃肿的 CLAUDE.md 会让 Claude 忽略你真正的指令！"
- 硬性约束前提（官方原话）："大多数最佳实践都基于一个约束：**Claude 的上下文窗口会很快填满，而性能随填充而下降。**"
- 明确列出的 **不该写** 内容：Claude 读代码就能搞清楚的东西、标准语言约定、详细 API 文档（改为链接）、频繁变化的信息、逐文件的代码库描述、"写干净代码"这类自明实践。
- **该写**：Claude 猜不到的 Bash 命令、与默认不同的风格规则、测试指令与首选 runner、仓库礼仪（分支命名/PR 约定）、项目特有架构决策、环境怪癖、常见坑点。
- 两个高价值运营手法：
  - **调试信号**：Claude 持续做你不想要的事 → "文件可能太长了，规则正在被淹没"；Claude 问文件里已答过的问题 → "措辞可能含糊"。
  - **强调技巧**：只给**单行**加 `IMPORTANT`；多行都加等于都没加。
  - 已签入的 CLAUDE.md 可跑 `/doctor`，让 Claude 提议删除"能从代码库推导"的内容。
  - **领域知识/偶发工作流应移到 Skills**（按需加载，不污染每次对话）。
- 社区量化的经验值（【实践观点】）：Addy Osmani 建议 **≤150 行**，小仓库 30–50 行足够，"比 README 还长就是太长了"（https://addyosmani.com/agents/15-agents-md/）；Red Hat 同口径，并给出每行的判据——"删掉这行，Agent 会犯一个它本来不会犯的错吗？不会就删"。
- 团队实践提醒（Red Hat，【实践观点】）：不要重复维护 CLAUDE.md / GEMINI.md / AGENTS.md 多份，用 AGENTS.md 做公共分母；**init 自动生成的上下文文件不要原样提交**，要人工删掉模型自己能推断的通用信息。

### 2.3 ★ 反证：ETH Zurich 的首次严格实证（本笔记最重要的一节）

来源（原文）：arXiv:2602.11988 *Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?*（v1 2026-02-12，v2 2026-06-23）
https://arxiv.org/abs/2602.11988
解读：InfoQ https://www.infoq.com/news/2026/03/agents-context-file-value-review/ ；The Decoder https://the-decoder.com/?p=32204

**这是"实测证据"，不是观点。**

- 设计：自建基准 **AGENTbench**（138 个来自 12 个**冷门** Python 仓库的真实 GitHub issue，仓库本身**自带开发者手写的上下文文件**，刻意避开 SWE-bench 的记忆污染）+ SWE-bench Lite 交叉验证；4 个 Agent（Claude Code/Sonnet 4.5、Codex/GPT-5.2、GPT-5.1 mini、Qwen Code）；三种条件：**无上下文文件 / LLM 生成 / 开发者手写**。
- 论文摘要原文结论（最可靠表述）："**提供上下文文件一般并不能提升任务成功率，同时平均把推理成本抬高 20% 以上**。该观察在多个 LLM、多个 coding agent、以及 LLM 生成与开发者提交两类文件上都成立。"并指出：**仓库概览（repository overview）虽流行且被模型厂商推荐，但无用**。
- 拆分数字（来自 InfoQ / The Decoder / Engineer's Codex 的一致转述，**作为二手数据标注**）：
  - LLM 生成文件：成功率平均 **-3%**（相比完全不给上下文），8 个测试设置里 5 个变差；成本 **+20~23%**
  - 开发者手写文件：成功率平均 **+4%**，但成本 **+19~20%**
  - 论文摘要的口径更保守，只说"generally does not improve"（不普遍提升）
- **机制（最有价值的部分）**：不是 Agent 无视文件，而是**Agent 太听话**。
  - 文件提到 `uv`，Agent 每实例用 1.6 次；没提到时几乎不用 → 说明指令被严格执行。
  - 但结果是**跑更多测试、读更多文件、更多 grep、更多质量检查**，而**"到相关文件的时间"并没有变快**。论文原话大意：多余的要求让任务变难了。
  - LLM 生成的文件大多与仓库已有文档**重复冗余**；只有在把仓库所有文档都删掉时，LLM 生成文件才转为 +2.7% 并优于手写文件 → **解释了为什么有些人觉得它有用**（新/冷门/无文档仓库正是标准基准不覆盖的场景）。
- 作者建议（可直接落地）：**整体跳过 LLM 自动生成的上下文文件**（包括 Claude Code `/init`、Codex、Qwen Code 的 init 命令产物）；若手写，**只写不可推断的工具链要求**（用 uv 不用 pip、自定义测试 runner 之类），**代码库架构概览不要写**。
- **边界**：论文自承只测了有限 Agent 与仓库集合，不能外推到所有工作流。另一条对照（The Decoder 转述）：Vercel 在"教 Agent 最新 Next.js 框架知识"这一**训练数据里没有**的场景下，持久上下文收益显著——两者不矛盾，**上下文文件的价值仅限于填补模型真正不知道的东西**。

---

## 3. 计划先行 / 子代理并行 / 审查回路

### 3.1 Anthropic 官方工作流（最系统的实操清单）

来源：https://code.claude.com/docs/en/best-practices 【官方推荐】

**(a) 验证闭环是第一实践**（直引）：

> "Claude 在工作**看起来**完成时就会停止。没有可运行的检查时，'看起来完成'是唯一可用的信号，而**你自己就成了验证循环**。给 Claude 一个能产生 pass/fail 的东西，这个循环就会自行闭合。"

- 可用的验证信号：测试套件、构建退出码、linter、与 fixture 对比的脚本、与设计稿对比的浏览器截图。
- 验证强度分四级：单次提示内自检 → 会话级 `/goal` 条件（独立评估器每轮复检）→ 确定性门禁（Stop hook 阻塞回合结束）→ **第二意见（全新 subagent 反驳）**。
- 明确要求："让 Claude **展示证据**而不是宣称成功：测试输出、它跑的命令和返回值、或结果截图。"
- **对抗性审查**（重要细节）：让审查者在**全新 subagent 上下文**里运行，它只看得到 diff 和验收标准，**看不到产生这次修改的推理过程**，因此能按自己的标准评估结果。
- 反过度工程警告（直引大意）："被要求找问题的审查者通常总能报出一些问题，即使工作是扎实的……逐条追每一条发现会导致过度工程。**告诉审查者只标记影响正确性或既定要求的问题**，其余视为可选。"

**(b) 探索→计划→写码→提交 四阶段**（对应 SDD 的轻量版）：

> "让 Claude 直接跳到写代码会产出**解决错误问题**的代码。用 plan mode 把探索和执行分开。"

- 流程：`Shift+Tab` 进 plan mode（只读）→ 让 Claude 出计划（`Ctrl+G` 可直接在编辑器改计划）→ 退出 plan mode 实现 → 提交。
- **但官方也明确说了何时该跳过计划**（这是多数"计划模式"布道文忽略的）：
  - "范围清楚、修复很小"（改错别字、加一行日志、改变量名）→ 直接做
  - **"如果你能用一句话描述这个 diff，就跳过计划。"**

**(c) 上下文管理（官方称为最重要的资源）**：

- `/clear` 在**不相关任务之间重置上下文**——"频繁使用"。
- **两次纠错法则**（直引）："如果你在同一个会话里针对同一问题**纠正过 Claude 超过两次**，上下文就被失败尝试污染了。跑 `/clear` 重新开始……**一个干净会话配更好的提示，几乎总能胜过带着累积修补的长会话。**"
- `/compact <instructions>` 定制压缩重点；可在 CLAUDE.md 里写 `"压缩时始终保留完整修改文件列表和测试命令"`。
- `/btw` 用于不需要留在上下文里的提问。
- 回退：`Esc` 停、`Esc+Esc`/`/rewind` 打开检查点菜单。**警告**：检查点只跟踪 Claude 文件编辑工具做的改动，**Bash 命令或外部进程的改动不记录**，"不能替代 git"。

**(d) 子代理（subagent）**：

> "既然上下文是你的根本约束，就用 subagent 把调研挡在主上下文之外……子代理跑在独立上下文窗口里，**只回报摘要**。"

- 典型用法："用 subagent 调查我们的认证系统如何处理 token 刷新，以及有没有可复用的 OAuth 工具。"
- 自定义子代理放在 `.claude/agents/`，独立上下文 + 各自允许的工具集（示例 `security-reviewer` 限定 `Read, Grep, Glob, Bash`）。

**(e) 并行与 writer/reviewer 模式**：

- 隔离手段：**git worktrees**（各自独立 checkout，避免编辑冲突）、跨会话消息、桌面 App 多会话、`claude agents` 后台派发、实验性 agent teams。
- **Writer/Reviewer 双会话模式**：A 实现 → B 在干净上下文里审查 → 把 B 的反馈交回 A 修正。官方理由："**全新上下文能改善代码审查，因为 Claude 不会偏向自己刚写的代码。**"
- **Fan-out 批量**：仓库内 `/batch <instruction>`，把改动拆给 5–30 个 subagent，各自在独立 worktree 工作并开 PR；或脚本循环 `claude -p "..." --allowedTools "Edit,Bash(git commit *)"`。建议"先在少数文件上试，再全量跑"。
- 非交互模式 `claude -p` 用于 CI / pre-commit hook / 自动化。

**(f) 官方自己总结的 5 个失败模式**（极有参考价值）：

| 失败模式 | 表现 | 修复 |
|---|---|---|
| Kitchen sink session | 多任务混在一个会话，上下文被无关信息塞满 | 不相关任务间 `/clear` |
| 反复纠错 | 修补污染上下文 | 两次纠错失败就 `/clear`，重写更好的初始提示 |
| CLAUDE.md 过度指定 | 文件太长，重要规则被淹没 | 无情删减；已做对的改成 hook |
| Trust-then-verify gap | 代码看着合理但没处理边界 | **始终提供验证；无法验证就不要发布** |
| 无限探索 | 无范围的"调查"读几百个文件 | 限定范围或用 subagent |

### 3.2 社区侧的"计划→拆票→执行"套路（实践观点，非证据）

来源：https://howtoclaude.dev/?p=431/ ；https://zencoder.ai/blog/claude-code-parallel-agents ；https://readerfi.com/discover/68839 ；https://dev.to/galian/claude-code-workflow-best-practices-that-ship-code-na

【实践观点】多处独立出现的同一套节奏，值得作为"社区共识"记录（**注意：全部无对照实验，属经验总结**）：

1. **PLAN 阶段**：先描述高层目标，明确要求"先不要写代码"，要一份需求/架构分析 → 在昂贵的实现前捕获逻辑错误。
2. **TASK CREATION 阶段**：让 Agent "创建实现整个计划所需的票据"，把模糊想法变成结构化可执行清单。
3. **EXECUTE 阶段**：派发 subagent 并行执行，用测试发现 bug，"不完成不要停"。
4. **Explore / Plan / Execute 三分**：探索用**便宜模型**（如 Haiku，比 Opus 便宜约 15 倍）跑只读工具，把**人工审批关卡放在"改文件之前"**这一个点。
5. 反复被强调的**常见错误**：
   - subagent 描述含糊（"帮忙改代码"永远路由不对）→ 必须写清触发条件
   - 工具权限过宽（只读研究型 subagent 给了 write/bash，隔离保证就没了）
   - **把有依赖关系的任务并行化**（B 需要 A 的产出就必须串行）
   - 用 subagent 干琐事（格式化 JSON、跑一条命令）
6. **文件锁 / 边界约定**：多个 Agent 同改一个文件会出事；社区做法是在 CLAUDE.md 里声明每个 Agent 的文件所有权（`Owns: /src/app/api/**`）、用 `.claude/locks/` 加锁、用 `progress.md` 做阶段进度板。这些是**手工约定，不是工具保证**。

### 3.3 反面：并行的代价与"验证税"

- 【大样本自评/质性】DORA 2025 直引工程师原话：
  - "我感觉效率高了些，但**是有代价的**。我写代码的时间少了，却花更多时间**'看管' AI 并审查它在干什么**。"
  - "**审别人的代码比写代码难得多**。AI 工具正在提高人们产出待审代码的速率……"
  - "AI 工具提高了我的生产力，写得比我快，但**代码质量（目前）不如我自己写的**。"
  - 来源：https://dora.dev/insights/balancing-ai-tensions/
- 结论（该页原话）：AI 加速了初始代码生成、降低了启动阻力，但**"创作时省下的时间经常被重新分配到审计与验证上"**；且**作者侧的速度提升，往往转化为审查者侧认知负荷的显著上升**。

---

## 4. 真实生产力研究证据（正反两面）

### 4.1 METR 2025 RCT —— 最硬的负面证据

原文：https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ （2025-07-10）
（注意：该页顶部现已标注 **"These results are out of date"**，见 4.2）

**准确转述（【RCT】，务必按此口径引用）：**

- **设计**：随机对照试验（RCT）。**16 名**资深开源开发者，在**他们自己长期贡献的仓库**上完成 **246 个真实 issue**（平均每个任务约 2 小时）。仓库平均 **110 万+ 行代码、约 10 年历史**；参与者平均 5 年项目经验、1,500 次 commit。时间：2025 年 2–6 月。主要工具：**Cursor Pro + Claude 3.5 / 3.7 Sonnet**（当时的前沿模型）。任务随机分为"允许 AI"与"禁止 AI"两组。
- **核心结果**：允许用 AI 时，**完成时间多 19%**（即变慢）。论文原句："we find that when developers use AI tools, they take 19% longer than without—AI makes them slower."
- **感知落差（最惊人的部分）**：
  - 事前预测：AI 让自己**快 24%**
  - 事后自评：仍然认为 AI 让自己**快 20%**
  - ML 专家预测加快 **38%**，经济学专家预测 **39%**
  - 论文结论："当人们报告 AI 加速了自己的工作，**他们可能是错的**。"
- **行为数据**：AI 建议的**接受率低于 44%**；**56%** 的开发者在采纳后仍需**大改**；约 **9%** 的任务时间花在审查和清理 AI 产出上。开发者报告 AI "在代码其他部分做了一些奇怪的改动，我花时间找出来删掉"。
- **论文列出的 5 个可能成因**：对 AI 有用性的过度乐观、开发者对本仓库的高度熟悉、仓库大且复杂、AI 可靠性低、**隐性的仓库上下文**（资深开发者依赖没写下来的知识，AI 拿不到）。
- **作者明确的"不主张"清单（必须一并转述，否则是断章取义）**：不主张"AI 目前不能加速多数软件开发者"；不主张其开发者/仓库代表主流软件开发；不主张 AI 在其他领域无效；不主张未来不会提速；也不主张**不存在**在同样场景下用得更有效从而获得正速的方法。
- 补充（TechCrunch，二手）：研究中 **94%** 的开发者此前用过网页版 LLM，但只有 **56%** 用过 Cursor；研究前有做 Cursor 培训。

### 4.2 ^ METR 2026-02 的自我修正（引用 METR 时必须带上）

原文：https://metr.org/blog/2026-02-24-uplift-update （2026-02-24）【RCT，但作者自称"不可靠信号"】

- 2025 年 8 月起做新实验：**10 名原班 + 47 名新招 = 57 名**开发者、**143 个仓库**、800+ 任务；报酬从 $150/hr 降到 **$50/hr**。
- 结果：
  - 原班开发者子集：估计**提速 18%**（论文写作口径为 "a speedup of -18%"，即任务时间 -18%），**CI 为 -38% ~ +9%**
  - 新招开发者：估计提速 **4%**，**CI 为 -15% ~ +9%**
  - **两个置信区间都跨过 0，均不显著。**
- **METR 自己判定数据不可靠**，原因：
  1. **选择偏差**：大量开发者拒绝参加（不愿 50% 的工作不用 AI），甚至**拒绝提交**部分任务——**30%~50% 的人说"我不想在没 AI 的情况下做这些任务"**，导致系统性地漏掉了"AI 收益最高"的开发者和任务，**把估计往下压**；
  2. 报酬降低（$150→$50）加剧了选择效应；
  3. 部分开发者**同时跑多个 AI agent**，导致"耗时"测量不可靠。
- METR 的措辞（原话大意）："我们认为**开发者在 2026 年初很可能确实比 2025 年初被 AI 加速得更多**，但由于选择效应，我们的数据只是**非常弱的证据**。"并且**该实验设计已被弃用**，团队正在改设计。
- **给引用者的纪律**：写"METR 证明 AI 拖慢开发者"是**不准确**的；准确说法是——"METR 2025 的 RCT 在**特定场景（资深开发者在自己的成熟仓库）**测到 19% 的减速；2026 年的后续实验因选择偏差**未能给出可信的提速幅度**，作者倾向于认为现已转为提速但证据薄弱。"

### 4.3 DORA（Google）2025 —— 大样本、测感知与交付结果

原文：https://blog.google/technology/developers/dora-report-2025 ；官方洞察页 https://dora.dev/insights/balancing-ai-tensions/ ；数据解读 https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025/

【大样本自评 + 质性分析，n≈5,000 人 + 100+ 小时访谈 + 1,110 条 Google 工程师开放式回答】

- **采用率**：**90%** 技术从业者在工作中使用 AI（2024 年为 76%）；中位数**每天 2 小时**；65% 属于"重度依赖"。
- **主观收益**：**>80%** 认为 AI 提升了生产力；**59%** 认为对代码质量有正面影响。
- **信任悖论**：仅 24% 表示"大量/很多"信任 AI 产出；**30% 表示"很少"或"完全不信"**。官方解读：这说明 AI 是被当作**辅助工具**而非人类判断的替代品。
- **交付结果（这是关键矛盾点）**：2025 年报告发现 **AI 采用率上升同时伴随"交付吞吐量上升 + 交付不稳定性上升"**。较 2024 年"吞吐下降"已转为正向，但**稳定性问题仍在上升**；报告检查了"快速失败快速修复"能否抵消，**结论是不能**。
- **"放大器"结论（原话）**："AI 在软件开发中的主要角色是**放大器**。它放大高绩效组织的优势，也放大挣扎组织的功能障碍。"有高质量内部平台/API/流程/测试的团队，AI 是强协作者；工具割裂、数据孤岛的团队，**AI 只是帮他们更快地生产技术债**。
- **验证税（原话）**：AI 加速了初始生成，但**"创作时省下的时间常被重新分配到审计与验证上"**，因为 AI **无法标示自己的不确定性**，工程师被迫把每次交互都当成可能具有欺骗性。
- **DORA AI 能力模型（7 项，面向组织而非个人工具）**：明确的 AI 政策/立场；健康的数据生态；AI 可访问的内部数据；**强版本控制实践**；**小批量工作**；以用户为中心；高质量内部平台。
- 对比数据（**二手转述，标注来源**）：InfoWorld 文章引 DORA 2024 报告称"AI 采用率每提高 25%，交付速度下降 1.5%、系统稳定性下降 7.2%"，并称 39% 受访者对 AI 生成代码"几乎不信任"。来源：https://www.infoworld.com/article/4020931/ai-coding-tools-can-slow-down-seasoned-developers-by-19.html —— **该数字来自 2024 年报告，与 2025 年报告的"吞吐转正"结论方向不同，引用时须注明年份。**

### 4.4 被广泛引用但需谨慎的旁证（未在本次调研中追溯到一手）

以下数字在多个二手文章中出现，**本次未核实原文，仅作线索记录，不建议直接引用**：

- Faros AI（2025，10,000+ 开发者 / 1,255 团队）：高 AI 采用团队合并 PR 数 **+98%**、完成任务 **+21%**，但 **PR 审查时间 +91%、PR 体积 +154%、bug +9%**。
- GitClear（2024–2025，2.11 亿行改动）：代码克隆占比 8.3%→12.3%；两周内被修改的新代码 3.1%→5.7%；重构占比从 25% 降到 <10%。
- 来源：https://www.birjob.com/blog/metr-study-ai-tools-experienced-developers-19-percent-slower
- 说明：这些数据如果成立，恰好共同指向同一个机制——**瓶颈从"写代码"迁移到"审查与集成"**（Amdahl 定律视角：若写码只占交付总时间的 30%，写码快 50% 只带来约 15% 的整体提升）。

---

## 5. 正反对照：哪些做法被证明有效，哪些是幻觉

| 做法 | 证据性质 | 结论 |
|---|---|---|
| 给 AI 一个可运行验证（测试/lint/构建/截图） | 【官方推荐】+【RCT 机制一致】 | **正**：METR 的减速成因之一正是"AI 建议方向对但不对焦"，需要人补审；闭环验证把这段成本压回机器 |
| 计划先行 / 计划模式 | 【官方推荐】+【实践观点】 | **有条件正**：大任务收益明确（避免解决错误问题）；**一句话能描述 diff 的任务上跳过** |
| 子代理做调研、主上下文只收摘要 | 【官方推荐】+【实践观点】 | **正**：直接对抗"上下文填满即降级"这一唯一硬约束 |
| 用全新上下文的第二意见做代码审查 | 【官方推荐】 | **正**：机制清晰（不受自己推理的偏向）；但要**限制只报影响正确性的问题**，否则过度工程 |
| 手写、极简、只写不可推断信息的上下文文件 | 【基准实测】ETH Zurich | **弱正**：+4 个百分点成功率，但 +19% 成本；仓库概览类内容**无用** |
| LLM 自动生成上下文文件（`/init` 产物） | 【基准实测】ETH Zurich | **负**：平均 -3% 成功率、+20%+ 成本，与仓库已有文档冗余。作者建议**整体跳过** |
| "AI 让我更快"的自我感知 | 【RCT】METR | **幻觉**：实测 -19%，感知 +20%，落差约 39 个百分点；ML/经济学专家预测误差更大 |
| 把 AI 生成速率直接等同于交付速率 | 【大样本自评】DORA + 旁证 | **幻觉**：吞吐上去了，**不稳定性同步上升**；瓶颈迁移到审查/集成/QA |
| 并行多个 Agent 提高产出 | 【实践观点】+ DORA 质性 | **有条件的正**：独立任务 + 独立 worktree 有效；**有依赖关系的任务并行会坏**；审查端会先饱和 |
| 规格驱动开发（SDD）整体 | 【官方推荐】+【实践观点】 | **有效但未经严格验证**：无 RCT/基准证明其净收益；已知代价是规格编写成本、编译变慢、**规格漂移会误导 Agent** |

---

## 6. 给个人开发者的可执行工作流建议（5 条）

1. **先搭"验证闭环"，再谈提速。**
   在写第一行 prompt 前，确保项目里有能给出 pass/fail 的东西：能跑的测试、lint、构建、或一个截图对比脚本。Anthropic 官方把它列为第一实践，不是因为它先进，而是因为**没有它，瓶颈就是你本人**。对没有测试的存量项目，先让 AI 补一层最小回归测试，再让它改代码。

2. **把上下文文件砍到 30–60 行，只写模型推断不出来的东西。**
   依据 ETH Zurich 的实测反证，**删掉 `/init` 生成的内容，不要提交**。保留：非常规构建/测试命令、非默认风格规则、"不要动这里"的禁区、以及会导致静默失败的隐性约束。把"项目架构概览""目录说明"删掉。领域知识放 Skills 或独立文档，用一行链接指向即可。

3. **计划模式用在"一句话说不清 diff"的任务上；其余直接做。**
   对小改动（改名、加日志、改错字）跳过计划——Anthropic 官方明确这么说。对大改动，走"探索 → 计划 → 批准计划 → 实现"四步，审批点放在**改文件之前**。要审查的是**计划**而不是 diff：计划错了改一句话，diff 错了要拆 300 行。

4. **用子代理隔离噪音，用全新上下文的第二意见做审查；上下文用完就清。**
   调研、找文件、读日志这类高噪音只读工作交给便宜模型的 subagent，主会话只收摘要。审查用另一个干净会话（Writer/Reviewer 双会话），并明确要求"只报影响正确性或既定要求的问题"。**同一问题纠正超过两次就 `/clear` 重开**——干净会话配好提示，胜过带一堆补丁的长会话。

5. **用自己的耗时做度量，不用自己的感觉做度量。**
   METR 的教训是自我评价可以偏差 39 个百分点。个人可执行的最低成本做法：对你**重复出现的几类任务**（写 CRUD 接口、修 bug、写测试、重构）记录"开干到提交"的实际分钟数，连续记 2–4 周，AI 用/不用各留一段对照。如果某类任务确实没变快，就按 DORA 的"放大器"逻辑接受它——**你的收益更可能出现在"降低启动阻力"和"减少枯燥度"，而不是"总时间变短"**。别为了感知上的爽感，把审查和调试的债留给自己。

---

## 7. 参考来源清单

**规格驱动开发**
1. GitHub Blog（官方）：Spec-driven development with AI: Get started with a new open source toolkit — https://github.blog/2025-01-21-spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit
2. GitHub Spec Kit 仓库 — https://github.com/github/spec-kit
3. Kiro 官网 — https://kiro.dev/
4. AWS Builder Center：7 Things You Didn't Know About Amazon Kiro — https://builder.aws.com/content/3GW3k3TdjL0Uy5iV3fYt4NWgfTV/7-things-you-didnt-know-about-amazon-kiro
5. AWS Builder Center：Kiro – The Complete Guide for Teams — https://builder.aws.com/content/39juiKF2uwxhek0RuYHhjf24JjL/kiro-the-complete-guide-for-teams
6. AWS Blog（厂商案例）：From spec to production: a three-week drug discovery agent using Kiro — https://aws.amazon.com/blogs/industries/from-spec-to-production-a-three-week-drug-discovery-agent-using-kiro/
7. Agent Patterns：Spec-Driven Development with Spec Kit（含 trade-offs 与规格漂移风险） — https://agentpatterns.ai/workflows/spec-driven-development/
8. Microsoft Dev Blogs：Diving Into Spec-Driven Development With GitHub Spec Kit — https://devblogs.microsoft.com/?p=19925/
9. 中文：GitHub Spec Kit 用"先写规格后写代码"重新定义 AI 辅助开发 — https://www.cnblogs.com/erikqin/articles/22504222
10. 中文：AI 辅助编程与 AI Specs 实战：2026 年最新最全进展详解（OpenSpec / Spec Kit / Kiro 对比） — https://cloud.tencent.com/developer/article/2656315

**上下文文件**
11. AGENTS.md 官网 — https://agents.md/
12. Anthropic 官方：Claude Code Best Practices — https://code.claude.com/docs/en/best-practices
13. Red Hat Developer：Standardize project context with AGENTS.md and Agent Skills — https://developers.redhat.com/articles/2026/07/27/standardize-project-context-agentsmd-and-agent-skills
14. Addy Osmani：Lesson 15 – AGENTS.md — https://addyosmani.com/agents/15-agents-md/
15. ★ ETH Zurich 论文（一手）：Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents? — arXiv:2602.11988 — https://arxiv.org/abs/2602.11988
16. InfoQ 解读 — https://www.infoq.com/news/2026/03/agents-context-file-value-review/
17. The Decoder 解读（含 Vercel 对照） — https://the-decoder.com/?p=32204
18. Engineer's Codex 解读（含分项数字） — https://engineerscodex.com/agents-md-making-ai-worse

**计划模式 / 子代理 / 审查回路**
19. Anthropic 官方 — 同 12
20. How to Claude Code：The Rise of the Specialist — https://howtoclaude.dev/?p=431/
21. Zencoder：How to Efficiently Use Claude Code Parallel Agents — https://zencoder.ai/blog/claude-code-parallel-agents
22. Readerfi：Claude Code Subagents: Setup, Config, and When to Use Them — https://readerfi.com/discover/68839
23. dev.to：Claude Code Workflow: Best Practices That Ship Code — https://dev.to/galian/claude-code-workflow-best-practices-that-ship-code-na
24. 中文：2026 Claude Code 工作流最佳实践 — https://blog.ccino.org/p/claude-code-workflow-best-practices-2026/

**生产力实证**
25. ★ METR 2025 RCT（一手） — https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/
26. ★ METR 2026-02 更新/自我修正（一手） — https://metr.org/blog/2026-02-24-uplift-update
27. Google Blog：DORA 2025 Report — https://blog.google/technology/developers/dora-report-2025
28. DORA 官方洞察页：Balancing AI tensions — https://dora.dev/insights/balancing-ai-tensions/
29. InfoQ：DORA Report Finds AI Is an Amplifier — https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025/
30. TechTarget：Google DORA – Software delivery caught up to AI coding tools — https://www.techtarget.com/it-infrastructure/news/366631712/Google-DORA-Software-delivery-caught-up-to-AI-coding-tools
31. InfoWorld：AI coding tools can slow down seasoned developers by 19% — https://www.infoworld.com/article/4020931/ai-coding-tools-can-slow-down-seasoned-developers-by-19.html
32. TechCrunch：AI coding tools may not speed up every developer — https://techcrunch.com/2025/07/11/ai-coding-tools-may-not-speed-up-every-developer-study-shows/
33. InfoQ：AI Is Amplifying Software Engineering Performance（2025 DORA） — https://www.infoq.com/news/2026/03/ai-dora-report/

---

## 8. 未解决 / 待验证事项

1. Spec Kit 提到的"基于精炼规格，LLM 生成代码错误率降低最高 50%"——**未追溯到原始 arXiv 论文**，暂不采信。
2. ETH Zurich 论文的分项数字（-3% / +4%）来自二手解读，一手摘要口径为"generally does not improve"，建议后续补读 PDF 正文核对表 1。
3. Kiro 的"52 周→3 周""效率 +90%"为厂商案例，无第三方复核。
4. Faros AI / GitClear 的组织级数据未追溯到一手报告。
5. METR 新实验设计（2026 年 2 月后）是否会给出可信的提速上限，值得在下一轮调研跟进。
