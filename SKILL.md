---
name: ai-workflow
description: AI 标准化多阶段工作方法论，适用于量化分析、跨境电商选品、小说写作、学习资料生成、技术调研等项目：任务分层（轻操作豁免 / 快速通道 / 全流程）→ 开工前查可用 Skill → 任务理解（一次性追问 + 任务确认表）→ 调研（开源查重 + 证据分级）→ AI 处理（计划先行、验证闭环、精检索、子智能体编排、质量门禁）→ Office 产出 → 自检交付（checks.py 自动对账）→ 复盘沉淀。内置 Token 纪律、评审防偏差与反模式清单。触发词：AI 工作流 / 按流程干活 / 标准流程 / 工作方法论 / ai-workflow。
agent_created: true
version: 2.4.4
---

# AI 工作流 v2.4.4

按阶段顺序执行任务。**三条不可豁免的红线**：① **用户确认前不执行** ② **计划先行**（未落盘 plan.yaml 不得开始处理）③ **工作区边界**（读写与产出只允许落在本次任务指定的工作区根目录内，越界必须先问）。其余按「任务分层」裁剪。**脚本用法、故障排查、变更日志见 `references/ops.md`。**

## 任务分层（开工第一件事）

| 层级 | 判定标准 | 执行方式 |
| --- | --- | --- |
| **L0 轻操作豁免** | 纯问答/查询/翻译、单文件读取、改一行字或一个变量、临时状态检查 | **直接做**，不建任务目录、不走阶段 0-6 |
| **L1 快速通道** | 阶段 0 命中 `assets/templates/` 同类模板且无实质差异 | 提议"按上次配置开跑"→ 确认后跳过追问循环，直接引用模板缓存的查重结论 |
| **L2 全流程** | 产出文件/代码/报告、多步操作、数据分析、跨文件改造、方案评审 | 完整走阶段 0-6 |

判定存疑时**默认 L2**。用户说"直接做/别走流程"则从其指令——**对用户的明示授权可替代"确认前不执行"，但"计划先行"仍需满足**（可在同一消息内给计划并直接执行）。

**环境预检**（仅当要跑脚本时）：venv 存在且能 import requests/openpyxl/python-docx/pypdf/pyyaml；异常则 `powershell -File scripts\setup_env.ps1`。检测与排障命令见 `references/ops.md`。

## 工作区边界（红线③，开工前必做）

- **工作区根由用户按任务指定**（每次任务一个根），写入任务确认表的 `workspace` 字段与 plan.yaml 的 `工作区根`；用户未指定时默认当前会话工作目录，并在确认表里显式标注供其纠正。
- **允许**：工作区根内的读取、写入、产出、脚本临时文件（放 `tasks/<任务>/tmp/`）。
- **越界（根目录之外的任何路径）**：先停下来说明「要访问 X、因为 Y、需要什么授权」，得到**当次明确同意**才执行，并在交付说明里记录该次授权。上一任务的授权不自动延续到本任务。
- **基础设施例外**（不算越界，仅限工具自身用途，不得存放用户数据与产出）：

  | 例外路径 | 允许用途 |
  | --- | --- |
  | `~/.workbuddy/skills/ai-workflow/` | 读取技能指令、写 `tasks/` 记录、改技能本体（改技能属独立任务） |
  | `~/.workbuddy/binaries/python/envs/ai-workflow/` | 调用 venv 解释器与依赖 |
  | `~/.workbuddy/cache/ai-workflow/` | http_fetch 缓存读写 |

- 用户显式给出的其他路径（如「去 E:\X 读数据」）= 该路径临时纳入本任务范围，但仍不扩展到其上级或兄弟目录。

## 阶段 0：开工前查可用 Skill（约 1 分钟）

1. 列本地 skill（`~/.workbuddy/skills/`、`.workbuddy/skills/`）；无匹配则用 find-skills / 推荐市场搜。
2. 判定：匹配 → 复用；部分匹配 → 复用可复用部分；无匹配 → 全新执行。
3. 查 `assets/templates/`（字段规范见 `assets/templates/README.md`）→ 命中走 L1。
4. **工作区状态一瞥**：`checks.py status` 看已有任务与交付物完成度，**不逐个打开历史任务文件**。
5. **确认工作区根**：确定本次任务的 `workspace`（用户指定 / 默认当前会话目录），写进确认表与 plan.yaml；发现所需输入在工作区外时，按红线③先申请授权。

## 阶段 1：任务理解（追问 ≤2 轮）

**红线①：未确认前禁止执行任何脚本或产出文件**（L0/L1 除外）。

1. **第 1 轮就把缺口问全**（1-4 个问题，选择题优先并附推荐项），能推断的要素默认推断、在确认表里标注"（默认，如无异议按此）"——**禁止挤牙膏式多轮追问，追问总轮次上限 2 轮**。
2. 六要素齐备：① 目标 ② 输入 ③ 交付物（格式/路径/命名）④ 验收标准 ⑤ 边界约束 ⑥ **工作区根**（本任务允许读写的目录，红线③依据；未指定则默认当前会话目录并标注「（默认，如无异议按此）」）。
3. 输出「任务确认表」并在**同一轮消息**里请求放行——用户回"确认/开干"即放行；**禁止再单独发起一轮确认提问**。
4. **模板沉淀**：确认后存为 `assets/templates/<任务类型>.yaml`，遵守 `assets/templates/README.md` 的统一 schema；同类型更新而非新建。

## 阶段 2：调研（查重优先 + 证据分级）

**未完成查重并给出复用决策前，禁止进入实现环节。**

1. **查重分流**：开发类 → 开源项目/数据集查重（产出对比表 + 直接复用/克隆改造/自研三选一）；调研类 → 既有报告与横评盘点 + 数据实测。
2. **数据一律实测**：GitHub 指标用 `http_fetch.py --github-repo`（含限流退避、多仓库并发、本地缓存）。**禁止二手 star 数**。
3. **证据分级标注**：【RCT】/【基准实测】/【大样本自评】/【官方推荐】/【实践观点】/【反例】。**厂商案例、营销倍数、"N× 效率"不得作为证据**。详见 `references/quality-gates.md`。
4. **并行硬规则**：检索方向 ≥3 个必须并行派子代理（见「子智能体编排」），禁止串行等待。
5. **引入前检查**：许可证（须 MIT/Apache-2.0 等宽松型，CC-BY-4.0 不适合代码）+ 基础安全（混淆脚本/硬编码密钥/异常外联/`pushed_at` 是否停更）。

## 阶段 3：AI 处理（计划 → 验证闭环 → 精检索 → 编排 → 质检）

**红线②：未产出 plan.yaml 前禁止调用处理脚本；每步未明确目标前禁止检索。**

1. **任务目录制**：`tasks/<任务类型>-<YYYY-MM-DD>/` 内存放 plan.yaml、交付物、中间数据。命名规则：任务类型为**不含空格与斜杠**的中文短语，日期取**任务创建日**（非完成日）；同日同类型多次迭代加版本后缀区分，如 `技能增强-ai-workflow-v2.1-2026-09-10/`；归档时整体移入 `tasks/_archive/<YYYY-MM>/`。plan.yaml 严格用 `assets/plan-template.yaml` 的**中文键格式**，**`交付物` 必填且写完整路径**（阶段 5 自动对账依赖它）。状态用 `checks.py mark <plan.yaml> <id> <状态>` 更新，不手工 sed。
2. **验证闭环前置检查**：动手前回答"完成时用什么可判定信号证明它成了？"——有信号就写进「验证方式」；无信号**先补最小验证物**，补不了就显式登记「人审点」。交付前**出示证据而非声称成功**。各类任务的可判定信号参考：代码类＝测试/构建码/lint/断言；Office 类＝写回后用 `office_io` 读回校验；**调研类＝资源条目数达标且每条含链接 + 关键链接实测探活（`http_fetch --check-links`）+ 时效性说法经官方页复核 + 反例/过期信息已剔除**；改造类＝`checks.py skill` 全绿 + py_compile 通过；**性能类＝耗时下降「且」输出与旧版逐字节一致**（预热后多次取最小值，≥2 轮独立复现，禁用"冷基线 vs 热优化"的假加速）。
3. **逐步执行**：每步前重述目标与判定标准，完成后更新状态；未达成先修正再推进。
4. **进度汇报节奏**：每完成 2-3 步或切换阶段回报**一行**（`步骤 x/y 完成 → 下一步：…`）；只在受阻、需决策、完成时展开。预计 >5 分钟的任务先报一句预期与中间产出节点。
5. **精确检索（先选对工具再搜）**：网页 → `http_fetch <URL> --grep --max-chars`（缓存自动兜底）；**GitHub 找项目 → `http_fetch --github-search "<query>"`**（限定符 `language:` `stars:` `topic:` `pushed:` `archived:`），**GitHub 找代码实现 → `--github-code-search "<代码片段> repo:owner/name"`**（⭐**强制 `GITHUB_TOKEN`**，返回"哪个仓库的哪个文件"+命中片段），取指标 → `--github-repo a/b,c/d`（凭据按 `--token` → `GITHUB_TOKEN` → `GH_TOKEN` → `gh auth token` 自动解析，已登录 gh CLI 即免配置）；两个搜索都支持 **`--dry-run`**（只打印将请求的 URL，不发请求，无 token 也能验证参数构造）；本地小目录 → 内置 `Grep`/`Glob`；**跨行/结构模式 → `ast-grep`**（"先 A 后 B 且中间无 try"这类；⚠️ 其 pattern **不支持正则**，且**复合语句必须写全**，文本匹配回 `Grep`；符号级用 `ast-grep outline`）；**大数据集/大目录 → `data_query.py files|sql|find`**（DuckDB 零导入直查 Parquet/JSON/CSV；`big` 默认跳过 `.venv` 等依赖目录，旧口径加 `--no-skip`）。**交付物里的外部链接一律先用 `http_fetch.py --check-links <urls.txt>` 并发探活**（只取状态码，不下载正文）。引用标明来源。
6. **Token 纪律**：稳定前缀在前吃 KV 缓存；上下文分热/温/冷三层、每层压缩 40-60%（**禁止 90%+**）；记忆只读索引与摘要；**项目上下文文件保持 30-60 行、只写模型推断不出的内容、禁止提交 `/init` 产物**（ETH Zurich 实测 -3% 成功率 / +20% 成本）；选型黑名单 RouteLLM/GPTCache/Memobase，LiteLLM 须 ≥1.83.7。
7. 批量总结/生成用 `ai_call.py`（`--batch-file` + `--concurrency` 并发、`--model` 覆盖、`--stats` 用量回显）；项目差异化流程见 `references/playbook.md`（模板已就绪，可走 L1）。

### 子智能体编排

细则见 `references/orchestration.md`。硬规则：**Handoff 结构化**（`task`/`background`/`input_paths`/`acceptance`/`deliverable_path`/`evidence_rule`，禁止自由文本）；**独立才并行**（建议 ≤4；有依赖必须串行；只读调研用轻量模型）；子代理**只回传浓缩结论**（1-2k token）；主代理负责拆分与汇总。

### 质量把关（信任但验证）

细则见 `references/quality-gates.md`。硬规则：子代理产出**未经核实不得进入下一环节**（优先抽查可复现硬数据）；不合格带具体问题退回（**最多 2 轮**），2 轮后改派两个子代理**对抗式互审**，主代理汇总裁决；评审由模型完成时须**防六偏差**（位置交换双跑、异家族裁判、长度/格式不计分、pin 版本、容差带）。

## 阶段 4：Office 产出

1. 用 `scripts/office_io.py` 生成 Excel/Word/PDF（支持 CSV 读入、多 sheet、列宽/冻结首行）；报告结构参照 `assets/report-template.md`。
2. 写文件统一 `utf-8-sig`；Word 中文必须设两层字体（`run.font.name` + `w:eastAsia`）。
3. 产出前先列将写入的文件路径清单，**逐条确认落在工作区根内**（红线③）；库的坑见 `references/office-guide.md`。

## 阶段 5：自检交付

1. **Anti-drop 对账**：`checks.py plan <plan.yaml>` 自动核对交付物是否真实存在、字段是否齐全、状态是否合法（非文件型交付物标 SKIP 需人工确认）。**FAIL 未清零不得交付**。
2. 输出自检状态表：文件存在、可打开、编码正确、数据完整、符合验收标准、**验证闭环证据已出示**、**产出全部落在工作区根内**。
3. 全部通过后用 present_files 交付；不通过则回到对应阶段修复后重新自检。
4. 交付说明简洁：结论 + 关键文件 + 下一步建议。

## 阶段 6：复盘与沉淀

任务交付后（L2 默认执行，L1 可跳过）：

1. **复盘四问**：哪个阶段返工最多？哪条假设被推翻？踩了什么坑？下次少走哪一步？
2. **沉淀分流**：流程 → 更新本 skill；配置 → 更新 `assets/templates/<类型>.yaml`；坑 → 追加 `references/quality-gates.md` 反模式清单；仅本次有效的事实 → 工作区 memory 一行带过。
3. 复盘结论压缩 3-5 行，随交付说明给出。
4. **任务目录治理**：`checks.py status` 会提示陈旧/超额任务；超 10 个或超 30 天的移入 `tasks/_archive/<YYYY-MM>/`（保留 plan.yaml 与最终交付物，中间产物可删），**只移动不删除**，并在回复中列出移动清单。

## 手册与脚本索引

| 文件 | 内容 |
| --- | --- |
| `references/ops.md` | **脚本用法速查、环境检测、故障排查、变更日志** |
| `references/playbook.md` | 四类项目差异化流程（量化/选品/小说/学习资料） |
| `references/quality-gates.md` | 证据分级、验证闭环、CI 门禁、评审六偏差、反模式清单 |
| `references/orchestration.md` | 子代理编排手册、Handoff 模板、并行规则、失败升级 |
| `references/office-guide.md` | openpyxl / python-docx / pypdf 避坑 |
| `assets/plan-template.yaml` ／ `report-template.md` ／ `templates/README.md` | 计划、报告、确认表规范 |

核心命令：`checks.py skill`（技能自检）｜`checks.py plan <plan.yaml>`（对账）｜`checks.py status`（任务总览）｜`checks.py mark`（状态更新）｜`http_fetch.py --github-search "..."`（GitHub 找项目）｜`http_fetch.py --github-code-search "..."`（GitHub 找代码，需 token）｜`data_query.py files|sql|find`（大数据集检索）。完整参数见 `references/ops.md`。
