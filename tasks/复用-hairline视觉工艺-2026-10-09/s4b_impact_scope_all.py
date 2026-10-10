"""s4b: H1 射程参数的**对照证据** —— 证明「默认 transition」与「显式 scope: all」确有差别。

为什么必须做：s3b 给 H1 加了 scope 参数并改默认值。改完只说「收窄了」不算证据 ——
必须**同一语料、只改这一个参数**跑出两份可 diff 的输出，才能断定差别来自该参数，
而不是来自语料/其他判据的变化。

做法：取判据集原件，只把 H1 的 `params: { banned: linear, scope: transition }`
改写为 `scope: all`，落到 tmp 临时副本；两份 rubric 分别跑同一批合成语料。
⚠️ 判据集原件**零改动**（这里只读不写）。
"""
import pathlib
import subprocess
import sys

# 原为硬编码本机绝对路径（出站清单第 4 项）⇒ 改由 __file__ 推导
SKILL = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
TMP = SKILL / "tmp" / "hairline-20261009"
RUBRIC = SKILL / "references" / "aesthetic-rubric.yaml"
OLD = "params: { banned: linear, scope: transition }"
NEW = "params: { banned: linear, scope: all }"


def run(rubric: pathlib.Path, tag: str):
    out = TMP / f"impact-synthetic-scope-{tag}.txt"
    cmd = [PY, str(SKILL / "scripts" / "check_aesthetics.py"),
           "--rubric", str(rubric),
           "--batch", str(TMP / "corpus" / "*.css"), "--product", "ui"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out.write_text(r.stdout + r.stderr, encoding="utf-8")
    h1 = [ln for ln in r.stdout.splitlines() if "H1" in ln and "缓动" in ln]
    print(f"[{tag}] rc={r.returncode} 落 {out.name} :: {h1[0].strip() if h1 else 'N/A'}")
    return r.returncode


def main():
    src = RUBRIC.read_text(encoding="utf-8")
    n = src.count(OLD)
    assert n == 1, f"锚点不唯一：OLD 出现 {n} 次（期望 1）——改写前须先确认锚点"
    tmp_rubric = TMP / "aesthetic-rubric-scope-all.yaml"
    tmp_rubric.write_text(src.replace(OLD, NEW), encoding="utf-8")

    # 语料必须先存在（s4_impact.py 生成）；不存在则这里补生成
    if not (TMP / "corpus" / "01-常规产物-合规.css").exists():
        subprocess.run([PY, str(SKILL / "tasks" / "复用-hairline视觉工艺-2026-10-09" / "s4_impact.py")],
                       capture_output=True, text=True)

    run(RUBRIC, "transition")          # 默认射程（当前生效口径）
    run(tmp_rubric, "all")             # 显式收紧

    # 自证：原件未被改动
    after = RUBRIC.read_text(encoding="utf-8")
    assert after == src, "判据集原件在本次对照中被改动 —— 违反「只读」约定"
    print("[OK] 判据集原件零改动；两份输出可 diff")
    return 0


if __name__ == "__main__":
    sys.exit(main())
