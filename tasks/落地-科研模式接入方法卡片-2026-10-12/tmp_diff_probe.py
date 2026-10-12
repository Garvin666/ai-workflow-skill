# -*- coding: utf-8 -*-
"""diff 探针 PNG：确认不同字体栈的渲染是否真的不同。"""
import pathlib
import numpy as np
from PIL import Image

D = pathlib.Path(__file__).resolve().parent / "tmp" / "font-probe"
imgs = {}
for n in ("century", "cambria", "georgia", "times", "palatino", "bodoni_mt"):
    p = D / f"p2-{n}.png"
    if p.exists():
        imgs[n] = np.array(Image.open(p).convert("L"), dtype=np.int16)

names = list(imgs)
print("shape check:", {n: imgs[n].shape for n in names})
base = "century"
for n in names[1:]:
    a, b = imgs[base], imgs[n]
    if a.shape != b.shape:
        print(f"{base} vs {n}: shape mismatch {a.shape} vs {b.shape}")
        continue
    diff = int(np.abs(a - b).sum())
    px = int((np.abs(a - b) > 8).sum())
    print(f"{base} vs {n}: sum|d|={diff}  pixels>8={px}")
