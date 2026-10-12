# -*- coding: utf-8 -*-
"""样板卡 2：GMM（高斯混合模型）—— 复杂版（分布／软分配热力格／椭圆更新／收敛）。
内容自行撰写（参考图仅作版式参照）；数据为固定种子示例，可复现。
"""
import sys, pathlib, random

TASK = pathlib.Path(__file__).resolve().parents[1]
SKILL = TASK.parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

import methodcard_lib as M   # noqa: E402
import methodcard_build as B  # noqa: E402

# ---------- 示例数据（固定种子） ----------
def cluster_pts(seed, n, mx, my, sx, sy, rho=0.55):
    rnd = random.Random(seed)
    pts = []
    for _ in range(n):
        z1 = max(-2.2, min(2.2, rnd.gauss(0, 1)))
        z2 = max(-2.2, min(2.2, rnd.gauss(0, 1)))
        x = mx + sx * z1
        y = my + sy * (rho * z1 + (1 - rho ** 2) ** 0.5 * z2)
        pts.append((round(min(9.6, max(0.4, x)), 2), round(min(9.6, max(0.4, y)), 2)))
    return pts

C1 = cluster_pts(11, 24, 3.0, 2.9, 0.80, 0.62)
C2 = cluster_pts(22, 24, 6.8, 6.7, 0.82, 0.70)

# 1D 投影示意点（步骤 1 底部点串：左峰 8 个、右峰 7 个）
DOTS = [(-3.9, 0.0), (-3.5, 0.5), (-3.1, 1.0), (-2.8, 0.25), (-2.5, 0.65),
        (-2.2, 0.05), (-1.9, 0.5), (-1.5, 0.0),
        (1.4, 0.5), (1.8, 0.0), (2.2, 0.65), (2.6, 0.2), (3.0, 0.5),
        (3.4, 0.05), (3.8, 0.35)]

# 责任矩阵（E 步热力格；每行和为 1）
RESP = [[0.95, 0.05], [0.88, 0.12], [0.72, 0.28],
        [0.24, 0.76], [0.10, 0.90], [0.06, 0.94]]

# 收敛序列（数学自洽：LOGLIK 差值与 DL 逐项一致）
DL = [0.44, 0.31, 0.19, 0.11, 0.06, 0.03, 0.01]
LOGLIK = [-3.18, -2.74, -2.43, -2.24, -2.13, -2.07, -2.04, -2.03]

# ---------- 子图 ----------
def fig_step1():
    # 窄高（暖）+ 宽矮（蓝）→ 叠加后总密度与任一分量形态明显不同
    comps = [(-2.2, 0.85, 0.6, M.TOKENS["warm_deep"]), (2.6, 1.6, 0.4, M.TOKENS["blue"])]
    return M.fig_density(246, 250, comps, xr=(-6.5, 6.5), dot_pts=DOTS,
                         total_color=M.TOKENS["blue_deep"])

def fig_step2():
    return M.fig_heatgrid(246, 250, RESP,
                          row_labels=["P1", "P2", "P3", "P4", "P5", "P6"],
                          col_labels=["C1", "C2"])

def fig_step3():
    clusters = [
        (C1[::2][:10], M.TOKENS["blue"], (3.0, 2.9), [(26, 19, -28, None), (50, 36, -28, "3 3")]),
        (C2[::2][:10], M.TOKENS["warm_deep"], (6.8, 6.7), [(25, 20, -24, None), (48, 37, -24, "3 3")]),
    ]
    return M.fig_cluster_ellipses(246, 250, clusters, dot=3.3)

def fig_step4():
    return M.fig_coef_bars(246, 250, ["1", "2", "3", "4", "5", "6", "7"],
                           [(DL, M.TOKENS["blue"])], ylab="Δ lnL")

def fig_hero1():
    clusters = [
        (C1, M.TOKENS["blue"], (3.0, 2.9), [(34, 20, -30, None), (78, 46, -30, "4 4")]),
        (C2, M.TOKENS["warm_deep"], (6.8, 6.7), [(32, 21, -26, None), (74, 48, -26, "4 4")]),
    ]
    return M.fig_cluster_ellipses(428, 304, clusters, dot=4.2,
                                  legend=[("分量 1", M.TOKENS["blue"]),
                                          ("分量 2", M.TOKENS["warm_deep"])],
                                  axis_label=("y", "x"))

def fig_hero2():
    return M.fig_trace(428, 304, list(range(len(LOGLIK))), [(LOGLIK, M.TOKENS["blue"], 2.4)],
                       xlab="迭代轮次 t", ylab="对数似然", yr=(-3.4, -1.9),
                       marks=[(0, LOGLIK[0], M.TOKENS["blue"]), (7, LOGLIK[-1], M.TOKENS["red"])],
                       note=(4.0, -2.06, "趋于平稳"))

HERO_BODY = (
    f'<div class="hb-fig">{fig_hero1()}</div>'
    f'<div class="hb-arrow">{M.fig_steps_arrow(64, 36)}</div>'
    f'<div class="hb-fig">{fig_hero2()}</div>'
    f'<div class="badge">软分配<br>单调收敛</div>'
)

# ---------- 卡片定义 ----------
CARD = {
    "series": ["MACHINE LEARNING", "ALGORITHM SERIES"],
    "num": "#02",
    "title": "Gaussian Mixture",
    "subtitle": "高斯混合模型",
    "tags": ["CLUSTERING", "EM", "DENSITY"],
    "idea_text": "用 K 个高斯分布加权叠加来刻画任意形状的数据分布；每个样本以概率（而非硬标签）归属各分量，EM 交替估计责任与参数。",
    "idea_eq_svg": M.eq_scaled(r"p(x)=\sum_{k}\pi_{k}\,\mathcal{N}(x\mid\mu_{k},\Sigma_{k})",
                               52, M.TOKENS["ink"]),
    "steps": [
        {"n": 1, "title": "混合假设", "note": "单峰高斯不足以描述多峰或重叠数据；改用 K 个高斯分量按权重叠加。",
         "fig": fig_step1(), "cap": "混合密度：分量（细）与总密度（粗）"},
        {"n": 2, "title": "E 步·估责任", "note": "按当前参数计算每个样本对各分量的责任（后验概率），即软分配。",
         "fig": fig_step2(), "cap": "责任矩阵（颜色越深=责任越大）"},
        {"n": 3, "title": "M 步·更新参数", "note": "以责任为权重，重新估计各分量的均值、协方差与混合权重。",
         "fig": fig_step3(), "cap": "按责任加权重新估计各分量"},
        {"n": 4, "title": "迭代至收敛", "note": "交替 E/M 步，对数似然的增量逐步减小并趋于零。",
         "fig": fig_step4(), "cap": "对数似然增量（横轴=迭代轮次）"},
    ],
    "hero": {"title": "拟合与收敛", "body": HERO_BODY,
             "cap": "左：两个分量（蓝/暖）拟合出的簇结构与等密度椭圆；右：EM 迭代的对数似然单调上升并趋于平稳。"},
    "takeaway": "GMM 用高斯分量的加权混合逼近复杂分布：EM 以软分配交替更新责任与参数，单调提升对数似然 —— 处理重叠簇、软聚类与密度估计的标准工具。",
}

if __name__ == "__main__":
    out = TASK / "output" / "card-gmm.html"
    B.write_html(CARD, out)
    print("HTML:", out)
