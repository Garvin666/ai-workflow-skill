"""s6b：修正行尾断言（LF 文件不该要求「裸 LF 数为 0」），幂等续跑 SKILL.md ＋ 补 README / changelog。

⚠️ 教训：上一版断言对 LF 文件套用了 CRLF 的判据（b_lone==0）⇒ LF 文件恒判失败（假 FAIL）。
   正确判据：CRLF 文件 → crlf>0 且 lone==0；LF 文件 → crlf==0。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def patch(rel, pairs):
    p = ROOT / rel
    raw = p.read_bytes()
    crlf = raw.count(b"\r\n") > 0
    lone = raw.count(b"\n") - raw.count(b"\r\n")
    if crlf:
        assert lone == 0, f"{rel} 本身已 MIXED（{lone} 个裸 LF）"
    kind = "CRLF" if crlf else "LF"
    t = raw.decode("utf-8").replace("\r\n", "\n")
    applied = skipped = 0
    for i, (o, n) in enumerate(pairs, 1):
        c = t.count(o)
        if c == 0 and t.count(n) == 1:
            skipped += 1
            continue          # 幂等：上次已应用
        assert c == 1, f"{rel} 第 {i} 处命中 {c} 次（应恰 1；新串命中 {t.count(n)} 次）: {o[:70]!r}"
        t = t.replace(o, n)
        applied += 1
    out = t.replace("\n", "\r\n") if crlf else t
    p.write_bytes(out.encode("utf-8"))
    back = p.read_bytes()
    b_crlf = back.count(b"\r\n")
    b_lone = back.count(b"\n") - b_crlf
    if crlf:
        assert b_crlf > 0 and b_lone == 0, f"{rel} 写后行尾异常"
    else:
        assert b_crlf == 0, f"{rel} 写后行尾异常"
    print(f"{rel}: 新应用 {applied} 处 / 幂等跳过 {skipped} 处，行尾 {kind}（零 MIXED），{len(back)} B")
    return t


S = [
    ("version: 4.32.1", "version: 4.33.0"),
    ("# AI 工作流 v4.32.1", "# AI 工作流 v4.33.0"),
    ("- **外部技能簇**（技能库根下五上游：mattpocock 24 个 ＋ ppt-master ＋ humanizer ＋ hairline-create ＋ archify）命中时",
     "- **外部技能簇**（技能库根下六上游：mattpocock 24 个 ＋ ppt-master ＋ humanizer ＋ hairline-create ＋ archify ＋ diagram-design）命中时"),
    ("| **R5 撰写与绘图** | 论文结构 ＋ **图**（交 `diagram-mode` 或外部数据图技能）＋ **claim–evidence 对齐** | **构造层**（图部分含**可数层**） |",
     "| **R5 撰写与绘图** | 论文结构 ＋ **图**（交 `diagram-mode`（示意图）或**已接入的** `diagram-design`（数据图）；见手册 §7.11）＋ **claim–evidence 对齐** | **构造层**（图部分含**可数层**） |"),
    ("／**N6 图走既有通道**（数据图 → 外部数据图技能；示意 / 架构 / 时序 / 流程 / 看板 / 象限图 → 本仓 `references/diagram-mode.md`，**不新造流程**）。",
     "／**N6 图走既有通道**（**数据图与示意图 → 已接入的** `diagram-design`；示意图**另叠**本仓 `references/diagram-mode.md` 的 P0–P4，**不新造流程**；见手册 §7.11）。"),
    ("一句话检验法）、自检 10 项与诚实边界｜命中科研识别后按需加载",
     "一句话检验法、**科研制图 §7.11**：通道归属（数据图 / 示意图同属已接入的 `diagram-design`）｜ 科研场景→类型映射 ｜ 论文配图八条 RF1–RF8 ｜ 输出拨盘 ｜ 机器自检复用）、自检 10 项与诚实边界｜命中科研识别后按需加载"),
    ("预算档与保真档四类、与既有面的重叠处置、自检 8 项与诚实边界｜命中图示识别后按需加载",
     "预算档与保真档四类、与既有面的重叠处置（**v4.33.0 起含与外部技能 `diagram-design` 的「契约层 ↔ 引擎层」分界**）、自检 8 项与诚实边界｜命中图示识别后按需加载"),
    ("**v4.26.0 起「四上游」、v4.30.0 起「五上游」**）",
     "**v4.26.0 起「四上游」、v4.30.0 起「五上游」、v4.33.0 起「六上游」**）"),
    ("**只作产物层的一个实现、不引判据**，与既有 `diagram-mode` 的分界见该手册 §1.5；",
     "**只作产物层的一个实现、不引判据**，与既有 `diagram-mode` 的分界见该手册 §1.5；**上游六** `diagram-design`（**扁平外挂、复制安装、零补丁**）—— 自包含 HTML ＋ 内联 SVG 的**编辑型图表技能**（44 类型 ＋ 可导出 SVG / PNG），**只作产物层的实现、不引判据**，与既有 `diagram-mode` 的「**契约层 ↔ 引擎层**」分界见该手册 §1.7；"),
    ("⚠️ **五批技能都不属本体**，本文件是它们唯一的宿主侧适配层",
     "⚠️ **六批技能都不属本体**，本文件是它们唯一的宿主侧适配层"),
]
t = patch("SKILL.md", S)
for s in ["version: 4.33.0", "# AI 工作流 v4.33.0", "六上游", "**上游六** `diagram-design`", "六批技能都不属本体", "科研制图 §7.11"]:
    assert s in t, f"SKILL.md 缺 {s}"
print("  SKILL.md 10 处内容复核 OK\n")

R = [
    ("（当前版本 **v4.32.1**）", "（当前版本 **v4.33.0**）"),
    ("**R5 的图走既有通道**（数据图 → 外部数据图技能 / 示意图 → `diagram-mode`），**不新造流程、不安装任何外部技能**。",
     "**R5 的图走既有通道**（数据图与示意图 → **已接入的**外部技能 `diagram-design`；示意图**另叠** `diagram-mode` 的 P0–P4），配图规范见手册 §7.11，**不新造流程**。"),
    ("（v4.16.0 建；**v4.26.0 起「四上游」、v4.30.0 起五上游**）",
     "（v4.16.0 建；**v4.26.0 起「四上游」、v4.30.0 起五上游、v4.33.0 起六上游**）"),
    ("图类任务产 HTML 走该手册 §二「默认豁免（图示例外）」）。机器检查用 `scripts/external_skill_lint.py`（缺省遍历 `.vendor/*.lock.json`），不走本体的 `checks.py skill`。",
     "图类任务产 HTML 走该手册 §二「默认豁免（图示例外）」）；**上游六** `diagram-design`（自包含 HTML ＋ 内联 SVG 的**编辑型图表技能**，44 类型；**扁平外挂、复制安装、零补丁**；只作**产物层的一个实现**、不引判据，与 `diagram-mode` 是「**契约层 ↔ 引擎层**」关系）。机器检查用 `scripts/external_skill_lint.py`（缺省遍历 `.vendor/*.lock.json`），不走本体的 `checks.py skill`。"),
    ("当前 v4.32.1 基线为 **通过 76/76，FAIL=0，SKIP=0，WARN=0**（v4.26.0 ／ v4.27.0 ／ v4.28.0 ／ v4.29.0 ／ v4.30.0 ／ v4.31.0 ／ v4.32.0 亦为 76/76）。",
     "当前 v4.33.0 基线为 **通过 76/76，FAIL=0，SKIP=0，WARN=0**（v4.26.0 ／ v4.27.0 ／ v4.28.0 ／ v4.29.0 ／ v4.30.0 ／ v4.31.0 ／ v4.32.0 ／ v4.32.1 亦为 76/76）。"),
]
t2 = patch("README.md", R)
for s in ["**v4.33.0**", "六上游", "**上游六** `diagram-design`", "v4.32.1 亦为 76/76"]:
    assert s in t2, f"README 缺 {s}"
print("  README 5 处内容复核 OK")
