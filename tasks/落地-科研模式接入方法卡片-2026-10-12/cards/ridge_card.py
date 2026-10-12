# -*- coding: utf-8 -*-
"""样板卡 1：Ridge Regression（岭回归）。
内容自行撰写（参考图仅作版式参照）；子图数据为显式示例数据（固定种子，可复现）。
"""
import sys, pathlib, random

TASK = pathlib.Path(__file__).resolve().parents[1]
SKILL = TASK.parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

import methodcard_lib as M   # noqa: E402
import methodcard_build as B  # noqa: E402

# ---------- 示例数据（固定种子） ----------
def scatter_pts(seed=7, n=26):
    rnd = random.Random(seed)
    pts = []
    for _ in range(n):
        x = 0.4 + 9.0 * rnd.random()
        y = 0.78 * x + 1.05 + rnd.gauss(0, 0.92)
        pts.append((round(x, 2), round(max(y, 0.4), 2)))
    return pts

PTS = scatter_pts()
# 两条参考线：普通回归（稍陡）与岭回归（稍缓）
OLS_LINE = [(0.4, 0.4 * 0.86 + 0.95), (9.4, 9.4 * 0.86 + 0.95)]
RIDGE_LINE = [(0.4, 0.4 * 0.63 + 1.55), (9.4, 9.4 * 0.63 + 1.55)]

COEF_LABELS = ["M1", "M2", "M3", "M4", "M5"]
OLS_VALS = [0.95, 1.30, -0.82, 1.05, -0.48]
RIDGE_VALS = [0.58, 0.79, -0.50, 0.64, -0.29]

# ---------- 子图 ----------
def fig_step1():
    return M.fig_scatter_fit(246, 250, PTS, lines_=[(OLS_LINE, M.TOKENS["ink_muted"], 2.2)],
                             xr=(0, 10), yr=(0, 10), dot=4.0, axis_label=("y", "x"))

def fig_step2():
    e1 = M.eq_scaled(r"\min_{w}\ \|y - Xw\|^{2}", 30, M.TOKENS["ink"])
    e2 = M.eq_scaled(r"+\ \lambda\|w\|_{2}^{2}", 27, M.TOKENS["blue_deep"])
    return (f'<div class="fb">'
            f'<div class="fb-l1">{e1}</div>'
            f'<div class="fb-l2">{e2}<span class="fb-tag">L2 正则项</span></div>'
            f'</div>')

def fig_step3():
    return M.fig_contour(246, 250)

def fig_step4():
    return M.fig_coef_bars(246, 250, COEF_LABELS,
                           [(OLS_VALS, M.TOKENS["gray_fill"]), (RIDGE_VALS, M.TOKENS["blue"])],
                           legend=[("普通回归", M.TOKENS["gray_fill"]), ("岭回归", M.TOKENS["blue"])],
                           ylab="")

def fig_hero1():
    return M.fig_scatter_fit(428, 304, PTS,
                             lines_=[(OLS_LINE, M.TOKENS["ink_muted"], 2.4),
                                     (RIDGE_LINE, M.TOKENS["blue"], 2.6)],
                             xr=(0, 10), yr=(0, 10), dot=4.4,
                             legend=[("普通回归", M.TOKENS["ink_muted"]), ("岭回归", M.TOKENS["blue"])],
                             axis_label=("y", "x"))

def fig_hero2():
    return M.fig_coef_bars(428, 304, COEF_LABELS,
                           [(OLS_VALS, M.TOKENS["gray_fill"]), (RIDGE_VALS, M.TOKENS["blue"])],
                           legend=[("普通回归", M.TOKENS["gray_fill"]), ("岭回归", M.TOKENS["blue"])],
                           ylab="系数值")

HERO_BODY = (
    f'<div class="hb-fig">{fig_hero1()}</div>'
    f'<div class="hb-arrow">{M.fig_steps_arrow(64, 36)}</div>'
    f'<div class="hb-fig">{fig_hero2()}</div>'
    f'<div class="badge">减小方差<br>提升稳定性</div>'
)

# ---------- 卡片定义 ----------
CARD = {
    "series": ["MACHINE LEARNING", "ALGORITHM SERIES"],
    "num": "#01",
    "title": "Ridge Regression",
    "subtitle": "岭回归",
    "tags": ["REGRESSION", "L2", "SHRINKAGE"],
    "idea_text": "最小二乘在特征相关时会放大系数方差；岭回归在损失中加入 L2 惩罚，把系数向零收缩 —— 用少量偏差换取方差的大幅下降。",
    "idea_eq_svg": M.eq_scaled(r"\min_{w}\ \|y - Xw\|^{2} + \lambda\|w\|_{2}^{2}", 52, M.TOKENS["ink"]),
    "steps": [
        {"n": 1, "title": "建立线性模型", "note": "假设输出与输入近似线性相关，写出模型 y = Xw + ε。",
         "fig": fig_step1(), "cap": "散点与拟合线"},
        {"n": 2, "title": "加入 L2 惩罚", "note": "在残差平方和之外，对系数平方和施加 λ 倍惩罚。",
         "fig": fig_step2(), "cap": "目标函数"},
        {"n": 3, "title": "优化求解", "note": "解得 w = (XᵀX + λI)⁻¹Xᵀy，在拟合与复杂度间平衡。",
         "fig": fig_step3(), "cap": "解的几何（红=普通解，蓝=岭解）"},
        {"n": 4, "title": "得到稳健结果", "note": "系数被整体收缩、更稳定，但通常不会精确归零。",
         "fig": fig_step4(), "cap": "系数收缩对比"},
    ],
    "hero": {"title": "收缩示意", "body": HERO_BODY,
             "cap": "同一组数据：普通回归（灰）与岭回归（蓝）的拟合线与系数对照"},
    "takeaway": "岭回归通过 L2 正则化收缩系数：牺牲少量无偏性，换取方差的大幅下降 —— 多重共线性或小样本场景下的稳健选择。",
}

if __name__ == "__main__":
    out = TASK / "output" / "card-ridge.html"
    B.write_html(CARD, out)
    print("HTML:", out)
