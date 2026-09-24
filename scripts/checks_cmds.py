# -*- coding: utf-8 -*-
"""checks 命令层：status / mark / decide / revise / selftool / trace / metrics

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
from checks_core import (  # noqa: F401
    MAX_REVISIONS,
    METHOD_KEY,
    VALID_CAPABILITY,
    VALID_FUSE,
    VALID_STATUS,
    VALID_TRIGGER,
    _append_meta_list,
    _capability_ok,
    _jsonl_append,
    _load_batch,
    _pad,
    _require_yaml,
    _set_meta_fuse,
    _task_dir,
    _yaml_scalar,
    audit_step,
    fail,
    load_plan,
    ok,
)

def cmd_status(workspace: Path, archive_days: int, max_tasks: int, light: bool = False) -> int:
    tasks_root = workspace / "tasks"
    if not tasks_root.exists():
        fail("tasks/ 目录存在", str(tasks_root))
        print("       提示：工作区不是当前目录时请加 --workspace <工作区根>；"
              "任务目录应建在工作区根下的 tasks/（见 SKILL.md 红线③）")
        return 1
    dirs = sorted([d for d in tasks_root.iterdir() if d.is_dir() and not d.name.startswith("_")])
    if not dirs:
        ok("tasks/ 下无任务目录")
        return 0

    now = time.time()
    stale = []
    tripped_tasks = []
    print(_pad("任务目录", 46) + _pad("层级", 7) + _pad("步骤完成", 11) + _pad("交付物", 11) + "最后修改")
    print("-" * 86)
    for d in dirs:
        plan = d / "plan.yaml"
        age_days = (now - d.stat().st_mtime) / 86400
        layer, steps_txt, deliv_txt = "—", "无 plan", "—"
        fuse_mark = ""
        if plan.exists():
            try:
                data = load_plan(plan)
                meta = data.get("meta") or {}
                layer = str(meta.get("任务层级", "—"))
                steps = data.get("steps") or []
                if str(meta.get("熔断状态", "") or "").strip() == "已熔断" or any(
                    str(s.get("状态", "")).strip() == "熔断" for s in steps
                ):
                    fuse_mark = " ⚡已熔断"
                    tripped_tasks.append(d.name)
                done = [s for s in steps if str(s.get("状态", "")).strip() == "完成"]
                steps_txt = f"{len(done)}/{len(steps)}"
                if light:
                    deliv_txt = "—"  # 轻量模式不核对交付物存在性（跳过逐文件 exists 检查，N6）
                else:
                    audited = [audit_step(s, workspace) for s in steps]
                    total_deliv = sum(a["交付物总数"] for a in audited)
                    exist = sum(a["存在数"] for a in audited)
                    deliv_txt = f"{exist}/{total_deliv}" if total_deliv else "0"
                    # 已完成步骤中若有交付物缺失 → 打 ⚠（v2.5.3 修复：原写法 `for a in done` 拿
                    # 「步骤 dict」去取审计结果键 `缺失`，必抛 KeyError 并被外层宽 except 吞成
                    # 「解析失败(KeyError)」，导致总览的完成度列长期失真）
                    if any(a["缺失"] for a, s in zip(audited, steps)
                           if str(s.get("状态", "")).strip() == "完成"):
                        deliv_txt += " ⚠"
                if not any("状态" in s for s in steps):  # v2 之前的计划结构，仅统计步数
                    steps_txt = f"旧格式 {len(steps)} 步"
            except Exception as e:  # noqa: BLE001 - 单个任务解析失败不应中断总览
                steps_txt = f"解析失败({type(e).__name__})"
        mark = " ← 建议归档" if age_days > archive_days else ""
        if age_days > archive_days:
            stale.append(d.name)
        print(_pad(d.name, 46) + _pad(layer, 7) + _pad(steps_txt, 11) + _pad(deliv_txt, 11)
              + f"{age_days:>4.0f} 天{mark}{fuse_mark}")

    if tripped_tasks:
        print(f"\n[WARN] {len(tripped_tasks)} 个任务处于「已熔断」：{', '.join(tripped_tasks[:5])}{' …' if len(tripped_tasks) > 5 else ''}")
        print("       已熔断的任务禁止自动续跑、不得交付；复位须用户明示且两步缺一不可（见 SKILL.md 熔断机制）")
    if len(dirs) > max_tasks:
        print(f"\n[WARN] 任务目录 {len(dirs)} 个 > 阈值 {max_tasks}，建议归档最旧的若干个（参考 SKILL.md 阶段 6 归档规则）")
    if stale:
        print(f"[WARN] {len(stale)} 个任务超过 {archive_days} 天未改动：{', '.join(stale[:5])}{' …' if len(stale) > 5 else ''}")
    else:
        print(f"\n[ OK ] 无超过 {archive_days} 天的陈旧任务")
    ok("任务总览", f"{len(dirs)} 个任务目录" + (f"，其中 {len(tripped_tasks)} 个已熔断" if tripped_tasks else ""))
    return 0

def cmd_mark(plan_path: Path, step_id: str | None, status: str | None,
             fuse: str | None = None, batch: str | None = None) -> int:
    if status is not None and status not in VALID_STATUS:
        fail("状态合法", f"『{status}』不在 {VALID_STATUS}")
        return 1
    if fuse is not None and fuse not in VALID_FUSE:
        fail("熔断状态合法", f"『{fuse}』不在 {VALID_FUSE}")
        return 1
    # 收集本次要改的步骤：(step_id, status)；batch 与单步二选一来源
    if batch is not None:
        pairs = _load_batch(batch)
    else:
        if step_id is None and fuse is None:
            fail("参数", "至少给出 ` <step_id> <状态>` 或 `--fuse <正常|已熔断>` 或 `--batch <文件>`")
            return 1
        if step_id is not None and status is None:
            fail("参数", "给出 <step_id> 时必须同时给出 <状态>")
            return 1
        pairs = [(step_id, status)] if step_id is not None else []
    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1

    # 先处理 fuse（一次性写 meta）
    if fuse is not None:
        if not _set_meta_fuse(plan_path, fuse):
            fail("meta.熔断状态 写入", "未找到 `meta:` 块，请手工添加该键")
            return 1
        ok("meta.熔断状态已更新", f"→ {fuse}")
        if not pairs:
            return 0

    # N7：一次性读盘，定位所有目标行；任一缺失则整体失败、不落盘（信任但验证）
    lines = plan_path.read_text(encoding="utf-8").splitlines(keepends=True)
    targets: dict[str, int] = {}
    for sid, _ in pairs:
        cur = None
        target = None
        for i, ln in enumerate(lines):
            m = re.match(r"^\s*-\s*id:\s*(\S+)\s*$", ln)
            if m:
                cur = m.group(1)
            elif re.match(r"^\s*状态:", ln) and cur == str(sid):
                target = i
                break
        if target is None:
            fail("找到该步骤的『状态』行", f"id={sid}")
            return 1
        targets[sid] = target
    changes = []
    for sid, st in pairs:
        i = targets[sid]
        old = lines[i].strip()
        indent = re.match(r"^(\s*)", lines[i]).group(1)
        lines[i] = f"{indent}状态: {st}\n"
        changes.append(f"{sid}: {old} → 状态: {st}")
    plan_path.write_text("".join(lines), encoding="utf-8")
    ok("步骤状态已更新", f"{len(pairs)} 个：" + "; ".join(changes))
    return 0

def cmd_decide(plan_path: Path, point: str, basis: str,
               capability: str | None, choice: str | None,
               ms_index: int | None = None) -> int:
    """追加一条能力决策记录（自主决策层留痕，v3.0.0）。

    v4.4.0 增强：--from-method-select [INDEX] 从 plan 的 meta.方法选用 列表读取一条
    method-judge 产出，自动推导 能力类/选择/依据（可被同名参数覆盖）；决策点(--point)
    仍须手填（方法选用不记录步骤名）。INDEX 缺省取最新一条；传正整数为 1-based 序号。
    """
    if not (point or "").strip():
        fail("参数", "必须给出 --point（决策点：这一步缺什么/要决定什么）")
        return 1
    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1

    # —— v4.4.0：从 meta.方法选用 推导缺失字段 ——
    if ms_index is not None:
        yaml = _require_yaml()
        try:
            _data = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
            _ms_list = (_data.get("meta") or {}).get(METHOD_KEY)
        except Exception as e:  # noqa: BLE001 - 解析失败的明确报错，不静默
            fail("meta.方法选用 读取", f"YAML 解析失败：{e}")
            return 1
        if not isinstance(_ms_list, list) or not _ms_list:
            fail("meta.方法选用", "不存在或为空，无法从中推导决策记录"
                 "（先经 method-judge 产出并写入 meta.方法选用 列表）")
            return 1
        _idx = (len(_ms_list) - 1) if ms_index < 0 else (ms_index - 1)
        if not (0 <= _idx < len(_ms_list)):
            fail("meta.方法选用 索引", f"INDEX={ms_index} 越界（共 {len(_ms_list)} 条）")
            return 1
        _ms = _ms_list[_idx] or {}
        if not _capability_ok(capability):
            capability = str(_ms.get("gap_class", "") or "").strip() or None
        if not (choice or "").strip():
            _cands = _ms.get("candidates") or []
            _top = max(_cands, key=lambda c: float(c.get("fit_score", 0) or 0)) if _cands else None
            choice = (_top.get("tool") if isinstance(_top, dict) else None) or None
        if not (basis or "").strip():
            _rh = str(_ms.get("route_hint", "") or "").strip()
            _conf = _ms.get("confidence")
            basis = (f"{_rh}（confidence={_conf}）" if _rh
                     else f"（confidence={_conf}）")

    if not _capability_ok(capability):  # argparse choices 已兜一层；此处含「+」组合
        fail("能力类合法", f"『{capability}』不在 {VALID_CAPABILITY}（或「+」组合越界；可经 --capability 显式给出）")
        return 1
    if not (basis or "").strip() or not (choice or "").strip():
        fail("参数", "必须给出 --basis（依据）与 --choice（选择）；或从 --from-method-select 推导")
        return 1
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    item = [
        f"    - 决策点: {_yaml_scalar(point)}\n",
        f"      能力类: {_yaml_scalar(capability or '')}\n",
        f"      依据: {_yaml_scalar(basis)}\n",
        f"      选择: {_yaml_scalar(choice or '')}\n",
        f"      时间: {_yaml_scalar(ts)}\n",
    ]
    if not _append_meta_list(plan_path, "决策记录", item):
        fail("meta.决策记录 写入", "未找到 `meta:` 块，请手工添加该键")
        return 1
    ok("决策记录已追加", f"能力类={capability}；决策点={point[:40]}"
       + ("（自 meta.方法选用 推导）" if ms_index is not None else ""))
    return 0

def cmd_revise(plan_path: Path, trigger: str, change: str,
               unchanged: str | None) -> int:
    """追加一条计划修订（重规划留痕，v3.0.0）；超上限 FAIL 并提示重新对齐目标。"""
    if trigger not in VALID_TRIGGER:
        fail("触发编号合法", f"『{trigger}』不在 {VALID_TRIGGER}")
        return 1
    if not (change or "").strip():
        fail("参数", "必须给出 --change（变化摘要）")
        return 1
    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1
    yaml = _require_yaml()
    try:
        data = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        fail("plan.yaml 可解析", str(e).splitlines()[0][:120])
        return 1
    cur = (data.get("meta") or {}).get("计划修订") or []
    if not isinstance(cur, list):
        fail("meta.计划修订 格式", "应为列表")
        return 1
    if len(cur) >= MAX_REVISIONS:
        fail("计划修订上限", f"已有 {len(cur)} 条，上限 {MAX_REVISIONS}：说明初始拆解方法有问题"
                             "或该任务不适合线性计划，应停下与用户重新对齐目标（这是重新澄清，非熔断）")
        return 1
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    ver = f"v{len(cur) + 1} → v{len(cur) + 2}"
    item = [
        f"    - 版本: {_yaml_scalar(ver)}\n",
        f"      触发: {_yaml_scalar(trigger)}\n",
        f"      时间: {_yaml_scalar(ts)}\n",
        f"      变化: {_yaml_scalar(change)}\n",
        f"      未变: {_yaml_scalar(unchanged or '')}\n",
    ]
    if not _append_meta_list(plan_path, "计划修订", item):
        fail("meta.计划修订 写入", "未找到 `meta:` 块，请手工添加该键")
        return 1
    ok("计划修订已追加", f"第 {len(cur) + 1}/{MAX_REVISIONS} 条；触发={trigger}")
    return 0

def cmd_selftool(plan_path: Path, name: str, purpose: str, scenario: str, repo: str) -> int:
    """追加一条自研工具/技能登记到 meta.自研工具（v3.1.0 公开留痕）。

    四项参数均必填 —— 与 `decide` 同口径：登记的价值在于"事后能查到它是什么、
    从哪来"，缺任何一项都会让留痕退化成走过场。
    """
    if not all((x or "").strip() for x in (name, purpose, scenario, repo)):
        fail("参数", "必须给出 --name（名称）、--purpose（用途）、--scenario（适用场景）与 --repo（仓库链接）")
        return 1
    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1
    item = [
        f"    - 名称: {_yaml_scalar(name)}\n",
        f"      用途: {_yaml_scalar(purpose)}\n",
        f"      适用场景: {_yaml_scalar(scenario)}\n",
        f"      仓库链接: {_yaml_scalar(repo)}\n",
    ]
    if not _append_meta_list(plan_path, "自研工具", item):
        fail("meta.自研工具 写入", "未找到 `meta:` 块，请手工添加该键")
        return 1
    ok("自研工具已登记", f"{name}；仓库={repo[:48]}")
    return 0

def cmd_trace(plan_path: Path, step: str | None, action: str, command: str,
              result: str, elapsed: float | None, replay: bool,
              note: str = "", attempt: int | None = None) -> int:
    """U3：执行 trace —— `plan.yaml` 记的是**离散状态点**（做到哪/为什么引入/为什么变了），
    不含时序；trace 补上时序，让阶段 6 的复盘四问从"回忆"变"查账"。

    ⚠️ **约定：`trace.jsonl` 不进 `交付物` 字段** —— 它是留痕不是交付物。
    若写进交付物，`_is_file_like()` 会命中 `.jsonl` 并按存在性判定，把留痕误当产物。

    v4.1.0：新增 `--note` / `--attempt` —— 用于结构化记录「反思重试」（action=retry 时
    填根因·调整摘要与第几轮重试），与其它 trace 行同构、可 `--replay` 回放。
    """
    tf = _task_dir(plan_path) / "trace.jsonl"
    if replay:
        if not tf.exists():
            print("[INFO] 无 trace 记录 —— %s 不存在" % tf)
            return 0
        n = 0
        for i, ln in enumerate(tf.read_text(encoding="utf-8").splitlines(), 1):
            if ln.strip():
                print("%3d  %s" % (i, ln[:200]))
                n += 1
        print("=== trace 回放：%d 条 ===" % n)
        return 0
    if not step:
        print("[ERROR] --step 必填（--replay 时不需要）", file=sys.stderr)
        return 2
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M"), "step": str(step),
           "action": action or "", "cmd": command or "", "result": result or ""}
    if elapsed is not None:
        rec["elapsed_s"] = elapsed
    if note:
        rec["note"] = note
    if attempt is not None:
        rec["attempt"] = attempt
    _jsonl_append(tf, rec)
    print("[OK] trace 已追加 —— %s（step=%s）" % (tf, step))
    return 0

def cmd_metrics(plan_path: Path, finalize: bool) -> int:
    """U8：任务级指标沉淀 —— 收尾时把本任务指标追加进**本任务目录**的 `_metrics.jsonl`
    （即 `tasks/<任务>/_metrics.jsonl`）。

    ⚠️ **路径口径修正（v4.3.0）**：此前 docstring 与 `SKILL.md` 都写作"工作区级
    `tasks/_metrics.jsonl`"，但代码一直是 `_task_dir(pp) / "_metrics.jsonl"` —— 落点是**任务
    目录内**。实测工作区：`tasks/*/_metrics.jsonl` 有 1 个、`tasks/_metrics.jsonl` 为 0 个，
    证明实际行为与文档不符。按「同一物理量两处即为不符合」（技能库卫生第 4 条）**改文档对齐
    代码**，而不是改代码去迁就文档 —— 因为按任务分文件才能让归档随任务一起移动。

    目的：此前**没有任何任务级统计**（返修轮次、熔断频次、门禁 FAIL 率、步骤耗时全无），
    技能自身演进缺数据依据。
    """
    if not finalize:
        print("[ERROR] 目前只支持 --finalize（收尾时汇总一次，避免中途写入半成品）", file=sys.stderr)
        return 2
    pp = plan_path if plan_path.is_dir() else plan_path.parent
    if pp.is_dir():
        pp = pp / "plan.yaml"
    if not pp.exists():
        print("[ERROR] 找不到 plan.yaml —— %s" % pp, file=sys.stderr)
        return 2
    yaml = _require_yaml()
    data = yaml.safe_load(pp.read_text(encoding="utf-8")) or {}
    meta = data.get("meta") or {}
    steps = data.get("steps") or []
    st = [str(s.get("状态", "") or "") for s in steps]
    rec = {
        "task": str(meta.get("任务", "") or "")[:80],
        "level": str(meta.get("任务层级", "") or "") or "?",
        "date": time.strftime("%Y-%m-%d"),
        "revisions": len(meta.get("计划修订") or []),
        "fused": str(meta.get("熔断状态", "") or "").strip() == "已熔断",
        "steps": len(steps),
        "done": sum(1 for x in st if x == "完成"),
        "irreversible": len(meta.get("不可逆副作用") or []),
        "released": len(meta.get("用户放行") or []),
    }
    tf = _task_dir(pp) / "_metrics.jsonl"
    _jsonl_append(tf, rec)
    print("[OK] 指标已追加 —— %s" % tf)
    print("    " + json.dumps(rec, ensure_ascii=False)[:220])
    return 0
