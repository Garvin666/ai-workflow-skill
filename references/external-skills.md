# 外部技能路由与适配（vendored: mattpocock-skills-zh-CN）

> **定位**：装在技能库根、但**不属于 ai-workflow 本体**的第三方技能，本文件是它们的**唯一宿主侧适配层** —— 说明从哪来、什么时候该调、与本体口径怎么对齐。
> **加载口径**：阶段 0 第 3 步「查可用 Skill」命中外部技能簇时读；日常任务不需要（SKILL.md 只留一句指针）。
> **版本**：1（2026-09-30，随 mattpocock 整合任务新增）

---

## 一、来源与许可

| 项 | 值 |
| --- | --- |
| 上游 | vinvcn/mattpocock-skills-zh-CN（mattpocock/skills 的简体中文本地化版） |
| 锁定 rev | 3f92a83668ef8f303e6278f31c49fed9543cbc51（2026-09-28） |
| 许可 | MIT（上游 LICENSE 与 LICENSE.zh-CN.md 随库保留） |
| 安装形态 | **扁平外挂**：每个技能原样装为技能库根的独立技能，**不并入 ai-workflow 本体** |
| 账本 | 技能库根 `.vendor/mattpocock.lock.json`（上游 rev + 逐文件 sha256 + 补丁清单 + 占用名 + 引用提及登记） |
| 安装数 | **24**（上游 engineering/productivity/misc 的 21 个 + 上游 in-progress 的 writing-* 3 个） |

**⚠️ 资产归属**：这批是**第三方 MIT 资产，不是自研**。不得登记进 `meta.自研工具`；不得随 ai-workflow 本体仓推送（本体仓是 `Garvin666/ai-workflow-skill`，与技能库根不是同一处）。

**为什么选扁平外挂而非并入本体**：三条实测约束 —— ① 技能库索引只扫一层目录，上游的三层布局直接装等于隐形；② 本体自检的 frontmatter 判据要求含 `agent_created`；③ 21 个能力折进本体会显著抬高每次任务的固定 token 成本。详见任务 `tasks/mattpocock整合设计-ai-workflow-2026-09-30/`。

---

## 二、调用口径（上游两分类 → 宿主语言）

上游按「谁能调用」把技能分两轴，宿主阶段 0 只按目录名与 description 匹配，没有对应机制。**本轮的实测口径是：上游的 `disable-model-invocation: true` 就是 User-invoked 的机器实现** —— 不必靠推断（设计阶段曾推断「宿主无对应」，实施期读 frontmatter 实样后修正）。

| 上游分类 | 机器判据 | 数量 | 宿主侧怎么用 |
| --- | --- | --- | --- |
| **User-invoked** | frontmatter 含 `disable-model-invocation: true` | 10 | **由主代理按场景显式调用**，不指望自动匹配命中 |
| **Model-invoked** | 无该字段 | 14 | 可被阶段 0 的索引匹配自动命中，作为阶段内联纪律使用 |

> **为什么保留 `disable-model-invocation` 而不删**：它是这批技能**唯一机器可读的分类依据**，删掉就只剩推断；且不违反宿主 frontmatter 判据（该判据只要求**含**三键，不禁止额外键）。`argument-hint` 同理保留。

---

## 三、路由表（何时该调 → 调哪个）

> 表里**只写技能名与触发场景，不复制技能正文**（防双写）。正文以技能库根对应目录为准。

| 场景 | 调哪个 | 来源分类 |
| --- | --- | --- |
| 要用先写测试的方式做功能或修缺陷 | tdd | Model-invoked |
| 要设计模块边界、判断该在哪测 | codebase-design | Model-invoked |
| 要建或打磨项目领域模型、统一术语 | domain-modeling | Model-invoked |
| 设计问题答不上来，要个一次性原型验证 | prototype | Model-invoked |
| 疑难 bug 或性能回退，要纪律化诊断 | diagnosing-bugs | Model-invoked |
| 要对一段 diff 做 Standards × Spec 双轴评审 | code-review | Model-invoked |
| 要逐个 hunk 解 merge 或 rebase 冲突 | resolving-merge-conflicts | Model-invoked |
| 要对照一手来源调研并把结论落成文件 | research | Model-invoked |
| 要生成带人走过一次性步骤的交互式脚本 | wizard | Model-invoked |
| 计划或设计没想透，要被追问到每个分支都有答案 | grilling | Model-invoked |
| 同上，但用户主动点名要「拷问」 | grill-me | User-invoked |
| 要边追问边建 domain model 与 ADR | grill-with-docs | User-invoked |
| 要扫描代码库的深化机会并出报告 | improve-codebase-architecture | User-invoked |
| 跨会话续接，要把当前对话压成交接文档 | handoff | User-invoked |
| 要跨会话学一个新概念 | teach | User-invoked |
| 某条消息没讲明白，要对方重讲 | wait-what | User-invoked |
| 有答不了的决策，要变成问卷交给能答的人 | to-questionnaire | User-invoked |
| 要给 agent 写文档（技能、AGENTS 类文件等） | writing-for-agents | Model-invoked |
| 要在危险 git 命令执行前拦住 | git-guardrails-claude-code | Model-invoked |
| 要配 pre-commit 钩子 | setup-pre-commit | Model-invoked |
| 要生成练习目录结构 | scaffold-exercises | Model-invoked |
| 要按「节拍」组织叙事段落（**上游标未定稿**） | writing-beats | User-invoked |
| 要写叙事片段（**上游标未定稿**） | writing-fragments | User-invoked |
| 要定叙事整体形状（**上游标未定稿**） | writing-shape | User-invoked |

**依赖提示**：`tdd` 正文要求配合 `codebase-design` 使用（后者是 seam、adapter、depth 这些词的唯一定义处）；`grill-with-docs` 依赖 `domain-modeling`。这几个**成组装齐了**，不要单装一个。

---

## 四、只取机制（上游有、但**不搬运文件**的 7 个）

这 7 个是为「每仓持久 domain model + issue tracker」设计的编排层，而宿主的编排层是 `plan.yaml` + `tasks/`。硬搬会造成两套留痕体系并存，直接违反宿主「同一任务内无两套口径」的质量原则。故**只取词汇，折进本体手册并注明出处**：

| 上游技能 | 取走的机制 | 折进哪里 |
| --- | --- | --- |
| to-tickets | tracer bullet（可独立验证的纵向切片）+ blocking edges | `references/adaptive-planning.md` |
| wayfinder | decision ticket 与共享 map（超出单会话的工作拆成待决问题） | `references/adaptive-planning.md` |
| implement | 在约定 seams 处驱动 tdd、提交前以 code-review 收尾 | `references/orchestration.md` |
| to-spec | 「不做访谈、只综合已讨论内容」的总结式产出纪律 | 宿主任务确认表已有同类，**未新增** |
| ask-matt | 「当前情境该用哪个 skill」的路由思路 | 由本手册承担，**不单独造技能** |
| triage | roles state machine | **暂缓**（宿主无 issue 入口） |
| setup-matt-pocock-skills | 「每仓一次配置」的一次性前置模式 | 宿主 `assets/templates/` 已有同类 |

> 折进时**必须注明出处**（写法：「借自 mattpocock/skills 的 to-tickets」），不要伪装成本体原创。

---

## 五、已知边界（诚实边界）

1. **正文里的文件名提及 ≠ 技能内引用**。实测扫描出 24 条反引号 `.md` 在技能内解析不到，逐条看下来绝大多数是**正文对被整合项目仓文件的提及** —— 例如 CONTEXT 文档、AGENTS 类文件、CONTRIBUTING、CODING_STANDARDS、0001-slug 这类 ADR 命名模板。**设计文档原定的「改引用写法」补丁因此未执行**：把它们改成 markdown 链接会变成死链、并破坏上游语义（`writing-for-agents` 正文里的 AGENTS 与 CLAUDE 是它的**主题对象**，不是引用）。这 24 条已登记在 lock 的 `reference_mentions`，由 lint 脚本分档判定（已登记 → SKIP 并计数，未登记 → FAIL）。
2. **writing-\* 三个是上游未定稿**（上游 in-progress 目录），用户拍板纳入。内容可能随后续同步变动。
3. **上游随技能附带的 agents 清单**（agents 目录下的 openai.yaml）与 dsh-plugin 调用约定**不适用**宿主，保留不删（删掉只增加同步时的 diff 噪音）。不采用 `/zh-<name>` 调用形式。
4. **本地补丁只有一处**：frontmatter 追加 `agent_created: false` / `source` / `upstream_rev` 三键。**正文逐字未改**（补丁清单在 lock 的 `patches`）。
5. **通用名辨识度低**：research、teach、handoff、code-review、prototype 等是通用词，按簇定位时可能与既有技能混淆。lock 登记了占用名，本手册的路由表提供语义锚。
6. **状态模型不合并**：上游的每仓持久 domain model（CONTEXT 类文档、ADR）只在**被整合的项目仓**内作为项目文档存在，**不参与宿主留痕**。宿主侧仍是每任务一份 `plan.yaml`。

---

## 六、机器检查

**`scripts/external_skill_lint.py`** —— 外部技能的放宽判据，是本体自检在外部技能上的对应物。

| 判据 | 分级 |
| --- | --- |
| frontmatter 可解析且含 name / description | 缺 → FAIL |
| 引用完整性（分档：技能内可解析 / 已登记提及 / 真断链） | 真断链 → FAIL |
| 无硬编码密钥 | 命中 → FAIL |
| 无可疑或混淆脚本片段 | 命中 → **WARN**（不是 FAIL） |
| lock 与磁盘 sha256 一致（加 `--verify-lock`） | 不一致 → FAIL |

**为什么另起一套而不复用 `checks.py skill`**：后者是为**宿主本体**设计的（还查 `assets/templates` schema、口径守卫、平台门控、指标幂等），拿它卡上游技能会产出一屏与兼容性无关的 FAIL；但完全不给外部技能机器检查，就等于把它们置于**未检测**状态 —— 未检测不是通过。

**判据 4 为何只 WARN**：`git-guardrails-claude-code` 这类技能的**正当内容就是**识别并拦截危险命令，正文里必然出现危险命令字面量。命中即 FAIL 会把「技能在讲怎么防」误判成「技能在干坏事」，由人判定。

用法：

```
python scripts/external_skill_lint.py                 # 查 lock 登记的全部外部技能
python scripts/external_skill_lint.py --verify-lock   # 加做 lock 一致性
python scripts/external_skill_lint.py --skill tdd     # 只查一个
```

---

## 七、同步上游

上游按内容刷新同步 mattpocock/skills，本地有 1 处补丁。同步规程：

1. 取上游新 rev，与 lock 的 `upstream_rev` 比对，确认有更新。
2. 按 lock 的 `patches` **重放补丁**（不是 fork，也不是手工改）。
3. 逐文件 sha256 重算写回 lock，跑 `external_skill_lint.py --verify-lock`。
4. 若上游新增了技能间引用，检查被引目标是否已在库内 —— 断链会让上层技能失效。

**不要**把上游内容并进 ai-workflow 本体仓，也不要把本体内容写进这批技能目录 —— 两边一旦互写，同步时无法区分差异来源。
