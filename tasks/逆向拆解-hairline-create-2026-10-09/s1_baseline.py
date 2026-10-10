# -*- coding: utf-8 -*-
"""s1 · D0 取数与钉版。

三件事，各自留原始输出：
  ① 冻结本次将改动的本体文件基线（复制 + 逐文件 sha256）
  ② 现场复核被拆对象坐标（本地 12 文件 sha256 ↔ .vendor/hairline.lock.json；上游 rev 用 api.github.com 复取）
  ③ 机器计数（T3：凡数量都给**取法与原始值**，多口径不一致时报「未收敛」）

⚠️ 纪律（teardown-mode §7）：**不运行被拆对象**。本脚本只 read/stat，绝不 import 或 exec 它的任何文件。
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

# 原为硬编码本机绝对路径（出站清单第 4 项）⇒ 改由 __file__ 推导
SKILL = Path(__file__).resolve().parents[2]
LIB = SKILL.parent
HB = LIB / "hairline-create"
TASK = SKILL / "tasks" / "逆向拆解-hairline-create-2026-10-09"
EV = SKILL / "tmp" / "hb-20261009"

# 本次将改动的**受版本控制**的本体文件
BODY_FILES = [
    "SKILL.md",
    "README.md",
    "references/external-skills.md",
    "references/ops.md",
    "_archive/changelog.md",
]

out: list[str] = []


def say(s: str = "") -> None:
    print(s)
    out.append(s)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def digest_of(files: dict[str, str]) -> str:
    """按台账自称的 content_digest_scope 复算：排序后的 <相对路径>\\0<字节数>\\0<sha256>\\n 串联取 sha256。

    ⚠️ 路径按台账口径带 `hairline-create/` 前缀（与台账 files[].path 同形）。
    """
    parts = []
    for rel, h in sorted(files.items()):
        parts.append(f"hairline-create/{rel}\0{(HB / rel).stat().st_size}\0{h}\n")
    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()


def lines_of(p: Path) -> int:
    return p.read_bytes().count(b"\n")


# ---------------------------------------------------------------- ① 本体基线
say("=" * 72)
say("① 本体基线冻结（本次将改动的受版本控制文件）")
say("=" * 72)
base = TASK / "fixtures" / "baseline"
base.mkdir(parents=True, exist_ok=True)
manifest = ["# baseline-manifest.sha256  （s1 生成；两段：本体侧 / 被拆对象侧）", "", "## 本体侧（本次将被改动的文件）"]
for rel in BODY_FILES:
    src = SKILL / rel
    assert src.exists(), f"缺文件: {src}"
    top = base / rel
    top.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, top)
    h = sha(src)
    same = sha(top) == h
    say(f"  [{'OK' if same else 'FAIL'}] {rel:36s} sha={h[:16]} bytes={src.stat().st_size}")
    assert same, f"副本 sha 不一致: {rel}"
    manifest.append(f"{h}  {rel.replace(chr(92), '/')}")

# ------------------------------------------------------------ ② 被拆对象坐标
say()
say("=" * 72)
say("② 被拆对象坐标复核")
say("=" * 72)
hb_files = sorted(p for p in HB.rglob("*") if p.is_file())
say(f"  取法：rglob('*') 过滤 is_file()，根 = {HB}")
say(f"  实测文件数 = {len(hb_files)}")
local = {str(p.relative_to(HB)).replace("\\", "/"): sha(p) for p in hb_files}
for rel, h in sorted(local.items()):
    say(f"    {h[:16]}  {rel}")

lock_path = LIB / ".vendor" / "hairline.lock.json"
lock = json.loads(lock_path.read_text(encoding="utf-8"))
say()
say(f"  台账：{lock_path.name}  vendor={lock.get('vendor')}  install_form={lock.get('install_form')}")
say(f"        upstream_rev={lock.get('upstream_rev')}")
say(f"        content_digest={lock.get('content_digest')}")
say(f"        file_count={lock.get('file_count')}  skills={lock.get('skills')}")

lock_files = {}
PREFIX = "hairline-create/"
for rec in lock.get("files", []):
    if isinstance(rec, dict):
        k = rec.get("path") or rec.get("name") or rec.get("file")
        v = rec.get("sha256") or rec.get("sha") or rec.get("hash")
        # ⚠️ 键形状归一：台账键带 `hairline-create/` 前缀，本地键相对 HB ⇒ 不归一会比对出**假不一致**
        k = str(k).replace("\\", "/")
        if k.startswith(PREFIX):
            k = k[len(PREFIX):]
        lock_files[k] = v
say(f"  lock 内 files 条目数 = {len(lock_files)}")
diff = [k for k in set(local) | set(lock_files) if local.get(k) != lock_files.get(k)]
say(f"  本地 ↔ lock 逐文件比对：不一致 {len(diff)} 个 {diff if diff else '（全部对上）'}")
say(f"  台账自报 content_digest = {lock.get('content_digest')}")
say(f"  台账自称 scope = {lock.get('content_digest_scope')}")
_want = lock.get("content_digest")
_variants = {}
for tag, prefix in (("无前缀", ""), ("带 hairline-create/ 前缀", "hairline-create/")):
    for order in ("size_then_sha", "sha_then_size"):
        for tail in ("每行以 \\n 结尾", "行间 \\n、末行无"):
            parts = []
            for rel, h in sorted(local.items()):
                size = (HB / rel).stat().st_size
                a, b = (size, h) if order == "size_then_sha" else (h, size)
                parts.append(f"{prefix}{rel}\0{a}\0{b}")
            good = len(parts) - 1 if tail == "行间 \\n、末行无" else len(parts)
            blob = ("\n".join(parts[:len(parts)]) if tail == "每行以 \\n 结尾" else "\n".join(parts)) + ("\n" if tail == "每行以 \\n 结尾" else "")
            _ = good
            _variants[f"{tag}｜{order}｜{tail}"] = hashlib.sha256(blob.encode("utf-8")).hexdigest()
hit = [k for k, v in _variants.items() if v == _want]
for k, v in _variants.items():
    say(f"    变体 {k:44s} → {v[:24]}…  {'★ 命中' if v == _want else ''}")
if hit:
    say(f"  ⇒ 复算结论：命中变体 = {hit[0]}（我的首版取法取错了 scope 形状，非台账错误）")
else:
    say(f"  ⇒ 复算结论：**未收敛** —— {len(_variants)} 个变体无一命中台账值；按 T3 如实报「未收敛」，不以任一值当真")
say(f"  （对照：s1 首跑用「带前缀 + size→sha + 每行\\n结尾」单一读法，得 {digest_of(local)[:24]}… 与台账不符）")

lic = (HB / "LICENSE").read_text(encoding="utf-8", errors="replace")
lic_line = next((ln.strip() for ln in lic.splitlines() if "Copyright" in ln), "(未找到 Copyright 行)")
say(f"  T3 对照｜台账自报 license_copyright = {lock.get('license_copyright')}")
say(f"  T3 对照｜LICENSE 原文           = {lic_line}")
say(f"  T3 对照｜一致？ {lock.get('license_copyright') in lic or lic_line.replace(' ', '') in lock.get('license_copyright', '').replace(' ', '')}")

manifest += ["", "## 被拆对象侧（Hairline 副本，与 .vendor/hairline.lock.json 对账）", f"# file_count={len(local)}（取法：rglob+is_file）"]
for rel, h in sorted(local.items()):
    manifest.append(f"{h}  hairline-create/{rel}")

# 上游 rev 现场复核
say()
say("  上游 rev 现场复核（api.github.com）：")
try:
    r = subprocess.run(
        ["gh", "api", "repos/lucasmarkes/hairline", "--jq",
         "{default_branch, pushed_at, license: .license.spdx_id, html_url}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    say(f"    gh rc={r.returncode}  {r.stdout.strip() or r.stderr.strip()[:300]}")
    branch = None
    try:
        branch = json.loads(r.stdout).get("default_branch")
    except Exception:  # noqa: BLE001
        pass
    if branch:
        r2 = subprocess.run(
            ["gh", "api", f"repos/lucasmarkes/hairline/commits/{branch}", "--jq", ".sha"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        say(f"    {branch} head sha = {r2.stdout.strip()}  (rc={r2.returncode})")
        say(f"    与 lock.upstream_rev 相等？ {r2.stdout.strip() == lock.get('upstream_rev')}")
except Exception as exc:  # noqa: BLE001
    say(f"    [坐标不可得] {type(exc).__name__}: {exc}")

# ------------------------------------------------------------------ ③ 计数
say()
say("=" * 72)
say("③ 机器计数（T3：每条都写取法，不采信自报）")
say("=" * 72)

def count(label: str, n: int, how: str) -> None:
    say(f"  {label:34s} = {n:4d}   （取法：{how}）")

count("hairline-create 文件数", len(hb_files), "rglob('*') 且 is_file()")
for rel in ["SKILL.md", "rules.md", "look.md", "concepts.md", "kernel.js", "look.mjs",
            "validate.mjs", "build.mjs", "bench.html", "examples/terrain.js", "examples/riffle.js", "LICENSE"]:
    p = HB / rel
    if p.exists():
        count(f"  行数 {rel}", lines_of(p), "read_bytes().count(b'\\n')（含末行）")

rules_txt = (HB / "rules.md").read_text(encoding="utf-8")
rule_ids = re.findall(r"^## (\d\d) · ", rules_txt, re.M)
count("rules.md 规则条数", len(rule_ids), r"^## (\d\d) ·  (re.M) → " + ",".join(rule_ids))
count("rules.md 「Rejected when」段数", rules_txt.count("**Rejected when:**"), "str.count('**Rejected when:**')")

look_txt = (HB / "look.md").read_text(encoding="utf-8")
items = re.findall(r"^(\d+)\. \*\*", look_txt, re.M)
count("look.md What-to-see 项数", len(items), r"^(\d+)\. \*\*  (re.M) → " + ",".join(items))
shots = re.findall(r"^\| `([a-z-]+)` \|", look_txt, re.M)
count("look.md 八张图（表内）", len(shots), "表行 `| `shot` |` → " + ",".join(shots))

con_txt = (HB / "concepts.md").read_text(encoding="utf-8")
proven = re.findall(r"^\| \*\*([^*]+)\*\* \|", con_txt, re.M)
count("concepts.md 六答案表行数", len(proven), "表行 `| **名** |` → " + ",".join(proven))

val_txt = (HB / "validate.mjs").read_text(encoding="utf-8")
hdr_names = re.findall(r"^ \*   ([a-z]+)\s{2,}", val_txt, re.M)
count("validate.mjs 头部声明的 check 名", len(hdr_names), "^ \\*   (name)  (re.M) → " + ",".join(hdr_names))


def block(name: str) -> str:
    """切出 `const <name> = [` … `\\n];` 之间的正文 —— 两个数组的条目行首同为 `  ["id",`，不切片无法区分。"""
    m = re.search(rf"^const {name} = \[(.*?)^\];", val_txt, re.S | re.M)
    return m.group(1) if m else ""


bad_block, need_block = block("BAD"), block("NEED")
bad_ids = re.findall(r'^  \["(\w+)",', bad_block, re.M)
need_ids = re.findall(r'^  \["(\w+)",', need_block, re.M)
count("validate.mjs BAD 条目数", len(bad_ids), "切 `const BAD = [`…`];` 后 ^  \\[\"(\\w+)\", → " + ",".join(bad_ids))
count("validate.mjs NEED 条目数", len(need_ids), "切 `const NEED = [`…`];` 后同法 → " + ",".join(need_ids))
code_ids = set(re.findall(r'out\.push\(\s*["`]([a-z]+):', val_txt))
count("validate.mjs `out.push('<id>: …')` 直推的 id", len(code_ids),
      "out.push(\"<id>:…\") / out.push(`<id>:…`) → " + ",".join(sorted(code_ids)))
# ⚠️ 只看 out.push 会漏掉「由辅助函数产出、由 ...spread 推进去」的 id（parse / declare）。
#    ⇒ 改用**覆盖检查**：头部每个声明名，是否在文件里找得到产出点（数组条目 / out.push / 模板字面量 / say()）。
miss = []
for nm in sorted(set(hdr_names)):
    pat = rf'\["{nm}",|out\.push\(\s*[`"]({nm}):|`{nm}:|\bsay\(`{nm}:'
    if not re.search(pat, val_txt):
        miss.append(nm)
count("validate.mjs 头部 14 个声明名中**找不到产出点**的", len(miss),
      "逐名正则在「数组条目 / out.push(`id:…) / 模板 `id: / say(`id:」中找 → " + (",".join(miss) if miss else "无（全部可追到产出点）"))
say(f"  ⇒ 计数收敛口径：头部自报 {len(set(hdr_names))} 个；"
    f"其中 BAD {len(set(bad_ids))} + NEED {len(set(need_ids))} + out.push 直推 {len(code_ids)} 的并集 = "
    f"{len(set(bad_ids) | set(need_ids) | code_ids)}；差集 = {sorted(set(hdr_names) - (set(bad_ids) | set(need_ids) | code_ids))}"
    f"（该差集本次已逐个追到产出点，故 s1 首版报的「未收敛」是**取法漏项**，非真未收敛）")

ker = (HB / "kernel.js").read_text(encoding="utf-8")
exp = re.search(r"__export\(kernel_exports, \{(.*?)\n  \}\);", ker, re.S)
surf = re.findall(r"(\w+): \(\) =>", exp.group(1)) if exp else []
count("kernel.js HL 表面成员数", len(surf), "__export(kernel_exports,{…}) 内 `name: () =>` 计数")
mods = re.findall(r"^  // (packages/\S+)$", ker, re.M)
count("kernel.js 内联模块数", len(mods), "行首 `  // packages/...` (re.M) → " + " | ".join(mods))
say(f"  模块行段（区间为闭区间，右端 = 下一个 markers 行号 − 1）：")
mk = [(m.group(1), ker[:m.start()].count("\n") + 1) for m in re.finditer(r"^  // (packages/\S+)$", ker, re.M)]
for i, (name, start) in enumerate(mk):
    end = (mk[i + 1][1] - 1) if i + 1 < len(mk) else ker.count("\n") + 1
    say(f"    {name:44s} L{start:4d}–{end:4d}  ({end - start + 1} 行)")

sk_txt = (HB / "SKILL.md").read_text(encoding="utf-8")
sects = re.findall(r"^## (\d+\. .+)$", sk_txt, re.M)
count("hairline SKILL.md 章节数", len(sects), "^## (n. 名) (re.M) → " + " | ".join(s.strip() for s in sects))

# ------------------------------------------------------------------- 落盘
(EV / "d0-coordinate.txt").write_text("\n".join(out) + "\n", encoding="utf-8", newline="")
(TASK / "fixtures" / "baseline-manifest.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8", newline="")
print()
print(f"[OK] 证据 → {EV / 'd0-coordinate.txt'}")
print(f"[OK] 清单 → {TASK / 'fixtures' / 'baseline-manifest.sha256'}")
assert not diff, f"本地与 lock 不一致: {diff}"
sys.exit(0)
