# -*- coding: utf-8 -*-
"""模式契约判据的阴性对照（四项）。

做法：在临时目录构造最小技能（SKILL.md + 7 份 mode 手册），逐个注入缺陷，
断言对应判据由 OK 转 FAIL。**没有对照的判据不许上线。**
"""
import shutil, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NC = ROOT / "tasks/重构-主干瘦身与模式接口卡-2026-10-20/fixtures/nc"
sys.path.insert(0, str(ROOT / "scripts"))
import checks_core as core
import checks

DOCS = ["homework-mode.md", "research-mode.md", "teardown-mode.md", "diagram-mode.md",
        "ppt-mode.md", "method-card-mode.md", "literature-reading-mode.md"]

def build(dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "references").mkdir(parents=True)
    shutil.copy2(ROOT / "SKILL.md", dst / "SKILL.md")
    for d in DOCS:
        shutil.copy2(ROOT / "references" / d, dst / "references" / d)

def run(dst: Path):
    core.results.clear()
    checks._check_mode_contracts(dst)
    return list(core.results)

def verdicts(res):
    return {name: st for st, name, _ in res}

def show(tag, res):
    print(f"\n--- {tag} ---")
    for st, name, note in res:
        print(f"  [{st}] {name} — {note[:90]}")

base = NC / "base"
build(base)
res0 = run(base)
show("对照0 基线（应全 OK）", res0)
ok_all = all(st == "OK" for st, _, _ in res0)
print(f"基线全 OK = {ok_all}")

cases = []

# 缺陷1：删掉作业模式整张卡 → 清单双向一致应 FAIL
d = NC / "c1"; build(d)
t = (d / "SKILL.md").read_text("utf-8")
t2 = re.sub(r"^### 作业模式（.*?(?=^### 科研模式)", "", t, flags=re.S | re.M)
(d / "SKILL.md").write_text(t2, encoding="utf-8")
cases.append(("缺陷1 删一张卡", d, "模式契约：清单双向一致"))

# 缺陷2：删掉科研卡的「前置路由」行 → 字段完整应 FAIL
d = NC / "c2"; build(d)
t = (d / "SKILL.md").read_text("utf-8")
t2 = t.replace("- **前置路由**：**无 judge**（理由见共性①）。\n- **结构 R0–R6**",
               "- **结构 R0–R6**", 1)
assert t2 != t, "注入点1 未命中"
(d / "SKILL.md").write_text(t2, encoding="utf-8")
cases.append(("缺陷2 删前置路由", d, "模式契约：卡片字段完整"))

# 缺陷3：科研卡指针改成别人的手册 → 细则指针可达应 FAIL
d = NC / "c3"; build(d)
t = (d / "SKILL.md").read_text("utf-8")
t2 = t.replace("> 细则 `references/research-mode.md`", "> 细则 `references/teardown-mode.md`", 1)
assert t2 != t, "注入点2 未命中"
(d / "SKILL.md").write_text(t2, encoding="utf-8")
cases.append(("缺陷3 指针错挂", d, "模式契约：细则指针可达"))

# 缺陷4：手册里删掉 S2 → 编号可追溯应 FAIL
d = NC / "c4"; build(d)
p = d / "references/homework-mode.md"
t = p.read_text("utf-8")
t2 = t.replace("S2", "SX")
assert t2 != t, "注入点3 未命中"
p.write_text(t2, encoding="utf-8")
cases.append(("缺陷4 编号缺失", d, "模式契约：编号可追溯"))

print("\n" + "=" * 70)
all_pass = ok_all
for tag, dst, expect in cases:
    r = run(dst)
    v = verdicts(r)
    got = v.get(expect, "MISSING")
    good = got == "FAIL"
    all_pass &= good
    print(f"{tag:18} 目标项『{expect}』 → {got}  {'✔ 正确转红' if good else '✘ 未转红（判据空转）'}")

print("=" * 70)
print(f"\n总体：{'全部通过（4 个缺陷均被抓到，基线全绿）' if all_pass else '有未通过项，见上'}")
sys.exit(0 if all_pass else 1)
