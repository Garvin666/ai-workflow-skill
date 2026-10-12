# -*- coding: utf-8 -*-
"""s5 细节检查：裁剪关键区域供目检。用法：s5_crop.py"""
import pathlib
from PIL import Image

TASK = pathlib.Path(__file__).resolve().parent
png = TASK / "output" / "export" / "card-ridge.png"
im = Image.open(png)
W, H = im.size  # 2400x3200
out = TASK / "output" / "export"

# 步骤区右两列（步骤3 等高线 / 步骤4 系数柱）
im.crop((1180, 1150, 2400, 1950)).save(out / "chk-steps34.png")
# 示意区左右（散点拟合对比 / 系数柱 + 徽章）
im.crop((40, 2150, 1250, 2980)).save(out / "chk-heroL.png")
im.crop((1230, 2150, 2400, 2980)).save(out / "chk-heroR.png")
print("crops:", [p.name for p in sorted(out.glob("chk-*.png"))])
