# -*- coding: utf-8 -*-
"""向 diagram-design 任务追加 s9（最小实跑：产 4 张数据图）到 plan.yaml 与 trace.jsonl。

幂等；trace.jsonl 按其自身 CRLF 口径追加。
"""

import json
import pathlib

T = pathlib.Path(__file__).resolve().parent
PLAN, TRACE = T / "plan.yaml", T / "trace.jsonl"

S9 = (
    "  - id: s9\n"
    "    做什么: 最小实跑 —— 用新装的 diagram-design 产 4 张数据类可视化图"
    "（柱状图 / 折线图 / 热力图 / 散点图），程序化生成（不手搓 SVG），"
    "并跑上游 self_check.py 与自建几何自检（判坐标是否越出 viewBox）\n"
    "    输入: ~/.workbuddy/skills/diagram-design 的 references/style-guide.md、"
    "type-{bar,line,heatmap,scatter}.md、assets/example-bar-full.html、scripts/self_check.py\n"
    "    预期产出: output/chart-0{1..4}-*.html（4 个自包含 HTML ＋ 内联 SVG）\n"
    "    验证方式: 4/4 上游 self_check.py rc=0；自建几何自检 越界坐标=0；"
    "几何判据配阴性对照（注入 cx=1180 ⇒ rc=1，证明判据非空）\n"
    "    状态: 完成\n"
    "    交付物: tasks/落地-科研模式接入diagram-design-2026-10-11/output/chart-01-bar.html、"
    "tasks/落地-科研模式接入diagram-design-2026-10-11/output/chart-02-line.html、"
    "tasks/落地-科研模式接入diagram-design-2026-10-11/output/chart-03-heatmap.html、"
    "tasks/落地-科研模式接入diagram-design-2026-10-11/output/chart-04-scatter.html\n"
)

s = PLAN.read_text(encoding="utf-8")
if "- id: s9" in s:
    print("[SKIP] s9 已在 plan.yaml")
else:
    if not s.endswith("\n"):
        s += "\n"
    s += S9
    PLAN.write_text(s, encoding="utf-8", newline="")
    print("[OK] plan.yaml 追加 s9")

raw = TRACE.read_bytes()
crlf = raw.count(b"\r\n")
lone = raw.count(b"\n") - crlf
print(f"[INFO] trace 现况 CRLF={crlf} loneLF={lone}（既有口径 = CRLF）")
if b'"step": "s9"' in raw:
    print("[SKIP] s9 已在 trace")
else:
    rec = {
        "ts": "2026-10-11 16:48",
        "step": "s9",
        "action": "diagram-design 最小实跑：产 4 张数据图（柱/折线/热力/散点）",
        "cmd": "s9_gen_charts.py ; s9b_geom_check.py",
        "result": "4 文件落 output/；self_check 4/4 rc=0；几何越界=0；阴性对照 rc=1 证明判据非空",
    }
    with TRACE.open("a", encoding="utf-8", newline="") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\r\n")
    print("[OK] trace 追加 s9（CRLF）")

# 回读断言
back = PLAN.read_text(encoding="utf-8")
assert back.count("- id: s9") == 1, "plan 回读失败"
b = TRACE.read_bytes()
c, l = b.count(b"\r\n"), b.count(b"\n") - b.count(b"\r\n")
assert l == 0, f"trace 行尾出现异类 loneLF={l}"
assert b.count(b'"step": "s9"') == 1, "trace 回读失败"
print(f"[ASSERT] plan s9 恰 1 次；trace s9 恰 1 次；trace 纯 CRLF（{c} 行）")
