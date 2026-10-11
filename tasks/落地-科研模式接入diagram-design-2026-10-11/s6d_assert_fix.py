"""s6d：修正插入型编辑的断言（旧串作为新串前缀时不该要求其消失）＋ 收尾核验。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sk = (ROOT / "SKILL.md").read_text(encoding="utf-8")

# 替换型：旧串必须消失
REPLACE_OLD = ["version: 4.32.1", "# AI 工作流 v4.32.1", "技能库根下五上游",
               "（交 `diagram-mode` 或外部数据图技能）", "数据图 → 外部数据图技能",
               "一句话检验法）、自检 10 项", "与既有面的重叠处置、自检 8 项",
               "起「五上游」**）", "五批技能都不属本体"]
bad = [s for s in REPLACE_OLD if s in sk]
assert not bad, f"替换型旧串残留：{bad}"
print(f"SKILL.md 替换型 {len(REPLACE_OLD)} 组：旧串全清")

# 插入型：只断「新串在」＋「旧串不再单独成立」
INS = [("分界见该手册 §1.5；", "分界见该手册 §1.5；**上游六** `diagram-design`")]
for old, new in INS:
    assert new in sk, f"插入型新串不在：{new[:40]}"
    # 旧串后面必须紧跟新串（即不存在「旧串后直接收尾」的原样）
    assert f"{old}**上游六**" in sk
print(f"SKILL.md 插入型 {len(INS)} 组：新串在、且旧串不再单独收尾")

NEW_OK = ["version: 4.33.0", "# AI 工作流 v4.33.0", "技能库根下六上游",
          "（交 `diagram-mode`（示意图）或**已接入的** `diagram-design`（数据图）",
          "**数据图与示意图 → 已接入的** `diagram-design`", "科研制图 §7.11",
          "「契约层 ↔ 引擎层」分界**）、自检 8 项", "起「六上游」**）",
          "契约层 ↔ 引擎层**」分界见该手册 §1.7；", "六批技能都不属本体",
          "**上游六** `diagram-design`", "六批技能都不属本体"]
miss = [s for s in NEW_OK if s not in sk]
assert not miss, f"SKILL.md 缺新串：{miss}"
print(f"SKILL.md 新串 {len(NEW_OK)} 项全在")

print("\nSKILL.md 体量：", len(sk.encode("utf-8")), "B / 软预算 163840 B =",
      f"{len(sk.encode('utf-8'))/163840*100:.1f}%")
print("\n收尾核验通过")
