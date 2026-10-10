"""s3: 审美判据集新增 H 层（借自 lucasmarkes/hairline）+ check_aesthetics.py 实现。

设计口径（见确认表「前置裁决」）：**按 judgeability 分档** ——
  能机器量的 → machine（本轮实跑）；只有眼睛能看的 → manual（check: null ⇒ 产出 SKIP「人审点」）。
已先做重叠排除：rule 02 → 既有 G16；rule 06 → 既有 R4；rule 04 的强调色半面 → 既有 G2/G8。
"""
import pathlib

RUBRIC = pathlib.Path("references/aesthetic-rubric.yaml")
CHECKER = pathlib.Path("scripts/check_aesthetics.py")

# ============================ 一、校验器 ============================
cs = CHECKER.read_text(encoding="utf-8")


def sub(text, old, new, label, count=1):
    n = text.count(old)
    if n != count:
        raise SystemExit(f"[FAIL] {label}: 期望命中 {count} 次，实际 {n} 次\n---\n{old[:220]}\n---")
    return text.replace(old, new)


# 1) 版本号
cs = sub(cs, 'VERSION = "1.8.0"', 'VERSION = "1.9.0"', "VERSION")

# 2) extract_css：新增三组取数（插在 return 之前）
EXTRACT_BLOCK = '''    # v1.9.0（H 层，借自 hairline）：缓动 / 阴影滤镜 / 无限循环 三组取数。
    #   与既有 motion_decls 同源（都走 _DECL_RE），但**另立三门**：H1 要缓动、H2 要深度效果、H3 要循环性，
    #   三者都与「有没有时长」正交 —— 混进 motion_decls 会让 M1 的覆盖面被稀释。
    motion_easings, depth_decls, infinite_decls = [], [], []
    _EASE_PROPS = _DUR_PROPS | {"transition-timing-function", "animation-timing-function"}
    for m in _DECL_RE.finditer(css):
        prop = m.group(1).lower()
        val = m.group(2).strip()
        _norm2 = re.sub(r"\\s*!important\\s*$", "", val, flags=re.I).strip().lower()
        if _norm2 in _NO_MOTION_KEYWORDS:
            continue                      # `none` 是「没有」，不是「有但劣化」
        if prop in _EASE_PROPS:
            _e = _easing_of(val)
            if _e:
                motion_easings.append({"decl": f"{prop}: {val[:48]}", "easing": _e})
        elif prop in ("box-shadow", "text-shadow", "filter"):
            depth_decls.append({"prop": prop, "value": val[:64]})
        if prop in ("animation", "animation-iteration-count") and re.search(r"\\binfinite\\b", val, re.I):
            infinite_decls.append(f"{prop}: {val[:48]}")

    return {
        "colors": colors,'''

cs = sub(cs, '''    return {
        "colors": colors,''', EXTRACT_BLOCK, "extract_css 取数块")

cs = sub(cs, '''        "radial_blocks": radial_blocks,         # v1.6.0：含 radial 的块 + 其声明的层
    }''', '''        "radial_blocks": radial_blocks,         # v1.6.0：含 radial 的块 + 其声明的层
        "motion_easings": motion_easings,       # v1.9.0：动效缓动（H1 的对象）
        "depth_decls": depth_decls,             # v1.9.0：box-shadow / text-shadow / filter（H2 的对象）
        "infinite_decls": infinite_decls,       # v1.9.0：无限循环动画（H3 的对象）
        "has_reduced_motion": "prefers-reduced-motion" in css,  # v1.9.0：H3 的兜底依据
    }''', "extract_css 返回字典")

# 3) 新增 helper + 3 个检查器（插在 CHECKS 注册表之前）
NEW_CHECKS = '''# --------------------------------------------------------------------------
# 四点五、H 层检查器（v1.9.0 新增 · 借自 lucasmarkes/hairline 的视觉工艺）
# --------------------------------------------------------------------------
# 来历：用户 2026-10-09 指定「把 hairline 这个 skill 复用进 ai-workflow 以提高审美」。
# 提炼口径 = **按 judgeability 分档**：能机器量的走 machine，只有眼睛能看的走 manual。
# 本节的 helper 由 extract_css 调用，故必须在**模块级**定义（运行时解析，与定义顺序无关）。
_EASING_KEYWORDS = ("ease-in-out", "step-start", "step-end", "ease-in", "ease-out", "ease", "linear")
_EASING_FN_RE = re.compile(r"\\b(cubic-bezier|steps|linear|spring)\\s*\\(", re.I)


def _easing_of(value: str):
    """从一条动效声明里取**缓动**标记；取不到返回 None。

    ① 先剔除 `linear-gradient(...)` —— 它是绘色函数，不是缓动（不剔除会把「用了渐变」误判成「用了线性缓动」）；
    ② 关键字按**最长优先**匹配，否则 `ease-in-out` 会被 `ease-in` 截断（匹配顺序即语义）；
    ③ `linear(...)` / `cubic-bezier(...)` / `steps(...)` 属函数形态，返回 `<名>(...)`。
    """
    v = re.sub(r"linear-gradient\\s*\\([^)]*\\)", " ", value, flags=re.I)
    for kw in _EASING_KEYWORDS:
        if re.search(r"(?<![\\w.-])" + re.escape(kw) + r"(?![\\w.])", v, re.I):
            return f"{kw}(...)" if re.search(re.escape(kw) + r"\\s*\\(", v, re.I) else kw
    m = _EASING_FN_RE.search(v)
    return f"{m.group(1)}(...)" if m else None


def _shadow_blur_px(value: str):
    """`text-shadow` 的模糊半径（px 口径）：取第 3 个长度；不足 3 个 ⇒ 0。

    相对单位（em/rem）**不折成像素**（同 G12 对 `em` 的处置）⇒ 返回 None，「判不了」不等于「没问题」。
    含 `var(...)` 的声明会被解析成「长度数不足」⇒ 记 0 —— 该限制写进判据集 note，不假装已覆盖。
    """
    cleaned = re.sub(r"#[0-9a-fA-F]{3,8}|rgba?\\([^)]*\\)|\\b(?:none|inset|var\\([^)]*\\))\\b", " ", value, flags=re.I)
    lens = [(float(n), u or "px") for n, u in re.findall(r"(-?[\\d.]+)(px|em|rem|pt)?", cleaned)]
    if len(lens) < 3:
        return 0.0
    n, u = lens[2]
    if u in ("em", "rem"):
        return None
    return n * {"px": 1.0, "pt": 1.3333}.get(u, 1.0)


def chk_easing_discipline(ctx, params):
    """H1（借自 hairline rule 08「两只钟」）：禁线性缓动。

    hairline 原文把「anything is linear」明确列为 rejected。本判据取它可机器化的那一半：
    扫全部 `transition` / `animation` 及其长写的 timing-function，出现**被禁缓动**即 FAIL。
    ⚠️ 诚实边界：本判据**不判**「该用弹簧却用了 tween」这类**手法归属**问题 ——
    机器判不出「这个目标是不是每帧都在动」（hairline 的弹簧参数 `k 100 · c 18 · m 1` 因此也未搬）。
    未提供 CSS ⇒ SKIP；有 CSS 但**零动效声明** ⇒ SKIP（无对象，不是通过）。
    """
    if not ctx.get("css"):
        return "SKIP", "未提供 CSS"
    decls = ctx["css"].get("motion_easings") or []
    if not decls:
        return "SKIP", "全文件零动效声明（本判据**无对象**，不是通过）"
    banned = {x.strip().lower() for x in str(params.get("banned") or "linear").split(",") if x.strip()}
    bad = [d for d in decls if d["easing"].lower() in banned]
    if bad:
        return "FAIL", (f"{len(bad)} 处使用被禁缓动 {sorted(banned)}（线性 = 匀速，"
                        f"与 hairline『两只钟』相悖）：" + "；".join(d["decl"] for d in bad[:4]))
    seen = sorted({d["easing"] for d in decls})
    return "PASS", f"{len(decls)} 处动效声明均未使用被禁缓动；出现的缓动：{seen[:6]}"


def chk_no_glow_effects(ctx, params):
    """H2（借自 hairline rule 04「描边即唯一高亮」）：禁**发光式**效果。

    只判发光，**不判**常规抬升阴影（elevation）—— 后者是功能性的，本判据不越权：
      ① `filter` 非 none 且含 `drop-shadow(` / `blur(` ⇒ FAIL；
      ② `text-shadow` 的模糊半径 ≥ `glow_blur_min_px`（默认 16）⇒ FAIL
         （小半径文字描边是「边缘清晰化」，放行）。
    未提供 CSS ⇒ SKIP；有 CSS 但**零阴影/滤镜声明** ⇒ SKIP（无对象，不是通过）。
    """
    if not ctx.get("css"):
        return "SKIP", "未提供 CSS"
    decls = ctx["css"].get("depth_decls") or []
    if not decls:
        return "SKIP", "全文件零 box-shadow / text-shadow / filter 声明（本判据**无对象**，不是通过）"
    thr = float(params.get("glow_blur_min_px") or 16)
    bad = []
    for d in decls:
        p, v = d["prop"], d["value"]
        if p == "filter" and re.search(r"\\b(?:drop-shadow|blur)\\s*\\(", v, re.I):
            bad.append(f"filter: {v[:40]}（滤镜式发光）")
        elif p == "text-shadow":
            blur = _shadow_blur_px(v)
            if blur is not None and blur >= thr:
                bad.append(f"text-shadow: {v[:40]}（模糊 {blur:g}px ≥ {thr:g}px）")
    if bad:
        return "FAIL", (f"{len(bad)} 处发光式效果（规则：描边即唯一高亮、颜色即信息）："
                        + "；".join(bad[:4]))
    return "PASS", (f"{len(decls)} 处阴影/滤镜声明均未构成发光"
                    f"（门槛：滤镜 drop-shadow·blur，或文字阴影模糊 ≥ {thr:g}px；"
                    f"常规抬升阴影**不在**本条射程）")


def chk_infinite_motion_guard(ctx, params):
    """H3（借自 hairline rule 07「loops sleep offscreen」）：无限循环动效须有减动效处置。

    取它可机器化的那一半：声明了 `infinite` 的动画，若**全文件没有任何
    `prefers-reduced-motion` 处置** ⇒ FAIL（hairline 原文要求 reduced motion 下一次性落位）。
    ⚠️ **不判「是否真的在屏外休眠」**（机器无从观测）—— 本条只是「减动效兜底缺失」的**代理信号**，
    边界写进判据集 note。未提供 CSS ⇒ SKIP；**零 infinite 声明** ⇒ SKIP（无对象，不是通过）。
    """
    if not ctx.get("css"):
        return "SKIP", "未提供 CSS"
    inf = ctx["css"].get("infinite_decls") or []
    if not inf:
        return "SKIP", "全文件零 infinite 动画（本判据**无对象**，不是通过）"
    if ctx["css"].get("has_reduced_motion"):
        return "PASS", f"{len(inf)} 处 infinite 动画已有 prefers-reduced-motion 处置兜底"
    return "FAIL", (f"{len(inf)} 处 infinite 循环动效，而全文件无 prefers-reduced-motion 处置："
                    + "；".join(inf[:4]))


# --------------------------------------------------------------------------
# 五、check 注册表 + 参数契约（v1.2.0 P2-2）
# --------------------------------------------------------------------------
CHECKS = {'''

cs = sub(cs, '''# --------------------------------------------------------------------------
# 五、check 注册表 + 参数契约（v1.2.0 P2-2）
# --------------------------------------------------------------------------
CHECKS = {''', NEW_CHECKS, "新增检查器块")

# 4) 注册表
cs = sub(cs, '''    "series_count_max": ("spec", chk_series_count_max),
}''', '''    "series_count_max": ("spec", chk_series_count_max),
    # v1.9.0：H 层（借自 hairline）
    "easing_discipline": ("machine", chk_easing_discipline),
    "no_glow_effects": ("machine", chk_no_glow_effects),
    "infinite_motion_guard": ("machine", chk_infinite_motion_guard),
}''', "CHECKS 注册")

cs = sub(cs, '''    "series_count_max": {"max": _N},
}''', '''    "series_count_max": {"max": _N},
    # v1.9.0：H 层。`banned` 用**逗号分隔的字符串**而非列表 —— 判据集解析器是小 YAML 子集，
    #   内联 map 里再嵌内联 list 不在其支持面内（实测：`{ banned: [linear] }` 会解析失败）。
    "easing_discipline": {"banned": _S},
    "no_glow_effects": {"glow_blur_min_px": _N},
}''', "PARAM_SPEC 注册")

# 5) 自检夹具（插在 fail-closed 段之前）
FIXTURES = '''    # ---- v1.9.0：H 层（借自 hairline）—— 每条配**成对阴性对照**（阳性必 FAIL、阴性必 PASS、
    #      结构性缺失必 SKIP）；无对照的判据不许上线（技能库卫生第 4 条）----
    print("=== H 层自检（H1 缓动纪律 / H2 禁发光式 / H3 无限循环须有减动效处置）===")

    # 先做 helper 的**单元断言** —— 夹具只比状态，比不出「匹配顺序」这类语义错误
    _ease_units = [
        ("ease-in-out 不得被 ease-in 截断（最长优先）", "ease-in-out", "ease-in-out"),
        ("linear 关键字", "linear", "linear"),
        ("linear-gradient 不是缓动 ⇒ 剔除后无缓动", "linear-gradient(#fff,#000)", None),
        ("cubic-bezier 属函数形态", "cubic-bezier(.32,.72,0,1)", "cubic-bezier(...)"),
        ("var() 取不到 ⇒ None（判不了 ≠ 没问题）", "var(--ease)", None),
    ]
    for _cn, _v, _exp in _ease_units:
        _got = _easing_of(_v)
        _ok = (_got == _exp)
        print(f"{'[ OK ]' if _ok else '[FAIL]'} _easing_of({_v!r}) = {_got!r}（期望 {_exp!r}）")
        if not _ok:
            rc = 1
    _blur_units = [
        ("0 0 20px #ff0 ⇒ 20", "0 0 20px #ff0", 20.0),
        ("0 1px 1px #000 ⇒ 1", "0 1px 1px #000", 1.0),
        ("无模糊（只有两个偏移）⇒ 0", "1px 1px #000", 0.0),
        ("em 无量纲 ⇒ None（不折成像素）", "0 0 1.5em #000", None),
    ]
    for _cn, _v, _exp in _blur_units:
        _got = _shadow_blur_px(_v)
        _ok = (_got == _exp)
        print(f"{'[ OK ]' if _ok else '[FAIL]'} _shadow_blur_px({_v!r}) = {_got!r}（期望 {_exp!r}）")
        if not _ok:
            rc = 1

    _h_cases = [
        (chk_easing_discipline, {"banned": "linear"},
         "transition 用 linear ⇒ FAIL", ".x{transition:opacity 220ms linear;}", "FAIL"),
        (chk_easing_discipline, {"banned": "linear"},
         "animation 简写用 linear ⇒ FAIL", ".x{animation:spin 1s infinite linear;}", "FAIL"),
        (chk_easing_discipline, {"banned": "linear"},
         "linear-gradient + 合规缓动 ⇒ PASS（不得误伤）",
         ".x{transition:opacity 220ms ease-out;background:linear-gradient(#fff,#000);}", "PASS"),
        (chk_easing_discipline, {"banned": "linear"},
         "ease-in-out ⇒ PASS", ".x{transition:all 300ms ease-in-out;}", "PASS"),
        (chk_easing_discipline, {"banned": "linear"},
         "零动效声明 ⇒ SKIP（无对象）", ".x{color:#111;}", "SKIP"),
        (chk_no_glow_effects, {"glow_blur_min_px": 16},
         "filter: drop-shadow ⇒ FAIL", ".x{filter:drop-shadow(0 0 8px #000);}", "FAIL"),
        (chk_no_glow_effects, {"glow_blur_min_px": 16},
         "filter: blur ⇒ FAIL", ".x{filter:blur(6px);}", "FAIL"),
        (chk_no_glow_effects, {"glow_blur_min_px": 16},
         "大模糊文字阴影 ⇒ FAIL", ".x{text-shadow:0 0 20px #ff0;}", "FAIL"),
        (chk_no_glow_effects, {"glow_blur_min_px": 16},
         "小半径文字描边 ⇒ PASS（边缘清晰化，不是发光）", ".x{text-shadow:0 1px 1px #000;}", "PASS"),
        (chk_no_glow_effects, {"glow_blur_min_px": 16},
         "常规抬升阴影 ⇒ PASS（**不在本条射程**）", ".x{box-shadow:0 1px 2px rgba(0,0,0,.1);}", "PASS"),
        (chk_no_glow_effects, {"glow_blur_min_px": 16},
         "filter: none ⇒ SKIP（无对象）", ".x{filter:none;}", "SKIP"),
        (chk_no_glow_effects, {"glow_blur_min_px": 16},
         "零阴影/滤镜声明 ⇒ SKIP（无对象）", ".x{color:#111;}", "SKIP"),
        (chk_infinite_motion_guard, {},
         "infinite + 无 reduced-motion ⇒ FAIL", ".x{animation:spin 1s infinite;}", "FAIL"),
        (chk_infinite_motion_guard, {},
         "animation-iteration-count:infinite + 无兜底 ⇒ FAIL",
         ".x{animation-name:spin;animation-iteration-count:infinite;}", "FAIL"),
        (chk_infinite_motion_guard, {},
         "infinite + 有 prefers-reduced-motion ⇒ PASS",
         ".x{animation:spin 1s infinite;}\\n@media (prefers-reduced-motion: reduce){.x{animation:none;}}",
         "PASS"),
        (chk_infinite_motion_guard, {},
         "零 infinite ⇒ SKIP（无对象）", ".x{animation:fade 1s ease-out;}", "SKIP"),
    ]
    for _fn, _pa, _cn, _css, _exp in _h_cases:
        _st, _det = _fn(_css_ctx(_css), _pa)
        _ok = (_st == _exp)
        print(f"{'[ OK ]' if _ok else '[FAIL]'} {_cn} — {_st}")
        if not _ok:
            print(f"        实际 detail：{_det}")
            rc = 1

    # ---- v1.2.1：fail-closed 护栏（某检查器内部异常 ⇒ 降级 FAIL，不得吞掉其它结果）----'''

cs = sub(cs, '''    # ---- v1.2.1：fail-closed 护栏（某检查器内部异常 ⇒ 降级 FAIL，不得吞掉其它结果）----''',
         FIXTURES, "自检夹具")

CHECKER.write_text(cs, encoding="utf-8")

# ============================ 二、判据集 ============================
rs = RUBRIC.read_text(encoding="utf-8")

rs = sub(rs, '''#   · Material Design 3（15 样式 / 11 档）与 Tailwind v4 默认 theme（13 档字号 / 288 色令牌）''',
         '''#   · Material Design 3（15 样式 / 11 档）与 Tailwind v4 默认 theme（13 档字号 / 288 色令牌）
# 外部依据（2026-10-09 追加，第 4 处）
#   · lucasmarkes/hairline@a2217852fed6d1a4f20bc7d43d4fad1a3de117b8
#     skills/hairline-create/rules.md（十条规则）+ look.md（十三项肉眼验收）
#     —— 用户 2026-10-09 指定「把 hairline 这个 skill 复用进 ai-workflow 以提高审美」；
#     提炼口径 = **按 judgeability 分档**（能机器量的走 machine，只有眼睛能看的走 manual）。
#     其来源 / 许可 / 安装形态 / 账本在 references/external-skills.md §1.4（**不在此重述**）。''',
         "表头外部依据")

rs = sub(rs, 'version: "1.7"', 'version: "1.8"', "rubric version")
rs = sub(rs, 'updated: "2026-10-07"', 'updated: "2026-10-09"', "rubric updated")

H_LAYER = '''

# ============ H 层（v1.8 新增 · 借自 lucasmarkes/hairline 的视觉工艺）============
# 来历：见文件头「外部依据（2026-10-09 追加，第 4 处）」。
#
# ⭐ 分档口径（**这是本层最重要的一条**）：hairline 的十条规则与十三项肉眼验收**绝大多数是判断层** ——
#   look.md 自己写着「The validator reads text. This is what only eyes can check.」。
#   故本层**不把它们一律硬配机器判据**（那会制造假绿），而是按 judgeability 分档：
#     能机器量出 → machine（H1/H2/H3，本轮实跑，各配成对阴性对照）；
#     只有眼睛能看 → manual（H4/H5，`check: null` ⇒ 产出 SKIP「人审点（机器不判定）」）。
#
# ⭐ 重叠已先排除（**不在本层重复造** —— 同一物理量不写两处；重叠会让既有阴性对照恒判假绿）：
#     rule 02「按距离错峰」        → 既有 **G16 rhythm_ladder**（已覆盖）
#     rule 06「构造不穿透」        → 既有 **R4 geometry_occlusion**（已覆盖）
#     rule 04 的「唯一强调色」半面 → 既有 **G2 accent_unique** / **G8 memory_point_count**
#   本层只补**未被覆盖**的部分：缓动纪律（H1）、发光式效果（H2）、无限循环的减动效兜底（H3）、
#   静止态构图（H4）、命中区稳定性（H5）。
#
# ⚠️ 未迁移（强绑定 isometric 线稿画面，对通用视觉产物**无判别力**，硬搬＝凭空发明契约）：
#   rule 03「不出框」（依赖 400×320 固定画框与指针极值位形）/ rule 07「屏外休眠」的**屏外半面** /
#   rule 09「圆角化 + 亮外暗内」（依赖 `prism` 双环实体这一表示法）/ rule 10「图内无文字」（依赖图元即几何）。

  - id: H1
    dimension: "动效节奏"
    name: "缓动纪律（禁线性）"
    judgeability: machine
    check: easing_discipline
    params: { banned: linear }
    source: "lucasmarkes/hairline@a2217852fed6d1a4f20bc7d43d4fad1a3de117b8:skills/hairline-create/rules.md#08『两只钟』—— 离散变化走长缓出 `(.32,.72,0,1)`、连续输入走弹簧，rejected 明列「anything is linear」"
    applies_to: [ui, ppt]
    note: "**只取可机器化的那一半**：扫 `transition`/`animation` 及其长写的 timing-function，出现被禁缓动即 FAIL（`linear-gradient()` 已先剔除，不误伤）。⚠️ **不判**「该用弹簧却用了缓动」—— 机器判不出「这个目标是不是每帧都在动」，故 hairline 的弹簧参数 `k 100 · c 18 · m 1` 与 700ms 长缓出**均未搬**（搬了就是凭空发明契约）。未提供 CSS ⇒ SKIP；有 CSS 但**零动效声明** ⇒ SKIP（无对象，不是通过）。要放宽/收紧用 `params.banned`（**逗号分隔字符串**，非列表）。"

  - id: H2
    dimension: "焦点"
    name: "禁发光式效果"
    judgeability: machine
    check: no_glow_effects
    params: { glow_blur_min_px: 16 }
    source: "lucasmarkes/hairline@a2217852fed6d1a4f20bc7d43d4fad1a3de117b8:skills/hairline-create/rules.md#04『描边即唯一高亮』—— No fills, glows or shadows；rejected 明列「sets any colour, fill, opacity trick, gradient, filter, shadow or stroke width of its own」"
    applies_to: [ui, ppt]
    note: "**只判发光、不判抬升**（elevation）—— 后者是功能性的，本判据不越权。两条：① `filter` 非 none 且含 `drop-shadow(`/`blur(` ⇒ FAIL；② `text-shadow` 模糊半径 ≥ `glow_blur_min_px`（默认 16）⇒ FAIL（小半径文字描边是「边缘清晰化」，放行）。⚠️ **诚实边界三条**：① **不判 box-shadow 的发光**（颜色/模糊的「发光」判定需要色相+透明度联合阈值，本轮不做，如实登记为未覆盖）；② 含 `var(...)` 的 text-shadow 解析成长度不足 ⇒ 记 0（**漏报**，不假装覆盖）；`em`/`rem` 模糊判 None 不计入。③ 门槛 16px 是**本仓默认档**（可 override），**不是** hairline 的产物数值 —— 它没有这条阈值，本条**只搬规则、不搬阈值**。未提供 CSS ⇒ SKIP；零阴影/滤镜声明 ⇒ SKIP（无对象）。"

  - id: H3
    dimension: "动效完备性"
    name: "无限循环须有减动效处置"
    judgeability: machine
    check: infinite_motion_guard
    source: "lucasmarkes/hairline@a2217852fed6d1a4f20bc7d43d4fad1a3de117b8:skills/hairline-create/rules.md#07『loops sleep offscreen』—— 只有环境动效可在无输入下运行，且仅在可见时；reduced motion 下须一次性落位"
    applies_to: [ui, ppt]
    note: "**代理信号，非等价判定**：本判据查的是「声明了 infinite 却全文件无 `prefers-reduced-motion` 处置」，而 rule 07 的原文要求是「循环须在屏外休眠」。⚠️ **屏外那一半机器无从观测**，故本条**只作兜底缺失的代理**，不得读成「已实现屏外休眠」。与 M1 的分工：M1 管「有没有写时长」，本条管「无限循环有没有减动效出口」。未提供 CSS ⇒ SKIP；**零 infinite 声明** ⇒ SKIP（无对象，不是通过）。"

  - id: H4
    dimension: "版式结构"
    name: "静止态是构图（非空/平/对称）"
    judgeability: manual
    check: null
    source: "lucasmarkes/hairline@a2217852fed6d1a4f20bc7d43d4fad1a3de117b8:skills/hairline-create/rules.md#05『rest is designed, never flat』+ look.md 第 2 项『Rest is a composition』"
    applies_to: [ui]
    note: "**人审点（机器不判定）**：hairline 的原话是「The still frame is the thumbnail, so it has to hold up alone」—— 留白/静态帧必须本身是构图，而不是「还没渲染」。人审动作：截一张静止态图，问「这一帧单独拿出去，能不能说清这是什么？」。⚠️ 不给它硬配机器判据（如「非对称度」「亮度熵」）：机器算不出「构图成不成立」，硬配＝制造假绿。与本仓既有手动项的分工：G10 管「贯穿元素复用」，本条管「静止帧自身是否成图」。"

  - id: H5
    dimension: "交互反馈"
    name: "命中区不随位形移动"
    judgeability: manual
    check: null
    source: "lucasmarkes/hairline@a2217852fed6d1a4f20bc7d43d4fad1a3de117b8:skills/hairline-create/rules.md#01『hit areas don't move』—— 命中判定须对**静止位形或目标位形**做，不得对屏上现态做，否则产生抖动环"
    applies_to: [ui]
    note: "**人审点（机器不判定）**：hairline 描述的失效形态是「指针按住一个会动的元素不动 → 图元抬起 → 焦点丢失 → 图元落回 → 焦点恢复 → 循环抖动」。人审动作：把指针停在一个被选中后会移动的元素上，等 2 秒，看是否稳定。⚠️ **不硬配机器判据**：这需要「随时间的位形序列」，CSS 静态取数与单帧渲染色都拿不到；用单帧几何去判会造出 100% 假绿。"
'''

rs = rs.rstrip("\n") + H_LAYER

RUBRIC.write_text(rs, encoding="utf-8")

# ============================ 三、回读断言 ============================
cb = CHECKER.read_text(encoding="utf-8")
rb = RUBRIC.read_text(encoding="utf-8")
checks = [
    ("checker VERSION 1.9.0", 'VERSION = "1.9.0"' in cb),
    ("chk_easing_discipline 在", "def chk_easing_discipline(ctx, params):" in cb),
    ("chk_no_glow_effects 在", "def chk_no_glow_effects(ctx, params):" in cb),
    ("chk_infinite_motion_guard 在", "def chk_infinite_motion_guard(ctx, params):" in cb),
    ("_easing_of 在", "def _easing_of(value: str):" in cb),
    ("_shadow_blur_px 在", "def _shadow_blur_px(value: str):" in cb),
    ("CHECKS 三个新名", all(f'"{n}": ("machine", chk_{n})' in cb for n in
                             ("easing_discipline", "no_glow_effects", "infinite_motion_guard"))),
    ("PARAM_SPEC 两条", '"easing_discipline": {"banned": _S},' in cb and '"no_glow_effects": {"glow_blur_min_px": _N},' in cb),
    ("extract_css 新键", all(f'"{k}"' in cb for k in
                            ("motion_easings", "depth_decls", "infinite_decls", "has_reduced_motion"))),
    ("自检夹具在", "_h_cases = [" in cb),
    ("rubric version 1.8", 'version: "1.8"' in rb),
    ("rubric H1-H5", all(f"  - id: H{i}" in rb for i in (1, 2, 3, 4, 5))),
    ("rubric 表头第 4 处依据", "外部依据（2026-10-09 追加，第 4 处）" in rb),
]
bad = [n for n, ok in checks if not ok]
if bad:
    raise SystemExit(f"[FAIL] 回读断言未过：{bad}")

print(f"[OK] 校验器与判据集改造完成：{len(checks)} 项回读断言通过")
print(f"[INFO] check_aesthetics.py {len(cs.encode())} B；aesthetic-rubric.yaml {len(rb.encode())} B")
