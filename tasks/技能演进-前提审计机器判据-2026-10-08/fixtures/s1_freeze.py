# -*- coding: utf-8 -*-
"""s1：冻结 v4.21.0 基线快照（本次将改动的 8 个文件）+ 逐文件 sha256 清单 + 自证。"""
import hashlib, os, shutil

SKILL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # 原为硬编码本机绝对路径（出站清单第 4 项）
TASK = os.path.join(SKILL, "tasks", "技能演进-前提审计机器判据-2026-10-08")
DST = os.path.join(TASK, "tmp", "baseline-frozen")

FILES = [
    "SKILL.md",
    "README.md",
    "assets/plan-template.yaml",
    "references/thinking-panel.md",
    "references/data-model.md",
    "scripts/checks_judges.py",
    "scripts/thinking_model.py",
    "_archive/changelog.md",
]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

os.makedirs(DST, exist_ok=True)
lines, bad = [], []
for rel in FILES:
    src = os.path.join(SKILL, rel.replace("/", os.sep))
    dst = os.path.join(DST, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    s1, s2 = sha(src), sha(dst)
    ok = (s1 == s2)
    if not ok:
        bad.append(rel)
    lines.append("%s  %d  %s  %s" % (s1, os.path.getsize(src), rel, "OK" if ok else "MISMATCH"))
    print("  %-34s %8d B  sha=%s  %s" % (rel, os.path.getsize(src), s1[:16], "OK" if ok else "MISMATCH"))

man = os.path.join(DST, "manifest.sha256")
with open(man, "w", encoding="utf-8") as f:
    f.write("# 冻结时点: 2026-10-08 基线 = ai-workflow v4.21.0\n")
    f.write("# 格式: <sha256>  <字节数>  <相对路径>  <复制自证>\n")
    f.write("\n".join(lines) + "\n")

print("\n清单行数 =", len(lines), "| 期望 =", len(FILES))
print("复制后有哈希不符的文件 =", bad or "无")
print("manifest =", man)
