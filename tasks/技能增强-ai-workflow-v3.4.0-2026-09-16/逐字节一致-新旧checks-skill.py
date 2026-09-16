#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成「新旧 checks.py skill 输出逐字节一致」的证据（ai-workflow v3.4.0 / P1 的硬判据）。

判据来源：`SKILL.md` 阶段 3 第 2 条 —— **性能类改动 = 耗时下降「且」输出与旧版逐字节一致**。
这只是前半句的对偶：只证明"更快"不算通过，还要证明"没改行为"。

为什么拿 `_backup-v3.3.0/scripts/checks.v3.3.0.py` 当对照，而不是拿 before 那次基线的输出：
before/after 两次基线之间**新增了脚本文件**（`gen_skill_index.py`、`perf_baseline.py`），而
`checks.py skill` 的工作量与被测脚本数成正比 → 两次基线的 stdout 本来就**不是同一被测对象**
（行数不同是设计使然，不是缺陷）。本对照固定「**同一棵 scripts/ 树、只换实现**」，才干净。

用法：python tasks/技能增强-ai-workflow-v3.4.0-2026-09-16/逐字节一致-新旧checks-skill.py
"""
from __future__ import annotations

import difflib
import hashlib
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_suffix(".txt")
VENV_PY = Path.home() / ".workbuddy" / "binaries" / "python" / "envs" / "ai-workflow" / "Scripts" / "python.exe"

CASES = [
    ("旧版 v3.3.0（_backup 内）", SKILL / "_backup-v3.3.0" / "scripts" / "checks.v3.3.0.py"),
    ("新版 v3.4.0（scripts 内）", SKILL / "scripts" / "checks.py"),
]


def main() -> int:
    lines: list[str] = []
    results: dict[str, bytes] = {}
    for tag, path in CASES:
        r = subprocess.run([str(VENV_PY), str(path), "skill"], capture_output=True)
        results[tag] = r.stdout
        lines.append("%-26s rc=%d  stdout=%d 字节  sha1=%s"
                     % (tag, r.returncode, len(r.stdout), hashlib.sha1(r.stdout).hexdigest()))
    same = results[CASES[0][0]] == results[CASES[1][0]]
    lines += ["", "逐字节一致：%s" % same]
    if not same:
        a = results[CASES[0][0]].decode("utf-8", "replace").splitlines()
        b = results[CASES[1][0]].decode("utf-8", "replace").splitlines()
        lines += list(difflib.unified_diff(a, b, "old", "new", lineterm="", n=1))
    lines += [
        "",
        "判据来源：SKILL.md 阶段 3 第 2 条「性能类＝耗时下降「且」输出与旧版逐字节一致」。",
        "为何用 v3.3.0 的 checks.py 当对照：before/after 两次基线之间新增了脚本文件，直接比",
        "两次基线的 stdout 不是同一被测对象；本对照固定「同一棵 scripts/ 树、只换实现」。",
        "",
        "⚠️ 这条判据对 P3/P8 没有鉴别力（它们改动前后输出本就相同）—— 那两项另有断言脚本",
        "   `断言-P3-P8.py`（数调用次数 + 阴性对照），二者互补，不可互相替代。",
    ]
    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print("\n[ OK ] 已写入 %s" % OUT)
    return 0 if same else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
