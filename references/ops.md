# 脚本用法与环境运维（按需加载）

> 本文件由 SKILL.md 拆出，承载「脚本速查 / 环境检测 / 故障排查 / 链接核验 SOP」。
> **变更日志已拆到 `references/changelog.md`**（v3.4.0 / P4）—— 它是**追加式无上限增长**的台账，
> 与「查个命令怎么写」完全无关，混在一起会让常用路径白付 2.9 万 token（实测变更日志占本文件 73.7%）。
> **需要查历史时读它的尾部**，不要整篇读。
> 环境：Windows + Git Bash，脚本一律用 ai-workflow venv 的 python 运行。

## 一、运行方式

调用一律用 PowerShell `&` 运算符或 Git Bash 绝对路径：

```bash
SK="$HOME/.workbuddy/skills/ai-workflow"
PY="$HOME/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"
"$PY" "$SK/scripts/checks.py" skill
```

也可用 `scripts/run_stage.ps1 <脚本名> [参数...]`（自带状态检查 + **执行后自检**）。

> **优先级（重要）**：**首选**上面这种「venv 解释器绝对路径 + 脚本」的直接调用；`run_stage.ps1` 只作为**交互式终端**里的便捷入口。原因：在本机的某些宿主通道下，ps1 内启动的**原生子进程根本不会执行**（表现为只打印状态检查、退出码 0、产物不生成）。自 v2.5.1 起脚本已把「子进程未跑起来」判为 `[FAIL]` 并以 1 退出，但这只是防呆，不是修复宿主差异。

## 二、脚本速查

| 脚本 | 用途 | 示例 |
| --- | --- | --- |
| **checks.py** | `skill` 技能自检（frontmatter/引用完整性/模板 schema/py_compile）；`plan` 计划校验 + Anti-drop 对账 + **熔断门禁**（`熔断状态: 已熔断` 或步骤状态 `熔断` → 直接 FAIL）；`status` 工作区任务总览（交付物完成度 + 归档建议 + **已熔断任务 ⚡ 标记与 WARN 汇总**）；`mark` 更新步骤状态（含 `熔断`）与 **meta 熔断状态**（`--fuse 正常\|已熔断`，复位用 `--fuse 正常`，不必手改 YAML）；**`mark <plan> --batch <文件>` 一次更新多步**（文件每行 `<id> <状态>`，`#` 开头为注释；⭐ **多步状态更新一律走 `--batch`，不要逐条调**——批量只需一次进程启动，实测 8 步 1544 ms → 196 ms（**−87%**）。省的是**调用次数**，不是"少留痕"；**禁止**为省这点时间手改 YAML，那会破坏"留痕不靠记忆"。v2.5.3 就已实现，v3.4.0 才补上文档引导）；**`decide` 追加一条能力决策记录到 meta.决策记录**（`--point --basis --capability --choice`，四参数均必填）；**`revise` 追加一条计划修订到 meta.计划修订**（`--trigger R1–R6 --change [--unchanged]`，上限 3 条，超限即 FAIL）；**`selftool` 追加一条自研工具/技能登记到 meta.自研工具**（`--name --purpose --scenario --repo`，四参数均必填，v3.1.0） | `checks.py plan tasks/x/plan.yaml --base "E:/ChatGPT/工作流"`<br>`checks.py decide tasks/x/plan.yaml --point "缺外部事实" --basis "本机推不出" --capability 事实 --choice "gh api repos/…"`<br>`checks.py selftool tasks/x/plan.yaml --name "foo.py" --purpose "…" --scenario "…" --repo "https://github.com/…/blob/main/scripts/foo.py"` |
| setup_env.ps1 | 初始化 venv 与依赖（requests / openpyxl / python-docx / pypdf / pyyaml / **duckdb** / **ast-grep-cli**） | `powershell -File scripts\setup_env.ps1` |
| ai_call.py | 调 AI 模型：`--model` 覆盖、`--system-file`、`--max-tokens`、`--temperature`、`--stats` 用量回显、`--batch-file` + `--concurrency` 批量并发（结果落 JSONL） | `ai_call.py --batch-file prompts.txt --concurrency 3` |
| http_fetch.py | 联网抓取：`--github-repo a/b,c/d` 指标实测（并发 + 限流退避 + 缓存）、**`--github-search "<query>"` 按关键词搜仓库**（限定符 `language:` `stars:` `topic:` `pushed:`；`--search-sort stars,forks,updated`、`--search-limit`）、**`--github-code-search "<代码> repo:owner/name"` 按代码内容搜文件（⭐强制 token，返回仓库/路径/命中片段）**、**`--dry-run` 只打印将请求的 URL 与附加头（不发请求，无 token 也能验证参数构造）**、`--text` HTML→文本、`--grep`/`--max-chars` 定向提取、`--no-cache`/`--ttl` 控缓存、**`--check-links` 批量探活（只取状态码不下载正文，并发 8，交付外链前必跑；403 会换头重试并按 CDN/WAF 响应头分类）** | `http_fetch.py --github-search "code search language:rust stars:>500" --search-limit 20`<br>`http_fetch.py --github-code-search "read_parquet repo:duckdb/duckdb" --dry-run` |
| **data_query.py** | **大数据集/大目录检索（DuckDB）**：`files` 目录概览（文件数/总大小/按扩展名/大文件）、`big` 列大文件（**默认跳过 `.venv`/`node_modules` 等依赖与缓存目录；旧口径加 `--no-skip`**）、`find` 跨文件正则检索（带行号，DuckDB `read_text`）、`sql` 对 Parquet/JSON/CSV **零导入直接跑 SQL** | `data_query.py big . --min-mb 100`<br>`data_query.py sql "SELECT count(*) FROM read_parquet('x.parquet')"` |
| office_io.py | Office 读写：excel-read（xlsx/csv）、excel-write（单表/多表，默认表头加粗+冻结首行+自适应列宽）、word-read/write、pdf-extract/merge | `office_io.py excel-read data.csv --fmt json` |
| run_stage.ps1 | 状态检查 + 一键调脚本 | `run_stage.ps1 http_fetch.py <URL>` |
| **ast-grep**（`ast-grep-cli`，已装入 venv） | **跨行/结构模式检索 + 符号检索**。`run -p '<pattern>' -l py <路径>` 结构匹配；`outline <文件>` 列符号（替代 ctags 需求）；`scan` 跑规则文件。⚠️ pattern **不支持正则**（`\|`/`.*`/`\w` 无效），且**复合语句必须写全**（`except:` 单独不是合法 pattern，须写成 `try: $$$B except: pass`）。`sg` 命令**已废弃**，用 `ast-grep`。MIT / Windows 原生 / 离线 | `ast-grep run -p 'print($$$A, file=sys.stderr)' -l py scripts/` |
| **archive_tasks.py** | **任务目录归档**（阶段 6 治理）：`--older-than <YYYY-MM-DD>` 或 `--dirs "a,b,c"` 选定 → 默认 **dry-run**（只看计划），`--apply` 执行。**只移动不删除**；带**前置门禁**——被 `SKILL.md`／`references/*.md` 引用的目录自动剔除并打印引用出处（归档它们会使「文档引用完整性」FAIL）；移动前后用逐文件 sha256 快照自证零丢失。退出码 0／1／2 | `archive_tasks.py --root . --older-than 2026-09-11`<br>`archive_tasks.py --root . --older-than 2026-09-11 --apply` |
| **gen_skill_index.py**（v3.4.0 自研） | **技能库索引生成/校检**：默认扫描各技能 `SKILL.md`（跳过 `_backup-*`/`_archive`/`.git`）→ 生成 `~/.workbuddy/skills/README.md`（**按簇**分组：目录名首连字符前缀出现 ≥2 次才成簇，不足即归「独立技能」）。`--check` 只读校检新鲜度（`exit 0` 新鲜／`1` 过期或缺失／`2` 用法错）；`--print` 只打印；`--workspace <工作区根>` 把项目级技能一并纳入；`--roots`/`--index` 覆盖路径。**新鲜度用「源集合内容指纹」（`目录名+SKILL.md 内容 sha1` 再 sha1），刻意不含 mtime** —— 比 mtime 的两种写法都踩过坑：比索引自身 mtime 会被未来 mtime 永久判过期；指纹带 mtime 则 `touch` 一下（内容没变）也误报。⚠️ 索引 ≈1.7k tok，全量读 25 份 frontmatter ≈17.6k tok（本报告口径），故阶段 0 先 `--check` 再读索引 | `gen_skill_index.py --check`<br>`gen_skill_index.py --workspace "E:/ChatGPT/工作流"` |
| **perf_baseline.py**（v3.4.0 自研） | **本地可测耗时基线**：`--label before\|after` 采一组固定测点（解释器启动／`gh auth token`／`checks.py skill`／`plan`／`status`／`mark` 逐条 vs `--batch`／`py_compile` 两条路／`--github-repo` 缓存命中／`search --dry-run`），`--compare <json>` 出 before/after 表。**内置两条自证判据**：① **环境一致性前置**——本机 `python` 启动受 `PYTHONPATH` 注入的 shim 影响可差 4 倍，两次基线比值 ≥1.5 即判「不可直接比绝对值」② **同树对照**——用 `_backup-v3.3.0` 的旧 `checks.py` 跑**同一棵** scripts/ 树（新增脚本会让两次基线的被测对象不同，直接比绝对耗时是假的）。⚠️ **不测 LLM 推理耗时**（不在本机产生）、**不测 token**（无离线 tokenizer） | `perf_baseline.py --label before --out .` <br>`perf_baseline.py --label after --compare perf_baseline_before.json` |
| **publish_tools.py**（v3.1.0 自研） | **自研工具/技能的公开留痕**：`init` 创建**公开**仓库（默认 public，**不提供 `--private`**；**幂等**——已存在且 public 则跳过，已存在但 private 则 FAIL 并给改可见性指引）；`push` 推送本地文件（默认 dry-run，`--apply` 才写；已存在文件带远端 `sha` 更新，幂等）；`verify` 校验仓库 `private=false` + 远端 blob sha 与本地一致（**版本一致的机器判据**）。走 `api.github.com`，优先 `gh api` 子进程、回退 urllib；凭据 `--token`→`GITHUB_TOKEN`→`GH_TOKEN`→`gh auth token`。`--repo` 或 `SELFTOOL_REPO` 覆盖目标仓（默认 `Garvin666/ai-workflow-tools`）。⚠️ 文本类扩展名默认做 **CRLF→LF 规范化**再算 sha（否则工作区 CRLF 会与仓内 LF 不一致，表现为"每次都判需推送"），`--no-normalize` 关闭。**技能根之外**的自研工具（如工作区 `tools/` 下的脚本）只能直接用它，`push_router` 不管辖 | `publish_tools.py init --name ai-workflow-tools --apply`<br>`publish_tools.py push --file scripts/foo.py --dest scripts/foo.py --apply`<br>`publish_tools.py verify --file scripts/foo.py --dest scripts/foo.py` |
| **push_ontology.py**（v3.2.0 自研） | **本体（Ontology）专用推送通道** → `ai-workflow-skill`：`--base <rev> --head <rev>` 增量推送本地 commit 范围。走 `api.github.com` Git Data API（blob → tree(**base_tree**) → commit → PATCH ref），远端混合仓故用 `base_tree` 精确列改动；内容从 `git cat-file blob` 取（**git 对象库天然 LF**，不用工作区 CRLF 字节）；新 blob 的 sha 与远端返回不符**立即抛错**（换行符口径的机器判据）。**默认 dry-run**，`--apply` 才写；`--allow-delete` 才删远端（默认只列出）；`--expect-remote <sha>` 锁基线防并发。`--repo` / `ONTOLOGY_REPO` 覆盖（默认 `Garvin666/ai-workflow-skill`）。由 v3.0 任务临时脚本 `tasks/技能增强-ai-workflow-v3.0-2026-09-15/tmp/push_incremental.py` 提升而来（v3.2.0 修正其三个隐患：藏在 tmp 不入仓、仓名硬编码、**默认就真推**） | `push_ontology.py --base 8f14ac61 --head HEAD`<br>`push_ontology.py --base X --head Y --apply --allow-delete` |
| **push_router.py**（v3.2.0 自研） | **两类资源的分流推送路由**：`classify` 离线分类 + **交叉校验**（标注头×`meta.自研工具` 登记表；漏登记／登记与实现不符／标注头缺项 → FAIL）；`push` 分流推两仓（本体 → 技能仓，自研工具 → 工具仓，默认 dry-run）。⚠️ **分流不是互斥二选一**：本体＝改动面全量，自研工具＝其子集，`scripts/` 下自研脚本属**双属**。判定三条件缺一不可：① 事实＝有 `[自研工具]`/`[自研技能]` 标注或 `SKILL.md` frontmatter `selfbuilt: true` ② 意图＝已登记 ③ **指向＝登记链接指向工具仓**（否则技能本体本身的登记会被误判成自研工具）。⚠️ **标注头判据的收窄（两处，都是实测换来的）**：只认**注释行**（否则 `ops.md` 的标注格式说明表会误命中）、且**文档类 `.md` 整体不走脚本分支**（markdown 的 `#` 是标题不是注释，而 `references/push-routing.md` 的标注模板**必须**写出 `# [自研工具] xxx.py` 这样的示例——不排除就会把文档判成"有标注头却没登记"，**修法是收窄判据而不是把文档改得躲开门禁**）。交叉校验 FAIL **阻塞两条通道**；本体通道失败则中止、不继续工具通道 | `push_router.py classify --files scripts/foo.py`<br>`push_router.py push --base X --head Y --apply` |
| **verify_push.py**（v3.2.1 自研） | **推送结果的独立验收器**（与三条推送通道**零代码共享**）：`--rev <本地 rev> [--prev-remote <推送前远端 HEAD>] [--expect-remote <sha>] [--repo] [--tools-repo] [--skill-dir] [--allow-dirty]`。**1 条前提 + 7 条实质判据** —— 判据 0（前提）：工作区干净 + rev 可解析；判据 1：远端 HEAD 等值/非空跑；判据 2：本地 rev ⊆ 远端且 blob sha 逐一相等；判据 3：远端独有项早于本次推送 + blob 数不减少；判据 **4 / 6**（同一段两项）：每个自研工具在工具仓的 sha == 本地**独立重算**值（CRLF→LF 归一化）／**跨仓一致性**（同文件两仓 sha 必须相同）；判据 5：发布物自证（远端 `SKILL.md` 自身 + 它指向的下沉手册）；判据 7：两仓 public。**期望版本从本地 rev 的 SKILL.md 自动推导；自研工具清单从 `tasks/**/plan.yaml` 的 `meta.自研工具` 自动发现**（`tasks/*/tmp/` 不读——那里是探针伪造的假登记）。口径坑内建：`git -c core.quotePath=false ls-tree`、混合仓用「本地⊆远端」而非「集合相等」。几种"像失败其实不是"的情形显式判 **SKIP**（未传 prev-remote／登记链接为「待推送」／登记文件只存在于工作区未入版本控制）。退出码 0=全通过、1=有 FAIL、2=基建错误。⚠️ **`--skill-dir` 同时是本地 git 根**（v3.4.0 补的功能缺口：此前它只喂 `read_registrations()`，而 `git()` 的 `cwd` 硬编码为脚本位置 → 「指定技能根来验收」文档上成立、实现上不成立，混合仓的另一条本地来源**根本无法被本脚本验收**）。⚠️ **多通道同轮推送须按通道分跑**（口径与两条结构性限制详见 `push-routing.md` →「推送后的独立验收：多通道口径与两条结构性限制」） | `verify_push.py --rev HEAD --prev-remote db2a3e58`<br>`verify_push.py --rev HEAD --prev-remote X --expect-remote Y`<br>`verify_push.py --skill-dir "E:/ChatGPT/工作流" --rev <工作区 rev> --expect-version <v> --prev-remote X` |
| **outbound_scan.py**（v3.5.0 自研） | **出站前扫描的可机器化部分**：检测「将外发的文件」是否含本机绝对路径。两级严重度 —— **FAIL** 含用户名的主目录路径（`C:\Users\<具体用户名>\…`，出站清单第 4 项的字面要求）；**WARN** 其它具名盘符路径（第 3 项「内部目录结构」，**只提示不阻断** —— 一并升级为 FAIL 会让存量档案大面积变红，处置需人拍板）。**已掩码形态两侧都不命中**（`<用户名>` / `%USERNAME%` / `$HOME` / `~/.workbuddy/`）—— 报它们等于惩罚已按规则脱敏的文件。行内豁免 `outbound-scan:allow`。`--list <文件>` 按清单扫（**扫的是指定推送清单，不是全仓**）；**已被 `push_router.py` 导入为推送前门禁，导入失败即阻塞（fail-closed）** | `outbound_scan.py --list push_list.txt`<br>`outbound_scan.py "a.md" "b.py" --json` |
| **guard_constants.py**（v4.2.0 自研） | **跨模块同名常量的同源守卫**（技能库卫生第 4 条）：把 `scripts/` 下同名顶层常量的关系登记成 `GROUPS` 清单，机器校验漂移即 FAIL。两类关系 —— ① **必须同源**（取值应相同：`RETRY_DELAYS` / `CODE_EXT` / `REF_PATTERN` / `SELFTOOL_KEYS`）② **刻意不同**（语义不同、合并会改变行为：`TEXT_EXT` 的真子集关系、`DEFAULT_REPO`/`DEFAULT_BRANCH` 指向不同仓）—— 后者**不允许被「顺手统一」**，但关系被悄悄打破同样要能发现。自带**阴性对照** `--selftest`（注入 4 类漂移：改一侧取值／少登记一项／打破子集／把两个不同默认值改成一样） | `guard_constants.py`<br>`guard_constants.py --selftest` |
| **gate.py**（v4.3.0 自研） | **统一运行时闸门**：跑在**删改既有文件之前**，把红线③的**范围判定**与**风险判定**分离后统一收口。`check <路径…> --base <工作区根> --intent <read\|write\|delete\|move>`；判定三态 **INSIDE / INFRA（基础设施例外）/ OUTSIDE**；**基础设施例外 ≠ 高风险豁免** —— `read` 豁免，`write`/`delete`/`move` 仍须当次授权（`needs_authorization()`）。**fail-closed**：`checks.py` 的 `INFRA_EXCEPTIONS` 加载失败即拒绝，不静默放行。退出码 **0 放行／1 拒绝／2 用法错／3 fail-closed**；`--allow-outside <理由>` 显式授权放行；越界与授权事件记 `~/.workbuddy/cache/ai-workflow/gate_audit.jsonl`（常态 INSIDE 不记，零噪音）；`--selftest` 13 项含**决策层×意图对照**（"范围判对 ≠ 决策判对"的回归） | `gate.py check "<技能根>/scripts/x.py" --base "<工作区根>" --intent delete`<br>`gate.py check … --allow-outside "用户已确认"`<br>`gate.py --selftest` |

各脚本详细参数：加 `--help`。

## 三、环境变量

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| AI_API_KEY | AI 调用凭据（必填，不落日志） | — |
| AI_API_BASE / AI_MODEL | API 地址 / 模型 | https://api.deepseek.com/v1 ／ deepseek-chat |
| AI_PRICE_IN / AI_PRICE_OUT | 成本估算单价（元/百万 token） | 未设则只报 token |
| GITHUB_TOKEN | GitHub API 鉴权。**解析优先级：`--token` → `GITHUB_TOKEN` → `GH_TOKEN` → `gh auth token`（gh CLI 已登录则免配置，核心限额 60 → 5000/小时）**。做形态校验，非凭据文本会被忽略并告警 | 未设则匿名（60/小时） |
| AIWF_HTTP_TTL | 抓取缓存有效秒数（0 = 关闭） | 3600 |
| AIWF_CACHE_DIR | 缓存目录 | ~/.workbuddy/cache/ai-workflow/http |
| AIWF_GH_CONCURRENCY | GitHub 多仓库并发数 | 5 |
| AIWF_GH_CORE_LIMIT_ANON ／ \_AUTH | `gh_core` 桶窗口内自限次数（**按有无凭据分档**，v3.4.0/P8）。带凭据时官方配额 5000/h，旧版无条件按匿名 60/h 自限 → 多仓库对比时会白等（单次最多 60s） | 60 ／ 4500 |
| AIWF_GH_SEARCH_LIMIT_ANON ／ \_AUTH | `gh_search` 桶自限次数（同上分档）。官方：匿名 10/min、认证 30/min | 10 ／ 30 |
| AIWF_GITHUB_MAX_WAIT / MAX_RETRY | 限流单次等待秒数 / 重试次数 | 60 ／ 2 |

## 四、环境检测

**执行顺序（与 §一 的优先级一致，勿颠倒）**：① 先跑下面的**最小探测命令**（Bash 可直接照抄）；
② 只有在需要**创建 venv / 安装依赖**时，才去**真实交互式终端**跑 `setup_env.ps1`。

⚠️ `setup_env.ps1` 的两个环境坑：a) **不能从 Bash 工具调用**（命令文本命中"从 Bash 调用 PowerShell"会被安全策略整条拦截）；b) 在本机沙箱下它启动的**原生子进程 stdout 会丢、退出码读不到** —— 需要它的输出时请**先重定向落盘、再用读文件的工具读**，不要依赖回显。

**最小探测命令（推荐先跑这条；不依赖 ps1，任何环境都能照抄）**：

```bash
PY="$HOME/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"
AST="$HOME/.workbuddy/binaries/python/envs/ai-workflow/Scripts/ast-grep.exe"
"$PY" -c "import requests, openpyxl, docx, pypdf, yaml, duckdb; print('deps OK')"
"$AST" --version
```

> ⚠️ **v2.5.2 更正**：本节原先把 `"$PY" -m ast_grep_cli --version` 标为「首选」，该命令**恒失败**——
> `ast_grep_cli` 包**没有可执行的模块入口**（`import ast_grep_cli` → `ModuleNotFoundError`，
> `find_spec` → `None`），能出结果全靠后半段的 `||` 兜底。已改为**直接调用 `Scripts/ast-grep.exe`**。

**首次使用或需要建环境时（真实交互式终端）**：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1
```

检查项：managed python 存在 → venv 存在（否则创建）→ **依赖标记检查**（`$pkgDir` 按 site-packages 目录判定；**CLI-only 包**如 `ast-grep-cli` 按 venv `Scripts/` 下的**可执行文件**判定，比 dist-info 更可靠；**未映射项显式 FAIL**；不依赖 pip 退出码）→ AI_API_KEY 是否设置（仅提示）。

> ⚠️ **依赖自检的两条纪律**（v2.5.1 修复的真实缺陷教训）：① **未映射的依赖必须显式 FAIL**，不得静默通过——历史上 `duckdb`/`ast-grep-cli` 因缺映射取到空值，而 `Join-Path` 遇空子路径会**返回父目录本身**，使 `Test-Path` 恒为 True，缺失也报 `[ OK ]`；② **改写过的存在性检查必须配一次负向测试**（故意移除目标，确认它真的报 FAIL）。

依赖全量：`requests` / `openpyxl` / `python-docx` / `pypdf` / `pyyaml` / `duckdb` / `ast-grep-cli`。
装完后可直接用 venv 内的可执行文件：`<venv>/Scripts/ast-grep.exe`（`sg.exe` 同在，但**已废弃**）。

## 五、故障排查

| 现象 | 处理 |
| --- | --- |
| 控制台乱码 | 脚本已强制 UTF-8；仍乱码用 `chcp 65001` |
| AI 调用 401/超时 | 检查 AI_API_KEY / AI_API_BASE / AI_MODEL；脚本自带 3 次指数退避 |
| GitHub API 403 | 多为**匿名限流**（非权限），脚本自动识别并退避；持续限流会提示设 GITHUB_TOKEN，或改用已有数据并标注"未实时校验" |
| 抓取结果疑似旧数据 | 缓存导致——加 `--no-cache`，或调小 `AIWF_HTTP_TTL` |
| `checks.py` 报缺 pyyaml | 用错解释器了——必须用 venv：`$HOME/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe`。脚本会**以退出码 2 中止**并给出该提示（早期版本会继续输出 `FAIL=0` 造成假绿，v2.3 已修） |
| `checks.py plan` 报 `mapping values are not allowed here` | **plan.yaml 某个未加引号的值里出现了 ASCII 冒号 `: `**（如 `（A: GitHub API…）`），YAML 会把它当成嵌套映射。改用全角 `：`/`－`，或整段加双引号。此错由对账当场拦下，**不要手工编辑后再忘跑对账** |
| `checks.py plan` 报交付物缺失 | 逐项查：① 路径是否写全（缩写如「选品分析.yaml」无法定位）；② 括号注释是否多余；③ `--base` 是否用了 Windows 字面路径（**相对路径只以 `--base` 为基准**，Git Bash 的 `$(pwd)` 会给出 `/c/...` 这种 pathlib 解析不了的形态）；④ **交付物是否在工作区根之外** —— v2.5.2 起候选**只有 `base/<p>`**，跨根引用（如改技能本体的 `skills/ai-workflow/...`）**必须写绝对路径**。旧的 `~/.workbuddy/<p>` 与 `base.parent/<p>` 两条兜底通道已移除：前者让工作区内不存在的交付物被同名文件"救活"（假 PASS），后者让落在工作区根之外的交付物也判通过（撞红线③） |
| 抓取失败但 `--out` 文件还在 | 脚本会打印告警（避免把旧内容当成新结果用）；确认后重跑或改用其它来源 |
| 报告里的外链点开是 404 | 交付前必须跑 `--check-links` 探活；子代理转述的 URL 尤其容易错（实战中 OWASP ZAP 链接被转述成已 404 的旧路径，另有一次抓到**子代理编造的日期型假链接**：站点根 200、该文章路径 404、原文还带省略号） |
| 链接返回 502 `Tunnel connection failed` | **本机出口隧道限制，不是站点失效**。已知稳定 502 的域名：`huggingface.co`、`jina.ai`、`console.cloud.google.com`。应标注「本机环境无法验证」，**不要判为站点挂了** |
| 探活结果里 403 怎么读 | 403 **不等于失效**。脚本会换浏览器头重试一次，再按响应头分类：`403-CDN反爬(Cloudflare…)`、`403-WAF反爬(Akamai/Imperva…)`、`403-限流`、`403-拒绝(需授权或反爬，无法自动区分)`。前两类**人工可访问**，不得据此改链接；只有 404 才算失效 |
| `academy.hackthebox.com` 探活失败 | 本机是 **SSL 握手超时（本地出口限制）**，不是反爬也不是站点下线；输出为 `ERR 网络失败: handshake operation timed out`。需与 403 反爬区分描述 |
| 设了凭据但 GitHub 仍是匿名限额 | 检查是否用错解释器/子进程未继承环境变量；`gh auth status` 可能误报未登录，直接用 `gh auth token` 验证。凭据**只打印前缀掩码**，不要 print 完整 token |
| 在 Bash 工具里跑的命令被安全策略拒绝 | 命令文本中出现 `PowerShell` 字样（例如把该词写进注释、heredoc 或 commit message）会被判为"从 Bash 调用 PowerShell"而整条拦截。**改写措辞**（用 `ps1`／"命令行" 代替），或改用编辑工具/`Write` 落盘脚本再执行 |
| 沙箱内 PowerShell 读不到子进程退出码 | 本机沙箱下 `.ps1` 内启动的原生进程 `$LASTEXITCODE` 可能为空、stdout 可能丢失，导致"空值 -ne 0 → 误判失败"。**脚本成败判定不要依赖退出码**，改用文件系统事实（如查 site-packages 目录）或改用 Bash 直接调 venv 解释器验证 |
| GitHub 搜索/取数突然全 403 | 分清两套配额：core 为 **60 次/小时**（匿名），search 为 **10 次/分钟**（匿名）/ 30 次/分钟（认证）——search 每分钟自动重置，可等 1 分钟重试而不必等 1 小时 |
| `data_query.py find` 报「glob 未匹配到任何文件」 | ⚠️ **DuckDB 的 glob 不支持 `{a,b}` 花括号展开，且是静默零命中**（曾因此误判"没有该内容"）。脚本已加防呆：先 `glob()` 计数，0 就报错。多个模式请用**逗号分隔** |
| `data_query.py find` 命中 0 但确认有内容 | 检查 `--glob` 是否用了花括号；确认扩展名在默认文本清单内（默认扫 57 类文本扩展名，二进制会跳过） |
| `data_query.py` 报缺 duckdb | 用 venv 解释器；或 `setup_env.ps1`（依赖清单已含 duckdb） |
| `ast-grep` 报 `Multiple AST nodes are detected` | pattern 写法问题，不是语法错。两种原因：① **复合语句没写全**（`except:` 单独不合法 → 写成 `try: $$$B except: pass`）；② 用了正则语法。参见 https://ast-grep.github.io/guide/pattern-syntax.html |
| `ast-grep` 提示 `sg is deprecated` | 用 `ast-grep` 命令，不要用 `sg`（两者都在 venv 的 Scripts 下） |
| `--github-search` 返回 403 / Validation failed | 分两种：**403＝限流**（匿名搜索 10 次/分钟，认证 30 次/分钟）；**Validation failed＝查询语法超限**（q ≤256 字符、AND/OR/NOT ≤5 个） |
| `--search-sort updated` 结果全是几十 star 的小仓库 | 正常现象——按最近更新排序会把新建仓库排前。找成熟项目用默认 `stars`，找活跃新项目才用 `updated` |
| `--github-code-search` 报「强制要求认证」 | **不是限流，是 `/search/code` 官方强制登录**（匿名必返 401，已实测）。设 `GITHUB_TOKEN=<PAT>` 后重试，认证后限流 10 次/分钟。只想按仓库名/描述找项目改用 `--github-search`（匿名可用） |
| `--github-code-search` 命中 0 但代码确实存在 | 三个已知原因：① 只搜**默认分支**；② 大仓库可能**未被索引**；③ 查询里没加 `repo:`/`user:`/`org:` 限定符时范围太宽反而被截断。加限定符重试 |
| `--github-code-search` 结果没有命中片段 | 缺 `Accept: application/vnd.github.text-match+json` 头——脚本已内置；若裸 curl 调用需自行加上 |
| 想确认请求参数对不对但不想消耗配额 | 加 `--dry-run`：打印完整 URL + 附加头 + 认证状态后即返回，两个搜索端点都支持 |
| `--dry-run` 没输出 URL | 它只对 `--github-search` / `--github-code-search` 生效，脚本会打印告警提示本次忽略 |
| ps1 包装器只打印状态检查、产物没生成 | 本宿主通道下**原生子进程未执行**（`$LASTEXITCODE` 残留为 0，看起来"成功"）。v2.5.1 起会判为 `[FAIL]` 并退出 1。**改用 §一 的首选方式（直接调 venv 解释器）** |
| 从 Bash 工具执行 `powershell -File xxx.ps1` 被拒 | 报 `Command blocked for security`（Bash 里禁止调 ps1）。改用 §一 的直接调用；确需 ps1 时改用本工具链的 **PowerShell 工具**，并注意**其 stdout 可能不回显，需落盘再读** |
| `office_io.py excel-write` 直接喂 CSV 报 `JSONDecodeError: Expecting value: line 1 column 1` | `excel-write` **只接受 `--rows` 的 JSON**。先 `excel-read <csv> --fmt json > rows.json`，再 `excel-write <out.xlsx> --rows rows.json`（见 SKILL.md 阶段 4 第 2 条） |
| `checks.py status` 报 `[FAIL] tasks/ 目录存在` 但目录确实有 | 它按**当前目录**找 `tasks/`。加 `--workspace <工作区根>`；任务目录应建在工作区根下的 `tasks/`（v2.5.1 起 FAIL 文案会附带此提示） |
| 依赖自检报 `[ OK ]` 但实际 `import` 失败 | 早期的空映射缺陷：`Join-Path` 遇空子路径**返回父目录本身**，`Test-Path` 恒为 True → 缺失也报 OK（`duckdb`/`ast-grep-cli` 曾如此）。v2.5.1 已修（未映射项显式 FAIL）。若怀疑环境，用 §四 的 `import` 探测命令直接验证 |
| `checks.py plan` 报**所有**交付物都缺失，但文件确实存在 | 多半是 `--base` 传了 **Git Bash 风格的 POSIX 路径**：`$(pwd)` 返回 `/c/Users/...`，Windows 下 `pathlib` 解析不了，于是全部判缺失（**假 FAIL**）。改用字面 Windows 路径或 `C:/...` 形式 |
| `checks.py plan` 报 `meta.工作区根 — 为空` | 该计划建于 **v2.4.4 之前**（该版本才把「工作区根」列为必填）。**属历史遗留，不是新引入的回归**：给旧计划补上 `工作区根` 即可，或按废弃处理 |
| `checks.py plan` 从不报 FAIL，文件明明不存在 | 早期路径候选过宽：相对路径会在别处再试一遍，把同名文件当成交付物命中（假 PASS）。**v2.5.2 已把候选收敛为仅 `base/<p>`**（v2.5.1 只收窄到「本任务基准／`~/.workbuddy/<p>`／基准的上级」三处，后两条仍属同型缺陷）；技能内部文件请写**绝对路径** |
| 出现 `[FAIL] 已熔断：不得作为可交付物` | 该任务已熔断（meta `熔断状态: 已熔断` 或存在步骤状态 `熔断`）——**这是设计意图，不是 bug**。产出并补全《熔断报告》后交用户决策；**只有用户能复位**，且复位是**两步**（都得做，只改 meta 仍会被"步骤状态=熔断"阻断）：`checks.py mark <plan> --fuse 正常` + `checks.py mark <plan> <id> <非熔断状态>`，随后重跑 `plan` 确认 FAIL 清零并留痕 |
| PowerShell 报"无法识别" | 用 `&` 加引号完整路径调用 |
| Excel 打开乱码 | 确认写文件用默认 `utf-8-sig` |
| 批量 AI 调用全部失败 | 多为 API key 无效/欠费，检查 JSONL 里的 error 字段 |
| `npm install` 跑十几分钟不动 | 本机到 `registry.npmjs.org` 单次 packument RTT **2~16s**，`node_modules` 迟迟不生成属**正常但极慢**（实测 18 分钟未完成）。**不要切 npmmirror**：本机走代理时 `registry.npmmirror.com` 只返回空的 `200 Connection Established` 隧道，无响应体；`registry.npm.taobao.org` 直接超时。正确解法是项目内 `.npmrc` 设 `maxsockets=64` + `fetch-retries=5`（实测 18 分钟 → 4 分钟） |
| `npm install` 报 `ETARGET No matching version found for X@=1.2.3`，但该版本确实存在 | ⚠️ `.npmrc` 里的 **`prefer-offline=true` 用的是旧 packument 缓存**，新发布的版本不在其中，于是误报"版本不存在"（实测 `@oxc-project/types@0.149.0` 明明就是 latest 却解析不到）。**去掉 `prefer-offline`**，只保留 `maxsockets` |
| 用 curl 取 `registry.npmjs.org/<pkg>` 后 `json.load` 报 `Unterminated string` | 全量文档太大，**经管道/head 会被截断**（react-dom 可达 8MB+）。加头 `-H "Accept: application/vnd.npm.install-v1+json"` 取精简元数据；只要单版本就用 `/<pkg>/<version>` 或 `/<pkg>/latest` 这类小文档 |
| `agent-browser open` 无任何输出即被 SIGTERM | 本机沙箱**拦截浏览器启动**（Chromium 已装在 `%LOCALAPPDATA%\ms-playwright`，但 `open` 连一行日志都不给就死）。环境变量里的 `HTTP_PROXY=http://127.0.0.1:54912` 会让 localhost 也走代理，即便 `unset` 全部 proxy 变量 + 设 `NO_PROXY` 仍无效。**不要在无头浏览器上反复重试**：改派可判定的静态信号（如 `vite build` 全量构建过一遍模块），并把"运行时渲染"显式登记为人审点交用户确认 |
| `checks.py skill` 报「文档引用完整性 — 缺失：某脚本名（来自 ops.md）」 | 该检查是**扁平**的：任何**反引号包裹**且后缀为 md／yaml／py／ps1 的 token 都被当成**相对技能根的路径**，用 `skill_dir` 及其 `scripts`／`assets`／`references` 子目录做存在性判断，**不区分"引用"与"举例提及"**。所以文档里用裸文件名举例会被判缺失（v3.0.1 实测：一条变更日志举例提到某个测试脚本的裸名，自检当场 19/20 FAIL）。**两种改法**：① 改写成**完整相对路径**（推荐——它真正可被核验，且该文件日后被移动时门禁会 FAIL 提醒你同步引用）；② 去掉反引号，使其不被识别为路径 |

## 六、链接收集与核验 SOP（调研类任务交付前必跑）

调研类交付物里的每一个外链都要走完这四步，缺一步不得交付：

```bash
# 1. 提取：从所有 findings / 草稿里抓 URL
grep -ohE "https?://[A-Za-z0-9._~:/?#@!$&'*+,;=%()-]+" findings-*.md \
  | sed 's/[.,;:)]*$//' | sort -u > all_urls.txt

# 2. 去重后剔除不可直接验证的（模板 URL、纯 API 端点会误导）
grep -vE "api\.github\.com" all_urls.txt > check_urls.txt

# 3. 探活（只取状态码，不下载正文；并发 8。单条耗时受超时条数影响极大：
#    正常条 ~150-260ms，遇超时条可达数秒——不要把它当固定基线）
"$PY" scripts/http_fetch.py --check-links check_urls.txt --concurrency 8

# 4. 分类标注 —— 四类含义完全不同，禁止混为一谈
```

**分类标准（务必区分）**：

| 状态 | 含义 | 处理 |
| --- | --- | --- |
| `200` | 可达 | 保留 |
| `404` | **真失效** | 必须剔除或修正；⚠️ 重点怀疑"日期型 URL"（`/2026/04/17/...`），这是子代理最常编造的形态 |
| `403 / 429` | 反爬或限流 | **不是失效**，标注「可达但被拒绝」即可 |
| `ERR 502 Tunnel` | **本机出口问题** | 标注「本机环境无法验证」，不得判为站点失效 |

**硬规则**：子代理产出的链接**必须全量探活后才可进交付物**。实战数据：140 条中查出 3 条 404，其中 1 条是**编造的日期型假链接**，且它正被用于支撑一条结论。
