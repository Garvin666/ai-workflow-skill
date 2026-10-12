# -*- coding: utf-8 -*-
"""[自研工具] methodcard_lib —— 方法原理卡片引擎核心库。

名称：methodcard（方法原理卡片引擎）
用途：把「一个方法/概念」渲染为五区教学卡片（页眉／核心思想／步骤／示意区／总结），
      公式经 ziamath 转纯 path SVG（零字体依赖、零远程引用），子图程序化生成。
适用场景：科研模式 R5「方法解释图」、学习资料卡片、汇报演示素材。
仓库：https://github.com/Garvin666/ai-workflow-tools（待推送）

设计令牌与版式取自参考图采样（fixtures/token-samples.txt），五区结构对齐参考系。
本库只产 SVG 片段与骨架 HTML，导出（PDF/PNG）由 methodcard_build.py 负责。
"""
from __future__ import annotations
import re
from functools import lru_cache

# ============================================================
# 1. 设计令牌（s2 定稿，来源：token-samples.txt 四图采样 + 目视校正）
# ============================================================
TOKENS = {
    "paper":      "#FAF8EC",   # 纸底（暖米白）
    "panel":      "#EAE9E3",   # 分区底（浅暖灰）
    "panel_blue": "#E7EDF3",   # 浅蓝分区底（公式区）
    "line":       "#C6C4BB",   # 边框线
    "line_soft":  "#DAD8CF",   # 内部细线
    "ink":        "#1F1E1C",   # 标题墨色
    "ink_body":   "#3B3A36",   # 正文
    "ink_muted":  "#8C8C88",   # 次级文字／灰散点
    "blue":       "#4278B0",   # 主蓝（数据线／强调）
    "blue_deep":  "#2F5E93",   # 深蓝（编号／重点）
    "blue_light": "#C0D3E4",   # 浅蓝填充
    "warm":       "#EFC9A4",   # 暖橙（第二焦点）
    "warm_deep":  "#C08460",   # 深暖（加重）
    "red":        "#9A5F4F",   # 砖红（第三焦点／最优点）
    "tan":        "#E9DFC9",   # 米色标签底
    "gray_fill":  "#B9B8B3",   # 灰填充（普通回归系）
}

FONTS = {
    # 英文大标题：Playfair Display（SIL OFL，静态 woff2 由 methodcard_build 内嵌）。
    # ⚠️ 勿改回系统展示字体：Windows 的 Sitka 是「可变字体」（SitkaVF.ttf），
    #    Chrome 打印 PDF 时无法子集嵌入 → 整段标题落成 Type3（期刊/印厂拒收，肉眼不可见）。
    #    标题字体必须是「静态文件内嵌」，后随栈仅为字体缺失时的安全降级。
    "title":  "'Playfair Display','Cambria','Georgia',serif",
    "sans":   "'Microsoft YaHei','Segoe UI','Segoe UI Semibold',sans-serif",
    "sans_lt":"'Deng','Microsoft YaHei','Segoe UI',sans-serif",
    "serif_cn": "'Source Han Serif SC Heavy','Noto Serif SC','STSong','SimSun',serif",
    "mono":   "'Consolas','Cascadia Mono',monospace",
}

CARD_W, CARD_H = 1200, 1600   # 卡面尺寸（3:4）
PAD = 36                      # 卡外框与内容边距


# ============================================================
# 2. SVG 基础工具
# ============================================================
def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def num(v: float) -> str:
    """紧凑数字格式：去尾零。"""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def svg(w, h, body: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {num(w)} {num(h)}" '
            f'width="{num(w)}" height="{num(h)}"{c}>{body}</svg>')


def rect(x, y, w, h, fill="none", stroke=None, sw=1, rx=0, dash=None, opacity=None):
    a = f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}"'
    if rx: a += f' rx="{num(rx)}"'
    a += f' fill="{fill}"'
    if stroke: a += f' stroke="{stroke}" stroke-width="{num(sw)}"'
    if dash: a += f' stroke-dasharray="{dash}"'
    if opacity is not None: a += f' opacity="{num(opacity)}"'
    return a + "/>"


def line(x1, y1, x2, y2, stroke, sw=1, dash=None, cap="round", opacity=None):
    a = f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" stroke="{stroke}" stroke-width="{num(sw)}" stroke-linecap="{cap}"'
    if dash: a += f' stroke-dasharray="{dash}"'
    if opacity is not None: a += f' opacity="{num(opacity)}"'
    return a + "/>"


def circle(cx, cy, r, fill, stroke=None, sw=1, opacity=None):
    a = f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}" fill="{fill}"'
    if stroke: a += f' stroke="{stroke}" stroke-width="{num(sw)}"'
    if opacity is not None: a += f' opacity="{num(opacity)}"'
    return a + "/>"


def ellipse(cx, cy, rx, ry, fill="none", stroke=None, sw=1, rot=0, opacity=None, dash=None):
    a = f'<ellipse cx="{num(cx)}" cy="{num(cy)}" rx="{num(rx)}" ry="{num(ry)}" fill="{fill}"'
    if stroke: a += f' stroke="{stroke}" stroke-width="{num(sw)}"'
    if rot: a += f' transform="rotate({num(rot)} {num(cx)} {num(cy)})"'
    if dash: a += f' stroke-dasharray="{dash}"'
    if opacity is not None: a += f' opacity="{num(opacity)}"'
    return a + "/>"


def polyline(pts, stroke, sw=1.4, fill="none", dash=None, opacity=None):
    d = " ".join(f"{num(x)},{num(y)}" for x, y in pts)
    a = f'<polyline points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{num(sw)}" stroke-linejoin="round" stroke-linecap="round"'
    if dash: a += f' stroke-dasharray="{dash}"'
    if opacity is not None: a += f' opacity="{num(opacity)}"'
    return a + "/>"


def txt(x, y, s, size=13, fill=None, font=None, anchor="start", weight=None, ls=None, opacity=None, italic=False):
    fill = fill or TOKENS["ink_body"]
    font = font or FONTS["sans"]
    a = (f'<text x="{num(x)}" y="{num(y)}" font-size="{num(size)}" fill="{fill}" '
         f'font-family="{font}"')
    if anchor != "start": a += f' text-anchor="{anchor}"'
    if weight: a += f' font-weight="{weight}"'
    if ls is not None: a += f' letter-spacing="{num(ls)}"'
    if italic: a += ' font-style="italic"'
    if opacity is not None: a += f' opacity="{num(opacity)}"'
    return a + f'>{esc(s)}</text>'


def path(d, stroke=None, sw=1.4, fill="none", dash=None):
    a = f'<path d="{d}" fill="{fill}"'
    if stroke: a += f' stroke="{stroke}" stroke-width="{num(sw)}" stroke-linejoin="round" stroke-linecap="round"'
    if dash: a += f' stroke-dasharray="{dash}"'
    return a + "/>"


def arrow(x1, y1, x2, y2, stroke=None, sw=2.2, head=7):
    """直线箭头（终点三角头）。"""
    stroke = stroke or TOKENS["ink_muted"]
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - head * math.cos(ang), y2 - head * math.sin(ang)
    p1 = (x2, y2)
    p2 = (bx - head * 0.55 * math.sin(ang), by + head * 0.55 * math.cos(ang))
    p3 = (bx + head * 0.55 * math.sin(ang), by - head * 0.55 * math.cos(ang))
    tri = (f'M {num(p1[0])} {num(p1[1])} L {num(p2[0])} {num(p2[1])} '
           f'L {num(p3[0])} {num(p3[1])} Z')
    return line(x1, y1, bx, by, stroke, sw) + f'<path d="{tri}" fill="{stroke}"/>'


def wrap_cjk(text: str, max_units: float):
    """按显示宽度断行：中文=1 单位，ASCII≈0.55 单位。返回行列表。"""
    lines, cur, w = [], "", 0.0
    for ch in text:
        cw = 1.0 if ord(ch) > 0x2E80 else 0.55
        if w + cw > max_units and cur:
            lines.append(cur)
            cur, w = "", 0.0
        cur += ch
        w += cw
    if cur:
        lines.append(cur)
    return lines


# ============================================================
# 3. 公式封装（ziamath → 纯 path SVG；尺寸解析出 px 供布局）
# ============================================================
@lru_cache(maxsize=256)
def eq(latex: str, size: float = 16.0, color: str = "") -> str:
    """LaTeX → SVG 片段。size 为 pt；返回的 <svg> 自带 width/height(pt)。"""
    from ziamath import Latex
    color = color or TOKENS["ink"]
    m = Latex(latex, size=size, color=color)
    s = m.svg()
    return s


def eq_size(svg_str: str):
    """取回公式 SVG 的 (w, h)（pt 数值）。"""
    m = re.search(r'<svg[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"', svg_str)
    if not m:
        return (100.0, 20.0)
    return (float(m.group(1)), float(m.group(2)))


def eq_scaled(latex: str, target_h: float, color: str = "") -> str:
    """按目标显示高度（px）渲染公式：先估 size，再回填 width/height 属性。"""
    probe = eq(latex, 16.0, color)
    _, h0 = eq_size(probe)
    size = 16.0 * target_h / max(h0, 1e-6)
    s = eq(latex, round(size, 1), color)
    w, h = eq_size(s)
    s = re.sub(r'(<svg[^>]*width=")[\d.]+(")', rf"\g<1>{num(w)}\g<2>", s, count=1)
    s = re.sub(r'(<svg[^>]*height=")[\d.]+(")', rf"\g<1>{num(h)}\g<2>", s, count=1)
    return s


# ============================================================
# 4. 子图组件库（每个函数返回一个完整的内联 <svg> 片段）
# ============================================================
def _axes(w, h, xr, yr, axis_color=None, font_size=12, pad_l=34, pad_b=26, y_arrow=True):
    """通用坐标轴组：返回 (body, 映射函数)。映射函数 (x,y)->(px,py)。"""
    ac = axis_color or TOKENS["ink"]
    x0, x1 = xr
    y0, y1 = yr
    px0, px1 = 8, w - 6
    py0, py1 = 8, h - 6
    plot_l, plot_r = px0 + pad_l, px1
    plot_t, plot_b = py0, py1 - pad_b

    def MX(x): return plot_l + (x - x0) / (x1 - x0) * (plot_r - plot_l)
    def MY(y): return plot_b - (y - y0) / (y1 - y0) * (plot_b - plot_t)

    parts = []
    # y 轴（带箭头）
    parts.append(line(plot_l, plot_b, plot_l, plot_t - 2, ac, 1.1))
    if y_arrow:
        parts.append(path(f"M {num(plot_l-3.2)} {num(plot_t+3)} L {num(plot_l)} {num(plot_t-2)} L {num(plot_l+3.2)} {num(plot_t+3)} Z", fill=ac))
    parts.append(line(plot_l, plot_b, plot_r, plot_b, ac, 1.1))
    return "".join(parts), MX, MY, (plot_l, plot_b, plot_r, plot_t)


def fig_scatter_fit(w, h, pts, lines_=None, xr=(0, 10), yr=(0, 10), dot=4.2,
                    dot_fill=None, axis_label=None, legend=None, grid=False):
    """散点 + 可选多条线（回归线对比）。lines_ = [(pts, color, width, dash?)]"""
    dot_fill = dot_fill or TOKENS["ink_muted"]
    body, MX, MY, (pl, pb, pr, pt) = _axes(w, h, xr, yr)
    parts = [body]
    if grid:
        for gy in (0.25, 0.5, 0.75):
            y = MY(yr[0] + gy * (yr[1] - yr[0]))
            parts.append(line(MX(xr[0]), y, MX(xr[1]), y, TOKENS["line_soft"], 0.7, dash="2 3"))
    for (px, py) in pts:
        parts.append(circle(MX(px), MY(py), dot, dot_fill, opacity=0.85))
    for i, item in enumerate(lines_ or []):
        lp, color, sw = item[0], item[1], item[2] if len(item) > 2 else 2.0
        dash = item[3] if len(item) > 3 else None
        pts2 = [(MX(x), MY(y)) for x, y in lp]
        parts.append(polyline(pts2, color, sw, dash=dash))
    if axis_label:
        parts.append(txt(12, MY(yr[1]) + 16, axis_label[0], 15, TOKENS["ink_body"],
                         font="Georgia,serif", italic=True))
        parts.append(txt(w - 12, h - 8, axis_label[1], 15, TOKENS["ink_body"],
                         font="Georgia,serif", anchor="end", italic=True))
    if legend:
        lx, ly = pl + 16, 26
        for name, color in legend:
            parts.append(line(lx, ly, lx + 18, ly, color, 2.4))
            parts.append(txt(lx + 23, ly + 4.5, name, 12, TOKENS["ink_body"]))
            ly += 20
    return svg(w, h, "".join(parts))


def fig_coef_bars(w, h, labels, series, legend=None, ylab="系数值", xlab_right=None):
    """成组条形：series = [(值表, 颜色, 名称?)]（2 组：普通回归 / 岭回归）。"""
    n = len(labels)
    ng = len(series)
    body, MX, MY, (pl, pb, pr, pt) = _axes(
        w, h, (0, n), (min(0, min(min(s[0]) for s in series)) * 1.15,
                       max(max(s[0]) for s in series) * 1.25),
        pad_l=40, pad_b=30)
    parts = [body]
    zero_y = MY(0)
    parts.append(line(MX(0), zero_y, MX(n), zero_y, TOKENS["ink"], 1.0))
    bw = (pr - pl) / n / (ng + 1.6)
    for i, lab in enumerate(labels):
        gx = MX(i) + (MX(i + 1) - MX(i)) / 2
        for j, s in enumerate(series):
            val = s[0][i]
            color = s[1]
            bx = gx - (ng * bw + (ng - 1) * 3) / 2 + j * (bw + 3)
            y0, y1 = (zero_y, MY(val)) if val >= 0 else (MY(val), zero_y)
            parts.append(rect(bx, min(y0, y1), bw, max(abs(y1 - y0), 1.2), fill=color, rx=1.5))
        parts.append(txt(gx, h - 8, lab, 11.5, TOKENS["ink_body"], anchor="middle"))
    if ylab:
        parts.append(txt(10, pt + 10, ylab, 11, TOKENS["ink_muted"]))
    if legend:
        lx, ly = w - 106, 22
        for name, color in legend:
            parts.append(rect(lx, ly - 9, 11, 11, fill=color, rx=2))
            parts.append(txt(lx + 16, ly + 1, name, 12, TOKENS["ink_body"]))
            ly += 20
    if xlab_right:
        parts.append(txt(pr, h - 8, xlab_right, 11, TOKENS["ink_muted"], anchor="end"))
    return svg(w, h, "".join(parts))


def fig_contour(w, h):
    """等高线（拟合误差椭圆）+ 两个解点：普通解（红）与岭解（蓝）。"""
    body, MX, MY, _ = _axes(w, h, (0, 10), (0, 10), pad_l=30, pad_b=26)
    parts = [body]
    cx, cy = MX(4.1), MY(2.9)
    for k, (rx, ry, rot) in enumerate([(46, 30, -32), (74, 48, -32), (102, 66, -32)]):
        parts.append(ellipse(cx, cy, rx, ry, stroke=TOKENS["line"], sw=1.0, rot=rot,
                             opacity=1 - k * 0.22))
    # 约束圆（L2 球）
    parts.append(ellipse(MX(4.1), MY(3.35), 56, 56, stroke=TOKENS["blue"], sw=1.0, dash="3 3", opacity=0.85))
    parts.append(circle(MX(7.4), MY(6.9), 4.6, TOKENS["red"]))
    parts.append(circle(MX(4.6), MY(3.6), 4.6, TOKENS["blue"]))
    parts.append(txt(MX(7.4) + 8, MY(6.9) - 7, "普通回归", 11.5, TOKENS["ink_body"]))
    parts.append(txt(MX(4.6) - 8, MY(3.6) + 16, "岭回归", 11.5, TOKENS["ink_body"], anchor="end"))
    return svg(w, h, "".join(parts))


def fig_density(w, h, comps, xr=(-6, 6), show_axis=True, dot_pts=None, total_color=None):
    """混合密度：comps=[(mu, sigma, weight, color)] + 可选样本点串。
    total_color 非空时叠加总混合曲线 Σ wₖ·N(x|μₖ,σₖ)。"""
    import math
    body, MX, MY, _ = _axes(w, h, xr, (0, 1.05), pad_l=14, pad_b=20, y_arrow=False)
    parts = [body] if show_axis else []
    if dot_pts:
        for (x, jy) in dot_pts:
            parts.append(circle(MX(x), MY(0.03 + jy * 0.16), 2.2, TOKENS["ink_muted"], opacity=0.55))
    N = 80
    xs = [xr[0] + (xr[1] - xr[0]) * i / N for i in range(N + 1)]
    for (mu, sg, wt, color) in comps:
        pts = [(MX(x), MY(wt * math.exp(-((x - mu) ** 2) / (2 * sg * sg)))) for x in xs]
        parts.append(polyline(pts, color, 1.7, opacity=0.7))
    if total_color:
        def _tot(x):
            return sum(wt * math.exp(-((x - mu) ** 2) / (2 * sg * sg))
                       for (mu, sg, wt, _c) in comps)
        pts = [(MX(x), MY(min(_tot(x), 1.05))) for x in xs]
        parts.append(polyline(pts, total_color, 2.2))
    return svg(w, h, "".join(parts))


def fig_heatgrid(w, h, matrix, row_labels=None, col_labels=None, cell=None, cmap_colors=None):
    """热力格（软分配矩阵）：matrix[r][c] ∈ 0..1；颜色 = 蓝深浅。"""
    rows = len(matrix)
    cols = len(matrix[0])
    cw = (w - 46) / cols
    ch = (h - 34) / rows
    parts = []
    def shade(v):
        v = max(0.0, min(1.0, v))
        r0, g0, b0 = 0xFA, 0xF8, 0xEC
        r1, g1, b1 = 0x2F, 0x5E, 0x93
        return "#%02x%02x%02x" % (round(r0 + (r1 - r0) * v), round(g0 + (g1 - g0) * v), round(b0 + (b1 - b0) * v))
    for r in range(rows):
        for c in range(cols):
            v = matrix[r][c]
            parts.append(rect(40 + c * cw, 8 + r * ch, cw - 2.5, ch - 2.5, fill=shade(v), rx=2.5))
    if col_labels:
        for c, lab in enumerate(col_labels):
            parts.append(txt(40 + c * cw + cw / 2, h - 6, lab, 11, TOKENS["ink_muted"], anchor="middle"))
    if row_labels:
        for r, lab in enumerate(row_labels):
            parts.append(txt(34, 8 + r * ch + ch / 2 + 4, lab, 11, TOKENS["ink_muted"], anchor="end"))
    return svg(w, h, "".join(parts))


def fig_trace(w, h, xs, series, xlab="λ", ylab="系数", yr=None, marks=None, note=None):
    """多条曲线随 x 变化（岭迹／收敛曲线）。yr 缺省 [-0.25,1.05]。
    marks=[(x, y, color)] 画端点标记；note=(x, y, text) 画一处标注。"""
    yr2 = yr if yr else (-0.25, 1.05)
    body, MX, MY, _ = _axes(w, h, (min(xs), max(xs)), yr2, pad_l=34, pad_b=26)
    parts = [body]
    for vals, color, sw in series:
        pts = [(MX(x), MY(y)) for x, y in zip(xs, vals)]
        parts.append(polyline(pts, color, sw))
    if marks:
        for (mx, my, mc) in marks:
            parts.append(circle(MX(mx), MY(my), 3.2, mc, stroke="#FFFFFF", sw=1.2))
    if note:
        parts.append(txt(MX(note[0]) + 7, MY(note[1]) + 4, note[2], 11, TOKENS["ink_muted"]))
    parts.append(txt(w - 8, h - 6, xlab, 11.5, TOKENS["ink_muted"], anchor="end"))
    parts.append(txt(8, 16, ylab, 11.5, TOKENS["ink_muted"]))
    return svg(w, h, "".join(parts))


def fig_steps_arrow(w, h):
    """区块间大箭头（→）。"""
    y = h / 2
    parts = [
        line(4, y, w - 14, y, TOKENS["ink_muted"], 3.0),
        path(f"M {num(w-4)} {num(y)} L {num(w-18)} {num(y-7)} L {num(w-18)} {num(y+7)} Z",
             fill=TOKENS["ink_muted"]),
    ]
    return svg(w, h, "".join(parts))


def fig_badge(w, h, text, color=None):
    """小徽章（如『减小方差』块）。"""
    color = color or TOKENS["blue"]
    parts = [
        rect(1, 1, w - 2, h - 2, fill=color, rx=8),
        txt(w / 2, h / 2 + 5, text, 14, "#FFFFFF", anchor="middle", weight="bold"),
    ]
    return svg(w, h, "".join(parts))


def fig_gaussian2d(w, h, cx, cy, rx, ry, rot, color):
    """2D 高斯椭圆（GMM 组件用）。"""
    parts = [
        ellipse(cx, cy, rx, ry, fill=color, opacity=0.16, rot=rot),
        ellipse(cx, cy, rx, ry, stroke=color, sw=1.4, rot=rot),
    ]
    return svg(w, h, "".join(parts))


def fig_cluster_ellipses(w, h, clusters, xr=(0, 10), yr=(0, 10), dot=3.8,
                         axis_label=None, legend=None):
    """聚类结果示意：clusters=[(pts, color, center, [(rx,ry,rot,dash),…])]。
    每簇 = 层叠等密度椭圆（底）→ 散点（中）→ 中心点（顶）。椭圆尺寸为像素值。"""
    body, MX, MY, (pl, _pb, _pr, _pt) = _axes(w, h, xr, yr)
    parts = [body]
    for pts, color, center, ells in clusters:
        cx, cy = MX(center[0]), MY(center[1])
        for (rx, ry, rot, dash) in ells:
            parts.append(ellipse(cx, cy, rx, ry, stroke=color, sw=1.1, rot=rot,
                                 dash=dash, opacity=0.85))
        for (px, py) in pts:
            parts.append(circle(MX(px), MY(py), dot, color, opacity=0.72))
        parts.append(circle(cx, cy, 3.4, color, stroke="#FFFFFF", sw=1.3))
    if axis_label:
        parts.append(txt(12, MY(yr[1]) + 16, axis_label[0], 15, TOKENS["ink_body"],
                         font="Georgia,serif", italic=True))
        parts.append(txt(w - 12, h - 8, axis_label[1], 15, TOKENS["ink_body"],
                         font="Georgia,serif", anchor="end", italic=True))
    if legend:
        lx, ly = pl + 16, 26
        for name, color in legend:
            parts.append(circle(lx + 5, ly - 4, 4.4, color))
            parts.append(txt(lx + 15, ly, name, 12, TOKENS["ink_body"]))
            ly += 20
    return svg(w, h, "".join(parts))


# ============================================================
# 5. 自检（组件冒烟 + 工具函数断言；几何越界由 methodcard_check.py 独立判）
# ============================================================
def _selftest():
    # 工具函数
    assert esc("<a>&") == "&lt;a&gt;&amp;", "esc 异常"
    assert num(1.50) == "1.5" and num(-0.0) == "0" and num(0.0) == "0", "num 异常"
    lines = wrap_cjk("中文测试加长文本ABC", 5)
    assert all(sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in ln) <= 5.01 for ln in lines), \
        f"wrap_cjk 超宽：{lines}"

    # 公式链：纯 path、无远程引用
    s = eq(r"x^{2}+y^{2}=1", 16)
    assert s.startswith("<svg") and "</svg>" in s, "eq 输出异常"
    assert "<text" not in s and "<image" not in s, "eq 含 text/image（违反纯路径承诺）"
    assert "http://" not in s.replace("http://www.w3.org/2000/svg", ""), "eq 有远程引用"
    w0, h0 = eq_size(s)
    assert w0 > 0 and h0 > 0, "eq_size 异常"

    # 组件冒烟（全部 fig_* 至少调用一次）
    T = TOKENS
    comps = {
        "scatter_fit": fig_scatter_fit(200, 200, [(1, 1), (2, 3)],
                                       lines_=[([(0, 0), (10, 10)], T["blue"], 2.0)],
                                       legend=[("a", T["blue"])]),
        "coef_bars": fig_coef_bars(200, 200, ["a", "b"],
                                   [([1, -1], T["blue"]), ([0.5, -0.5], T["gray_fill"])]),
        "contour": fig_contour(200, 200),
        "density": fig_density(200, 200, [(0, 1, 0.5, T["blue"])], total_color=T["blue_deep"]),
        "heatgrid": fig_heatgrid(200, 200, [[0.2, 0.8], [0.9, 0.1]], ["r1", "r2"], ["c1", "c2"]),
        "trace": fig_trace(200, 200, [0, 1, 2], [([1, 0.5, 0.2], T["blue"], 2.0)],
                           yr=(0, 1.2), marks=[(0, 1, T["blue"])], note=(1, 0.9, "n")),
        "steps_arrow": fig_steps_arrow(60, 30),
        "badge": fig_badge(60, 30, "测试"),
        "gaussian2d": fig_gaussian2d(200, 200, 100, 100, 50, 30, 20, T["blue"]),
        "cluster_ellipses": fig_cluster_ellipses(
            200, 200, [([(2, 2), (3, 3)], T["blue"], (2.5, 2.5), [(30, 20, -20, None)])],
            legend=[("c", T["blue"])], axis_label=("y", "x")),
    }
    for name, s in comps.items():
        assert s.startswith("<svg") and s.endswith("</svg>"), f"{name} 输出异常"
        assert "http://" not in s.replace("http://www.w3.org/2000/svg", ""), \
            f"{name} 有远程引用"
    print(f"[selftest] methodcard_lib OK：{len(comps)} 组件冒烟 + 公式/工具断言全过")
    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description="methodcard_lib 自检")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
