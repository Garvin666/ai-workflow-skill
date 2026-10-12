# -*- coding: utf-8 -*-
"""下载 Playfair Display（fontsource 静态 woff2）+ @font-face 内嵌渲染探针。"""
import base64, pathlib, subprocess, urllib.request
import pymupdf

TASK = pathlib.Path(__file__).resolve().parent
FDIR = TASK / "tmp" / "fonts"
FDIR.mkdir(parents=True, exist_ok=True)
OUT = TASK / "tmp" / "font-probe"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

FILES = {
    "pf600": "https://cdn.jsdelivr.net/npm/@fontsource/playfair-display@5/files/playfair-display-latin-600-normal.woff2",
    "pf700": "https://cdn.jsdelivr.net/npm/@fontsource/playfair-display@5/files/playfair-display-latin-700-normal.woff2",
}
local = {}
for name, u in FILES.items():
    p = FDIR / f"{name}.woff2"
    if not p.exists():
        with opener.open(u, timeout=30) as r:
            p.write_bytes(r.read())
    local[name] = p
    print(f"{name}: {p.stat().st_size}B")

b64 = {k: base64.b64encode(v.read_bytes()).decode() for k, v in local.items()}
ff = (
    "@font-face{font-family:'PlayfairX';font-style:normal;font-weight:600;"
    f"src:url(data:font/woff2;base64,{b64['pf600']}) format('woff2');}}"
    "@font-face{font-family:'PlayfairX';font-style:normal;font-weight:700;"
    f"src:url(data:font/woff2;base64,{b64['pf700']}) format('woff2');}}"
)
html = OUT / "pf-embed.html"
pdf = OUT / "pf-embed.pdf"
html.write_text(
    f'<!doctype html><html><head><style>{ff}</style></head><body style="margin:0">'
    f'<div style="font-family:\'PlayfairX\',serif;font-weight:700;font-size:82px;padding:20px">'
    f'Ridge Regression #01</div>'
    f'<div style="font-family:\'PlayfairX\',serif;font-weight:600;font-size:40px;padding:0 20px">'
    f'Gaussian Mixture K-Means ABCD</div>'
    f'</body></html>', encoding="utf-8")

def check(pdf):
    doc = pymupdf.open(pdf)
    try:
        page = doc[0]
        fonts = [(f[2], f[3]) for f in page.get_fonts(full=True)]
        d = page.get_text("dict")
        spans = []
        for block in d["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    spans.append((span["font"], span["text"]))
        return fonts, spans
    finally:
        doc.close()

subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf}", html.resolve().as_uri()], capture_output=True, timeout=60)
png = OUT / "pf-embed.png"
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--window-size=1000,260", f"--screenshot={png}", html.resolve().as_uri()],
               capture_output=True, timeout=60)

fonts, spans = check(pdf)
print("--- fonts ---")
for f in fonts:
    print("  ", f)
print("--- spans ---")
for s in spans:
    print("  ", s)
