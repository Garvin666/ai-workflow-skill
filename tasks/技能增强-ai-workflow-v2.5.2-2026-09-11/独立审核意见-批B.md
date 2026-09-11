# 独立审核意见（批 B）

审核范围：批次 B（文档与手册）——`references/ops.md`、`references/orchestration.md`、`references/quality-gates.md`、`Ledger.md`、`tasks/技能增强-ai-workflow-v2.5.2-2026-09-11/方案评审-熔断机制.md`。
方法：有罪推定式复核，只看产出物与验收标准，不采信执行者自述；下面每条判定均附我**亲手跑出**的原始输出片段。未修改任何被审文件。

## 结论：通过

6 条验收标准逐条判定均为「通过」，其中验收标准 1（本次审核重点：旧口径残留）经全库检索确认**没有任何一处把旧实现当现状描述**。问题清单存在 1 条中等、1 条低，均不影响本轮文档一致性结论（其中最严重一条为设计文档内部的一个数字口径错误，非"旧口径当现状"，且已被同任务另一文档标注更正，但未传播）。

## 逐条判定（验收标准 1–6）

### 标准 1：无未清的旧口径残留 —— 通过

对「彻底移除 / 三处解析 / `~/.workbuddy/<p>` / 基准的上级」逐词全库检索（`SKILL.md`、`references/*.md`、`assets/**`、`scripts/**`、`Ledger.md`），**每一处命中均为合法的历史/更正性叙述**，无一处把旧实现当现状。

原始输出（逐词单独检索）：

```
###### 关键词: 彻底移除
Ledger.md:21:...同时坐实 v2.5.1 的两处**虚假自述**：变更日志与 `plan.yaml` 称跨技能兜底「**彻底移除**」，实为收窄为固定 `~/.workbuddy/` 前缀...
###### 关键词: 三处解析
  (无命中)
###### 关键词: 基准的上级
references/ops.md:120:...v2.5.1 只收窄到「本任务基准／`~/.workbuddy/<p>`／基准的上级」三处，后两条仍属同型缺陷...
references/ops.md:171:...当时只把候选"收窄为固定三处"（`基准／~/.workbuddy/<p>／基准的上级`）...
scripts/checks.py:174:    #   2) base.parent/<p> —— 基准的上级，使交付物落在工作区根之外也判 PASS，与红线③冲突。
```

综合检索 `~/.workbuddy/<p>` / `base.parent` / `base/<p>` / `收窄` 命中 `ops.md:91,120,165,171`、`quality-gates.md:115`、`scripts/checks.py:172,174`、`Ledger.md:21`。逐处定性：
- `ops.md:91,120`：故障排查条目，以「**v2.5.2 已把候选收敛为仅 `base/<p>`**」陈述现状并解释旧通道已移除 → 正确现状 + 历史说明，**合法**。
- `ops.md:165,171`：变更日志 v2.5.2 / v2.5.1 条目，描述"移除两条通道"这一变更本身 → **合法历史叙述**。
- `quality-gates.md:115`（反模式 45）：明确写「**旧**解析器额外尝试 `~/.workbuddy/<p>` 与 `base.parent/<p>`」，并给出新口径"相对路径**只**以 `--base` 为基准" → **合法**（被描述为已移除的旧实现）。
- `scripts/checks.py:172,174`：代码注释，写明"移除的两条通道均属假 PASS" → **合法**（注释解释移除原因）。
- `Ledger.md:21`：更正性叙述，引号内引用原述「彻底移除」并紧跟"实为收窄为…" → **合法**。

**关键的文档-实现一致性核验**（防"文档写了、代码不是那样"）：读 `scripts/checks.py:165-176` 确认 `_candidate_paths()` 实际就返回 `[base / p]`（绝对路径直通），与四处文档声称的"候选收敛为仅 `base/<p>`"**完全一致**：

```python
def _candidate_paths(raw: str, base: Path) -> list[Path]:
    ...
    if p.is_absolute():
        return [p]
    return [base / p]   # ← 候选唯一，旧的两条兜底通道确已移除
```

### 标准 2：反模式清单编号连续、无重复、无跳号 —— 通过

用命令数（`awk` 截取 `## 五、反模式清单` 段后提取行首编号），非目测：

```
序列: 1 2 3 4 5 6 7 8 9 10 11 12 ... 44 45 46
计数: 46
重复（uniq -d）: （空）
与 1..46 的差集（缺失号）: （空）
```

即 1..46 连续、共 46 条、无重复、无缺号。40–46 中：40/41/42/43/44/46 为熔断类（6 条），45 为路径候选类（1 条），与 `ops.md:166`「反模式 39 → **46 条**（新增熔断类 6 条 + 路径候选 1 条）」的口径一致（39+6+1=46）。

### 标准 3：熔断机制四处口径一致 —— 通过

比对 `SKILL.md`「熔断机制」、`orchestration.md §五`、`ops.md`（速查/排障/变更日志）、`quality-gates.md` 四处的三态命名、F1–F5、五步动作、复位条件，**未发现互相矛盾**。

- **三态**：四处均为 `正常` / `已熔断` / 复位（`SKILL.md:160-164`；`ops.md:163`「三态为 `正常` / `已熔断` / 复位」；`方案评审 3.1`；`checks.py:63` `VALID_FUSE=("正常","已熔断")`）。备选命名排查（`熔断中`/`已冻结`/`冻结状态`）**无第二叫法**；`assets/熔断报告模板.md:18` 的"已冻结"是描述性散文而非状态取值，不构成冲突。
- **F1–F5**：`SKILL.md:170-174` 与 `方案评审 3.2` 的表逐行一致；`orchestration.md:54`「F2 复发 / F3 证据不可得 / F4 越界未授权 / F5 配额硬阻断」与 `ops.md:163`「F1 审核链触顶…F5 配额硬阻断」为同一组条件的简述，语义对齐。（`ops.md` 将 F1 简述为"审核链触顶"，与 SKILL 精确定义"同产出返修 2 轮仍不过且互审仍不通过"指同一事，**属简述不属矛盾**。）
- **五步动作**：四处一致为 **停 / 冻 / 证 / 拦 / 报**（`SKILL.md:180-184`、`orchestration.md:51`、`ops.md:163`、`方案评审 3.3`）。
- **复位条件**：四处一致为「只有用户能复位，主代理不得自行解除」（`SKILL.md:164,188`、`orchestration.md:54`、`ops.md:121,163`、`方案评审 3.4`）。
- **机器门禁**：`checks.py:319-349` `_check_fuse()` 实际实现"已熔断即 FAIL + 要求熔断报告含五节"，与文档声称一致：

```
FUSE_SECTIONS = ("触发条件", "已试路径", "卡点根因", "待决策选项", "复位条件")
```

且 `assets/熔断报告模板.md` 实含同名五节（grep 命中 `## 触发条件 / ## 已试路径 / ## 卡点根因 / ## 待决策选项 / ## 复位条件`），`assets/plan-template.yaml:16` 有可选 meta `熔断状态: ""`。

### 标准 4：台账纪律 —— 判定为「带痕迹的更正」（非掩盖历史）

`Ledger.md` 本次确实修改了 v2.5.1 那一行（`Ledger.md:15`）的两格，判定为**带痕迹的更正**，理由与证据：

1. **原表述痕迹仍可辨认**：验收结论格写「**未达成**（本行原写"达成"，2026-09-11 **更正**）」；独立审核格写「…**原此处写"未执行"，已更正为实际结论**」——原措辞以引号内联保留，未被抹平。
2. **更正有依据出处**：`Ledger.md:19` 备注区「2026-09-11 更正说明」明确写更正依据 = `tasks/对抗互审-ai-workflow-v2.5.1-2026-09-11/裁决.md §5`。核验该文件**实存**且 §5 含对应必改项：

```
tasks/对抗互审-ai-workflow-v2.5.1-2026-09-11/裁决.md  (9514 bytes, 实存)
81:## 5. 必改项（按严重度）
89:| 3 | **严重** | **虚假自述**：`Ledger.md:15` 称…、`plan.yaml:25` 称兜底「彻底移除」，均与事实不符 … | 逐处改正为真实口径…
```

即更正对象、依据文件、依据条款三者对得上，**不是"改掉不好的记录"而是"把虚假记录改回真实并留痕"**。
3. **在备注区有说明**：满足标准所要求的第三点。

**残留风险（低）**：`Ledger.md:4` 头部规则仍字面写「只追加，不重写、不删改历史条目」，本次修改与之**字面冲突**——规则本身未补「更正须留痕」条款。建议后续把该规则扩为"只追加；如确需更正，须内联保留原表述 + 备注区给出依据"。此为制度性张力，**不影响本次"带痕迹更正"的成立**。

### 标准 5：设计文档的自证程度 —— 通过（外部依据抽查全部可追溯）

用指定 venv 解释器 + `http_fetch.py` 抓取 3 条（≥2）带 URL 的外部依据，**全部指向真实存在且内容对得上的页面**：

```
########## https://aipatternbook.com/circuit-breaker
<title>Circuit Breaker - Encyclopedia of Agentic Coding Patterns</title>
<meta property="og:description" content="A circuit breaker is a stateful guard that stops calling a failing dependency or runaway loop once it crosses a failure threshold, fails fast while the path…">
########## https://docs.tryhyphen.com/agents/stuck-detection
<title>Stuck Detection | Hyph-en</title>
########## https://hackernoon.com/how-to-survive-the-multi-agent-loop-of-death-in-production
{"@type":"Article","name":"How to Survive the Multi Agent Loop of Death in Production","author":{"name":"Abhilash Pakalapati"},"datePublished":"2026-05-26", ...}
...the circuit breaker must serialize the entire state dictionary, package the iteration audit logs, and push the transaction into a priority queue... highlight the two alternating outputs that caused the loop...
```

- `aipatternbook.com/circuit-breaker`：真实 mdBook 页，副标题与设计文档引用的"断路器三态 / 状态机"点吻合。
- `docs.tryhyphen.com/agents/stuck-detection`：真实页「Stuck Detection」，与 F2 阈值来源（同一动作连续 N 次）吻合。
- `hackernoon.com/...loop-of-death`：真实文章（作者、日期在 JSON-LD 中），正文含"序列化 state 字典 + 打包 iteration audit logs + 高亮导致循环的两处输出"，**与设计文档"熔断报告必须带状态快照与已试路径"的引用点逐字对应**。无 404、无日期型假链接、无 502。候选方案对比维度（可行性/成本/风险/可回滚性/验收匹配度）与推荐理由（B 方案）在文档内自洽。
- 未出现本机出口限制导致的 502，故本项**无需**标注"本机无法验证"。

**但本项附带一处发现（列入问题清单）**：设计文档中的一个内部计数与事实不符（见问题清单 #1），不属"外部依据失效"，故不影响本项判定。

### 标准 6：文档引用完整性 —— 通过

跑 `checks.py skill` 读回，其中"文档引用完整性"一项 OK：

```
[ OK ] 文档引用完整性 — 检查 28 条引用
...
=== 结果：19/19 通过，FAIL=0 ===
```

（`SKILL.md` 与 `references/*.md` 中以反引号写的 `xxx.md/.yaml/.py/.ps1` 引用均真实存在。注意 `checks.py` 的 `REF_PATTERN` **只扫 `SKILL.md` 与 `references/*.md`**，不覆盖 `tasks/` 内文档与 `assets/` 内正文，故本项通过不代表任务目录内的引用也全存在——这也是问题清单 #2 不被自动门禁拦下的原因。）

## 问题清单（按严重度排序）

### #1（中等）设计文档残留一个与事实不符的计数："21 个"应为"20 个"

- **现象**：`方案评审-熔断机制.md:95` 写「不迁移 **21 个**"相对技能目录"写法的历史交付物 token」，而 `references/ops.md:165` 与 `tasks/.../基线-复现与回归风险.md:26,32` 均为 **20 个**，且 `基线-复现与回归风险.md:30` 明确记录"21"是本轮转述错误、已更正为 20。
- **精确定位**：`tasks/技能增强-ai-workflow-v2.5.2-2026-09-11/方案评审-熔断机制.md:95`。
- **期望**：改为"20 个"，或注明"（另见基线的口径更正）"。**同一任务内两份文档对同一事实给出不同数字，正是本技能反复强调的"描述与实现不符"同型问题**——虽属划界句里的次要事实、且 `ops.md`（对外变更日志）用的是正确值，仍应一并改齐。

原始输出：

```
references/ops.md:165:...两个工作区共 144 个交付物 token 中 **20 个**为"相对技能目录"的历史写法...
tasks/.../方案评审-熔断机制.md:95:- 不迁移 21 个"相对技能目录"写法的历史交付物 token...
tasks/.../基线-复现与回归风险.md:32:### 20 个风险 token 明细...
```

### #2（低）变更日志/设计文档前瞻引用了尚未生成的交付物

- **现象**：`改动对照表-v2.5.2.md` 被 `references/ops.md:165`、`方案评审-熔断机制.md:95`、`基线-复现与回归风险.md:62` 引用，但**该文件当前不存在**；`find ... -iname "*改动对照*"` 无命中。经查 `plan.yaml` 它对应 step 8 的交付物，而 step 8 状态 = **待办**（`plan.yaml:66-67`）。
- **定性**：这不属标准 6 的 FAIL——`checks.py` 只校验技能内引用，且该文件是"任务尚未收尾"的既定产出，非凭空引用。但 `ops.md` 的 v2.5.2 变更日志以**已完成语气**叙述并指向一个尚不存在的对照表，存在"交付时若忘记生成即变成虚假引用"的风险。
- **期望**：step 8 收尾时确保该文件落盘；否则把 `ops.md:165` 的指向改为"待生成的对照表（见 plan.yaml step 8）"。

### #3（低，制度建议）`Ledger.md` 头部规则未为"更正"留口

- **现象**：`Ledger.md:4` 规则写"只追加，不重写、不删改历史条目"，与本次（合规的）更正行为字面冲突。
- **期望**：把规则扩为"只追加；确需更正时须内联保留原表述 + 备注区给出依据"，使制度与本次实际做法自洽。**不影响标准 4 判定**。

## 我无法确认的项（诚实列出）

1. `方案评审` 表中其余带 URL 依据（`openlegion`、`multigrid`、`vibesecadvisory`、`workhint`、`naitive`、`hackernoon` 之外几条）我**只抽查了 3 条**（≥2 条即可），未逐条探活；其中境外域名若后续复抓遇 502，按规则应为"本机无法验证"而非"失效"，本次未遇 502。
2. 设计文档引用的 **LangGraph `recursion_limit` 默认 25 / OpenAI Agents SDK `max_turns` 默认 10 / AutoGen `max_consecutive_auto_reply`** 等**具体数值**，我未回到官方源码逐一核对（未在审查要求内，且需消耗配额）；仅确认其来源页可达、方向与业界常识一致。
3. `hackernoon` 文章正文含"$0.28 / 95.1% success"等**基准数字**，我未核验其数据来源（文中未给可复现方法）；设计文档未把这些数字当证据引用，故不构成文档缺陷，但**不建议**后续把它们当【基准实测】使用。
4. Ledger 之"**只追加**"纪律的**历史完备性**（即此前各版本行是否也从未被改过）我无法凭当前快照回溯确认——本次只能核验 v2.5.1 这一行确为带痕更正。
