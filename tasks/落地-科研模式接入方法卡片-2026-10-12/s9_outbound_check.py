# -*- coding: utf-8 -*-
"""s9：对本轮「会外发的文件」跑 `outbound_scan.py`（出站清单第 3/4 项的机器化部分）。

扫描面（= 本轮真实改动面）：
  * 任务目录下**未被 git 忽略**的全部文件（`plan.yaml` 由 `.gitignore` 忽略 ⇒ 不入面）；
  * 技能本体本轮改动的 10 个文件。
不扫 `tmp/`（清理容器的内容会被 cleanup_task 删除，届时不在推送面）。
"""
import pathlib
import subprocess
import sys

SKILL = pathlib.Path(__file__).resolve().parents[2]  # 脚本在 tasks/<任务>/ ⇒ 技能根是 parents[2]
TASK = SKILL / "tasks" / "落地-科研模式接入方法卡片-2026-10-12"
PY = sys.executable

BODY = [
    "SKILL.md", "README.md",
    "references/ops.md", "references/method-card-mode.md",
    "references/research-mode.md", "references/diagram-mode.md",
    "scripts/methodcard_lib.py", "scripts/methodcard_build.py", "scripts/methodcard_check.py",
    "_archive/changelog.md",
]

TEXT_EXT = {".py", ".md", ".txt", ".yaml", ".yml", ".json", ".js", ".ps1", ".svg"}
files = []
for p in sorted(TASK.rglob("*")):
    if not p.is_file() or "tmp" in p.parts:
        continue
    if p.suffix.lower() not in TEXT_EXT:
        continue
    r = subprocess.run(["git", "check-ignore", "-q", str(p)], cwd=SKILL)
    if r.returncode == 0:
        print(f"  [跳过·git 忽略] {p.relative_to(SKILL)}")
        continue
    files.append(str(p.relative_to(SKILL)))
for b in BODY:
    if (SKILL / b).is_file():
        files.append(b)

lst = TASK / "fixtures" / "outbound-list.txt"
lst.write_text("\n".join(files) + "\n", encoding="utf-8")
print(f"\n扫描面 {len(files)} 个文件 → {lst.relative_to(SKILL)}")
for f in files:
    print("   ", f)

print("\n" + "=" * 72)
r = subprocess.run([PY, "-u", "-X", "utf8", "scripts/outbound_scan.py", "--list", str(lst)],
                   cwd=SKILL, capture_output=True, text=True, encoding="utf-8")
print(r.stdout.strip())
if r.stderr.strip():
    print("[stderr]", r.stderr.strip()[:800])
print(f"\noutbound_scan rc={r.returncode}")
sys.exit(r.returncode)
