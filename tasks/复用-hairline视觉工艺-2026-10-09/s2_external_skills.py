"""s2: references/external-skills.md 由「三上游」泛化为「四上游」并登记 hairline-create。

每处替换都断言「命中恰 1 次」（防 off-by-one 与静默失配）；替换型与插入型的回读断言分开写。
"""
import pathlib
import sys

P = pathlib.Path("references/external-skills.md")
src = P.read_text(encoding="utf-8")
orig_bytes = len(src.encode())
log = []


def sub(old: str, new: str, label: str):
    """在当前累积结果上替换。⚠️ 必须作用于「累积串」而非原始串 ——
    作用于原始串会让每一处编辑都从零开始，前序编辑被静默丢弃（本脚本首版即踩此坑，
    由回读断言抓出）。"""
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"[FAIL] {label}: 期望命中 1 次，实际 {n} 次\n---\n{old[:200]}\n---")
    return s.replace(old, new)


s = src

# --- ① 标题 ---
s = sub("# 外部技能路由与适配（外部技能簇 · 三上游）",
        "# 外部技能路由与适配（外部技能簇 · 四上游）",
        "标题")

# --- ② 定位块：当前上游行 ---
s = sub("> **当前三个上游**：**mattpocock-skills-zh-CN**（24 个，扁平外挂）、**ppt-master**（1 个，目录联接）与 **humanizer**（1 个，扁平外挂）。来源与许可见 §一。",
        "> **当前四个上游**：**mattpocock-skills-zh-CN**（24 个，扁平外挂）、**ppt-master**（1 个，目录联接）、**humanizer**（1 个，扁平外挂）与 **hairline-create**（1 个，扁平外挂）。来源与许可见 §一。",
        "定位块上游行")

# --- ③ 定位块：分工行补一句（原则侧落点） ---
s = sub("> **与「整合方法」的分工**：本文件只讲**装好之后怎么调**（运行时路由）与**来源/许可/安装形态/账本**。",
        "> **与「整合方法」的分工**：本文件只讲**装好之后怎么调**（运行时路由）与**来源/许可/安装形态/账本**。⚠️ **原则侧不在这里**：上游技能若贡献的是**可迁移的视觉工艺原则**，它们入 `references/aesthetic-rubric.yaml`（判据集）而非本文件 —— 本文件只留出处与本文件不重述的声明（见 §1.4 第 2 条）。",
        "定位块分工行")

# --- ④ 版本行 ---
s = sub("> **版本**：3（2026-09-30 建；2026-10-09 首次泛化为两上游并登记 ppt-master，同日二次泛化为三上游并登记 humanizer）",
        "> **版本**：4（2026-09-30 建；2026-10-09 首次泛化为两上游并登记 ppt-master，同日二次泛化为三上游并登记 humanizer，同日三次泛化为四上游并登记 hairline-create）",
        "版本行")

# --- ⑤ §一 标题 ---
s = sub("## 一、三个上游", "## 一、四个上游", "§一 标题")

# --- ⑥ 新增 §1.4（插在 §一 末、§二 之前）---
SEC_14 = """### 1.4 hairline-create（1 个，扁平外挂）

| 项 | 值 |
| --- | --- |
| 上游 | lucasmarkes/hairline（等距线稿组件库；其 `skills/hairline-create/` 是一个「给一个想法就画一张等距线稿图」的**生成器技能**） |
| 锁定 rev | a2217852fed6d1a4f20bc7d43d4fad1a3de117b8（2026-10-08） |
| 许可 | MIT（Copyright (c) 2025 Lucas Markes；上游 LICENSE 随库携带为 `hairline-create/LICENSE`） |
| 规模 | 11 个上游文件 + 随库携带的 LICENSE = **12 文件 / 约 124 KB** |
| 安装形态 | **扁平外挂（复制安装）**：`~/.workbuddy/skills/hairline-create`（**真实目录**，`isjunction=False`） |
| 账本 | `.vendor/hairline.lock.json`（rev + 许可 + 逐文件 sha256 + `content_digest`） |
| 宿主侧路由 | **Model-invoked**（frontmatter 无 `disable-model-invocation`）—— 见 §三 第四上游表 |

**⚠️ 资产归属**：同属**第三方 MIT 资产，不是自研** —— 不得登记进 `meta.自研工具`，不得随 ai-workflow 本体仓推送。

**⚠️ 它与 1.3 的关键差别（这条决定它在本仓怎么用）**：

1. **它是个「产物生成器」，不是「方法论」**：给一个想法就产出一张单文件 HTML（等距线稿图 ＋ 强度滑杆 ＋ 主题切换 ＋ 播放巡游）。故它在宿主侧的价值分两半 —— **产物侧**（外挂复用、按需路由）与**原则侧**。
2. ⭐ **原则侧已入本仓判据集，且只入一次**：其 `rules.md` 的**十条规则**与 `look.md` 的**十三项肉眼验收**是可迁移的视觉工艺原则，已按 **judgeability 分档**提炼进 `references/aesthetic-rubric.yaml` 的 **H 层**（能机器量的走 `machine` 实跑；只有眼睛能看的走 `manual`，`check: null` ⇒ 登记为人审点），并在该文件表头「外部依据」块登记出处。**故它的原则不在本文件重述**（同一物理量不写两处）。
3. **重叠面已先排除**：十条规则中「按距离错峰」已由既有 `G16 rhythm_ladder` 覆盖、「构造不穿透」已由 `R4 geometry_occlusion` 覆盖、「唯一强调色」半面已由 `G2`/`G8` 覆盖 ⇒ 这三处**不新增判据**，只在判据集写分工。规则 ③⑦⑨⑩（不出框 / 循环屏外休眠 / 圆角化 / 图内无文字）**强绑定等距线稿画面、不迁移**，边界写进判据集 `note`。
4. **零补丁、逐字节复制**：与 `humanizer` 同法（`patched` 恒为 false）；源是普通 GitHub 仓库，故不用 `ppt-master` 那种目录联接。

> **为什么不做成本体内置**：① 它的产物是一种**风格**（isometric 线稿），不是通用能力 —— 折进本体会把「一种风格」写成「本仓默认」；② 本仓已有同轴的审美判据集与图示设计模式，再内置一套生成器会与 `diagram-mode` 的 P1「选型只挑一个类型」打架。⇒ **产物外挂、原则入判据集**，各归其位。

---

## 二、调用口径（上游两分类 → 宿主语言）"""
s = sub("## 二、调用口径（上游两分类 → 宿主语言）", SEC_14, "插入 §1.4")

# --- ⑦ §二 末补一句 ---
s = sub("**`humanizer` 则走 §二 的 Model-invoked 一栏**",
        "**`hairline-create` 同样走 §二 的 Model-invoked 一栏**（frontmatter 无 `disable-model-invocation`）⇒ 阶段 0 的索引匹配可自动命中它；但**它的原则侧不在本文件** —— 已入 `references/aesthetic-rubric.yaml` 的 H 层（见 §1.4 第 2 条），本文件只负责「它从哪来、什么形态、怎么同步」。\n\n**`humanizer` 则走 §二 的 Model-invoked 一栏**",
        "§二 补一句")

# --- ⑧ §三 第四上游表 ---
FOURTH = """**第三上游（`humanizer`，1 个，按 §二 两分类）**：

| 场景 | 调哪个 | 分类 |
| --- | --- | --- |
| 要去 AI 味 / 让文案更像人写的，需要**改写手法**（**判定仍看本仓 `humanize_scan.py`**） | `humanizer` | Model-invoked |

> ⚠️ 这一行**只引手法、不引判定**：本仓的「文风判定」（第七物理量）是判据唯一来源，`humanizer` 不参与判定。

**第四上游（`hairline-create`，1 个，按 §二 两分类）**：

| 场景 | 调哪个 | 分类 |
| --- | --- | --- |
| 要生成一张**等距线稿图**（单文件 HTML：图形 ＋ 强度滑杆 ＋ 主题切换 ＋ 播放巡游），或按 hairline 的十条规则改一张 | `hairline-create` | Model-invoked |

> ⚠️ 这一行**只引产物、不引判据**：它的十条规则里可迁移的那部分**已入判据集 H 层**（见 §1.4 第 2 条），本行不重复登记判据。"""
s = sub("""**第三上游（`humanizer`，1 个，按 §二 两分类）**：

| 场景 | 调哪个 | 分类 |
| --- | --- | --- |
| 要去 AI 味 / 让文案更像人写的，需要**改写手法**（**判定仍看本仓 `humanize_scan.py`**） | `humanizer` | Model-invoked |

> ⚠️ 这一行**只引手法、不引判定**：本仓的「文风判定」（第七物理量）是判据唯一来源，`humanizer` 不参与判定。""",
        FOURTH, "§三 第四上游表")

# --- ⑨ §五 新增第 9 条 ---
s = sub("""8. **`humanizer` 的边界（手法 ≠ 判定）**""",
        """8. **`hairline-create` 的边界（产物 ≠ 原则）**：它保证「能生成一张符合十条规则的图」，本仓判据集保证「明显劣化会被拦」—— **装了它不等于产物变好看**：判据只拦可枚举的劣化面，判断层（静止态是否是构图、命中区是否发抖）**仍是人审点**。另两条：**复制安装 ⇒ 上游更新不会自动生效**，须按 §7.3 整体重取；其 `look.mjs` 需浏览器与 `playwright-core`（首次运行联网安装），本仓**不代跑**其业务链路。
9. **`humanizer` 的边界（手法 ≠ 判定）**""",
        "§五 新增第 9 条")

# --- ⑩ §六 用法注释 ---
s = sub("python scripts/external_skill_lint.py                    # 查 .vendor/ 下全部 lock 登记的外部技能（三上游）",
        "python scripts/external_skill_lint.py                    # 查 .vendor/ 下全部 lock 登记的外部技能（四上游）",
        "§六 用法注释")

# --- ⑪ §七 新增 7.3 ---
SEC_73 = """

### 7.3 hairline-create（复制安装，无补丁）

它是**复制安装**（上游 `lucasmarkes/hairline` → `~/.workbuddy/skills/hairline-create`，**独立真实目录**）⇒ **上游更新不会自动生效**（与 7.1 的联接相反、与 7.2 同法）。同步规程：

1. 取上游新 rev，与 lock 的 `upstream_rev` 比对，确认有更新。
2. **整体重取**（复制安装的同步是「覆盖式重取」，不是「重放补丁」—— `patched` 恒为 false，无补丁可放）。
3. 逐文件 sha256 重算写回 lock，跑 `scripts/external_skill_lint.py --verify-lock`。
4. 取数时**必须带 rev**（`?ref=<40 位 sha>`），并逐文件校验 **git blob sha1** 与上游 `contents` 接口返回的 `sha` 相等 —— 这是「确实取自该 rev」的机器证据（`--verify-lock` 只比 sha256，证不了来源）。
5. ⚠️ **不要**把它的原则搬进本文件、也不要把 H 层判据写进它的目录 —— 两边一旦互写，同步时无法区分差异来源。
"""
s = s.rstrip("\n") + "\n" + SEC_73

if s == src:
    raise SystemExit("[FAIL] 无任何改动")

P.write_text(s, encoding="utf-8")
back = P.read_text(encoding="utf-8")

# --- 回读断言：替换型只断「新串在」，不沿用「旧串必须消失」的通式 ---
checks = [
    ("标题四上游", "（外部技能簇 · 四上游）" in back),
    ("当前四个上游", "**当前四个上游**" in back),
    ("§一 四个上游", "## 一、四个上游" in back),
    ("§1.4 已插入", "### 1.4 hairline-create（1 个，扁平外挂）" in back),
    ("§二 补句", "**`hairline-create` 同样走 §二 的 Model-invoked 一栏**" in back),
    ("§三 第四上游表", "**第四上游（`hairline-create`，1 个，按 §二 两分类）**：" in back),
    ("§五 第 9 条", "9. **`humanizer` 的边界（手法 ≠ 判定）**" in back),
    ("§六 四上游", "（四上游）" in back),
    ("§7.3 已插入", "### 7.3 hairline-create（复制安装，无补丁）" in back),
    ("版本 4", "> **版本**：4（" in back),
]
bad = [n for n, ok in checks if not ok]
if bad:
    raise SystemExit(f"[FAIL] 回读断言未过：{bad}")

# 旧串排除：只对「整段替换型」断言
gone = [
    ("旧标题三上游", "（外部技能簇 · 三上游）" not in back),
    ("旧 §一 标题", "## 一、三个上游" not in back),
    ("旧 当前三个上游", "**当前三个上游**" not in back),
    ("旧 版本 3", "> **版本**：3（" not in back),
]
bad2 = [n for n, ok in gone if not ok]
if bad2:
    raise SystemExit(f"[FAIL] 旧串仍在：{bad2}")

print(f"[OK] external-skills.md 四上游化完成：{len(checks)} 项回读断言通过、{len(gone)} 项旧串已清除")
print(f"[INFO] 体量 {orig_bytes} → {len(back.encode())} B（+{len(back.encode()) - orig_bytes}）")
