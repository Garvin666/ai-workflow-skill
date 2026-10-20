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


# ---- 模式接口卡契约（v4.42.0）----
# 唯一登记表：卡片名 → (手册文件, 须在手册中可追溯的编号)
# ⚠️ 新增/改名模式时**只改这一处**，不要把清单抄进文档（硬约定第 4 条：同一物理量不写两处）。
MODE_CARDS = {
    "作业模式": ("homework-mode.md", ("S0", "S1", "S2")),
    "科研模式": ("research-mode.md",
                 ("R0", "R1", "R2", "R3", "R4", "R5", "R6",
                  "N1", "N2", "N3", "N4", "N5", "N6")),
    "逆向拆解模式": ("teardown-mode.md",
                     ("D0", "D1", "D2", "D3", "D4", "D5",
                      "T1", "T2", "T3", "T4")),
    "图示设计模式": ("diagram-mode.md",
                     ("P0", "P1", "P2", "P3", "P4",
                      "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8")),
    "PPT 模式": ("ppt-mode.md",
                 ("Y0", "Y1", "Y2", "Y3", "Y4",
                  "E1", "E2", "E3", "E4", "E5", "E6")),
}
# 有手册但不独立成卡的两份：方法卡片是科研 R5 的第三通道，文献阅读是科研 R2 子阶段。
MODE_DOC_EXEMPT = {"method-card-mode.md", "literature-reading-mode.md"}
CARD_REQUIRED_FIELDS = ("触发", "前置路由", "验收")


def _check_mode_contracts(skill_dir: Path) -> None:
    """模式接口卡契约四条（v4.42.0）—— 保证「主干声明 ↔ 手册实现」不脱节。

    **存在意义**：接口卡把模式从 SKILL.md 正文降为「主干声明 + 手册实现」之后，
    声明侧与实现侧之间**此前没有任何机器约束** —— 卡片可以声明 N1–N6 而手册里删掉 N4，
    也可以新增一份 `*-mode.md` 却没有对应卡片，两种都不会被既有判据发现。

    **诚实边界**：只判**结构对齐**（清单、字段、指针、编号可追溯），
    不判内容质量、不判编号语义是否合理、不判卡片写得对不对。
    """
    sm = skill_dir / "SKILL.md"
    text = sm.read_text(encoding="utf-8")
    m = re.search(r"^## 模式接口卡.*?(?=\n## )", text, re.S | re.M)
    if not m:
        fail("模式契约：接口卡章节存在", "未找到 `## 模式接口卡` 章节")
        return
    ok("模式契约：接口卡章节存在")
    sec = m.group(0)
    refdir = skill_dir / "references"

    # ① 清单双向一致：卡片集合 ↔ 登记表 ↔ 磁盘手册，三方差集为空
    declared = re.findall(r"^### ([^（\n]+?)（", sec, re.M)
    on_disk = {p.name for p in refdir.glob("*-mode.md")}
    expected_docs = {d for d, _ in MODE_CARDS.values()}
    bad = []
    if set(declared) != set(MODE_CARDS):
        bad.append("卡片=%s 登记表=%s" % (sorted(set(MODE_CARDS) - set(declared)) or "-",
                                          sorted(set(declared) - set(MODE_CARDS)) or "-"))
    if expected_docs - on_disk:
        bad.append("手册缺失：" + ",".join(sorted(expected_docs - on_disk)))
    if on_disk - expected_docs - MODE_DOC_EXEMPT:
        bad.append("有手册无卡片且未豁免：" + ",".join(sorted(on_disk - expected_docs - MODE_DOC_EXEMPT)))
    if bad:
        fail("模式契约：清单双向一致", "；".join(bad))
    else:
        ok("模式契约：清单双向一致",
           "%d 张卡 ↔ %d 份手册，另 %d 份归子阶段（%s）"
           % (len(declared), len(expected_docs), len(MODE_DOC_EXEMPT),
              ",".join(sorted(MODE_DOC_EXEMPT))))

    parts = re.split(r"^### ", sec, flags=re.M)[1:]

    # ② 字段完整：每张卡必须自带触发/前置路由/验收，且至少含义务或结构
    incomplete = []
    for part in parts:
        name = part.split("（", 1)[0].strip() or "?"
        lack = [f for f in CARD_REQUIRED_FIELDS if f not in part]
        if "义务" not in part and "结构" not in part:
            lack.append("义务|结构")
        if lack:
            incomplete.append("%s 缺 %s" % (name, "/".join(lack)))
    if incomplete:
        fail("模式契约：卡片字段完整", "；".join(incomplete))
    else:
        ok("模式契约：卡片字段完整",
           "%d 张卡均含 %s + 义务|结构" % (len(parts), "/".join(CARD_REQUIRED_FIELDS)))

    # ③ 细则指针可达：每张卡必须指向**自己的**手册（防止错挂到别人的手册上）
    wrong = []
    for part in parts:
        name = part.split("（", 1)[0].strip() or "?"
        want = MODE_CARDS.get(name, (None,))[0]
        ptrs = re.findall(r"references/([\w\-]+-mode\.md)", part)
        if not ptrs:
            wrong.append("%s 无详情指针" % name)
        elif want not in ptrs:
            wrong.append("%s 未指向 %s（实为 %s）" % (name, want, ",".join(ptrs)))
    if wrong:
        fail("模式契约：细则指针可达", "；".join(wrong))
    else:
        ok("模式契约：细则指针可达", "每张卡均指向自己的手册")

    # ④ 编号可追溯：卡片声明的阶段/义务编号必须能在对应手册里检到
    untraceable = []
    total_ids = 0
    for name, (doc, ids) in MODE_CARDS.items():
        d = refdir / doc
        if not d.exists():
            untraceable.append("%s:%s 不存在" % (name, doc))
            continue
        dt = d.read_text(encoding="utf-8")
        miss = [i for i in ids if i not in dt]
        total_ids += len(ids)
        if miss:
            untraceable.append("%s 的 %s 在 %s 中检不到" % (name, ",".join(miss), doc))
    if untraceable:
        fail("模式契约：编号可追溯", "；".join(untraceable))
    else:
        ok("模式契约：编号可追溯", "%d 组编号共 %d 项，全部在手册中有定义" % (len(MODE_CARDS), total_ids))


# ---- 技能可见性双开关（v4.43.0）----
# 为什么单独成子命令、不并进 `skill`：本项判的是**主机配置漂移**，不是技能本体质量。
# 并进 `skill` 会把"主机把技能关了"报成技能 FAIL，指错排查方向（且会让技能本体永远红）。
VIS_CLOSED_VALUE = "user-invocable-only"   # settings.skillOverrides 的关闭态取值
VIS_FM_KEY = "disable-model-invocation"    # SKILL.md frontmatter 的关闭态字段


def _vis_homes(explicit=None):
    """候选数据家：显式 `--home` > `$CODEBUDDY_CONFIG_DIR` > `~/.workbuddy`，再加同族兄弟。

    ⚠️ 不做 `Path.home()` 单点推断：本机 `~/.workbuddy` 是**母本**，而会话实际跑在
    `E:\\WBHomes\\{A,B,C}\\.workbuddy` 之一 —— 只认 `~` 会去检查一个"没人用"的家，
    恒判一致（假绿）。故：以环境变量为准，再把**同父目录下**的 `*/.workbuddy` 一并纳入，
    用来做"跨家是否一致"的比对。
    """
    cands = []
    for p in (explicit or []):
        cands.append(Path(p))
    env = _os.environ.get("CODEBUDDY_CONFIG_DIR")
    if env:
        cands.append(Path(env))
    cands.append(Path.home() / ".workbuddy")
    seen, out = set(), []
    for p in cands:
        try:
            rp = p.resolve()
        except OSError:
            continue
        if rp in seen or not (rp / "settings.json").is_file():
            continue
        seen.add(rp)
        out.append(rp)
    # 同族兄弟：只取目录名恰为 `.workbuddy` 的（不含 `.workbuddy-*` 退役家）
    # ⚠️ 要往上看**两级**：本机 `Path.home()` 就是数据家本身（`E:\WBHomes\B`），
    # 数据家目录是 `E:\WBHomes\B\.workbuddy`，因此族根在 `home.parent.parent`。
    roots = []
    for h in list(out):
        for r in (h.parent, h.parent.parent):
            if r.is_dir() and r not in roots:
                roots.append(r)
    for container in roots:
        try:
            entries = sorted(container.iterdir())
        except OSError:
            continue
        # 两种布局都要：① `<族根>/X/.workbuddy`（本机 E:\WBHomes\{A,B,C}）
        # ② `<族根>/.workbuddy`（X 直接就是家）
        cands2 = [c / ".workbuddy" for c in entries if c.is_dir()]
        cands2 += [c for c in entries if c.name == ".workbuddy"]
        for s in cands2:
            if not (s / "settings.json").is_file():
                continue
            rp = s.resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(rp)
    return out


def _vis_label(home: Path) -> str:
    """家的可读标签：`<父目录名>/.workbuddy`（各家目录名都叫 .workbuddy，光看 name 分不清）。"""
    try:
        return "%s/%s" % (home.parent.name or str(home.parent), home.name)
    except (AttributeError, IndexError):
        return str(home)


def _vis_overrides(home: Path) -> dict:
    """读 `<home>/settings.json` 的 skillOverrides；缺失/坏 JSON 一律返回 {}（不抛）。"""
    try:
        data = json.loads((home / "settings.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    so = data.get("skillOverrides") or {}
    return so if isinstance(so, dict) else {}


def _vis_configured(home: Path) -> bool:
    """该家是否**做过可见性决策**（settings.json 里出现过 `skillOverrides` 键，哪怕值为空）。

    ⚠️ 为什么必须区分「无键」与「空字典」：本机预建了 D/E/F/G 等从未配置过的空数据家，
    它们没有这个键 ⇒ 技能全放（110 个双开）。把这种"从没配过"的家纳入跨家比对，
    会报出上百条**并非漂移**的分歧，把真实漂移（A/B/C 之间的几十条）淹掉。
    """
    try:
        data = json.loads((home / "settings.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    return "skillOverrides" in data


def _vis_has_fm_flag(skill_md: Path) -> bool:
    try:
        fm = _frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return False
    return bool(re.search(r"^%s:\s*true\s*$" % re.escape(VIS_FM_KEY), fm, re.M | re.I))


def _vis_states(skills_dir: Path, home: Path):
    """返回 (state_by_skill, unknown_values, closed_by_settings, closed_by_fm)。

    四态：双关（两处都关）/ 仅覆盖（只 settings 关）/ 仅frontmatter（只 frontmatter 关）/ 双开（可见）。
    """
    so = _vis_overrides(home)
    unknown = {k: v for k, v in so.items() if v != VIS_CLOSED_VALUE}
    st, by_s, by_f = {}, [], []
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir() or d.name.startswith((".", "_")):
            continue
        sm = d / "SKILL.md"
        if not sm.is_file():
            continue
        s_off = so.get(d.name) == VIS_CLOSED_VALUE
        f_off = _vis_has_fm_flag(sm)
        st[d.name] = ("双关" if (s_off and f_off) else
                      "仅覆盖" if s_off else
                      "仅frontmatter" if f_off else "双开")
        if s_off:
            by_s.append(d.name)
        if f_off:
            by_f.append(d.name)
    return st, unknown, by_s, by_f


def _check_version_alignment(skill_dir: Path) -> None:
    """版本三处对齐（v4.44.0）：frontmatter / H1 / README 的版本号必须同源。

    **存在意义**（2026-10-20 实测）：`SKILL.md` 已到 4.43.0，而 `README.md` 仍写着
    「当前版本 **v4.35.0**」—— 漂移 **8 个版本且无任何信号**。根因是「版本三处对齐」
    在 `skill-hygiene.md` 里只是**纪律项**，没有机器判据；而本仓同类结论早就写过：
    无机器判据的纪律项必然漂移（同一形态见 v4.44.0 之前的 `gen_skill_index --check` 口径）。

    **射程**：只判三处**字面版本号相等**。不判版本号该不该 bump、不判 `changelog` 是否
    有对应条目、不判版本语义（major/minor 该不该动）—— 那三项无客观 oracle。
    任一处**解析不到**也判 FAIL：声明缺失与声明不一致同样是「无法核对」，不能静默放行。
    """
    label = "版本三处对齐"
    sm = skill_dir / "SKILL.md"
    rd = skill_dir / "README.md"
    if not sm.exists():
        fail(label, "SKILL.md 不存在：%s" % sm)
        return
    try:
        sm_text = sm.read_text(encoding="utf-8")
    except OSError as exc:
        fail(label, "SKILL.md 读取失败：%s" % exc)
        return

    found: dict[str, str] = {}
    m = re.search(r"^version:\s*v?([0-9]+(?:\.[0-9]+)*)\s*$", sm_text, re.M)
    if m:
        found["frontmatter"] = m.group(1)
    m = re.search(r"^#\s+.*?\bv([0-9]+(?:\.[0-9]+)*)", sm_text, re.M)
    if m:
        found["H1"] = m.group(1)
    if rd.exists():
        try:
            m = re.search(r"当前版本\s*\*\*v?([0-9]+(?:\.[0-9]+)*)\*\*",
                          rd.read_text(encoding="utf-8"))
        except OSError as exc:
            fail(label, "README.md 读取失败：%s" % exc)
            return
        if m:
            found["README"] = m.group(1)

    missing = [k for k in ("frontmatter", "H1", "README") if k not in found]
    if missing:
        detail = "、".join("%s=%s" % (k, found[k]) for k in ("frontmatter", "H1", "README") if k in found)
        fail(label, "以下位置版本号解析不到：%s（已解析到：%s）"
                    % ("、".join(missing), detail or "无"))
        return

    if len(set(found.values())) == 1:
        ok(label, "%s（frontmatter / H1 / README 三处一致）" % found["frontmatter"])
    else:
        fail(label, "版本号不一致：frontmatter=%s ｜ H1=%s ｜ README=%s"
                    % (found["frontmatter"], found["H1"], found["README"]))


def _check_visibility(skills_dir: Path, homes=None) -> None:
    """技能可见性双开关比对（v4.43.0）：防「假复位」与「跨家不一致」。

    **存在意义**（2026-10-20 实测）：技能可见性由**两处**独立开关决定 ——
    `settings.json` 的 `skillOverrides` 与 `SKILL.md` 的 `disable-model-invocation`。
    两处同时关闭时，只清一处**不会**让技能重新可见，而**没有任何信号**提示；
    另外本机三个数据家各自一份 settings（覆盖条数互不相同），同一技能在不同家里
    可见性不同 ⇒ 在 A 家"放开"了、回 B 家发现"不生效"。这两类故障都属
    「改了没生效」，靠人眼比对两份文件发现不了。

    **射程**：只比对**开关状态**。不判该不该可见、不判可见性是否合理、不判技能质量。
    **分级**：两条判据均只 WARN（配置漂移是维护性问题，不是正确性问题）。
    **阴性对照**（人工执行、留档于 tasks/可见性判据与台账口径修复-2026-10-20/fixtures/）：
    ① 夹具里某技能两处都关 ⇒ 本项必须 WARN；② 只关一处 ⇒ 必须不报；
    ③ 两家可见集不同 ⇒ 跨家项必须 WARN；④ 两家相同 ⇒ 必须 OK。
    """
    if not skills_dir.is_dir():
        fail("可见性：技能库可读", str(skills_dir))
        return
    homes = [h for h in (homes or _vis_homes()) if (h / "settings.json").is_file()]
    if not homes:
        skip("可见性：数据家可定位", "未找到任何含 settings.json 的数据家（--home 可显式指定）")
        return
    # 只比对**做过可见性决策**的家（见 _vis_configured：预建但从未配置的家会把分歧淹没）
    homes = [h for h in homes if _vis_configured(h)]
    if not homes:
        skip("可见性：数据家可定位", "所有数据家的 settings.json 都无 skillOverrides 键（从未配置过）")
        return

    per_home = {}
    for h in homes:
        st, unknown, by_s, by_f = _vis_states(skills_dir, h)
        per_home[h] = (st, unknown, by_s, by_f)

    # ① 双关：同一家内两处同时关闭 —— 复位时最容易踩空
    both = {}
    for h, (st, unknown, _, _) in per_home.items():
        names = [n for n, s in st.items() if s == "双关"]
        if names:
            both[h] = names
    unknown_all = {h: u for h, (_, u, _, _) in per_home.items() if u}
    if both:
        detail = "；".join("%s：%s" % (_vis_label(h), ",".join(ns[:8]) + ("…" if len(ns) > 8 else ""))
                          for h, ns in both.items())
        warn("可见性：单家双关（复位须清两处）", detail)
    elif unknown_all:
        warn("可见性：单家双关（复位须清两处）",
             "未发现双关，但有未知取值未纳入判定：" +
             "；".join("%s：%s" % (_vis_label(h), u) for h, u in unknown_all.items()))
    else:
        ok("可见性：单家双关（复位须清两处）", "%d 家均无两处同时关闭的技能" % len(homes))

    # ② 跨家一致：同一技能在不同数据家的可见性必须相同
    base_home = homes[0]
    base_vis = {n for n, s in per_home[base_home][0].items() if s == "双开"}
    diffs, notes = {}, []
    for h in homes[1:]:
        vis = {n for n, s in per_home[h][0].items() if s == "双开"}
        d = base_vis ^ vis
        notes.append("%s 可见 %d" % (_vis_label(h), len(vis)))
        if d:
            diffs[h] = sorted(d)
    if len(homes) == 1:
        skip("可见性：跨家一致", "只定位到 1 家，无从比对")
    elif diffs:
        n_all = len(set().union(*diffs.values()))
        sample = sorted(set().union(*diffs.values()))[:6]
        warn("可见性：跨家一致",
             "基准 %s 可见 %d；%s；分歧 %d 个（%s%s）——在分歧家放开/关闭对另一家无效"
             % (_vis_label(base_home), len(base_vis), "，".join(notes), n_all,
                ",".join(sample), "…" if n_all > len(sample) else ""))
    else:
        ok("可见性：跨家一致", "%d 家可见集完全相同（%d 个）" % (len(homes), len(base_vis)))

    # ③ 矩阵（信息行）
    cells = []
    for h in homes:
        st = per_home[h][0]
        c = {k: 0 for k in ("双开", "仅覆盖", "仅frontmatter", "双关")}
        for s in st.values():
            c[s] += 1
        cells.append("%s 双开%d/仅覆盖%d/仅fm%d/双关%d"
                     % (_vis_label(h), c["双开"], c["仅覆盖"], c["仅frontmatter"], c["双关"]))
    ok("可见性：矩阵（双开=模型可见）", "；".join(cells))


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
    # v4.42.0：模式接口卡契约四条 —— 补上「主干声明 ↔ 手册实现」此前无任何机器约束的缺口
    _check_mode_contracts(skill_dir)
    # v4.44.0：版本三处对齐 —— 把「改了内容就 bump version」这条纪律项升格为门禁。
    #   实测缺口：README 停在 v4.35.0 而 SKILL.md 已 4.43.0，漂移 8 个版本无人发现。
    _check_version_alignment(skill_dir)
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

    p = sub.add_parser("visibility", help="技能可见性双开关比对（防假复位 / 跨数据家不一致，只 WARN）")
    p.add_argument("--skills-dir", default=str(Path(__file__).resolve().parent.parent.parent),
                   help="技能库根目录（默认按本文件位置反推，即 skills/）")
    p.add_argument("--home", action="append",
                   help="数据家目录（可重复；默认 $CODEBUDDY_CONFIG_DIR + 同族 */.workbuddy）")

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
    elif args.cmd == "visibility":
        _check_visibility(Path(args.skills_dir), [Path(h) for h in args.home] if args.home else None)
        code = 0
        name = "可见性比对"
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

    if args.cmd in ("skill", "plan", "visibility"):
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
