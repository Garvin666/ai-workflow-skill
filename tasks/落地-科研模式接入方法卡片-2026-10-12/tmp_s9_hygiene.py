# -*- coding: utf-8 -*-
"""s9 卫生修订：清掉本轮**新增文件**里的本机主目录路径（出站扫描 FAIL 级形态）。

口径（本仓成例，见 `references/push-routing.md` 与 v4.34.0 changelog）：
  * `C:\\Users\\<具体用户名>\\...` ⇒ **FAIL**（阻塞推送）；
  * 「已掩码形态」`<用户名>` / `$HOME` / `~/.workbuddy/` 两侧都不命中 —— 报它们等于惩罚已脱敏的文件。
  ⇒ 本轮只做两件事：**脚本类改为可推导路径**；**证据文本掩码**。**不动判据、不用 `outbound-scan:allow` 豁免**。

⚠️ 只改**本轮新增/新产生的文件**；本仓既有历史文件（13 文件 / 21 处）不在本次 diff 面，不动。
⚠️ 改动只涉及「路径怎么写」，不涉及任何断言语义 ⇒ 不重跑基线（基线必须保持改动前快照）。
"""
import os
import pathlib
import re
import sys

TASK = pathlib.Path(__file__).resolve().parent
# ⚠️ 本脚本自己也要过出站扫描 —— 故**不在源码里写死用户名**：
#    锚点（= 待替换的旧串）含本机主目录路径，若以字面量写出，脚本自身就成了 FAIL 级文件。
#    改为运行期由环境变量拼出。
_U = os.environ.get("USERNAME") or os.environ.get("USERPROFILE", "").rsplit("\\", 1)[-1]
_HOME = "C:" + "\\" + "Users" + "\\" + _U
PAT = re.compile(r"[Cc]:\\Users\\" + re.escape(_U) + r"\\")
edits = 0


def patch(rel: str, pairs: list[tuple[str, str]]) -> None:
    """定点替换；**可重入** —— 锚点已消失且新文本已在场时视为「已应用」并跳过。"""
    global edits
    p = TASK / rel
    raw = p.read_bytes()
    s = raw.decode("utf-8")
    applied = 0
    for old, new in pairs:
        # ⭐ 幂等判据看**目标态**，不看「旧串还在不在」—— 插入型替换里 `new` 以 `old` 为子串，
        #    已应用时 `s.count(old)` 仍为 1 ⇒ 用「旧串计数」当判据会把同一段**重复插入**
        #    （本脚本首版就这么把 s7_verify.py 的 import/_mask 各插了三遍）。
        if new in s:
            continue  # 目标态已在场 ⇒ 已应用
        n = s.count(old)
        if n == 1:
            s = s.replace(old, new)
            applied += 1
            continue
        raise SystemExit(f"[中止] {rel}：锚点命中 {n} 次（期望 1）—— {old[:70]!r}")
    if applied == 0:
        print(f"  [SKIP] {rel} 已应用（本次无改动）")
        assert not PAT.search(s), f"{rel} 仍有用户名路径"
        return
    p.write_bytes(s.encode("utf-8"))
    back = (TASK / rel).read_text(encoding="utf-8")
    assert back == s, f"{rel} 回读不一致"
    assert not PAT.search(back), f"{rel} 仍有用户名路径"
    edits += 1
    print(f"  [OK] {rel} 已改（{applied} 处）；残留用户名路径 0")


# ---- A. s1_baseline.py：技能根改为 __file__ 推导 + 加「勿重跑」警示 ----
patch("s1_baseline.py", [
    ('"""s1 基线：字体清单 + 公式链探针 + 版本记录（落 fixtures/）。"""',
     '"""s1 基线：字体清单 + 公式链探针 + 版本记录（落 fixtures/）。\n\n'
     '⚠️ **勿重跑**：`fixtures/baseline-fonts.txt` 记的是**改动前**的 SKILL.md 版本（4.34.0）——\n'
     '「基线」的价值就在于它是改动前的快照；重跑会把它改写成当前版本，基线即失效。\n'
     '（`fixtures/baseline-checks-skill.txt` 同理，由命令直接重定向产生、非本脚本产物。）\n"""'),
    ('import pathlib, sys', 'import os, pathlib, sys'),
    ('skill = pathlib.Path(r"' + _HOME + '\\.workbuddy\\skills\\ai-workflow")',
     'skill = pathlib.Path(__file__).resolve().parents[1]  # 技能根（脚本在 tasks/<任务>/ ⇒ parents[1]）'),
    ('fonts_dir = pathlib.Path(r"C:\\Windows\\Fonts")',
     'fonts_dir = pathlib.Path(os.environ.get("WINDIR") or "C:/Windows") / "Fonts"'),
])

# ---- B. s2_sample.py：参考图目录改为环境变量推导 ----
patch("s2_sample.py", [
    ('import pathlib, collections', 'import os, pathlib, collections'),
    ('CI = pathlib.Path(r"' + _HOME + '\\.workbuddy\\clipboard-images")',
     'CI = (pathlib.Path(os.environ.get("USERPROFILE") or pathlib.Path.home())\n'
     '      / ".workbuddy" / "clipboard-images")  # 输入源；不写死用户名路径'),
])

# ---- C. s7_verify.py：命令回显里的解释器路径折成 ~（改完须重跑以刷新证据） ----
patch("s7_verify.py", [
    ('import pathlib\nimport subprocess\nimport sys',
     'import os\nimport pathlib\nimport subprocess\nimport sys'),
    ('CMDS = [',
     'def _mask(line: str) -> str:\n'
     '    """把命令回显里的本机主目录前缀折成 `~`。\n\n'
     '    出站扫描口径：证据文本里出现「含用户名的绝对路径」是 FAIL 级（阻塞推送）；\n'
     '    折成 `~` 后两侧都不命中，且命令仍可读、可复跑（解释器位置可推）。\n'
     '    """\n'
     '    for key in ("USERPROFILE", "HOME"):\n'
     '        base = os.environ.get(key)\n'
     '        if base:\n'
     '            line = line.replace(base, "~").replace(base.replace("\\\\", "/"), "~")\n'
     '    return line\n\n\n'
     'CMDS = ['),
    ('    lines.append("$ " + " ".join(cmd))',
     '    lines.append("$ " + _mask(" ".join(cmd)))'),
])

# ---- D. 证据文本掩码：pre-s9-checks-plan.txt（改动前的 FAIL 留痕） ----
src = TASK / "fixtures" / "pre-s9-checks-plan.txt"
dst = TASK / "fixtures" / "checks-plan-before-fix.txt"
if not src.exists() and dst.exists():
    print("  [SKIP] fixtures/checks-plan-before-fix.txt 已生成（本次无改动）")
    assert not PAT.search(dst.read_text(encoding="utf-8")), "已生成件仍含用户名路径"
else:
    txt = src.read_text(encoding="utf-8")
    n = len(PAT.findall(txt))
    assert n == 1, f"预期待掩码 1 处，实测 {n} 处"
    txt = txt.replace("Users" + "\\" + _U + "\\", "Users" + "\\" + "<用户名>" + "\\")
    assert not PAT.search(txt) and "<用户名>" in txt
    dst.write_text(txt, encoding="utf-8")
    src.unlink()
    assert dst.is_file() and not src.exists()
    edits += 1
    print(f"  [OK] fixtures/pre-s9-checks-plan.txt → checks-plan-before-fix.txt（掩码 1 处）")

# ---- E. 三个含用户名路径的一次性脚本移入 tmp/（显式清单 + 计数自证） ----
MOVE = ["tmp_debug_plan.py", "tmp_update_plan.py", "tmp_update_plan2.py"]
TDST = TASK / "tmp"
TDST.mkdir(exist_ok=True)
moved = 0
for name in MOVE:
    s0, d0 = TASK / name, TDST / name
    if not s0.exists() and d0.exists():
        moved += 1
        continue  # 已搬（可重入）
    if not s0.exists():
        raise SystemExit(f"[中止] 源与目标都不存在：{name}")
    if d0.exists():
        raise SystemExit(f"[中止] 目标已存在，不覆盖：{d0}")
    s0.replace(d0)
    moved += 1
    assert d0.exists() and not s0.exists(), name
assert moved == len(MOVE) == 3, moved
print(f"  [OK] 移入 tmp/ {moved} 个（显式清单 3 项全部移动）")

# ---- F. 终检：**推送面**上剩余命中必须为 0 ----
# 排除项与理由（各一条，不含糊）：
#   * `tmp/**`      —— 清理容器的内容将由 cleanup_task.py 删除，届时不在推送面；
#                      扫它等于对一批即将消失的文件提要求（且会让「修好/没修好」失真）。
#   * `plan.yaml`   —— 必须写明工作区根（这是它的字段义务）；该文件由 .gitignore 忽略、不入推送面。
ALLOW = {"plan.yaml"}
SKIP_DIRS = {"tmp"}
left = []
for p in sorted(TASK.rglob("*")):
    if not p.is_file() or ".git" in p.parts:
        continue
    rel = p.relative_to(TASK)
    if SKIP_DIRS & set(rel.parts[:-1]):
        continue
    if p.suffix.lower() in (".png", ".pdf", ".woff2"):
        continue
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    hits = len(PAT.findall(t))
    if hits:
        left.append((str(rel), hits))
print()
print("终检（推送面 = 任务目录除去 tmp/ 与二进制；无用户名路径则通过）：")
for rel, h in left:
    mark = "（合法：必须声明工作区根，且不入推送面）" if rel in ALLOW else "  ⚠️ 未处置"
    print(f"  {rel:44s} {h} 处 {mark}")
if not left:
    print("  （无命中）")
bad = [r for r, _ in left if r not in ALLOW]
assert not bad, f"推送面仍有无处置命中：{bad}"
print(f"\nOK：修订 {edits} 组；推送面剩余命中仅 {sorted(ALLOW)}（已登记为合法）")
sys.exit(0)
