# -*- coding: utf-8 -*-
"""s9：重建技能库索引（`~/.workbuddy/skills/README.md`）。

为什么必须重建：索引指纹含各技能 `SKILL.md` 的**内容 sha1**，而本任务改了
`ai-workflow/SKILL.md`（入口手册）⇒ 索引按构造即失效（`--check` rc=1 [STALE]）。
本仓规程：**技能新增／改名／改入口 `SKILL.md` 内容后必须重生成**，且**重建须复现上次的根集**。

⚠️ 该文件在**技能根之外**（技能库根目录下），属 `gate.py` 的 `INFRA_EXCEPTIONS`
   基础设施例外；本例的写入由计划已声明验收条件「gen_skill_index.py --check rc=0」授权。
"""
import pathlib
import subprocess
import sys

# ⚠️ 技能库根**不得写成用户名字面量**（出站清单第 4 项：`C:\Users\<用户名>\…` 属 FAIL 级）。
# 本脚本按「技能根反推」取得：脚本在 tasks/<任务>/ ⇒ 技能根 = parents[2]，技能库根 = 技能根的 parent
# （本技能直属技能库根之下）。路径由此**运行期推出**，源码不留任何本机绝对路径。
# 若布局不符，下面的断言会**响亮失败**，不会静默取到错的根。
SKILL = pathlib.Path(__file__).resolve().parents[2]
SKILLS_ROOT = SKILL.parent
assert SKILL.name == "ai-workflow" and SKILLS_ROOT.is_dir(), \
    f"技能库根反推失败：SKILL={SKILL} SKILLS_ROOT={SKILLS_ROOT}"
SKILLS_ROOT = str(SKILLS_ROOT)
IDX = pathlib.Path(SKILLS_ROOT) / "README.md"
PY = sys.executable

before = IDX.read_text(encoding="utf-8")
b_head = before.split("\n")[:5]
print("---- 重建前 ----")
for l in b_head:
    print("  ", l[:150])

r = subprocess.run([PY, "-u", "-X", "utf8", "scripts/gen_skill_index.py", "--roots", SKILLS_ROOT],
                   cwd=SKILL, capture_output=True, text=True, encoding="utf-8")
print("\n---- 生成输出 ----")
print((r.stdout or "").strip()[-1200:])
if r.stderr.strip():
    print("[stderr]", r.stderr.strip()[:600])
assert r.returncode == 0, f"生成失败 rc={r.returncode}"

after = IDX.read_text(encoding="utf-8")
print("\n---- 重建后 ----")
for l in after.split("\n")[:5]:
    print("  ", l[:150])

# 自证：根集与生成前一致（复现上次根集这一步不能靠"看起来对"）
import re  # noqa: E402
ra = re.search(r"<!-- roots: (.+?) -->", before)
rb = re.search(r"<!-- roots: (.+?) -->", after)
assert ra and rb, "索引头部缺 roots 机器标记"
assert ra.group(1) == rb.group(1) == SKILLS_ROOT, f"根集不一致：{ra.group(1)!r} → {rb.group(1)!r}"

# 自证：--check 必须转绿（这才是本次重建的目的，须由脚本自己复核）
c = subprocess.run([PY, "-u", "-X", "utf8", "scripts/gen_skill_index.py", "--check"],
                   cwd=SKILL, capture_output=True, text=True, encoding="utf-8")
print("\n---- 重建后 --check ----")
print((c.stdout or c.stderr).strip()[:600])
print(f"rc={c.returncode}")
assert c.returncode == 0, "重建后 --check 仍非 0"
print("\nOK：索引已重建，根集复现，--check rc=0")
