# -*- coding: utf-8 -*-
"""s6d：plan.yaml 的 CRLF 是「既有约定」还是「本轮污染」？

判据（不凭单个文件推广 —— 取计数多数派）：
  1. 同类对照：技能仓内**其他任务**的 plan.yaml 行尾分布（多数派即既有约定）
  2. git 管辖：tasks/*/plan.yaml 是否被 .gitignore 排除（排除 ⇒ 不受 .gitattributes 约束）
  3. 时点：本会话是否编辑过它（mtime 与本会话动作比对）
  4. 内容未受损：YAML 可解析 + 关键字段在位
"""
from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path

# 原为硬编码本机绝对路径（出站清单第 4 项）⇒ 改由 __file__ 推导
SKILL = Path(__file__).resolve().parents[2]
TASKS = SKILL / "tasks"
THIS = "复用-hairline视觉工艺-2026-10-09"


def endings(p: Path) -> str:
    b = p.read_bytes()
    c = b.count(b"\r\n")
    l = b.count(b"\n") - c
    if c == 0:
        return "LF"
    if l == 0:
        return "CRLF"
    return "MIXED"


print("---- 1) 同类对照：技能仓内全部 tasks/*/plan.yaml 行尾分布 ----")
dist: Counter[str] = Counter()
rows = []
for d in sorted(TASKS.iterdir()):
    if not d.is_dir():
        continue
    p = d / "plan.yaml"
    if not p.exists():
        continue
    e = endings(p)
    dist[e] += 1
    rows.append((d.name, e, "  <== 本任务" if d.name == THIS else ""))
for name, e, tag in rows:
    print(f"  {e:6s}  {name}{tag}")
print(f"  ⇒ 分布：{dict(dist)}   （多数派 = {dist.most_common(1)[0][0]}）")

print()
print("---- 2) git 管辖检查 ----")
r = subprocess.run(["git", "check-ignore", "-v", f"tasks/{THIS}/plan.yaml"],
                   cwd=str(SKILL), capture_output=True, text=True, encoding="utf-8",
                   errors="replace")
print(f"  rc={r.returncode}  {r.stdout.strip() or r.stderr.strip()}")
print("  ⇒ rc=0 即被忽略（不受 .gitattributes 约束）；rc=1 即被跟踪")

print()
print("---- 3) 内容完整性（YAML 可解析 + 关键字段） ----")
try:
    import yaml  # type: ignore
    doc = yaml.safe_load((TASKS / THIS / "plan.yaml").read_text(encoding="utf-8"))
    steps = doc.get("steps", [])
    print(f"  [ OK ] YAML 可解析；steps={len(steps)}；"
          f"状态={[s.get('状态') for s in steps]}；"
          f"meta.计划修订={len(doc.get('meta', {}).get('计划修订', []))} 条")
except Exception as exc:  # noqa: BLE001
    print(f"  [FAIL] {exc}")
