# -*- coding: utf-8 -*-
"""追加 s12–s16（第五轮：共享图表库 / reveal 变体 / PNG 通道 / 零 Type3 回灌 / 一键入口）
到 plan.yaml 与 trace.jsonl。**幂等**（按 id 判重），末尾自带解析器自检。

⚠️ 教训固化：**追加 plan 步骤的脚本末尾必须自带 `yaml.safe_load` 断言** ——
上一轮就是因为缩进写成 3 空格（应为 2）导致 plan 无法解析，而当时没有解析器自检。
"""

import json
import pathlib

import yaml

T = pathlib.Path(__file__).resolve().parent
PLAN, TRACE = T / "plan.yaml", T / "trace.jsonl"
P = "tasks/落地-科研模式接入diagram-design-2026-10-11"

# ── 步骤号与脚本名的对应（刻意与脚本名对齐）────────────────────────────────
#   s12 ← 共享图表库重构（chartlib.py ＋ pxcompare.py）
#   s13 ← reveal 变体（s13_gen_reveal.py）—— 名字直接对上
#   s14 ← PNG 通道（diagram_export.py）
#   s15 ← 零 Type3 判据（check_vector_export.py）
#   s16 ← 一键入口（build_charts.py）
STEPS = [
    (
        "s12",
        "  - id: s12\n"
        "    做什么: 把 s9（静态）与 s11（动效）各写一份的几何/令牌/页面外壳收敛为**单一来源** chartlib.py；"
        "并建立**像素等同**验证器 pxcompare.py（Chrome 固定视口截图 ＋ numpy 逐像素比对 ＋ 差异包围盒 ＋ 位图 md5）\n"
        "    输入: output/chart-0{1..5}-*.html（重构前冻结件 fixtures/before-refactor/）、"
        "fixtures/before-refactor/scripts/{s9,s11}*.py\n"
        "    预期产出: chartlib.py、pxcompare.py、重构后的 output/chart-0{1..4}.html 与 chart-05-bar-motion.html\n"
        f"    验证方式: pxcompare.py --negctl **双向阴性对照**（同图两截 ⇒ identical；注入 1 像素 ⇒ DIFFERENT）；"
        "重构前后逐图比对 —— line/scatter/motion **差异=0**；bar 差 332 px（0.0158%）系**真缺陷修正**"
        "（旧版手写文案「7年6正1负」算错，应为 5正2负，新版改为从数据派生）；"
        "heatmap 差 5311 px（0.2529%）限于色带区（**60 rect → 1 rect + linearGradient**，有意改进）\n"
        "    状态: 完成\n"
        "    交付物: tasks/落地-科研模式接入diagram-design-2026-10-11/chartlib.py、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/pxcompare.py、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/chart-01-bar.html、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/chart-02-line.html、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/chart-03-heatmap.html、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/chart-04-scatter.html\n"
    ),
    (
        "s13",
        "  - id: s13\n"
        "    做什么: 加 reveal 自动播放变体（用户选项 ④）—— 同一柱状图做成 `data-motion-mode=\"reveal\"`；"
        "⭐ 关键发现：上游 canonical 控制器**原生支持** reveal（template-motion.html 第 433-436 行 render(0)→play()）"
        "⇒ 不另写控制器（另写会被 self_check 的脚本身份判据拒收）\n"
        "    输入: chartlib.motion_assets()/motion_page()、s11_gen_motion.STEPS（共用同一份步/标签定义）\n"
        "    预期产出: output/chart-06-bar-reveal.html\n"
        "    验证方式: 四条硬断言 —— 控制器与上游模板归一化后相等=True；data-motion-mode=reveal；"
        "**--motion-total=2880ms（=4 步 × 720ms，修正了一处契约缺口）**；与 step 版逐行集合差**仅 7 行**"
        "（mode ＋ 标题/眉题/aria id/描述）；上游 self_check.py rc=0\n"
        "    状态: 完成\n"
        "    交付物: tasks/落地-科研模式接入diagram-design-2026-10-11/output/chart-06-bar-reveal.html、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/s13_gen_reveal.py\n"
    ),
    (
        "s14",
        "  - id: s14\n"
        "    做什么: 实现 PNG 栅格化通道（用户选项 ②，含装 Playwright）并把三条导出通道收口为**一个脚本**"
        "scripts/diagram_export.py —— `svg` 转调上游真源 export_svg.py（不另写实现）；"
        "`pdf` 是**本仓扩展**（⚠️ 上游 export.md 只定义 svg/png）；`png` 按上游规程"
        "（透明底、只截 <svg> 元素盒、释放祖先裁剪、动效页先 ?motion=static 并断言 data-frame=static、scale 限 1..4）\n"
        "    输入: output/chart-0{1..6}-*.html、~/.workbuddy/skills/diagram-design/scripts/export_svg.py\n"
        "    预期产出: scripts/diagram_export.py、output/export/ 下 6 个 .svg ＋ 6 个 .pdf ＋ 6 个 .png、"
        "scripts/setup_env.ps1（加 playwright 依赖与第 4b 步浏览器二进制探测）\n"
        "    验证方式: --selftest 全绿（含 viewBox 四形态 ＋ 字体栈替换幂等且必带 CJK ＋ "
        "**fail-open 形态断言**：不先 unlink 则旧产物被读成成功）；6 图 × 3 通道实跑；"
        "⚠️ 本轮修掉**四个**真缺陷 —— ① 产出判据只看「文件存在」⇒ **旧产物冒充新产物**（实测 chart-01..04 报 OK 而时间戳仍是上一轮），"
        "现三条通道一律先删再写；② **相对路径传 Chrome** ⇒ 系统找不到指定的路径，现一律 resolve()；"
        "③ `import fitz` 是**弃用别名**（PyMuPDF ≥1.24 正式名为 pymupdf，旧名每次调用发 DeprecationWarning 且将移除）⇒ 两个名字都试，"
        "依赖探测改为「**包 vs 浏览器二进制分两级报**」；④ 硬编码 `/usr/bin/google-chrome` 等 POSIX 路径触发「平台门控」⇒ "
        "改为一律 `shutil.which()` 按 PATH 解析（Linux 落点随发行版/snap/flatpak/brew 而变，穷举必漏）\n"
        "    状态: 完成\n"
        "    交付物: scripts/diagram_export.py、scripts/setup_env.ps1、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/export/chart-01-bar.png、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/export/chart-02-line.png、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/export/chart-03-heatmap.png、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/export/chart-04-scatter.png、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/export/chart-05-bar-motion.png、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/export/chart-06-bar-reveal.png\n"
    ),
    (
        "s15",
        "  - id: s15\n"
        "    做什么: 新建**通用矢量件检查器** scripts/check_vector_export.py 并把「零 Type3」回灌成科研 R5 的制图检查项"
        "（用户选项 ③）—— 判据：单页 / --expect 页面尺寸 / 文本可提取 / **零 Type3** / **字体全嵌入**；"
        "SVG 侧另判纯矢量（无内嵌栅格）；四态（PASS/FAIL/SKIP/单条未检测）严格分开\n"
        "    输入: output/export/*.pdf、output/export/*.svg、references/research-mode.md §7.11\n"
        "    预期产出: scripts/check_vector_export.py、references/research-mode.md（v4.30.0 → v4.31.0）、"
        "references/ops.md 与 SKILL.md 的脚本登记两处\n"
        "    验证方式: --selftest 18 项全绿（含坏 XML fail-closed 不崩栈、**未给 --expect ⇒ 该项记「未检测」而非 PASS**）；"
        "对 8 个真实矢量件 PASS=8 FAIL=0 SKIP=0；⚠️ 本轮修掉一处**判据造信号** —— 期望图幅原在解析处统一换算成 pt，"
        "而 SVG 的 viewBox 比对需原单位 ⇒ **4 个 SVG 全假 FAIL**，现 parse_expect 不换算、由 to_pt 在 PDF 侧显式换\n"
        "    状态: 完成\n"
        "    交付物: scripts/check_vector_export.py、references/research-mode.md\n"
    ),
    (
        "s16",
        "  - id: s16\n"
        "    做什么: 建**一键入口** build_charts.py（5 道工序：生成 → 几何越界 → 上游契约 → 三通道导出 → 矢量件验收），"
        "并逐条加固边界（输出目录为空 / Chrome 缺失 / Playwright 或浏览器二进制缺失 / PDF 多页·尺寸不符·含 Type3 / "
        "坐标越界 / 动效页未达完整帧 / 重跑幂等）；**明确区分「环境缺件」(rc=3) 与「产物缺陷」(rc=1)**\n"
        "    输入: s9/s11/s13 生成器、s9b_geom_check.py、上游 self_check.py、scripts/diagram_export.py、"
        "scripts/check_vector_export.py\n"
        "    预期产出: build_charts.py、_archive/changelog.md（v4.34.0）、SKILL.md（v4.34.0）、README.md（v4.34.0）\n"
        "    验证方式: 一键实跑取汇总表；门禁 —— checks.py skill 76/76 FAIL=0；checks.py plan FAIL=0；"
        "external_skill_lint.py FAIL=0；gen_skill_index.py --check rc=0\n"
        "    状态: 完成\n"
        "    交付物: tasks/落地-科研模式接入diagram-design-2026-10-11/build_charts.py、"
        "SKILL.md、_archive/changelog.md、references/ops.md、README.md、"
        "references/external-skills.md\n"
    ),
    (
        "s17",
        "  - id: s17\n"
        "    做什么: 门禁收口 —— 跑 checks.py skill 时抓到**两条 FAIL**，两条都改**代码与文档**、不动判据："
        "①「文档引用完整性」**19 处假 FAIL**（该判据是扁平检查，反引号里的 .py/.md 一律按「技能目录内」解析，"
        "而 diagram-design 的文件在另一个根）⇒ 五文件摘除 19 处反引号 ＋ 在 external-skills.md §1.7 写**记号约定**；"
        "② 文档里**写死的自检项数**（写 14/18，实际 17/21）⇒ 改为**脚本自报项数**，文档不再写数字\n"
        "    输入: SKILL.md、references/{external-skills,ops,research-mode,diagram-mode}.md、"
        "scripts/{diagram_export,check_vector_export}.py\n"
        "    预期产出: 修正后的五份文档、两个脚本（自报项数 ＋ pymupdf 兼容 ＋ PATH 浏览器探测）、README 基线更新\n"
        "    验证方式: s17_docref_fix.py **逐串精确替换 ＋ 回读断言**（替换后这些精确串必须为 0，共 19 处）；"
        "checks.py skill 由 **76/78 FAIL=2 → 78/78 FAIL=0 SKIP=0 WARN=0**（+2 是新脚本带来的判据项，**非回归**）；"
        "两脚本 --selftest 自报「断言 17 项 / 21 项」且均 PASS\n"
        "    状态: 完成\n"
        "    交付物: SKILL.md、references/external-skills.md、references/ops.md、"
        "references/research-mode.md、scripts/diagram_export.py、scripts/check_vector_export.py、README.md、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/s17_docref_fix.py\n"
    ),
]

TRACE_RECS = [
    {
        "ts": "2026-10-11 17:15",
        "step": "s12",
        "action": "共享图表库重构 ＋ 像素等同验证（含双向阴性对照）",
        "cmd": "pxcompare.py fixtures/before-refactor output --negctl ; pxcompare.py …",
        "result": "阴性对照 2/2 PASS；line/scatter/motion 差异=0；bar 332px=真缺陷修正（6正1负→5正2负）；heatmap 5311px=色带 60rect→gradient",
    },
    {
        "ts": "2026-10-11 17:35",
        "step": "s13",
        "action": "reveal 自动播放变体（复用 canonical 控制器，修正 --motion-total 契约缺口）",
        "cmd": "s13_gen_reveal.py ; self_check.py",
        "result": "四条硬断言全 True；--motion-total 2880ms；与 step 版仅差 7 行；self_check rc=0",
    },
    {
        "ts": "2026-10-11 17:45",
        "step": "s14",
        "action": "PNG 栅格化通道 ＋ 三通道导出器收口（并装 Playwright 浏览器二进制）",
        "cmd": "playwright install chromium ; diagram_export.py out/*.html --formats svg,pdf,png --scale 2",
        "result": "selftest 22/22；6 图 × 3 通道；修掉「旧产物冒充新产物」fail-open 与「相对路径传 Chrome」两个真缺陷",
    },
    {
        "ts": "2026-10-11 17:50",
        "step": "s15",
        "action": "零 Type3 判据落地为通用矢量件检查器并回灌科研 R5",
        "cmd": "check_vector_export.py --selftest ; check_vector_export.py output/export/*.pdf output/export/*.svg --expect 1000x500",
        "result": "selftest 18/18；真实矢量件 PASS=8 FAIL=0 SKIP=0；修掉「解析处统一换算单位」造成的 4 个 SVG 全假 FAIL",
    },
    {
        "ts": "2026-10-11 17:55",
        "step": "s16",
        "action": "一键入口 build_charts.py ＋ 边界加固 ＋ 留痕（changelog/SKILL/README 版本同源）",
        "cmd": "build_charts.py ; checks.py skill ; checks.py plan ; external_skill_lint.py ; gen_skill_index.py --check",
        "result": "汇总表全通过；四道门禁 FAIL=0",
    },
    {
        "ts": "2026-10-11 18:05",
        "step": "s17",
        "action": "门禁收口：文档引用记号修正（19 处假 FAIL）＋ 自检项数改为脚本自报 ＋ pymupdf 兼容 ＋ PATH 浏览器探测",
        "cmd": "s17_docref_fix.py ; checks.py skill ; diagram_export.py --selftest ; check_vector_export.py --selftest",
        "result": "checks.py skill 76/78 FAIL=2 → 78/78 FAIL=0；两脚本自报「断言 17/21 项」且 PASS；未改任何判据",
    },
]

# ══════════════════════════════════════════════════════════════════════════
s = PLAN.read_text(encoding="utf-8")
for sid, block in STEPS:
    if f"- id: {sid}" in s:
        print(f"[SKIP] {sid} 已在 plan.yaml")
    else:
        if not s.endswith("\n"):
            s += "\n"
        s += block
        print(f"[OK] plan.yaml 追加 {sid}")
PLAN.write_text(s, encoding="utf-8", newline="")

# ⚠️ 追加后**立刻**用解析器自检（上一轮的教训：写完不自检 ⇒ 缩进错也发现不了）
doc = yaml.safe_load(PLAN.read_text(encoding="utf-8"))
ids = [st["id"] for st in doc["steps"]]
assert ids == [f"s{i}" for i in range(1, 18)], f"步骤 id 序列异常：{ids}"
print(f"[ASSERT] plan.yaml 解析通过，步骤 {ids[0]}..{ids[-1]}（共 {len(ids)} 步）")

raw = TRACE.read_bytes()
c0 = raw.count(b"\r\n")
l0 = raw.count(b"\n") - c0
print(f"[INFO] trace 追加前 CRLF={c0} loneLF={l0}")
for rec in TRACE_RECS:
    if f'"step": "{rec["step"]}"'.encode() in raw:
        print(f"[SKIP] {rec['step']} 已在 trace")
        continue
    with TRACE.open("a", encoding="utf-8", newline="") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\r\n")
    print(f"[OK] trace 追加 {rec['step']}")
    raw = TRACE.read_bytes()

b = TRACE.read_bytes()
lone = b.count(b"\n") - b.count(b"\r\n")
assert lone == 0, f"trace 出现异类 loneLF={lone}"
for sid, _ in STEPS:
    assert b.count(f'"step": "{sid}"'.encode()) == 1, f"trace {sid} 回读失败"
lines = [json.loads(x) for x in b.decode("utf-8").splitlines() if x.strip()]
print(f"[ASSERT] trace 纯 CRLF（{b.count(chr(13).encode()+chr(10).encode())} 行）、"
      f"共 {len(lines)} 条记录、s12–s17 各 1 条")
