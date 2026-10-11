# -*- coding: utf-8 -*-
"""s9 附加几何自检：把生成图里所有绘图坐标取出，断言不越出 viewBox。

为什么另做：上游 `self_check.py` 判的是**无障碍契约与单文件安全**，
不判「坐标有没有跑到画布外」—— 而越界坐标在任何判据里都静默消失，
只在肉眼看到时才发现。这是我在复核散点图参考线时踩到的形态。

用法：
    s9b_geom_check.py [目录]        # 缺省扫本任务 output/
"""

import re
import sys
from pathlib import Path

VB_FALLBACK = (1000.0, 500.0)          # ⚠️ **只作兜底**，正常一律从文件自己的 viewBox 取
ATTRS = ("x", "y", "x1", "y1", "x2", "y2", "cx", "cy")
DEFAULT_DIR = Path(__file__).resolve().parent / "output"


def viewbox_of(svg_tag: str) -> tuple[float, float] | None:
    """从 `<svg … viewBox="minX minY W H">` 取 (W, H)。

    ⭐ **图幅必须取自被测文件**，不能写死：写死时若画布换成 1200×600，
    横坐标 1000–1200 的越界会**静默漏掉**、而纵坐标 >500 的合法值会**假 FAIL** ——
    两种错误方向同时存在，且都不会报错。这与 `check_vector_export.py` 那次
    「单位在解析处被合并」是同一类病：**判据的输入口径必须与受检对象同源**。
    """
    m = re.search(r'viewBox="\s*([-\d.]+)[\s,]+([-\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)', svg_tag)
    if not m:
        return None
    return float(m.group(3)), float(m.group(4))


def scan(path: Path) -> tuple[list[str], tuple[float, float], bool]:
    html = path.read_text(encoding="utf-8")
    i, j = html.find("<svg"), html.find("</svg>")
    if i < 0 or j < 0:
        return ["未找到 <svg>"], VB_FALLBACK, True
    svg_tag = html[i:html.find(">", i) + 1]
    vb = viewbox_of(svg_tag)
    used_fallback = vb is None
    if vb is None:
        vb = VB_FALLBACK
    body = re.sub(r"<defs>.*?</defs>", "", html[i:j + 6], flags=re.S)
    bad: list[str] = []
    for m in re.finditer(r"<(rect|line|circle|text|polyline|polygon)\b([^>]*)>", body):
        tag, attrs = m.group(1), m.group(2)
        for a in ATTRS:
            mm = re.search(rf'\b{a}="(-?[0-9.]+)"', attrs)
            if not mm:
                continue
            v = float(mm.group(1))
            lim = vb[0] if (a.startswith("x") or a == "cx") else vb[1]
            if v < -0.5 or v > lim + 0.5:
                bad.append(f"<{tag} {a}={v}>")
    for m in re.finditer(r'points="([^"]+)"', body):
        for pair in m.group(1).split():
            try:
                px, py = (float(t) for t in pair.split(","))
            except ValueError:
                continue
            if px < -0.5 or px > vb[0] + 0.5 or py < -0.5 or py > vb[1] + 0.5:
                bad.append(f"points {pair}")
    return bad, vb, used_fallback


def main() -> int:
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR
    total = 0
    fb = 0
    files = sorted(d.glob("*.html"))
    if not files:
        print(f"[ERROR] {d} 下没有 .html")
        return 2
    for f in files:
        bad, vb, used_fallback = scan(f)
        total += len(bad)
        fb += int(used_fallback)
        vbs = f"viewBox={vb[0]:g}×{vb[1]:g}" + ("（**取自文件**）" if not used_fallback else "（**兜底值**，未读到 viewBox）")
        print(("[FAIL] " if bad else "[OK  ] ") + f"{f.name:<26}{vbs}" +
              (f"  越界 {len(bad)}: {bad[:6]}" if bad else "  坐标全部在范围内"))
    print(f"\n越界坐标合计 = {total}   （扫 {len(files)} 个文件；用兜底值的 {fb} 个）")
    return 1 if total or fb else 0


if __name__ == "__main__":
    sys.exit(main())
