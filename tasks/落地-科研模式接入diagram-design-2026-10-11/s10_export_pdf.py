# -*- coding: utf-8 -*-
"""s10 —— 用上游导出的 SVG 产投稿级 PDF（Chrome 无头打印）。

⚠️ **PDF 不是上游能力**：`references/export.md` 只定义 `svg` 与 `png`（png 需 Playwright）。
本步是**我方扩展**，故：
  · 严格沿用上游的「**导出物 = 纯图示**」口径（丢编辑式外框，与 svg/png 一致）；
  · 页面尺寸 = SVG 的 viewBox 尺寸（1000×500 px），零页边距 ⇒ 图不被缩放或加白边；
  · 矢量输出（PDF 内是矢量路径 + 文本），不是位图。
"""

import pathlib
import re
import subprocess
import sys

PY = sys.executable
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
BASE = pathlib.Path(__file__).resolve().parent / "output" / "export"
SRC = BASE / "pdf-src"
SRC.mkdir(parents=True, exist_ok=True)
UDD = BASE / "pdf-src" / "_chrome-profile"

PRINT_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  @page {{ size: {w}px {h}px; margin: 0; }}
  html, body {{ margin: 0; padding: 0; background: #ffffff; }}
  svg {{ display: block; width: {w}px; height: {h}px; }}
</style>
</head>
<body>
{svg}
</body>
</html>
"""

# ⭐ 字体可嵌入化（**仅对 PDF 派生副本**，不动交付的 .svg）
# 实测：不替换时，数字/拉丁字符会被 Chrome 落成 **Type3** 字体（矢量且已嵌入，但
# 部分期刊明确拒收 Type3）。把缺字的 mono 栈换成 Windows 自带 TrueType（Consolas）
# ⇒ 目标是让印厂/期刊侧拿到 Type0（CID）嵌入字体。
# 交付的 .svg 保持上游原样，本替换只在生成 PDF 时施加，且写进诚实边界。
FONT_SUBST = [
    # mono 栈必须**也**带一个 TrueType 中文字体：本图有用等宽字体渲染的中文
    # （如系列名「策略净值」「沪深300」）。只补 Consolas 时，这些中文无字形可落，
    # 回退后仍被 Chrome 落成 Type3（实测 line 8 个 / scatter 4 个）。
    ("'Geist Mono', ui-monospace, 'Cascadia Mono', monospace",
     "Consolas, 'Microsoft YaHei', monospace"),
    ("'Geist', system-ui, 'Microsoft YaHei', 'PingFang SC', sans-serif",
     "'Microsoft YaHei', Consolas, sans-serif"),
]


def embeddable_fonts(svg_text: str) -> str:
    for a, b in FONT_SUBST:
        svg_text = svg_text.replace(a, b)
    return svg_text


def viewbox(svg_text: str) -> tuple[int, int]:
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg_text)
    if not m:
        raise ValueError("未找到 viewBox")
    return int(float(m.group(1))), int(float(m.group(2)))


def main() -> int:
    svgs = sorted(BASE.glob("*.svg"))
    if not svgs:
        print("[ERROR] 没有 .svg")
        return 2
    made = []
    for svg in svgs:
        text = svg.read_text(encoding="utf-8")
        w, h = viewbox(text)
        # 补上显式尺寸（导出物可能只有 viewBox）
        text = re.sub(r"<svg\b", f'<svg width="{w}" height="{h}"', text, count=1)
        text = embeddable_fonts(text)
        html = PRINT_TPL.format(title=svg.stem, w=w, h=h, svg=text)
        psrc = SRC / f"{svg.stem}.print.html"
        psrc.write_text(html, encoding="utf-8", newline="\n")
        pdf = BASE / f"{svg.stem}.pdf"
        url = "file:///" + str(psrc).replace("\\", "/")
        r = subprocess.run(
            [
                CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
                f"--user-data-dir={UDD}", "--no-pdf-header-footer",
                "--run-all-compositor-stages-before-draw",
                f"--print-to-pdf={pdf}", url,
            ],
            capture_output=True, text=True, timeout=120,
        )
        ok = pdf.exists() and pdf.stat().st_size > 0
        print(f"{'[OK  ]' if ok else '[FAIL]'} {svg.stem}: {w}x{h}px -> "
              f"{pdf.name} ({pdf.stat().st_size if ok else 0} B) rc={r.returncode}")
        if not ok:
            print(r.stdout[-400:], r.stderr[-400:])
        else:
            made.append((svg.stem, pdf, w, h))

    # ── 回读校验（用 PyMuPDF 读页面尺寸与文本，证明不是空页/位图截屏）──
    try:
        import fitz
    except Exception:
        print("[WARN] 无 PyMuPDF，跳回读校验")
        return 0
    print("\n=== 回读校验（PyMuPDF）===")
    bad = 0
    for stem, pdf, w, h in made:
        d = fitz.open(pdf)
        pg = d[0]
        rect = pg.rect
        txt = pg.get_text().strip()
        ntext = len(re.findall(r"[0-9A-Za-z\u4e00-\u9fff]", txt))
        exp_w, exp_h = w * 72 / 96, h * 72 / 96  # px(96dpi) -> pt
        size_ok = abs(rect.width - exp_w) < 1.5 and abs(rect.height - exp_h) < 1.5
        pages_ok = d.page_count == 1
        fonts = pg.get_fonts()
        types = {}
        for f in fonts:
            types[f[2]] = types.get(f[2], 0) + 1
        t3 = types.get("Type3", 0)
        all_emb = all(f[1] != "" for f in fonts)
        # 判据：单页 + 尺寸吻合 + 有可提取文本 + **零 Type3** + 字体全嵌入
        vok = size_ok and pages_ok and ntext >= 20 and t3 == 0 and all_emb
        bad += 0 if vok else 1
        print(f"{'[OK  ]' if vok else '[FAIL]'} {pdf.name}: 页数={d.page_count} "
              f"尺寸={rect.width:.1f}x{rect.height:.1f}pt（期望 {exp_w:.1f}x{exp_h:.1f}）"
              f" 可提取字符={ntext} 字体类型={types} Type3={t3} 全嵌入={all_emb}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
