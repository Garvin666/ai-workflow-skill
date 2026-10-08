# -*- coding: utf-8 -*-
"""s5：三路回归 —— ① checks.py skill ② thinking_model selftest ③ 全量历史 plan 回归。
   ⭐ ③ 做真 A/B：用**冻结的旧版实现**（tmp/baseline-frozen/）临时换回技能里跑一遍 = 真实前一版基线，
   再换回新版实现跑一遍。全程 try/finally 保证技能一定被还原，并以 sha256 断言还原成功。"""
import hashlib, os, re, shutil, subprocess, sys

SKILL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))  # 原为硬编码本机绝对路径（出站清单第 4 项）
PY = sys.executable  # 原为硬编码本机 venv 解释器路径（出站清单第 4 项）
TASK = os.path.join(SKILL, "tasks", "技能演进-前提审计机器判据-2026-10-08")
TMP = os.path.join(TASK, "tmp")
FROZEN = os.path.join(TMP, "baseline-frozen")
NEWIMPL = os.path.join(TMP, "new-impl")
CHK = os.path.join(SKILL, "scripts", "checks.py")
ROOTS = [SKILL, r"E:\ChatGPT\工作流"]
TOUCHED = ["scripts/checks_judges.py", "scripts/thinking_model.py"]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def plans(root):
    base = os.path.join(root, "tasks")
    out = []
    if not os.path.isdir(base):
        return out
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d, "plan.yaml")
        if os.path.isfile(p):
            out.append((d, p))
    return out

RES = re.compile(r"结果：通过 (\d+)/(\d+)，FAIL=(\d+)，SKIP=(\d+)，WARN=(\d+)")

def run_all(label):
    """跑两个根的全部 plan，返回 {任务名: (fail, warn, skip, ok, total)}"""
    res = {}
    for root in ROOTS:
        for name, p in plans(root):
            try:
                r = subprocess.run([PY, CHK, "plan", p, "--base", root],
                                   capture_output=True, timeout=180)
                out = (r.stdout or b"").decode("utf-8", "replace")
            except subprocess.TimeoutExpired:
                res[name] = ("TIMEOUT",)
                continue
            m = RES.search(out)
            if not m:
                res[name] = ("NOPARSE rc=%d" % r.returncode,)
            else:
                ok, tot, f, s, w = (int(x) for x in m.groups())
                res[name] = (f, w, s, ok, tot)
    print("[%s] 覆盖 plan 数 = %d" % (label, len(res)))
    return res

# ---- 1) 现行版：checks.py skill + selftest ----
print("=" * 72)
r = subprocess.run([PY, CHK, "skill"], cwd=SKILL, capture_output=True, timeout=900)
skill_out = (r.stdout or b"").decode("utf-8", "replace")
print("[checks.py skill] rc =", r.returncode)
for ln in skill_out.splitlines():
    if "结果：" in ln or ln.startswith("[XX") or "入口手册体量预算" in ln:
        print("   ", ln)

r2 = subprocess.run([PY, os.path.join(SKILL, "scripts", "thinking_model.py"), "selftest"],
                    cwd=SKILL, capture_output=True, timeout=600)
st_out = (r2.stdout or b"").decode("utf-8", "replace")
print("[thinking_model selftest] rc =", r2.returncode)
for ln in st_out.splitlines():
    if "汇总" in ln or ln.startswith("[XX"):
        print("   ", ln)

# ---- 2) A/B：历史 plan 回归 ----
os.makedirs(NEWIMPL, exist_ok=True)
newshas = {}
for rel in TOUCHED:
    src = os.path.join(SKILL, rel.replace("/", os.sep))
    dst = os.path.join(NEWIMPL, os.path.basename(rel))
    shutil.copy2(src, dst)
    newshas[rel] = sha(src)
print("\n[新实现快照] ", {os.path.basename(k): v[:12] for k, v in newshas.items()})

before = after = None
try:
    # 换回旧实现
    for rel in TOUCHED:
        shutil.copy2(os.path.join(FROZEN, rel.replace("/", os.sep)),
                     os.path.join(SKILL, rel.replace("/", os.sep)))
    for rel in TOUCHED:
        got = sha(os.path.join(SKILL, rel.replace("/", os.sep)))
        exp = sha(os.path.join(FROZEN, rel.replace("/", os.sep)))
        assert got == exp, "换回旧实现失败: " + rel
    print("\n[已换回旧实现] 开始跑 A 侧（真实前一版）…")
    before = run_all("A=旧实现")
finally:
    for rel in TOUCHED:
        shutil.copy2(os.path.join(NEWIMPL, os.path.basename(rel)),
                     os.path.join(SKILL, rel.replace("/", os.sep)))
    ok_restore = all(sha(os.path.join(SKILL, r0.replace("/", os.sep))) == newshas[r0] for r0 in TOUCHED)
    print("[已还原新实现] sha256 断言 =", "OK" if ok_restore else "**FAIL**")
    if not ok_restore:
        sys.exit(2)

print("\n[新实现] 开始跑 B 侧…")
after = run_all("B=新实现")

# ---- 3) 差分 ----
with open(os.path.join(TMP, "regression-after.txt"), "w", encoding="utf-8") as f:
    f.write("A/B 全量历史 plan 回归（A=冻结的 v4.21.0 实现 / B=本次改后实现）\n")
    f.write("=" * 60 + "\n")
    f.write("[checks.py skill] rc=%d\n%s\n" % (r.returncode, skill_out))
    f.write("[thinking_model selftest] rc=%d\n%s\n" % (r2.returncode, st_out))
    f.write("=" * 60 + "\n")
    new_fail = []
    for k in sorted(set(before) | set(after)):
        b, a = before.get(k), after.get(k)
        f.write("%-46s A=%s  B=%s\n" % (k, b, a))
        if isinstance(b, tuple) and isinstance(a, tuple) and len(b) >= 1 and len(a) >= 1 \
           and isinstance(b[0], int) and isinstance(a[0], int) and a[0] > b[0]:
            new_fail.append((k, b[0], a[0]))
    f.write("=" * 60 + "\n")
    f.write("FAIL 增加的任务 = %s\n" % (new_fail or "无"))
print("\n★ FAIL 增加的任务 =", new_fail or "无")
print("★ 明细已写入", os.path.join(TMP, "regression-after.txt"))
