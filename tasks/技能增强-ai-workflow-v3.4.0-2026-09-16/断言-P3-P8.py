#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P3 / P8 的功能断言（ai-workflow v3.4.0）—— 性能类改动的**行为**判据，每条都配阴性对照。

为什么不是"看代码就知道改了"就够：
  P3 与 P8 都是**减少无谓调用次数**的改动，改动前后**输出完全一样**（这正是它们安全的原因），
  所以"输出逐字节一致"这条判据**对它们没有鉴别力** —— 改坏了也照样一致。
  能抓住它们的只有一种证据：**在受控输入下数调用次数**。

本脚本对同一输入分别驱动「新版」与「v3.3.0 旧版」，用 monkeypatch 计数器记录：
  · `_resolve_token` 被调用几次（P3 的目标：缓存命中时 = 0）
  · `_rl_throttle`  被调用几次、传的限额是多少（P8 的目标：只对真发的请求计数、限额按有无凭据分档）
旧版留在 `_backup-v3.3.0/scripts/http_fetch.v3.3.0.py`，是它让"阴性对照"成为可能 ——
没有旧版就只能声称"新代码看起来对"。

用法（从任意目录）：
    python tasks/技能增强-ai-workflow-v3.4.0-2026-09-16/断言-P3-P8.py
退出码：0 = 全部断言通过；1 = 有断言失败
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]
NEW_PY = SKILL / "scripts" / "http_fetch.py"
OLD_PY = SKILL / "_backup-v3.3.0" / "scripts" / "http_fetch.v3.3.0.py"
PROBE_SLUG = "psf/requests"
PROBE_URL = "https://api.github.com/repos/%s" % PROBE_SLUG

RESULTS: list[tuple[bool, str, str]] = []


def rec(ok: bool, title: str, note: str = "") -> None:
    RESULTS.append((bool(ok), title, note))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", title, ("  —— " + note) if note else ""))


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # 模块级只建目录常量，不联网
    return mod


class Countdown:
    """调用计数器：替换目标函数，记录每次实参（位置 + 关键字），并返回预设值。

    ⚠️ 必须**同时**记关键字实参：`fetch()` 的调用方全部用 `throttle=` 这种关键字形式传参，
      只记位置实参会让 `calls[0]` 成为空元组（首版就这么炸的）。计数器的判据本身也要
      能自证 —— 记不全等于测不到。
    """

    def __init__(self, ret=None):
        self.calls: list[dict] = []
        self.ret = ret

    def __call__(self, *a, **kw):
        self.calls.append({"args": a, "kwargs": kw})
        return self.ret

    @property
    def n(self) -> int:
        return len(self.calls)


def warm_cache(mod) -> bool:
    """确保探针 URL 有未过期缓存；没有就真取一次。返回是否就绪。"""
    if mod.cache_get(PROBE_URL, mod.CACHE_TTL) is not None:
        return True
    import urllib.request
    try:
        with urllib.request.urlopen(PROBE_URL, timeout=20) as r:
            data = r.read()
        mod.cache_put(PROBE_URL, data)
        return True
    except Exception as e:                                    # noqa: BLE001
        print("  [WARN] 预热缓存失败：%s" % e)
        return False


def run_cli(mod, argv: list[str]) -> tuple[int, str]:
    """在进程内跑真实 main()（不是绕开它调内部函数）：只有走真实入口才能证明
    "每一次 CLI 调用"都不再 eager 解析凭据。"""
    old_argv = sys.argv
    buf = io.StringIO()
    code = 0
    sys.argv = ["http_fetch.py"] + argv
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            mod.main()
    except SystemExit as e:
        code = int(e.code or 0)
    except Exception as e:                                    # noqa: BLE001
        code = 99
        buf.write("\n[EXC] %r" % e)
    finally:
        sys.argv = old_argv
    return code, buf.getvalue()


def main() -> int:
    print("=== P3 / P8 功能断言（新版 vs v3.3.0 旧版，同输入对照）===")
    if not OLD_PY.exists():
        print("[FAIL] 找不到旧版备份 %s —— 没有对照物，本脚本拒绝只测新版" % OLD_PY)
        return 1
    new = load(NEW_PY, "hf_new")
    old = load(OLD_PY, "hf_old")
    print("  新版：%s" % NEW_PY)
    print("  旧版：%s" % OLD_PY)
    print("")

    if not warm_cache(new):
        print("[FAIL] 缓存未能预热，断言无受控前提（网络不可用？）")
        return 1
    print("  前置：%s 已有有效缓存（TTL %ss）" % (PROBE_URL, new.CACHE_TTL))
    print("")

    # ------------------------------------------------------------------ #
    print("-- 断言 1／P3：缓存命中不得解析凭据（新版 main 真实入口）--")
    c = Countdown(ret="SHOULD_NOT_BE_USED")
    real_new = new._resolve_token
    new._resolve_token = c
    try:
        code, out = run_cli(new, ["--github-repo", PROBE_SLUG, "--json"])
    finally:
        new._resolve_token = real_new
    hit = "缓存命中" in out
    rec(code == 0 and hit, "新版 --github-repo 走缓存命中且退出码 0",
        "rc=%d，输出含『缓存命中』=%s" % (code, hit))
    rec(c.n == 0, "新版 _resolve_token 调用次数 == 0（P3 的直接判据）",
        "实际 %d 次" % c.n)

    # ------------------------------------------------------------------ #
    print("")
    print("-- 断言 2／P3 阴性对照：v3.3.0 旧版在同一输入下必然解析凭据 --")
    c_old = Countdown(ret=None)
    real_old = old._resolve_token
    old._resolve_token = c_old
    try:
        code_o, out_o = run_cli(old, ["--github-repo", PROBE_SLUG, "--json"])
    finally:
        old._resolve_token = real_old
    hit_o = "缓存命中" in out_o
    rec(code_o == 0 and hit_o, "旧版同样走缓存命中且退出码 0",
        "rc=%d，输出含『缓存命中』=%s" % (code_o, hit_o))
    rec(c_old.n >= 1, "旧版 _resolve_token 调用次数 >= 1（证明改前确实白付这笔）",
        "实际 %d 次  ← 这就是 P3 要消除的成本" % c_old.n)

    # ------------------------------------------------------------------ #
    print("")
    print("-- 断言 3／P8：桶限额按「有无凭据」分档（新版 github_repo_metrics）--")

    def limit_seen(mod, auth: bool) -> tuple | None:
        seen = Countdown(ret={"ok": True})
        fake_fetch = Countdown(ret=json.dumps({"full_name": PROBE_SLUG}).encode("utf-8"))
        keep_f, keep_h = mod.fetch, mod._auth_hint
        mod.fetch, mod._auth_hint = fake_fetch, (lambda: auth)
        try:
            mod.github_repo_metrics(PROBE_SLUG)
        finally:
            mod.fetch, mod._auth_hint = keep_f, keep_h
        return fake_fetch.calls[0]["kwargs"].get("throttle") if fake_fetch.calls else None

    t_anon = limit_seen(new, False)
    t_auth = limit_seen(new, True)
    rec(t_anon == ("gh_core", new.GH_CORE_LIMIT_ANON, 3600),
        "无凭据 → 匿名桶上限", "throttle=%r（期望 gh_core/%d/3600）" % (t_anon, new.GH_CORE_LIMIT_ANON))
    rec(t_auth == ("gh_core", new.GH_CORE_LIMIT_AUTH, 3600),
        "有凭据 → 认证桶上限（不再自限在匿名档）", "throttle=%r（期望 gh_core/%d/3600）" % (t_auth, new.GH_CORE_LIMIT_AUTH))
    rec(new.GH_CORE_LIMIT_AUTH > new.GH_CORE_LIMIT_ANON,
        "两档确有差异（不是把常量改了个名）",
        "%d vs %d" % (new.GH_CORE_LIMIT_AUTH, new.GH_CORE_LIMIT_ANON))

    # ------------------------------------------------------------------ #
    print("")
    print("-- 断言 4／P8 阴性对照：v3.3.0 旧版与凭据无关，恒按 60/h 自限 --")
    old_rl = Countdown()
    real_rl = old._rl_throttle
    old._rl_throttle = old_rl
    try:
        old.github_repo_metrics(PROBE_SLUG)          # 缓存已热，但旧版仍会先节流
    finally:
        old._rl_throttle = real_rl
    rec(old_rl.n >= 1 and old_rl.calls[0]["args"][:2] == ("gh_core", 60),
        "旧版无条件按 gh_core/60/h 计数（含缓存命中）",
        "调用 %d 次，首次实参=%r" % (old_rl.n, old_rl.calls[0]["args"] if old_rl.calls else None))

    # ------------------------------------------------------------------ #
    print("")
    print("-- 断言 5／P8：新版 fetch 的节流只在缓存未命中之后（缓存命中 = 0 次）--")
    new_rl = Countdown()
    real_rl2 = new._rl_throttle
    new._rl_throttle = new_rl
    try:
        data = new.fetch(PROBE_URL, throttle=("gh_core", new.GH_CORE_LIMIT_ANON, 3600))
    finally:
        new._rl_throttle = real_rl2
    rec(data is not None and new_rl.n == 0,
        "新版缓存命中的 fetch 不进入限流桶", "返回 %s 字节，_rl_throttle 调用 %d 次"
        % (len(data) if data else 0, new_rl.n))

    # ------------------------------------------------------------------ #
    print("")
    print("-- 断言 6／P8：`--github-code-search --dry-run` 不发请求也不解析凭据 --")
    c2 = Countdown(ret="SHOULD_NOT_BE_USED")
    keep = new._resolve_token
    new._resolve_token = c2
    try:
        code_d, out_d = run_cli(new, ["--github-code-search", "add_dependency repo:fastapi/fastapi", "--dry-run"])
    finally:
        new._resolve_token = keep
    rec(code_d == 0 and "[DRY-RUN]" in out_d and c2.n == 0,
        "dry-run 只打印 URL 不经凭据", "rc=%d，_resolve_token %d 次" % (code_d, c2.n))

    # ------------------------------------------------------------------ #
    n_fail = sum(1 for ok, _, _ in RESULTS if not ok)
    print("")
    print("=== 结果：%d/%d 通过，FAIL=%d ===" % (len(RESULTS) - n_fail, len(RESULTS), n_fail))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
