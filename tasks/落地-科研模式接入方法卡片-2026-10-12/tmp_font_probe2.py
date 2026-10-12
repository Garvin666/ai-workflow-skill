# -*- coding: utf-8 -*-
"""字体探针 2：分解 Type3 来源（逐 span 打印）。"""
import pathlib
import pymupdf

TASK = pathlib.Path(__file__).resolve().parent
TMP = TASK / "tmp" / "font-probe"

for name in ("sitka", "cambria", "georgia", "times", "palatino"):
    pdf = TMP / f"{name}.pdf"
    doc = pymupdf.open(pdf)
    page = doc[0]
    d = page.get_text("dict")
    t3 = []
    others = []
    for block in d["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if "Type3" in span["font"]:
                    t3.append(f'{span["font"]}:{span["text"]!r}')
                else:
                    others.append(f'{span["font"]}:{span["text"]!r}')
    print(f"== {name} ==")
    print("  T3:", "  ".join(t3))
    print("  OK:", "  ".join(others))
    doc.close()
