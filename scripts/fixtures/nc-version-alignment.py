# -*- coding: utf-8 -*-
"""[自研工具] 版本三处对齐判据的阴性对照（5 例）。

证明：`checks._check_version_alignment` 不是空转 ——
三处一致时判 OK；任一处漂移、或任一处声明缺失时判 FAIL。

做法：临时目录造假技能目录（`SKILL.md` ＋ `README.md`），直接调judge函数，
不经过 CLI、不依赖真实技能目录，因而不受本仓当前版本号影响。

用法：python scripts/fixtures/nc-version-alignment.py  （rc=0 全部符合期望）
"""
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import checks_core as core   # noqa: E402
import checks                # noqa: E402

LABEL = "版本三处对齐"
FM_TMPL = "---\nname: fixture\ndescription: 夹具技能\nversion: {v}\n---\n"
RD_TMPL = "说明（当前版本 **v{v}**）。\n"


def make(root: Path, ver_fm="1.2.3", ver_h1="1.2.3", ver_rd="1.2.3",
         with_fm=True, with_h1=True, with_rd=True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    body = FM_TMPL.format(v=ver_fm) if with_fm else "---\nname: fixture\n---\n"
    if with_h1:
        body += "# 夹具 v%s\n" % ver_h1
    body += "正文\n"
    (root / "SKILL.md").write_text(body, encoding="utf-8")
    if with_rd:
        (root / "README.md").write_text(RD_TMPL.format(v=ver_rd), encoding="utf-8")
    return root


def run(tag: str, root: Path, want: str) -> bool:
    core.results.clear()
    checks._check_version_alignment(root)
    got = [st for st, item, _ in core.results if item == LABEL]
    st = got[0] if got else "(无输出)"
    hit = (st == want)
    print("[%s] %s：实际=%s 期望=%s" % ("PASS" if hit else "MISS", tag, st, want))
    for s, i, n in core.results:
        print("        %s %s%s" % (s, i, (" — " + n[:110]) if n else ""))
    return hit


def main() -> int:
    missed = 0
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        # 例1 三处一致 ⇒ OK（正控；没有它，后面 4 例的 FAIL 可能只是判据恒红）
        missed += not run("例1 三处一致", make(base / "c1"), "OK")
        # 例2 README 落后 ⇒ FAIL（复现 v4.44.0 开工时的真实故障：README 停 v4.35.0）
        missed += not run("例2 README 落后", make(base / "c2", ver_rd="1.2.2"), "FAIL")
        # 例3 H1 版本号缺失 ⇒ FAIL（缺失 = 无法核对，不得静默放行）
        missed += not run("例3 H1 缺失", make(base / "c3", with_h1=False), "FAIL")
        # 例4 frontmatter 版本缺失 ⇒ FAIL
        missed += not run("例4 frontmatter 缺失", make(base / "c4", with_fm=False), "FAIL")
        # 例5 README 文件缺失 ⇒ FAIL
        missed += not run("例5 README 缺失", make(base / "c5", with_rd=False), "FAIL")

    print("\n=== 结果：%d/5 符合期望 ===" % (5 - missed))
    return 0 if missed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
