# -*- coding: utf-8 -*-
"""核验 PNG 通道产物：尺寸恰为 viewBox × scale、确实有内容（非纯色/非全透明）。

⚠️ 口径说明（**不要**把下面两条读成同一件事）：
  · **尺寸**是硬判据 —— 投稿图必须与图幅一致；本轮实测过 2300×1152（被页面 CSS
    放大 1.15×）与 2000×1002（元素截图每侧外扩 1px）两种错法，**都不报错**。
  · **alpha 不是硬判据** —— 上游 `omit_background=True` 只让**页面**背景透明；
    本仓图表自带 paper 底色卡片 ⇒ 产物是有底色的 RGB，这正是期刊要的
    （白/浅底、不透明）。故此处只**如实报出** mode 与 alpha 区间，不据此判合格。
"""
import pathlib
import sys

from PIL import Image

VB = (1000, 500)
SCALE = 2
EXPECT = (VB[0] * SCALE, VB[1] * SCALE)
D = pathlib.Path(__file__).resolve().parent / "output" / "export"

files = sorted(D.glob("*.png"))
if not files:
    print("[ERROR] 没有 PNG")
    sys.exit(2)
bad = 0
for f in files:
    with Image.open(f) as im:
        w, h = im.size
        mode = im.mode
        rgb = im.convert("RGB")
        colors = rgb.getcolors(maxcolors=1_000_000)
        ncolors = len(colors) if colors else 1_000_000
        alpha = im.getchannel("A").getextrema() if mode in ("RGBA", "LA") else None
    size_ok = abs(w - EXPECT[0]) <= 1 and abs(h - EXPECT[1]) <= 1
    content_ok = ncolors > 50           # 纯色/空白图会被这条挡住
    ok = size_ok and content_ok
    bad += 0 if ok else 1
    tag = "[OK  ]" if ok else "[FAIL]"
    a = f"  A∈{alpha}" if alpha else ""
    print(f"{tag} {f.name:<26} {w}x{h}  mode={mode}{a}  颜色数≈{ncolors}")
    if not size_ok:
        print(f"        ▲ 尺寸不符：期望 {EXPECT[0]}x{EXPECT[1]}（= {VB[0]}x{VB[1]} × scale {SCALE}）")
    if not content_ok:
        print("        ▲ 内容可疑：颜色数过少（疑似空白/纯色截图）")

print(f"\n合格 {len(files) - bad}/{len(files)}"
      f"   （硬判据＝尺寸与内容；alpha 只报不判）")
sys.exit(1 if bad else 0)
