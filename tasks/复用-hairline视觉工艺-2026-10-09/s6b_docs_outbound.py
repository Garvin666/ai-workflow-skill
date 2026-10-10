"""s6b: ① 把交付文档里的**本机主目录路径**改成 `~/.workbuddy/…` 占位（出站扫描 FAIL 项）；
        ② 更新 `确认表.md`：前置裁决对齐**实定名**（H2/H3 与原表不符）＋ 补验证结论 ＋ 修已知限制。

纪律同上：同文件多处编辑串行 ＋ 逐处「锚点恰 1 次」断言 ＋ 写盘后回读复核 ＋ 幂等（看目标态）。
"""
import pathlib
import subprocess
import sys

# 原为硬编码本机绝对路径（出站清单第 4 项）⇒ 改由 __file__ 推导
SKILL = pathlib.Path(__file__).resolve().parents[2]
TASK = SKILL / "tasks" / "复用-hairline视觉工艺-2026-10-09"
HOME = str(SKILL.parents[2])

EDITS = [
    # ── 出站扫描 FAIL：本机主目录路径 → 占位 ──
    ("确认表.md", "工作区根 占位",
     "- **工作区根**：`C:\\Users\\26717\\.workbuddy\\skills\\ai-workflow`（技能自身演进类任务，按本仓契约落技能目录）",  # outbound-scan:allow（本行是文档改前原文，编辑锚点不可改）
     "- **工作区根**：`~/.workbuddy/skills/ai-workflow`（技能自身演进类任务，按本仓契约落技能目录；本机绝对路径见 `plan.yaml` 的 `meta.工作区根`，此处按出站口径写占位）"),
    ("确认表.md", "六要素第 6 行 占位",
     "| ⑥ 工作区根 | `C:\\Users\\26717\\.workbuddy\\skills\\ai-workflow`（上表第 3 行） |",  # outbound-scan:allow（本行是文档改前原文，编辑锚点不可改）
     "| ⑥ 工作区根 | `~/.workbuddy/skills/ai-workflow`（上表第 3 行） |"),
    ("影响面实测.md", "工作区根 占位",
     "> 任务：把 hairline 视觉工艺复用进 ai-workflow（L2）· 工作区根 `C:\\Users\\26717\\.workbuddy\\skills\\ai-workflow`",  # outbound-scan:allow（本行是文档改前原文，编辑锚点不可改）
     "> 任务：把 hairline 视觉工艺复用进 ai-workflow（L2）· 工作区根 `~/.workbuddy/skills/ai-workflow`"),
    ("影响面实测.md", "复算命令 PY 占位",
     'PY="C:/Users/26717/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"',  # outbound-scan:allow（本行是文档改前原文，编辑锚点不可改）
     'PY="$HOME/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"   # 技能自带 venv'),
    ("影响面实测.md", "复算命令 cd 占位",
     'cd "C:/Users/26717/.workbuddy/skills/ai-workflow"',  # outbound-scan:allow（本行是文档改前原文，编辑锚点不可改）
     'cd ~/.workbuddy/skills/ai-workflow'),

    # ── 确认表：前置裁决对齐实定名 ──
    ("确认表.md", "裁决 ④ 高亮非填充 → 实定 H2",
     "| ④ 颜色即信息（高亮非填充） | 新增 **H3**（spec） |",
     "| ④ 发光/阴影/滤镜制造高亮或纵深 | 新增 **H2 `no_glow_effects`**（**machine**）；⚠️ 本行原写「④ 颜色即信息（高亮非填充）→ H3（spec）」**与落盘不符**，实定见下 |"),
    ("确认表.md", "裁决 ⑧ 缓动 → 实定 H1 补射程",
     "| ⑧ 两只钟（缓动纪律） | 新增 **H1**（machine） |",
     "| ⑧ 两只钟（缓动纪律） | 新增 **H1 `easing_discipline`**（machine）；带射程参数 `scope`，**默认 `transition`**（只判状态切换族），要连 `animation` 一起禁须显式 `scope: all` |"),
    ("确认表.md", "裁决 ⑤ 静止态 → 实定 H4 补名",
     "| ⑤ 静止态是构图 | 新增 **H4**（manual，登记为人审点） |",
     "| ⑤ 静止态是构图 | 新增 **H4 `rest_is_composed`**（manual，`check: null` ⇒ 登记为人审点） |"),
    ("确认表.md", "裁决 ① 命中区 → 实定 H5 补名",
     "| ① 命中区不动 | 新增 **H5**（manual，登记为人审点） |",
     "| ① 命中区不动 | 新增 **H5 `hit_area_stability`**（manual，`check: null` ⇒ 登记为人审点） |"),
    ("确认表.md", "补 H3（无限循环）行",
     "| ③⑦⑨⑩ | **不迁移** —— 强绑定 isometric 线稿画面（不出框 / 循环屏外休眠 / 圆角化 / 图内无文字），对通用视觉产物无判别力；边界写进判据集 `note` |",
     "| ⑦ 循环屏外休眠（**兜底面**） | 新增 **H3 `infinite_motion_guard`**（machine）；⚠️ 只作「无限循环缺减动效出口」的**代理信号**，**屏外那一半机器无从观测**（原文要求的是屏外休眠）|\n"
     "| ③⑦⑨⑩ | **不迁移** —— 强绑定 isometric 线稿画面（不出框 / 循环屏外休眠**半面** / 圆角化 / 图内无文字），对通用视觉产物无判别力；边界写进判据集 `note` |"),
]

VERDICT_BLOCK = """
## 验证结论（s6 收尾，2026-10-09）

| # | 验证信号 | 结果 |
| --- | --- | --- |
| 1 | `checks.py skill` | **通过 76/76，FAIL=0，SKIP=0，WARN=0**（引用完整性 142 条；SKILL.md 153733 B / 预算 163840 B，94%） |
| 2 | `external_skill_lint.py` / `--verify-lock` | **81 / 85 通过，FAIL=0**（四上游：hairline 12 ／ humanizer 9 ／ mattpocock 65 ／ ppt-master 12994） |
| 3 | 三旧上游 A/B 不回归 | mattpocock 72/72、humanizer 3/3、ppt-master 3/3，**不一致 0** |
| 4 | `check_aesthetics.py --audit` | **一致 30，人审点 6，不一致 0，判据总数 36**（悬空参数仍为既有 9 键，**未新增**） |
| 5 | `--self-test` | **rc=0**，`[ OK ]` 86 项，`[FAIL]` **0** |
| 6 | 反向断言（实现→判据集） | 实现 26 ↔ 声明 26，**孤儿 0 / 悬空 0** |
| 7 | 判据条数三处同源 | 判据集实测 **36**；5 处活文件均登记 36 |
| 8 | 影响面实测 | 合成矩阵 5 样本；H1 **1/2**、H2 **1/2**、H3 **1/2**；无对象样本**三条全 SKIP** |
| 9 | 文档改动可复现 | 23 处编辑各命中恰 1 次；**8/8** 文件「HEAD ＋ 编辑表 == 现状」逐字节相等 |
| 10 | 出站扫描（本任务三份文档） | 修后 **FAIL=0**（WARN 为工作区盘符路径，边界已如实登记） |

> **记录修正留痕**：本表「前置裁决」原先写的 H2／H3 对象与档位**与落盘不符**（原写「④ 高亮非填充 → H3（spec）」）。实定为 **H2 `no_glow_effects`（machine）** 与 **H3 `infinite_motion_guard`（machine）**，原因见 `plan.yaml` 的 `meta.计划修订`（R1 第 2 条）与《变更说明.md》§3。**保留原行并加注**，不做静默改写。
"""


def main():
    by_file = {}
    for f, t, old, new in EDITS:
        by_file.setdefault(f, []).append((t, old, new))

    for f, items in by_file.items():
        p = TASK / f
        s = p.read_text(encoding="utf-8")
        before = s
        for t, old, new in items:
            if new in s:
                print(f"     · 跳过（已应用）：{f} · {t}")
                continue
            n = s.count(old)
            assert n == 1, f"[{f} · {t}] 锚点出现 {n} 次（期望 1）"
            s = s.replace(old, new)
            assert new in s, f"[{f} · {t}] 替换后新串不在"
        if s == before:
            print(f"[ OK ] {f} — 全部 {len(items)} 处已应用（幂等）")
            continue
        p.write_text(s, encoding="utf-8", newline="")
        back = p.read_text(encoding="utf-8")
        assert back == s, f"[{f}] 回读与写盘不一致"
        print(f"[ OK ] {f} — {len(items)} 处改动 + 回读复核通过")

    # 追加验证结论块（确认表末尾；幂等）
    cf = TASK / "确认表.md"
    s = cf.read_text(encoding="utf-8")
    if "## 验证结论（s6 收尾" in s:
        print("[ OK ] 确认表.md — 验证结论块已存在（幂等）")
    else:
        assert "## 已知限制" in s
        s = s.rstrip("\n") + "\n" + VERDICT_BLOCK
        cf.write_text(s, encoding="utf-8", newline="")
        back = cf.read_text(encoding="utf-8")
        assert "## 验证结论（s6 收尾" in back and back == s, "验证结论块回读失败"
        print("[ OK ] 确认表.md — 追加验证结论块 + 回读复核通过")

    # 自证：任务目录下交付文档已无本机主目录路径
    r = subprocess.run(
        [sys.executable, "scripts/outbound_scan.py",
         *[str(TASK / n) for n in ("变更说明.md", "确认表.md", "影响面实测.md")]],
        cwd=SKILL, capture_output=True, text=True, encoding="utf-8")
    print(r.stdout.strip().splitlines()[-2] if r.stdout.strip() else "(无输出)")
    assert "FAIL=0" in r.stdout, "出站扫描仍有 FAIL"
    print("[ OK ] 三份任务文档出站扫描 FAIL=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
