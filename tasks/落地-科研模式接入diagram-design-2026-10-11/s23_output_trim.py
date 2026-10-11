# -*- coding: utf-8 -*-
"""s23：把 `output/` 恢复为「纯交付物」—— 清除 s10 时代的打印中间件 `output/export/pdf-src/`。

**为什么它可以删**（五条，逐条可核）：
  1. **现役路径不用它**：`scripts/diagram_export.py` 的 `pdf` 通道走
     `tempfile.TemporaryDirectory()`（s14 起），不再往 `output/` 写中间件。
  2. **它是被创建的、不是输入**：`s10_export_pdf.py` 第 23 行
     `SRC.mkdir(parents=True, exist_ok=True)` ⇒ 重跑 s10 即重建，**删除可逆**。
  3. **不在任何交付清单**：plan.yaml 全档不提 `pdf-src`（s10 预期产出为
     「output/export/ 下 4 个 .svg ＋ 4 个 .pdf」，即**根下**）。
  4. **已陈旧**：只含 chart-01…04，而图现有 6 张 ⇒ 留着会让
     「为什么只有 4 个」成为新的误导源（**不一致本身即是缺陷**）。
  5. **其验证证据已另存**：`fixtures/export-verify/`（含放大查 Type3 的 `_zoom-*.png`）。

纪律（同 s22）：显式文件名清单 ＋ 计数自证 ＋ `rmdir` 空目录保护
（清单漏列 ⇒ 非空即失败，不静默连坐删除）。
"""
from __future__ import annotations

import pathlib
import sys

TASK = pathlib.Path(__file__).resolve().parent
EXPORT = TASK / "output" / "export"
SRC = EXPORT / "pdf-src"
FILES = [
    "chart-01-bar.print.html",
    "chart-02-line.print.html",
    "chart-03-heatmap.print.html",
    "chart-04-scatter.print.html",
]

# 清理后 output/ 应有的面貌（用于自证「纯交付物」）
KEEP_HTML = [f"chart-0{i}-{n}.html" for i, n in
             ((1, "bar"), (2, "line"), (3, "heatmap"), (4, "scatter"), (5, "bar-motion"), (6, "bar-reveal"))]


def main() -> int:
    deleted = skipped = 0
    problems: list[str] = []

    print(f"== {SRC.relative_to(TASK)}/ （清单 {len(FILES)} 项）==")
    for n in FILES:
        f = SRC / n
        if f.is_file():
            f.unlink()
            deleted += 1
            print(f"  [删] {n}")
        else:
            skipped += 1
            print(f"  [跳] {n}（不存在 ⇒ 幂等）")
    if SRC.is_dir():
        rest = sorted(p.name for p in SRC.iterdir())
        if rest:
            problems.append(f"pdf-src/ 仍有未列出的 {len(rest)} 项：{rest}")
            print(f"  [!!] 目录非空（rmdir 拒绝执行）：{rest}")
        else:
            SRC.rmdir()
            print("  [删] pdf-src/（已空 ⇒ rmdir 成功）")

    print()
    print("== 自证：output/ 与 output/export/ 只余交付物 ==")
    out = TASK / "output"
    got_html = sorted(p.name for p in out.iterdir() if p.is_file())
    if got_html != KEEP_HTML:
        problems.append(f"output/ 文件集合不符：{got_html}")
    else:
        print(f"  [OK] output/ 恰为 6 个 HTML ＋ export/（{len(got_html)}/6）")
    got_exp = sorted(p.name for p in EXPORT.iterdir() if p.is_file())
    want_exp = sorted(f"chart-0{i}-{n}{e}" for i, n in
                      ((1, "bar"), (2, "line"), (3, "heatmap"), (4, "scatter"),
                       (5, "bar-motion"), (6, "bar-reveal"))
                      for e in (".pdf", ".png", ".svg"))
    if got_exp != want_exp:
        problems.append(f"export/ 文件集合不符：多={sorted(set(got_exp)-set(want_exp))} 缺={sorted(set(want_exp)-set(got_exp))}")
    else:
        print(f"  [OK] output/export/ 恰为 {len(got_exp)} 件（6 图 × svg/pdf/png）")
    sub = sorted(p.name for p in EXPORT.iterdir() if p.is_dir())
    if sub:
        problems.append(f"export/ 仍有子目录：{sub}")
    else:
        print("  [OK] export/ 无子目录（中间件已去）")

    print()
    print(f"汇总：清单 {len(FILES)} 项 = 实删 {deleted} + 跳过 {skipped}")
    if deleted + skipped != len(FILES):
        problems.append(f"计数不自洽（{deleted}+{skipped} != {len(FILES)}）")
    if problems:
        print("[FAIL] 存在问题：")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("[OK] output/ 已恢复为纯交付物")
    return 0


if __name__ == "__main__":
    sys.exit(main())
