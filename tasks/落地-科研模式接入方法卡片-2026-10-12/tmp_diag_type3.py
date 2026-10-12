# -*- coding: utf-8 -*-
"""诊断：定位 PDF 中 Type3 字体及其对应文本。"""
import pathlib
import pymupdf

TASK = pathlib.Path(__file__).resolve().parent
for name in ("card-ridge", "card-gmm"):
    pdf = TASK / "output" / "export" / f"{name}.pdf"
    print("=" * 60)
    print(name)
    print("=" * 60)
    doc = pymupdf.open(pdf)
    page = doc[0]
    print("--- fonts ---")
    for f in page.get_fonts(full=True):
        print(f)
    print("--- spans by font ---")
    seen = {}
    d = page.get_text("dict")
    for block in d["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                key = span["font"]
                seen.setdefault(key, []).append(span["text"])
    for k, v in seen.items():
        joined = " | ".join(v)
        print(f"[{k}] len={len(joined)}: {joined[:120]}")
    doc.close()
