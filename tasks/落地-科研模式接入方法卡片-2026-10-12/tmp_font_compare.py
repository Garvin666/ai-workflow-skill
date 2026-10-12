# -*- coding: utf-8 -*-
"""合成字体对比图：Sitka(现卡) / Century / Cambria / Palatino(fallback→times?) / Bodoni(fallback)。"""
import pathlib
from PIL import Image, ImageDraw

TASK = pathlib.Path(__file__).resolve().parent
PROBE = TASK / "tmp" / "font-probe"
card = Image.open(TASK / "output" / "export" / "card-ridge.png")

W = 1400
rows = []

# 现卡标题（Sitka）
sitka = card.crop((420, 40, 1980, 260)).resize((W - 40, int(220 * (W - 40) / 1560)), Image.LANCZOS)
rows.append(("Sitka Banner (current card)", sitka))

for name, label in (("century", "Century Schoolbook"), ("cambria", "Cambria"),
                    ("palatino", "Palatino(stack absent -> fallback)"),
                    ("bodoni_mt", "Bodoni MT(stack absent -> fallback)")):
    p = PROBE / f"p2-{name}.png"
    im = Image.open(p).crop((0, 0, 860, 160))
    im = im.resize((W - 40, int(160 * (W - 40) / 860)), Image.LANCZOS)
    rows.append((label, im))

pad = 12
label_h = 26
total_h = sum(im.height + label_h + pad for _, im in rows) + pad
out = Image.new("RGB", (W, total_h), "#FFFFFF")
d = ImageDraw.Draw(out)
y = pad
for label, im in rows:
    d.text((20, y), label, fill="#000000")
    y += label_h
    out.paste(im, (20, y))
    y += im.height + pad

out.save(TASK / "output" / "export" / "chk-font-compare.png")
print("saved", out.size)
