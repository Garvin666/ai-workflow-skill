"""s6c：changelog 追加 v4.33.0 ＋ SKILL/README 全量 old↔new 双向核验。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def patch(rel, pairs):
    p = ROOT / rel
    raw = p.read_bytes()
    crlf = raw.count(b"\r\n") > 0
    lone = raw.count(b"\n") - raw.count(b"\r\n")
    if crlf:
        assert lone == 0, f"{rel} 本身已 MIXED"
    t = raw.decode("utf-8").replace("\r\n", "\n")
    applied = skipped = 0
    for i, (o, n) in enumerate(pairs, 1):
        c = t.count(o)
        if c == 0 and t.count(n) == 1:
            skipped += 1
            continue
        assert c == 1, f"{rel} 第 {i} 处 old 命中 {c} 次: {o[:60]!r}"
        t = t.replace(o, n)
        applied += 1
    out = t.replace("\n", "\r\n") if crlf else t
    p.write_bytes(out.encode("utf-8"))
    b = p.read_bytes()
    bc, bl = b.count(b"\r\n"), b.count(b"\n") - b.count(b"\r\n")
    if crlf:
        assert bc > 0 and bl == 0
    else:
        assert bc == 0
    print(f"{rel}: 应用 {applied} / 跳过 {skipped}，行尾 {'CRLF' if crlf else 'LF'}，{len(b)} B")
    return t


CH = """> - **v4.33.0（2026-10-11）把第三方图表技能 `diagram-design` 接入「科研模式」的 R5 制图通道（外部技能簇第六上游 ＋ 科研制图契约）**：任务档案 `tasks/落地-科研模式接入diagram-design-2026-10-11/`（技能本体侧）。用户指令：「将 https://github.com/cathrynlavery/diagram-design 应用于 ai-workflow 科研模式中」；三项确认 = ① 接入＋落映射 ② **数据图与示意图都归它** ③ 复制安装。
  - **① 接入（外部技能簇第六上游）**：上游 `cathrynlavery/diagram-design`（MIT，rev **7a2e22170ee838e859d8142ba825d83f8b6375e6**／2026-10-10T21:10:13Z，无 release tag）以**复制安装**落到 `~/.workbuddy/skills/diagram-design` —— 交付面 = 上游 skills/diagram-design/ 子树的 **279 文件 ＋ 随库 LICENSE = 280 文件 / 约 4.9 MB**（references 62 ／ assets 211 ／ scripts 5），`content_digest = db41f86876959896923a6e4ded9f19fdf155a3773b6ea0497afb1c898bc88003`；账本 `~/.workbuddy/skills/.vendor/diagram-design.lock.json`（逐文件 sha256 ＋ **reference_mentions 50 条**）。⚠️ **版本号不可作判据**：SKILL.md frontmatter 写 2.6、插件 manifest 写 2.6.74 ⇒ 只认 `upstream_rev`（与 archify 同纪律）。
  - **② 与既有 `diagram-mode` 的关系（不是重复引入）**：该上游**早已被提炼过一次** —— `references/diagram-mode.md`（v4.20.0，钉 rev d1376371965f513d99cc9ec388835d255c5c88d5）提炼的是它的 **P0–P4 产出结构**；本轮接入的是**引擎与产物**（44 类型 ＋ 单文件 HTML/SVG ＋ self_check.py）。两者**不冲突**：**契约层 vs 引擎层**（分界写进 `diagram-mode.md` §8）。且本轮**替换了一条悬空指路** —— 旧口径的「数据图交外部数据图技能（如 `scipilot-figure-skill`）」在本仓**从未安装**（属「文档写着有、实际没有」）。
  - **③ 科研模式契约（`references/research-mode.md` v4.29.0 → v4.30.0）**：新增 **§7.11「科研制图（R5 展开）」**（8 小节）—— **通道归属修订**（**数据图与示意图同属已接入的 `diagram-design`**，唯一分界线改为「**轴编码数值 ⇒ 数据图／结构编码关系 ⇒ 示意图**」）｜**科研场景→类型映射**（精选 17 行，非 44 全抄）｜**论文配图八条 RF1–RF8**（矢量优先／尺寸按刊定／坐标轴不截断／误差与 n／色觉可达／图注自明／缩放可读／不出装饰性图）｜**输出拨盘**（承上游四拨盘，**Detail 并入 P2**，不新造第二套）｜**机器自检复用**（`diagram-mode` 的 F5 ＋ 上游 self_check.py ＋ 本仓审美判据）｜**与既有面分界**｜**诚实边界 6 条**。**接线 11 处**：§2 R5 行、§6 N6、§7.1 R3/R4/R5 工具行、§7.5 T1/T4、§9 第 5/7/8 条（**第 7 条改判**：分界由「依赖外部自述」改为「按编码方式」；**第 8 条改口径**：由「一个都不安装」改为「只接线、安装已完成」）。
  - **④ 其余接线**：`references/diagram-mode.md` 4 处（首部坐标补接入事实、§1 分界表、§8 重叠处置表新增「外部技能 `diagram-design`」行、§10 第 4 条边界不变声明）；`references/external-skills.md` 10 处（标题与 §一 泛化为**六上游**、新增 **§1.7**、§三 新增第六上游表、§五 新增第 12 条边界、§六 计数、§七 新增 **§7.6 同步规程**）；`SKILL.md` 10 处（frontmatter 与 H1 版本、阶段 0 外部技能簇句、R5 行、N6 句、三处手册索引行）；`README.md` 5 处。
  - **⑤ 机器验收（全部实跑）**：`external_skill_lint.py` 改前 **84 通过 / FAIL=0** → 改后 **87 通过 / FAIL=0 / SKIP=0 / WARN=0**（新增 diagram-design 3 项：frontmatter 可解析 ／ 引用完整性「技能内可解析 49 条；按约定豁免 51 条」／ 无硬编码密钥）；`--verify-lock` **93 通过 / FAIL=0**，其中 `cathrynlavery/diagram-design · 280 个文件逐一对上`；上游 `scripts/self_check.py` 对示例产物**实跑 rc=0**；`checks.py skill` 维持 **76/76 ／ FAIL=0 ／ SKIP=0 ／ WARN=0**（无回归）。⚠️ **首轮 lint 曾 FAIL=1**：新增技能的 49 条引用指向**上游仓根**（verify-* 一族 / commands / prompts），不属交付面 ⇒ 按 `external-skills.md` §五 第 1 条同法登记为**豁免**后才转绿（**豁免 ≠ 已验证**）。
  - **⑥ ⚠️ 诚实边界（不得读成绿）**：① **那些仓根门在装态不可用** —— 上游 SKILL.md 自检条明写 "From a repository checkout …" ⇒ 几何／动效／皮肤等条**退化为手动自检 ＋ 上游 self_check.py**；② **不代跑业务链路**：本轮只保证「装得上 ＋ 被路由到 ＋ lint 绿 ＋ self_check 可跑」，**不保证**任一具体图表在本机已产出过；③ **科研制图契约全是纪律项** —— 无机器判据、不进 §8 的 10 项编号、不新增 plan 字段／judge／脚本；④ **RF5 只给判据不给调色板**（色值在上游 style-guide，且按「只搬规则、不搬阈值」）；⑤ **数据图／示意图分界线是启发式**；⑥ **复制安装 ⇒ 上游更新不自动生效**（同步按 §7.6 整体重取）。
  - **⑦ 未 commit、未 push**（推送属不可逆对外动作，须单独确认；本体走 `push_ontology.py`）。
"""

patch("_archive/changelog.md", [
    ("# 变更日志（ai-workflow 演进台账）\n> - **v4.32.1（2026-10-11）修",
     "# 变更日志（ai-workflow 演进台账）\n" + CH + "\n> - **v4.32.1（2026-10-11）修"),
])

# ---------------- 全量双向核验 ----------------
print("\n=== 全量核验 ===")
S_OLD = ["version: 4.32.1", "# AI 工作流 v4.32.1", "技能库根下五上游", "（交 `diagram-mode` 或外部数据图技能）",
         "数据图 → 外部数据图技能", "一句话检验法）、自检 10 项", "与既有面的重叠处置、自检 8 项",
         "起「五上游」**）", "分界见该手册 §1.5；", "五批技能都不属本体"]
S_NEW = ["version: 4.33.0", "# AI 工作流 v4.33.0", "技能库根下六上游", "（交 `diagram-mode`（示意图）或**已接入的** `diagram-design`（数据图）",
         "**数据图与示意图 → 已接入的** `diagram-design`", "科研制图 §7.11", "「契约层 ↔ 引擎层」分界**）、自检 8 项",
         "起「六上游」**）", "契约层 ↔ 引擎层**」分界见该手册 §1.7；", "六批技能都不属本体"]
sk = (ROOT / "SKILL.md").read_text(encoding="utf-8")
bad_old = [s for s in S_OLD if s in sk]
miss_new = [s for s in S_NEW if s not in sk]
assert not bad_old, f"SKILL.md 残留旧串：{bad_old}"
assert not miss_new, f"SKILL.md 缺新串：{miss_new}"
print(f"SKILL.md：10 组 old 全清（注意「v4.32.1」作历史提及仍在正文，属预期）、10 组 new 全在")

R_OLD = ["（当前版本 **v4.32.1**）", "数据图 → 外部数据图技能 / 示意图 → `diagram-mode`），**不新造流程、不安装任何外部技能**",
         "v4.30.0 起五上游**）", "当前 v4.32.1 基线为"]
R_NEW = ["（当前版本 **v4.33.0**）", "**已接入的**外部技能 `diagram-design`", "v4.33.0 起六上游**）", "当前 v4.33.0 基线为"]
rd = (ROOT / "README.md").read_text(encoding="utf-8")
bad2 = [s for s in R_OLD if s in rd]
miss2 = [s for s in R_NEW if s not in rd]
assert not bad2, f"README 残留：{bad2}"
assert not miss2, f"README 缺：{miss2}"
print("README.md：4 组 old 全清、4 组 new 全在")

cl = (ROOT / "_archive/changelog.md").read_text(encoding="utf-8")
assert "**v4.33.0（2026-10-11）把第三方图表技能" in cl
assert cl.count("> - **v4.33.0") == 1
print("changelog：v4.33.0 条目已追加（1 处）")
print("\n全量核验通过")
