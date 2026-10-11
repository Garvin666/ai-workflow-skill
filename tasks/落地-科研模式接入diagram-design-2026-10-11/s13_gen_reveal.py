# -*- coding: utf-8 -*-
"""s13 —— 动效通道（reveal 模式）：同一柱状图的**自动播放一次**变体。

与 s11（step）的关系：
  · **同一份数据、同一份几何**（都取自 chartlib）⇒ 两个变体不会漂移；
  · **同一段 canonical 控制器**（chartlib.motion_assets 运行时从上游模板提取）
    ⇒ 不存在第二个控制器，`self_check` 的「控制器唯一且逐字相等」必然成立；
  · **唯一差别** = `data-motion-mode="step"` → `"reveal"`。

契约依据（references/animation.md）：
  · 第 12 行：`reveal` = **一次确定性自动播放、终态完整**；
  · 第 18 行：`reveal` 是**唯一被许可的自动播放模式** —— 首载跑一次，**从不**
    在视口重现时重启，**只能**由显式 Replay 触发再做一次；
  · 上游 canonical 控制器**原生实现**该模式（模板第 433-436 行：`render(0)` → `play()`）
    ⇒ 我**不需要也不允许**另写控制器（第 93 行：改控制器会被 skin linter 拒收）。
"""

import pathlib
import re
import sys

TASK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TASK))
import chartlib as C  # noqa: E402

OUT = TASK / "output"

# 与 s11 共用同一份步/标签定义（从 s11 导入，避免两处各写一份后漂移）
from s11_gen_motion import STEPS  # noqa: E402


def main() -> int:
    d = C.DATASETS["annual_returns"]
    labels, values = d["labels"], d["values"]
    item_steps = [(STEPS[lb][0], STEPS[lb][1]) for lb in labels]

    inner = C.build_bar(d["unit"], labels, values, item_steps=item_steps)
    svg = C.motion_svg(
        inner, aria=("reveal-bar-title", "reveal-bar-desc"),
        title=f"分年度收益率 · {labels[0]}–{labels[-1]} 自动揭示",
        desc=(f"柱状图按年份自动揭示 {labels[0]} 至 {labels[-1]} 的年度收益率，"
              f"播放一次后停在完整终态：{labels[0]}、{labels[1]}、{labels[4]}、"
              f"{labels[5]}、{labels[6]} 为正，{labels[2]}、{labels[3]} 为负。"
              f"红为上涨、绿为下跌。"),
    )
    html = C.motion_page(
        title="分年度收益率 · 自动揭示（动效）",
        eyebrow="Bar · Reveal motion · Diagram Design",
        h1="分年度收益率 · 自动揭示",
        mode="reveal", step_count=4, svg=svg,
    )
    p = OUT / "chart-06-bar-reveal.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8", newline="\n")
    print(f"[OK] {p.name}  {p.stat().st_size} B")

    # ── 自证（四条硬断言）────────────────────────────────────────────────
    got = re.search(r"<script data-diagram-controls>(.*?)</script>", html, re.S).group(1)
    ok_ctrl = C.controller_identity(got)
    ok_mode = 'data-motion-mode="reveal"' in html
    mtotal = re.search(r"--motion-total:\s*(\d+)ms", html).group(1)
    ok_total = int(mtotal) == 4 * C.MOTION_HOLD_MS
    # 与 step 版做**差异最小化**证明：唯一差别应只落在 mode 与文案上
    step_html = (OUT / "chart-05-bar-motion.html").read_text(encoding="utf-8")
    la = [l.strip() for l in html.splitlines() if l.strip()]
    lb = [l.strip() for l in step_html.splitlines() if l.strip()]
    sb = set(lb)
    uniq_a = [l for l in la if l not in sb]
    uniq_b = [l for l in lb if l not in set(la)]
    print(f"[ASSERT] 控制器与上游模板归一化后相等: {ok_ctrl}")
    print(f"[ASSERT] data-motion-mode=reveal: {ok_mode}")
    print(f"[ASSERT] --motion-total = {mtotal}ms（期望 2880ms）: {ok_total}")
    print(f"[INFO  ] 与 step 版的差异行：reveal 独有 {len(uniq_a)}，step 独有 {len(uniq_b)}")
    for l in uniq_a[:6]:
        print(f"           + {l[:88]}")
    for l in uniq_b[:6]:
        print(f"           - {l[:88]}")
    if not (ok_ctrl and ok_mode and ok_total):
        print("[FAIL] 自证未通过")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
