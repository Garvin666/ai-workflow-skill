# -*- coding: utf-8 -*-
"""checks 判据层：plan / skill 的各类 _check_* 判据

由 `scripts/checks.py` 拆分而来（v4.4.2 结构与可维护性优化，行为不变）。
依赖方向：core ← parity ← judges ← cmds ← entry（严格单向，无循环）。
"""
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)

import argparse
import ast
import json
import py_compile
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from checks_parity import (  # noqa: F401
    _p_category_decl,
    _resolve_sources,
    _scan_category_tables,
)
from checks_core import (  # noqa: F401
    AESTHETIC_DESIGN_EXT,
    AESTHETIC_EXEMPT_PLACEHOLDER,
    AESTHETIC_GEOM_EXT,
    AESTHETIC_GEOM_KEY,
    AESTHETIC_KEY,
    AESTHETIC_PRODUCTS,
    AESTHETIC_PROBE,
    AESTHETIC_REQUIRED,
    AESTHETIC_RUBRIC_DEFAULT,
    AESTHETIC_SCALE_IDS,
    AESTHETIC_SCALE_KEY,
    AESTHETIC_TOOL,
    CLEANUP_COUNT_KEYS,
    CLEANUP_KEY,
    CLEANUP_MANIFEST_KEY,
    CLEANUP_REQUIRED,
    CLEANUP_STATES,
    CATEGORY_SOURCES,
    CRAM_ARCHIVE_ROOT,
    CRAM_KEY,
    CRAM_PROJECT_KEY,
    CRAM_REASON_KEY,
    CRAM_REPORT_KEY,
    CRAM_REQUIRED,
    CRAM_STATES,
    DECISION_KEYS,
    ENTRY_DIMS,
    ENTRY_KEY,
    ENTRY_REQUIRED,
    FIELD_EXEMPT_BASIS_KEY,
    FIELD_EXEMPT_BLOCKED,
    FIELD_EXEMPT_KEY,
    FIELD_EXEMPT_VERDICT,
    FIELD_EXEMPTABLE,
    FUSE_REPORT,
    FUSE_SECTIONS,
    HOMEWORK_DIMS,
    HOMEWORK_KEY,
    HOMEWORK_MODES,
    HOMEWORK_REQUIRED,
    HOMEWORK_SAMPLE_BAND,
    HUMANIZE_DIMS,
    HUMANIZE_EXEMPT_PLACEHOLDER,
    HUMANIZE_KEY,
    HUMANIZE_REQUIRED,
    HUMANIZE_RUBRIC_DEFAULT,
    HUMANIZE_TEXT_EXT,
    HUMANIZE_TOOL,
    HUMANIZE_VERDICTS,
    INFRA_EXCEPTIONS,
    LEGACY_EXEMPT_BASIS_KEY,
    LEGACY_EXEMPT_DATE_KEY,
    LEGACY_EXEMPT_FIELDS_KEY,
    LEGACY_EXEMPT_FILE,
    LEGACY_EXEMPT_ITEM_NAMES,
    LEGACY_EXEMPT_LIST_KEY,
    IRREVERSIBLE_HINT,
    LEARNING_DIMS,
    LEARNING_KEY,
    LEARNING_KINDS,
    LEARNING_REQUIRED,
    LEARNING_SAMPLE_BAND,
    MAX_REVISIONS,
    METHOD_GAP_CLASSES,
    METHOD_KEY,
    METHOD_REQUIRED,
    METHOD_SAMPLE_BAND,
    PLAT_ALLOW_TOKEN,
    REVISION_KEYS,
    RETRIEVAL_KEY,
    RETRIEVAL_REQUIRED,
    RETRIEVAL_SAMPLE_BAND,
    RETRIEVAL_SOURCE_CLASSES,
    SCOPE_AUTH_KEY,
    SCOPE_HINT,
    SEDIMENT_TOKENS,
    SELFTOOL_KEYS,
    SELFTOOL_PENDING,
    SELFTOOL_PLACEHOLDER,
    STAGE2_SIGNAL_RE,
    STAGE2_STEP_RE,
    STAGE4_EXT,
    STAGE4_SIGNAL_RE,
    THINKING_AMEND_SIDES,
    THINKING_AXIS_EMPTY,
    THINKING_BANDS,
    THINKING_DIMS,
    THINKING_DIST_KEYS,
    THINKING_GOLD_MIN_ANNOTATED,
    THINKING_KEY,
    THINKING_LAYASTATUS,
    THINKING_MAIN_JUDGES,
    THINKING_NUOL_BAND,
    THINKING_PINNED_MODEL,
    THINKING_PROBE_KEYS,
    THINKING_REQUIRED,
    THINKING_SAMPLE_BAND,
    THINKING_VERDICTS,
    THINKING_VETO_AXES,
    VALID_CAPABILITY,
    VALID_CATEGORY,
    VALID_FUSE,
    VALID_MODEL_TIERS,
    VALID_TRIGGER,
    _DECL_BEGIN,
    _DECL_END,
    _DeclError,
    _PlatVisitor,
    _TRACE_HINT,
    _candidate_paths,
    _capability_ok,
    _frontmatter,
    _is_file_like,
    _norm_abs,
    _read_trace,
    _selftool_ledger,
    _selftool_marker_in,
    _selftool_registered,
    _selftool_scan_candidates,
    _step_tokens,
    _task_dir,
    _under,
    _validate_reflect_block,
    fail,
    ok,
    skip,
    warn,
)

# ---------------------------------------------------------------------------
# v4.13.0：整段缺省的分档出口（降噪 + 报覆盖率）
# v4.14.0：口径变硬 —— L2/层级不明 ⇒ 整段缺省**直接 FAIL**（用户拍板）；L1 ⇒ 仍汇成一条 SKIP
# ---------------------------------------------------------------------------
ABSENT = {}   # {检查项: 说明} —— 各 _check_* 在「整段缺省」分支登记，由 flush_absent 统一产出


def _tier_is_l1(meta):
    """本计划是否**已显式声明**为 L1。

    ⚠️ 缺层级信息 ⇒ False（**按 L2 处理**）：v4.14.0 起 L2 的整段缺省**直接 FAIL**，
       故「层级不明」= 从严（宁可多判红，也不静默放行 —— fail-open 的反面）。
       这里没有"猜它是轻任务于是静音"这条路。
    """
    return str((meta or {}).get("任务层级", "") or "").strip().upper() == "L1"


# ---------------------------------------------------------------------------
# v4.21.0：豁免粒度矩阵 —— 两条**独立于 L1** 的豁免读点
#   背景见checks_core.py同批常量块的注释（方案 §1.2/§3.4/§3.5）。
#   ⚠️⚠️ **三条防滥用约束，缺任一即为 fail-open 缺陷**：
#     1. 必须**产出 SKIP**，不得静默 return —— 否则该字段既不 FAIL 也不 SKIP，
#        从报告里彻底消失，这正是 `_absent` docstring 警告的「不是沉默」的反面；
#     2. 必须**校验客观依据**，不能只认自述串（护栏 G1/G4）；
#     3. **不得并进 `flush_absent` 聚合** —— 汇进去就分不清「不适用」与「已登记欠账」。
# ---------------------------------------------------------------------------

# 台账按base 缓存（同一份 plan 在一次 check_plan 里会被问 8 次；且文件读多��不必要）
_LEGACY_CACHE: dict = {}

# v4.21.0：本次 check_plan 的上下文（任务名 + steps），供 `_absent` 内部的两条豁免出口取用。
#   ⚠️ **刻意用模块级上下文，而不是给 8 个 `_check_*` 逐个加参数** ——
#     理由与既有的 `ABSENT`/`reset_absent` 同源：**豁免是横切关注点**，
#     让 8 个检查器各自透传两个与自身无关的参数只会把签名撑爆、且极易在新增检查器时漏传
#     （漏传 ⇒ 静默按「无依据」fail-closed —— 虽不假绿，但会让正当豁免莫名判红）。
#   ⚠️ 显式入参仍优先于上下文（夹具可直接调 `_absent` 做纯函数级对照）。
_EXEMPT_CTX: dict = {}


def set_exempt_context(task_name, steps):
    """设置本次 check_plan 的豁免上下文（`check_plan` 入口调用，与 `reset_absent` 并列）。"""
    _EXEMPT_CTX.clear()
    _EXEMPT_CTX["任务"] = str(task_name or "").strip()
    _EXEMPT_CTX["steps"] = steps or []


def _legacy_ledger():
    """读存量豁免台账（`scripts/legacy_exemptions.json`），返回 {任务名: {字段集, 依据}}。

    ⚠️ **台账读不到时必须 fail-closed**（返回空 dict ⇒ 全部维持 FAIL），**不得**因
       「文件缺失/JSON 坏了」而静默放行 —— 那正是「fail-open 取数面」的典型形态：
       判据看起来还在跑，实际已失效。
    ⚠️ 单条登记**四键不全 ⇒ 该条作废**（不放行）：台账不得成为「能往里塞任何任务」的万能豁免袋。
    """
    key = "ledger"
    if key in _LEGACY_CACHE:
        return _LEGACY_CACHE[key]
    out: dict = {}
    path = Path(__file__).resolve().parent / LEGACY_EXEMPT_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get("登记") or []
    except Exception:              # noqa: BLE001 —— 读不到就当没有台账（fail-closed）
        entries = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        task = str(e.get(LEGACY_EXEMPT_LIST_KEY, "") or "").strip()
        fields = e.get(LEGACY_EXEMPT_FIELDS_KEY) or []
        basis = str(e.get(LEGACY_EXEMPT_BASIS_KEY, "") or "").strip()
        when = str(e.get(LEGACY_EXEMPT_DATE_KEY, "") or "").strip()
        # 四键齐全才生效（缺依据/缺日期的登记不予放行 —— 防止台账被随手一填就开闸）
        if not (task and basis and when) or not isinstance(fields, list) or not fields:
            continue
        out[task] = {str(f).strip() for f in fields if str(f).strip()}
    _LEGACY_CACHE[key] = out
    return out


def reset_exempt_caches():
    """清空豁免相关缓存 —— `check_plan` 入口调用（与 `reset_absent` 同理：防上一轮残留）。"""
    _LEGACY_CACHE.clear()


def _stock_exempt(item, meta, task_name):
    """存量台账豁免：命中 ⇒ **产出一条带字段名的独立 SKIP**；未命中 ⇒ False（走后续分档）。

    语义 =「**需要但历史上没做**」（方案 §2.3 口径 C）—— 与 L1「本来就不需要」性质不同，
    故**不合并、不汇进 `flush_absent`**。
    """
    if _tier_is_l1(meta):
        return False                      # L1 走它自己的通道，两条出口不重叠
    fields = _legacy_ledger().get(str(task_name or "").strip())
    if not fields:
        return False
    sem = _item_to_semantic(item)
    if sem not in fields:
        return False
    item_name = LEGACY_EXEMPT_ITEM_NAMES.get(sem, item)
    skip(f"{item_name}（存量豁免）",
         "本计划已登记为**存量欠账**（v4.21.0 存量豁免台账）：该字段在 v4.14.0 之前交付时未落盘，"
         "**补齐等于编造当时的判断**，故不追认。这是「需要但历史上没做」，"
         "**不是「本来就不需要」**（后者是 L1 出口），二者不得合并。"
         "依据与登记时间见 scripts/legacy_exemptions.json")
    return True


def _item_to_semantic(item):
    """`_absent` 的 item 名 → 语义键。**刻意不用前缀匹配**（文风判定的 item 名无 `meta.` 前缀）。"""
    for sem, name in LEGACY_EXEMPT_ITEM_NAMES.items():
        if name == item:
            return sem
    return item


def _decl_matches_evidence(sem, decl, meta, steps):
    """声明「本任务该字段不适用」是否**与客观条件一致**（护栏 G1/G4 的实现点）。

    ⚠️ **本函数是这套设计的成败点**：`_field_exempt` 的前置由执行者自己写，
       若只认自述串，它就是「声明一句即永久免判」的**自证回路**（方案 §5.6 承认的风险）。
       故必须把声明**降格**为「必须与已落盘且已校验的字段一致」。

    返回 `(是否一致, 不一致时的说明)`。**查不到客观依据 ⇒ 一律判不一致（fail-closed）**，
    这是 `FIELD_EXEMPT_BLOCKED` 存在的全部理由。
    """
    cat = str(((meta or {}).get(ENTRY_KEY) or {}).get("category", "") or "").strip()
    entry = (meta or {}).get(ENTRY_KEY)
    if not isinstance(entry, dict) or not cat:
        return False, "`入口判定` 未落盘或无 `category` —— **客观依据不可得⇒ 不接受声明豁免**（fail-closed）"

    if sem == HUMANIZE_KEY:
        # 文风判据的适用面 = 面向人阅读的散文正文；code/chat 不涉散文 ⇒ 客观条件要求「不适用」
        if cat in ("code", "chat"):
            return True, ""
        return False, (f"`入口判定.category={cat}` 要求本任务判定文风（散文正文适用面）—— "
                       f"声明「不适用」与客观条件矛盾")

    if sem == HOMEWORK_KEY:
        # 作业判定的适用面 = 有作业特征的任务；code/chat 不可能是作业
        if cat in ("code", "chat"):
            return True, ""
        return False, (f"`入口判定.category={cat}` 不能排除作业特征（作业可能混在 content 里）—— "
                       f"声明「不适用」无客观依据可核")

    if sem == RETRIEVAL_KEY:
        # 检索判定的适用面 = 本任务是否要做检索动作；判据只能读**已落盘**的 steps[].验证方式
        sig = _retrieval_signal(steps)
        if sig is None:
            return False, "`steps[].验证方式` 未落盘 —— **客观依据不可得 ⇒ 不接受声明豁免**（fail-closed）"
        if not sig:
            return True, ""
        return False, f"`steps[].验证方式` 含检索类信号（命中 {len(sig)} 条）—— 声明「不适用」与已落盘内容矛盾"

    # 白名单外的字段走到这里：显式拒绝（不得静默放行）
    return False, f"`{sem}` **不在可豁免白名单内**（本版仅 {len(FIELD_EXEMPTABLE)} 个字段开通道）—— 不接受声明豁免（fail-closed）"


def _retrieval_signal(steps):
    """从 `steps[].验证方式` 抽检索类信号；返回命中的步骤 id 列表，**无 steps 时返回 None**（不可得）。

    ⚠️ 这是一道**启发式**判据（关键词命中），**会漏会误** —— 故它的作用是
       「**逼执行者把话说出来**」，而不是「自动判定该不该检索」。声明与它冲突时从严判FAIL。
    """
    if not steps:
        return None
    kw = ("检索", "搜索", "联网", "上网", "查资料", "查找", "调研", "grep", "search", "web")
    hit = []
    for s in steps:
        v = str(s.get("验证方式", "") or "").strip()
        low = v.lower()
        if v and any(k in low for k in kw):
            hit.append(str(s.get("id", "?")))
    return hit


def _field_exempt(item, meta, steps):
    """字段级适用性豁免（方案 A 的核心）：命中 ⇒ **产出一条带字段名的独立 SKIP**。

    ⚠️ 三条硬约束（见上方块注释）：必须产 SKIP / 必须校验客观依据 / 不得并入 flush_absent。
    ⚠️ 与存量台账**性质不同、不可互换**：本条是「**本任务不需要**」（客观条件已核），
       台账是「需要但历史上没做」。两者都产独立 SKIP，措辞可区分。
    """
    if _tier_is_l1(meta):
        return False
    decl_all = (meta or {}).get(FIELD_EXEMPT_KEY)
    if not isinstance(decl_all, dict):
        return False                      # 缺省 ⇒ 走现行 _absent 口径（向后兼容，老 plan 语义不变）
    sem = _item_to_semantic(item)
    if sem not in FIELD_EXEMPTABLE:
        # 白名单外：即使声明了也不放行，但**要说清为什么**（否则等于静音的另一种形式）
        if sem in decl_all:
            fail(item, f"声明 `{FIELD_EXEMPT_KEY}.{sem}` =「{FIELD_EXEMPT_VERDICT}」—— "
                       f"但 `{sem}` **不在可豁免白名单内**（本版仅 {'/'.join(FIELD_EXEMPTABLE)} 开通道）。"
                       f"白名单外的字段无客观依据可核，接受声明即等于自证豁免。处置：走 `任务层级: L1`，"
                       f"或照常落盘并填「不适用」")
        return False
    decl = decl_all.get(sem)
    if decl is None:
        return False
    if not isinstance(decl, dict) or str(decl.get("verdict", "") or "").strip() != FIELD_EXEMPT_VERDICT:
        fail(item, f"`{FIELD_EXEMPT_KEY}.{sem}` 结构非法 —— 须为 "
                   f"{{verdict: {FIELD_EXEMPT_VERDICT}, {FIELD_EXEMPT_BASIS_KEY}: <依据>}}")
        return False
    basis = str(decl.get(FIELD_EXEMPT_BASIS_KEY, "") or "").strip()
    if not basis:
        # 护栏 G2：不写依据 ⇒ FAIL（防静音 —— 与「未检测 ≠ 通过」同源）
        fail(item, f"声明 `{sem}` 不适用但**未写 `{FIELD_EXEMPT_BASIS_KEY}`** —— "
                   f"「不适用」必须留痕，否则「本就无需记」与「懒得记」机器不可区分")
        return False
    ok_, why = _decl_matches_evidence(sem, decl, meta, steps)
    if not ok_:
        # 护栏 G4：矛盾路径必判 FAIL（堵死自证回路；这是本函数唯一可能被滥用的地方）
        fail(item, f"声明 `{FIELD_EXEMPT_KEY}.{sem}` =「{FIELD_EXEMPT_VERDICT}」但**客观条件要求判定**"
                   f"（护栏 G4）—— {why}。声明理由『{basis}』不成立。**不得豁免**")
        return False
    skip(f"{item}（字段不适用）",
         f"本任务声明该字段不适用（v4.21.0 字段适用性矩阵）—— 客观依据已核：{why or '一致'}；"
         f"声明依据『{basis}』。这是「**本任务不需要**」，**不是「没记」**；"
         f"若客观条件变化（category 变了/ 新增了检索步骤）下次将判 FAIL")
    return True


def _absent(item, note, meta, steps=None, task_name=""):
    """整段缺省时的**分档出口**（v4.13.0 起统一写法；v4.14.0 起 L2 升 FAIL）。

    v4.14.0 口径（用户 2026-09-28 拍板「L2 一律升 FAIL」）：
      · **已声明 L1** ⇒ 只登记，由 `flush_absent` 汇成**一条 SKIP**
        —— L1 本就不跑这些判定，"不属本档的缺口"是明确结论，**不是沉默**（静音 ≠ 通过）；
      · **L2 / 层级不明** ⇒ **逐条 FAIL**。

    ⚠️ 与前版的区别（必须留痕，别当成"小改"）：v4.13.0 此处是 WARN，理由是
    （a）不追认历史计划（实测 24 份活跃 L2 里 11 份缺 `meta.入口判定`）；
    （b）避免 6–7 条同义 WARN 把真信号淹掉。用户已明确选择硬口径 ⇒ 本版按 FAIL 执行，
    但**存量影响面必须实测并逐份列出**（不得含糊成"影响不大"），且 L1 出口保留。

    ⚠️ **配套的契约变更（缺一不可）**：既然缺省即 FAIL，则这几项在 L2 **必须落盘**，
    **含显式否定结论** —— `needs_tool=false` / `needs_retrieval=false` 也要**写下来**。
    否则"合法结论"会被判成"缺口"，那是判据在造信号（与「无输入两态要分开」同源）。
    契约见 references/method-judge.md §10 与 references/retrieval-judge.md §10。

    ⚠️ 本项只判「**有没有落盘**」与「结构是否合法」，**不判判得对不对** ——
    校准无机器 oracle，不因升 FAIL 就变成准确率门禁。

    v4.21.0 起**新增两条前置豁免出口**（顺序刻意：先存量台账、再字段级适用性，
    最后才回到 L1/L2 分档 —— 理由是两者都比「L1 全豁免」**更精确**，
    应优先命中，否则「整任务豁免」会盖掉「字段级豁免」的可追溯性）：
      1. `_stock_exempt`  存量台账命中 ⇒ 独立 SKIP（「需要但历史上没做」）
      2. `_field_exempt`  字段适用性声明且客观依据一致 ⇒ 独立 SKIP（「本任务不需要」）
    ⚠️ 两条出口**各自已产 SKIP**，`_absent` 在命中时**立即 return**，
       **不再往下**登记 `ABSENT` —— 否则会出现「一条 SKIP + 一条聚合 SKIP」的重复计数
       （MEMORY 纪律：只看净计数会掩盖两股相反流动）。
    """
    # 出口 1：存量豁免台账（历史欠账，不追认）
    if _stock_exempt(item, meta, task_name or _EXEMPT_CTX.get("任务", "")):
        return
    # 出口 2：字段级适用性（客观依据已核才放行；矛盾路径已在函数内判 FAIL）
    _steps = steps if steps is not None else _EXEMPT_CTX.get("steps") or []
    if _field_exempt(item, meta, _steps):
        return
    if _tier_is_l1(meta):
        ABSENT[item] = note
    else:
        fail(item, note)


def reset_absent():
    """清空缺省登记 —— check_plan 入口调用，防上一轮残留（该函数可能异常提前返回）。"""
    ABSENT.clear()


def flush_absent(meta):
    """把本轮的缺省登记合并成**一条**（check_plan 末尾调用；漏调 ⇒ L1 的缺省会静默消失）。

    ⚠️ v4.14.0 起**只有 L1 会走到这里** —— L2/层级不明的缺省已在 `_absent` 里直接 FAIL。
    """
    n = len(ABSENT)
    items = "、".join(sorted(ABSENT))
    ABSENT.clear()
    if not n:
        return
    skip("判定字段覆盖率",
         "本计划已声明 L1：未落盘 %d 项（%s）—— 这几项是 L2 全流程的产出，"
         "L1 未做**不算缺口**（v4.14.0 起 L2/层级不明会**直接逐条 FAIL**，"
         "故须先显式声明 `meta.任务层级: L1` 才免判）；已落盘的字段仍按合法性校验"
         % (n, items))


def _check_fuse(meta: dict, steps: list, plan_path: Path) -> None:
    """熔断门禁（v2.5.2）：已熔断的任务不得作为可交付物。

    触发：meta「熔断状态」= 已熔断，**或**任一步骤状态为「熔断」（任一命中即阻断，fail-closed）。
    熔断时必须存在同目录《熔断报告.md》，且五个必填节**以标题行形式**出现（缺一即 FAIL）。
    复位须用户明示，且**两步缺一不可**，两步**均由 `mark` 支持**（不要求手改 YAML）：
    ① `mark <plan> --fuse 正常` 把 meta 改回『正常』；
    ② `mark <plan> <步骤id> <非熔断状态>` 把熔断步骤改回。
    合一句即：`mark <plan> <步骤id> 完成 --fuse 正常`。本工具**不做自动复位**。
    """
    raw = str(meta.get("熔断状态", "") or "").strip()
    if raw and raw not in VALID_FUSE:
        fail("meta.熔断状态 合法", f"实际『{raw}』，应为 {' / '.join(VALID_FUSE)} 之一（留空视为『正常』）")
        return
    tripped_steps = [str(s.get("id", "?")) for s in steps if str(s.get("状态", "")).strip() == "熔断"]
    if raw != "已熔断" and not tripped_steps:
        ok("熔断状态", "正常" if raw else "正常（未声明）")
        return

    detail = "meta.熔断状态=已熔断" if raw == "已熔断" else ""
    if tripped_steps:
        detail += ("；" if detail else "") + f"步骤 {'、'.join(tripped_steps)} 状态为『熔断』"
    fail("已熔断：不得作为可交付物",
         detail + " —— 自动化已停止。复位**须用户明示**，且两步缺一不可、均由 `mark` 完成："
         "① `mark <plan> --fuse 正常`；② `mark <plan> <步骤id> <非熔断状态>`。"
         "复位后重跑本命令确认 FAIL 清零（见 SKILL.md 熔断机制）")

    report = plan_path.parent / FUSE_REPORT
    if not report.exists():
        fail("熔断报告存在", f"缺失 {report}")
        return
    ok("熔断报告存在", str(report))
    text = report.read_text(encoding="utf-8", errors="replace")
    # 标题级校验：五个节名必须各自作为 markdown **标题行**出现。两步防绕过：
    #  ① 先剥除所有 fenced code block（```...```）——把节名写进代码块不算数（批D M1 复现的绕过）；
    #  ② 节名必须独占标题行（其后紧跟的不能是"单词字符"，含中文/字母/数字/下划线），
    #     防止「复位条件xx」这类前缀粘连绕过，同时允许「触发条件（质量类）」这种非单词字符后缀。
    text_body = re.sub(r"```.*?```", "", text, flags=re.S)
    miss = [s for s in FUSE_SECTIONS if not re.search(rf"^#+\s*{re.escape(s)}(?![\w])", text_body, re.M)]
    (ok if not miss else fail)(
        "熔断报告必含标题节",
        ("缺标题 " + "、".join(miss)) if miss else f"{len(FUSE_SECTIONS)}/{len(FUSE_SECTIONS)}",
    )

def _check_autonomy(meta: dict) -> None:
    """自主决策层留痕校验（v3.0.0）：字段**可选**，但一旦填写必须结构完整。

    设计取舍（与熔断机制同源）：不强制每个任务都产生决策记录 —— 纯本地读写的任务
    本就无外部辅助，"没写"是正常状态；此处只校验"写了的是否合法"。这样既不误伤
    历史 plan（无这些字段 → 判为未使用），也不给新 plan 添空表单负担。
    """
    dec = meta.get("决策记录")
    if dec is None or (isinstance(dec, list) and not dec):
        ok("决策记录", "未使用（无外部辅助引入，属正常）")
    elif not isinstance(dec, list):
        fail("决策记录格式", f"应为列表（每项必含 {'/'.join(DECISION_KEYS)}；时间由工具自动填）")
    else:
        bad = []
        for i, d in enumerate(dec, 1):
            if not isinstance(d, dict):
                bad.append(f"第{i}项非映射")
                continue
            miss = [k for k in DECISION_KEYS if not str(d.get(k, "") or "").strip()]
            if miss:
                bad.append(f"第{i}项缺 {'、'.join(miss)}")
            cap = str(d.get("能力类", "") or "").strip()
            if cap and not _capability_ok(cap):
                bad.append(f"第{i}项能力类『{cap}』不在 {VALID_CAPABILITY}")
        (ok if not bad else fail)("决策记录", f"{len(dec)} 条" if not bad else "；".join(bad))

    # v4.4.0：方法选用 ↔ 决策记录 一致性（留痕对齐，WARN 非门禁）。
    # 方法选用 marked needs_tool=true 的步骤应经 checks.py decide 留痕；漏记只是提示。
    _ms_list = meta.get(METHOD_KEY)
    if isinstance(_ms_list, list) and _ms_list:
        _need = sum(1 for _e in _ms_list if isinstance(_e, dict) and _e.get("needs_tool") is True)
        _dec_n = len(dec) if isinstance(dec, list) else 0
        if _need > _dec_n:
            warn("方法选用↔决策记录",
                 f"{_need} 条 needs_tool=true 但仅 {_dec_n} 条决策记录 —— 可能漏记"
                 "（needs_tool=true 应经 checks.py decide --from-method-select 留痕）")

    rev = meta.get("计划修订")
    if rev is None or (isinstance(rev, list) and not rev):
        ok("计划修订", "未使用（未发生重规划）")
    elif not isinstance(rev, list):
        fail("计划修订格式", f"应为列表（每项必含 {'/'.join(REVISION_KEYS)}）")
    else:
        bad = []
        for i, r in enumerate(rev, 1):
            if not isinstance(r, dict):
                bad.append(f"第{i}项非映射")
                continue
            miss = [k for k in REVISION_KEYS if not str(r.get(k, "") or "").strip()]
            if miss:
                bad.append(f"第{i}项缺 {'、'.join(miss)}")
            t = str(r.get("触发", "") or "").strip()
            if t and t not in VALID_TRIGGER:
                bad.append(f"第{i}项触发『{t}』不在 {VALID_TRIGGER}")
        if len(rev) > MAX_REVISIONS:
            bad.append(f"修订 {len(rev)} 次 > 上限 {MAX_REVISIONS}（应停下与用户重新对齐目标）")
        (ok if not bad else fail)("计划修订", f"{len(rev)} 条" if not bad else "；".join(bad))

def _check_selftools(meta: dict, steps: list | None = None, base: Path | None = None) -> None:
    """自研工具与技能留痕校验（v3.1.0）：字段**可选**，一旦填写必须结构完整。

    与 `_check_autonomy` 同口径 —— 多数任务本就没有自研产出，"没写"是正常状态；
    此处只校验"写了的是否合法"：四项必填非空 + 仓库链接须为真实 http(s) 地址
    （占位符判 FAIL；『待推送』判 SKIP 并明确提示，因为它是中间态而非完成态）。

    v3.5.0 / P1-1 增补：**反向检测**（交付物带标注头却未登记 → WARN）与**文案订正**。
    订正的依据是一次真实误读：原文案写"未使用（本任务无自研产出，**属正常**）"，读起来像
    "已验证本任务无自研产出"，但旧实现**根本没有扫过任何代码** —— 它只是没读到登记项。
    「无登记」不等于「无自研产出」，这句话必须说出来，否则这条判据会被当成"已验证"。
    """
    items = meta.get("自研工具")
    if items is None:
        items = []
    if not isinstance(items, list):
        fail("自研工具格式", f"应为列表（每项必含 {'/'.join(SELFTOOL_KEYS)}）")
        return

    bad, pending = [], []
    for i, t in enumerate(items, 1):
        if not isinstance(t, dict):
            bad.append(f"第{i}项非映射")
            continue
        miss = [k for k in SELFTOOL_KEYS if not str(t.get(k, "") or "").strip()]
        if miss:
            bad.append(f"第{i}项缺 {'、'.join(miss)}")
            continue
        url = str(t.get("仓库链接", "") or "").strip()
        if url == SELFTOOL_PENDING:
            pending.append(f"第{i}项『{str(t.get('名称', '')).strip() or '-'}』")
            continue
        if not re.match(r"^https?://", url) or SELFTOOL_PLACEHOLDER.search(url):
            bad.append(f"第{i}项仓库链接『{url[:40]}』非法：须为 http(s) 真实地址、禁止占位符"
                       f"（未推送前可填『{SELFTOOL_PENDING}』，但交付前必须回填）")

    # 反向检测：交付物里的自研标注头 ↔ **本 plan 的登记表 ∪ 全工作区登记总账**
    # ⚠️ 两侧都不能少（本轮被夹具的阴性对照抓到过）：只查总账 → 落在 `tasks/*/tmp/` 里的 plan
    # 自己的登记会被总账排除（总账刻意不读 tmp，因为那是探针伪造假登记的地方），
    # 于是「刚补登记却仍报警」；只查本 plan → 见 _selftool_ledger 的说明（既有工具被误判）。
    unreg: list[str] = []
    if steps is not None and base is not None:
        ledger = list(items) + _selftool_ledger(base)
        for p in _selftool_scan_candidates(steps, base):
            hit = _selftool_marker_in(p)
            if hit and not _selftool_registered(hit[1], ledger):
                unreg.append(f"{p.name}{hit[0]}")

    if bad:
        fail("自研工具登记", "；".join(bad))
    elif pending:
        skip("自研工具登记", f"{len(items)} 项，其中 {len(pending)} 项链接仍为『{SELFTOOL_PENDING}』"
                            f"（{'、'.join(pending)}）—— 交付前须回填真实仓库链接")
    elif items:
        ok("自研工具登记", f"{len(items)} 项")
    else:
        ok("自研工具登记", "未登记 —— ⚠️ 这是「**未检测**」不是「**已验证无自研**」：本判据只比对"
                           "**本任务交付物**里的自研标注头，且只扫**代码脚本**（不含 `tasks/*/tmp/`、"
                           "不遍历全盘代码、不扫文档类）；**未入交付物的自写脚本不会被发现**")

    if unreg:
        warn("自研工具漏登记", f"检出 {len(unreg)} 个带自研标注头、且**全工作区登记总账里都查不到**的交付物："
                               f"{'、'.join(unreg[:4])} —— 用 `checks.py selftool` 补登记后本告警消失"
                               f"（查表范围 = 本工作区所有 `tasks/**/plan.yaml` 的 `meta.自研工具`；"
                               f"只扫代码脚本，文档类不参与 —— 理由见 `CODE_EXT` 注释。此处只 WARN："
                               f"标注头是线索、登记才是判据，且推送前还有一道 FAIL 级交叉校验）")

def _check_scope(meta: dict, steps: list, base: Path) -> None:
    """交付物越界判据（v3.5.0 / P0-1）：把红线③从**纪律**变成**门禁**。

    判据：交付物解析后的绝对路径落在 `meta.工作区根` 之外，且既不在 `meta.越界授权` 登记的
    白名单内、也不属基础设施例外 → FAIL。

    ⚠️ **旧模板只警示不阻断**（关键设计，非妥协）：plan 里没有 `越界授权` 键说明它早于
    v3.3.0 的模板 —— 那种 plan 里出现根外交付物是**历史事实**，用新判据去追认它，等于拿新
    规则改写旧证据（技能在 P9-c 已立此口径：改历史记录去迁就新门禁是**为新判据篡改证据**）。
    故：无该键 → WARN 并列明；有该键（哪怕是空列表）→ 严格执行 FAIL。
    """
    root_txt = str(meta.get("工作区根", "") or "").strip()
    root = _norm_abs(Path(root_txt)) if root_txt else _norm_abs(base)
    allowed: list[str] = []
    auth = meta.get(SCOPE_AUTH_KEY)
    if isinstance(auth, list):
        for it in auth:
            if isinstance(it, dict):
                v = str(it.get("路径", "") or "").strip()
                if v:
                    allowed.append(_norm_abs(Path(v)))
    has_key = SCOPE_AUTH_KEY in meta

    outside, authed = [], []
    for s in steps:
        if not isinstance(s, dict):
            continue
        for tok in _step_tokens(s):
            if not _is_file_like(tok):
                continue
            for cand in _candidate_paths(tok, base):
                n = _norm_abs(cand)
                if _under(n, root) or any(x in n for x in INFRA_EXCEPTIONS):
                    continue
                rec = (s.get("id", "?"), tok, str(cand))
                (authed if any(_under(n, a) for a in allowed) else outside).append(rec)

    if not outside:
        note = "全部落在工作区根内（或属基础设施例外）"
        if authed:
            note = f"根外 {len(authed)} 项，均在 meta.{SCOPE_AUTH_KEY} 登记范围内"
        ok("交付物越界检查", note)
        return
    detail = "；".join(f"步骤 {i}『{t}』→ {p}" for i, t, p in outside[:4])
    if not has_key:
        warn("交付物越界检查", f"{len(outside)} 项落在工作区根 {root} 之外，但本 plan 无"
                               f"『{SCOPE_AUTH_KEY}』键（早于 v3.3.0 的旧模板）→ 只警示不阻断：{detail}{SCOPE_HINT}")
        return
    fail("交付物越界检查", f"{len(outside)} 项越界且未获授权：{detail}{SCOPE_HINT}")

def _aesthetic_css_deliverables(steps: list, base: Path) -> list[Path]:
    """设计类产物的**机器可判信号** = 本 plan 交付物里的 `.css`（v4.9.0 检查项 22）。

    范围口径与 `_selftool_scan_candidates` 一致并**同样显式声明**：不递归、不扫 `tasks/*/tmp/`
    （中间产物不入库、不外发，纳入只会让门禁被探针夹具误触）；**不要求文件已存在** ——
    「声明了 .css 却还没生成」由检查项 4（Anti-drop）负责，本判据只回答
    「这个任务是不是设计类任务」。后缀匹配走 `AESTHETIC_DESIGN_EXT`，不看 category。
    """
    seen: set[str] = set()
    out: list[Path] = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        for tok in _step_tokens(s):
            if not _is_file_like(tok):
                continue
            for cand in _candidate_paths(tok, base):
                rel = str(cand).replace("\\", "/").lower()
                if "/tmp/" in rel or rel in seen:
                    continue
                if cand.suffix.lower() not in AESTHETIC_DESIGN_EXT:
                    continue
                seen.add(rel)
                out.append(cand)
    return out


def _aesthetic_invoke(tool: Path, rubric: Path, css: Path, product: str, geom: Path | None = None,
                      scale_from: list | None = None):
    """实跑校验器，返回 `(exit, payload_or_None, raw)`。**fail-closed**：任何异常都不当作通过。

    `geom`（v1.2.1 / P3）为可选的渲染色 JSON；不带时 R1-R3 一律 SKIP —— 那是「未检测」，
    不是「通过」。调用方须把这一层**如实报出来**（见 `_check_aesthetic` 的渲染层注记）。

    `scale_from`（v1.5.0）为**声明刻度源** CSS 列表；不带时 G12/G13 一律 SKIP ——
    同样是「未检测」，由「刻度层注记」如实报出（与渲染层注记同构）。
    """
    cmd = [sys.executable, str(tool), "--rubric", str(rubric), "--css", str(css),
           "--product", product, "--json"]
    if geom is not None:
        cmd += ["--geom", str(geom)]
    for _s in scale_from or []:
        cmd += ["--scale-from", str(_s)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, None, f"{type(exc).__name__}: {exc}"
    raw = (p.stdout or "") + (p.stderr or "")
    try:
        return p.returncode, json.loads(p.stdout), raw
    except (ValueError, TypeError):
        return p.returncode, None, raw


def _check_aesthetic(meta: dict, steps: list | None = None, base: Path | None = None) -> None:
    """审美判据门禁（v4.9.0 / 检查项 22）：**设计类产物的验收，不是识别**。

    与四块快判的**分界**（一句话）：快判让模型自报置信度、机器只能校结构；
    本项**没有任何模型自填量** —— 判据是「登记了哪些产物 → 我把校验器跑一遍 → 跑出几个 FAIL」。
    故本条可以实现技能一直想要的那件事：**登记里的数字一概不采信**。

    ⚠️ 三条刻意的不对称，都在注释里说明理由而不是默默实现：
      · **缺省只 WARN**：技能既有口径 —— 新判据首版不上 FAIL（避免造出随机 FAIL 源），
        且向后兼容旧 plan（拿新规则追认历史计划 = 为新判据篡改证据）。
        但 WARN **只在真有 `.css` 交付物时**才出：非设计类任务判 SKIP，而不是把它也喊一遍。
      · **`豁免` 必须写理由**：口径不适用（例如判据的计量单位是「画面内」而产物是调色板）
        确实需要一个出口，但出口一旦无声就会变成橡皮图章 —— 故逐条打印、理由必填、
        并且「豁免了却本次没 FAIL」会 WARN（豁免项被长期闲置 = 该收回了）。
      · **渲染层单独报暴露率**（v1.2.1 / P3）：R1-R3 要渲染色才跑得起来。0 个产物带渲染色时
        不能只说「FAIL 已清零」—— 那会把「渲染层没测」读成「渲染层没问题」。故另出一条
        渲染层注记，明说 SKIP = **未检测**。（"an enabled setting does not show that the
        intervention was used" —— 开关存在 ≠ 干预生效。）
    """
    blk = meta.get(AESTHETIC_KEY)
    css_deliv = _aesthetic_css_deliverables(steps or [], base) if (steps and base) else []

    if blk is None:
        if css_deliv:
            warn("审美判据", f"交付物里有 {len(css_deliv)} 个 `.css`（设计类产物信号），"
                             f"但 `meta.{AESTHETIC_KEY}` 未登记 → **本次没跑过审美判据**"
                             f"（这不是「没问题」，是「未检测」）。登记后本项升级为 FAIL 级门禁；"
                             f"缺省只 WARN（不追认历史计划）。示例：\n"
                             f"    {AESTHETIC_KEY}:\n      产物类型: ppt\n      产物: [\n"
                             f"        - <交付物路径>.css\n      ]")
        else:
            skip("审美判据", "未登记，且交付物无 `.css` —— 非设计类任务（是「未涉及」，不是「已通过」）")
        return

    if not isinstance(blk, dict):
        fail("审美判据", f"应为映射（含 {'/'.join(AESTHETIC_REQUIRED)}）")
        return

    bad: list[str] = []
    for k in AESTHETIC_REQUIRED:
        if not blk.get(k):
            bad.append(f"缺 `{k}`")
    if bad:
        fail("审美判据", "；".join(bad))
        return

    product = str(blk.get("产物类型", "") or "").strip()
    if product not in AESTHETIC_PRODUCTS:
        fail("审美判据", f"`产物类型`『{product}』非法：须在 {'/'.join(AESTHETIC_PRODUCTS)} 内"
                         f"（与校验器 `--product` 同源；用于消费判据集的 `applies_to`）")
        return

    raw_targets = blk.get("产物")
    if not isinstance(raw_targets, list) or not raw_targets:
        fail("审美判据", "`产物` 须为非空列表（每项为一个 `.css` 产物路径）")
        return

    skill_root = Path(__file__).resolve().parent.parent
    tool = Path(__file__).resolve().parent / AESTHETIC_TOOL
    if not tool.is_file():
        fail("审美判据", f"校验器缺失：{tool} —— fail-closed（工具不在即判 FAIL，不降级为跳过）")
        return

    rubric_txt = str(blk.get("判据集", "") or "").strip() or AESTHETIC_RUBRIC_DEFAULT
    rp_cands = _candidate_paths(rubric_txt, base) if base else [Path(rubric_txt)]
    rubric = next((c for c in rp_cands if c.is_file()), None)
    if rubric is None:
        # 只在「用的是缺省值」时才回落到技能自带副本；自定义路径解析不到就是不存在，
        # 必须走 FAIL。⚠️ 此处曾写成 `rubric = skill_root / ...` 后直接 `rubric.is_file()`
        # —— 自定义路径分支下 `rubric` 仍是 None，会抛 AttributeError 把整个 checks.py 打崩
        # （既不是 FAIL 也不是 SKIP，且前面的检查项输出一起丢）。fail-closed 的反面教材，
        # 由 c6 夹具实测暴露并修掉（v4.9.0）。
        if rubric_txt == AESTHETIC_RUBRIC_DEFAULT:
            fallback = skill_root / AESTHETIC_RUBRIC_DEFAULT
            rubric = fallback if fallback.is_file() else None
    if rubric is None:
        fail("审美判据", f"判据集不存在：{rubric_txt}（相对路径以 --base 为基准解析；"
                         f"省略该键时取技能自带 `{AESTHETIC_RUBRIC_DEFAULT}`）")
        return

    # v1.5.0：**声明刻度源** —— G12/G13 的声明侧令牌 CSS。
    #   支持**两级登记**：`产物` 项里写 `声明刻度源: [...]`（该项专用），或在本块级写一份
    #   （块内所有产物共用）；**项级优先**。解析失败**不得**静默退回「未检测」——
    #   声明了就必须到位，否则 R 组的同类坑（`渲染色` 解析不到即 FAIL）会原样复现。
    def _resolve_scale(raw, where: str) -> tuple:
        out, bad = [], []
        for _j, _st in enumerate(raw or [], 1):
            _stxt = str(_st or "").strip()
            if not _stxt:
                bad.append(f"{where}第{_j}项为空")
                continue
            _cands = _candidate_paths(_stxt, base) if base else [Path(_stxt)]
            _sh = next((c for c in _cands if c.is_file()), None)
            if _sh is None:
                bad.append(f"{where}『{_stxt}』不存在（声明了就必须解析到位："
                           f"解析不到即 FAIL，不静默退回「未检测」）")
                continue
            out.append(_sh)
        return out, bad

    targets: list = []
    miss_t = []
    raw_scale = blk.get(AESTHETIC_SCALE_KEY)
    base_scale: list = []
    if raw_scale is not None:
        if not isinstance(raw_scale, list):
            fail("审美判据", f"`{AESTHETIC_SCALE_KEY}` 须为列表（每项为一个声明源 `.css` 路径）")
            return
        base_scale, _bad_bs = _resolve_scale(raw_scale, f"`{AESTHETIC_SCALE_KEY}` ")
        miss_t.extend(_bad_bs)
    for i, it in enumerate(raw_targets, 1):
        if isinstance(it, dict):
            txt = str(it.get("路径", "") or "").strip()
            gtxt = str(it.get(AESTHETIC_GEOM_KEY, "") or "").strip()
        else:
            txt, gtxt = str(it or "").strip(), ""
        if not txt:
            miss_t.append(f"第{i}项为空")
            continue
        cands = _candidate_paths(txt, base) if base else [Path(txt)]
        hit = next((c for c in cands if c.is_file()), None)
        if hit is None:
            miss_t.append(f"第{i}项『{txt}』不存在")
            continue
        if hit.suffix.lower() not in AESTHETIC_DESIGN_EXT:
            miss_t.append(f"第{i}项『{txt}』后缀非 {'/'.join(AESTHETIC_DESIGN_EXT)}"
                          f"（校验器以 CSS 为输入）")
            continue
        geom = None
        if gtxt:
            # 声明了渲染色就必须能解析到：解析不到**不得**静默退回「未检测」，
            # 否则 R 组会从「我登记了」悄悄变成「没测」，而调用方看不出差别。
            gc = _candidate_paths(gtxt, base) if base else [Path(gtxt)]
            gh = next((c for c in gc if c.is_file()), None)
            if gh is None:
                miss_t.append(f"第{i}项声明的 `{AESTHETIC_GEOM_KEY}`『{gtxt}』不存在"
                              f"（用 `{AESTHETIC_PROBE}` 取数后登记其输出路径）")
                continue
            if gh.suffix.lower() not in AESTHETIC_GEOM_EXT:
                miss_t.append(f"第{i}项 `{AESTHETIC_GEOM_KEY}`『{gtxt}』后缀非 "
                              f"{'/'.join(AESTHETIC_GEOM_EXT)}（校验器以 JSON 消费渲染色）")
                continue
            geom = gh
        # v1.5.0：项级 `声明刻度源` 覆盖块级；未写则继承块级（可为空 = 该产物不跑刻度层）
        s_scale = base_scale
        _raw_i = it.get(AESTHETIC_SCALE_KEY) if isinstance(it, dict) else None
        if _raw_i is not None:
            if not isinstance(_raw_i, list):
                miss_t.append(f"第{i}项 `{AESTHETIC_SCALE_KEY}` 须为列表")
                continue
            s_scale, _bad_i = _resolve_scale(_raw_i, f"第{i}项 `{AESTHETIC_SCALE_KEY}` ")
            miss_t.extend(_bad_i)
        targets.append((hit, geom, s_scale))
    if miss_t:
        fail("审美判据", "；".join(miss_t) + "（相对路径以 `--base` 为基准；工作区根之外须写绝对路径）")
        return

    # 豁免：{id, 理由} —— 出口唯一，且必须留痕
    exempt: dict[str, str] = {}
    raw_ex = blk.get("豁免") or []
    if not isinstance(raw_ex, list):
        fail("审美判据", "`豁免` 须为列表（每项 `{id, 理由}`）")
        return
    for i, it in enumerate(raw_ex, 1):
        if not isinstance(it, dict):
            fail("审美判据", f"豁免第{i}项非映射（应为 `{{id, 理由}}`）")
            return
        eid = str(it.get("id", "") or "").strip()
        why = str(it.get("理由", "") or "").strip()
        if not eid:
            fail("审美判据", f"豁免第{i}项缺 `id`")
            return
        if not why or why.lower() in AESTHETIC_EXEMPT_PLACEHOLDER:
            fail("审美判据", f"豁免 `{eid}` 的理由为空或为占位符（『{why}』）—— "
                             f"覆盖必须留痕：写清「为什么不适用」，否则不得豁免")
            return
        exempt[eid] = why

    all_fails: dict[str, list[str]] = {}
    tool_err: list[str] = []
    r_stat = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    s_stat = {"PASS": 0, "FAIL": 0, "SKIP": 0}   # v1.5.0：G12/G13 的**实测**状态
    for t, geom, s_scale in targets:
        rc, payload, raw = _aesthetic_invoke(tool, rubric, t, product, geom, s_scale)
        if payload is None:
            tool_err.append(f"{t.name} → 校验器未产出可解析 JSON（exit={rc}）：{raw.strip()[:120]}")
            continue
        # v1.5.0 修一处真缺陷（由门禁夹具 c4 暴露）：**`override_problems` 原先被丢掉**。
        #   校验器对「刻度源与被检文件同源 / 覆盖键非法」等情形会把问题写进
        #   `override_problems` 并**以非零码退出**，但这里只看 results 里有没有 FAIL
        #   ⇒ 那些问题被静默吞掉，门禁报「FAIL 已清零」。这正是 fail-closed 的反面：
        #   **进程已经说「有问题」，调用方却读成绿色**。改为与 FAIL 同级的阻断项。
        _ovp = payload.get("override_problems") or []
        if _ovp:
            tool_err.append(f"{t.name} → 覆盖/刻度源问题："
                            + "；".join(str(x) for x in _ovp[:2]))
            continue
        if rc not in (0, None) and not any(r.get("status") == "FAIL"
                                           for r in payload.get("results") or []):
            # 退出码非零却既无 FAIL 也无 problems：说明校验器自己认为有问题而无处可读，
            # 按 fail-closed 处理，不得当作通过。
            tool_err.append(f"{t.name} → 校验器 exit={rc}，但输出既无 FAIL 也无 problems"
                            f"（fail-closed：不当作通过）")
            continue
        for r in payload.get("results") or []:
            if str(r.get("id", "")).startswith("R") and r.get("status") in r_stat:
                r_stat[r["status"]] += 1
            if str(r.get("id", "")) in AESTHETIC_SCALE_IDS and r.get("status") in s_stat:
                s_stat[r["status"]] += 1
            if r.get("status") == "FAIL":
                all_fails.setdefault(str(r.get("id")), []).append(f"{t.name}: {r.get('detail', '')}")

    if tool_err:
        fail("审美判据", "；".join(tool_err))
        return

    blocked = {k: v for k, v in all_fails.items() if k not in exempt}
    stale = [k for k in exempt if k not in all_fails]

    if blocked:
        items = "；".join(f"{k}（{len(v)} 个产物）" for k, v in sorted(blocked.items()))
        detail = "；".join(v[0] for _, v in sorted(blocked.items()))
        fail("审美判据", f"实跑 FAIL={sum(len(v) for v in blocked.values())} 处，未清零不得交付：{items}。"
                         f"样例：{detail[:200]}")
    else:
        note = (f"实跑 {len(targets)} 个产物 / 判据集 {rubric.name} / 产物类型 {product}；FAIL 已清零"
                + (f"；豁免 {len(exempt)} 条已放行" if exempt else ""))
        ok("审美判据", note)

    # 渲染层暴露率（v1.2.1 / P3）——「没测」必须与「通过」可区分，不许并进同一个绿。
    # v1.2.2：**再进一步** —— 「登记了渲染色」也不等于「R 组真跑起来了」。
    #   实测暴露的形态：geom 文件存在但作用域选择器没命中 / nodes 为空 ⇒ R1-R3 全 SKIP，
    #   若只看「带没带 geom」，注记会写「已实跑」——那是**开关存在冒充干预生效**。
    #   故改为按**校验器实际产出的 R 组状态**计数，并单独报 PAL。
    n_geom = sum(1 for _, g, _ in targets if g is not None)
    r_ran = r_stat["PASS"] + r_stat["FAIL"]
    if n_geom == 0:
        warn("审美判据渲染层", f"0/{len(targets)} 个产物登记 `{AESTHETIC_GEOM_KEY}` —— "
                                f"R1-R3（近乎对齐 / 兄弟尺寸 / 垂直韵律）本次判 SKIP，**渲染层未检测**，"
                                f"不是通过。要覆盖该层：按 references/aesthetic-rubric.yaml 渲染层段用 "
                                f"`scripts/{AESTHETIC_PROBE}` 取数，再在 `产物` 项里写 "
                                f"`{AESTHETIC_GEOM_KEY}: <geom.json 路径>`。")
    elif n_geom < len(targets):
        warn("审美判据渲染层", f"{n_geom}/{len(targets)} 个产物带渲染色 —— 其余产物的 R1-R3 仍是 SKIP"
                                f"（**未检测**，不是通过）。")
    elif r_ran == 0:
        warn("审美判据渲染层", f"{n_geom}/{len(targets)} 个产物**登记了**渲染色，但 R 组实跑后"
                                f"**全部 SKIP**（PASS 0 / FAIL 0 / SKIP {r_stat['SKIP']}）—— "
                                f"渲染色里没有可判的输入（作用域选择器未命中 / nodes 为空 / "
                                f"韵律网格未声明等）。**仍未检测，不是通过。**")
    else:
        ok("审美判据渲染层", f"{n_geom}/{len(targets)} 个产物带渲染色 → R 组实跑"
                             f"（PASS {r_stat['PASS']} / FAIL {r_stat['FAIL']} / SKIP {r_stat['SKIP']}）")

    # v1.5.0：**刻度层暴露率**（与渲染层注记同构）。G12/G13 要「声明刻度源」才跑得起来；
    #   0 个产物登记时不能只说「FAIL 已清零」——那会把「刻度层没测」读成「刻度层没问题」。
    #   且**登记了 ≠ 真跑起来了**（产物无时长 ⇒ G13 仍 SKIP），故按**实跑状态**计数，
    #   不用「带没带开关」冒充干预生效（与 v1.2.2 渲染层那条同源）。
    n_scale = sum(1 for _, _, s in targets if s)
    s_ran = s_stat["PASS"] + s_stat["FAIL"]
    if n_scale == 0:
        warn("审美判据刻度层", f"0/{len(targets)} 个产物登记 `{AESTHETIC_SCALE_KEY}` —— "
                                f"G12/G13（字号/时长刻度一致性）本次判 SKIP，**刻度层未检测**，"
                                f"不是通过。要覆盖该层：在 `{AESTHETIC_KEY}` 块（或单个产物项）里写"
                                f"『{AESTHETIC_SCALE_KEY}』，列出该产物依赖的**声明侧**令牌 CSS"
                                f"（ui kit 类产物通常为 `src/styles/tokens.css` + 所用主题的令牌 CSS；"
                                f"相对路径以 `--base` 为基准；**不得填被检的那份 CSS**）。")
    elif s_ran == 0:
        warn("审美判据刻度层", f"{n_scale}/{len(targets)} 个产物**登记了** `{AESTHETIC_SCALE_KEY}`，"
                                f"但 G12/G13 实跑后**全部 SKIP**（PASS 0 / FAIL 0 / SKIP {s_stat['SKIP']}）"
                                f"—— 仍**未检测，不是通过**（常见因：声明源里没有对应维度的令牌，"
                                f"或产物本身不含该维度，如版式层无时长）。")
    else:
        ok("审美判据刻度层", f"{n_scale}/{len(targets)} 个产物带声明刻度源 → G12/G13 实跑"
                             f"（PASS {s_stat['PASS']} / FAIL {s_stat['FAIL']} / SKIP {s_stat['SKIP']}）")

    if exempt:
        trace = "；".join(f"{k}=『{v}』" for k, v in exempt.items())
        if stale:
            warn("审美判据豁免", f"本次实跑并未 FAIL、却被豁免的判据：{'、'.join(stale)} —— "
                                 f"豁免项长期闲置应收回（否则它会从「有理由的例外」退化成橡皮图章）。"
                                 f"现存豁免：{trace}")
        else:
            ok("审美判据豁免", f"{len(exempt)} 条（留痕：{trace}）")


def _humanize_invoke(tool: Path, rubric: Path, text: Path | None = None,
                     gate: bool = False, diff: tuple | None = None):
    """实跑去 AI 味校验器，返回 `(exit, payload_or_None, raw)`。**fail-closed**：任何异常都不当作通过。

    `diff=(before, after)` 时跑 `--diff-fidelity`（保真比对）；否则跑 `--text <产物> --gate`（FAIL 即 exit 1）。
    两者都带 `--json`，便于调用侧读结构化结果而**不解析人读文本**（解析展示串是"读数从被截断的字符串反解"
    那类事故的温床）。
    """
    cmd = [sys.executable, str(tool)]
    if diff is not None:
        cmd += ["--diff-fidelity", str(diff[0]), str(diff[1]), "--json"]
    else:
        cmd += ["--text", str(text), "--rubric", str(rubric), "--json"]
        if gate:
            cmd += ["--gate"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, None, f"{type(exc).__name__}: {exc}"
    raw = (p.stdout or "") + (p.stderr or "")
    try:
        return p.returncode, json.loads(p.stdout), raw
    except (ValueError, TypeError):
        return p.returncode, None, raw


def _check_humanize(meta: dict, steps: list | None = None, base: Path | None = None) -> None:
    """文风判据门禁（v4.15.0 / 检查项 26）：**面向人阅读的散文正文的验收，不是识别**。

    与七块快判的分界（一句话）：快判让模型自报置信度、机器只能校结构；本项**除结构校验外还有一层实跑** ——
    判据是「登记了哪些产物 → 我把校验器跑一遍 → 跑出几个 FAIL」。故本条实现技能一直想要的那件事：
    **登记里的数字一概不采信**。

    ⚠️ 与审美判据（检查项 22）的关系：同族、同一套三档纪律（PASS/FAIL/SKIP 严格分开、`source` 字段、
    `豁免` 出口、阴性对照），但**输入不同**（审美吃 `.css`，本项吃散文正文），且**触发信号不同** ——
    审美用「交付物后缀含 `.css`」做确定性触发；本项**不用后缀**（散文正文可以是 `.md/.txt/.docx`，
    也可内嵌在别的产物里，靠后缀会漏），改由 style-judge 自报。**代价如实登记：漏报（该登记没登记）
    机器抓不到** —— 这是本项诚实边界的一部分，不得含糊成"已全覆盖"。

    ⚠️ 四条刻意的不对称，都在注释里说明理由而不是默默实现：
      · **整段缺省按 L2 FAIL / L1 SKIP 分档**（与检查项 13/14/16/18/20/23/24 同口径）。
        与审美判据的「缺省只 WARN」**不同**：审美缺省只 WARN 是因为它的触发信号是交付物后缀、
        可能对非设计类任务误报；本项由 style-judge 自报，**缺省即"该判没判"**，故从严。
      · **`豁免` 必须写理由**：口径不适用确实需要一个出口，但出口一旦无声就会变成橡皮图章 ——
        故逐条打印、理由必填、并且「豁免了却本次没 FAIL」会 WARN（闲置的豁免该收回）。
      · **事实保真不可豁免**：`--diff-fidelity` 出的差异是**硬约束**（去味不得改动任何数字/否定/限定/归因），
        与 rubric 的风格类 FAIL **不是一回事** —— 它是「改坏了」，故**不给豁免出口**（同 §7.1 双条件）。
      · **保真层单独报暴露率**（与审美判据的渲染层/刻度层注记同构）：未登记 `改写前`/`改写后` 时
        不能只说「FAIL 已清零」—— 那会把「保真没测」读成「保真没问题」。
    """
    blk = meta.get(HUMANIZE_KEY)

    if blk is None:
        _absent(HUMANIZE_KEY,
                "**L2 必填**：v4.15.0 起整段缺省判 FAIL（L1 出口见同批变更）。本项是面向人阅读"
                "散文正文的机器验收 —— 交付物含报告/方案/文档类正文时，阶段 0 第 1.5 步的 style-judge "
                "应产出本字段（判定为「不适用」也要写下来）。示例：\n"
                "    %s:\n      verdict: 走去味\n"
                "      distribution: {走去味: 0.8, 只登记: 0.1, 已达标: 0.05, 不适用: 0.05}\n"
                "      confidence: 0.8\n      dimensions: {S1: 0.9, S2: 0.8, S3: 0.7, S4: 0.6, S5: 0.1}\n"
                "      ambiguity: false\n      route_hint: 阶段 3 展开改写＋保真核对\n"
                "      needs_humanize: true\n      适用范围: 报告正文（.md）\n"
                "      产物: [tasks/<任务>/报告.md]\n"
                "      改写前: tasks/<任务>/tmp/初稿.md\n      改写后: tasks/<任务>/报告.md"
                % HUMANIZE_KEY,
                meta)
        return

    if not isinstance(blk, dict):
        fail(HUMANIZE_KEY, f"应为映射（含 {'/'.join(HUMANIZE_REQUIRED)}）")
        return

    bad = [f"缺 `{k}`" for k in HUMANIZE_REQUIRED if blk.get(k) in (None, "", [])]
    if bad:
        fail(HUMANIZE_KEY, "；".join(bad))
        return

    verdict = str(blk.get("verdict", "") or "").strip()
    if verdict not in HUMANIZE_VERDICTS:
        fail(HUMANIZE_KEY, f"`verdict`『{verdict}』非法：须在 {'/'.join(HUMANIZE_VERDICTS)} 内"
                           f"（取值域唯一源见 references/humanize-judge.md §1）")
        return

    dist = blk.get("distribution")
    if not isinstance(dist, dict) or set(dist) != set(HUMANIZE_VERDICTS):
        fail(HUMANIZE_KEY, f"`distribution` 须恰含四键 {sorted(HUMANIZE_VERDICTS)}（与 verdict 同源）")
        return
    try:
        dvals = {k: float(v) for k, v in dist.items()}
    except (TypeError, ValueError):
        fail(HUMANIZE_KEY, "`distribution` 各项须为数值")
        return
    if any(v < 0 or v > 1 for v in dvals.values()):
        fail(HUMANIZE_KEY, "`distribution` 各项须 ∈ [0,1]")
        return
    if abs(sum(dvals.values()) - 1.0) > 1e-3:
        fail(HUMANIZE_KEY, f"`distribution` 四键之和须 = 1（实测 {sum(dvals.values()):.4f}）")
        return

    try:
        conf = float(blk.get("confidence"))
    except (TypeError, ValueError):
        fail(HUMANIZE_KEY, f"`confidence` 须为数值（实测『{blk.get('confidence')}』）")
        return
    if not (0.0 <= conf <= 1.0):
        fail(HUMANIZE_KEY, f"`confidence` 须 ∈ [0,1]（实测 {conf}）")
        return
    if abs(conf - max(dvals.values())) > 1e-3:
        fail(HUMANIZE_KEY, f"`confidence` 须 = max(distribution) = {max(dvals.values()):.4f}"
                           f"（实测 {conf:.4f}）—— 派生自洽，不采信自报")
        return

    dims = blk.get("dimensions")
    if not isinstance(dims, dict) or set(dims) != set(HUMANIZE_DIMS):
        fail(HUMANIZE_KEY, f"`dimensions` 须恰含 {list(HUMANIZE_DIMS)}（不含其它键）")
        return
    try:
        dvs = {k: float(v) for k, v in dims.items()}
    except (TypeError, ValueError):
        fail(HUMANIZE_KEY, "`dimensions` 各项须为数值")
        return
    if any(v < 0 or v > 1 for v in dvs.values()):
        fail(HUMANIZE_KEY, "`dimensions` 各项须 ∈ [0,1]")
        return

    amb = blk.get("ambiguity")
    if not isinstance(amb, bool):
        fail(HUMANIZE_KEY, f"`ambiguity` 须为 bool（实测『{amb}』）")
        return

    nh = blk.get("needs_humanize")
    if not isinstance(nh, bool):
        fail(HUMANIZE_KEY, f"`needs_humanize` 须为 bool（实测『{nh}』）")
        return
    if nh != (verdict == "走去味"):
        fail(HUMANIZE_KEY, f"`needs_humanize`={nh} 与 `verdict`『{verdict}』矛盾"
                           f"（派生值必须 =（verdict == 走去味））—— 这是确定性判据，不采信自报")
        return

    scope = str(blk.get("适用范围", "") or "").strip()
    if not scope:
        fail(HUMANIZE_KEY, "`适用范围` 须非空（人审信号：写明产物范围与体裁，供核对「未对代码/JSON 跑去味」）")
        return

    skill_root = Path(__file__).resolve().parent.parent
    tool = Path(__file__).resolve().parent / HUMANIZE_TOOL
    if not tool.is_file():
        fail(HUMANIZE_KEY, f"校验器缺失：{tool} —— fail-closed（工具不在即判 FAIL，不降级为跳过）")
        return

    rubric_txt = str(blk.get("判据集", "") or "").strip() or HUMANIZE_RUBRIC_DEFAULT
    rp_cands = _candidate_paths(rubric_txt, base) if base else [Path(rubric_txt)]
    rubric = next((c for c in rp_cands if c.is_file()), None)
    if rubric is None and rubric_txt == HUMANIZE_RUBRIC_DEFAULT:
        fallback = skill_root / HUMANIZE_RUBRIC_DEFAULT
        rubric = fallback if fallback.is_file() else None
    if rubric is None:
        fail(HUMANIZE_KEY, f"判据集不存在：{rubric_txt}（相对路径以 --base 为基准解析；"
                           f"省略该键时取技能自带 `{HUMANIZE_RUBRIC_DEFAULT}`）")
        return

    # 豁免：{id, 理由} —— 出口唯一，且必须留痕（**不适用于事实保真**）
    exempt: dict[str, str] = {}
    raw_ex = blk.get("豁免") or []
    if not isinstance(raw_ex, list):
        fail(HUMANIZE_KEY, "`豁免` 须为列表（每项 `{id, 理由}`）")
        return
    for i, it in enumerate(raw_ex, 1):
        if not isinstance(it, dict):
            fail(HUMANIZE_KEY, f"豁免第{i}项非映射（应为 `{{id, 理由}}`）")
            return
        eid = str(it.get("id", "") or "").strip()
        why = str(it.get("理由", "") or "").strip()
        if not eid:
            fail(HUMANIZE_KEY, f"豁免第{i}项缺 `id`")
            return
        if not why or why.lower() in HUMANIZE_EXEMPT_PLACEHOLDER:
            fail(HUMANIZE_KEY, f"豁免 `{eid}` 的理由为空或为占位符（『{why}』）—— "
                               f"覆盖必须留痕：写清「为什么不适用」，否则不得豁免")
            return
        exempt[eid] = why

    # 产物：逐项解析到位（声明了就必须能解析 —— 不静默退回「未检测」）
    raw_targets = blk.get("产物")
    targets: list = []
    miss_t: list[str] = []
    if raw_targets is not None:
        if not isinstance(raw_targets, list):
            fail(HUMANIZE_KEY, "`产物` 须为列表（每项为一个文本产物路径）")
            return
        for i, it in enumerate(raw_targets, 1):
            txt = str(it or "").strip()
            if not txt:
                miss_t.append(f"第{i}项为空")
                continue
            cands = _candidate_paths(txt, base) if base else [Path(txt)]
            hit = next((c for c in cands if c.is_file()), None)
            if hit is None:
                miss_t.append(f"第{i}项『{txt}』不存在")
                continue
            if hit.suffix.lower() not in HUMANIZE_TEXT_EXT:
                miss_t.append(f"第{i}项『{txt}』后缀非 {'/'.join(HUMANIZE_TEXT_EXT)}"
                              f"（本项以散文正文为输入；代码/JSON/YAML 不应登记）")
                continue
            targets.append(hit)
    if miss_t:
        fail(HUMANIZE_KEY, "；".join(miss_t) + "（相对路径以 `--base` 为基准；工作区根之外须写绝对路径）")
        return

    # 改写前/改写后：成对登记，供 --diff-fidelity
    diff_pair = None
    b_raw = str(blk.get("改写前", "") or "").strip()
    a_raw = str(blk.get("改写后", "") or "").strip()
    if b_raw or a_raw:
        if not (b_raw and a_raw):
            fail(HUMANIZE_KEY, "`改写前`/`改写后` 须**成对**登记（只填一个无法比对）")
            return
        bp = next((c for c in (_candidate_paths(b_raw, base) if base else [Path(b_raw)]) if c.is_file()), None)
        ap = next((c for c in (_candidate_paths(a_raw, base) if base else [Path(a_raw)]) if c.is_file()), None)
        if bp is None or ap is None:
            fail(HUMANIZE_KEY, f"`改写前`/`改写后` 声明的路径解析不到（『{b_raw}』/『{a_raw}』）—— "
                               f"声明了就必须到位，**不静默退回「未检测」**")
            return
        diff_pair = (bp, ap)

    if verdict == "走去味" and not targets and diff_pair is None:
        fail(HUMANIZE_KEY, "`verdict` = 走去味，但既未登记 `产物` 也未登记 `改写前/改写后` —— "
                           "**声称要去味却没有实跑入口**（登记里的数字一概不采信；无入口即无法验证）")
        return
    if verdict == "不适用" and (targets or diff_pair):
        warn(HUMANIZE_KEY, "`verdict` = 不适用，却登记了 `产物`/`改写前/改写后` —— "
                           "判定与登记自相矛盾，请核对（仍会实跑，结果照报）")

    all_fails: dict[str, list[str]] = {}
    tool_err: list[str] = []
    ran = 0
    for t in targets:
        rc, payload, raw = _humanize_invoke(tool, rubric, t, gate=True)
        if payload is None:
            tool_err.append(f"{t.name} → 校验器未产出可解析 JSON（exit={rc}）：{raw.strip()[:120]}")
            continue
        ran += 1
        for h in payload.get("fail") or []:
            all_fails.setdefault(str(h.get("id")), []).append(
                f"{t.name}:L{h.get('line')} {h.get('snippet', '')}")
    if tool_err:
        fail(HUMANIZE_KEY, "；".join(tool_err))
        return

    fidelity_fail: dict = {}
    if diff_pair is not None:
        rc, payload, raw = _humanize_invoke(tool, rubric, None, diff=diff_pair)
        if payload is None:
            fail(HUMANIZE_KEY, f"保真比对未产出可解析 JSON（exit={rc}）：{raw.strip()[:120]}")
            return
        fidelity_fail = payload or {}

    blocked = {k: v for k, v in all_fails.items() if k not in exempt}
    stale = [k for k in exempt if k not in all_fails]

    msgs: list[str] = []
    if blocked:
        items = "；".join(f"{k}（{len(v)} 处）" for k, v in sorted(blocked.items()))
        sample = "；".join(v[0] for _, v in sorted(blocked.items()))
        msgs.append(f"实跑 FAIL={sum(len(v) for v in blocked.values())} 处，未清零不得交付：{items}。"
                    f"样例：{sample[:200]}")
    if fidelity_fail:
        cats = "；".join(f"{c} 缺失={d.get('缺失')} 新增={d.get('新增')}"
                        for c, d in fidelity_fail.items())
        msgs.append(f"**事实保真 FAIL**（硬约束、**不可豁免**）：{cats}")
    if msgs:
        fail(HUMANIZE_KEY, "｜".join(msgs)[:400])
    else:
        note = (f"verdict={verdict}；实跑 {ran} 个产物 / 判据集 {rubric.name} / 适用范围『{scope[:40]}』"
                + (f"；豁免 {len(exempt)} 条已放行" if exempt else ""))
        ok(HUMANIZE_KEY, note)

    # 保真层暴露率（与审美判据的渲染层/刻度层注记同构）——「没测」必须与「通过」可区分。
    if diff_pair is None:
        warn("文风判据保真层", "未登记 `改写前`/`改写后` —— **事实保真本次未检测**，不是通过。"
                               "去味改写的双条件之一是「保真零丢失」，它需要两份文本才能机器判。"
                               "要覆盖该层：把改写前的稿与本轮定稿各存一份，在块内写 "
                               "`改写前: <路径>` / `改写后: <路径>`。")
    else:
        ok("文风判据保真层", "已登记改写前后 → `--diff-fidelity` 实跑"
                             + ("（零丢失、零新增）" if not fidelity_fail else "（有差异，见上）"))

    if exempt:
        trace = "；".join(f"{k}=『{v}』" for k, v in exempt.items())
        if stale:
            warn("文风判据豁免", f"本次实跑并未 FAIL、却被豁免的判据：{'、'.join(stale)} —— "
                                 f"豁免项长期闲置应收回（否则它会从「有理由的例外」退化成橡皮图章）。"
                                 f"现存豁免：{trace}")
        else:
            ok("文风判据豁免", f"{len(exempt)} 条（留痕：{trace}）")


def _check_category_decl(skill_dir: Path) -> None:
    """入口判定主类：① 声明块（确定性 → FAIL）② 疑似列扫描（启发式 → WARN）。

    阴性对照（验收用，**判据换了必须重做夹具** —— 旧的"表头/绕过"夹具对本案无效）：
      (a) 块内 `code` → `codex`，或 `**chat**` → `**Chat**`（大小写）→ 必须 FAIL；
      (b) 块内**新增一行** `| **image** | … |` → 必须 FAIL 且文案含 `image`；
      (c) 删掉 `end` 标记（或让标记出现两次）→ 必须 FAIL（"读不到块"不得静默降级为绿）；
      (d) **块外**（如 `SKILL.md`）新插一张含 `image` 的主类表 → 确定性项**必须仍绿**、
          启发式项**必须出 WARN** —— 这是"两半各司其职"的证明，**别再宣称块外能 FAIL**；
      (e) 块内无取值 / 第 2 行不是分隔行 → 必须 FAIL（块形是本判据的机器接口）；
      (f) 块内**首格连写/多值**（`| **chat** / **image** |`）→ 必须 FAIL（"块形不合法"）；
      (g) 块内**首格为空**（`|  | **image** |`）→ 必须 FAIL（空首格不是裸词）。
          这是**本轮补的**：此前该写法只被 `_norm_cell` 读到 `chat`、第二个取值静默丢失
          （独立复核 c13 实测）。**阴性对照**：撤掉 `_p_category_decl` 的裸词约束，(f) 必须
          转绿 —— 否则说明该夹具空转。
    """
    label = "口径守卫：入口判定主类"
    item_scan = "口径守卫：入口判定主类扫描（启发式·WARN）"
    want = set(VALID_CATEGORY)
    texts: list[tuple[str, str]] = []
    for p in _resolve_sources(skill_dir, CATEGORY_SOURCES):
        try:
            if p.exists():
                texts.append((p.name, p.read_text(encoding="utf-8")))
        except OSError:
            pass
    if not texts:
        fail(label, "源集合一个文件都读不到（守卫读不到规则 = 没有规则）")
        return
    per = []
    for name, t in texts:
        ls = [l.strip() for l in t.splitlines()]
        per.append((name, ls.count(_DECL_BEGIN), ls.count(_DECL_END)))
    nb = sum(x[1] for x in per)
    ne = sum(x[2] for x in per)
    if nb != 1 or ne != 1:
        where = "、".join(f"{n}(begin {b}/end {e})" for n, b, e in per if b or e) or "无"
        fail(label, f"声明块标记须在**源规格面内各恰 1 处**（源规格＝`CATEGORY_SOURCES`，不递归）：实测 begin={nb}、end={ne}｜出现处：{where}"
                    "｜（第二处声明应改成「引用」：用反引号把标记包起来，不要让它单独成行）")
    else:
        holder = next(n for n, b, _e in per if b)
        src = next(t for n, t in texts if n == holder)
        try:
            got = _p_category_decl(src)
        except _DeclError as exc:
            fail(label, f"声明块解析失败：{exc}｜块形是本判据的机器接口，改块形须同步改判据")
        else:
            if got != want:
                fail(label, f"声明块（{holder}）取值得 {sorted(got)} ≠ 代码常量 {sorted(want)}"
                            "（同一物理量两处不同源 —— 要么统一，要么显式声明二者关系）")
            else:
                ok(label, f"声明块（{holder}，源规格面内须恰 1 处）↔ 代码常量 "
                          f"{'/'.join(sorted(want))}（{len(want)} 项一致）")
    hits: list[str] = []
    for name, t in texts:
        hits += _scan_category_tables(t, want, name)
    if hits:
        warn(item_scan, f"疑似未登记的取值 {len(hits)} 处 —— **只提示不阻断**，请人审："
                        + "；".join(hits[:8]) + ("…" if len(hits) > 8 else ""))
    else:
        ok(item_scan, f"源集合 {len(texts)} 个文件未见「主类疑似列」含未登记取值"
                      "（启发式按列裸词占比判定，会漏会误，**不作门禁**）")


def _check_cleanup(meta: dict, plan_path: Path | None = None) -> None:
    """v4.10.0：meta.清理 —— 任务产物清理登记（阶段 6 第 7 条 / 检查项 23）。

    与 `_check_entry_verdict` / `_check_aesthetic` 同源口径：
      * 整段缺省 → **WARN**（向后兼容旧 plan，**不追认历史计划** —— 不拿新判据改写旧证据）
      * 非映射 / 缺必填项 / `状态` 越界 / 计数项为负或非整数 → **FAIL**
      * 登记了 `清单` 却解析不到文件 → **FAIL**（"登记了就必须到位"，同 `_check_aesthetic`
        的渲染色口径：声明了就不能静默退回"未检测"）

    ⚠️ **它不是门禁**：`状态` 由执行者填写，机器只校验**结构**与**清单文件是否存在**。
       「确实安全清过」「这个该不该清」不在射程内 —— 与「用户放行」字段同一处诚实边界
       （可自填的字段不是门禁，只能提高伪造成本）。
    """
    v = meta.get(CLEANUP_KEY, None)
    if not v:
        _absent("meta.清理",
                "未记录 —— 阶段 6 第 7 条（任务产物清理）本应产出。"
                "**L2 必填**：v4.14.0 起整段缺省**直接判 FAIL**（不再 WARN）。本项只判「有没有落盘」，**不"
                "判判得对不对**（校准无机器 oracle）。若本计划确属 L1，请显式写 `meta.任务层级: L1` —— 那样只"
                "汇成一条 SKIP，不判缺口。", meta)
        return
    if not isinstance(v, dict):
        fail("meta.清理 合法", f"应为映射，实际 {type(v).__name__}")
        return
    bad: list[str] = []
    for k in CLEANUP_REQUIRED:
        if not str(v.get(k, "") or "").strip():
            bad.append(f"缺『{k}』或为空")
    st = str(v.get("状态", "") or "").strip()
    if st and st not in CLEANUP_STATES:
        bad.append(f"状态=『{st}』（只允许 {'/'.join(CLEANUP_STATES)}）")
    for k in CLEANUP_COUNT_KEYS:
        n = v.get(k, None)
        if n is None:
            continue
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            bad.append(f"{k}={n!r}（须为非负整数）")
    man = str(v.get(CLEANUP_MANIFEST_KEY, "") or "").strip()
    if man and plan_path is not None:
        cand = Path(man)
        if not cand.is_absolute():
            cand = plan_path.parent / man
        if not cand.is_file():
            bad.append(f"清单『{man}』不存在（登记了就必须解析到位：{cand}）")
    if bad:
        fail("meta.清理 合法", "；".join(bad[:3]))
    else:
        ok("meta.清理 合法", f"状态={st}（**留痕，非门禁**；结构合法不代表清得干净）")


def _check_cram(meta: dict, plan_path: Path | None = None) -> None:
    """v4.19.0：meta.恶补 —— 知识点恶补报告登记（阶段 6 第 4 条 / 检查项 27）。

    背景：v4.18.1 把「每个 L2 收尾都出恶补报告」写成**提示层纪律**（本机无「强制总是执行」档位），
    changelog 已如实登记「不新增 plan 字段、不新增 judge、不新增 checks.py 判据」。实测遵守率
    取决于模型记不记得 —— 10-07 多个 L2 收尾未出、也无任何痕迹。本条把它从「无声」抬到「可见」。

    ⚠️ **缺省只 WARN，不判 FAIL**（与 `_check_aesthetic` 同源口径，**刻意不同于** `_check_cleanup`）：
      · 恶补是**条件性产出** —— 确无值得记的知识点时可合法不产出，属「未涉及」而非「缺口」；
      · 设「L2 缺省即 FAIL」会让全工作区（含他线）每个 L2 任务**回溯判红**，并迫使空任务
        写橡皮图章（`状态: 无知识点` 变成形式主义）。诚实边界：**漏报（该出没出）首版机器抓不到**，
        机器只让「登记了的」可判。
      · L1 直接 SKIP（恶补报告属 L2 全流程产出，L1 未做不算缺口）。

    一旦登记则**必须结构合法**：
      · 非映射 / 缺必填项 / `状态` 越界 → **FAIL**
      · `状态: 已出` 时：`项目名` 与 `报告` 必填；`报告` 须能解析到真实文件；且路径须落在
        `恶补/` 目录下（用户 2026-10-07 硬约束：报告只落 `<工作区根>/恶补/<项目名>/<年-月>/`）
        —— 任一条不满足即 **FAIL**（"登记了就必须到位"，同 `_check_cleanup` 的清单口径）

    ⚠️ **它不是质量门禁**：不判报告内容好不好、对不对（校准无机器 oracle），只判「有没有落盘」
    与「归档位置是否守约」。
    """
    v = meta.get(CRAM_KEY, None)
    if not v:
        if _tier_is_l1(meta):
            skip("meta.恶补",
                 "本计划已声明 L1 —— 知识点恶补报告属 L2 全流程产出，L1 未做**不算缺口**"
                 "（是「未涉及」，不是「已通过」）")
        else:
            warn("meta.恶补",
                 "未登记 —— 阶段 6 第 4 条（知识点恶补报告，v4.18.1 起挂载）本应产出。"
                 "**本项首版只 WARN**（不阻断、不回溯打断既有任务）：恶补是**条件性产出**，"
                 "确无知识点可合法不产出，故未设「L2 缺省即 FAIL」。⚠️ WARN ≠ 通过 —— 它是"
                 "「这次没做、也没说明」，不是「做过且没问题」。若本就无需出，请显式登记 "
                 "`状态: 无知识点`（+ `理由`），让「确实没有」与「忘了做」在留痕上可区分。"
                 "示例：\n    " + CRAM_KEY + ":\n      状态: 已出\n"
                 "      项目名: <本任务所属项目（归档分区）>\n"
                 "      报告: <工作区根>/" + CRAM_ARCHIVE_ROOT + "/<项目名>/<年-月>/xxx_恶补报告.pdf")
        return
    if not isinstance(v, dict):
        fail("meta.恶补 合法", f"应为映射（含 {'/'.join(CRAM_REQUIRED)}），实际 {type(v).__name__}")
        return
    bad: list[str] = []
    for k in CRAM_REQUIRED:
        if not str(v.get(k, "") or "").strip():
            bad.append(f"缺『{k}』或为空")
    st = str(v.get("状态", "") or "").strip()
    if st and st not in CRAM_STATES:
        bad.append(f"状态=『{st}』（只允许 {'/'.join(CRAM_STATES)}）")
    if bad:
        fail("meta.恶补 合法", "；".join(bad[:3]))
        return
    if st == "已出":
        proj = str(v.get(CRAM_PROJECT_KEY, "") or "").strip()
        rep = str(v.get(CRAM_REPORT_KEY, "") or "").strip()
        if not proj:
            fail("meta.恶补 合法",
                 f"状态=已出 时必须写『{CRAM_PROJECT_KEY}』（归档按项目名分层，无项目名 = 无归档分区）")
            return
        if not rep:
            fail("meta.恶补 合法", f"状态=已出 时必须写『{CRAM_REPORT_KEY}』（归档产物路径）")
            return
        cands: list[Path] = []
        cp = Path(rep)
        if cp.is_absolute():
            cands.append(cp)
        elif plan_path is not None:
            cands.append(plan_path.parent / rep)                     # 相对任务目录
            cands.append(plan_path.parent.parent.parent / rep)       # 相对工作区根（tasks/<任务> → 工作区根）
        found = next((c for c in cands if c.is_file()), None)
        if found is None:
            where = "；".join(str(c) for c in cands) if cands else rep
            fail("meta.恶补 合法",
                 f"报告『{rep}』解析不到真实文件（登记了就必须到位：{where}）")
            return
        if CRAM_ARCHIVE_ROOT not in Path(rep).parts:
            fail("meta.恶补 合法",
                 f"报告路径『{rep}』不含『{CRAM_ARCHIVE_ROOT}』目录段 —— 归档硬约束：报告**只落** "
                 f"`<工作区根>/{CRAM_ARCHIVE_ROOT}/<项目名>/<年-月>/` 一处（用户 2026-10-07 指定）")
            return
        ok("meta.恶补 合法",
           f"状态=已出，项目名={proj}，报告已归档（**只校验存在与归档位置，不判内容质量**）")
    else:
        reason = str(v.get(CRAM_REASON_KEY, "") or "").strip()
        tail = f"；理由={reason}" if reason else "（未写 `理由` —— 建议补，便于人审）"
        ok("meta.恶补 合法",
           f"状态={st}（**留痕，非门禁**；'确实没有值得记的' 靠人审{tail}）")


def _check_stage_gates(steps: list) -> None:
    """阶段 2 / 4 的两条最低成本门禁（v3.5.0 / P2-2）：**只出 WARN**。

    背景（《报告》§5.3）：门禁密度实测 —— 阶段 2 与阶段 4 均为 **0 门禁**，而这两处恰是
    「决策质量的关键节点」与技能自认「最容易静默失真」处。原因不是"不该有"，是"没人去建"。

    ⚠️ **诚实标注（三条限制，别当成已验证的保护）**：
      ① 步骤没有"阶段"字段，故此处用**代理判据**（关键词 / 交付物后缀）推断它属哪一阶段；
      ② 它检的是**验证方式里有没有对应信号词**，不是"数值真的一致"—— 能挡住"忘了写"，挡不住"写了没做"；
      ③ **首版只 WARN、不判 FAIL**：判据尚未经受真实数据检验，直接上 FAIL 会造出随机 FAIL 源
         （security-guide.md §九 末条：门禁出问题绝大多数是**误判**而非漏判）。
    """
    g2, g4 = [], []
    for s in steps:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id", "?"))
        do = str(s.get("做什么", "") or "")
        ver = str(s.get("验证方式", "") or "")
        exp = str(s.get("预期产出", "") or "")
        deliv = str(s.get("交付物", "") or "").lower()
        if STAGE2_STEP_RE.search(do) and not STAGE2_SIGNAL_RE.search(ver + " " + exp):
            g2.append(sid)
        if any(e in deliv for e in STAGE4_EXT) and not STAGE4_SIGNAL_RE.search(ver):
            g4.append(sid)
    if g2:
        warn("阶段 2 门禁（方案评审 ≥2 候选）",
             f"步骤 {'、'.join(g2)} 提到方案评审，但「验证方式/预期产出」里读不到「≥2 候选」的可判定信号"
             f" —— 补信号，或写明为何只有一条路（本判据首版只 WARN）")
    if g4:
        warn("阶段 4 门禁（数值口径 / 估算标注 / 脱敏）",
             f"步骤 {'、'.join(g4)} 产出 Office 类交付物，但「验证方式」里读不到口径一致 / 估算标注 / "
             f"写回读回 / 脱敏类信号 —— 这三条正是流程自认最易静默失真处（本判据首版只 WARN）")

def _check_model_tiers(steps: list) -> None:
    """校验每步 `模型档位` 的取值（P9-c，v3.4.0）。

    与 `_check_autonomy` / `_check_selftools` **同口径**：字段可选，**留空即合法**；
    但一旦填了，就必须在 `VALID_MODEL_TIERS` 内 —— 否则"填了"只是装饰，无法参与成本核对。

    ⚠️ 为什么把 `default` 收进合法集而不是改写历史 plan：真实数据（v3.2.0 的 plan.yaml）里
    就有 `default`。改历史记录去迁就新门禁，等于**为新判据篡改证据**；正解是把 `default`
    定义为「显式声明按阶段默认档位」并写进 `plan-template.yaml` 与 `routing-guide.md`，
    让**文档与实际用法一致**。门禁只拦真正的越界值（如拼错的 `cheep`、`fast`）。
    """
    bad, seen = [], []
    for i, s in enumerate(steps, 1):
        if not isinstance(s, dict):
            continue
        v = str(s.get("模型档位", "") or "").strip()
        if not v:
            continue
        seen.append(v)
        if v not in VALID_MODEL_TIERS:
            bad.append(f"步骤 {s.get('id', i)}={v!r}")
    if bad:
        fail("模型档位合法", "非法取值：" + "；".join(bad) + f"（合法：{'/'.join(VALID_MODEL_TIERS)}；留空=跳过）")
    else:
        ok("模型档位合法", f"{len(seen)} 步已标注，取值均在 enum 内" if seen else "步骤均未标注（字段可选）")

def _check_irreversible(meta: dict, steps: list) -> None:
    """U5：不可逆副作用登记 —— **可选字段，填了就必须合法**。

    口径沿用 `_check_autonomy` / `_check_selftools`：不强制填空，填了就不能糊弄。
      * 命中不可逆关键词却留空 → **SKIP**（"是否该有副作用"无法机器判断，不做 FAIL ——
        逼执行者编造比留空更糟）
      * 登记项缺 `可否回滚`，或取值越界 → **FAIL**
    """
    items = meta.get("不可逆副作用") or []
    if not isinstance(items, list):
        fail("meta.不可逆副作用 合法", f"应为列表，实际 {type(items).__name__}")
        return
    if not items:
        blob = " ".join(str(s.get(k, "") or "") for s in steps
                        for k in ("做什么", "交付物", "验证方式"))
        hit = [h for h in IRREVERSIBLE_HINT if h in blob]
        if hit:
            skip("meta.不可逆副作用",
                 f"步骤文本命中不可逆关键词（{'、'.join(hit[:3])}）但本字段留空"
                 f" —— 需人工确认是否该登记（不 FAIL：无法机器判断「是否该有副作用」）")
        return
    bad = []
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict):
            bad.append(f"第 {i} 项应为映射")
            continue
        v = str(it.get("可否回滚", "") or "").strip()
        if not v:
            bad.append(f"第 {i} 项缺『可否回滚』（未知必须显式写，空值不等于『应该没问题』）")
        elif v not in ("可回滚", "不可回滚", "未知"):
            bad.append(f"第 {i} 项『可否回滚』=『{v}』（只允许 可回滚/不可回滚/未知）")
    if bad:
        fail("meta.不可逆副作用", "；".join(bad[:3]))
    else:
        ok("meta.不可逆副作用", f"登记 {len(items)} 项，合法")

def _check_user_release(meta: dict) -> None:
    """U2：用户放行留痕 —— **非门禁**，只提高伪造成本。

    ⚠️ 本字段做不到真正的机器强制（执行者可自填）。字段注释与 SKILL.md 都必须
    原样保留这一事实，否则就是造「看起来有门禁其实没有」的假安全感 —— 比不做更糟。
    """
    # 适用范围：L2 全量；**L1 可省**（命中模板即跳过追问循环，无独立放行环节 —— 清单 §2.3）
    if str(meta.get("任务层级", "") or "").strip() == "L1":
        return
    items = meta.get("用户放行") or []
    if not isinstance(items, list):
        fail("meta.用户放行 合法", f"应为列表，实际 {type(items).__name__}")
        return
    if not items:
        skip("meta.用户放行", "未记录 —— 本字段**不是门禁**（可自填，机器无法强制），留空只作提示")
        return
    bad = []
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict):
            bad.append(f"第 {i} 项应为映射")
            continue
        for k in ("时间", "摘要"):
            if not str(it.get(k, "") or "").strip():
                bad.append(f"第 {i} 项缺『{k}』")
    if bad:
        fail("meta.用户放行", "；".join(bad[:3]))
    else:
        ok("meta.用户放行", f"登记 {len(items)} 项（**留痕，非门禁**）")

def _check_entry_verdict(meta: dict) -> None:
    """v4.2.0：meta.入口判定 —— **可选字段，填了就必须合法**。

    口径与 `_check_user_release` / `_check_reflection_retry` 同源：
      * 整段缺省 → **WARN**（向后兼容旧 plan，**不追认历史计划** ——
        不拿新判据改写旧证据）
      * 非映射 / 缺必填项 / 取值越界 → **FAIL**

    ⚠️ **它不是门禁**：`confidence` 由模型自填，**校准无法被机器证明**。
    本函数只做"结构合法"这一层；"类别选对了没"不在此判据射程内
    （类型合法 ≠ 判断正确）。依据与原文见 references/self-judge.md §10。
    """
    v = meta.get(ENTRY_KEY, None)
    if not v:
        _absent("meta.入口判定",
                "未记录 —— 阶段 0 第 1 步（self-judge）本应产出。"
                "**L2 必填**：v4.14.0 起整段缺省**直接判 FAIL**（不再 WARN）。本项只判「有没有落盘」，**不"
                "判判得对不对**（校准无机器 oracle）。若本计划确属 L1，请显式写 `meta.任务层级: L1` —— 那样只"
                "汇成一条 SKIP，不判缺口。", meta)
        return
    if not isinstance(v, dict):
        fail("meta.入口判定 合法", f"应为映射，实际 {type(v).__name__}")
        return
    bad = []
    for k in ENTRY_REQUIRED:
        if k not in v or (not isinstance(v[k], (int, float, bool)) and not v[k]):
            bad.append(f"缺『{k}』或为空")
    cat = str(v.get("category", "") or "").strip()
    if cat and cat not in VALID_CATEGORY:
        bad.append(f"category=『{cat}』（只允许 {'/'.join(VALID_CATEGORY)}）")
    conf = v.get("confidence", None)
    if conf is not None:
        if isinstance(conf, bool) or not isinstance(conf, (int, float)):
            bad.append(f"confidence={conf!r}（须为 0–1 的数）")
        elif not 0.0 <= float(conf) <= 1.0:
            bad.append(f"confidence={conf!r}（越界，须在 0–1）")
    amb = v.get("ambiguity", None)
    if amb is not None and not isinstance(amb, bool):
        bad.append(f"ambiguity={amb!r}（须为 bool）")
    dist = v.get("distribution", None)
    if isinstance(dist, dict):
        if set(dist) != set(VALID_CATEGORY):
            bad.append(f"distribution 键={sorted(dist)}（须恰为 {sorted(VALID_CATEGORY)}）")
        else:
            nums = [float(x) for x in dist.values()
                    if isinstance(x, (int, float)) and not isinstance(x, bool)]
            if len(nums) != len(VALID_CATEGORY):
                bad.append("distribution 含非数值项")
            elif abs(sum(nums) - 1.0) > 1e-6:
                bad.append(f"distribution 之和={sum(nums):.4f}（须为 1）")
    elif dist is not None:
        bad.append(f"distribution 应为映射，实际 {type(dist).__name__}")
    dims = v.get("dimensions", None)
    if isinstance(dims, dict):
        miss_d = [d for d in ENTRY_DIMS if d not in dims]
        if miss_d:
            bad.append(f"dimensions 缺 {'/'.join(miss_d)}")
    elif dims is not None:
        bad.append(f"dimensions 应为映射，实际 {type(dims).__name__}")
    sec = v.get("secondary", None)
    if sec not in (None, "") and str(sec).strip() not in VALID_CATEGORY:
        bad.append(f"secondary=『{sec}』（留空或在 {'/'.join(VALID_CATEGORY)} 内）")
    if bad:
        fail("meta.入口判定 合法", "；".join(bad[:3]))
    else:
        ok("meta.入口判定 合法", f"category={cat}（**留痕，非门禁**；结构合法不代表判对）")

def _check_method_select(meta: dict) -> None:
    """v4.4.0：meta.方法选用 —— **可选字段，填了就必须合法**。

    与 `_check_entry_verdict` 同源口径：整段缺省/空列表 → WARN（向后兼容旧 plan，
    不追认历史计划）；应为**列表（每步一条判定）**，非列表/缺必填项/取值越界 → FAIL。
    ⚠️ **它不是门禁**：`confidence` 由模型自填，校准无法机器强制；
    "选了工具"≠"工具对"（类型合法 ≠ 判断正确）。契约见 references/method-judge.md §10。
    """
    v = meta.get(METHOD_KEY, None)
    if v is None or (isinstance(v, list) and not v):
        _absent("meta.方法选用",
                "未记录 —— 阶段 3 第②步（method-judge）。**L2 必须落盘（v4.14.0 契约变更）**："
                "各步都要写下选用的工具／方法，**含显式否定结论** —— 该步不必引入工具也要写成"
                "`needs_tool: false`：「这一步不必引入工具」是**结论**，不是免写理由。"
                "缺省即 FAIL；一旦填写则必须结构合法，非法亦 FAIL。"
                "本项只判有无与结构，**不判选得对不对**（见 references/method-judge.md §10）。", meta)
        return
    # 单映射（过渡期偶发）归一化为 1 元素列表，便于统一校验
    entries = v if isinstance(v, list) else [v]
    if not isinstance(v, list):
        warn("meta.方法选用 形态", "应为列表（每步一条），检测到单映射已按 1 条处理；"
             "建议改为「方法选用: []」后逐条追加")

    bad = []
    for i, e in enumerate(entries, 1):
        if not isinstance(e, dict):
            bad.append(f"第{i}项非映射")
            continue
        for k in METHOD_REQUIRED:
            if k not in e or (not isinstance(e[k], (int, float, bool)) and not e[k]):
                bad.append(f"第{i}项缺『{k}』或为空")
        gc = str(e.get("gap_class", "") or "").strip()
        if gc:
            parts = [p.strip() for p in gc.split("+")]
            if any(p not in METHOD_GAP_CLASSES for p in parts):
                bad.append(f"第{i}项 gap_class=『{gc}』（只允许 {'/'.join(METHOD_GAP_CLASSES)} 及其 '+' 组合）")
        nt = e.get("needs_tool", None)
        if nt is not None and not isinstance(nt, bool):
            bad.append(f"第{i}项 needs_tool={nt!r}（须为 bool）")
        conf = e.get("confidence", None)
        if conf is not None:
            if isinstance(conf, bool) or not isinstance(conf, (int, float)):
                bad.append(f"第{i}项 confidence={conf!r}（须为 0–1 的数）")
            elif not 0.0 <= float(conf) <= 1.0:
                bad.append(f"第{i}项 confidence={conf!r}（越界，须在 0–1）")
        cand = e.get("candidates", None)
        if isinstance(cand, list):
            for j, c in enumerate(cand):
                if not isinstance(c, dict) or "tool" not in c:
                    bad.append(f"第{i}项 candidates[{j}] 缺『tool』")
                    continue
                fs = c.get("fit_score", None)
                if fs is None or isinstance(fs, bool) or not isinstance(fs, (int, float)):
                    bad.append(f"第{i}项 candidates[{j}].fit_score 须为 0–1 的数")
                elif not 0.0 <= float(fs) <= 1.0:
                    bad.append(f"第{i}项 candidates[{j}].fit_score 越界")
        elif cand is not None:
            bad.append(f"第{i}项 candidates 应为列表，实际 {type(cand).__name__}")
        rh = e.get("route_hint", None)
        if rh is not None and not str(rh).strip():
            bad.append(f"第{i}项 route_hint 为空")
    if bad:
        fail("meta.方法选用 合法", "；".join(bad[:3]))
    else:
        _need = sum(1 for e in entries if isinstance(e, dict) and e.get("needs_tool") is True)
        ok("meta.方法选用 合法",
           f"{len(entries)} 条（needs_tool=true {_need} 条；**留痕，非门禁**；结构合法不代表选对工具）")

def _check_method_select_sample(meta: dict) -> None:
    """v4.4.0：方法选用的**抽样人审信号** —— 非门禁，只指路。

    契约 §10 把「工具选用 ↔ 人工复核**一致率**」列为**人审**信号：机器能指出"该抽样看哪里"
    （哪些条目值得复核），但**不能代替复核**，也无法机器判定"选得对不对"。故本项只出
    **WARN**（无需抽样时出 OK），**永不计入 FAIL、不改退出码**。

    抽样池 = `needs_tool=true` 的条目（真正引入了外部手段，复核杠杆最高）∪ `confidence`
    低于自采信带 `METHOD_SAMPLE_BAND` 的条目（§5 的"复核带"）。
    与 `_check_autonomy` 的「方法选用↔决策记录」一致性 WARN 互补：那条查**有没有留痕**，
    这条提示**留痕里选得对不对需人抽验**。
    ⚠️ 未证实前只说「**一致率**」，**不声称「准确率」** —— 与 §10 原样一致。
    """
    v = meta.get(METHOD_KEY)
    if not isinstance(v, list) or not v:
        return  # 无留痕 → 无可抽样项（"缺省"由检查项 14 的 WARN 覆盖，此处不重复提示）
    pool: list[str] = []
    for i, e in enumerate(v, 1):
        if not isinstance(e, dict):
            continue
        nt = e.get("needs_tool") is True
        conf = e.get("confidence")
        mid = (isinstance(conf, (int, float)) and not isinstance(conf, bool)
               and float(conf) < METHOD_SAMPLE_BAND)
        if nt or mid:
            why = "引入外部手段" if nt else ""
            if mid:
                why = (why + "；" if why else "") + f"confidence={conf}<{METHOD_SAMPLE_BAND}"
            pool.append(f"第{i}条（{why}）")
    if not pool:
        ok("方法选用抽样人审",
           "无待抽样条目（均 needs_tool=false 且 confidence 达自采信带）—— 机器未指路，非门禁")
        return
    k = min(2, len(pool))
    warn("方法选用抽样人审",
         f"{len(pool)} 条待复核，建议抽 {k} 条人工核验：" + "、".join(pool[:k])
         + ("…" if len(pool) > k else "")
         + " —— 核对所选手段是否真解决了 gap_class 所述缺口。"
           "**这是「一致率」抽样，不是「准确率」验证**；机器只指路，判定靠人（契约 §10）。**非门禁**。")

def _check_retrieval_verdict(meta: dict) -> None:
    """v4.5.0：meta.检索判定 —— **可选字段，填了就必须合法**。

    与 `_check_entry_verdict` / `_check_method_select` 同源口径：整段缺省 / 空列表 → **WARN**
    （向后兼容旧 plan，**不追认历史计划**）；应为**列表（每次检索一条）**，非列表 / 缺必填项 /
    取值越界 → **FAIL**。

    ⚠️ **它不是门禁**：`confidence` 由模型自填，校准无法机器强制；**「未检索」与「不存在」的
    区分同样无法机器强制** —— 机器只能校验字段结构，不能校验那句"没有"背后是否真查过。
    契约见 references/retrieval-judge.md §10。
    """
    v = meta.get(RETRIEVAL_KEY, None)
    if v is None or (isinstance(v, list) and not v):
        _absent("meta.检索判定",
                "未记录 —— 阶段 3 第 5 条之前（retrieval-judge）。**L2 必须落盘（v4.14.0 契约变更）**："
                "确需检索的自然要写下；**确不需检索的也要写下否定结论**（`needs_retrieval: false` /"
                "「本任务无需检索」）—— 否则「该记未记」与「本就无需记」机器不可区分。"
                "缺省即 FAIL；一旦填写则必须结构合法，非法亦 FAIL。"
                "本项只判有无与结构，**不判检索得对不对**（见 references/retrieval-judge.md §10）。", meta)
        return
    # 单映射（过渡期偶发）归一化为 1 元素列表，便于统一校验
    entries = v if isinstance(v, list) else [v]
    if not isinstance(v, list):
        warn("meta.检索判定 形态", "应为列表（每次检索一条），检测到单映射已按 1 条处理；"
             "建议改为「检索判定: []」后逐条追加")

    bad = []
    for i, e in enumerate(entries, 1):
        if not isinstance(e, dict):
            bad.append(f"第{i}项非映射")
            continue
        for k in RETRIEVAL_REQUIRED:
            if k not in e or (not isinstance(e[k], (int, float, bool)) and not e[k]):
                bad.append(f"第{i}项缺『{k}』或为空")
        sc = str(e.get("source_class", "") or "").strip()
        if sc:
            parts = [p.strip() for p in sc.split("+")]
            if any(p not in RETRIEVAL_SOURCE_CLASSES for p in parts):
                bad.append(f"第{i}项 source_class=『{sc}』"
                           f"（只允许 {'/'.join(RETRIEVAL_SOURCE_CLASSES)} 及其 '+' 组合）")
        nr = e.get("needs_retrieval", None)
        if nr is not None and not isinstance(nr, bool):
            bad.append(f"第{i}项 needs_retrieval={nr!r}（须为 bool）")
        conf = e.get("confidence", None)
        if conf is not None:
            if isinstance(conf, bool) or not isinstance(conf, (int, float)):
                bad.append(f"第{i}项 confidence={conf!r}（须为 0–1 的数）")
            elif not 0.0 <= float(conf) <= 1.0:
                bad.append(f"第{i}项 confidence={conf!r}（越界，须在 0–1）")
        cand = e.get("candidates", None)
        if isinstance(cand, list):
            for j, c in enumerate(cand):
                if not isinstance(c, dict) or "source" not in c:
                    bad.append(f"第{i}项 candidates[{j}] 缺『source』")
                    continue
                fs = c.get("fit_score", None)
                if fs is None or isinstance(fs, bool) or not isinstance(fs, (int, float)):
                    bad.append(f"第{i}项 candidates[{j}].fit_score 须为 0–1 的数")
                elif not 0.0 <= float(fs) <= 1.0:
                    bad.append(f"第{i}项 candidates[{j}].fit_score 越界")
        elif cand is not None:
            bad.append(f"第{i}项 candidates 应为列表，实际 {type(cand).__name__}")
        rh = e.get("route_hint", None)
        if rh is not None and not str(rh).strip():
            bad.append(f"第{i}项 route_hint 为空")
    if bad:
        fail("meta.检索判定 合法", "；".join(bad[:3]))
    else:
        _need = sum(1 for e in entries if isinstance(e, dict) and e.get("needs_retrieval") is True)
        ok("meta.检索判定 合法",
           f"{len(entries)} 条（needs_retrieval=true {_need} 条；**留痕，非门禁**；结构合法不代表查全）")

def _check_retrieval_sample(meta: dict) -> None:
    """v4.5.0：检索判定的**抽样人审信号** —— 非门禁，只指路。

    契约 §10 把「源类选择 ↔ 人工复核**一致率**」与「否定断言的检索范围是否属实」列为
    **人审**信号：机器能指出"该抽样看哪里"（哪些条目值得复核），但**不能代替复核**，
    也无法机器判定"查得够不够"。故本项只出 **WARN**（无需抽样时出 OK），
    **永不计入 FAIL、不改退出码**。

    抽样池 = `needs_retrieval=true` 的条目（真正发起了检索，复核杠杆最高）∪ `confidence`
    低于自采信带 `RETRIEVAL_SAMPLE_BAND` 的条目（§5 的"复核带"）。
    ⚠️ 未证实前只说「**一致率**」，**不声称「准确率」** —— 与 §10 原样一致。
    """
    v = meta.get(RETRIEVAL_KEY)
    if not isinstance(v, list) or not v:
        return  # 无留痕 → 无可抽样项（"缺省"由检查项 16 的 WARN 覆盖，此处不重复提示）
    pool: list[str] = []
    for i, e in enumerate(v, 1):
        if not isinstance(e, dict):
            continue
        nr = e.get("needs_retrieval") is True
        conf = e.get("confidence")
        mid = (isinstance(conf, (int, float)) and not isinstance(conf, bool)
               and float(conf) < RETRIEVAL_SAMPLE_BAND)
        if nr or mid:
            why = "发起了检索" if nr else ""
            if mid:
                why = (why + "；" if why else "") + f"confidence={conf}<{RETRIEVAL_SAMPLE_BAND}"
            pool.append(f"第{i}条（{why}）")
    if not pool:
        ok("检索判定抽样人审",
           "无待抽样条目（均 needs_retrieval=false 且 confidence 达自采信带）—— 机器未指路，非门禁")
        return
    k = min(2, len(pool))
    warn("检索判定抽样人审",
         f"{len(pool)} 条待复核，建议抽 {k} 条人工核验：" + "、".join(pool[:k])
         + ("…" if len(pool) > k else "")
         + " —— 核对①所选源类是否真覆盖缺口 ②若下了否定断言，其检索范围是否属实。"
           "**这是「一致率」抽样，不是「准确率」验证**；机器只指路，判定靠人（契约 §10）。**非门禁**。")

def _check_homework_verdict(meta: dict) -> None:
    """v4.7.0：meta.作业判定 —— **可选字段，填了就必须合法**（homework-judge 的产出）。

    口径与 `_check_entry_verdict` 同源：整段缺省 → **WARN**（向后兼容旧 plan，
    **不追认历史计划**）；非映射 / 缺必填项 / 取值越界 → **FAIL**。

    ⚠️ **它不是门禁**：`confidence` 由模型自填、校准无法机器证明；本函数只做"结构合法 +
    **派生字段自洽**"这一层（"模式选对了没"不在射程内）。

    ⭐ **本项比另三份 judge 多一条机器判据（刻意加的）**：`needs_homework` 是 `mode` 的**派生值**，
    故"两者矛盾"是**确定性错误**（不是判断分歧）—— 矛盾即 FAIL。`method-judge` 的
    `needs_tool=false` 与 `gap_class=事实` 自相矛盾正是**只能事后识别**的那类问题；
    本模块从设计上不给出矛盾的机会，再把"不得矛盾"落成判据。
    """
    v = meta.get(HOMEWORK_KEY, None)
    if not v:
        _absent("meta.作业判定",
                "未记录 —— 阶段 0 作业识别（homework-judge）本应产出。"
                "**L2 必填**：v4.14.0 起整段缺省**直接判 FAIL**（不再 WARN）。本项只判「有没有落盘」，**不"
                "判判得对不对**（校准无机器 oracle）。若本计划确属 L1，请显式写 `meta.任务层级: L1` —— 那样只"
                "汇成一条 SKIP，不判缺口。", meta)
        return
    if not isinstance(v, dict):
        fail("meta.作业判定 合法", f"应为映射，实际 {type(v).__name__}")
        return
    bad = []
    for k in HOMEWORK_REQUIRED:
        if k not in v or (not isinstance(v[k], (int, float, bool)) and not v[k]):
            bad.append(f"缺『{k}』或为空")
    mode = str(v.get("mode", "") or "").strip()
    if mode:
        parts = [p.strip() for p in mode.split("+")]
        if any(p not in HOMEWORK_MODES for p in parts):
            bad.append(f"mode=『{mode}』（只允许 {'/'.join(HOMEWORK_MODES)} 及其 '+' 组合）")
        elif len(parts) != len(set(parts)):
            # ⭐ v4.7.0 补：`_combine` 只会把**两个不同**模式并列，故重复项是确定性错误
            bad.append(f"mode=『{mode}』组合串含重复项（组合应是**不同**模式的并列）")
    conf = v.get("confidence", None)
    if conf is not None:
        if isinstance(conf, bool) or not isinstance(conf, (int, float)):
            bad.append(f"confidence={conf!r}（须为 0–1 的数）")
        elif not 0.0 <= float(conf) <= 1.0:
            bad.append(f"confidence={conf!r}（越界，须在 0–1）")
    amb = v.get("ambiguity", None)
    if amb is not None and not isinstance(amb, bool):
        bad.append(f"ambiguity={amb!r}（须为 bool）")
    dist = v.get("distribution", None)
    dist_top = None
    if isinstance(dist, dict):
        if set(dist) != set(HOMEWORK_MODES):
            bad.append(f"distribution 键={sorted(dist)}（须恰为 {sorted(HOMEWORK_MODES)}）")
        else:
            nums = []
            for k, x in dist.items():
                if isinstance(x, bool) or not isinstance(x, (int, float)):
                    bad.append(f"distribution[{k}]={x!r}（须为数值）")
                    continue
                # ⭐ v4.7.0 补：**各项 ∈ [0,1]** —— 只校验"和 = 1"时**负概率可以配平通过**
                #   （如 {作业题:1.5, 讲解题:-0.4, 非作业:-0.1} 和恰为 1）。该漏网已实测复现。
                if not 0.0 <= float(x) <= 1.0:
                    bad.append(f"distribution[{k}]={x}（须在 0–1；负概率与 >1 均非法）")
                nums.append(float(x))
            if len(nums) != len(HOMEWORK_MODES):
                bad.append("distribution 含非数值项")
            elif abs(sum(nums) - 1.0) > 1e-6:
                bad.append(f"distribution 之和={sum(nums):.4f}（须为 1）")
            if nums:
                dist_top = max(nums)
    elif dist is not None:
        bad.append(f"distribution 应为映射，实际 {type(dist).__name__}")

    # ⭐ confidence 的派生自洽（v4.7.0 补，与下方 needs_homework **同型**）：
    #   契约 §5.1 定义 `confidence = max(distribution)` ⇒ 二者不等是**确定性不一致**，非判断分歧。
    #   容差 1e-3 **不是**放宽：distribution 落盘是 4 位小数，量化误差量级 ≤ 2e-4；
    #   若用 1e-6，纯噪声会被判成漂移（真漂移如 0.99 vs 0.42 差 0.57，远在容差外）。
    if dist_top is not None and isinstance(conf, (int, float)) and not isinstance(conf, bool):
        if abs(float(conf) - dist_top) > 1e-3:
            bad.append(f"confidence={conf} ≠ max(distribution)={dist_top:.4f}"
                       f"（派生值，§5.1 定义为分布最大值）")

    dims = v.get("dimensions", None)
    if isinstance(dims, dict):
        miss_d = [d for d in HOMEWORK_DIMS if d not in dims]
        if miss_d:
            bad.append(f"dimensions 缺 {'/'.join(miss_d)}")
        for d in HOMEWORK_DIMS:
            if d not in dims:
                continue
            x = dims[d]
            # ⭐ v4.7.0 补：**值域 0–1**（契约 §3 的 W1–W5 是 0–1 分）——原先只校验键齐
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                bad.append(f"dimensions[{d}]={x!r}（须为数值）")
            elif not 0.0 <= float(x) <= 1.0:
                bad.append(f"dimensions[{d}]={x}（越界，须在 0–1）")
    elif dims is not None:
        bad.append(f"dimensions 应为映射，实际 {type(dims).__name__}")
    # ⭐ 派生字段自洽（确定性判据，见 docstring）
    nh = v.get("needs_homework", None)
    if nh is not None:
        if not isinstance(nh, bool):
            bad.append(f"needs_homework={nh!r}（须为 bool：它是 mode 的派生值）")
        elif mode:
            expect = mode.split("+")[0].strip() == "作业题"
            if nh is not expect:
                bad.append(f"needs_homework={nh} 与 mode=『{mode}』矛盾"
                           f"（派生值应为主模式 === 『作业题』⇒ {expect}）")
    if bad:
        # 判据已增至 8 条，只显示前 3 条会把真正的第一因截掉；显示前 4 并**报出总数**
        fail("meta.作业判定 合法",
             "；".join(bad[:4]) + (f"（…等 {len(bad)} 项）" if len(bad) > 4 else ""))
    else:
        ok("meta.作业判定 合法",
           f"mode={mode}（**留痕，非门禁**；结构合法不代表判对 —— 见 references/homework-judge.md §10）")

def _check_homework_sample(meta: dict) -> None:
    """v4.7.0：作业判定的**抽样人审信号** —— 非门禁，只指路。

    抽样池（复核杠杆最高的两类）：① `mode` 为**组合态**（说明 top2 接近，判定本身不稳）
    ② `confidence` 低于自采信带 `HOMEWORK_SAMPLE_BAND`。**永不计入 FAIL、不改退出码。**

    复核三问（写进提示，机器不代替人做）：① 模式选得对吗（作业题／讲解题／非作业）
    ② **W5 有没有被忽略** —— 简单题被套上完整五阶段即违反效率项 ③ W4 高时是否真给了诚信提示。
    ⚠️ 未证实前只说「**一致率**」，**不声称「准确率」**。
    """
    v = meta.get(HOMEWORK_KEY)
    if not isinstance(v, dict) or not v:
        return  # 无留痕 → 无可抽样项（缺省由检查项 18 的 WARN 覆盖）
    mode = str(v.get("mode", "") or "").strip()
    conf = v.get("confidence")
    reasons = []
    if "+" in mode:
        reasons.append(f"mode=『{mode}』（组合态，top2 接近）")
    if isinstance(conf, (int, float)) and not isinstance(conf, bool) and float(conf) < HOMEWORK_SAMPLE_BAND:
        reasons.append(f"confidence={conf}<{HOMEWORK_SAMPLE_BAND}")
    if v.get("ambiguity") is True:
        reasons.append("ambiguity=true（契约 §5 要求先澄清）")
    if not reasons:
        ok("作业判定抽样人审",
           "无待抽样条目（单模式、confidence 达自采信带、非模糊）—— 机器未指路，非门禁")
        return
    warn("作业判定抽样人审",
         "建议人工复核本任务作业判定：" + "；".join(reasons)
         + " —— 复核三问：①模式选对否 ②W5 有没有被忽略（简单题不该套完整五阶段）"
           "③W4 高时是否真给了诚信提示。**这是「一致率」抽样，不是「准确率」验证**；"
           "机器只指路，判定靠人（契约 §10）。**非门禁**。")

def _check_learning_verdict(meta: dict) -> None:
    """v4.8.0：meta.学习判定 —— **可选字段，填了就必须合法**（learning-judge 的产出）。

    口径与 `_check_entry_verdict` / `_check_homework_verdict` 同源：整段缺省 → **WARN**
    （向后兼容旧 plan，**不追认历史计划**）；非映射 / 缺必填项 / 取值越界 → **FAIL**。

    ⚠️ **它不是门禁**：`confidence` 由模型自填、校准无法机器证明；本函数只做"结构合法 +
    **派生字段自洽**"这一层（"这条值不值得学"不在射程内）。

    ⭐ **两条确定性判据（与 `homework-judge` 同款，且是"算错"不是"判断分歧"）**：
      ① `needs_learning` 是 `kind` 的**派生值**，矛盾即 FAIL；
      ② **`无` 不得参与 `A+B` 组合** —— "没有"与"有"并列无意义，故属确定性非法。
    """
    v = meta.get(LEARNING_KEY, None)
    if not v:
        _absent("meta.学习判定",
                "未记录 —— 阶段 6 收尾（learning-judge）本应产出。"
                "**L2 必填**：v4.14.0 起整段缺省**直接判 FAIL**（不再 WARN）。本项只判「有没有落盘」，**不"
                "判判得对不对**（校准无机器 oracle）。若本计划确属 L1，请显式写 `meta.任务层级: L1` —— 那样只"
                "汇成一条 SKIP，不判缺口。", meta)
        return
    if not isinstance(v, dict):
        fail("meta.学习判定 合法", f"应为映射，实际 {type(v).__name__}")
        return
    bad = []
    for k in LEARNING_REQUIRED:
        if k not in v or (not isinstance(v[k], (int, float, bool)) and not v[k]):
            bad.append(f"缺『{k}』或为空")
    kind = str(v.get("kind", "") or "").strip()
    if kind:
        parts = [p.strip() for p in kind.split("+")]
        if any(p not in LEARNING_KINDS for p in parts):
            bad.append(f"kind=『{kind}』（只允许 {'/'.join(LEARNING_KINDS)} 及其 '+' 组合）")
        elif len(parts) != len(set(parts)):
            bad.append(f"kind=『{kind}』组合串含重复项（组合应是**不同**类型的并列）")
        elif "无" in parts and len(parts) > 1:
            # ⭐ v4.8.0：`无` 不得参与组合 —— "没有"与"有"并列无意义，属确定性非法
            bad.append(f"kind=『{kind}』：『无』不得参与组合（它表示「本任务无可学信号」，不能与有并列）")
    conf = v.get("confidence", None)
    if conf is not None:
        if isinstance(conf, bool) or not isinstance(conf, (int, float)):
            bad.append(f"confidence={conf!r}（须为 0–1 的数）")
        elif not 0.0 <= float(conf) <= 1.0:
            bad.append(f"confidence={conf!r}（越界，须在 0–1）")
    amb = v.get("ambiguity", None)
    if amb is not None and not isinstance(amb, bool):
        bad.append(f"ambiguity={amb!r}（须为 bool）")
    dist = v.get("distribution", None)
    dist_top = None
    if isinstance(dist, dict):
        if set(dist) != set(LEARNING_KINDS):
            bad.append(f"distribution 键={sorted(dist)}（须恰为 {sorted(LEARNING_KINDS)}）")
        else:
            nums = []
            for k, x in dist.items():
                if isinstance(x, bool) or not isinstance(x, (int, float)):
                    bad.append(f"distribution[{k}]={x!r}（须为数值）")
                    continue
                # 同作业判定：只校验"和 = 1"时**负概率可以配平通过**（如 {偏好:1.5, …:-0.5}）
                if not 0.0 <= float(x) <= 1.0:
                    bad.append(f"distribution[{k}]={x}（须在 0–1；负概率与 >1 均非法）")
                nums.append(float(x))
            if len(nums) != len(LEARNING_KINDS):
                bad.append("distribution 含非数值项")
            elif abs(sum(nums) - 1.0) > 1e-6:
                bad.append(f"distribution 之和={sum(nums):.4f}（须为 1）")
            if nums:
                dist_top = max(nums)
    elif dist is not None:
        bad.append(f"distribution 应为映射，实际 {type(dist).__name__}")

    # confidence 的派生自洽（契约 §5.1 定义 `confidence = max(distribution)`）
    # 容差 1e-3 不是放宽：落盘是 4 位小数，量化误差量级 ≤ 2e-4
    if dist_top is not None and isinstance(conf, (int, float)) and not isinstance(conf, bool):
        if abs(float(conf) - dist_top) > 1e-3:
            bad.append(f"confidence={conf} ≠ max(distribution)={dist_top:.4f}"
                       f"（派生值，§5.1 定义为分布最大值）")

    dims = v.get("dimensions", None)
    if isinstance(dims, dict):
        miss_d = [d for d in LEARNING_DIMS if d not in dims]
        if miss_d:
            bad.append(f"dimensions 缺 {'/'.join(miss_d)}")
        for d in LEARNING_DIMS:
            if d not in dims:
                continue
            x = dims[d]
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                bad.append(f"dimensions[{d}]={x!r}（须为数值）")
            elif not 0.0 <= float(x) <= 1.0:
                bad.append(f"dimensions[{d}]={x}（越界，须在 0–1）")
    elif dims is not None:
        bad.append(f"dimensions 应为映射，实际 {type(dims).__name__}")

    # ⭐ 派生字段自洽（确定性判据，见 docstring）
    nl = v.get("needs_learning", None)
    if nl is not None:
        if not isinstance(nl, bool):
            bad.append(f"needs_learning={nl!r}（须为 bool：它是 kind 的派生值）")
        elif kind:
            expect = kind.split("+")[0].strip() != "无"
            if nl is not expect:
                bad.append(f"needs_learning={nl} 与 kind=『{kind}』矛盾"
                           f"（派生值应为主类型 ≠『无』⇒ {expect}）")
    # 可选计数字段（由 kb_learn.py commit 回填，供"学习真的发生了"对账）
    for ck in ("入库", "候选"):
        cv = v.get(ck, None)
        if cv is None:
            continue
        if isinstance(cv, bool) or not isinstance(cv, int) or cv < 0:
            bad.append(f"{ck}={cv!r}（须为非负整数）")
    if bad:
        fail("meta.学习判定 合法",
             "；".join(bad[:4]) + (f"（…等 {len(bad)} 项）" if len(bad) > 4 else ""))
    else:
        ok("meta.学习判定 合法",
           f"kind={kind}（**留痕，非门禁**；结构合法不代表判对 —— 见 references/learning-judge.md §10）")

def _check_learning_sample(meta: dict) -> None:
    """v4.8.0：学习判定的**抽样人审信号** —— 非门禁，只指路。

    抽样池（复核杠杆最高的三类）：① `kind` 为**组合态**（top2 接近，判定本身不稳）
    ② `confidence` 低于自采信带 `LEARNING_SAMPLE_BAND` ③ `ambiguity=true`。
    **永不计入 FAIL、不改退出码。**

    复核三问（写进提示，机器不代替人做）：① 类型选得对吗（四类之一，还是应判『无』）
    ② **V5 稳定性有没有被忽略** —— 时效性事实不该进 KB（应记工作区 memory）
    ③ 若已入库，`入库` / `候选` 计数与实际 KB 文档数是否对得上。
    ⚠️ 未证实前只说「**一致率**」，**不声称「准确率」**。
    """
    v = meta.get(LEARNING_KEY)
    if not isinstance(v, dict) or not v:
        return  # 无留痕 → 无可抽样项（缺省由检查项 20 的 WARN 覆盖）
    kind = str(v.get("kind", "") or "").strip()
    conf = v.get("confidence")
    reasons = []
    if "+" in kind:
        reasons.append(f"kind=『{kind}』（组合态，top2 接近）")
    if isinstance(conf, (int, float)) and not isinstance(conf, bool) and float(conf) < LEARNING_SAMPLE_BAND:
        reasons.append(f"confidence={conf}<{LEARNING_SAMPLE_BAND}")
    if v.get("ambiguity") is True:
        reasons.append("ambiguity=true（契约 §5 要求留池观察，不得自动入库）")
    if not reasons:
        ok("学习判定抽样人审",
           "无待抽样条目（单类型、confidence 达自采信带、非模糊）—— 机器未指路，非门禁")
        return
    warn("学习判定抽样人审",
         "建议人工复核本任务学习判定：" + "；".join(reasons)
         + " —— 复核三问：①类型选对否（还是应判『无』）②V5 稳定性有没有被忽略"
           "（时效性事实不该进 KB，应记工作区 memory）③入库/候选计数与 KB 文档数对不对得上。"
           "**这是「一致率」抽样，不是「准确率」验证**；机器只指路，判定靠人（契约 §10）。**非门禁**。")

def _check_thinking_verdict(meta: dict) -> None:
    """v4.11.0：检查项 24 —— `meta.思考判定` 结构合法 + **D 系列跨字段自洽**（thinking-judge 的产出）。

    口径与既有快判检查项同源：**L2／层级不明 ⇒ 整段缺省判 FAIL**（v4.14.0 起，用户 2026-09-28 拍板）；**L1 出口**：显式声明 `meta.任务层级: L1` ⇒ 汇总为**一条 SKIP**（「不算缺口」）；
    字段存在但非法 → **FAIL**。⚠️「没填」≠「填错了」（设计 §3.9 判据纪律第 2 条）。

    ⚠️ **它不是门禁** —— `confidence` / `veto` 由模型自填，机器只能校验**结构合法与跨字段自洽**
    （**类型合法 ≠ 判得对**，见 `references/thinking-panel.md` §9）。价值观判定**无机器 oracle**。

    ⭐ **本函数覆盖 D1–D11、D14–D19 与 D20–D22（共 20 条），刻意不含 D12 / D13** —— 那两条的**靶面不在
    `plan.yaml` 里**（契约 §5.3 明列）：D12 读 `thinking-gold.yaml` 的 `provenance`/`anchors_fitted`
    与一致率报表，D13 读 `thinking_model agree --report` 的分母。它们的机器落点是
    `thinking_model.py` 的 `selftest` / `gold`（同为可复跑的机器判据），**不是**本检查项 ——
    ⛔ 不得据此声称「检查项 24 覆盖了全部 19 条」（**文档说全、实现只做一半**正是本项目最忌的形态）。

    ⭐ **D7 / D9 是「底线不可加权稀释」的结构约束**（内核 N2）：`拒绝` 不得作 `distribution` 的键、
    `T5` 不得进 `dimensions` —— 二者同源，堵的是同一条退化路径的两条支路。
    """
    v = meta.get(THINKING_KEY, None)
    if not v:
        _absent("meta.思考判定",
                "未记录 —— 阶段 0 第 0 步（thinking-judge）本应产出。"
                "**L2 必填**：v4.14.0 起整段缺省**直接判 FAIL**（不再 WARN）。本项只判「有没有落盘」，**不"
                "判判得对不对**（校准无机器 oracle）。若本计划确属 L1，请显式写 `meta.任务层级: L1` —— 那样只"
                "汇成一条 SKIP，不判缺口。", meta)
        return
    if not isinstance(v, dict):
        fail("meta.思考判定 合法", f"应为映射，实际 {type(v).__name__}")
        return

    bad = []
    # ---- D17：veto.triggered / suspect 必须是布尔（缺失/null ⇒ fail-open）----
    # 先做：它决定后续 derive 语义（suspect 缺失会被 derive rule 2 读成 false ⇒ 中间带静默放行）
    veto = v.get("veto", None)
    if not isinstance(veto, dict):
        bad.append(f"veto 应为映射，实际 {type(veto).__name__}（D17 要求 triggered/suspect 为布尔）")
        veto = {}
    for bk in ("triggered", "suspect"):
        if not isinstance(veto.get(bk), bool):
            bad.append(f"veto.{bk}={veto.get(bk)!r}（须为布尔；缺失/null 会让 derive 读成 false"
                       f" ⇒ 中间带违规静默放行，D17）")

    # ---- 必填 12 项（缺即 FAIL；`laya` 允许为 null）----
    for k in THINKING_REQUIRED:
        if k not in v:
            bad.append(f"缺必填『{k}』")

    # ---- verdict ----
    verdict = str(v.get("verdict", "") or "").strip()
    if verdict not in THINKING_VERDICTS:
        bad.append(f"verdict=『{verdict}』（只允许 {'/'.join(THINKING_VERDICTS)}）")

    # ---- D6 / D7：distribution ----
    dist = v.get("distribution", None)
    dist_top = None
    if isinstance(dist, dict):
        if "拒绝" in dist:
            bad.append("distribution 含『拒绝』键（D7：否决层不得并入分布 —— 底线不可加权稀释）")
        if set(dist) != set(THINKING_DIST_KEYS):
            bad.append(f"distribution 键={sorted(dist)}（须恰为 {sorted(THINKING_DIST_KEYS)}）")
        nums = []
        for k, x in dist.items():
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                bad.append(f"distribution[{k}]={x!r}（须为数值）")
                continue
            if not 0.0 <= float(x) <= 1.0:
                bad.append(f"distribution[{k}]={x}（须在 0–1；负概率与 >1 均非法）")
            nums.append(float(x))
        if len(nums) == len(dist):
            if abs(sum(nums) - 1.0) > 1e-6:
                bad.append(f"distribution 之和={sum(nums):.4f}（须为 1）")
            if nums:
                dist_top = max(nums)
    elif dist is not None:
        bad.append(f"distribution 应为映射，实际 {type(dist).__name__}")

    # ---- D6 派生自洽：confidence == max(distribution)（容差 1e-3，落盘 4 位小数量化误差 ≤2e-4）----
    conf = v.get("confidence", None)
    if isinstance(conf, bool) or not isinstance(conf, (int, float)):
        bad.append(f"confidence={conf!r}（须为 0–1 的数）")
    elif not 0.0 <= float(conf) <= 1.0:
        bad.append(f"confidence={conf!r}（越界，须在 0–1）")
    elif dist_top is not None and abs(float(conf) - dist_top) > 1e-3:
        bad.append(f"confidence={conf} ≠ max(distribution)={dist_top:.4f}（D6：派生值）")

    # ---- D8 / D9：dimensions ----
    dims = v.get("dimensions", None)
    if isinstance(dims, dict):
        if "T5" in dims:
            bad.append("dimensions 含『T5』（D9：否决层不得降格为维度分，与 D7 同源）")
        miss_d = [d for d in THINKING_DIMS if d not in dims]
        if miss_d:
            bad.append(f"dimensions 缺 {'/'.join(miss_d)}（D8）")
        for d in THINKING_DIMS:
            if d not in dims:
                continue
            x = dims[d]
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                bad.append(f"dimensions[{d}]={x!r}（须为数值）")
            elif not 0.0 <= float(x) <= 1.0:
                bad.append(f"dimensions[{d}]={x}（越界，须在 0–1）")
    elif dims is not None:
        bad.append(f"dimensions 应为映射，实际 {type(dims).__name__}")

    # ---- D11：旁证不得进 dimensions / distribution（只留痕）----
    for pk in THINKING_PROBE_KEYS:
        if isinstance(dims, dict) and pk in dims:
            bad.append(f"旁证『{pk}』出现在 dimensions（D11：旁证不作依据）")
        if isinstance(dist, dict) and pk in dist:
            bad.append(f"旁证『{pk}』出现在 distribution（D11）")

    # ---- amendments（D3 / D4 / D18 的公共前提）----
    ambs = v.get("amendments", None)
    if ambs is None:
        bad.append("amendments 缺失（须为列表；无修正时为空表）")
        ambs = []
    elif not isinstance(ambs, list):
        bad.append(f"amendments 应为列表，实际 {type(ambs).__name__}")
        ambs = []
    else:
        for i, a in enumerate(ambs):
            if not isinstance(a, dict):
                bad.append(f"amendments[{i}] 应为映射，实际 {type(a).__name__}")
                continue
            side = a.get("越线性")
            if side not in THINKING_AMEND_SIDES:
                bad.append(f"amendments[{i}].越线性={side!r}（须为 {'/'.join(THINKING_AMEND_SIDES)}）")

    if verdict == "修正" and not ambs:
        bad.append("verdict=修正 而 amendments 为空（D3：裁决与修正案不符）")
    if verdict == "接受" and ambs:
        bad.append(f"verdict=接受 而 amendments 非空（{len(ambs)} 条）（D4：有修正案却按原样做）")

    # ---- D18：澄清态携带修正案 ⇒ needs_human_confirm 必须为 true ----
    nhc = v.get("needs_human_confirm", None)
    if not isinstance(nhc, bool):
        bad.append(f"needs_human_confirm={nhc!r}（须为 bool）")
    elif verdict == "澄清" and ambs and nhc is not True:
        bad.append("verdict=澄清 且 amendments 非空 而 needs_human_confirm≠true"
                   "（D18：触界修正案随澄清静默带出）")

    # ---- D1 / D2 / D5 / D10 / D14：轴与拒绝路径 ----
    trig = veto.get("triggered")
    axis = str(veto.get("axis", "") or "").strip()
    if trig is True:
        if verdict != "拒绝":
            bad.append(f"veto.triggered=true 而 verdict=『{verdict}』（D1：否决层被绕过）")
        if axis not in THINKING_VETO_AXES:
            bad.append(f"veto.triggered=true 而 axis=『{axis}』（D5：须 ∈ {'/'.join(THINKING_VETO_AXES)}）")
        elif axis == "A6" and not str(veto.get("underlying_axis", "") or "").strip():
            bad.append("axis=A6（元轴）而 underlying_axis 缺失/空（D5：A6 不得当『实质轴不明』的垃圾桶）")
    elif trig is False:
        if verdict == "拒绝":
            bad.append("verdict=拒绝 而 veto.triggered≠true（D2：无依据的拒绝）")
        if axis not in THINKING_AXIS_EMPTY:
            bad.append(f"veto.triggered=false 而 axis=『{axis}』（D10：无违规却挂罪名，须为空/无）")

    if verdict == "拒绝":
        for fk, lbl in (("alternative", "替代方向"), ("appeal_hint", "申诉指引")):
            if not str(veto.get(fk, "") or "").strip():
                bad.append(f"verdict=拒绝 而 {fk} 为空白（D14：拒绝不可申诉 —— {lbl}必填）")

    # ---- D15：判定权不外流（内核 N1）----
    mj = str(v.get("main_judge", "") or "").strip()
    if mj != "A":
        bad.append(f"main_judge=『{mj}』（D15：定稿恒为 A —— 判定权不得外流）")

    # ---- D16：影子对照必须跑 multilingual（Router 只看 state）----
    laya = v.get("laya", None)
    if laya is not None and not isinstance(laya, dict):
        bad.append(f"laya 应为映射或 null，实际 {type(laya).__name__}")
    elif isinstance(laya, dict):
        st = str(laya.get("status", "") or "").strip()
        if st not in THINKING_LAYASTATUS:
            bad.append(f"laya.status=『{st}』（须 ∈ {'/'.join(THINKING_LAYASTATUS)}）")
        elif st == "ok" and str(laya.get("model_key", "") or "").strip() != THINKING_PINNED_MODEL:
            bad.append(f"laya.status=ok 而 model_key=『{laya.get('model_key')}』≠ {THINKING_PINNED_MODEL}"
                       f"（D16：影子对照跑错了模型 ⇒ 对照无效却被当成有效）")

    # ---- D19：band 与 confidence 同源 ----
    band = str(v.get("band", "") or "").strip()
    if band not in THINKING_BANDS:
        bad.append(f"band=『{band}』（须 ∈ {'/'.join(THINKING_BANDS)}）")
    elif isinstance(conf, (int, float)) and not isinstance(conf, bool):
        amb = v.get("ambiguity", None)
        lo, hi = THINKING_SAMPLE_BAND
        if amb is True or float(conf) < lo:
            expect_band = THINKING_BANDS[2]
        elif float(conf) >= hi:
            expect_band = THINKING_BANDS[0]
        else:
            expect_band = THINKING_BANDS[1]
        if band != expect_band:
            bad.append(f"band=『{band}』≠ f(confidence={conf}, ambiguity={amb})={expect_band}"
                       f"（D19：置信档与置信度不同源）")

    # ---- 基础类型 ----
    if not isinstance(v.get("ambiguity", None), bool):
        bad.append(f"ambiguity={v.get('ambiguity')!r}（须为 bool）")
    if not str(v.get("route_hint", "") or "").strip():
        bad.append("route_hint 为空（须给出处理指引，§3.2 route_hint 对应表）")

    # ---- D20 / D21 / D22：前提审计（v4.22.0 新增子块，挂在 meta.思考判定 下，契约 §5.6）----
    # 承载用户 2026-10-08 指定的回复口径要求里「既有面未覆盖」的三项：
    #   P1 前提审计 / P3 来源核实 / P5 遗漏提醒。另两项（P2 不迎合·独立判断、P4 直陈依据）
    #   **由既有面覆盖**（四态『修正/拒绝』+ amendments[].依据 + D3/D4/D14），故不重复登记 ——
    #   新增判据若与既有面重叠，会让既有的阴性对照恒判假绿（项目纪律）。
    # ⭐ 接入策略 = **软启动**（沿用 v4.11.0 的 thinking-judge 先例）：**缺省只 WARN**，
    #   以兼容存量 plan（实测两个工作区根合计 56 个任务目录、多为 L2；缺省即 FAIL 会让
    #   全量历史 plan 回归新增大量 FAIL）；**一旦填写则结构/自洽非法即 FAIL**。
    #   ⚠️ WARN ≠ 通过 —— 它是「这次没填」，不是「填过且没问题」（同 meta.恶补 的口径）。
    pa = v.get("前提审计", None)
    if pa is None:
        pass                                   # 缺省 → 末尾只 WARN（软启动）
    elif not isinstance(pa, dict):
        bad.append(f"前提审计 应为映射，实际 {type(pa).__name__}（D22）")
    else:
        for _k in ("前提", "来源核实", "遗漏提醒"):
            if _k not in pa:
                bad.append(f"缺前提审计子键『{_k}』（D22：三键齐备）")
        # D20：裁决与前提审计自洽 ——「接受」= 按原样做，不得同时登记着未消解的前提问题
        qian = pa.get("前提", None)
        if qian is not None and not isinstance(qian, list):
            bad.append(f"前提审计.前提 应为列表，实际 {type(qian).__name__}（D22）")
        elif isinstance(qian, list) and qian and verdict == "接受":
            bad.append(f"verdict=接受 而 前提审计.前提 非空（{len(qian)} 项）（D20：说前提有问题却按原样做"
                       f" —— 与 D4 同族，堵同一条退化路径的另一条支路）")
        # D21：来源核实 fail-closed —— 声称需要核实，就必须留下「已核实」或「未核实」的痕迹
        src = pa.get("来源核实", None)
        if src is not None and not isinstance(src, dict):
            bad.append(f"前提审计.来源核实 应为映射，实际 {type(src).__name__}（D22）")
        elif isinstance(src, dict):
            need = src.get("需要核实", None)
            if not isinstance(need, bool):
                bad.append(f"前提审计.来源核实.需要核实={need!r}（D22：须为布尔 —— 缺失/null 会被静默读成"
                           f" false ⇒ fail-open，与 D17 同源）")
            elif need and not (src.get("已核实") or []) and not (src.get("未核实") or []):
                bad.append("前提审计.来源核实.需要核实=true 而 已核实/未核实 均为空"
                           "（D21：声称要核实却什么都没记 —— fail-closed）")
        miss = pa.get("遗漏提醒", None)
        if miss is not None and not isinstance(miss, list):
            bad.append(f"前提审计.遗漏提醒 应为列表，实际 {type(miss).__name__}（D22）")

    if bad:
        fail("meta.思考判定 合法",
             "；".join(bad[:4]) + (f"（…等 {len(bad)} 项）" if len(bad) > 4 else ""))
    else:
        ok("meta.思考判定 合法",
           f"verdict=『{verdict}』band={band}（**留痕，非门禁**；类型合法 ≠ 判得对"
           f" —— 见 references/thinking-panel.md §9）")
        if pa is None:
            warn("meta.思考判定.前提审计",
                 "未登记 —— v4.22.0 新增子块（前提审计 / 来源核实 / 遗漏提醒）。**本项首版只 WARN**"
                 "（软启动，兼容 v4.22.0 之前创建的存量 plan）：新计划应从 assets/plan-template.yaml 的模板"
                 "或 `thinking_model.to_yaml_block` 带上该子块；**一旦填写，结构/自洽非法即 FAIL**（D20–D22）。"
                 "⚠️ WARN ≠ 通过 —— 它是「这次没填」，不是「填过且没问题」。契约见 references/thinking-panel.md §5.6。")

def _check_thinking_sample(meta: dict) -> None:
    """v4.11.0：检查项 25 —— 思考判定的**抽样人审指路**（非门禁，只指路）。

    抽样池（复核杠杆最高的五类）：
      ① `verdict == 拒绝`（**过拒审计** —— C22②；本模块选「宁严不宽」，过拒是首要观测对象）
      ② `veto.suspect == true` 或 `ambiguity == true`（中间带：derive 把它推给了澄清）
      ③ `band == 低` 或 `confidence < THINKING_SAMPLE_BAND[1]`（低置信）
      ④ `needs_human_confirm == true`（触界修正案待人工确认）
      ⑤ `laya.status != "ok"`（本次无对照 —— 暴露率）
    **永不计入 FAIL、不改退出码**（与检查项 19/21 同款）。

    复核三问：① 目标/前提/约束/路径的读数与实际相符否；② 若拒绝，是真违规还是过拒
    （A1–A6 无 oracle，只能人审）；③ 一致率分母是否干净（只含人工标 ∩ Laya-ok）。
    ⚠️ 未拟合前只说「**一致率**」，**不声称「准确率」**。
    """
    v = meta.get(THINKING_KEY, None)
    if not isinstance(v, dict) or not v:
        return  # 无留痕 → 无可抽样项（缺省由检查项 24 的 WARN 覆盖）
    verdict = str(v.get("verdict", "") or "").strip()
    veto = v.get("veto") if isinstance(v.get("veto"), dict) else {}
    conf = v.get("confidence")
    band = str(v.get("band", "") or "").strip()
    laya = v.get("laya") if isinstance(v.get("laya"), dict) else None
    reasons = []
    if verdict == "拒绝":
        reasons.append("verdict=拒绝（过拒审计 —— 「宁严不宽」的首要观测对象，C22②）")
    if veto.get("suspect") is True:
        reasons.append("veto.suspect=true（中间带：noul 在模糊带内，derive 推给了澄清）")
    if v.get("ambiguity") is True:
        reasons.append("ambiguity=true（信息不足/歧义）")
    if isinstance(conf, (int, float)) and not isinstance(conf, bool) \
            and float(conf) < THINKING_SAMPLE_BAND[1] and band != THINKING_BANDS[2]:
        reasons.append(f"confidence={conf}<{THINKING_SAMPLE_BAND[1]}（中置信）")
    if band == THINKING_BANDS[2]:
        reasons.append("band=低（置信档最低）")
    if v.get("needs_human_confirm") is True:
        reasons.append("needs_human_confirm=true（触界修正案待人工确认）")
    if laya is not None and str(laya.get("status", "") or "").strip() != "ok":
        reasons.append(f"laya.status={laya.get('status')}（本次无有效对照 —— 报暴露率，不并入分母）")
    if not reasons:
        ok("思考判定抽样人审",
           "无待抽样条目（非拒绝/非模糊/置信达档/有有效对照）—— 机器未指路，非门禁")
        return
    warn("思考判定抽样人审",
         "建议人工复核本任务思考判定：" + "；".join(reasons)
         + " —— 复核三问：①目标/前提/约束/路径的读数与实际相符否 ②若拒绝，是真违规还是过拒"
           "（A1–A6 无 oracle，只能人审）③一致率分母是否干净（只含人工标 ∩ Laya-ok）。"
           "**这是「一致率」抽样，不是「准确率」验证**；机器只指路，判定靠人（契约 §9）。**非门禁**。")

def _check_reflection_retry(meta: dict, steps: list) -> None:
    """v4.1.0：反思重试配置 —— **可选块，整段缺省即 SKIP（向后兼容）**。

    口径沿用「可选字段、填了就不能糊弄」：整段（meta + 步骤级覆盖均）缺省＝关闭自动重试，
    旧 plan 不受影响；一旦 meta 或某步骤填了，就校验结构合法（最大重试次数整数 ≥1 /
    触发条件为 T1-T3 子集 / 终止策略在枚举内）。**语义**（"重试是否真的改了什么"）无法
    机器判定，靠抽查。
    """
    cfg = meta.get("反思重试配置", None)
    bad = []
    if cfg:
        bad += _validate_reflect_block(cfg, "meta.反思重试配置")
    # 步骤级覆盖：模板口径「不写则用 meta，写了只对本步生效」—— 即便 meta 无配置，
    # 单步也可独立声明自己的重试策略，故同样校验（不依赖 meta 是否存在）。
    step_overrides = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        ov = s.get("反思重试", None)
        if ov:
            step_overrides.append((s.get("id", "?"), ov))
    if not cfg and not step_overrides:
        skip("meta.反思重试配置", "未配置（含步骤级覆盖）—— 旧 plan 或显式关闭自动重试（不影响判定）")
        return
    for sid, ov in step_overrides:
        bad += _validate_reflect_block(ov, f"步骤 {sid}.反思重试")
    if bad:
        fail("meta.反思重试配置 合法", "；".join(bad[:3]))
    else:
        ok("meta.反思重试配置 合法", "配置结构合法（语义靠抽查，非门禁）")

def _check_closure(steps: list[dict], plan_path: Path, meta: dict) -> None:
    """E′：完成态 = 状态 + trace + 沉淀登记（验证方式由 PLAN_STEP_REQUIRED 覆盖）。"""
    done = [s for s in steps if str(s.get("状态", "")).strip() == "完成"]
    if not done:
        skip("步骤闭环不变量", "无已完成步骤")
        return

    trace_path = _task_dir(plan_path) / "trace.jsonl"
    if not trace_path.exists():
        warn("步骤闭环不变量（trace 自证）",
             f"{len(done)}/{len(steps)} 步已完成但无 trace.jsonl —— 复盘只能靠回忆，"
             f"且本次是否沉淀无法自证。{_TRACE_HINT}")
        return

    ids, actions = _read_trace(trace_path)
    if not actions:
        warn("步骤闭环不变量（trace 自证）", f"trace.jsonl 存在但 0 条记录。{_TRACE_HINT}")
        return

    miss = [str(s.get("id", "?")) for s in done if str(s.get("id", "?")) not in ids]
    if miss:
        fail("步骤闭环不变量（trace 自证）",
             f"本任务已启用 trace，但 {len(miss)} 个完成步骤无记录：{','.join(miss[:10])}"
             f"{'…' if len(miss) > 10 else ''}。{_TRACE_HINT}")
    else:
        ok("步骤闭环不变量（trace 自证）", f"{len(done)} 个完成步骤均有 trace 记录")

    # M-1′：零沉淀须**显式登记**。hermes 原文：a pass that does nothing is a missed
    # learning opportunity, **not a neutral outcome** —— 空转通过等于漏掉一次学习。
    noted = str(meta.get("复盘沉淀", "") or "").strip()
    learned = any(any(tok in a for tok in SEDIMENT_TOKENS) for a in actions)
    if noted or learned:
        pieces = []
        if noted:
            pieces.append("meta.复盘沉淀 已登记")
        if learned:
            pieces.append("trace 含沉淀/复盘动作")
        ok("复盘沉淀登记", "；".join(pieces))
    else:
        warn("复盘沉淀登记",
             "本次未登记任何沉淀（既无 meta.复盘沉淀，trace 中亦无沉淀/复盘动作）。"
             "若确无可沉淀内容，须**显式写明**『无沉淀：理由』后重跑；"
             "什么都不做的一次 pass 是漏掉的学习机会，不是中性结果。")

def _check_platform(skill_dir: Path) -> None:
    """B：脚本用了单平台能力 vs frontmatter 是否声明 `platforms:`。"""
    skill_md = skill_dir / "SKILL.md"
    head = _frontmatter(skill_md.read_text(encoding="utf-8")) if skill_md.exists() else ""
    declared = bool(re.search(r"^\s*platforms\s*[:\-]", head, re.M))

    hits: list[tuple[str, str, str, str, int]] = []  # (文件, 类别, 名称, 平台, 行号)
    allowed: list[str] = []
    for py in sorted((skill_dir / "scripts").glob("*.py")):
        try:
            src = py.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src, filename=str(py))
        except (SyntaxError, ValueError, OSError):
            continue  # 语法不合法由「py_compile」判据负责，这里不重复报错
        lines = src.splitlines()
        v = _PlatVisitor()
        v.visit(tree)
        for cat, name, plat, ln in v.hits:
            if 0 < ln <= len(lines) and PLAT_ALLOW_TOKEN in lines[ln - 1]:
                allowed.append(f"{py.name}:{name}@{ln}")
                continue
            hits.append((py.name, cat, name, plat, ln))

    if allowed:
        # 豁免不是逃生门 —— 它必须被**看见**（列出文件名与行号），否则就成了"悄悄地放行"。
        ok("平台门控：行内豁免", f"{len(allowed)} 处（{'; '.join(allowed[:5])}"
                                f"{'…' if len(allowed) > 5 else ''}）—— 合法用途仅限判据自身规则表与文档示范")

    if not hits:
        ok("平台门控 vs 真实 import", "scripts/*.py 无单平台 API 依赖（AST 口径）")
        return

    detail = "；".join(f"{f}:{nm}@{ln}[{pl}]" for f, _c, nm, pl, ln in hits[:6])
    if len(hits) > 6:
        detail += f"…（共 {len(hits)} 处）"
    pol = "/".join(sorted({pl for _, _, _, pl, _ in hits}))
    if declared:
        ok("平台门控 vs 真实 import",
           f"frontmatter 已声明 platforms；命中 {len(hits)} 处 {pol} 依赖 —— {detail}。"
           f"⚠️ **声明与实际是否一致本判据不代您核对**（它能发现『未声明』，无法发现『声明得不对』）。")
    else:
        fail("平台门控 vs 真实 import",
             f"用了 {pol} 专属能力却未在 frontmatter 声明 `platforms:` —— {detail}。"
             f"补声明，或改用跨平台实现（如 `tempfile`/`pathlib` 替代硬编码路径）。")

def _check_gate(skill_dir: Path) -> None:
    """C-1 常驻判据：运行时闸门 `gate.py` 的可用性 + 同源性 + fail-closed 行为。

    三级判据，缺一不可 ——
      ① **存在性/语法**：文件在且能 AST 解析（不靠 py_compile 代劳，独立判定）；
      ② **同源性**：`INFRA_EXCEPTIONS` 必须**从 checks.py 加载**（技能库卫生第 4 条：
         同一物理量单一事实源）。**自建副本 → FAIL** —— 那正是「复制粘贴」的复发形态；
      ③ **行为**：跑 `--selftest`，要求退出码 0（含决策层 × 意图对照）。
    ⚠️ 本判据**不复制** `INFRA_EXCEPTIONS` 的取值，只断言「它是被加载来的」——
    否则判据自己就成了第三个副本。
    """
    NAME = "运行时闸门（gate.py 可用性与同源）"
    gate = skill_dir / "scripts" / "gate.py"
    if not gate.exists():
        fail(NAME, "scripts/gate.py 缺失 —— 红线③在**运行时**无收口："
                   "阶段 3 的删改既有文件动作失去前置拦截（事后对账拦不住已发生的事）")
        return
    try:
        src = gate.read_text(encoding="utf-8", errors="ignore")
        ast.parse(src, filename=str(gate))
    except SyntaxError as e:
        fail(NAME, f"gate.py 语法错误（L{e.lineno}）：{e.msg}")
        return
    except (ValueError, OSError) as e:
        fail(NAME, f"gate.py 不可读：{type(e).__name__}: {e}")
        return

    # ② 同源性：不得自建 INFRA_EXCEPTIONS 副本；必须由 checks.py 加载
    self_def = bool(re.search(r"^INFRA_EXCEPTIONS\s*[:=]", src, re.M))
    loads_it = bool(re.search(r"spec_from_file_location|importlib", src)) and "INFRA_EXCEPTIONS" in src
    if self_def:
        fail(NAME, "gate.py **自行定义**了 INFRA_EXCEPTIONS —— 违反技能库卫生第 4 条"
                   "（同一物理量必须单一事实源）。改为从 checks.py 加载，不要复制取值。")
        return
    if not loads_it:
        fail(NAME, "gate.py 未见从 checks.py 加载 INFRA_EXCEPTIONS 的代码 —— 同源性无法证明"
                   "（口径来源不可验证即随时可能漂移）")
        return

    # ③ 行为：阴性对照。第一版假绿正出在「只测范围不测决策」，故这里要求整组退出码 0。
    try:
        r = subprocess.run([sys.executable, str(gate), "--selftest"],
                           capture_output=True, text=True, errors="replace", timeout=120)
    except subprocess.TimeoutExpired:
        fail(NAME, "--selftest 超时（120s）—— 闸门自身可能死锁")
        return
    except OSError as e:
        fail(NAME, f"--selftest 无法启动：{type(e).__name__}: {e}")
        return
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        bad = [l.strip() for l in out.splitlines() if "[XX " in l]
        extra = f"：{'；'.join(bad[:3])}" if bad else ""
        fail(NAME, f"--selftest 退出码 {r.returncode}（{len(bad)} 项不符预期）{extra}")
        return
    n_ok = out.count("[OK ]")
    ok(NAME, f"gate.py 就位；INFRA_EXCEPTIONS 由 checks.py 同源加载（未自建副本）；"
             f"--selftest 退出码 0（{n_ok} 项对照全绿）")
