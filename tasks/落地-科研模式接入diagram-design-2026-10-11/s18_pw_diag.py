# -*- coding: utf-8 -*-
"""诊断 Playwright 浏览器下载是否在进行（以及卡在哪）。"""
import os
import pathlib
import time

LA = pathlib.Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
TMP = pathlib.Path(os.environ.get("TEMP", r"C:\Windows\Temp"))
now = time.time()

print(f"ms-playwright = {LA}")
for p in sorted(LA.iterdir()) if LA.exists() else []:
    st = p.stat()
    age = (now - st.st_mtime) / 60
    size = ""
    if p.is_dir():
        try:
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            size = f"{size / 1e6:.1f} MB"
        except Exception as e:
            size = f"(err {e})"
    print(f"  {p.name:<34} age={age:7.1f}min  {size}")

print(f"\nTEMP = {TMP}")
hits = 0
for p in TMP.rglob("*") if TMP.exists() else []:
    n = p.name.lower()
    if ("playwright" in n or "chromium" in n or "chrome-win" in n) and p.is_file():
        print(f"  {p}  {p.stat().st_size / 1e6:.1f} MB  age={(now - p.stat().st_mtime) / 60:.1f}min")
        hits += 1
        if hits > 15:
            break
print(f"  （命中 {hits} 个）")

# 本项目 1.63.0 需要的 rev
try:
    from playwright._impl._driver import compute_driver_executable  # noqa
except Exception:
    pass
try:
    import playwright._impl._browser_type as bt  # noqa
except Exception:
    pass

# 直接从 playwright 的 registry 取它要找的目录名
try:
    from playwright._impl._driver import compute_driver_executable  # noqa: F811
except Exception:
    compute_driver_executable = None
import json
import subprocess
node, cli = None, None
try:
    d = pathlib.Path(__import__("playwright").__file__).parent / "driver"
    print(f"\nplaywright 包目录 = {pathlib.Path(__import__('playwright').__file__).parent}")
    for f in sorted(d.glob("*")):
        print(f"  driver/{f.name}")
except Exception as e:
    print(f"driver 探查失败：{e}")
