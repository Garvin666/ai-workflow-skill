"""s5b: 修 s5 幂等守卫缺陷造成的「插入型编辑被重复应用」，并用「HEAD + 编辑表」全量重推做对照。

背景（如实留痕）：s5 首版幂等判据写成 `s.count(old)==0 and new in s`。对**插入型**编辑
（new 以 old 为前缀）该条件永不成立 ⇒ 第二次运行时把同一段**又插了一遍**，
`references/diagram-mode.md` 与 `references/ppt-mode.md` 各重复一次（证据留存
`tmp/hairline-20261009/s5-dup-evidence/`）。

⭐ 本脚本不只做「去掉一份」的字符串手术 —— 它同时做**确定性重推**：
   以 `git show HEAD:<file>` 为前态，用修好判据的**同一张编辑表**重新推一遍，
   再断言「修复后的文件 == 重推结果」逐字节相等。
   这一步同时证明三件事：① 修复是精确的（不多不少）② HEAD 与 s5 前的工作树无其他分歧
   ③ 编辑表本身完备且可复现。
"""
import importlib.util
import pathlib
import subprocess
import sys

# 原为硬编码本机绝对路径（出站清单第 4 项）⇒ 改由 __file__ 推导
SKILL = pathlib.Path(__file__).resolve().parents[2]
TASK = SKILL / "tasks" / "复用-hairline视觉工艺-2026-10-09"

spec = importlib.util.spec_from_file_location("s5_docs", TASK / "s5_docs.py")
s5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s5)          # 模块级只定义、不执行 main()

S5_FILES = ["SKILL.md", "README.md", "assets/plan-template.yaml", "references/ops.md",
            "scripts/checks_core.py", "references/diagram-mode.md", "references/ppt-mode.md",
            "_archive/changelog.md"]


def head_of(rel: str) -> str:
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=SKILL,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, f"git show HEAD:{rel} 失败：{r.stderr}"
    return r.stdout.replace("\r\n", "\n") if "\r\n" in r.stdout else r.stdout


def apply_table(src: str, items):
    """用**修好的**幂等判据把编辑表作用到 src 上（纯函数，可复算）。"""
    s = src
    for t, old, new in items:
        if new in s:
            continue
        assert s.count(old) == 1, f"[{t}] 锚点出现 {s.count(old)} 次（期望 1）"
        s = s.replace(old, new)
    return s


def main():
    by_file = {}
    for f, t, old, new in s5.EDITS:
        by_file.setdefault(f, []).append((t, old, new))

    # ── 第一步：修「重复插入」──
    # ⚠️ 检测口径：插入型编辑重复的是 **chunk（新插入的那一段）**，不是 new（= old+chunk）。
    #    首版按 `s.count(new) > 1` 检测 ⇒ 恒为 1（chunk 的第二份前面没有 old）⇒ **漏检、误报「未发现」**。
    fixed_any = []
    for f, items in by_file.items():
        p = SKILL / f
        s = p.read_text(encoding="utf-8")
        before = s
        for t, old, new in items:
            if not new.startswith(old):
                continue                      # 只处理插入型
            chunk = new[len(old):]
            while s.count(chunk) > 1:
                assert (chunk + chunk) in s, f"[{f} · {t}] 重复形态不是 chunk+chunk，拒绝硬改"
                s = s.replace(chunk + chunk, chunk, 1)
            assert s.count(chunk) == 1, f"[{f} · {t}] 修复后 chunk 仍出现 {s.count(chunk)} 次"
        if s != before:
            p.write_text(s, encoding="utf-8")
            back = p.read_text(encoding="utf-8")
            assert back == s, f"[{f}] 修复后回读不一致"
            fixed_any.append(f)
            print(f"[FIX] {f} — 去掉了重复插入的片段"
                  + "".join(f"（{t}）" for t, old, new in items
                            if new.startswith(old) and new[len(old):] in before))

    if not fixed_any:
        print("[ OK ] 未发现重复插入（全部已是单份）")

    # ── 第二步：每个文件「目标串恰 1 份」断言（插入型额外查 chunk）──
    for f, items in by_file.items():
        s = (SKILL / f).read_text(encoding="utf-8")
        for t, old, new in items:
            assert s.count(new) == 1, f"[{f} · {t}] 目标串出现 {s.count(new)} 次（期望恰 1）"
            if new.startswith(old):
                chunk = new[len(old):]
                assert s.count(chunk) == 1, f"[{f} · {t}] 插入片段出现 {s.count(chunk)} 次（期望恰 1）"
    print(f"[ OK ] 幂等性：{sum(len(v) for v in by_file.values())} 处编辑的目标串**各出现恰 1 次**"
          f"（插入型另查 chunk）")

    # ── 第三步：确定性重推对照（HEAD + 编辑表 == 现状）──
    bad = []
    for f in S5_FILES:
        head = head_of(f)
        if f == "_archive/changelog.md":
            # changelog 是「追加」而非替换，按追加语义单独重推
            expected = head
            if f"v{s5.NEWVER}（{s5.TODAY}）" not in head:
                assert head.count(s5.CHANGELOG_ANCHOR) == 1
                expected = head.replace(s5.CHANGELOG_ANCHOR,
                                        s5.CHANGELOG_ENTRY + s5.CHANGELOG_ANCHOR, 1)
        else:
            expected = apply_table(head, by_file[f])
        actual = (SKILL / f).read_text(encoding="utf-8")
        same = actual == expected
        print(f"[{' OK ' if same else 'FAIL'}] 重推对照 {f} — "
              f"HEAD {len(head)} B ＋ 编辑表 ⇒ {len(expected)} B；现状 {len(actual)} B")
        if not same:
            bad.append(f)
            import difflib
            d = list(difflib.unified_diff(expected.splitlines(), actual.splitlines(),
                                          "expected(HEAD+table)", "actual", lineterm="", n=1))
            for ln in d[:24]:
                print("      " + ln[:200])

    if bad:
        print(f"=== 重推不一致 {len(bad)} 个：{bad} ===")
        return 1
    print("=== 重推对照：8/8 逐字节相等 —— 修复精确、HEAD 无其他分歧、编辑表可复现 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
