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
| setup_env.ps1 | 初始化 venv 与依赖（requests / openpyxl / python-docx / pypdf / pyyaml） | `powershell -File scripts\setup_env.ps1` |
| ai_call.py | 调 AI 模型：`--model` 覆盖、`--system-file`、`--max-tokens`、`--temperature`、`--stats` 用量回显、`--batch-file` + `--concurrency` 批量并发（结果落 JSONL） | `ai_call.py --batch-file prompts.txt --concurrency 3` |
| http_fetch.py | 联网抓取：`--github-repo a/b,c/d` 指标实测（并发 + 限流退避 + 缓存）、`--text` HTML→文本、`--grep`/`--max-chars` 定向提取、`--no-cache`/`--ttl` 控缓存、**`--check-links` 批量探活（只取状态码不下载正文，并发 8，交付外链前必跑）** | `http_fetch.py --check-links urls.txt`（探活）／ `http_fetch.py <URL> --grep "关键词" --max-chars 3000`（定向抓取） |
| office_io.py | Office 读写：excel-read（xlsx/csv）、excel-write（单表/多表，默认表头加粗+冻结首行+自适应列宽）、word-read/write、pdf-extract/merge | `office_io.py excel-read data.csv --fmt json` |
| run_stage.ps1 | 状态检查 + 一键调脚本 | `run_stage.ps1 http_fetch.py <URL>` |

各脚本详细参数：加 `--help`。

## 三、环境变量

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| AI_API_KEY | AI 调用凭据（必填，不落日志） | — |
| AI_API_BASE / AI_MODEL | API 地址 / 模型 | https://api.deepseek.com/v1 ／ deepseek-chat |
| AI_PRICE_IN / AI_PRICE_OUT | 成本估算单价（元/百万 token） | 未设则只报 token |
| GITHUB_TOKEN | GitHub API 鉴权（匿名仅 60 次/小时，易 403 限流） | 未设则匿名 |
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
| GitHub 搜索/取数突然全 403 | 分清两套配额：core 为 **60 次/小时**（匿名），search 为 **10 次/分钟**（匿名）/ 30 次/分钟（认证）——search 每分钟自动重置，可等 1 分钟重试而不必等 1 小时 |
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

- **v2.3（2026-09-10）实战修复**（由真实任务 `tasks/技术调研-网络安全学习-2026-09-10/` 驱动）：
  - `checks.py` **修假绿**：缺 pyyaml 时原会先报错、再打印 `结果：0/0 通过，FAIL=0` 并返回 0，调用方（含 CI/子代理）会误判为通过。现改为 `_require_yaml()` 统一守卫，**以退出码 2 中止**并给出 venv 绝对路径提示；`main()` 不再吞掉非零 `code`（`return 1 if n_fail else code`），未跑起来时输出「未执行」而非「全绿」。同一守卫也修掉 `load_plan` 在 `status` 子命令下的裸 traceback。
  - `http_fetch.py` 新增 **`--check-links`** 批量探活：只取状态码不下载正文。实战量化——12 条链接串行探活 41.2s 且白下载 3.5MB；新工具并发 8 实测 1.9s（≈40× 加速，平均 156ms/条 vs 3400ms/条）。
  - `http_fetch.py fetch` 在 `--out` 目标已存在但抓取失败时打印告警（防旧内容被误用）。
  - 交付前置动作确立：**外部链接必须探活后才可写进交付物**（实战中拦下 1 条 404 死链并修正）。
- **v2.2（2026-09-10）**：效率增强——SKILL.md 瘦身（脚本速查/排障/日志移入本文件）；`http_fetch.py` 增加本地缓存（TTL + `--no-cache`）与 GitHub 多仓库并发；`ai_call.py` 增加 `--batch-file` 批量并发（JSONL 输出）；`checks.py` 增加 `status`（任务总览 + 归档建议）与 `mark`（安全更新步骤状态）；阶段 1 追问轮次上限 2 轮、阶段 0 用 `status` 替代逐个翻历史任务。
- **v2.1（2026-09-10）**：新增 `checks.py`（自检 + Anti-drop 对账）；模板 3 → 7 类；`office_io.py` 支持 CSV/多 sheet/格式化；`http_fetch.py` 增加 `--grep`/`--max-chars`；`report-template.md` 补证据等级、验证闭环证据、复盘三节；依赖补 pyyaml。快照 `_backup-v2/`。
- **v2.0（2026-09-10）**：任务分层 L0/L1/L2；验证闭环前置门禁；阶段 6 复盘沉淀；证据分级标注；评审六偏差；references 拆分（quality-gates / orchestration，补全 playbook）；模板 schema 统一；`http_fetch.py` 403 限流重试与 HTML→文本；`ai_call.py` model 覆盖与用量回显。快照 `_backup-v1/`。
- **v1.0**：六阶段主干。
