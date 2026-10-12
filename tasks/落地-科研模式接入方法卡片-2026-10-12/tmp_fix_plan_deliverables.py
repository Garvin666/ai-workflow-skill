# -*- coding: utf-8 -*-
"""s9 修订：更正 plan.yaml 中 s1 的交付物声明（名称与现场不符 + 补登记基线）。

背景（实测）：
  * 现场有 `fixtures/baseline-checks-skill.txt`（checks.py skill 基线）与
    `fixtures/baseline-lint.txt`（external_skill_lint.py 基线），
    而 plan 声明的是 `fixtures/baseline-checks.txt`（不存在）⇒ checks.py plan 判
    「步骤 s1 交付物缺失」FAIL。
  * 两处基线是 changelog 里「非回归」结论的依据 ⇒ 必须进交付物清单（否则将来被清理器删掉）。

纪律：CRLF 保真（read_bytes → decode → 定点替换 → 断言命中数 → 回读断言）。
"""
import pathlib
import sys

TASK = pathlib.Path(__file__).resolve().parent
PLAN = TASK / "plan.yaml"

OLD = ("    交付物: tasks/落地-科研模式接入方法卡片-2026-10-12/fixtures/baseline-checks.txt、"
       "tasks/落地-科研模式接入方法卡片-2026-10-12/fixtures/baseline-fonts.txt")
NEW = ("    交付物: tasks/落地-科研模式接入方法卡片-2026-10-12/fixtures/baseline-checks-skill.txt、"
       "tasks/落地-科研模式接入方法卡片-2026-10-12/fixtures/baseline-lint.txt、"
       "tasks/落地-科研模式接入方法卡片-2026-10-12/fixtures/baseline-fonts.txt")

raw = PLAN.read_bytes()
crlf_before = raw.count(b"\r\n")
s = raw.decode("utf-8")

n = s.count(OLD)
assert n == 1, f"锚点命中 {n} 次（期望恰 1 次），中止"
assert s.count(NEW) == 0, "目标串已存在，疑似重复执行，中止"

out = s.replace(OLD, NEW)
assert out.count(NEW) == 1, "替换后未命中目标串"
assert out.count(OLD) == 0, "替换后旧串仍在"

PLAN.write_bytes(out.encode("utf-8"))

# ---- 回读断言（同一进程内读回只是自证；真正的对账由 checks.py plan 独立跑）----
back = PLAN.read_bytes()
assert back == out.encode("utf-8"), "回读字节与写入不一致"
crlf_after = back.count(b"\r\n")
assert crlf_after == crlf_before, f"CRLF 数变了：{crlf_before} → {crlf_after}"

# 交付物清单自证：新声明的两个基线文件必须真实存在
for name in ("baseline-checks-skill.txt", "baseline-lint.txt", "baseline-fonts.txt"):
    p = TASK / "fixtures" / name
    assert p.is_file() and p.stat().st_size > 0, f"声明的交付物不存在或为空：{p}"
    print(f"  [OK] {name:28s} {p.stat().st_size} B")

print(f"OK：s1 交付物声明已更正（2 项 → 3 项）；CRLF {crlf_before} 保持")
sys.exit(0)
