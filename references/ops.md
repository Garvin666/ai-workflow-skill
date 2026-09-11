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
| **checks.py** | `skill` 技能自检（frontmatter/引用完整性/模板 schema/py_compile）；`plan` 计划校验 + Anti-drop 对账 + **熔断门禁**（`熔断状态: 已熔断` 或步骤状态 `熔断` → 直接 FAIL）；`status` 工作区任务总览（交付物完成度 + 归档建议 + **已熔断任务 ⚡ 标记与 WARN 汇总**）；`mark` 更新步骤状态（含 `熔断`）与 **meta 熔断状态**（`--fuse 正常\|已熔断`，复位用 `--fuse 正常`，不必手改 YAML） | `checks.py plan tasks/x/plan.yaml --base "E:/ChatGPT/工作流"` |
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

- **v2.5.3（2026-09-11）「独立审核」由强制门禁降级为抽查制**（用户决定；由 `tasks/技能增强-ai-workflow-v2.5.3-2026-09-11/` 驱动）：
  - **口径变更**：原「每个关键产出都必须派未参与执行的子代理送审」→ **默认自查 + 机器门禁**（`checks.py plan` 交付物对账与熔断门禁、`checks.py skill`、`--check-links` 链接探活、`office_io` 写回读回、py_compile／测试断言），仅三类情形**必送审**：① **高危产出**（安全/资金/权限/凭据/不可逆动作）② **用户点名**复核 ③ 同一反模式**第 2 次复发**或返修触顶（转对抗式互审）。
  - **未放松的部分**：「执行者不得自审」只在命中三类时生效，但**禁令未取消**；送审者仍只拿产出物 + 验收标准、须亲手复现至少一项硬证据；新增第 4 条**只报影响正确性的问题**（防"审查者为找问题而过度工程"）。
  - **连带调整**：阶段 5 门禁由「独立审核已通过」改为「**审核状态已闭合**（通过／抽查豁免）」；返修复查第 2 条区分送审／未送审两种复查主体；熔断 **F2** 取证不再要求"三次审核记录"，改为"三次可回溯留痕（独立审核／主代理自查／用户指出）"；反模式 37/38 改写、并新增 47（PS 5.1 脚本写非 ASCII 会静默置空变量）/48（Windows BOM 兼容）/49（测试里 `hasattr` 兜底导致静默不测），**反模式总数 46 → 49**；`assets/ledger-template.md` 值域改 `通过 / 抽查豁免（理由）`（**列名保留**以兼容历史台账）。
  - **决策依据**：每任务对每个关键产出另起干净上下文送审，是稳定发生的双倍人力税（见工作区 `E:\ChatGPT\工作流\工作流瓶颈分析与优化方案-2026-09-11.md` B3）。
  - **反证（刻意保留备查，不删）**：该环节是**唯一**抓到过"自查抓不到"类缺陷的机制——`checks.py` 的 `base.parent` 假 PASS 通道**两轮常规审核都没发现**、由对抗互审挖出；`体验报告` 4 处实质错误、`Ledger.md:15` 虚假自述、「描述与实现不符」3 次复发均系其发现。故本次为**减税**而非**撤防**：高压情形仍强制送审，未命中者亦有机器门禁兜底。
  - **连带修复（本次验证阶段撞出的真缺陷，入口类型=Bug）**：`checks.py` 的 `status` 子命令有**两处回归**，均被 `:283` 的宽 `except` 吞成「解析失败(XXX)」，使**阶段 0 必跑**的任务总览长期失真（完成度与交付物两列全废，且表面看像数据格式问题、不像代码 bug）：① `:272` `if args.light:` —— `args` 是 `main()` 的**局部变量**（`:550`），`cmd_status` 里访问它必抛 `NameError`；② `:279` `any(a["缺失"] for a in done)` —— `done` 是**步骤 dict 列表**，却去取审计结果字典的键，必抛 `KeyError`。两处均系 N6「轻量模式」改动引入。修复：① 改用形参 `light`；② 改为按 `zip(audited, steps)` 且**只对状态为「完成」的步骤**判交付物缺失。**教训（已入反模式视角）**：宽 `except Exception` 会把代码 bug 伪装成数据问题——总览出现「解析失败(XXX)」时**不得默认**为数据格式问题，须先看 traceback。
  - **第二类连带缺陷：`setup_env.ps1` 被 N8 的中文注释彻底跑不起来（RC=1）**。N8 把 marker 定义上移到文件顶部时，顺手把注释写成了中文；而 PS 5.1 读 .ps1 在**无 BOM 时按 cp936 解码**，UTF-8 中文字节把注释行与下一行代码**并成一行** → `$pkgDir = @{...}` / `$cliDir = @{...}` 整行进注释、变量恒 `$null` → 运行即 `无法对 Null 数组进行索引`。该文件头部本就写着 "ASCII-only for Windows PowerShell 5.1 compat"，属**明文纪律被违反**。**根因对照实验**：同内容 + UTF-8 BOM → RC=0 全绿；不带 BOM → RC=1；且 cp936 解码得 83 行 vs UTF-8 86 行（正好差 3 行中文注释，也解释了报错行号 38 与实际 41 的漂移）。修复：6 处非 ASCII 全部改英文，并全库扫描确认 `scripts/*.ps1` 已 **0 处非 ASCII**。已沉淀为**反模式 47**。
  - **第三类：Windows BOM 兼容**——PS 5.1 的 `Out-File -Encoding utf8` 与记事本写出的文本**带 BOM**，而 `checks.py` 读侧用 `encoding="utf-8"`，使 `mark --batch` 的首个 `step_id` 变成 `'\ufeff1'`，报「找到该步骤的『状态』行 — id=1」（看着像 id 不存在）。修复：`load_plan()` 与 `_load_batch()` 改用 `encoding="utf-8-sig"`（带/不带 BOM 皆可）。已沉淀为**反模式 48**。
  - **验证**：`checks.py skill` 19/19 FAIL=0；旧口径关键词全库 grep 0 命中；本任务 plan 对账 **7/7** FAIL=0；`status` 修复前后原始输出 + 跨工作区（`E:\ChatGPT\工作流`，⚠ 分支被真实触发）对照见该任务目录 `tasks/技能增强-ai-workflow-v2.5.3-2026-09-11/改动对照表-v2.5.3.md` 与 `验证输出.txt`。

- **v2.6.0（2026-09-11）落地瓶颈分析优化3 / 优化2措施3 / 优化5措施2**（由 `工作流瓶颈分析与优化方案-2026-09-11.md` 驱动，用户明示"按此前确定的计划完成实现"）：
  - **优化3｜阶段感知模型路由（最高 ROI）**：SKILL.md 阶段3 新增「阶段感知模型路由」决策清单——规划→强模型、关键实现/安全→强模型+双审、常规实现→中档、探索/调研/测试/文档/格式转换→便宜模型（本地 Ollama+DeepSeek/Qwen 或 Haiku 级）；附理由与硬规则（探索段默认便宜模型、红线相关产出仍强模型+双审、档位记入 plan.yaml 便于成本核对）。依据：路由报告行业实测编码场景成本降 70–90%、findings-3 Haiku 比 Opus 便宜约 15×。
  - **优化2 措施3｜跨任务 GitHub 限流计数器**：`http_fetch.py` 新增 `_rl_throttle(bucket, limit, window)`，状态落 `~/.workbuddy/cache/ai-workflow/ratelimit.json`（跨任务/跨进程共享，基础设施例外目录），在 `gh_core`(60/hr)/`gh_search`(10/min) 调用前按桶节流，避免多任务串行/并发打爆匿名限流；失败静默跳过、绝不阻断抓取，先写临时文件再 rename 防半截文件。smoke 测试（limit=2/window=1 连调 3 次）触发 ~1.2s 等待且状态文件落盘。
  - **优化5 措施2｜references 按需加载自检项**：SKILL.md 阶段3 Token 纪律补"references 严格按需加载、禁全量注入"约束；阶段5 交付前自检表新增"references 按需加载（未预读全量/主上下文未超量）"项。
  - **未做项（如实登记，非漏做）**：优化1（scandir 9.6×）已在 v2.4.2 完成；优化2 措施1（HTTP 正文缓存）与措施2（链接探活缓存）**当前代码已落在跨任务持久层**（`CACHE_DIR`/`LINKCHECK_CACHE_DIR` 即 `~/.workbuddy/cache/ai-workflow/` 下），经 grep 核实**已满足"跨任务持久"口径**，故不再重写（复用优先）；优化4（抽查制）已在 v2.5.3 完成。本次只补优化2 剩余的措施3。
  - **验证**：`checks.py skill` 19/19 FAIL=0；`http_fetch.py` py_compile 通过；节流 smoke 通过；SKILL.md grep 确认含路由表与自检项。

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
  - 实战修掉 2 个 bug：① `data_query.py` 的 glob 相对 **CWD** 而非 `--path` 解析 → 静默零命中；② 用 `json.dumps` 拼 SQL 字面量 → **中文被转义成 `\uXXXX`** + **双引号在 SQL 中是标识符**，双坑叠加致零命中。改用 `_sql_str()` 单引号转义。
  - SKILL.md 版本号 2.2 → 2.3 → **2.4**（前两轮漏改头部，已补齐）。
- **v2.3（2026-09-10）实战修复**（由真实任务 `tasks/技术调研-网络安全学习-2026-09-10/` 驱动）：
  - `checks.py` **修假绿**：缺 pyyaml 时原会先报错、再打印 `结果：0/0 通过，FAIL=0` 并返回 0，调用方（含 CI/子代理）会误判为通过。现改为 `_require_yaml()` 统一守卫，**以退出码 2 中止**并给出 venv 绝对路径提示；`main()` 不再吞掉非零 `code`（`return 1 if n_fail else code`），未跑起来时输出「未执行」而非「全绿」。同一守卫也修掉 `load_plan` 在 `status` 子命令下的裸 traceback。
  - `http_fetch.py` 新增 **`--check-links`** 批量探活：只取状态码不下载正文。实战量化——12 条链接串行探活 41.2s 且白下载 3.5MB；新工具并发 8 实测 1.9s（≈40× 加速）。⚠️ 当时记录的"平均 156ms/条"取自 12 条小样本，**均值受超时条数影响极大**（另有实测 1 条 502 超时即把均值拉到 2573ms/条），**不可当基线引用**。
  - `http_fetch.py fetch` 在 `--out` 目标已存在但抓取失败时打印告警（防旧内容被误用）。
  - 交付前置动作确立：**外部链接必须探活后才可写进交付物**（实战中拦下 1 条 404 死链并修正）。
- **v2.2（2026-09-10）**：效率增强——SKILL.md 瘦身（脚本速查/排障/日志移入本文件）；`http_fetch.py` 增加本地缓存（TTL + `--no-cache`）与 GitHub 多仓库并发；`ai_call.py` 增加 `--batch-file` 批量并发（JSONL 输出）；`checks.py` 增加 `status`（任务总览 + 归档建议）与 `mark`（安全更新步骤状态）；阶段 1 追问轮次上限 2 轮、阶段 0 用 `status` 替代逐个翻历史任务。
- **v2.1（2026-09-10）**：新增 `checks.py`（自检 + Anti-drop 对账）；模板 3 → 7 类；`office_io.py` 支持 CSV/多 sheet/格式化；`http_fetch.py` 增加 `--grep`/`--max-chars`；`report-template.md` 补证据等级、验证闭环证据、复盘三节；依赖补 pyyaml。快照 `_backup-v2/`。
- **v2.0（2026-09-10）**：任务分层 L0/L1/L2；验证闭环前置门禁；阶段 6 复盘沉淀；证据分级标注；评审六偏差；references 拆分（quality-gates / orchestration，补全 playbook）；模板 schema 统一；`http_fetch.py` 403 限流重试与 HTML→文本；`ai_call.py` model 覆盖与用量回显。快照 `_backup-v1/`。
- **v1.0**：六阶段主干。
