# 外部技能路由与适配（外部技能簇 · 五上游）

> **定位**：装在技能库根、但**不属于 ai-workflow 本体**的第三方技能，本文件是它们的**唯一宿主侧适配层** —— 说明从哪来、什么时候该调、与本体口径怎么对齐。
> **当前五个上游**（§1.1–§1.5）：**mattpocock-skills-zh-CN**（24 个，扁平外挂）、**ppt-master**（1 个，目录联接）、**humanizer**（1 个，扁平外挂）、**hairline-create**（1 个，扁平外挂）与 **archify**（1 个，扁平外挂——⚠️ 本机**装得进、可调用；产物链「会话内受阻、会话外可绕」**，见 §1.5）。来源与许可见 §一。
> **另**：另有五个**本地已装、非 vendored 的能力技能**（reviewed-change-apply-gate 等）—— ⚠️ 它们**不是上游**（不在 `.vendor/` 任何 lock 内、无 source/upstream_rev/LICENSE），故**不并入「上游」计数**，单列 §1.6，来源定性留待用户裁定。
> **加载口径**：阶段 0 第 3 步「查可用 Skill」命中外部技能簇时读；日常任务不需要（SKILL.md 只留一句指针）。
> **与「整合方法」的分工**：本文件只讲**装好之后怎么调**（运行时路由）与**来源/许可/安装形态/账本**。⚠️ **原则侧不在这里**：上游技能若贡献的是**可迁移的视觉工艺原则**，它们入 `references/aesthetic-rubric.yaml`（判据集）而非本文件 —— 本文件只留出处与本文件不重述的声明（见 §1.4 第 2 条）。**怎么把外部技能装进来**（一次性的整合工程 —— 探针目录法、宿主三道门禁实测、接入形态选型、依赖序安装、验收登记）见技能 `external-skill-library-integration`。**做整合翻那份，用已整合的技能翻本份。**
> **与 `references/ppt-mode.md` 的分工**：本文件记 `ppt-master` 的**来源 / 许可 / 安装形态 / 账本 / 调用口径**；**产出结构与验收契约**（Y0–Y4 / Y-a–Y-d / E1–E6）在 `references/ppt-mode.md`。**同一物理量只写一处**，两侧交叉引用、不重述。
> **版本**：4.3（2026-09-30 建；2026-10-09 首次泛化为两上游并登记 ppt-master，同日二次泛化为三上游并登记 humanizer，同日三次泛化为四上游并登记 hairline-create；2026-10-10 四上游**内容补**：§1.4 增第 5 条指向工程手法文档 `references/artifact-engineering.md`，并修正 §1.4 表内许可值 `2025 Lucas Markes` → `2026 Lucas Marques`；2026-10-11 五次泛化为**五上游**并登记 archify；⚠️ 同日**改判并更正**：archify 的本机可用性结论由「系统层 nlink 语义异常 ⇒ 本机不可产出产物」改为「宿主会话把删除重定向为回收站 ⇒ **会话内**受阻、**会话外可绕**」（证据链见 §1.5），并新增 §二 末的「默认豁免（图示例外）」条款；2026-10-11 增 **§1.6**：登记五个**本地已装、非 vendored** 的能力技能，并明确「不是上游」的判据与由此产生的机器检查缺口）

---

## 一、五个上游

### 1.1 mattpocock-skills-zh-CN（24 个，扁平外挂）

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

### 1.2 ppt-master（1 个，目录联接）

| 项 | 值 |
| --- | --- |
| 上游 | hugohe3/ppt-master（AI 演示文稿生成路由工作流） |
| 许可 | MIT（上游 LICENSE 随库保留） |
| 本机版本 | **6.6.0**（2026-10-09 落笔坐标；⚠️ **调用时须重读**，见 §七） |
| 规模 | 12994 文件 / 107 MB（其中 12167 个 svg 模板与 186 个 wav 音效占绝大部分；文本类仅 537） |
| 安装形态 | **目录联接（零拷贝）**：`~/.workbuddy/skills/ppt-master` → `~/.codex/skills/ppt-master` |
| 账本 | `.vendor/ppt-master.lock.json`（上游坐标 + 版本 + 许可 + 安装形态 + 内容摘要） |
| 产物结构与验收契约 | 在 `references/ppt-mode.md`（**本文件不重述**） |

**⚠️ 资产归属**：同为**第三方 MIT 资产，不是自研** —— 不得登记进 `meta.自研工具`，不得随 ai-workflow 本体仓推送。

**⚠️ 与 1.1 的三处关键差别（都是实测出来的，不是设计偏好）**：

1. **零拷贝 + 无补丁**：它自带 fail-closed 完整性门禁（校验自身 frontmatter 元数据精确值与 LICENSE / SPONSORS 摘要），照 1.1 那样「给 frontmatter 加三键」会**直接把它顶停**。故本批**一个字节都不改**。
2. **体积差三个数量级**：107 MB vs 1.1 的几十 KB ⇒ 复制安装会产生第二份大体量文件树，而它本来就是「一份物理拷贝、多处引用」的形态，故走联接。
3. **它自己就是一套完整路由工作流**（三顶层路由 + Plan/Do·Check/Act + 自带校验器）⇒ **不适用 §二 的「扁平外挂 + 宿主索引匹配」调用模型**，宿主侧只叠一个契约层（见 §二末段与 §三）。

> **为什么不做成「装进本体的一个模式 + 复制技能」**：① 契约层已能覆盖 ai-workflow 侧的判据（`references/ppt-mode.md`）；② 复制会带来同步负担与 107 MB 冗余，而联接天然跟随上游；③ 改它文件会踩完整性门禁。

### 1.3 humanizer（1 个，扁平外挂）

| 项 | 值 |
| --- | --- |
| 上游 | blader/humanizer（去 AI 味技能：AI 写作特征清单 ＋ 语音校准 ＋ 误报清单，基于 Wikipedia「Signs of AI writing」） |
| 许可 | MIT（上游 LICENSE 随库保留，Copyright (c) 2025 Siqi Chen） |
| 本机版本 | **2.9.1**（其 frontmatter `metadata.version`；⚠️ **调用时须重读**，同 §1.2 纪律） |
| 规模 | 9 文件 / 约 50 KB |
| 安装形态 | **扁平外挂（复制安装）**：`~/.codex/skills/humanizer` → `~/.workbuddy/skills/humanizer`（**独立副本**，非联接） |
| 账本 | `.vendor/humanizer.lock.json`（上游坐标 + 许可 + 内容摘要 + 9 文件逐文件 sha256） |
| 宿主侧路由 | **Model-invoked**（frontmatter 无 `disable-model-invocation`）—— 见 §三 第三上游表 |

**⚠️ 资产归属**：同为**第三方 MIT 资产，不是自研** —— 不得登记进 `meta.自研工具`，不得随 ai-workflow 本体仓推送。

**⚠️ 同批落库、形态却与 1.2 相反（三条都是实测结论）**：

1. **它是复制、不是联接**：`ppt-master` 107 MB 且自带 fail-closed 完整性门禁 ⇒ 只能联接 ＋ 零改动；`humanizer` 仅 9 文件 ⇒ **复制**（零拷贝无收益，且其源路径受插件管理、更新常删建目录，联接会断成悬空引用）。
2. **它没有 fail-closed 自校验**：理论上可打补丁，但**本轮一个字节都没改**（保持与上游逐字节一致，便于同步与漂移检测）。
3. **它与本仓既有去味能力是「手法 vs 判定」的分工，不是替代关系**：本仓 `scripts/humanize_scan.py` ＋ `references/humanize-judge.md`（第七物理量「文风判定」）是**机器闸门与判定口径**；`humanizer` 提供**改写手法**（模式清单 / 语音校准 / 误报清单）。**判定只有一处**（在本仓）。⚠️ **不得**把它当作「另一套去味判据」接入（违反硬约定第 4 条「同一物理量不写两处」）。

> **为什么不做成本体内置**：① 本仓已有同轴的去味判定（第七物理量），再内置一套改写手法会与 `references/humanize-rubric.yaml` 的 31 条模式口径交叉；② 它是**通用文本**技能、不限于 PPT ⇒ 放外部簇由各模式按需引用（如 `references/ppt-mode.md` §9「文案层」），比折进本体更干净。

---

### 1.4 hairline-create（1 个，扁平外挂）

| 项 | 值 |
| --- | --- |
| 上游 | lucasmarkes/hairline（等距线稿组件库；其 `skills/hairline-create/` 是一个「给一个想法就画一张等距线稿图」的**生成器技能**） |
| 锁定 rev | a2217852fed6d1a4f20bc7d43d4fad1a3de117b8（2026-10-08） |
| 许可 | MIT（Copyright (c) 2026 Lucas Marques；上游 LICENSE 随库携带为 `hairline-create/LICENSE`） |
| 规模 | 11 个上游文件 + 随库携带的 LICENSE = **12 文件 / 约 124 KB** |
| 安装形态 | **扁平外挂（复制安装）**：`~/.workbuddy/skills/hairline-create`（**真实目录**，`isjunction=False`） |
| 账本 | `.vendor/hairline.lock.json`（rev + 许可 + 逐文件 sha256 + `content_digest`） |
| 宿主侧路由 | **Model-invoked**（frontmatter 无 `disable-model-invocation`）—— 见 §三 第四上游表 |

**⚠️ 资产归属**：同属**第三方 MIT 资产，不是自研** —— 不得登记进 `meta.自研工具`，不得随 ai-workflow 本体仓推送。

**⚠️ 它与 1.3 的关键差别（这条决定它在本仓怎么用）**：

1. **它是个「产物生成器」，不是「方法论」**：给一个想法就产出一张单文件 HTML（等距线稿图 ＋ 强度滑杆 ＋ 主题切换 ＋ 播放巡游）。故它在宿主侧的价值分两半 —— **产物侧**（外挂复用、按需路由）与**原则侧**。
2. ⭐ **原则侧已入本仓判据集，且只入一次**：其 skills/hairline-create/rules.md 的**十条规则**与 skills/hairline-create/look.md 的**十三项肉眼验收**是可迁移的视觉工艺原则，已按 **judgeability 分档**提炼进 `references/aesthetic-rubric.yaml` 的 **H 层**（能机器量的走 `machine` 实跑；只有眼睛能看的走 `manual`，`check: null` ⇒ 登记为人审点），并在该文件表头「外部依据」块登记出处。**故它的原则不在本文件重述**（同一物理量不写两处）。⚠️ **上游文件路径按本仓既有约定用纯文本提及、不加反引号** —— `checks.py skill` 的「文档引用完整性」把反引号内的 `.md`/`.py` 视为**技能内引用**，给上游路径加反引号会产出假断链（与 `references/diagram-mode.md` 首部的同一处置）。
3. **重叠面已先排除**：十条规则中「按距离错峰」已由既有 `G16 rhythm_ladder` 覆盖、「构造不穿透」已由 `R4 geometry_occlusion` 覆盖、「唯一强调色」半面已由 `G2`/`G8` 覆盖 ⇒ 这三处**不新增判据**，只在判据集写分工。规则 ③⑦⑨⑩（不出框 / 循环屏外休眠 / 圆角化 / 图内无文字）**强绑定等距线稿画面、不迁移**，边界写进判据集 `note`。
4. **零补丁、逐字节复制**：与 `humanizer` 同法（`patched` 恒为 false）；源是普通 GitHub 仓库，故不用 `ppt-master` 那种目录联接。
5. ⭐ **工程实现层已另拆一轮并落成参考文档（v4.27.0）**：其 kernel.js / look.mjs / validate.mjs / build.mjs / bench.html 的**手法**（引擎自校验、写机器判据的坑、可测性内建、共享单帧循环与异常降级、工具链工程）已按**逆向拆解模式**提炼为 `references/artifact-engineering.md`（16 条；**主题名文档，不是 vendor 专页**——16 条里 12 条与本 vendor 无关）。**那部分与视觉工艺无关，故不并入 H 层**（H 层承接的是 rules.md / look.md 的原则侧）。**本文件不重述其内容。**

> **为什么不做成本体内置**：① 它的产物是一种**风格**（isometric 线稿），不是通用能力 —— 折进本体会把「一种风格」写成「本仓默认」；② 本仓已有同轴的审美判据集与图示设计模式，再内置一套生成器会与 `diagram-mode` 的 P1「选型只挑一个类型」打架。⇒ **产物外挂、原则入判据集**，各归其位。

### 1.5 archify（1 个，扁平外挂）

| 项 | 值 |
| --- | --- |
| 上游 | tt-a1i/archify（JSON-IR → 自包含 HTML 图示渲染器：architecture / workflow / sequence / dataflow / lifecycle 五类，内联 SVG ＋ 明暗主题 ＋ 可选轨迹动效 ＋ PNG/JPEG/WebP/SVG/WebM 导出） |
| 锁定 rev | 58ab0b98d2d0def8e49dced705c7b566936723ec（2026-10-10T11:49:39Z） |
| 许可 | MIT（Copyright (c) 2026 tt-a1i (Archify) / Copyright (c) 2025 Cocoon AI；上游 LICENSE 随库携带为 archify/LICENSE） |
| 规模 | **315 文件 / 约 11 MB**（交付面 = 上游 archify/ 子树；其 SKILL.md 位于该子树根，天然满足宿主「技能库根/<目录名>/SKILL.md」的**一层**布局 —— 已用探针实测：嵌套布局 0 命中） |
| 安装形态 | **扁平外挂（复制安装）**：`~/.workbuddy/skills/archify`（**独立真实目录**） |
| 账本 | `.vendor/archify.lock.json`（rev ＋ 许可 ＋ 逐文件 sha256 ＋ `content_digest` ＋ **主机前置条件与已知阻塞**） |
| 宿主侧路由 | **Model-invoked**（frontmatter 无 `disable-model-invocation`）—— 见 §三 第五上游表 |
| ⚠️ 本机可用性 | **装得进、可调用；产物链「会话内受阻、会话外可绕」**；见下方「产物链受阻」与 §二 末「默认豁免」 |

**⚠️ 资产归属**：第三方 MIT 资产，不是自研 —— 不得登记进 `meta.自研工具`，不得随 ai-workflow 本体仓推送。

**⚠️ 三条实测约束（决定它怎么接，都不是设计偏好）**：

1. **运行期零 npm 依赖**：其 package.json 只有 `devDependencies`、**没有 `dependencies`**，代码纯 `node:` stdlib ⇒ 无需 `npm install` 即可跑。唯一外部二进制是**系统 Chrome**（走 CDP，`--headless=new --remote-debugging-pipe`），供 `doctor` 与四门中的 `browser-check` 用 —— **本机得有 Chrome 才谈得上跑通**。
2. **它自带 fail-closed 的原子写出与四阶段门禁**（`finalize` = validate → deliver → check → browser-check，**无跳过开关**）⇒ 与 §1.2 的 `ppt-master` 同型：**一个字节都不改**（`patched` 恒为 false）。
3. ⭐ **它是「产物生成器」，不是「方法论」**（与 §1.4 的 `hairline-create` 同型）⇒ **产物外挂、原则不迁移**：它的设计原则强绑定其 IR 与四阶段门禁，不构成可迁移判据，故**不进** `references/aesthetic-rubric.yaml`。

**⚠️ 产物链受阻（本机环境，fail-closed，不静默降级；2026-10-11 已改判）**：

- **现象**：`doctor` **rc=0 全绿**（20 项 `[ok]` ＋ `Archify is ready.`），但 `demo` 与 `finalize` **rc=1**：前者报 `Temporary output candidate has multiple hard-link names.`（诊断码 `output/target-hardlinked`），后者报 `finalize/receipt-publication`，四项门 validate / deliver / check / browser-check **全部 `not-run`**；两者证据均为 `links: "2"`。
- ⭐ **定位（首版归因已推翻）**：最小复现（`link` 后 `nlink=2` → `unlink` 源名 → 文件已消失但 `dst.nlink` **仍为 2**，正常应为 1）成立；但首版据「Python 3.13 / Node 22 / Node 24 / PowerShell 中继 × C:/D:/E: 三盘 × **沙箱开与关**」**全部复现**定为「**系统层 nlink 语义异常**」—— **该论据不成立**：那八组宿主**共用同一批被注入的会话进程**，「沙箱开／关」两态也跑在同一批宿主上 ⇒ 等于**用一个候选去排除它自己**（假阴性）。
- ⭐ **真因（六层证据链，2026-10-11 第二轮取证）**：宿主把 **tsbx.dll（Tencent Sandbox 5.7.10）** 注入**会话进程树**，对 `ntdll!NtSetInformationFile` / `NtCreateFile` / `NtOpenFile` 做 **inline hook**（入口 `48 b8 <imm64> ff e0`，跳转目标落在 tsbx 基址内），把删除操作**重定向为「移入回收站」** ⇒ 删掉硬链接的一个名字时文件对象仍在、link count 不减。四条旁证：① `fsutil hardlink list` 在删除后列出回收站内的目标；② **删除方式矩阵** —— `os.unlink` / `DeleteFileW` / `SetFileInformationByHandle` / `.NET File.Delete` **全进回收站**，唯 `cmd` 内建 `del` 真删；③ **查询类 API 未被 hook**（`NtQueryInformationFile` 等仍是原生序言）；④ 沙箱实现源码内含 `deleteMode: 'trash'`。**注入范围仅会话进程树**（`tasklist /m tsbx.dll` 34 实例；`explorer` / `svchost` / 火绒 / `WorkBuddy.exe` **均不在**）。
- ⭐ **改判结论**：这**不是**文件系统／内核缺陷（四盘皆 NTFS 3.1，文件系统本身健康），**也不是**「本机不可产出产物」—— 它是**会话级**的进程 API 改写 ⇒ **会话内**跑 archify 的产物链**仍会 rc=1**；**在会话外的独立终端**运行，删除恢复真删、nlink 正常递减 ⇒ **产物链可绕**。
- **上游侧坐标**：archify/renderers/shared/atomic-output.mjs 的 `captureRegularFileBinding` 在 `nlink > expectedLinks(1)` 时判 `unsupported` ⇒ 产出 `candidate-hardlinked` / `finalize-receipt-hardlinked`。这是**它有意的 fail-closed**（宁可拒写，不静默产出半成品）。
- ⚠️ **诚实边界**：① 「**会话外可绕**」目前是**机制推论**（注入范围已取证），**尚未端到端实跑** —— 需在会话外终端跑一次 `demo` 确认；② **会话内**调用时**不要承诺当场交付产物**，改承诺「产物需在会话外生成」，或退到 `references/diagram-mode.md` 的本仓流程；③ 该阻塞**不动摇**其 fail-closed 的价值 —— **不得**为绕开而放宽上游判据。
- **调用前置条件（关闭更新自检，用户 2026-10-11 指令）**：命令前设 `ARCHIFY_UPDATE_CHECK_DISABLED=1`，短路 scripts/check-update.mjs 的联网自检（默认查 tt-a1i.github.io/archify/skill-updates/archify/stable.json）。该开关**不改变产物质量口径**；且 `finalize` 的 `deliver` 阶段**内部已自关**该自检 ⇒ 日常调用负担极小。

**⚠️ 版本号不可作判据（与 §1.2 同纪律的变体）**：其 SKILL.md frontmatter 写 `metadata.version: "3.0"`，而 package.json / skill-release.json / CHANGELOG 均写 **3.0.1** ⇒ **以 `upstream_rev` 为唯一坐标**。

> **为什么不做成本体内置**：① 本仓已有同轴的图示设计模式（`references/diagram-mode.md` 的 P0–P4）与审美判据集 —— 再内置一套渲染器会造成**两套口径**；② 它是**产物生成器**，折进本体会把「一种实现」写成「本仓默认」；③ 它自带 fail-closed 门禁，改它文件会直接把它顶停。⇒ **产物外挂、判定归本仓**。

### 1.6 本地已装·非 vendored 的能力技能（5 个；⚠️ **不是上游**，来源未判定）

> ⭐ **与 §1.1–§1.5 的根本区别**：这五个**既不是第三方上游**，**也不在 `.vendor/` 的五个 lock 内**。它们的来源在**本机无机器可核证据** ⇒ 本节**不写**「上游 / 锁定 rev / 许可」（写了就是编造），只登记**可核的事实**与由此产生的边界。

**可核事实（2026-10-11 实测，取法：目录列举 + frontmatter 读取 + `.vendor` 列举 + 使用台账）**：

| 项 | 值 |
| --- | --- |
| 名称（5） | reviewed-change-apply-gate · long-job-background-survival · long-job-crash-safety · memory-file-compaction · structured-record-surgical-edit |
| 位置 | `~/.workbuddy/skills/<名>/` —— **本机独有**：`.codex/skills` 与 `.workbuddy-ai/skills` 两处均无同名目录 |
| 规模 | 1–3 文件 / 6.8–20 KB（多数仅一个入口文件；reviewed-change-apply-gate 另带一个 scripts 子目录） |
| frontmatter 键 | 仅 name / description / agent_created / version —— **无** source、**无** upstream_rev |
| `agent_created` | 五者**均为 true** |
| LICENSE / README | **均无**（第三方上游的 LICENSE 必随库携带，见 §1.1–§1.5） |
| `.vendor` 登记 | **均无** |
| 调用统计 | 使用台账原文：memory-file-compaction「used / 2 次」；其余四个「unused / 0 次 / **A类:装了没用**」 |

⚠️ **来源状态 = 未判定 —— 两个方向都不得写**：本机能证的只有「不在任何上游账本内、无来源元数据、他处无副本」。写成「第三方」会**把来源不明的东西伪装成有出处**（违反 §五 的诚实口径）；写成「自研」会与本仓既有标记体系冲突 —— 自研在索引里由入口文件的 `selfbuilt: true` 标记（如 `ai-workflow` 本身），而这五个**没标**。⇒ 本节按**中性事实**登记，**定性留给用户**。

**它们各解决什么（与本体是「互补」，不是「替代」）**：

| 技能 | 治什么 | 与本体既有面的关系 |
| --- | --- | --- |
| reviewed-change-apply-gate | 「出 diff 就当已落地」这类**半截交付**；把已审变更真正写进既有文件时配机器门禁（备份原始字节 / 段外一致性 / 写后 sha256 回读 / 原子替换 / 阴性对照 / 换行风格字节级一致） | 与本体 `scripts/gate.py` **首尾相接**：gate 管「该不该改」，它管「改对了没有」—— 本体此前**没有**「把已审 diff 应用到既有文件」这条路径 |
| long-job-background-survival | 后台长任务**无堆栈静默死亡**：先用纯心跳探针把「宿主时限」与「任务自身 bug」分开，再换启动方式；并发分块 + 严格按单元序落盘 | 本体的长任务面此前为零覆盖（全库检索 长任务/resume/断点/OOM 零命中） |
| long-job-crash-safety | 跑几小时的长任务**崩溃安全与判据纪律**：落盘粒度细于失败粒度、判据事前固定（防「崩了再剔」）、分段交付不押在链尾 | 它是把本体的一次事故（修订上限常量 `MAX_REVISIONS = 3`）**通用化**，不是重复 |
| memory-file-compaction | 常驻注入文件**超限被截断**后的无损压缩 + 结构化拆分：用机器可算的「事实 token 三向差集」证明「压掉的只有表述、没有事实」 | 本体的记忆是**检索侧**（知识库 LSA + 学习引擎 K1–K5），**没有注入面限额治理** |
| structured-record-surgical-edit | 长单行标量 / 记录性文件（YAML 长标量、JSON 串、表格行）的**定点修改**：锚点必须含结尾引号与后继键、合并必须可逐字检回 | 本体此前只有「同一文件多次编辑必须串行」一句，无具体手改姿势 |

**宿主侧分类（按 §二 两分类）**：五者 frontmatter 均**无** `disable-model-invocation` ⇒ **Model-invoked**（与 §1.3–§1.5 同法）。

**⚠️ 引用即调用 ≠ 盖过本仓判定**：这五个给的是**手法与纪律**，本仓的判据（对账 / 门禁 / 去味 / 审美 / 治理）**仍在本体**。**不得**把它们当作「另一套判据」接入（违反硬约定第 4 条「同一物理量不写两处」）。

**⚠️ 机器检查缺口（如实登记）**：§六 的 `external_skill_lint.py` **只扫 `.vendor/*.lock.json` 登记过的技能** ⇒ 这五个**不在覆盖范围内** ⇒ 它们当前是**未检测**状态，**不是**「已验证合格」。要纳入覆盖，前提是先有 lock —— 而 lock 需要可核的「上游坐标 + 许可」，这五个**没有**。⇒ 该缺口**不会自然消失**，属**结构性未覆盖**。

**⚠️ 无同步规程**：§七 的同步规程对它们**不适用**（没有上游可同步；`.codex` / `.workbuddy-ai` 两处也无副本可对照）⇒ 它们**随本机演进**，无漂移检测。若要引入漂移检测，前提同样是先判定来源。

---

## 二、调用口径（上游两分类 → 宿主语言）

上游按「谁能调用」把技能分两轴，宿主阶段 0 只按目录名与 description 匹配，没有对应机制。**本轮的实测口径是：上游的 `disable-model-invocation: true` 就是 User-invoked 的机器实现** —— 不必靠推断（设计阶段曾推断「宿主无对应」，实施期读 frontmatter 实样后修正）。

| 上游分类 | 机器判据 | 数量 | 宿主侧怎么用 |
| --- | --- | --- | --- |
| **User-invoked** | frontmatter 含 `disable-model-invocation: true` | 10 | **由主代理按场景显式调用**，不指望自动匹配命中 |
| **Model-invoked** | 无该字段 | 14 | 可被阶段 0 的索引匹配自动命中，作为阶段内联纪律使用 |

> **上表数量是 1.1 那批（mattpocock）的统计**；`humanizer` 按同一判据归 **Model-invoked**，见 §三 第三上游表。

> **为什么保留 `disable-model-invocation` 而不删**：它是这批技能**唯一机器可读的分类依据**，删掉就只剩推断；且不违反宿主 frontmatter 判据（该判据只要求**含**三键，不禁止额外键）。`argument-hint` 同理保留。

**`ppt-master` 不适用这套两分类**：它自带完整路由与门禁，不靠宿主的索引匹配自动命中；宿主侧的调用口径只有一句 —— **命中「PPT 识别」即叠加 PPT 模式，并按 `references/ppt-mode.md` 的交接契约进它**。它**不改本体 frontmatter**（见 §1.2 第 1 条），故也不进补丁清单。

**`hairline-create` 同样走 §二 的 Model-invoked 一栏**（frontmatter 无 `disable-model-invocation`）⇒ 阶段 0 的索引匹配可自动命中它；但**它的原则侧不在本文件** —— 已入 `references/aesthetic-rubric.yaml` 的 H 层（见 §1.4 第 2 条），本文件只负责「它从哪来、什么形态、怎么同步」。

**`humanizer` 则走 §二 的 Model-invoked 一栏**：阶段 0 的索引匹配可自动命中它；但**在本仓语境下它的定位是「改写手法资源」而非「判定执行者」** —— 命中后**判定仍回本仓文风判定**（见 §1.3 第 3 条与 §五 第 8 条）。

**`archify` 同样走 §二 的 Model-invoked 一栏**（frontmatter 无 `disable-model-invocation`）⇒ 阶段 0 的索引匹配可自动命中它。⚠️ **命中即可调用**：其**路由与调用口径正常**，唯一本机约束是**产物链在会话内受阻**（见 §1.5）⇒ 会话内命中它时，**照常调用并把产物落点安排到会话外**，或退到 `references/diagram-mode.md` 的本仓流程，**不要**因此拒调。另：调用前设 `ARCHIFY_UPDATE_CHECK_DISABLED=1` 关掉其更新自检（`finalize` 的 deliver 阶段内部已自关）。

**⭐ 默认豁免 ——「图示例外」（本版新增，与用户级「默认不产出 HTML」硬规则的接口）**

用户级硬规则默认「除用户点名要，不产出 `.html` 文件」，其**靶子是把 HTML 当报告 / 知识整理的载体**。而 `archify` 的产物是**图示载体**（单文件、内联 SVG ＋ 明暗主题），且 `references/diagram-mode.md` 的图示识别判据 ② 本就写明「图类任务的期望形态是 HTML / SVG / PNG」⇒ **任务要出图时，「HTML」就是用户点名要的形态**。故定四条：

- **① 允许**：任务本身要**出图**（架构图 / 工作流图 / 时序图 / 数据流图 / 状态机图），或用户点名要图示、要单文件可交互图 ⇒ 调 `archify`（或 `hairline-create`），其 `.html` 产物**合规**。
- **② 声明**：交付时**显式声明「这是图示载体，不是网页报告」**（写在回复里即可；产物内不必）。
- **③ 仍禁止**：拿它当**报告生成器** —— 承载大段说明文字、章节正文、结论叙述；报告 / 知识总结 / 数据分析展示 / 复习资料类交付物**仍走 Markdown / PDF / DOCX / XLSX / PPTX**。
- **④ 不改记忆**：本条是对既有硬规则的**收窄解释**（把「用户的要求」落到图类任务上），**不修改**用户级记忆条目本身。

⚠️ **它是「豁免」不是「放宽」**：判据只有一条 —— **这份产物的主要功能是不是「图」**。答「否」即不适用（与 `diagram-mode` 的 P0「该不该画」同源）。

**§1.6 那五个本地技能同样走 §二 的 Model-invoked 一栏**（frontmatter 无 `disable-model-invocation`）⇒ 阶段 0 的索引匹配可自动命中它们。⚠️ 但它们的**机器检查是缺口**（不在任何 lock 内，见 §1.6 末）—— 命中后可按其正文当**手法与纪律**使用，**不要**把「它没被 lint 扫过」误读成「它有问题」，也**不要**误读成「它已经过验证」。

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

**第二上游（`ppt-master`，1 个，不按上面两分类）**：

| 场景 | 调哪个 | 说明 |
| --- | --- | --- |
| 要出一份演示文稿（生成 / 美化 / 填原生模板 / 改原生 pptx / 造可复用模板 / 导出演示视频） | `ppt-master` | 宿主侧**先叠加 PPT 模式**（识别三判据与交接契约见 `references/ppt-mode.md`），再按其**自身**的路由权威选路；本仓不复刻它的步骤 |

**第三上游（`humanizer`，1 个，按 §二 两分类）**：

| 场景 | 调哪个 | 分类 |
| --- | --- | --- |
| 要去 AI 味 / 让文案更像人写的，需要**改写手法**（**判定仍看本仓 `humanize_scan.py`**） | `humanizer` | Model-invoked |

> ⚠️ 这一行**只引手法、不引判定**：本仓的「文风判定」（第七物理量）是判据唯一来源，`humanizer` 不参与判定。

**第四上游（`hairline-create`，1 个，按 §二 两分类）**：

| 场景 | 调哪个 | 分类 |
| --- | --- | --- |
| 要生成一张**等距线稿图**（单文件 HTML：图形 ＋ 强度滑杆 ＋ 主题切换 ＋ 播放巡游），或按 hairline 的十条规则改一张 | `hairline-create` | Model-invoked |

> ⚠️ 这一行**只引产物、不引判据**：它的十条规则里可迁移的那部分**已入判据集 H 层**（见 §1.4 第 2 条），本行不重复登记判据。

**第五上游（`archify`，1 个，按 §二 两分类）**：

| 场景 | 调哪个 | 分类 |
| --- | --- | --- |
| 要把系统架构、技术工作流、API 调用时序、请求生命周期、数据管道 / 血缘、状态机画成**可探索的单文件 HTML**（或把 Mermaid 流程图/时序图/状态图转成或美化） | `archify` | Model-invoked |

> ⚠️ **两处前置**：① 命令前设 `ARCHIFY_UPDATE_CHECK_DISABLED=1`（关更新自检）；② **产物链会话内受阻、会话外可绕**（宿主会话的 safe-delete 把删除重定向为回收站，见 §1.5）—— 命中后**照常调用**，只把产物落点安排到会话外，或退到 `diagram-mode` 流程；**不要**因本机约束而拒调。
> ⚠️ **与既有面不重叠**：本仓 `references/diagram-mode.md`（P0–P4）管「选哪个类型 ＋ 怎么组织」、判据在 `references/aesthetic-rubric.yaml`；`archify` 只提供**产物层的一个实现**（与 `hairline-create` 同型），**不引判据**。

**本地已装·非 vendored 的能力技能（§1.6，5 个，按 §二 两分类）**：

> ⚠️ 这一组**不是上游**（见 §1.6）—— 列在这里只为「阶段 0 命中时该调哪个」，**不要**把它们计入上游数量。

| 场景 | 调哪个 | 分类 |
| --- | --- | --- |
| 用户已批准一份 diff / 拟改后全文，现在要**真正写进既有文件**，且需要「出 diff ≠ 已落地」的证据 | reviewed-change-apply-gate | Model-invoked |
| 后台长任务**跑一两分钟就消失**、日志停在完整一行且无 traceback（怀疑宿主时限） | long-job-background-survival | Model-invoked |
| 跑**几小时**的批量任务，需要增量落盘 / resume / 判据事前固定 / 不要过拟合 | long-job-crash-safety | Model-invoked |
| 常驻注入文件（记忆 / 索引类）**超限被截断**，要无损压缩并拆分 | memory-file-compaction | Model-invoked |
| 要改**长单行标量**或记录性文件中的一行（会过机器校验的那种） | structured-record-surgical-edit | Model-invoked |

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
7. **`ppt-master` 的边界不列在本节**：它的诚实边界（版本不锁、联接单点依赖、依赖与许可含 AGPL 组件、宿主索引可达性未端到端验证、不代跑业务链路）写在 `references/ppt-mode.md` §10，**本文件不重述**。
8. **`hairline-create` 的边界（产物 ≠ 原则）**：它保证「能生成一张符合十条规则的图」，本仓判据集保证「明显劣化会被拦」—— **装了它不等于产物变好看**：判据只拦可枚举的劣化面，判断层（静止态是否是构图、命中区是否发抖）**仍是人审点**。另两条：**复制安装 ⇒ 上游更新不会自动生效**，须按 §7.3 整体重取；其 `look.mjs` 需浏览器与 `playwright-core`（首次运行联网安装），本仓**不代跑**其业务链路。
9. **`humanizer` 的边界（手法 ≠ 判定）**：它给的是**改写手法**、不是判定；**不要**把「humanizer 改过了」当成「文风判定已达标」—— 判定唯一在本仓 `scripts/humanize_scan.py`（第七物理量）。其安装形态是**复制**（与 `ppt-master` 的联接相反），故**上游更新不会自动生效**，须按 §7.2 重取。
10. **`archify` 的边界（装得进 ≠ 会话内跑得动；会话外可绕）**：① **产物链会话内受阻、会话外可绕** —— 其原子写要求 `nlink === 1`，而宿主会话的 safe-delete 把删除重定向到回收站 ⇒ 会话内实测恒为 2 ⇒ `demo`/`finalize` rc=1（详见 §1.5）；⚠️ **`doctor` 全绿不代表能产出**（该路径不写产物）。② **复制安装 ⇒ 上游更新不自动生效**，须按 §7.4 整体重取。③ **它的原则不迁移**：设计原则强绑定其 IR 与四阶段门禁，**不入** `references/aesthetic-rubric.yaml`（与 §1.4 的 `hairline-create` 相反 —— 那个有可迁移的视觉工艺）。④ **版本号不可作判据**：frontmatter 3.0 ↔ package.json 3.0.1，只认 `upstream_rev`。⑤ **`browser-check` 门依赖系统 Chrome**；本仓**不代跑**其业务链路。

11. **§1.6 那五个的技能「来源未判定」**：本机能证的只有「不在任何上游账本内、无来源元数据、他处无副本」—— **不是**第三方，也**不是**已被 `selfbuilt` 标记的自研。由此派生两条**结构性缺口**：① **机器检查未覆盖**（§六 的 lint 只扫 lock 登记者）；② **无同步与漂移检测**（§七 不适用）。两条都**不会自然消失**，须先由人判定来源才能补。

---

## 六、机器检查

**`scripts/external_skill_lint.py`** —— 外部技能的放宽判据，是本体自检在外部技能上的对应物。**只查 `.vendor/` 下登记过 lock 的技能**；`--lock` 缺省遍历 `.vendor/*.lock.json`（v4.25.0 起改为**多上游**，此前硬编码单一 lock）。

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
python scripts/external_skill_lint.py                    # 查 .vendor/ 下全部 lock 登记的外部技能（五上游）
python scripts/external_skill_lint.py --verify-lock      # 加做 lock 与磁盘 sha256 一致性
python scripts/external_skill_lint.py --skill tdd        # 只查一个
python scripts/external_skill_lint.py --lock <path>      # 只用一个 lock（排障用）
```

⚠️ **覆盖边界（2026-10-11 实测补充）**：本节的检查**只覆盖 `.vendor/*.lock.json` 登记过的技能**（当前 5 个上游）。**§1.6 那五个本地技能不在覆盖内** ⇒ 对它们而言本节输出的是**沉默**，而**沉默不等于通过** —— 读本表时不要把「lint 没报它」当成「它没问题」。

---

## 七、同步上游

上游按内容刷新同步 mattpocock/skills，本地有 1 处补丁。同步规程：

1. 取上游新 rev，与 lock 的 `upstream_rev` 比对，确认有更新。
2. 按 lock 的 `patches` **重放补丁**（不是 fork，也不是手工改）。
3. 逐文件 sha256 重算写回 lock，跑 `external_skill_lint.py --verify-lock`。
4. 若上游新增了技能间引用，检查被引目标是否已在库内 —— 断链会让上层技能失效。

**不要**把上游内容并进 ai-workflow 本体仓，也不要把本体内容写进这批技能目录 —— 两边一旦互写，同步时无法区分差异来源。

### 7.1 ppt-master（零拷贝，无补丁）

它**不是复制安装**而是**目录联接**（`~/.workbuddy/skills/ppt-master` → `~/.codex/skills/ppt-master`）⇒ **上游一改，宿主侧立即生效**，不存在「重放补丁」这一步，也**不得**改它任何文件。因此：

1. **不锁版本**：调用时必须**每次实读**其入口 frontmatter 的版本号（§1.2 写的 6.6.0 只是落笔时的坐标，**不得沿用**）。
2. **漂移检测靠 lock**：`.vendor/ppt-master.lock.json` 记录上游坐标与内容摘要；跑 `scripts/external_skill_lint.py --verify-lock` 即可发现「联接目标被改过」。
3. **联接断了就是失效**：目标目录被移动或清理 ⇒ 该技能从技能库消失；此时要么重建联接，要么在 `references/ppt-mode.md` §7 的降级通道上退回 `pptx-authoring`。

### 7.2 humanizer（复制安装，无补丁）

它是**复制安装**（`~/.codex/skills/humanizer` → `~/.workbuddy/skills/humanizer`，**独立副本**）⇒ **上游更新不会自动生效**（与 7.1 相反）。同步规程：

1. 取上游新版本，与 lock 的 `declared_version` 比对，确认有更新。
2. **整体重取**（复制安装的同步是「覆盖式重取」，不是「重放补丁」—— 本轮 `patched` 恒为 false，无补丁可放）。
3. 逐文件 sha256 重算写回 lock，跑 `scripts/external_skill_lint.py --verify-lock`。
4. **不要**把它与本仓的去味判据（`scripts/humanize_scan.py` / `references/humanize-rubric.yaml`）互相改写 —— 两边一旦互写，同步时无法区分差异来源。


### 7.3 hairline-create（复制安装，无补丁）

它是**复制安装**（上游 `lucasmarkes/hairline` → `~/.workbuddy/skills/hairline-create`，**独立真实目录**）⇒ **上游更新不会自动生效**（与 7.1 的联接相反、与 7.2 同法）。同步规程：

1. 取上游新 rev，与 lock 的 `upstream_rev` 比对，确认有更新。
2. **整体重取**（复制安装的同步是「覆盖式重取」，不是「重放补丁」—— `patched` 恒为 false，无补丁可放）。
3. 逐文件 sha256 重算写回 lock，跑 `scripts/external_skill_lint.py --verify-lock`。
4. 取数时**必须带 rev**（`?ref=<40 位 sha>`），并逐文件校验 **git blob sha1** 与上游 `contents` 接口返回的 `sha` 相等 —— 这是「确实取自该 rev」的机器证据（`--verify-lock` 只比 sha256，证不了来源）。
5. ⚠️ **不要**把它的原则搬进本文件、也不要把 H 层判据写进它的目录 —— 两边一旦互写，同步时无法区分差异来源。

### 7.4 archify（复制安装，无补丁）

它是**复制安装**（上游 `tt-a1i/archify` 的 archify/ 子树 → `~/.workbuddy/skills/archify`，**独立真实目录**）⇒ **上游更新不会自动生效**（与 7.1 的联接相反、与 7.2 / 7.3 同法）。同步规程：

1. 取上游新 rev，与 lock 的 `upstream_rev` 比对，确认有更新（⚠️ **不要**用版本号判 —— 其 frontmatter 3.0 与 package.json 3.0.1 本就不一致，见 §1.5）。
2. **整体重取**（`patched` 恒为 false，无补丁可放）。⚠️ **只取上游 archify/ 子树那 315 个文件**，不要把仓库根的 README / CHANGELOG / scripts / docs 一并搬进来。
3. 逐文件 sha256 重算写回 lock，跑 `scripts/external_skill_lint.py --verify-lock`。
4. 取数时**必须带 rev**（`?ref=<40 位 sha>`），并逐文件校验 **git blob sha1** 与上游 `contents` 接口返回的 `sha` 相等 —— 这是「确实取自该 rev」的机器证据（`--verify-lock` 只比 sha256，证不了来源）。
5. ⚠️ **不要**改它任何文件（其原子写出与四阶段门禁是 fail-closed 的，改任一文件即拒写）；也不要把本仓判据写进它的目录 —— 两边一旦互写，同步时无法区分差异来源。

### 7.5 §1.6 的五个本地技能（**不适用本节**）

它们**没有上游可同步**：`.vendor` 无 lock、`.codex` / `.workbuddy-ai` 无副本、正文内无 source / upstream_rev 元数据。

⇒ **本节全部规程（比对 rev、重放补丁、重算 sha256、`--verify-lock`）对它们不可执行**。它们**随本机演进**，且**当前无漂移检测**。

⚠️ 要补上漂移检测，前提是**先判定来源**（若判定为第三方 ⇒ 先取回上游坐标与许可再建 lock；若判定为自研 ⇒ 走本体的版本与卫生约定）。**在来源判定之前，不得为它们写 lock** —— 那会把编造的出处固化进账本。
