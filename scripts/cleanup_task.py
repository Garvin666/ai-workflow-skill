#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务产物清理：任务成功后清掉中间产物，仅留必要输出（**默认 dry-run，删除是不可逆动作**）。

[自研工具] ai-workflow 任务产物清理器（cleanup_task.py）
名称：cleanup_task.py —— 任务成功收尾后的中间产物清理
用途：任务全部步骤成功后，清理 `tasks/<任务>/tmp/` 下的脚手架文件、临时目录与中间产物，
      仅保留必要的输出结果（交付物）与全部留痕/证据文件，使工作区保持干净整洁。
适用场景：L2 任务阶段 6 收尾（全部步骤完成 + 未熔断 + 交付物对账 FAIL=0）。
          不适用：任务未完成 / 已熔断 / 交付物对账未清零 / 任务目录之外的一切路径。
仓库：https://github.com/Garvin666/ai-workflow-tools

为什么需要它
------------
v3.4.0 / P7 已把「探针与夹具输出一律放 `tasks/<任务>/tmp/`」定为约定（当时从生产缓存根里
扫出 290.75 MB 残留），但此后**没有任何清理机制** —— `tmp/` 只进不出。实测技能自身
`tasks/*/tmp/` 已积累 152 文件 / 1.52 MB。`archive_tasks.py` 管的是「任务目录整体归档」，
管不到「目录内的中间产物」，两者互补而非替代。

本脚本与技能内四处 dry-run 先例同源（`archive_tasks.py` / `push_router.py` /
`push_ontology.py` / `kb_learn.py commit`）：**默认只打印计划，`--apply` 才动**。
理由不是谨慎，是红线①（用户确认前不执行）与「删改既有文件属高风险」这条硬规矩。

设计上刻意做的三件事
--------------------
1. **白名单容器式，不是黑名单**。「中间产物」无法机器判定，但「约定容器」可以 ——
   故只清 `tmp/` 一棵树，而不是「删掉所有非交付物」。后者会误删留痕与人审证据。
2. **保护清单优先于删除清单**。交付物、`plan.yaml`、`trace.jsonl`、`_metrics.jsonl`、
   各类报告、被 `SKILL.md`／`references/*.md` 引用的路径、**被本任务自身记录文件
   （任务根 `*.md`）引用**的路径 —— 即使它们出现在 `tmp/` 里也不删。
   （交付物优先于容器约定：约定说的是「tmp 是中间产物」，不是「tmp 里的都该删」。）
   ⚠️ **v4.14.1 补第二类引用面**：此前只扫技能自己的手册，于是**任务记录里引用的 tmp 证据会被清掉**，
   记录正文随即留下**悬空引用**（与「文档写着有、实际不在」同源）—— 实测本仓 25/30 个活跃任务目录
   都有这种引用。两类引用面合并为同一个保护判据，理由文案区分「技能手册」与「本任务记录」以便人核。
   **该面的诚实边界**：只扫任务根 `*.md`，**`plan.yaml` 里的 `tmp/` 引用不覆盖** ——
   若把 plan.yaml 一并纳入，就会与 `deliverable_paths()` 重叠，令 S4 阴性对照（"撤掉交付物保护后
   必须能删到"）**恒判假绿**，反而毁掉「交付物保护有牙齿」的唯一证据（详见 `referenced_in_task()` 注释）。
   故 `plan.yaml` 里**单独**引用的证据项仍会被清掉 —— 写记录时请把证据一并写进任务根的 `*.md`。
3. **删后不给结论、只给证据**。删完重跑一次交付物对账 —— 双条件：**删干净了** **且**
   **没删该留的**。只报前半句等于把「误删」读成「成功」。

触发条件（四条 AND，任一不满足即拒绝，退出码 2）
------------------------------------------------
T1 全部步骤 `状态 == 完成`      —— 有 待办/进行中/受阻 说明任务没完
T2 `熔断状态` ∈ {空, 正常}       —— 已熔断的任务须保留现场，绝不清理
T3 交付物对账 FAIL == 0          —— 清理必须在交付之后（"先落产物后对账"）
T4 用户放行（`--apply` 本身即放行动作；dry-run 不需要）

清理失败的处理
--------------
逐项容错、不静默；删前落 sha256 快照存档；失败项列出 + 退出码非零；
**绝不阻断已完成的交付**，但必须显式报「本次清理未完成：N 项」，不得报成功。

退出码：0 成功（含 dry-run 与"无待清理项"）／1 执行后校验失败／2 前置检查拒绝
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

try:  # Windows 控制台默认可能是 GBK，与调用方约定的 utf-8 不一致会产生乱码
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

SELF = Path(__file__).resolve()

# 与 checks_core.py 同口径（那边是唯一事实源，此处只复刻判定规则，不另立一套）
REF_PATTERN = re.compile(r"`([A-Za-z0-9_./\u4e00-\u9fff-]+\.(?:md|yaml|py|ps1))`")
VALID_STATUS = ("待办", "进行中", "完成", "受阻", "熔断")
FUSE_OK = ("", "正常")

# ── 保护清单 ────────────────────────────────────────────────────────────────
# 刻意写成"可被 selftest 逐条撤掉"的形态：阴性对照要能证明**每一条都在起作用**。
PROTECT_NAMES = {"plan.yaml", "trace.jsonl", "_metrics.jsonl", "确认表.md", "熔断报告.md"}
PROTECT_SUFFIXES = ("报告.md",)
# ⚠️ 测试钩子：仅供 `selftest` 的阴性对照使用（把它改成 False 后必须能删到交付物）。
#    生产路径恒为 True —— 它不是开关，是"让保护机制可被证伪"的接口。
HONOR_DELIVERABLE_PROTECTION = True

_SPLIT = re.compile(r"[,;、\n]+")      # 交付物字段里可能一次写多个路径
_BRACKET = re.compile(r"[（(].*?[）)]")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_yaml():
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        print("[ERROR] 缺 pyyaml。请用技能 venv 运行："
              "~/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe", file=sys.stderr)
        return None
    return yaml


def resolve_plan(arg: str) -> Path | None:
    p = Path(arg)
    if p.is_dir():
        p = p / "plan.yaml"
    if not p.is_file():
        p = Path.cwd() / p
    return p if p.is_file() else None


def is_file_like(tok: str) -> bool:
    """交付物字段里的一段是否是路径（而非描述性文字）。口径参照 checks_core._is_file_like。"""
    tok = tok.strip()
    if not tok or len(tok) > 260:
        return False
    if "/" in tok or "\\" in tok:
        return True
    return bool(re.search(r"\.[A-Za-z0-9]{1,6}$", tok))


def deliverable_paths(data: dict, base: Path) -> set:
    """把 plan.yaml 所有步骤的 `交付物` 解析成绝对路径集合（保护清单的第一优先级）。"""
    out = set()
    if not HONOR_DELIVERABLE_PROTECTION:
        return out
    for s in data.get("steps") or []:
        raw = str(s.get("交付物", "") or "")
        for part in _SPLIT.split(raw):
            part = _BRACKET.sub("", part).strip().strip("`\"'")
            if not is_file_like(part):
                continue
            cand = Path(part)
            if not cand.is_absolute():
                cand = base / part
            try:
                out.add(cand.resolve())
            except OSError:
                continue
    return out


def referenced_paths(skill_root: Path) -> set:
    """被 SKILL.md / references/*.md 反引号引用、且指向 tasks/ 的路径（同 archive_tasks 口径）。"""
    out = set()
    docs = [skill_root / "SKILL.md", *sorted((skill_root / "references").glob("*.md"))]
    for doc in docs:
        if not doc.exists():
            continue
        try:
            text = doc.read_text(encoding="utf-8")
        except OSError:
            continue
        for ref in REF_PATTERN.findall(text):
            if ref.startswith("tasks/"):
                out.add((skill_root / ref).resolve())
    return out


# 「本任务记录文件引用的 tmp 路径」抽取口径（v4.14.1 新增）。
# 只认 `tmp/` 或 `tmp\` 起头、且不含空白/引号/括号/全角标点的连续片段 —— **刻意从宽**：
# 多保护一项的代价是「少删一个中间产物」（可重来），漏保护一项的代价是
# 「记录里出现悬空引用」（不可逆，且与「文档写着有、实际不在」同源）。
_TMP_REF_RE = re.compile(r"tmp[\\/][^\s`\"'()\[\]{}<>，,；;：:、）】]+")


def referenced_in_task(task_dir: Path) -> set:
    """被**本任务自身的记录文件**（任务根 `*.md`）引用、且落在本任务 `tmp/` 下的路径。

    v4.14.1 新增。此前 `referenced_paths()` 只扫**技能自己的** `SKILL.md`／`references/*.md` ——
    而最可能引用本任务 `tmp/` 证据的恰恰是任务自己的记录（`三件套记录.md`、`自检-*.md`…）。
    缺口后果：任务记录里的 `tmp/...` 引用在清理后全部变成**悬空引用**，
    且 `engine_v4130/`（旧版引擎对照副本）这类**可重放证据**会被一并清掉。
    """
    out = set()
    try:
        tmp_root = (task_dir / "tmp").resolve()
    except OSError:
        return out
    # ⚠️ 刻意**只扫任务根 `*.md`**：`plan.yaml` 的 `交付物` 字段已由 `deliverable_paths()` 单独覆盖，
    #    若再把它算作「记录引用」，两套保护就会**重叠** —— 撤掉交付物保护时该项仍被这套兜住，
    #    于是 S4 阴性对照（"撤掉后必须能删到"）**恒判假绿**，等于毁掉「交付物保护有牙齿」的唯一证据。
    #    （实测踩过：把 plan.yaml 一并纳入后 S4 立刻 FAIL。）结论：**新增保护面必须先查它与既有面的重叠**。
    for doc in sorted(task_dir.glob("*.md")):
        if not doc.is_file():
            continue
        try:
            text = doc.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in _TMP_REF_RE.findall(text):
            try:
                cand = (task_dir / m).resolve()
            except OSError:
                continue
            if cand == tmp_root or tmp_root in cand.parents:
                out.add(cand)
    return out


def check_triggers(data: dict, gate_runner) -> tuple[bool, list, list]:
    """T1/T2/T3 —— 三条机器可判定的前置条件。返回 (是否通过, 通过项, 拒绝理由)。"""
    okk, bad = [], []

    steps = data.get("steps") or []
    not_done = [str(s.get("id", "?")) for s in steps if str(s.get("状态", "")).strip() != "完成"]
    if not steps:
        bad.append("T1：plan.yaml 无 steps")
    elif not_done:
        bad.append(f"T1：仍有 {len(not_done)} 步未完成（步骤 {'/'.join(not_done)}）—— 任务未收尾")
    else:
        okk.append(f"T1：全部 {len(steps)} 步状态均为『完成』")

    meta = data.get("meta") or {}
    fuse = str(meta.get("熔断状态", "") or "").strip()
    if fuse not in FUSE_OK:
        bad.append(f"T2：熔断状态为『{fuse}』—— 已熔断任务须保留现场，清理被禁止")
    else:
        okk.append("T2：熔断状态正常（未熔断）")

    fused_steps = [str(s.get("id", "?")) for s in steps if str(s.get("状态", "")).strip() == "熔断"]
    if fused_steps:
        bad.append(f"T2：步骤 {'/'.join(fused_steps)} 状态为『熔断』—— 清理被禁止")

    if bad:
        return False, okk, bad

    passed, detail = gate_runner()
    if not passed:
        bad.append(f"T3：交付物对账未清零（{detail}）—— 清理必须在交付之后")
    else:
        okk.append(f"T3：交付物对账 FAIL=0（{detail}）")
    return (not bad), okk, bad


def _gate_checks_py(plan_path: Path, base: Path, checks_py):
    """默认门禁实现：调技能自带 checks.py plan，只数 FAIL（口径与交付门禁同源）。"""
    def runner():
        if not checks_py or not Path(checks_py).is_file():
            return False, "checks.py 缺失 → 门禁不可用（不可逆动作 fail-closed）"
        try:
            p = subprocess.run([sys.executable, str(checks_py), "plan", str(plan_path), "--base", str(base)],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=180)
        except (OSError, subprocess.SubprocessError) as e:  # noqa: BLE001
            return False, f"checks.py 调用失败（{type(e).__name__}）→ fail-closed"
        out = (p.stdout or "") + (p.stderr or "")
        m = re.search(r"FAIL=(\d+)", out)
        if m is None:
            return False, "checks.py 未给出结果行 → 无法判定 → fail-closed"
        n = int(m.group(1))
        return (n == 0), f"FAIL={n}（exit {p.returncode}）"
    return runner


def trash_channel() -> tuple:
    """探测可恢复删除通道。返回 (通道名或 None, 说明)。

    ⚠️ 诚实边界：无法机器证明文件「确实进了回收站」。本函数只判断**通道是否存在**。
       本机实测：会话侧 `PYTHONPATH` 注入的 shim 会把 `shutil.rmtree` 导向回收站
       （见 checks_core.py v3.4.0/P1 的实测注释），但它**只劫持 rmtree，不劫持 unlink**。
       故本脚本目录删除可走回收站，而"精细模式"下的单文件删除不可恢复 —— 后者被单独标注。
    """
    try:
        import send2trash  # noqa: F401,PLC0415
        return "send2trash", "已安装 send2trash（文件与目录均可恢复）"
    except ImportError:
        pass
    pp = os.environ.get("PYTHONPATH", "")
    if "cli" in pp and "shim" in pp:
        return "shim-rmtree", "会话 shim 存在：**目录**删除走回收站；**单文件**删除不走（不可恢复）"
    return None, "未检测到可恢复删除通道（既无 send2trash，也无 shim）"


def collect(tmp_dir: Path, protected: set, task_dir: Path, skill_root: Path) -> tuple:
    """返回 (待删顶层项, 受保护而保留项)。仅扫 tmp_dir 一棵树；可删的整棵子树合并为一项。"""
    keep = []
    if not tmp_dir.is_dir():
        return [], keep
    refs = referenced_paths(skill_root) | referenced_in_task(task_dir)
    items = list(tmp_dir.rglob("*"))

    def why(p: Path):
        try:
            ap = p.resolve()
        except OSError:
            return None
        if ap in protected:
            return "交付物（`交付物` 字段登记）"
        if p.name in PROTECT_NAMES or any(p.name.endswith(s) for s in PROTECT_SUFFIXES):
            return "保护名单（留痕/证据文件）"
        if ap in refs:
            return "被技能手册或本任务记录引用"
        if ap == SELF or ap == task_dir:
            return "脚本自身或任务目录"
        return None

    prot = {p: w for p in items if (w := why(p))}
    prot_dirs = set()
    for p in prot:
        prot_dirs.update(a for a in p.parents if a != tmp_dir and tmp_dir in a.parents or a.parent == tmp_dir)

    kill = []

    def walk(p: Path):
        if p in prot:
            keep.append((p, prot[p]))
            return
        if p.is_dir():
            if p not in prot_dirs:
                kill.append(p)          # 整棵子树都可删 → 合并为一项
            else:
                for c in sorted(p.iterdir()):
                    walk(c)
            return
        kill.append(p)

    for c in sorted(tmp_dir.iterdir()):
        walk(c)
    return kill, keep


def measure(items: list) -> tuple:
    n = b = 0
    for p in items:
        try:
            if p.is_file():
                n += 1; b += p.stat().st_size
            elif p.is_dir():
                for q in p.rglob("*"):
                    if q.is_file():
                        n += 1; b += q.stat().st_size
        except OSError:
            pass
    return n, b


def remove_path(p: Path, channel, allow_hard: bool) -> tuple:
    """删除单项。占用类失败退避重试 1 次。返回 (成功, 走哪条通道)。"""
    if channel is None and not allow_hard and p.is_file():
        return False, "无可恢复通道且未加 --no-trash（fail-closed，未删除）"
    for attempt in (1, 2):
        try:
            if channel == "send2trash":
                from send2trash import send2trash  # noqa: PLC0415
                send2trash(str(p))
            elif p.is_dir():
                shutil.rmtree(p)            # shim 环境下属可恢复通道
            else:
                p.unlink()
            return True, channel or "unlink(不可恢复)"
        except OSError as e:
            if attempt == 2:
                return False, f"{type(e).__name__}: {e}"
            time.sleep(0.4)                 # 句柄未释放：退避一次再试
    return False, "未知失败"


def write_manifest(task_dir: Path, snaps: list) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = task_dir / f"清理清单-{ts}.txt"
    lines = [f"# 清理清单 —— {task_dir.name}",
             f"# 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             "# 用途：删除是不可逆动作，本清单是「删了什么」的永久证据（sha256 可复核）。",
             f"# 条目：{len(snaps)}", ""]
    lines += [f"{h}  {size:>9}  {rel}" for rel, size, h in snaps]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def gate_ok(plan_path: Path, base: Path, checks_py):
    return _gate_checks_py(plan_path, base, checks_py)()


def main_clean(args) -> int:
    yaml = _load_yaml()
    if yaml is None:
        return 2
    plan_path = resolve_plan(args.plan)
    if plan_path is None:
        print(f"[拒绝] 找不到 plan.yaml：{args.plan}")
        return 2
    try:
        data = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    except Exception as e:  # noqa: BLE001
        print(f"[拒绝] plan.yaml 不可解析：{e}")
        return 2

    meta = data.get("meta") or {}
    task_dir = plan_path.parent
    skill_root = SELF.parent.parent
    base = Path(args.base).resolve() if args.base else Path(str(meta.get("工作区根", "") or Path.cwd())).resolve()
    tmp_dir = task_dir / "tmp"
    checks_py = Path(args.checks_py) if args.checks_py else (skill_root / "scripts" / "checks.py")

    print("任务产物清理报告    " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(f"任务目录：{task_dir}")
    print(f"工作区根：{base}")
    print(f"模式：{'APPLY（真实删除）' if args.apply else 'DRY-RUN（仅打印计划）'}")
    print("=" * 72)

    passed, okk, bad = check_triggers(data, _gate_checks_py(plan_path, base, checks_py))
    print("---- 触发条件（四条 AND）----")
    for x in okk:
        print(f"  [ OK ] {x}")
    for x in bad:
        print(f"  [FAIL] {x}")
    print()
    if not passed:
        print("[拒绝] 触发条件不满足，未做任何改动（fail-closed）。")
        return 2

    channel, chan_note = trash_channel()
    print("---- 删除通道 ----")
    print(f"  通道：{channel or '无'}")
    print(f"  说明：{chan_note}")
    print()

    protected = deliverable_paths(data, base)
    protected |= {task_dir.resolve(), plan_path.resolve()}
    kill, keep = collect(tmp_dir, protected, task_dir, skill_root)

    print("---- 待清理（仅 tasks/<任务>/tmp/ 一棵树）----")
    if not kill:
        print("  （无）")
    for p in kill[:200]:
        try:
            rel = p.relative_to(task_dir)
            kin = "目录" if p.is_dir() else f"{p.stat().st_size:,} 字节"
        except OSError:
            rel, kin = p.name, "?"
        print(f"  · {rel}    {kin}")
    if len(kill) > 200:
        print(f"  … 另有 {len(kill) - 200} 项")
    nf, nb = measure(kill)
    print(f"  合计：{len(kill)} 个顶层项 / {nf} 个文件 / {nb:,} 字节")
    print()

    if keep:
        print("---- 受保护而保留（保护清单优先于删除清单）----")
        for p, why in keep:
            try:
                rel = p.relative_to(task_dir)
            except ValueError:
                rel = p
            print(f"  ✗ 保留 {rel}    —— {why}")
        print()

    if not args.apply:
        print("（DRY-RUN 结束，未删除任何文件。加 --apply 执行。）")
        return 0

    if not kill:
        print("[无操作] 无待清理项（幂等）。")
        return 0

    if channel is None and not args.no_trash:
        print("[拒绝] 未检测到可恢复删除通道，且未加 --no-trash —— 不可逆动作 fail-closed。")
        print("       出路：① 安装 send2trash；② 若确认接受不可恢复删除，显式加 --no-trash。")
        return 2

    snaps = []
    for p in kill:
        if p.is_file():
            snaps.append((str(p.relative_to(task_dir)).replace("\\", "/"), p.stat().st_size, sha256(p)))
        elif p.is_dir():
            for q in p.rglob("*"):
                if q.is_file():
                    snaps.append((str(q.relative_to(task_dir)).replace("\\", "/"), q.stat().st_size, sha256(q)))
    snaps.sort()
    manifest = write_manifest(task_dir, snaps)
    print(f"---- 已落快照 ----\n  {manifest.name}（{len(snaps)} 条，sha256 可复核）\n")

    print("---- 执行删除 ----")
    failures, done = [], []
    for p in kill:
        good, note = remove_path(p, channel, args.no_trash)
        try:
            rel = p.relative_to(task_dir)
        except ValueError:
            rel = p
        if good:
            done.append(p)
            print(f"  [ OK ] {rel}    ({note})")
        else:
            failures.append((p, note))
            print(f"  [FAIL] {rel}    —— {note}")
    print()

    print("---- 删后复核（双条件：删干净了 且 没删该留的）----")
    n_left = [p for p in kill if p.exists()]
    missing = []
    for p in protected:
        if p == task_dir.resolve() or p == plan_path.resolve():
            continue
        if p.exists():
            continue
        if p.name in PROTECT_NAMES or any(p.name.endswith(s) for s in PROTECT_SUFFIXES):
            continue                        # 保护名单里的文件本就不存在于 tmp/ 时不算误删
        missing.append(p)
    g_ok, g_detail = gate_ok(plan_path, base, checks_py)
    print(f"  待删项残留：{len(n_left)} 个")
    print(f"  交付物对账：{'PASS' if g_ok else 'FAIL'}（{g_detail}）")
    print(f"  [{'FAIL' if missing else ' OK '}] 交付物与留痕文件{'被误删：' + str(missing) if missing else '均完好'}")
    print()

    all_ok = not failures and not n_left and g_ok and not missing
    print(f"==== 结论：{'PASS' if all_ok else 'FAIL（本次清理未完成）'} ====")
    print(f"  已清理：{len(done)}/{len(kill)} 个顶层项 / {nf} 个文件 / {nb:,} 字节")
    print(f"  清单：{manifest.name}")
    for p, note in failures:
        print(f"  失败：{p} —— {note}")
    print("  ⚠️ 清理未完成**不影响已完成交付的有效性**，但不得被读成「工作区已干净」。")
    return 0 if all_ok else 1


# ── selftest（含阴性对照：证明触发门禁与保护清单**都有牙齿**）────────────────
TASK_NAME = "夹具任务-2026-01-01"


def _fixture(root: Path, *, status="完成", fuse="", with_deliv_in_tmp=True) -> Path:
    """构造一个自洽的夹具任务目录 —— 必须能通过 checks.py plan（否则 T3 会正确地拦下它）。"""
    task = root / "tasks" / TASK_NAME
    (task / "tmp" / "sub").mkdir(parents=True, exist_ok=True)
    (task / "out").mkdir(parents=True, exist_ok=True)
    (task / "out" / "result.txt").write_text("最终输出\n", encoding="utf-8")
    (task / "tmp" / "scratch.py").write_text("print(1)\n", encoding="utf-8")
    (task / "tmp" / "sub" / "probe.txt").write_text("中间产物\n", encoding="utf-8")
    (task / "tmp" / "确认表.md").write_text("留痕\n", encoding="utf-8")          # 测保护名单
    (task / "tmp" / "refed_evidence.txt").write_text("被任务记录引用的证据\n", encoding="utf-8")
    # v4.14.1：任务根记录**引用** tmp 证据 ⇒ 该证据必须被保护（否则清理会让记录出现悬空引用）。
    #   ⚠️ 记录里**只**引用这一个文件 —— 若一并引用 `tmp/sub/probe.txt`，`sub/` 整棵会被保护，
    #   下面「S2 tmp/ 子目录一并清除」的断言就会（正确地）失败。
    (task / "记录.md").write_text("证据见 `tmp/refed_evidence.txt`。\n", encoding="utf-8")
    if with_deliv_in_tmp:
        (task / "tmp" / "declared_deliverable.md").write_text("被登记为交付物\n", encoding="utf-8")
    # ⚠️ 任务根**不放** trace.jsonl：那会启用「步骤闭环不变量（trace 自证）」判据而 FAIL。
    #    保护名单的测试在 tmp/ 内同样成立，无需借任务根的文件来测。
    deliv = f"tasks/{TASK_NAME}/out/result.txt"
    if with_deliv_in_tmp:
        deliv += f", tasks/{TASK_NAME}/tmp/declared_deliverable.md"
    plan = (
        "meta:\n"
        "  任务: \"selftest 夹具\"\n"
        f"  工作区根: \"{root.as_posix()}\"\n"
        "  创建时间: \"2026-01-01 00:00\"\n"
        "  验证信号: \"夹具：out/result.txt 存在\"\n"
        # ⚠️ v4.14.0 起必须**显式声明层级**：本夹具不含任何 L2 全流程字段，
        #    不声明即「层级不明」⇒ 按 fail-closed 判 7 条 FAIL ⇒ T3 门禁
        #    「只数 FAIL」会（正确地）拦下它，整个 selftest 连带红 10 项。
        #    声明 L1 后由 flush_absent 走 L1 出口 ⇒ 汇成 1 条 SKIP、FAIL=0。
        "  任务层级: \"L1\"\n"
        "  复盘沉淀: \"无沉淀：本目录只是 selftest 夹具，没有可沉淀内容\"\n"
        f"  熔断状态: \"{fuse}\"\n"
        "steps:\n"
        "  - id: 1\n"
        "    做什么: \"产出结果\"\n"
        "    输入: \"无\"\n"
        "    预期产出: \"result.txt\"\n"
        "    验证方式: \"文件存在\"\n"
        f"    状态: {status}\n"
        f"    交付物: \"{deliv}\"\n"
    )
    (task / "plan.yaml").write_text(plan, encoding="utf-8")
    return task


def _run(task: Path, root: Path, apply=False, extra=(), script=SELF):
    cmd = [sys.executable, str(script), "clean", "--plan", str(task / "plan.yaml"),
           "--base", str(root), "--checks-py", str(SELF.parent / "checks.py")]
    if apply:
        cmd.append("--apply")
    cmd += list(extra)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=300)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _tamper(dst: Path, *, kill_names=False, kill_deliv=False, kill_taskref=False) -> Path:
    """复制本脚本并按需撤掉一处保护 —— 阴性对照的核心：**撤掉后必须能删到受保护项**。"""
    text = SELF.read_text(encoding="utf-8")
    if kill_names:
        text = text.replace(
            'PROTECT_NAMES = {"plan.yaml", "trace.jsonl", "_metrics.jsonl", "确认表.md", "熔断报告.md"}',
            "PROTECT_NAMES = set()").replace(
            'PROTECT_SUFFIXES = ("报告.md",)', "PROTECT_SUFFIXES = ()")
    if kill_deliv:
        text = text.replace("HONOR_DELIVERABLE_PROTECTION = True", "HONOR_DELIVERABLE_PROTECTION = False")
    if kill_taskref:
        # v4.14.1 新增保护面的阴性对照：只撤「本任务记录引用」这一半引用面。
        text = text.replace(
            "refs = referenced_paths(skill_root) | referenced_in_task(task_dir)",
            "refs = referenced_paths(skill_root)")
    dst.write_text(text, encoding="utf-8")
    return dst


def _seg(out: str, key: str) -> str:
    """取输出中 `---- <key>… ----` 到下一个 `----` 之间的正文。"""
    parts = out.split("----")
    for i, x in enumerate(parts):
        if key in x and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def main_selftest() -> int:
    n_ok = n_bad = 0

    def case(name, cond, extra=""):
        nonlocal n_ok, n_bad
        if cond:
            n_ok += 1
            print(f"  [ OK ] {name}" + (f"  —— {extra}" if extra else ""))
        else:
            n_bad += 1
            print(f"  [FAIL] {name}" + (f"  —— {extra}" if extra else ""))

    with tempfile.TemporaryDirectory(prefix="aiwf_clean_") as td:
        R = Path(td)

        # ── S1/S2 正例：dry-run 不出手、--apply 真删且双条件成立、幂等
        r1 = R / "c1"; r1.mkdir()
        t1 = _fixture(r1)
        rc, out = _run(t1, r1)
        case("S1 dry-run 退出码 0", rc == 0, f"exit={rc}")
        case("S1 未删除任何文件", (t1 / "tmp" / "scratch.py").exists())
        case("S1 保护名单项不出现在待删清单", "确认表.md" not in _seg(out, "待清理"), "")
        case("S1 交付物不出现在待删清单", "declared_deliverable.md" not in _seg(out, "待清理"))
        case("S1 保护项被显式列出并说明理由",
             "确认表.md" in _seg(out, "受保护") and "交付物" in _seg(out, "受保护"))
        case("S1 本任务记录引用的 tmp 项不出现在待删清单",
             "refed_evidence.txt" not in _seg(out, "待清理"))

        r2 = R / "c2"; r2.mkdir()
        t2 = _fixture(r2)
        rc, out = _run(t2, r2, apply=True, extra=("--no-trash",))
        case("S2 --apply 退出码 0", rc == 0, f"exit={rc}")
        case("S2 tmp/ 中间产物已清除", not (t2 / "tmp" / "scratch.py").exists())
        case("S2 tmp/ 子目录一并清除", not (t2 / "tmp" / "sub").exists())
        case("S2 交付物仍在", (t2 / "out" / "result.txt").exists())
        case("S2 tmp 内的交付物仍在（交付物优先于容器约定）", (t2 / "tmp" / "declared_deliverable.md").exists())
        case("S2 tmp 内的保护名单项仍在", (t2 / "tmp" / "确认表.md").exists())
        case("S2 本任务记录引用的 tmp 项仍在（防记录悬空引用）",
             (t2 / "tmp" / "refed_evidence.txt").exists())
        case("S2 生成了清理清单", bool(list(t2.glob("清理清单-*.txt"))))
        rc2, out2 = _run(t2, r2, apply=True, extra=("--no-trash",))
        case("S2 幂等：重跑报无待清理项", rc2 == 0 and "无操作" in out2, f"exit={rc2}")

        # ── S3/S4 阴性对照：撤掉保护 → 必须能删到受保护项（否则保护是"假的"）
        r3 = R / "c3"; r3.mkdir()
        tp = _tamper(R / "tamper_names.py", kill_names=True)
        t3 = _fixture(r3)
        rc, out = _run(t3, r3, apply=True, extra=("--no-trash",), script=tp)
        gone3 = not (t3 / "tmp" / "确认表.md").exists()
        case("S3 阴性对照（撤掉 PROTECT_NAMES）→ 保护名单项被删除",
             gone3,
             "撤掉后已删掉 ⇒ 该保护确实由该名单实现（非假绿）" if gone3
             else "撤掉后仍删不掉 ⇒ 该保护不是它实现的（假绿）")

        r4 = R / "c4"; r4.mkdir()
        td2 = _tamper(R / "tamper_deliv.py", kill_deliv=True)
        t4 = _fixture(r4)
        rc, out = _run(t4, r4, apply=True, extra=("--no-trash",), script=td2)
        gone4 = not (t4 / "tmp" / "declared_deliverable.md").exists()
        case("S4 阴性对照（撤掉交付物保护）→ tmp 内的交付物被删除",
             gone4,
             "撤掉后已删掉 ⇒ 该保护确实由交付物清单实现（非假绿）" if gone4
             else "撤掉后仍删不掉 ⇒ 该保护不是它实现的（假绿）")

        r4b = R / "c4b"; r4b.mkdir()
        tt = _tamper(R / "tamper_taskref.py", kill_taskref=True)
        t4b = _fixture(r4b)
        rc, out = _run(t4b, r4b, apply=True, extra=("--no-trash",), script=tt)
        gone4b = not (t4b / "tmp" / "refed_evidence.txt").exists()
        case("S4b 阴性对照（撤掉任务记录引用保护）→ 被引用项被删除",
             gone4b,
             "撤掉后已删掉 ⇒ 该保护确实由本任务记录引用实现（非假绿）" if gone4b
             else "撤掉后仍删不掉 ⇒ 该保护不是它实现的（假绿）")

        # ── S5/S6 阴性对照：触发条件不满足 → 拒绝且不动手
        r5 = R / "c5"; r5.mkdir()
        t5 = _fixture(r5, status="进行中")
        rc, out = _run(t5, r5, apply=True, extra=("--no-trash",))
        case("S5 阴性对照（有步骤未完成）→ 拒绝 exit 2", rc == 2 and "T1" in out, f"exit={rc}")
        case("S5 拒绝时未删除任何文件", (t5 / "tmp" / "scratch.py").exists())

        r6 = R / "c6"; r6.mkdir()
        t6 = _fixture(r6, fuse="已熔断")
        rc, out = _run(t6, r6, apply=True, extra=("--no-trash",))
        case("S6 阴性对照（熔断状态=已熔断）→ 拒绝 exit 2", rc == 2 and "T2" in out, f"exit={rc}")
        case("S6 拒绝时未删除任何文件", (t6 / "tmp" / "scratch.py").exists())

        # ── S7 单元：T3 门禁的两种输入
        sys.path.insert(0, str(SELF.parent))
        try:
            import cleanup_task as _ct  # noqa: PLC0415
            data = {"meta": {"熔断状态": ""}, "steps": [{"id": 1, "状态": "完成"}]}
            ok1, _, bad1 = _ct.check_triggers(data, lambda: (False, "FAIL=1"))
            ok2, _, bad2 = _ct.check_triggers(data, lambda: (True, "FAIL=0"))
            case("S7 T3：对账未清零即拒绝", (not ok1) and any("T3" in b for b in bad1))
            case("S7 T3：对账清零才放行", ok2 and not bad2)
        except Exception as e:  # noqa: BLE001
            case("S7 T3 门禁可注入测试", False, f"{type(e).__name__}: {e}")
        finally:
            if str(SELF.parent) in sys.path:
                sys.path.remove(str(SELF.parent))

        # ── S8 幂等：tmp 目录整体不存在时 --apply 不报错
        r7 = R / "c7"; r7.mkdir()
        t7 = _fixture(r7, with_deliv_in_tmp=False)   # 交付物不在 tmp/ 里，删掉 tmp 不影响 T3
        shutil.rmtree(t7 / "tmp")
        rc, out = _run(t7, r7, apply=True, extra=("--no-trash",))
        case("S8 tmp 不存在时 --apply 幂等 exit 0", rc == 0 and "无操作" in out, f"exit={rc}")

    print()
    print(f"==== selftest：{n_ok}/{n_ok + n_bad} 通过，FAIL={n_bad} ====")
    return 0 if n_bad == 0 else 1


def main() -> None:
    ap = argparse.ArgumentParser(description="任务产物清理（默认 dry-run）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("clean", help="清理某任务的中间产物（默认 dry-run，--apply 才删）")
    p.add_argument("--plan", required=True, help="plan.yaml 路径或任务目录")
    p.add_argument("--base", default="", help="相对路径解析基准（默认取 plan 的 meta.工作区根）")
    p.add_argument("--apply", action="store_true", help="真正执行删除（默认只打印计划）")
    p.add_argument("--no-trash", action="store_true",
                   help="显式接受不可恢复删除（无回收站通道时的唯一出路；默认 fail-closed 拒绝）")
    p.add_argument("--checks-py", default="", help="checks.py 路径（默认取技能自带）")

    sub.add_parser("selftest", help="内置自检（含阴性对照）")

    args = ap.parse_args()
    if args.cmd == "selftest":
        raise SystemExit(main_selftest())
    raise SystemExit(main_clean(args))


if __name__ == "__main__":
    main()
