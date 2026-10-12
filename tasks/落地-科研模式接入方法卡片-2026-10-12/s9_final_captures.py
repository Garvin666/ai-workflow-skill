# -*- coding: utf-8 -*-
"""s9 尾段（一）：补齐两处门禁留痕 —— 都在**全部写入结束之后**用**新进程**复跑。

⭐ 为什么必须复跑：一致性声明的有效期只到「其后不再有写入」为止。12:23 那时的
   `outbound` / `plan` 留痕都**早于**后续的写入（变更说明、清理清单、索引重建、
   若干收尾脚本）⇒ 旧结论不能直接当最终口径，须在写入收敛后重取。

1) `gen_skill_index.py --check`：索引指纹含各技能 `SKILL.md` 的内容 sha1，本任务改了
   `ai-workflow/SKILL.md` ⇒ 索引**按构造即失效**。旧留痕记的是**重建前**的 `rc=1 [STALE]`
   （那是「改了入口手册 ⇒ 索引失效」的现场证据），按本仓惯例（参照
   `checks-skill-before-platform-fix.txt` 的处置）**改名保留**，另写**重建后**的结论。
2) `checks.py plan`：验证 `meta.清理` 回填**之后**结构仍合法、Anti-drop 仍 FAIL=0。

⚠️ 两个 rc 都**不接管道**取（管道会吞掉被测脚本的退出码 ⇒ 把失败读成 0）。
⚠️ 留痕落盘前**掩码本机主目录的用户名段**（与既有留痕 `checks-plan-before-fix.txt` 同形）——
   含用户名的绝对路径是出站扫描的 **FAIL 级**形态；掩码范围**只限当前用户自己的主目录**，
   刻意不给兜底规则（放宽会让出站判据空转）。命中次数**回显**，以证这一步真生效（0 = 未生效）。
"""

import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent          # tasks/<本任务>/
SKILL = HERE.parents[1]                                  # 技能根
FIX = HERE / "fixtures"
PY = sys.executable
assert (SKILL / "scripts" / "checks.py").is_file(), f"技能根探测失败：{SKILL}"


def _mask(text: str) -> tuple[str, int]:
    """把**本机主目录前缀的用户名段**折成 `<用户名>`；返回 (文本, 命中次数)。"""
    home = (os.environ.get("USERPROFILE") or os.environ.get("HOME") or "").rstrip("\\/")
    if not home:
        return text, 0
    hits = 0
    m = re.match(r"^([A-Za-z]:)[\\/]+Users[\\/]+([^\\/]+)$", home)
    if m:
        drive, name = m.group(1), m.group(2)
        for sep in ("\\", "/"):
            src = f"{drive}{sep}Users{sep}{name}"
            hits += text.count(src)
            text = text.replace(src, f"{drive}{sep}Users{sep}<用户名>")
    else:                       # 非 `X:\Users\<name>` 形态（如多 home 段）⇒ 整体折成 `~`
        for form in (home, home.replace("\\", "/")):
            hits += text.count(form)
            text = text.replace(form, "~")
    return text, hits


def write_capture(name: str, text: str) -> int:
    """写留痕：统一 CRLF（与既有 fixtures 同族）；返回字节数。"""
    p = FIX / name
    p.write_text(text, encoding="utf-8")                # 默认换行翻译 ⇒ CRLF
    return p.stat().st_size


# --- 0) 旧留痕改名保留（重建前的 STALE 现场） ---
old = FIX / "after-cleanup-gen-skill-index.txt"
keep = FIX / "gen-skill-index-before-rebuild.txt"
if old.exists() and not keep.exists():
    n_before = old.stat().st_size
    keep.write_bytes(old.read_bytes())
    old.unlink()
    print(f"[改名] {old.name} → {keep.name}（{n_before} B，重建前 rc=1 现场）")
else:
    print(f"[改名] 跳过（old 存在={old.exists()}，keep 存在={keep.exists()}）")


def capture(cmd, out_name: str, title: str):
    """跑一条命令 → 掩码 → 落留痕 → 回显。rc 走捕获值，不经管道。"""
    r = subprocess.run(cmd, cwd=SKILL, capture_output=True, text=True, encoding="utf-8")
    raw = ((r.stdout or "") + (r.stderr or "")).rstrip("\n")
    body, hits = _mask(raw)
    n = write_capture(out_name, body + f"\nrc={r.returncode}\n")
    print(f"\n==== {title} ====")
    print(body or "(无输出)")
    print(f"rc={r.returncode}  ｜ 掩码命中 {hits} 处  ｜ 留痕 {out_name} = {n} B")
    return r.returncode, body, hits


# --- 1) gen_skill_index.py --check（重建后；沿用索引自己记录的根集） ---
rc1, t1, h1 = capture([PY, "-u", "-X", "utf8", "scripts/gen_skill_index.py", "--check"],
                      "after-cleanup-gen-skill-index.txt",
                      "gen_skill_index.py --check（索引重建之后）")

# --- 2) checks.py plan（meta.清理 回填之后） ---
rc2, t2, h2 = capture([PY, "-u", "-X", "utf8", "scripts/checks.py", "plan", str(HERE), "--base", str(SKILL)],
                      "after-cleanup-checks-plan.txt",
                      "checks.py plan（meta.清理 回填之后）")

fails = [l for l in t2.splitlines() if "[FAIL]" in l]
print("\n---- 判定 ----")
print(f"  索引 --check rc = {rc1}（须 0），掩码命中 {h1} 处")
print(f"  plan rc = {rc2}（须 0），掩码命中 {h2} 处；FAIL 行 {len(fails)} 条")
for l in fails:
    print("   ", l)
print("\n---- 留痕 ----")
for n in ("gen-skill-index-before-rebuild.txt", "after-cleanup-gen-skill-index.txt",
          "after-cleanup-checks-plan.txt"):
    p = FIX / n
    print(f"  {n}: {p.stat().st_size if p.exists() else 'MISSING'} B")
