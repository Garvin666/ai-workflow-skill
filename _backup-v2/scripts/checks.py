"""checks.py - ai-workflow 自检工具（子命令式）。

子命令:
    skill [--skill-dir DIR]      技能自身完整性自检（开发/改造后用）
    plan <plan.yaml|任务目录>     任务执行计划校验 + Anti-drop 交付物对账（阶段 3/5 用）

用法:
    python checks.py skill
    python checks.py plan "E:/ChatGPT/工作流/tasks/xxx/plan.yaml" --base "E:/ChatGPT/工作流"

skill 子命令检查项:
    1. SKILL.md 存在且 frontmatter 含 name / description / agent_created
    2. 文档间引用完整性（SKILL.md 与 references/*.md 中 `路径.ext` 引用是否真实存在）
    3. assets/templates/*.yaml 统一 schema 字段齐全（8 字段）
    4. assets/plan-template.yaml 必填键存在
    5. scripts/*.py 语法编译通过（py_compile，检查后自动清理 __pycache__）

plan 子命令检查项:
    1. YAML 可解析（需 pyyaml：setup_env.ps1 已纳入依赖）
    2. meta 必填（任务 / 验证信号）；steps 必填（做什么 / 验证方式 / 状态 / 交付物）
    3. 状态取值合法（待办 / 进行中 / 完成 / 受阻）
    4. Anti-drop 对账：状态=完成的步骤，其「交付物」必须真实存在（不接受"应该生成了"）
       —— 非文件型交付物（如「本次对话记录」）标记为 SKIP，需人工确认

退出码: 0 = 全部通过；1 = 有 FAIL（不可交付）；2 = 用法错误
"""
import argparse
import py_compile
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_SKILL_DIR = Path.home() / ".workbuddy" / "skills" / "ai-workflow"
TEMPLATE_FIELDS = (
    "task_type",
    "confirmed_at",
    "goal",
    "inputs",
    "deliverable",
    "acceptance",
    "constraints",
    "research",
)
PLAN_META_REQUIRED = ("任务", "验证信号")
PLAN_STEP_REQUIRED = ("做什么", "验证方式", "状态", "交付物")
VALID_STATUS = ("待办", "进行中", "完成", "受阻")
# 业务性相对路径：不是技能内文件，跳过引用检查
REF_WHITELIST = {"plan.yaml", "memory/YYYY-MM-DD.md", "README.md"}
REF_PATTERN = re.compile(r"`([A-Za-z0-9_./\u4e00-\u9fff-]+\.(?:md|yaml|py|ps1))`")

results: list[tuple[str, str, str]] = []  # (状态, 检查项, 说明)


def ok(item: str, note: str = "") -> None:
    results.append(("OK", item, note))


def fail(item: str, note: str = "") -> None:
    results.append(("FAIL", item, note))


def skip(item: str, note: str = "") -> None:
    results.append(("SKIP", item, note))


def _resolve(ref: str, skill_dir: Path) -> Path | None:
    """在技能目录常见位置查找引用文件。"""
    for cand in (skill_dir / ref, skill_dir / "scripts" / ref, skill_dir / "assets" / ref,
                 skill_dir / "references" / ref):
        if cand.exists():
            return cand
    return None


def check_skill(skill_dir: Path) -> int:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        fail("SKILL.md 存在", str(skill_md))
        return 1
    ok("SKILL.md 存在")

    head = skill_md.read_text(encoding="utf-8")[:800]
    for key in ("name:", "description:", "agent_created:"):
        (ok if key in head else fail)(f"frontmatter 含 {key.rstrip(':')}")

    docs = [p for p in [skill_md, *sorted((skill_dir / "references").glob("*.md"))] if p.exists()]
    missing = []
    seen = set()
    for doc in docs:
        for ref in REF_PATTERN.findall(doc.read_text(encoding="utf-8")):
            if ref in REF_WHITELIST or ref in seen:
                continue
            seen.add(ref)
            if _resolve(ref, skill_dir) is None:
                missing.append(f"{ref}（来自 {doc.name}）")
    if missing:
        fail("文档引用完整性", "缺失：" + "；".join(missing))
    else:
        ok("文档引用完整性", f"检查 {len(seen)} 条引用")

    tmpl_dir = skill_dir / "assets" / "templates"
    tmpls = [p for p in sorted(tmpl_dir.glob("*.yaml"))]
    if not tmpls:
        fail("模板 schema", "未找到 assets/templates/*.yaml")
    for t in tmpls:
        text = t.read_text(encoding="utf-8")
        miss = [f for f in TEMPLATE_FIELDS if not re.search(rf"^{f}:", text, re.M)]
        (ok if not miss else fail)(f"模板 schema：{t.name}", ("缺 " + ",".join(miss)) if miss else "8/8")

    pt = skill_dir / "assets" / "plan-template.yaml"
    if pt.exists():
        text = pt.read_text(encoding="utf-8")
        miss = [k for k in ("任务", "验证信号", "步骤", "交付物") if k not in text]
        (ok if not miss else fail)("plan-template 必填键", ("缺 " + ",".join(miss)) if miss else "齐全")
    else:
        fail("plan-template.yaml 存在")

    pyfiles = sorted((skill_dir / "scripts").glob("*.py"))
    if not pyfiles:
        fail("脚本存在", "scripts/*.py 为空")
    for py in pyfiles:
        try:
            py_compile.compile(str(py), doraise=True)
            ok(f"py_compile：{py.name}")
        except py_compile.PyCompileError as e:
            fail(f"py_compile：{py.name}", str(e).splitlines()[0][:120])
    cache = skill_dir / "scripts" / "__pycache__"
    if cache.exists():
        shutil.rmtree(cache, ignore_errors=True)
    return 0


def _candidate_paths(raw: str, base: Path) -> list[Path]:
    raw = raw.strip().strip('"').strip("'")
    p = Path(raw)
    cands = [p] if p.is_absolute() else [base / p, Path.home() / ".workbuddy" / p, base.parent / p]
    return cands


def _is_file_like(token: str) -> bool:
    return bool(re.search(r"\.[A-Za-z0-9]{1,5}$", token.strip())) or "/" in token or "\\" in token


def check_plan(plan_path: Path, base: Path) -> int:
    try:
        import yaml
    except ModuleNotFoundError:
        print("[ERROR] 缺少 pyyaml，请先运行 scripts/setup_env.ps1 安装依赖", file=sys.stderr)
        return 2

    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1
    ok("plan.yaml 存在", str(plan_path))

    try:
        data = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        fail("plan.yaml 可解析", str(e).splitlines()[0][:120])
        return 1
    ok("plan.yaml 可解析")

    meta = data.get("meta") or {}
    for k in PLAN_META_REQUIRED:
        value = str(meta.get(k, "") or "").strip()
        (ok if value else fail)(f"meta.{k}", "" if value else "为空")

    steps = data.get("steps") or []
    if not steps:
        fail("steps 非空")
        return 1
    ok("steps 非空", f"{len(steps)} 步")

    done_total = deliverable_ok = 0
    for s in steps:
        sid = s.get("id", "?")
        miss = [k for k in PLAN_STEP_REQUIRED if not str(s.get(k, "") or "").strip()]
        if miss:
            fail(f"步骤 {sid} 必填字段", "缺 " + ",".join(miss))
        st = str(s.get("状态", "")).strip()
        if st not in VALID_STATUS:
            fail(f"步骤 {sid} 状态合法", f"实际『{st}』")
        if st != "完成":
            continue
        done_total += 1
        raw = str(s.get("交付物", "")).strip()
        tokens = [t for t in re.split(r"[、,;；]|(?<=\.(?:md|yaml|py|ps1|xlsx|docx|pdf|csv|html))\s+", raw) if t.strip()]
        found_any = False
        for token in tokens:
            if not token.strip():
                continue
            if not _is_file_like(token):
                skip(f"步骤 {sid} 交付物", f"『{token.strip()[:40]}』非文件型，需人工确认")
                continue
            if any(c.exists() for c in _candidate_paths(token, base)):
                found_any = True
            else:
                fail(f"步骤 {sid} 交付物缺失", token.strip()[:80])
        if found_any:
            deliverable_ok += 1

    ok("Anti-drop 对账", f"已完成步骤 {done_total} 个，交付物确认 {deliverable_ok} 个")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="ai-workflow 自检工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("skill", help="技能自身完整性自检")
    p.add_argument("--skill-dir", default=str(DEFAULT_SKILL_DIR))

    p = sub.add_parser("plan", help="计划校验 + Anti-drop 对账")
    p.add_argument("target", help="plan.yaml 路径或任务目录")
    p.add_argument("--base", default=str(Path.cwd()), help="相对路径解析基准（默认当前目录）")

    args = ap.parse_args()
    code = check_skill(Path(args.skill_dir)) if args.cmd == "skill" else check_plan(Path(args.target), Path(args.base))

    name = "技能自检" if args.cmd == "skill" else "计划对账"
    print(f"=== ai-workflow {name} ===")
    for status, item, note in results:
        mark = {"OK": "[ OK ]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
        print(f"{mark} {item}" + (f" — {note}" if note else ""))
    n_fail = sum(1 for r in results if r[0] == "FAIL")
    print(f"=== 结果：{len(results) - n_fail}/{len(results)} 通过，FAIL={n_fail} ===")
    raise SystemExit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
