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
    CATEGORY_SOURCES,
    DECISION_KEYS,
    ENTRY_DIMS,
    ENTRY_KEY,
    ENTRY_REQUIRED,
    FUSE_REPORT,
    FUSE_SECTIONS,
    HOMEWORK_DIMS,
    HOMEWORK_KEY,
    HOMEWORK_MODES,
    HOMEWORK_REQUIRED,
    HOMEWORK_SAMPLE_BAND,
    INFRA_EXCEPTIONS,
    IRREVERSIBLE_HINT,
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
        warn("meta.入口判定",
             "未记录 —— 阶段 0 第 1 步（self-judge）本应产出。**只提示不阻断**："
             "向后兼容旧 plan，不追认历史计划；本项**不是门禁**（校准无法机器强制）")
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
        warn("meta.方法选用",
             "未记录 —— 阶段 3 第②步（method-judge）本应每步产出一条，追加到列表。"
             "**只提示不阻断**：向后兼容旧 plan，不追认历史计划；本项**不是门禁**（校准无法机器强制）")
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
        warn("meta.检索判定",
             "未记录 —— 阶段 3 第 5 条之前（retrieval-judge）本应每次检索产出一条，追加到列表。"
             "**只提示不阻断**：向后兼容旧 plan，不追认历史计划；本项**不是门禁**（校准无法机器强制）")
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
        warn("meta.作业判定",
             "未记录 —— 阶段 0 作业识别（homework-judge）本应产出。**只提示不阻断**："
             "向后兼容旧 plan，不追认历史计划；本项**不是门禁**（校准无法机器强制）")
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
