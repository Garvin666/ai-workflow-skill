"""s6a: 还原各文件**原有行尾**（把本次写盘引入的 CRLF 转回原状）。

病根：`Path.write_text(s, encoding="utf-8")` 的 `newline=None` 会按 `os.linesep` 转换
⇒ 在 Windows 上把内存里的 `\\n` 写成 `\\r\\n`。本次经此写盘的文件**全部被改成 CRLF**，
而本仓 `.gitattributes` 是 `* text=auto eol=lf`（声明 LF），且工作树多数文件本就是 LF。

判据（**不猜**）：以 s1 基线快照的**同一文件副本**为准 —— 它保存了 s1 时刻工作树的真实字节，
故其行尾即「改动前的原状」。基线里没有的文件（ops.md / plan-template.yaml）按 `.gitattributes` 取 LF，
并把该假设**显式打印**出来。

验收（三条，缺一不可）：
  ① **内容零变化**：LF 归一后 sha256 与还原前逐文件相等；
  ② **git diff 逐字节不变**：`--numstat` 的 (增,删) 对还原前一致；
  ③ 行尾与目标一致（并按目标写回后回读复核）。
"""
import hashlib
import pathlib
import subprocess
import sys

# 原为硬编码本机绝对路径（出站清单第 4 项）⇒ 改由 __file__ 推导
SKILL = pathlib.Path(__file__).resolve().parents[2]
BASE = SKILL / "tmp" / "hairline-20261009" / "baseline"

# 本次经 Python 写盘改过的全部文件（s2/s3/s5 合计）
WRITTEN = [
    "SKILL.md", "README.md", "references/external-skills.md",
    "references/aesthetic-rubric.yaml", "references/diagram-mode.md",
    "references/ppt-mode.md", "scripts/check_aesthetics.py",
    "scripts/checks_core.py", "_archive/changelog.md",
]
# 基线里没有、本次也写过：按 .gitattributes 取 LF（假设显式登记）
ASSUMED_LF = ["references/ops.md", "assets/plan-template.yaml"]

# 基线里这些文件本来就是 CRLF ⇒ 还原成 CRLF（保持改动前的原状）
BASELINE_CRLF = {"README.md", "scripts/checks_core.py", "_archive/changelog.md"}


def lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def numstat(paths) -> dict:
    r = subprocess.run(["git", "diff", "--numstat", "--", *paths], cwd=SKILL,
                       capture_output=True, text=True, encoding="utf-8")
    out = {}
    for ln in r.stdout.splitlines():
        parts = ln.split("\t")
        if len(parts) == 3:
            out[parts[2]] = (parts[0], parts[1])
    return out


def main():
    targets = WRITTEN + ASSUMED_LF
    before = {f: (SKILL / f).read_bytes() for f in targets}
    before_ns = numstat(targets)

    changed = []
    for f in targets:
        want_crlf = f in BASELINE_CRLF
        src = before[f]
        # 目标字节：LF 版内容 + 按需换回 CRLF
        base = lf(src)
        if want_crlf:
            out = base.replace(b"\n", b"\r\n")
        else:
            out = base
        eol_now = "CRLF" if src.count(b"\r\n") and not src.count(b"\n") - src.count(b"\r\n") else "LF"
        eol_want = "CRLF" if want_crlf else "LF"
        # ① 内容零变化
        assert sha(lf(out)) == sha(lf(src)), f"[{f}] 行尾还原改变了内容 —— 拒绝写盘"
        if out == src:
            print(f"[ -- ] {f:36} 已是 {eol_now}（目标 {eol_want}），跳过")
            continue
        (SKILL / f).write_bytes(out)
        back = (SKILL / f).read_bytes()
        assert back == out, f"[{f}] 回读与写盘不一致"
        assert sha(lf(back)) == sha(lf(src)), f"[{f}] 回读后内容变化"
        changed.append(f)
        src_kind = "基线副本 CRLF" if want_crlf else (
            "基线副本 LF" if (BASE / f).exists() else "基线无此文件 ⇒ 按 .gitattributes 取 LF（假设）")
        print(f"[ OK ] {f:36} {eol_now} → {eol_want}（依据：{src_kind}）")

    # ② git diff 逐字节不变
    after_ns = numstat(targets)
    diff_moved = {f: (before_ns.get(f), after_ns.get(f))
                  for f in targets if before_ns.get(f) != after_ns.get(f)}
    assert not diff_moved, f"行尾还原改变了 git diff：{diff_moved}"
    print(f"[ OK ] git diff --numstat 逐文件不变（{len(after_ns)} 个文件）—— 改动面仍只有内容行")

    # ③ 汇总
    left = [f for f in targets
            if ("CRLF" if (SKILL / f).read_bytes().count(b"\r\n") else "LF")
            != ("CRLF" if f in BASELINE_CRLF else "LF")]
    assert not left, f"仍与目标行尾不符：{left}"
    print(f"[ OK ] 行尾还原完成：改了 {len(changed)} 个；全部与目标一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
