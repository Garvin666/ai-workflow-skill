# -*- coding: utf-8 -*-
"""可见性判据的阴性对照（4 例）。

证明：① 双关必须 WARN  ② 只关一处不得报  ③ 跨家不同必须 WARN  ④ 跨家相同必须 OK。
做法：临时目录造 2 个假数据家 + 3 个假技能，直接调 `checks._check_visibility`。
"""
import json, shutil, sys, tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import checks_core as core          # noqa: E402
import checks                       # noqa: E402

FM_OFF = "---\nname: {n}\ndescription: 夹具技能 {n}\ndisable-model-invocation: true\n---\n正文\n"
FM_ON = "---\nname: {n}\ndescription: 夹具技能 {n}\n---\n正文\n"


def build(root: Path, fm_off=(), homes=None):
    sk = root / "skills"
    for n in ("s1", "s2", "s3"):
        d = sk / n
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text((FM_OFF if n in fm_off else FM_ON).format(n=n), encoding="utf-8")
    out = []
    for name, ov in (homes or {}).items():
        h = root / name / ".workbuddy"
        h.mkdir(parents=True)
        (h / "settings.json").write_text(json.dumps({"skillOverrides": ov}), encoding="utf-8")
        out.append(h)
    return sk, out


def run(tag, sk, homes, want):
    core.results.clear()
    checks._check_visibility(sk, homes)
    got = {item: st for st, item, _ in core.results}
    k1 = "可见性：单家双关（复位须清两处）"
    k2 = "可见性：跨家一致"
    st1, st2 = got.get(k1), got.get(k2)
    okk = (st1 == want[0]) and (st2 == want[1])
    print(f"[{'PASS' if okk else 'MISS'}] {tag}: 双关={st1} 跨家={st2}（期望 {want[0]}/{want[1]}）")
    for s, i, n in core.results:
        print(f"        {s} {i}" + (f" — {n[:110]}" if n else ""))
    return okk


fails = 0
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)

    # 例1：s1 两处都关（settings + frontmatter）⇒ 双关必须 WARN。
    # ⚠️ 跨家项**期望 OK**：frontmatter 是共享的，带 flag 的技能在所有家都不可见，
    #    所以"双关"与"仅覆盖"的**可见集完全相同** —— 双关的影响面是**复位成本**，不是可见性差异。
    #    （首版把期望写成 WARN，是夹具期望错、不是判据错 —— 已按实测修正。）
    sk, homes = build(root / "c1", fm_off=("s1",),
                      homes={"A": {"s1": "user-invocable-only"}, "B": {}})
    fails += not run("例1 双关", sk, homes, ("WARN", "OK"))

    # 例2：只关一处（settings 关，frontmatter 不关）⇒ 不得判双关；两家同配置 ⇒ 跨家一致
    sk, homes = build(root / "c2", fm_off=(),
                      homes={"A": {"s1": "user-invocable-only"}, "B": {"s1": "user-invocable-only"}})
    fails += not run("例2 仅一处（全绿对照）", sk, homes, ("OK", "OK"))

    # 例3：跨家不同，但没有任何双关 ⇒ 双关 OK / 跨家 WARN
    sk, homes = build(root / "c3", fm_off=(),
                      homes={"A": {"s1": "user-invocable-only"}, "B": {"s2": "user-invocable-only"}})
    fails += not run("例3 仅跨家分歧", sk, homes, ("OK", "WARN"))

    # 例4：两家完全一致且无关闭 ⇒ 双 OK
    sk, homes = build(root / "c4", fm_off=(),
                      homes={"A": {}, "B": {}})
    fails += not run("例4 全一致（全绿对照）", sk, homes, ("OK", "OK"))

print(f"\n=== 阴性对照 {4 - fails}/4 通过 ===")
raise SystemExit(1 if fails else 0)
