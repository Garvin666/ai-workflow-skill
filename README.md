# AI Workflow（ai-workflow）

AI 标准化多阶段工作方法论 —— 一套「流程编排 + 机器可校验门禁」的自研技能（当前版本 **v4.18.1**）。

它不只是一个提示词模板：每个阶段都有对应的**机器判据**（自检、口径守卫、出站扫描、独立验收），流程产物（计划、决策、履历）全部落盘留痕，可审计、可回归。

- 本体仓：`https://github.com/Garvin666/ai-workflow-skill`（本仓）
- 自研工具公开留痕仓：`https://github.com/Garvin666/ai-workflow-tools`

## 项目简介

`ai-workflow` 为多阶段任务提供标准化流程：**入口分型 → 任务分层 → 计划先行 → 编排执行 → 独立审核 → 测试交付 → 核验归档**，末梢设**熔断机制**（触发即冻结并升级，机器可判定）。

适用于：产出文件 / 代码 / 报告、多步且步骤间有依赖、数据分析、跨文件改造、调研查重、方案评审等场景。
不适用于：纯问答 / 查询 / 翻译 / 单文件读取。

内置七种快判（judge），与主流程同构、可独立调用：

| 快判 | 回答的问题 | 契约 |
| --- | --- | --- |
| self-judge | 这条消息该进流程还是直接答（chat / code / content 三态） | `references/self-judge.md` |
| method-judge | 这一步该选哪个工具 / 方法 | `references/method-judge.md` |
| retrieval-judge | 该不该查、查哪类源、能否断言「不存在」 | `references/retrieval-judge.md` |
| homework-judge | 是否叠加**作业模式**（精简解题结构 S0–S2） | `references/homework-judge.md` |
| learning-judge | 这次有什么值得学（偏好 / 领域知识 / 流程坑 / 事实 / 无） | `references/learning-judge.md` |
| thinking-judge | **这个任务该不该按原样做**（接受 / 修正 / 澄清 / 拒绝 四态 + 否决轴 A1–A6） | `references/thinking-panel.md` |
| style-judge | **本次产出要不要去 AI 味改写**（走去味 / 只登记 / 已达标 / 不适用 四态） | `references/humanize-judge.md` |

七块判据的问题模板集中在 `scripts/judges.json`，聚合模型为 `scripts/*_model.py`。

## 功能说明

- **流程编排**：入口分型（消息 / 正式需求 / Bug）、任务分层（轻操作豁免 / 快速通道 / 全流程）、自适应计划与重规划、决策留痕（能力决策 + 计划修订，机器校验）。
- **思考板块**（v4.11.0）：阶段 0 **第 0 步**的任务审计快判 —— 判「该不该按原样做」，产出四态裁决（接受 / 修正 / 澄清 / 拒绝）落 `meta.思考判定`；否决轴 A1–A6 命中即拒绝（**审计不产生授权、不替代红线**），配 Laya 影子对照。
- **文风判别**（v4.15.0）：阶段 0 第 1.5 步的第七块快判 —— 判「本次产出要不要去 AI 味改写、命中哪几组模式」，四态落 `meta.文风判定`；触发面收敛到 `content` 类的散文正文（对代码 / JSON / YAML 判「不适用」）。判据集 `references/humanize-rubric.yaml`（31 条模式 A–F），校验器 `scripts/humanize_scan.py`（`--gate` 实跑 + `--diff-fidelity` 事实保真比对），验收为双条件（FAIL 命中数下降 且 保真零丢失）。它**不判作者身份、不保证过任何 AI 检测器**。
- **作业模式**（v4.10.1）：面向课程作业 / 习题的精简解题结构 S0–S2（简要已知 → 解题过程（验证内联）→ 答案），配数学计算 / 编程实现 / 论述写作三类题型骨架。
- **学习模型**（v4.8.0）：阶段 6 收尾的持续优化回路 —— 采集既有留痕 → 抽取四类知识（偏好 / 领域知识 / 流程坑 / 事实）→ 蒸馏去重 → 证据门槛校验 → 两段式并入个人知识库，使后续任务经 KB-First 检索直接吃到历史经验。入库由 `scripts/kb_learn.py` 的六条门槛裁决。
- **文献阅读模式**（v4.17.0）：以**严苛审稿人**视角审阅一篇文献的产出结构 —— 角色契约 P1–P4（默认怀疑 / 判断可回溯 / 作者声称≠实际做到 / 不越界评价）＋ 四问结构 Q1–Q4（研究问题 / 创新点 / 可质疑点 / 精读略读分区），**四问按论证角色归入主张层（Q1/Q2，可在原文核对）/ 证据层（Q3，须审稿人构造）/ 结构层（Q4，阅读策略）三域**，配证据分级 A/B/C/D（直引 / 归纳 / 推断 / 无法确认）与位置锚（章节号或页码）要求。**不新增 plan 字段、judge 与机器判据**（识别是启发式），手册见 `references/literature-reading-mode.md`。
- **知识点恶补报告**（v4.18.1）：阶段 6 收尾**每个 L2 任务都调用****独立技能** `knowledge-cram-report` —— 把本次任务真正学到的东西抽出来、去重、讲人话，渲染成带公式与自测题的 PDF，按项目名归档并排下次复习日（含 FSRS 形状的复习调度与索引台账）。触发边界：L1 / L0 不触发；**每个 L2 收尾都跑一遍抽取**，确无「可迁移 + 可解释」知识点时不产出（**必出 = 必跑这一遍**，不是硬凑）。本技能**不属本体**，源码留痕在 `ai-workflow-tools` 仓 `skills/knowledge-cram-report/`。
- 项目 Git 开发规范：`main` 只放稳定可运行版，新功能与新增模块走 `dev`，并行实验各建 `exp-xxx`；commit 注释类型取自手册枚举，机器校验 `scripts/git_check.py`。
- **外部技能簇**（v4.16.0）：技能库根下 mattpocock vendored 的 24 个第三方 MIT 技能，**扁平外挂、不属本体**，其 User-invoked / Model-invoked 分类与「何时该调」见 `references/external-skills.md`；机器检查用 `scripts/external_skill_lint.py`，不走本体的 `checks.py skill`。
- 机器门禁：
  - `checks.py`：技能自检 / 计划校验 / Anti-drop 对账 / 熔断门禁（内部模块 `checks_core` / `checks_parity` / `checks_judges` / `checks_cmds`）
  - `gate.py`：删改既有文件**之前**的运行时闸门，范围判定与风险判定分离，fail-closed
  - `guard_constants.py`：跨模块常量同源守卫
  - `outbound_scan.py`：外发内容脱敏扫描
  - `humanize_scan.py` / `check_aesthetics.py`：文风判据（31 条）与审美判据（30 条）的校验器
  - `external_skill_lint.py`：外部技能簇检查
  - `cleanup_task.py`：任务产物清理（删前 sha256 快照，删后复核）
- 双仓推送体系：本体 → `ai-workflow-skill`，自研工具 → `ai-workflow-tools`；`push_router.py` 分流路由（默认 dry-run），`push_ontology.py` 走 Git Data API 增量，`publish_tools.py` 单文件推送，`verify_push.py` 推送后独立验收（与推送通道零代码共享）。
- 效率工具：`ai_call.py`（AI 调用 / 批量并发）、`http_fetch.py`（GitHub 搜索 / 抓取缓存 / 链接探活）、`data_query.py`（DuckDB 大目录检索）、`office_io.py`（Excel / Word / PDF 读写）。

## 安装与使用

### 安装

```bash
# 1. 克隆到技能目录（路径按你的技能 home 调整）
git clone https://github.com/Garvin666/ai-workflow-skill.git ~/.workbuddy/skills/ai-workflow

# 2. 初始化 Python venv 并安装依赖（Windows / PowerShell）
powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1
# 依赖：requests / openpyxl / python-docx / pypdf / pyyaml / duckdb / ast-grep-cli
```

> ⚠️ **`setup_env.ps1` 内含硬编码路径**（`$managedPython` 与 `$venvDir` 指向作者本机的 `C:\Users\<用户名>\.workbuddy\...`）。
> 在别人的机器上直接跑会以 `[FAIL] managed python not found` 退出。**克隆后请先改这两个变量**，
> 再执行安装。README 里「路径按你的技能 home 调整」那句话覆盖的是 `git clone`，**不覆盖**该脚本。

最小自检（不依赖安装脚本）：

```bash
PY="$HOME/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"
"$PY" scripts/checks.py skill
```

### 使用

- **作为技能调用**：在支持的宿主里用触发词唤起，主入口为 `SKILL.md`。常见触发词：`AI 工作流` / `按流程干活` / `标准流程` / `工作方法论` / `ai-workflow` / `作业模式` / `解题` / `做作业` / `习题` / `Git 开发规范` / `分支规范` / `commit 注释规范` / `学习模型` / `归纳偏好` / `复盘学习` / `清理中间产物` / `任务收尾清理` / `cleanup_task` / `思考板块` / `该不该这么做` / `任务审计` / `拒绝这个任务` / `去 AI 味` / `文风` / `humanize` / `去味改写` / `别这么写` / `外部技能` / `第三方技能` / `文献阅读` / `读文献` / `论文审阅` / `审稿意见`。
- **直接跑工具**（进入技能目录后）：

```bash
PY="$HOME/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"

# 技能自检（frontmatter / 文档引用完整性 / 模板 schema / py_compile / 口径守卫）
"$PY" scripts/checks.py skill

# 计划校验 + Anti-drop 对账 + 熔断门禁
# ⚠️ target 必须给**绝对路径** —— 它不参与 --base 拼接，按 **CWD** 解析。
#    给相对路径会报 [FAIL] plan.yaml 存在（文件其实存在），且报错只回显你给的那串路径。
"$PY" scripts/checks.py plan "/abs/path/to/tasks/<任务目录>/plan.yaml" --base "/abs/path/to/工作区根"

# 工作区任务总览（层级 / 步骤完成度 / 交付物完成度 / 陈旧任务归档建议）
"$PY" scripts/checks.py status --workspace "/abs/path/to/工作区根"

# 删改既有文件前过运行时闸门
"$PY" scripts/gate.py check <路径> --base <工作区根> --intent write

# 历史任务目录归档（只移动不删除，默认 dry-run）
"$PY" scripts/archive_tasks.py --root . --older-than 2026-09-23
```

`checks.py` 共 9 个子命令：`skill` / `plan` / `status` / `mark` / `decide` / `revise` / `selftool` / `trace` / `metrics`。
其中 `mark` 支持 `--batch <文件>`（每行 `<step_id> <状态>`）一次落盘，避免 N 步 N 次重写；
步骤状态枚举为 `待办 / 进行中 / 完成 / 受阻 / 熔断`（**没有「待执行」**）。

各脚本详细参数见 `references/ops.md` 速查表，或加 `--help`。

## 配置项

| 配置 | 位置 | 说明 |
| --- | --- | --- |
| `AI_API_KEY` | 环境变量 | AI 调用（`ai_call.py`）所需的密钥。未设置时安装脚本只提示 `[INFO]`，不报错；只有真正发起 AI 调用才需要 |
| `AI_API_BASE` | 环境变量 | `strong` / `mid` 档的端点覆盖项；缺省取 `scripts/model_tiers.json` 里的 `base` |
| `OLLAMA_BASE` | 环境变量 | `cheap` 档的端点覆盖项；缺省 `http://localhost:11434/v1` |
| `GH_TOKEN` / `GITHUB_TOKEN` | 环境变量 | 推送通道（`push_ontology.py` / `publish_tools.py`）鉴权用。⚠️ `gh auth token` 在 shell 里可用，但**脚本子进程读不到登录态**，需先 `export GH_TOKEN=$(gh auth token)` 注入（只在内存，不落盘） |
| 模型档位 | `scripts/model_tiers.json` | 三档 `strong` / `mid` / `cheap`，各自定义 `model` / `base` / `base_env` / `key_env` / `price_in` / `price_out`。`ai_call.py --tier <档位>` 按此解析。档位名与 `references/routing-guide.md`（**唯一口径源**）一致；计划里另有第四值 `default`＝按阶段默认档位，不在本文件里映射到具体模型 |
| 依赖清单 | `scripts/setup_env.ps1` 的 `$deps` | `requests` / `openpyxl` / `python-docx` / `pypdf` / `pyyaml` / `duckdb` / `ast-grep-cli` |
| 运行时闸门范围 | `scripts/checks_core.py` 的 `INFRA_EXCEPTIONS` | 判定「是否落在工作区根之外」时的基础设施例外清单（`/.workbuddy/skills/`、`/.workbuddy/binaries/python/envs/ai-workflow/`、`/.workbuddy/cache/ai-workflow/`）。`gate.py` 从 `checks.py` 同源加载，不自建副本 |
| 提交过滤 | `.gitignore` | 凭据类（项目 Git 开发规范 §4.1 第⑤类）共 9 条规则：`.env` / `.env.*` / `!.env.example` / `*.pem` / `*.key` / `*.p12` / `*.pfx` / `secrets.*` / `credentials.json` |

## 目录结构

```
ai-workflow/
├── SKILL.md                  # 主手册（流程阶段 / 纪律 / 核心命令，技能入口）
├── Ledger.md                 # 版本台账（版本链与逐条变更登记）
├── README.md
├── .gitattributes
├── .gitignore
├── scripts/                  # 33 个可执行脚本（30 .py + 1 .js + 2 .ps1）+ 2 个 JSON 数据文件 + fixtures/
│   ├── checks.py             # 自检入口（内部模块：checks_core / checks_parity / checks_judges / checks_cmds）
│   ├── gate.py               # 运行时闸门（范围判定 × 风险判定，fail-closed）
│   ├── guard_constants.py    # 跨模块常量同源守卫
│   ├── outbound_scan.py      # 出站脱敏扫描（含用户名路径 → FAIL）
│   ├── humanize_scan.py      # 文风判据校验器（--gate / --diff-fidelity / --selftest）
│   ├── check_aesthetics.py   # 审美判据校验器（设计类产物，30 条 rubric）
│   ├── external_skill_lint.py# 外部技能簇检查（不走 checks.py skill）
│   ├── cleanup_task.py       # 任务产物清理（删前 sha256 快照）
│   ├── kb_learn.py           # 知识库入库（六条门槛）
│   ├── push_router.py        # 双仓分流推送路由（默认 dry-run）
│   ├── push_ontology.py      # 本体通道（Git Data API 增量，支持删除）
│   ├── publish_tools.py      # 工具通道（单文件公开留痕）
│   ├── verify_push.py        # 推送后独立验收器
│   ├── ai_call.py / http_fetch.py / data_query.py / office_io.py
│   ├── laya_client.py        # 离线决策服务客户端（影子期只作对照）
│   ├── laya_ensure.py / laya_record.py   # Laya 服务就位与记录
│   ├── homework_model.py     # 作业模式聚合模型（Realization A）
│   ├── thinking_model.py     # 思考板块聚合模型（Realization A，v4.11.0）
│   ├── archive_tasks.py      # 任务目录归档（只移动不删除）
│   ├── gen_skill_index.py / perf_baseline.py / git_check.py
│   ├── geom-probe.js         # 页面侧几何取数（CDP 注入，审美判据渲染层用）
│   ├── judges.json           # 七块快判的问题模板
│   ├── model_tiers.json      # 模型档位配置（strong / mid / cheap）
│   ├── fixtures/             # 校验器测试夹具（humanize）
│   └── setup_env.ps1 / run_stage.ps1
├── references/               # 33 份下沉手册（= 31 .md + 2 .yaml；judge 契约 / 流程模型 / 门禁口径 / 推送路由…）
├── assets/                   # 计划 / 报告 / 台账模板（根下 4 份）+ templates/ 项目模板库（11 份 .yaml）+ thinking-gold.yaml + 熔断报告模板.md
├── tasks/                    # 活跃任务档案（plan.yaml / 报告 / 交付物）
│   └── _archive/             # 历史任务归档（仅本地保留，不入版本控制）
└── _archive/                 # 本地归档
    ├── changelog.md          # 演进台账（只追加，勿整篇读）
    └── backups/              # 备份（不入版本控制）
```

## 注意事项

- **凭据安全**：`AI_API_KEY`、`GH_TOKEN`、`GITHUB_TOKEN` 等一律走环境变量，不落盘、不进日志；`.gitignore` 已过滤凭据类（项目 Git 开发规范 §4.1 第⑤类）共 9 条规则。
- **出站纪律**：外发文件不得含本机用户名主目录路径（`outbound_scan.py` 强制，命中即阻塞推送）；文档中路径请用 `~/.workbuddy/...` 或 `<用户名>` 占位。
- **本地归档不入库**：`tasks/_archive/` 与 `_archive/backups/` 在 `.gitignore` 中，克隆者侧不会拿到历史归档；依赖旧快照对照的脚本（如 `perf_baseline.py`）对此有优雅降级。
- **推送三原则**：默认 dry-run、`--apply` 才写远端；删除远端文件必须显式 `--allow-delete`；推送后用 `verify_push.py` 独立验收，不自证。
- **推送不是 `git push`**：技能仓推的是**文件内容**（`push_ontology.py` 走 `api.github.com` Git Data API + `base_tree` 增量），不是提交历史，故本地 `dev` 与远端 `main` 的历史分叉不构成障碍，也不需要 force push。
- **分支约定**：`main` 只放稳定可运行版；新功能走 `dev`，并行实验各建 `exp-xxx`；commit 注释类型取自 `references/git-conventions.md` 枚举，机器校验见 `scripts/git_check.py`。
- **门禁口径**：`checks.py skill` 的计数与阈值是版本相关的状态量，跨版本不可直接相减；改判据须先量影响面，不为消 FAIL 改判据。当前 v4.18.1 基线为 **通过 72/72，FAIL=0，SKIP=0，WARN=0**（v4.18.0 / v4.17.0 均为 72/72）。
- **平台限制**：技能面向 Windows / Git Bash 环境；`setup_env.ps1` 依赖 Windows PowerShell 5.1（脚本注释为 ASCII-only，因为 5.1 按 ANSI/cp936 读文件，非 ASCII 注释会吞掉下一行代码）。
