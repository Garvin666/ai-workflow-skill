# -*- coding: utf-8 -*-
"""s9 最小实跑 —— 用 diagram-design 产 4 张数据类可视化图（自包含 HTML + 内联 SVG）。

契约来源（只读，零改动）：
  ~/.workbuddy/skills/diagram-design/references/style-guide.md          令牌
  ~/.workbuddy/skills/diagram-design/references/type-{bar,line,heatmap,scatter}.md  布局约定
  ~/.workbuddy/skills/diagram-design/assets/example-bar-full.html       编辑式外框
  ~/.workbuddy/skills/diagram-design/scripts/self_check.py              验收判据

纯标准库。数据均为**示例数据**（显式标注，不冒充真实统计）。
"""

from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / "output"
OUT.mkdir(parents=True, exist_ok=True)

# ── 令牌（浅色皮肤，取自 style-guide.md） ─────────────────────────────
PAPER = "#f5f5f5"
PAPER2 = "#ececec"
INK = "#2d3142"
MUTED = "#4f5d75"
SOFT = "#5a6580"
ACCENT = "#bf4520"          # 唯一编辑式焦点色
S1 = "#7c8f6f"              # sage
S2 = "#5e7a9b"              # dusty-blue
S3 = "#b8915a"              # mustard
S4 = "#9c6b50"              # rust-brown
RULE = "rgba(45,49,66,0.10)"

# ⭐ 语义色覆盖：A 股「涨红跌绿」—— 这是**有意的皮肤覆盖**，不是编辑式焦点
# （原规范：accent 只给 1–2 个焦点节点；此处 accent 被借作语义「涨」）
UP, DOWN = ACCENT, S1

# 中文回退：上游令牌无 CJK 字形，输出语言为 zh-CN ⇒ 按 style-guide 的可换字体令牌补回退
FONT_SANS = "'Geist', system-ui, 'Microsoft YaHei', 'PingFang SC', sans-serif"
FONT_SERIF = "'Instrument Serif', 'Songti SC', 'SimSun', 'Microsoft YaHei', serif"
FONT_MONO = "'Geist Mono', ui-monospace, 'Cascadia Mono', monospace"
GFONTS = (
    "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1"
    "&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500;600&display=swap"
)

DOT_PATTERN = (
    '        <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">\n'
    '          <circle cx="1" cy="1" r="0.9" fill="rgba(45,49,66,0.10)"/>\n'
    '        </pattern>\n'
)

# ── 页面模板（编辑式外框，取自 example-bar-full.html） ────────────────
CSS = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root { --color-paper:#f5f5f5; --color-paper-2:#ececec; --color-ink:#2d3142; --color-muted:#4f5d75; --color-soft:#5a6580; --color-rule:rgba(45,49,66,0.12); --color-accent:#bf4520; --font-sans:__FS__; --font-serif:__FR__; --font-mono:__FM__; }
    body { font-family: var(--font-sans); background: var(--color-paper); min-height: 100vh; padding: 3rem 2rem; color: var(--color-ink); }
    .container { max-width: 1200px; margin: 0 auto; }
    .header { margin-bottom: 2.5rem; }
    .header-eyebrow { font-family: var(--font-mono); font-size: 0.66rem; font-weight: 500; letter-spacing: 0.18em; text-transform: uppercase; color: var(--color-muted); margin-bottom: 0.75rem; }
    h1 { font-family: var(--font-serif); font-size: clamp(1.75rem, 3vw + 1rem, 2.5rem); font-weight: 400; letter-spacing: -0.02em; line-height: 1.1; margin-bottom: 0.5rem; }
    .subtitle { font-size: 1rem; line-height: 1.55; color: var(--color-muted); max-width: 58ch; }
    .diagram-container { background: var(--color-paper-2); border-radius: 8px; border: 1px solid var(--color-rule); padding: 1.5rem; overflow-x: auto; }
    svg { width: 100%; min-width: 760px; display: block; }
    .cards { display: grid; grid-template-columns: 1.1fr 1fr 0.9fr; gap: 1rem; margin-top: 1.5rem; }
    @media (max-width: 720px) { .cards { grid-template-columns: 1fr; } }
    .card { background: #fff; border-radius: 6px; border: 1px solid var(--color-rule); padding: 1.25rem; }
    .card .eyebrow { font-family: var(--font-mono); font-size: 0.5rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--color-muted); margin-bottom: 0.5rem; }
    .card-header { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.875rem; padding-bottom: 0.875rem; border-bottom: 1px solid rgba(45,49,66,0.08); }
    .card-dot { width: 7px; height: 7px; border-radius: 50%; }
    .card-dot.coral { background: var(--color-accent); } .card-dot.ink { background: var(--color-ink); } .card-dot.muted { background: var(--color-muted); }
    .card h3 { font-size: 0.875rem; font-weight: 600; }
    .card p { color: var(--color-muted); font-size: 0.8125rem; line-height: 1.55; }
    .footer { margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid rgba(45,49,66,0.10); font-family: var(--font-mono); font-size: 0.72rem; letter-spacing: 0.06em; color: var(--color-soft); display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }
""".replace("__FS__", FONT_SANS).replace("__FR__", FONT_SERIF).replace("__FM__", FONT_MONO)

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__TITLE__</title>
  <link href="__GFONTS__" rel="stylesheet">
  <style>__CSS__</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <p class="header-eyebrow">__EYEBROW__</p>
      <h1>__H1__</h1>
      <p class="subtitle">__SUB__</p>
    </div>
    <div class="diagram-container">
__SVG__
    </div>
    <div class="cards">
__CARDS__
    </div>
    <div class="footer">
      <span>__FOOTL__</span>
      <span>__FOOTR__</span>
    </div>
  </div>
</body>
</html>
"""


def card(eyebrow: str, dot: str, h3: str, p: str) -> str:
    eb = f'\n        <p class="eyebrow">{eyebrow}</p>' if eyebrow else ""
    return (
        '      <div class="card">' + eb + "\n"
        f'        <div class="card-header"><span class="card-dot {dot}"></span><h3>{h3}</h3></div>\n'
        f"        <p>{p}</p>\n"
        "      </div>"
    )


def render(fname, *, title, eyebrow, h1, sub, svg, cards, footl, footr) -> Path:
    html = (
        PAGE.replace("__TITLE__", title)
        .replace("__GFONTS__", GFONTS)
        .replace("__CSS__", CSS)
        .replace("__EYEBROW__", eyebrow)
        .replace("__H1__", h1)
        .replace("__SUB__", sub)
        .replace("__SVG__", svg)
        .replace("__CARDS__", "\n".join(cards))
        .replace("__FOOTL__", footl)
        .replace("__FOOTR__", footr)
    )
    p = OUT / fname
    p.write_text(html, encoding="utf-8", newline="\n")
    return p


def axisfont(sz=8, mono=True):
    f = FONT_MONO if mono else FONT_SANS
    return f'font-size="{sz}" font-family="{f}"'


# ══════════════════════════════════════════════════════════════════════
# 1. 柱状图 —— 分年度收益（涨红跌绿）
# ══════════════════════════════════════════════════════════════════════
def chart_bar():
    labels = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]
    vals = [38.2, 25.1, -12.4, -21.3, 6.8, 18.5, 12.9]
    x0, x1, ytop, ybase = 80, 960, 40, 420
    n = len(vals)
    pitch = (x1 - x0) / n
    bw = 72.0
    off = (pitch - bw) / 2
    vmax, vmin = 45.0, -25.0

    def vy(v):
        return ybase - (v - vmin) / (vmax - vmin) * (ybase - ytop)

    yz = vy(0.0)
    s = []
    s.append(f'      <rect width="100%" height="100%" fill="{PAPER}"/>')
    s.append('      <rect width="100%" height="100%" fill="url(#dots)" opacity="0.55"/>')
    s.append(
        f'      <text transform="rotate(-90 24 230)" x="24" y="230" fill="{MUTED}" '
        f'{axisfont(7)} letter-spacing="0.14em" text-anchor="middle">年度收益率 (%)</text>'
    )
    for gv in (-20, -10, 10, 20, 30, 40):
        gy = vy(gv)
        s.append(
            f'      <line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" '
            f'stroke="rgba(45,49,66,0.08)" stroke-width="0.8"/>'
        )
        s.append(
            f'      <text x="{x0-8}" y="{gy+3:.1f}" fill="{MUTED}" {axisfont(8)} '
            f'text-anchor="end">{gv}</text>'
        )
    s.append(
        f'      <line x1="{x0}" y1="{ytop}" x2="{x0}" y2="{ybase}" '
        f'stroke="rgba(45,49,66,0.25)" stroke-width="1"/>'
    )
    s.append(
        f'      <line x1="{x0}" y1="{yz:.1f}" x2="{x1}" y2="{yz:.1f}" '
        f'stroke="rgba(45,49,66,0.38)" stroke-width="1"/>'
    )
    s.append(
        f'      <text x="{x0-8}" y="{yz+3:.1f}" fill="{INK}" {axisfont(8)} '
        f'text-anchor="end" font-weight="600">0</text>'
    )

    for i, (lb, v) in enumerate(zip(labels, vals)):
        bx = x0 + i * pitch + off
        yv = vy(v)
        y_t, h = (yv, yz - yv) if v >= 0 else (yz, yv - yz)
        focal = (v == max(vals))
        col = UP if v >= 0 else DOWN
        alpha = 0.30 if focal else (0.18 if v >= 0 else 0.22)
        sw = 1.4 if focal else 1.0
        s.append(f'      <rect x="{bx:.1f}" y="{y_t:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{PAPER}"/>')
        s.append(
            f'      <rect x="{bx:.1f}" y="{y_t:.1f}" width="{bw:.1f}" height="{h:.1f}" '
            f'fill="rgba({",".join(str(int(col[1:][k:k+2],16)) for k in (0,2,4))},{alpha})" '
            f'stroke="{col}" stroke-width="{sw}"/>'
        )
        ly = (yv - 8) if v >= 0 else (yv + 15)
        s.append(
            f'      <text x="{bx+bw/2:.1f}" y="{ly:.1f}" fill="{col}" {axisfont(8)} '
            f'text-anchor="middle"{" font-weight=\"600\"" if focal else ""}>{v:+.1f}</text>'
        )
        s.append(
            f'      <text x="{bx+bw/2:.1f}" y="440" fill="{INK}" '
            f'font-size="11" font-weight="600" font-family="{FONT_SANS}" '
            f'text-anchor="middle">{lb}</text>'
        )

    s.append(f'      <line x1="40" y1="462" x2="960" y2="462" stroke="{RULE}" stroke-width="0.8"/>')
    s.append(
        f'      <text x="40" y="478" fill="{MUTED}" {axisfont(8)} letter-spacing="0.18em">图例</text>'
    )
    s.append(f'      <rect x="40" y="488" width="16" height="10" rx="2" fill="rgba(191,69,32,0.18)" stroke="{UP}" stroke-width="1"/>')
    s.append(f'      <text x="64" y="497" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">上涨（{UP}）</text>')
    s.append(f'      <rect x="200" y="488" width="16" height="10" rx="2" fill="rgba(124,143,111,0.22)" stroke="{DOWN}" stroke-width="1"/>')
    s.append(f'      <text x="224" y="497" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">下跌（{DOWN}）</text>')
    s.append(f'      <rect x="360" y="488" width="16" height="10" rx="2" fill="rgba(191,69,32,0.30)" stroke="{UP}" stroke-width="1.4"/>')
    s.append(f'      <text x="384" y="497" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">区间最高（2019）</text>')

    svg = (
        '    <svg viewBox="0 0 1000 500" xmlns="http://www.w3.org/2000/svg" '
        'role="img" aria-labelledby="bar-title bar-desc">\n'
        '      <title id="bar-title">分年度收益率 · 2019–2025</title>\n'
        '      <desc id="bar-desc">柱状图展示 2019 至 2025 七个年度的收益率，'
        '2019 年为区间最高（+38.2%），2022 年为最低（−21.3%）。</desc>\n'
        "      <defs>\n" + DOT_PATTERN + "      </defs>\n"
        + "\n".join(s) + "\n    </svg>"
    )
    return render(
        "chart-01-bar.html",
        title="分年度收益率 · 柱状图",
        eyebrow="BAR · DIAGRAM DESIGN",
        h1="分年度收益率 · 2019–2025",
        sub="七个年度的组合收益率。2019 年是区间峰值（+38.2%），2022 年回撤最深（−21.3%）。柱体按 A 股习惯着色：红涨、绿跌。",
        svg=svg,
        cards=[
            card(
                "区间峰值",
                "coral",
                "2019 · +38.2%",
                "峰值不来自加杠杆，而来自当年小盘成长因子的极端占优。柱高记录结果，不记录成因。",
            ),
            card(
                "回撤最深处",
                "muted",
                "2022 · −21.3%",
                "2021–2022 连续两年为负，累计回撤 −31.2%。图中两根绿柱是唯一的连续负收益段。",
            ),
            card(
                "图上看不出的",
                "ink",
                "7 年 6 正 1 负",
                "年度收益掩盖了年内路径。2020 年最高 25.1% 的年份，年内最大回撤达 −14.8%。",
            ),
        ],
        footl="分年度收益率 · 2019–2025",
        footr="示例数据 · 非真实统计 · diagram design",
    )


# ══════════════════════════════════════════════════════════════════════
# 2. 折线图 —— 净值曲线（3 系列）
# ══════════════════════════════════════════════════════════════════════
def chart_line():
    months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
    series = [
        ("策略净值", [1.00, 1.04, 1.02, 1.09, 1.15, 1.12, 1.21, 1.27, 1.24, 1.33, 1.38, 1.44], ACCENT, 1.8, True),
        ("沪深300", [1.00, 1.02, 0.99, 1.03, 1.06, 1.04, 1.09, 1.12, 1.10, 1.15, 1.18, 1.21], S2, 1.2, False),
        ("中证500", [1.00, 0.98, 0.96, 1.01, 1.03, 1.00, 1.06, 1.10, 1.07, 1.12, 1.15, 1.19], S3, 1.2, False),
    ]
    x0, x1, ytop, ybase = 80, 960, 40, 420
    n = len(months)
    step = (x1 - x0) / (n - 1)
    vmax, vmin = 1.45, 0.90

    def pxy(i, v):
        return x0 + i * step, ybase - (v - vmin) / (vmax - vmin) * (ybase - ytop)

    s = []
    s.append(f'      <rect width="100%" height="100%" fill="{PAPER}"/>')
    s.append('      <rect width="100%" height="100%" fill="url(#dots)" opacity="0.55"/>')
    s.append(
        f'      <text transform="rotate(-90 24 230)" x="24" y="230" fill="{MUTED}" '
        f'{axisfont(7)} letter-spacing="0.14em" text-anchor="middle">净值（起点 = 1.00）</text>'
    )
    for gv in (0.9, 1.0, 1.1, 1.2, 1.3, 1.4):
        _, gy = pxy(0, gv)
        s.append(f'      <line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="rgba(45,49,66,0.08)" stroke-width="0.8"/>')
        s.append(f'      <text x="{x0-8}" y="{gy+3:.1f}" fill="{MUTED}" {axisfont(8)} text-anchor="end">{gv:.1f}</text>')
    s.append(f'      <line x1="{x0}" y1="{ytop}" x2="{x0}" y2="{ybase}" stroke="rgba(45,49,66,0.25)" stroke-width="1"/>')
    s.append(f'      <line x1="{x0}" y1="{ybase}" x2="{x1}" y2="{ybase}" stroke="rgba(45,49,66,0.25)" stroke-width="1"/>')

    for i, lb in enumerate(months):
        cx, _ = pxy(i, vmin)
        s.append(
            f'      <text x="{cx:.1f}" y="440" fill="{INK}" font-size="9" '
            f'font-family="{FONT_SANS}" text-anchor="middle">{lb}</text>'
        )

    # 焦点系列面积
    pts = [pxy(i, v) for i, v in enumerate(series[0][1])]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = poly + f" {x1:.1f},{ybase:.1f} {x0:.1f},{ybase:.1f}"
    s.append(f'      <polygon points="{area}" fill="{ACCENT}" opacity="0.08"/>')

    for name, vals, col, sw, focal in series:
        pts = [pxy(i, v) for i, v in enumerate(vals)]
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        s.append(f'      <polyline points="{poly}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linejoin="round"/>')
        if focal:
            for x, y in pts:
                s.append(f'      <circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{col}"/>')

    # 最右端标签
    for idx, (name, vals, col, sw, focal) in enumerate(series):
        x, y = pxy(n - 1, vals[-1])
        dy = (-10, 0, 14)[idx]
        s.append(
            f'      <text x="{x-6:.1f}" y="{y+dy:.1f}" fill="{col}" {axisfont(8)} '
            f'text-anchor="end" font-weight="600">{name} {vals[-1]:.2f}</text>'
        )

    s.append(f'      <line x1="40" y1="462" x2="960" y2="462" stroke="{RULE}" stroke-width="0.8"/>')
    s.append(f'      <text x="40" y="478" fill="{MUTED}" {axisfont(8)} letter-spacing="0.18em">图例</text>')
    lx = 40
    for name, vals, col, sw, focal in series:
        s.append(f'      <line x1="{lx}" y1="493" x2="{lx+18}" y2="493" stroke="{col}" stroke-width="{sw}"/>')
        s.append(f'      <text x="{lx+24}" y="496" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">{name}</text>')
        lx += 170

    svg = (
        '    <svg viewBox="0 0 1000 500" xmlns="http://www.w3.org/2000/svg" '
        'role="img" aria-labelledby="line-title line-desc">\n'
        '      <title id="line-title">净值曲线 · 12 个月三系列对比</title>\n'
        '      <desc id="line-desc">折线图对比策略净值、沪深300、中证500 三条曲线 12 个月走势，'
        '策略净值年末 1.44 领先，沪深300 为 1.21，中证500 为 1.19。</desc>\n'
        "      <defs>\n" + DOT_PATTERN + "      </defs>\n"
        + "\n".join(s) + "\n    </svg>"
    )
    return render(
        "chart-02-line.html",
        title="净值曲线 · 折线图",
        eyebrow="LINE · DIAGRAM DESIGN",
        h1="净值曲线 · 12 个月三系列",
        sub="三条曲线的起点均为 1.00。策略净值年末 1.44，超额主要产生在 4 月与 7 月两个上行段。",
        svg=svg,
        cards=[
            card("焦点系列", "coral", "策略净值 · 1.44", "全段 12 个月仅 3 个月为负；面积填充与顶点圆点只给焦点系列，其余两条只留线。"),
            card("同期基准", "muted", "沪深300 · 1.21", "与策略的差距在 6 月收窄到 0.08，随后在 7 月重新拉开。"),
            card("图上看不出的", "ink", "净值 ≠ 体验", "曲线是月度收盘点连成的。月内路径、申赎摩擦与仓位漂移都不在这条线上。"),
        ],
        footl="净值曲线 · 12 个月三系列",
        footr="示例数据 · 非真实统计 · diagram design",
    )


# ══════════════════════════════════════════════════════════════════════
# 3. 热力图 —— 行业 × 月份收益矩阵
# ══════════════════════════════════════════════════════════════════════
def chart_heatmap():
    rows = ["电子", "医药生物", "电力设备", "食品饮料", "银行", "计算机"]
    cols = ["1月", "2月", "3月", "4月", "5月", "6月"]
    data = [
        [12.4, -6.2, 8.9, 15.1, -3.4, 6.8],
        [-8.7, 4.3, -11.5, 2.6, 7.9, -5.1],
        [15.2, 9.6, -4.8, 11.3, -8.2, 3.7],
        [-2.1, 6.4, 3.2, -1.8, 5.5, -7.3],
        [1.8, 2.9, -0.6, 4.1, 3.3, 2.2],
        [9.7, -9.4, 13.6, -6.8, 10.2, -4.5],
    ]
    left, top, right, bottom = 160, 64, 40, 120
    nr, nc = len(rows), len(cols)
    gap = 4.0
    avail_w = 1000 - left - right
    avail_h = 500 - top - bottom
    cw = (avail_w - gap * (nc - 1)) / nc
    ch = (avail_h - gap * (nr - 1)) / nr
    maxabs = max(abs(v) for r in data for v in r)

    def cellcolor(v):
        a = 0.12 + 0.58 * abs(v) / maxabs
        base = "191,69,32" if v >= 0 else "124,143,111"
        return f"rgba({base},{a:.2f})", a

    s = []
    s.append(f'      <rect width="100%" height="100%" fill="{PAPER}"/>')
    s.append('      <rect width="100%" height="100%" fill="url(#dots)" opacity="0.55"/>')
    s.append(
        f'      <text x="{(left + 1000 - right) / 2:.0f}" y="30" fill="{MUTED}" '
        f'{axisfont(7)} letter-spacing="0.18em" text-anchor="middle">月度收益率 (%)</text>'
    )
    for j, c in enumerate(cols):
        cx = left + j * (cw + gap) + cw / 2
        s.append(f'      <text x="{cx:.1f}" y="52" fill="{INK}" font-size="9" font-family="{FONT_SANS}" text-anchor="middle">{c}</text>')
    for i, r in enumerate(rows):
        cy = top + i * (ch + gap) + ch / 2
        s.append(
            f'      <text x="{left-12:.1f}" y="{cy+3:.1f}" fill="{INK}" font-size="9" '
            f'font-family="{FONT_SANS}" text-anchor="end">{r}</text>'
        )
        for j, v in enumerate(data[i]):
            x = left + j * (cw + gap)
            y = top + i * (ch + gap)
            col, a = cellcolor(v)
            s.append(f'      <rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="{PAPER}"/>')
            s.append(f'      <rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="{col}"/>')
            tc = PAPER if a >= 0.40 else INK
            s.append(
                f'      <text x="{x+cw/2:.1f}" y="{y+ch/2+3:.1f}" fill="{tc}" '
                f'{axisfont(8)} text-anchor="middle">{v:+.1f}</text>'
            )
    # 色带图例
    lgx, lgy, lgw, lgh = left, 452, 340, 12
    steps = 60
    for k in range(steps):
        t = k / (steps - 1)
        col, _ = cellcolor((t * 2 - 1) * maxabs)
        s.append(f'      <rect x="{lgx + k*lgw/steps:.2f}" y="{lgy}" width="{lgw/steps+0.6:.2f}" height="{lgh}" fill="{col}"/>')
    s.append(f'      <text x="{lgx}" y="{lgy-6}" fill="{MUTED}" {axisfont(7)} letter-spacing="0.14em">图例 · 冷绿 ← 0 → 暖红</text>')
    s.append(f'      <text x="{lgx}" y="{lgy+24}" fill="{MUTED}" {axisfont(8)}>{-maxabs:+.1f}%</text>')
    s.append(f'      <text x="{lgx+lgw/2:.0f}" y="{lgy+24}" fill="{MUTED}" {axisfont(8)} text-anchor="middle">0.0%</text>')
    s.append(f'      <text x="{lgx+lgw}" y="{lgy+24}" fill="{MUTED}" {axisfont(8)} text-anchor="end">{maxabs:+.1f}%</text>')
    s.append(f'      <text x="{lgx+lgw+40}" y="{lgy+9}" fill="{MUTED}" font-size="8" font-family="{FONT_SANS}">深色格内文字自动翻为纸白（阈值 α ≥ 0.40）</text>')

    svg = (
        '    <svg viewBox="0 0 1000 500" xmlns="http://www.w3.org/2000/svg" '
        'role="img" aria-labelledby="hm-title hm-desc">\n'
        '      <title id="hm-title">行业 × 月份月度收益率热力图</title>\n'
        '      <desc id="hm-desc">六行行业、六列月份构成的收益矩阵。'
        '电子与电力设备整体偏暖（正收益），医药生物偏冷（负收益），银行行最为平稳。</desc>\n'
        "      <defs>\n" + DOT_PATTERN + "      </defs>\n"
        + "\n".join(s) + "\n    </svg>"
    )
    return render(
        "chart-03-heatmap.html",
        title="行业×月份收益热力图",
        eyebrow="HEATMAP · DIAGRAM DESIGN",
        h1="行业 × 月份 · 月度收益率矩阵",
        sub="六个行业 × 六个月。需要一眼扫完整个矩阵、找出哪几个格子在跳的时候用它 —— 而不是拿来逐格比较。",
        svg=svg,
        cards=[
            card("最暖的格子", "coral", "电子 · 4月 +15.1%", "同一行的 5 月却是 −3.4%。热力图的用途是找「哪一格异常」，不是看趋势方向。"),
            card("最冷的行", "muted", "医药生物 · 4 冷 2 暖", "全行偏冷：−8.7 / −11.5 / −5.1 三个格子构成主要的负贡献。"),
            card("图上看不出的", "ink", "颜色即全部", "格子只有色阶与数值。样本量、换手率、市值分布都不在格子里 —— 极端格子可能是小样本噪声。"),
        ],
        footl="行业 × 月份 · 月度收益率矩阵",
        footr="示例数据 · 非真实统计 · diagram design",
    )


# ══════════════════════════════════════════════════════════════════════
# 4. 散点图 —— 风险 / 收益
# ══════════════════════════════════════════════════════════════════════
def chart_scatter():
    # (名称, 年化波动率%, 年化收益%, 规模权重, 是否焦点)
    pts = [
        ("A", 12.4, 6.8, 1.0, False), ("B", 18.6, 11.2, 1.4, False),
        ("C", 24.1, 9.3, 1.1, False), ("D", 9.8, 3.1, 0.8, False),
        ("E", 28.7, 18.4, 1.8, True), ("F", 15.2, 5.6, 1.0, False),
        ("G", 21.3, 13.7, 1.2, False), ("H", 33.5, 14.9, 1.5, False),
        ("I", 7.2, 2.4, 0.7, False), ("J", 26.4, 7.1, 1.0, False),
        ("K", 17.9, 15.8, 1.3, False), ("L", 30.2, 4.2, 0.9, False),
    ]
    x0, x1, ytop, ybase = 80, 960, 40, 420
    xmax, xmin = 36.0, 5.0
    ymax, ymin = 21.0, 0.0

    def pxy(vx, vyv):
        return (x0 + (vx - xmin) / (xmax - xmin) * (x1 - x0),
                ybase - (vyv - ymin) / (ymax - ymin) * (ybase - ytop))

    s = []
    s.append(f'      <rect width="100%" height="100%" fill="{PAPER}"/>')
    s.append('      <rect width="100%" height="100%" fill="url(#dots)" opacity="0.55"/>')
    s.append(
        f'      <text transform="rotate(-90 24 230)" x="24" y="230" fill="{MUTED}" '
        f'{axisfont(7)} letter-spacing="0.14em" text-anchor="middle">年化收益 (%)</text>'
    )
    s.append(
        f'      <text x="{(x0+x1)/2:.0f}" y="440" fill="{MUTED}" {axisfont(8)} '
        f'letter-spacing="0.14em" text-anchor="middle">年化波动率 (%)</text>'
    )
    for gy in (0, 5, 10, 15, 20):
        _, y = pxy(xmin, gy)
        s.append(f'      <line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="rgba(45,49,66,0.08)" stroke-width="0.8"/>')
        s.append(f'      <text x="{x0-8}" y="{y+3:.1f}" fill="{MUTED}" {axisfont(8)} text-anchor="end">{gy}</text>')
    for gx in (5, 10, 15, 20, 25, 30, 35):
        x, _ = pxy(gx, ymin)
        s.append(f'      <line x1="{x:.1f}" y1="{ytop}" x2="{x:.1f}" y2="{ybase}" stroke="rgba(45,49,66,0.05)" stroke-width="0.8"/>')
        s.append(f'      <text x="{x:.1f}" y="{ybase+16}" fill="{MUTED}" {axisfont(8)} text-anchor="middle">{gx}</text>')
    s.append(f'      <line x1="{x0}" y1="{ytop}" x2="{x0}" y2="{ybase}" stroke="rgba(45,49,66,0.25)" stroke-width="1"/>')
    s.append(f'      <line x1="{x0}" y1="{ybase}" x2="{x1}" y2="{ybase}" stroke="rgba(45,49,66,0.25)" stroke-width="1"/>')

    # 中位数分割线
    xs = sorted(p[1] for p in pts)
    ys = sorted(p[2] for p in pts)
    mx = (xs[5] + xs[6]) / 2
    my = (ys[5] + ys[6]) / 2
    mxp, _ = pxy(mx, ymin)
    _, myp = pxy(xmin, my)
    s.append(f'      <line x1="{mxp:.1f}" y1="{ytop}" x2="{mxp:.1f}" y2="{ybase}" stroke="{MUTED}" stroke-width="0.8" stroke-dasharray="4,3" opacity="0.55"/>')
    s.append(f'      <line x1="{x0}" y1="{myp:.1f}" x2="{x1}" y2="{myp:.1f}" stroke="{MUTED}" stroke-width="0.8" stroke-dasharray="4,3" opacity="0.55"/>')

    for name, vx, vyv, w, focal in pts:
        x, y = pxy(vx, vyv)
        r = 5.0 + 2.4 * w if not focal else 6.0 + 2.4 * w
        if focal:
            s.append(f'      <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{PAPER}"/>')
            s.append(f'      <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="rgba(191,69,32,0.15)" stroke="{ACCENT}" stroke-width="1.2"/>')
            s.append(f'      <text x="{x+r+5:.1f}" y="{y+3:.1f}" fill="{ACCENT}" {axisfont(8)} font-weight="600">{name} 波动 28.7 / 收益 18.4</text>')
        else:
            s.append(f'      <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{PAPER}"/>')
            s.append(f'      <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="rgba(79,93,117,0.20)" stroke="{MUTED}" stroke-width="1"/>')

    # 参考线：等夏普 0.55（过 (xmin, 0)、斜率 0.55）
    # 坐标 y 向下增长 ⇒ 「越出画布上沿」的判据是 py < ytop，不是 py > ytop
    SLOPE = 0.55
    px0, py0 = pxy(xmin, 0.0)
    px1, py1 = pxy(xmax, (xmax - xmin) * SLOPE)
    if py1 < ytop:  # 越出上沿则改为在上沿处收口
        py1 = ytop
        px1 = x0 + ((ymax / SLOPE) - xmin) / (xmax - xmin) * (x1 - x0)
        px1 = min(px1, x1)
    s.append(f'      <line x1="{px0:.1f}" y1="{py0:.1f}" x2="{px1:.1f}" y2="{py1:.1f}" stroke="{INK}" stroke-width="0.9" stroke-dasharray="5,4" opacity="0.28"/>')
    lx, ly = pxy(xmax - 3.0, (xmax - 3.0 - xmin) * SLOPE)
    s.append(f'      <text x="{lx:.1f}" y="{ly-6:.1f}" fill="{MUTED}" {axisfont(8)} text-anchor="end">等夏普参考线 · {SLOPE}</text>')

    s.append(f'      <line x1="40" y1="462" x2="960" y2="462" stroke="{RULE}" stroke-width="0.8"/>')
    s.append(f'      <text x="40" y="478" fill="{MUTED}" {axisfont(8)} letter-spacing="0.18em">图例</text>')
    s.append(f'      <circle cx="48" cy="492" r="6" fill="rgba(191,69,32,0.15)" stroke="{ACCENT}" stroke-width="1.2"/>')
    s.append(f'      <text x="62" y="495" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">单位风险收益最优标的</text>')
    s.append(f'      <circle cx="250" cy="492" r="6" fill="rgba(79,93,117,0.20)" stroke="{MUTED}" stroke-width="1"/>')
    s.append(f'      <text x="264" y="495" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">其它标的（气泡大小 = 规模权重）</text>')

    svg = (
        '    <svg viewBox="0 0 1000 500" xmlns="http://www.w3.org/2000/svg" '
        'role="img" aria-labelledby="sc-title sc-desc">\n'
        '      <title id="sc-title">风险—收益散点图 · 12 只标的</title>\n'
        '      <desc id="sc-desc">散点图以年化波动率为横轴、年化收益为纵轴，'
        '展示 12 只标的；标的 E（波动 28.7%、收益 18.4%）单位风险收益最优。</desc>\n'
        "      <defs>\n" + DOT_PATTERN + "      </defs>\n"
        + "\n".join(s) + "\n    </svg>"
    )
    return render(
        "chart-04-scatter.html",
        title="风险—收益散点图",
        eyebrow="SCATTER · DIAGRAM DESIGN",
        h1="风险 — 收益 · 12 只标的",
        sub="横轴年化波动率、纵轴年化收益。虚线为中位数分割线，斜虚线是 0.55 的等夏普参考线 —— 在它左上方才是「单位风险更划算」。",
        svg=svg,
        cards=[
            card("单位风险最优", "coral", "标的 E", "波动 28.7% 不是最低，但收益 18.4% 使其落在等夏普参考线左上方 —— 高波动不等于高性价比。"),
            card("右下角的陷阱", "muted", "标的 L / J / H", "高波动 + 低收益：三者都在参考线右下方，属于「多承担了风险却没换来收益」。"),
            card("图上看不出的", "ink", "相关性与容量", "散点只说单标的的风险收益，不说它们之间的相关性，也不说策略容量。"),
        ],
        footl="风险 — 收益 · 12 只标的",
        footr="示例数据 · 非真实统计 · diagram design",
    )


def main():
    made = [chart_bar(), chart_line(), chart_heatmap(), chart_scatter()]
    for p in made:
        b = p.read_bytes()
        print(f"[OK] {p.name}  {len(b)} B")
    print(f"\n共 {len(made)} 个文件 -> {OUT}")


if __name__ == "__main__":
    main()
