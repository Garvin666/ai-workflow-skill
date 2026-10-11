"""s2b：用与 external_skill_lint.py 同源的判据，生成 reference_mentions 并写回 lock。

这 49 条「断链」全部指向上游**仓根**的 scripts/verify-*.py 与 commands/ prompts/（其 SKILL.md
自检条写 'From a repository checkout, run ...'）—— 属**正文对上游仓文件的提及**，非技能内引用。
按 external-skills.md §五 第 1 条同法登记为豁免（豁免 ≠ 已验证）。
"""
import importlib.util, json
from pathlib import Path

LINT = Path(__file__).resolve().parents[2] / "scripts" / "external_skill_lint.py"
SK = Path(__file__).resolve().parents[3] / "diagram-design"
LOCK = Path(__file__).resolve().parents[3] / ".vendor" / "diagram-design.lock.json"

spec = importlib.util.spec_from_file_location("esl", LINT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

refs: dict[str, set[str]] = {}
for p in sorted(SK.rglob("*.md")):
    for ref in m.REF_PATTERN.findall(p.read_text(encoding="utf-8", errors="replace")):
        if m.REF_PLACEHOLDER.search(ref):
            continue
        if m.resolve(ref, SK) is not None:
            continue
        if ref in m.REF_WHITELIST or ref.startswith(m.REF_EXTERNAL_PREFIXES):
            continue
        refs.setdefault(ref, set()).add(p.relative_to(SK).as_posix())

mentions = [
    {"skill": "diagram-design", "ref": r, "from": sorted(v)}
    for r, v in sorted(refs.items())
]

lock = json.loads(LOCK.read_text(encoding="utf-8"))
lock["reference_mentions"] = mentions
lock["reference_mention_count"] = len(mentions)
lock["reference_mentions_note"] = (
    "全部为**正文对上游仓根文件的提及**（skills/diagram-design/SKILL.md 自检条与各 references 里的 "
    "'From a repository checkout, run python3 <repo-root>/scripts/verify-*.py' 一类），"
    "以及上游仓根 commands/ prompts/ 的 CLI 入口文档。它们在装态下本就不存在（**不属于交付面**），"
    "按 external-skills.md §五 第 1 条同法登记为豁免。**豁免 ≠ 已验证** —— 这些路径上界为 SKIP 并计数。"
)
LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8", newline="\n")

print(f"reference_mentions 登记 {len(mentions)} 条")
for x in mentions[:8]:
    print("   ", x["ref"])
print("    …" if len(mentions) > 8 else "")
back = json.loads(LOCK.read_text(encoding="utf-8"))
assert back["reference_mention_count"] == len(mentions)
print("回读断言 OK")
