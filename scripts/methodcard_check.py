#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[自研工具] methodcard_check —— 方法原理卡片几何自检器。

名称：methodcard_check
用途：对 methodcard 引擎产出的卡片做几何级机器验收：
      ① 静态解析 HTML 内联 SVG：图元（rect/circle/ellipse/line/polyline）是否越出 viewBox；
      ② 渲染一张加高截图：卡面区域之下不得有内容（版面溢出检测）；
      ③ 可选：断言 PNG 尺寸 == 卡面尺寸 × 倍率。
适用场景：卡片交付前与 check_vector_export.py 配合 —— 后者判「PDF 是不是合格矢量件」，
      本器判「图形几何有没有越界、版面有没有被撑破」（两者判据不相交）。
仓库：https://github.com/Garvin666/ai-workflow-tools（待推送）

诚实边界：
  · path 元素的 d 数据不检查（Bézier 解析面过大；公式 path 由 ziamath 保证且另有探针）
    —— 计数后按「未检测」报出，不报 PASS。
  · text 元素按锚点坐标粗查（字宽不可靠），只报 WARN 不计 FAIL。
  · 溢出检测基于「卡面之下应为纯白」这一版面事实（卡面底色 #FAF8EC 非白）。

用法：
    python methodcard_check.py card.html --png card.png
    python methodcard_check.py card.html --no-render      # 只做 SVG 静态检查
    python methodcard_check.py --selftest
退出码：0 = 无 FAIL；1 = 有 FAIL；2 = 用法错。
"""
from __future__ import annotations

import argparse
import math
import pathlib
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

TOL = 2.0
SVG_NS = "http://www.w3.org/2000/svg"


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _extract_svgs(html: str):
    return re.findall(r"<svg\b.*?</svg>", html, flags=re.S)


def check_svg(svg_text: str):
    """检查单个 SVG 片段；返回 (fails:list, warns:list, n_path:int)。"""
    fails, warns = [], []
    n_path = 0
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as e:
        return [f"SVG 解析失败: {e}"], [], 0
    vb = root.get("viewBox")
    if not vb:
        return fails, ["无 viewBox，跳过几何检查"], 0
    x0, y0, w, h = (_f(t) for t in vb.split())

    def inside(x, y):
        return (x0 - TOL <= x <= x0 + w + TOL) and (y0 - TOL <= y <= y0 + h + TOL)

    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "rect":
            x, y = _f(el.get("x")), _f(el.get("y"))
            rw, rh = _f(el.get("width")), _f(el.get("height"))
            for px, py, what in ((x, y, "左上"), (x + rw, y + rh, "右下")):
                if not inside(px, py):
                    fails.append(f"rect 越界（{what} {px:g},{py:g}）")
        elif tag == "circle":
            cx, cy, r = _f(el.get("cx")), _f(el.get("cy")), _f(el.get("r"))
            for px, py, what in ((cx - r, cy, "左"), (cx + r, cy, "右"),
                                 (cx, cy - r, "上"), (cx, cy + r, "下")):
                if not inside(px, py):
                    fails.append(f"circle 越界（{what} {px:g},{py:g}）")
        elif tag == "ellipse":
            cx, cy, rx, ry = (_f(el.get("cx")), _f(el.get("cy")),
                              _f(el.get("rx")), _f(el.get("ry")))
            rot = 0.0
            m = re.search(r"rotate\(\s*(-?[\d.]+)", el.get("transform", ""))
            if m:
                rot = float(m.group(1))
            a = math.radians(rot)
            hw = math.sqrt((rx * math.cos(a)) ** 2 + (ry * math.sin(a)) ** 2)
            hh = math.sqrt((rx * math.sin(a)) ** 2 + (ry * math.cos(a)) ** 2)
            for px, py, what in ((cx - hw, cy, "左"), (cx + hw, cy, "右"),
                                 (cx, cy - hh, "上"), (cx, cy + hh, "下")):
                if not inside(px, py):
                    fails.append(f"ellipse 越界（{what} {px:g},{py:g} rot={rot:g}）")
        elif tag == "line":
            for px, py, what in ((_f(el.get("x1")), _f(el.get("y1")), "起"),
                                 (_f(el.get("x2")), _f(el.get("y2")), "终")):
                if not inside(px, py):
                    fails.append(f"line 越界（{what} {px:g},{py:g}）")
        elif tag == "polyline" or tag == "polygon":
            pts = re.findall(r"(-?[\d.]+),(-?[\d.]+)", el.get("points", ""))
            for i, (pxs, pys) in enumerate(pts):
                px, py = float(pxs), float(pys)
                if not inside(px, py):
                    fails.append(f"{tag} 越界（点{i} {px:g},{py:g}）")
                    break
        elif tag == "text":
            tx = el.get("x")
            ty = el.get("y")
            if tx is None or ty is None:
                continue
            px, py = _f(tx), _f(ty)
            if not inside(px, py):
                warns.append(f"text 锚点可疑（{px:g},{py:g}）")
        elif tag == "path":
            n_path += 1
    return fails, warns, n_path


def region_nonwhite(im, y_from: int) -> int:
    """统计 im 中 y >= y_from 的非白像素数（白 = 各通道 ≥250）。"""
    region = im.crop((0, y_from, im.width, im.height))
    px = region.load()
    bad = 0
    for yy in range(region.height):
        for xx in range(region.width):
            r, g, b = px[xx, yy]
            if r < 250 or g < 250 or b < 250:
                bad += 1
    return bad


def check_overflow(html_path: pathlib.Path, card_w=1200, card_h=1600, pad=150):
    """渲染加高截图，检查卡面之下无内容。返回 (state, msg)。state ∈ {PASS, FAIL, SKIP}。"""
    try:
        import methodcard_build as B
        chrome = B._find_chrome()
    except Exception as e:  # noqa: BLE001
        return "SKIP", f"无法定位 Chrome（{e}）——未检测"
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001
        return "SKIP", "缺 Pillow——未检测"

    with tempfile.TemporaryDirectory() as td:
        png = pathlib.Path(td) / "tall.png"
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=1",
             f"--window-size={card_w},{card_h + pad}",
             f"--screenshot={png}", html_path.resolve().as_uri()],
            capture_output=True, timeout=120)
        if not png.exists():
            return "SKIP", "截图未产出——未检测"
        im = Image.open(png).convert("RGB")
        if (im.width, im.height) != (card_w, card_h + pad):
            return "FAIL", f"加高截图尺寸异常 {im.size}"
        bad = region_nonwhite(im, card_h + 2)
        if bad:
            return "FAIL", f"卡面之下发现 {bad} 个非白像素（版面溢出）"
    return "PASS", "卡面之下无内容溢出"


def main():
    ap = argparse.ArgumentParser(description="methodcard 几何自检器")
    ap.add_argument("html", nargs="?", help="卡片 HTML")
    ap.add_argument("--png", help="卡面 PNG（断言尺寸 = 卡面 × 倍率）")
    ap.add_argument("--card-size", default="1200x1600", help="卡面尺寸 px（默认 1200x1600）")
    ap.add_argument("--no-render", action="store_true", help="跳过溢出渲染检查")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()
    if not args.html:
        ap.print_help()
        return 2

    cw, ch = (int(t) for t in args.card_size.lower().split("x"))
    html_path = pathlib.Path(args.html)
    html = html_path.read_text(encoding="utf-8")
    svgs = _extract_svgs(html)

    fails, warns, n_path_total, n_svg = [], [], 0, 0
    for i, s in enumerate(svgs):
        f, w, np_ = check_svg(s)
        fails += [f"[svg#{i}] {m}" for m in f]
        warns += [f"[svg#{i}] {m}" for m in w]
        n_path_total += np_
        n_svg += 1

    print(f"== {html_path.name} ==")
    print(f"  SVG 片段 {n_svg} 个：FAIL={len(fails)} WARN={len(warns)}"
          f"（path 元素 {n_path_total} 个未检——诚实边界）")
    for m in fails:
        print(f"    [FAIL] {m}")
    for m in warns:
        print(f"    [WARN] {m}")

    if args.png:
        try:
            from PIL import Image
            im = Image.open(args.png)
            if im.size == (cw * 2, ch * 2):
                print(f"  PNG 尺寸：{im.size[0]}x{im.size[1]} == {cw}x{ch} × 2 ✓")
            else:
                print(f"  [FAIL] PNG 尺寸 {im.size[0]}x{im.size[1]} != {cw}x{ch} × 2")
                fails.append("PNG 尺寸不符")
        except Exception as e:  # noqa: BLE001
            print(f"  [SKIP] PNG 检查不可用（{e}）——未检测")

    if not args.no_render:
        state, msg = check_overflow(html_path, cw, ch)
        print(f"  版面溢出：{state} —— {msg}")
        if state == "FAIL":
            fails.append(msg)

    print(f"  结果：FAIL={len(fails)} WARN={len(warns)}"
          f"{'（未检测项已标注）' if not args.no_render else '（溢出检查已跳过）'}")
    return 1 if fails else 0


def _selftest():
    """5 用例：1 正 4 反（circle/rect/ellipse-rot/polyline 各撞一个分支）+ 2 白区像素对照。"""
    ok_svg = (f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
              '<rect x="5" y="5" width="90" height="90"/>'
              '<circle cx="50" cy="50" r="40"/>'
              '<ellipse cx="50" cy="50" rx="30" ry="10" transform="rotate(45 50 50)"/>'
              '<line x1="0" y1="0" x2="100" y2="100"/>'
              '<polyline points="10,10 90,10 90,90"/></svg>')
    f0, _, _ = check_svg(ok_svg)
    assert not f0, f"正例误报: {f0}"

    bad_circle = (f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
                  '<circle cx="95" cy="50" r="20"/></svg>')
    f1, _, _ = check_svg(bad_circle)
    assert f1, "circle 越界未检出"

    bad_rect = (f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
                '<rect x="90" y="10" width="30" height="30"/></svg>')
    f2, _, _ = check_svg(bad_rect)
    assert f2, "rect 越界未检出"

    bad_ell = (f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
               '<ellipse cx="80" cy="50" rx="40" ry="10" transform="rotate(30 80 50)"/></svg>')
    f3, _, _ = check_svg(bad_ell)
    assert f3, "旋转椭圆越界未检出"

    bad_poly = (f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
                '<polyline points="10,10 90,10 90,120"/></svg>')
    f4, _, _ = check_svg(bad_poly)
    assert f4, "polyline 越界未检出"

    # 白区像素对照（需要 Pillow；缺则明示跳过）
    try:
        from PIL import Image
        im_white = Image.new("RGB", (60, 40), "#FFFFFF")
        im_dirty = Image.new("RGB", (60, 40), "#FFFFFF")
        for x in range(10, 20):
            im_dirty.putpixel((x, 35), (0, 0, 0))
        assert region_nonwhite(im_white, 2) == 0, "纯白区误报"
        assert region_nonwhite(im_dirty, 2) > 0, "脏区未检出"
        pixel_msg = "白/脏两对照过"
    except ImportError:
        pixel_msg = "Pillow 缺——像素对照未检测"

    print(f"[selftest] SVG 用例 5 个（1 正 4 反）全过；像素对照：{pixel_msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
