#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P7 缓存残留**扫描**（只读，不删任何东西）—— 产出待确认清单。

为什么单独一个脚本：报告 §五 已把 P7 归为「唯一涉及删除用户数据的项」，红线③ + 高风险分级
要求**先列出待删清单、取得用户明确同意**才可动。故本脚本**只扫不删**，且把"哪些能安全删、
哪些不能"分开说清楚 —— 混淆这两类是这类清理最常见的翻车点。

安全边界（区分三类，不是一律都算废数据）：
  · 生产缓存 `http/`：**保留**（删了 = 后续任务全部重新联网，是净损失）
  · 限量状态 `ratelimit.json`：**保留**（含 `_auth_ok` 非机密布尔位，删了只是退化为按匿名桶保守自限）
  · 探针/夹具残留：**候选删除**（`_dq_verify` / `_dq_probe` / `n4test` / `*probe*` / `*test*` 等）
  · `usage_ledger.jsonl`：**保留**（不存在也不该由本脚本创建）

用法：python tasks/技能增强-ai-workflow-v3.4.0-2026-09-16/扫描缓存残留.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

CACHE = Path.home() / ".workbuddy" / "cache" / "ai-workflow"
OUT = Path(__file__).with_name("缓存残留清理-待确认.txt")

# 生产性条目：明确保留（名字即判据，不靠"看起来像缓存"猜）
KEEP = {"http", "ratelimit.json", "usage_ledger.jsonl"}
KEEP_PREFIX = ("_probe",)   # 约定：探针输出应集中放这里，故整体保留（它是"分类好的地方"）


def dir_size(p: Path) -> tuple[int, int]:
    n = size = 0
    for dp, _dn, fn in os.walk(p):
        for f in fn:
            try:
                size += os.path.getsize(os.path.join(dp, f))
                n += 1
            except OSError:
                pass
    return n, size


def main() -> int:
    lines: list[str] = ["=== P7 缓存残留扫描（只读；本脚本不含任何删除调用）===", ""]
    if not CACHE.exists():
        lines.append("缓存根不存在：%s" % CACHE)
        OUT.write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        return 0

    entries = sorted(CACHE.iterdir())
    tot_n = tot_s = 0
    cand: list[tuple[str, int, int]] = []
    keep: list[tuple[str, int, int]] = []
    for e in entries:
        if e.is_dir():
            n, s = dir_size(e)
        else:
            n, s = 1, e.stat().st_size
        tot_n += n
        tot_s += s
        (keep if (e.name in KEEP or e.name.startswith(KEEP_PREFIX)) else cand).append((e.name, n, s))

    lines.append("缓存根：%s" % CACHE)
    lines.append("合计：%d 个文件 / %.2f MB" % (tot_n, tot_s / 1024 / 1024))
    lines.append("")

    lines.append("-- 保留项（生产缓存与状态位，删了是净损失）--")
    for name, n, s in keep:
        lines.append("  [保留] %-24s %6d 文件  %10.2f MB  %s"
                     % (name, n, s / 1024 / 1024,
                        {"http": "真实抓取缓存（命中是 O(1) 寻址）",
                         "ratelimit.json": "限流计数 + _auth_ok 非机密布尔位"}.get(name, "约定集中存放探针输出")))
    ks = sum(s for _, _, s in keep)
    lines.append("  小计：%.2f MB" % (ks / 1024 / 1024))
    lines.append("")

    lines.append("-- 候选删除项（探针/夹具残留）--")
    for name, n, s in sorted(cand, key=lambda x: -x[2]):
        lines.append("  [候选] %-24s %6d 文件  %10.2f MB" % (name, n, s / 1024 / 1024))
    cs = sum(s for _, _, s in cand)
    lines.append("  小计：%d 项 / %.2f MB（占缓存总量 %.1f%%）"
                 % (len(cand), cs / 1024 / 1024, (cs / tot_s * 100) if tot_s else 0))
    lines.append("")

    lines.append("-- 最大的单个文件（Top 5）--")
    big: list[tuple[float, str]] = []
    for dp, _dn, fn in os.walk(CACHE):
        for f in fn:
            fp = os.path.join(dp, f)
            try:
                big.append((os.path.getsize(fp) / 1024 / 1024, os.path.relpath(fp, CACHE)))
            except OSError:
                pass
    for mb, rel in sorted(big, reverse=True)[:5]:
        lines.append("  %10.2f MB  %s" % (mb, rel))
    lines.append("")

    lines += [
        "=== 结论与待确认事项 ===",
        "1. 本脚本**未删除任何文件**（源码中不含 unlink/rmtree/remove 调用，可自查）。",
        "2. 候选项的删除是**不可逆动作**，须用户逐项确认后另行执行；且应优先走回收站而非直接删除。",
        "3. 即使清理，**也不改善运行速度** —— 缓存命中是 sha1 直接寻址（O(1)），本项只改善",
        "   磁盘占用、目录遍历、备份体量与「缓存里到底有什么」的可解释性（与报告 §三 P7 一致）。",
        "4. 约定建议：探针/夹具输出今后一律放 `tasks/<任务>/tmp/` 或 `cache/_probe/`，不混入生产缓存根。",
    ]
    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print("\n[ OK ] 已写入 %s（只读扫描，未删任何文件）" % OUT)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
