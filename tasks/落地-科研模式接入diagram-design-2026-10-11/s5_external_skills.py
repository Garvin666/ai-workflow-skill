"""s5：external-skills.md 六上游化 + research-mode 引用编号修正。"""
from pathlib import Path

ES = Path(__file__).resolve().parents[2] / "references" / "external-skills.md"
RM = Path(__file__).resolve().parents[2] / "references" / "research-mode.md"

# ---------- research-mode.md 先修正引用编号（§7.5 → §7.6） ----------
rm = RM.read_text(encoding="utf-8")
old_no = "⇒ 同步按 `references/external-skills.md` §7.5 整体重取。"
new_no = "⇒ 同步按 `references/external-skills.md` §7.6 整体重取。"
assert rm.count(old_no) == 1, f"引用编号锚点命中 {rm.count(old_no)} 次"
rm = rm.replace(old_no, new_no)
RM.write_text(rm, encoding="utf-8", newline="\n")
print("research-mode：§7.5 → §7.6 引用编号已修正")

# ---------- external-skills.md ----------
t = ES.read_text(encoding="utf-8")

SEC17 = """### 1.7 diagram-design（1 个，扁平外挂；**第六上游**）

> ⚠️ **与 §1.6 的区别（本节最易混）**：本节这个**是上游** —— 第三方 MIT 资产、有 `.vendor` lock、可同步；§1.6 那五个**不是上游** —— 来源未判定、无 lock、无同步。两者编号相邻只是**插入顺序**，**不要混为一类**。

| 项 | 值 |
| --- | --- |
| 上游 | cathrynlavery/diagram-design（自包含 HTML ＋ 内联 SVG 的**编辑型图表设计**技能：**44 种图表类型**、语义模式、可蒙皮设计系统、导入 draw.io / Mermaid / Excalidraw、可导出 SVG / PNG） |
| 锁定 rev | 7a2e22170ee838e859d8142ba825d83f8b6375e6（2026-10-10T21:10:13Z；上游**无 release tag**） |
| 许可 | MIT（上游根 LICENSE **随库携带**为 diagram-design/LICENSE） |
| 本机版本 | 2.6（其 SKILL.md frontmatter 的 metadata.version）；⚠️ 插件 manifest 为 **2.6.74** ⇒ **版本号不可作判据**，以 `upstream_rev` 为唯一坐标（与 §1.5 的 archify 同纪律） |
| 规模 | **280 文件 / 约 4.9 MB**（交付面 = 上游 skills/diagram-design/ 子树的 279 文件 ＋ 随库 LICENSE；其中 references/ 62 ＋ assets/ 211 ＋ scripts/ 5） |
| 安装形态 | **扁平外挂（复制安装，非联接）**：`~/.workbuddy/skills/diagram-design`（**独立真实目录**） |
| 账本 | `.vendor/diagram-design.lock.json`（rev ＋ 许可 ＋ 逐文件 sha256 ＋ `content_digest` ＋ **reference_mentions 50 条**） |
| 宿主侧路由 | **Model-invoked**（frontmatter 无 `disable-model-invocation`）—— 见 §三 第六上游表 |

**⚠️ 资产归属**：第三方 MIT 资产，不是自研 —— 不得登记进 `meta.自研工具`，不得随 ai-workflow 本体仓推送。

**⚠️ 三条实测约束（决定它怎么接，都不是设计偏好）**：

1. **交付面自包含、且有「装态降级」**：其 SKILL.md 与 references/ 的自检条分两路 —— 装态走上游的 self_check.py（**本仓已实跑 rc=0**）；仓根门（verify-geometry / verify-motion / lint-skin 等）只在 "From a repository checkout" 时可用。⇒ 那些仓根路径**不属交付面**，其 **50 条**引用已在 lock 的 `reference_mentions` 登记为**豁免**（**豁免 ≠ 已验证**，lint 对该处给 SKIP 并计数）。
2. **它已被本仓「提炼」过一次，但那是产出结构侧**：`references/diagram-mode.md`（v4.20.0，钉 rev d1376371965f513d99cc9ec388835d255c5c88d5）提炼的是它的 **P0–P4 产出结构**（README / semantic-patterns / layout-budget / output-spec / self_check.py / 14 份 ADR）；本次接入的是**引擎与产物**（44 类型 ＋ 单文件 HTML/SVG ＋ self_check.py）。两者**不冲突**：**契约层 vs 引擎层**（分界见 `references/diagram-mode.md` §8）。
3. ⚠️ **默认产物形态是 HTML，但 format 拨盘可取 svg / png** ⇒ 科研 / 投稿场景**不与之冲突**：论文配图默认走 `format=svg`（见 `references/research-mode.md` §7.11）。⚠️ 上游明写**导出是 manual、不得未经要求自行产出导出件**。

> **为什么不做成本体内置、也不并进 diagram-mode.md**：① 本仓 `references/diagram-mode.md` 是**契约层**（该不该画 / 画成什么 / 画到什么密度），把 44 类型的绘制细则折进去会把**契约**写成**手册**；② 它是**产物生成器**（与 §1.4 hairline-create、§1.5 archify 同型）⇒ **产物外挂、契约留本仓**；③ 复制安装便于 `--verify-lock` 漂移检测。

"""

SEC3 = """**第六上游（`diagram-design`，1 个，按 §二 两分类）**：

| 场景 | 调哪个 | 分类 |
| --- | --- | --- |
| 要把「组件 ＋ 连接」「时序 / 消息」「流程 / 分支」「状态机」「数据模型 / ER」「数据流」「层级 / 树」「象限」「甘特」「统计图（bar / line / scatter / heatmap / radar / treemap / sankey 等）」画成**单文件 HTML（内联 SVG）**，或把 draw.io / Mermaid / Excalidraw **改绘**成编辑型图表 | `diagram-design` | Model-invoked |

> ⚠️ **与既有面的分界**：本仓 `references/diagram-mode.md`（P0–P4）是**契约层**，本节这个技能是**引擎层** —— 示意图**先过 P0–P4、再交它绘制**；**数据图不经 P0–P4**（直接用，见 `references/research-mode.md` §7.11）。⚠️ 它的 style-guide 阈值是**它自己的设计系统** ⇒ 承 `diagram-mode` §10 第 4 条**只搬规则、不搬阈值**。

"""

SEC5_12 = """12. **`diagram-design` 的边界（引擎 ≠ 契约；装态降级；默认 HTML）**：① **它只给引擎与产物、不给判据** —— 「该不该画」与像素级审美仍归本仓（`references/diagram-mode.md` ＋ `references/aesthetic-rubric.yaml`），**不得**把它当「另一套图示判据」接入（违反硬约定第 4 条「同一物理量不写两处」）；② **装态降级** —— 仓根门（verify-* 一族 / lint-skin）在本机不可用，只剩 self_check.py ＋ 手动自检，该缺口由 lock 的 `reference_mentions` 登记为**豁免**（≠ 已验证）；③ **默认产物是 HTML**，但 format 拨盘可取 svg / png，且上游明写**导出是 manual、不得自行产出导出件**；④ **复制安装 ⇒ 上游更新不自动生效**，须按 §7.6 整体重取；⑤ **版本号不可作判据**：frontmatter 2.6 ↔ 插件 manifest 2.6.74，只认 `upstream_rev`。

"""

SEC76 = """### 7.6 diagram-design（复制安装，无补丁）

它是**复制安装**（上游 `cathrynlavery/diagram-design` 的 skills/diagram-design/ 子树 ＋ 随库 LICENSE → `~/.workbuddy/skills/diagram-design`，**独立真实目录**，280 文件）⇒ **上游更新不会自动生效**（与 7.1 的联接相反、与 7.2–7.4 同法）。同步规程：

1. 取上游新 rev，与 lock 的 `upstream_rev` 比对，确认有更新（⚠️ **不要**用版本号判 —— frontmatter 2.6 与插件 manifest 2.6.74 本就不一致，见 §1.7）。
2. **整体重取**（`patched` 恒为 false，无补丁可放）。⚠️ **只取上游 skills/diagram-design/ 子树 ＋ 根 LICENSE**，不要把仓库根的 scripts/（verify-* 一族）、commands/、prompts/、docs/、.github/ 一并搬进来 —— 它们**不属于交付面**。
3. 逐文件 sha256 重算写回 lock，跑 `scripts/external_skill_lint.py --verify-lock`。
4. 取数时**必须带 rev**（`?ref=<40 位 sha>`），并逐文件校验 **git blob sha1** 与上游 `contents` 接口返回的 `sha` 相等 —— 这是「确实取自该 rev」的机器证据（`--verify-lock` 只比 sha256，证不了来源）。
5. ⚠️ **不要**改它任何文件；也不要把本仓判据写进它的目录 —— 两边一旦互写，同步时无法区分差异来源。
6. ⚠️ **重取后可能新报 FAIL**：若上游 references 新增了指向**仓根**的引用（verify-* 等），须补进 lock 的 `reference_mentions`，否则会被「引用完整性」判为**未登记断链**。

"""

PAIRS = [
    # 1 标题
    ("# 外部技能路由与适配（外部技能簇 · 五上游）",
     "# 外部技能路由与适配（外部技能簇 · 六上游）"),
    # 2 「当前五个上游」
    ("> **当前五个上游**（§1.1–§1.5）：**mattpocock-skills-zh-CN**（24 个，扁平外挂）、**ppt-master**（1 个，目录联接）、**humanizer**（1 个，扁平外挂）、**hairline-create**（1 个，扁平外挂）与 **archify**（1 个，扁平外挂——⚠️ 本机**装得进、可调用；产物链「会话内受阻、会话外可绕」**，见 §1.5）。来源与许可见 §一。",
     "> **当前六个上游**（§1.1–§1.5 ＋ §1.7）：**mattpocock-skills-zh-CN**（24 个，扁平外挂）、**ppt-master**（1 个，目录联接）、**humanizer**（1 个，扁平外挂）、**hairline-create**（1 个，扁平外挂）、**archify**（1 个，扁平外挂——⚠️ 本机**装得进、可调用；产物链「会话内受阻、会话外可绕」**，见 §1.5）与 **diagram-design**（1 个，扁平外挂；⚠️ 编号在 §1.6 之后但**是上游**，见 §1.7）。来源与许可见 §一。"),
    # 3 版本行尾
    ("并明确「不是上游」的判据与由此产生的机器检查缺口）",
     "并明确「不是上游」的判据与由此产生的机器检查缺口；2026-10-11 六次泛化为**六上游**并登记 **diagram-design**（新增 §1.7 —— ⚠️ 与 §1.6 的「非上游」区分：本节这个**有 lock、可同步**））"),
    # 4 §一 标题
    ("## 一、五个上游", "## 一、六个上游"),
    # 5 §1.6 标题后加区分注（在 §1.6 表头行前插入）
    ("### 1.6 本地已装·非 vendored 的能力技能（5 个；⚠️ **不是上游**，来源未判定）\n",
     "### 1.6 本地已装·非 vendored 的能力技能（5 个；⚠️ **不是上游**，来源未判定）\n\n> ⚠️ **本节五个不是上游**；本簇的**第六上游** `diagram-design` 编号虽在其后（§1.7），但**性质与它们相反**（有 lock、可同步）。\n"),
    # 6 §1.7 插入（§1.6 末尾的 --- 之前）
    ("⇒ 它们**随本机演进**，无漂移检测。若要引入漂移检测，前提同样是先判定来源。\n\n---\n\n## 二、调用口径",
     "⇒ 它们**随本机演进**，无漂移检测。若要引入漂移检测，前提同样是先判定来源。\n\n"
     + SEC17 +
     "---\n\n## 二、调用口径"),
    # 7 §三 第六上游表（插在 §1.6 那组表之后、依赖提示之前）
    ("| 要改**长单行标量**或记录性文件中的一行（会过机器校验的那种） | structured-record-surgical-edit | Model-invoked |\n\n**依赖提示**",
     "| 要改**长单行标量**或记录性文件中的一行（会过机器校验的那种） | structured-record-surgical-edit | Model-invoked |\n\n"
     + SEC3 +
     "**依赖提示**"),
    # 8 §五 第 12 条（插在第 11 条之后）
    ("两条都**不会自然消失**，须先由人判定来源才能补。\n\n---\n\n## 六、机器检查",
     "两条都**不会自然消失**，须先由人判定来源才能补。\n\n"
     + SEC5_12 +
     "---\n\n## 六、机器检查"),
    # 9 §六 注释计数
    ("python scripts/external_skill_lint.py                    # 查 .vendor/ 下全部 lock 登记的外部技能（五上游）",
     "python scripts/external_skill_lint.py                    # 查 .vendor/ 下全部 lock 登记的外部技能（六上游）"),
    # 10 §7.6（插在 7.5 之前，保持 7.5 在末）
    ("### 7.5 §1.6 的五个本地技能（**不适用本节**）",
     SEC76 + "### 7.5 §1.6 的五个本地技能（**不适用本节**）"),
]

for i, (old, new) in enumerate(PAIRS, 1):
    n = t.count(old)
    assert n == 1, f"第 {i} 处命中 {n} 次（应恰 1）: {old[:70]!r}"
    t = t.replace(old, new)

ES.write_text(t, encoding="utf-8", newline="\n")

back = ES.read_text(encoding="utf-8")
for s in ["六上游", "### 1.7 diagram-design", "第六上游（`diagram-design`", "### 7.6 diagram-design", "12. **`diagram-design` 的边界"]:
    assert s in back, f"缺 {s}"
assert "五上游" not in back.replace("六上游", ""), "仍有五上游残留"
print("external-skills 六上游化完成：10 处")
print("字节数：", len(back.encode("utf-8")))
