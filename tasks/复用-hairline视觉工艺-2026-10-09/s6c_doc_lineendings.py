# -*- coding: utf-8 -*-
"""s6c：交付文档编辑后的行尾复验 + 门禁复跑。

动机：s6c 之前用编辑工具改了《变更说明.md》三处；本仓 `.gitattributes` 为
`* text=auto eol=lf`，而任务文档此前是 LF。编辑工具若按 os.linesep 写盘会把
全文件变成 CRLF —— 这属「不报错的失效」，故这里**逐文件数行尾**（计数多数派），
不做单文件推广。

判据（三条，每条都可失败 ⇒ 非恒真）：
  A. **交付文档**（3 份 .md，本轮由编辑工具改动）行尾为 LF 且 CRLF 数为 0
  B. `plan.yaml` **不按 LF 期望** —— 它被 `.gitignore` 排除（`tasks/*/plan.yaml`）、
     不受 `.gitattributes` 的 `eol=lf` 约束，且其同类多数派本就是 CRLF（见 s6d.log）。
     ⇒ 本判据**只要求它内容可解析**，行尾按**同类多数派**核对，不硬编 LF。
     ⚠️ 首版判据把 plan.yaml 也期望成 LF ⇒ 报 `CRLF=217` 的**假 FAIL**。
     这正是「全红要先怀疑判据」：先问「这个输入是这条判据该吃的吗」。
  C. 门禁复跑：checks.py skill / checks.py plan / external_skill_lint.py --verify-lock
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# 原为硬编码本机绝对路径（出站清单第 4 项）⇒ 改由 __file__ 推导
SKILL = Path(__file__).resolve().parents[2]
TASK = SKILL / "tasks" / "复用-hairline视觉工艺-2026-10-09"
PY = Path(sys.executable)   # 原为硬编码本机绝对路径 ⇒ 用调用者解释器

DOCS = ["变更说明.md", "影响面实测.md", "确认表.md"]
PLAN = "plan.yaml"          # 单独处置：git-ignored ⇒ 不按 eol=lf 期望
PEER_MAJORITY = "CRLF"      # 同类多数派（s6d.log 实测：CRLF 10 / LF 6）

fails: list[str] = []


def line_ending_report(p: Path) -> tuple[int, int, str]:
    b = p.read_bytes()
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    eol = "LF" if crlf == 0 else ("CRLF" if lf == 0 else "MIXED")
    return crlf, lf, eol


print("---- A：交付文档（本轮被编辑工具改动）行尾须 LF、CRLF=0 ----")
for name in DOCS:
    p = TASK / name
    if not p.exists():
        print(f"  [SKIP] {name} 不存在")
        fails.append(f"{name} 不存在")
        continue
    crlf, lf, eol = line_ending_report(p)
    mark = " OK " if crlf == 0 else "FAIL"
    print(f"  [{mark}] {name:16s} CRLF={crlf:5d}  LF={lf:5d}  ⇒ {eol}")
    if crlf != 0:
        fails.append(f"{name} 含 CRLF {crlf} 处（期望 0）")

print()
print(f"---- B：{PLAN}（git-ignored ⇒ 不按 LF 期望，与同类多数派 {PEER_MAJORITY} 核对）----")
pp = TASK / PLAN
if not pp.exists():
    print(f"  [SKIP] {PLAN} 不存在")
    fails.append(f"{PLAN} 不存在")
else:
    crlf, lf, eol = line_ending_report(pp)
    mark = " OK " if eol == PEER_MAJORITY else "WARN"
    print(f"  [{mark}] {PLAN:16s} CRLF={crlf:5d}  LF={lf:5d}  ⇒ {eol}"
          f"（同类多数派 {PEER_MAJORITY}）")
    if eol != PEER_MAJORITY:
        print(f"     ⚠️ 与同类多数派不一致 —— 需人工判断是「约定变更」还是「污染」")

print()
print("---- B2：行尾探测器的**诱饵对照**（阴性：真 LF／阳性：真 CRLF／混合）----")
_DECOY = [
    ("纯 LF",   b"a\nb\nc\n",           "LF"),
    ("纯 CRLF", b"a\r\nb\r\nc\r\n",     "CRLF"),
    ("混合",    b"a\r\nb\nc\r\n",       "MIXED"),
    ("无换行",  b"abc",                 "LF"),   # crlf=0 ⇒ 归 LF，与实现一致
]
for label, blob, want in _DECOY:
    fp = TASK / f".decoy-{want}-{abs(hash(blob)) % 10000}.tmp"
    fp.write_bytes(blob)
    try:
        crlf, lf, got = line_ending_report(fp)
    finally:
        fp.unlink()
    mark = " OK " if got == want else "FAIL"
    print(f"  [{mark}] {label:6s} 期望 {want:6s} 实得 {got:6s}  (CRLF={crlf} LF={lf})")
    if got != want:
        fails.append(f"诱饵对照失败：{label} 期望 {want} 实得 {got}")

print()
print("---- C：门禁复跑 ----")
cmds = [
    ("checks.py skill", [str(PY), "scripts/checks.py", "skill"]),
    ("checks.py plan", [str(PY), "scripts/checks.py", "plan",
                        str(TASK / "plan.yaml")]),
    ("external_skill_lint --verify-lock", [str(PY), "scripts/external_skill_lint.py", "--verify-lock"]),
]
for label, cmd in cmds:
    r = subprocess.run(cmd, cwd=str(SKILL), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    tail = [ln for ln in r.stdout.splitlines() if ln.startswith("=== 结果") or "结果：" in ln]
    summary = tail[-1] if tail else "(无结果行)"
    mark = " OK " if r.returncode == 0 else "FAIL"
    print(f"  [{mark}] {label:34s} rc={r.returncode}  {summary}")
    if r.returncode != 0:
        fails.append(f"{label} rc={r.returncode}")

print()
if fails:
    print("=== 自检失败 ===")
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("=== 自检通过：行尾零污染 + 三项门禁 rc=0 ===")
