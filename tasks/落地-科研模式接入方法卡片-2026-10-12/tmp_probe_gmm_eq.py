# -*- coding: utf-8 -*-
"""GMM 公式探针：验证 ziamath 对所需 LaTeX 的支持。"""
import sys, pathlib
TASK = pathlib.Path(__file__).resolve().parent
SKILL = TASK.parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import methodcard_lib as M

CASES = [
    r"p(x)=\sum_{k}\pi_{k}\,\mathcal{N}(x\mid\mu_{k},\Sigma_{k})",
    r"\gamma_{ik}=\frac{\pi_{k}\,\mathcal{N}(x_{i}\mid\mu_{k},\Sigma_{k})}{\sum_{j}\pi_{j}\,\mathcal{N}(x_{i}\mid\mu_{j},\Sigma_{j})}",
    r"\Delta \ln L \to 0",
]
for i, c in enumerate(CASES):
    s = M.eq_scaled(c, 40, M.TOKENS["ink"])
    w, h = M.eq_size(s)
    has_text = "<text" in s
    has_image = "<image" in s
    remote = "http://" in s.replace("http://www.w3.org/2000/svg", "")
    print(f"[{i}] size={w:.0f}x{h:.0f} text={has_text} image={has_image} remote={remote}")
    out = TASK / "fixtures" / f"probe-gmm-eq{i}.svg"
    out.write_text(s, encoding="utf-8")
print("OK")
