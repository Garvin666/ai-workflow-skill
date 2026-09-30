#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计数一致性复核器（本任务自写，与 checks.py **零代码共享**）。

为什么需要它：
    `checks.py skill` 只查「引用**存在性**」，**不查**「文档里的计数句与仓库实测是否相等」。
    本轮实测 8 处计数漂移**全部逃过**该门禁（当时 72/72 FAIL=0）。
    故本类一致性必须由本复核器兜底 —— 且**不得**声称「已由门禁保证」。

设计口径（照 Ledger 记录的上一轮 README 对齐任务）：
    从**文档正则抠出数字**，再与**仓库实测**对撞 —— 把期望值写死在脚本里等于自证。

用法：
    python verify_counts.py                # 全部检查，FAIL=0 时退出码 0
"""
import json
import os
import re
import sys
from pathlib import Path

# <技能根>/tasks/<任务>/verify_counts.py → tasks/<任务> → tasks → 技能根
SK = Path(__file__).resolve().parents[2]

CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def cn2int(s):
    return CN.get(s)


def read(rel):
    return (SK / rel).read_text(encoding="utf-8")


# ---------------- 实测（来自文件系统与文档结构） ----------------
def real_counts():
    refs = list((SK / "references").iterdir())
    dt = read("references/decision-tables.md")
    hyg = read("references/skill-hygiene.md")
    pb = read("references/playbook.md")
    return {
        "ref_total": len(refs),
        "ref_md": len([f for f in refs if f.suffix == ".md"]),
        "ref_yaml": len([f for f in refs if f.suffix == ".yaml"]),
        "tpl_yaml": len(list((SK / "assets/templates").glob("*.yaml"))),
        # 「X、……决策表」标题数 —— ⚠️ 不能写成 `决策表（`：第五张「五、终止策略决策表」标题
        #   后面没有括号，会被漏掉（本复核器首版即踩此坑，实测 10 被判成 9）。
        #   改为：数全部 `## X、` 编号节，排除「决策表索引」「诚实边界」两节。
        "dt_tables": len(
            [
                h
                for h in re.findall(r"^## [一二三四五六七八九十]+、(.+)$", dt, re.M)
                if "索引" not in h and "诚实边界" not in h
            ]
        ),
        "hygiene_items": len(re.findall(r"^\| [0-9] \|", hyg, re.M)),
        "playbook_sections": len(re.findall(r"^## [一二三四五六七八九十]+、", pb, re.M)),
        # —— v2 新增（由 scan_numeric_claims.py 扫出 3 候选 + scripts 4 计数 = 7 条，原 9 条未覆盖）——
        "scripts_exec": len(
            [f for f in (SK / "scripts").iterdir()
             if f.is_file() and f.suffix in {".py", ".js", ".ps1"}]
        ),
        "scripts_py": len(list((SK / "scripts").glob("*.py"))),
        "scripts_js": len(list((SK / "scripts").glob("*.js"))),
        "scripts_ps1": len(list((SK / "scripts").glob("*.ps1"))),
        "judges_blocks": _judge_blocks(),
        "ext_skills": _ext_skill_count(),
        "kb_gates": _kb_gate_count(),
    }


def _judge_blocks():
    """judges.json 的 judge 块数（排除 `_` 开头的元信息键）。"""
    d = json.loads((SK / "scripts/judges.json").read_text(encoding="utf-8"))
    return len([k for k in d if not k.startswith("_")])


def _ext_skill_count():
    """外部技能安装数 —— 权威源是技能库根的 vendor lock，不是目录数（目录里混有自研技能）。"""
    p = Path(os.path.expanduser("~/.workbuddy/skills/.vendor/mattpocock.lock.json"))
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    n, lst = d.get("skill_count"), len(d.get("skills", []))
    return n if n == lst else None  # 两处不一致 ⇒ 报 None 触发 FAIL，不静默取一个


def _kb_gate_count():
    """K4 门槛条数 —— 权威源是 kb_learn.py 的 docstring 枚举，不是手册概览表的简写。"""
    src = (SK / "scripts/kb_learn.py").read_text(encoding="utf-8")
    m = re.search(r"门槛判定（([^）]+)）", src)
    return len([x for x in m.group(1).split("/") if x.strip()]) if m else None


# ---------------- 文档侧抠数（正则，不写死期望值） ----------------
def doc_claims():
    readme = read("README.md")
    skill = read("SKILL.md")
    lit = read("references/literature-reading-mode.md")
    c = {}

    m = re.search(r"# (\d+) 份下沉手册（= (\d+) \.md \+ (\d+) \.yaml", readme)
    c["README 目录树 references 份数"] = int(m.group(1)) if m else None
    c["README 目录树 references .md 数"] = int(m.group(2)) if m else None
    c["README 目录树 references .yaml 数"] = int(m.group(3)) if m else None

    m = re.search(r"templates/ 项目模板库（(\d+) 份 \.yaml）", readme)
    c["README 目录树 templates .yaml 数"] = int(m.group(1)) if m else None

    m = re.search(r"；([一二三四五六七八九十]+)类决策（能力 /", skill)
    c["SKILL.md §自主决策层 决策类数"] = cn2int(m.group(1)) if m else None

    m = re.search(r"：([一二三四五六七八九十]+)张决策表集中映射", skill)
    c["SKILL.md 手册索引 decision-tables 张数"] = cn2int(m.group(1)) if m else None

    m = re.search(r"技能库卫生([一二三四五六七八九十]+)条硬约定", skill)
    c["SKILL.md 手册索引 skill-hygiene 条数"] = cn2int(m.group(1)) if m else None

    m = re.search(r"\| `references/playbook\.md` \| ([一二三四五六七八九十]+)类任务差异化流程", skill)
    c["SKILL.md 手册索引 playbook 类数"] = cn2int(m.group(1)) if m else None

    m = re.search(r"的([一二三四五六七八九十]+)类决策表\*\*未收录本模式\*\*", lit)
    c["手册 §9 第 6 条 决策表类数"] = cn2int(m.group(1)) if m else None

    # —— v2 新增 7 条 ——
    m = re.search(r"# (\d+) 个可执行脚本（(\d+) \.py \+ (\d+) \.js \+ (\d+) \.ps1）", readme)
    c["README 目录树 scripts 可执行数"] = int(m.group(1)) if m else None
    c["README 目录树 scripts .py 数"] = int(m.group(2)) if m else None
    c["README 目录树 scripts .js 数"] = int(m.group(3)) if m else None
    c["README 目录树 scripts .ps1 数"] = int(m.group(4)) if m else None

    m = re.search(r"judges\.json\s*# ([一二三四五六七八九十]+)块快判", readme)
    c["README 目录树 judges.json 块数"] = cn2int(m.group(1)) if m else None

    m = re.search(r"\*\*(\d+) 个第三方 MIT 技能\*\*", skill)
    c["SKILL.md 手册索引 外部技能数"] = int(m.group(1)) if m else None

    m = re.search(r"六条门槛（", skill)
    c["SKILL.md 学习模型 K4 门槛条数"] = cn2int("六") if m else None

    return c


def main():
    r = real_counts()
    c = doc_claims()

    pairs = [
        ("README 目录树 references 份数", c["README 目录树 references 份数"], r["ref_total"]),
        ("README 目录树 references .md 数", c["README 目录树 references .md 数"], r["ref_md"]),
        ("README 目录树 references .yaml 数", c["README 目录树 references .yaml 数"], r["ref_yaml"]),
        ("README 目录树 templates .yaml 数", c["README 目录树 templates .yaml 数"], r["tpl_yaml"]),
        ("SKILL.md §自主决策层 决策类数", c["SKILL.md §自主决策层 决策类数"], r["dt_tables"]),
        ("SKILL.md 手册索引 decision-tables 张数", c["SKILL.md 手册索引 decision-tables 张数"], r["dt_tables"]),
        ("SKILL.md 手册索引 skill-hygiene 条数", c["SKILL.md 手册索引 skill-hygiene 条数"], r["hygiene_items"]),
        ("SKILL.md 手册索引 playbook 类数", c["SKILL.md 手册索引 playbook 类数"], r["playbook_sections"]),
        ("手册 §9 第 6 条 决策表类数", c["手册 §9 第 6 条 决策表类数"], r["dt_tables"]),
        # —— v2 新增 4 组 ——
        ("README 目录树 scripts 可执行数", c["README 目录树 scripts 可执行数"], r["scripts_exec"]),
        ("README 目录树 scripts .py 数", c["README 目录树 scripts .py 数"], r["scripts_py"]),
        ("README 目录树 scripts .js 数", c["README 目录树 scripts .js 数"], r["scripts_js"]),
        ("README 目录树 scripts .ps1 数", c["README 目录树 scripts .ps1 数"], r["scripts_ps1"]),
        ("README 目录树 judges.json 块数", c["README 目录树 judges.json 块数"], r["judges_blocks"]),
        ("SKILL.md 手册索引 外部技能数", c["SKILL.md 手册索引 外部技能数"], r["ext_skills"]),
        ("SKILL.md 学习模型 K4 门槛条数", c["SKILL.md 学习模型 K4 门槛条数"], r["kb_gates"]),
    ]

    ok = fail = 0
    for name, doc_v, real_v in pairs:
        if doc_v is None:
            print(f"[FAIL] {name}: 文档正则**未抠到**该计数句（可能已被改写，复核器需同步）")
            fail += 1
        elif doc_v == real_v:
            print(f"[ OK ] {name}: 文档={doc_v} 实测={real_v}")
            ok += 1
        else:
            print(f"[FAIL] {name}: 文档={doc_v} ≠ 实测={real_v}")
            fail += 1

    print(f"\n=== 结果：OK {ok} / FAIL {fail} ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
