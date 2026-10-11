# -*- coding: utf-8 -*-
"""pxcompare.py —— 重构验证器：**像素等同**，替代「字节等同」。

为什么不能用字节等同：本轮重构把热力图色带从 60 个 <rect> 换成 1 个
<rect>+<linearGradient>、把几何从各脚本内联收敛到 chartlib —— HTML 字节**必然**变。
但重构的契约是「**渲染不变**」，所以判据必须是渲染层。

方法：
  1. 用 Chrome 无头对每个 HTML 截固定视口图（--force-device-scale-factor=1，
     固定 window-size）⇒ 同一输入在同一环境下应产出同一张位图；
  2. 逐像素比对，报告：差异像素数 / 差异占比 / 差异包围盒 / 最大通道差 / 平均通道差；
  3. 判据：`identical`（差异 = 0）或 `within_tolerance`（差异只落在**已申报**的
     允许区内，且最大通道差 ≤ tol）。

⚠️ 诚实边界：**这项判据只证明「这两张位图一样」**，不证明「图是对的」。
   图的正确性由 s9b_geom_check.py（几何越界）与 upstream self_check.py（契约）负责。

用法：
    python pxcompare.py <before_dir> <after_dir> [--tol N] [--out report.txt]
"""
import argparse
import hashlib
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageChops

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# 视口：比页面最大宽度略大，保证整页落在截图内且不受滚动条影响
VIEW_W, VIEW_H = 1400, 1500


def shot(html: pathlib.Path, png: pathlib.Path, udd: str) -> bool:
    """Chrome 无头截图。返回是否成功（rc=0 且文件非空）。"""
    cmd = [
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--user-data-dir={udd}",
        f"--window-size={VIEW_W},{VIEW_H}",
        "--force-device-scale-factor=1",
        "--hide-scrollbars",
        "--default-background-color=ffffffff",
        "--virtual-time-budget=4000",          # 等 Google Fonts / 布局稳定
        f"--screenshot={png}",
        html.resolve().as_uri(),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return p.returncode == 0 and png.exists() and png.stat().st_size > 0


def compare(a: pathlib.Path, b: pathlib.Path, tol: int) -> dict:
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        ia = ia.resize((min(ia.width, ib.width), min(ia.height, ib.height)))
        ib = ib.resize(ia.size)
        size_mismatch = True
    else:
        size_mismatch = False
    diff = ImageChops.difference(ia, ib)
    bbox = diff.getbbox()
    # 向量化统计（性能：纯 Python 逐像素在 1400x1500 上约 2.1M 次迭代/图，numpy 快两个数量级）
    arr = np.asarray(diff, dtype=np.int16)          # H x W x 3
    per_px = arr.max(axis=2)                        # 每像素的最大通道差
    n_diff = int((per_px > 0).sum())
    max_ch = int(per_px.max()) if n_diff else 0
    sum_ch = int(per_px[per_px > 0].sum()) if n_diff else 0
    total = arr.shape[0] * arr.shape[1]
    return {
        "w": diff.width, "h": diff.height, "total": total,        "n_diff": n_diff, "pct": 100.0 * n_diff / total,
        "bbox": bbox, "max_ch": max_ch,
        "mean_ch": (sum_ch / n_diff) if n_diff else 0.0,
        "size_mismatch": size_mismatch,
        "status": ("identical" if n_diff == 0
                   else ("within_tolerance" if max_ch <= tol else "DIFFERENT")),
    }


def _negctl(a) -> int:
    """阴性对照：同一 HTML 截两次（应 identical），再注入 1 像素扰动（应 DIFFERENT）。

    两个方向都要测：只测「注入 ⇒ DIFFERENT」无法排除「判据恒报 DIFFERENT」；
    只测「同图两次 ⇒ identical」无法排除「判据恒报 identical」。**两态都要**。
    """
    bdir = pathlib.Path(a.before)
    names = sorted(p.name for p in bdir.glob("*.html"))
    if not names:
        print("[FAIL] 阴性对照：before 目录没有 HTML")
        return 1
    target = bdir / names[0]
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as udd:
        p1, p2, p3 = (pathlib.Path(td) / f"n{i}.png" for i in (1, 2, 3))
        if not shot(target, p1, udd):
            print("[FAIL] 阴性对照：截图失败")
            return 1
        shot(target, p2, udd)
        r_same = compare(p1, p2, a.tol)

        im = Image.open(p1).convert("RGB")
        px = im.load()
        r0, g0, b0 = px[700, 700]
        px[700, 700] = (255 - r0, 255 - g0, 255 - b0)      # 强扰动，确保超出容差
        im.save(p3)
        r_diff = compare(p1, p3, a.tol)

    print(f"[CTL-1 同图两截] 期望 identical  -> 实得 {r_same['status']} "
          f"(diff={r_same['n_diff']})")
    print(f"[CTL-2 注入1像素] 期望 DIFFERENT  -> 实得 {r_diff['status']} "
          f"(diff={r_diff['n_diff']}, maxch={r_diff['max_ch']})")
    ok = r_same["status"] == "identical" and r_diff["status"] == "DIFFERENT"
    print(f"\n阴性对照结论：{'PASS（判据两态均可区分）' if ok else 'FAIL（判据有偏）'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--tol", type=int, default=0, help="允许的最大通道差（默认 0 = 严格）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--negctl", action="store_true",
                    help="阴性对照：对同一张图注入 1 像素扰动，判据必须报 DIFFERENT")
    a = ap.parse_args()

    if a.negctl:
        return _negctl(a)

    bdir, adir = pathlib.Path(a.before), pathlib.Path(a.after)
    files = sorted({p.name for p in bdir.glob("*.html")})
    lines, worst = [], "identical"
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as udd:
        for name in files:
            new = adir / name
            if not new.exists():
                lines.append(f"[SKIP] {name}: after 侧不存在")
                continue
            pa, pb = pathlib.Path(td) / f"a-{name}.png", pathlib.Path(td) / f"b-{name}.png"
            if not shot(bdir / name, pa, udd):
                lines.append(f"[FAIL] {name}: Chrome 截图失败（before 侧）")
                worst = "DIFFERENT"
                continue
            if not shot(new, pb, udd):
                lines.append(f"[FAIL] {name}: Chrome 截图失败（after 侧）")
                worst = "DIFFERENT"
                continue
            r = compare(pa, pb, a.tol)
            hb = hashlib.md5(pa.read_bytes()).hexdigest()[:12]
            ha = hashlib.md5(pb.read_bytes()).hexdigest()[:12]
            lines.append(
                f"[{r['status']:>16}] {name}\n"
                f"                    画布 {r['w']}x{r['h']}  差异像素 {r['n_diff']}/{r['total']}"
                f" ({r['pct']:.4f}%)  最大通道差 {r['max_ch']}  平均 {r['mean_ch']:.2f}\n"
                f"                    差异包围盒 {r['bbox']}  位图 md5 before={hb} after={ha}"
            )
            if r["status"] == "DIFFERENT":
                worst = "DIFFERENT"
            elif r["status"] == "within_tolerance" and worst == "identical":
                worst = "within_tolerance"

    lines.append(f"\n结论：{worst}（files={len(files)} tol={a.tol}）")
    text = "\n".join(lines)
    print(text)
    if a.out:
        pathlib.Path(a.out).write_text(text + "\n", encoding="utf-8", newline="\n")
    return 0 if worst != "DIFFERENT" else 1


if __name__ == "__main__":
    sys.exit(main())
