# -*- coding: utf-8 -*-
"""s1 基线：字体清单 + 公式链探针 + 版本记录（落 fixtures/）。

⚠️ **勿重跑**：`fixtures/baseline-fonts.txt` 记的是**改动前**的 SKILL.md 版本（4.34.0）——
「基线」的价值就在于它是改动前的快照；重跑会把它改写成当前版本，基线即失效。
（`fixtures/baseline-checks-skill.txt` 同理，由命令直接重定向产生、非本脚本产物。）
"""
import os, pathlib, sys

OUT = pathlib.Path(__file__).parent / "fixtures"
OUT.mkdir(exist_ok=True)
lines = []

# 1) 版本记录
import yaml
skill = pathlib.Path(__file__).resolve().parents[1]  # 技能根（脚本在 tasks/<任务>/ ⇒ parents[1]）
fm = (skill / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
for ln in fm.splitlines():
    if ln.startswith("version:"):
        lines.append(f"ai-workflow version: {ln.strip()}")
lines.append(f"python: {sys.version.split()[0]}")

# 2) ziamath 探针
import ziamath
from ziamath import Latex
lines.append(f"ziamath: {ziamath.__version__ if hasattr(ziamath, '__version__') else 'n/a'}")
from importlib.metadata import version as _v
lines.append(f"ziamath dist: {_v('ziamath')} / latex2mathml: {_v('latex2mathml')} / ziafont: {_v('ziafont')}")
probe = Latex(r"\min_w \|y - Xw\|^2 + \lambda\|w\|_2^2", size=16, color="#2d3142")
s = probe.svg()
import re
lines.append("probe svg: len=%d, <path>=%d, <use>=%d, <text>=%d, <image>=%d, font-face=%s, remote-ref=%s"
             % (len(s), s.count("<path"), s.count("<use"), s.count("<text"), s.count("<image"),
                "font-face" in s.lower(),
                bool([u for u in re.findall(r'https?://[^"\'\s>]+', s) if "w3.org" not in u])))
(OUT / "ziamath-probe.svg").write_text(s, encoding="utf-8")

# 3) 字体清单（关键候选）
fonts_dir = pathlib.Path(os.environ.get("WINDIR") or "C:/Windows") / "Fonts"
wanted = {
    "微软雅黑 Regular": "msyh.ttc", "微软雅黑 Bold": "msyhbd.ttc", "微软雅黑 Light": "msyhl.ttc",
    "宋体": "simsun.ttc", "黑体": "simhei.ttf", "等线 Light": "Deng.ttf", "等线 Bold": "Dengb.ttf",
    "Georgia": "georgia.ttf", "Georgia Bold": "georgiab.ttf", "Georgia Italic": "georgiai.ttf",
    "Cambria": "cambria.ttc", "Times New Roman": "times.ttf", "Consolas": "consola.ttf",
    "Consolas Bold": "consolab.ttf", "Segoe UI": "segoeui.ttf", "Segoe UI Semibold": "seguisb.ttf",
    "Cascadia Mono": "CascadiaMono.ttf", "Cascadia Code": "CascadiaCode.ttf",
    "TH Sarabun": "n/a", "Source Serif": "n/a", "思源宋体": "n/a",
}
lines.append("")
lines.append("== fonts ==")
for name, fn in wanted.items():
    if fn == "n/a":
        lines.append(f"  {name}: (预设无)")
        continue
    p = fonts_dir / fn
    lines.append(f"  {name}: {'OK' if p.exists() else 'MISSING'} ({fn})")

# 4) 扫描 Fonts 目录中可能的衬线/无衬线候选（只列前若干）
allf = sorted(x.name.lower() for x in fonts_dir.glob("*") if x.suffix.lower() in (".ttf", ".ttc", ".otf"))
lines.append("")
lines.append(f"== fonts dir total: {len(allf)} files ==")
for kw in ("georgia", "cambria", "book", "garamond", "palatino", "serif", "yahei", "deng", "song", "hei"):
    hit = [f for f in allf if kw in f]
    if hit:
        lines.append(f"  [{kw}] {', '.join(hit[:8])}")

(OUT / "baseline-fonts.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
