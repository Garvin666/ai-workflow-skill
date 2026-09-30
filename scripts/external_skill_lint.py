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

    python scripts/external_skill_lint.py                    # 用默认技能库根与 lock
    python scripts/external_skill_lint.py --root <技能库根>
    python scripts/external_skill_lint.py --verify-lock       # 加做 lock 一致性
    python scripts/external_skill_lint.py --skill tdd         # 只查一个

退出码：0 = 无 FAIL；1 = 有 FAIL；2 = 前置条件不满足（lock 缺失/不可解析）。

## 诚实边界

- **只查 lock 里登记的技能**，不遍历技能库全量 —— 用户自建技能与宿主本体不在范围内。
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
    if bad:
        add("FAIL", "lock 与磁盘一致性", "；".join(bad[:10]) +
            (f"（共 {len(bad)} 项）" if len(bad) > 10 else ""))
    else:
        add("OK", "lock 与磁盘一致性", f"{len(lock.get('files', []))} 个文件逐一对上")


def main() -> int:
    ap = argparse.ArgumentParser(description="外部 vendored 技能的放宽判据检查器")
    ap.add_argument("--root", default=str(Path.home() / ".workbuddy" / "skills"),
                    help="技能库根（默认 ~/.workbuddy/skills）")
    ap.add_argument("--lock", default=None, help="lock 路径（默认 <root>/.vendor/mattpocock.lock.json）")
    ap.add_argument("--skill", default=None, help="只查指定技能")
    ap.add_argument("--verify-lock", action="store_true", help="加做 lock 与磁盘 sha256 一致性检查")
    args = ap.parse_args()

    root = Path(args.root)
    lock_path = Path(args.lock) if args.lock else root / ".vendor" / "mattpocock.lock.json"
    if not lock_path.is_file():
        print(f"[ERROR] lock 不存在：{lock_path}")
        return 2
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERROR] lock 不可解析：{e}")
        return 2

    names = lock.get("skills", [])
    if args.skill:
        if args.skill not in names:
            print(f"[ERROR] 技能 {args.skill} 不在 lock 登记范围内")
            return 2
        names = [args.skill]

    exempt = {(m["skill"], m["ref"]) for m in lock.get("reference_mentions", [])}

    print("=== 外部技能放宽判据检查 ===")
    print(f"来源：{lock.get('vendor')} @ {lock.get('upstream_rev_short')}"
          f"（{lock.get('upstream_date')}）｜许可 {lock.get('license')}")
    print(f"范围：{len(names)} 个已登记技能（lock 口径；不含宿主本体与用户自建技能）\n")

    for name in names:
        d = root / name
        if not d.is_dir():
            add("FAIL", f"{name} · 目录存在", "lock 已登记但磁盘无此目录")
            continue
        if check_frontmatter(d, name):
            check_refs(d, name, exempt)
        check_secrets_and_scripts(d, name)

    if args.verify_lock:
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
