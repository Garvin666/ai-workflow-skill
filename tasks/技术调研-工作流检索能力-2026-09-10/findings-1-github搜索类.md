# findings-1：让本地 Python 工作流具备 GitHub 搜索能力

- 调研日期：2026-09-10
- 调研方式：纯联网检索（WebSearch + WebFetch），**未运行任何实测请求**；所有数字均标注来源，厂商宣传语不采信
- 现状参考：`C:/Users/26717/.workbuddy/skills/ai-workflow/scripts/http_fetch.py`
  - 现有能力：`--github-repo owner/repo` → 调 `https://api.github.com/repos/{owner}/{repo}`，已内建 403 限流识别 / 退避重试 / 本地缓存 / 多仓库并发（`ThreadPoolExecutor`）/ 无第三方依赖（仅 `urllib` + 标准库）
  - 缺口：**没有任何 search 端点**，无法按关键词发现仓库
- 证据分级：**【官方推荐】**＝官方文档 / 官方手册 / 包官方项目页；**【实践观点】**＝社区帖子、聚合站、第三方 skill 文档（数字一律不当证据）
- 未验证项一律显式标注「未验证」

---

## 0. 先说结论（缺口能否补上的最短路径）

现有 `http_fetch.py` 的 `fetch()` 已经是「带 token、带重试、带缓存」的通用 HTTP 函数，**追加 search 能力不需要引入任何第三方库**——只需新增一个「拼 `/search/repositories` 的 URL → 复用 `fetch()` → 解析 `items[]`」的函数即可。这是**最低成本、最高确定性**的路径（详见第 5 节）。

---

## 1. GitHub 官方 Search API

### 1.1 【C1】`GET /search/repositories`（按关键词/条件搜仓库）— 官方API

- **URL**：https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28 （端点小节 "Search repositories"）
- **端点**：`GET https://api.github.com/search/repositories`
- **必填参数**：
  - `q`（string）：关键词 + 限定符（qualifier）
- **可选参数**（官方原文）：
  - `sort`：`stars` / `forks` / `help-wanted-issues` / `updated`；缺省＝best match
  - `order`：`desc` / `asc`；缺省 `desc`（仅在提供 `sort` 时生效）
  - `per_page`：默认 30，**max 100**
  - `page`：默认 1
- **`q` 支持的限定符**（官方列出）：`in:`（name/description/readme）、`user:`、`org:`、`repo:`、`language:`、`topic:`（可叠加多个）、`stars:`、`forks:`、`size:`、`created:`、`pushed:`、`fork:`、`archived:`
  - 官方示例：`https://api.github.com/search/repositories?q=tetris+language:assembly&sort=stars&order=desc`
- **限流**（官方，2022-11-28 版本文档）：
  - 认证请求：**30 次/分钟**（除 code search 外的所有 search 端点）
  - 未认证请求：**10 次/分钟**
- **结果上限**：**每次搜索最多 1000 条**（官方原文 "provides up to 1,000 results for each search"）→ 1000/100 = 最多 10 页
- **额外限制**：
  - 搜索范围：**最多扫描 4000 个匹配仓库**（官方 "Search scope limits"）
  - 查询长度：**≤256 字符**；布尔算子 `AND/OR/NOT` **≤5 个**，超限返回 `Validation failed`
  - 超时会出现 `incomplete_results: true`（结果可能不全）
  - 构造 `q` 必须做 URL 编码（官方提醒）
- **响应关键字段**：`total_count`、`incomplete_results`、`items[]`（含 `full_name` / `stargazers_count` / `forks_count` / `pushed_at` / `language` / `license` / `description` / `html_url`）——**与现有脚本 `GITHUB_FIELDS` 字段完全同源**，解析逻辑可复用
- **能否嵌入 Python 脚本**：**是**（`urllib` 直接 GET，无需任何依赖）
- **证据等级**：【官方推荐】（GitHub 官方 REST 文档；另见镜像 https://githubdocs.cn/en/rest/search/search 表述一致）
- **能否补上本缺口**：**能，且是首选**。这正是「按主题找开源项目」所需的端点。

### 1.2 【C2】`GET /search/code`（按内容搜代码）— 官方API

- **URL**：同 1.1 文档页 "Search code" 小节
- **端点**：`GET https://api.github.com/search/code`
- **参数**：`q`（必填）、`per_page`（默认 30，max 100）、`page`
  - `sort` / `order`：官方标注 **"This field is closing down"**（字段正在下线，仅 `sort=indexed`）
- **【关键】是否强制认证**：官方文档内部表述不一致，需注意：
  - 正文/限流章节：**"The Search code endpoint requires you to authenticate and limits you to 10 requests per minute."**
  - 但同页 "Fine-grained access tokens" 小节又写：**"This endpoint can be used without authentication if only public resources are requested."**
  - → 结论：**带 token 才稳妥**；且认证状态下限流 **10 次/分钟**（比其它 search 端点更紧）
- **code search 特有硬限制**（官方 "Considerations for code search"）：
  - **只看默认分支**（default branch）
  - **只索引 <384 KB 的文件**
  - **查询必须包含至少一个非限定符关键词**（`language:go` 这种纯限定符查询非法，`amazing language:go` 才合法）
- **结果上限**：1000 条（同上），每页最多 100
- **补充（非官方）**：`github-code-search` 项目文档页 https://fulll.github.io/github-code-search/reference/github-api-limits 称「默认排除 fork，需 `fork:true` 才含 fork」「不支持正则」「至少要有一个搜索词」——该页为第三方工具文档，**fork 排除一项未在官方页确认，标为未验证**
- **能否嵌入 Python 脚本**：**是**（同 `urllib`）
- **证据等级**：【官方推荐】（GitHub 官方文档）+ 第三方工具文档补充标「未验证」
- **能否补上本缺口**：**部分能**。适合「找某段代码/某个文件名出现在哪些仓库」，**不适合作为「按主题找项目」的主路径**（主题发现用 C1 更直接、限流更宽松、无 384KB/默认分支约束）。

### 1.3 【C3】`GET /search/topics`（按主题搜 topic）— 官方API

- **URL**：https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28 （"Search topics" 小节）
- **端点**：`GET https://api.github.com/search/topics`
- **参数**：`q`（必填）、`per_page`（默认 30，max 100）、`page`
- **排序**：官方原文 "Results are sorted by best match"（**不支持 `sort`/`order`**）
- **状态码**：200 / 304
- **限流**：属 search 端点族 → 认证 30 次/分钟 / 未认证 10 次/分钟
- **响应**：返回 topic 对象（含 `name`、`display_name`、`description`、`featured` 等；**注意其 items 不含仓库列表**，只给 topic 自身）
- **能否嵌入 Python 脚本**：**是**
- **证据等级**：【官方推荐】
- **能否补上本缺口**：**辅助能、单独不能**。它只解析 topic 元信息，拿不到仓库列表；要与 C1 的 `topic:` 限定符配合才能闭环——即「先用 C3 确认 topic 存在/规范名，再用 C1 `q=topic:xxx` 拉仓库」。**没有 C1 时 C3 无独立价值**。

> 补充可选：**GraphQL `search(query:, type: REPOSITORY, first:, after:)`** 也在官方能力内，`first` 上限 100，可用游标翻页（社区 skill 文档 https://skillmd.ai/skills/mastering-github-cli 有示例）；但仍是 1000 条硬顶，且需写 GraphQL，**对「免依赖嵌入」不如 REST 直接**，本笔记归为 C1 的备选。

---

## 2. 命令行 / 客户端封装

### 2.1 【C4】`gh` CLI（`gh search repos` / `gh search code`）— CLI

- **URL（官方手册）**：https://cli.github.com/manual/gh_search_repos
- **语法**：`gh search repos [<query>] [flags]`
- **`gh search repos` 主要 flags**（官方手册原文摘录）：
  - `--language`、`--topic`、`--owner`、`--stars`、`--forks`、`--created`、`--updated`、`--archived`、`--license`、`--visibility`
  - `-L, --limit <int>`（**默认 30**）、`--match {name|description|readme}`
  - `--sort {forks|help-wanted-issues|stars|updated}`（默认 best-match）、`--order {asc|desc}`
  - `--json <fields>`、`-q/--jq`、`-t/--template`、`-w/--web`
  - JSON 字段含 `fullName` / `stargazersCount` / `forksCount` / `pushedAt` / `language` / `license` / `url` 等
- **`gh search code`**：存在，支持 `--owner`、`--extension`、`--filename`、`--language`、`--repo`；**不支持 `--sort`/`--order`**（结果恒按相关度排序）
- **认证 / 限流**（综合社区 skill 文档，标【实践观点】；与官方 search 文档数值一致）：
  - core API 认证后 5000/小时
  - search（repos/issues/prs/commits）认证 **30/分钟**
  - code search 认证 **10/分钟**，**必须认证**
  - 结果上限 1000 条
  - 另有「`gh search` 子命令**不支持 `--paginate`**，要翻页需改用 `gh api --paginate search/repositories`」的说法（来源 https://skillmd.ai/skills/mastering-github-cli ，【实践观点】，未官方确认）
- **能否嵌入 Python 脚本**：**需改造**。gh 是独立二进制，Python 脚本要 `subprocess` 调它，并依赖 `gh auth` 已完成登录；对「纯 stdlib 自包含脚本」是额外耦合
- **证据等级**：命令与 flags ＝【官方推荐】（cli.github.com 官方手册）；限流数字 ＝【实践观点】（社区文档，但与官方 search 文档一致）
- **能否补上本缺口**：**能，但不是最省事的**。若工作流本就允许调外部二进制，`gh search repos ... --json fullName,stargazersCount` 一行即可用；若坚持「单文件 stdlib」，它不如直接调 REST。

### 2.2 【C5】PyGithub — Python库

- **URL**：https://pypi.org/project/PyGithub/ ｜文档 https://pygithub.readthedocs.io/en/v2.10.0/examples/MainClass.html ｜仓库 https://github.com/pygithub/pygithub
- **包名**：`PyGithub`（`pip install PyGithub`）
- **许可证**：**LGPL**（PyPI 页面 License 栏原文 "GNU Library or Lesser General Public License (LGPL)"）
- **搜索能力**（官方文档示例）：`g.search_repositories(query='language:python')`、`g.search_repositories(query='good-first-issues:>3')`；另有 `search_code` / `search_users` / `search_issues` 等
- **维护状态**：PyPI 页面显示 **最新版本 2.10.0，Released: Aug 20, 2026**，4 位 maintainer；页面同时写「正在积极寻找 maintainer」→ **仍活跃发布，但维护人力偏紧**
- **需要认证**：是（`Auth.Token(...)`；匿名会撞搜索限流）
- **能否嵌入 Python 脚本**：**是**，但**引入第三方依赖**（`pip install PyGithub`），且 **LGPL** 对某些分发场景有约束
- **证据等级**：【官方推荐】（PyPI 包官方页 + PyGithub 官方文档）
- **能否补上本缺口**：**能**。搜索封装最省心（一个方法调用），代价是新增依赖 + LGPL；对现有「零依赖」脚本是「最大改动」的选项。

### 2.3 【C6】ghapi — Python库

- **URL**：https://pypi.org/project/ghapi/ ｜仓库 https://github.com/fastai/ghapi ｜文档 https://ghapi.fast.ai/
- **包名**：`ghapi`
- **许可证**：**Apache-2.0**（PyPI "License: Apache-2.0"）
- **搜索能力**：官方 README 的 API 分组列表里明确有 `search` 分组（即 `api.search.repos(...)` / `api.search.code(...)` 等形式；由 OpenAPI 规范自动生成，覆盖全部 GitHub API）
- **维护状态**：PyPI 显示 **ghapi 1.0.13 Released: Feb 28, 2026**；deps.dev 页（https://deps.dev/pypi/ghapi/2.1.0）显示有 2.1.x 版本且 OpenSSF "Maintained 10/10"；但注意 skillfed.io（聚合站，非官方）称 v2 为 async-first、需 Python 3.10+ —— 该页数字（下载量等）**未验证，不采信**，仅作线索
- **需要认证**：认证可选（token 提高限额）；搜索建议带 token
- **能否嵌入 Python 脚本**：**是**，但**引入依赖**（`fastcore` 等）
- **证据等级**：【官方推荐】（PyPI 官方包页 + 官方 README/文档）
- **能否补上本缺口**：**能**。许可证比 PyGithub 宽松（Apache-2.0），API 覆盖率号称 100%；仍不如「零依赖直连 REST」轻。

### 2.4 【C7】github3.py — Python库

- **URL**：https://pypi.org/project/github3.py/ ｜仓库 https://github.com/sigmavirus24/github3.py ｜文档 https://github3.readthedocs.io
- **包名**：`github3.py`
- **许可证**：**BSD-3-Clause**（libraries.io / deps.dev 均标 BSD-3-Clause）
- **搜索能力**：官方 changelog（PyPI 页）明确 "Add github3.search_code, github3.search_issues, github3.search_repositories, github3.search_users"
- **维护状态**：libraries.io 显示 **latest release 4.0.1，Apr 26, 2023**；deps.dev 显示 OpenSSF "Maintained 10/10"（截至 2025-11）；→ **发布节奏偏慢（最近一个大版本是 2023）**，但仍有提交
- **需要认证**：是（token）
- **能否嵌入 Python 脚本**：**是**，但**引入依赖**（`requests`、`uritemplate`、`python-dateutil`、`PyJWT`）
- **证据等级**：【官方推荐】（PyPI 官方页 + changelog）
- **能否补上本缺口**：**能**。许可证宽松、功能完整，但**功能已被 PyGithub/ghapi 覆盖且维护更慢**，无选择优势。

### 2.5 【C8】gh-search（PyPI 同名工具）— Python CLI 工具

- **URL**：https://pypi.org/project/gh-search/ ｜仓库 https://github.com/janeklb/gh-search
- **包名**：`gh-search`（注意与另一个 2020 年停更的 `github-search` 包 https://test.pypi.org/project/github-search/ 不是同一个，后者 【实践观点】证认为已废弃）
- **许可证**：PyPI 页面未标注 License 字段（**未验证**）
- **能力**：基于 GitHub Code Search REST API 的 CLI，**带正则内容过滤**、按 org/repo 分组、**主动检查限流**（自称「防止误耗 core 配额」）
- **维护状态**：PyPI 显示 **0.9.2，Released: May 8, 2026**（较新）；要求 **Python ≥3.12**
- **需要认证**：是，**必须 PAT（repo scope）**，经 `GITHUB_TOKEN` 或 `--github-token`
- **能否嵌入 Python 脚本**：**需改造**（外部 CLI，`subprocess`），且**强依赖 3.12+**，对「内嵌进 http_fetch.py」不友好
- **证据等级**：【官方推荐】（PyPI 官方包页 + 仓库 README）
- **能否补上本缺口**：**锦上添花，不建议作为主方案**。它的独特价值是「正则二次过滤 code search 结果」，可作为独立工具使用，不适合并进现有脚本。

---

## 3. 第三方代码搜索服务

### 3.1 【C9】Sourcegraph — 第三方服务

- **URL**：官方 API 总览 https://sourcegraph.com/docs/api/overview ｜GraphQL https://sourcegraph.com/api/graphql ｜文档镜像 https://mintlify.wiki/sourcegraph/docs/api/overview
- **公开 API**：有。四类接口：
  - **REST API**（Sourcegraph 7.0 起，官方称「有版本化、向后兼容承诺」）→ `https://<instance>/api-reference`
  - **GraphQL**（官方定性为 **debug 用途、"no backwards-compatibility guarantees"**）→ `POST /.api/graphql`
  - **Streaming search API**（SSE，官方称「官方 UI 用的同一套，适合消费搜索结果」）→ `/.api/search/stream`
  - **MCP server** → `/.api/mcp`
- **是否需要 key**：**是**。需在实例 Settings > Access tokens 生成 token，走 `Authorization: token ...` 或 `Authorization: Bearer ...`（含 OAuth）；有 sudo token
- **限流**：官方 **GraphQL cost limits**（非「次数/分钟」）：`graphQLMaxDepth=30`、`graphQLMaxFieldCount=500000`、`graphQLMaxAliases=500`、`graphqlMaxDuplicateFieldCount=500`、`graphqlMaxUniqueFieldCount=500`（可在 site config 调）——官方未在此页给「请求数/分钟」硬指标（**未验证**）
- **能否程序化调用**：**是**（任一 HTTP 客户端；官方也有 `src` CLI）
- **能否嵌入 Python 脚本**：**需改造**。要处理 token、GraphQL 或 SSE 流、可能的自建实例 endpoint，且 `sourcegraph.com` 上的公开索引覆盖范围需自行确认（**未验证**）
- **证据等级**：【官方推荐】（Sourcegraph 官方文档）
- **能否补上本缺口**：**能，但过重**。适合「跨仓库深度代码检索」，对「按主题发现项目」属于杀鸡用牛刀，且引入 token 管理与外部服务依赖。

### 3.2 【C10】grep.app — 第三方服务

- **URL**：https://grep.app/ ｜端点 `https://grep.app/api/search`
- **公开 API**：**是，且无需 key**（第三方 crate 文档 https://docs.rs/crate/grepapp_haystack/1.16.33 明确 "No Authentication: grep.app API currently doesn't require authentication"）
- **端点格式**（来源为第三方 skill 文档与 crate 文档，标【实践观点】）：
  - `GET https://grep.app/api/search?q={query}&page=1`
  - 过滤参数：`f.lang`（语言）、`f.repo.pattern`、`f.path.pattern`；另有 `regexp=true`、`case=true` 一说（不同来源参数名不一致：另有 `l`/`r`/`regexp` 写法 → **参数名以实测为准，未验证**）
  - 响应结构：`hits.hits[]`（含 `repo`、`path`、`content.snippet`，snippet 为 HTML → 需二次清洗）
- **限制**：有速率限制（第三方文档称 "enforces rate limits"，**具体阈值未公布/未验证**）；仅索引**公开 GitHub 仓库**；不支持正则（一处文档称「text-based, not regex」，另一处又称 `regexp=true` 可用 → **自相矛盾，未验证**）
- **能否程序化调用**：**是**（GET JSON）
- **能否嵌入 Python 脚本**：**是**（`urllib` 即可，但需额外写 snippet HTML 清洗；现有 `html_to_text()` 可复用一部分思路）
- **证据等级**：【实践观点】（无官方 API 文档页可引用；证据来自第三方 crate/ MCP 集成文档；grep.app 官网本身未提供公开文档）
- **能否补上本缺口**：**部分能**。适合「按代码片段/文件名找仓库」，**不能替代 C1 的按主题发现**（它不返回 star/topic 等仓库元数据，也不做主题聚合）。且**无官方文档 = 长期稳定性存疑**。

### 3.3 【C11】searchcode.com — 第三方服务（**能力已转型，需注意**）

- **URL**：https://searchcode.com/ ｜REST 基址 `https://api.searchcode.com/api/v1/{tool_name}?client=your-app` ｜OpenAPI `https://searchcode.com/openapi.json`
- **【重要变化】**：从官网当前文案看，searchcode **已从「代码搜索索引站」转为面向 LLM 的「代码智能 MCP 服务 + REST API」**，围绕**单个公开 git 仓库**做分析（`code_analyze` / `code_search` / `code_get_file` / `code_get_files` / `code_file_tree` / `code_get_findings` 共 6 个工具），而非「全 GitHub 关键词搜仓库」
- **公开 API**：有。REST 形如 `POST https://api.searchcode.com/api/v1/code_analyze?client=my-app`，body 传 `{"repository":"https://github.com/..."}`
- **是否需要 key**：官网称 **"No install, no API key"**，但**要求 `?client=your-app` 参数**标识调用方；官网同页称 **beta 期间免费，长期会有付费档（称免费档可能保留）**
- **限流**：官网**未公布具体速率**（**未验证**）
- **能否程序化调用**：**是**（REST POST JSON，或 MCP）
- **能否嵌入 Python 脚本**：**需改造**。是**面向「已知仓库」的分析接口**，不是「按关键词发现仓库」——与目标场景错位
- **证据等级**：【官方推荐】（searchcode.com 官网文案 + 其 openapi.json 链接；注：官网含较强营销措辞如「省 99% token」，**此类宣传语不采信**）
- **能否补上本缺口**：**不能补本缺口**。它不提供「按主题搜全 GitHub 找项目」的能力；其「读单个仓库」能力与现有 `/repos/{owner}/{repo}` 部分重叠。

### 3.4 【C12】publicwww — 第三方服务（**定位不符，列出以排除**）

- **URL**：https://publicwww.com/ ｜定价 https://publicwww.com/prices.html ｜语法 https://publicwww.com/syntax.html
- **索引对象**：**网页源码（HTML/JS/CSS/headers）**，不是 GitHub 仓库代码
- **是否需要 key**：**是**，API 需 `PUBLICWWW_KEY`；且 **API 访问仅 Pro($109/mo) 及以上档**（官方定价页：Free 档 "API access" 无勾，Pro/Business 档有）→ **免费档无 API**
- **API 形式**（第三方 skill 文档 https://skillsmp.com/creators/duckduckgo/autoconsent/agents-skills-publicwww-search ，【实践观点】）：
  - `https://publicwww.com/websites/{QUERY}/?export=csvsnippetsu&key=$KEY` 下载 CSV，格式 `url;rank;snippet`
- **限流**：官方按「搜索次数/天」和「导出条数/天」限制（如 Pro 100 次/天、100K 行）
- **能否嵌入 Python 脚本**：**是**（GET + CSV 解析），但**需付费 key**
- **证据等级**：定价/API 有无限流 ＝【官方推荐】（官方 pricing 页）；API 参数格式 ＝【实践观点】
- **能否补上本缺口**：**不能补本缺口**。它搜的是「哪些网站用了某段 HTML/JS」，与「GitHub 上找开源项目」无关；仅当任务是「找用了某 SDK 的网站」时才相关。

---

## 4. 替代路径：批量数据集

### 4.1 【C13】GH Archive（含 BigQuery 公共数据集）— 数据集

- **URL**：官网 https://www.gharchive.org/ ｜BigQuery 入口 https://console.cloud.google.com/bigquery （数据集 `githubarchive`）
- **内容**：GitHub **公开事件流**（Star/Fork/Issue/PR/Release/Commit 等 15+ 类事件），按小时归档为 `.json.gz`，可 `wget` 直取：
  - `https://data.gharchive.org/2015-01-01-15.json.gz`；归档自 **2015-01-01 起为 Events API，2011-02-12 起为旧 Timeline API**
- **BigQuery 表**：`githubarchive.day.YYYYMMDD` / `githubarchive.month.YYYYMM` / `githubarchive.year.YYYY`
- **免费额度**：官方「**1 TB 数据/月免费**」；官方称数据集**每小时自动更新**
- **许可证**：官网/仓库未在本次访问页面标注明确许可（原 happydust 镜像标注 MIT License，但该仓库为个人镜像，**非官方，未验证**）
- **是否需要 key**：**是**（用 BigQuery 需 Google Cloud 项目并启用 BigQuery API）
- **能否程序化调用**：**是**（BigQuery client 库），但**需 GCP 账号 + 计费项目**；或用 HTTP 拉 `.json.gz`（无需 key，但数据量巨大）
- **适合「按主题找项目」吗**：**间接适合、不直接**。它只有「事件」没有「主题/关键词索引」——想按主题找项目，得先有候选仓库名单，再用事件流验证活跃度/热度。**已知的一个反例证据**：一篇中文实操文（来源未署名，标注在搜索结果中，【实践观点】）展示了用 BigQuery 查某仓库的 star 日增趋势，属于「已知仓库 → 查趋势」，而非「关键词 → 发现仓库」
- **能否嵌入 Python 脚本**：**需重大改造**（GCP 依赖或大文件下载解析）
- **证据等级**：【官方推荐】（gharchive.org 官方站）
- **能否补上本缺口**：**不能直接补**。它解决「验证/排序已有候选」，不解决「从 0 发现候选」。

### 4.2 【C14】GitHub Repos 公共数据集（BigQuery）— 数据集

- **URL**：`bigquery-public-data.github_repos`（Google Cloud Marketplace 数据集；本次未直接访问 GCP 控制台页，来源为第三方清单 https://github.com/duo-labs/secret-bridge/blob/master/DATASETS.md ，【实践观点】）
- **内容**：据该第三方清单称，是「完整快照，覆盖 280 万+ 开源 GitHub 仓库的内容」——**数字来自第三方清单，未验证**
- **能否程序化调用**：是（BigQuery SQL），需 GCP
- **能否嵌入 Python 脚本**：**需重大改造**
- **证据等级**：【实践观点】（第三方 DATASETS.md）
- **能否补上本缺口**：**不能直接补**。是**全量代码快照**，理论可用 SQL `LIKE` 按内容筛，但**无仓库元数据/主题排序**，且快照**非实时**，不适合「找当下活跃的某主题项目」。

### 4.3 【C15】GHTorrent — 数据集

- **URL**：https://ghtorrent.org/ ｜FAQ https://github.com/yul11a/ghtorrent.org/blob/master/faq.md ｜下载页 `ghtorrent.org/downloads.html`（FAQ 中引用）
- **内容**：在 GH Archive 事件流之上做「依赖式抓取」，产出两套库：**MySQL（关系视图）+ MongoDB（原始 JSON）**；有 SQL dumps 与在线访问服务
- **许可证**：**双许可**——非商用（教育/研究/个人）**CC-BY-SA**；商用需联系维护者（FAQ 原文）
- **⚠️ 实际可用性风险**：本次访问 `https://ghtorrent.org/` 首页**返回的是无关的第三方营销内容（疑似域名被抢注/挂靠）**，**并非 GHTorrent 官方页面**；FAQ 与 GitHub 镜像（https://github.com/yul11a/ghtorrent.org ）仍可访问。→ **下载页可达性与数据是否仍在更新，本次未验证**（多处第三方资料指向「数据截止约 2019 年」，但**本次未找到官方停更声明，未验证**）
- **能否程序化调用**：是（MySQL/Mongo 连接），需自行部署数据库
- **能否嵌入 Python 脚本**：**否/需重大改造**（要 MySQL 客户端 + 本地导入多 GB dump）
- **证据等级**：FAQ ＝【官方推荐】；首页异常与更新状态 ＝【实践观点】/ 未验证
- **能否补上本缺口**：**不能补**。面向历史学术分析，需自建库、数据可能停更，与「免依赖嵌入脚本」目标完全相反。

---

## 5. 给主代理的结论

### 5.1 最值得嵌入的方案（1-2 个）

**首选：【C1】GitHub 官方 `/search/repositories`，直接复用现有 `fetch()` 函数。**

理由（全部基于已核实事实）：
1. **零新增依赖**：现有 `http_fetch.py` 已用 `urllib.request`，`fetch()` 已内建「token 注入 + 403 限流识别与退避 + 本地缓存 + 超时重试」。追加搜索只需新增一个函数，把 URL 拼成 `https://api.github.com/search/repositories?q=<urlencoded>&sort=stars&order=desc&per_page=100&page=N`，然后复用 `fetch()` + 解析 `items[]`。
2. **字段零成本对接**：`/search/repositories` 的 `items[]` 里就是 `full_name` / `stargazers_count` / `forks_count` / `pushed_at` / `language` / `license` / `description` / `html_url`，**与脚本现有 `GITHUB_FIELDS` 同源**，解析与 TSV/JSON 输出逻辑可整段复用。
3. **限流已知且可管理**：认证 30 次/分钟、未认证 10 次/分钟；脚本已有 `AIWF_GITHUB_MAX_WAIT` / `AIWF_GITHUB_MAX_RETRY` 参数，天然适配。
4. **与「先发现、再取指标」的工作流天然串联**：C1 拿候选 `full_name` 列表 → 现有 `--github-repo` 并发取详细指标，形成闭环。
5. **官方端点，稳定性最高**（对比 grep.app 无官方文档、GHTorrent 首页异常）。

**次要备选（若必须复用外部工具）：【C4】`gh search repos --json fullName,stargazersCount,url`。** 官方手册完整、JSON 字段含 star/fork/language/license，一行拿到结果；代价是脚本要 `subprocess` 调外部二进制并依赖 `gh auth` 登录态。**不建议**引入 PyGithub/ghapi/github3.py 等库来「解锁搜索」——它们只是在 REST 上包一层，却给一个刻意零依赖的脚本平添依赖与许可约束（PyGithub 还是 LGPL）。

### 5.2 明确排除

| 候选 | 排除理由 |
|---|---|
| C2 `/search/code` | 需认证且仅 10 次/分钟、只看默认分支、<384KB、必须有搜索词；适合「找代码」不适合「按主题找项目」 |
| C3 `/search/topics` | 只返回 topic 元信息，不含仓库列表；单独用无法闭环 |
| C5/C6/C7 PyGithub/ghapi/github3.py | 均需新增第三方依赖；能力未超出 C1+现有脚本 |
| C8 gh-search(PyPI) | 外部 CLI + 强依赖 Python 3.12+，不适合内嵌 |
| C9 Sourcegraph | 重、需 token/实例配置；对「按主题发现」过重 |
| C10 grep.app | 无官方文档、参数不稳、无仓库元数据 |
| C11 searchcode.com | 已转型为「单仓库分析 MCP」，与「按关键词发现」错位 |
| C12 publicwww | 索引网页源码而非 GitHub 仓库；免费档无 API |
| C13/C14 GH Archive / GitHub Repos | 只能「验证/排序已有候选」，不能「从 0 发现候选」，且需 GCP |
| C15 GHTorrent | 需自建 MySQL、官网首页异常、数据更新状态未验证 |

### 5.3 给主代理的实测建议（避免编造数字）

- 本笔记**未运行任何请求**，因此**未断言任何 star/fork/下载量数字**。
- 建议主代理实测时优先验证 3 件事：
  1. `GET /search/repositories?q=<主题>&sort=stars&order=desc&per_page=100` 在带 `GITHUB_TOKEN` 下返回的 `total_count` 与 `items[].full_name`（确认字段可直接喂给现有 `--github-repo`）。
  2. 未认证时是否如官方所说为 10 次/分钟（观察响应头 `X-RateLimit-Limit`、`X-RateLimit-Remaining`）。
  3. grep.app 的实际参数名（`f.lang` vs `l`，`regexp` vs `f.regexp`）——本笔记中该处**多源矛盾，标为未验证**，若要用必须实测。

---

## 附：本次访问过的页面（证据索引）

| 候选 | URL | 证据等级 |
|---|---|---|
| C1/C2/C3 | https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28 | 【官方推荐】 |
| C1 中文镜像 | https://githubdocs.cn/en/rest/search/search?apiVersion=2022-11-28 | 【官方推荐】(镜像) |
| C2 补充 | https://fulll.github.io/github-code-search/reference/github-api-limits | 未验证 |
| C4 | https://cli.github.com/manual/gh_search_repos | 【官方推荐】 |
| C4 限流数字 | https://skillmd.ai/skills/mastering-github-cli | 【实践观点】 |
| C5 | https://pypi.org/project/PyGithub/ ｜ https://pygithub.readthedocs.io/en/v2.10.0/examples/MainClass.html | 【官方推荐】 |
| C6 | https://pypi.org/project/ghapi/ ｜ https://deps.dev/pypi/ghapi/2.1.0 | 【官方推荐】 |
| C7 | https://pypi.org/project/github3.py/ ｜ https://libraries.io/pypi/github3.py/0.3 ｜ https://deps.dev/pypi/github3-py/3.1.2 | 【官方推荐】 |
| C8 | https://pypi.org/project/gh-search/ | 【官方推荐】 |
| C9 | https://sourcegraph.com/docs/api/overview ｜ https://mintlify.wiki/sourcegraph/docs/api/overview | 【官方推荐】 |
| C10 | https://docs.rs/crate/grepapp_haystack/1.16.33 ｜ https://deepwiki.com/ai-tools-all/grep_app_mcp/4-grep.app-integration | 【实践观点】 |
| C11 | https://searchcode.com/ ｜ https://searchcode.com/openapi.json （引用自官网） | 【官方推荐】 |
| C12 | https://publicwww.com/prices.html ｜ https://skillsmp.com/creators/duckduckgo/autoconsent/agents-skills-publicwww-search | 【官方推荐】+【实践观点】 |
| C13 | https://www.gharchive.org/ | 【官方推荐】 |
| C14 | https://github.com/duo-labs/secret-bridge/blob/master/DATASETS.md | 【实践观点】 |
| C15 | https://github.com/yul11a/ghtorrent.org/blob/master/faq.md ｜ https://ghtorrent.org/ (首页异常) | 【官方推荐】 |
