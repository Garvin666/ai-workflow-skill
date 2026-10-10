"""s3 附：反向断言（实现 → 判据集）+ 影响面语料盘点。

--audit 只做**单向**（判据集 → 实现），故「实现了却未在判据集声明」的孤儿 check 它抓不到。
本脚本补这一半：CHECKS 里每个 check 名必须至少被一条判据声明。
"""
import importlib.util
import pathlib
import sys

# 原为硬编码本机绝对路径（出站清单第 4 项）⇒ 改由 __file__ 推导
SKILL = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ca", SKILL / "scripts" / "check_aesthetics.py")
ca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ca)

rubric = ca.mini_yaml_load((SKILL / "references" / "aesthetic-rubric.yaml").read_text(encoding="utf-8"))
crit = rubric["criteria"]
declared = {c.get("check") for c in crit if c.get("judgeability") not in ("manual", "external")}
impl = set(ca.CHECKS) - {"_selftest_boom"}

print(f"判据条数：{len(crit)}（文件声明 version={rubric.get('version')} / updated={rubric.get('updated')}）")
print(f"实现侧 check 名：{len(impl)} 个")
print(f"判据集声明的 check 名：{len(declared)} 个")
orphan = sorted(impl - declared)
missing = sorted(declared - impl)
print(f"孤儿 check（有实现、判据集未声明）：{orphan or '无'}")
print(f"悬空 check（判据集声明、实现没有）：{missing or '无'}")
newly = sorted(n for n in ("easing_discipline", "no_glow_effects", "infinite_motion_guard") if n in impl and n in declared)
print(f"本轮新增 check 双向可解析：{newly}")
manual_ids = [c.get("id") for c in crit if c.get("judgeability") == "manual"]
print(f"人审点（manual）：{manual_ids}")
h_ids = [c.get("id") for c in crit if str(c.get("id", "")).startswith("H")]
h_judge = {c.get("id"): c.get("judgeability") for c in crit if str(c.get("id", "")).startswith("H")}
print(f"H 层：{h_ids} → {h_judge}")
rc = 1 if (orphan or missing) else 0
print(f"=== 反向断言结论：{'通过' if rc == 0 else '不通过'} ===")

print("\n--- 影响面语料盘点（限定在工作区根与技能库根内，不越界）---")
roots = [SKILL, SKILL.parent]
for r in roots:
    hits = [p for p in r.rglob("*.css") if "ppt-master" not in p.parts and "_archive" not in p.parts]
    print(f"  {r}：{len(hits)} 个 .css" + (f"，例：{[str(h.relative_to(r)) for h in hits[:5]]}" if hits else ""))
sys.exit(rc)
