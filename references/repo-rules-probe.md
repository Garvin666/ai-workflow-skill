# 外部仓库规则前置调研（repo-rules-probe，v4.46.0）

> **定位**：在「读／改／推任何非本机仓库」之前，先摸清对方规则。产物是**三态结论**，不是「一份规则清单」。
> 执行器：`scripts/repo_rules_probe.py`｜流程位置：阶段 2（方案评审之前）｜机器校验：`--selftest`

## 一、什么时候必须跑

**触发（任一命中）**：

- 要给上游提 PR / 开 issue / 改 fork；
- 要往非本机仓库写入（含建分支、推 commit）；
- 要把对方仓库的产物纳入本任务（克隆改造、二次分发）。

**不触发**（跑了就是冗余，违反效率原则）：

- 纯查资料、查 star、找实现（走 `http_fetch.py --github-search/--github-repo`）；
- 只读某一个文件（`gh api .../contents/<path>` 即可）；
- 操作的是本机隔离仓（`scripts/git_check.py` 的地盘）。

## 二、命令

```bash
# 人读摘要（默认）
python scripts/repo_rules_probe.py --repo owner/name

# 多仓 + 结构化输出
python scripts/repo_rules_probe.py --repo owner/a,owner/b --json

# 离线自检（不联网，含 404 两义阴性对照）
python scripts/repo_rules_probe.py --selftest
```

| 参数 | 说明 |
| --- | --- |
| `--repo` | `owner/name`，逗号分隔多个；必填 |
| `--json` | 输出 `{"results":[...]}`；缺省为人读摘要 |
| `--token` | PAT；缺省按 `--token → GITHUB_TOKEN → GH_TOKEN → gh auth token` 解析（**复用 `http_fetch._resolve_token`，优先级单一事实源在该文件**） |
| `--detail-limit` | 最多取多少条**生效** ruleset 的详情，默认 3（防 N+1） |
| `--timeout` | 单请求超时秒数，默认 15 |

退出码遵循 `references/interface-contract.md`：`0` 至少一仓得到结论｜`2` 用法错误｜`3` 全部仓「未检测」。本脚本不产出 `1`。

## 三、三态语义（本契约的核心）

| 态 | 含义 | 允许的下一步 |
| --- | --- | --- |
| `有` | 端点 200 且字段非空 | 按该规则准备（读 CONTRIBUTING、对齐 PR 模板、满足必过检查） |
| `无` | 端点 200 但列表/字段为空，**或** `branch protection` 返回 `404 + Branch not protected` | 可认为对方未设该规则 |
| `未检测` | 403 / 401 / 网络失败 / `404 + Not Found` / message 语义不明 | **不得当成「无」**；必须在方案里写明「未确认」并说明原因 |

### 为什么 `未检测` 必须独立成态（实测依据）

`branch protection` 同一个 404 有两种 message（本机实测，2026-10-20）：

| 场景 | 状态码 | message | 正确判读 |
| --- | --- | --- | --- |
| 无 admin 的公开仓（`anthropics/claude-code`） | 404 | `Not Found` | **未检测**（你看不到） |
| 有 admin 但未设保护的自家仓 | 404 | `Branch not protected` | **无**（真的没有） |

只看状态码，这两种会合并成「没有保护」——正是「未检索不得说不存在」在实现层要防的静默失真。`--selftest` 里有一条专门的阴性对照卡这个分支。

## 四、输出字段

```
results[]
├─ repo / fetched_at
├─ basic              state / default_branch / archived / pushed_at / license / 三种合并方式
├─ community          state / health_percentage / files{6 类}（files 内每项 state + url）
├─ governance
│   ├─ rulesets       state / items[]{name, enforcement, required_checks, required_approvals, code_owner_review}
│   └─ branch_protection  state / required_checks / required_approvals / reason
├─ agent_files        state / found[]{name, location, priority, size, url}
├─ rate_limit         core_remaining / core_limit / reset_epoch
└─ summary            []string，3–8 行中文摘要（未检测会显式出现）
```

**`summary` 的写法约束**：`未检测` 必须原样出现，禁止渲染成「无保护」「无」。摘要行数控制在 3–8 行（超出说明该仓规则面异常复杂，应改用 `--json` 自行处理）。

## 五、读结果做决策

| 信号 | 动作 |
| --- | --- |
| `community.files.contributing.state == 有` | 读该 URL 的贡献指南，把「构建/测试命令 + 提交要求」抄进方案 |
| `community.files.pull_request_template.state == 有` | 按模板字段准备 PR 描述，不自拟结构 |
| `rulesets.items[].required_checks` 非空 | 这些检查是**合并前置条件**，方案里必须给出「本地怎么先跑一遍」 |
| `rulesets.items[].required_approvals > 0` | 说明需要人审，排期时计入等待 |
| `branch_protection.state == 未检测` | 方案中写「分支保护未确认」；若之后推送被拒（protected branch hook），优先怀疑此项而不是权限 |
| `agent_files.found` 含 AGENTS.md（裸名，对方仓文件） | 动手前读它（本脚本只报存在性，不拉正文） |
| `rate_limit.core_remaining < 100` | 停止批量探测，改用缓存/缩小范围 |

## 六、局限（诚实边界，勿夸大）

1. **`community/profile` 只认 GitHub 认可的路径**。对方把贡献说明写在 wiki 或自定义位置时返回 `无`——这是**假阴性**，已知未解。
2. **`agent_files` 只探三层**（根 / `.github` / `.cursor/rules`），不递归整树。monorepo 子目录里的 AGENTS.md 会漏；需要时用 `gh api .../contents/<path>` 手工补。
3. **CLA / DCO 无法从仓库元数据判定**。它们发生在 PR 事件与 CI 里，本脚本不输出这两项的「有/无」；如需判断，读 `.github/workflows/` 与 PR 检查上下文，并标「推断，未验证」。
4. **`rulesets` 的 `bypass_actors` 未解析**：谁可以绕过规则不在射程。
5. **`health_percentage` 不是治理严格度**：它是元数据完整度（codex 62% 却有 9 条生效规则），**不得当质量指标引用**。
6. **未做磁盘缓存**：同一仓重复调用会重新请求（每仓约 5–7 次 core 请求）。多仓批量时注意 `rate_limit`。
7. **`rulesets` 匿名可读性未实测**：本次只在带 token 下验证；无 token 时该项报 `未检测`。

## 七、与既有工具的边界（不重叠、不互相替代）

| 工具 | 管什么 | 与本脚本的关系 |
| --- | --- | --- |
| `http_fetch.py --github-repo` | 仓库**指标**（star/forks/pushed_at/license） | 本脚本不做指标横评；需要选型时先跑它 |
| `http_fetch.py --github-search` | 按关键词**找项目** | 本脚本假设「项目已选定」，只查规则 |
| `references/push-routing.md` | **推自家两仓**的分流、dry-run、验收 | 本脚本查的是**对方**的规则，不替代自家推送口径 |
| `references/git-conventions.md` | **本机仓**的分支模型与 commit 规范 | 本脚本不判断本机仓；两条规范互不覆盖 |

## 八、登记与自检

- 双处登记：`SKILL.md`「手册与脚本索引」E 区 ＋ `references/ops.md`。
- 自检：`python scripts/repo_rules_probe.py --selftest`（离线，16 项断言，含 404 两义与三态全覆盖）。
- 新增字段或改判据前，先扩 `--selftest` 的阴性对照，再改实现——顺序反了就会用「跑通」替代「判对」。
