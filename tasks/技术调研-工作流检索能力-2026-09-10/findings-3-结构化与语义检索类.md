# findings-3：超越行级正则 —— 结构化 / 语义代码检索开源方案

- 调研日期：2026-09-10
- 调研方式：纯联网检索（WebSearch + WebFetch），**未运行任何实测、未跑任何工具**；因此本笔记只写「能力与限制」，不写任何性能/准确率/star 数字
- 现状背景：ai-workflow 的检索手段只有行级正则（Grep）与 Glob。两个缺口：
  - **缺口 A（跨行/跨语句结构）**：如「先调用 A 再调用 B 且中间没有 try」——行级正则原理上做不到
  - **缺口 B（语义相近但字面不同）**：如「找所有鉴权逻辑」而代码里写的是 `verify_jwt` / `check_token` / `authz_guard`
- **证据分级**：【官方推荐】＝官方文档/官方手册/官方项目页；【基准实测】＝有明确出处且被独立复现的实测（本笔记**无**此类条目，一律不写数字）；【实践观点】＝社区博客、聚合站、第三方包文档；【反例】＝被证明/被怀疑被高估的说法
- **铁律**：不采信厂商或论文宣传的「准确率提升 N%」「减少 80% 误报」「SWE-bench X%」等数字，一律归入【反例】或直接标注为宣传语。凡未亲自访问页面确认的字段，显式标「未验证」
- 硬约束（用户偏好，按优先级）：① 能跑 Windows ② 能 CLI 或 Python 调用 ③ 许可证宽松（MIT/Apache/BSD 优先，GPL 次之，非开源排除）④ 可离线

---

## 0. 先说结论

1. **补缺口 A（跨行结构）的最优解是 `ast-grep(sg)`**：MIT、Rust 单文件二进制、Windows 原生、离线、无需建库，CLI + `pip install ast-grep-cli` + JSON 输出三种接法，且顺带能做 lint 与安全重写。**若只能加一个工具，就加它**（第 7 节给理由与代价）。
2. **缺「语义」这一刀，向量检索是唯一解，但投入产出比目前偏低**：它解决的是缺口 B，而缺口 A 更痛、更常用。本地工作流的向量索引维护成本（模型体积、增量索引、chunk 策略）是长期负担，且**对「先 A 后 B 无 try」这类结构性约束完全无能为力**——两者是互补而非替代（第 7 节给出反面意见）。
3. **CodeQL 直接排除**：不是宽松许可证，闭源/私有代码需商业授权；且必须先建数据库。**comby 慎用**：2022 年后基本停更，**Windows 仅支持 WSL**（非原生）。

---

## 1. AST 结构化搜索与重写（缺口 A 的主力方案）

### 1.1 【C1】ast-grep（命令 `sg`）

- **URL**：https://github.com/ast-grep/ast-grep ｜文档 https://ast-grep.github.io/ ｜规则语义 https://ast-grep.github.io/guide/rule-config.html
- **类别**：AST 结构化搜索 + lint + 重写（tree-sitter 后端，Rust 实现）
- **支持语言**：多语言，经 tree-sitter 语法；官方规则页示例覆盖 C/C++/Dart/Go/Java/Kotlin/Python/Ruby/Rust/TypeScript/TSX/HTML/YAML，并支持在 `sgconfig.yaml` 里**自定义语言**（完整清单见文档 `/reference/languages`，本次未逐一核验）【官方推荐】
- **模式语法形态**：写「像普通代码」的 pattern，用 `$VAR` 捕获单个 AST 节点、`$$$` 捕获多个节点；另有 YAML 规则：原子规则 `pattern` / `kind` / `regex`，关系规则 `inside` / `has` / `follows` / `precedes`（可加 `stopBy: neighbor|end|<rule>` 与 `field`），复合规则 `all` / `any` / `not` / `matches`【官方推荐】
- **能否跨行/跨语句匹配**：**能**。单条 `pattern` 本身即可跨行（AST 节点不按行计）；跨语句/跨兄弟节点要靠关系规则 + `stopBy: end`。官方示例就是跨行的：`pattern: Promise.all($A)` + `has: { pattern: await $_, stopBy: end }`；「先 A 后 B」可用 `follows`/`precedes` 表达【官方推荐】。**注意**：官方明确列出 pattern **不支持**正则语法（`foo|bar`、`.*`、`\w`、`[a-z]` 都无效），要文本匹配时回头用 grep【实践观点，来源为第三方移植文档 https://github.com/code-yeongyu/pi-ast-grep ，与官方规则页一致】
- **Windows 支持**：**支持**。存在 win32-x64/arm64/ia32 的 npm 包（`@ast-grep/cli-win32-x64-msvc`），并支持 `scoop install main/ast-grep`、`pip install ast-grep-cli`【官方推荐】
- **许可证**：**MIT**【官方推荐】（npm/PyPI 项目页均标 MIT）
- **是否离线**：**完全离线**，无网络依赖、无需建库
- **是否需建库后查询**：**否**，直接扫源码
- **证据等级**：【官方推荐】

### 1.2 【C2】comby

- **URL**：https://github.com/comby-tools/comby ｜文档 https://comby.dev/docs/overview
- **类别**：结构化搜索 + 重写（**不建全量 AST**，用「平衡括号/字符串/注释」的通用分词器）
- **支持语言**：自称覆盖 ~every language，官方列出 Bash、C/C++、C#、Clojure、CSS、Dart、Elixir、Go、Java、JavaScript/JSX、Kotlin、PHP、Python、Ruby、Rust、Scala、Solidity、Swift、TSX/TypeScript、Terraform 等，另有 generic 兜底（YAML/VHDL 等）【官方推荐】
- **模式语法形态**：模板洞 `:[name]`，如 `if (:[condition])`、`(:[emoji] hi)`；匹配是语法感知的（懂字符串/注释/嵌套括号）
- **能否跨行/跨语句匹配**：**能跨行、能跨嵌套**（这是它的核心卖点，README 直接以「你写得出匹配这两个 if 且只匹配这两个的正则吗」作为对比）；**但只到"形状"层面，无法表达"中间不含 try"这类否定/语义约束**【官方推荐】
- **Windows 支持**：**仅 WSL**。官方 README 原文：「Windows Install the Windows Subsystem for Linux and install Ubuntu.」——**无原生 Windows 二进制**【官方推荐】
- **许可证**：Apache-2.0【官方推荐】
- **是否离线**：**是**（本地二进制，另有 docker 镜像）
- **是否需建库后查询**：**否**
- **证据等级**：【官方推荐】
- **风险标注**：仓库最近推送 2025-03、最新 release 1.8.1 发布于 2022-06（第三方聚合数据 https://awesome.ecosyste.ms/projects/github.com%2Fcomby-tools%2Fcomby ）→ 维护活跃度低，属【实践观点】

### 1.3 【C3】Semgrep（Community Edition）

- **URL**：https://semgrep.dev/ ｜CE 页 https://semgrep.dev/products/community-edition ｜文档 https://docs.semgrep.dev/getting-started/cli/
- **类别**：AST 语义模式匹配（主打 SAST，**但本身就是通用的结构化模式检索器**——`semgrep --lang python --pattern '$X == $X' <path>` 是官方文档里的用法）【官方推荐】
- **支持语言**：CE 声明 **30+ 语言**（PyPI 早期文档列出 Python/JS/Go/Java/C/TS/PHP/Ruby/OCaml，官方 CE 页称 30+）【官方推荐】
- **模式语法形态**：模式直接写成像源码（`exec(...)`），元变量 `$X` 跟踪同名变量，`...`（省略号）抽象掉任意序列/中间语句；规则用 YAML 组合 `patterns` / `pattern-not-inside` / `pattern-inside`；支持在 AST 节点内做 regex 文本匹配
- **能否跨行/跨语句匹配**：**能**。官方示例明确指出 `exec(...)` 会匹配跨多行的 `exec (\n bar \n )`；`pattern-not-inside` 官方示例即「open 之后没有 close」——本质上是**跨语句**匹配。CE 的深度/作用域限制见下
- **关键限制**：**CE 只能做单文件 / 单函数作用域分析；跨文件数据流（interfile）是商业版能力**（官方 CE 页与第三方评测 https://dev.co/security/open-source/semgrep 均如此表述）【官方推荐 + 实践观点】
- **Windows 支持**：**原生支持（GA）**。官方 CE 页给 Windows 安装方式 `python3 -m pip install semgrep`；Autumn '25 发布说明写「Native Windows support is GA for CLI and IDEs… without WSL or Docker」【官方推荐】
- **许可证**：**LGPL-2.1**（CE/OSS 引擎）【官方推荐】
- **是否离线**：**可离线**，但需注意：`--config auto` / 规则名（如 `p/default`）会**从 Semgrep Registry 联网下载规则**；完全离网时要改为 `--config <本地规则文件>`。第三方评测亦指出「air-gapped 环境需要手工管理规则」【实践观点】
- **是否需建库后查询**：**否**
- **证据等级**：【官方推荐】

### 1.4 【C4】tree-sitter 及其 query 语法

- **URL**：https://tree-sitter.github.io/ ｜query API https://tree-sitter.github.io/tree-sitter/using-parsers/queries/4-api.html ｜code navigation https://tree-sitter.github.io/tree-sitter/4-code-navigation.html
- **类别**：增量解析库（**是上面 ast-grep / 语义 chunk 的公共底座**），本身不是现成 CLI 搜索工具
- **支持语言**：**语法按语言单独安装**（tree-sitter grammar），生态覆盖上百种语言；Python 绑定 `py-tree-sitter` 有预编译 wheel【官方推荐 + 官方包页 https://openapps.pro/packages/py-tree-sitter 】
- **模式语法形态**：S-表达式 query，如 `(function_definition name: (identifier) @name) @definition.function`；支持捕获 `@name`、字段限定 `name:`、交替 `[...]`、重复 `(comment)*`，以及内置谓词 `#strip!` / `#select-adjacent!` / `#match?`【官方推荐】
- **能否跨行/跨语句匹配**：**能捕获跨行的 AST 节点**（节点天然跨行）；官方 `#select-adjacent!` 体现「相邻/顺序」概念。**但 query 是单层树模式**：想表达「A 之后 B 且中间无 try」这类**带否定的序列约束，query 语言没有直接语法，必须在宿主代码里遍历结果再过滤**——这是与 ast-grep YAML 规则的关键差距【实践观点，基于官方 query 文档能力边界推断，标注为未实测】
- **Windows 支持**：**支持**（`py-tree-sitter` 提供各平台预编译 wheel；另有 .NET 绑定明确列出 win-x86/x64/arm64）【官方推荐】
- **许可证**：**MIT**【官方推荐】（py-tree-sitter 项目页标 MIT）
- **是否离线**：**是**
- **是否需建库后查询**：**否**（按需解析即可；是否缓存由你自己决定）
- **证据等级**：【官方推荐】

### 1.5 【C5】CodeQL

- **URL**：https://codeql.github.com/ ｜CLI 文档 https://codeql.github.com/docs/codeql-cli/about-the-codeql-cli ｜库与查询仓库 https://github.com/github/codeql
- **类别**：语义代码分析引擎（**把代码当数据查询**，表达能力最强，含整程序数据流/污点追踪）
- **支持语言**：C/C++、C#、Go、Java/Kotlin、JavaScript/TypeScript、Python、Ruby、Swift（Kotlin/Swift 为 beta）【官方推荐】
- **模式语法形态**：QL 语言 + 标准库（`import TaintTracking::Global<...>`、`flowPath(source, sink)`），不是"写一段代码当模式"
- **能否跨行/跨语句匹配**：**能，且是最强的**——可表达调用顺序、数据流、异常处理路径等跨文件语义约束
- **Windows 支持**：**支持**（CLI 提供 Windows 包；文档提到 Windows 用户直接解压 zip）【官方推荐】
- **许可证**：**不是宽松开源**。查询库仓库（github/codeql）是 MIT，**但 CodeQL CLI/引擎单独授权**：免费仅限 OSI 开源项目、学术研究、以及 GitHub 上开源仓库的 CI；**闭源代码需商业许可**【官方推荐】（官方原文 "If you'd like to use the CodeQL CLI to analyze closed-source code, you will need a separate commercial license"）
- **是否离线**：可离线（需下载 bundle + 建库），规则 bundle 可预置
- **是否需建库后查询**：**是，必须**。`codeql database create`，编译型语言还要指定构建命令（如 `--command make`）【官方推荐】
- **结论**：**不满足用户的「许可证宽松」前提，建议排除**（除非只用于开源仓库的一次性深挖）
- **证据等级**：【官方推荐】

---

## 2. 核心对比：「同一条跨行查询，谁能查到、谁查不到」

**测试查询 Q**：在同一个函数体内，找出「先调用 `A()`、之后调用 `B()`，且两者之间**没有 `try`**」的所有位置。
（这是一个"跨行 + 顺序 + 否定"的复合约束，正好卡在行级正则的能力边界外）

| 工具 | 能查到？ | 原因 / 表达方式 | 证据 |
|---|---|---|---|
| **Grep / ripgrep（现状）** | **否** | 逐行匹配，跨行需 `-U`/多行模式，且无结构概念。`A(.*)[\s\S]*?B(` 会误报：同名函数、注释、字符串、缩进换行全部会被卷进来 | 【实践观点】 |
| **ugrep（C6）** | **勉强/脆弱** | 官方支持 `\n`、`\R` 多行匹配，并有 `--bool` 布尔查询（AND/OR/NOT）。可用多行正则近似「先 A 后 B」，但**「中间无 try」只能靠负向匹配硬拼，且不区分注释/字符串/不同类里的同名方法**。另有 `--files --bool` 可做**整文件级**布尔匹配（非逐行），对大文件更宽松但仍无语义 | 【官方推荐】https://github.com/Genivia/ugrep |
| **ast-grep（C1）** | **能** | 规则锚定 `A()` 调用节点 + 关系规则 `precedes: { pattern: 'B($$$)', stopBy: end }`，再叠加 `not: { has: { kind: try_statement, stopBy: end } }`（或把 `stopBy` 设为 `try_statement` 作为搜索边界）。**顺序、跨行、否定都能表达**；代价是要懂一点 node kind，且需为该语言写 YAML | 【官方推荐】规则页 |
| **Semgrep CE（C3）** | **能（限定在单函数内）** | `pattern: A(...)` + `pattern-not-inside: { try ... }` + 顺序约束的 `patterns` 组合可近似表达；`...` 天然跨行跨语句。**但 CE 作用域是单文件/单函数，跨函数/跨文件不行**（商业版才有 interfile） | 【官方推荐】 |
| **tree-sitter query（C4）** | **部分** | query 能同时捕获 `A` 与 `B` 的调用节点（跨行没问题），**但"中间没有 try"和"先后顺序"需要你在 Python 里对命中结果做遍历/过滤**，query 语言自身不提供序列否定 | 【实践观点】（基于官方 query 文档边界，未实测） |
| **comby（C2）** | **部分** | 模板 `:[pre] A(...) :[mid] B(...) :[post]` 能跨行、跨嵌套。**「mid 中不含 try」无法表达**（`:[mid]` 是"任意平衡片段"，没有否定谓词） | 【官方推荐】 |
| **CodeQL（C5）** | **能（最精确）** | QL 可精确表达调用顺序 + 异常路径 + 跨文件数据流。代价：必须建库、非宽松许可 | 【官方推荐】 |
| **ctags / GNU Global（C7/C8）** | **否** | 只有符号的**定义/引用**位置，不表达调用顺序与语句序列 | 【官方推荐】 |
| **向量语义检索（§4）** | **否** | 语义相似度只回答"这段像不像鉴权"，**无法表达"先 A 后 B 且中间无 try"这种结构化/否定约束**。这是语义检索最常被高估的地方 | 【反例】 |

**对比小结**：
- 纯行级/多行正则（Grep、ugrep）在 Q 上只能做**启发式近似**，会产生注释、字符串、同名函数等噪声 → 缺口 A 靠正则**原理上补不上**。
- **ast-grep 是唯一「许可证宽松 + Windows 原生 + 离线 + 无需建库 + 能表达顺序与否定」的组合**；Semgrep CE 次之但作用域受限；CodeQL 最强但许可不合规。
- 语义检索与结构化检索**正交**，不能互相替代。

---

## 3. 符号级检索（与文本检索的区别与互补）

**核心区别**：文本检索回答「哪一行出现了这个字符串」；符号索引回答「这个**符号**在哪定义、在哪些地方被引用」。前者会被注释/字符串/同名符号/局部变量污染，后者靠「定义 vs 引用」的角色区分来消歧，是**跨行、跨文件导航**的基础，但**不理解调用顺序、不表达语句模式**——所以它补的是「精确定位」，不是缺口 A 也不是缺口 B。

### 3.1 【C6】universal-ctags

- **URL**：https://ctags.io/ ｜https://github.com/universal-ctags/ctags
- **类别**：符号索引生成器（生成 `tags` 文件/交叉引用），**只生成索引，检索要靠编辑器或自己写脚本**
- **支持语言**：几十种语言的解析器（官方以 Exuberant Ctags 后继身份持续增加 parser；C/C++/Python/Java/Go/Rust/Ruby/PHP 等，Windows 侧打包说明见下）【官方推荐】
- **能否跨行/语义匹配**：**否**（只做符号定义/角色抽取）；**解决"谁引用了这个函数"这类跨文件问题靠角色标记，不支持调用顺序或语句模式**
- **Windows 支持**：**支持**（官方提供 Windows 二进制；MSYS2 / Cygwin 亦有包，Cygwin 打包说明见 https://sourceware.org/pipermail/cygwin-apps/2024-June/043789.html ）【官方推荐】
- **许可证**：**GPL-2.0-or-later**【官方推荐】（Cygwin 打包页明确标注）
- **是否离线**：**是**
- **是否需建库后查询**：需先跑一次 `ctags -R` 生成索引（秒级/分钟级，取决于仓库）
- **证据等级**：【官方推荐】

### 3.2 【C7】GNU Global（`gtags` / `global`）

- **URL**：https://www.gnu.org/software/global/ ｜手册 https://www.gnu.org/software/global/manual/global.html
- **类别**：源码 tagging 系统（**比 ctags 多一层：同时索引"定义"和"引用"**，可回答"谁调用了这个函数"）
- **支持语言**：内置解析器 **5 种**（C、Yacc、Java、PHP4、汇编）；通过 **Universal Ctags 插件解析器**扩展到 **25 种**（官方列出 Awk、C++、C#、Erlang、Fortran、JavaScript、Lisp、Lua、Pascal、Perl、Python、Ruby、Verilog、VHDL、Vim 等）【官方推荐】
- **能否跨行/语义匹配**：**否**（符号定义/引用；**不做 AST 解析**——VS Code 扩展文档明确写 "GNU global doesn't do any AST parsing"）【实践观点】
- **Windows 支持**：**非原生**。MSYS2 有 `global` 包（提供 `gtags.exe`/`global.exe`，见 https://packages.msys2.org/package/global ），但社区与扩展文档**普遍推荐 WSL**；VS Code 扩展明确表示 `objDirPrefix` 这类选项 "Only support UNIX style filesystem so Windows is unsupported"【官方推荐 + 实践观点】
- **许可证**：**GPL-3.0**【官方推荐】（MSYS2 包页标注 GPL3）
- **是否离线**：**是**
- **是否需建库后查询**：**是**，须先在源码根目录跑 `gtags`，生成 `GTAGS`/`GRTAGS`/`GPATH` 三个文件【官方推荐】
- **证据等级**：【官方推荐】

### 3.3 【C8】LSP 的 `workspace/symbol`

- **URL**：https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- **类别**：编辑器协议里的「工作区符号搜索」请求（能力驱动，需配套语言服务器）
- **支持语言**：取决于装了哪个 language server（每语言一个 server）
- **输入输出形态**：客户端发 `workspace/symbol`，**返回类型为 `SymbolInformation[]` 或 `WorkspaceSymbol[]`**（官方原句），并支持 partial result 流式返回【官方推荐】。字段定义（name/kind/location/containerName）在规范 Workspace Features 小节，本次抓取被截断，**标注未完整核验**
- **能否跨行/语义匹配**：**能按名字搜符号，且若有良好的类型系统 server，可做到"类型感知的引用"**（比文本精确）；**但不能表达语句序列/否定约束**；官方文档未在本次访问范围内说明其匹配算法（模糊/精确），**未验证**
- **Windows 支持**：**支持**（协议与 OS 无关，只要 server 能跑）
- **许可证**：协议规范本身（微软，MIT；本次未核验 LICENSE 页，**未验证**）
- **是否离线**：**是**（本地 server）
- **是否需建库后查询**：通常需要 server 自己建索引（有的在内存里，有的落盘）
- **实践价值**：【实践观点】博客 https://magicliang.github.io/2026/04/17/... 指出 LSP 的 Find References 相比 grep 的关键优势是「只返回真正引用该方法的点，且能区分不同类中的同名方法」——这正是符号检索相对文本检索的互补点
- **证据等级**：【官方推荐】（返回类型）+【实践观点】（互补性论述）

### 3.4 【C9】aider 的 repo map（可复用）

- **URL**：https://aider.chat/ ｜机制说明 https://deepwiki.com/Aider-AI/aider/4.1-repository-mapping-system
- **做法（关键，这决定了能否单独复用）**：tree-sitter 解析 → 用各语言的 `tags.scm`（`name.definition.*` / `name.reference.*`）抽符号 → 建**文件级依赖图** → **PageRank** 按"被引用程度"排序 → **按 token 预算二分裁剪**输出「仓库地图」（默认 ~1024 tokens 量级，来自第三方整理 https://agentpatterns.ai/context-engineering/repository-map-pattern ）【实践观点】
- **能否跨行/语义匹配**：**不是查询工具**，而是"给 LLM 的上下文摘要"；不做模式匹配、不做语义相似度
- **能否单独复用**：**能**。① 直接调 aider 的 `RepoMap` 模块；② 用独立包 `@aiderdesk/tree-sitter-utils`（npm，**MIT**，提供 `extractSymbols()` / `getRepoMap()`，内含 PageRank + SQLite 缓存，18+ 语言）https://www.npmjs.com/package/@aiderdesk/tree-sitter-utils 。**注意该独立包首次遇到新语言会从 unpkg 下载 WASM 语法并缓存**（其 README 自述）→ 严格离网环境需预置缓存【官方推荐（包页）】
- **Windows 支持**：**支持**（Node.js 包 / Python 包均为跨平台）
- **许可证**：aider 主仓许可证本次**未核验**（标未验证）；`@aiderdesk/tree-sitter-utils` **MIT**（npm 页已核验）
- **是否离线**：**基本可离线**（需预置 WASM 语法，见上）
- **是否需建库后查询**：有缓存（`diskcache` / SQLite），非必须
- **证据等级**：【实践观点】+【官方推荐（npm 包页）】

### 3.5 【C10】zoekt（符号加权的三元组索引，**列为文本检索的增强项**）

- **URL**：https://github.com/sourcegraph/zoekt
- **类别**：**trigram 索引的代码文本搜索引擎**（Sourcegraph 后端），支持布尔查询 `and/or/not`
- **支持语言**：语言无关（通用文本索引 + 语法解析辅助）
- **能否跨行/语义匹配**：**以子串/正则匹配为主**（官方自述 "fast substring and regexp matching"），**不是 AST 语义匹配**；官方建议装 **Universal ctags** 以把"命中符号"作为**排序信号**（symbol-aware ranking）→ 这是「文本检索 + 符号加权」的混合形态，比纯 grep 更懂"哪条命中更重要"【官方推荐】
- **Windows 支持**：Go 实现，理论可跨平台构建；**官方是否提供 Windows 预编译二进制未验证**
- **许可证**：**Apache-2.0**【官方推荐】（deps.dev / 项目页）
- **是否离线**：**是**
- **是否需建库后查询**：**是**，须先 `zoekt-index` / `zoekt-git-index` 建索引
- **证据等级**：【官方推荐】

---

## 4. 语义 / 向量代码检索（缺口 B）

**定位**：只解决「字面不同但语义相近」。**对缺口 A（跨行结构/否定约束）完全无能**。本地可行性 = 模型能否离线加载 + 向量库是否嵌入式。模型体积只做**定性分级**（小 / 中 / 大），不写具体 MB 数（避免造数字；个别官方标称值附 URL 供主代理核验）。

### 4.1 代码 embedding 模型（只列存在的，不评优劣）

| 编号 | 名称 | URL | 许可证 | 体积（定性） | 代码特化 | 离线 | 证据 |
|---|---|---|---|---|---|---|---|
| **C11** | nomic-embed-code | https://ollama.com （社区模型标签 `manutic/nomic-embed-code`；一手页未在本次访问核验，**标未验证**） | Apache-2.0（第三方评测 https://www.baseten.com/blog/the-best-open-source-embedding-models/ 称 Apache-2.0） | **大**（第三方评测称 7B 量级） | **是** | 是 | 【实践观点】 |
| **C12** | jina-embeddings-v2-base-code | https://huggingface.co/jinaai/jina-embeddings-v2-base-code ｜https://jina.ai/models/jina-embeddings-v2-base-code | **Apache-2.0**【官方推荐，模型卡已核验】 | **小**（官方称 137M 参数 / 307MB 量级） | **是**（30+ 编程语言、8K 上下文、可跨语言匹配） | 是（有 GGUF 量化版） | 【官方推荐】 |
| **C13** | Qwen3-Embedding（0.6B/4B/8B） | https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF | **Apache-2.0**【官方推荐，模型卡已核验】 | 小→中→大（官方列 0.6B/4B/8B） | 否，但官方称含 code retrieval 能力 | 是（GGUF + llama.cpp） | 【官方推荐】 |
| **C14** | CodeBERT / GraphCodeBERT | https://github.com/microsoft/CodeBERT | 上游仓 **MIT**（本次未核验 LICENSE 页，**未验证**） | **小**（官方论文为 base 规模） | **是**（GraphCodeBERT 引入数据流图） | 是 | 【实践观点】（**注意**：这是 2020 年前后模型，是否仍具竞争力本次未验证，不写任何分数） |

### 4.2 向量库（全部具备嵌入式/本地模式）

| 编号 | 名称 | URL | 许可证 | 定位 | 备注 | 证据 |
|---|---|---|---|---|---|---|
| **C15** | sqlite-vec | https://github.com/asg017/sqlite-vec | **MIT OR Apache-2.0** | SQLite 扩展 | 最轻；纯 C 零依赖；与 SQL 同库 | 【实践观点】https://d-central.tech/self-hosted-vector-databases |
| **C16** | LanceDB (OSS) | https://github.com/lancedb/lancedb | **Apache-2.0** | 嵌入式列式向量库 | **原生 BM25+向量混合检索**与 reranker；无需起服务 | 同上 |
| **C17** | FAISS | https://github.com/facebookresearch/faiss | **MIT**（第三方页标 Apache/MIT 表述不一，**未验证**） | 纯算法库 | **无持久化/无 CRUD/无 metadata 过滤**，需自己造轮子 | 【实践观点】 |
| **C18** | Chroma | https://github.com/chroma-core/chroma | **Apache-2.0** | 嵌入式向量库 | `pip install` 即用；自带默认 embedding 函数；**大量数据时性能受限**（第三方实测口径，不作证据） | 【实践观点】 |
| **C19** | Qdrant | https://qdrant.tech/ | **Apache-2.0** | 独立服务 | Rust 实现；本地需 Docker 起服务（**不算"无服务"**） | 【实践观点】 |

> 说明：以上许可证以第三方横评页 https://d-central.tech/self-hosted-vector-databases 与 https://zairalabs.ai/guide/guides/vector-database-compared 的一手抓取内容为准；FAISS/Chroma 的精确许可证请主代理以官方 LICENSE 二次核验。

### 4.3 现成的、开箱可用的本地代码语义检索项目（**给可跑的项目，不是论文**）

#### 【C20】ChunkHound
- **URL**：https://reporank.net/en/repo/chunkhound-chunkhound.html （项目聚合页，含 README 摘要）
- **类别**：本地优先的代码库语义检索 CLI + **MCP server**
- **做法**：tree-sitter 结构化解析 + 自研「cAST」语义 chunk + DuckDB 本地存储 + MCP（Claude/VS Code/Cursor/Windsurf/Zed）
- **支持语言**：自述 32 种（含配置/文本文件）
- **能否语义匹配**：**能**（同时保留 regex 模式）；**不做跨行结构化否定匹配**
- **Windows 支持**：Python 实现，**理论支持，未在本次访问中核验 Windows 专项说明**
- **许可证**：**MIT**【实践观点，聚合页标注】
- **离线**：支持本地 Ollama embedding（也可接 VoyageAI/OpenAI → **非严格离线**）
- **证据等级**：【实践观点】

#### 【C21】semgrepll
- **URL**：https://github.com/rizperdana/semgrepll
- **类别**：**100% 离线**语义 grep CLI（`semgrep index/search/ls`）+ 配套 agent skill
- **做法**：多后端自动探测 `llama.cpp → ONNX → Ollama`；SQLite（小项目）/ LanceDB（大库）混合存储；embedding 缓存
- **支持语言**：随 embedding 模型（不限语言）
- **能否语义匹配**：**能**；无结构化匹配能力
- **Windows 支持**：pip 安装的 Python 包，**未在本次访问中核验 Windows 专项说明**
- **许可证**：**MIT**（README 明示）
- **离线**：**是**（README 明确 "100% offline"）
- **证据等级**：【官方推荐（项目 README）】

#### 【C22】codebase-semantic-search（MCP）
- **URL**：https://lobehub.com/mcp/xveyn-codebase-semantic-search ｜上游 https://github.com/Xveyn/codebase-semantic-search
- **类别**：Claude Code 的语义检索 **MCP server**
- **做法**：LanceDB + Ollama / transformers.js；AST(tree-sitter)/行混合 chunk；**索引存在 `~/.vectordb/` 不污染仓库**；增量更新
- **输入输出形态**：MCP 工具 `search_code` / `search_files` / `search_symbols` / `index_status` / `index_update` / `reindex`（返回带元数据的匹配片段）
- **Windows 支持**：Node.js，**未核验**
- **许可证**：**MIT**【实践观点，LobeHub 页标注】
- **离线**：**是**（Ollama 或内置 transformers.js）
- **证据等级**：【实践观点】

#### 【C23】codebase-rag（MCP）
- **URL**：https://lobehub.com/fr/mcp/joinquantish-codebase-rag ｜上游 https://github.com/joinQuantish/codebase-rag
- **类别**：本地代码 RAG（SQLite FTS5 + 向量 + RRF 混合）MCP server
- **做法**：克隆仓库 → 按函数/类边界切块 → 本地 all-MiniLM 系 ONNX embedding → SQLite 存储；三种检索模式（keyword / semantic / hybrid）
- **输入输出形态**：MCP 工具 `search` / `semantic_search` / `query`（混合）/ `stats`
- **Windows 支持**：Node/Bun 运行时，**未核验**
- **许可证**：**未验证**（LobeHub 页未给出）
- **离线**：**是**（README 明确 "No API keys needed. Runs 100% locally on CPU."）
- **证据等级**：【实践观点】

#### 【C24】mcp-intelligence-context（**无 embedding 的对照方案**）
- **URL**：https://himcp.ai/server/mcp-intelligence-context ｜上游 https://github.com/LeoChimal09/MCP-INTELLIGENCE-CONTEXT
- **类别**：**符号/依赖索引 + token 预算上下文包** MCP server（**MVP 不做 embedding**，纯词法/符号检索）
- **做法**：Python `ast` + JS/TS 正则抽符号与 import，建反向依赖图，缓存 `.mcp_intel_cache/index.json`，后台 watcher 增量更新
- **输入输出形态**：`search_code` / `get_relevant_context`（返回**符号表 + 小代码片段**，并自报 token 节省比例）/ `get_file_summary` / `get_dependencies`
- **意义**：**证明了"不做向量、只做符号+依赖图"也能显著减少 agent 的盲目扫描**——是评估"语义检索是否值得上"的重要对照组
- **离线**：是；**许可证**：未验证；**证据等级**：【实践观点】

#### 【C25】claude-context（**反面例子，见 §6**）
- **URL**：https://dudarik.com/en/blog/claude-context-mcp ｜包 `@zilliz/claude-context-mcp`
- **类别**：语义代码检索 MCP（Milvus/Zilliz 向量库）
- **离线**：**否**。**必须** `OPENAI_API_KEY` + Milvus 端点（默认 Zilliz Cloud）→ 既不适合离线，也不适合个人本地工作流
- **证据等级**：【实践观点】

---

## 5. Agent 侧代码检索工具（MCP server / 给 LLM 用的上下文选择）

| 编号 | 名称 | URL | 输入输出形态 | 是否结构化 | 是否语义 | 离线 | 证据 |
|---|---|---|---|---|---|---|---|
| **C26** | ast-grep MCP（官方实验版） | https://github.com/ast-grep/ast-grep-mcp | 4 个工具：`dump_syntax_tree` / `test_match_code_rule` / `find_code`（简单 pattern，文本或 JSON 输出，官方称 text 模式省 ~75% token，**属厂商自述不采信**）/ `find_code_by_rule`（复杂 YAML 规则，支持 inside/has/precedes/follows） | **是（真 AST）** | 否 | 是 | 【官方推荐】 |
| **C27** | ast-grep MCP（Rust 版） | https://github.com/GodSpeedAI/ast-grep-mcp-rs | 同上四工具；`--transport stdio/sse`；`--config sgconfig.yaml` | **是** | 否 | 是 | 【实践观点】 |
| **C28** | RepoMapper（aider repo map 的 MCP 封装） | 参见 https://agentpatterns.ai/context-engineering/repository-map-pattern （文中称 "RepoMapper — Aider's repo map logic as an MCP server"） | 输入：预算/关注点；输出：PageRank 排序后的符号骨架 | 符号级 | 否 | 是 | 【实践观点】（**该 MCP 的独立仓库地址本次未核验，标未验证**） |
| **C29** | mcp-intelligence-context | 见 C24 | 见 C24 | 符号级 | 否 | 是 | 【实践观点】 |

**小结（输入输出形态的启示）**：给 LLM 用的检索工具，**输出应是「文件路径 + 行范围 + 符号名 + 截断片段 + 命中理由」**，而不是整文件——C26/C24/C22 的工具设计都体现了这一点；这比"换个更聪明的检索算法"对 token 成本的影响更直接。

---

## 6. 反例：容易踩的坑与被高估的说法

1. **【反例】厂商/论文的百分比一律不可当证据**。本次访问到的页面里就有大量这类表述：Semgrep 官方首页称「AppSec 团队减少 80% 误报」「95% 安全评审员在 600 万条发现中验证」；第三方评测引 aider「SWE-bench Lite 26.3%」。**其中 SWE-bench 数字来自"整个 Aider 技术栈"，该来源自身也承认并未做消融实验来隔离 repo map 的贡献**（第三方整理页 https://agentpatterns.ai/context-engineering/repository-map-pattern 明确点出 "the SWE-bench post credits the repo map but does not isolate its contribution in an ablation"）→ 这类数字不能用来论证"repo map 有效"。
2. **【反例】"本地语义搜索开箱即用"普遍被高估**。① 多数项目**首次运行要联网下载 embedding 模型/WASM**（如 `@aiderdesk/tree-sitter-utils` 首次按语言从 unpkg 拉 WASM；codebase-rag 首次自动下载 ONNX 模型）——严格离网前必须预热缓存；② claude-context 这类"知名"方案**根本不是离线的**（OpenAI key + Milvus 云）；③ 本地量化模型在代码检索上的效果"may vary"（第三方项目页自己写的）。
3. **【反例】"向量检索能替代 grep/AST"是错的**。语义相似度无法表达**否定、顺序、作用域**（见 §2 末行）。把"先 A 后 B 无 try"交给 embedding，是范畴错误。
4. **【反例】"Comby 是通用方案"需打折**：README 的安装章节里 Windows 只有 WSL 一条路，且项目 2022 年后几乎停更。
5. **【反例】CodeQL 常被当作"开源工具"推荐**，但它实际上是**许可受限的免费品**（闭源需商业授权），不满足本项目"许可证宽松"前提。
6. **【注意】Semgrep CE 的结构化检索作用域是单文件/单函数**；跨文件/跨过程要商业版。把它当"grep 的替代"没问题，当"全仓库语义分析器"会失望。
7. **【注意】符号索引（ctags/Global/LSP）不是缺口 A/B 的解**：它只解决"精确定位符号"，不回答"这些调用之间的顺序/条件"。

---

## 7. 给主代理的结论

### 7.1 投入产出比排序（只考虑"给这个工作流加检索工具"）

1. **ast-grep(sg)** —— 直接命中缺口 A 的最痛点，成本最低（单二进制 / pip 安装 / 无需建库 / 离线 / MIT / Windows 原生）。
2. **Semgrep CE** —— 若工作流本来就想顺手要一套 lint+安全规则，它同时提供结构化 pattern 检索；但**作用域被限制在单文件/单函数**，且 `--config auto` 需联网，需改成本地规则。
3. **tree-sitter（自写 Python）** —— 最灵活、MIT、离线，但**序列/否定约束要自己写遍历逻辑**，开发成本高于 ast-grep；适合已有 Python 工程、想深度定制的场景。
4. **universal-ctags + 自写查询**（可选）—— 若痛点是"精准跳转/找引用"而非"跨行模式"，这是极便宜的补充（一个二进制 + 一次 `ctags -R`）。
5. **向量语义检索** —— 排在最后（理由见 7.3）。

### 7.2 若只能加一个结构化检索工具 → **加 ast-grep**

**为什么是它（逐条对应硬约束）**：
- **Windows 原生**：有 `win32-x64-msvc` 的 npm 包、`scoop install main/ast-grep`、`pip install ast-grep-cli` —— 不需要 WSL（comby 需要，GNU Global 推荐 WSL）。
- **许可证宽松**：**MIT**（Semgrep 是 LGPL-2.1，CodeQL 不是开源免费品）。
- **可离线**：无网络依赖、无规则云、无建库步骤（Semgrep 默认拉 registry，CodeQL 必须先建库）。
- **CLI + Python 双通道**：`pip install ast-grep-cli` 后有 `sg`/`ast-grep` 命令；也可 `subprocess` 调 `sg --pattern ... --lang ... --json` 拿结构化结果，极易塞进现有 Python 工作流。
- **真正补上缺口 A**：`$VAR` / `$$$` + 关系规则 `inside`/`has`/`follows`/`precedes` + `stopBy: end` 能表达**跨行、跨语句、顺序、否定**（第 2 节 Q 的对比里，它是唯一"许可合规 + 能表达顺序与否定"的选项）。
- **附带收益**：同一套工具还能做 lint 与大规模安全重写（`--rewrite` + dry-run），一次投入覆盖两个场景。

**必须承认的代价**（主代理要在计划里预置）：
- 写复杂规则**需要懂目标语言的 node kind**，初次使用要用 `dump_syntax_tree` 之类的调试手段试错；
- **pattern 不支持正则**（`|`、`.*`、`\w`、`[a-z]` 都不行）——纯文本查询仍要交回 Grep，两者是并存不是替代；
- 每种语言要单独 `--lang`，多语言仓库需按后缀分派。

**落地建议（最小可行）**：先只加一条能力——`sg -p '<pattern>' -l <lang> --json <path>` 的封装函数（无需 YAML、无需建库），把"跨行模式"变成工作流里可调用的一等公民；等真的遇到需要"顺序/否定"的查询，再引入 YAML 规则文件。**不要一上来就上 tree-sitter 自研或 CodeQL 建库，那是过度投入。**

### 7.3 语义向量检索，在「本地个人工作流 + 大仓库」现在值不值得上？—— **倾向：暂不上；要上就必须按"粗筛"定位上**

**不值得上的理由（正面）**：
- **需求顺序错位**：工作流当前缺的是缺口 A（跨行结构），这是高频、刚需、有确定性答案的；缺口 B（语义近似）是低频、模糊、本来也难验证对错的。先补确定性需求。
- **维护成本是长期的**：要跑 embedding（模型体积从**小**到**大**不等，jina 代码模型官方称 137M/307MB 量级，nomic-embed-code 第三方称 7B 量级）、要处理**增量索引**、要调 **chunk 边界**（定长切块 vs 按函数/类切块，后者要靠 tree-sitter，又回到 AST 成本）、要防"改了代码忘了重建索引"。这些都是持续负担。
- **收益不稳定**：仓库越大、样板代码越多，"语义最近邻"越容易被**重复的样板/生成的代码**带偏；而关键词明确的查询，Grep 往往又快又准。
- **有权威侧的相反经验**：第三方整理指出 Claude Code 早期做过 RAG 实验，但**最终选择不索引、改用 agentic search（Glob/Grep/Read）**（转述自 https://agentpatterns.ai/context-engineering/repository-map-pattern ）【实践观点，非一手 —— 请主代理按需核验原文】。
- **"符号+依赖图"常常就够了**：mcp-intelligence-context 的 MVP **完全不做 embedding**，只靠符号表与反向依赖图 + token 预算，就能把"盲目扫仓库"变成"拿一小包上下文"——这是**性价比极高的中间态**，值得先试（C24）。

**如果一定要上，请按下述方式上（把风险压到最低）**：
1. **定位为"第一跳粗筛"，绝不作为最终结果**：向量只用来把候选文件/符号缩到一小撮，再用 **ast-grep（结构）/ Grep（精确）** 精查。这样即便召回有噪声也不影响最终正确性。
2. **模型选小、选代码特化、选 Apache**：优先 **jina-embeddings-v2-base-code**（Apache-2.0、代码特化、体积小、有 GGUF）。**不要**一上来用 7B 级嵌入模型（体积与内存代价大，收益未验证）。
3. **向量库选嵌入式，选 Apache/MIT**：`sqlite-vec`（MIT/Apache）或 `LanceDB OSS`（Apache，且原生 BM25+向量**混合**检索）。**避免需要 Docker 起服务的 Qdrant/Milvus**（把"离线"变成"要维护一个服务"）。
4. **一定要做混合检索，不要纯向量**：BM25/关键词 + 向量 + RRF 融合（多个现成项目都走这条路）。纯向量在代码这种**强标识符语言**上会丢掉精确匹配优势。
5. **chunk 按符号边界切，不要定长切**：用 tree-sitter 按函数/类/方法边界切块（C20/C22/C24 都这么做），并**把 `path + 行范围 + 符号名` 一并作为返回元数据**——这才是 agent 真正能用的输出。
6. **先做一次性验证再决定是否常驻**：挑 3–5 个"我知道答案在哪、但 grep 搜不出来"的目标查询，手工对比"向量召回 / Grep 召回 / 符号召回"三者结果，**用你自己的语料判优劣**，不要采信任何第三方准确率数字。

**一句话**：语义向量检索对**缺口 B** 是有效补充，但对**缺口 A** 无用；在当前阶段，**先用 ast-grep + （可选）符号索引把确定性能力补齐**，把向量检索作为一个"待验证的可选层"，而不是现在就为它背上长期索引维护成本。

---

## 附：本次调研访问过的页面清单（去重，供主代理复核）

**AST / 结构化**
- https://github.com/ast-grep/ast-grep ； https://ast-grep.github.io/guide/rule-config.html ； https://pypi.org/project/ast-grep-cli/ ； https://libraries.io/npm/@ast-grep%2Fcli-win32-x64-msvc/0.39.2
- https://github.com/comby-tools/comby ； https://comby.dev/docs/overview ； https://awesome.ecosyste.ms/projects/github.com%2Fcomby-tools%2Fcomby
- https://semgrep.dev/ ； https://semgrep.dev/products/community-edition ； https://docs.semgrep.dev/getting-started/cli/ ； https://semgrep.dev/resources/whats-new ； https://pypi.org/project/semgrep/0.18.0/
- https://tree-sitter.github.io/tree-sitter/using-parsers/queries/4-api.html ； https://tree-sitter.github.io/tree-sitter/4-code-navigation.html ； https://openapps.pro/packages/py-tree-sitter
- https://codeql.github.com/ ； https://codeql.github.com/docs/codeql-cli/about-the-codeql-cli ； https://github.com/github/codeql
- https://github.com/Genivia/ugrep

**符号 / 索引**
- https://www.gnu.org/software/global/ ； https://www.gnu.org/software/global/manual/global.html ； https://packages.msys2.org/package/global ； https://github.com/Kztpia/vscode-gnu-global
- https://sourceware.org/pipermail/cygwin-apps/2024-June/043789.html
- https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- https://deepwiki.com/Aider-AI/aider/4.1-repository-mapping-system ； https://www.npmjs.com/package/@aiderdesk/tree-sitter-utils ； https://agentpatterns.ai/context-engineering/repository-map-pattern
- https://github.com/sourcegraph/zoekt ； https://deps.dev/go/github.com%2Fsourcegraph%2Fzoekt

**语义 / 向量 / 项目**
- https://huggingface.co/jinaai/jina-embeddings-v2-base-code ； https://jina.ai/models/jina-embeddings-v2-base-code
- https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF ； https://www.baseten.com/blog/the-best-open-source-embedding-models/
- https://d-central.tech/self-hosted-vector-databases ； https://zairalabs.ai/guide/guides/vector-database-compared ； https://qdrant.tech/
- https://github.com/rizperdana/semgrepll ； https://reporank.net/en/repo/chunkhound-chunkhound.html
- https://lobehub.com/mcp/xveyn-codebase-semantic-search ； https://lobehub.com/fr/mcp/joinquantish-codebase-rag ； https://dudarik.com/en/blog/claude-context-mcp

**Agent / MCP**
- https://github.com/ast-grep/ast-grep-mcp ； https://lobehub.com/mcp/godspeedai-ast-grep-mcp-rs ； https://github.com/code-yeongyu/pi-ast-grep
- https://himcp.ai/server/mcp-intelligence-context
