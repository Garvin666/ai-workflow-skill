"""s4: H 层新判据的影响面实测。

⚠️ 诚实标注：**存量语料不可得** —— 工作区根（技能本体）与技能库根内 `.css` 实测 **0 个**
（见 tmp/hairline-20261009/reverse-assert.txt）。真实语料（ui库 21 套主题 / Deck.css）在
`E:/ChatGPT/ui库`，属**工作区根之外** ⇒ 需当次授权才能读，本轮**未申请**。
故本次影响面用**合成矩阵**代替：构造「常见合规产物」与若干「已知劣化形态」，看三条新判据
是不是「只在劣化形态上报红」。**合成 ≠ 存量**，结论只作区分度证据，不得读成「存量零影响」。
"""
import pathlib
import subprocess
import sys

# 原为硬编码本机绝对路径（出站清单第 4 项）⇒ 改由 __file__ 推导；
# PY 原指向技能自带 venv ⇒ 改用调用者解释器（本仓约定：必须用 venv 解释器跑）
SKILL = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
CORPUS = SKILL / "tmp" / "hairline-20261009" / "corpus"

CASES = {
    # ---- 常见合规产物（期望：三条全部 PASS 或 SKIP，不得报红）----
    "01-常规产物-合规.css": """
:root{--deck-bg:#FFFFFF;--deck-fg:#111111;--deck-accent:#1E5AA8;--deck-duration-normal:0.22s;}
.card{background:#FFFFFF;color:#111111;border-radius:8px;
      box-shadow:0 1px 2px rgba(0,0,0,.12);
      transition:opacity var(--deck-duration-normal) ease-out;}
.card:nth-child(1){animation-delay:0s;}
.card:nth-child(2){animation-delay:0.08s;}
.card:nth-child(3){animation-delay:0.18s;}
.spinner{animation:spin 1.2s linear infinite;}
@media (prefers-reduced-motion: reduce){.spinner{animation:none;}}
""",
    # ---- 劣化形态 1：线性缓动（H1 应 FAIL）----
    "02-线性缓动.css": """
.card{background:#FFFFFF;color:#111111;transition:opacity 220ms linear;}
""",
    # ---- 劣化形态 2：发光式效果（H2 应 FAIL）----
    "03-发光式.css": """
.card{background:#FFFFFF;color:#111111;filter:drop-shadow(0 0 12px #1E5AA8);}
.title{color:#111111;text-shadow:0 0 24px #FFD400;}
""",
    # ---- 劣化形态 3：无限循环无减动效兜底（H3 应 FAIL）----
    "04-无限循环无兜底.css": """
.card{background:#FFFFFF;color:#111111;animation:pulse 2s ease-in-out infinite;}
""",
    # ---- 无对象形态（三条都应 SKIP，不得判 PASS）----
    "05-零动效零阴影.css": """
.card{background:#FFFFFF;color:#111111;border-radius:8px;}
""",
}


def main():
    CORPUS.mkdir(parents=True, exist_ok=True)
    for name, text in CASES.items():
        (CORPUS / name).write_text(text.lstrip(), encoding="utf-8")

    out = CORPUS.parent / "impact-synthetic.txt"
    cmd = [PY, str(SKILL / "scripts" / "check_aesthetics.py"),
           "--rubric", str(SKILL / "references" / "aesthetic-rubric.yaml"),
           "--batch", str(CORPUS / "*.css"), "--product", "ui"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out.write_text(r.stdout + r.stderr, encoding="utf-8")
    print(f"[INFO] --batch rc={r.returncode}；原始输出落 {out}")
    print(r.stdout[-2200:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
