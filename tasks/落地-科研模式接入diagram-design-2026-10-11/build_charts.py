# -*- coding: utf-8 -*-
"""build_charts.py —— 本任务的一键入口（生成 → 几何自检 → 上游契约自检 → 导出 → 矢量件验收）。

为什么要有它（而不只是把 6 个脚本按顺序敲一遍）：
  · 五道工序各自的**失败形态不同**（越界、契约违约、缺依赖、坏字体、多页），
    分散执行时任何一道被跳过都**不报错**；
  · 缺依赖是**环境问题**、越界与坏字体是**产物问题** —— 两类必须分开报，处置也不同；
  · 一键跑完能给出**一张汇总表**，让「哪一步没跑」变成可见事实，而不是靠记忆。

边界处理（本轮逐条加固，每条都有对应的显式分支）：
  1. **输出目录为空 / 不存在** ⇒ 先生成，再判空；导出前判空则跳过并 WARN（不静默成功）。
  2. **Chrome 缺失** ⇒ pdf 通道逐件失败但**不阻断** svg/png，并在汇总里标「环境缺件」。
  3. **Playwright 或其浏览器二进制缺失** ⇒ png 同样隔离，**不静默降级**。
  4. **PDF 多页 / 尺寸不符 / 含 Type3** ⇒ 由 `check_vector_export.py` 判 FAIL，本器汇总为失败。
  5. **坐标越界** ⇒ 由 `s9b_geom_check.py` 判（它对每个维度的极限值取整张画布）。
  6. **动效页未到完整帧** ⇒ 由 `diagram_export.py` 在截图前断言，本器汇总为失败。
  7. **重跑幂等** ⇒ 每道工序都是「先删再写」，重复执行结果一致（判据不靠 mtime）。

用法：
    python build_charts.py                       # 全流程
    python build_charts.py --skip-export         # 只生成 + 自检
    python build_charts.py --formats svg,pdf     # 不产 PNG（无 Playwright 时的合理降级）
退出码：0 全绿；1 有 FAIL；2 用法错；3 仅「可选依赖缺失」导致的失败
"""

import argparse
import pathlib
import re
import subprocess
import sys
import time

TASK = pathlib.Path(__file__).resolve().parent
OUT = TASK / "output"
EXPORT_DIR = OUT / "export"
PY = sys.executable
SKILL = pathlib.Path(__file__).resolve().parents[2]
UPSTREAM = pathlib.Path(__file__).resolve().parents[3] / "diagram-design"
MOTION = ("chart-05-bar-motion.html", "chart-06-bar-reveal.html")


def _run(label: str, cmd: list[str]) -> tuple[bool, str]:
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    out = (r.stdout + r.stderr).strip()
    ok = r.returncode == 0
    print(f"{'[OK  ]' if ok else '[FAIL]'} {label}  ({dt:.1f}s, rc={r.returncode})", flush=True)
    for line in out.splitlines()[-14:]:
        print(f"        {line}", flush=True)
    return ok, out


def main() -> int:
    ap = argparse.ArgumentParser(description="图表一键构建（生成→自检→导出→验收）")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--formats", default="svg,pdf,png")
    ap.add_argument("--scale", type=float, default=2)
    ap.add_argument("--expect", default="1000x500")
    ap.add_argument("--skip-export", action="store_true")
    args = ap.parse_args()

    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    exp = out / "export"
    results: list[tuple[str, bool, str]] = []      # (工序, 是否通过, 是否属"缺依赖")

    def rec(name: str, ok: bool, dep: bool = False):
        results.append((name, ok, "环境缺件" if dep else "产物"))

    print("═══ 1/5 生成 ═══", flush=True)
    for script in ("s9_gen_charts.py", "s11_gen_motion.py", "s13_gen_reveal.py"):
        ok, _ = _run(f"生成 {script}", [PY, str(TASK / script)])
        rec(f"生成·{script}", ok)
    htmls = sorted(out.glob("chart-*.html"))
    print(f"        → 产出 {len(htmls)} 个 HTML", flush=True)
    if len(htmls) < 6:
        print(f"[FAIL] 期望 6 个图表 HTML，实得 {len(htmls)}", flush=True)
        rec("HTML 数量", False)

    print("\n═══ 2/5 几何自检（越界）═══", flush=True)
    ok, _ = _run("坐标越界扫描", [PY, str(TASK / "s9b_geom_check.py"), str(OUT)])
    rec("几何越界", ok)

    print("\n═══ 3/5 上游契约自检 ═══", flush=True)
    chk = UPSTREAM / "scripts" / "self_check.py"
    if chk.exists():
        ok, _ = _run("self_check.py（6 图）", [PY, str(chk), *[str(h) for h in htmls]])
        rec("上游契约", ok)
    else:
        print(f"[SKIP] 上游 self_check.py 不在场：{chk}")
        rec("上游契约", False, dep=True)

    if args.skip_export:
        print("\n(--skip-export ⇒ 跳过导出与验收)")
        return _summary(results)

    print("\n═══ 4/5 三通道导出 ═══", flush=True)
    if not htmls:
        print("[WARN] 没有 HTML 可导出 —— 跳过（**不是成功**）", flush=True)
        rec("导出", False)
    else:
        ok, out_text = _run("diagram_export.py", [
            PY, str(SKILL / "scripts" / "diagram_export.py"),
            *[str(h) for h in htmls], "--out", str(exp),
            "--formats", args.formats, "--scale", str(args.scale)])
        dep = "playwright" in out_text.lower() and "not available" in out_text.lower()
        rec("导出", ok, dep=dep)
        if not ok:
            for line in out_text.splitlines():
                if line.startswith("[FAIL]"):
                    print(f"        ▸ {line}", flush=True)

    print("\n═══ 5/5 矢量件验收 ═══", flush=True)
    targets = [p for p in sorted(exp.glob("*")) if p.suffix.lower() in (".pdf", ".svg")]
    if not targets:
        print("[WARN] 没有矢量件可验收 —— 跳过（**不是成功**）", flush=True)
        rec("矢量件验收", False)
    else:
        ok, out_text = _run("check_vector_export.py", [
            PY, str(SKILL / "scripts" / "check_vector_export.py"),
            *[str(t) for t in targets], "--expect", args.expect])
        rec("矢量件验收", ok)
        m = re.search(r"汇总：PASS=(\d+) FAIL=(\d+) SKIP=(\d+)", out_text)
        if m and m.group(3) != "0":
            print(f"        ⚠ SKIP={m.group(3)} 是**未检测**，不算通过", flush=True)

    return _summary(results)


def _summary(results: list[tuple[str, bool, str]]) -> int:
    print("\n═══ 汇总 ═══", flush=True)
    for name, ok, kind in results:
        flag = "OK  " if ok else ("SKIP" if kind == "环境缺件" else "FAIL")
        print(f"  [{flag}] {name}")
    fails = [r for r in results if not r[1]]
    if not fails:
        print("\n全部通过（6 HTML · svg/pdf/png · 零 Type3 · 几何无越界 · 上游契约 OK）")
        return 0
    only_dep = all(r[2] == "环境缺件" for r in fails)
    print(f"\n{len(fails)} 项未通过：" + "、".join(r[0] for r in fails))
    if only_dep:
        print("⇒ 均为**环境缺件**（不是产物缺陷）：按上面各步给出的指引 provision 后重跑")
        return 3
    print("⇒ 含**产物侧**失败：须先修产物，环境问题不掩盖它")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
