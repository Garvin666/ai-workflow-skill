# -*- coding: utf-8 -*-
"""s11 —— 动效通道最小实跑：把「分年度收益」柱状图做成 `step` 模式可播放图。

严格对齐 `references/animation.md` 与上游判据：
  · 控制器**从 assets/template-motion.html 运行时提取**（不是手抄）⇒ 必然逐字一致；
    上游 self_check 的 check_scripts 要求 script 的 body 与模板**归一化后完全相等**。
  · `step` 模式：4 步、每步 ≤2 项、语义步连续 1..4、7 个 item ≤12、每项带非颜色 aria-label。
  · **源码态完整**：不加 JS 时全部柱体可见（animation.md「Static-first」第 1 条）；
    隐藏只允许由 `.motion-ready` 触发。
  · 静态/打印/reduced-motion 三条路径由模板 CSS 自带。

⚠️ 我方对模板的两处最小偏离（都在产物内可核）：
  1. 字体栈补 CJK 回退（模板无中文字形）；
  2. 文案中文化（按钮与提示），`data-motion-*` 属性与控制器一字不改。
"""

import pathlib
import re

SKILL = pathlib.Path(__file__).resolve().parents[6] / "diagram-design"
TPL = SKILL / "assets" / "template-motion.html"
OUT = (
    pathlib.Path(__file__).resolve().parents[3] / "output"
    / "chart-05-bar-motion.html"
)

PAPER, INK, MUTED, ACCENT, S1 = "#f5f5f5", "#2d3142", "#4f5d75", "#bf4520", "#7c8f6f"
UP, DOWN = ACCENT, S1
FONT_SANS = "'Geist', system-ui, 'Microsoft YaHei', 'PingFang SC', sans-serif"
FONT_MONO = "'Geist Mono', ui-monospace, 'Consolas', monospace"


def extract_template():
    tpl = TPL.read_text(encoding="utf-8")
    style = re.search(r"<style>(.*?)</style>", tpl, re.S).group(1)
    script = re.search(
        r"<script data-diagram-controls>(.*?)</script>", tpl, re.S
    ).group(1)
    return style, script


def bars_svg(items):
    """items: [(step, year, value, aria_label), ...]"""
    labels = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]
    vals = [38.2, 25.1, -12.4, -21.3, 6.8, 18.5, 12.9]
    by_year = {y: (s, a) for s, y, _, a in items}

    x0, x1, ytop, ybase = 80, 960, 40, 420
    n = len(vals)
    pitch = (x1 - x0) / n
    bw, off = 72.0, ((x1 - x0) / n - 72.0) / 2
    vmax, vmin = 45.0, -25.0

    def vy(v):
        return ybase - (v - vmin) / (vmax - vmin) * (ybase - ytop)

    yz = vy(0.0)
    s = []
    s.append(f'        <rect width="100%" height="100%" fill="{PAPER}"/>')
    s.append('        <rect width="100%" height="100%" fill="url(#tp-dots)" opacity="0.55"/>')
    s.append(
        f'        <text transform="rotate(-90 24 230)" x="24" y="230" fill="{MUTED}" '
        f'font-size="7" font-family="{FONT_MONO}" letter-spacing="0.14em" text-anchor="middle">年度收益率 (%)</text>'
    )
    for gv in (-20, -10, 10, 20, 30, 40):
        gy = vy(gv)
        s.append(f'        <line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="rgba(45,49,66,0.08)" stroke-width="0.8"/>')
        s.append(f'        <text x="{x0-8}" y="{gy+3:.1f}" fill="{MUTED}" font-size="8" font-family="{FONT_MONO}" text-anchor="end">{gv}</text>')
    s.append(f'        <line x1="{x0}" y1="{ytop}" x2="{x0}" y2="{ybase}" stroke="rgba(45,49,66,0.25)" stroke-width="1"/>')
    s.append(f'        <line x1="{x0}" y1="{yz:.1f}" x2="{x1}" y2="{yz:.1f}" stroke="rgba(45,49,66,0.38)" stroke-width="1"/>')
    s.append(f'        <text x="{x0-8}" y="{yz+3:.1f}" fill="{INK}" font-size="8" font-family="{FONT_MONO}" text-anchor="end" font-weight="600">0</text>')
    for i, lb in enumerate(labels):
        cx = x0 + i * pitch + off + bw / 2
        s.append(f'        <text x="{cx:.1f}" y="440" fill="{INK}" font-size="11" font-weight="600" font-family="{FONT_SANS}" text-anchor="middle">{lb}</text>')

    for i, (lb, v) in enumerate(zip(labels, vals)):
        step, aria = by_year[lb]
        bx = x0 + i * pitch + off
        yv = vy(v)
        y_t, h = (yv, yz - yv) if v >= 0 else (yz, yv - yz)
        focal = v == max(vals)
        col = UP if v >= 0 else DOWN
        alpha = 0.30 if focal else (0.18 if v >= 0 else 0.22)
        sw = 1.4 if focal else 1.0
        rgb = ",".join(str(int(col[1:][k:k + 2], 16)) for k in (0, 2, 4))
        ly = (yv - 8) if v >= 0 else (yv + 15)
        bold = ' font-weight="600"' if focal else ""
        s.append(f'        <g data-motion-item data-step="{step}" aria-label="{aria}">')
        s.append(f'          <rect x="{bx:.1f}" y="{y_t:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{PAPER}"/>')
        s.append(f'          <rect x="{bx:.1f}" y="{y_t:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="rgba({rgb},{alpha})" stroke="{col}" stroke-width="{sw}"/>')
        s.append(f'          <text x="{bx+bw/2:.1f}" y="{ly:.1f}" fill="{col}" font-size="8" font-family="{FONT_MONO}" text-anchor="middle"{bold}>{v:+.1f}</text>')
        s.append('        </g>')

    s.append('        <line x1="40" y1="462" x2="960" y2="462" stroke="rgba(45,49,66,0.10)" stroke-width="0.8"/>')
    s.append(f'        <text x="40" y="478" fill="{MUTED}" font-size="8" font-family="{FONT_MONO}" letter-spacing="0.18em">图例</text>')
    s.append(f'        <rect x="40" y="488" width="16" height="10" rx="2" fill="rgba(191,69,32,0.18)" stroke="{UP}" stroke-width="1"/>')
    s.append(f'        <text x="64" y="497" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">上涨</text>')
    s.append(f'        <rect x="140" y="488" width="16" height="10" rx="2" fill="rgba(124,143,111,0.22)" stroke="{DOWN}" stroke-width="1"/>')
    s.append(f'        <text x="164" y="497" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">下跌</text>')
    s.append(f'        <rect x="240" y="488" width="16" height="10" rx="2" fill="rgba(191,69,32,0.30)" stroke="{UP}" stroke-width="1.4"/>')
    s.append(f'        <text x="264" y="497" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">区间最高（2019）</text>')
    return "\n".join(s)


def main():
    style, script = extract_template()
    # CJK 回退（模板字体栈无中文字形）
    style = (
        style.replace("'Geist', system-ui, sans-serif", FONT_SANS)
        .replace("'Geist Mono', ui-monospace, monospace", FONT_MONO)
        .replace("'Instrument Serif', 'Noto Serif', 'Noto Serif KR', serif",
                 "'Instrument Serif', 'Songti SC', 'SimSun', 'Microsoft YaHei', serif")
    )

    items = [
        (1, "2019", 38.2, "第 1 步：2019 年收益 +38.2%，为区间最高"),
        (1, "2020", 25.1, "第 1 步：2020 年收益 +25.1%"),
        (2, "2021", -12.4, "第 2 步：2021 年收益 -12.4%，转为下跌"),
        (2, "2022", -21.3, "第 2 步：2022 年收益 -21.3%，回撤最深"),
        (3, "2023", 6.8, "第 3 步：2023 年收益 +6.8%，恢复为正"),
        (3, "2024", 18.5, "第 3 步：2024 年收益 +18.5%"),
        (4, "2025", 12.9, "第 4 步：2025 年收益 +12.9%，七年收官"),
    ]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>分年度收益率 · 逐年揭示（动效）</title>
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>{style}</style>
</head>
<body>
  <main data-motion-root data-motion-mode="step" data-step-count="4" data-step-current="4" data-frame="static" data-static-frame="complete">
    <p class="eyebrow">Bar · Step motion · Diagram Design</p>
    <h1>分年度收益率 · 逐年揭示</h1>

    <div class="diagram-container">
      <svg viewBox="0 0 1000 500" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="motion-bar-title motion-bar-desc">
        <title id="motion-bar-title">分年度收益率 · 2019–2025 逐年揭示</title>
        <desc id="motion-bar-desc">柱状图按年份分四步揭示 2019 至 2025 的年度收益率：2019 与 2020 为正，2021 与 2022 转负，2023 起恢复为正。红为上涨、绿为下跌。</desc>
        <defs>
          <pattern id="tp-dots" width="22" height="22" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="0.9" fill="rgba(45,49,66,0.10)"/>
          </pattern>
        </defs>
{bars_svg(items)}
      </svg>
    </div>

    <div data-motion-controls role="group" aria-label="图示播放控制">
      <button type="button" data-motion-action="prev">上一步</button>
      <button type="button" data-motion-action="play" aria-pressed="false">播放</button>
      <button type="button" data-motion-action="pause" aria-pressed="true">暂停</button>
      <button type="button" data-motion-action="next">下一步</button>
      <button type="button" data-motion-action="replay">重播</button>
      <span class="keyboard-help">←/→ 切换步骤 · 空格 播放/暂停 · R 重播 · Home/End 跳到首/末</span>
      <span data-motion-status-visible aria-hidden="true">第 <span data-motion-step-label>4</span> / 4 步</span>
    </div>

    <p class="sr-only" data-motion-status role="status" aria-live="polite" aria-atomic="true"></p>
    <noscript><p>播放控制需要 JavaScript。上方已展示完整的最终图示。</p></noscript>
  </main>

  <script data-diagram-controls>{script}</script>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8", newline="\n")
    b = OUT.read_bytes()
    print(f"[OK] {OUT.name}  {len(b)} B")
    # 自证：脚本与模板归一化后相等
    got = re.search(r"<script data-diagram-controls>(.*?)</script>", html, re.S).group(1)
    norm = lambda t: t.replace("\r\n", "\n").replace("\r", "\n").strip()
    print("[ASSERT] 控制器与模板归一化后相等:", norm(got) == norm(script))


if __name__ == "__main__":
    main()
