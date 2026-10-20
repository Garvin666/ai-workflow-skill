# 技能库索引（由 `gen_skill_index.py` 自动生成，请勿手改）

<!-- 出站脱敏：本快照中的本机用户名已替换为 <用户名> 占位符（2026-10-20 推送前），其余字节未改 -->

<!-- fp: 4f3216acc3a32ddc -->  源集合**内容**指纹（不含 mtime）；`--check` 就是拿它与实时值比对
<!-- roots: C:\Users\<用户名>\.workbuddy\skills -->  生成时用的扫描根（**机器可读**；`--check` 未显式指定根时按此校检）
> 生成时间：2026-10-20 10:50 ｜ 技能数：**120**（自动跳过 `_backup-*` / `*.bak*` / `*.backup*` / `_archive` / `.git` / 点开头）
> 扫描根：C:\Users\<用户名>\.workbuddy\skills ｜ 文件位置：各技能的 `<根>/<目录名>/SKILL.md`
> **读法（阶段 0）**：先在本表**按簇**定位候选 → **只读命中候选的 `SKILL.md` frontmatter** →
> 一个都不命中才回落全量 Glob。**索引过期时以全量为准并重跑本脚本重建**（`--check` 可判新鲜度）。
> 本表刻意只放「技能名 + 用途摘要」：全量表 ≈ 各 SKILL.md frontmatter 的 1/4 字节，这正是它的存在理由。
> 🏷️ **使用标注**（来自 `_usage_ledger.tsv`，只影响显示、**不参与指纹**）：
> 下方**主表只列在用的 36 个**；`⛔未启用` 的 **84** 个已**分区**到文末「未启用区」（仅索引分区，磁盘上**未移动/未删除**任何技能，装载状态不变，可逆）。
> `✅{n}次`/`✅` = 有过真实调用；`⭐自研` = frontmatter `selfbuilt: true`。

## github-*（3）

| 技能 | 用途 |
| --- | --- |
| `github-api-deploy` ✅4次 | 在 github.com 主域被网络阻断或抖动（中国网络典型场景：api.github.com 通、github.com 超时/502）时，用 PAT 令牌… |
| `github-codeload-clone` ✅2次 | 在中国网络环境下 github.com 主域被墙（api.github.com 通、codeload.github.com 通、github.com 超时）… |
| `github-repo-recon` ✅6次 | 在**不克隆仓库**、且本机对 github.com/huggingface.co 的 HTML 页面不可达的网络环境下，用 GitHub/HF 的 API… |

## ai-*（2）

| 技能 | 用途 |
| --- | --- |
| `ai-workflow` ✅146次 ⭐自研 | AI 标准化多阶段工作方法论（自研），适用于量化分析、跨境电商选品、小说写作、学习资料生成、技术调研、软件与数据分析等项目。按阶段执行：**thinking… |
| `ai-workflow-l2-closeout` ✅2次 ⭐自研 | 把 ai-workflow 的 **L2 任务收尾**做成一条固定顺序、可机器复核的流水线 —— 治「`checks.py plan` 还有 FAIL」「文… |

## cdp-*（1）

| 技能 | 用途 |
| --- | --- |
| `cdp-browser-probe` ✅4次 | 零依赖 CDP 浏览器实测 —— 用 Node 内置 WebSocket 驱动 headless Chromium，做性能采样（draw call/帧、帧间… |

## codebase-*（1）

| 技能 | 用途 |
| --- | --- |
| `codebase-audit` ✅2次 | 对一个代码仓库做「全面体检」（结构/技术栈梳理 + 代码质量 + 潜在 bug + 异常处理 + 安全隐患 + 性能瓶颈 + 依赖过时冲突），输出按严重程度… |

## doc-*（1）

| 技能 | 用途 |
| --- | --- |
| `doc-impl-parity-audit` ✅4次 | 审「文档声明」与「代码实现」是否一致 —— 抓 CLI 参数/子命令/字段名/枚举值/索引锚点的脱节，尤其是"照文档执行 → 工具写入 → 同一工具自己判 … |

## knowledge-*（1）

| 技能 | 用途 |
| --- | --- |
| `knowledge-cram-report` ✅6次 ⭐自研 | 把「一次任务真正学到的东西」抽出来、用自己的话讲一遍、渲染成带公式和自测题的 PDF，按**项目名**归档并排好下次复习日。触发词：恶补报告 / 知识点恶补… |

## win-*（1）

| 技能 | 用途 |
| --- | --- |
| `win-bat-launcher` ✅6次 | 写/修 Windows 一键启动脚本（.bat 与它调用的 .ps1）的正确姿势与坑清单。.bat 侧三大坑：①「%~dp0 尾反斜杠 + 收尾引号」被 C… |

## 独立技能（26）

| 技能 | 用途 |
| --- | --- |
| `AI HOT` | 查询 AI HOT 的中文 AI 资讯、精选、当前热点和日报。用户询问今天或最近的 AI 新闻、AI 圈动态、大模型或产品发布、OpenAI／Anthrop… |
| `archify` | Create polished, validated architecture, workflow, sequence, data-flow, and li… |
| `artifact-integrity-protocol` ✅2次 | 给"跑一次产出一堆文件"的管线加产物完整性协议 —— 每个产物带 sha256 身份、失败也留痕、校验器分四态判定。适用于生成式管线（音频/图像/报告/构建… |
| `derived-layer-writeback` | 给「agent 向既有语料库自动写回」这类功能加**零破坏门禁** —— 治「声称只写派生层、原文一字不动，实则无从证伪」。核心判据：**「只写派生层」必须… |
| `diagram-design` | Create branded architecture, architecture delta, IT current-state, flowchart, … |
| `guarded-git-commit-mixed-repo` ✅6次 | 在「工作区里有并发会话/多条发布线」或「混合仓（一个仓里有多条上传线）」时，安全地做一次只包含本线文件的版本粒度提交，并核查「有没有该推送的没推」。当需要 … |
| `hairline-create` | Use when someone asks for a new Hairline figure, or runs /hairline-create with… |
| `humanizer` | Remove signs of AI-generated writing from text. Use when editing or reviewing … |
| `impeccable` | Use when the user wants to design, redesign, shape, critique, audit, polish, s… |
| `math-modeling-contest` ✅2次 | 数学建模竞赛（国赛 CUMCM / 美赛 MCM·ICM / 亚太杯 APMCM / 大湾区杯 / 校赛 / 限时模拟训练）的全流程作战技能。覆盖审题分诊与… |
| `md-trilogy-qc` ✅2次 | 中文长文「Markdown → PDF/Word」三态交付的质检链——交付前用三个脚本依次过关：① fix_emphasis 修复 CommonMark 强… |
| `memory-file-compaction` ✅2次 | 对"超限被截断"的长期记忆/档案文件（MEMORY.md、沉淀笔记、索引表、README 之类的常驻注入文件）做**无损压缩 + 结构化拆分**的正规流程。… |
| `nonvacuous-review-protocol` ✅4次 | 审「复核/自检本身是否有效」—— 治七类假绿：①断言恒真（`x or True`、`all(...) or True`、永远满足的下界比较），结构上不可能失… |
| `obsidian` | Work with Obsidian vaults (plain Markdown notes) and automate via obsidian-cli… |
| `paper-writing` ⭐自研 | 学术论文写作的执行层技能 —— 把「已做好的研究」写成「能投出去的稿子」。覆盖 C0 契约确认（目标刊物·体裁·引用风格·字数·语言）＋ 六步 W0–W5（… |
| `ppt-master` | AI-driven presentation workflow for generating editable PPTX decks and slides,… |
| `quantity-website-restart` ✅8次 | 一键恢复 quantity.website 并定位故障链路（FastAPI 后端 + Vite 前端 preview + Cloudflare Tunnel… |
| `scanned-book-close-reading` | 给「无文本层（扫描版）」的整本书做全书精读 / 结构化笔记，交付 Markdown + PDF。含形态判定（pypdf 统计文本层与图像对象）、渲染识读通道… |
| `secret-leak-response` ✅2次 | 凭据（API Key / Token / 密码）泄露后的应急响应流程：三维扫描定位残留（文件系统全盘 + git 全历史 + 远端）→ 清理并做脱敏备份 →… |
| `selfcheck-assertion-integrity` | 审「自检/测试给了绿灯，但它其实什么都没测」—— CLI 的退出码与断言两条线。 治两种最坏的假绿：① 本该分发命令的函数 fall through 到兜底… |
| `skill-copy-distribution-sync` | 把某个技能的「最新版」同步到分布在机器多个位置的存量旧副本，并留下可回滚证据。定位按 SKILL.md frontmatter name 全树扫（不按目录名… |
| `sqlite-fts5-chinese-bigram` | 用 SQLite FTS5 做中文全文检索的正确做法 —— 默认 unicode61 分词器对中文完全失效（查询恒 0 命中），trigram 只对 >=3… |
| `svg-iso-figures` | 等距线框 SVG 图形的拆解 / 纳入 / 造新。三条路径——① 逆向拆解一个外部等距图形库或渲染引擎，按 D0–D5 出可复用判定；② 把图形引擎移植进现… |
| `tkinter-local-llm-desktop` | 用 Tkinter 做「本地大模型桌面应用」时的定式与实测坑 —— 治「壳跑起来了但一问就崩 / 首字不达标 / 性能数字只有一个口径说不清 / 近黑 UI… |
| `tong-jincheng-perspective` | 童锦程视角：以"深情祖师爷"、直播情感内容创作者的思维框架看待人际关系、社会动态与个人成长。 素材来源：9个一手视频字幕（直播/约会vlog/搭讪解析），约… |
| `totorosir-workbuddy-score` | WorkBuddy积分助手（WorkBuddy积分查询、获取、播报 Skill，跨平台支持 Windows / macOS / Linux）积分余额、连续登… |

## ⛔ 未启用区（84）

> **这是候选下线池，不是「已删除」**：以下技能在会话记录里**零真实调用**，因此被**移出上表、仅在索引里分区**。磁盘上**未移动、未修改、未删除**任何一个技能目录，装载状态与从前完全一致 —— 随时可回退（删掉本节、把行放回各簇即可）。
> 阶段 0 按簇找候选时**默认不看本节**；只有当全表都不命中、要扩大搜索面时才回看这里。
> 台账口径见 `ai-workflow/scripts/gen_skill_index.py` 的 `load_usage` docstring。

- `aggregation-hotpath-snapshot` — 把「读重、参数多、被反复调用」的聚合接口热路径做快照化重构 —— 用「阶段计时之和 ≠ 总耗时」找出隐藏的 O(窗口) 循环与 Python 回调，把与筛选
- `ai-workflow-plan-compliance-backfill` — 把「写于旧版 ai-workflow 契约下的 L2 计划」清到 checks.py plan FAIL=0：补齐 v4.14.0/v4.15.0 起升为 
- `aliyun-ecs-windows-ssh` — 从 Windows 本机打通到「阿里云 ECS（Windows Server）」的 SSH 通道并配置公钥认证。核心判据 —— **ECONNREFUSED
- `ardot-xai-dark-style` — 在 Ardot 画布上按 xAI 风格模板 00009（近黑画布/白描边胶囊/mono 眉标）快速搭建报告汇报页与 Web App UI 的可复用流程与避坑
- `cache-freshness-fingerprint` — 判定「派生缓存/快照什么时候该重建」的正确做法 —— 用源集合指纹替代比文件 mtime，配幂等-原子重建协议。适用于列存快照 / 索引 / 物化视图 / 
- `cartesian-doubt-reduction` — 笛卡尔式前提审计（Cartesian Doubt Reduction）——用「普遍怀疑 → 不可再分基点 → 逐跳重建 + 结论强度与证据强度对齐」的流程，
- `cdp-real-browser-ux-eval` — 在没有 Playwright/Chromium 可装的机器上，用系统已装 Chrome + websocket-client 直驱 CDP，对本地 Web 
- `classic-models-orchestrator` — 经典思维模型编排路由——面对一个问题，判断该用「第一性原理 / 英雄之旅 / 笛卡尔式前提审计 / 工程控制论 / 矛盾分析」中的哪一个或哪几个，并给出**
- `cli-agent-relay` — 把多个 CLI agent（codex / claude / dsh / 任意 stdin-or-positional CLI）串成「产物接力链」的正确形态
- `code-review` — 从固定点（commit、branch、tag 或 merge-base）开始，按 Standards（代码是否符合本仓库记录的编码标准？）和 Spec（代码
- `codebase-design` — 用于设计深模块的共享词汇。适用于用户想设计或改进模块接口、寻找深化机会、决定 seam 放在哪里、让代码更容易测试或更适合 AI 导航，或其他技能需要深模块
- `contradiction-practice-method` — 矛盾分析与实践迭代方法（方法论层）——用「调查研究 → 矛盾清点 → 定主要矛盾（影响面大 + 本阶段可控 + 可放大到全局）→ 两点论/重点论 → 集中兵
- `daily-prediction-verify-loop` — 把「预测 vs 实际」做成每日自动复盘任务时的接线与判据纪律：报告日/截断面/目标日三者语义、逐标的逐日完整性哨兵、「已判定的劣势」与「无法判定」的措辞分离
- `datasource-feasibility-probe` — 判断「某个数据源/接口能不能真的取到数据及其消费是否正确」的实测方法论。核心结论反直觉 —— 失败时先别急着换库，因为**问题通常不在「库」而在「链路」**
- `design-token-unification-audit` — 把「多套前端界面」统一到一套设计令牌并去掉 AI 生成设计痕迹（糖果渐变、毛玻璃、装饰光斑、emoji 图标、圆角/阴影混用），并用可复跑的只读审计脚本证明
- `diagnosing-bugs` — 面向棘手缺陷和性能回退的诊断循环。适用于用户说 “diagnose” / “debug this”，或报告某些东西 broken、throwing、fail
- `doc-code-sync` — 依据一份「源代码文档」（软著登记用代码摘录、供应商交付的代码说明、AI 生成的规格+代码文档）反向同步代码库的正规流程与实测坑。当用户给出 docx/pdf
- `doc-example-runnability-gate` — 给「含代码块的教程/文档/报告」加可机器判定的质量门禁 —— 抽取全部 ```python 围栏块，逐个在独立子进程 + 独立临时 cwd 里执行并断言退出
- `docx-layout-surgery` — 对 .docx 做版式级精修并用真实渲染验收——加照片位/插入证件照、改纸张（Letter→A4）、表格边框与纵向合并、行高与垂直居中、页数压到目标值。当任
- `domain-modeling` — 构建并打磨项目的领域模型。适用于讨论 codebase 术语、编写或编辑 CONTEXT.md，或记录或编辑 ADR。
- `dsh-isolated-home` — 在不污染本机 `~/.dsh`（用户正在用的 dsh web）的前提下，用 `DSH_HOME` 建一套隔离环境，把 `dsh --profile head
- `dsh-upgrade-plugin-compat` — 升级 DeepSeek Harness (dsh) 版本并保证第三方插件继续可用 —— 覆盖插件 API 断层审计、最小必要抬升、pnpm 死锁的判据与绕行
- `dual-path-parity-audit` — 判断「同一件事的两条代码路径是否真的同源」的验收方法 —— 治「离线脚本与线上 API 算出两份名单、却不知道差异来自接线还是来自数据源」。核心判据：**端
- `dual-source-drift-sentinel` — 双源交叉校验类哨兵（拿本地快照对照外部权威源、超容差报警）的正确搭法与排期 —— 核心是**容差里有一块不是留给你要抓的错误的**：两端不是同一时刻时，差的
- `electron-selftest-harness` — 给 Electron 应用搭一套进程内端到端自检 —— `electron . --selftest --report=x.json` 注入断言脚本、跑完退
- `engineering-cybernetics-control` — 工程控制论诊断（Engineering Cybernetics）——用反馈、稳定性、可观性、可控性与最优控制的概念，对「系统跑偏 / 振荡 / 失控 / 越
- `env-vs-code-failure-triage` — 判断一批测试/校验失败到底是「本次改动引入的代码回归」，还是「环境缺陷 / 产物过期 / 数据新鲜度闸门」造成。核心是两条可执行判据替代读代码猜：①用系统自
- `falsifiable-file-migration` ⭐自研 — 把「把一个目录/一批文件从一个位置迁到另一个位置」做成**可证伪**的操作 —— 复制 → 逐文件 sha256 对账 → 原件**送回收站**（不是硬删）
- `field-availability-registry` — 给「多源拼接的数据集」建一份**机器可校验**的字段可用性与权威来源登记表 —— 先做零成本字段普查（parquet row-group statistic
- `first-principles-thinking` — 第一性原理思维（First Principles Thinking）——把「只能这样 / 别人都这么做 / 行业惯例」的结论拆到不可再分的物理、数学、经济或
- `forecast-acceptance-audit` — 在接受任何「模型更准了 / 预测精度提升了」的结论之前，做最小充分的验收审计：过拟合 gap、统计功效 MDE、多重比较修正、方向命中率。适用于时序价格预测
- `git-guardrails-claude-code` — 设置 Claude Code hooks，在危险 git commands（push、reset --hard、clean、branch -D 等）执行前阻
- `git-init-large-workspace` — 给「已有大量文件的工作区」初始化 git 仓库（GB 级 / 上万文件 / 混着第三方克隆与生成产物）。核心是**先探测再 add** —— 不清点体积就 
- `grill-me` — 一个用来打磨计划或设计的持续追问式访谈。
- `grill-with-docs` — 一个用来打磨计划或设计的持续追问式访谈，并在过程中创建文档（ADRs 和词汇表）。
- `grilling` — 围绕计划、decision 或 idea 持续追问用户。适用于用户想对自己的思路做压力测试，或使用任何 “grill” 触发措辞时。
- `handoff` — 把当前对话压缩成交接文档，让另一个代理接手。
- `hf-offline-guard` — 给用 HuggingFace 的 Python 项目加「离线优先守卫」，根治 hf_hub_download / from_pretrained 因 HEA
- `html-to-docx-plugin-pitfalls` — 把自建 HTML（含 MathJax `$...$` 公式或 `<img>` 公式图、内联 CSS 变量）转成 .docx：选路线（pandoc→OMML 
- `html-to-pdf-print-pipeline` — 把 HTML/Markdown 长文档交付成「可打印、可检索、可跳转」的 PDF —— 用 headless Chrome 打印 + 两遍渲染注入目录真实页
- `improve-codebase-architecture` — 扫描代码库中的深化机会，生成可视化 HTML 报告，然后围绕你选中的候选项继续追问。
- `knowledge-base-merge-qc` — 「把一堆既有素材并入一个带受管词表的索引库」这类合并 / 重建任务的验收协议。 核心是三条判据：① 同义标记查重（只认自己写入用的那个标记 ⇒ 重复条目假绿
- `literature-list-to-index` — 把「一批参考文献」转成可检索的结构化成果，两条分支：(A) 付费墙源（CNKI/知网等）⇒ 探鉴权后产出元数据索引 + 带占位槽位的提炼框架，无原文不填内容
- `long-job-background-survival` — 长时任务（下载/抓取/训练/构建）在受限宿主上「跑一会儿就没了」时的存活与提速法：先用**纯心跳探针**做双机制时长对照，把「宿主时限」与「任务自身 bug
- `long-job-crash-safety` — 编排"跑几小时才出结果"的长任务的崩溃安全与判据纪律 —— 持久化粒度必须细于失败粒度（增量落盘 + resume，且切分粒度与一致性口径对齐）、判据必须事
- `mcp-remote-server-probe` — 在**不装任何 MCP 客户端**的前提下，用零依赖 Node 脚本直接验证一个远程 MCP Server（SSE / Streamable-HTTP）能否
- `model-name-config-audit` — 给「AI 工具链」做「配置里写的模型名 vs 上游实际接受的名字」一致性体检，并辨析账本里"累计失败数"与"当前活跃故障"。适用于：代理账本/日志出现大量 
- `modeling-pipeline-pitfalls` — 搭建或审查「数据 → 预处理 → 建模 → 评估」流水线时的隐蔽缺陷检查清单。当要从零搭数据分析/建模项目骨架、或排查「代码能跑但指标明显偏低/报错莫名其妙
- `monomyth-narrative-design` — 英雄之旅叙事设计（Hero's Journey / 单一神话）——用坎贝尔「分离—启蒙—回归」三幕结构，把已想清楚的想法、产品、项目或方案搭成外部读者走得进
- `outbound-publish-guard` ⭐自研 — 在把内容**发到本机之外**（推 public 仓 / 发布站点 / 生成分享链接 / 导出交付包 / 上传云盘）之前，扫描内容里残留的**本机绝对路径与本
- `pptx-authoring` — 做 PPT 与拆 PPT 的单一入口。① 生成向：用 slidep / SlideDSL 从零做一份有判断力的 .pptx（汇报、行业研究、趋势分析），并在
- `predemo-check-local-web` ⭐自研 — 本地起服的 Web 演示项目「上台前自检 + 交互实测 + 基线留档」三步法（阴阳性双跑的自检脚本、无头浏览器临时探针页验前端交互、区分确定性与耗时的基线口
- `prototype` — 构建一次性原型来回答一个设计问题。适用于用户想验证某个 state model 或 logic 是否感觉对，或探索 UI 应该长什么样时。
- `research` — 对照高可信一手来源调研问题，并把发现保存为仓库中的 Markdown 文件。适用于用户想调研主题、收集文档或 API 事实，或把阅读工作委托给后台代理时。
- `resolving-merge-conflicts` — 适用于需要解决正在进行的 git merge/rebase 冲突时。
- `reviewed-change-apply-gate` — 把「已审过的变更」真正落到既有文件上时，给这一步配可机器验证的门禁 —— 治「出 diff 就当已落地」这类**半截交付**。核心判据：**出 diff ≠
- `safe-lint-autofix` — 安全地执行大规模 lint 自动修复（ruff/eslint 等）。在"一键修 100 项告警"这类任务中，先备份、再自动修、再手工收口，并用 AST 差集
- `scaffold-exercises` — 创建包含章节、题目、答案和讲解的练习目录结构，并确保通过 linting。适用于用户想 scaffold exercises、创建 exercise stu
- `screener-backfill-scan` — 给「多条件 AND 的选股/筛选/风控条件链」做跨时刻逐日回溯扫描 —— 治「单截面命中为 0 或极少，到底是形态稀缺、判据写错，还是阈值过严」。核心是四条
- `setup-pre-commit` — 在当前仓库设置 Husky pre-commit hooks，集成 lint-staged (Prettier)、类型检查和测试。适用于用户想添加 pre-
- `signal-cross-validation` — 判断「新做的选股器/信号」与「已有的因子或条件体系」是同一个维度的重复，还是真正正交的新信息 —— 用同日同池归属检验（Mann-Whitney AUC /
- `sim-trading-verify` — 为「量化分析平台」的模拟交易盘（snapshot 撮合、非 tick 级）子系统提供端到端验证门禁。当新增/修改 sim 后端（backend/servic
- `structured-record-surgical-edit` — 对「长单行标量 / 记录性文件」（YAML 的 `key: "一整段话"`、plan.yaml 的 meta 字段、JSON 串、Markdown 表格行、
- `subbase-train-optimize` — 次底座（subbase）单个方向的"训练+迭代调优+优化前后对比报告"标准作业。当用户要在 D:\数模\次底座\<方向>\ 下训练/优化一个次底座方向、或要
- `task-direction-purge` — 在某个项目任务里「取消一个方向」并要把它的痕迹**彻底清除**（数据 + 派生文档/脚本 + 计划与留痕里的引用 + 死链 + 出站泄漏），且清完仍要让 a
- `tdd` — 测试驱动开发。适用于用户想用先写测试的方式构建功能或修复缺陷、提到 “red-green-refactor”，或需要集成测试时。
- `teach` — 在这个工作区中教用户一个新技能或概念。
- `throttled-host-large-install` — 在被限流的宿主上装大包 / 拉大权重 —— 当「下载慢得像断网」「进程跑到一半被杀」「pip 装完后 import 报 DLL 失败」这三件事出现任意一件时
- `to-questionnaire` — 把你无法完整回答的 decision 转成一份交给他人填写的 questionnaire。
- `truncation-silent-field-loss` — 给「预算内裁剪结构化数据」（LLM 工具摘要 / API 响应裁剪 / 日志·报告摘要 / 导出前截断 / 任何 max_chars·budget·limi
- `unreachable-branch-audit` — 审「**声称有、实际到不了**」—— 功能/分支/门槛写在那儿、手册也写着有，但**没有任何代码路径能进入它**；最典型是**循环依赖型死代码**（分支的唯
- `usage-ledger-merge` — 汇总「已有」的用量 / 计费 / 调用账本（API 网关、代理、CLI agent 的 token 与花费）时的正确口径与三个必踩的坑。 核心结论：**先查
- `vendor-demo-integration` — 把第三方 GitHub 项目（Python/Node 服务）作为 demo 模块集成进既有 Web 应用的标准流程与坑清单。适用于「克隆某开源项目并集成到本
- `video-content-dissect` — 把视频拆成「可复用的规范」——先用 ffmpeg 抽帧 + 分区拼图读画面烧录字幕（无 ASR 也能做），再放大关键帧拆成品画面，最后落成结构化报告；需要复
- `wait-what` — 停一下：刚才那条消息没有说清楚——重新表述一遍。
- `win-folder-lock-diagnose` — 定位 Windows 上「某文件夹/文件被占用、无法删除或移动/重命名」（弹「文件夹正在使用：其中的文件夹或文件已在另一程序中打开」）的根因进程。核心判据 
- `win-resident-service` — 在 Windows 上让服务「真正常驻」的正确形态与实操。核心结论反直觉 —— 常驻进程是最不可靠的形态；正解是「OS 计划任务托管 + 短寿命幂等进程」。
- `wizard` — 生成一个交互式 bash wizard，逐步引导人完成只有他们能执行的手动流程。用于 provisioning 基础设施、设置 credentials 或 
- `workbuddy-scene-resolver` — 把 WorkBuddy / CodeBuddy 客户端里的 `@scene#<id>:<名称>`、`@skill:`、`@expert:` 这类**引用符（
- `writing-beats` — Writing, exploit——把原始素材组装成一段节拍旅程，在某个 beat 依赖一个术语之前先把它 grounded。
- `writing-for-agents` — 为 agent 编写文档。适用于创建或编辑 skills，或修改 AGENTS.md 或 CLAUDE.md 时。
- `writing-fragments` — Writing, explore：挖掘原始 fragments，暂不施加任何结构。
- `writing-shape` — Writing, exploit：把原始素材塑造成文章，一段一段地推进。
- `zero-hit-condition-audit` — 当一套「多条件 AND」的筛选/选股/风控策略命中为 0（或只有个位数）时，用来区分「目标形态确实稀缺」与「判据写错」，并量化「最少动多少才能出名单」。触发
