"""s5: 计数与文档同源 + 版本注册 + 第 4 上游登记。

纪律（本仓硬约定第 5 条）：同一文件多处编辑**串行**下发 + **逐处回读断言**；
`sub()` 必须作用于**累积串**（s2 首版写成 `src.replace(...)` ⇒ 前序编辑被静默丢弃）。

同时区分两类「N 条」：
  · **现在时计数**（描述当前判据集）→ 必须改成 36；
  · **历史版本注记**（"v1.7 新增 R4，既有 30 条一字未改"）→ 是当时事实，**不得改写**（改它＝篡改历史）。
凡涉及历史链条的（ops.md 的版本链），采取「追加上一段」而非「改写上一段」。
"""
import pathlib
import sys

# 原为硬编码本机绝对路径（出站清单第 4 项）⇒ 改由 __file__ 推导
SKILL = pathlib.Path(__file__).resolve().parents[2]
TODAY = "2026-10-09"
NEWVER = "4.26.0"
OLDVER = "4.25.0"

# (文件, tag, old, new) —— 每条的 old 必须在**该文件累积串**里恰出现 1 次
EDITS = [
    # ── SKILL.md：版本 2 处（frontmatter / H1）＋ 计数 3 处 ＋ 第 4 上游 ──
    ("SKILL.md", "frontmatter 版本",
     f"version: {OLDVER}", f"version: {NEWVER}"),
    ("SKILL.md", "H1 标题版本",
     f"# AI 工作流 v{OLDVER}", f"# AI 工作流 v{NEWVER}"),
    ("SKILL.md", "阶段 5 判据集计数",
     "判据集 `references/aesthetic-rubric.yaml`（31 条），逐产物或 `--batch` 出原始输出。",
     f"判据集 `references/aesthetic-rubric.yaml`（36 条，v{NEWVER} 起含 H 层 5 条），逐产物或 `--batch` 出原始输出。"),
    ("SKILL.md", "手册索引表 判据集版本+计数",
     "| `references/aesthetic-rubric.yaml` | **审美判据集**（31 条，判据集 v1.7）：由",
     "| `references/aesthetic-rubric.yaml` | **审美判据集**（36 条，判据集 v1.8）：由"),
    ("SKILL.md", "手册索引表 H 层说明",
     "**韵律层 G16**（错峰阶梯非递减，无序列则 SKIP）。⚠️ 它是**数据文件不是手册**",
     "**韵律层 G16**（错峰阶梯非递减，无序列则 SKIP）；"
     "**v1.8 起另含 H 层 5 条**（提炼自第三方技能 `hairline` 的视觉工艺："
     "H1 缓动纪律／H2 禁发光式效果／H3 无限循环减动效兜底 三条 `machine` 实跑 ＋ "
     "H4 静止态构图／H5 命中区稳定 两条 `manual` 人审；出处见 `references/external-skills.md` §1.4）。"
     "⚠️ 它是**数据文件不是手册**"),
    ("SKILL.md", "CLI 行 计数",
     "审美判据校验器（31 条）；", "审美判据校验器（36 条）；"),
    ("SKILL.md", "索引表 external-skills 上游数",
     "（v4.16.0 建；**v4.25.0 起为「三上游」**）",
     f"（v4.16.0 建；**v{NEWVER} 起为「四上游」**）"),
    ("SKILL.md", "索引表 加第 4 上游",
     "**上游三** `humanizer`（**扁平外挂、复制安装**）—— 去 AI 味的**改写手法**资源（**判定仍在第七物理量，不另立判据**）。",
     "**上游三** `humanizer`（**扁平外挂、复制安装**）—— 去 AI 味的**改写手法**资源（**判定仍在第七物理量，不另立判据**）；"
     "**上游四** `hairline-create`（**扁平外挂、复制安装、零补丁**）—— 等距线稿**风格的产物生成器**，"
     "其**原则侧已按 judgeability 分档折进 `references/aesthetic-rubric.yaml` 的 H 层、不另立判定**，"
     "结构侧与 `diagram-mode` 的分界见 §1.4。"),
    ("SKILL.md", "索引表 三批→四批",
     "⚠️ **三批技能都不属本体**", "⚠️ **四批技能都不属本体**"),

    # ── README.md：版本 2 处 ＋ 计数 2 处 ＋ 第 4 上游 ──
    ("README.md", "头部版本",
     f"（当前版本 **v{OLDVER}**）", f"（当前版本 **v{NEWVER}**）"),
    ("README.md", "计数 校验器行",
     "文风判据（31 条）与审美判据（30 条）的校验器",
     "文风判据（31 条）与审美判据（36 条）的校验器"),
    ("README.md", "计数 目录树行",
     "审美判据校验器（设计类产物，30 条 rubric）",
     "审美判据校验器（设计类产物，36 条 rubric）"),
    ("README.md", "外部技能簇 上游数",
     "- **外部技能簇**（v4.16.0 建；**v4.25.0 起为三上游**）：",
     f"- **外部技能簇**（v4.16.0 建；**v{NEWVER} 起为四上游**）："),
    ("README.md", "外部技能簇 加第 4 上游",
     "**上游三** `humanizer`（去 AI 味的**改写手法**资源，**扁平外挂、复制安装**；⚠️ 判定仍在本仓第七物理量，不另立判据）。",
     "**上游三** `humanizer`（去 AI 味的**改写手法**资源，**扁平外挂、复制安装**；⚠️ 判定仍在本仓第七物理量，不另立判据）；"
     "**上游四** `hairline-create`（等距线稿**风格的产物生成器**，**扁平外挂、复制安装、零补丁**；"
     "其**原则侧已分档折进审美判据集的 H 层**，不另立判定）。"),
    ("README.md", "门禁口径 版本+基线",
     f"当前 v{OLDVER} 基线为 **通过 76/76，FAIL=0，SKIP=0，WARN=0**（v4.24.0 亦为 76/76）",
     f"当前 v{NEWVER} 基线为 **通过 76/76，FAIL=0，SKIP=0，WARN=0**（v{OLDVER} 亦为 76/76）"),

    # ── assets/plan-template.yaml：计数 ──
    ("assets/plan-template.yaml", "模板注释 计数",
     "判据集 references/aesthetic-rubric.yaml（30 条）",
     f"判据集 references/aesthetic-rubric.yaml（36 条，v{NEWVER} 起含 H 层 5 条）"),

    # ── references/ops.md：校验器版本 1 处 ＋ 计数 1 处 ＋ 版本链追加 1 段 ──
    ("references/ops.md", "校验器版本号",
     "| **check_aesthetics.py**（v1.8.0 自研；随技能发行） |",
     "| **check_aesthetics.py**（v1.9.0 自研；随技能发行） |"),
    ("references/ops.md", "校验器 计数+H 层摘要",
     "判据集 = `references/aesthetic-rubric.yaml`（**31 条**，每条含 `judgeability` / `params` / `source` / `applies_to`）。"
     "⚠️ **v1.8.0 新增渲染层判据 R4 几何重叠**",
     "判据集 = `references/aesthetic-rubric.yaml`（**36 条**，每条含 `judgeability` / `params` / `source` / `applies_to`）。"
     "⚠️ **v1.9.0 新增 H 层 5 条**（提炼自第三方技能 `hairline` 的视觉工艺："
     "**H1 缓动纪律**／**H2 禁发光式效果**／**H3 无限循环减动效兜底** 三条 `machine` 实跑 ＋ "
     "**H4 静止态构图**／**H5 命中区稳定** 两条人审 `check: null` ⇒ SKIP；**既有 31 条条文与阈值一字未改**；"
     "H1 带射程参数 `scope`，默认 `transition`（只判状态切换族），显式 `all` 才连 `animation` 一起禁）。"
     "⚠️ **v1.8.0 新增渲染层判据 R4 几何重叠**"),
    ("references/ops.md", "版本链追加（不改历史段）",
     "—— 既有 30 条条文与阈值**一字未改** |",
     "—— 既有 30 条条文与阈值**一字未改**；**v1.9.0 起**判据集 **36 条**"
     "（新增 **H 层 5 条**，提炼自第三方技能 `hairline`：三条 `machine` 实跑 ＋ 两条人审登记）"
     "—— 既有 31 条条文与阈值**一字未改** |"),

    # ── scripts/checks_core.py：检查项 22 说明计数 ──
    ("scripts/checks_core.py", "检查项 22 计数",
     "判据集：`references/aesthetic-rubric.yaml`（31 条）；校验器：`scripts/check_aesthetics.py`。",
     "判据集：`references/aesthetic-rubric.yaml`（36 条）；校验器：`scripts/check_aesthetics.py`。"),

    # ── references/diagram-mode.md：H 层指针 ＋ 陈旧计数 ──
    ("references/diagram-mode.md", "H 层指针",
     "**画完之后的机器验收仍归既有的审美判据**（`aesthetic-rubric.yaml` + `check_aesthetics.py`），本模块是它的**上游**，不替换它。",
     "**画完之后的机器验收仍归既有的审美判据**（`aesthetic-rubric.yaml` + `check_aesthetics.py`），本模块是它的**上游**，不替换它。"
     f"该判据集自 **v{NEWVER}** 起含 **H 层 5 条**（缓动纪律／禁发光式效果／无限循环减动效兜底 三条 `machine` ＋ "
     "静止态构图／命中区稳定 两条人审），提炼自第三方技能 `hairline`（见 `references/external-skills.md` §1.4）—— "
     "**图内的动效与发光同吃这三条**。"),
    ("references/diagram-mode.md", "重叠处置行 陈旧计数",
     "**不重定义已有 30 条**",
     f"**不重定义已有判据**（截至 v{NEWVER} 计 36 条）"),

    # ── references/ppt-mode.md：H 层指针 ──
    ("references/ppt-mode.md", "H 层指针",
     "与 §10 九项自检**都是纪律项**。",
     "与 §10 九项自检**都是纪律项**。  \n"
     "> **下游视觉验收归既有判据集**：本模式不新造判据，交付前用本仓 `check_aesthetics.py --product ppt` ＋ "
     "`references/aesthetic-rubric.yaml` 出机器证据；该判据集自 **v" + NEWVER + "** 起含 **H 层 5 条**"
     "（缓动纪律／禁发光式效果／无限循环减动效兜底 三条 `machine` 实跑 ＋ 静止态构图／命中区稳定 两条人审），"
     "提炼自第三方技能 `hairline`（见 `references/external-skills.md` §1.4）。"),
]

CHANGELOG_ANCHOR = "> - **v4.25.0（2026-10-09）「PPT 模式」"

CHANGELOG_ENTRY = f"""> - **v{NEWVER}（{TODAY}）把第三方技能 `lucasmarkes/hairline` 的视觉工艺复用进本体 —— 「装技能 + 取原则」，新增审美判据 H 层 5 条**：任务档案 `tasks/复用-hairline视觉工艺-2026-10-09/`（技能本体侧）。
  - **① 来历与关键判断**：用户 {TODAY} 指定「lucasmarkes/hairline 将这个 skill 复用进 ai-workflow 以提高审美」，三项确认：复用形态=**装技能 + 取原则**；原则落点=**扩审美判据集**；机器判据=**本轮一并做**。⭐ 关键判断：hairline 交付的 skills/hairline-create 是一个**产物生成器**（给一个想法画一张等距线稿图），**不是一个方法论**；且其十条规则／十三项肉眼验收**绝大多数在判断层**（look.md 自述「The validator reads text. This is what only eyes can check.」）⇒ 折进本体的正确形态是**产物外挂、原则按 judgeability 分档入判据集**；给判断层硬配机器判据＝制造假绿（本仓已立口径）。
  - **② 修法（四处落盘）**：`skills/hairline-create/` 以**扁平外挂（复制安装、零补丁、逐字节复制）**接入技能库根（11 个上游文件 ＋ 随库携带上游 LICENSE 供 MIT 署名），立账本 `.vendor/hairline.lock.json`（12 条 files 记录／`content_digest`／`install_form`）；`references/external-skills.md` 由「三上游」泛化为「**四上游**」（新增 §1.4 表、§三 路由表第四行、§五 边界条、§7.3 同步规程；version 3 → 4）；`references/aesthetic-rubric.yaml` 新增 **H 层 5 条**（H1 `easing_discipline`／H2 `no_glow_effects`／H3 `infinite_motion_guard` 三条 `machine` ＋ H4 `rest_is_composed`／H5 `hit_area_stability` 两条 `manual`；判据集 31 → **36** 条，version 1.7 → 1.8）；`scripts/check_aesthetics.py` 同步实现 3 个 check（VERSION 1.8.0 → **1.9.0**；取数侧新增「动效缓动／纵深声明／无限循环」三组，CHECKS ＋ PARAM_SPEC ＋ 自检夹具各一处）。**不新增 plan 字段、不新增 judge、不新增 `checks.py` 判据**。
  - **③ ⭐ 重叠先排除（不重复造）**：rule 02「按距离错峰」→ 既有 **G16**；rule 06「构造不穿透」→ 既有 **R4**；rule 04 的「唯一强调色」半面 → 既有 **G2/G8** ⇒ 这三处**不新增**，只在判据集表头登记分工。**未迁移 4 条**（强绑定 isometric 画面、对通用视觉产物无判别力）：rule 03「不出框」／rule 07 的**屏外休眠半面**／rule 09「圆角化 + 亮外暗内」／rule 10「图内无文字」。
  - **④ ⭐ s4 影响面实测抓出 H1 首版的误报并收窄（本轮最重要的一条）**：合成矩阵证明首版**无射程**的 H1 把**合规产物**的 `.spinner{{animation:spin 1.2s linear infinite;}}` 判 FAIL —— 旋转／进度／跑马灯用线性**是对的**（匀速旋转的物理语义本就是线性），原样套用属**作用域错配**（同 G1/G6/G7/G11 一族）。处置：H1 加射程参数 `scope`，**默认 `transition`**（只判状态切换族），`animation` 族默认放行，要收紧须显式 `scope: all`；`PARAM_SPEC` 登记两值；判据集 note 登记边界；自检夹具同步改判。**参数活性自证**：同一语料只改 `scope` 一个值即产出两份可 diff 的输出（H1 `1/2` → `2/3`）⇒ 它是活的、非死参数。
  - **⑤ 机器验收（全部实跑）**：`checks.py skill` **76/76 / FAIL=0 / SKIP=0 / WARN=0**（文档引用完整性 **142** 条，与 v4.25.0 同）；`check_aesthetics.py --audit` **一致 30 / 人审点 6 / 不一致 0 / 判据总数 36**；`--self-test` rc=0（H 层 25 项全 OK，`[FAIL]` 计数 0）；**反向断言**（`--audit` 只有单向，故本任务自加）实现侧 26 ↔ 判据集声明 26，**孤儿 0 / 悬空 0**；`external_skill_lint.py --verify-lock` **通过 85 / FAIL=0**（四上游逐文件对上：hairline 12 ／ humanizer 9 ／ mattpocock 65 ／ ppt-master 12994）；**A/B 前后对照**（对照侧＝冻结的改前脚本副本）三旧上游结论**逐条一致、不一致 0**。
  - **⑥ 三处自身缺陷（如实留痕）**：① `s2` 改写脚本首版 `sub()` 写成 `src.replace(...)`（**每次都从原始串替换**）⇒ 前序编辑被静默丢弃、8 项回读断言全红；改为作用于**累积串**后通过 —— 由「回读断言」抓出，是本仓硬约定第 5 条的实证。② 给**上游**文件 rules.md / look.md 加了**反引号**，被「文档引用完整性」判为技能内引用 ⇒ **FAIL=1 假断链**（本仓既有约定「外部路径用纯文本提及」写在 `diagram-mode.md` 首部，本次违反）⇒ 改为纯文本带路径后 FAIL 归零、引用数回到 142。③ `s4` 首版输出的 H1 FAIL 分布是**收窄前**的（改完判据未复跑）⇒ 按「上一轮结论＝待复测假设」复跑，并保留前后两份输出对照。
  - **⑦ ⚠️ 诚实边界（不得读成绿）**：① **未在存量真实语料上实测影响面** —— 工作区根与技能库根内 `.css` 实测 **0 个**，真实语料在 `E:/ChatGPT/ui库`（工作区根之外、本次**未申请授权**）⇒ 改用**合成矩阵**（5 样本），结论**只作区分度证据、不得读成「存量零影响」**；计划 `meta.前提审计` 的「新增 machine 判据不会把存量产物一次性判红」维持 **待验证**。② **H4/H5 是 `manual`（`check: null`）**，产出 SKIP「人审点（机器不判定）」—— **SKIP 不是通过**；hairline 的十三条肉眼验收**只能靠眼睛**。③ **装了 hairline 不等于产物变好看** —— 本次只保证可路由 ＋ 判据可跑，判据只拦**明显劣化**。④ **复制安装 ⇒ 上游更新不会自动生效**，须按 §7.3 整体重取（与 ppt-master 的联接相反）。⑤ **未跑 hairline-create 的业务链路**（其 `look.mjs` 需浏览器与 playwright-core）。
  - **⑧ 未 commit、未 push**（推送属不可逆动作，须单独确认；本体走 `push_ontology.py`、工具走 `publish_tools.py`）。
"""


def main():
    assert len({(f, t) for f, t, _, _ in EDITS}) == len(EDITS), "同一文件同一 tag 重复"
    by_file = {}
    for f, t, old, new in EDITS:
        by_file.setdefault(f, []).append((t, old, new))

    for f, items in by_file.items():
        p = SKILL / f
        src = p.read_text(encoding="utf-8")
        s = src
        for t, old, new in items:
            # ⚠️ 幂等判据必须看「目标态是否已达成」（`new in s`），**不能**看「旧串是否消失」：
            #    插入型编辑的 new 以 old 为前缀 ⇒ 「旧串仍在」对**已应用**的编辑同样成立，
            #    按旧串判会把它**再插入一遍**（本轮实测踩到：diagram-mode / ppt-mode 各重复一次）。
            if new in s:
                print(f"     · 跳过（已应用）：{f} · {t}")
                continue
            n = s.count(old)
            assert n == 1, f"[{f} · {t}] 锚点出现 {n} 次（期望 1）—— 拒绝在模糊锚点上改"
            s = s.replace(old, new)
            assert new in s, f"[{f} · {t}] 替换后新串不在（插入型断言另计）"
        if s == src:
            print(f"[ OK ] {f} — 全部 {len(items)} 处已应用，无改动（幂等）")
            continue
        p.write_text(s, encoding="utf-8")
        # 写盘后**回读复核**（不信内存）
        back = p.read_text(encoding="utf-8")
        assert back == s, f"[{f}] 回读与写盘内容不一致"
        for t, old, new in items:
            assert new in back, f"[{f} · {t}] 回读缺新串"
        print(f"[ OK ] {f} — {len(items)} 处改动 + 回读复核通过")

    # changelog：追加（本文件「只追加、不删改」；最新在开头 ⇒ 插在 v4.25.0 条目之前）
    cl = SKILL / "_archive" / "changelog.md"
    src = cl.read_text(encoding="utf-8")
    if f"v{NEWVER}（{TODAY}）" in src:
        print(f"[ OK ] _archive/changelog.md — v{NEWVER} 条目已存在，跳过（幂等）")
    else:
        assert src.count(CHANGELOG_ANCHOR) == 1, "changelog 插入锚点不唯一"
        s = src.replace(CHANGELOG_ANCHOR, CHANGELOG_ENTRY + CHANGELOG_ANCHOR, 1)
        cl.write_text(s, encoding="utf-8")
        back = cl.read_text(encoding="utf-8")
        assert back == s, "changelog 回读与写盘不一致"
        assert f"v{NEWVER}（{TODAY}）" in back, "changelog 回读缺新条目"
        print(f"[ OK ] _archive/changelog.md — 追加 v{NEWVER} 条目（1 处）+ 回读复核通过")

    # 交叉自证：判据集实际条数 == 四处文档写的条数（**机器数数，不手写**）
    import re
    rub = (SKILL / "references" / "aesthetic-rubric.yaml").read_text(encoding="utf-8")
    real = len(re.findall(r"^  - id: [A-Z]+\d+\s*$", rub, re.M))
    assert real == 36, f"判据集实测 {real} 条（期望 36）"
    checks = {
        "SKILL.md": (SKILL / "SKILL.md").read_text(encoding="utf-8"),
        "README.md": (SKILL / "README.md").read_text(encoding="utf-8"),
        "checks_core.py": (SKILL / "scripts" / "checks_core.py").read_text(encoding="utf-8"),
        "ops.md": (SKILL / "references" / "ops.md").read_text(encoding="utf-8"),
        "plan-template.yaml": (SKILL / "assets" / "plan-template.yaml").read_text(encoding="utf-8"),
    }
    for name, txt in checks.items():
        assert "（36 条" in txt or "36 条" in txt, f"{name} 未登记 36 条"
    print(f"[ OK ] 计数同源：判据集实测 {real} 条，5 处活文件均登记 36 条")

    # 版本同源：活文件里 v4.25.0 只应出现在**历史注记**语境
    for f in ("SKILL.md", "README.md"):
        txt = (SKILL / f).read_text(encoding="utf-8")
        for i, ln in enumerate(txt.splitlines(), 1):
            if OLDVER in ln:
                print(f"     · 仍有 {OLDVER} 行 {f}:{i} :: {ln.strip()[:110]}")
    print("[ OK ] s5 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
