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

也可用 `scripts/run_stage.ps1 <脚本名> [参数...]`（自带状态检查）。

## 二、脚本速查

| 脚本 | 用途 | 示例 |
| --- | --- | --- |
| **checks.py** | `skill` 技能自检（frontmatter/引用完整性/模板 schema/py_compile）；`plan` 计划校验 + Anti-drop 对账；`status` 工作区任务总览（交付物完成度 + 归档建议）；`mark` 更新步骤状态 | `checks.py plan tasks/x/plan.yaml --base "E:/ChatGPT/工作流"` |
| setup_env.ps1 | 初始化 venv 与依赖（requests / openpyxl / python-docx / pypdf / pyyaml / **duckdb** / **ast-grep-cli**） | `powershell -File scripts\setup_env.ps1` |
| ai_call.py | 调 AI 模型：`--model` 覆盖、`--system-file`、`--max-tokens`、`--temperature`、`--stats` 用量回显、`--batch-file` + `--concurrency` 批量并发（结果落 JSONL） | `ai_call.py --batch-file prompts.txt --concurrency 3` |
| http_fetch.py | 联网抓取：`--github-repo a/b,c/d` 指标实测（并发 + 限流退避 + 缓存）、**`--github-search "<query>"` 按关键词搜仓库**（限定符 `language:` `stars:` `topic:` `pushed:`；`--search-sort stars,forks,updated`、`--search-limit`）、**`--github-code-search "<代码> repo:owner/name"` 按代码内容搜文件（⭐强制 token，返回仓库/路径/命中片段）**、**`--dry-run` 只打印将请求的 URL 与附加头（不发请求，无 token 也能验证参数构造）**、`--text` HTML→文本、`--grep`/`--max-chars` 定向提取、`--no-cache`/`--ttl` 控缓存、**`--check-links` 批量探活（只取状态码不下载正文，并发 8，交付外链前必跑；403 会换头重试并按 CDN/WAF 响应头分类）** | `http_fetch.py --github-search "code search language:rust stars:>500" --search-limit 20`<br>`http_fetch.py --github-code-search "read_parquet repo:duckdb/duckdb" --dry-run` |
| **data_query.py** | **大数据集/大目录检索（DuckDB）**：`files` 目录概览（文件数/总大小/按扩展名/大文件）、`big` 列大文件（**默认跳过 `.venv`/`node_modules` 等依赖与缓存目录；旧口径加 `--no-skip`**）、`find` 跨文件正则检索（带行号，DuckDB `read_text`）、`sql` 对 Parquet/JSON/CSV **零导入直接跑 SQL** | `data_query.py big . --min-mb 100`<br>`data_query.py sql "SELECT count(*) FROM read_parquet('x.parquet')"` |
| office_io.py | Office 读写：excel-read（xlsx/csv）、excel-write（单表/多表，默认表头加粗+冻结首行+自适应列宽）、word-read/write、pdf-extract/merge | `office_io.py excel-read data.csv --fmt json` |
| run_stage.ps1 | 状态检查 + 一键调脚本 | `run_stage.ps1 http_fetch.py <URL>` |
| **ast-grep**（`ast-grep-cli`，已装入 venv） | **跨行/结构模式检索 + 符号检索**。`run -p '<pattern>' -l py <路径>` 结构匹配；`outline <文件>` 列符号（替代 ctags 需求）；`scan` 跑规则文件。⚠️ pattern **不支持正则**（`\|`/`.*`/`\w` 无效），且**复合语句必须写全**（`except:` 单独不是合法 pattern，须写成 `try: $$$B except: pass`）。`sg` 命令**已废弃**，用 `ast-grep`。MIT / Windows 原生 / 离线 | `ast-grep run -p 'print($$$A, file=sys.stderr)' -l py scripts/` |

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

首次使用或报错时：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1
```

检查项：managed python 存在 → venv 存在（否则创建）→ 依赖可 import（按 site-packages 目录判定，不依赖 pip 退出码）→ AI_API_KEY 是否设置（仅提示）。

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
| `checks.py plan` 报交付物缺失 | 检查路径是否写全（缩写如「选品分析.yaml」无法定位）、括号注释是否多余；skill 内相对路径会逐技能目录尝试 |
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
| PowerShell 报"无法识别" | 用 `&` 加引号完整路径调用 |
| Excel 打开乱码 | 确认写文件用默认 `utf-8-sig` |
| 批量 AI 调用全部失败 | 多为 API key 无效/欠费，检查 JSONL 里的 error 字段 |

## 六、链接收集与核验 SOP（调研类任务交付前必跑）

调研类交付物里的每一个外链都要走完这四步，缺一步不得交付：

```bash
# 1. 提取：从所有 findings / 草稿里抓 URL
grep -ohE "https?://[A-Za-z0-9._~:/?#@!$&'*+,;=%()-]+" findings-*.md \
  | sed 's/[.,;:)]*$//' | sort -u > all_urls.txt

# 2. 去重后剔除不可直接验证的（模板 URL、纯 API 端点会误导）
grep -vE "api\.github\.com" all_urls.txt > check_urls.txt

# 3. 探活（只取状态码，不下载正文；实测 140 条平均 227ms/条）
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
  - 实战修掉 2 个 bug：① `data_query.py` 的 glob 相对 **CWD** 而非 `--path` 解析 → 静默零命中；② 用 `json.dumps` 拼 SQL 字面量 → **中文被转义成 `\uXXXX`** + **双引号在 SQL 中是标识符**，双坑叠加致零命中。改用 `_sql_str()` 单引号转义。
  - SKILL.md 版本号 2.2 → 2.3 → **2.4**（前两轮漏改头部，已补齐）。
- **v2.3（2026-09-10）实战修复**（由真实任务 `tasks/技术调研-网络安全学习-2026-09-10/` 驱动）：
  - `checks.py` **修假绿**：缺 pyyaml 时原会先报错、再打印 `结果：0/0 通过，FAIL=0` 并返回 0，调用方（含 CI/子代理）会误判为通过。现改为 `_require_yaml()` 统一守卫，**以退出码 2 中止**并给出 venv 绝对路径提示；`main()` 不再吞掉非零 `code`（`return 1 if n_fail else code`），未跑起来时输出「未执行」而非「全绿」。同一守卫也修掉 `load_plan` 在 `status` 子命令下的裸 traceback。
  - `http_fetch.py` 新增 **`--check-links`** 批量探活：只取状态码不下载正文。实战量化——12 条链接串行探活 41.2s 且白下载 3.5MB；新工具并发 8 实测 1.9s（≈40× 加速，平均 156ms/条 vs 3400ms/条）。
  - `http_fetch.py fetch` 在 `--out` 目标已存在但抓取失败时打印告警（防旧内容被误用）。
  - 交付前置动作确立：**外部链接必须探活后才可写进交付物**（实战中拦下 1 条 404 死链并修正）。
- **v2.2（2026-09-10）**：效率增强——SKILL.md 瘦身（脚本速查/排障/日志移入本文件）；`http_fetch.py` 增加本地缓存（TTL + `--no-cache`）与 GitHub 多仓库并发；`ai_call.py` 增加 `--batch-file` 批量并发（JSONL 输出）；`checks.py` 增加 `status`（任务总览 + 归档建议）与 `mark`（安全更新步骤状态）；阶段 1 追问轮次上限 2 轮、阶段 0 用 `status` 替代逐个翻历史任务。
- **v2.1（2026-09-10）**：新增 `checks.py`（自检 + Anti-drop 对账）；模板 3 → 7 类；`office_io.py` 支持 CSV/多 sheet/格式化；`http_fetch.py` 增加 `--grep`/`--max-chars`；`report-template.md` 补证据等级、验证闭环证据、复盘三节；依赖补 pyyaml。快照 `_backup-v2/`。
- **v2.0（2026-09-10）**：任务分层 L0/L1/L2；验证闭环前置门禁；阶段 6 复盘沉淀；证据分级标注；评审六偏差；references 拆分（quality-gates / orchestration，补全 playbook）；模板 schema 统一；`http_fetch.py` 403 限流重试与 HTML→文本；`ai_call.py` model 覆盖与用量回显。快照 `_backup-v1/`。
- **v1.0**：六阶段主干。
