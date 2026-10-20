# -*- coding: utf-8 -*-
"""提取索引章节（751-847）里被点名的文件，用于压缩后集合一致性对账。"""
import re, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
txt = (ROOT / "SKILL.md").read_text("utf-8")
lines = txt.splitlines()
seg = "\n".join(lines[750:847])  # 0-based 750 => 第 751 行

pat = re.compile(r"(?:references|scripts|assets)/[\w.\-/]+\.(?:md|py|yaml|json|js)")
found = sorted(set(pat.findall(seg)))
print(f"索引章节中出现的文件路径（去重）= {len(found)}")
for f in found:
    print(" ", f)

out = Path(r"E:\ChatGPT\工作流\tmp\index-files-before.json")
out.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n已写入 {out}")
print(f"章节字符数 = {len(seg):,}  行数 = {len(lines[750:847])}")
