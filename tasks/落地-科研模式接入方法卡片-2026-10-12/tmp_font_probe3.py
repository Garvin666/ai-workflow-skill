# -*- coding: utf-8 -*-
"""列出本机候选衬线字体 + 逐候选做 Type3 探针。"""
import pathlib, subprocess
import pymupdf

OUT = pathlib.Path(__file__).resolve().parent / "tmp" / "font-probe"
OUT.mkdir(parents=True, exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# 1) 枚举候选（名字含衬线关键词）
fonts_dir = pathlib.Path(r"C:\Windows\Fonts")
cands = []
for p in sorted(fonts_dir.iterdir()):
    n = p.name.lower()
    if any(k in n for k in ("bodoni", "garamond", "constantia", "cambria", "georgia",
                            "palatino", "bookman", "century", "didot", "sitka", "times",
                            "candara", "corbel", "perpetua", "baskerville")):
        cands.append(p.name)
print("字体文件候选：")
for c in cands:
    print("  ", c)

# 2) 对字体名栈逐个探针
STACKS = {
    "bodoni_mt": "'Bodoni MT','Bodoni 72',serif",
    "garamond":  "Garamond,serif",
    "constantia": "Constantia,serif",
    "bookman":   "'Bookman Old Style',serif",
    "century":   "'Century Schoolbook',serif",
    "palatino":  "'Palatino Linotype','Book Antiqua',serif",
    "cambria":   "Cambria,serif",
}

def type3_text(pdf):
    doc = pymupdf.open(pdf)
    try:
        page = doc[0]
        d = page.get_text("dict")
        t3 = []
        for block in d["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if "Type3" in span["font"]:
                        t3.append(span["text"])
        return "".join(t3)
    finally:
        doc.close()

print("\nType3 探针（英文标题 + 全角冒号）：")
for name, stack in STACKS.items():
    html = OUT / f"p2-{name}.html"
    pdf = OUT / f"p2-{name}.pdf"
    html.write_text(
        f'<!doctype html><html><body style="margin:0">'
        f'<div style="font-family:{stack};font-weight:700;font-size:82px;padding:20px">'
        f'Ridge Regression 0123</div>'
        f'<div style="font-family:{stack};font-weight:700;font-size:40px;padding:0 20px">'
        f'Gaussian Mixture K-Means</div>'
        f'</body></html>', encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html.resolve().as_uri()],
                   capture_output=True, timeout=60)
    t3 = type3_text(pdf)
    print(f"  [{name:12s}] Type3文本={t3!r}  {'OK' if not t3 else 'FAIL'}")

    # 同时出一张 PNG 供目检
    png = OUT / f"p2-{name}.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", "--window-size=900,300",
                    f"--screenshot={png}", html.resolve().as_uri()],
                   capture_output=True, timeout=60)
print("done")
