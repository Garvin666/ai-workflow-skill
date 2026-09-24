# AI Workflow（ai-workflow）

AI 标准化多阶段工作方法论 —— 一套「流程编排 + 机器可校验门禁」的自研技能（当前版本 **v4.7.0**）。

它不只是一个提示词模板：每个阶段都有对应的**机器判据**（自检、口径守卫、出站扫描、独立验收），流程产物（计划、决策、履历）全部落盘留痕，可审计、可回归。

- 本体仓：`https://github.com/Garvin666/ai-workflow-skill`（本仓）
- 自研工具公开留痕仓：`https://github.com/Garvin666/ai-workflow-tools`

## 项目简介

`ai-workflow` 为多阶段任务提供标准化流程：**入口分型 → 任务分层 → 计划先行 → 编排执行 → 独立审核 → 测试交付 → 核验归档**，末梢设**熔断机制**（触发即冻结并升级，机器可判定）。

适用于：产出文件 / 代码 / 报告、多步且步骤间有依赖、数据分析、跨文件改造、调研查重、方案评审等场景。
不适用于：纯问答 / 查询 / 翻译 / 单文件读取。

内置四种**快判（judge）**，与主流程同构、可独立调用：

| 快判 | 回答的问题 | 契约 |
| --- | --- | --- |
| self-judge | 这条消息该进流程还是直接答（chat / code / content 三态） | `references/self-judge.md` |
| method-judge | 这一步该选哪个工具 / 方法 | `references/method-judge.md` |
| retrieval-judge | 该不该查、查哪类源、能否断言「不存在」 | `references/retrieval-judge.md` |
| homework-judge | 是否叠加**作业模式**（解题结构 H1–H5） | `references/homework-judge.md` |

## 功能说明

- **流程编排**：入口分型（消息 / 正式需求 / Bug）、任务分层（轻操作豁免 / 快速通道 / 全流程）、自适应计划与重规划、决策留痕（能力决策 + 计划修订，机器校验）。
- **作业模式**（v4.7.0）：面向课程作业 / 习题的解题结构 —— 审题 → 思路分析 → 分步求解 → 关键步骤解释 → 答案与验证，配数学计算 / 编程实现 / 论述写作三类题型骨架。
- **机器门禁**：`checks.py`（技能自检 / 计划校验 / Anti-drop 对账 / 熔断门禁）、`gate.py`（删改既有文件前的运行时闸门，fail-closed）、`guard_constants.py`（跨模块常量同源守卫）、`outbound_scan.py`（外发内容脱敏扫描）。
- **双仓推送体系**：本体 → `ai-workflow-skill`，自研工具 → `ai-workflow-tools`；`push_router.py` 分流路由（默认 dry-run），`push_ontology.py` 走 Git Data API 增量，`publish_tools.py` 单文件推送，`verify_push.py` 推送后独立验收（与推送通道零代码共享）。
- **效率工具**：`ai_call.py`（AI 调用 / 批量并发）、`http_fetch.py`（GitHub 搜索 / 抓取缓存 / 链接探活）、`data_query.py`（DuckDB 大目录检索）、`office_io.py`（Excel / Word / PDF 读写）。

## 安装与使用

### 安装

```bash
# 1. 克隆到技能目录（路径按你的技能 home 调整）
git clone https://github.com/Garvin666/ai-workflow-skill.git ~/.workbuddy/skills/ai-workflow

# 2. 初始化 Python venv 并安装依赖（Windows / PowerShell）
powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1
# 依赖：requests / openpyxl / python-docx / pypdf / pyyaml / duckdb / ast-grep-cli
```

最小自检（不依赖安装脚本）：

```bash
PY="$HOME/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"
"$PY" scripts/checks.py skill
```

### 使用

- **作为技能调用**：在支持的宿主里用触发词（如「按流程干活」「标准流程」「ai-workflow」「作业模式」）唤起，主入口为 `SKILL.md`。
- **直接跑工具**（进入技能目录后）：

```bash
# 技能自检（frontmatter / 文档引用完整性 / 模板 schema / py_compile）
python scripts/checks.py skill

# 计划校验 + Anti-drop 对账 + 熔断门禁
python scripts/checks.py plan tasks/<任务目录>/plan.yaml

# 删改既有文件前过运行时闸门
python scripts/gate.py check <路径> --base <工作区根> --intent write

# 历史任务目录归档（只移动不删除，默认 dry-run）
python scripts/archive_tasks.py --root . --older-than 2026-09-23
```

各脚本详细参数见 `references/ops.md` 速查表，或加 `--help`。

## 目录结构

```
ai-workflow/
├── SKILL.md                  # 主手册（流程阶段 / 纪律 / 核心命令，技能入口）
├── Ledger.md                 # 版本台账（版本链与逐条变更登记）
├── README.md
├── scripts/                  # 26 个可执行脚本
│   ├── checks.py             # 自检入口（内部模块：checks_core/parity/judges/cmds）
│   ├── gate.py               # 运行时闸门（范围判定 × 风险判定，fail-closed）
│   ├── guard_constants.py    # 跨模块常量同源守卫
│   ├── outbound_scan.py      # 出站脱敏扫描（含用户名路径 → FAIL）
│   ├── push_router.py        # 双仓分流推送路由（默认 dry-run）
│   ├── push_ontology.py      # 本体通道（Git Data API 增量，支持删除）
│   ├── publish_tools.py      # 工具通道（单文件公开留痕）
│   ├── verify_push.py        # 推送后独立验收器
│   ├── ai_call.py / http_fetch.py / data_query.py / office_io.py
│   ├── laya_client.py        # 离线决策服务客户端（影子期只作对照）
│   ├── homework_model.py     # 作业模式聚合模型（Realization A）
│   ├── archive_tasks.py      # 任务目录归档（只移动不删除）
│   ├── gen_skill_index.py / perf_baseline.py / git_check.py
│   ├── judges.json / model_tiers.json
│   └── setup_env.ps1 / run_stage.ps1
├── references/               # 25 份下沉手册（judge 契约 / 流程模型 / 门禁口径 / 推送路由…）
├── assets/                   # 计划模板 / 报告模板 / 台账模板 / 题型骨架（templates/）
├── tasks/                    # 活跃任务档案（plan.yaml / 报告 / 交付物）
│   └── _archive/             # 历史任务归档（仅本地保留，不入版本控制）
└── _archive/                 # 本地归档（backups/ 不入版本控制）
```

## 注意事项

- **凭据安全**：`AI_API_KEY`、`GITHUB_TOKEN` 等一律走环境变量，不落盘、不进日志；`.gitignore` 已过滤 `.env`、`*.pem`、`*.key` 等五类禁止提交项。
- **出站纪律**：外发文件不得含本机用户名主目录路径（`outbound_scan.py` 强制，命中即阻塞推送）；文档中路径请用 `~/.workbuddy/...` 或 `<用户名>` 占位。
- **本地归档不入库**：`tasks/_archive/` 与 `_archive/backups/` 在 `.gitignore` 中，克隆者侧不会拿到历史归档；依赖旧快照对照的脚本（如 `perf_baseline.py`）对此有优雅降级。
- **推送三原则**：默认 dry-run、`--apply` 才写远端；删除远端文件必须显式 `--allow-delete`；推送后用 `verify_push.py` 独立验收，不自证。
- **分支约定**：`main` 只放稳定可运行版；新功能走 `dev`，并行实验各建 `exp-xxx`；commit 注释类型取自 `references/git-conventions.md` 枚举，机器校验见 `scripts/git_check.py`。
- **门禁口径**：`checks.py skill` 的计数与阈值是版本相关的状态量，跨版本不可直接相减；改判据须先量影响面，不为消 FAIL 改判据。
