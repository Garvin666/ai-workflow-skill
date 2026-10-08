# -*- coding: utf-8 -*-
"""s4：D20–D22 的阴性对照夹具（纯函数级驱动 _check_thinking_verdict）。
   纪律：每条判据必须配「期望 FAIL 且走的正是该分支」的对照；并配反向对照证明判据**不是恒真**。"""
import copy, io, os, sys

SKILL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # 原为硬编码本机绝对路径（出站清单第 4 项）
sys.path.insert(0, os.path.join(SKILL, "scripts"))
sys.stdout.reconfigure(encoding="utf-8")
import checks_core as C            # noqa: E402
import checks_judges as J          # noqa: E402

BASE = {
    "verdict": "接受",
    "distribution": {"接受": 0.9, "修正": 0.05, "澄清": 0.05},
    "confidence": 0.9,
    "dimensions": {"T1": 0.9, "T2": 0.9, "T3": 0.9, "T4": 0.9},
    "veto": {"triggered": False, "suspect": False},
    "amendments": [],
    "ambiguity": False,
    "band": "中",
    "needs_human_confirm": False,
    "main_judge": "A",
    "laya": None,
    "route_hint": "按原样进既有流程（红线①②③照旧）",
}
PA_OK = {"前提": [], "来源核实": {"需要核实": False, "已核实": [], "未核实": []}, "遗漏提醒": []}


def drive(v, label, expect):
    C.results.clear()
    J._check_thinking_verdict({"思考判定": copy.deepcopy(v)})
    fails = [r for r in C.results if r[0] == "FAIL"]
    warns = [r for r in C.results if r[0] == "WARN"]
    got = "FAIL" if fails else ("WARN" if warns else "OK")
    parts = expect.split(":")
    want_mark = parts[0]
    want_code = parts[1] if len(parts) > 1 else ""
    hit = ""
    code_ok = True
    if want_code:
        code_ok = any(want_code in r[2] for r in fails)
        hit = want_code if code_ok else "**未命中" + want_code + "**"
    passed = (got == want_mark) and code_ok
    print("%-8s %-46s 期望=%-10s 实得=%-4s %s" % ("PASS" if passed else "**FAIL**", label,
                                                  expect, got, hit))
    if fails:
        print("         FAIL 文案: " + fails[0][2][:150])
    if warns and got == "WARN":
        print("         WARN 文案: " + warns[0][2][:110])
    return passed


def mk(**over):
    v = copy.deepcopy(BASE)
    v.update(over)
    return v


cases = []
# F0 合法空骨架 → OK（且不产生 WARN）
v = mk(); v["前提审计"] = copy.deepcopy(PA_OK)
cases.append((v, "F0 合法空骨架（无缺陷）", "OK"))
# F1 D20：接受 却登记着未消解前提 → FAIL
v = mk(); v["前提审计"] = copy.deepcopy(PA_OK)
v["前提审计"]["前提"] = [{"项": "x", "判定": "错误前提", "依据": "y"}]
cases.append((v, "F1 注入 D20（接受 + 前提非空）", "FAIL:D20"))
# F1' 反向对照：同一条前提，但 verdict=修正（且 amendments 非空）→ 不报 D20
v = mk(verdict="修正", amendments=[{"项": "x", "原表述": "a", "修正为": "b", "依据": "y", "越线性": "授权内"}])
v["前提审计"] = copy.deepcopy(PA_OK)
v["前提审计"]["前提"] = [{"项": "x", "判定": "错误前提", "依据": "y"}]
cases.append((v, "F1' 反向对照（修正 + 前提非空）→ 不应报 D20", "OK"))
# F2 D21：需要核实=true 但已/未核实均空 → FAIL
v = mk(); v["前提审计"] = copy.deepcopy(PA_OK)
v["前提审计"]["来源核实"] = {"需要核实": True, "已核实": [], "未核实": []}
cases.append((v, "F2 注入 D21（需要核实=true 且两空）", "FAIL:D21"))
# F2' 反向对照：需要核实=true 且 未核实 有内容 → OK
v = mk(); v["前提审计"] = copy.deepcopy(PA_OK)
v["前提审计"]["来源核实"] = {"需要核实": True, "已核实": [], "未核实": [{"项": "p", "原因": "核不到"}]}
cases.append((v, "F2' 反向对照（需要核实=true 且未核实非空）→ 不应报 D21", "OK"))
# F2'' fail-open 兜底：需要核实 缺失（None）→ 结构非法，归 D22（契约 §5.6 明列「需要核实 非布尔」属 D22）
v = mk(); v["前提审计"] = copy.deepcopy(PA_OK)
v["前提审计"]["来源核实"] = {"已核实": [], "未核实": []}
cases.append((v, "F2'' 需要核实 缺失（结构非法=D22，fail-open 兜底）", "FAIL:D22"))
# F3 D22：三键缺一 → FAIL
v = mk(); v["前提审计"] = {"前提": []}
cases.append((v, "F3 注入 D22（缺 来源核实/遗漏提醒）", "FAIL:D22"))
# F3' 类型非法 → FAIL
v = mk(); v["前提审计"] = copy.deepcopy(PA_OK)
v["前提审计"]["遗漏提醒"] = "应为列表却给了字符串"
cases.append((v, "F3' 注入 D22（遗漏提醒 类型非法）", "FAIL:D22"))
# F4 缺省 → WARN（不是 FAIL，也不是 OK）
v = mk()
cases.append((v, "F4 缺省 前提审计（软启动）", "WARN"))

print("=" * 96)
results_all = [drive(v, lb, ex) for v, lb, ex in cases]   # ⚠️ 必须先全跑：all(生成器) 会短路，漏测后续用例
n_pass = sum(1 for x in results_all if x)
print("=" * 96)
print("对照总数 = %d；通过 = %d；全符 = %s" % (len(cases), n_pass, n_pass == len(cases)))
print("注：F0/F1'/F2' 是**反向对照**（证明判据不是恒真），F2'' 是类型/fail-open 兜底对照。")
sys.exit(0 if n_pass == len(cases) else 1)
