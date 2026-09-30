#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阴性对照：注入计数漂移 → 复核器必须 FAIL 且**只红对应那一条**（证明判据非恒真）。

⚠️ 全程**字节级**读写（`read_bytes` / `write_bytes`）—— 用 `write_text` 会在 Windows 文本模式下
   把 LF 转成 CRLF，**改坏文件**（本工作区已登记的坑）。

每组四步：读原文（内存备份）→ 注入 → 跑复核器解析红名单 → 还原 → sha256 判等（证明还原干净）。
"""
import hashlib
import subprocess
import sys
from pathlib import Path

SK = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PY = sys.executable
VERIFY = HERE / "verify_counts.py"

CASES = [
    ("改 README references 份数 33→26", "README.md", "33 份下沉手册", "26 份下沉手册",
     ["README 目录树 references 份数"]),
    ("改 SKILL skill-hygiene 五条→四条", "SKILL.md", "技能库卫生五条硬约定", "技能库卫生四条硬约定",
     ["SKILL.md 手册索引 skill-hygiene 条数"]),
    ("改 SKILL decision-tables 十张→九张", "SKILL.md", "十张决策表集中映射", "九张决策表集中映射",
     ["SKILL.md 手册索引 decision-tables 张数"]),
    ("改手册 §9 十类→九类", "references/literature-reading-mode.md", "的十类决策表**未收录本模式**",
     "的九类决策表**未收录本模式**", ["手册 §9 第 6 条 决策表类数"]),
]


def run_verify():
    p = subprocess.run([PY, str(VERIFY)], capture_output=True, text=True, encoding="utf-8")
    red = [ln for ln in p.stdout.splitlines() if ln.startswith("[FAIL]")]
    names = [ln.split(":")[0].replace("[FAIL] ", "").strip() for ln in red]
    return p.returncode, names


def main():
    allok = True
    for title, rel, old, new, expect_red in CASES:
        f = SK / rel
        orig = f.read_bytes()
        sha_before = hashlib.sha256(orig).hexdigest()

        n = orig.count(old.encode("utf-8"))
        if n != 1:
            print(f"[FAIL] {title}: 注入串出现 {n} 次（应恰 1 次），跳过")
            allok = False
            continue

        f.write_bytes(orig.replace(old.encode("utf-8"), new.encode("utf-8")))
        rc, red = run_verify()
        f.write_bytes(orig)  # 还原
        sha_after = hashlib.sha256(f.read_bytes()).hexdigest()

        ok_rc = rc != 0
        ok_red = set(red) == set(expect_red)
        ok_restore = sha_before == sha_after
        ok = ok_rc and ok_red and ok_restore
        allok &= ok
        print(f"[{'OK' if ok else 'FAIL'}] {title}")
        print(f"        退出码={rc}（应非 0）{'✓' if ok_rc else '✗'}；"
              f"红名单={red}（应={expect_red}）{'✓' if ok_red else '✗'}；"
              f"还原 sha 一致={ok_restore}")

    print(f"\n=== 阴性对照：{'全部成立' if allok else '有不成立项'} ===")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
