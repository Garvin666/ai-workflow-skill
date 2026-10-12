# -*- coding: utf-8 -*-
"""字体探针：最小复现 Sitka → Type3，并测试备选标题字体栈。"""
import pathlib, subprocess, sys

TASK = pathlib.Path(__file__).resolve().parent
TMP = TASK / "tmp" / "font-probe"
TMP.mkdir(parents=True, exist_ok=True)

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

CASES = {
    "sitka":   "'Sitka Banner','Sitka Display','Sitka Heading','Cambria','Georgia',serif",
    "cambria": "Cambria,Georgia,serif",
    "georgia": "Georgia,serif",
    "times":   "'Times New Roman','Times',serif",
    "palatino": "Palatino Linotype,Book Antiqua,Georgia,serif",
}

import pymupdf

def type3_count(pdf):
    doc = pymupdf.open(pdf)
    try:
        page = doc[0]
        return sum(1 for f in page.get_fonts(full=True) if f[2] == "Type3")
    finally:
        doc.close()

for name, stack in CASES.items():
    html = TMP / f"{name}.html"
    pdf = TMP / f"{name}.pdf"
    html.write_text(
        f'<!doctype html><html><body style="margin:0">'
        f'<div style="font-family:{stack};font-weight:700;font-size:82px;padding:40px;color:#1F1E1C">'
        f'Ridge Regression #01</div>'
        f'<div style="font-family:{stack};font-weight:600;font-size:22px;padding:0 40px">Gaussian Mixture 高斯</div>'
        f'</body></html>', encoding="utf-8")
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           f"--print-to-pdf={pdf}", html.resolve().as_uri()]
    subprocess.run(cmd, capture_output=True, timeout=60)
    n = type3_count(pdf)
    print(f"[{name:8s}] Type3={n}  ({'OK' if n == 0 else 'FAIL'})")
