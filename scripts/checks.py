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
    _check_humanize_parity,
    _check_parity,
    _check_thinking_band_source,
)
from checks_judges import (  # noqa: F401
    _check_aesthetic,
    _check_autonomy,
    _check_category_decl,
    _check_cleanup,
    _check_closure,
    _check_cram,
    _check_entry_verdict,
    _check_fuse,
    _check_gate,
    _check_homework_sample,
    _check_homework_verdict,
    _check_humanize,
    _check_irreversible,
    _check_learning_sample,
    _check_learning_verdict,
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
    _check_thinking_sample,
    _check_thinking_verdict,
    _check_user_release,
    flush_absent,
    reset_absent,
    reset_exempt_caches,
    set_exempt_context,
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
    warn,
)

def _check_metrics_idempotent(skill_dir: Path) -> None:
    """幂等**行为**守卫（v4.10.1）：`metrics --finalize` 必须使 `_metrics.jsonl` 恰好一行。

    为什么必须做「行为级」而不是再加一句文档：`SKILL.md` 阶段 6 第 3 条写「**每任务一行**」，
    而落点按任务分文件 ⇒ 同一物理量的两处表述。旧实现无条件追加、**实测**产生 2~3 行（受控
    复现 + 真实工作区各一例），说明纯文档口径约束不住，必须真跑命令数行数。

    三个场景，**每个都可失败**（故不是恒真断言）：
      A 空目录连跑 2 次           → 恒 1 行（首次写入后必须是覆盖，不是追加）
      B 预置 2 行（造缺陷现场）   → 跑 1 次收敛为 1 行（自愈历史脏数据）
      C 预置 1 行                 → 行数仍 1，且内容刷新为最新终值（幂等 + 内容不陈旧）

    ⚠️ **本守卫的射程**：它只证「重复调用不增行」。不证「指标项统计得对」—— 那是
    `cmd_metrics` 的字段口径问题，本项不作判据。**不得**读成「metrics 已全部正确」。
    阴性对照（人工执行、留档，不入自检）：把 `cmd_metrics` 退回 `_jsonl_append` → 场景 A
    得 2 行、B 得 3 行 ⇒ 本守卫 FAIL。
    """
    import contextlib
    import io
    import json as _json

    with tempfile.TemporaryDirectory(prefix="aiwf_metrics_") as td:
        d = Path(td)
        plan = d / "plan.yaml"
        plan.write_text(
            'meta:\n  任务: "幂等守卫用例"\n  任务层级: L2\n  熔断状态: "正常"\n'
            '  计划修订: []\n  用户放行: []\n  不可逆副作用: []\n'
            'steps:\n  - id: 1\n    状态: 完成\n',
            encoding="utf-8")
        tf = d / "_metrics.jsonl"

        def _run() -> None:
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_metrics(plan, True)

        def _lines() -> list:
            return [x for x in tf.read_text(encoding="utf-8-sig").splitlines() if x.strip()]

        # A 空目录连跑 2 次
        _run()
        _run()
        n_a = len(_lines())
        (ok if n_a == 1 else fail)("metrics 幂等：空目录连跑 2 次恒 1 行", "实测 %d 行" % n_a)

        # B 预置 2 行 → 一次调用收敛
        tf.write_text('{"task": "旧1"}\n{"task": "旧2"}\n', encoding="utf-8")
        _run()
        n_b = len(_lines())
        (ok if n_b == 1 else fail)("metrics 幂等：预置 2 行收敛为 1 行", "实测 %d 行" % n_b)

        # C 预置 1 行 → 幂等且内容为最新终值
        tf.write_text('{"task": "旧", "done": 0}\n', encoding="utf-8")
        _run()
        ls = _lines()
        detail = "实测 %d 行" % len(ls)
        good = len(ls) == 1
        if good:
            try:
                rec = _json.loads(ls[0])
            except ValueError:
                rec, good = {}, False
            good = good and rec.get("done") == 1 and rec.get("superseded") == 1
            detail = "内容=%s" % (ls[0][:80] if ls else "")
        (ok if good else fail)("metrics 幂等：预置 1 行时刷新内容且不增行", detail)


def _check_entry_budget(skill_dir: Path) -> None:
    """入口手册体量预算（v4.19.0）：**只报 WARN，永不 FAIL**。

    为什么做：`SKILL.md` 是本技能的入口，它的体量直接决定每次加载的固定成本，而它此前
    **没有任何约束**（落地实测 2026-10-07 为 125 086 B）。参照外部技能 diagram-design 的
    入口硬上限（40 000 B）做了**本土化取舍**：本仓体量等级不同（3.13 倍），且体量本身不是
    正确性问题 ⇒ 只取「可见」这一半 —— 超软预算报 WARN，并把 `references/` 的总体量一并
    报出，便于判断「细则是否已在往 references 外迁」。

    ⚠️ 射程：本项**只量体量**。不判内容质量，不判该不该外迁，不判引用是否合理。
    ⚠️ 分级：永不 FAIL（理由与阈值取值见 `checks_core.SKILL_MD_BUDGET_BYTES` 的注释）。
    阴性对照（人工执行、留档）：把 `SKILL_MD_BUDGET_BYTES` 临时改为小于实测值的数 ⇒ 本项
    必须转 WARN；改回 ⇒ 必须复原为 OK。无此对照的判据不许上线。
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return  # 存在性由上游判据负责，此处不重复判（重复判会让同一缺陷报两次）
    n = skill_md.stat().st_size
    refs = sorted((skill_dir / "references").glob("*.md"))
    ref_bytes = sum(p.stat().st_size for p in refs)
    budget = SKILL_MD_BUDGET_BYTES
    detail = ("SKILL.md %d B / 预算 %d B（%.0f%%）；references/ %d 个文件共 %d B"
              % (n, budget, 100.0 * n / budget, len(refs), ref_bytes))
    if n > budget:
        warn("入口手册体量预算",
             "%s —— 超出 %d B：优先把细则外迁 references 并更新手册索引表，不要继续往入口堆"
             "（本项只 WARN，不阻断交付）" % (detail, n - budget))
    else:
        ok("入口手册体量预算", detail)


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
    # v4.11.0：跨格式阈值同源判据（思考模块的 ambiguity_band 在 judges.json 里，guard_constants 走 AST
    # 够不到 JSON）—— 单列，不并入 PARITY_ITEMS（后者比字符串集合，本条比浮点数组 + question 结构）。
    _check_thinking_band_source(skill_dir)
    # v4.15.0：跨格式同源判据（文风判据的 rubric 在 YAML、可执行副本在 Python）—— 单列理由同 v4.11.0，
    #   且比对逻辑归校验器自己（`humanize_scan.py --audit`），本条只读它的退出码，不重复实现。
    _check_humanize_parity(skill_dir)
    # v4.2.0 第五轮：主类枚举单独判（声明块 FAIL + 启发式 WARN）—— 它的模型是「跨文件唯一性（源规格面内）」，塞不进 PARITY_ITEMS 的并集模型
    _check_category_decl(skill_dir)
    # v4.3.0 / 批次 B：平台门控 vs 真实 import（AST 口径，不认注释与字符串里的同名字面量）
    _check_platform(skill_dir)
    # v4.3.0 / 批次 C：运行时闸门可用性与同源（gate.py 缺失、或口径另存一份副本，均 FAIL）
    _check_gate(skill_dir)
    # v4.10.1：`metrics --finalize` 的幂等**行为**守卫（SKILL.md 六「每任务一行」↔ 实现）
    _check_metrics_idempotent(skill_dir)
    # v4.19.0：入口手册体量预算（**只报 WARN**，不阻断）—— 补上「入口此前无任何体量约束」这一缺口
    _check_entry_budget(skill_dir)
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
    reset_absent()   # v4.13.0 起：清上一轮残留（本函数可能异常提前返回）
    # v4.21.0：设置豁免上下文（存量台账按任务名匹配、字段级豁免需读 steps[].验证方式）。
    #   与 `reset_absent` 并列清缓存 —— **两者都必须在入口调用**，否则上一轮的台账/上下文会串到本轮。
    set_exempt_context(plan_path.parent.name, steps)
    reset_exempt_caches()   # v4.21.0：清台账缓存（与上下文成对，同理必须每轮清）
    _check_entry_verdict(meta)
    _check_method_select(meta)
    _check_method_select_sample(meta)
    _check_retrieval_verdict(meta)
    _check_retrieval_sample(meta)
    # v4.7.0：检查项 18 = 作业判定结构合法（+ 派生字段自洽）；19 = 抽样人审指路（只 WARN）
    _check_homework_verdict(meta)
    _check_homework_sample(meta)
    # v4.8.0：检查项 20 = 学习判定结构合法（+ needs_learning 派生自洽 + 『无』组合非法）；21 = 抽样人审指路（只 WARN）
    _check_learning_verdict(meta)
    _check_learning_sample(meta)
    _check_autonomy(meta)
    _check_selftools(meta, steps, base)
    # v4.9.0：检查项 22 = 审美判据门禁（设计类产物：交付物含 .css）。与上面几条**不同族** ——
    # 它不做识别，也不信 plan 里自报的数字：登记了产物，就把校验器**实跑一遍**，跑出 FAIL 即 FAIL。
    _check_aesthetic(meta, steps, base)
    # v4.15.0：检查项 26 = 文风判据门禁（面向人阅读的散文正文）。与检查项 22 **同族但触发信号不同**：
    #   它不用交付物后缀（散文正文可内嵌在别的产物里，靠后缀会漏），改由 style-judge 自报 ——
    #   故整段缺省按 **L2 FAIL / L1 SKIP** 分档（与 13/14/16/18/20/23/24 同口径），
    #   而审美判据缺省只 WARN。**登记了产物就把校验器实跑一遍，跑出 FAIL 即 FAIL。**
    #   独立 try 包裹（与检查项 24 同源理由）：异常降级为 FAIL，不让异常吞掉整批输出。
    try:
        _check_humanize(meta, steps, base)
    except Exception as e:                       # noqa: BLE001 —— 刻意兜底，防穿透崩栈
        fail("meta.文风判定 合法（检查器异常）",
             f"{type(e).__name__}: {e} —— 已降级为 FAIL，不让异常吞掉整批输出")
    # v4.10.0：检查项 23 = 任务产物清理登记（可选字段；缺省 WARN、填写须合法；
    #   登记了 `清单` 却解析不到文件即 FAIL）。与检查项 22 同源口径：可选、填了就不能糊弄。
    _check_cleanup(meta, plan_path)
    # v4.19.0：检查项 27 = 知识点恶补报告登记（可选字段；**缺省 WARN**、填写须合法；
    #   状态=已出 时 `报告` 须解析到位且落在 `恶补/` 目录下，否则 FAIL）。
    #   ⚠️ 刻意**不**沿用 `_check_cleanup` 的「L2 缺省即 FAIL」—— 恶补是条件性产出（确无知识点
    #   可合法不产出），升 FAIL 会让全工作区 L2 任务回溯判红。理由与边界见 `_check_cram` docstring。
    _check_cram(meta, plan_path)
    # v4.11.0：检查项 24 = 思考判定结构合法（含 D1–D11、D14–D19 跨字段自洽；D12/D13 的靶面在
    #   报表/gold 而不在 plan.yaml，机器落点是 thinking_model.py 的 selftest/gold）；25 = 抽样人审
    #   指路（只 WARN）。⭐ 独立 try 包裹（设计 §9.2 第 4 条）：check_plan 原仅 1 个 try
    #   （except yaml.YAMLError），新增检查器若抛异常会穿透到 main ⇒ rc=1 且 stdout 残缺
    #   （整批结果被吞）——「崩栈比跳过更坏」。异常一律降级：24 → FAIL（没跑成必须显式）；
    #   25 → WARN（该检查项契约上永不计入 FAIL，崩溃只是「未能指路」）。
    try:
        _check_thinking_verdict(meta)
    except Exception as e:                       # noqa: BLE001 —— 刻意兜底，防穿透崩栈
        fail("meta.思考判定 合法（检查器异常）",
             f"{type(e).__name__}: {e} —— 已降级为 FAIL，不让异常吞掉整批输出")
    try:
        _check_thinking_sample(meta)
    except Exception as e:                       # noqa: BLE001
        warn("思考判定抽样人审（检查器异常）",
             f"{type(e).__name__}: {e} —— 该检查项契约上只 WARN，故降级为 WARN")
    # v4.13.0 起：把散落的「整段缺省」合并为一条（L1 出口专用；L2 已在 _absent 里直接 FAIL）。
    #   漏调 ⇒ 已声明 L1 的计划其缺省项会**静默消失**（静音 ≠ 通过），故此处不可省。
    flush_absent(meta)
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

    p = sub.add_parser("metrics", help="任务级指标沉淀（v4.0.0 / U8：写入 <任务目录>/_metrics.jsonl，v4.10.1 起幂等）")
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
