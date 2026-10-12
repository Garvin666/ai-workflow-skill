# -*- coding: utf-8 -*-
"""s2 设计令牌采样：从参考图提取精确色值（分类采样法）+ 字体候选渲染对比。

采样法（不靠目测）：
  - 纸底类：全卡区域亮度 V>=205 的像素 → 量化高频色
  - 墨色类：V<=70 → 中位
  - 主蓝类：B-R>=28 且 B>=110 → 中位
  - 灰类：低饱和（max-min<=12）且 90<V<190 → 中位
  - 暖强调（橙/红）：R-B>=40 → 中位
"""
import os, pathlib, collections
from PIL import Image

CI = (pathlib.Path(os.environ.get("USERPROFILE") or pathlib.Path.home())
      / ".workbuddy" / "clipboard-images")  # 输入源；不写死用户名路径
OUT = pathlib.Path(__file__).parent / "fixtures"
OUT.mkdir(exist_ok=True)

# Ridge（630Z）、GMM（670Z）、HMM（609Z）、Kalman（632Z）
picks = {
    "ridge": "clipboard-2026-10-12T02-57-47-630Z-9aef0659.jpg",
    "gmm": "clipboard-2026-10-12T02-57-47-670Z-2f71a339.jpg",
    "hmm": "clipboard-2026-10-12T02-57-47-609Z-a309b328.jpg",
    "kalman": "clipboard-2026-10-12T02-57-47-632Z-a6239365.jpg",
}

lines = []
for tag, fn in picks.items():
    im = Image.open(CI / fn).convert("RGB")
    w, h = im.size
    # 卡片区域（去掉手机 UI 与黑边）：沿 y 中带取
    card = im.crop((int(w*0.02), int(h*0.20), int(w*0.98), int(h*0.76)))
    px = list(card.getdata())
    n = len(px)

    def med(sel):
        s = [p for p in px if sel(p)]
        if not s:
            return None, 0
        s.sort(key=lambda c: c[0]*65536 + c[1]*256 + c[2])
        return s[len(s)//2], len(s)

    def V(c): return max(c)
    def sat(c): return max(c) - min(c)

    light = collections.Counter((r//4*4, g//4*4, b//4*4) for r, g, b in px if V((r, g, b)) >= 205)
    dark, dn = med(lambda c: V(c) <= 70)
    blue, bn = med(lambda c: c[2] - c[0] >= 28 and c[2] >= 110)
    gray, gn = med(lambda c: sat(c) <= 12 and 90 < V(c) < 190)
    warm, wn = med(lambda c: c[0] - c[2] >= 40 and c[0] >= 120)

    lines.append(f"== {tag} ({fn[:48]}…) ==")
    lines.append(f"  纸底 top5: " + ", ".join(f"#{r:02x}{g:02x}{b:02x}({cnt})" for (r, g, b), cnt in light.most_common(5)))
    lines.append(f"  墨色: {('#%02x%02x%02x' % dark + f' n={dn}') if dark else 'n/a'}")
    lines.append(f"  主蓝: {('#%02x%02x%02x' % blue + f' n={bn}') if blue else 'n/a'}")
    lines.append(f"  灰类: {('#%02x%02x%02x' % gray + f' n={gn}') if gray else 'n/a'}")
    lines.append(f"  暖强调: {('#%02x%02x%02x' % warm + f' n={wn}') if warm else 'n/a'}")
    lines.append("")

out = "\n".join(lines)
(OUT / "token-samples.txt").write_text(out, encoding="utf-8")
print(out)
