"""s4：diagram-mode.md 接线（分界表 / 重叠处置表 / 诚实边界 / 首部坐标）。"""
from pathlib import Path

F = Path(__file__).resolve().parents[2] / "references" / "diagram-mode.md"
text = F.read_text(encoding="utf-8")

PAIRS = [
    # A 首部「机制来源与坐标」补一句：该上游已整体接入
    ("与十四份 ADR（docs/adr/0001–0014）。",
     "与十四份 ADR（docs/adr/0001–0014）。⚠️ **v4.33.0 起该上游已作为外部技能整体接入**（接入钉的 rev 为 7a2e22170ee838e859d8142ba825d83f8b6375e6，见 `references/external-skills.md` §1.7）—— 本页提炼的是**产出结构**（当时钉的 rev 为 d1376371965f513d99cc9ec388835d255c5c88d5），两者**不冲突**：**本页是契约层、技能是引擎层**。"),

    # B §1 分界表：科研模式那一行
    ("| 「从选题到投稿做一项研究」 | **科研模式**（R0–R6 七阶段）；其中**数据图**交外部数据图技能（如 `scipilot-figure-skill`），**示意 / 架构 / 时序 / 流程 / 看板 / 象限图**归本模式（见科研模式 N6） |",
     "| 「从选题到投稿做一项研究」 | **科研模式**（R0–R6 七阶段）；其中**数据图**与**示意图**均交**已接入的**外部技能 `diagram-design`，示意图**另叠本模式**（P0–P4 契约层）（见科研模式 §7.11） |"),

    # C §8 重叠处置表加一行
    ("| **`outbound-publish-guard`** | 不重叠 | 若图要出站，先过该守卫 |\n\n---\n\n## 9. 自检 8 项（纪律项，**机器不校验**）",
     "| **`outbound-publish-guard`** | 不重叠 | 若图要出站，先过该守卫 |\n"
     "| **外部技能 `diagram-design`**（v4.33.0 起已整体接入，见 `references/external-skills.md` §1.7） | **上下游（契约层 ↔ 引擎层）** | 本模块管**该不该画、画成什么、画到什么密度**（P0–P4 契约层）；它是**引擎层**（44 类型 ＋ 单文件 HTML/SVG 产物 ＋ self_check.py）。**分界**：示意图先过本模块 P0–P4、再交它绘制；**数据图不经本模块**（直接用它，见 `references/research-mode.md` §7.11）。⚠️ 它的 style-guide 阈值是**它自己的设计系统** ⇒ 按 §10 第 4 条**只搬规则、不搬阈值** |\n\n---\n\n## 9. 自检 8 项（纪律项，**机器不校验**）"),

    # D §10 第 4 条补一句
    ("4. **不能把 diagram-design 的审美阈值直接搬进本仓**：它的 `source` 是它自己的设计系统（纸色 / 珊瑚色 / Geist·Instrument Serif 字体）。本仓纪律要求**阈值来自 `source` 字段、非普适真理** ⇒ 只搬**规则**，不搬**阈值**。",
     "4. **不能把 diagram-design 的审美阈值直接搬进本仓**：它的 `source` 是它自己的设计系统（纸色 / 珊瑚色 / Geist·Instrument Serif 字体）。本仓纪律要求**阈值来自 `source` 字段、非普适真理** ⇒ 只搬**规则**，不搬**阈值**。⚠️ **v4.33.0 起该上游已整体接入** —— 接入的是**引擎与产物**，本条的边界**不变**（判据仍只搬规则）。"),
]

for i, (old, new) in enumerate(PAIRS, 1):
    n = text.count(old)
    assert n == 1, f"第 {i} 处命中 {n} 次（应恰 1）: {old[:70]!r}"
    text = text.replace(old, new)

F.write_text(text, encoding="utf-8", newline="\n")

back = F.read_text(encoding="utf-8")
for s in ["§1.7", "7a2e22170ee838e859d8142ba825d83f8b6375e6", "契约层 ↔ 引擎层"]:
    assert s in back, f"缺 {s}"
assert "scipilot-figure-skill" not in back, "旧串 scipilot 仍在"
assert "**机制来源与坐标**" in back
print("diagram-mode 接线完成：4 处")
print("字节数：", len(back.encode("utf-8")))
