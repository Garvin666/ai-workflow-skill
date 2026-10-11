# -*- coding: utf-8 -*-
"""追加 s10（导出 SVG/PDF）与 s11（动效通道）到 plan.yaml 与 trace.jsonl。幂等。"""

import json
import pathlib

T = pathlib.Path(__file__).resolve().parent
PLAN, TRACE = T / "plan.yaml", T / "trace.jsonl"

STEPS = [
    (
        "s10",
        "   - id: s10\n"
        "    做什么: 跑上游导出通道产投稿级矢量件 —— export_svg.py 出 4 个 SVG（--system-fonts 免联网），"
        "再以「仅图示」打印页（页面尺寸 = viewBox 1000×500，零页边距）经 Chrome 无头 --print-to-pdf 出 4 个 PDF；"
        "并做字体可嵌入化（Type3 → Type0）修正\n"
        "    输入: output/chart-0{1..4}-*.html、~/.workbuddy/skills/diagram-design/scripts/export_svg.py 与 self_check.py\n"
        "    预期产出: output/export/ 下 4 个 .svg ＋ 4 个 .pdf\n"
        "    验证方式: self_check.py --offline 对 4 个 SVG rc=0；SVG 全部 XML 良构且零脚本/零远程引用；"
        "PDF 回读（PyMuPDF）单页、尺寸 750×375pt 与 1000×500px@96dpi 吻合、文本可提取、**Type3=0**、字体全嵌入\n"
        "    状态: 完成\n"
        "    交付物: tasks/落地-科研模式接入diagram-design-2026-10-11/output/export/chart-01-bar.pdf、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/export/chart-02-line.pdf、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/export/chart-03-heatmap.pdf、"
        "tasks/落地-科研模式接入diagram-design-2026-10-11/output/export/chart-04-scatter.pdf\n"
    ),
    (
        "s11",
        "   - id: s11\n"
        "    做什么: 动效通道最小实跑 —— 把柱状图做成 `step` 模式可播放图（4 步 / 7 项 / 每步 ≤2 项），"
        "控制器从 assets/template-motion.html 运行时提取以保证逐字一致\n"
        "    输入: ~/.workbuddy/skills/diagram-design/assets/template-motion.html、references/animation.md\n"
        "    预期产出: output/chart-05-bar-motion.html\n"
        "    验证方式: self_check.py rc=0（含 check_motion 与 check_scripts：控制器归一化后与模板相等）；"
        "自证断言「控制器与模板归一化后相等」= True；Chrome 实跑三态 DOM —— 无参 data-frame=start/step=0、"
        "?motion=static data-frame=static/step=4、?motion=step&step=2 data-frame=step/step=2；"
        "截图比对 static 与 step4 **逐字节相同**（证明静态帧=完整帧）\n"
        "    状态: 完成\n"
        "    交付物: tasks/落地-科研模式接入diagram-design-2026-10-11/output/chart-05-bar-motion.html\n"
    ),
]

TRACE_RECS = [
    {
        "ts": "2026-10-11 17:02",
        "step": "s10",
        "action": "导出投稿级 SVG/PDF（export_svg.py + Chrome 无头打印）",
        "cmd": "export_svg.py --system-fonts ; s10_export_pdf.py",
        "result": "4 SVG self_check --offline rc=0；4 PDF 单页 750x375pt、Type3=0、字体全嵌入",
    },
    {
        "ts": "2026-10-11 17:02",
        "step": "s11",
        "action": "动效通道 step 模式实跑（控制器取自模板，逐字一致）",
        "cmd": "s11_gen_motion.py ; chrome --dump-dom/screenshot",
        "result": "self_check rc=0；三态 DOM 合契约；static 与 step4 截图 md5 相同",
    },
]

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

raw = TRACE.read_bytes()
c0, l0 = raw.count(b"\r\n"), raw.count(b"\n") - raw.count(b"\r\n")
print(f"[INFO] trace 追加前 CRLF={c0} loneLF={l0}")
for rec in TRACE_RECS:
    if f'"step": "{rec["step"]}"'.encode() in raw:
        print(f"[SKIP] {rec['step']} 已在 trace")
        continue
    with TRACE.open("a", encoding="utf-8", newline="") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\r\n")
    print(f"[OK] trace 追加 {rec['step']}")
    raw = TRACE.read_bytes()

# 回读断言
back = PLAN.read_text(encoding="utf-8")
for sid, _ in STEPS:
    assert back.count(f"- id: {sid}") == 1, f"plan {sid} 回读失败"
b = TRACE.read_bytes()
lone = b.count(b"\n") - b.count(b"\r\n")
assert lone == 0, f"trace 出现异类 loneLF={lone}"
for sid, _ in STEPS:
    assert b.count(f'"step": "{sid}"'.encode()) == 1, f"trace {sid} 回读失败"
nl = b.count(b"\r\n")
print(f"[ASSERT] plan s10/s11 各 1 次；trace s10/s11 各 1 次；trace 纯 CRLF（{nl} 行）")
