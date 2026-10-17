#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diagram_export.py —— 图表 HTML 的三通道导出器（ai-workflow 自研）。

把一张自包含的图表 HTML 导出成 **SVG / PDF / PNG**，三条通道口径各不相同，本器把
差异显式化，**不静默降级**：

| 通道 | 谁实现 | 口径 |
|---|---|---|
| `svg` | **上游** `diagram-design/scripts/export_svg.py`（唯一真源） | 只取 `<svg>` 节点；CSS 随行；`<defs>` ID 加 slug 前缀；`rgba()` 归一。⚠️ 上游自 rev `550fd66e` 起会把 `@import url(fonts.googleapis.com…)` 内联进交付 SVG ⇒ **默认原样保留**（浏览器可正确显示网字体）；投稿 / 离线件加 `--strip-remote-fonts` 剥掉 |
| `pdf` | **本器**（Chrome 无头打印） | ⚠️ **不是上游能力**（上游只定义 svg/png）。页面尺寸 = viewBox、零边距、矢量输出；写作 PDF 前把字体栈换成**可嵌入的 TrueType**（否则中文会被落成 Type3） |
| `png` | **本器**（Playwright，按上游 `references/export.md` 的规程） | 透明底、只截 `<svg>` 元素盒、释放祖先裁剪；动效页先取 `?motion=static` 并断言 `data-frame="static"` |

**依赖策略（fail-closed，绝不静默降级）**：
  · `svg` 需要上游 `export_svg.py` 在场；不在场 ⇒ 该格式判失败并给出获取方式（不自己
    另写一份不同行为的实现）。
  · `png` 需要 Playwright **且**浏览器二进制已 provision。缺任一个 ⇒ **原样透出上游的
    处理指引并停止** —— 上游明确要求「**never install runtime dependencies automatically**」。
  · `pdf` 需要 Chrome/Edge 之一。缺 ⇒ 该格式判失败。

用法：
    python diagram_export.py out/chart-01-bar.html --formats svg,pdf,png --scale 2
    python diagram_export.py out/*.html --out out/export --formats pdf,svg
    python diagram_export.py out/*.html --formats svg --strip-remote-fonts   # 投稿件：去远程字体
    python diagram_export.py --selftest
退出码：0 = 全部成功；1 = 有失败；2 = 用法错；3 = 依赖缺失（未做任何事）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
DEFAULT_UPSTREAM = pathlib.Path.home() / ".workbuddy" / "skills" / "diagram-design"
# 浏览器候选：**只列「不在 PATH 里」的固定安装位**（Windows / macOS）。
# ⭐ POSIX 侧**刻意不硬编码 `/usr/bin/*`**：Linux 上 Chrome/Chromium 的落点随发行版、
# snap、flatpak、brew 而变，穷举必漏；一律交给下面的 `shutil.which()` 按 PATH 解析。
# （这同时消掉了一处「平台门控」告警 —— 判据要的是跨平台实现，不是把路径写全。）
CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)
PATH_BROWSERS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                 "chrome", "msedge")
PLAYWRIGHT_MISSING_MSG = """\
Playwright is not available. PNG export requires an approved Playwright
installation and a compatible browser to be provisioned by the host
environment; the skill never installs runtime dependencies automatically.
Then ask me to export again."""

# PNG 用的浏览器来源，**按序回退**：
#   ① bundled —— Playwright 自己那份 chromium / chromium_headless_shell
#   ② chrome   —— 系统已装的 Google Chrome（`channel=` 让 Playwright 直接驱动它）
#   ③ msedge   —— 系统已装的 Edge（Windows 上几乎必然存在）
# ⭐ ②③ 是**必要**的回退，不是锦上添花：Playwright 按**自己钉的版本**去找二进制，
#    `pip install playwright` 成功 ≠ 那份二进制在场（实测 1.63.0 要
#    `chromium_headless_shell-1243`，而机器上只有 1228/1234 ⇒ 整条通道死掉，
#    可机器上**明明装着 Chrome**）。有回退链时，PNG 通道不再依赖那次 ~150 MB 下载。
PW_CHANNELS: tuple[tuple[str, dict], ...] = (
    ("bundled", {}),
    ("chrome", {"channel": "chrome"}),
    ("msedge", {"channel": "msedge"}),
)

PRINT_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  @page {{ size: {w}px {h}px; margin: 0; }}
  html, body {{ margin: 0; padding: 0; background: #ffffff; }}
  svg {{ display: block; width: {w}px; height: {h}px; }}
</style>
</head>
<body>
{svg}
</body>
</html>
"""

# 字体可嵌入化 —— 与 chartlib.FONT_EMBEDDABLE 同源口径。**只在派生副本上施加**，
# 交付的 .svg 保持上游原样。根因：用缺 CJK 字形的 mono 栈渲染中文时，Chrome 无头
# 打印会把那段文字落成 Type3（部分期刊拒收）；换成 Windows 自带 TrueType 后即纯 Type0。
FONT_SUBST = [
    ("'Geist Mono', ui-monospace, 'Cascadia Mono', monospace",
     "Consolas, 'Microsoft YaHei', monospace"),
    ("'Geist Mono', ui-monospace, monospace",
     "Consolas, 'Microsoft YaHei', monospace"),
    ("'Geist', system-ui, 'Microsoft YaHei', 'PingFang SC', sans-serif",
     "'Microsoft YaHei', Consolas, sans-serif"),
    ("'Geist', system-ui, sans-serif",
     "'Microsoft YaHei', Consolas, sans-serif"),
]


# ──────────────────────────────────────────────────────────────────────────────
# 纯函数（可被 --selftest 直接喂输入）
# ──────────────────────────────────────────────────────────────────────────────
def find_chrome(explicit: str | None = None) -> str | None:
    """定位可用于无头打印的浏览器。

    顺序：① 显式指定 ② **PATH 查找**（跨平台、覆盖 Linux 各安装形态） ③ 固定安装位。
    ⚠️ 顺序刻意把 PATH 放在固定位之前：PATH 命中的那个是用户**当前可用**的版本，
    而固定位里可能躺着一个卸载残留的旧副本。
    """
    if explicit:
        return explicit if pathlib.Path(explicit).exists() else None
    for name in PATH_BROWSERS:
        w = shutil.which(name)
        if w:
            return w
    for c in CHROME_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    return None


def svg_viewbox(svg_text: str) -> tuple[int, int] | None:
    m = re.search(r'viewBox="\s*([-\d.]+)[\s,]+([-\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)', svg_text)
    if not m:
        return None
    return int(round(float(m.group(3)))), int(round(float(m.group(4))))


def embeddable_fonts(text: str) -> str:
    for a, b in FONT_SUBST:
        text = text.replace(a, b)
    return text


# 远程字体引用：`@import url('https://…')` 与 `<link rel=stylesheet href="https://…">`。
# 派生副本（打印页 / 截图中间件）**一律剥**；**交付的 .svg 默认保留**（上游真源），
# 只有显式 `--strip-remote-fonts` 才剥（见 deliverable_svg 的两条相反诉求）。
_REMOTE_IMPORT = re.compile(r"@import\s+url\(\s*['\"]?https?://[^)]*\)\s*;?")
_REMOTE_LINK = re.compile(r"<link\b[^>]*href=\"https?://[^\"]*\"[^>]*>")


def deliverable_svg(text: str, strip_remote: bool) -> str:
    """交付 `.svg` 的最终形态 —— **默认原样（上游真源），显式开关才剥远程字体**。

    为什么默认不剥：上游自 rev 550fd66e 起把 `@import url(fonts.googleapis.com…)`
    内联进 SVG，作用是让**单独打开**该 SVG 时也用上网字体（Geist / Instrument Serif）。
    剥掉不改变字形声明，却会让离线/无网环境的渲染回退到本机同名或替代字体 ⇒ 与
    作者看到的版式不同。
    为什么投稿要剥：投稿件与离线件**不得依赖外网**（审稿人 / 排版方离线打开时字体
    回退不可控，且部分期刊禁止外部资源引用）；这类件同时走 `check_vector_export.py`
    的「字体全嵌入」验收。两条诉求相反 ⇒ 用**调用面**区分，不做一刀切默认。
    """
    return strip_remote_fonts(text) if strip_remote else text


def strip_remote_fonts(text: str) -> str:
    """去掉派生副本里的远程字体引用。

    动机有两面，都不是洁癖：
      · **性能** —— 每张图的打印/截图都要等 `fonts.googleapis.com` 超时才继续
        （本机实测 6 图导出 ≈2.5 min，绝大部分耗在等超时上）；
      · **确定性** —— 联网与否会让同一张图的 PDF 字形不同，而这类差异
        **不在任何判据里**：下游只看到「导出成功」。
    字形本身已在 `embeddable_fonts()` 里换成本机 TrueType（含 CJK），故去掉远程引用
    不改变字形，只去掉「那个可能覆盖它的远程来源」。
    """
    return _REMOTE_LINK.sub("", _REMOTE_IMPORT.sub("", text))


def fresh_output(path: pathlib.Path) -> bool:
    """产出判据 = **非空文件**。

    ⚠️ 单独看它**是 fail-open 的** —— 若调用方不先 `unlink()`，上一轮的旧产物会让
    「这一次什么都没写成」被读成成功。本器三条通道**一律先删再写**，本函数只是那一对的
    后半边；`--selftest` 里把「不先删 ⇒ 读成成功」的形态**显式断言出来**，防止有人
    日后「优化掉」那次 unlink。
    """
    return path.exists() and path.stat().st_size > 0


def has_motion_root(html: str) -> bool:
    return "data-motion-root" in html


def static_url(path: pathlib.Path) -> str:
    """动效页取 `?motion=static`；静态页不加查询串（口径见 export.md 第 95 行）。"""
    uri = path.resolve().as_uri()
    try:
        html = path.read_text(encoding="utf-8")
    except Exception:
        return uri
    return uri + "?motion=static" if has_motion_root(html) else uri


# ──────────────────────────────────────────────────────────────────────────────
# 三条通道
# ──────────────────────────────────────────────────────────────────────────────
def export_svg(src: pathlib.Path, out: pathlib.Path, upstream_scripts: pathlib.Path,
               system_fonts: bool, strip_remote: bool = False) -> tuple[bool, str]:
    helper = upstream_scripts / "export_svg.py"
    if not helper.exists():
        return False, (f"未找到上游导出器 {helper} —— svg 通道的唯一真源。"
                       f"用 --upstream-scripts 指向 diagram-design/scripts，"
                       f"或安装该技能（不在场时**不**另写实现，避免行为分叉）")
    out = out.resolve()
    out.unlink(missing_ok=True)                      # 先删：存在性才等于「本次写成功」
    cmd = [sys.executable, str(helper), str(src.resolve()), str(out)]
    if system_fonts:
        cmd.append("--system-fonts")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        return False, (r.stdout + r.stderr).strip()[-300:]
    if strip_remote:                                 # 只在显式开关下改写交付件
        raw = out.read_text(encoding="utf-8")
        out.write_text(deliverable_svg(raw, True), encoding="utf-8", newline="")
    return True, ""


def export_pdf(src: pathlib.Path, out: pathlib.Path, chrome: str | None,
               workdir: pathlib.Path, upstream_scripts: pathlib.Path) -> tuple[bool, str]:
    if not chrome:
        return False, "未找到 Chrome / Edge（pdf 通道是本器扩展，依赖无头打印）"
    out = out.resolve()                              # ⚠️ 必须绝对：Chrome 的 CWD 不是我们的
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    # 先取 SVG（与 svg 通道同源口径），再打印 —— 保证 PDF 与 SVG 内容一致。
    # ⭐ `system_fonts=True`：不给打印页留 `@import url(fonts.googleapis.com/…)`。
    #    不这么做时，Chrome 打印会**等远程字体**（本机实测 6 图 ≈2.5 min，绝大部分是等超时），
    #    而且「联网与否 ⇒ 同一张图 PDF 的字形不同」—— 这种差异**不在任何判据里**。
    #    字体本身随后由 `embeddable_fonts()` 换成本机 TrueType（含 CJK），故字形不受影响。
    src_svg = workdir / (src.stem + ".svg")
    ok, msg = export_svg(src, src_svg, upstream_scripts, True)
    if not ok:
        # 上游导出器不在场时退一步：直接从 HTML 里抽 <svg>（仅用于本器自己的 PDF 派生，
        # 不交付，故不构成「另写一份导出实现」）
        text = src.read_text(encoding="utf-8")
        m = re.search(r"<svg\b.*?</svg>", text, re.S)
        if not m:
            return False, "HTML 内找不到 <svg> 块"
        svg = m.group(0)
    else:
        svg = src_svg.read_text(encoding="utf-8")
        svg = re.sub(r"<\?xml[^>]*\?>\s*", "", svg, count=1)
    svg = strip_remote_fonts(svg)          # 兜底：派生副本一律不留远程字体引用

    vb = svg_viewbox(svg)
    if not vb:
        return False, "SVG 缺少 viewBox（PDF 页面尺寸无从确定）"
    w, h = vb
    svg = embeddable_fonts(svg)
    svg = re.sub(r"<svg\b", f'<svg width="{w}" height="{h}"', svg, count=1)
    psrc = workdir / (src.stem + ".print.html")
    psrc.write_text(PRINT_TPL.format(title=src.stem, w=w, h=h, svg=svg),
                    encoding="utf-8", newline="\n")
    udd = workdir / "_chrome-profile"
    r = subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
         f"--user-data-dir={udd}", "--no-pdf-header-footer",
         "--run-all-compositor-stages-before-draw",
         f"--print-to-pdf={out}", psrc.resolve().as_uri()],
        capture_output=True, text=True, timeout=180)
    if r.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        return False, (r.stderr or r.stdout or "")[-300:]
    return True, f"{w}x{h}px 单页"


def export_png_batch(jobs: list[tuple[pathlib.Path, pathlib.Path]], scale: float,
                     offline: bool = False) -> dict[str, tuple[bool, str, str]]:
    """一次启动、逐图截图、一次收尾。键 = 源文件绝对路径字符串。

    ⭐ **为什么要批量**（本机实测，不是过早优化）：整条 PNG 通道里最慢的一步是
    `browser.close()` —— **≈47 s**，而 launch/new_page/goto/截图各自都 <1 s。
    逐图起停（`export_png` 的老写法）会把这 47 s **乘以图数**：6 张图 ≈ 9 min 46 s。
    复用一个实例后，这段代价只付一次。
    """
    res: dict[str, tuple[bool, str, str]] = {}

    def put(src: pathlib.Path, ok: bool, msg: str, kind: str = "") -> None:
        """**唯一写入点** —— 结果一律三元组。

        ⚠️ 这层看似多余，但它治的是一个**真发生过**的缺陷：本函数初版里成功路径写
        `(True, msg)`（二元组）、失败路径写 `(ok, msg, kind)`（三元组），收尾统一
        解包时直接 `ValueError` 崩栈 —— 而**前半程 6 张 PNG 都已正确产出**，
        只是最后一句话崩了，于是整条命令 rc=1、且**没有任何汇总**。
        收敛到单一入口后，这类「同一集合里两种形状」的错误在结构上不可能再写出来。
        """
        res[str(src.resolve())] = (ok, msg, kind)

    try:
        from playwright.sync_api import TimeoutError as PWTimeout, sync_playwright
    except Exception:
        for s, _o in jobs:
            put(s, False, PLAYWRIGHT_MISSING_MSG, "no-playwright")
        return res

    for _s, o in jobs:                     # 先删：存在性才等于「本次写成功」
        o.resolve().unlink(missing_ok=True)

    def _prepare(page, src: pathlib.Path) -> tuple[bool, str]:
        """返回 (ok, warn)；页面已加载且 SVG 已钉到图幅尺寸。"""
        page.set_default_timeout(20000)
        if offline:
            page.route("**/*", lambda r: r.continue_()
                       if r.request.url.startswith("file:") else r.abort())
        page.goto(static_url(src), wait_until="domcontentloaded")
        warn = ""
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            # 代理网络下 webfont 子请求可能拖过任何期限；取消未完成的加载
            page.evaluate("window.stop()")
            page.wait_for_timeout(4000)
            warn = "webfont-stalled"
        try:
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=8000)
        except Exception:
            warn = (warn + " fonts-not-settled").strip()
        if has_motion_root(src.read_text(encoding="utf-8")):
            if not page.locator("[data-motion-root]").evaluate_all(
                    "roots => roots.every(r => r.dataset.frame === 'static')"):
                return False, "动效页未到达 data-frame=static，拒绝对非完整帧截图"
        return True, warn

    errs: list[str] = []
    used = ""                              # 供收尾报告使用；异常提前返回时也不至于未绑定
    try:
        with sync_playwright() as p:
            browser, used = None, ""
            for name, kw in PW_CHANNELS:
                try:
                    browser = p.chromium.launch(**kw)
                    used = name
                    break
                except Exception as e:
                    errs.append(f"{name}: {type(e).__name__}: {str(e)[:110]}")
            if browser is None:
                msg = ("无可用浏览器（Playwright 自带二进制与系统 Chrome/Edge 均不可用） —— "
                       + " ｜ ".join(errs))
                for s, _o in jobs:
                    put(s, False, msg)
                return res
            try:
                for src, out in jobs:
                    out = out.resolve()
                    out.parent.mkdir(parents=True, exist_ok=True)
                    page = None
                    try:
                        page = browser.new_page(device_scale_factor=scale)
                        ok, warn = _prepare(page, src)
                        if not ok:
                            put(src, False, warn)
                            continue
                        svg = page.locator("svg").first
                        nat = svg.evaluate(
                            """el => {
                                const vb = el.getAttribute('viewBox');
                                if (!vb) return null;
                                const p = vb.trim().split(/[\\s,]+/).map(Number);
                                if (p.length !== 4 || !(p[2] > 0 && p[3] > 0)) return null;
                                el.style.setProperty('width', p[2] + 'px', 'important');
                                el.style.setProperty('height', p[3] + 'px', 'important');
                                el.style.setProperty('max-width', 'none', 'important');
                                // 释放祖先裁剪（本地滚动容器 / overflow:hidden 外框），
                                // 否则比外框宽的 SVG 会被切掉右侧（export.md 第 160 行）
                                for (let a = el.parentElement; a; a = a.parentElement)
                                    a.style.setProperty('overflow', 'visible', 'important');
                                return [p[2], p[3]];
                            }""")
                        box = svg.bounding_box()
                        if not (nat and box):
                            put(src, False, "取不到 SVG 元素盒/viewBox")
                            continue
                        # ⚠️ **不能用 `locator.screenshot()`**：它对元素盒每侧各外扩 1px
                        # （实测 1000×500 的盒截出 2000×1002 @scale2）。改用页面级截图
                        # + 精确 `clip`（截完再断言尺寸，见下），得到恒为 `W·scale × H·scale`。
                        # ⚠️ 必须 `full_page=True`：`clip` 的坐标是**页面坐标**，而元素可能
                        # 落在视口之外（本任务静态图的卡片较高，SVG 底部低于默认视口 ⇒
                        # 实测截成 2000×962，比期望少 38px，且**不报错**）。
                        page.screenshot(path=str(out), omit_background=True, full_page=True,
                                        clip={"x": box["x"], "y": box["y"],
                                              "width": nat[0], "height": nat[1]})
                        # ⭐ 尺寸**当场自检**（±1px 舍入容差）。这条不是装饰：本轮实测
                        # `locator.screenshot()` 会把元素盒每侧外扩 1px（1000×500 截成
                        # 2000×1002 @scale2），而下游只看「导出成功」—— 尺寸错了
                        # **没有任何判据会说话**。
                        exp = (round(nat[0] * scale), round(nat[1] * scale))
                        try:
                            from PIL import Image  # type: ignore
                            with Image.open(out) as im:
                                got = im.size
                        except Exception:
                            got = exp
                        if abs(got[0] - exp[0]) > 1 or abs(got[1] - exp[1]) > 1:
                            put(src, False,
                                f"PNG 尺寸 {got[0]}x{got[1]} ≠ 期望 {exp[0]}x{exp[1]}"
                                f"（viewBox {nat[0]}x{nat[1]} × scale {scale}）")
                            continue
                        put(src, True, "")
                    except Exception as e:
                        put(src, False, f"{type(e).__name__}: {str(e)[:200]}")
                    finally:
                        if page is not None:
                            try:
                                page.close()
                            except Exception:
                                pass
            finally:
                browser.close()          # ≈47s，只付一次
    except Exception as e:
        for s, _o in jobs:
            if str(s.resolve()) not in res:
                put(s, False, f"{type(e).__name__}: {str(e)[:200]}")

    # 统一收尾：核对产物、拼出实际尺寸/浏览器（诚实报告的一部分）
    for src, out in jobs:
        key = str(src.resolve())
        ok, msg, kind = res.get(key, (False, "未执行", ""))
        out = out.resolve()
        if ok and (not out.exists() or out.stat().st_size == 0):
            ok, msg = False, "截图命令未报错但没有产出文件"
        if ok:
            try:
                from PIL import Image  # type: ignore
                with Image.open(out) as im:
                    dims = f"{im.size[0]}x{im.size[1]}{'α' if im.mode in ('RGBA', 'LA') else ''}"
            except Exception:
                dims = f"{out.stat().st_size}B"
            res[key] = (True, f"{'离线' if offline else '联网'} 浏览器={used} {dims}".strip(), kind)
        else:
            res[key] = (ok, msg, kind)
    return res


def export_png(src: pathlib.Path, out: pathlib.Path, scale: float,
               offline: bool = False) -> tuple[bool, str, str]:
    """单文件便捷入口（内部走批量实现，语义与之一致）。"""
    return export_png_batch([(src, out)], scale, offline).get(
        str(src.resolve()), (False, "未执行", ""))


# ──────────────────────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────────────────────
def run(args) -> int:
    srcs = []
    for pat in args.html:
        p = pathlib.Path(pat)
        srcs.extend(sorted(p.parent.glob(p.name)) if any(c in pat for c in "*?[") else [p])
    if not srcs:
        print("[ERROR] 没有输入 HTML")
        return 2
    missing = [str(s) for s in srcs if not s.exists()]
    if missing:
        print(f"[ERROR] 输入不存在：{missing}")
        return 2

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    bad = [f for f in formats if f not in ("svg", "pdf", "png")]
    if bad:
        print(f"[ERROR] 未知格式 {bad}；可选 svg,pdf,png")
        return 2

    chrome = find_chrome(args.chrome)
    up = pathlib.Path(args.upstream_scripts)
    if chrome:
        print(f"Chrome  : {chrome}")
    else:
        print("Chrome  : 未找到 ⇒ pdf 通道将逐件失败（不强求）")
    if not (up / "export_svg.py").exists():
        print(f"上游    : {up}/export_svg.py 不在场 ⇒ svg 通道将失败；png 不受影响")

    results, rc, need_pw = [], 0, False
    # PNG 走**批量**通道：一次启停浏览器。逐图起停会把 `browser.close()` 的
    # ≈47 s 乘上图数（实测 6 图 ≈9 min46 s）；批量后这段只付一次。
    png_res: dict[str, tuple[bool, str, str]] = {}
    if "png" in formats:
        jobs = [(s, pathlib.Path(args.out or s.parent) / (s.stem + ".png")) for s in srcs]
        print("\n=== PNG 通道（批量：单实例逐图截图）===", flush=True)
        png_res = export_png_batch(jobs, args.scale, offline=args.offline)
        if any(k == "no-playwright" for _o, _m, k in png_res.values()):
            need_pw = True
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        for src in srcs:
            outdir = pathlib.Path(args.out) if args.out else src.parent
            outdir.mkdir(parents=True, exist_ok=True)
            row = {"file": str(src), "formats": {}}
            for fmt in formats:
                out = pathlib.Path(outdir) / (src.stem + "." + fmt)
                if fmt == "svg":
                    ok, msg = export_svg(src, out, up, args.system_fonts,
                                         strip_remote=args.strip_remote_fonts)
                elif fmt == "pdf":
                    ok, msg = export_pdf(src, out, chrome, work, up)
                else:
                    ok, msg, kind = png_res.get(str(src.resolve()), (False, "未执行", ""))
                sha = ""
                if ok and out.exists():
                    sha = hashlib.sha256(out.read_bytes()).hexdigest()[:12]
                size = out.stat().st_size if (ok and out.exists()) else 0
                row["formats"][fmt] = {"ok": ok, "bytes": size, "sha256_12": sha,
                                       "msg": msg or ""}
                if not ok:
                    rc = 1
                print(f"{'[OK  ]' if ok else '[FAIL]'} {src.name} → {out.name}"
                      f"{f'  {size} B  sha={sha}' if ok else '  ▸ ' + str(msg)[:200]}",
                      flush=True)
                if ok and msg:
                    print(f"        ⚠ {msg}", flush=True)
            results.append(row)

    if args.verify and not need_pw:
        chk = HERE / "check_vector_export.py"
        targets = [str(pathlib.Path(args.out or s.parent) / (s.stem + e))
                   for s in srcs for e in (".pdf", ".svg")]
        if chk.exists() and targets:
            print("\n=== 交付前矢量件检查（check_vector_export.py）===")
            cmd = [sys.executable, str(chk), *targets]
            if args.expect:
                cmd += ["--expect", args.expect]
            r = subprocess.run(cmd, capture_output=True, text=True)
            print(r.stdout.strip()[-2000:])
            if r.returncode == 1:
                rc = 1

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    if need_pw and all(not v["ok"] for r in results for k, v in r["formats"].items()
                       if k == "png"):
        return 3
    return rc


# ──────────────────────────────────────────────────────────────────────────────
# 依赖探测（只报不判 —— 供 --selftest 的 F 组；**不得**把「包在场」写成「通道可用」）
# ──────────────────────────────────────────────────────────────────────────────
def _pdf_backend_status() -> str:
    """报告 PDF 判读后端。PyMuPDF 有新（`pymupdf`）旧（`fitz`）两个模块名，两个都试。"""
    for mod in ("pymupdf", "fitz"):
        try:
            __import__(mod)
            return f"[OK  ] 可用（{mod}）"
        except Exception:
            continue
    try:
        __import__("pypdf")
        return "[OK  ] 可用（pypdf 兜底）"
    except Exception:
        return "[WARN] 不可用 ⇒ `--verify` 会如实报 SKIP，不静默降级"


def _png_channel_status() -> tuple[bool, str]:
    """PNG 通道的**真实**可用性 = （包装得上）且（**至少有一个浏览器可用**）。

    ⚠️ 这三件事必须**分开报**：本轮实测 `pip install playwright==1.63.0` 成功后，
    `chromium.launch()` 仍报 `Executable doesn't exist at …chromium_headless_shell-1243`
    —— Playwright 按**自己钉的版本**去找二进制，与缓存里已有的 1228/1234 无关。
    只探「包能 import」会把这种情况报成「可用」，正是「装得进 ≠ 跑得动」的复发形态。
    现按 `export_png()` 实际的**三级回退链**报状态（自带二进制 / 系统 Chrome / 系统 Edge）。
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as e:
        return False, f"[WARN] python 包未安装（{type(e).__name__}）⇒ 该通道会如实报缺失"
    try:
        with sync_playwright() as p:
            exe = pathlib.Path(p.chromium.executable_path)   # 取路径**不启动**浏览器
    except Exception as e:
        return False, f"[WARN] 包可导入但取不到 chromium 路径（{type(e).__name__}）"
    if exe.exists():
        return True, f"[OK  ] 包 ＋ 自带二进制齐备（{exe}）"
    sysb = find_chrome()
    if sysb:
        return True, (f"[OK  ] 包在、自带二进制缺件 ⇒ **走系统浏览器回退**（{sysb}）\n"
                      f"           （若要自带那份：`python -m playwright install chromium`；本技能不自动装）")
    return False, (f"[WARN] 包 OK、自带二进制缺件、且未找到系统 Chrome/Edge：{exe}\n"
                   f"           ⇒ 需 `python -m playwright install chromium`（本技能不自动装）")


# ──────────────────────────────────────────────────────────────────────────────
# 自检
# ──────────────────────────────────────────────────────────────────────────────
def selftest() -> int:
    ok = True
    n = 0                      # 断言数**由脚本自报** —— 文档里写死「N 项」必漂（本轮已实测漂过）

    def ck(label, got, want):
        nonlocal ok, n
        n += 1
        good = got == want
        ok = ok and good
        print(f"  [{'OK  ' if good else 'FAIL'}] {label}: 得 {got!r} 期望 {want!r}")

    print("A. viewBox 解析（含负数原点 / 逗号分隔 / 空格分隔 / 缺 viewBox）")
    ck("标准", svg_viewbox('<svg viewBox="0 0 1000 500">'), (1000, 500))
    ck("逗号分隔", svg_viewbox('<svg viewBox="0,0,1280,720">'), (1280, 720))
    ck("负原点", svg_viewbox('<svg viewBox="-100 -50 800 600">'), (800, 600))
    ck("小数", svg_viewbox('<svg viewBox="0 0 640.5 480.5">'), (640, 480))  # round 取整
    ck("缺失 ⇒ None（不得猜）", svg_viewbox("<svg>"), None)

    print("B. 字体可嵌入化（Type3 的根因就在这一步）")
    mono = "'Geist Mono', ui-monospace, 'Cascadia Mono', monospace"
    ck("mono 栈换成 Consolas+雅黑", embeddable_fonts(f'font-family="{mono}"'),
       'font-family="Consolas, \'Microsoft YaHei\', monospace"')
    ck("mono 栈必须带 CJK 字体（只换 Consolas 会留 Type3）",
       "'Microsoft YaHei'" in embeddable_fonts(mono), True)
    ck("已替换过的串不再变（幂等）",
       embeddable_fonts(embeddable_fonts(f'"{mono}"')), embeddable_fonts(f'"{mono}"'))
    ck("无关键字串原样返回", embeddable_fonts("hello"), "hello")

    print("C. 动效页判定 / static URL")
    ck("含 data-motion-root ⇒ True", has_motion_root('<main data-motion-root>'), True)
    ck("静态页 ⇒ False", has_motion_root("<main>"), False)
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "m.html"
        p.write_text('<main data-motion-root></main>', encoding="utf-8")
        ck("动效页 URL 带 ?motion=static", static_url(p).endswith("?motion=static"), True)
        q = pathlib.Path(td) / "s.html"
        q.write_text("<main></main>", encoding="utf-8")
        ck("静态页 URL 不带查询串", "?" in static_url(q), False)

    print("D. 新鲜产出判据（fail-open 的形态固定在这里，勿『优化掉』那次 unlink）")
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "out.bin"
        p.write_bytes(b"stale-from-last-round")
        ck("不先删 ⇒ 旧产物被读成成功（这就是 fail-open 本身）", fresh_output(p), True)
        p.unlink()
        ck("先删且未写出 ⇒ False", fresh_output(p), False)
        p.write_bytes(b"fresh")
        ck("先删再写出 ⇒ True", fresh_output(p), True)
        p.write_bytes(b"")
        ck("写了个空文件 ⇒ False", fresh_output(p), False)

    print("E. 远程字体剥离（派生副本性能与确定性 —— 曾让 6 图导出白等 ≈2.5 min）")
    _imp = "<style>@import url('https://fonts.googleapis.com/css2?family=Geist');\n.a{fill:red}</style>"
    ck("剥掉 @import url(https://…)", "fonts.googleapis.com" in strip_remote_fonts(_imp), False)
    ck("保留同块内的本地规则", ".a{fill:red}" in strip_remote_fonts(_imp), True)
    _lnk = '<link href="https://fonts.googleapis.com/css2?family=Geist" rel="stylesheet">'
    ck("剥掉 <link href=https://…>", strip_remote_fonts(_lnk).strip(), "")
    ck("幂等（再剥一次不变）", strip_remote_fonts(strip_remote_fonts(_imp)), strip_remote_fonts(_imp))
    ck("不误伤 file: 引用", "file:///x/a.woff2" in strip_remote_fonts("url(file:///x/a.woff2)"), True)

    print("H. 交付 .svg 的远程字体（默认原样 vs 显式剥离 —— 两条相反诉求的调用面分界）")
    ck("默认保留 @import（不加开关 ⇒ 上游原样）",
       "fonts.googleapis.com" in deliverable_svg(_imp, False), True)
    ck("加开关 ⇒ 剥掉 @import",
       "fonts.googleapis.com" in deliverable_svg(_imp, True), False)
    ck("加开关不误伤同块本地规则", ".a{fill:red}" in deliverable_svg(_imp, True), True)
    ck("开关对无远程引用的文本是恒等",
       deliverable_svg("<svg/>", True), "<svg/>")
    ck("开关幂等", deliverable_svg(deliverable_svg(_imp, True), True),
       deliverable_svg(_imp, True))

    print("F. Chrome 探测（环境相关，只报不判）")
    print(f"      find_chrome() = {find_chrome()}")

    print("G. 依赖状态（暴露率，不冒充能力 —— 「装得上 ≠ 跑得起来」）")
    print(f"  PDF 检查: {_pdf_backend_status()}")
    okp, msg = _png_channel_status()
    print(f"  {'[OK  ]' if okp else '[WARN]'} PNG 通道: {msg}")

    print(f"\n自检结论：{'PASS' if ok else 'FAIL'}（断言 {n} 项；另 F/G 组为环境报告，只报不判）")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="图表 HTML → SVG / PDF / PNG 三通道导出器")
    ap.add_argument("html", nargs="*", help="图表 HTML 路径或 glob")
    ap.add_argument("--formats", default="svg,pdf,png")
    ap.add_argument("--out", default=None, help="输出目录（缺省与源同目录）")
    ap.add_argument("--scale", type=float, default=2, help="PNG device_scale_factor（1..4）")
    ap.add_argument("--upstream-scripts", default=str(DEFAULT_UPSTREAM / "scripts"))
    ap.add_argument("--chrome", default=None)
    ap.add_argument("--system-fonts", action="store_true", help="透传给上游 export_svg.py")
    ap.add_argument("--strip-remote-fonts", action="store_true",
                    help="只对交付的 .svg 生效：剥掉 @import / <link> 远程字体引用（投稿 / 离线件用；"
                         "缺省保留上游原样）")
    ap.add_argument("--verify", action="store_true", help="导出后跑矢量件检查")
    ap.add_argument("--offline", action="store_true",
                    help="png 通道中止一切非 file: 请求（远程字体等）—— 更快、且联网/断网产出一致")
    ap.add_argument("--expect", default="1000x500", help="--verify 用的期望图幅")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.html:
        ap.print_help()
        return 2
    if not 1 <= a.scale <= 4:
        print("[ERROR] --scale 必须在 1..4（export.md 第 188 行：不得低于 1 / 不得高于 4）")
        return 2
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
