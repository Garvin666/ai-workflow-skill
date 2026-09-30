"""计数断言扫描器 v2 —— 只扫「会长漂移」的两处结构化区块。

v1 全量扫出 162 行，绝大多数是「三条红线」「一步」「一个」这类**叙述**，不是**计数断言**。
⇒ 教训：自动枚举不能替代「哪些句子是可测断言」的判断；必须收窄取值域。

v2 只取两类行：
  (a) README 目录树行（├── / └── / │ 开头）
  (b) SKILL.md 与 references/*.md 的**表格行**（| 开头）中含「数字+量词」
因为描述漂移实际只发生在这两处（目录树的文件份数、索引表的条/张/类数）。
同样：只枚举、不断言。
"""
import os
import re
import sys

# 由脚本位置反推（不写死本机路径 —— 出站扫描会拦，且换机即失效）
from pathlib import Path as _P
SK = str(_P(__file__).resolve().parents[2])

NUM = r"(?:\d+|[一二三四五六七八九十两]+)"
UNIT = r"(?:份|张|条|类|个|节|块|种|项)"
PAT = re.compile(NUM + r"\s*" + UNIT)

TREE = re.compile(r"^\s*(?:[├└│┬─\s])*[├└│]")
TABLE = re.compile(r"^\s*\|")


def scan_tree(path, rel):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out = []
    for i, ln in enumerate(lines, 1):
        if TREE.match(ln) and PAT.search(ln):
            out.append((i, ln.strip()[:140]))
    return out


def scan_tables(path, rel):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out = []
    for i, ln in enumerate(lines, 1):
        if TABLE.match(ln) and PAT.search(ln) and not ln.strip().startswith("| ---"):
            out.append((i, ln.strip()[:140]))
    return out


print("########## (a) README.md 目录树 ##########")
for i, ln in scan_tree(os.path.join(SK, "README.md"), "README.md"):
    print(f"  README.md:{i}  {ln}")

print("\n########## (b) 索引/清单表格行 ##########")
targets = ["SKILL.md"] + ["references/" + f for f in sorted(os.listdir(os.path.join(SK, "references"))) if f.endswith(".md")]
n = 0
for rel in targets:
    p = os.path.join(SK, rel.replace("/", os.sep))
    if not os.path.exists(p):
        continue
    hits = scan_tables(p, rel)
    if hits:
        print(f"\n--- {rel} ---")
        for i, ln in hits:
            print(f"  {rel}:{i}  {ln}")
            n += 1
print(f"\n表格行候选合计：{n}")
print("说明：只枚举不断言。每条都需实测核对，不得直接当缺陷清单。")
sys.exit(0)
