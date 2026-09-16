#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 v3.4.0 的自检回归证据（`验证输出.txt`）。

内含四段：
  ① `checks.py skill`（技能自身门禁）
  ② `checks.py plan` 对本任务 plan.yaml 的对账
  ③ `checks.py plan` 对 **真实历史 plan.yaml** 的回归（数量与写法多样性远高于任何夹具 ——
     报告 §六 收尾判据第 3 条明确要求"确认没有误伤历史任务"）
  ④ `checks.py status` 工作区总览

为什么③不能省：本版新增了「模型档位合法」门禁，而**真实数据里就有越界值**（v3.2.0 的
`default`）。若把门禁写成"只认 strong/mid/cheap"，历史任务会被判 FAIL —— 那种 FAIL
是**新判据误伤旧数据**，不是旧数据有问题。

⚠️ **本脚本必须跑两次**（自指次序，不是判据放松）：② 段要校验的交付物里包含**本脚本自己的
产物** `验证输出.txt`。首次运行时它还不存在 → 必然出现**且仅出现**一条
「步骤 6 交付物缺失 — 验证输出.txt」；第二次运行时它已落盘 → 该条转 OK。
这与 v3.2.1 推送到「验收报告本身即工作区改动」同型：**自指边界要显式说明，不能假装闭合，
也不能顺手把判据改松**（"交付物存在"这条判据本身是对的，不该为自指让路）。

用法（需连续执行两次）：
    python tasks/技能增强-ai-workflow-v3.4.0-2026-09-16/生成验证输出.py
    python tasks/技能增强-ai-workflow-v3.4.0-2026-09-16/生成验证输出.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("验证输出.txt")
VENV_PY = Path.home() / ".workbuddy" / "binaries" / "python" / "envs" / "ai-workflow" / "Scripts" / "python.exe"
CHECKS = SKILL / "scripts" / "checks.py"
TASK_DIR = Path(__file__).parent

# 挑 4 份真实历史 plan.yaml：越分散越好（不同时期、不同作者轮次、含越界取值的）
HISTORIC = [
    "tasks/技能增强-ai-workflow-v3.2.1-2026-09-16/plan.yaml",
    "tasks/技能增强-ai-workflow-v3.2.0-2026-09-16/plan.yaml",   # 含 default（越界取值）
    "tasks/技能增强-ai-workflow-v2.6.0-2026-09-11/plan.yaml",
    "tasks/对抗互审-ai-workflow-v2.5.1-2026-09-11/plan.yaml",
]


def run(*args: str) -> tuple[int, str]:
    r = subprocess.run([str(VENV_PY), str(CHECKS), *args],
                       capture_output=True, cwd=str(SKILL))
    body = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    return r.returncode, body + (("\n[stderr] " + err) if err.strip() else "")


def main() -> int:
    lines: list[str] = ["=== ai-workflow v3.4.0 自检回归（原始输出，未加工）===", ""]
    bad = 0

    def section(title: str, args: list[str]) -> None:
        nonlocal bad
        lines.append("$ checks.py " + " ".join(args))
        rc, body = run(*args)
        lines.append(body.rstrip())
        lines.append("[退出码 %d]" % rc)
        lines.append("")
        if rc != 0:
            bad += 1

    lines.append("-- ① 技能自身门禁 --")
    section("skill", ["skill"])

    lines.append("-- ② 本任务 plan.yaml 对账 --")
    section("plan（本任务）", ["plan", str(TASK_DIR), "--base", str(SKILL)])

    lines.append("-- ③ 真实历史 plan.yaml 回归（确认新门禁未误伤旧数据）--")
    for rel in HISTORIC:
        p = SKILL / rel
        if not p.exists():
            lines.append("$ （跳过，不存在）%s" % rel)
            lines.append("")
            continue
        section("plan（%s）" % rel, ["plan", rel, "--base", str(SKILL)])

    lines.append("-- ④ 工作区总览 --")
    section("status", ["status", "--workspace", str(SKILL)])

    lines.append("=== 汇总：退出码非 0 的段数 = %d ===" % bad)
    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print("[ OK ] 已写入 %s" % OUT)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
