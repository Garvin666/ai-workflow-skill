# -*- coding: utf-8 -*-
"""s9：补录 trace.jsonl（9 步各一条）。

为什么补录而不是"算了"：plan 校验有一条「步骤闭环不变量（trace 自证）」——
8/9 步已完成却无 trace.jsonl ⇒ 复盘只能靠回忆，且「本次是否沉淀」无法自证。
trace 的 --action/--result 只写**可回查的结论**，不写感想。
"""
import pathlib
import subprocess
import sys

SKILL = pathlib.Path(__file__).resolve().parents[2]
PLAN = str(SKILL / "tasks" / "落地-科研模式接入方法卡片-2026-10-12" / "plan.yaml")
PY = sys.executable

STEPS = [
    ("s1", "基线留痕：参考图令牌采样 + 字体清单 + 公式链探针 + 技能自检基线",
     "python s2_sample.py / s1_baseline.py；checks.py skill",
     "token-samples.txt（4 张参考图分类采样色值）／baseline-fonts.txt（version 4.34.0 快照；"
     "ziamath probe: path=12 use=18 text=0 image=0 remote=ref False）／baseline-checks-skill.txt 78/78 FAIL=0"),
    ("s2", "methodcard_lib：16 槽设计令牌 + SVG 基础件 + wrap_cjk + 公式包装（ziamath→纯 path）",
     "python scripts/methodcard_lib.py --selftest",
     "令牌取自实测采样；公式 SVG 零 text/image/远程引用 ⇒ 天然免 Type3；selftest 工具断言全过"),
    ("s3", "10 个副图组件 + 组件冒烟自检",
     "python scripts/methodcard_lib.py --selftest",
     "10 组件全数冒烟通过；修复 Y 轴映射反向（MY(y) 误用 plot_t-plot_b）"),
    ("s4", "methodcard_build：五区骨架 HTML + Chrome 原生导出 + 字体 base64 内嵌",
     "python scripts/methodcard_build.py --selftest",
     "selftest：card_html 6 个 svg / 零远程引用 / font_faces 2 个 @font-face 含 base64"),
    ("s5", "样板卡 #01 Ridge Regression：四步副图 + hero 双图 + PNG @2×",
     "python s5_render.py card-ridge 2",
     "output/card-ridge.html + export/card-ridge.png 2400×3200"),
    ("s6", "样板卡 #02 Gaussian Mixture：混合密度/责任度/聚类椭圆/对数似然 + PNG @2×",
     "python s6_crop.py / s5_render.py card-gmm 2",
     "实跑抓到并修 3 处副图缺陷：分量与总密度黏连 / 聚类椭圆过稀 / hero 2.5σ 外游离点（采样钳 ±2.2σ）"),
    ("s7", "导出链与机器验收：PDF 矢量 + 零 Type3 + 几何自检 + selftest",
     "python s7_export.py && python s7_verify.py",
     "verify-exports.txt 6 组命令 rc 全零；两 PDF 900.0×1200.0pt、Type3=0、字体全嵌入；"
     "两卡几何 FAIL=0 WARN=0；⭐ 本轮抓到「平台门控」FAIL（POSIX 字面量 /usr/bin/*，与 v4.34.0 同形态复发）"
     "→ 改 PATH 解析并做注入式阴性对照证明判据非空转"),
    ("s8", "契约与登记链：新建 method-card-mode.md；research-mode §7.11 第三通道；diagram-mode §8 分界；四处登记",
     "编辑 references/*.md 与 SKILL.md / README.md / ops.md / _archive/changelog.md",
     "登记 v4.35.0：ops.md 脚本速查 +3 行、SKILL.md 索引 +3 行与 CLI +3 行、changelog 追加（含 9 项真缺陷）；"
     "⭐ 抓到「追加 changelog 时吃掉上一条标题行」→ 回读结构断言（版本链严格递减）发现并修复"),
    ("s9", "收尾：Anti-drop 更正 + 出站卫生 + 清理 + 门禁复跑 + 变更说明",
     "python tmp_fix_plan_deliverables.py / tmp_s9_hygiene.py / cleanup_task.py / checks.py plan",
     "修 plan 交付物声明（baseline-checks.txt→baseline-checks-skill.txt+baseline-lint.txt）使 Anti-drop FAIL→0；"
     "出站扫描 FAIL 2→0（脚本改路径推导、证据掩码 ~）；四道门禁复跑见 fixtures/"),
]

for sid, action, command, result in STEPS:
    r = subprocess.run(
        [PY, "-u", "-X", "utf8", "scripts/checks.py", "trace", PLAN,
         "--step", sid, "--action", action, "--command", command, "--result", result],
        cwd=SKILL, capture_output=True, text=True, encoding="utf-8")
    ok = r.returncode == 0
    print(f"  [{'OK' if ok else 'FAIL'}] {sid} rc={r.returncode} {(r.stdout or r.stderr).strip()[:110]}")
    if not ok:
        raise SystemExit(1)

tp = SKILL / "tasks" / "落地-科研模式接入方法卡片-2026-10-12" / "trace.jsonl"
n = len([l for l in tp.read_text(encoding="utf-8").splitlines() if l.strip()])
print(f"\nOK：trace.jsonl 现有 {n} 条")
assert n >= 9, n
