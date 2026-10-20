# -*- coding: utf-8 -*-
"""逐条对比改前/改后 checks 输出：原来的 OK 项必须仍是 OK，只允许新增。"""
import re
from pathlib import Path

T = Path(__file__).resolve().parent
pat = re.compile(r"^\[\s*(\w+)\s*\]\s+(.+?)(?:\s+—\s+.*)?$")

def parse(p):
    d = {}
    for ln in p.read_text("utf-8", errors="replace").splitlines():
        m = pat.match(ln)
        if m and not ln.lstrip().startswith("==="):
            d.setdefault(m.group(2).strip(), []).append(m.group(1))
    return d

b = parse(T / "baseline-checks.txt")
v = parse(T / "verify-checks.txt")
# 非空断言：空集比对恒真，必须先断条目数
assert len(b) > 0 and len(v) > 0, f"解析到 {len(b)}/{len(v)} 项 —— 正则失配，结论无效"
print(f"改前项数={len(b)}  改后项数={len(v)}")

regressed = []
for k, sts in b.items():
    now = v.get(k)
    if now is None:
        regressed.append(f"{k}（消失）")
    elif set(sts) != set(now):
        regressed.append(f"{k}：{sts} → {now}")

added = sorted(set(v) - set(b))
print(f"\n原有项状态变化 {len(regressed)}：" + ("无" if not regressed else ""))
for r in regressed:
    print("  ✘", r)
print(f"\n新增项 {len(added)}：")
for a in added:
    print(f"  + [{','.join(v[a])}] {a}")

print("\n" + ("✔ 原 82 项逐条保持，无一项由 OK 转 FAIL/SKIP/WARN" if not regressed
              else "✘ 有回落项，见上"))
