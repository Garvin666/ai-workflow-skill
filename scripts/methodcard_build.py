# -*- coding: utf-8 -*-
"""[自研工具] methodcard_build —— 方法原理卡片组装器与导出（PNG/PDF）。

名称：methodcard_build
用途：把卡片内容 dict（页眉/核心思想/步骤/示意区/总结 ＋ 子图 SVG）组装为五区
      自包含 HTML（内联 CSS，零远程引用），并可导出 PNG（Chrome headless @2x）
      与 PDF（Chrome --print-to-pdf，矢量）。
适用场景：科研模式 R5「方法解释图」、学习资料卡片、汇报演示素材。
仓库：https://github.com/Garvin666/ai-workflow-tools（待推送）
"""
from __future__ import annotations
import argparse, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from methodcard_lib import TOKENS, FONTS, CARD_W, CARD_H, esc, num  # noqa: E402

CSS = """
:root{
  --paper:%(paper)s; --panel:%(panel)s; --panel_blue:%(panel_blue)s;
  --line:%(line)s; --line_soft:%(line_soft)s;
  --ink:%(ink)s; --ink_body:%(ink_body)s; --ink_muted:%(ink_muted)s;
  --blue:%(blue)s; --blue_deep:%(blue_deep)s; --blue_light:%(blue_light)s;
  --warm:%(warm)s; --warm_deep:%(warm_deep)s; --red:%(red)s; --tan:%(tan)s;
  --gray_fill:%(gray_fill)s;
  --f-title: %(f_title)s; --f-sans: %(f_sans)s; --f-light: %(f_light)s; --f-cn-serif: %(f_cn_serif)s;
}
*{box-sizing:border-box; margin:0; padding:0;}
html,body{background:#FFFFFF;}
.card{
  width:1200px; height:1600px; background:var(--paper);
  border:2px solid var(--line); border-radius:10px;
  padding:22px; display:flex; flex-direction:column; gap:13px;
  font-family:var(--f-sans); color:var(--ink_body);
}
/* ---------- 页眉 ---------- */
.head{height:170px; display:flex; align-items:center; justify-content:space-between;
  border:1.5px solid var(--line); border-radius:6px; padding:10px 22px 8px; position:relative;}
.series{font-family:var(--f-light); font-size:15px; letter-spacing:.34em; color:#7C7A72;
  line-height:1.75; text-transform:uppercase; min-width:150px;}
.series .hash{display:block; margin-top:10px; font-family:var(--f-title); font-size:22px;
  letter-spacing:.08em; color:var(--ink); font-weight:600;}
.ttl-wrap{flex:1; text-align:center;}
.ttl{font-family:var(--f-title); font-weight:700; font-size:82px; line-height:1.02;
  color:var(--ink); letter-spacing:.005em; white-space:nowrap;}
.sub{display:flex; align-items:center; justify-content:center; gap:14px; margin-top:14px;}
.sub .dash{height:1.5px; background:var(--ink_muted); width:152px; opacity:.75; position:relative;}
.sub .dash::after{content:""; position:absolute; right:-3px; top:-3.2px; width:7px; height:7px;
  background:var(--ink_muted); transform:rotate(45deg); opacity:.9;}
.sub .dash.l::after{left:-3px; right:auto;}
.sub-tag{background:var(--tan); border-radius:8px; padding:7px 26px 9px;
  font-family:var(--f-cn-serif); font-size:30px; color:#33322E; letter-spacing:.22em;
  text-indent:.22em; white-space:nowrap;}
.tags{font-family:var(--f-light); font-size:14px; letter-spacing:.30em; color:#7C7A72;
  line-height:2.15; text-transform:uppercase; text-align:right; min-width:150px;}
/* ---------- 核心思想 ---------- */
.idea{border:1.5px solid var(--line); border-radius:6px; background:var(--panel);
  padding:16px 20px 8px; height:236px; position:relative;}
.idea-row{display:flex; align-items:flex-start; gap:16px;}
.idea-tag{background:var(--tan); border-radius:7px; padding:5px 14px 7px; flex:0 0 auto;
  font-family:var(--f-sans); font-weight:600; font-size:19px; color:#33322E;
  letter-spacing:.12em; text-indent:.12em;}
.idea-text{font-size:21px; line-height:1.62; color:var(--ink_body); padding-top:2px;}
.idea-eq{display:flex; align-items:center; justify-content:center; padding-top:10px;}
.idea-eq svg{display:block;}
/* ---------- 步骤区 ---------- */
.steps{height:588px; display:grid; grid-template-columns:repeat(4,1fr); gap:12px;}
.step{border:1.5px solid var(--line); border-radius:6px; padding:12px 13px 10px;
  display:flex; flex-direction:column; min-width:0;}
.st-head{display:flex; align-items:center; gap:9px; margin-bottom:9px;}
.st-num{width:34px; height:34px; border-radius:50%%; background:#6E6D68; color:#FFFFFF;
  display:flex; align-items:center; justify-content:center; font-size:19px; font-weight:600;
  flex:0 0 auto;}
.st-title{font-size:22px; font-weight:600; color:var(--ink); letter-spacing:.01em;}
.st-note{font-size:17.5px; line-height:1.58; color:#4A4944; min-height:92px;}
.st-fig{flex:1 1 auto; display:flex; align-items:center; justify-content:center; padding-top:4px;}
.st-fig svg{display:block; max-width:100%%;}
.st-cap{margin-top:6px; text-align:center; font-size:14px; color:#5A5952;}
/* ---------- 示意区 ---------- */
.hero{border:1.5px solid var(--line); border-radius:6px; height:412px; flex:1 1 auto;
  padding:8px 18px 10px; display:flex; flex-direction:column;}
.hero-title{display:flex; align-items:center; justify-content:center; gap:16px; height:42px;}
.hero-title .hl{height:1.2px; background:#4A4944; width:322px; opacity:.8;}
.hero-title span.t{font-family:var(--f-cn-serif); font-size:24px; color:var(--ink);
  letter-spacing:.24em; text-indent:.24em; white-space:nowrap;}
.hero-body{flex:1; display:flex; align-items:center; justify-content:space-around; gap:6px;}
.hero-cap{height:22px; text-align:center; font-size:14px; color:#6A6962;}
/* ---------- 组件族（步骤/示意区内嵌） ---------- */
.fb{background:var(--panel_blue); border-radius:5px; padding:12px 10px 10px; width:100%%;
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:7px;
  min-height:118px;}
.fb-l1{display:flex;} .fb-l2{display:flex; align-items:center; gap:8px;}
.fb-tag{font-size:13px; color:var(--blue_deep); background:#D6E2EF; border-radius:4px;
  padding:2px 8px; white-space:nowrap;}
.hb-fig{flex:0 0 auto;}
.hb-arrow{flex:0 0 auto;}
.badge{background:var(--blue); color:#FFFFFF; border-radius:8px; padding:15px 16px;
  font-size:17px; line-height:1.55; text-align:center; font-weight:600; letter-spacing:.04em;}
/* ---------- 总结 ---------- */
.takeaway{border:1.5px solid var(--line); border-radius:6px; background:var(--panel);
  height:104px; display:flex; align-items:center; gap:18px; padding:0 26px;}
.bulb{flex:0 0 auto;}
.tk-text{font-size:20.5px; line-height:1.5; color:#3B3A36;}
/* ---------- 打印（PDF 导出） ---------- */
@page{size:1200px 1600px; margin:0;}
"""


_FONT_DIR = pathlib.Path(__file__).parent.parent / "assets" / "fonts"
_FONT_CACHE: dict = {}


def font_faces() -> str:
    """自嵌标题字体 @font-face（Playfair Display 600/700 静态 woff2 → base64）。

    ⚠️ 为什么内嵌而不引用系统字体：系统「可变字体」（如 Windows Sitka 的 SitkaVF.ttf）
    在 Chrome 打印 PDF 时无法子集嵌入，会把整段标题落成 **Type3**（矢量但期刊/印厂
    拒收，肉眼完全不可见）⇒ 标题字体一律走「静态文件内嵌」；缺文件时**显式告警**
    并降级到本地安全栈（Cambria/Georgia），不静默降级。
    """
    if "css" in _FONT_CACHE:
        return _FONT_CACHE["css"]
    import base64
    parts = []
    for weight, fname in ((600, "playfair-display-600.woff2"),
                          (700, "playfair-display-700.woff2")):
        p = _FONT_DIR / fname
        if not p.exists():
            print(f"[methodcard] ⚠ 缺字体文件 {p}，降级到本地字体栈（可能影响质感）",
                  file=sys.stderr)
            continue
        b64 = base64.b64encode(p.read_bytes()).decode()
        parts.append("@font-face{font-family:'Playfair Display';font-style:normal;"
                     f"font-weight:{weight};"
                     f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
    _FONT_CACHE["css"] = "".join(parts)
    return _FONT_CACHE["css"]


def css() -> str:
    return font_faces() + CSS % {
        **TOKENS,
        "f_title": FONTS["title"], "f_sans": FONTS["sans"],
        "f_light": FONTS["sans_lt"], "f_cn_serif": FONTS["serif_cn"],
    }


def bulb_icon(size=44) -> str:
    s = size
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 44 44" width="{s}" height="{s}">'
        f'<path d="M22 6c-6.6 0-11 4.9-11 10.6 0 3.6 1.8 6.2 3.8 8.2 1 1 1.7 2.1 1.9 3.2h10.6c.2-1.1.9-2.2 1.9-3.2 2-2 3.8-4.6 3.8-8.2C33 10.9 28.6 6 22 6z" '
        f'fill="none" stroke="{TOKENS["ink"]}" stroke-width="2.1"/>'
        f'<path d="M17 31h10M18.5 35.5h7" stroke="{TOKENS["ink"]}" stroke-width="2.1" stroke-linecap="round"/>'
        f'<path d="M22 2.2v2M11 9l1.7 1.2M33 9l-1.7 1.2M6.5 20h2.3M35.2 20h2.3" '
        f'stroke="{TOKENS["ink_muted"]}" stroke-width="1.8" stroke-linecap="round"/></svg>'
    )


def hero_title(text: str) -> str:
    return f'<div class="hero-title"><span class="hl"></span><span class="t">{esc(text)}</span><span class="hl"></span></div>'


def card_html(card: dict) -> str:
    series = "<br>".join(esc(s) for s in card["series"])
    tags = "<br>".join(esc(t) for t in card.get("tags", []))
    steps_html = []
    for st in card["steps"]:
        cap = f'<div class="st-cap">{esc(st["cap"])}</div>' if st.get("cap") else ""
        steps_html.append(
            '<div class="step">'
            f'<div class="st-head"><span class="st-num">{st["n"]}</span>'
            f'<span class="st-title">{esc(st["title"])}</span></div>'
            f'<div class="st-note">{esc(st["note"])}</div>'
            f'<div class="st-fig">{st["fig"]}</div>{cap}</div>')
    idea_eq = card.get("idea_eq_svg", "")
    hero = card["hero"]
    tk = card["takeaway"]
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{esc(card["title"])} · 方法原理卡片</title>
<style>{css()}</style></head>
<body>
<div class="card">
  <div class="head">
    <div class="series">{series}<span class="hash">{esc(card.get("num",""))}</span></div>
    <div class="ttl-wrap">
      <div class="ttl">{esc(card["title"])}</div>
      <div class="sub"><span class="dash l"></span><span class="sub-tag">{esc(card["subtitle"])}</span><span class="dash"></span></div>
    </div>
    <div class="tags">{tags}</div>
  </div>
  <div class="idea">
    <div class="idea-row"><span class="idea-tag">核心思想</span><div class="idea-text">{esc(card["idea_text"])}</div></div>
    <div class="idea-eq">{idea_eq}</div>
  </div>
  <div class="steps">{"".join(steps_html)}</div>
  <div class="hero">{hero_title(hero["title"])}
    <div class="hero-body">{hero["body"]}</div>
    <div class="hero-cap">{esc(hero.get("cap",""))}</div>
  </div>
  <div class="takeaway"><span class="bulb">{bulb_icon()}</span><div class="tk-text">{esc(tk)}</div></div>
</div>
</body></html>
"""


def write_html(card: dict, out: pathlib.Path) -> pathlib.Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(card_html(card), encoding="utf-8")
    return out


# ---------------- 导出通道（Chrome headless 原生，无 Playwright 依赖） ----------------
# 浏览器候选：**只列「不在 PATH 里」的固定安装位**（Windows / macOS）。
# ⭐ POSIX 侧**刻意不硬编码 `/usr/bin/*`**：Linux 上 Chrome/Chromium 的落点随发行版、
# snap、flatpak、brew 而变，穷举必漏；一律交给下面的 `shutil.which()` 按 PATH 解析，
# 而且 PATH 里那个才是用户当前真正可用的版本。
# ⚠️ 这同时消掉一处「平台门控」FAIL —— 与 diagram_export.py 同一条纪律：该形态在
#    v4.34.0 已被抓到过一次，本文件初版又犯了一次（判据要的是跨平台实现，不是把路径写全）。
_CHROME_FIXED = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)
_PATH_BROWSERS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                  "chrome", "msedge")


def _find_chrome() -> str:
    """候选探测 Chrome/Edge 可执行文件（不回退到不可用默认值）。"""
    import os
    import shutil
    cands = [pathlib.Path(p) for p in _CHROME_FIXED]
    localapp = os.environ.get("LOCALAPPDATA")
    if localapp:
        cands.append(pathlib.Path(localapp) / "Google/Chrome/Application/chrome.exe")
    for c in cands:
        if c.exists():
            return str(c)
    for name in _PATH_BROWSERS:
        w = shutil.which(name)
        if w:
            return w
    raise FileNotFoundError(
        "未找到 Chrome/Edge 可执行文件（固定安装位 %d 处与 PATH 均未命中）" % len(cands))


def _run_chrome(args: list, timeout: int = 120):
    import subprocess
    chrome = _find_chrome()
    cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--disable-extensions", "--no-first-run"] + args
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    return r


def export_png(html_path: pathlib.Path, png_path: pathlib.Path, scale: int = 2):
    """Chrome headless 截图 @scale 倍。窗口 = 卡片尺寸，卡片铺满视口。"""
    png_path.parent.mkdir(parents=True, exist_ok=True)
    if png_path.exists():
        png_path.unlink()
    _run_chrome([f"--force-device-scale-factor={scale}",
                 f"--window-size={CARD_W},{CARD_H}",
                 f"--screenshot={png_path}",
                 "--virtual-time-budget=1500",
                 html_path.resolve().as_uri()])
    assert png_path.exists() and png_path.stat().st_size > 0, f"截图未产出：{png_path}"
    return png_path


def export_pdf(html_path: pathlib.Path, pdf_path: pathlib.Path):
    """Chrome --print-to-pdf。页面尺寸由 CSS @page 定义（1200×1600px ⇒ 900×1200pt）。"""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    _run_chrome(["--no-pdf-header-footer",
                 f"--print-to-pdf={pdf_path}",
                 "--virtual-time-budget=1500",
                 html_path.resolve().as_uri()])
    assert pdf_path.exists() and pdf_path.stat().st_size > 0, f"PDF 未产出：{pdf_path}"
    return pdf_path


def main():
    ap = argparse.ArgumentParser(description="methodcard 组装器")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        # 自检：组装一个最小卡并断言结构
        card = {
            "series": ["A", "B"], "num": "#0", "title": "T", "subtitle": "测",
            "tags": ["X"], "idea_text": "一句话。", "idea_eq_svg": "",
            "steps": [{"n": 1, "title": "s", "note": "n", "fig": "<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'><rect width='10' height='10' fill='#000'/></svg>"} for _ in range(4)],
            "hero": {"title": "h", "body": "<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'/>", "cap": ""},
            "takeaway": "tk",
        }
        html = card_html(card)
        assert html.count("<svg") == 6, html.count("<svg")  # 4 步 fig + hero 1 + 灯泡 1
        assert "http://" not in html.replace("http://www.w3.org/2000/svg", ""), "存在远程引用"
        ff = font_faces()
        assert ff, ("字体文件缺失：assets/fonts/playfair-display-{600,700}.woff2 未找到"
                    "（构建会降级到系统字库，PDF 质量与嵌入性无保障）")
        assert ff.count("@font-face") == 2 and "base64," in ff, "font_faces 结构异常"
        print("[selftest] card_html OK；无远程引用 OK；font_faces OK（2 个 @font-face 内嵌）")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
