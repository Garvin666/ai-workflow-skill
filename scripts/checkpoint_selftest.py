# -*- coding: utf-8 -*-
"""checkpoint_selftest.py — 「输入指纹 / 检查点」判据的可复跑用例（v4.47.0 / P2 补）

为什么要有它：v4.47.0 首版的六态矩阵是**手跑一次性沙盒**验完即删 —— 那种验证在改判据的
那天一点用都没有（下一个人只能靠重读代码判断"我有没有改坏"）。本脚本把那份矩阵固化下来：
每条用例自带**阴性对照**（BAD 用例必须真的红），并断言 `checks.py checkpoint` 的落盘行为。

设计口径（与 `cleanup_task.py selftest` / `gate.py --selftest` 一致）：
  · **纯标准库**；沙盒建在系统临时目录，跑完删除（不污染技能树、不进 `tasks/`）；
  · 直接调判据函数与命令函数，不起子进程 —— 快，且能看到 `results` 里的原始条目；
  · **PASS / FAIL / SKIP 严格分开**：`SKIP` 不得当成"通过"（本脚本自己也守这条）；
  · 每条用例打印实际拿到的判定，错了能直接看出差在哪一条。

用法：
    python scripts/checkpoint_selftest.py

退出码：0 = 全部符合预期；1 = 有用例不符；2 = 环境不满足（缺 pyyaml）。
"""
from __future__ import annotations

import contextlib
import io
import os as _os
import shutil
import sys
import tempfile
from pathlib import Path

_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from checks_core import results                      # noqa: E402
from checks_judges import _check_checkpoint          # noqa: E402
from checks_cmds import cmd_checkpoint, cmd_trace    # noqa: E402

BASE_PLAN = """meta:
  任务: "检查点自测"
  工作区根: "{root}"
  创建时间: "2026-11-07 21:20"
  任务层级: L1
  验证信号: "本脚本全绿"
steps:
  - id: 1
    做什么: "读输入产出结果"
    输入: "in1.txt"
    预期产出: "out1.md"
    验证方式: "out1.md 存在"
    状态: 完成
    交付物: "out1.md"
    模型档位: cheap
"""


def _plan_yaml(root: Path) -> str:
    return BASE_PLAN.format(root=root.as_posix())


def _load(root: Path) -> dict:
    import yaml
    return yaml.safe_load((root / "plan.yaml").read_text(encoding="utf-8"))


def _judge(root: Path) -> list[tuple[str, str, str]]:
    """跑一次判据，返回当次条目（先清空全局 results）。"""
    results.clear()
    _check_checkpoint(_load(root).get("steps") or [], root)
    return list(results)


def _status(entries: list[tuple[str, str, str]], item_kw: str) -> str:
    for st, item, _ in entries:
        if item_kw in item:
            return st
    return "(缺该项)"


def main() -> int:
    try:
        import yaml  # noqa: F401
    except ImportError:
        print("[ERR] 缺 pyyaml —— 请用 venv 解释器："
              r"%USERPROFILE%\.workbuddy\binaries\python\envs\ai-workflow\Scripts\python.exe", file=sys.stderr)
        return 2

    box = Path(tempfile.mkdtemp(prefix="ckpt-st-"))
    bad = 0
    total = 0

    def case(name: str, got, want) -> None:
        nonlocal bad, total
        total += 1
        okflag = got == want
        if not okflag:
            bad += 1
        print(f"[{'OK ' if okflag else 'BAD'}] {name:<34} got={got!r:<26} want={want!r}")

    try:
        (box / "in1.txt").write_text("src A\n", encoding="utf-8")
        (box / "out1.md").write_text("# out\n\nresult\n", encoding="utf-8")
        plan = box / "plan.yaml"
        plan.write_text(_plan_yaml(box), encoding="utf-8")

        # ---------- 1. 未登记 → SKIP（不是 OK，也不是 FAIL）
        e = _judge(box)
        case("未登记 → SKIP", _status(e, "检查点"), "SKIP")

        # ---------- 2. 落盘 → 结构 OK + 时效 OK
        rc = cmd_checkpoint(plan, "1", "步骤1后可续跑", False, box)
        case("checkpoint 退出码", rc, 0)
        e = _judge(box)
        case("落盘后 → 结构 OK", _status(e, "检查点结构"), "OK")
        case("落盘后 → 时效 OK", _status(e, "检查点时效"), "OK")

        d = _load(box)["steps"][0]
        case("写入 输入指纹（16 hex）", bool(isinstance(d.get("输入指纹"), str) and len(d["输入指纹"]) == 16), True)
        ck = d.get("检查点") or {}
        case("检查点四键齐全", sorted(ck.keys()), ["产物", "可续跑", "时间", "说明"])
        case("可续跑=true", ck.get("可续跑"), True)
        case("产物 1 项且含 sha256", (len(ck.get("产物") or []), bool((ck.get("产物") or [{}])[0].get("sha256"))), (1, True))

        # ---------- 3. 幂等：重复执行只留一份
        cmd_checkpoint(plan, "1", "第二次", False, box)
        raw = plan.read_text(encoding="utf-8")
        case("幂等：检查点块数", raw.count("检查点:"), 1)
        case("幂等：说明被更新", "第二次" in raw, True)

        # ---------- 4. 输入变了 → WARN（事实变化，不是格式错）
        (box / "in1.txt").write_text("src A changed\n", encoding="utf-8")
        e = _judge(box)
        case("改输入 → 时效 WARN", _status(e, "检查点时效"), "WARN")
        case("改输入 → 结构仍 OK", _status(e, "检查点结构"), "OK")

        # ---------- 5. 产物变了 → WARN
        # ⚠️ 必须先**重落检查点**：run 4 已把 in1.txt 改过，输入漂移的 WARN 会把产物那条掩盖掉
        #    —— 首版用例正是栽在这里（变异 M4 关掉 sha256 比对后仍全绿，SURVIVED）。
        cmd_checkpoint(plan, "1", "重落", False, box)
        case("重落后 → 时效回到 OK", _status(_judge(box), "检查点时效"), "OK")
        (box / "out1.md").write_text("# out\n\nresult changed again\n", encoding="utf-8")
        e = _judge(box)
        case("改产物 → 时效 WARN", _status(e, "检查点时效"), "WARN")
        case("该 WARN 明确指向产物", any("产物" in note for st, _, note in e if st == "WARN"), True)

        # ---------- 6. 三种结构非法 → FAIL（阴性对照）
        import copy
        base_steps = copy.deepcopy(_load(box)["steps"])

        s1 = copy.deepcopy(base_steps)
        s1[0]["检查点"].pop("可续跑", None)
        results.clear()
        _check_checkpoint(s1, box)
        case("缺 可续跑 → FAIL", _status(list(results), "检查点结构"), "FAIL")

        s2 = copy.deepcopy(base_steps)
        s2[0]["输入指纹"] = "41AD8920"
        results.clear()
        _check_checkpoint(s2, box)
        case("指纹大写/短 → FAIL", _status(list(results), "检查点结构"), "FAIL")

        s3 = copy.deepcopy(base_steps)
        s3[0].pop("检查点", None)
        results.clear()
        _check_checkpoint(s3, box)
        case("只有指纹没检查点 → FAIL", _status(list(results), "检查点结构"), "FAIL")

        s4 = copy.deepcopy(base_steps)
        s4[0]["检查点"]["产物"][0]["sha256"] = "0" * 64
        results.clear()
        _check_checkpoint(s4, box)
        case("产物 sha256 伪造 → WARN", _status(list(results), "检查点时效"), "WARN")

        s5 = copy.deepcopy(base_steps)
        s5[0]["检查点"]["可续跑"] = "yes"
        results.clear()
        _check_checkpoint(s5, box)
        case("可续跑非 bool → FAIL", _status(list(results), "检查点结构"), "FAIL")

        # ---------- 7. --no-resume
        cmd_checkpoint(plan, "1", "含推送", True, box)
        case("--no-resume → 可续跑 false", _load(box)["steps"][0]["检查点"].get("可续跑"), False)

        # ---------- 8. 输入解析不到 → rc=2 且不落盘（干净夹具，前后都数一遍）
        clean = box / "clean"
        clean.mkdir()
        (clean / "plan.yaml").write_text(_plan_yaml(clean).replace('"in1.txt"', '"不存在.txt"'), encoding="utf-8")
        before = (clean / "plan.yaml").read_text(encoding="utf-8").count("输入指纹")
        rc2 = cmd_checkpoint(clean / "plan.yaml", "1", "", False, clean)
        after = (clean / "plan.yaml").read_text(encoding="utf-8").count("输入指纹")
        case("无输入文件 → 退出码 2", rc2, 2)
        case("无输入文件 → 不落盘", (before, after), (0, 0))

        # ---------- 9. trace 四字段与拒绝面
        results.clear()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc3 = cmd_trace(plan, "1", "读输入", "", "完成", None, False, "", None, 3400, "ok", 1, 1200)
        case("trace 退出码", rc3, 0)
        line = [ln for ln in (box / "trace.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()][-1]
        case("trace 四字段齐全", all(k in line for k in ('"duration_ms": 3400', '"outcome": "ok"',
                                                          '"retries": 1', '"tokens": 1200')), True)
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            bad_enum = cmd_trace(plan, "1", "", "", "", None, False, "", None, None, "done", None, None)
            neg_tok = cmd_trace(plan, "1", "", "", "", None, False, "", None, None, None, None, -1)
            elapsed_ok = cmd_trace(plan, "1", "", "", "", 2.5, False)
        case("trace 非法枚举 → rc=2", bad_enum, 2)
        case("trace 负 tokens → rc=2", neg_tok, 2)
        case("trace --elapsed 折算 ms", elapsed_ok == 0 and
             '"duration_ms": 2500' in (box / "trace.jsonl").read_text(encoding="utf-8"), True)
    finally:
        shutil.rmtree(box, ignore_errors=True)

    print(f"=== {total - bad}/{total} 通过 ===")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
