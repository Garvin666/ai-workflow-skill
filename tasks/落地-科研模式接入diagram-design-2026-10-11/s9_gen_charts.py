# -*- coding: utf-8 -*-
"""s9 —— 静态数据图生成（driver）。

契约来源（只读，零改动）：
  ~/.workbuddy/skills/diagram-design/references/style-guide.md          令牌
  ~/.workbuddy/skills/diagram-design/references/type-{bar,line,heatmap,scatter}.md  布局约定
  ~/.workbuddy/skills/diagram-design/assets/example-bar-full.html       编辑式外框
  ~/.workbuddy/skills/diagram-design/scripts/self_check.py              验收判据

几何与令牌全部来自 chartlib（**单一来源**）；本文件只管**内容**（标题/副题/卡片/描述）
与**落盘**。原先几何写在这里、与 s11 各存一份 —— 已收敛。
纯标准库。数据均为**示例数据**（显式标注，不冒充真实统计）。
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import chartlib as C  # noqa: E402

TASK = pathlib.Path(__file__).resolve().parent
OUT = TASK / "output"


def spec_bar() -> dict:
    d = C.DATASETS["annual_returns"]
    vals = d["values"]
    hi = d["labels"][vals.index(max(vals))]
    lo = d["labels"][vals.index(min(vals))]
    n_pos = sum(1 for v in vals if v > 0)
    n_neg = sum(1 for v in vals if v < 0)
    svg = C.wrap_svg(
        C.build_bar(d["unit"], d["labels"], vals),
        viewbox="0 0 1000 500", aria=("bar-title", "bar-desc"),
        title=f"分年度收益率 · {d['labels'][0]}–{d['labels'][-1]}",
        desc=(f"柱状图展示 {d['labels'][0]} 至 {d['labels'][-1]} 七个年度的收益率，"
              f"{hi} 年为区间最高（+{max(vals)}%），{lo} 年为最低（−{abs(min(vals))}%）。"),
    )
    return dict(
        fname="chart-01-bar.html", title="分年度收益率 · 柱状图",
        eyebrow="BAR · DIAGRAM DESIGN",
        h1=f"分年度收益率 · {d['labels'][0]}–{d['labels'][-1]}",
        sub=(f"七个年度的组合收益率。{hi} 年是区间峰值（+{max(vals)}%），"
             f"{lo} 年回撤最深（−{abs(min(vals))}%）。柱体按 A 股习惯着色：红涨、绿跌。"),
        svg=svg,
        cards=[
            C.card("区间峰值", "coral", f"{hi} · +{max(vals)}%",
                   "峰值不来自加杠杆，而来自当年小盘成长因子的极端占优。柱高记录结果，不记录成因。"),
            C.card("回撤最深处", "muted", f"{lo} · {min(vals)}%",
                   "2021–2022 连续两年为负，累计回撤 −31.2%。图中两根绿柱是唯一的连续负收益段。"),
            C.card("图上看不出的", "ink", f"{len(vals)} 年 {n_pos} 正 {n_neg} 负",
                   "年度收益掩盖了年内路径。2020 年最高 25.1% 的年份，年内最大回撤达 −14.8%。"),
        ],
        footl=f"分年度收益率 · {d['labels'][0]}–{d['labels'][-1]}",
        footr="示例数据 · 非真实统计 · diagram design",
    )


def spec_line() -> dict:
    d = C.DATASETS["nav_curves"]
    s0, s1 = d["series"][0], d["series"][1]
    names = "、".join(s[0] for s in d["series"])
    ends = "，".join(f"{s[0]} {s[1][-1]:.2f}" for s in d["series"])
    svg = C.wrap_svg(
        C.build_line(d["unit"], d["labels"], d["series"]),
        viewbox="0 0 1000 500", aria=("line-title", "line-desc"),
        title="净值曲线 · 12 个月三系列对比",
        desc=f"折线图对比 {names} 三条曲线 12 个月走势，年末分别为 {ends}。",
    )
    return dict(
        fname="chart-02-line.html", title="净值曲线 · 折线图",
        eyebrow="LINE · DIAGRAM DESIGN", h1="净值曲线 · 12 个月三系列",
        sub=(f"三条曲线的起点均为 1.00。{s0[0]}年末 {s0[1][-1]:.2f}，"
             f"超额主要产生在 4 月与 7 月两个上行段。"),
        svg=svg,
        cards=[
            C.card("焦点系列", "coral", f"{s0[0]} · {s0[1][-1]:.2f}",
                   "全段 12 个月仅 3 个月为负；面积填充与顶点圆点只给焦点系列，其余两条只留线。"),
            C.card("同期基准", "muted", f"{s1[0]} · {s1[1][-1]:.2f}",
                   "与策略的差距在 6 月收窄到 0.08，随后在 7 月重新拉开。"),
            C.card("图上看不出的", "ink", "净值 ≠ 体验",
                   "曲线是月度收盘点连成的。月内路径、申赎摩擦与仓位漂移都不在这条线上。"),
        ],
        footl="净值曲线 · 12 个月三系列",
        footr="示例数据 · 非真实统计 · diagram design",
    )


def spec_heatmap() -> dict:
    d = C.DATASETS["industry_months"]
    svg = C.wrap_svg(
        C.build_heatmap(d["unit"], d["rows"], d["cols"], d["data"]),
        viewbox="0 0 1000 500", aria=("hm-title", "hm-desc"),
        title="行业 × 月份月度收益率热力图",
        desc=("六行行业、六列月份构成的收益矩阵。电子与电力设备整体偏暖（正收益），"
              "医药生物偏冷（负收益），银行行最为平稳。"),
    )
    return dict(
        fname="chart-03-heatmap.html", title="行业×月份收益热力图",
        eyebrow="HEATMAP · DIAGRAM DESIGN", h1="行业 × 月份 · 月度收益率矩阵",
        sub="六个行业 × 六个月。需要一眼扫完整个矩阵、找出哪几个格子在跳的时候用它 —— 而不是拿来逐格比较。",
        svg=svg,
        cards=[
            C.card("最暖的格子", "coral", "电子 · 4月 +15.1%",
                   "同一行的 5 月却是 −3.4%。热力图的用途是找「哪一格异常」，不是看趋势方向。"),
            C.card("最冷的行", "muted", "医药生物 · 4 冷 2 暖",
                   "全行偏冷：−8.7 / −11.5 / −5.1 三个格子构成主要的负贡献。"),
            C.card("图上看不出的", "ink", "颜色即全部",
                   "格子只有色阶与数值。样本量、换手率、市值分布都不在格子里 —— 极端格子可能是小样本噪声。"),
        ],
        footl="行业 × 月份 · 月度收益率矩阵",
        footr="示例数据 · 非真实统计 · diagram design",
    )


def spec_scatter() -> dict:
    pts = C.DATASETS["risk_return"]["points"]
    f = next(p for p in pts if p[4])
    svg = C.wrap_svg(
        C.build_scatter(pts),
        viewbox="0 0 1000 500", aria=("sc-title", "sc-desc"),
        title=f"风险—收益散点图 · {len(pts)} 只标的",
        desc=(f"散点图以年化波动率为横轴、年化收益为纵轴，展示 {len(pts)} 只标的；"
              f"标的 {f[0]}（波动 {f[1]}%、收益 {f[2]}%）单位风险收益最优。"),
    )
    return dict(
        fname="chart-04-scatter.html", title="风险—收益散点图",
        eyebrow="SCATTER · DIAGRAM DESIGN", h1=f"风险 — 收益 · {len(pts)} 只标的",
        sub="横轴年化波动率、纵轴年化收益。虚线为中位数分割线，斜虚线是 0.55 的等夏普参考线 —— 在它左上方才是「单位风险更划算」。",
        svg=svg,
        cards=[
            C.card("单位风险最优", "coral", f"标的 {f[0]}",
                   f"波动 {f[1]}% 不是最低，但收益 {f[2]}% 使其落在等夏普参考线左上方 —— 高波动不等于高性价比。"),
            C.card("右下角的陷阱", "muted", "标的 L / J / H",
                   "高波动 + 低收益：三者都在参考线右下方，属于「多承担了风险却没换来收益」。"),
            C.card("图上看不出的", "ink", "相关性与容量",
                   "散点只说单标的的风险收益，不说它们之间的相关性，也不说策略容量。"),
        ],
        footl=f"风险 — 收益 · {len(pts)} 只标的",
        footr="示例数据 · 非真实统计 · diagram design",
    )


SPECS = [spec_bar, spec_line, spec_heatmap, spec_scatter]


def main() -> int:
    paths = [C.render_page(s(), OUT) for s in SPECS]
    for p in paths:
        print(f"[OK] {p.name}  {p.stat().st_size} B")
    print(f"\n共 {len(paths)} 个文件 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
