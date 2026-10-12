# -*- coding: utf-8 -*-
"""s5 渲染：把卡片 HTML 导出为 PNG（@2x）。用法：s5_render.py card-ridge [scale]"""
import sys, pathlib
TASK = pathlib.Path(__file__).resolve().parent
SKILL = TASK.parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import methodcard_build as B  # noqa: E402

name = sys.argv[1] if len(sys.argv) > 1 else "card-ridge"
scale = int(sys.argv[2]) if len(sys.argv) > 2 else 2
html = TASK / "output" / f"{name}.html"
png = TASK / "output" / "export" / f"{name}.png"
assert html.exists(), html
B.export_png(html, png, scale=scale)
from PIL import Image
im = Image.open(png)
print(f"PNG: {png}  size={im.size}")
