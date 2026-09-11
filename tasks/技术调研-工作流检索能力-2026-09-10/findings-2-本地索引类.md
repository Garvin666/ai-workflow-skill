# findings-2：让本地工作流具备「索引 + 快速检索」能力的开源方案

- 调研日期：2026-09-10
- 调研方式：纯联网检索（WebSearch + WebFetch），**未运行任何实测**；不写入任何 star 数 / 内存占用 / 跑分数字
- 现状：ai-workflow 检索手段只有 Glob + 行级正则 Grep，**无索引层**，每次现搜
- 目标场景：① ~1.4GB 代码审查数据集（大量文本/JSON，超 GitHub 限制）搜不动；② 本地大代码仓库跨文件检索慢
- 证据分级：**【官方推荐】**＝官方文档/手册/README 原文；**【实践观点】**＝社区帖/聚合站/二手（数字一律不当证据）；**【反例】**＝官方明确说明的限制
- **不确定的一律标「未验证」**；所有事实来自本次实际访问过的页面，URL 随条给出

---

## 0. 结论速览（先看这条）

- **没有「一个工具通吃」的方案**。三大路线各管一段：
  1. **命令行扫描增强**（ripgrep 生态）：零安装负担，但**本质仍是全量扫描**，对 1.4GB/大仓库只能"扫得更快"，不能"跳过不相关的字节"。
  2. **建索引 + 检索**（tantivy / DuckDB-FTS / SQLite-FTS5 / Zoekt / ugrep-indexer）：先付建索引成本，换后续检索的秒级响应。**这是补上"索引层"的正路**。
  3. **直查文件不建库**（DuckDB / DataFusion / Polars）：对结构化/半结构化（JSON/CSV/Parquet）可**零导入**直接 SQL，Windows + Python 友好度最高。
- **Windows + Python 是本地的硬约束**：JVM/需守护进程的方案（Lucene/ES/OpenSearch/OpenGrok/livegrep/TypeSense-server）在本机落地成本高，列为"重方案/备选"。
- **关键区分**：`fzf / ripgrep / ag / sift / GNU grep` 全部是**每次扫描**（fzf 每次从管道读列表）；真带**持久化索引**的是 `ugrep-indexer / tantivy / DuckDB-FTS / SQLite-FTS5 / Zoekt / cindex / Hound / livegrep / Recoll / DocFetcher / Everything / AnyTXT`。

---

## 1. 命令行全文检索

| # | 名称 | URL | 类别 | 语言 / Python 可用性 | 是否支持索引 | Windows | 许可证 | 增量更新 | 证据等级 |
|---|------|-----|------|----------------------|--------------|---------|--------|----------|----------|
| 1 | ripgrep (rg) | https://github.com/BurntSushi/ripgrep | CLI 全文检索 | Rust / 无绑定，需 subprocess | **每次扫描**（无索引） | ✅ 一等公民，逐版本出 Windows 二进制 | MIT 或 UNLICENSE 双许可（官方 README 原文） | 不适用 | 【官方推荐】 |
| 2 | ugrep (+ugrep-indexer) | https://github.com/Genivia/ugrep ; https://github.com/Genivia/ugrep-indexer | CLI 全文检索（**带索引**） | C++ / 无绑定，需 CLI | **真索引**：`ug --index`，索引器写入每目录隐藏文件 `._UG#_Store` | ✅ 仓库含 `msvc/` 与 `vs/` 工程（未实测） | BSD-3-Clause（ugrep-indexer 仓库页标注） | ✅ 索引器支持**增量更新**（按时间戳比对，`-f` 强制重建） | 【官方推荐】 |
| 3 | The Silver Searcher (ag) | https://github.com/ggreer/the_silver_searcher | CLI 全文检索 | C / 无绑定 | 每次扫描 | ⚠️ 官方称"Unofficial daily builds"，源码构建"It's complicated" | Apache-2.0 | 不适用 | 【官方推荐】+【反例】 |
| 4 | sift | https://github.com/svent/sift（README 亦指向 sift-tool.org） | CLI 全文检索 | Go / 无绑定 | 每次扫描 | ✅ 官方称提供 Linux/Windows/OSX/*BSD 二进制 | GPL-3.0 | 不适用 | 【官方推荐】 |
| 5 | fzf | https://github.com/junegunn/fzf | 交互式模糊查找器 | Go / 无绑定 | **无索引**，每次从 STDIN 读列表/遍历目录 | ✅ Chocolatey/Scoop/Winget/MSYS2 | MIT | 不适用 | 【官方推荐】 |
| 6 | fd | https://github.com/sharkdp/fd | 文件名查找（非内容） | Rust / 无绑定 | 每次扫描 | ✅ | MIT 或 Apache-2.0（未逐字核对） | 不适用 | 【官方推荐】 |

**要点补充（原文/来源）：**
- **ripgrep 官方 README**：「recursively searches the current directory for a regex pattern」「respect gitignore ... automatically skip hidden files/directories and binary files」「first class support on Windows, macOS and Linux」「Dual-licensed under MIT or the UNLICENSE」。支持 `-tpy/-Tjs` 文件类型过滤、`-E/--encoding`（UTF-16、latin-1、GBK、EUC-JP、Shift_JIS 等）、`-z` 搜压缩包；**大小限制**：无专门的"按大小跳过"选项（靠 gitignore/glob 间接控制）。
- **ripgrep 索引现状（重要，勿误引）**：作者在 **issue #1497「RFC: add ngram indexing support to ripgrep」**里长期规划索引（称"ripgrep at scale"），但**明确说明初版不做索引同步、不做相关度排序**；**CHANGELOG 到 15.2.0（2026-07-15）均未记录已发布的索引功能**。同时 master 分支出现提交 **「index: add some initial indexing scaffolding」(2026-07-22)**（见 Cargo.toml/.gitignore/tests 的最近提交）——属**开发中脚手架，未发布、未文档化**，标「未验证」。→ 现在**不能**把 ripgrep 当索引工具用。
- **ugrep 官方（ugrep-indexer README）**：「Index-based searching is typically faster ... it only searches those files that may match a specified regex pattern by using an index of the file」；索引为"monotonic indexer"，**准确度 vs 索引体积可调**（`-0`..`-9`）；`ugrep-indexer` 增量更新，`-I` 忽略二进制、`-X` 尊重 gitignore、`-z` 索引压缩包；**索引不跟随符号链接目录**；**索引器本身尚非多线程**（官方 0.9 beta 说明）。**已知限制【反例】**：`--index` **不支持** `-v/--invert-match`、`--filter`、`-P/--perl-regexp`、`-Z/--fuzzy`；复杂正则（大 Unicode 类 + `*`/`+`）会拖慢 `--index` 启动。
- **ag 官方**：Windows 需 winget/choco/MSYS2/Cygwin；README 里自陈 **「Exuberant Ctags ... Faster than Ag, but it builds an index beforehand. Good for *really* big codebases.」**（=官方承认纯扫描对超大代码库不够）。
- **fzf 官方**：**每次**从 STDIN 读列表，或（无管道时）遍历当前目录；与 ripgrep/fd 集成靠 `reload` 绑定**每次重跑搜索进程**，**不建索引**。

---

## 2. 可嵌入式索引库（Python 可用）

| # | 名称 | URL | 类别 | 语言 / Python 可用性 | 是否需独立服务进程 | 是否支持索引 | Windows | 许可证 | 增量更新 | 证据等级 |
|---|------|-----|------|----------------------|--------------------|--------------|---------|--------|----------|----------|
| 7 | Tantivy | https://github.com/quickwit-oss/tantivy | 嵌入式全文索引库 | Rust 库 / **官方 FAQ 指向 tantivy-py** | ❌ 否，**进程内库**（非 server） | ✅ 真索引（倒排，Lucene 风格） | ✅ 官方 README：「supports Linux, macOS, and Windows」 | MIT | ✅ 官方 FAQ：「Does tantivy support incremental indexing? — Yes.」 | 【官方推荐】 |
| 8 | tantivy-py | https://github.com/quickwit-oss/tantivy-py | Python 绑定 | Rust→Python / `pip`（未逐字核对包名） | ❌ 否 | ✅ 同上 | ✅（继承） | MIT（继承 Tantivy，未逐字核对该仓库） | ✅ | 【官方推荐】（Tantivy FAQ 点名） |
| 9 | Whoosh | https://github.com/mchaput/whoosh | 纯 Python 全文索引库 | Python / 原生 | ❌ 否 | ✅ 真索引（倒排，BM25F） | ✅（纯 Python，无编译） | BSD-2-Clause（官方「simplified BSD」） | ⚠️ 支持增删改文档，但**项目近乎停更**（仓库最近提交 2021/2022） | 【官方推荐】+【反例】 |
| 10 | Apache Lucene | https://lucene.apache.org/core/ | Java 索引库 | Java / **PyLucene**（官方 "Implementations in other programming languages available"） | ❌ 库（但 Java，需 JVM） | ✅ 真索引；官方称「incremental indexing as fast as batch indexing」 | ✅（JVM 跨平台） | Apache-2.0 | ✅ 官方明示增量 | 【官方推荐】 |
| 11 | Elasticsearch | https://www.elastic.co/ ; 许可 FAQ https://www.elastic.co/pricing/faq/licensing/ | 分布式搜索引擎 | Java / 官方 Python 客户端 | ✅ 需独立服务 | ✅ 真索引 | ✅ | **SSPL 1.0 + Elastic License 2.0 + AGPLv3 三选一**（官方 FAQ 原文，2024-09 起加 AGPLv3） | ✅ | 【官方推荐】+【反例】重方案 |
| 12 | OpenSearch | https://opensearch.org/ | 分布式搜索引擎（ES 7.10 fork） | Java / 官方 Python 客户端 | ✅ 需独立服务 | ✅ 真索引 | ✅ | Apache-2.0（Linux 基金会治理） | ✅ | 【实践观点】（二次源，用于 fork/许可证说明） |
| 13 | Meilisearch | https://github.com/meilisearch/meilisearch | 搜索引擎（REST） | Rust / 官方 Python 客户端 | ✅ 需独立服务 | ✅ 真索引 | ⚠️ 官方仅支持 **Windows Server 2022+**，「Windows 10+ may work but is not officially supported」；可 Docker | **MIT + BUSL-1.1**（官方 LICENSE：`SPDX-License-Identifier: MIT AND BUSL-1.1`，EE 部分走 BUSL） | ✅ 运行中增量写入 | 【官方推荐】 |
| 14 | Typesense | https://github.com/typesense/typesense | 搜索引擎（REST） | C++ / 官方 Python 客户端 `pip install typesense` | ✅ 需独立服务 | ✅ 真索引（内存型 + 磁盘） | ⚠️ 官方只发 Linux/macOS 二进制，**Windows 需 Docker**（未提原生） | **Server: GPL-3.0；客户端: Apache-2.0**（官方 FAQ「Why the GPL license?」） | ✅ | 【官方推荐】 |
| 15 | Sonic | https://github.com/valeriansaliou/sonic | 轻量 ID 索引后端 | Rust / **社区** Python 库（asonic 等，非官方） | ✅ 需独立服务（Sonic Channel 协议，**无 HTTP API**） | ✅ 真索引（存 ID，不存原文） | ⚠️ 官方只发 Debian 包/源码/Docker，**Windows 未提及** | **未验证**（仓库页未见许可声明） | ⚠️ 索引改动轻量，但 **FST 重建有批处理延迟**（官方「Real-time limits」） | 【官方推荐】+【反例】 |

**要点补充：**
- **Tantivy 官方定位**：「closer to Apache Lucene ... not an off-the-shelf search engine server, but rather a crate」→ **正是"嵌入式索引层"**。特性含：增量索引、多线程索引、BM25、Mmap 目录、JSON 字段、压缩文档存储。**官方宣称"约比 Lucene 快 2x"属厂商基准，不作为证据**。
- **Meilisearch/Typesense/Sonic 都是"独立服务进程"**：对"嵌入 Python 工作流、少运维"的目标属**重方案**；若不想常驻进程，应优先 7/8/9/24。
- **Whoosh 风险【反例】**：纯 Python 免编译是优点，但**维护几乎停滞**（最近提交 2022-01；README 无活跃承诺），大语料性能未知，列为"仅在不想装原生依赖时"的备选。
- **Sonic 官方限制【反例】**：只存 ID 不存原文；查询返回 ID 需外部库回查；「only keeps the N most recently pushed results for a given word」；FST 需重建，新词不立即可搜。

---

## 3. 代码专用索引 / 搜索服务

| # | 名称 | URL | 类别 | 语言 / Python 可用性 | 索引机制 | 是否需服务 | Windows | 许可证 | 增量更新 | 证据等级 |
|---|------|-----|------|----------------------|----------|-----------|---------|--------|----------|----------|
| 16 | Zoekt（Sourcegraph） | https://github.com/sourcegraph/zoekt | 代码搜索索引 | Go / 无官方 Python，可跑 CLI 二进制 | **trigram 索引** + 语法解析；官方「works well for a variety of programming languages」 | 可选：有 `zoekt-index`/`zoekt` **纯 CLI**，也有 indexserver+webserver | ⚠️ Go 可跨平台编译，但**未见官方 Windows 支持声明**（未验证） | **未验证**（仓库有 LICENSE 但抓取未见正文） | ✅ 提供 `zoekt-local-sync` 增量（`-f` 应用变更，默认预览） | 【官方推荐】 |
| 17 | livegrep / codesearch | https://github.com/livegrep/livegrep | 交互式正则代码搜索 | C++ / 无 Python 绑定 | **trigram 索引**（re2 引擎），索引文件 3–5x 源码，mmap | ✅ 需 codesearch 后端 + livegrep 前端 | ❌ 官方只述 Linux/Bazel 构建（未提 Windows） | 2-clause BSD（COPYING：License under the 2-clause BSD license） | ⚠️ 支持 `-dump_index`/`-load_index` 复用索引；增量需重跑索引（未验证细粒度增量） | 【官方推荐】 |
| 18 | google/codesearch (cindex/csearch) | https://github.com/google/codesearch | CLI 索引式正则搜索 | Go / 无 Python 绑定 | **trigram 索引**（Russ Cox「Regular Expression Matching with a Trigram Index」） | ❌ 纯 CLI（`cindex` 建、`csearch` 查） | ⚠️ Go 可编译，未声明 Windows（未验证） | **未验证**（LICENSE 文件存在，抓取未见正文；Go 生态通常 BSD-3） | ⚠️ 每次 `cindex` 重建目录索引（官方未述细粒度增量） | 【官方推荐】 |
| 19 | Hound | https://github.com/hound-search/hound | 代码搜索服务 | Go 后端 + React 前端 / 无 Python 绑定 | **trigram 索引**（同 Russ Cox 文章） | ✅ 需 `houndd` 服务（默认 :6080，含 Web UI） | ⚠️ 官方「only tested on MacOS and CentOS」「**Hound on Windows is not supported but we've heard it compiles and runs just fine**」 | **未验证**（LICENSE 文件存在，抓取未见正文） | ✅ 轮询更新（默认每 30s；`local` 驱动可 `watch-changes` 自动重索引） | 【官方推荐】 |
| 20 | OpenGrok | https://github.com/oracle/opengrok | 源码交叉引用/搜索 | Java / 无 Python 绑定 | **Lucene 倒排** | ✅ 需 Java servlet 容器（可 Docker） | ⚠️ Docker 可行，原生需 JVM 环境（未验证） | **未验证**（README 未列；Oracle 项目） | ⚠️ 版本升级常需**全量 reindex**（官方「Updating」：minor 需 clean reindex） | 【官方推荐】+【反例】 |
| 21 | Universal ctags | https://github.com/universal-ctags/ctags | 符号索引（非全文） | C / 有 CLI，可被编辑器调用 | 生成**符号 tag 索引**（非全文倒排） | ❌ 纯 CLI | ✅ | GPL-2.0（未逐字核对） | ✅ 可增量重跑 | 【实践观点】（ag README 与社区提及） |

**要点补充：**
- 这一类**普遍是"服务式"或"Go/C++ 工具链"**，对"Windows + 纯 Python 调用"友好度低。若走此路，**Zoekt 的纯 CLI 模式**（`zoekt-index` + `zoekt`）最接近"可被工作流 subprocess 调用"，但 **Windows 可行性未验证**。
- **Zoekt 官方**：「fast substring and regexp matching on source code ... boolean operators (and, or, not)」「基于 trigram indexing 和 syntactic parsing」；**推荐安装 Universal ctags** 以提供符号信号。索引/搜索可纯命令行。
- **livegrep 官方**：定位「interactive regex search of ~gigabyte-scale source repositories」→ **正好覆盖场景②"大仓库"**；但需 Bazel 构建 + 后端服务，**Windows 支持未述**。
- **Hound 官方【反例】**：Windows 官方**不支持**（可编译运行属社区传闻）；且需常驻服务。

---

## 4. 结构化数据直查（大 JSON/CSV/Parquet 不导入数据库）

| # | 名称 | URL | 类别 | 语言 / Python 可用性 | 是否支持索引 | Windows | 许可证 | 增量更新 | 证据等级 |
|---|------|-----|------|----------------------|--------------|---------|--------|----------|----------|
| 22 | DuckDB | https://github.com/duckdb/duckdb ; 文档 https://duckdb.org/why_duckdb | 嵌入式分析型 DB | C++ / **官方 Python 包**（`pip install duckdb`） | **默认直查文件，无需建索引**；另可建二级索引；FTS 扩展可建全文倒排 | ✅ 官方明列 Linux/macOS/Windows | **MIT**（官方「released under the very permissive MIT License」） | ✅ FTS 扩展新版支持 `incremental`（触发器等，见 duckdb-fts）；默认 FTS 索引为静态快照需重建 | 【官方推荐】 |
| 23 | Apache DataFusion | https://github.com/apache/datafusion ; 文档 https://datafusion.apache.org/ | 可嵌入查询引擎 | Rust / **官方 Python 绑定** datafusion-python | 无持久化全文索引；**直接查询文件** | ⚠️ 官方文档主打 Rust/Python 库，**Windows 未明确声明**（未验证） | Apache-2.0（Apache 项目，未逐字核对 LICENSE 文件） | 不适用（无索引层） | 【官方推荐】 |
| 24 | Polars | https://github.com/pola-rs/polars | 查询引擎 | Rust 核心 + **Python 一等绑定** | 无全文索引；**lazy/streaming 直扫文件** | ✅（官方支持主流平台，未逐字核对 Windows 句） | **MIT**（官方「licensed under the MIT License (SPDX: MIT)」） | 不适用 | 【官方推荐】 |
| 25 | SQLite FTS5 | https://www.sqlite.org/fts5.html | 嵌入式全文索引扩展 | C / Python 标准库 `sqlite3`（是否默认启用 FTS5 需实测，未验证） | ✅ **真倒排索引**（term→rowid/列/offset，由 b-tree 组成） | ✅（SQLite 跨平台；FTS5 默认随 amalgamation） | public domain（SQLite 惯例，**FTS5 页面未写**，未验证） | ⚠️ 需自行维护同步（contentless/外部内容表各有限制） | 【官方推荐】 |

**要点补充：**
- **DuckDB 直查文件（官方原文）**：`SELECT * FROM 'test.csv';`、`read_csv(...)`、`read_parquet('test.parquet')`、`read_json('test.json')`，**无需先导入**；支持压缩 CSV（`.csv.gz`）；v1.3.0 起文件读取器带 `filename` 虚拟列（**正好用于"带来源的文件检索"**）。
- **DuckDB 定位（官方）**：「in-process」「no DBMS server software to install ... completely embedded within a host process」「no external dependencies」；Python 包**可直接在 Pandas 数据上跑查询而不拷贝**。→ **Windows + Python 落地成本最低**。
- **DuckDB FTS 扩展（官方文档）**：`INSTALL fts; LOAD fts;` → `PRAGMA create_fts_index(...)` + `match_bm25(...)`；官方明言「similar to SQLite's FTS5 extension」。**社区/新版扩展 duckdb-fts** 提供 `incremental`（触发器维护 INSERT/DELETE）等选项，但**默认索引是静态快照**：官方「the FTS index will not update automatically when input table changes」（旧文档原文）。
- **Polars 官方**：「Larger-than-RAM: the streaming engine processes datasets that don't fit in memory」「process your 250GB dataset on your laptop ... `collect(engine='streaming')`」；`pl.scan_parquet(...)` 为惰性扫描。
- **DataFusion 官方**：「extensible query engine written in Rust」「built-in support for CSV, Parquet, JSON, and Avro」「Python Bindings are also available」「columnar, streaming, multi-threaded, vectorized execution engine」→ **库/框架**，非服务。
- **SQLite FTS5 官方**：自 **3.9.0（2015-10-14）起包含在 amalgamation**；`--enable-fts5` / `SQLITE_ENABLE_FTS5` 启用；有 **contentless / contentless-delete / external content** 三种表各自的限制（官方列明）。**注意**：Python 自带 sqlite3 是否启用 FTS5 因发行版而异，须实测（未验证）。

---

## 5. 桌面级本地文档索引

| # | 名称 | URL | 类别 | 语言 / Python 可用性 | 是否支持索引 | Windows | 许可证 | 增量更新 | 证据等级 |
|---|------|-----|------|----------------------|--------------|---------|--------|----------|----------|
| 26 | Recoll | https://www.recoll.org/（features 页 404，佐证：https://www.freshports.org/deskutils/recoll/ 、维基） | 桌面全文搜索 | C++/Python / **有 Python API + CLI** | ✅ 真索引（**Xapian** 后端） | ⚠️ 有 Windows 版但"配置更复杂"（实践观点） | GPL-2.0-or-later（freshports/nixpkgs 标注 GPLv2+） | ✅ 批量/实时（inotify 或定时） | 【官方推荐】（CLI 名 `recollq`/`recollindex`） |
| 27 | DocFetcher | https://docfetcher.sourceforge.io/ | 桌面全文搜索 | Java / GUI 为主 | ✅ 真索引（**Apache Lucene**） | ✅ Windows/Linux/macOS，含便携版 | Eclipse Public License（官方原文） | ✅ 运行时或后台守护检测变更并更新 | 【官方推荐】/命令行调用**未验证** |
| 28 | Everything (es.exe) | https://www.voidtools.com/ ; CLI https://github.com/voidtools/ES | Windows 文件名索引 | C++ / 无 Python，**有官方 CLI `es.exe`** | ✅ 真索引（**仅文件名/目录名**，读 NTFS MFT） | ✅ **Windows 专属** | **Freeware（非开源）**；二进制近 Expat/MIT（维基称，未逐字核对源） | ✅ 实时（NTFS Change Journal / USN） | 【官方推荐】+【反例】 |
| 29 | AnyTXT Searcher | https://anytxt.net/ ; 镜像 https://gitlab.com/Anytxt/anytxt-searcher | Windows 全文搜索 | C++ / 无 Python，**有命令行参数** | ✅ 真索引（文档内容全文倒排） | ✅ **Windows 专属**（7/10/11…） | **未验证**（未开源声明；GitLab 镜像存在但许可未标注） | ✅ 后台索引服务，NTFS 下读 USN 日志增量 | 【官方推荐】 |

**要点补充：**
- **CLI 可调用性是"能否嵌入工作流"的关键**：
  - **Recoll**：有 `recoll` / `recollindex` / `recollq`（man 页随包），**可直接被 subprocess 调用**；且有 **Python API**（`import recoll`）。
  - **Everything**：官方 **`es.exe`** 命令行接口，支持搜索语法/正则/CSV-JSON 导出（`-csv -json -tsv`），前提是 **Everything 已安装并运行**（官方 Requirements）；另有 **Everything SDK**。→ **最易嵌入的 Windows 文件名层**。
  - **AnyTXT**：官方更新日志记 **「2020-2-27 Added the command line」**（可传关键词/盘符/扩展名），但其行为细节未在官网文档化（未验证）。
  - **DocFetcher**：官网**只描述 GUI**，**未发现命令行/查询 API**（未验证，倾向于"不可直接 subprocess 调用"）。
- **Everything 官方【反例·关键】**：**只索引文件名，不索引内容**——「File content is not indexed, searching content is slow」。→ **不能**用它解决 1.4GB 数据集的内容检索，只能做"按文件名/路径快速定位"。
- **DocFetcher 官方**：索引「in the order of milliseconds」；索引速度经验值「200 files per minute」；更新「much faster ... a couple of seconds」（**属厂商口径，不作为基准**）。

---

## 6. 候选汇总（共 29 条，均含链接）

- **命令行扫描类（无索引）**：ripgrep、ag、sift、fzf、fd
- **命令行带索引**：ugrep（+ugrep-indexer）
- **可嵌入索引库（Python 可用）**：Tantivy、tantivy-py、Whoosh、Lucene/PyLucene
- **搜索引擎服务（重）**：Elasticsearch、OpenSearch、Meilisearch、Typesense、Sonic
- **代码专用索引/服务**：Zoekt、livegrep、google/codesearch、Hound、OpenGrok、Universal ctags
- **结构化直查/嵌入式 FTS**：DuckDB（+FTS 扩展）、DataFusion、Polars、SQLite FTS5
- **桌面文档索引**：Recoll、DocFetcher、Everything、AnyTXT Searcher

> 已按要求 ≥10 条；本清单 29 条，每条字段见上方各节表格。**所有 star/性能/内存数字均未采信**，主代理需另行实测。

---

## 7. 给主代理的结论（针对两个具体场景）

### 场景① ~1.4GB 代码审查数据集（大量文本/JSON，超 GitHub 限制）搜不动

**如果是"结构化的 JSON/JSONL/CSV/Parquet"（能解析字段）→ 首选 DuckDB 直查（路线 A）。**
- 理由：官方支持 `read_json`/`read_parquet`/`read_csv` **零导入直查** + 带 `filename` 虚拟列（可回溯来源）；**进程内、无服务、MIT、Windows + Python 一等公民**；无需预先建索引即可跑聚合/过滤；数据不再变大时连索引维护都省了。
- 若需要"按关键词全文找、还要 BM25 排序"→ 在 DuckDB 内 `INSTALL fts` 建 **FTS 索引**（官方对标 SQLite FTS5）。**代价**：FTS 索引默认是静态快照，数据变更需重建或改用支持 `incremental` 的新版扩展。

**如果是"一大批自由文本/代码，字段不规整"→ 首选"建 tantivy 索引"（路线 B）。**
- 理由：tantivy 是**嵌入式库**（非服务），**官方明示增量索引 + Windows 支持**，`tantivy-py` 让 Python 直接调用；这正是 ai-workflow 缺的"索引层"，且能塞进现有 Python 工具链。

**两条路线的取舍（务必让主代理知道）：**
| 维度 | A. DuckDB 直查 | B. 建 tantivy 索引 |
|------|----------------|--------------------|
| 语料形态 | 结构化/半结构化（JSON/CSV/Parquet）最顺 | 自由文本/代码最顺 |
| 首次成本 | **几乎为零**（不建索引，直接扫） | 需一次性建索引（时间/磁盘） |
| 反复检索 | 每次仍要扫/过滤文件（除非建了 FTS/二级索引） | **后续每次检索快**（倒排直接命中） |
| 全文相关度排序 | 需 FTS 扩展（BM25） | 内建 BM25 |
| 增量维护 | FTS 默认静态快照，需重建 | **官方支持增量** |
| 运维/依赖 | 单文件嵌入式，最轻 | Python 包，轻 |
- **判据一句话**：**数据是"字段"→ DuckDB 直查；数据是"文本"→ 建 tantivy 索引**。两者并非互斥：可"先用 DuckDB 直查做结构化过滤，再把命中的文本字段灌进 tantivy 做全文"。
- **不推荐**：Sonic（只存 ID、有重建延迟、无 Windows 支持）、ES/OpenSearch（服务重、许可复杂）、Whoosh（停更）。

### 场景② 本地大代码仓库跨文件检索慢

**首选：`ugrep --index`（+ ugrep-indexer）作为"rg 的带索引替代/补充"（低改造、命令行级）。**
- 理由：ugrep 与 grep/ripgrep 命令习惯几乎一致，**唯一在"命令行 grep"里内建真索引 + 增量更新**的方案；Windows 有工程支持；BSD-3 许可宽松。**适合"不动 Python 代码结构、只换/加一条 CLI"**。
- **已知限制【反例】**：`--index` 不支持 `-v`/`-P`/`--fuzzy`/`--filter`；索引器非多线程（大仓库首次建索引慢）；不适合"频繁改动的仓库"（索引需追赶）。

**次选 / 更强的代码语义检索：Zoekt（纯 CLI 模式）。**
- 理由：专为"大代码库 + 正则 + 布尔查询"设计，trigram 索引 + 符号信号；`zoekt-index` + `zoekt` 可纯命令行调用，`zoekt-local-sync` 支持增量同步。**最贴近 livegrep 的能力但更好维护**。
- **风险**：**Windows 可行性未验证**（Go 可编译但无官方声明）、**许可证未验证**、首次索引成本高。**建议主代理先做 Windows 构建/真机验证再定。**

**若只需"按文件名/路径秒定位"，且不介意 Windows 专属 → Everything + `es.exe`。**
- 理由：读 NTFS MFT，文件名索引极快且事件驱动实时更新，`es.exe` 可被 subprocess 调用（支持 `-json`）。
- **反例**：**不索引内容**，只能解文件名层，**不解决内容检索**。

**明确不推荐（针对场景②）**：livegrep（Windows 未述、需 Bazel+服务）、Hound（官方不支持 Windows、需常驻服务）、OpenGrok（Java 容器 + 升级常需全量重建）、ag（2018 起未维护）、ripgrep 索引（**尚未发布**，脚手架阶段勿依赖）。

### 一句总纲
**补"索引层"优先顺序：结构化数据 → DuckDB；自由文本 → tantivy（Python 内嵌）；代码仓库命令行 → ugrep-indexer，重需求再评估 Zoekt（需先验证 Windows/许可）。避免为本地工作流引入 JVM/常驻服务类方案。**
