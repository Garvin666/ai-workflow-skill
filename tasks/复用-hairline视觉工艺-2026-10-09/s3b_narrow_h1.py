"""s3b: 按 s4 影响面实测结果**收窄 H1 的默认射程**（transition → 不含 animation）。

实测证据（tmp/hairline-20261009/impact-synthetic.txt 第 01 行）：常见合规产物里的
`.spinner{animation:spin 1.2s linear infinite;}` 被 H1 判 FAIL —— 但**旋转/进度类动效用线性是对的**
（匀速旋转的物理语义就是线性的）。hairline 之所以禁线性，是因为它自己的动效都是「离散选择」与
「指针跟随」；把这条规则原样套到通用产物上就是**作用域错配**（本仓已记过 G1/G6/G7/G11 一族的同型病）。
修法＝给 H1 加 `scope` 参数（默认 `transition`），`animation` 族默认放行、要收紧可显式 `scope: all`。
"""
import pathlib

CHECKER = pathlib.Path("scripts/check_aesthetics.py")
RUBRIC = pathlib.Path("references/aesthetic-rubric.yaml")
cs = CHECKER.read_text(encoding="utf-8")
rs = RUBRIC.read_text(encoding="utf-8")


def sub(text, old, new, label, count=1):
    n = text.count(old)
    if n != count:
        raise SystemExit(f"[FAIL] {label}: 期望命中 {count} 次，实际 {n} 次\n---\n{old[:200]}\n---")
    return text.replace(old, new)


# 1) 取数：给每条缓动记录带上**族**（transition / animation）
cs = sub(cs, '''        if prop in _EASE_PROPS:
            _e = _easing_of(val)
            if _e:
                motion_easings.append({"decl": f"{prop}: {val[:48]}", "easing": _e})''',
         '''        if prop in _EASE_PROPS:
            _e = _easing_of(val)
            if _e:
                motion_easings.append({
                    "decl": f"{prop}: {val[:48]}",
                    "easing": _e,
                    # v1.9.0：带上**族** —— H1 默认只判 transition 族（见 chk_easing_discipline）
                    "scope": "animation" if prop.startswith("animation") else "transition",
                })''', "缓动族标记")

# 2) 检查器：加 scope 过滤 + 更新 docstring/边界
cs = sub(cs, '''    hairline 原文把「anything is linear」明确列为 rejected。本判据取它可机器化的那一半：
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
    return "PASS", f"{len(decls)} 处动效声明均未使用被禁缓动；出现的缓动：{seen[:6]}"''',
         '''    hairline 原文把「anything is linear」明确列为 rejected。本判据取它可机器化的那一半：
    扫动效声明，出现**被禁缓动**即 FAIL。
    ⚠️ **`scope` 默认 `transition`** —— 只判 transition 族（状态切换：hover / 展开 / 淡入淡出）。
    **`animation` 族默认放行**，理由是**作用域错配**：旋转 / 进度 / 跑马灯用线性**是对的**
    （匀速旋转的物理语义就是线性的）。实测证据：合成矩阵的「常见合规产物」样本里
    `.spinner{animation:spin 1.2s linear infinite;}` 被首版无 scope 的判据判 FAIL —— 那是**判据在造信号**。
    hairline 禁线性，是因为它自己的动效都是「离散选择」与「指针跟随」；原样套到通用产物上就出错。
    要收紧成「连 animation 也禁」⇒ `params: { scope: all }`（显式，不默认）。
    ⚠️ 另一条诚实边界：本判据**不判**「该用弹簧却用了 tween」这类**手法归属**问题 ——
    机器判不出「这个目标是不是每帧都在动」（hairline 的弹簧参数 `k 100 · c 18 · m 1` 因此也未搬）。
    未提供 CSS ⇒ SKIP；**射程内零动效声明** ⇒ SKIP（无对象，不是通过）。
    """
    if not ctx.get("css"):
        return "SKIP", "未提供 CSS"
    scope = str(params.get("scope") or "transition").strip().lower()
    all_decls = ctx["css"].get("motion_easings") or []
    decls = [d for d in all_decls if scope == "all" or d.get("scope") == scope]
    if not decls:
        return "SKIP", (f"射程（{scope}）内零动效声明（本判据**无对象**，不是通过）"
                        f"；全文件共 {len(all_decls)} 处动效声明在射程外")
    banned = {x.strip().lower() for x in str(params.get("banned") or "linear").split(",") if x.strip()}
    bad = [d for d in decls if d["easing"].lower() in banned]
    if bad:
        return "FAIL", (f"{len(bad)} 处（射程 {scope}）使用被禁缓动 {sorted(banned)}"
                        f"（线性 = 匀速，与 hairline『两只钟』相悖）：" + "；".join(d["decl"] for d in bad[:4]))
    seen = sorted({d["easing"] for d in decls})
    return "PASS", f"{len(decls)} 处（射程 {scope}）动效声明均未使用被禁缓动；出现的缓动：{seen[:6]}"''',
         "H1 收窄射程")

# 3) PARAM_SPEC 加 scope
cs = sub(cs, '''    "easing_discipline": {"banned": _S},''',
         '''    "easing_discipline": {"banned": _S, "scope": ("transition", "all")},''',
         "PARAM_SPEC scope")

# 4) 自检：改 animation 那条的期望，并补 scope=all 的两条
cs = sub(cs, '''        (chk_easing_discipline, {"banned": "linear"},
         "animation 简写用 linear ⇒ FAIL", ".x{animation:spin 1s infinite linear;}", "FAIL"),''',
         '''        (chk_easing_discipline, {"banned": "linear"},
         "animation 用 linear ⇒ **SKIP**（旋转类线性是对的，默认射程只含 transition）",
         ".x{animation:spin 1s infinite linear;}", "SKIP"),
        (chk_easing_discipline, {"banned": "linear", "scope": "all"},
         "同上但显式 scope=all ⇒ FAIL（收紧是显式的，不默认）",
         ".x{animation:spin 1s infinite linear;}", "FAIL"),
        (chk_easing_discipline, {"banned": "linear", "scope": "all"},
         "scope=all 下 compliance 样本仍 PASS",
         ".x{transition:opacity 220ms ease-out;animation:spin 1s ease-in infinite;}", "PASS"),''',
         "自检夹具改判")

CHECKER.write_text(cs, encoding="utf-8")

# 5) 判据集：params 加 scope + note 登记边界
rs = sub(rs, '''    params: { banned: linear }
    source: "lucasmarkes/hairline@a2217852fed6d1a4f20bc7d43d4fad1a3de117b8:skills/hairline-create/rules.md#08''',
         '''    params: { banned: linear, scope: transition }
    source: "lucasmarkes/hairline@a2217852fed6d1a4f20bc7d43d4fad1a3de117b8:skills/hairline-create/rules.md#08''',
         "H1 params scope")

rs = sub(rs, '''note: "**只取可机器化的那一半**：扫 `transition`/`animation` 及其长写的 timing-function，出现被禁缓动即 FAIL（`linear-gradient()` 已先剔除，不误伤）。''',
         '''note: "**只取可机器化的那一半**：扫动效声明，出现被禁缓动即 FAIL（`linear-gradient()` 已先剔除，不误伤）。⚠️ **`scope` 默认 `transition`**（只判状态切换族）；**`animation` 族默认放行** —— 旋转 / 进度 / 跑马灯用线性是对的，实测「常见合规产物」样本里 `.spinner{animation:spin 1.2s linear infinite;}` 被首版无 scope 的判据判 FAIL，即**作用域错配**（同 G1/G6/G7/G11 一族）。要连 animation 一起禁 ⇒ 显式 `params: { scope: all }`。''',
         "H1 note 边界")

RUBRIC.write_text(rs, encoding="utf-8")

# ---- 回读断言 ----
cb, rb = CHECKER.read_text(encoding="utf-8"), RUBRIC.read_text(encoding="utf-8")
checks = [
    ("族标记在", '"scope": "animation" if prop.startswith("animation") else "transition",' in cb),
    ("检查器 scope 过滤在", 'decls = [d for d in all_decls if scope == "all" or d.get("scope") == scope]' in cb),
    ("PARAM_SPEC scope 在", '"easing_discipline": {"banned": _S, "scope": ("transition", "all")},' in cb),
    ("自检新增 scope=all 用例", '同一但显式 scope=all' in cb or '同上但显式 scope=all' in cb),
    ("rubric scope 参数在", 'params: { banned: linear, scope: transition }' in rb),
    ("rubric note 登记边界", '作用域错配**（同 G1/G6/G7/G11 一族）' in rb),
]
bad = [n for n, ok in checks if not ok]
if bad:
    raise SystemExit(f"[FAIL] 回读断言未过：{bad}")
print(f"[OK] H1 射程收窄完成：{len(checks)} 项回读断言通过")
