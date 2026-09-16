# 脚本用法与环境运维（按需加载）

> 本文件由 SKILL.md 拆出，承载「脚本速查 / 环境检测 / 故障排查 / 变更日志」。
> 环境：Windows + Git Bash，脚本一律用 ai-workflow venv 的 python 运行。

## 一、运行方式

调用一律用 PowerShell `&` 运算符或 Git Bash 绝对路径：

```bash
SK="C:/Users/26717/.workbuddy/skills/ai-workflow"
PY="C:/Users/26717/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"
"$PY" "$SK/scripts/checks.py" skill
```

也可用 `scripts/run_stage.ps1 <脚本名> [参数...]`（自带状态检查 + **执行后自检**）。

> **优先级（重要）**：**首选**上面这种「venv 解释器绝对路径 + 脚本」的直接调用；`run_stage.ps1` 只作为**交互式终端**里的便捷入口。原因：在本机的某些宿主通道下，ps1 内启动的**原生子进程根本不会执行**（表现为只打印状态检查、退出码 0、产物不生成）。自 v2.5.1 起脚本已把「子进程未跑起来」判为 `[FAIL]` 并以 1 退出，但这只是防呆，不是修复宿主差异。

## 二、脚本速查

| 脚本 | 用途 | 示例 |
| --- | --- | --- |
| **checks.py** | `skill` 技能自检（frontmatter/引用完整性/模板 schema/py_compile）；`plan` 计划校验 + Anti-drop 对账 + **熔断门禁**（`熔断状态: 已熔断` 或步骤状态 `熔断` → 直接 FAIL）；`status` 工作区任务总览（交付物完成度 + 归档建议 + **已熔断任务 ⚡ 标记与 WARN 汇总**）；`mark` 更新步骤状态（含 `熔断`）与 **meta 熔断状态**（`--fuse 正常\|已熔断`，复位用 `--fuse 正常`，不必手改 YAML）；**`decide` 追加一条能力决策记录到 meta.决策记录**（`--point --basis --capability --choice`，四参数均必填）；**`revise` 追加一条计划修订到 meta.计划修订**（`--trigger R1–R6 --change [--unchanged]`，上限 3 条，超限即 FAIL）；**`selftool` 追加一条自研工具/技能登记到 meta.自研工具**（`--name --purpose --scenario --repo`，四参数均必填，v3.1.0） | `checks.py plan tasks/x/plan.yaml --base "E:/ChatGPT/工作流"`<br>`checks.py decide tasks/x/plan.yaml --point "缺外部事实" --basis "本机推不出" --capability 事实 --choice "gh api repos/…"`<br>`checks.py selftool tasks/x/plan.yaml --name "foo.py" --purpose "…" --scenario "…" --repo "https://github.com/…/blob/main/scripts/foo.py"` |
| setup_env.ps1 | 初始化 venv 与依赖（requests / openpyxl / python-docx / pypdf / pyyaml / **duckdb** / **ast-grep-cli**） | `powershell -File scripts\setup_env.ps1` |
| ai_call.py | 调 AI 模型：`--model` 覆盖、`--system-file`、`--max-tokens`、`--temperature`、`--stats` 用量回显、`--batch-file` + `--concurrency` 批量并发（结果落 JSONL） | `ai_call.py --batch-file prompts.txt --concurrency 3` |
| http_fetch.py | 联网抓取：`--github-repo a/b,c/d` 指标实测（并发 + 限流退避 + 缓存）、**`--github-search "<query>"` 按关键词搜仓库**（限定符 `language:` `stars:` `topic:` `pushed:`；`--search-sort stars,forks,updated`、`--search-limit`）、**`--github-code-search "<代码> repo:owner/name"` 按代码内容搜文件（⭐强制 token，返回仓库/路径/命中片段）**、**`--dry-run` 只打印将请求的 URL 与附加头（不发请求，无 token 也能验证参数构造）**、`--text` HTML→文本、`--grep`/`--max-chars` 定向提取、`--no-cache`/`--ttl` 控缓存、**`--check-links` 批量探活（只取状态码不下载正文，并发 8，交付外链前必跑；403 会换头重试并按 CDN/WAF 响应头分类）** | `http_fetch.py --github-search "code search language:rust stars:>500" --search-limit 20`<br>`http_fetch.py --github-code-search "read_parquet repo:duckdb/duckdb" --dry-run` |
| **data_query.py** | **大数据集/大目录检索（DuckDB）**：`files` 目录概览（文件数/总大小/按扩展名/大文件）、`big` 列大文件（**默认跳过 `.venv`/`node_modules` 等依赖与缓存目录；旧口径加 `--no-skip`**）、`find` 跨文件正则检索（带行号，DuckDB `read_text`）、`sql` 对 Parquet/JSON/CSV **零导入直接跑 SQL** | `data_query.py big . --min-mb 100`<br>`data_query.py sql "SELECT count(*) FROM read_parquet('x.parquet')"` |
| office_io.py | Office 读写：excel-read（xlsx/csv）、excel-write（单表/多表，默认表头加粗+冻结首行+自适应列宽）、word-read/write、pdf-extract/merge | `office_io.py excel-read data.csv --fmt json` |
| run_stage.ps1 | 状态检查 + 一键调脚本 | `run_stage.ps1 http_fetch.py <URL>` |
| **ast-grep**（`ast-grep-cli`，已装入 venv） | **跨行/结构模式检索 + 符号检索**。`run -p '<pattern>' -l py <路径>` 结构匹配；`outline <文件>` 列符号（替代 ctags 需求）；`scan` 跑规则文件。⚠️ pattern **不支持正则**（`\|`/`.*`/`\w` 无效），且**复合语句必须写全**（`except:` 单独不是合法 pattern，须写成 `try: $$$B except: pass`）。`sg` 命令**已废弃**，用 `ast-grep`。MIT / Windows 原生 / 离线 | `ast-grep run -p 'print($$$A, file=sys.stderr)' -l py scripts/` |
| **archive_tasks.py** | **任务目录归档**（阶段 6 治理）：`--older-than <YYYY-MM-DD>` 或 `--dirs "a,b,c"` 选定 → 默认 **dry-run**（只看计划），`--apply` 执行。**只移动不删除**；带**前置门禁**——被 `SKILL.md`／`references/*.md` 引用的目录自动剔除并打印引用出处（归档它们会使「文档引用完整性」FAIL）；移动前后用逐文件 sha256 快照自证零丢失。退出码 0／1／2 | `archive_tasks.py --root . --older-than 2026-09-11`<br>`archive_tasks.py --root . --older-than 2026-09-11 --apply` |
| **publish_tools.py**（v3.1.0 自研） | **自研工具/技能的公开留痕**：`init` 创建**公开**仓库（默认 public，**不提供 `--private`**；**幂等**——已存在且 public 则跳过，已存在但 private 则 FAIL 并给改可见性指引）；`push` 推送本地文件（默认 dry-run，`--apply` 才写；已存在文件带远端 `sha` 更新，幂等）；`verify` 校验仓库 `private=false` + 远端 blob sha 与本地一致（**版本一致的机器判据**）。走 `api.github.com`，优先 `gh api` 子进程、回退 urllib；凭据 `--token`→`GITHUB_TOKEN`→`GH_TOKEN`→`gh auth token`。`--repo` 或 `SELFTOOL_REPO` 覆盖目标仓（默认 `Garvin666/ai-workflow-tools`）。⚠️ 文本类扩展名默认做 **CRLF→LF 规范化**再算 sha（否则工作区 CRLF 会与仓内 LF 不一致，表现为"每次都判需推送"），`--no-normalize` 关闭 | `publish_tools.py init --name ai-workflow-tools --apply`<br>`publish_tools.py push --file scripts/foo.py --dest scripts/foo.py --apply`<br>`publish_tools.py verify --file scripts/foo.py --dest scripts/foo.py` |
| **push_ontology.py**（v3.2.0 自研） | **本体（Ontology）专用推送通道** → `ai-workflow-skill`：`--base <rev> --head <rev>` 增量推送本地 commit 范围。走 `api.github.com` Git Data API（blob → tree(**base_tree**) → commit → PATCH ref），远端混合仓故用 `base_tree` 精确列改动；内容从 `git cat-file blob` 取（**git 对象库天然 LF**，不用工作区 CRLF 字节）；新 blob 的 sha 与远端返回不符**立即抛错**（换行符口径的机器判据）。**默认 dry-run**，`--apply` 才写；`--allow-delete` 才删远端（默认只列出）；`--expect-remote <sha>` 锁基线防并发。`--repo` / `ONTOLOGY_REPO` 覆盖（默认 `Garvin666/ai-workflow-skill`）。由 v3.0 任务临时脚本 `tasks/技能增强-ai-workflow-v3.0-2026-09-15/tmp/push_incremental.py` 提升而来（v3.2.0 修正其三个隐患：藏在 tmp 不入仓、仓名硬编码、**默认就真推**） | `push_ontology.py --base 8f14ac61 --head HEAD`<br>`push_ontology.py --base X --head Y --apply --allow-delete` |
| **push_router.py**（v3.2.0 自研） | **两类资源的分流推送路由**：`classify` 离线分类 + **交叉校验**（标注头×`meta.自研工具` 登记表；漏登记／登记与实现不符／标注头缺项 → FAIL）；`push` 分流推两仓（本体 → 技能仓，自研工具 → 工具仓，默认 dry-run）。⚠️ **分流不是互斥二选一**：本体＝改动面全量，自研工具＝其子集，`scripts/` 下自研脚本属**双属**。判定三条件缺一不可：① 事实＝有 `[自研工具]`/`[自研技能]` 标注或 `SKILL.md` frontmatter `selfbuilt: true` ② 意图＝已登记 ③ **指向＝登记链接指向工具仓**（否则技能本体本身的登记会被误判成自研工具）。交叉校验 FAIL **阻塞两条通道**；本体通道失败则中止、不继续工具通道 | `push_router.py classify --files scripts/foo.py`<br>`push_router.py push --base X --head Y --apply` |

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
| AIWF_GITHUB_MAX_WAIT / MAX_RETRY | 限流单次等待秒数 / 重试次数 | 60 ／ 2 |

## 四、环境检测

**执行顺序（与 §一 的优先级一致，勿颠倒）**：① 先跑下面的**最小探测命令**（Bash 可直接照抄）；
② 只有在需要**创建 venv / 安装依赖**时，才去**真实交互式终端**跑 `setup_env.ps1`。

⚠️ `setup_env.ps1` 的两个环境坑：a) **不能从 Bash 工具调用**（命令文本命中"从 Bash 调用 PowerShell"会被安全策略整条拦截）；b) 在本机沙箱下它启动的**原生子进程 stdout 会丢、退出码读不到** —— 需要它的输出时请**先重定向落盘、再用读文件的工具读**，不要依赖回显。

**最小探测命令（推荐先跑这条；不依赖 ps1，任何环境都能照抄）**：

```bash
PY="C:/Users/26717/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"
AST="C:/Users/26717/.workbuddy/binaries/python/envs/ai-workflow/Scripts/ast-grep.exe"
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
| `checks.py` 报缺 pyyaml | 用错解释器了——必须用 venv：`C:\Users\26717\.workbuddy\binaries\python\envs\ai-workflow\Scripts\python.exe`。脚本会**以退出码 2 中止**并给出该提示（早期版本会继续输出 `FAIL=0` 造成假绿，v2.3 已修） |
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

## 七、变更日志

- **v3.2.0（2026-09-16）新增「两类资源的分流推送路由」（SKILL.md 新小节，唯一事实源）**（用户 2026-09-16 指定：「本体（Ontology）→ `ai-workflow-skill`，自研工具 → `ai-workflow-tools`，并明确触发条件／判定依据／推送格式／冲突处理策略」）：
  - **四要素**：**①触发条件** —— 新增/更新 → 推（内容一致则幂等跳过）；重命名 → 本体按「删旧+增新」、工具按新路径更新；删除 → 本体须 `--allow-delete`、工具**不自动删**。**②判定依据** —— 本体＝路径落在技能仓内（改动面**全量**）；自研工具＝三条**同时**满足：*事实*＝有 `[自研工具]`/`[自研技能]` 标注块或 `SKILL.md` frontmatter `selfbuilt: true`，*意图*＝`meta.自研工具` 已登记，***指向*＝登记链接指向工具仓**。**③推送格式** —— 本体走 Git Data API + `base_tree`（一次 commit 覆盖全部改动，内容取 `git cat-file blob`）；工具走 contents API（**逐文件**，CRLF→LF 归一化）。**④冲突处理** —— 幂等跳过／本体 commit parent 取远端**当前** HEAD 且 ref 非强推（非快进即失败）／blob sha 不符**立即抛错**／混合仓远端独有项**永不删**／交叉校验 FAIL **阻塞两条通道**／本体通道失败即**中止**、不继续工具通道。
  - **⚠️ 最易误解点（已写进规则正文）**：**分流不是互斥二选一** —— 本体＝技能仓改动面的**全量**，自研工具＝其中的**子集**，故 `scripts/` 下自研脚本属**双属**：既作本体快照进技能仓，又作独立工具进工具仓。同一文件在两仓的 blob sha 相同，本身就是「版本一致」的天然证据。
  - **新增 `scripts/push_ontology.py`（v3.2.0 自研，本体通道）**：由 v3.0 任务遗留的临时脚本提升为正式脚本。原脚本三个隐患一并修掉：① 藏在 `tasks/技能增强-ai-workflow-v3.0-2026-09-15/` 的 `tmp/` 里，而 `tasks/*/tmp/` 按约定**不入版本控制** → 本体推送的唯一通道竟不在版本控制内；② 仓名硬编码；③ **默认就真推**（不加 `--dry-run` 即写远端），与同族的 `publish_tools.py`（默认 dry-run）**口径相反** → 分流器无法安全包装两条命令。现改为默认 dry-run（`--apply` 才写），并新增 `--allow-delete`（默认只列出待删项）与 `--expect-remote`（锁基线防并发）。
  - **新增 `scripts/push_router.py`（v3.2.0 自研，分流器）**：`classify`（离线分类 + 交叉校验）／`push`（分流推两仓，默认 dry-run）。把「标注头（事实）」「登记表（意图）」「链接指向（归属）」三者交叉：漏登记 → FAIL、登记与实现不符 → FAIL、标注头缺项 → FAIL、指向本体仓 → 只走本体通道。
  - **验证**：`checks.py skill` **23/23 FAIL=0**（21→23 系两个新脚本纳入 py_compile）；双脚本 `py_compile` 通过；**判定真伪用 6 个隔离 fixture 证明**（本体普通文件→OK；自研工具→双属；技能包 `selfbuilt` 且登记指向本体仓→**只走本体通道**；漏登记→FAIL；登记与实现不符→FAIL；标注头缺项→FAIL），**6/6 断言全过**；**两通道 dry-run 实测**——推送前后远端 HEAD 经 `gh api` 比对**不变**。证据见 `tasks/技能增强-ai-workflow-v3.2.0-2026-09-16/`。
  - **本轮撞出的 2 个真缺陷（均由实测暴露，非推演）**：
    - **① 技能包判定顺序陷阱**：`scan_selftool_header` 初版先扫正文标记、后判 frontmatter → `SKILL.md` 正文首段的 `[自研技能]` **输出标注**抢先命中脚本分支，技能包分支（读 `repo:`）**永不生效**，真实目录下 `SKILL.md` 被误报「漏登记」。修：技能包分支**前置**。
    - **② 技能包映射依赖中文命名**：初版靠 `名称` 里是否含「技能本体/技能包」把登记项映射到 `SKILL.md` —— 一改命名就失效。改为用 frontmatter `repo` 与登记链接**同仓比对**（基于数据本身，不依赖命名习惯）。
  - **诚实边界（未解决，如实登记）**：① 无跨会话基线时**无法检测「远端被第三方改写」**这类漂移（如需该保护，推送后记录 sha 并用 `--expect-remote` 显式约束）；② 工具仓删除**需人工在网页进行**（contents API 单文件通道未实现删除）；③ `push_router` 只管辖**技能根内**的文件，技能根外的自研工具直接用 `publish_tools.py`。

- **v3.1.1（2026-09-16）新增「技能库卫生」四条硬约定（SKILL.md 新小节）**（用户指定「现在就做一次归并梳理」→「全做」；起因是一次 32 个技能的全量盘点）：
  - **盘点的反直觉结论**：问题**不是内容重复**，而是**导航缺失 + 元数据不全 + 跨模块口径分叉**。段落级（≥60 字符）比对**零重复**；32 个技能中 24 个是孤岛（全库仅 8 条互引）。故**没有做任何"归并"**——改做三件事：建索引、补元数据、修口径分叉。
  - **规则本体（四条约定，`SKILL.md` §技能库卫生 为唯一事实源）**：① **先查索引再新建**（`.workbuddy/skills/README.md` 与同簇技能先过一遍，能扩写既有技能就不新建）② **`description` 必须带触发锚**（显式 `触发词：a / b / c` ／用户原话「…」／「当…时」，**三选一即可**，别把"没写触发词标签"误判成"没有锚"）③ **改了内容就 bump `version`**，且过时内容**加时点注记（`⚠️ 已过时（YYYY-MM-DD）`）不删原文**——删原文等于毁掉证据 ④ **同一物理量的判据必须跨模块同源**，且配**跨模块守卫测试 + 阴性对照**。
  - **⭐ 同一轮抓出的真缺陷（本约定第 4 条的直接证据，非假想）**：批量取数通道 `历史数据集/scripts/tencent_batch.py::_resolve_volume_lots` 用「绝对误差择近」，其**隐含阈值是 50.5**；而 `indicators/volume_caliber.py` 的窗口中位数阈值是 **10.0** —— 两阈值之间真躺着样本：`BJ920176` 2026-07-27 单行 `ratio = 35.11`（该标的窗口中位数 100.17，实为「手」）被判成「股」→ volume **静默写成 1/100**，且原"偏差 > 1 倍才丢弃"的保护兜不住（偏差仅 0.65 倍）。**修法：外侧定侧 + 灰区弃权**（`ratio ≥ 50` 判手／`ratio ≤ 2` 判股／中间**返回 `None` 回流**逐只通道）——纪律是 **单行判定必须比窗口判定保守**，因为窗口有中位数投票、单行没有。**为什么抽样对拍没抓到**：抽样只覆盖 15 只典型标的，灰区样本不在样本里 —— 即 **"抽样对拍通过" ≠ "判据正确"**。
  - **验证**：`tests/test_optim_20260916.py` **23 → 34 用例**（新增跨模块守卫 + 真实异常样本回归 + 9 个参数化 ratio 边界）；**阴性对照**把旧实现内联回放跑同款不变式 —— 旧实现被守卫抓 **5 条**违反（含真缺陷那只 `35.11`）、新实现 **0 条**，**证明守卫有抓取能力而非恒过**。全量回归 **697 passed / 1 skipped**（证据 `.scratch/junit_full_20260916b.xml`，277.9s）；技能库侧另建 `.workbuddy/skills/README.md` 索引（9 簇分簇表 + 按症状排序的路由速查 + 待办台账）。
  - **本轮撞出的第 2 个真问题（改 `ops.md` 时暴露，已修）**：本技能自检的「文档引用完整性」会把**日志里引用的工作区路径**也当成「技能内引用」做存在性校验 → 补一次变更日志就撞出 **3 条 FAIL**（`.workbuddy/skills/README.md` / `indicators/volume_caliber.py` / `tests/test_optim_20260916.py`）。**修法不是去掉反引号逐处规避**（那样每引用一次就要记得躲一次），而是给 `checks.py` 加 `REF_EXTERNAL_PREFIXES`（跨根前缀：`.workbuddy/`、`.scratch/`、`历史数据集/`、`backend/`、`frontend/`、`indicators/`、`daily_scheduler/`、`tests/`），并**把判定顺序改为「先尝试按技能内解析、失败后才判前缀/白名单」** —— 顺序反了会让技能内同名路径（如 `scripts/checks.py`）被前缀规则误放行。**阴性对照三项**（脚本 `.scratch/verify_docref_guard.py` → 输出 `.scratch/docref_guard_result.txt`）：A 注入技能内假引用 → **FAIL**（证明没被改成恒过）；B 注入跨根引用 → **放行**（前缀生效，且只对跨根生效）；C 还原后 → **23/23 FAIL=0**。
  - **⭐ 连带教训（对照脚本自己抓到的）**：阴性对照首跑时两项**误报失败** —— 我的断言写的是 `startswith("[OK]")`，而检查器实际输出是 `[ OK ]`（**带内空格**），于是判据本身错了。**这是"作者自查漏"的现场复现**：连"用来验别人的对照脚本"也得被验一遍。修断言后三项全 PASS。
  - **诚实边界（未解决，如实登记）**：① 索引 `README.md` 是**人工维护**的，新增技能若忘了登记会**静默过期** —— 目前只受本小节约定约束，**无机器门禁**（与 `selftool` 子命令那种"可 FAIL 的门禁"不同）；② 「段落级零重复」只覆盖 ≥60 字符的连续片段，**短句级、语义级的重复未被检测**，不能据此断言"全库无冗余"；③ 本轮**未改写任何人工手写技能** —— 无 `agent_created: true` 者（如 `quantity-website-restart`）只报问题、不动手，已登记进排除名单；④ **跨根前缀是"约定式放行"**：落在那 8 个前缀下的引用**一律不校验**，所以工作区侧真有文件被删/改名时，「文档引用完整性」**不会报**（它只保技能内引用不断链）—— 这是为了让日志能正常引用证据而付的代价，登记在此以免日后误以为"门禁全保"。

- **v3.1.0（2026-09-15）新增「自研工具与技能：标注与公开留痕」（贯穿阶段 3–6）**（用户 2026-09-15 指定；方案评审三选：新建独立仓 `Garvin666/ai-workflow-tools` ／ 文档规则 + 机器门禁 ／ **不追溯存量**）：
  - **规则本体（SKILL.md 新增独立小节，唯一事实源）**：先给**判定口径**——同时满足「① 本任务自行编写（非复用第三方、非用户既有资产）② 以文件形式落地」才算自研；**不算**的三种：未落盘的一次性内联命令、对既有文件的局部修改、第三方 fork 改造（仍走阶段 2 引入前检查并注明上游）。**三条硬要求**：① **代码内标注**五项（自研标识 / 名称 / 用途 / 适用场景 / 仓库链接；脚本写文件头注释块，技能包写 `SKILL.md` frontmatter + 首段）② **输出中标注**（交付说明 / 报告 / `Ledger.md` 凡引用处须出现「自研」+ 名称 + 链接）③ **同步推送 public 仓库，此后每次新增/修改及时推送、保持版本一致**。**禁止**把自研产出写得像成熟第三方库。四处接缝：阶段 3 第 1 步（新建文件同时标注 + 登记）、阶段 5 第 8 条（交付说明附仓库链接）、阶段 6 第 4 条（沉淀分流：更新后重跑 `push --apply` + `verify`）、阶段 6 台账（交付物列注明「自研 + 链接」）。
  - **`checks.py` 新增 `selftool` 子命令 + `_check_selftools()` 门禁**：`meta.自研工具` 逐项登记四项必填（名称 / 用途 / 适用场景 / 仓库链接），**字段可选、一旦填写必须合法**（与 `_check_autonomy` 同口径 —— 多数任务没有自研产出，强制填空会退化成走过场）。判 **FAIL**：缺字段、非列表、仓库链接非 `http(s)` 或含占位符（`<>`／TODO／xxx／待定／N/A）；判 **SKIP**：链接为『待推送』。**为什么留这个口子**：存在「先登记、后推送」的时序，一登记就 FAIL 会阻断流程；但它是 SKIP 而非 OK，汇总显式提示"交付前须回填"，不做成静默通过。
  - **新增 `scripts/publish_tools.py`（本规则的落地工具，本身即自研，已按规则在文件头标注）**：`init`（创建仓库，`private=False` 硬编码，**不提供 `--private`**；**幂等**：建仓前先查仓库，已存在且 public → `[OK] …跳过创建（幂等）` 且退出码 0，已存在但 private → FAIL + 改可见性指引。**此幂等性是实机跑出来的修正**——初版无前置查询，重跑 `init` 直接吃 422 并报 FAIL，与「幂等可重跑」口径冲突；另加 422 竞态兜底：POST 撞车后复查仓库，public 则按幂等通过）／`push`（默认 dry-run，`--apply` 才写；已存在文件带远端 `sha` 更新，幂等可重跑）／`verify`（查 `private` 字段 + 比对远端 blob sha 与本地，**这是"版本一致"的机器判据**，不靠"我记得推过了"）。走 `api.github.com`（本机 github.com 主域间歇不通），优先 `gh api` 子进程、回退 urllib；凭据四来源，只读不落盘。目标仓默认 `Garvin666/ai-workflow-tools`，`--repo` 或 `SELFTOOL_REPO` 覆盖。⚠️ 文本类扩展名默认做 **CRLF→LF 规范化**再算 sha —— 工作区文件常是 CRLF，直接按原始字节算会与仓内 LF 内容不一致，表现为"每次都判需推送"（`--no-normalize` 关闭）。
  - **验证**：`checks.py skill` **21/21 FAIL=0**（20→21 系新脚本纳入 py_compile；文档引用 35→38）；`py_compile` 双脚本通过；**门禁真伪用 6 个自造 fixture 证明**——缺字段→FAIL、占位符链接→FAIL、非列表→FAIL、待推送→SKIP、合法→OK、无该字段→OK（"未使用"）；**历史 plan 零回归**：27 份（技能目录 + 工作区）用 monkey-patch 开关做**同体对照**（同一份 plan 有/无新门禁各跑一遍），**FAIL 数 27/27 完全一致**。证据见 `tasks/技能增强-ai-workflow-v3.1.0-2026-09-15/验证输出.txt`（工作区档案侧同目录）；**实机首推验证**见同目录 `远端推送验收.txt`（建仓 `Garvin666/ai-workflow-tools` public → 首推 → 幂等复跑 → 用自带代码独立重算 blob sha 复核，非复用脚本自证）。
  - **本轮撞出并修掉的 2 个真缺陷**（入口类型=Bug，均属"作者自查抓不到"型，由实测输出暴露）：
    - **① `gh` 状态码提取失败**：gh 报错形如 `gh: Not Found (HTTP 404)`，原实现按 token 逐个 `isdigit()` 扫描，而 `404)` 带右括号判不出来 → 真实 404 被误报成 `HTTP 1`，"仓库不存在"的提示永远不会触发。修：改用正则 `HTTP\s+(\d{3})` 优先提取。
    - **② 假绿同型病**：`verify` / `push` 的仓库查询失败分支只 `print` 不入 `results`，导致输出 `0/0 通过，FAIL=0` 却带退出码 1 —— 与 `checks.py` v2.3 修过的病同源。修：失败一律 `fail()` 计入 results，并把「**函数只填 results、打印统一交给 main**」定为口径（修的过程中还出现过内部与 main 各打一次的重复，一并收敛）。
  - **坑（写 fixture 时踩到，非产品代码缺陷）**：YAML 里用**双引号**包 Windows 路径（`工作区根: "C:\Users\…"`）会被当成转义序列（`\U`）而抛 `ScannerError`；plan.yaml 写 Windows 路径须用**单引号**或不加引号。该坑使首轮 fixture 全部在解析阶段失败、根本没走到新门禁 —— 是"阴性对照必须先自证能跑通"的反例。
  - **诚实边界（未解决，如实登记）**：① 门禁只能校验"登记项是否完整"，**不能自动发现「代码里写了自研工具却没登记」** —— 漏登记仍靠阶段 5 自检与人工；② `verify` 只比对**显式传入的文件**，不扫全仓；③ ~~目标仓 `Garvin666/ai-workflow-tools` 截至本条写入时尚未创建~~ → **2026-09-16 已修正**：该仓已创建（public）并完成首推，`自研工具.仓库链接` 已回填；④ 按用户决定**不追溯存量** —— 本机既有自研脚本不补登记、不补推送。
  - **2026-09-16 建仓与首推（本规则的首次落地，两仓分工）**：
    - **`Garvin666/ai-workflow-tools`**（public，2026-09-16 建）—— 放**自研工具**源码，如 `scripts/publish_tools.py`（`scripts/` 前缀）。
    - **`Garvin666/ai-workflow-skill`**（public，早于本次）—— 放**本技能本体**；本次已把 v3.1.0 增量推上去（远端 `ddd13643` → `dc2121d5` → `c5b53c7d`，均为 Git Data API 创建的 commit，**与本地历史不互通**）。
    - ⭐ **技能自身也受本规则约束**：`ai-workflow` 就是本任务自研的技能包，故本次一并补齐了「技能包」标注 —— frontmatter `selfbuilt: true` + `repo:`，正文首段给出用途／适用场景／仓库链接。
    - ⭐ **`init` 幂等是实机跑出来的修正**（前文已记）：初版复跑吃 `422` 报 FAIL，与「幂等可重跑」口径冲突。**教训：同一脚本里 `push` 幂等，不代表 `init` 也幂等 —— 幂等要逐个动作验。**
    - **推送方式**：走 `api.github.com` Git Data API（blob → tree(**base_tree**) → commit → ref）。为何不能直接 `git push`：远端 `ai-workflow-skill` 是**混合仓**（技能本体 ∪ 工作区档案），且历史由 API 创建、与本地无关 → 直接 push 会因历史无关被拒。故 `base_tree` 精确列本次改动文件，其余路径原样承袭。
    - **独立验收（`tasks/技能增强-ai-workflow-v3.1.0-2026-09-15/远端推送独立验收.txt`）**：验收器自写、与推送脚本**零代码共享**，五判据 PASS —— 本地 173 文件 ⊆ 远端 239 blob 且 sha 全等；远端独有 66 项经 `base_tree` 证明**全部早于本次推送**；关键文件 sha 一致；远端 `SKILL.md` 确含 `selfbuilt`／`repo`／`[自研技能]`／3.1.0；删除项 0。**两个老坑在验收器里显式处理**：本地侧 `git -c core.quotePath=false ls-tree`（否则中文路径转义造出假缺失）、混合仓用「本地 ⊆ 远端 + 独有项须早于本次推送」而非「集合相等」。
- **v3.0.1（2026-09-15）阶段 6 治理工具化：新增 `scripts/archive_tasks.py`**（首次执行记录见 `tasks/_archive/2026-09/README.md`）：
  - **起因**：`checks.py status` 会周期性提示「任务目录 N 个 > 阈值 10，建议归档」，但**只有建议、没有工具**——每次归档都要临时写脚本；而归档有一个**非显然的破坏性约束**：`checks.py skill` 的「文档引用完整性」会扫 `SKILL.md` 与 `references/*.md` 中反引号包裹、后缀 md/yaml/py/ps1 的路径，并用 `skill_dir/ref` 做存在性校验，**归档被引用的目录会直接使自检 FAIL**。首次执行的实测案例：最旧的 `技能增强-ai-workflow-v2.4.3-2026-09-10` 被 `references/ops.md` 引用其下的 `tasks/技能增强-ai-workflow-v2.4.3-2026-09-10/_test_server.py`（403 分类实测证据），故**保留原位不归档**，切分线定为「2026-09-10 归档、09-11 起保留」；归档 6 个目录（28 文件 / 158,687 字节）后 `skill` 仍 **19/19 FAIL=0**、`status` 由 14 个降至 8 个且不再 WARN。
  - **工具形态**：`--older-than`／`--dirs` 选定 → 默认 **dry-run** → `--apply` 执行；**只移动不删除**（脚本内无任何删除调用）；把上述引用约束做成**前置门禁**（被引用目录自动剔除 + 打印引用出处）；移动前后用**逐文件 sha256 快照**比对自证零丢失；报告剩余目录集合与"来源目录去向全部有据"核对。退出码 0（成功，含 dry-run）／1（移动后校验失败）／2（前置检查拒绝）。
  - **验证**：`py_compile` 通过；dry-run 正确剔除 v2.4.3 并列出可归档项；**阴性对照**——显式 `--dirs "技能增强-ai-workflow-v2.4.3-2026-09-10"` 被拒（退出码 2 并给出引用出处）。
  - **诚实边界**：归档仍是**位置敏感的破坏性动作**。工具只解决"安全地移动"，**不解决"引用该不该随动"**——除 `SKILL.md`／`references/*.md` 外，`Ledger.md` 与 `tasks/` 内部的历史路径引用**不受任何机械校验**，归档后它们会静默失效（见 Ledger 备注区 2026-09-15 条）。
  - **文档↔实现交叉自查（用同期沉淀的 `doc-impl-parity-audit` 技能跑）**：高置信维度命中 6 项，逐项人工核实后 **4 项假阳性**（参数被"描述为不存在"、命令被"记录为失败"、通用词被当字段名）、**1 项措辞不精确**（把位置参数写成了选项形式）、**1 项真脱节**（写了一个并不存在的子命令，该脚本实为单层 argparse、无子命令）——后两项已在本条目上方的历史记载处修正并标注。**意义**：该检查在本次改动**同一轮**就抓出了存量脱节，实证「作者自查对描述↔实现脱节失效、须用机器交叉查」这一结论。注意其精度：6 项中仅 2 项为真，**它是缩窄候选范围的工具，不是问题清单**。
- **v3.0.0（2026-09-15）新增「自主决策层」：能力路由 + 自适应计划 + 决策留痕**（由 `tasks/技能增强-ai-workflow-v3.0-2026-09-15/` 驱动；用户明示"升级为具备自主决策能力的智能工作流"，经方案评审选定「文档 + 机器门禁」方案）：
  - **新增 `references/capability-routing.md`（能力路由）**：把"外部辅助"拆为**四类能力**（知识＝skill／算力＝子代理／事实＝联网／手脚＝脚本与 MCP），每类给出**该用与不该用双向判据**（只给"该用"会造成滥用，滥用比不用更贵）；决策三步（识别缺口 → 估收益（**须可验证**）→ 估开销）；**反合理化红线表 8 条**——借 superpowers 的形、**改其义**：拦的是"没想清楚就动手"，不是"没调用"；声明制 `[能力] <类> → <手段> ← 依据：<判据>`（同时是决策留痕的原始素材）；优先级两条（**方法先于执行**、**只读先于写入且本地先于联网**）。
  - **新增 `references/adaptive-planning.md`（自适应计划）**：拆解四规则（右尺寸三问／可验证前置（含正反例）／依赖显式化／粒度可调——探索性任务粗拆、执行性任务细拆，**不要在计划期假装知道执行期才知道的事**）；**R1–R6 重规划触发**（R1 新事实推翻假设／R2 验证信号不可达／R3 暴露新依赖／R4 成本超阈／R5 用户改需求／R6 连续性断裂）与**「不触发」清单**（防过度重规划：只改路径且新路径不比旧路径更可靠时不重规划）；重规划四步（**停→记→改→报**，先留痕再改动）；**上限 3 次**（超限说明初始拆解有问题或任务不适合线性计划 → 停下与用户重新对齐目标，**这是重新澄清、非熔断**）；执行期六动作循环。
  - **三层留痕（全部落在 `plan.yaml`，均为可选字段）**：`steps[].状态`（`checks.py mark`）／`meta.决策记录`（`checks.py decide`）／`meta.计划修订`（`checks.py revise`）。设计口径：**留痕只记录真实发生过的决策**——纯本地读写任务无外部辅助，"没写"是正常状态，故**不强制填空**（强制会退化成走过场）。
  - **`checks.py` 新增 `decide` / `revise` 子命令**：均为**就地行插入**（与 `_set_meta_fuse` / `cmd_mark` 同风格），保留 plan.yaml 的注释与键序——整份 `yaml.dump` 会吃掉注释，那才是真正的信息损失。`decide` 四参数（`--point` / `--basis` / `--capability` / `--choice`）**均必填**；`revise` 在第 4 次追加时 FAIL（上限 3）。
  - **`checks.py` 新增 `_check_autonomy()`**（`plan` 子命令调用）：校验决策记录／计划修订的**结构完整性**（必填键、能力类枚举、触发 R1–R6、修订上限）。**字段可选、但一旦填写必须合法**——既不误伤历史 plan，也不给新 plan 添空表单负担。FAIL 文案**由 `DECISION_KEYS` / `REVISION_KEYS` 常量生成**，防止再出现"文案写 5 个字段、代码只强制 3 个"的脱节。
  - **与强制式机制的分界（重要，防口径漂移）**：外部参照 `obra/superpowers`（286,871 star，MIT，2026-09-14 更新）的 `using-superpowers` 采用**无条件强制**（"1% 可能适用就必须调用" + 12 条反合理化红线）。本技能**只取其机制（按需加载／反合理化表／声明制／优先级／子代理 STOP），不取其强制**——要不要走本流程、要不要引入某能力，一律按用户「最高准则」（**能否让结果更快更好**）自判。**照搬强制口径会推翻该准则**，故明确排除。
  - **未改动**：三条红线（逐字节相同）、熔断机制（逐字节相同）、`VALID_STATUS`/`VALID_FUSE`、既有阶段骨架。
  - **验证**：`checks.py skill` **19/19 FAIL=0**（文档引用数 29 → 35）；**零回归**——22 个既有 plan 的 FAIL 数**逐项完全一致**（总 FAIL 9 → 8，唯一变化是本任务 plan 1 → 0，因基线采样时 step1 交付物尚未生成）；**门禁真伪用自造 fixture 证明**（缺必填键／能力类非法／触发 R9／修订超上限 → 全部 FAIL；历史 plan 判「未使用」→ 不误伤），证明校验**真的在跑**而非空壳。详见该任务目录 `回归证据.txt`。
  - **独立审核（未参与改造的子代理）发现 5 项描述↔实现脱节，全部返修**：① 文档写 `checks.py mark --revise`——该参数**不存在**（实为独立子命令 `checks.py revise`）；② `decide` 文档用法未列 `--choice`，而门禁强制其非空 → **照文档执行会被自家门禁判 FAIL**；③ 模板新增 `steps[].决策依据` 在代码中**零引用**（已**删除该字段**，避免"看起来有机制、实则无校验"的假象）；④ 门禁 FAIL 文案称 5 个字段、实际只强制 3 个（**改为由常量生成**，并补齐"能力类"必填）；⑤ SKILL.md 称"完整参数／变更日志见 ops.md"而本文件未收录（**本条即为此而补**）。返修后由原审核者逐条回归。

- **v2.5.3（2026-09-11）「独立审核」由强制门禁降级为抽查制**（用户决定；由 `tasks/技能增强-ai-workflow-v2.5.3-2026-09-11/` 驱动）：
  - **口径变更**：原「每个关键产出都必须派未参与执行的子代理送审」→ **默认自查 + 机器门禁**（`checks.py plan` 交付物对账与熔断门禁、`checks.py skill`、`--check-links` 链接探活、`office_io` 写回读回、py_compile／测试断言），仅三类情形**必送审**：① **高危产出**（安全/资金/权限/凭据/不可逆动作）② **用户点名**复核 ③ 同一反模式**第 2 次复发**或返修触顶（转对抗式互审）。
  - **未放松的部分**：「执行者不得自审」只在命中三类时生效，但**禁令未取消**；送审者仍只拿产出物 + 验收标准、须亲手复现至少一项硬证据；新增第 4 条**只报影响正确性的问题**（防"审查者为找问题而过度工程"）。
  - **连带调整**：阶段 5 门禁由「独立审核已通过」改为「**审核状态已闭合**（通过／抽查豁免）」；返修复查第 2 条区分送审／未送审两种复查主体；熔断 **F2** 取证不再要求"三次审核记录"，改为"三次可回溯留痕（独立审核／主代理自查／用户指出）"；反模式 37/38 改写、并新增 47（PS 5.1 脚本写非 ASCII 会静默置空变量）/48（Windows BOM 兼容）/49（测试里 `hasattr` 兜底导致静默不测），**反模式总数 46 → 49**；`assets/ledger-template.md` 值域改 `通过 / 抽查豁免（理由）`（**列名保留**以兼容历史台账）。
  - **决策依据**：每任务对每个关键产出另起干净上下文送审，是稳定发生的双倍人力税（见工作区 E:\ChatGPT\工作流\工作流瓶颈分析与优化方案-2026-09-11.md（工作区根，非技能内部文件） B3）。
  - **反证（刻意保留备查，不删）**：该环节是**唯一**抓到过"自查抓不到"类缺陷的机制——`checks.py` 的 `base.parent` 假 PASS 通道**两轮常规审核都没发现**、由对抗互审挖出；`体验报告` 4 处实质错误、`Ledger.md:15` 虚假自述、「描述与实现不符」3 次复发均系其发现。故本次为**减税**而非**撤防**：高压情形仍强制送审，未命中者亦有机器门禁兜底。
  - **连带修复（本次验证阶段撞出的真缺陷，入口类型=Bug）**：`checks.py` 的 `status` 子命令有**两处回归**，均被 `:283` 的宽 `except` 吞成「解析失败(XXX)」，使**阶段 0 必跑**的任务总览长期失真（完成度与交付物两列全废，且表面看像数据格式问题、不像代码 bug）：① `:272` `if args.light:` —— `args` 是 `main()` 的**局部变量**（`:550`），`cmd_status` 里访问它必抛 `NameError`；② `:279` `any(a["缺失"] for a in done)` —— `done` 是**步骤 dict 列表**，却去取审计结果字典的键，必抛 `KeyError`。两处均系 N6「轻量模式」改动引入。修复：① 改用形参 `light`；② 改为按 `zip(audited, steps)` 且**只对状态为「完成」的步骤**判交付物缺失。**教训（已入反模式视角）**：宽 `except Exception` 会把代码 bug 伪装成数据问题——总览出现「解析失败(XXX)」时**不得默认**为数据格式问题，须先看 traceback。
  - **第二类连带缺陷：`setup_env.ps1` 被 N8 的中文注释彻底跑不起来（RC=1）**。N8 把 marker 定义上移到文件顶部时，顺手把注释写成了中文；而 PS 5.1 读 .ps1 在**无 BOM 时按 cp936 解码**，UTF-8 中文字节把注释行与下一行代码**并成一行** → `$pkgDir = @{...}` / `$cliDir = @{...}` 整行进注释、变量恒 `$null` → 运行即 `无法对 Null 数组进行索引`。该文件头部本就写着 "ASCII-only for Windows PowerShell 5.1 compat"，属**明文纪律被违反**。**根因对照实验**：同内容 + UTF-8 BOM → RC=0 全绿；不带 BOM → RC=1；且 cp936 解码得 83 行 vs UTF-8 86 行（正好差 3 行中文注释，也解释了报错行号 38 与实际 41 的漂移）。修复：6 处非 ASCII 全部改英文，并全库扫描确认 `scripts/*.ps1` 已 **0 处非 ASCII**。已沉淀为**反模式 47**。
  - **第三类：Windows BOM 兼容**——PS 5.1 的 `Out-File -Encoding utf8` 与记事本写出的文本**带 BOM**，而 `checks.py` 读侧用 `encoding="utf-8"`，使 `mark --batch` 的首个 `step_id` 变成 `'\ufeff1'`，报「找到该步骤的『状态』行 — id=1」（看着像 id 不存在）。修复：`load_plan()` 与 `_load_batch()` 改用 `encoding="utf-8-sig"`（带/不带 BOM 皆可）。已沉淀为**反模式 48**。
  - **验证**：`checks.py skill` 19/19 FAIL=0；旧口径关键词全库 grep 0 命中；本任务 plan 对账 **7/7** FAIL=0；`status` 修复前后原始输出 + 跨工作区（`E:\ChatGPT\工作流`，⚠ 分支被真实触发）对照见该任务目录 `tasks/技能增强-ai-workflow-v2.5.3-2026-09-11/改动对照表-v2.5.3.md` 与 `验证输出.txt`。

- **v2.6.0（2026-09-11）落地瓶颈分析优化3 / 优化2措施3 / 优化5措施2**（由 工作流瓶颈分析与优化方案-2026-09-11.md（工作区根，非技能内部文件） 驱动，用户明示"按此前确定的计划完成实现"）：
  - **优化3｜阶段感知模型路由（最高 ROI）**：SKILL.md 阶段3 新增「阶段感知模型路由」决策清单——规划→强模型、关键实现/安全→强模型+双审、常规实现→中档、探索/调研/测试/文档/格式转换→便宜模型（本地 Ollama+DeepSeek/Qwen 或 Haiku 级）；附理由与硬规则（探索段默认便宜模型、红线相关产出仍强模型+双审、档位记入 plan.yaml 便于成本核对）。依据：路由报告行业实测编码场景成本降 70–90%、findings-3 Haiku 比 Opus 便宜约 15×。
  - **优化2 措施3｜跨任务 GitHub 限流计数器**：`http_fetch.py` 新增 `_rl_throttle(bucket, limit, window)`，状态落 `~/.workbuddy/cache/ai-workflow/ratelimit.json`（跨任务/跨进程共享，基础设施例外目录），在 `gh_core`(60/hr)/`gh_search`(10/min) 调用前按桶节流，避免多任务串行/并发打爆匿名限流；失败静默跳过、绝不阻断抓取，先写临时文件再 rename 防半截文件。smoke 测试（limit=2/window=1 连调 3 次）触发 ~1.2s 等待且状态文件落盘。
  - **优化5 措施2｜references 按需加载自检项**：SKILL.md 阶段3 Token 纪律补"references 严格按需加载、禁全量注入"约束；阶段5 交付前自检表新增"references 按需加载（未预读全量/主上下文未超量）"项。
  - **未做项（如实登记，非漏做）**：优化1（scandir 9.6×）已在 v2.4.2 完成；优化2 措施1（HTTP 正文缓存）与措施2（链接探活缓存）**当前代码已落在跨任务持久层**（`CACHE_DIR`/`LINKCHECK_CACHE_DIR` 即 `~/.workbuddy/cache/ai-workflow/` 下），经 grep 核实**已满足"跨任务持久"口径**，故不再重写（复用优先）；优化4（抽查制）已在 v2.5.3 完成。本次只补优化2 剩余的措施3。
  - **验证**：`checks.py skill` 19/19 FAIL=0；`http_fetch.py` py_compile 通过；节流 smoke 通过；SKILL.md grep 确认含路由表与自检项。

- **v2.6.1（2026-09-11）把阶段路由接入真实调用 + 拿降本实测**（由 工作流瓶颈分析与优化方案-2026-09-11.md（工作区根，非技能内部文件） 优化3 驱动，用户明示"把阶段路由接入真实任务调用、拿降本实测"）：
  - **接入真实调用**：新增 `scripts/model_tiers.json`（strong/mid/cheap → 模型/base/key_env/¥价目，单一事实源）；`ai_call.py` 加 `--tier <strong|mid|cheap>`（按配置解析 base/key/model/price，本地档 Ollama 自动 `none` key）与 `--ledger`（每次调用把档位/token/成本追加到 `~/.workbuddy/cache/ai-workflow/usage_ledger.jsonl`）；`assets/plan-template.yaml` 每步新增「模型档位」字段（checks 校验兼容，非必填）；SKILL.md 路由段补「落地与实测」口径。
  - **降本实测（本机口径）**：本机当前 `AI_API_KEY` 未设、Ollama `:11434` 返回 502 → **无法跑真实云账单**；改用「真实 token 用量（tiktoken cl100k_base，已装 v0.14.0）× 官方价目表」做可复现测算（token 只取决于文本，与是否联网无关）。实测见 tasks/技能增强-ai-workflow-v2.6.1-模型路由接入实测-2026-09-11/降本实测.md（工作区 tasks 目录，非技能内部文件）：本任务真实交付物（代码比重高，实现走 mid 而非 cheap）路由降本 **71.4%**；代表性技术调研报告任务（含 1 个 strong 关键实现阶段）投影降本 **78.0%**——均落入优化3 行业实测 70–90% 区间。配好 `AI_API_KEY` 或起 Ollama 后，账本直接出真实账单口径降本%。
  - **未做项（如实登记，非漏做）**：① 真实云账单实测（待凭据/Ollama 就位后由账本自动出，无需再改代码）；② cheap 档默认 `qwen2.5:7b`，换本地模型改 `model_tiers.json` 一行即可——属配置项，非代码缺口。
  - **验证**：`ai_call.py` py_compile 通过；路由逻辑单测全绿（三档位解析、未知档退回、cheap 注入本地 base+¥0、账本成本计算 ¥0.012 正确）；`model_tiers.json` 合法 JSON；`checks.py skill`/`plan` 待本任务末跑。

- **v2.6.2（2026-09-11）明确三条红线的适用范围（澄清性修订，红线内容一字未改）**（由用户级规则变更连带驱动，用户明示"按照你的想法走"）：
  - **问题**：用户级 `USER.md`／`MEMORY.md` 当天已把"要不要走 ai-workflow"改为**模型自行判断**（判据：能否让结果更快更好），并把"要不要先出计划、先等确认"改为**风险分级**（低风险直接干／高风险先问）。而 SKILL.md 第 10 行仍写"**三条不可豁免的红线**"，阶段 1／阶段 3 各有一条同款硬门禁 —— 两个文件**直接冲突**，模型在冲突处会摇摆。
  - **处置（划清管辖，不削弱流程）**：SKILL.md 顶部新增「**适用范围**」声明 —— ① 本流程**仅在被调用时生效**，调用与否由模型按「最高准则」自判（并指向用户级 USER.md／MEMORY.md）；② 日常任务的"先计划／先确认"按风险分级处理，**与本流程无关**；③ **一旦决定走本流程，红线在本流程内不可豁免**（选了走就把它走完）。红线内容本身**未改一字** —— 这是划界，不是放松。
  - **理由**：三条红线的价值只在"流程内"成立。外溢到日常轻操作 → 把 L0／L1 的分层豁免架空；在流程内也按风险分级 → L2 失去存在意义（用户调用它，图的就是这份严谨）。
  - **附带修复（发现的既有遗留）**：SKILL.md 版本号**双处滞后**——标题停在 `v2.5.3`、frontmatter 停在 `2.6.0`，而本文件已记到 `v2.6.1`、提交 `a7584c3` 已发布。本次三者统一到 **v2.6.2**。（"描述与实现脱节"在本技能已复发多次，属结构性问题。）
  - **连带修复（本次自检抓出的真回归，入口类型=Bug）**：首跑 `checks.py skill` 得 **18/19、FAIL=1** —— `文档引用完整性` 报「缺失：USER.md（来自 SKILL.md）；MEMORY.md（来自 SKILL.md）」。根因：`REF_PATTERN` 把**反引号包裹的 `.md` 一律按技能内引用**校验，而这两个是**用户级**文件、按约定不在技能目录内（与 `plan.yaml`／`Ledger.md` 同类）。修复：把二者加入 `REF_WHITELIST` —— 即**补检查的语义缺口，而不是把文档措辞改歪去绕过检查**。
  - **验证**：`checks.py skill` **19/19 FAIL=0**（修好上述回归后；文档引用完整性检查 29 条）；标题／frontmatter／本条目三处版本号均为 **2.6.2**；`grep -n "三条不可豁免" SKILL.md` **0 命中**。

- **v2.5.2（2026-09-11）新增流程末梢「熔断机制」+ 收敛交付物路径候选 + 清 v2.5.1 记录类遗留**（由 `tasks/技能增强-ai-workflow-v2.5.2-2026-09-11/` 驱动）：
  - **新增熔断机制（两个存储态 + 一次复位迁移 + F1–F5 触发 + 五步动作 + 复位条件）**：存储态为 `正常` / `已熔断`，**「复位」是一次迁移动作、不是第三个存储态**（`VALID_FUSE` 只有前两项）；**只有用户能复位**，且复位**两步缺一不可**、两步都由 `mark` 支持（`--fuse 正常` + 改步骤状态）。触发条件分质量（F1 审核链触顶、F2 同类缺陷 ≥3 次复发）与环境（F3 验证信号不可得、F4 越界未授权、F5 配额硬阻断）两类，**每条都必须有硬证据**。动作固定为 **停 / 冻 / 证 / 拦 / 报**。设计依据：工业界断路器三态，以及"**写在提示里的熔断不是熔断，是建议**"——故本机制**由 `checks.py plan` 强制执行**，不是文档约定。
  - **`checks.py` 新增熔断门禁**：`plan` 子命令新增 `_check_fuse()` —— meta `熔断状态` 取值须为 `正常`/`已熔断`（留空即正常）；一旦为 `已熔断` 或存在步骤状态 `熔断`，**直接 `[FAIL] 已熔断：不得作为可交付物`**，并要求同目录产出**熔断报告**（格式模板 `assets/熔断报告模板.md`）且含五个必填节。`VALID_STATUS` 增加 `熔断`。
  - **`checks.py` 交付物路径候选收敛为仅 `base/<p>`**：移除 `~/.workbuddy/<p>`（固定前缀兜底，使工作区内不存在的交付物被同名文件"救活"）与 `base.parent/<p>`（使交付物落在**工作区根之外**也判 PASS，撞红线③）两条通道；绝对路径直通。**跨根引用必须写绝对路径**。⚠️ 实测影响（口径：两个工作区 `tasks/` 下**全部** plan.yaml，递归含 `_archive/`、排除 `tmp/` 夹具；时点 2026-09-11 14:23）：文件型交付物 token 合计 **156**，其中 **20 个**为"相对技能目录"的历史写法（全在 `E:\ChatGPT\工作流` 的历史任务里），旧 PASS → 新 FAIL —— 属应然行为（它们的交付物确实不在各自工作区根内）。**注意口径陷阱**：改动生效后再"跑一遍现状"数 PASS→FAIL 必然得 0，必须用同一脚本复刻旧候选对照。是否迁移这 20 条写法见 `tasks/技能增强-ai-workflow-v2.5.2-2026-09-11/` 目录内的改动对照表（该表在本任务收尾时生成）。
  - **新增 `assets/熔断报告模板.md`**；`assets/plan-template.yaml` 增可选 meta `熔断状态`；反模式 39 → **46 条**（新增熔断类 6 条 + 路径候选 1 条）；`SKILL.md` 在阶段 6 之后新增「熔断机制」独立小节，并在阶段 0 / 阶段 3 返修复查 / 阶段 5 / 阶段 6 四处加接缝。
  - **清 v2.5.1 记录类遗留（对抗互审裁决 §5 必改项 2/3/4/5/6）**：`回归证据.txt` **整份重写**（原版 `回归 8/9` 各重复 6 次、2 处安全策略拦截回执被当成命令输出、算式 `7+6+1` 有误）；`plan.yaml` 的两处不实措辞与 2 对重复交付物更正；本节 R6 条目口径更正（见下）；§四原「首选」恒失败命令改为直调 `ast-grep.exe`；`Ledger.md` 的虚假自述补注更正。
  - **教训（已入反模式 40–46）**：熔断必须是机器门禁；熔断后不得再当交付物；复位只能由用户做且须留痕；交付物跨根必须写绝对路径（**假 PASS 与假 FAIL 同样有害**）。
- **v2.5.1（2026-09-10）修复体验评估发现的 2 处真实代码缺陷 + 4 处主干部问题 + 10 项文档收口**（入口类型=**Bug/缺陷**，走「复现→根因→修复→回归」；由 `tasks/技能增强-ai-workflow-v2.5.1-2026-09-10/` 驱动，复现基线见该目录 `复现基线.txt`）：
  - **R5 真缺陷｜`setup_env.ps1` 依赖自检恒报 OK**：`deps` 列 7 包但 `$pkgDir` 只映射 5 个 → 未映射项取到空值，而 `Join-Path` 遇**空子路径会返回父目录本身**，使 `Test-Path` **恒为 True**，`duckdb`/`ast-grep-cli` **从未被真正校验**（缺失也报 `[ OK ]`）。修复：补全映射并**用双表区分包形态**——`$pkgDir`（可导入模块，按 site-packages）补 `duckdb`；CLI-only 的 `ast-grep-cli` 改由新增的 `$cliDir` 按 venv `Scripts\ast-grep.exe` 判定（**比用 dist-info 作标记更可靠**：dist-info 在部分卸载后可能残留）；**未映射项显式 `[FAIL]`，禁止静默通过**。
  - **R6 真缺陷｜`checks.py` 路径候选过宽致假 PASS**：`_candidate_paths()` 曾把 `SKILLS_ROOT` 下每个技能目录都并入候选，使**工作区里并不存在**的交付物被别的技能目录同名文件"救活"。复现（最极端形态）：目录内**只有 plan.yaml**、连 `references/` 都没有，对账仍报「交付物确认 1 个 / 7/7 通过」。⚠️ **v2.5.1 的修复并未真正闭合**：当时只把候选"收窄为固定三处"（`基准／~/.workbuddy/<p>／基准的上级`），而这两条附加通道与 R6 属**同型缺陷** —— 前者同样能救活工作区内不存在的交付物，后者让落在工作区根之外的交付物判通过。该结论由 2026-09-11 的**对抗式互审**（两个子代理独立发现 + 主代理复现）坐实，详见 `tasks/对抗互审-ai-workflow-v2.5.1-2026-09-11/裁决.md` §4。**真正的收敛（候选仅为 `base/<p>`）在 v2.5.2 完成**（见上一条）。
  - **R1 主干自相矛盾**：红线①"未确认前禁止执行任何脚本" vs 阶段 0 要求跑 `checks.py status`。修复：红线①限定为"**处理类**脚本与产出文件"，显式豁免 `status`／`skill`／`Read`／`Grep`／`Glob` 等只读检查。
  - **R2 `tasks/` 口径三套并存（已被现场复现，红线③当场失守）**：修复：明确"**任务目录一律建在工作区根下的 `tasks/`**"（写入工作区边界段与阶段 3 第 1 条）；例外表把技能目录的"写 `tasks/` 记录"限缩为"**仅技能自身演进类任务**"。
  - **R3 冷启动缺「数据分析」验证信号**：主干信号清单（`:85` 附近）补「数据分析类＝交叉校验脚本（总额对账／行数一致／空值率）+ 抽样复算」，并注明完整信号表在 `quality-gates.md`。
  - **R4 独立审核缺粒度规则**：新增第 7 条**优先级**（豁免仅在未命中四类关键产出时适用）与第 8 条**批次规则**（同任务多交付物可合并为一次送审，单批 ≤5 文件，审核者须拿到全部产出物 + 统一验收标准，**不得以合并为由减少覆盖面**）。
  - **R7（原 N1）`report-template.md` 确认表缺「工作区根」**：已补第 6 行——与 R2 构成"漏字段 → 交付物落错位置"的因果链，故提升优先级。
  - **P1 文档收口**：阶段 4 明确「非 Office 交付跳过本阶段」+ 阶段 5 交付前自检处**也**给出 `assets/report-template.md` 指针（两者都指，避免跳过阶段 4 的任务看不到模板）+ `excel-write` **只吃 `--rows` JSON**（CSV 须先 `excel-read --fmt json`，直接喂会抛 `JSONDecodeError`）；L1 判定**排除 `_` 开头示例文件**且注明"需待阶段 0 查模板后确认"；阶段 0「列本地 skill」给出可执行做法（`Glob */SKILL.md` + `find-skills`）；阶段 5 对账命令补 `--base <工作区根>`；阶段 2 方案对比补非工程类维度；`run_stage.ps1` 加**执行后自检**（先清空 `$LASTEXITCODE`，调用后仍为空 ⇒ 判 `[FAIL]` 退出 1，不再把宿主的静默 no-op 当成功）；ops.md §一 明确**首选直接调 venv 解释器**、ps1 包装器仅作交互式终端备选；§四 增**不依赖 ps1 的 `import` 探测命令**与"未映射必须 FAIL + 改写检查必配负向测试"两条纪律；排障表 **+8 行**（ps1 静默 no-op、Bash 拒调 ps1、excel-write CSV、status 无 `--workspace`、依赖自检假 OK、对账假 PASS、旧计划 `meta.工作区根` 为空、`--base` 传 POSIX 路径致假 FAIL）；`--check-links` 均值改为**区间并标注不可当基线**；`office_io.py` 按子命令前置依赖检查（`[ERROR]`+`[HINT]` 退出 2，替代裸 traceback；**`ai_call.py` 经核为纯标准库，无需守卫**——原体验报告该项不成立）；`data_query.py files` 的 `[提示]` 改走 **stdout**（原先走 stderr，`2>&1` 下因缓冲差异插到正文之前）。
  - **回归**：`checks.py skill` 全绿 + `py_compile` 通过 + **两处负向测试**（移除 venv 中 `duckdb` 目录后 `setup_env.ps1` 必须报 `[FAIL]`；无关目录下引用 `references/` 的假交付物对账必须 `FAIL`）。详见 `回归证据.txt`。

- **v2.5.0（2026-09-10）按用户给定流程图补齐四个缺失环节**（用户提供标准流程：入口 → 上下文收集/材料理解/代码调查 → 方案评审 → 人工确认与授权 → 任务编排/执行/独立审核 → 返修复查 → 测试交付/验收与发布协作 → 结果核验与履历归档）。**保留原有 0-6 编号，只补缺口不重排**：
  - **入口分型**（阶段 0）：新增「消息 / 正式需求 / Bug」三型判定表；**Bug 类必须走「复现 → 根因 → 修复 → 回归」**，禁止未复现就改。
  - **上下文收集**（阶段 1）：新增「收集相关文件 / 历史任务 / 既有交付物与台账」→「材料理解摘要（3-5 行）」→「代码调查（编码类：入口定位 + 影响面 + 最小改动点）」三步，**先收再问**。
  - **方案评审**（阶段 2）：新增「≥2 个候选方案 × 可行性/成本/风险/可回滚性/验收匹配度」对比与推荐；新增**方案级确认**——实质分歧须用户拍板，**不可逆或需外部协作的动作（发布/推送/花钱）单独确认**。阶段 2 标题改为「调研与方案评审」。
  - **独立审核（执行者≠审核者，强制）**（阶段 3 新增小节）：关键产出必须由**未参与该步执行**的子代理独立审核，审核者只拿产出物 + 验收标准、须亲手复现至少一项硬证据；**不得以"我已检查过"替代**；L0/L1 或极小产出可豁免但须写明理由。
  - **返修复查（回归闭环）**（阶段 3 新增小节）：返修须带具体问题清单；返修后**强制由审核者逐条回归**并重跑原有验证信号；同产出返修上限 2 轮 → 转对抗式互审 → 仍不过升级用户；每轮结论用 `checks.py mark` 回写 plan.yaml。
  - **测试交付与验收**（阶段 5 改名）：新增「测试证据（跑出来的原始输出）」独立成项、**用户验收确认点**（明确列出请你验收什么）、**发布协作**（不可逆动作单独确认 + 发布后探活/冒烟，结果入履历）。
  - **结果核验与履历归档**（阶段 6 改名）：新增「结果核验（逐条对照验收标准给达成证据）」与**履历台账**（工作区根 `Ledger.md`，新增模板 `assets/ledger-template.md`：入口类型/日期/任务/交付物/验收结论/独立审核/越界授权），**只追加不删改**。
  - 反模式清单 34 → **39 条**（新增：执行者自审、返修不复查、缺陷未复现就改）。
  - `playbook.md` 新增「五、缺陷修复类（Bug 入口）」：复现/根因/影响面/最小改动/回归双条件/交付口径。
  - **首次实跑「独立审核」环节即发现 4 项真实缺陷并完成返修复查**（执行者=主代理，审核者=未参与改造的子代理；审核者只拿产出物 + 验收标准，逐条有罪推定式复核）：① **口径冲突（中）**——「质量把关」写"优先抽查"而「独立审核」写"必须"，两处并存易被读成可互相替代 → 明确前者为**通用原则**（主代理核实子代理产出）、后者为**不可豁免门禁**，并加注"满足质量把关不等于过了独立审核"；② **豁免条件不封闭（中）**——原"L0/L1 或产出极小可豁免"给了执行者自行扩权的口子 → 新增**关键产出判定清单**（支撑结论的数据/代码改动/报告核心结论/对外交付物，命中任一必须送审），豁免限缩为"L0/L1 或单文件微改/纯格式转换/仅追加文字"，且**须在 `plan.yaml` 验证方式与工作区 `Ledger.md` 两处留痕、由主代理判定、不得由执行者自行宣布**；③ **职责重叠（低）**——阶段 5 与阶段 6 均称"验收" → 分别标注 `**交付前自检**`（东西做得对不对）与 `**交付后核验**`（逐条对照验收标准 + 纳入用户验收意见）；④ **索引失真（低）**——手册索引称 playbook"四类"而实际已五节 → 补「+ 缺陷修复类（Bug 入口）」。
  - **返修回归验证（逐条重跑，非"我认为改好了"）**：4 项问题逐条回归全部 OK；原有验证信号不回退——`checks.py skill` **18/18 通过 FAIL=0**；`checks.py plan` Anti-drop 对账 **7/7 通过 FAIL=0**（已完成步骤 8 / 交付物确认 8）。**结论：该环节在首次使用中即产出真实价值，保留为强制门禁。**
  - 新增 **`assets/ledger-template.md`** 与技能根 **`Ledger.md`**（已回填 3 条历史任务），确立「履历台账追加不删改」纪律。

- **v2.4.4（2026-09-10）工作区边界成为红线③**（用户指定：Agent 工作范围仅限所选文件夹）：
  - SKILL.md 新增「**工作区边界**」硬性规则段（置于任务分层之后）：工作区根**按任务由用户指定**，写入确认表 `workspace` 字段与 plan.yaml `工作区根`；未指定则默认当前会话目录并显式标注。
  - 越界（根目录之外任何路径）→ **先说明再申请当次授权**，上一任务的授权不延续；授权记录须写进交付说明。
  - 基础设施例外白名单（不算越界，仅限工具用途、不得存用户数据）：`~/.workbuddy/skills/ai-workflow/`、`~/.workbuddy/binaries/python/envs/ai-workflow/`、`~/.workbuddy/cache/ai-workflow/`。
  - 配套 schema 升级：7 个任务模板加 `workspace` 字段（**schema 8 → 9 字段**）；plan-template 的 meta 加 `工作区根`，`PLAN_META_REQUIRED` 同步（**缺失即对账 FAIL**）；`checks.py` 模板计数改动态输出。
  - 阶段 1 五要素 → **六要素**（加工作区根）；阶段 4 产出前列路径清单须逐条确认落在工作区内；阶段 5 自检表加「产出全部落在工作区根内」。

- **v2.4.3（2026-09-10）清理三项遗留**（任务 `tasks/技能增强-ai-workflow-v2.4.3-2026-09-10/`）：
  - **① `data_query.py big` 默认跳过依赖/缓存目录**：`BIG_SKIP_DIRS` 由 `{.git, __pycache__}` 扩为含 `.venv`/`venv`/`site-packages`/`node_modules`/`.conda`/`.mypy_cache`/`.pytest_cache`/`.ruff_cache`/`.tox`/`.nox`/`.ipynb_checkpoints`/`.cache`。**旧口径用 `--no-skip`（别名 `--legacy-skip`）复现**。实测（`E:\ChatGPT\量化分析与数据分析`，≥1MB）：旧口径 488 个（其中 115 行来自 `.venv`）→ 新口径 **328 个**；旧口径复现**逐字节一致（488 行全等）**。
  - **② GitHub 凭据解析扩为四来源**：`--token` → `GITHUB_TOKEN` → `GH_TOKEN` → **`gh auth token`（gh CLI 自动读取）**，新增 `_looks_like_token()` 形态校验（前缀/长度 ≥20/无空白），防把 gh 的提示文本当凭据发出。实测本机 `gh` 已有凭据：**core 60 → 5000/小时、search 10 → 30/分钟**，认证后 `--github-search` 端到端可用（"language:python stars:>60000" 命中 92 条）。凭据只读不落盘。
  - **③ `--check-links` 403 分类与换头重试**：403/429 先用常规 UA 探测，失败后换一套浏览器头重试一次，仍失败才判定；新增 `_classify_403()` 按响应头分类——**CDN 反爬(Cloudflare，识别 `cf-ray`/`cf-mitigated`/`server: cloudflare`)**、**WAF 反爬(Akamai/Imperva/Sucuri/CloudFront)**、**限流**、**未知拒绝**。用本地测试服务器（`tasks/技能增强-ai-workflow-v2.4.3-2026-09-10/_test_server.py`，模拟 200/404/401/Cloudflare-403/Akamai-403/nginx-403）实测六种路径全部分类正确。
  - 同类事实修正：`academy.hackthebox.com` 在本机的失败是 **SSL 握手超时（本机出口限制）**，不是 403 反爬——探活工具现可把二者分开，不再混为一谈。
  - 反模式清单 30 → **34 条**（凭据形态/403≠404/口径回退/凭据不得打印）。

- **v2.4.2（2026-09-10）清理 v2.4 遗留两项**（由 `tasks/技能增强-ai-workflow-v2.4.2-2026-09-10/` 驱动）：
  - **性能修复｜`data_query.py files/big` 在大目录上耗时 21s** → 遍历改为 **`os.scandir` + `DirEntry.stat()`**（新增 `_walk_stat()`）。原理：**Windows 上 `os.scandir` 列目录时已由 FindFirstFile 带回文件属性，`DirEntry.stat()` 直接复用**；旧写法 `os.walk` + `os.path.getsize` 会对每个文件**再发一次 stat 系统调用**（12 万文件 = 12 万次多余系统调用）。
    - 公平基准（预热后各跑 3 次取最小值，两轮独立复现）：**22,365~22,875 ms → 2,278~2,341 ms，≈9.6×**。
    - **输出逐字节一致**：文件数 121,146、总字节 11,982,072,013、扩展名分布、大文件列表与旧版完全相同（`--top 12` 比对 31 行无差异）——**纯优化，零口径变化**。
    - 排障记录：端到端命令耗时（4.0s）明显高于纯遍历（2.3s），因为还含扩展名聚合+排序（约 1.4s）与解释器启动；排查性能问题时**要区分「遍历」与「聚合」两段开销**，不要误判优化无效。
  - **补 P0｜GitHub 只能搜仓库、不能搜代码内容** → `http_fetch.py` 新增 **`--github-code-search "<代码片段> repo:owner/name"`**（官方 `/search/code`），返回「哪个仓库的哪个文件」+ text_match 命中片段。
    - **实测确认该端点强制认证**：匿名请求直接 401，**不是限流**。脚本据此**提前拦截并给出可执行提示**（设 `GITHUB_TOKEN` / 或改用 `--github-search`），不再抛出裸 401 堆栈。
    - 需 `Accept: application/vnd.github.text-match+json` 才返回 `text_matches` 片段 → `fetch()` 增加 `headers_extra` 参数支持自定义头，脚本内置该头。
    - ⚠️ **诚实标注**：本机无 PAT，**响应解析逻辑依官方文档实现，未经带 token 的端到端实测**（已实测的是 401 分支与 URL 构造）。
  - **新增 `--dry-run`**（两个 GitHub 搜索端点通用）：只打印将请求的 URL + 附加头 + 认证状态即返回，**不发请求、不消耗配额**，用于离线校验参数构造。对非搜索命令使用时会显式告警本次忽略。
  - 已知遗留（本轮**未改**，避免影响逐字节一致性）：`big` 的 `BIG_SKIP_DIRS` 只跳 `.git`/`__pycache__`，**不跳 `.venv`**，故在本机量化目录里会把 `torch/lib/dnnl.lib`（675 MB）等虚拟环境文件列进大文件榜。属既有行为，如需过滤需另开任务。
- **v2.4.1（2026-09-10）ast-grep 实装修正**（P2 落地后实装验证）：
  - **`sg` 命令已废弃** → 文档全部改用 **`ast-grep`**（安装 `ast-grep-cli` 到 venv，实测版本 0.45.3；`sg.exe` 仍在但会打印废弃警告）。
  - **新增能力：`ast-grep outline`** —— 符号级检索（列变量/函数/导入/成员），**替代了原调研中要引入 ctags 的需求**，少一个依赖。
  - **实测踩坑记录**：① `except:` 单独不是合法 pattern，报 `Multiple AST nodes are detected`——**复合语句必须写全**（`try: $$$B except: pass`）；② 该报错**不是语法错误**，容易被误判为"工具不支持 Python"，实际是 pattern 写法问题。
  - 实测正例：`ast-grep run -p 'print($$$A, file=sys.stderr)' -l py scripts/` 一次命中 10 处（多节点捕获 + 参数约束，正则难以表达）。
  - 依赖清单加入 `ast-grep-cli`。
- **v2.4（2026-09-10）检索能力增强**（由调研 `tasks/技术调研-工作流检索能力-2026-09-10/` 驱动，方案经用户确认后执行）：
  - **补 P0｜GitHub 只能取不能搜** → `http_fetch.py` 新增 **`--github-search "<query>"`** + `--search-sort` + `--search-limit`，复用现有 `fetch()`（**零新依赖**）。实测匿名调用 `/search/repositories` 成功。内置官方硬限制提示：结果上限 1000 条 / 扫描上限 4000 个匹配仓库 / q ≤256 字符 / 布尔算子 ≤5 个 / 匿名限流 10 次每分钟（认证 30）。未设 `GITHUB_TOKEN` 时显式告警；空结果显式告警（防"搜不到就编造"）。输出 TSV 增加 `language`/`html_url`/`description` 列，`archived` 正确显示否/是。
  - **补 P1a｜大数据集搜不动** → 新增 **`scripts/data_query.py`**（DuckDB），四个子命令 `files` / `big` / `find` / `sql`。依赖清单加入 `duckdb`。实测：**470MB Parquet / 1,710 万行 / 5,665 只标的，全表聚合 1.53 秒，零导入**；跨文件正则检索 41 文件 2.2 秒带行号。
  - **P2｜跨行/结构检索** → SKILL.md 阶段 3 第 5 条改为「**先选对工具再搜**」决策清单：`Grep`/`Glob` → `--github-search` → `sg`(ast-grep) → `data_query.py`。写入 `sg` 的关键避坑：**pattern 不支持正则**，文本匹配必须回 `Grep`。（ast-grep MIT / Windows 原生 / 离线；实测排除 comby（停更）与 CodeQL（许可））
  - **P1b｜自由文本索引 → 暂缓**：实测 `Genivia/ugrep-indexer` 仅 84★ 且停更 14 个月，原推荐被推翻，不引入。
  - 实战修掉 2 个 bug：① `data_query.py` 的 glob 相对 **CWD** 而非其**位置参数** `path` 解析 → 静默零命中；② 用 `json.dumps` 拼 SQL 字面量 → **中文被转义成 `\uXXXX`** + **双引号在 SQL 中是标识符**，双坑叠加致零命中。改用 `_sql_str()` 单引号转义。
  - SKILL.md 版本号 2.2 → 2.3 → **2.4**（前两轮漏改头部，已补齐）。
- **v2.3（2026-09-10）实战修复**（由真实任务 `tasks/技术调研-网络安全学习-2026-09-10/` 驱动）：
  - `checks.py` **修假绿**：缺 pyyaml 时原会先报错、再打印 `结果：0/0 通过，FAIL=0` 并返回 0，调用方（含 CI/子代理）会误判为通过。现改为 `_require_yaml()` 统一守卫，**以退出码 2 中止**并给出 venv 绝对路径提示；`main()` 不再吞掉非零 `code`（`return 1 if n_fail else code`），未跑起来时输出「未执行」而非「全绿」。同一守卫也修掉 `load_plan` 在 `status` 子命令下的裸 traceback。
  - `http_fetch.py` 新增 **`--check-links`** 批量探活：只取状态码不下载正文。实战量化——12 条链接串行探活 41.2s 且白下载 3.5MB；新工具并发 8 实测 1.9s（≈40× 加速）。⚠️ 当时记录的"平均 156ms/条"取自 12 条小样本，**均值受超时条数影响极大**（另有实测 1 条 502 超时即把均值拉到 2573ms/条），**不可当基线引用**。
  - `http_fetch.py` 在 `--out` 目标已存在但抓取失败时打印告警（防旧内容被误用）。⚠️ 原写「http_fetch.py fetch…」，**更正**：该脚本是**单层 argparse、没有子命令**，`fetch` 并非子命令名（v3.0.1 由文档↔实现交叉检查发现）。
  - 交付前置动作确立：**外部链接必须探活后才可写进交付物**（实战中拦下 1 条 404 死链并修正）。
- **v2.2（2026-09-10）**：效率增强——SKILL.md 瘦身（脚本速查/排障/日志移入本文件）；`http_fetch.py` 增加本地缓存（TTL + `--no-cache`）与 GitHub 多仓库并发；`ai_call.py` 增加 `--batch-file` 批量并发（JSONL 输出）；`checks.py` 增加 `status`（任务总览 + 归档建议）与 `mark`（安全更新步骤状态）；阶段 1 追问轮次上限 2 轮、阶段 0 用 `status` 替代逐个翻历史任务。
- **v2.1（2026-09-10）**：新增 `checks.py`（自检 + Anti-drop 对账）；模板 3 → 7 类；`office_io.py` 支持 CSV/多 sheet/格式化；`http_fetch.py` 增加 `--grep`/`--max-chars`；`report-template.md` 补证据等级、验证闭环证据、复盘三节；依赖补 pyyaml。快照 `_backup-v2/`。
- **v2.0（2026-09-10）**：任务分层 L0/L1/L2；验证闭环前置门禁；阶段 6 复盘沉淀；证据分级标注；评审六偏差；references 拆分（quality-gates / orchestration，补全 playbook）；模板 schema 统一；`http_fetch.py` 403 限流重试与 HTML→文本；`ai_call.py` model 覆盖与用量回显。快照 `_backup-v1/`。
- **v1.0**：六阶段主干。
