"""checks.py - ai-workflow 自检工具（子命令式）。

子命令:
    skill [--skill-dir DIR]      技能自身完整性自检（开发/改造后用）
    plan <plan.yaml|任务目录>     任务执行计划校验 + Anti-drop 交付物对账（阶段 3/5 用）
    status [--workspace DIR]     工作区任务总览：层级/步骤完成/交付物完成度/陈旧任务归档建议（阶段 0/6 用）
    mark <plan.yaml> <id> <状态>  安全更新某步骤状态（替代手工编辑，保留文件其余内容）

用法:
    python checks.py skill
    python checks.py plan "E:/ChatGPT/工作流/tasks/xxx/plan.yaml" --base "E:/ChatGPT/工作流"
    python checks.py status --workspace "E:/ChatGPT/工作流"
    python checks.py mark "E:/ChatGPT/工作流/tasks/xxx/plan.yaml" 3 完成

skill 子命令检查项:
    1. SKILL.md 存在且 frontmatter 含 name / description / agent_created
    2. 文档间引用完整性（SKILL.md 与 references/*.md 中 `路径.ext` 引用是否真实存在）
    3. assets/templates/*.yaml 统一 schema 字段齐全（9 字段，含 workspace 工作区根）
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
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_SKILL_DIR = Path.home() / ".workbuddy" / "skills" / "ai-workflow"
SKILLS_ROOT = Path.home() / ".workbuddy" / "skills"
TEMPLATE_FIELDS = (
    "task_type",
    "confirmed_at",
    "workspace",
    "goal",
    "inputs",
    "deliverable",
    "acceptance",
    "constraints",
    "research",
)
PLAN_META_REQUIRED = ("任务", "验证信号", "工作区根")
PLAN_STEP_REQUIRED = ("做什么", "验证方式", "状态", "交付物")
VALID_STATUS = ("待办", "进行中", "完成", "受阻")
# 业务性相对路径：不是技能内文件，跳过引用检查
REF_WHITELIST = {"plan.yaml", "memory/YYYY-MM-DD.md", "README.md"}
# 命名占位符（如 第NNN章-标题.md、报告-YYYY-MM-DD.md、<主题>.md）不是真实文件路径，跳过
REF_PLACEHOLDER = re.compile(r"N{2,}|Y{2,}|M{2,}|D{2,}|<|>|\{|\}|xxx|XXX")
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
            if ref in REF_WHITELIST or ref in seen or REF_PLACEHOLDER.search(ref):
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
        (ok if not miss else fail)(f"模板 schema：{t.name}", ("缺 " + ",".join(miss)) if miss else f"{len(TEMPLATE_FIELDS) - len(miss)}/{len(TEMPLATE_FIELDS)}")

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


def _expand_braces(token: str) -> list[str]:
    """展开 {a,b} 花括号组合（plan 中常见的批量路径写法）。"""
    m = re.search(r"\{([^{}]*)\}", token)
    if not m:
        return [token]
    out = []
    for part in m.group(1).split(","):
        out.extend(_expand_braces(token[: m.start()] + part.strip() + token[m.end():]))
    return out


def _candidate_paths(raw: str, base: Path) -> list[Path]:
    raw = _clean_token(raw).strip().strip('"').strip("'")
    p = Path(raw)
    if p.is_absolute():
        return [p]
    cands = [base / p, Path.home() / ".workbuddy" / p, base.parent / p]
    # skill 内相对路径（如 references/xxx.md、scripts/yyy.py）逐个技能目录再试一遍
    if SKILLS_ROOT.exists():
        cands.extend(sd / p for sd in SKILLS_ROOT.glob("*/"))
    return cands


def _is_file_like(token: str) -> bool:
    return bool(re.search(r"\.[A-Za-z0-9]{1,5}$", token.strip())) or "/" in token or "\\" in token


def _require_yaml():
    """导入 pyyaml；缺失时给出可执行的修复指引并以 2 退出（避免裸 traceback 与假绿）。"""
    try:
        import yaml
    except ModuleNotFoundError:
        print("[ERROR] 缺少 pyyaml，请先运行 scripts/setup_env.ps1 安装依赖", file=sys.stderr)
        print("[HINT ] 若 venv 已建好，请直接用 venv 解释器运行：", file=sys.stderr)
        print("        C:\\Users\\26717\\.workbuddy\\binaries\\python\\envs\\ai-workflow\\Scripts\\python.exe checks.py ...",
              file=sys.stderr)
        raise SystemExit(2)
    return yaml


def load_plan(path: Path) -> dict:
    yaml = _require_yaml()

    if path.is_dir():
        path = path / "plan.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _clean_token(token: str) -> str:
    """剥离交付物字段里常见的括号注释，如 `路径/文件.md（说明）`。"""
    return re.sub(r"[（(][^）)]*[）)]\s*$", "", token).strip()


def audit_step(s: dict, base: Path) -> dict:
    """返回单步对账结果：{id, 状态, 交付物总数, 存在数, 缺失列表, 非文件型列表}"""
    raw = str(s.get("交付物", "")).strip()
    tokens: list[str] = []
    for variant in _expand_braces(raw):  # 先展开 {a,b}，再按分隔符切分
        tokens.extend(_clean_token(t) for t in re.split(r"[、,;；]|\s／\s", variant) if t.strip())
    missing, nonfile = [], []
    for token in tokens:
        if not _is_file_like(token):
            nonfile.append(token)
        elif not any(c.exists() for c in _candidate_paths(token, base)):
            missing.append(token)
    return {
        "id": s.get("id", "?"),
        "状态": str(s.get("状态", "")).strip(),
        "交付物总数": len([t for t in tokens if _is_file_like(t)]),
        "存在数": len([t for t in tokens if _is_file_like(t)]) - len(missing),
        "缺失": missing,
        "非文件型": nonfile,
    }


def _pad(text: str, width: int) -> str:
    """按显示宽度补齐（中文/全角算 2 列）。"""
    disp = sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)
    return text + " " * max(1, width - disp)


def cmd_status(workspace: Path, archive_days: int, max_tasks: int) -> int:
    tasks_root = workspace / "tasks"
    if not tasks_root.exists():
        fail("tasks/ 目录存在", str(tasks_root))
        return 1
    dirs = sorted([d for d in tasks_root.iterdir() if d.is_dir() and not d.name.startswith("_")])
    if not dirs:
        ok("tasks/ 下无任务目录")
        return 0

    now = time.time()
    stale = []
    print(_pad("任务目录", 46) + _pad("层级", 7) + _pad("步骤完成", 11) + _pad("交付物", 11) + "最后修改")
    print("-" * 86)
    for d in dirs:
        plan = d / "plan.yaml"
        age_days = (now - d.stat().st_mtime) / 86400
        layer, steps_txt, deliv_txt = "—", "无 plan", "—"
        if plan.exists():
            try:
                data = load_plan(plan)
                layer = str((data.get("meta") or {}).get("任务层级", "—"))
                steps = data.get("steps") or []
                audited = [audit_step(s, workspace) for s in steps]
                done = [a for a in audited if a["状态"] == "完成"]
                total_deliv = sum(a["交付物总数"] for a in audited)
                exist = sum(a["存在数"] for a in audited)
                steps_txt = f"{len(done)}/{len(steps)}"
                deliv_txt = f"{exist}/{total_deliv}" if total_deliv else "0"
                if any(a["缺失"] for a in done):
                    deliv_txt += " ⚠"
                if not any("状态" in s for s in steps):  # v2 之前的计划结构，仅统计步数
                    steps_txt = f"旧格式 {len(steps)} 步"
            except Exception as e:  # noqa: BLE001 - 单个任务解析失败不应中断总览
                steps_txt = f"解析失败({type(e).__name__})"
        mark = " ← 建议归档" if age_days > archive_days else ""
        if age_days > archive_days:
            stale.append(d.name)
        print(_pad(d.name, 46) + _pad(layer, 7) + _pad(steps_txt, 11) + _pad(deliv_txt, 11) + f"{age_days:>4.0f} 天{mark}")

    if len(dirs) > max_tasks:
        print(f"\n[WARN] 任务目录 {len(dirs)} 个 > 阈值 {max_tasks}，建议归档最旧的若干个（参考 SKILL.md 阶段 6 归档规则）")
    if stale:
        print(f"[WARN] {len(stale)} 个任务超过 {archive_days} 天未改动：{', '.join(stale[:5])}{' …' if len(stale) > 5 else ''}")
    else:
        print(f"\n[ OK ] 无超过 {archive_days} 天的陈旧任务")
    ok("任务总览", f"{len(dirs)} 个任务目录")
    return 0


def cmd_mark(plan_path: Path, step_id: str, status: str) -> int:
    if status not in VALID_STATUS:
        fail("状态合法", f"『{status}』不在 {VALID_STATUS}")
        return 1
    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1
    lines = plan_path.read_text(encoding="utf-8").splitlines(keepends=True)
    cur = None
    target = None
    for i, ln in enumerate(lines):
        m = re.match(r"^\s*-\s*id:\s*(\S+)\s*$", ln)
        if m:
            cur = m.group(1)
        elif re.match(r"^\s*状态:", ln) and cur == str(step_id):
            target = i
            break
    if target is None:
        fail("找到该步骤的『状态』行", f"id={step_id}")
        return 1
    old = lines[target].strip()
    indent = re.match(r"^(\s*)", lines[target]).group(1)
    lines[target] = f"{indent}状态: {status}\n"
    plan_path.write_text("".join(lines), encoding="utf-8")
    ok("步骤状态已更新", f"id={step_id}：{old} → 状态: {status}")
    return 0


def check_plan(plan_path: Path, base: Path) -> int:
    yaml = _require_yaml()

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
        a = audit_step(s, base)
        for token in a["缺失"]:
            hint = "（交付物须写完整路径，缩写如『选品分析.yaml』无法定位）" if "/" not in token and "\\" not in token else ""
            fail(f"步骤 {sid} 交付物缺失", token[:80] + hint)
        for token in a["非文件型"]:
            skip(f"步骤 {sid} 交付物", f"『{token[:40]}』非文件型，需人工确认")
        if not a["缺失"] and a["交付物总数"] > 0:
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

    p = sub.add_parser("status", help="工作区任务总览（含交付物完成度与归档建议）")
    p.add_argument("--workspace", default=str(Path.cwd()), help="工作区根目录（含 tasks/）")
    p.add_argument("--archive-days", type=int, default=30, help="超过该天数未改动则建议归档（默认 30）")
    p.add_argument("--max-tasks", type=int, default=10, help="任务目录数超过该值则提示归档（默认 10）")

    p = sub.add_parser("mark", help="更新 plan.yaml 中某步骤的状态（替代手工编辑）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("step_id", help="步骤 id")
    p.add_argument("status", choices=VALID_STATUS, help="新状态")

    args = ap.parse_args()
    if args.cmd == "skill":
        code = check_skill(Path(args.skill_dir))
        name = "技能自检"
    elif args.cmd == "plan":
        code = check_plan(Path(args.target), Path(args.base))
        name = "计划对账"
    elif args.cmd == "status":
        code = cmd_status(Path(args.workspace), args.archive_days, args.max_tasks)
        name = "任务总览"
    else:
        code = cmd_mark(Path(args.plan), args.step_id, args.status)
        name = "状态更新"

    if args.cmd in ("skill", "plan"):
        print(f"=== ai-workflow {name} ===")
        for status, item, note in results:
            mark = {"OK": "[ OK ]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
            print(f"{mark} {item}" + (f" — {note}" if note else ""))
        n_fail = sum(1 for r in results if r[0] == "FAIL")
        if code != 0 and not results:
            # 环境/输入不满足，检查根本没跑起来 —— 绝不能输出"全绿"误导调用方
            print("=== 结果：未执行（环境或输入不满足，见上方 [ERROR]）===")
            return code
        print(f"=== 结果：{len(results) - n_fail}/{len(results)} 通过，FAIL={n_fail} ===")
        return 1 if n_fail else code
    else:  # status / mark：明细已即时打印，仅汇总结果行
        n_fail = sum(1 for r in results if r[0] == "FAIL")
        if args.cmd == "mark":  # mark 需要回显结果，status 的表格已打印
            for status, item, note in results:
                mark = {"OK": "[ OK ]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
                print(f"{mark} {item}" + (f" — {note}" if note else ""))
        if n_fail:
            if args.cmd != "mark":
                for status, item, note in results:
                    if status == "FAIL":
                        print(f"[FAIL] {item}" + (f" — {note}" if note else ""))
            return 1
        return code


if __name__ == "__main__":
    raise SystemExit(main())
