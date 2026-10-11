# -*- coding: utf-8 -*-
"""摘掉**外部技能（diagram-design）文件名**周围的 Markdown 反引号。

为什么要做这件事（不是「把措辞改歪去绕过检查」）：
  `checks.py` 的「文档引用完整性」是**扁平检查** —— 反引号里的 `xxx.py` / `xxx.md`
  一律被当作**本技能目录内**的引用去四个位置解析；解析不到就是断链。
  而 diagram-design 的文件在**另一个根**（`~/.workbuddy/skills/diagram-design/`），
  用同一种记号去引用它们 ⇒ **假阳性**（本轮实测 12 条）。

  两种去歧义方式：(a) 写成安装后的完整路径；(b) 不用「文件引用」记号（即去掉反引号）。
  本处取 (b)：这些名字大多是**成串列举**（如「scripts/ 下只有 a.py / b.py / …」），
  逐个写 45 字符的完整路径会把句子压垮；而上游的**安装位置与形态**已在
  `references/external-skills.md` §一 的六张表里逐上游登记过，不靠这里重复。

⚠️ 只替换**精确串**（含两端反引号），不做正则/模糊匹配；替换后逐串回读断言。
"""
import pathlib

SKILL = pathlib.Path(__file__).resolve().parents[2]
FILES = [
    SKILL / "SKILL.md",
    SKILL / "references" / "external-skills.md",
    SKILL / "references" / "ops.md",
    SKILL / "references" / "research-mode.md",
    SKILL / "references" / "diagram-mode.md",
]

# 只摘这些**外部技能文件名**的反引号（本仓同名文件不存在，故不会误伤真引用）
NAMES = [
    "export.md",
    "references/export.md",
    "self_check.py",
    "animation.md",
    "verify-motion.py",
    "lint-skin.py",
    "drawio_extract.py",
    "excalidraw_extract.py",
    "mermaid_extract.py",
    "export_svg.py",
    "scripts/export_svg.py",
    "diagram-design/scripts/export_svg.py",
]

total = 0
for f in FILES:
    if not f.exists():
        print(f"[SKIP] 不在场：{f}")
        continue
    s = f.read_text(encoding="utf-8")
    before = s
    hits = []
    for nm in NAMES:
        old, new = f"`{nm}`", nm
        c = s.count(old)
        if c:
            s = s.replace(old, new)
            hits.append(f"{nm}×{c}")
            total += c
    if s != before:
        f.write_text(s, encoding="utf-8", newline="")
        # 回读断言：替换后这些精确串必须为 0
        back = f.read_text(encoding="utf-8")
        for nm in NAMES:
            assert f"`{nm}`" not in back, f"{f.name}: 仍有 `{nm}`"
        print(f"[OK  ] {f.name}: {len(hits)} 类 / 共 {sum(int(h.split('×')[1]) for h in hits)} 处 —— {'；'.join(hits)}")
    else:
        print(f"[----] {f.name}: 无需改动")

print(f"\n合计摘除反引号 {total} 处")
