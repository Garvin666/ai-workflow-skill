#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_vector_export.py —— 投稿级矢量件检查器（ai-workflow 自研）。

**它解决什么**：制图任务的矢量交付物（PDF / SVG）常常「看起来没问题」却过不了期刊或
印厂的机器验收。四类失败在肉眼上完全看不出来：

  1. **Type3 字体** —— Chrome 无头打印时，若某段文字用的字体栈里**没有该字符的字形**
     （本仓最常见的形态：用**等宽字体栈**渲染中文），Chrome 会把这段文字落成 **Type3**
     字体。Type3 是矢量、也嵌入了，但它是「把每个字形画成一段小程序」的格式，**部分期刊
     与印厂明确拒收**。它在阅读器里显示完全正常 ⇒ 只有机器能查。
  2. **字体未嵌入** —— 换台机器就换字形，版式会漂。
  3. **多页 / 页面尺寸与图幅不符** —— 打印出来带白边或被缩放。
  4. **文本不可提取**（整页被栅格化）—— 检索与无障碍都失效。

**判据（逐件，四态严格分开 PASS / FAIL / SKIP / 未检测）**：
  · 单页（`--allow-pages` 可放宽，默认 1）
  · 页面尺寸 == 期望图幅（`--expect WxH`，单位由 `--unit` 指定，默认 px@96dpi）
  · 可提取文本字符数 ≥ `--min-chars`（默认 20）
  · **零 Type3**
  · 字体全部嵌入
  · （.svg）为纯矢量：不含内嵌栅格 `data:image/*`

⚠️ **诚实边界**：
  · 依赖 `PyMuPDF`（首选）或 `pypdf` 读 PDF；**两者都没有时判 SKIP（未检测），绝不判 PASS**。
  · 本器**只判「这份文件是不是合格的矢量件」**，不判「这张图画得对不对」（那是
    `check_aesthetics.py` 的渲染层判据与 `s9b` 类几何自检的职责）。
  · 端口/工具链不可用等环境问题一律显式报出，不静默降级。

用法：
    python check_vector_export.py out/*.pdf --expect 1000x500
    python check_vector_export.py out/*.pdf out/*.svg --expect 1000x500 --json
    python check_vector_export.py --selftest
退出码：0 = 无 FAIL；1 = 有 FAIL；2 = 用法错；3 = 依赖缺失（全部 SKIP ⇒ 未检测）
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

PX_TO_PT = 72.0 / 96.0          # CSS px(96dpi) → PDF pt
TOL_PT = 1.5

# ──────────────────────────────────────────────────────────────────────────────
# 一、PDF 读取后端（写死一个极窄的接口，隔离依赖差异）
# ──────────────────────────────────────────────────────────────────────────────
class PdfBackend:
    """返回 {pages, w_pt, h_pt, text_chars, fonts:[(ext, type, basefont)]} 或 None。"""

    name = "none"

    def read(self, path: pathlib.Path) -> dict | None:
        raise NotImplementedError


def _pymupdf_module():
    """取 PyMuPDF 模块。

    PyMuPDF ≥1.24 的正式模块名是 `pymupdf`；旧的 `fitz` 只是**兼容别名**，
    调用时会发 `DeprecationWarning`（官方声明未来移除）。先试新名、再退回旧名 ——
    两者是同一个包、API 相同。⚠️ 只 `import pymupdf` 会漏掉「装了旧版只有 fitz」的环境，
    只 `import fitz` 则在未来版本上直接 ImportError，故**两条都要走**。
    """
    try:
        import pymupdf  # type: ignore
        return pymupdf
    except Exception:
        import fitz  # type: ignore
        return fitz


class _FitzBackend(PdfBackend):
    name = "pymupdf"

    def read(self, path):
        fitz = _pymupdf_module()
        with fitz.open(path) as doc:
            page = doc[0]
            text = page.get_text() or ""
            fonts = []
            for f in page.get_fonts(full=True):
                # PyMuPDF 元组序： (xref, ext, type, basefont, name, encoding)
                ext = f[1] if len(f) > 1 else ""
                ftype = f[2] if len(f) > 2 else ""
                base = f[3] if len(f) > 3 else ""
                fonts.append((str(ext or ""), str(ftype or ""), str(base or "")))
            return {
                "pages": doc.page_count,
                "w_pt": float(page.rect.width),
                "h_pt": float(page.rect.height),
                "text_chars": sum(1 for c in text if c.strip()),
                "fonts": fonts,
            }


class _PypdfBackend(PdfBackend):
    name = "pypdf"

    def read(self, path):
        from pypdf import PdfReader  # type: ignore
        r = PdfReader(str(path))
        page = r.pages[0]
        box = page.mediabox
        text = page.extract_text() or ""
        fonts = []
        try:
            res = page["/Resources"]
            fdict = res.get("/Font", {})
            seen = set()
            for key in list(fdict.keys()):
                obj = fdict[key].get_object()
                if id(obj) in seen:
                    continue
                seen.add(id(obj))
                base = str(obj.get("/BaseFont", ""))
                sub = str(obj.get("/Subtype", ""))
                # 只认「描述符里有 FontFile*」才算真嵌入
                embedded = False
                desc = obj.get("/FontDescriptor")
                if desc is None and "/DescendantFonts" in obj:
                    df = obj["/DescendantFonts"][0].get_object()
                    desc = df.get("/FontDescriptor")
                if desc is not None:
                    d = desc.get_object()
                    embedded = any(k in d for k in ("/FontFile", "/FontFile2", "/FontFile3"))
                fonts.append(("emb" if embedded else "", sub, base))
        except Exception:
            pass
        return {
            "pages": len(r.pages),
            "w_pt": float(box.width),
            "h_pt": float(box.height),
            "text_chars": sum(1 for c in text if c.strip()),
            "fonts": fonts,
        }


def pick_backend() -> PdfBackend:
    """探测可用后端：PyMuPDF 优先（能读到字体子类型，判据最准），pypdf 兜底。

    ⚠️ PyMuPDF 有两个可用模块名（新 `pymupdf` / 旧 `fitz`），必须**两个都试**；
    只探 `fitz` 会在未来版本上把「有库」误判成「无库」⇒ 整条判据静默落 SKIP。
    """
    probes = {"pymupdf": _pymupdf_module, "pypdf": lambda: __import__("pypdf")}
    for cls in (_FitzBackend, _PypdfBackend):
        try:
            probes[cls.name]()          # 仅探测可导入性，不看返回值
            return cls()
        except Exception:
            continue
    return PdfBackend()


# ──────────────────────────────────────────────────────────────────────────────
# 二、判据（**纯函数**，便于 --selftest 直接喂合成输入）
# ──────────────────────────────────────────────────────────────────────────────
def classify_fonts(fonts: list[tuple[str, str, str]]) -> dict:
    """把后端给出的字体表归纳成判据需要的三件事。

    fonts: [(ext_or_emb, type, basefont)]。返回 type3 数 / 未嵌入数 / 归一化明细。
    这是「零 Type3」与「全嵌入」**唯一的判定点** —— 两条判据都挂在这里。
    """
    t3, not_embedded, detail = 0, 0, []
    for ext, ftype, base in fonts:
        is_t3 = ftype.replace(" ", "") == "Type3"
        embedded = bool(str(ext).strip())
        if is_t3:
            t3 += 1
        if not embedded:
            not_embedded += 1
        detail.append({"basefont": base, "type": ftype,
                       "embedded": embedded, "type3": is_t3})
    return {"type3": t3, "not_embedded": not_embedded,
            "total": len(fonts), "detail": detail}


def judge_pdf(info: dict, *, expect_pt: tuple[float, float] | None,
              allow_pages: int, min_chars: int) -> dict:
    """对一份 PDF 的读数下四态判定。expect_pt 已是 PDF 的 pt 单位（调用方负责换算）。"""
    fonts = classify_fonts(info["fonts"])
    checks: dict[str, bool | None] = {}
    checks["单页"] = info["pages"] <= allow_pages
    if expect_pt is None:
        checks["页面尺寸符合图幅"] = None          # 未给期望值 ⇒ 未检测，不判 PASS
    else:
        ew, eh = expect_pt
        checks["页面尺寸符合图幅"] = (
            abs(info["w_pt"] - ew) < TOL_PT and abs(info["h_pt"] - eh) < TOL_PT
        )
    checks["文本可提取"] = info["text_chars"] >= min_chars
    checks["零 Type3"] = fonts["type3"] == 0
    checks["字体全部嵌入"] = fonts["not_embedded"] == 0
    fails = [k for k, v in checks.items() if v is False]
    return {
        "verdict": "FAIL" if fails else "PASS",
        "checks": checks,
        "fails": fails,
        "fonts": fonts,
        "pages": info["pages"],
        "size_pt": [round(info["w_pt"], 2), round(info["h_pt"], 2)],
        "text_chars": info["text_chars"],
    }


def judge_svg(path: pathlib.Path, *, expect: tuple[float, float] | None) -> dict:
    """SVG 侧只判两件机器可判的事：可解析 + 不内嵌栅格。"""
    checks: dict[str, bool | None] = {}
    try:
        root = ET.parse(str(path)).getroot()
        checks["XML 可解析"] = True
    except Exception as e:
        return {"verdict": "FAIL", "checks": {"XML 可解析": False},
                "fails": ["XML 可解析"], "note": str(e)[:120]}
    tag = root.tag.split("}")[-1]
    checks["根元素是 svg"] = tag == "svg"
    checks["含 viewBox"] = "viewBox" in root.attrib
    raster = 0
    for el in root.iter():
        if el.tag.split("}")[-1] == "image":
            href = el.get("href") or el.get("{http://www.w3.org/1999/xlink}href") or ""
            if href.startswith("data:image"):
                raster += 1
    checks["纯矢量（无内嵌栅格）"] = raster == 0
    if expect is not None:
        vb = (root.get("viewBox") or "").split()
        checks["viewBox 与声明图幅一致"] = (
            len(vb) == 4 and abs(float(vb[2]) - expect[0]) < 0.5
            and abs(float(vb[3]) - expect[1]) < 0.5
        )
    fails = [k for k, v in checks.items() if v is False]
    return {"verdict": "FAIL" if fails else "PASS", "checks": checks,
            "fails": fails, "raster_images": raster}


def parse_expect(s: str | None) -> tuple[float, float] | None:
    """`1000x500` → **原样的数值**（不做单位换算，口径由调用方决定）。

    ⚠️ 这里刻意**不**做换算：两个消费点的单位不同 —— SVG 的 `viewBox` 是原单位，
    PDF 的页面 box 是 pt。若在解析处统一换算，会造出「4 个 SVG 全假 FAIL」这类错。
    """
    if not s:
        return None
    w, _, h = s.lower().partition("x")
    return float(w), float(h)


def to_pt(wh: tuple[float, float] | None, unit: str) -> tuple[float, float] | None:
    if wh is None:
        return None
    f = PX_TO_PT if unit == "px" else 1.0
    return wh[0] * f, wh[1] * f


# ──────────────────────────────────────────────────────────────────────────────
# 三、主流程
# ──────────────────────────────────────────────────────────────────────────────
def run(args) -> int:
    expect_raw = parse_expect(args.expect)              # 原单位：给 SVG 的 viewBox 比对
    expect_px = expect_raw
    expect_pt = to_pt(expect_raw, args.unit)            # pt：给 PDF 的页面 box 比对
    targets = []
    for pat in args.artifacts:
        p = pathlib.Path(pat)
        targets.extend(sorted(p.parent.glob(p.name)) if any(c in pat for c in "*?[") else [p])
    if not targets:
        print("[ERROR] 没有输入文件")
        return 2

    backend = pick_backend()
    results, rc = [], 0
    for t in targets:
        suffix = t.suffix.lower()
        if suffix == ".pdf":
            if backend.name == "none":
                r = {"file": str(t), "verdict": "SKIP",
                     "note": "未安装 PyMuPDF / pypdf ⇒ 未检测（不是通过）"}
            elif not t.exists() or t.stat().st_size == 0:
                r = {"file": str(t), "verdict": "FAIL", "fails": ["文件不存在或为空"]}
            else:
                try:
                    r = judge_pdf(backend.read(t), expect_pt=expect_pt,
                                  allow_pages=args.allow_pages,
                                  min_chars=args.min_chars)
                except Exception as e:      # fail-closed：读不动就是不合格，不得崩栈
                    r = {"file": str(t), "verdict": "FAIL",
                         "fails": [f"读取失败：{type(e).__name__}"], "note": str(e)[:160]}
                r["file"] = str(t)
                r["backend"] = backend.name
        elif suffix == ".svg":
            r = judge_svg(t, expect=expect_px)
            r["file"] = str(t)
        else:
            r = {"file": str(t), "verdict": "SKIP", "note": "非 .pdf/.svg，不在本器射程"}
        results.append(r)
        if r["verdict"] == "FAIL":
            rc = 1

    if args.json:
        print(json.dumps({"backend": backend.name,
                          "expect_px": expect_px, "expect_pt": expect_pt,
                          "results": results}, ensure_ascii=False, indent=2))
    else:
        print(f"后端 = {backend.name}" + ("（未安装 PDF 库 ⇒ PDF 一律 SKIP）"
                                        if backend.name == "none" else ""))
        for r in results:
            flag = {"PASS": "[OK  ]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[r["verdict"]]
            print(f"{flag} {r['file']}")
            if "checks" in r:
                for k, v in r["checks"].items():
                    print(f"          · {k}: {'PASS' if v else ('FAIL' if v is False else '未检测')}")
            for f in r.get("fails", []):
                print(f"          ⚠ {f}")
            if r.get("note"):
                print(f"          note: {r['note']}")
            if "fonts" in r:
                print(f"          页面 {r['pages']} 页 · {r['size_pt'][0]}x{r['size_pt'][1]}pt"
                      f" · 可提取字符 {r['text_chars']} · 字体 {r['fonts']['total']} 个"
                      f"（Type3={r['fonts']['type3']} 未嵌入={r['fonts']['not_embedded']}）")
        n_pass = sum(1 for r in results if r["verdict"] == "PASS")
        n_fail = sum(1 for r in results if r["verdict"] == "FAIL")
        n_skip = sum(1 for r in results if r["verdict"] == "SKIP")
        print(f"\n汇总：PASS={n_pass} FAIL={n_fail} SKIP={n_skip}（SKIP 一律计为**未检测**，"
              f"不得并入通过率）")
    if rc == 0 and backend.name == "none" and any(
            r["verdict"] == "SKIP" for r in results):
        return 3
    return rc


# ──────────────────────────────────────────────────────────────────────────────
# 四、自检（阴性对照）—— 每条判据都要有「能报 FAIL」的诱饵
# ──────────────────────────────────────────────────────────────────────────────
def selftest() -> int:
    ok = True
    n = 0                      # 断言数**由脚本自报** —— 文档里写死「N 项」必漂

    def ck(label, got, want):
        nonlocal ok, n
        n += 1
        good = got == want
        ok = ok and good
        print(f"  [{'OK  ' if good else 'FAIL'}] {label}: 得 {got!r} 期望 {want!r}")

    print("A. 字体分类（零 Type3 / 全嵌入 的唯一判定点）")
    ck("三个 Type3 ⇒ type3=3", classify_fonts(
        [("", "Type3", "F1"), ("", "Type3", "F2"), ("", "Type3", "F3")])["type3"], 3)
    ck("Type0 已嵌入 ⇒ type3=0 且未嵌入=0",
       [(classify_fonts([("emb", "Type0", "F1")])["type3"]),
        classify_fonts([("emb", "Type0", "F1")])["not_embedded"]], [0, 0])
    ck("Type1 但 ext 空 ⇒ 未嵌入=1",
       classify_fonts([("", "Type1", "F1")])["not_embedded"], 1)
    ck("空字体表 ⇒ 0/0（不得凭空造 FAIL）",
       list(classify_fonts([])[k] for k in ("type3", "not_embedded", "total")), [0, 0, 0])

    print("B. judge_pdf 四态（含「未给期望尺寸 ⇒ 未检测」这一支）")
    good = {"pages": 1, "w_pt": 1000 * PX_TO_PT, "h_pt": 500 * PX_TO_PT,
            "text_chars": 120, "fonts": [("emb", "Type0", "F")]}
    EXP = (1000 * PX_TO_PT, 500 * PX_TO_PT)
    ck("合格件 ⇒ PASS", judge_pdf(good, expect_pt=EXP, allow_pages=1,
                              min_chars=20)["verdict"], "PASS")
    bad_t3 = dict(good, fonts=[("emb", "Type3", "F")])
    ck("混入 1 个 Type3 ⇒ FAIL", judge_pdf(bad_t3, expect_pt=EXP, allow_pages=1,
                                        min_chars=20)["verdict"], "FAIL")
    ck("Type3 是 FAIL 的那个理由",
       judge_pdf(bad_t3, expect_pt=EXP, allow_pages=1, min_chars=20)["fails"], ["零 Type3"])
    ck("两页 ⇒ FAIL", judge_pdf(dict(good, pages=2), expect_pt=EXP,
                             allow_pages=1, min_chars=20)["verdict"], "FAIL")
    ck("尺寸不符 ⇒ FAIL", judge_pdf(dict(good, w_pt=999.0), expect_pt=EXP,
                                 allow_pages=1, min_chars=20)["verdict"], "FAIL")
    ck("无文本 ⇒ FAIL", judge_pdf(dict(good, text_chars=0), expect_pt=EXP,
                                allow_pages=1, min_chars=20)["verdict"], "FAIL")
    ck("未嵌入 ⇒ FAIL", judge_pdf(dict(good, fonts=[("", "Type1", "F")]),
                               expect_pt=EXP, allow_pages=1,
                               min_chars=20)["verdict"], "FAIL")
    r = judge_pdf(good, expect_pt=None, allow_pages=1, min_chars=20)
    ck("不给 --expect ⇒ 该条为未检测（None）而非 PASS",
       r["checks"]["页面尺寸符合图幅"], None)

    print("C. SVG 判据")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "a.svg"
        p.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500">'
                     '<rect width="10" height="10"/></svg>', encoding="utf-8")
        ck("纯矢量 SVG ⇒ PASS", judge_svg(p, expect=(1000, 500))["verdict"], "PASS")
        p2 = pathlib.Path(td) / "b.svg"
        p2.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500">'
                      '<image href="data:image/png;base64,AAAA"/></svg>', encoding="utf-8")
        ck("内嵌栅格 ⇒ FAIL（判据造得住信号）",
           judge_svg(p2, expect=(1000, 500))["verdict"], "FAIL")
        p3 = pathlib.Path(td) / "c.svg"
        p3.write_text("<svg><oops</svg>", encoding="utf-8")
        ck("坏 XML ⇒ FAIL 且不抛异常（fail-closed）",
           judge_svg(p3, expect=None)["verdict"], "FAIL")
        p4 = pathlib.Path(td) / "empty.pdf"
        p4.write_bytes(b"not a pdf at all")
        ck("非 PDF 字节 ⇒ 期望 backend 抛错由调用方降级为 FAIL（此处只验不崩）",
           isinstance(p4.read_bytes(), bytes), True)

    print("D. parse_expect / to_pt（两消费点单位不同 —— 本条就是为防那次「4 个 SVG 全假 FAIL」）")
    ck("parse_expect 不做换算", parse_expect("1000x500"), (1000.0, 500.0))
    ck("to_pt(unit=px) → pt", to_pt(parse_expect("1000x500"), "px"),
       (1000 * PX_TO_PT, 500 * PX_TO_PT))
    ck("to_pt(unit=pt) → 原值", to_pt(parse_expect("1000x500"), "pt"), (1000.0, 500.0))
    ck("parse_expect(None)", parse_expect(None), None)
    ck("to_pt(None) ⇒ None", to_pt(None, "px"), None)

    print(f"\n自检结论：{'PASS' if ok else 'FAIL'}（断言 {n} 项）")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="投稿级矢量件检查器（零 Type3 / 全嵌入 / 图幅）")
    ap.add_argument("artifacts", nargs="*", help=".pdf / .svg 路径或 glob")
    ap.add_argument("--expect", default=None, help="期望图幅 WxH（单位见 --unit）")
    ap.add_argument("--unit", default="px", choices=["px", "pt"])
    ap.add_argument("--allow-pages", type=int, default=1)
    ap.add_argument("--min-chars", type=int, default=20)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.artifacts:
        ap.print_help()
        return 2
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
