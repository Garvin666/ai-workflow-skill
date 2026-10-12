# -*- coding: utf-8 -*-
"""探针：确认 `s9_rebuild_index.py` 的「技能根反推」**语义未变**。

不重跑重建（重建会重写技能库索引）；只做三件**独立**的事：
  1) 按同样的反推写法（`parents[2]` / `.parent`）算出技能库根；
  2) 读索引头部的 `<!-- roots: … -->` 机器标记（那是重建时实际写入的根集）；
  3) 断言两者相等 —— 不相等就说明这次「去字面量」改动**改变了语义**，必须回退。

另外 `py_compile` 一遍，确认改写没引入语法错。
"""
import pathlib
import py_compile
import re

HERE = pathlib.Path(__file__).resolve().parent          # tasks/<本任务>/
SKILL = HERE.parents[1]                                  # 技能根
SKILLS_ROOT = SKILL.parent                               # 技能库根
print(f"反推 技能根   = {SKILL}")
print(f"反推 技能库根 = {SKILLS_ROOT}")
print(f"SKILL.name    = {SKILL.name!r}")

idx = SKILLS_ROOT / "README.md"
head = idx.read_text(encoding="utf-8")[:600]
m = re.search(r"<!-- roots: (.+?) -->", head)
print(f"索引 roots 标记 = {m.group(1) if m else 'MISSING'}")
assert m, "索引头部缺 roots 机器标记"
assert m.group(1).strip() == str(SKILLS_ROOT), \
    f"反推值与索引记录不一致：{m.group(1)!r} != {str(SKILLS_ROOT)!r}"
print("OK：反推值 == 索引记录值（语义未变）")

tgt = HERE / "s9_rebuild_index.py"
py_compile.compile(str(tgt), doraise=True)
print("OK：s9_rebuild_index.py py_compile 通过")
print(f"OK：改写后行数 = {len(tgt.read_text(encoding='utf-8').splitlines())}")
