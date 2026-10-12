# -*- coding: utf-8 -*-
"""s9 尾段（二）：对**最终**文件面重跑出站扫描，并证明结论是**幂等不动点**。

⭐ 为什么必须重跑：12:23 那次扫描的面（41 文件）**早于**后续的写入 ——
   变更说明、清理清单、索引重建、以及若干个收尾脚本都在它之后落地。
   一致性声明的有效期只到「其后不再有写入」为止 ⇒ 旧结论只作历史留痕，不作最终口径。

⚠️ 面定义的一处**判据缺陷**（本轮发现，两段）：
   ① 若把**扫描器自身的产物**也放进面，判据就**非幂等** —— 输出里的 WARN 行引用被扫文件里的
      盘符路径，二次扫描时再被自己扫到 ⇒ WARN 逐轮自增（发散的假信号）。
   ② 首版排除谓词把相对路径**手拼成正斜杠**，而 `Path` 给出的是反斜杠 ⇒ 集合判定**恒假**、
      排除**静默失效**（表观症状：WARN 由 27 涨到 54，恰是被扫到的自指行）。
      ⇒ 改为**同源 `pathlib` 构造绝对路径比对** ＋ **后置断言**（排除数须等于现场存在的产物数；
      面的文件名集合里不得残留这些名字）—— fail-closed，谓词失配会当场响亮失败。

本脚本：面外排除自身产物 → **同面连跑两遍断言输出逐字节相同**（幂等证明）→
另跑一次**含自身产物**的对照并把数字如实登记（不藏）。
"""

import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parents[1]
FIX = HERE / "fixtures"
PY = sys.executable

TEXT_EXT = {".py", ".md", ".txt", ".yaml", ".yml", ".json", ".js", ".ps1", ".svg"}
SELF_NAMES = (
    "outbound-list.txt", "outbound-scan.txt",
    "after-cleanup-outbound-list.txt", "after-cleanup-outbound-scan.txt",
    "after-cleanup-outbound-list-with-self.txt",
)
SELF_ABS = {str(FIX / n) for n in SELF_NAMES}
BODY = [                                   # 技能本体本轮改动的 10 个文件
    "SKILL.md", "README.md",
    "references/ops.md", "references/method-card-mode.md",
    "references/research-mode.md", "references/diagram-mode.md",
    "scripts/methodcard_lib.py", "scripts/methodcard_build.py", "scripts/methodcard_check.py",
    "_archive/changelog.md",
]


def _rel(p: pathlib.Path) -> str:
    """相对技能根（反斜杠，与既有 `outbound-list.txt` 同形）。"""
    return str(p.relative_to(SKILL))


def build_face(include_self: bool):
    """枚举扫描面 → (面, 被排除的自身产物)。"""
    face, excluded = [], []
    for p in sorted(HERE.rglob("*")):
        if not p.is_file() or "tmp" in p.parts:
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        if str(p) in SELF_ABS:                     # ← 同源绝对路径比对（别再手拼分隔符）
            (face if include_self else excluded).append(_rel(p))
            continue
        if subprocess.run(["git", "check-ignore", "-q", _rel(p)], cwd=SKILL).returncode == 0:
            continue
        face.append(_rel(p))
    for b in BODY:
        face.append(b.replace("/", os.sep))        # 本体文件一律入面（不经 ignore 判定）
    return face, excluded


def scan(listfile: pathlib.Path):
    r = subprocess.run([PY, "-u", "-X", "utf8", "scripts/outbound_scan.py", "--list", str(listfile)],
                       cwd=SKILL, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).rstrip("\n")


def summary(text: str) -> str:
    hit = [l for l in text.splitlines() if l.startswith("=== 出站扫描")]
    return hit[0] if hit else "(无汇总行)"


print("---- 枚举最终面 ----")
face, excluded = build_face(False)
for e in excluded:
    print(f"  [排除·扫描器产物] {e}")
expect = sum(1 for n in SELF_NAMES if (FIX / n).exists())
print(f"  排除 {len(excluded)} 件 / 现场存在 {expect} 件")
assert len(excluded) == expect, \
    f"排除数({len(excluded)}) ≠ 现场产物数({expect}) ⇒ 排除谓词失配，结论不可作证据"
assert not (set(pathlib.Path(x).name for x in face) & set(SELF_NAMES)), \
    f"面里残留扫描器产物：{sorted(set(pathlib.Path(x).name for x in face) & set(SELF_NAMES))}"

lst = FIX / "after-cleanup-outbound-list.txt"
lst.write_text("\n".join(face) + "\n", encoding="utf-8")
print(f"\n扫描面 {len(face)} 个文件 → {lst.name}")

print("\n---- 第一遍 ----")
rc1, out1 = scan(lst)
print(out1)

print("\n---- 第二遍（同面；用于断言幂等） ----")
rc2, out2 = scan(lst)
print(summary(out2))

assert rc1 == rc2 == 0, f"出站扫描非零：rc1={rc1} rc2={rc2} ⇒ 有 FAIL 级命中，必须处理"
assert out1 == out2, "两次同面扫描输出不一致 ⇒ 判据非幂等，结论不可作证据"
print("\nOK：同面两次扫描**输出逐字节相同**、rc 均 0 ⇒ 结论是幂等不动点")

# ---- 对照：把扫描器自身产物也纳入面（如实登记，不藏） ----
print("\n---- 对照：含扫描器自身产物 ----")
face2, _ = build_face(True)
lst2 = FIX / "after-cleanup-outbound-list-with-self.txt"
lst2.write_text("\n".join(face2) + "\n", encoding="utf-8")
rc3, out3 = scan(lst2)
print(f"rc={rc3}；{summary(out3)}")

# ---- 落留痕（含面定义 / 幂等性 / 对照结论） ----
note = [
    "",
    "=" * 72,
    "【面定义】扫描面 = 本任务目录下未被 git 忽略的文本文件 ∪ 技能本体本轮改动的 10 个文件；",
    "         排除 tmp/；排除**扫描器自身的产物**（入面会使判据非幂等 + 输出自指，见 s9_final_scan.py）。",
    f"【幂等性】同面连跑两遍，输出**逐字节相同**、rc 均 0 ⇒ 结论为幂等不动点（非时序快照）。",
    f"【对照】把扫描器自身产物也纳入面（共 {len(face2)} 文件）时：rc={rc3}，本次 {summary(out3)}",
    "        ⇒ 自指只推高 WARN（引用被扫文件里的盘符路径），FAIL 仍为 0。",
    "        ⚠️ 该对照数字**不具可复现性**：它引用的正是本次自己的输出，重跑即变（同一脚本两次",
    "           运行实测 WARN=81 与 108）⇒ 只作「自指会推高 WARN」的**定性**证据，不作判据。",
    "【为何本留痕不含掩码】FAIL=0 蕴含「被扫的每一行都不含『含用户名的主目录路径』」；",
    "        而本留痕每行都是那些行的前缀或截取窗口 ⇒ 同样不含。此为由 FAIL=0 直接推出的结论。",
    "【WARN 口径】WARN 全为既有盘符路径（本版只提示不阻断，出站清单第 3 项），本轮未升级、未豁免。",
]
(FIX / "after-cleanup-outbound-scan.txt").write_text(out1 + "\n" + "\n".join(note) + "\n", encoding="utf-8")
print(f"\n留痕 after-cleanup-outbound-scan.txt = {(FIX / 'after-cleanup-outbound-scan.txt').stat().st_size} B")
print(f"留痕 after-cleanup-outbound-list.txt = {lst.stat().st_size} B")
