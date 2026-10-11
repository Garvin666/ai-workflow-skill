# -*- coding: utf-8 -*-
"""向 diagram-design 任务 plan.yaml 追加 s8 步骤（修订 ops.md 陈旧 lock 表述）。

幂等：若已存在 `- id: s8` 则跳过，只回读断言。
"""
import io
import pathlib

P = pathlib.Path(__file__).resolve().parent / "plan.yaml"
s = P.read_text(encoding="utf-8")

S8 = (
    "  - id: s8\n"
    "    做什么: 修订 references/ops.md 中 external_skill_lint.py 条目的陈旧表述"
    "（原写默认 lock 为 .vendor/mattpocock.lock.json，而实现自 v4.25.0 起已泛化为遍历 .vendor/*.lock.json）："
    "补版本标注「v4.25.0 起多上游」、默认路径改遍历 .vendor/*.lock.json 并把旧值降为历史、补 --lock 参数、"
    "明确「每个 lock 自成判定域、豁免不跨上游串用」\n"
    "    输入: references/research-mode.md（s1 基线副本）、scripts/external_skill_lint.py（实现即判据源）\n"
    "    预期产出: references/ops.md 该条目两处修订落盘（+580 B，77059 → 77639 B）\n"
    "    验证方式: 旧串「默认 `~/.workbuddy/skills/.vendor/mattpocock.lock.json`」全仓 0 残留；"
    "新串「v4.25.0 起多上游」「每个 lock 自成判定域」各命中 1 次；行尾仍为纯 LF；"
    "复跑 checks.py skill / external_skill_lint.py / gen_skill_index.py --check 三绿\n"
    "    状态: 完成\n"
    "    交付物: references/ops.md\n"
)

if "- id: s8" in s:
    print("[SKIP] s8 已存在，不重复追加")
else:
    if not s.endswith("\n"):
        s += "\n"
    s += S8
    P.write_text(s, encoding="utf-8", newline="")
    print("[OK] 已追加 s8")

# 回读断言
back = P.read_text(encoding="utf-8")
assert "- id: s8" in back, "回读失败：s8 不在盘上"
assert back.count("- id: s8") == 1, "s8 出现次数 != 1"
print("[ASSERT] s8 在盘上，恰 1 次；文件 %d B" % len(back.encode("utf-8")))
