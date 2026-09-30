"""阴性对照 v2 —— 专测 verify_counts.py 新增的 4 组判据。

纪律：判据每改一次，对照重做一轮。要求：注入即红、**只红对应的那一条**、还原后逐字节一致。
字节级读写（write_text 在 Windows 会转 CRLF，破坏文件）。
"""
import hashlib
import os
import shutil
import subprocess
import sys

# 由脚本位置反推（不写死本机路径 —— 出站扫描会拦，且换机即失效）
# __file__ = <技能根>/tasks/<任务>/negative_control_v2.py
#   parents[0] = <任务>（verify_counts.py 同目录）  parents[2] = <技能根>
from pathlib import Path as _P
_here = _P(__file__).resolve()
SK = str(_here.parents[2])
T = str(_here.parents[0])
VERIFY = str(_here.parents[0] / "verify_counts.py")
BAK = str(_here.parents[0] / "_nc2_bak")
os.makedirs(BAK, exist_ok=True)

def E(s):  # bytes 字面量不能含非 ASCII，运行时再编码
    return s.encode("utf-8")


CASES = [
    ("README.md", E("# 33 个可执行脚本（30 .py + 1 .js + 2 .ps1）"),
     E("# 29 个可执行脚本（30 .py + 1 .js + 2 .ps1）"),
     "README 目录树 scripts 可执行数"),
    # ⚠️ 「七块快判」在 README 里出现 2 处（L35 散文 + L152 目录树），必须取更长的唯一锚点
    ("README.md", E("七块快判的问题模板"), E("五块快判的问题模板"),
     "README 目录树 judges.json 块数"),
    ("SKILL.md", "**24 个第三方 MIT 技能**".encode("utf-8"), "**20 个第三方 MIT 技能**".encode("utf-8"),
     "SKILL.md 手册索引 外部技能数"),
    ("SKILL.md", "六条门槛（".encode("utf-8"), "四条门槛（".encode("utf-8"),
     "SKILL.md 学习模型 K4 门槛条数"),
]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run_verify():
    p = subprocess.run([sys.executable, VERIFY], capture_output=True, text=True)
    red = [ln.split("] ", 1)[1].split(":")[0]
            for ln in p.stdout.splitlines() if ln.startswith("[FAIL]")]
    return p.returncode, red


passed = 0
for fname, old, new, expect in CASES:
    p = os.path.join(SK, fname)
    b = open(p, "rb").read()
    assert b.count(old) == 1, f"{fname}: 锚点不唯一（{b.count(old)} 处）"
    orig_sha = sha(p)
    shutil.copy2(p, os.path.join(BAK, fname + ".bak"))
    open(p, "wb").write(b.replace(old, new))
    rc, red = run_verify()
    shutil.copy2(os.path.join(BAK, fname + ".bak"), p)
    back = sha(p)
    ok = (rc != 0) and (red == [expect]) and (back == orig_sha)
    print(f"{'成立' if ok else '不成立'}  {fname}  注入「{old.decode('utf-8','replace')[:22]}」"
          f" → 退出码={rc} 红名单={red} 还原一致={back == orig_sha}")
    passed += ok

print(f"\n阴性对照：{passed}/{len(CASES)} 成立")
sys.exit(0 if passed == len(CASES) else 1)
