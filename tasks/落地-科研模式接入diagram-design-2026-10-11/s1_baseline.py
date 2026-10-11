import hashlib, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "落地-科研模式接入diagram-design-2026-10-11"
BASE = TASK / "fixtures" / "baseline"
BASE.mkdir(parents=True, exist_ok=True)

FILES = [
    "SKILL.md",
    "README.md",
    "references/research-mode.md",
    "references/diagram-mode.md",
    "references/external-skills.md",
    "references/ops.md",
]

rows = []
for rel in FILES:
    src = ROOT / rel
    dst = BASE / rel.replace("/", "__")
    shutil.copy2(src, dst)
    data = src.read_bytes()
    h = hashlib.sha256(data).hexdigest()
    rows.append((rel, h, len(data)))
    print(f"{h}  {len(data):>8}  {rel}")

manifest = TASK / "fixtures" / "baseline-manifest.sha256"
manifest.write_text(
    "\n".join(f"{h}  {rel}" for rel, h, _ in rows) + "\n",
    encoding="utf-8", newline="\n",
)
print("MANIFEST ->", manifest)
# 回读断言
back = manifest.read_text(encoding="utf-8").splitlines()
assert len(back) == len(rows), f"manifest 行数不符 {len(back)} != {len(rows)}"
print("回读断言 OK，共", len(back), "行")
