# -*- coding: utf-8 -*-
"""数据图生成库 —— 本任务自研的**共享单一来源**（不是上游资产）。

被下列脚本共用：
  s9_gen_charts.py   静态 4 图
  s11_gen_motion.py  step 模式动效图
  s13_gen_reveal.py  reveal 模式动效图

抽取目的（本轮「代码可读性与一致性」改进）：原先令牌 / 字体栈 / 页面模板 / 柱状图几何
在 s9 与 s11 里**各写一份** —— 两份一旦漂移，同一张图的两个变体会长得不一样，而且没有任何
判据能发现。现在只有一处。

对外只暴露：TOKEN 常量、PAGE_* 模板、card()/axisfont()/render_page() 组装件、
build_*() 四个图构建器、DATASETS 数据配置，以及动效外壳 motion_assets()/motion_page()/
motion_svg()/controller_identity()。
"""

from pathlib import Path
import pathlib
import re

# ══════════════════════════════════════════════════════════════════════
# 一、令牌（取自 diagram-design/references/style-guide.md 浅色皮肤）
# ══════════════════════════════════════════════════════════════════════
PAPER = "#f5f5f5"
PAPER2 = "#ececec"
INK = "#2d3142"
MUTED = "#4f5d75"
SOFT = "#5a6580"
ACCENT = "#bf4520"      # 上游唯一编辑式焦点色
S1 = "#7c8f6f"          # sage
S2 = "#5e7a9b"          # dusty-blue
S3 = "#b8915a"          # mustard
S4 = "#9c6b50"          # rust-brown
RULE = "rgba(45,49,66,0.10)"
GRID = "rgba(45,49,66,0.08)"
AXIS = "rgba(45,49,66,0.25)"

# ⭐ 语义色覆盖：A 股「涨红跌绿」—— 有意的皮肤覆盖（上游规定 accent 只给 1–2 焦点节点）
UP, DOWN = ACCENT, S1

# ⭐ 中文回退：上游字体令牌无 CJK 字形。**唯一定义处** —— 导出侧（exportlib）也引用这里，
# 避免「生成用一套、导出替换另一套」的漂移。
FONT_SANS = "'Geist', system-ui, 'Microsoft YaHei', 'PingFang SC', sans-serif"
FONT_SERIF = "'Instrument Serif', 'Songti SC', 'SimSun', 'Microsoft YaHei', serif"
FONT_MONO = "'Geist Mono', ui-monospace, 'Cascadia Mono', monospace"

# 导出/打印时替换为**可嵌入的 TrueType**，否则 Chrome 会把缺字回退落成 Type3 字体
# （Type3 虽为矢量，部分期刊明确拒收）。键与上面三个常量一一对应。
FONT_EMBEDDABLE = {
    FONT_MONO: "Consolas, 'Microsoft YaHei', monospace",
    FONT_SANS: "'Microsoft YaHei', Consolas, sans-serif",
    FONT_SERIF: "'Microsoft YaHei', Consolas, serif",
}

GFONTS = (
    "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1"
    "&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500;600&display=swap"
)

DOT_PATTERN = (
    '        <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">\n'
    '          <circle cx="1" cy="1" r="0.9" fill="rgba(45,49,66,0.10)"/>\n'
    '        </pattern>\n'
)


def hex_rgb(color: str) -> str:
    """'#bf4520' -> '191,69,32'（rgba() 里用）。集中一处，避免各处手拼。"""
    c = color.lstrip("#")
    return ",".join(str(int(c[k:k + 2], 16)) for k in (0, 2, 4))


def rgba(color: str, alpha: float) -> str:
    return f"rgba({hex_rgb(color)},{alpha})"


def axisfont(size: int = 8, mono: bool = True) -> str:
    """SVG 文本的 font-size + font-family 属性串。"""
    return f'font-size="{size}" font-family="{FONT_MONO if mono else FONT_SANS}"'


# ══════════════════════════════════════════════════════════════════════
# 二、页面模板（编辑式外框，形制取自上游 assets/example-bar-full.html）
# ══════════════════════════════════════════════════════════════════════
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


def render_page(spec: dict, out_dir: Path) -> Path:
    """spec 键：fname/title/eyebrow/h1/sub/svg/cards/footl/footr。"""
    html = (
        PAGE.replace("__TITLE__", spec["title"])
        .replace("__GFONTS__", GFONTS)
        .replace("__CSS__", CSS)
        .replace("__EYEBROW__", spec["eyebrow"])
        .replace("__H1__", spec["h1"])
        .replace("__SUB__", spec["sub"])
        .replace("__SVG__", spec["svg"])
        .replace("__CARDS__", "\n".join(spec["cards"]))
        .replace("__FOOTL__", spec["footl"])
        .replace("__FOOTR__", spec["footr"])
    )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / spec["fname"]
    p.write_text(html, encoding="utf-8", newline="\n")
    return p


def wrap_svg(inner: str, *, viewbox: str, aria: tuple[str, str],
             title: str, desc: str) -> str:
    """包出合法的自包含 SVG：无障碍契约（role=img + aria-labelledby + title + desc）。"""
    t_id, d_id = aria
    return (
        f'    <svg viewBox="{viewbox}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-labelledby="{t_id} {d_id}">\n'
        f'      <title id="{t_id}">{title}</title>\n'
        f'      <desc id="{d_id}">{desc}</desc>\n'
        "      <defs>\n" + DOT_PATTERN + "      </defs>\n"
        + inner + "\n    </svg>"
    )


# ══════════════════════════════════════════════════════════════════════
# 三、数据配置（**示例数据**，全库唯一来源；改数据只改这里）
# ══════════════════════════════════════════════════════════════════════
DATASETS = {
    "annual_returns": {
        "labels": ["2019", "2020", "2021", "2022", "2023", "2024", "2025"],
        "values": [38.2, 25.1, -12.4, -21.3, 6.8, 18.5, 12.9],
        "unit": "年度收益率 (%)",
    },
    "nav_curves": {
        "labels": ["1月", "2月", "3月", "4月", "5月", "6月",
                   "7月", "8月", "9月", "10月", "11月", "12月"],
        "series": [
            ("策略净值", [1.00, 1.04, 1.02, 1.09, 1.15, 1.12, 1.21, 1.27, 1.24, 1.33, 1.38, 1.44], ACCENT, 1.8, True),
            ("沪深300", [1.00, 1.02, 0.99, 1.03, 1.06, 1.04, 1.09, 1.12, 1.10, 1.15, 1.18, 1.21], S2, 1.2, False),
            ("中证500", [1.00, 0.98, 0.96, 1.01, 1.03, 1.00, 1.06, 1.10, 1.07, 1.12, 1.15, 1.19], S3, 1.2, False),
        ],
        "unit": "净值（起点 = 1.00）",
    },
    "industry_months": {
        "rows": ["电子", "医药生物", "电力设备", "食品饮料", "银行", "计算机"],
        "cols": ["1月", "2月", "3月", "4月", "5月", "6月"],
        "data": [
            [12.4, -6.2, 8.9, 15.1, -3.4, 6.8],
            [-8.7, 4.3, -11.5, 2.6, 7.9, -5.1],
            [15.2, 9.6, -4.8, 11.3, -8.2, 3.7],
            [-2.1, 6.4, 3.2, -1.8, 5.5, -7.3],
            [1.8, 2.9, -0.6, 4.1, 3.3, 2.2],
            [9.7, -9.4, 13.6, -6.8, 10.2, -4.5],
        ],
        "unit": "月度收益率 (%)",
    },
    "risk_return": {
        # (名称, 年化波动率%, 年化收益%, 规模权重, 是否焦点)
        "points": [
            ("A", 12.4, 6.8, 1.0, False), ("B", 18.6, 11.2, 1.4, False),
            ("C", 24.1, 9.3, 1.1, False), ("D", 9.8, 3.1, 0.8, False),
            ("E", 28.7, 18.4, 1.8, True), ("F", 15.2, 5.6, 1.0, False),
            ("G", 21.3, 13.7, 1.2, False), ("H", 33.5, 14.9, 1.5, False),
            ("I", 7.2, 2.4, 0.7, False), ("J", 26.4, 7.1, 1.0, False),
            ("K", 17.9, 15.8, 1.3, False), ("L", 30.2, 4.2, 0.9, False),
        ],
    },
}

# 条形图/散点/折线共用的绘图区（viewBox 0 0 1000 500）
PLOT = {"x0": 80, "x1": 960, "ytop": 40, "ybase": 420}


# ══════════════════════════════════════════════════════════════════════
# 四、四个图构建器 —— 只产「SVG 内部」，由调用方决定是否包 item 组（动效需要）
# ══════════════════════════════════════════════════════════════════════
def build_bar(unit: str, labels: list[str], values: list[float],
              item_steps: list[tuple[int, str]] | None = None) -> str:
    """柱状图。item_steps 给定则每根柱包进 <g data-motion-item>（动效用）。

    item_steps: [(step, aria_label), ...] 与 labels 等长。
    """
    x0, x1, ytop, ybase = PLOT["x0"], PLOT["x1"], PLOT["ytop"], PLOT["ybase"]
    n = len(values)
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
        f'{axisfont(7)} letter-spacing="0.14em" text-anchor="middle">{unit}</text>'
    )
    for gv in (-20, -10, 10, 20, 30, 40):
        gy = vy(gv)
        s.append(f'      <line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="0.8"/>')
        s.append(f'      <text x="{x0-8}" y="{gy+3:.1f}" fill="{MUTED}" {axisfont(8)} text-anchor="end">{gv}</text>')
    s.append(f'      <line x1="{x0}" y1="{ytop}" x2="{x0}" y2="{ybase}" stroke="{AXIS}" stroke-width="1"/>')
    s.append(f'      <line x1="{x0}" y1="{yz:.1f}" x2="{x1}" y2="{yz:.1f}" stroke="rgba(45,49,66,0.38)" stroke-width="1"/>')
    s.append(f'      <text x="{x0-8}" y="{yz+3:.1f}" fill="{INK}" {axisfont(8)} text-anchor="end" font-weight="600">0</text>')

    for i, (lb, v) in enumerate(zip(labels, values)):
        bx = x0 + i * pitch + off
        yv = vy(v)
        y_t, h = (yv, yz - yv) if v >= 0 else (yz, yv - yz)
        focal = v == max(values)
        col = UP if v >= 0 else DOWN
        alpha = 0.30 if focal else (0.18 if v >= 0 else 0.22)
        sw = 1.4 if focal else 1.0
        ly = (yv - 8) if v >= 0 else (yv + 15)
        bold = ' font-weight="600"' if focal else ""
        ind = "        "
        if item_steps:
            step, aria = item_steps[i]
            s.append(f'{ind}<g data-motion-item data-step="{step}" aria-label="{aria}">')
            ind = "          "
        s.append(f'{ind}<rect x="{bx:.1f}" y="{y_t:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{PAPER}"/>')
        s.append(f'{ind}<rect x="{bx:.1f}" y="{y_t:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="{rgba(col, alpha)}" stroke="{col}" stroke-width="{sw}"/>')
        s.append(f'{ind}<text x="{bx+bw/2:.1f}" y="{ly:.1f}" fill="{col}" {axisfont(8)} text-anchor="middle"{bold}>{v:+.1f}</text>')
        if item_steps:
            s.append("        </g>")

    for i, lb in enumerate(labels):
        cx = x0 + i * pitch + off + bw / 2
        s.append(
            f'      <text x="{cx:.1f}" y="440" fill="{INK}" font-size="11" '
            f'font-weight="600" font-family="{FONT_SANS}" text-anchor="middle">{lb}</text>'
        )
    s.append(f'      <line x1="40" y1="462" x2="960" y2="462" stroke="{RULE}" stroke-width="0.8"/>')
    s.append(f'      <text x="40" y="478" fill="{MUTED}" {axisfont(8)} letter-spacing="0.18em">图例</text>')
    s.append(f'      <rect x="40" y="488" width="16" height="10" rx="2" fill="{rgba(UP, 0.18)}" stroke="{UP}" stroke-width="1"/>')
    s.append(f'      <text x="64" y="497" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">上涨（{UP}）</text>')
    s.append(f'      <rect x="200" y="488" width="16" height="10" rx="2" fill="{rgba(DOWN, 0.22)}" stroke="{DOWN}" stroke-width="1"/>')
    s.append(f'      <text x="224" y="497" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">下跌（{DOWN}）</text>')
    s.append(f'      <rect x="360" y="488" width="16" height="10" rx="2" fill="{rgba(UP, 0.30)}" stroke="{UP}" stroke-width="1.4"/>')
    s.append(f'      <text x="384" y="497" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">区间最高（{labels[values.index(max(values))]}）</text>')
    return "\n".join(s)


def build_line(unit: str, labels: list[str], series: list) -> str:
    x0, x1, ytop, ybase = PLOT["x0"], PLOT["x1"], PLOT["ytop"], PLOT["ybase"]
    n = len(labels)
    step = (x1 - x0) / (n - 1)
    vmax, vmin = 1.45, 0.90

    def pxy(i, v):
        return x0 + i * step, ybase - (v - vmin) / (vmax - vmin) * (ybase - ytop)

    s = [f'      <rect width="100%" height="100%" fill="{PAPER}"/>',
         '      <rect width="100%" height="100%" fill="url(#dots)" opacity="0.55"/>',
         f'      <text transform="rotate(-90 24 230)" x="24" y="230" fill="{MUTED}" '
         f'{axisfont(7)} letter-spacing="0.14em" text-anchor="middle">{unit}</text>']
    for gv in (0.9, 1.0, 1.1, 1.2, 1.3, 1.4):
        _, gy = pxy(0, gv)
        s.append(f'      <line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="0.8"/>')
        s.append(f'      <text x="{x0-8}" y="{gy+3:.1f}" fill="{MUTED}" {axisfont(8)} text-anchor="end">{gv:.1f}</text>')
    s.append(f'      <line x1="{x0}" y1="{ytop}" x2="{x0}" y2="{ybase}" stroke="{AXIS}" stroke-width="1"/>')
    s.append(f'      <line x1="{x0}" y1="{ybase}" x2="{x1}" y2="{ybase}" stroke="{AXIS}" stroke-width="1"/>')
    for i, lb in enumerate(labels):
        cx, _ = pxy(i, vmin)
        s.append(f'      <text x="{cx:.1f}" y="440" fill="{INK}" font-size="9" font-family="{FONT_SANS}" text-anchor="middle">{lb}</text>')

    pts = [pxy(i, v) for i, v in enumerate(series[0][1])]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    s.append(f'      <polygon points="{poly} {x1:.1f},{ybase:.1f} {x0:.1f},{ybase:.1f}" fill="{ACCENT}" opacity="0.08"/>')

    for name, vals, col, sw, focal in series:
        pts = [pxy(i, v) for i, v in enumerate(vals)]
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        s.append(f'      <polyline points="{poly}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linejoin="round"/>')
        if focal:
            for x, y in pts:
                s.append(f'      <circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{col}"/>')
    for idx, (name, vals, col, sw, focal) in enumerate(series):
        x, y = pxy(n - 1, vals[-1])
        dy = (-10, 0, 14)[idx]
        s.append(f'      <text x="{x-6:.1f}" y="{y+dy:.1f}" fill="{col}" {axisfont(8)} text-anchor="end" font-weight="600">{name} {vals[-1]:.2f}</text>')
    s.append(f'      <line x1="40" y1="462" x2="960" y2="462" stroke="{RULE}" stroke-width="0.8"/>')
    s.append(f'      <text x="40" y="478" fill="{MUTED}" {axisfont(8)} letter-spacing="0.18em">图例</text>')
    lx = 40
    for name, vals, col, sw, focal in series:
        s.append(f'      <line x1="{lx}" y1="493" x2="{lx+18}" y2="493" stroke="{col}" stroke-width="{sw}"/>')
        s.append(f'      <text x="{lx+24}" y="496" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">{name}</text>')
        lx += 170
    return "\n".join(s)


def heat_cell_color(v: float, maxabs: float) -> tuple[str, float]:
    """发散色阶：正→暖红、负→冷绿；alpha 随 |v| 增长。"""
    a = 0.12 + 0.58 * abs(v) / maxabs
    base = hex_rgb(ACCENT) if v >= 0 else hex_rgb(DOWN)
    return f"rgba({base},{a:.2f})", a


def build_heatmap(unit: str, rows: list[str], cols: list[str],
                  data: list[list[float]]) -> str:
    left, top, right, bottom = 160, 64, 40, 120
    nr, nc = len(rows), len(cols)
    gap = 4.0
    cw = (1000 - left - right - gap * (nc - 1)) / nc
    ch = (500 - top - bottom - gap * (nr - 1)) / nr
    maxabs = max(abs(v) for r in data for v in r)

    s = [f'      <rect width="100%" height="100%" fill="{PAPER}"/>',
         '      <rect width="100%" height="100%" fill="url(#dots)" opacity="0.55"/>',
         f'      <text x="{(left + 1000 - right) / 2:.0f}" y="30" fill="{MUTED}" '
         f'{axisfont(7)} letter-spacing="0.18em" text-anchor="middle">{unit}</text>']
    for j, c in enumerate(cols):
        cx = left + j * (cw + gap) + cw / 2
        s.append(f'      <text x="{cx:.1f}" y="52" fill="{INK}" font-size="9" font-family="{FONT_SANS}" text-anchor="middle">{c}</text>')
    for i, r in enumerate(rows):
        cy = top + i * (ch + gap) + ch / 2
        s.append(f'      <text x="{left-12:.1f}" y="{cy+3:.1f}" fill="{INK}" font-size="9" font-family="{FONT_SANS}" text-anchor="end">{r}</text>')
        for j, v in enumerate(data[i]):
            x, y = left + j * (cw + gap), top + i * (ch + gap)
            col, a = heat_cell_color(v, maxabs)
            s.append(f'      <rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="{PAPER}"/>')
            s.append(f'      <rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="{col}"/>')
            tc = PAPER if a >= 0.40 else INK
            s.append(f'      <text x="{x+cw/2:.1f}" y="{y+ch/2+3:.1f}" fill="{tc}" {axisfont(8)} text-anchor="middle">{v:+.1f}</text>')

    # ⭐ 本轮改进：色带由「60 个 <rect> 硬拼」改为「1 个 rect + <linearGradient>」
    #    —— 元素数 60 → 1，缩放时不会出现细缝，且是真正的连续渐变。
    lgx, lgy, lgw, lgh = left, 452, 340, 12
    stops = []
    for k in range(9):
        t = k / 8
        col, _ = heat_cell_color((t * 2 - 1) * maxabs, maxabs)
        css = col.replace("rgba(", "rgba(").replace(",", ", ")  # 归一为 CSS 写法
        stops.append(f'          <stop offset="{t:.3f}" stop-color="{css}"/>')
    s.append('      <linearGradient id="heat-legend" x1="0" y1="0" x2="1" y2="0">')
    s.extend(stops)
    s.append('      </linearGradient>')
    s.append(f'      <rect x="{lgx}" y="{lgy}" width="{lgw}" height="{lgh}" fill="url(#heat-legend)"/>')
    s.append(f'      <text x="{lgx}" y="{lgy-6}" fill="{MUTED}" {axisfont(7)} letter-spacing="0.14em">图例 · 冷绿 ← 0 → 暖红</text>')
    s.append(f'      <text x="{lgx}" y="{lgy+24}" fill="{MUTED}" {axisfont(8)}>{-maxabs:+.1f}%</text>')
    s.append(f'      <text x="{lgx+lgw/2:.0f}" y="{lgy+24}" fill="{MUTED}" {axisfont(8)} text-anchor="middle">0.0%</text>')
    s.append(f'      <text x="{lgx+lgw}" y="{lgy+24}" fill="{MUTED}" {axisfont(8)} text-anchor="end">{maxabs:+.1f}%</text>')
    s.append(f'      <text x="{lgx+lgw+40}" y="{lgy+9}" fill="{MUTED}" font-size="8" font-family="{FONT_SANS}">深色格内文字自动翻为纸白（阈值 α ≥ 0.40）</text>')
    return "\n".join(s)


def build_scatter(points: list) -> str:
    x0, x1, ytop, ybase = PLOT["x0"], PLOT["x1"], PLOT["ytop"], PLOT["ybase"]
    xmax, xmin, ymax, ymin = 36.0, 5.0, 21.0, 0.0

    def pxy(vx, vyv):
        return (x0 + (vx - xmin) / (xmax - xmin) * (x1 - x0),
                ybase - (vyv - ymin) / (ymax - ymin) * (ybase - ytop))

    s = [f'      <rect width="100%" height="100%" fill="{PAPER}"/>',
         '      <rect width="100%" height="100%" fill="url(#dots)" opacity="0.55"/>',
         f'      <text transform="rotate(-90 24 230)" x="24" y="230" fill="{MUTED}" '
         f'{axisfont(7)} letter-spacing="0.14em" text-anchor="middle">年化收益 (%)</text>',
         f'      <text x="{(x0+x1)/2:.0f}" y="440" fill="{MUTED}" {axisfont(8)} '
         f'letter-spacing="0.14em" text-anchor="middle">年化波动率 (%)</text>']
    for gy in (0, 5, 10, 15, 20):
        _, y = pxy(xmin, gy)
        s.append(f'      <line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{GRID}" stroke-width="0.8"/>')
        s.append(f'      <text x="{x0-8}" y="{y+3:.1f}" fill="{MUTED}" {axisfont(8)} text-anchor="end">{gy}</text>')
    for gx in (5, 10, 15, 20, 25, 30, 35):
        x, _ = pxy(gx, ymin)
        s.append(f'      <line x1="{x:.1f}" y1="{ytop}" x2="{x:.1f}" y2="{ybase}" stroke="rgba(45,49,66,0.05)" stroke-width="0.8"/>')
        s.append(f'      <text x="{x:.1f}" y="{ybase+16}" fill="{MUTED}" {axisfont(8)} text-anchor="middle">{gx}</text>')
    s.append(f'      <line x1="{x0}" y1="{ytop}" x2="{x0}" y2="{ybase}" stroke="{AXIS}" stroke-width="1"/>')
    s.append(f'      <line x1="{x0}" y1="{ybase}" x2="{x1}" y2="{ybase}" stroke="{AXIS}" stroke-width="1"/>')

    xs = sorted(p[1] for p in points)
    ys = sorted(p[2] for p in points)
    mx, my = (xs[5] + xs[6]) / 2, (ys[5] + ys[6]) / 2
    mxp, _ = pxy(mx, ymin)
    _, myp = pxy(xmin, my)
    s.append(f'      <line x1="{mxp:.1f}" y1="{ytop}" x2="{mxp:.1f}" y2="{ybase}" stroke="{MUTED}" stroke-width="0.8" stroke-dasharray="4,3" opacity="0.55"/>')
    s.append(f'      <line x1="{x0}" y1="{myp:.1f}" x2="{x1}" y2="{myp:.1f}" stroke="{MUTED}" stroke-width="0.8" stroke-dasharray="4,3" opacity="0.55"/>')

    for name, vx, vyv, w, focal in points:
        x, y = pxy(vx, vyv)
        r = (6.0 + 2.4 * w) if focal else (5.0 + 2.4 * w)
        s.append(f'      <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{PAPER}"/>')
        if focal:
            s.append(f'      <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{rgba(ACCENT, 0.15)}" stroke="{ACCENT}" stroke-width="1.2"/>')
            s.append(f'      <text x="{x+r+5:.1f}" y="{y+3:.1f}" fill="{ACCENT}" {axisfont(8)} font-weight="600">{name} 波动 {vx:.1f} / 收益 {vyv:.1f}</text>')
        else:
            s.append(f'      <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{rgba(MUTED, 0.20)}" stroke="{MUTED}" stroke-width="1"/>')

    # 等夏普参考线：y 向下增长 ⇒ 「越出上沿」的判据是 py < ytop，不是 py > ytop
    SLOPE = 0.55
    px0, py0 = pxy(xmin, 0.0)
    px1, py1 = pxy(xmax, (xmax - xmin) * SLOPE)
    if py1 < ytop:
        py1 = ytop
        px1 = min(x0 + ((ymax / SLOPE) - xmin) / (xmax - xmin) * (x1 - x0), x1)
    s.append(f'      <line x1="{px0:.1f}" y1="{py0:.1f}" x2="{px1:.1f}" y2="{py1:.1f}" stroke="{INK}" stroke-width="0.9" stroke-dasharray="5,4" opacity="0.28"/>')
    lx, ly = pxy(xmax - 3.0, (xmax - 3.0 - xmin) * SLOPE)
    s.append(f'      <text x="{lx:.1f}" y="{ly-6:.1f}" fill="{MUTED}" {axisfont(8)} text-anchor="end">等夏普参考线 · {SLOPE}</text>')
    s.append(f'      <line x1="40" y1="462" x2="960" y2="462" stroke="{RULE}" stroke-width="0.8"/>')
    s.append(f'      <text x="40" y="478" fill="{MUTED}" {axisfont(8)} letter-spacing="0.18em">图例</text>')
    s.append(f'      <circle cx="48" cy="492" r="6" fill="{rgba(ACCENT, 0.15)}" stroke="{ACCENT}" stroke-width="1.2"/>')
    s.append(f'      <text x="62" y="495" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">单位风险收益最优标的</text>')
    s.append(f'      <circle cx="250" cy="492" r="6" fill="{rgba(MUTED, 0.20)}" stroke="{MUTED}" stroke-width="1"/>')
    s.append(f'      <text x="264" y="495" fill="{MUTED}" font-size="8.5" font-family="{FONT_SANS}">其它标的（气泡大小 = 规模权重）</text>')
    return "\n".join(s)


# ══════════════════════════════════════════════════════════════════════
# 五、动效外壳（mode ∈ {step, reveal}）
# ══════════════════════════════════════════════════════════════════════
# 契约来源：diagram-design/references/animation.md
#   · 控制器**必须逐字复用** assets/template-motion.html 的 <script data-diagram-controls>
#     （animation.md 第 93 行；self_check 的 check_scripts 要求 body 归一化后完全相等）
#     ⇒ 因此**运行时提取**，绝不手抄。
#   · `reveal` 是唯一被许可的自动播放模式，且 canonical 控制器**原生支持**
#     （模板第 433-436 行：render(0) → play()）⇒ 不需要、也不允许另写控制器。
#   · `--motion-total` 必须 = 步数 × `--motion-hold`（animation.md 第 109 行）。
MOTION_TPL = pathlib.Path(__file__).resolve().parents[3] / "diagram-design" / "assets" / "template-motion.html"
MOTION_HOLD_MS = 720

# 模板字体栈 → 带 CJK 字形的栈。模板无中文字形，中文会落成豆腐块。
_MOTION_STYLE_SUBS = (
    ("--font-sans: 'Geist', system-ui, sans-serif;", f"--font-sans: {FONT_SANS};"),
    ("--font-mono: 'Geist Mono', ui-monospace, monospace;", f"--font-mono: {FONT_MONO};"),
    ("--font-serif: 'Instrument Serif', 'Noto Serif', 'Noto Serif KR', serif;",
     "--font-serif: 'Instrument Serif', 'Songti SC', 'SimSun', 'Microsoft YaHei', serif;"),
)


def _sub_once(text: str, old: str, new: str, label: str) -> str:
    """替换且**断言命中恰一次**。

    为什么不静默 replace：上游模板是可被上游改动的外部资产。若它换了声明文本，
    `.replace()` 会**静默不做替换**⇒ 产出的中文全部变成豆腐块，而任何现有判据都不报错。
    这里把「模板漂移」变成硬失败。
    """
    n = text.count(old)
    if n != 1:
        raise AssertionError(f"模板替换锚点 `{label}` 命中 {n} 次（期望 1）—— 上游模板可能已改")
    return text.replace(old, new)


def motion_assets(total_ms: int | None = None,
                  tpl: pathlib.Path | None = None) -> tuple[str, str]:
    """返回 (style, script)：从上游模板运行时提取 + CJK 字体栈替换 + --motion-total 归位。"""
    tpl = pathlib.Path(tpl or MOTION_TPL)
    raw = tpl.read_text(encoding="utf-8")
    m_style = re.search(r"<style>(.*?)</style>", raw, re.S)
    m_script = re.search(r"<script data-diagram-controls>(.*?)</script>", raw, re.S)
    if not m_style or not m_script:
        raise AssertionError("未能在上游模板中定位 <style> / <script data-diagram-controls>")
    style, script = m_style.group(1), m_script.group(1)
    for old, new in _MOTION_STYLE_SUBS:
        style = _sub_once(style, old, new, old[:40])
    if total_ms is not None:
        style = _sub_once(style, "--motion-total: 3600ms;",
                          f"--motion-total: {total_ms}ms;", "--motion-total")
    return style, script


def motion_page(*, title: str, eyebrow: str, h1: str, mode: str,
                step_count: int, svg: str,
                hold_ms: int = MOTION_HOLD_MS,
                tpl: pathlib.Path | None = None) -> str:
    """step / reveal 两种动效页。两者**唯一差别**是 data-motion-mode 与文案。

    svg 由 `motion_svg()` 产出（标题/描述已写在 SVG 内，此处不重复声明）。
    """
    if mode not in ("step", "reveal"):
        raise ValueError("mode 只支持 step / reveal（loop/none 不需要外壳）")
    if not 1 <= step_count <= 8:
        raise ValueError("语义步数须在 1..8（animation.md 第 105 行）")
    total = step_count * hold_ms
    if total > 8000:
        raise ValueError(f"--motion-total={total}ms 超出 8000ms 预算")
    style, script = motion_assets(total_ms=total, tpl=tpl)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link href="{GFONTS}" rel="stylesheet">
  <style>{style}</style>
</head>
<body>
  <main data-motion-root data-motion-mode="{mode}" data-step-count="{step_count}" data-step-current="{step_count}" data-frame="static" data-static-frame="complete">
    <p class="eyebrow">{eyebrow}</p>
    <h1>{h1}</h1>

    <div class="diagram-container">
{svg}
    </div>

    <div data-motion-controls role="group" aria-label="图示播放控制">
      <button type="button" data-motion-action="prev">上一步</button>
      <button type="button" data-motion-action="play" aria-pressed="false">播放</button>
      <button type="button" data-motion-action="pause" aria-pressed="true">暂停</button>
      <button type="button" data-motion-action="next">下一步</button>
      <button type="button" data-motion-action="replay">重播</button>
      <span class="keyboard-help">←/→ 切换步骤 · 空格 播放/暂停 · R 重播 · Home/End 跳到首/末</span>
      <span data-motion-status-visible aria-hidden="true">第 <span data-motion-step-label>{step_count}</span> / {step_count} 步</span>
    </div>

    <p class="sr-only" data-motion-status role="status" aria-live="polite" aria-atomic="true"></p>
    <noscript><p>播放控制需要 JavaScript。上方已展示完整的最终图示。</p></noscript>
  </main>

  <script data-diagram-controls>{script}</script>
</body>
</html>
"""


def motion_svg(inner: str, *, aria: tuple[str, str], title: str, desc: str) -> str:
    """动效图的 SVG 包装 —— 与 wrap_svg 同一契约，但按动画页缩进。"""
    t_id, d_id = aria
    return (
        f'      <svg viewBox="0 0 1000 500" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-labelledby="{t_id} {d_id}" width="1000" height="500">\n'
        f'        <title id="{t_id}">{title}</title>\n'
        f'        <desc id="{d_id}">{desc}</desc>\n'
        "        <defs>\n" + DOT_PATTERN.replace("        ", "          ") + "        </defs>\n"
        + inner.replace("\n", "\n  ") + "\n      </svg>"
    )


def controller_identity(script: str, tpl: pathlib.Path | None = None) -> bool:
    """自证：产物里的控制器与上游模板**归一化后完全相等**（换行归一 + 去首尾空白）。"""
    _, canonical = motion_assets(total_ms=None, tpl=tpl)
    norm = lambda t: t.replace("\r\n", "\n").replace("\r", "\n").strip()
    return norm(script) == norm(canonical)
