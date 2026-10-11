# -*- coding: utf-8 -*-
"""s22 收尾清理：删除本轮（s12–s17 及其 PNG 缺陷追踪期）留下的**探针中间产物**，
任务档案只保留交付物与证据文本。

纪律（本仓既有教训）：
  * 批删一律**显式文件名清单**，禁通配符（共享区曾发生误搬）。
  * 计数算术自证：清单数 == 实删数 + 跳过数，且删后目录**必为空**。
  * 目录用 `rmdir()` 而非 `rmtree()` —— **非空即失败**是最后一道保护：
    若清单漏列了文件，rmdir 会当场报错，而不是静默连坐删除。
  * 幂等：已删则跳过，重跑不报错。

删除对象（20 项）：
  A. tmp_probe/        —— s20/s21 探针产物 11 件
  B. __pycache__/      —— 字节码 8 件
  C. fixtures/png-fixprobe.txt —— **0 字节空证据**（s21 被 kill 时留下）。
     依「沉默必须与通过可区分」纪律：留一个空文件会让后人误以为「跑过且通过」
     ⇒ 删文件，并把探针的真实状态记入 变更说明.md §十一。

保留（可复跑取证工具；两者均自带 mkdir(exist_ok=True)，重跑会自动重建 tmp_probe/）：
  s18_pw_diag.py / s19_png_check.py / s20_png_probe.py / s21_png_fixprobe.py
"""
from __future__ import annotations

import pathlib
import sys

TASK = pathlib.Path(__file__).resolve().parent

TMP_PROBE = TASK / "tmp_probe"
TMP_PROBE_FILES = [
    "chart-01-bar.png",
    "chart-02-line.png",
    "chart-03-heatmap.png",
    "chart-04-scatter.png",
    "chart-05-bar-motion.png",
    "chart-06-bar-reveal.png",
    "clip-element.png",
    "clip-page-floored.png",
    "clip-page.png",
    "nosys.svg",
    "probe.png",
]
PYCACHE = TASK / "__pycache__"
PYCACHE_FILES = [
    "chartlib.cpython-313.pyc",
    "pxcompare.cpython-313.pyc",
    "s11_gen_motion.cpython-313.pyc",
    "s13_gen_reveal.cpython-313.pyc",
    "s16_log.cpython-313.pyc",
    "s17_docref_fix.cpython-313.pyc",
    "s9_gen_charts.cpython-313.pyc",
    "s9b_geom_check.cpython-313.pyc",
]
LOOSE = [TASK / "fixtures" / "png-fixprobe.txt"]

TOTAL = len(TMP_PROBE_FILES) + len(PYCACHE_FILES) + len(LOOSE)


def main() -> int:
    deleted = skipped = 0
    problems: list[str] = []

    for d, names in ((TMP_PROBE, TMP_PROBE_FILES), (PYCACHE, PYCACHE_FILES)):
        print(f"== {d.name}/ （清单 {len(names)} 项）==")
        for n in names:
            f = d / n
            if f.is_file():
                f.unlink()
                deleted += 1
                print(f"  [删] {n}")
            else:
                skipped += 1
                print(f"  [跳] {n}（不存在 ⇒ 幂等）")
        if d.is_dir():
            rest = sorted(p.name for p in d.iterdir())
            if rest:
                problems.append(f"{d.name}/ 仍有未列出的 {len(rest)} 项：{rest}")
                print(f"  [!!] 目录非空（rmdir 拒绝执行）：{rest}")
            else:
                d.rmdir()
                print(f"  [删] {d.name}/（已空 ⇒ rmdir 成功）")

    print("== fixtures/ 空证据 ==")
    for f in LOOSE:
        if f.is_file():
            size = f.stat().st_size
            f.unlink()
            deleted += 1
            tag = "0 字节空证据" if size == 0 else "**非空**"
            print(f"  [删] {f.name}（{size} B —— {tag}）")
            if size != 0:
                problems.append(f"{f.name} 非空（{size} B）却按空证据处置，须复核")
        else:
            skipped += 1
            print(f"  [跳] {f.name}（不存在）")

    print()
    print(f"汇总：清单 {TOTAL} 项 = 实删 {deleted} + 跳过 {skipped}")
    if deleted + skipped != TOTAL:
        problems.append(f"计数不自洽（{deleted}+{skipped} != {TOTAL}）")
    if problems:
        print("[FAIL] 存在问题：")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("[OK] 清理完成：探针产物已清空；任务档案只余交付物（output/）"
          "与证据（fixtures/、s*.py、*.md、plan.yaml、trace.jsonl、确认表.md）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
