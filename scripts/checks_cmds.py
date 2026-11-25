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
import hashlib
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
    VALID_TRACE_OUTCOMES,
    VALID_TRIGGER,
    _append_meta_list,
    _capability_ok,
    _jsonl_append,
    _load_batch,
    _pad,
    _require_yaml,
    _set_meta_fuse,
    _sha256_file,
    _step_input_paths,
    _task_dir,
    _yaml_scalar,
    audit_step,
    fail,
    load_plan,
    ok,
    warn,
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
             fuse: str | None = None, batch: str | None = None,
             no_trace: bool = False) -> int:
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
        # 建议 5（2026-11-25）：熔断是**事件**，不是终态。复位后 meta 会变回「正常」，
        # 而 `_metrics.fused` 只读终态 ⇒ 中途熔断过的任务看不出来。这里留一条事件行，
        # 让 metrics 的 fuse_events 有据可查（历史无记录的任务仍记 null，不写成 0）。
        if fuse == "已熔断" and not no_trace:
            wrote, why = _append_mark_trace(
                plan_path, [(str(step_id) if step_id else "-", "熔断")],
                action="熔断：meta 置为已熔断")
            (ok if wrote else warn)("熔断事件留痕",
                                    why or "已写入 trace（fuse_events 可据此累计）")
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
    # 建议 1（2026-11-25）：状态一落盘就把时刻记下来，不依赖执行者事后补 elapsed_s
    if pairs and not no_trace:
        wrote, why = _append_mark_trace(plan_path, pairs)
        (ok if wrote else warn)("mark 自动留痕",
                                why if not wrote else
                                f"{len(pairs)} 个步骤的时刻与步间间隔已写入 trace.jsonl")
    return 0


def _last_trace_epoch(tf: Path) -> tuple[float | None, str]:
    """读 trace 最后一行的时刻，返回 (epoch 秒, 精度)。

    新行带 `ts_epoch`（秒级）；旧行只有 `ts`（分钟级），按分钟解析并标注精度 ——
    分钟级算出的 gap_ms 只能当量级用，如实带 `gap_精度` 供下游判别。
    """
    if not tf.exists():
        return None, "none"
    last = None
    for ln in tf.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.strip():
            last = ln
    if not last:
        return None, "none"
    try:
        row = json.loads(last)
    except json.JSONDecodeError:
        return None, "none"
    v = row.get("ts_epoch")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v), "second"
    ts = str(row.get("ts", "") or "").strip()
    for fmt, prec in (("%Y-%m-%d %H:%M:%S", "second"), ("%Y-%m-%d %H:%M", "minute")):
        try:
            return datetime.strptime(ts, fmt).timestamp(), prec
        except ValueError:
            continue
    return None, "none"


def _append_mark_trace(plan_path: Path, pairs: list[tuple[str, str]],
                       action: str = "mark 自动留痕：状态更新") -> tuple[bool, str]:
    """mark 落盘后自动追加一行 trace（2026-11-25 / 效率改进建议 1）。

    解决的问题：`elapsed_s` 由执行者自填，实测只覆盖 32% 的 trace 行，且 46/51 份
    trace 的时间戳少于步骤数（事后补记）。把「mark 发生的真实时刻」交给工具写，
    相邻行相减即可得步间间隔，不再取决于谁记得填。

    ⚠️ 射程：本项只记**时刻**，不测「这一步干了多久」—— 那仍要靠 `--duration-ms`。
    两者不重复：gap_ms 是相邻事件的间隔（含人的思考时间），duration_ms 是单次操作耗时。
    """
    try:
        tf = _task_dir(plan_path) / "trace.jsonl"
        prev, prec = _last_trace_epoch(tf)
        now = datetime.now()
        epoch = now.timestamp()
        row = {
            "ts": now.strftime("%Y-%m-%d %H:%M"),
            "ts_epoch": round(epoch, 3),
            "step": ",".join(str(sid) for sid, _ in pairs),
            "action": action,
            "result": "；".join(f"{sid}→{st}" for sid, st in pairs),
            "outcome": "ok",
            "source": "mark-auto",
        }
        if prev is not None:
            row["gap_ms"] = int(round((epoch - prev) * 1000))
            row["gap_精度"] = prec
        tf.parent.mkdir(parents=True, exist_ok=True)
        with open(tf, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return True, ""
    except OSError as e:  # 留痕失败不得让状态更新失败（状态已落盘，回滚更糟）
        return False, f"自动留痕写入失败（状态已更新，不影响结果）：{e}"

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
              note: str = "", attempt: int | None = None,
              duration_ms: int | None = None, outcome: str | None = None,
              retries: int | None = None, tokens: int | None = None) -> int:
    """U3：执行 trace —— `plan.yaml` 记的是**离散状态点**（做到哪/为什么引入/为什么变了），
    不含时序；trace 补上时序，让阶段 6 的复盘四问从"回忆"变"查账"。

    ⚠️ **约定：`trace.jsonl` 不进 `交付物` 字段** —— 它是留痕不是交付物。
    若写进交付物，`_is_file_like()` 会命中 `.jsonl` 并按存在性判定，把留痕误当产物。

    v4.1.0：新增 `--note` / `--attempt` —— 用于结构化记录「反思重试」（action=retry 时
    填根因·调整摘要与第几轮重试），与其它 trace 行同构、可 `--replay` 回放。

    v4.47.0 / P2：新增四个**可选**计量字段，把「协同健康度」从"数事件条数"变成可算：
      · `duration_ms` —— 规范字段。给了 `--elapsed`（秒）也自动折算，避免同一物理量两套单位；
      · `outcome`     —— 四态枚举 `ok|fail|blocked|skip`（`result` 仍是自由文字，人读）；
      · `retries`     —— 本步已重试次数（≥0），与 `attempt` 不重复：`attempt` 是"第几次尝试"，
                        `retries` 是"累计重试了几回"，聚合时用后者免去按 attempt 求差；
      · `tokens`      —— 本步 token 用量（≥0）。**量不到就留空，不许估** ——
                        留空在统计里是"未采集"，填错是"假数据"，后者更贵。
    ⚠️ 四个字段一律**可选**：旧 trace 行不带它们仍然合法（向后兼容），统计侧按"未采集"处理。
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
    if outcome is not None and outcome not in VALID_TRACE_OUTCOMES:
        print("[ERROR] --outcome 须在 %s 内，实际 %r" % ("/".join(VALID_TRACE_OUTCOMES), outcome),
              file=sys.stderr)
        return 2
    for name, v in (("duration_ms", duration_ms), ("retries", retries), ("tokens", tokens)):
        if v is not None and v < 0:
            print("[ERROR] --%s 不得为负（实际 %s）" % (name.replace("_", "-"), v), file=sys.stderr)
            return 2

    rec = {"ts": time.strftime("%Y-%m-%d %H:%M"), "step": str(step),
           "action": action or "", "cmd": command or "", "result": result or ""}
    if duration_ms is None and elapsed is not None:
        duration_ms = int(round(elapsed * 1000))
    if duration_ms is not None:
        rec["duration_ms"] = int(duration_ms)
    if elapsed is not None:
        # 兼容旧读者：v4.47.0 前只认 elapsed_s。新写入方优先看 duration_ms。
        rec["elapsed_s"] = elapsed
    if outcome:
        rec["outcome"] = outcome
    if retries is not None:
        rec["retries"] = int(retries)
    if tokens is not None:
        rec["tokens"] = int(tokens)
    if note:
        rec["note"] = note
    if attempt is not None:
        rec["attempt"] = attempt
    _jsonl_append(tf, rec)
    print("[OK] trace 已追加 —— %s（step=%s）" % (tf, step))
    return 0


# --------------------------------------------------------------------------- checkpoint
# `_step_input_paths` / `_sha256_file` 已下沉到 checks_core（依赖方向 core←parity←judges←cmds，
# 判据侧 `_check_checkpoint` 也要用同一份解析口径 —— 两处各写一份就会"工具算的指纹与判据
# 复算的指纹不是同一个东西"，那种漂移最难查）。


def cmd_checkpoint(plan_path: Path, step_id: str, note: str, no_resume: bool,
                   base: Path) -> int:
    """P2：给某一步落「输入指纹 + 检查点」，让熔断 / 中断后能**从断点续跑**而不是重跑全链。

    为什么不是手工填：`输入指纹` 与产物 `sha256` 都是 64 位 hex，手抄必错且无法复核；
    而检查点的全部价值就在"它记录的是当时的真实字节"。所以由工具现算。

    写入面（步骤级两项，皆为可选字段，旧 plan 不加也合法）：
      · `输入指纹` —— 本步输入文件的 sha256 取前 16 位（16 位够区分，又不至于把 plan 撑爆）；
      · `检查点`   —— `{时间, 产物[{路径,sha256,字节}], 可续跑, 说明}`。

    ⚠️ `可续跑` 默认 true，`--no-resume` 置 false。它的语义是"从这一步之后接着跑不会
    破坏已完成的因果"，不是"这一步跑成功了"——后者由 `状态` 字段管。
    ⚠️ 解析不到任何输入文件 ⇒ **退出码 2 不落盘**。宁可让人补 `输入`，也不写一个假的指纹
    （假指纹会让续跑判据永远显示"输入没变"，比没有指纹更危险）。
    """
    yaml = _require_yaml()
    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1
    try:
        data = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    except Exception as e:                                  # noqa: BLE001
        fail("plan.yaml 可解析", f"{type(e).__name__}: {e}")
        return 1
    steps = data.get("steps") or []
    target = None
    for s in steps:
        if isinstance(s, dict) and str(s.get("id")) == str(step_id):
            target = s
            break
    if target is None:
        fail("找到该步骤", f"id={step_id}；现有 id：{', '.join(str(x.get('id')) for x in steps if isinstance(x, dict))}")
        return 1

    inputs = _step_input_paths(target, base)
    if not inputs:
        fail("本步输入可解析",
             f"id={step_id} 的「输入」里找不到真实存在的文件（base={base}）—— "
             f"请先把输入写成实际路径再落检查点（不写假指纹）")
        return 2
    fp_src = "\n".join(f"{p.as_posix()}:{_sha256_file(p)}" for p in sorted(inputs, key=lambda x: x.as_posix()))
    fingerprint = hashlib.sha256(fp_src.encode("utf-8")).hexdigest()[:16]

    arts = []
    deliv = target.get("交付物")
    raw_deliv = [str(x) for x in deliv] if isinstance(deliv, list) else ([str(deliv)] if deliv else [])
    for tok in raw_deliv:
        p = Path(tok.strip().strip("`'\""))
        if not p.is_absolute():
            p = base / p
        try:
            if p.is_file():
                arts.append({"路径": tok.strip(), "sha256": _sha256_file(p), "字节": p.stat().st_size})
        except OSError:
            continue

    # ---- 文本级插入（不用 yaml.dump：那会重排整份 plan、抹掉注释）
    lines = plan_path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = None
    cur = None
    for i, ln in enumerate(lines):
        m = re.match(r"^(\s*)-\s*id:\s*(\S+)\s*$", ln)
        if m:
            if cur == str(step_id) and start is not None:
                break
            cur = m.group(2)
            if cur == str(step_id):
                start = i
                body_indent = len(m.group(1)) + 2
    if start is None:
        fail("定位步骤块", f"id={step_id}")
        return 1
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^(\s*)-\s*id:\s*\S+\s*$", lines[j]) and len(re.match(r"^(\s*)", lines[j]).group(1)) <= body_indent - 2:
            end = j
            break
        if re.match(r"^[^\s#]", lines[j]):     # 顶层键（steps 之后的兄弟）
            end = j
            break

    # 先摘掉旧的 `输入指纹` 行与 `检查点` 子块（幂等：重复执行只留一份）
    keep: list[str] = []
    k = start + 1
    while k < end:
        ln = lines[k]
        if re.match(r"^\s*输入指纹\s*:", ln):
            k += 1
            continue
        m = re.match(r"^(\s*)检查点\s*:", ln)
        if m:
            ck_indent = len(m.group(1))
            k += 1
            while k < end:
                nxt = lines[k]
                if nxt.strip() and not nxt.startswith(" " * (ck_indent + 1)):
                    break
                k += 1
            continue
        keep.append(ln)
        k += 1
    tail = lines[end:]
    pad = " " * body_indent
    new_block = [f"{pad}输入指纹: {fingerprint}\n", f"{pad}检查点:\n",
                 f"{pad}  时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
    if arts:
        new_block.append(f"{pad}  产物:\n")
        for a in arts:
            new_block.append(f"{pad}    - 路径: {_yaml_scalar(a['路径'])}\n")
            new_block.append(f"{pad}      sha256: {a['sha256']}\n")
            new_block.append(f"{pad}      字节: {a['字节']}\n")
    else:
        new_block.append(f"{pad}  产物: []\n")
    new_block.append(f"{pad}  可续跑: {'false' if no_resume else 'true'}\n")
    new_block.append(f"{pad}  说明: {_yaml_scalar(note)}\n")

    plan_path.write_text("".join(lines[: start + 1] + keep + new_block + tail), encoding="utf-8")
    ok("检查点已落盘",
       f"step={step_id} 指纹={fingerprint}（{len(inputs)} 个输入）产物 {len(arts)} 项"
       f"{'，标记为不可续跑' if no_resume else ''}")
    return 0

def _metrics_upsert(path: Path, rec: dict) -> "tuple[int, dict]":
    """把 `rec` **幂等**写入 `_metrics.jsonl`：使该文件恰好一行（v4.10.1）。

    为什么不用 `_jsonl_append`（本函数存在的全部理由）：
      · `SKILL.md` 阶段 6 第 3 条明文写「**每任务一行**」，而 `_metrics.jsonl` 按任务分文件
        （v4.3.0 路径口径）⇒ 「一个文件 = 一个任务 = 一行」是**天然唯一键**。
      · 旧实现无条件追加，产生两类脏数据：① 重复收尾 → 同任务多行、统计双计；② 中途调用的
        **半成品行**（如 `done=6`）与终值行（`done=9`）并存 ⇒ 数据自相矛盾。两类均已实测
        （受控复现 3 行 / 真实工作区 2 行）。
      · ⚠️ **不要为了修它去改 `_jsonl_append`** —— 同一 helper 也服务于 `trace.jsonl`
        （本文件 `_cmd_trace` 内），那里**必须保持追加语义**（`--replay` 依赖逐条时序）。

    唯一键取「文件自身」而非 `meta.任务` 文本：任务在收尾前改名时文本键会失配，反而造出
    「又变成两行」这一新失败模式。

    自愈：文件里已有的重复行**不是**报错，而是本次一并收敛，旧行数记入写入记录的
    `superseded` 字段 —— 使「替换掉了几条」可审计，而不是静默抹掉。

    原子性：先写 `<name>.tmp` 再 `os.replace`，避免半写状态被消费方读到。

    返回 `(被替换的旧行数, 实际写入的记录)`；旧行数为 0 表示首次写入。
    """
    prev_n = 0
    if path.exists():
        prev_n = sum(1 for ln in path.read_text(encoding="utf-8-sig").splitlines() if ln.strip())
    out = dict(rec)
    out["superseded"] = prev_n
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False) + "\n", encoding="utf-8")
    _os.replace(tmp, path)
    return prev_n, out

def _count_fuse_events(meta: dict, steps: list, trace_path: Path) -> tuple[int | None, str]:
    """熔断发生次数（建议 5／2026-11-25）。

    背景：`_metrics.fused` 读的是 `meta.熔断状态 == "已熔断"` —— 那是**终态声明**。
    中途熔断、后来复位，meta 变回「正常」，`fused` 就是 false，事件整个消失。
    效率调研实测 51 个任务全 false，而台账里确有「三轮送审均不通过」的记录。

    三级来源，按可信度取：

    - `trace`：逐条数 `action` 以「熔断：」开头的行。本版起 `mark --fuse 已熔断` 会自动写，
      所以**从今天起可累计**。⚠️ 只要 trace 里**有可解析的行**就归到这一级，哪怕熔断行数为 0 ——
      「有观测面、观测到 0 次」与「没有观测面、不知道」是两件事（2026-11-25 修正：首版只要
      数不到熔断行就返回 `none`，把「完整的 trace + 确实零熔断」写成了未知，与本函数自己的
      「`none` = 没有任何痕迹」自相矛盾）；
    - `status-only`：无 trace 时的**可证下界** —— meta 已熔断记 1、处于熔断态的步骤各记 1。
      这是下界不是真值，故单独标注来源；
    - `none`：**trace 缺失、为空、或一行都解析不出来** ⇒ 返回 **None 而非 0**。
      「没记录」与「没发生」是两件事，写成 0 就是替历史编数（效率调研 §7 已把这条列为方法论局限）。
    """
    n_trace = 0
    n_rows = 0
    if trace_path.exists():
        for ln in trace_path.read_text(encoding="utf-8", errors="replace").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            n_rows += 1
            if str(row.get("action", "")).startswith("熔断："):
                n_trace += 1
    if n_rows:
        return n_trace, "trace"
    lower = 0
    if str(meta.get("熔断状态", "") or "").strip() == "已熔断":
        lower += 1
    lower += sum(1 for s in steps if str(s.get("状态", "") or "").strip() == "熔断")
    if lower:
        return lower, "status-only"
    return None, "none"


def cmd_metrics(plan_path: Path, finalize: bool) -> int:
    """U8：任务级指标沉淀 —— 收尾时把本任务指标写入**本任务目录**的 `_metrics.jsonl`
    （即 `tasks/<任务>/_metrics.jsonl`）。

    ⚠️ **路径口径修正（v4.3.0）**：此前 docstring 与 `SKILL.md` 都写作"工作区级
    `tasks/_metrics.jsonl`"，但代码一直是 `_task_dir(pp) / "_metrics.jsonl"` —— 落点是**任务
    目录内**。实测工作区：`tasks/*/_metrics.jsonl` 有 1 个、`tasks/_metrics.jsonl` 为 0 个，
    证明实际行为与文档不符。按「同一物理量两处即为不符合」（技能库卫生第 4 条）**改文档对齐
    代码**，而不是改代码去迁就文档 —— 因为按任务分文件才能让归档随任务一起移动。

    目的：此前**没有任何任务级统计**（返修轮次、熔断频次、门禁 FAIL 率、步骤耗时全无），
    技能自身演进缺数据依据。

    ⚠️ **幂等修正（v4.10.1）**：本命令此前**无条件追加**，与上面那段「每任务一行」的口径不符
    —— 重复 `--finalize` 会在同一任务目录堆出多行，其中中途调用的**半成品行**（当时步骤尚未
    跑完，如 `done=6`）与终值行（`done=9`）并存，使任何按行聚合的统计重复计数、且数据自相
    矛盾。现改走 `_metrics_upsert`（读旧行 → 单行原子重写）：重复调用**恒为一行**，历史重复
    行在下次调用时自动收敛。首次写入与刷新在输出上**显式区分**，刷新还会报出替换了几条。
    """
    if not finalize:
        print("[ERROR] 目前只支持 --finalize（收尾时汇总一次，避免中途写入半成品）", file=sys.stderr)
        return 2
    # 2026-11-25 修：原写法 `plan_path if is_dir() else plan_path.parent` 会把
    # 「传进来的具体文件名」改写成同目录的固定 `plan.yaml`，导致传 `xxx.yaml` 时报找不到。
    # 现改为：目录 → 拼 plan.yaml；文件 → 原样使用。
    pp = (plan_path / "plan.yaml") if plan_path.is_dir() else plan_path
    if not pp.exists():
        print("[ERROR] 找不到 plan.yaml —— %s" % pp, file=sys.stderr)
        return 2
    yaml = _require_yaml()
    data = yaml.safe_load(pp.read_text(encoding="utf-8")) or {}
    meta = data.get("meta") or {}
    steps = data.get("steps") or []
    st = [str(s.get("状态", "") or "") for s in steps]
    tpath = _task_dir(pp) / "trace.jsonl"
    fuse_ev, fuse_src = _count_fuse_events(meta, steps, tpath)
    rec = {
        "task": str(meta.get("任务", "") or "")[:80],
        "level": str(meta.get("任务层级", "") or "") or "?",
        "date": time.strftime("%Y-%m-%d"),
        "revisions": len(meta.get("计划修订") or []),
        "fused": str(meta.get("熔断状态", "") or "").strip() == "已熔断",
        "fuse_events": fuse_ev,
        "fuse_events_source": fuse_src,
        "steps": len(steps),
        "done": sum(1 for x in st if x == "完成"),
        "irreversible": len(meta.get("不可逆副作用") or []),
        "released": len(meta.get("用户放行") or []),
    }
    tf = _task_dir(pp) / "_metrics.jsonl"
    superseded, written = _metrics_upsert(tf, rec)
    if superseded:
        print("[OK] 指标已刷新（幂等覆盖，替换旧记录 %d 条）—— %s" % (superseded, tf))
    else:
        print("[OK] 指标已写入（首次）—— %s" % tf)
    print("    " + json.dumps(written, ensure_ascii=False)[:260])
    return 0
