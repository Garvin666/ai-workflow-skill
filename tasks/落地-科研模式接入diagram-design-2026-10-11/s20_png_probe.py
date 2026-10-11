# -*- coding: utf-8 -*-
"""PNG 通道分段计时探针：找出 1m42s 花在哪一步，并查 SVG 元素盒为何多 2px。"""
import pathlib
import time

from playwright.sync_api import sync_playwright

SRC = pathlib.Path(__file__).resolve().parent / "output" / "chart-01-bar.html"
OFFLINE = True


def t0():
    return time.time()


def log(label, t):
    print(f"  {label:<22} {time.time() - t:7.2f}s")
    return time.time()


print("== 分段计时 ==")
a = t0()
with sync_playwright() as p:
    a = log("sync_playwright 进入", a)
    browser = p.chromium.launch(channel="chrome")
    a = log("launch(channel=chrome)", a)
    page = browser.new_page(device_scale_factor=2)
    a = log("new_page", a)
    page.set_default_timeout(20000)
    if OFFLINE:
        page.route("**/*", lambda r: r.continue_()
                   if r.request.url.startswith("file:") else r.abort())
    a = log("route 安装", a)
    page.goto(SRC.resolve().as_uri(), wait_until="domcontentloaded")
    a = log("goto", a)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception as e:
        print(f"  networkidle 超时：{type(e).__name__}")
    a = log("networkidle", a)
    try:
        page.wait_for_function("document.fonts.status === 'loaded'", timeout=8000)
    except Exception as e:
        print(f"  fonts 未 settled：{type(e).__name__}")
    a = log("fonts.status", a)

    info = page.evaluate("""() => {
        const s = document.querySelector('svg');
        const cs = getComputedStyle(s);
        const r = s.getBoundingClientRect();
        return {rect: [r.width, r.height], display: cs.display, border: cs.borderWidth,
                padding: cs.padding, margin: cs.margin, box: cs.boxSizing,
                radius: cs.borderTopLeftRadius, shadow: cs.boxShadow.slice(0, 40),
                w: s.getAttribute('width'), h: s.getAttribute('height'),
                vb: s.getAttribute('viewBox'), count: document.querySelectorAll('svg').length};
    }""")
    for k, v in info.items():
        print(f"  {k:<10} = {v}")
    a = log("evaluate 取盒", a)
    s = page.locator("svg").first
    s.evaluate("""el => {
        const p = el.getAttribute('viewBox').trim().split(/[\\s,]+/).map(Number);
        el.style.setProperty('width', p[2] + 'px', 'important');
        el.style.setProperty('height', p[3] + 'px', 'important');
        el.style.setProperty('max-width', 'none', 'important');
        el.style.setProperty('border', 'none', 'important');
        el.style.setProperty('padding', '0', 'important');
        el.style.setProperty('margin', '0', 'important');
        el.style.setProperty('box-shadow', 'none', 'important');
        el.style.setProperty('display', 'block', 'important');
        return null;
    }""")
    a = log("钉尺寸", a)
    box = s.bounding_box()
    print(f"  bounding_box = {box}")
    out = pathlib.Path(__file__).parent / "tmp_probe" / "probe.png"
    out.parent.mkdir(exist_ok=True)
    s.screenshot(path=str(out), omit_background=True)
    a = log("screenshot", a)
    browser.close()
    a = log("browser.close", a)
print(f"  总 {time.time() - a:.2f}s(尾)")
from PIL import Image  # noqa: E402
print(f"  产物 = {Image.open(out).size} {Image.open(out).mode}")
