# -*- coding: utf-8 -*-
"""s9 前置：把诊断用裁剪图从交付目录 output/export/ 移入 tmp/。

纪律（本仓成例）：
  * **不用通配符** —— 只按显式文件名清单操作（避免误伤同目录的交付物）。
  * **计数算术自证** —— 移前/移后分别数一遍，断言「源目录剩 N 个交付物、tmp 收到 M 个」。
  * 只 move 不 delete；任何一项对不上即抛错退出。
"""
import pathlib
import sys

TASK = pathlib.Path(__file__).resolve().parent  # 本脚本位于任务根 ⇒ parent 即任务目录
SRC = TASK / "output" / "export"
DST = TASK / "tmp"

# 显式清单（8 个；来源：s5_crop.py / s6_crop.py 的诊断裁剪）
CHK = [
    "chk-font-compare.png",
    "chk-gmm-heroL.png",
    "chk-gmm-heroR.png",
    "chk-gmm-steps12.png",
    "chk-gmm-steps34.png",
    "chk-heroL.png",
    "chk-heroR.png",
    "chk-steps34.png",
]
# 交付物（移后必须仍在）
KEEP = ["card-ridge.pdf", "card-ridge.png", "card-gmm.pdf", "card-gmm.png"]

before_src = sorted(p.name for p in SRC.iterdir() if p.is_file())
assert set(KEEP) <= set(before_src), f"交付物缺失，中止：{set(KEEP) - set(before_src)}"
assert set(CHK) <= set(before_src), f"清单与现场不符，中止：{set(CHK) - set(before_src)}"
extra = set(before_src) - set(KEEP) - set(CHK)
assert not extra, f"源目录出现清单外的未登记文件（先分类再动手）：{sorted(extra)}"
print(f"[移前] 源目录 {len(before_src)} 个 = 交付 {len(KEEP)} + 诊断 {len(CHK)}")

DST.mkdir(parents=True, exist_ok=True)
moved = 0
for name in CHK:
    s, d = SRC / name, DST / name
    if d.exists():
        raise SystemExit(f"[中止] 目标已存在，不覆盖：{d}")
    s.replace(d)
    moved += 1
    assert not s.exists() and d.exists(), f"移动未生效：{name}"

after_src = sorted(p.name for p in SRC.iterdir() if p.is_file())
assert after_src == sorted(KEEP), f"移后源目录不等于交付物集合：{after_src}"
print(f"[移后] 源目录 {len(after_src)} 个（= 交付物全集）；tmp 收到 {moved} 个")
assert moved == len(CHK) == 8, moved
print("OK：显式清单 8 项全部移动，交付目录只剩 4 件交付物")
sys.exit(0)
