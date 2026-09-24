# -*- coding: utf-8 -*-
"""ai-workflow 校验器（CLI 入口）。

v4.4.2：本体按职责层拆分为 `checks_core`（常量/通用工具）、`checks_parity`（口径守卫）、
`checks_judges`（判据）、`checks_cmds`（子命令）；**本文件保留为入口并 re-export 全部常量**，
以保证既有调用面不变 —— 尤其是 `gate.py` 按路径加载本文件取 `INFRA_EXCEPTIONS`、
`guard_constants.py` 取 `SELFTOOL_KEYS` / `CODE_EXT` 这两条既有依赖。

**CLI 用法与输出与拆分前完全一致**（已由 baseline 逐命令 diff 验证）。
"""
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)

from checks_core import *          # noqa: F401,F403 —— 常量与通用工具（含 INFRA_EXCEPTIONS / CODE_EXT / SELFTOOL_KEYS）
from checks_core import (          # noqa: F401 —— 下划线开头的模块级变量，`import *` 不导出，显式补齐

    _BARE_CELL,
    _DECL_BEGIN,
    _DECL_END,
    _SELFTOOL_LEDGER_CACHE,
    _SEP_CELL,
    _TRACE_HINT,
)
from checks_parity import (  # noqa: F401
    _check_parity,
)
from checks_judges import (  # noqa: F401
    _check_autonomy,
    _check_category_decl,
    _check_closure,
    _check_entry_verdict,
    _check_fuse,
    _check_gate,
    _check_homework_sample,
    _check_homework_verdict,
    _check_irreversible,
    _check_method_select,
    _check_method_select_sample,
    _check_model_tiers,
    _check_platform,
    _check_reflection_retry,
    _check_retrieval_sample,
    _check_retrieval_verdict,
    _check_scope,
    _check_selftools,
    _check_stage_gates,
    _check_user_release,
)
from checks_cmds import (  # noqa: F401
    cmd_decide,
    cmd_mark,
    cmd_metrics,
    cmd_revise,
    cmd_selftool,
    cmd_status,
    cmd_trace,
)
from checks_core import (  # noqa: F401
    DEFAULT_SKILL_DIR,
    MARKS,
    PLAN_META_REQUIRED,
    PLAN_STEP_REQUIRED,
    REF_EXTERNAL_PREFIXES,
    REF_PATTERN,
    REF_PLACEHOLDER,
    REF_WHITELIST,
    TEMPLATE_FIELDS,
    VALID_FUSE,
    VALID_STATUS,
    VALID_TRIGGER,
    _frontmatter,
    _require_yaml,
    _resolve,
    audit_step,
    fail,
    ok,
    result_line,
    results,
    skip,
)

def check_skill(skill_dir: Path) -> int:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        fail("SKILL.md 存在", str(skill_md))
        return 1
    ok("SKILL.md 存在")

    fm = _frontmatter(skill_md.read_text(encoding="utf-8"))
    if not fm:
        fail("frontmatter 可解析",
             "未找到以 `---` 包裹的 frontmatter 块（首行须为 `---`，末行须为 `---`）")
    else:
        ok("frontmatter 可解析",
           f"{len(fm)} 字符 / {fm.count(chr(10)) + 1} 行（结构化取块，非字符窗口）")
        for key in ("name:", "description:", "agent_created:"):
            (ok if key in fm else fail)(f"frontmatter 含 {key.rstrip(':')}")

    docs = [p for p in [skill_md, *sorted((skill_dir / "references").glob("*.md"))] if p.exists()]
    missing = []
    seen = set()
    for doc in docs:
        for ref in REF_PATTERN.findall(doc.read_text(encoding="utf-8")):
            if ref in seen or REF_PLACEHOLDER.search(ref):
                continue
            seen.add(ref)
            if _resolve(ref, skill_dir) is not None:
                continue  # 技能内文件，已确认存在
            # 走到这里说明按技能内四个位置都找不到。若不是已知的跨根引用，就是真断链。
            # ⚠️ 顺序要紧：**先解析、后判前缀/白名单** —— 反过来会让技能内同名路径被前缀规则误放行。
            if ref in REF_WHITELIST or ref.startswith(REF_EXTERNAL_PREFIXES):
                continue
            missing.append(f"{ref}（来自 {doc.name}）")
    if missing:
        fail("文档引用完整性", "缺失：" + "；".join(missing))
    else:
        ok("文档引用完整性", f"检查 {len(seen)} 条引用")

    tmpl_dir = skill_dir / "assets" / "templates"
    tmpls = [p for p in sorted(tmpl_dir.glob("*.yaml"))]
    if not tmpls:
        fail("模板 schema", "未找到 assets/templates/*.yaml")
    for t in tmpls:
        text = t.read_text(encoding="utf-8")
        miss = [f for f in TEMPLATE_FIELDS if not re.search(rf"^{f}:", text, re.M)]
        (ok if not miss else fail)(f"模板 schema：{t.name}", ("缺 " + ",".join(miss)) if miss else f"{len(TEMPLATE_FIELDS) - len(miss)}/{len(TEMPLATE_FIELDS)}")

    pt = skill_dir / "assets" / "plan-template.yaml"
    if pt.exists():
        text = pt.read_text(encoding="utf-8")
        miss = [k for k in ("任务", "验证信号", "步骤", "交付物") if k not in text]
        (ok if not miss else fail)("plan-template 必填键", ("缺 " + ",".join(miss)) if miss else "齐全")
    else:
        fail("plan-template.yaml 存在")

    pyfiles = sorted((skill_dir / "scripts").glob("*.py"))
    if not pyfiles:
        fail("脚本存在", "scripts/*.py 为空")
    # ⭐ v3.4.0 / P1：**不要"为了清理而先产生"** —— 把 .pyc 写到**系统临时目录**，
    # 从根上不产生 `scripts/__pycache__`，原先的清理逻辑随之取消。
    #   为什么必须改：`py_compile.compile(str(py))` 默认把 .pyc 写进脚本同目录的
    #   `__pycache__`，于是自检每轮都"先造 10 个文件、再 rmtree 删掉它们"。而本机
    #   `PYTHONPATH` 注入的 shim（`…\cli\vendor\shim`）会把**非临时目录**的 rmtree
    #   改走回收站（spawn 子进程）—— 受控实验：同一个 rmtree 删 8 个 4KB 文件，按父目录
    #   分别为 19.5 / 564.2 / 855.8 ms（43.9×）。实测本机 legacy 路径 = 产生 121 ms +
    #   清理 708 ms = 829 ms；改 `cfile` 后 87 ms 且零残留（原始数据见
    #   `.workbuddy/tmp/perf_baseline_*.json` 与 `rm.txt`）。
    #   诚实标注：该收益**依环境而变**（裸终端里同一个 rmtree 只要 ≈19 ms），
    #   但"不产生"在任何环境下都只有好处、没有坏处。
    with tempfile.TemporaryDirectory(prefix="aiwf_pyc_") as pyc_dir:
        for py in pyfiles:
            try:
                py_compile.compile(str(py), cfile=str(Path(pyc_dir) / (py.stem + ".pyc")), doraise=True)
                ok(f"py_compile：{py.name}")
            except py_compile.PyCompileError as e:
                fail(f"py_compile：{py.name}", str(e).splitlines()[0][:120])
    # 兜底：清掉**历史遗留**的 `__pycache__`（本版不主动造，但旧版本可能已经留下）。
    # 用逐文件 unlink 而非递归 rmtree —— ① shim 只劫持 `shutil.rmtree`，unlink 不受影响；
    # ② 目标只是"别留下垃圾"，**扩大删除面与优化目标相反**。
    cache = skill_dir / "scripts" / "__pycache__"
    if cache.exists():
        for f in sorted(cache.iterdir(), reverse=True):
            try:
                f.rmdir() if f.is_dir() else f.unlink()
            except OSError:
                pass
        try:
            cache.rmdir()
        except OSError:
            pass

    # v3.5.0 / P0-3：口径守卫 —— 手册/模板里写的取值必须与代码常量同源。放在最后，
    # 因为前面几项都是"代码自身"的完整性判据，这一项是"文档 ↔ 代码"的一致性判据。
    _check_parity(skill_dir)
    # v4.2.0 第五轮：主类枚举单独判（声明块 FAIL + 启发式 WARN）—— 它的模型是「跨文件唯一性（源规格面内）」，塞不进 PARITY_ITEMS 的并集模型
    _check_category_decl(skill_dir)
    # v4.3.0 / 批次 B：平台门控 vs 真实 import（AST 口径，不认注释与字符串里的同名字面量）
    _check_platform(skill_dir)
    # v4.3.0 / 批次 C：运行时闸门可用性与同源（gate.py 缺失、或口径另存一份副本，均 FAIL）
    _check_gate(skill_dir)
    return 0

def check_plan(plan_path: Path, base: Path) -> int:
    yaml = _require_yaml()

    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1
    ok("plan.yaml 存在", str(plan_path))

    try:
        data = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        fail("plan.yaml 可解析", str(e).splitlines()[0][:120])
        return 1
    ok("plan.yaml 可解析")

    meta = data.get("meta") or {}
    for k in PLAN_META_REQUIRED:
        value = str(meta.get(k, "") or "").strip()
        (ok if value else fail)(f"meta.{k}", "" if value else "为空")

    steps = data.get("steps") or []
    if not steps:
        fail("steps 非空")
        return 1
    ok("steps 非空", f"{len(steps)} 步")

    done_total = deliverable_ok = 0
    for s in steps:
        sid = s.get("id", "?")
        miss = [k for k in PLAN_STEP_REQUIRED if not str(s.get(k, "") or "").strip()]
        if miss:
            fail(f"步骤 {sid} 必填字段", "缺 " + ",".join(miss))
        st = str(s.get("状态", "")).strip()
        if st not in VALID_STATUS:
            fail(f"步骤 {sid} 状态合法", f"实际『{st}』")
        if st != "完成":
            continue
        done_total += 1
        a = audit_step(s, base)
        for token in a["缺失"]:
            hint = "（未在 --base=<工作区根> 下找到；相对路径以 --base 为基准，工作区根之外的文件须写绝对路径）"
            fail(f"步骤 {sid} 交付物缺失", token[:80] + hint)
        for token in a["非文件型"]:
            skip(f"步骤 {sid} 交付物", f"『{token[:40]}』非文件型，需人工确认")
        if not a["缺失"] and a["交付物总数"] > 0:
            deliverable_ok += 1

    ok("Anti-drop 对账", f"已完成步骤 {done_total} 个，交付物确认 {deliverable_ok} 个")

    _check_scope(meta, steps, base)
    _check_irreversible(meta, steps)
    _check_user_release(meta)
    _check_entry_verdict(meta)
    _check_method_select(meta)
    _check_method_select_sample(meta)
    _check_retrieval_verdict(meta)
    _check_retrieval_sample(meta)
    # v4.7.0：检查项 18 = 作业判定结构合法（+ 派生字段自洽）；19 = 抽样人审指路（只 WARN）
    _check_homework_verdict(meta)
    _check_homework_sample(meta)
    _check_autonomy(meta)
    _check_selftools(meta, steps, base)
    _check_stage_gates(steps)
    _check_model_tiers(steps)
    _check_reflection_retry(meta, steps)
    _check_fuse(meta, steps, plan_path)
    # v4.3.0 / 批次 B：E′ 步骤闭环不变量（trace 自证 + 零沉淀须显式登记）。放最后，
    # 因为它依赖前面各项的判定结果（plan 可解析、meta 完整），且它的输出会引用 step id。
    _check_closure(steps, plan_path, meta)
    return 0

def main() -> None:
    ap = argparse.ArgumentParser(description="ai-workflow 自检工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("skill", help="技能自身完整性自检")
    p.add_argument("--skill-dir", default=str(DEFAULT_SKILL_DIR))

    p = sub.add_parser("plan", help="计划校验 + Anti-drop 对账")
    p.add_argument("target", help="plan.yaml 路径或任务目录")
    p.add_argument("--base", default=str(Path.cwd()), help="相对路径解析基准（默认当前目录）")

    p = sub.add_parser("status", help="工作区任务总览（含交付物完成度与归档建议）")
    p.add_argument("--workspace", default=str(Path.cwd()), help="工作区根目录（含 tasks/）")
    p.add_argument("--archive-days", type=int, default=30, help="超过该天数未改动则建议归档（默认 30）")
    p.add_argument("--max-tasks", type=int, default=10, help="任务目录数超过该值则提示归档（默认 10）")
    p.add_argument("--light", action="store_true", help="轻量模式：仅统计 meta/步数/状态，跳过逐交付物 exists 检查（N6）")

    p = sub.add_parser("mark", help="更新 plan.yaml 的步骤状态与/或 meta 熔断状态（替代手工编辑）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("step_id", nargs="?", help="步骤 id（只改熔断状态时可省略）")
    p.add_argument("status", nargs="?", choices=VALID_STATUS, help="该步骤的新状态")
    p.add_argument("--fuse", choices=VALID_FUSE,
                   help="设置 meta.熔断状态；复位填『正常』（须与步骤状态一并复位，见 _check_fuse）")
    p.add_argument("--batch", help="批量文件：每行 `<step_id> <status>`（空行/# 忽略）；一次性落盘，避免 N 步 N 次重写（N7）")

    p = sub.add_parser("decide", help="追加一条能力决策记录到 meta.决策记录（自主决策层留痕，v3.0.0）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("--point", required=True, help="决策点：这一步缺什么/要决定什么（方法选用不记录步骤名，故必填）")
    p.add_argument("--basis", help="依据：一句话判据（说不出可验证收益就别引入）；--from-method-select 时可省略")
    p.add_argument("--capability", help="能力类：知识/算力/事实/手脚（支持「+」组合）；--from-method-select 时可省略（校验走 _capability_ok，故不设 argparse choices）")
    p.add_argument("--choice", help="选择：实际引入的具体手段；--from-method-select 时可省略")
    p.add_argument("--from-method-select", nargs="?", const=-1, type=int, default=None,
                   help="v4.4.0：从 meta.方法选用 列表推导 能力类/选择/依据；缺省取最新一条，传正整数为 1-based 序号")

    p = sub.add_parser("revise", help="追加一条计划修订到 meta.计划修订（重规划留痕）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("--trigger", required=True, choices=VALID_TRIGGER, help="触发编号：R1–R6")
    p.add_argument("--change", required=True, help="变化摘要（改了什么）")
    p.add_argument("--unchanged", help="未变部分（已完成步骤是否受影响）")

    p = sub.add_parser("selftool", help="追加一条自研工具/技能登记到 meta.自研工具（公开留痕，v3.1.0）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("--name", required=True, help="名称：工具/技能叫什么")
    p.add_argument("--purpose", required=True, help="用途：一句话，它做什么")
    p.add_argument("--scenario", required=True, help="适用场景：什么情况该用；什么情况不该用")
    p.add_argument("--repo", required=True, help="仓库链接：http(s) 真实地址；尚未推送时填『待推送』（交付前须回填）")

    p = sub.add_parser("trace", help="追加一条执行 trace（v4.0.0 / U3：补 plan.yaml 缺失的时序）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("--step", help="步骤 id（--replay 时不需要）")
    p.add_argument("--action", default="", help="本步动作摘要")
    p.add_argument("--command", default="", help="实际执行的命令（避免与子命令名 cmd 冲突，故拼全）")
    p.add_argument("--result", default="", help="结果摘要")
    p.add_argument("--elapsed", type=float, help="耗时（秒）")
    p.add_argument("--note", default="", help="执行备注（v4.1.0：反思重试时填根因·调整摘要）")
    p.add_argument("--attempt", type=int, help="重试轮次（v4.1.0：action=retry 时填第几轮）")
    p.add_argument("--replay", action="store_true", help="回放该任务的完整时序")

    p = sub.add_parser("metrics", help="任务级指标沉淀（v4.0.0 / U8：写入 tasks/_metrics.jsonl）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("--finalize", action="store_true", help="收尾时汇总写入一次")

    args = ap.parse_args()
    if args.cmd == "skill":
        code = check_skill(Path(args.skill_dir))
        name = "技能自检"
    elif args.cmd == "plan":
        code = check_plan(Path(args.target), Path(args.base))
        name = "计划对账"
    elif args.cmd == "status":
        code = cmd_status(Path(args.workspace), args.archive_days, args.max_tasks, args.light)
        name = "任务总览"
    elif args.cmd == "mark":
        code = cmd_mark(Path(args.plan), args.step_id, args.status, args.fuse, args.batch)
        name = "状态更新"
    elif args.cmd == "decide":
        code = cmd_decide(Path(args.plan), args.point, args.basis, args.capability, args.choice, args.from_method_select)
        name = "决策留痕"
    elif args.cmd == "revise":
        code = cmd_revise(Path(args.plan), args.trigger, args.change, args.unchanged)
        name = "计划修订"
    elif args.cmd == "selftool":
        code = cmd_selftool(Path(args.plan), args.name, args.purpose, args.scenario, args.repo)
        name = "自研工具登记"
    elif args.cmd == "trace":
        code = cmd_trace(Path(args.plan), args.step, args.action, args.command,
                         args.result, args.elapsed, args.replay, args.note, args.attempt)
        name = "执行 trace"
    else:  # metrics
        code = cmd_metrics(Path(args.plan), args.finalize)
        name = "指标沉淀"

    if args.cmd in ("skill", "plan"):
        print(f"=== ai-workflow {name} ===")
        for status, item, note in results:
            print(f"{MARKS[status]} {item}" + (f" — {note}" if note else ""))
        n_fail = sum(1 for r in results if r[0] == "FAIL")
        if code != 0 and not results:
            # 环境/输入不满足，检查根本没跑起来 —— 绝不能输出"全绿"误导调用方
            print("=== 结果：未执行（环境或输入不满足，见上方 [ERROR]）===")
            return code
        print(result_line())
        return 1 if n_fail else code
    else:  # status / mark：表格/明细已即时打印，这里只回显结果行（status 的熔断汇总行在此可见）
        for status, item, note in results:
            print(f"{MARKS[status]} {item}" + (f" — {note}" if note else ""))
        n_fail = sum(1 for r in results if r[0] == "FAIL")
        return 1 if n_fail else code

if __name__ == "__main__":
    raise SystemExit(main())
