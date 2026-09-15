# 体验官 B：端到端可执行性实测

- 被评估对象：`ai-workflow` v2.5.0（SKILL.md 161 行 + references/assets/scripts）
- 沙箱：`tasks/体验评估-ai-workflow-v2.5.0-2026-09-10/toy/`
- 解释器：`C:\Users\26717\.workbuddy\binaries\python\envs\ai-workflow\Scripts\python.exe`
- 立场：有罪推定。凡我跑通的都贴原始输出；凡我跑挂的照实记录。

## 1. 一眼印象

主干六阶段与门禁设计是可信的，`checks.py plan` 的负向拦截和 `office_io` 的读回闭环我都真跑通了（含篡改测试）。
但**文档给的"第二套运行方式"（`run_stage.ps1` 包装器）在本机是静默 no-op，却打印状态 OK 并返回退出码 0** —— 这是本次最危险的一条。
此外"独立审核"环节的**粒度不可操作**：判定清单有、批次/合并规则没有，按字面执行会让 N 个交付物变成 N 次子代理送审。

## 2. 实测记录（命令 / 结果 / 是否与文档一致）

> 约定：`PY` = venv 解释器，`SK` = `C:/Users/26717/.workbuddy/skills/ai-workflow`，`TOY` = `<SK>/tasks/体验评估-ai-workflow-v2.5.0-2026-09-10/toy`。全部命令为真实执行、原样粘贴。

### 步骤 1｜照抄 ops.md §一 命令跑环境/自检（对照 ops.md:10-14）

```bash
SK="C:/Users/26717/.workbuddy/skills/ai-workflow"
PY="C:/Users/26717/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"
"$PY" "$SK/scripts/checks.py" skill
```
结果：可照抄即跑，`=== 结果：18/18 通过，FAIL=0 ===`，EXIT=0。**与文档一致**（changelog ops.md:137 也写 18/18）。

### 步骤 2｜venv 依赖探测

```bash
"$PY" -c "import requests,openpyxl,docx,pypdf,yaml,duckdb;print('all imports OK')"
```
→ `all imports OK`；`openpyxl 3.1.5`、`duckdb 1.5.5`。
裸解释器对照：`C:/.../versions/3.13.12/python.exe -c "import yaml"` → `ModuleNotFoundError: No module named 'yaml'`（确认"用错必炸"的前提成立）。
`<venv>/Scripts/` 下确有 `ast-grep.exe` 与 `sg.exe`。
**摩擦**：SKILL.md:22 写「检测与排障命令见 `references/ops.md`」，但 ops.md §四只给了 `setup_env.ps1`，**没有一条可直接照抄的 import 探测命令**；上面这行是我自己写的。

### 步骤 3｜`checks.py` 四个子命令 `--help` 对账（对照 ops.md:22、SKILL.md:160）

| 子命令 | help 实际输出 | 与文档 |
| --- | --- | --- |
| `skill` | `[--skill-dir]` | 一致（ops.md 未提该参数，但非冲突） |
| `plan` | `target`（"plan.yaml 路径或任务目录"）+ `--base` | 一致 |
| `status` | `--workspace/--archive-days/--max-tasks` | 一致 |
| `mark` | `plan step_id {待办,进行中,完成,受阻}` | 一致 |

**不一致项**：`checks.py` docstring 第 24 行写 `meta 必填（任务 / 验证信号）`，而代码 `checks.py:55` 是 `PLAN_META_REQUIRED = ("任务","验证信号","工作区根")` —— 三字段，docstring 没跟上 v2.4.4 的变更。

### 步骤 4｜`status` 两种调用

```bash
"$PY" "$SK/scripts/checks.py" status                      # cwd = e:/ChatGPT/工作流
"$PY" "$SK/scripts/checks.py" status --workspace "$SK"
```
两者都对：前者列出 `e:/ChatGPT/工作流/tasks/` 的 7 个任务，后者列出技能目录 `tasks/` 的 7 个（含本任务 `1/6 步骤、1/8 交付物`）。
边界：在无 `tasks/` 的目录里跑 → `[FAIL] tasks/ 目录存在 — <cwd>/tasks`，**没有任何"请加 --workspace"的提示**（checks.py:229-230）。

### 步骤 5｜造 CSV + 生成 xlsx + 读回（验证闭环）

造 `toy/sales.csv`（表头 + 5 行销售数据）。

负向：照 SKILL.md:122「支持 CSV 读入」的字面理解直接喂 CSV 给 excel-write：
```bash
"$PY" office_io.py excel-write "$TOY/sales_naive.xlsx" --rows "$TOY/sales.csv"
```
→ 裸异常：`json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`，EXIT=1，`sales_naive.xlsx` 未生成。

正向（两步）：
```bash
"$PY" office_io.py excel-read "$TOY/sales.csv" --fmt json > "$TOY/rows.json"
"$PY" office_io.py excel-write "$TOY/sales.xlsx" --rows "$TOY/rows.json"
"$PY" office_io.py excel-read "$TOY/sales.xlsx" --fmt json
```
→ `[ OK ] 已写入 ...（6 行 x 5 列，格式化=开）`；读回 JSON 与源逐一比对：`CSV 行数: 6  xlsx 读回行数: 6  逐字段一致: True`。**验证闭环成立，与文档一致。**

### 步骤 6｜手写 plan.yaml 对账（正向 + 负向）

按 `assets/plan-template.yaml` 的中文键手写 `toy/plan.yaml`（2 步，交付物写完整相对路径）。

正向：`checks.py plan "$TOY/plan.yaml" --base "$SK"` → `7/7 通过，FAIL=0`，EXIT=0。
负向 5 组，全部按预期 FAIL：

| 变体 | 篡改内容 | 原始输出 | 退出码 |
| --- | --- | --- | --- |
| n1 | 抽掉 `meta.工作区根` | `[FAIL] meta.工作区根 — 为空` → `6/7` | 1 |
| n2 | 交付物指向不存在文件 | `[FAIL] 步骤 1 交付物缺失 — .../不存在的文件.csv` | 1 |
| n3 | 值里写未加引号的 ASCII 冒号 | `[FAIL] plan.yaml 可解析 — mapping values are not allowed here` | 1 |
| n4 | 抽掉 step 的 `交付物` 键 | `[FAIL] 步骤 1 必填字段 — 缺 交付物` | 1 |
| n5 | 交付物缩写为 `sales.xlsx` | `[FAIL] 步骤 2 交付物缺失 — sales.xlsx（交付物须写完整路径，缩写如『选品分析.yaml』无法定位）` | 1 |

→ **ops.md:68（ASCII 冒号）、:69（缩写路径无法定位）两条排障描述 100% 复现。**

`mark` 正反向：`mark plan.yaml 2 进行中` → `[ OK ] ... 完成 → 状态: 进行中`；改回 `完成` 后 `plan` 复验 7/7；非法状态 `已完成` → argparse 拒绝 EXIT=2；不存在的 id=99 → `[FAIL] 找到该步骤的『状态』行 — id=99` EXIT=1。

### 步骤 7｜路径基准鲁棒性

```bash
(cd /tmp && "$PY" checks.py plan "$TOY/plan.yaml")   # 不带 --base
```
→ 仍 `7/7 通过`。注意：此时 base=/tmp，候选基准 `base/p`、`Path.home()/.workbuddy/p`、`base.parent/p` **都不可能命中**，唯一能命中的是 `checks.py:164-165` 的"逐个技能目录再试一遍"兜底 —— 也就是说**别的技能目录里的同名相对路径会把缺失交付物"救活"**（假 PASS 风险，且与红线③的边界语义不符）。

### 步骤 8｜`http_fetch` dry-run / check-links（对照 ops.md:25、:89、:99-122）

```bash
"$PY" http_fetch.py --github-search "code search language:rust stars:>500" --search-limit 20 --dry-run
"$PY" http_fetch.py --github-code-search "read_parquet repo:duckdb/duckdb" --dry-run
```
→ 分别打印完整 URL + `附加头：无（/search/repositories 匿名可用）` / `Accept: application/vnd.github.text-match+json`，且首行 `[INFO] 未设环境变量，改用 gh CLI 凭据（gh auth token）提高限额` —— **gh 凭据自动读取这条文档承诺实测成立**。
非搜索命令加 `--dry-run` → `[WARN] --dry-run 只对 --github-search / --github-code-search 生效，本次忽略`（ops.md:90 一致）。

`--check-links toy/urls.txt`（含 1 条 200、1 条 200、1 条 huggingface、1 条伪造日期型 URL）：
```
200  可达        example.com
200  可达        www.python.org
ERR  网络失败: <urlopen error Tunnel connection failed: 502 Bad Gateway>  huggingface.co
404  不存在      www.python.org/2026/04/17/fake-article-for-404-test
```
→ **ops.md:72（huggingface 稳定 502 本机出口）与 :118（日期型 URL 最可疑）双双复现。**
**但**：本次 `[STATS] 平均 2573 ms/条`，与文档写的 `平均 227ms/条`（ops.md:107）/`156ms/条`（:180）差一个数量级——慢因是那条 502 超时占 10.2s。文档把单次实测均值写成定值（撞上自己 quality-gates.md:91 反模式#21）。另外 404 时进程仍 EXIT=0，**无法用退出码做自动化门禁**。

### 步骤 9｜`data_query` files/sql/find

```bash
"$PY" data_query.py files "$TOY"         # 9 文件 / 10.62 KB / 按扩展名分布 / 大文件榜
"$PY" data_query.py sql "SELECT 商品, CAST(销售额 AS INTEGER) AS 销售额 FROM read_csv_auto('.../sales.csv') ORDER BY 销售额 DESC"
"$PY" data_query.py find "$TOY" --pattern "显示器"
```
→ 三个子命令全部按文档工作；`sql` 对中文列名 CSV 零导入直查成功（显示器 1798 > 耳机 996 > 鼠标 400 > 键盘 360 > 摄像头 359）；`find` 命中 2 条带行号。**与文档一致。**

### 步骤 10｜用错解释器（对照 ops.md:67）

```bash
"$BARE" checks.py plan "$TOY/plan.yaml"   # BARE = versions/3.13.12/python.exe
```
→ `[ERROR] 缺少 pyyaml...` + `[HINT ] ...请直接用 venv 解释器...`，**EXIT=2**。文档承诺（"以退出码 2 中止"）成立。
但同样用裸解释器跑 `office_io.py` → 裸 `ModuleNotFoundError: No module named 'openpyxl'` + traceback，**没有 [ERROR]/[HINT] 守卫**。

### 步骤 11｜`run_stage.ps1`（本次最严重发现）

按 ops.md:16/28 用包装器跑（三次独立试验）：

```powershell
& "$SK\scripts\run_stage.ps1" checks.py skill
& "$SK\scripts\run_stage.ps1" office_io.py excel-write "$TOY\sales_via_runstage.xlsx" --rows "$TOY\rows.json"
& "$SK\scripts\run_stage.ps1" checks.py mark "$TOY\plan.yaml" 1 进行中
```
三次都只打印状态检查三行：
```
=== AI Workflow status check ===
[ OK ] venv: ...\Scripts\python.exe
[ OK ] script: ...\scripts\office_io.py
[ -- ] AI_API_KEY (only needed for AI calls)
```
而事实是：
- `checks.py skill` 的 18 行结果 **完全没有出现**；
- `sales_via_runstage.xlsx` **未生成**；
- `plan.yaml` 的 `状态:` 行**保持 `完成` 未变**（即 `mark` 根本没跑）；
- 包装调用方读到的 `WRAPPER_LASTEXITCODE=0`。

定位到根因：**本机沙箱下 PowerShell 工具根本不执行原生子进程**。隔离验证：
```powershell
& $py -c "open(r'$toy\native_probe.txt','w',encoding='utf-8').write('native child ran')"
```
→ `native_probe.txt` 未生成（`No such file or directory`）。
→ 即 ops.md:77 说的"`$LASTEXITCODE` 可能为空、stdout 可能丢失"**描述偏轻**：真实情况是子进程不执行且被报成成功。

### 步骤 12｜`setup_env.ps1`（假 OK）

实跑 `& "$SK\scripts\setup_env.ps1"`（输出落盘后解码），结尾：
```
[ OK ] requests
[ OK ] openpyxl
[ OK ] python-docx
[ OK ] pypdf
[ OK ] pyyaml
[ OK ] duckdb
[ OK ] ast-grep-cli
```
但 `setup_env.ps1:8` 的 `$deps` 有 7 项，`:41` 的 `$pkgDir` 只映射了 5 项（无 `duckdb`/`ast-grep-cli`）。复刻该检查逻辑做对照实验：
```
dep=requests                          dirName=[requests] joined=[...\site-packages\requests]  TestPath=True -> prints [ OK ] requests
dep=definitely-not-a-real-package-xyz dirName=[]         joined=[...\site-packages\]          TestPath=True -> prints [ OK ] definitely-not-a-real-package-xyz
dep=duckdb                            dirName=[]         joined=[...\site-packages\]          TestPath=True -> prints [ OK ] duckdb
```
→ **任何不在映射表里的依赖都会被判 OK**（`Join-Path $sitePkgs $null` 静默退化成 site-packages 自身，目录恒存在）。`duckdb`/`ast-grep-cli` 的"OK"是假的。这正好是本 skill 自己的反模式 #19（quality-gates.md:89）。

### 步骤 13｜命令被安全策略拦截（复现已知怪癖）

```bash
echo "probe-powershell-token" | cat
```
→ `Command rejected: ... Reason: Command blocked for security: Invoking PowerShell from Bash bypasses PowerShell security checks; use the PowerShell tool instead`
→ 意味着 ops.md:22/:51 推荐的 `powershell -File scripts\setup_env.ps1` **无法从 Bash 工具发出**；而 PowerShell 工具在本机不回显 stdout（我所有 PowerShell 调用都只回 `Command completed with exit code 0`）。ops.md:76 教的"改写措辞/落盘脚本"没指向"改用 PowerShell 工具"。

## 3. 问题清单

| # | 级别 | 问题 | 证据（文件:行 或 命令+原始输出） | 是否有绕法 | 建议 |
| --- | --- | --- | --- | --- | --- |
| 1 | **阻断** | 文档推荐的第二套运行方式 `run_stage.ps1` 在本机**静默 no-op**，且打印状态 OK、调用方退出码 0 —— 照文档做会"以为跑了其实没跑" | ops.md:16/:28（"`run_stage.ps1 <脚本名> [参数...]`（自带状态检查）"）+ run_stage.ps1:24-25 + 实测三次：`sales_via_runstage.xlsx` 未生成、`plan.yaml` 状态未变、`WRAPPER_LASTEXITCODE=0`；根因隔离验证 `native_probe.txt` 未生成 | 有：直接用 venv 解释器 + 绝对路径（ops.md:10-14 主例，实测可用） | 在 ops.md:77 把现象改写为"本机沙箱下 .ps1 内**原生子进程可能根本不执行**且退出码为 0"，并在 §一 明确"**首选**直接调 venv 解释器，run_stage.ps1 仅作交互式终端备选" |
| 2 | 绕路 | `setup_env.ps1` 依赖自检对未映射的包给**假 OK**（duckdb / ast-grep-cli 从未被校验） | setup_env.ps1:8（7 个 deps）vs :41（pkgDir 仅 5 项）+ :45；对照实验 `definitely-not-a-real-package-xyz ... prints [ OK ]` | 有：改用 `import` 实测（我步骤 2 就是这么做的） | `$pkgDir` 加 `"duckdb"="duckdb"`、`"ast-grep-cli"="ast_grep_cli"`；或在 step 4 后追加一次 `& $venvPython -c "import duckdb"` 的失败即 exit 1 |
| 3 | 绕路 | SKILL.md 说 office_io "支持 CSV 读入"，实际 `excel-write` 只吃 JSON，直接喂 CSV 抛裸异常 | SKILL.md:122 + office_io.py:109 + 实测 `JSONDecodeError: Expecting value: line 1 column 1 (char 0)` | 有：两步 `excel-read --fmt json > rows.json` 再 `excel-write`（实测通过） | 把 SKILL.md:122 改为"CSV 经 `excel-read --fmt json` 转 JSON 后再 `excel-write`"；或 excel-write 增加 `--from-csv` |
| 4 | 绕路 | `checks.py status` 默认工作区=cwd，在非工作区根跑只有 `[FAIL] tasks/ 目录存在` 而无参数提示 | checks.py:229-230 + 实测 `[FAIL] tasks/ 目录存在 — <cwd>/tasks`，EXIT=1；SKILL.md:53/:146 只说"用 checks.py status" | 有：手动加 `--workspace` | FAIL 文案补一句"若工作区非当前目录，请加 `--workspace <工作区根>`"；SKILL.md 示例带上 `--workspace` |
| 5 | 绕路 | Anti-drop 路径解析会**跨技能目录兜底**，可能把别的技能里的同名相对路径判为"存在"（假 PASS） | checks.py:164-165（`cands.extend(sd / p for sd in SKILLS_ROOT.glob("*/"))`）+ 实测从 `/tmp` 不带 `--base` 仍 `7/7 通过`（其余候选基准均不可能命中） | 无（属隐性风险） | 兜底改为"仅在本任务 `工作区根` 与 `--base` 内解析"，跨技能兜底要么删除、要么仅在路径显式以 `references/`/`scripts/`/`assets/` 开头时启用 |
| 6 | 绕路 | "独立审核"粒度不可操作：判定清单有、**批次/合并规则没有**，按字面执行 = N 个对外交付物 N 次送审 | SKILL.md:104-106（④"任何对外交付物"必审）+ 全文 grep 无"合并/批量送审"规则 + 本任务 plan（`体验评估.../plan.yaml:34`）只对 1 个交付物设了送审，两份"体验官原始记录"（命中①"支撑结论的数据"）未设 | 有：自行按批次聚合送审 | 增设批次规则："同一批次同类产出合并为一次送审，单批 ≤5 个文件；每批至少独立复现 1 项硬证据"；并按产出数量设送审次数上限（见 §4 独立审核条） |
| 7 | 绕路 | 豁免条件与关键产出判定**互相打架**：纯格式转换产生的对外文件同时命中"必审④"与"可豁免" | SKILL.md:106（④任何对外交付物）vs :111（"纯格式转换...可豁免"） | 有：靠主代理自行判定 | 在 :111 补一句优先级："豁免仅在**产出未命中 :106 四类**时适用；命中任一类的产出不得以'格式转换'为由豁免" |
| 8 | 绕路 | SKILL.md 把"环境预检命令"指向 ops.md，但 ops.md 只有本机不可用的 `setup_env.ps1`，无一条可直接照抄的 import 探测命令 | SKILL.md:22（"检测与排障命令见 references/ops.md"）+ ops.md §四 全节（仅 setup_env.ps1 调用） | 有：自写 `python -c "import ..."` | 在 ops.md §四 增一行可照抄命令：`"$PY" -c "import requests,openpyxl,docx,pypdf,yaml,duckdb"` |
| 9 | 绕路 | 文档推荐的 `powershell -File scripts\setup_env.ps1` 无法从 Bash 工具发出；PowerShell 工具又不回显 stdout | ops.md:22/:51（推荐命令）+ 实测 `Command blocked for security: Invoking PowerShell from Bash...`；本轮所有 PowerShell 调用均只回 `Command completed with exit code 0` | 有：改用 Bash 直调 venv 解释器 | ops.md:76 补"在本机用 **PowerShell 工具**（而非 Bash 调用）执行 ps1；且其 stdout 需自行落盘再读" |
| 10 | 不适 | `check-links` 平均耗时被文档写成定值，实测差一个数量级 | ops.md:107（"平均 227ms/条"）、:180（"156ms/条"）vs 实测 `[STATS] 平均 2573 ms/条`（1 条 502 超时占 10.2s） | 有：不看该数字 | 改成区间并注明"取决于超时条数"，或直接删去均值只标并发数 |
| 11 | 不适 | `checks.py` docstring 与代码不一致（meta 必填字段数） | checks.py:24（"meta 必填（任务 / 验证信号）"）vs checks.py:55（含"工作区根"） | 无（仅误导，不影响执行） | 同步 docstring |
| 12 | 不适 | `office_io.py`/`ai_call.py` 缺依赖时抛裸 traceback，与 checks.py / data_query.py 的 [ERROR]+[HINT] 守卫风格不一致 | 实测裸解释器跑 office_io → `ModuleNotFoundError: No module named 'openpyxl'` + traceback；对照 checks.py:173-183、data_query.py:55-62 | 有：看 traceback 就知道换解释器 | 给 office_io / ai_call 加同样的 `_require()` 守卫（退出码 2 + venv 路径提示） |
| 13 | 不适 | `data_query.py files` 的 `[提示]` 走 stderr，`2>&1` 下会插到正文之前，观感错位 | 实测输出首行为 `[提示] 结构化(JSON/CSV/Parquet)优先用 sql 子命令直查…`，后接 `目录：…` | 无（仅观感） | 把提示移到最后或改走 stdout 尾部 |

统计：**阻断 1 条、绕路 8 条、不适 4 条，合计 13 条。**

## 4. 评分（1-5 分）

| 维度 | 分 | 理由 |
| --- | --- | --- |
| 文档准确度 | **4/5** | 主干描述、两个已知怪癖（ops.md:72/76/77）、ASCII 冒号陷阱（:68）、缩写路径（:69）、gh 凭据自动读取（:40/:149）**逐条实测成立**，这份排障表是真打过仗的。扣分在 3 处偏差：SKILL.md:122"支持 CSV 读入"与 office_io 实现不符；checks.py:24 docstring 落后于代码；ops.md:107/:180 把单次实测耗时写成定值。 |
| 脚本可用性 | **3/5** | 四个主力脚本（checks / office_io / data_query / http_fetch）在正确解释器下都能跑，负向行为也正确。扣分在两处"脚本级"缺陷：`setup_env.ps1` 假 OK（问题 2）、`run_stage.ps1` 静默 no-op 且谎报成功（问题 1，虽是本机沙箱根因，但文档未把严重度说清）；另有 office_io 裸 traceback（问题 12）。 |
| 流程可跑通度 | **4/5** | 六阶段主干 + 三道红线 + 任务分层是可执行的，L2 路径我用 toy 数据实跑到"对账通过 + 读回验证"。扣分：跑通需要"自带绕法"（跳过 run_stage、自写 import 命令、记得加 --base/--workspace），且大量重复前缀（每条命令都要重贴 `PY`/绝对路径），体感累。 |
| 验证闭环可操作性 | **5/5** | 这是全场最强项。`office_io` 读回 + 逐字段比对（实测 `True`）+ `checks.py plan` 对账（正向 7/7、5 组篡改全部 FAIL 且定位到行）——**"标完成但文件不存在"这个最典型的自欺被真正拦住了**，而且 FAIL 文案带可执行提示（"交付物须写完整路径"）。 |
| 独立审核可操作性 | **2/5** | 判定清单（SKILL.md:106 四类）能照着判"是否关键"，但**没有任何批次/合并/抽样规则**，也没有数量上限。规则与 quality-gates.md:69 自己承认的"审查端最先饱和"直接冲突。字面执行 N 个对外交付物 → N 次子代理派发，每次还要审核者亲手复现硬证据（SKILL.md:108）。见下方专项分析。 |

**加权总分：3.6 / 5**（文档 4、脚本 3、流程 4、验证闭环 5、独立审核 2）。

### 专项：独立审核的可操作成本（任务第 7 项）

先看规则原文与代码事实：

- 判定：`SKILL.md:106`"命中任一即为关键，必须送审：① 支撑结论的数据/统计结果 ② 代码或配置改动 ③ 报告/文档的**核心结论** ④ **任何对外交付物**"。
- 送审动作：`:104`"每个关键产出必须派**未参与该步执行**的子代理独立审核"；`:107` 审核者只拿产出物 + 验收标准；`:108`"须亲手验证至少一项可复现硬证据（重跑脚本、抽查数据、重新探活链接、读回文件）"。
- 返修：`:117` 同产出返修上限 2 轮 → 2 轮不过转"两个子代理对抗式互审" → 仍不过升级用户。

**我的判断（有罪推定）：这一步的默认成本是"每个交付物 × 1 次子代理"，且文档没有给任何可操作的降本口径。**

依据：
1. **④"任何对外交付物"是全覆盖条款**。只要产出是"给对方看的文件"，就必审。于是"要不要派 10 次子代理"的答案在字面上就是**要**。
2. **全文无批次/合并/抽样规则**。我对 skill 目录全量 grep `独立审核|送审|合并|批量审|审核者|关键产出`，命中的只有规则本身与变更日志，**没有一处**写"同类产出可合并为一次送审"或"可抽样审核"。
3. **每次送审都要有硬证据复现**（`:108`），意味着每个批次至少一次真实执行；审核者还需要工作区访问权 → 又会反复触发红线③的越界授权流程，成本再度叠加。
4. **最坏路径的放大倍数**：1 次送审 + 2 轮返修（每轮强制复查，`:116`）+ 对抗式互审 2 个子代理 ≈ **单产出最多 5 次子代理派发**。10 个交付物 → 量级 40-50 次派发。
5. **连作者自己都没能一致执行**：本任务 `体验评估.../plan.yaml:34` 只给"体验报告"设了 1 次独立审核，而同一任务的两份"体验官原始记录"完全命中 :106①（支撑报告结论的数据），却没有对应送审步骤。这不是指责，而是**规则的粒度不可判定**的最直接证据——同一份计划里，同一个人对同一批产出给出了不同判定。
6. **豁免也堵死了小任务的出口**：`:111` 只允许"L0/L1 或单文件微改/纯格式转换/仅追加文字"豁免。一份 1 页的小分析报告命中的是 ③/④，必须走完整送审——为一个 toy 级产出派一个专职审核子代理，收益/成本明显倒挂。

**结论**：独立审核作为"门禁"价值成立（ops.md:137 也记录了首次实跑就抓出 4 项真实缺陷），但**当前缺一个"粒度与配额"条款**，照字面执行在中等规模任务上会直接失控。建议补两条：① 批次规则（同批同类产出合并送审，单批 ≤5 个文件，每批至少复现 1 项硬证据）；② 降级口径（"产出为对内中间物且已被同一批次的其他送审覆盖时，可记为『随批送审』不再单独派发"），并明确它与 :106④ 的优先级。

## 5. 亮点（≤3 条，具体到"哪条设计实际省了事"）

1. **`checks.py plan` 的 Anti-drop 是"真拦人"，且 FAIL 文案自带修法。**
   我构造的 5 组篡改（缺 `meta.工作区根`、交付物不存在、缩写路径、缺 `交付物` 键、未加引号 ASCII 冒号）**全部被拦下且退出码=1**；缩写那次直接回 `（交付物须写完整路径，缩写如『选品分析.yaml』无法定位）`。实跑省掉了我"逐个 file 手工 ls 一遍交付物"的核对——这是 verify 环节里最容易被 AI 糊弄过去的一步。

2. **`--dry-run` 让 GitHub 参数构造与"凭据是否被读到"在零额度下暴露。**
   一次 `--dry-run` 就打印出完整 URL + 附加头 + `[INFO] 未设环境变量，改用 gh CLI 凭据（gh auth token）提高限额` —— 我不必真发请求就确认了 ops.md:40/:149 的"四来源凭据解析"在本机成立，省掉了"先跑一次、爆 403 再回头查"的试错。

3. **ops.md 的排障表把两个平台级怪癖前置写明了，我因此少踩两次坑。**
   `ops.md:72`（huggingface 502 = 本机出口，不是站点挂）和 `ops.md:76`（命令含 `PowerShell` 字样会被整条拦截）我都实测 100% 复现；`ops.md:68`（ASCII 冒号）也在负向测试里一次命中。这三条让我在遇到"诡异失败"时**直接定位到环境而不是怀疑脚本**，省下的是最贵的排查时间。

## 6. 我没能覆盖的维度（诚实声明）

- **`ai_call.py` 完全没跑**：本机 `AI_API_KEY not set`（setup_env 输出可证），批量并发、`--stats` 用量回显、JSONL 落盘均未验证。
- **`http_fetch` 只验证了参数构造与本地分支**：`--github-search` 未做非 dry-run 的真实请求（不想消耗匿名配额），`--github-repo` 指标实测、`--github-code-search` 带 token 的端到端、403 退避/分类（ops.md:73）**都未实测**——尤其 :73 那套 403 四分类我只读代码没触发过。
- **`office_io` 的 Word / PDF 分支没跑**：`word-write/read`（含 SKILL.md:123 要求的两层字体）、`pdf-extract/merge` 未验证。
- **`data_query.py big` 与大数据集性能未跑**：没有 ≥50MB 的样本，v2.4.2 宣称的"9.6× 加速"与逐字节一致未复现。
- **阶段 2 的"并行派子代理"、阶段 5 的"发布协作/探活"、阶段 6 的"归档移动"未实操**：无外部依赖，且归档会动现有 tasks（只读约束）。
- **`run_stage.ps1` 的结论有环境不确定性**：我证明的是"在本机 PowerShell 工具沙箱下原生子进程不执行、stdout 丢失"。**交互式终端里它是否正常，我未能区分**——这一点请在真机终端复核后再定级。
- **未做多轮返修 / 对抗式互审的实跑**：返修复查（SKILL.md:113-118）的上限 2 轮与升级路径是读文档得出的，不是跑出来的。
- **未验证 SKILL.md:88 的 `ast-grep` 用法**：`ast-grep.exe` 存在且 py_compile 通过，但 `run -p` / `outline` 的实际行为（含"复合语句必须写全"那条坑）没跑。

## 附：本次实际生成的 toy 文件清单

```
tasks/体验评估-ai-workflow-v2.5.0-2026-09-10/toy/
├── sales.csv                     # 5 行销售数据（表头 + 5 行）
├── rows.json                     # excel-read CSV 导出的 JSON
├── sales.xlsx                    # 生成的 Excel（读回逐字段一致）
├── plan.yaml                     # 正向对账用计划（7/7 通过）
├── plan_n1_missing_ws.yaml       # 负向：抽掉 meta.工作区根
├── plan_n2_missing_deliv.yaml    # 负向：交付物不存在
├── plan_n3_ascii_colon.yaml      # 负向：未加引号 ASCII 冒号
├── plan_n4_no_deliv_field.yaml   # 负向：抽掉 step.交付物 键
├── plan_n5_short.yaml            # 负向：交付物写成缩写文件名
├── urls.txt                      # check-links 探活输入（4 条）
├── setup_env_run.txt             # setup_env.ps1 实跑输出（假 OK 证据）
├── ps_joinpath_probe.txt         # 复刻 setup_env step4 的对照实验
├── run_stage_probe.txt           # run_stage.ps1 试验 1（输出缺失）
├── run_stage_probe2.txt          # 试验 2（office_io 未产出）
└── run_stage_probe3.txt          # 试验 3（mark 未生效）
```
预期未生成（即证据本身）：`sales_naive.xlsx`（CSV 直喂 excel-write 失败）、`sales_via_runstage.xlsx`（run_stage 未执行）、`native_probe.txt`（PowerShell 工具不执行原生子进程）。

## 附：流程步数与重复劳动体感

- 实际执行约 **29 个独立命令/探查步**（不含读文档 6 步）；其中"跑脚本"类 18 步、读文档 6 步、纯探针 5 步。
- **重复劳动明显**：① 每条 bash 都要重贴 `PY=`+绝对路径前缀和 `SK=`/`TOY=` 三个变量；② `checks.py` 的 `plan` 要记得 `--base`、`status` 要记得 `--workspace`，两者默认值都是 cwd，一旦 cwd 不是工作区根就静默错位；③ 由于 run_stage.ps1 不可用，脚本调用方式实际只有一种，文档给的"两条路"并没有省事。
- 体感：**中等偏长**。真正"干活"（造数、生成、读回、对账）只占约一半步骤，另一半花在"确认自己没踩环境坑"上。
