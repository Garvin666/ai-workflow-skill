# -*- coding: utf-8 -*-
"""s7 验收：跑全部机器验收命令并落 fixtures/verify-exports.txt（rc 汇总判定）。

⚠️ 回显中的解释器路径经 `_mask()` 折成本机主目录前缀 `~` —— 证据文本里出现
「含用户名的绝对路径」是出站扫描的 **FAIL 级**形态（会阻塞推送）；折成 `~` 后两侧都不
命中，且命令仍可读、可复跑（解释器位置可推）。
"""
import os
import pathlib
import subprocess
import sys

TASK = pathlib.Path(__file__).resolve().parent
SKILL = TASK.parents[1]
PY = sys.executable
TD = f"tasks/{TASK.name}"
FIX = TASK / "fixtures" / "verify-exports.txt"


def _mask(line: str) -> str:
    """把命令回显里的本机主目录前缀折成 `~`（两种分隔符都折）。"""
    for key in ("USERPROFILE", "HOME"):
        base = os.environ.get(key)
        if base:
            line = line.replace(base, "~").replace(base.replace("\\", "/"), "~")
    return line


CMDS = [
    ("[1] check_vector_export.py —— 两张 PDF（零 Type3／字体嵌入／单页／图幅／文本可提取）",
     [PY, "-X", "utf8", "scripts/check_vector_export.py",
      f"{TD}/output/export/card-ridge.pdf", f"{TD}/output/export/card-gmm.pdf",
      "--expect", "1200x1600"]),
    ("[2] methodcard_check.py —— Ridge 几何自检（SVG 图元 + 版面溢出 + PNG 尺寸）",
     [PY, "-X", "utf8", "scripts/methodcard_check.py",
      f"{TD}/output/card-ridge.html", "--png", f"{TD}/output/export/card-ridge.png"]),
    ("[3] methodcard_check.py —— GMM 几何自检",
     [PY, "-X", "utf8", "scripts/methodcard_check.py",
      f"{TD}/output/card-gmm.html", "--png", f"{TD}/output/export/card-gmm.png"]),
    ("[4] methodcard_lib.py --selftest", [PY, "-X", "utf8", "scripts/methodcard_lib.py", "--selftest"]),
    ("[5] methodcard_build.py --selftest", [PY, "-X", "utf8", "scripts/methodcard_build.py", "--selftest"]),
    ("[6] methodcard_check.py --selftest", [PY, "-X", "utf8", "scripts/methodcard_check.py", "--selftest"]),
]

lines = []
all_rc = []
for title, cmd in CMDS:
    lines.append("=" * 72)
    lines.append(title)
    lines.append("$ " + _mask(" ".join(cmd)))
    r = subprocess.run(cmd, cwd=SKILL, capture_output=True, text=True,
                       encoding="utf-8", timeout=300)
    all_rc.append(r.returncode)
    lines.append(f"(rc={r.returncode})")
    lines.append(r.stdout.strip())
    if r.stderr.strip():
        lines.append("[stderr] " + r.stderr.strip()[:600])
    lines.append("")

summary = f"汇总：{len(CMDS)} 组命令，rc 全零 = {all(r == 0 for r in all_rc)}" \
          f"（rcs={all_rc}）"
lines.append("=" * 72)
lines.append(summary)
FIX.parent.mkdir(parents=True, exist_ok=True)
FIX.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
raise SystemExit(0 if all(r == 0 for r in all_rc) else 1)
