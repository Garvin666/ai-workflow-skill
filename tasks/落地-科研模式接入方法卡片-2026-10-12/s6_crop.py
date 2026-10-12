# -*- coding: utf-8 -*-
"""s6 细节检查：裁剪 GMM 卡关键区域。"""
import pathlib
from PIL import Image

TASK = pathlib.Path(__file__).resolve().parent
png = TASK / "output" / "export" / "card-gmm.png"
im = Image.open(png)
out = TASK / "output" / "export"

im.crop((0, 1150, 1250, 1950)).save(out / "chk-gmm-steps12.png")     # 步骤1、2
im.crop((1180, 1150, 2400, 1950)).save(out / "chk-gmm-steps34.png")  # 步骤3、4
im.crop((40, 2150, 1250, 2980)).save(out / "chk-gmm-heroL.png")      # hero 左
im.crop((1230, 2150, 2400, 2980)).save(out / "chk-gmm-heroR.png")    # hero 右
print("crops done")
