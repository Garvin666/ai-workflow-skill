# -*- coding: utf-8 -*-
"""s9：把 cleanup_task.py 的清理结果回填进 plan.yaml 的 meta.清理（CRLF 保真）。

cleanup_task.py **刻意不自动回填**（checks_core 明写「状态由执行者填写、机器只校验结构」），
故本步由执行者落笔；`清单` 用**裸相对路径**（相对任务目录，模板 §131 的口径），
使其能被 `_check_cleanup` 解析到位（登记了就必须存在）。
"""
import pathlib
import sys

PLAN = pathlib.Path(__file__).resolve().parent / "plan.yaml"

OLD = ('  清理:\n'
       '    状态: "未完成"\n'
       '    回填说明: "收尾由 cleanup_task.py 判定后回填（中间产物预计落 tasks/<任务>/tmp/ 与 __pycache__）"')
NEW = ('  清理:\n'
       '    状态: "已清理"\n'
       '    清单: 清理清单-20261012-122614.txt\n'
       '    文件数: 49\n'
       '    字节数: 921780\n'
       '    回填说明: "cleanup_task.py --apply 执行；删前 sha256 快照、删后双条件复核（PASS，15/15 项）"')

raw = PLAN.read_bytes()
crlf_before = raw.count(b"\r\n")
NL = "\r\n" if crlf_before else "\n"   # ⚠️ 锚点必须按**文件自身行尾**构造：本文件是 CRLF
s = raw.decode("utf-8")

OLD = ('  清理:\n'
       '    状态: "未完成"\n'
       '    回填说明: "收尾由 cleanup_task.py 判定后回填（中间产物预计落 tasks/<任务>/tmp/ 与 __pycache__）"').replace("\n", NL)
NEW = ('  清理:\n'
       '    状态: "已清理"\n'
       '    清单: 清理清单-20261012-122614.txt\n'
       '    文件数: 49\n'
       '    字节数: 921780\n'
       '    回填说明: "cleanup_task.py --apply 执行；删前 sha256 快照、删后双条件复核（PASS，15/15 项）"').replace("\n", NL)

assert s.count(OLD) == 1, f"锚点命中 {s.count(OLD)} 次（期望 1）"
assert NEW.split(NL)[1] not in s, "目标态已在场，疑似重复执行"
out = s.replace(OLD, NEW)
assert out.count(OLD) == 0 and out.count('状态: "已清理"') == 1

PLAN.write_bytes(out.encode("utf-8"))
back = PLAN.read_bytes()
assert back == out.encode("utf-8"), "回读不一致"
assert back.count(b"\r\n") == crlf_before, "CRLF 数变了"

# 自证：清单文件真实存在（登记了就必须解析到位）
man = PLAN.parent / "清理清单-20261012-122614.txt"
assert man.is_file() and man.stat().st_size > 0, f"清单不存在：{man}"
print(f"OK：meta.清理 已回填（已清理 / 49 文件 / 921780 B）；CRLF {crlf_before} 保持")
print(f"    清单实测：{man.name} {man.stat().st_size} B")
sys.exit(0)
