# -*- coding: utf-8 -*-
"""s11 —— 动效通道（step 模式）：分年度收益柱状图，4 步逐年揭示。

本轮（重构）改动：
  · 几何 / 令牌 / 页面外壳**全部改由 chartlib 提供**（原先在本文件内联了一份，与 s9 各存
    一份 —— 两份一旦漂移，同一张图的静态版与动效版会悄悄长得不一样，且无判据能发现）。
  · 修正一处**契约缺口**：`--motion-total` 原先从模板原样继承 `3600ms`（那是模板自己
    5 步的值），而本图是 4 步 ⇒ 按 animation.md 第 109 行必须是 `步数 × --motion-hold`
    = `4 × 720 = 2880ms`。现由 `chartlib.motion_page()` 按步数算出。

契约（只读，零改动）：
  references/animation.md · assets/template-motion.html
  · 控制器**运行时从模板提取**（不手抄）⇒ check_scripts 的「归一化后完全相等」必然成立。
  · `step` 模式：4 步、7 项、每步 ≤2 项、语义步连续 1..4、每项带非颜色 aria-label。
  · **源码态完整**：不加 JS 时 7 根柱体全部可见；隐藏只由 `.motion-ready` 触发。
"""

import pathlib
import sys

TASK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TASK))
import chartlib as C  # noqa: E402

OUT = TASK / "output"

# (step, 年份, 数值, aria-label) —— 与 DATASETS["annual_returns"] 同源，数值不另抄
STEPS = {
    "2019": (1, "第 1 步：2019 年收益 +38.2%，为区间最高"),
    "2020": (1, "第 1 步：2020 年收益 +25.1%"),
    "2021": (2, "第 2 步：2021 年收益 -12.4%，转为下跌"),
    "2022": (2, "第 2 步：2022 年收益 -21.3%，回撤最深"),
    "2023": (3, "第 3 步：2023 年收益 +6.8%，恢复为正"),
    "2024": (3, "第 3 步：2024 年收益 +18.5%"),
    "2025": (4, "第 4 步：2025 年收益 +12.9%，七年收官"),
}


def main() -> int:
    d = C.DATASETS["annual_returns"]
    labels, values = d["labels"], d["values"]
    # 与 build_bar 的入参一一对应；顺序即 DOM 顺序 = 叙事顺序（animation.md 第 26 行）
    item_steps = [(STEPS[lb][0], STEPS[lb][1]) for lb in labels]

    inner = C.build_bar(d["unit"], labels, values, item_steps=item_steps)
    svg = C.motion_svg(
        inner, aria=("motion-bar-title", "motion-bar-desc"),
        title=f"分年度收益率 · {labels[0]}–{labels[-1]} 逐年揭示",
        desc=(f"柱状图按年份分四步揭示 {labels[0]} 至 {labels[-1]} 的年度收益率："
              f"{labels[0]} 与 {labels[1]} 为正，{labels[2]} 与 {labels[3]} 转负，"
              f"{labels[4]} 起恢复为正。红为上涨、绿为下跌。"),
    )
    html = C.motion_page(
        title="分年度收益率 · 逐年揭示（动效）",
        eyebrow="Bar · Step motion · Diagram Design",
        h1="分年度收益率 · 逐年揭示",
        mode="step", step_count=4, svg=svg,
    )
    p = OUT / "chart-05-bar-motion.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8", newline="\n")
    print(f"[OK] {p.name}  {p.stat().st_size} B")

    # ── 自证（三条，均为硬断言）────────────────────────────────────────────
    import re
    got = re.search(r"<script data-diagram-controls>(.*?)</script>", html, re.S).group(1)
    ok_ctrl = C.controller_identity(got)
    mtotal = re.search(r"--motion-total:\s*(\d+)ms", html).group(1)
    ok_total = int(mtotal) == 4 * C.MOTION_HOLD_MS
    # ⚠️ 计数必须用只在**真实元素**上出现的形态：`[data-motion-item]` 这个选择器在
    #    CSS（4 处）与控制器脚本（1 处）里也各出现一次 ⇒ 用 `re.findall` 数子串会把它们
    #    一并算进来（实测 16 = 7 真实项 + 9 处选择器），从而把自己判成不合格。
    n_items = html.count("data-motion-item data-step=")
    print(f"[ASSERT] 控制器与上游模板归一化后相等: {ok_ctrl}")
    print(f"[ASSERT] --motion-total = 步数×hold = {mtotal}ms（期望 2880ms）: {ok_total}")
    print(f"[ASSERT] data-motion-item 计数 = {n_items}（期望 7 ≤12）: {n_items == 7}")
    if not (ok_ctrl and ok_total and n_items == 7):
        print("[FAIL] 自证未通过")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
