# -*- coding: utf-8 -*-
"""两个修法的可行性验证：
  ① 元素截图 +1px/侧 ⇒ 能否用 page.screenshot(clip=) 拿到精确尺寸？
  ② browser.close() 46s ⇒ 复用同一浏览器实例能否摊薄到每文件 ~1s？
"""
import pathlib
import time

from PIL import Image
from playwright.sync_api import sync_playwright

TASK = pathlib.Path(__file__).resolve().parent
SRCS = [TASK / "output" / f"chart-0{i}-{n}.html" for i, n in
        ((1, "bar"), (2, "line"), (3, "heatmap"), (4, "scatter"),
         (5, "bar-motion"), (6, "bar-reveal"))]
OUT = TASK / "tmp_probe"
OUT.mkdir(exist_ok=True)

PIN = """el => {
    const p = el.getAttribute('viewBox').trim().split(/[\\s,]+/).map(Number);
    el.style.setProperty('width', p[2] + 'px', 'important');
    el.style.setProperty('height', p[3] + 'px', 'important');
    el.style.setProperty('max-width', 'none', 'important');
    for (let a = el.parentElement; a; a = a.parentElement)
        a.style.setProperty('overflow', 'visible', 'important');
    return [p[2], p[3]];
}"""

print("== ① clip 精确性 ==")
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(device_scale_factor=2)
    pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
    pg.goto(SRCS[0].resolve().as_uri(), wait_until="domcontentloaded")
    s = pg.locator("svg").first
    w, h = s.evaluate(PIN)
    box = s.bounding_box()
    print(f"  bounding_box = {box}")
    e1 = OUT / "clip-element.png"
    s.screenshot(path=str(e1), omit_background=True)
    e2 = OUT / "clip-page.png"
    pg.screenshot(path=str(e2), omit_background=True, clip={
        "x": box["x"], "y": box["y"], "width": w, "height": h})
    e3 = OUT / "clip-page-floored.png"
    pg.screenshot(path=str(e3), omit_background=True, clip={
        "x": int(box["x"]), "y": int(box["y"]), "width": w, "height": h})
    for e in (e1, e2, e3):
        print(f"  {e.name:<24} {Image.open(e).size}")
    t = time.time()
    b.close()
    print(f"  close(收尾) {time.time() - t:.1f}s")

print("\n== ② 复用单实例跑 6 图 ==")
t_all = time.time()
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for src in SRCS:
        t = time.time()
        pg = b.new_page(device_scale_factor=2)
        pg.set_default_timeout(20000)
        pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
        pg.goto(src.resolve().as_uri(), wait_until="domcontentloaded")
        s = pg.locator("svg").first
        w, h = s.evaluate(PIN)
        box = s.bounding_box()
        o = OUT / (src.stem + ".png")
        pg.screenshot(path=str(o), omit_background=True,
                      clip={"x": box["x"], "y": box["y"], "width": w, "height": h})
        pg.close()
        print(f"  {src.name:<26} {time.time() - t:5.2f}s  {Image.open(o).size}")
    t = time.time()
    b.close()
    print(f"  close(收尾) {time.time() - t:.1f}s")
print(f"  6 图总耗时 {time.time() - t_all:.1f}s")
