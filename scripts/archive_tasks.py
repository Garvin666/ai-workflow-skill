#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务目录归档：先快照 → 移动 → 后核对（**只移动不删除**，默认 dry-run）。

为什么需要它
------------
`checks.py status` 会周期性提示「任务目录 N 个 > 阈值 10，建议归档」，但只有建议、
没有工具，且归档有两个**非显然的坑**，手工做容易踩：

1. **归档会打断「文档引用完整性」。** `checks.py skill` 会扫 `SKILL.md` 与
   `references/*.md` 中**反引号包裹、后缀 md/yaml/py/ps1** 的路径，并用
   `skill_dir/ref` 做存在性校验。若某任务目录正被这些文档引用（实测：`references/ops.md`
   引用了 `tasks/技能增强-ai-workflow-v2.4.3-2026-09-10/_test_server.py`），
   归档它**会直接使自检 FAIL**。
   → 本脚本把这条做成**前置门禁**：被文档引用的目录自动剔除并显著提示。

2. **手工移动无法自证没丢文件。** 目录名含中文，`mv` 出错时症状不明显。
   → 本脚本用「移动前逐文件 sha256 快照 == 移动后快照」逐项自证零丢失。

用法
----
    # 只看计划（默认，不动任何文件）
    python scripts/archive_tasks.py --root . --older-than 2026-09-11
    python scripts/archive_tasks.py --root . --dirs "任务A-2026-09-10,任务B-2026-09-10"

    # 执行
    python scripts/archive_tasks.py --root . --older-than 2026-09-11 --apply

3. **（v4.3.0）日期不等于使用度**：一个创建较早、却仍被反复引用的任务目录，只按日期会被卷走。
   故叠加两个**使用度**维度与一个 **pinned** 声明，三者**默认全关**（不传参数＝与旧版行为一致）：
       --keep-recent-days N   最近 N 天内有改动的目录跳过
       --keep-used            目录内含 _metrics.jsonl / trace.jsonl（已有收尾记录）则跳过
       --pin "A,B"            显式 pinned；或写进 `tasks/_pinned.txt`（每行一个目录名）
   pinned 是**意图声明**，不因 `--dirs` 点名而被推翻。

退出码：0 成功（含 dry-run）／1 移动后校验失败／2 前置检查拒绝
"""
import argparse
import hashlib
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# 与 checks.py 的「文档引用完整性」同口径（那边是唯一事实源，此处只复刻判定规则）
REF_PATTERN = re.compile(r"`([A-Za-z0-9_./\u4e00-\u9fff-]+\.(?:md|yaml|py|ps1))`")
DATE_TAIL = re.compile(r"^(?P<base>.+?)-(?P<date>\d{4}-\d{2}-\d{2})$")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(d: Path):
    """返回 [(相对路径, 字节数, sha256), ...]，按相对路径排序。"""
    return sorted(
        (str(p.relative_to(d)).replace("\\", "/"), p.stat().st_size, sha256(p))
        for p in d.rglob("*") if p.is_file()
    )


def referenced_dirs(root: Path, names):
    """返回 {目录名: [引用位置, ...]}。只扫 SKILL.md 与 references/*.md（与 checks.py 同口径）。"""
    hits = {}
    docs = [root / "SKILL.md", *sorted((root / "references").glob("*.md"))]
    for doc in docs:
        if not doc.exists():
            continue
        for ref in REF_PATTERN.findall(doc.read_text(encoding="utf-8")):
            if not ref.startswith("tasks/"):
                continue
            for n in names:
                if ref == f"tasks/{n}" or ref.startswith(f"tasks/{n}/"):
                    hits.setdefault(n, []).append(f"{doc.name} -> {ref}")
    return hits


def month_of(name: str) -> str:
    m = DATE_TAIL.match(name)
    return m.group("date")[:7] if m else "undated"


# ── 使用度与 pinned（v4.3.0 / 批次 B-3）──────────────────────────────────────
# 背景：原脚本只有"按日期"一个维度 —— 但**日期不等于使用度**。一个 30 天前创建、却仍在被
# 反复引用的任务目录，按日期会被卷走；而"只移动不删除"虽保证可恢复，恢复成本仍不为零。
#
# ⚠️ 三条既有不变量（只移动不删 / 引用门禁 / sha256 自证）**一条未动**，本组只做**叠加跳过**。
# ⚠️ 新增维度**全部默认关闭**：`--keep-recent-days 0`、`--keep-used` 关、无 `--pin` 参数时
#    仅在 `tasks/_pinned.txt` **存在**才生效 —— 因此**不传新参数时的行为与旧版逐字节一致**。
USAGE_MARKERS = ("_metrics.jsonl", "trace.jsonl")


def latest_mtime(d: Path) -> float:
    """目录内所有文件的**最新** mtime。0.0 表示读不到（保守：调用方按"很旧"处理）。"""
    newest = 0.0
    for p in d.rglob("*"):
        if p.is_file():
            try:
                newest = max(newest, p.stat().st_mtime)
            except OSError:
                pass
    return newest


def load_pins(root: Path, cli_pins: str, pin_file: str) -> tuple[set[str], list[str]]:
    """pinned 目录集合 + 来源说明。来源必须**被打印出来**（否则"为什么没归档"无法解释）。"""
    pins: set[str] = set()
    sources: list[str] = []
    if cli_pins:
        pins.update(s.strip() for s in cli_pins.split(",") if s.strip())
        sources.append("--pin")
    pf = Path(pin_file) if pin_file else root / "tasks" / "_pinned.txt"
    if pf.exists():
        for ln in pf.read_text(encoding="utf-8-sig").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                pins.add(ln)
        if pins or pin_file:
            sources.append(str(pf))
    return pins, sources


def main() -> int:
    ap = argparse.ArgumentParser(description="任务目录归档（只移动不删除，默认 dry-run）")
    ap.add_argument("--root", default=".", help="技能目录（含 tasks/），默认当前目录")
    ap.add_argument("--dirs", default="", help="要归档的目录名，逗号分隔")
    ap.add_argument("--older-than", default="", help="归档早于该日期（YYYY-MM-DD）的任务")
    ap.add_argument("--apply", action="store_true", help="真正执行移动（默认只打印计划）")
    ap.add_argument("--pin", default="",
                    help="pinned 目录名，逗号分隔；这些目录**不被归档**（v4.3.0）")
    ap.add_argument("--pin-file", default="",
                    help="pinned 清单文件（每行一个目录名，# 注释）。默认自动读 "
                         "<root>/tasks/_pinned.txt —— **仅在文件存在时生效**（v4.3.0）")
    ap.add_argument("--keep-recent-days", type=int, default=0,
                    help="最近 N 天内有改动的目录跳过（默认 0 = 不启用，与旧行为一致，v4.3.0）")
    ap.add_argument("--keep-used", action="store_true",
                    help="目录内含 _metrics.jsonl/trace.jsonl（已有收尾/使用记录）则跳过（默认关，v4.3.0）")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    tasks = root / "tasks"
    if not tasks.is_dir():
        print(f"[拒绝] tasks/ 不存在：{tasks}")
        return 2

    all_dirs = sorted(d.name for d in tasks.iterdir() if d.is_dir() and not d.name.startswith("_"))
    before_n = len(all_dirs)

    print("任务目录归档报告    " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(f"技能目录：{root}")
    print(f"模式：{'APPLY（真实移动）' if args.apply else 'DRY-RUN（仅打印计划）'}")
    print("=" * 72)
    print(f"当前 tasks/ 下任务目录：{before_n} 个（阈值 10）")
    print()

    # ---- 选定归档集 ----
    if args.dirs and args.older_than:
        print("[拒绝] --dirs 与 --older-than 只能给一个")
        return 2
    if args.dirs:
        want = [s.strip() for s in args.dirs.split(",") if s.strip()]
        unknown = [n for n in want if n not in all_dirs]
        if unknown:
            print(f"[拒绝] 这些目录不在 tasks/ 下：{unknown}")
            return 2
    elif args.older_than:
        want = [n for n in all_dirs
                if (m := DATE_TAIL.match(n)) and m.group("date") < args.older_than]
        if not want:
            print(f"[无操作] 没有早于 {args.older_than} 的任务目录")
            return 0
    else:
        print("[拒绝] 必须给 --dirs 或 --older-than")
        return 2

    # ---- 前置门禁：被文档引用的目录剔除 ----
    refs = referenced_dirs(root, want)

    # ---- v4.3.0：使用度 / pinned 叠加跳过（三项新维度全默认关闭 → 不传参数时零影响）----
    pins, pin_src = load_pins(root, args.pin, args.pin_file)
    skipped: dict[str, str] = {}
    now = time.time()
    for n in want:
        if n in refs:
            continue
        if n in pins:
            skipped[n] = "pinned（来源：%s）" % ("、".join(pin_src) or "--pin")
            continue
        if args.keep_recent_days > 0:
            newest = latest_mtime(tasks / n)
            age = (now - newest) / 86400.0 if newest else 1e6
            if age < args.keep_recent_days:
                skipped[n] = "%.1f 天前仍有改动（< --keep-recent-days=%d）" % (age, args.keep_recent_days)
                continue
        if args.keep_used:
            marks = [m for m in USAGE_MARKERS if (tasks / n / m).exists()]
            if marks:
                skipped[n] = "含使用记录 %s（--keep-used）" % "、".join(marks)
                continue

    movable = [n for n in want if n not in refs and n not in skipped]

    print("---- 选定归档集 ----")
    for n in want:
        # ⚠️ 引用剔除沿用**原标签**（`✗ 剔除`），不加后缀 —— 未启用新维度时输出必须与旧版
        #    逐字节一致；只有**新维度**造成的跳过才用新标签 `✗ 跳过`，便于二者区分。
        if n in refs:
            tag = "✗ 剔除"
        elif n in skipped:
            tag = "✗ 跳过（使用度/pinned）"
        else:
            tag = "· 待归档"
        print(f"  {tag}  {n}")
    print()

    if skipped:
        print("---- 跳过明细（v4.3.0：使用度 / pinned）----")
        for n, why in sorted(skipped.items()):
            print(f"  - {n}：{why}")
        print("  说明：pinned 是**意图声明**，不因 --dirs 点名而被推翻 —— 想归档须先从清单移除。")
        print()

    if refs:
        print("[门禁] 以下目录被文档引用，归档会使「文档引用完整性」FAIL，已剔除：")
        for n, where in sorted(refs.items()):
            print(f"  - {n}")
            for w in where:
                print(f"      {w}")
        print("  若确需归档：先更新这些引用指向的新位置（或改用不随位置变化的引用写法）。")
        print()

    if not movable:
        print("[拒绝] 剔除后无可归档目录，未做任何改动。")
        return 2

    # ---- 快照 ----
    print(f"---- 计划移动 {len(movable)} 个目录 ----")
    snaps = {}
    total_files = total_bytes = 0
    for n in movable:
        s = snapshot(tasks / n)
        snaps[n] = s
        nb = sum(x[1] for x in s)
        total_files += len(s)
        total_bytes += nb
        print(f"  - {n}    {len(s)} 个文件 / {nb:,} 字节")
    print(f"  合计：{total_files} 个文件 / {total_bytes:,} 字节")
    print()

    if not args.apply:
        print("（DRY-RUN 结束，未移动任何文件。加 --apply 执行。）")
        return 0

    # ---- 移动 ----
    print("---- 执行移动 ----")
    failures, verified = [], []
    for n in movable:
        src, dst = tasks / n, tasks / "_archive" / month_of(n) / n
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            failures.append(f"{n}：目标已存在，拒绝覆盖")
            print(f"  [失败] {n}：目标已存在 {dst}")
            continue
        try:
            shutil.move(str(src), str(dst))
        except Exception as e:  # noqa: BLE001
            failures.append(f"{n}：移动异常 {e}")
            print(f"  [失败] {n} -> {e}")
            continue
        after = snapshot(dst)
        if after == snaps[n]:
            verified.append(n)
            print(f"  [ OK ] {n}  ({len(after)} 文件，sha256 逐项一致)")
        else:
            failures.append(f"{n}：移动前后快照不一致")
            print(f"  [失败] {n}  移动前后快照不一致")

    # ---- 核对 ----
    after_dirs = sorted(d.name for d in tasks.iterdir() if d.is_dir() and not d.name.startswith("_"))
    print()
    print("---- 移动后核对 ----")
    print(f"tasks/ 下剩余任务目录：{len(after_dirs)} 个")
    for d in after_dirs:
        print(f"  - {d}")
    lost = [n for n in all_dirs if n not in after_dirs and n not in verified]
    if lost:
        print(f"[失败] 来源目录既不在 tasks/ 又未成功归档：{lost}")
        failures.append(f"目录去向不明：{lost}")
    else:
        print("[ OK ] 来源目录去向全部有据（已归档 或 仍原位）")
    print()

    ok_all = not failures and len(verified) == len(movable)
    print(f"==== 结论：{'PASS' if ok_all else 'FAIL'} ====")
    print(f"  移动并逐项校验：{len(verified)}/{len(movable)}")
    print(f"  任务目录 {before_n} 个 -> {len(after_dirs)} 个")
    print(f"  归档文件总数：{total_files} 个（只移动，未删除任何文件）")
    for f in failures:
        print(f"  失败：{f}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
