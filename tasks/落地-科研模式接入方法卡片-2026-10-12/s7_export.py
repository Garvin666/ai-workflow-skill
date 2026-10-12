# -*- coding: utf-8 -*-
"""s7 导出：两张卡片 HTML → PDF（Chrome --print-to-pdf，矢量）。"""
import sys, pathlib

TASK = pathlib.Path(__file__).resolve().parent
SKILL = TASK.parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import methodcard_build as B  # noqa: E402

for name in ("card-ridge", "card-gmm"):
    html = TASK / "output" / f"{name}.html"
    pdf = TASK / "output" / "export" / f"{name}.pdf"
    assert html.exists(), f"缺 HTML：{html}"
    B.export_pdf(html, pdf)
    print(f"PDF: {pdf}  {pdf.stat().st_size} bytes")
