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
    2. meta 必填（任务 / 验证信号 / 工作区根）；steps 必填（做什么 / 验证方式 / 状态 / 交付物）
    3. 状态取值合法（待办 / 进行中 / 完成 / 受阻 / 熔断）
    4. Anti-drop 对账：状态=完成的步骤，其「交付物」必须真实存在（不接受"应该生成了"）
       —— 非文件型交付物（如「本次对话记录」）标记为 SKIP，需人工确认
    5. 熔断门禁（v2.5.2）：meta「熔断状态」取值合法（正常 / 已熔断，留空视为正常）；
       已熔断（或存在状态为「熔断」的步骤）时——必须存在《熔断报告》且含 5 个必填字段，
       并直接判 FAIL：**已熔断的任务不得作为可交付物**（见 SKILL.md 熔断机制）
    6. 交付物路径解析口径（v2.5.2）：相对路径**只**以 --base（工作区根）为基准；
       工作区根之外的文件必须写绝对路径（旧的跨目录兜底通道已移除）

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
VALID_STATUS = ("待办", "进行中", "完成", "受阻", "熔断")
# 熔断机制（v2.5.2）：两个存储态的唯一叫法 —— 正常（Closed）/ 已熔断（Open）；复位是一次迁移动作（Half-Open），不是第三个存储态，改回「正常」须用户明示并留痕
VALID_FUSE = ("正常", "已熔断")
FUSE_REPORT = "熔断报告.md"
FUSE_SECTIONS = ("触发条件", "已试路径", "卡点根因", "待决策选项", "复位条件")
# 业务性相对路径：不是技能内文件，跳过引用检查
REF_WHITELIST = {"plan.yaml", "Ledger.md", "memory/YYYY-MM-DD.md", "README.md",
                 # 用户级人格/记忆文件：按约定存在于 ~/.workbuddy/，不在技能目录内，不应按技能内引用校验
                 "USER.md", "MEMORY.md"}
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
    # 【v2.5.2】交付物**只**在「本次任务基准目录（--base，应为工作区根）」下解析，候选唯一。
    # 移除的两条通道均属假 PASS（夹具 A/B 实测，见 tasks/技能增强-ai-workflow-v2.5.2-2026-09-11/）：
    #   1) ~/.workbuddy/<p> —— 固定前缀兜底，使工作区内并不存在的交付物被
    #      ~/.workbuddy/skills/<技能>/… 的同名文件"救活"；
    #   2) base.parent/<p> —— 基准的上级，使交付物落在工作区根之外也判 PASS，与红线③冲突。
    # 需要声明工作区根之外的文件（如跨目录改技能本体）时，交付物**必须写绝对路径**。
    return [base / p]


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
    return yaml.safe_load(path.read_text(encoding="utf-8-sig")) or {}


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


def cmd_status(workspace: Path, archive_days: int, max_tasks: int, light: bool = False) -> int:
    tasks_root = workspace / "tasks"
    if not tasks_root.exists():
        fail("tasks/ 目录存在", str(tasks_root))
        print("       提示：工作区不是当前目录时请加 --workspace <工作区根>；"
              "任务目录应建在工作区根下的 tasks/（见 SKILL.md 红线③）")
        return 1
    dirs = sorted([d for d in tasks_root.iterdir() if d.is_dir() and not d.name.startswith("_")])
    if not dirs:
        ok("tasks/ 下无任务目录")
        return 0

    now = time.time()
    stale = []
    tripped_tasks = []
    print(_pad("任务目录", 46) + _pad("层级", 7) + _pad("步骤完成", 11) + _pad("交付物", 11) + "最后修改")
    print("-" * 86)
    for d in dirs:
        plan = d / "plan.yaml"
        age_days = (now - d.stat().st_mtime) / 86400
        layer, steps_txt, deliv_txt = "—", "无 plan", "—"
        fuse_mark = ""
        if plan.exists():
            try:
                data = load_plan(plan)
                meta = data.get("meta") or {}
                layer = str(meta.get("任务层级", "—"))
                steps = data.get("steps") or []
                if str(meta.get("熔断状态", "") or "").strip() == "已熔断" or any(
                    str(s.get("状态", "")).strip() == "熔断" for s in steps
                ):
                    fuse_mark = " ⚡已熔断"
                    tripped_tasks.append(d.name)
                done = [s for s in steps if str(s.get("状态", "")).strip() == "完成"]
                steps_txt = f"{len(done)}/{len(steps)}"
                if light:
                    deliv_txt = "—"  # 轻量模式不核对交付物存在性（跳过逐文件 exists 检查，N6）
                else:
                    audited = [audit_step(s, workspace) for s in steps]
                    total_deliv = sum(a["交付物总数"] for a in audited)
                    exist = sum(a["存在数"] for a in audited)
                    deliv_txt = f"{exist}/{total_deliv}" if total_deliv else "0"
                    # 已完成步骤中若有交付物缺失 → 打 ⚠（v2.5.3 修复：原写法 `for a in done` 拿
                    # 「步骤 dict」去取审计结果键 `缺失`，必抛 KeyError 并被外层宽 except 吞成
                    # 「解析失败(KeyError)」，导致总览的完成度列长期失真）
                    if any(a["缺失"] for a, s in zip(audited, steps)
                           if str(s.get("状态", "")).strip() == "完成"):
                        deliv_txt += " ⚠"
                if not any("状态" in s for s in steps):  # v2 之前的计划结构，仅统计步数
                    steps_txt = f"旧格式 {len(steps)} 步"
            except Exception as e:  # noqa: BLE001 - 单个任务解析失败不应中断总览
                steps_txt = f"解析失败({type(e).__name__})"
        mark = " ← 建议归档" if age_days > archive_days else ""
        if age_days > archive_days:
            stale.append(d.name)
        print(_pad(d.name, 46) + _pad(layer, 7) + _pad(steps_txt, 11) + _pad(deliv_txt, 11)
              + f"{age_days:>4.0f} 天{mark}{fuse_mark}")

    if tripped_tasks:
        print(f"\n[WARN] {len(tripped_tasks)} 个任务处于「已熔断」：{', '.join(tripped_tasks[:5])}{' …' if len(tripped_tasks) > 5 else ''}")
        print("       已熔断的任务禁止自动续跑、不得交付；复位须用户明示且两步缺一不可（见 SKILL.md 熔断机制）")
    if len(dirs) > max_tasks:
        print(f"\n[WARN] 任务目录 {len(dirs)} 个 > 阈值 {max_tasks}，建议归档最旧的若干个（参考 SKILL.md 阶段 6 归档规则）")
    if stale:
        print(f"[WARN] {len(stale)} 个任务超过 {archive_days} 天未改动：{', '.join(stale[:5])}{' …' if len(stale) > 5 else ''}")
    else:
        print(f"\n[ OK ] 无超过 {archive_days} 天的陈旧任务")
    ok("任务总览", f"{len(dirs)} 个任务目录" + (f"，其中 {len(tripped_tasks)} 个已熔断" if tripped_tasks else ""))
    return 0


def _set_meta_fuse(plan_path: Path, value: str) -> bool:
    """在 `meta` 块内设置 `熔断状态` 键（已存在则就地替换，缺失则插入到 meta 末尾；幂等）。

    存在的意义：熔断**复位**要求「meta 改回正常」+「熔断步骤改回非熔断」两步。
    若第一步只能手改 YAML，复位链路就留了个易错的人工口子（且与 `mark` 替代手工编辑的
    设计目标不一致）。本函数让两步都能被工具完成：`mark <plan> <step> <status> --fuse 正常`。
    """
    lines = plan_path.read_text(encoding="utf-8").splitlines(keepends=True)
    key_re = re.compile(r"^\s{2}熔断状态\s*:")
    in_meta, last_meta = False, None
    for i, ln in enumerate(lines):
        if re.match(r"^meta\s*:\s*$", ln):
            in_meta = True
            continue
        if not in_meta:
            continue
        if re.match(r"^\S", ln):  # 顶层键 → meta 块结束
            in_meta = False
            continue
        if key_re.match(ln):
            lines[i] = f"  熔断状态: {value}\n"
            plan_path.write_text("".join(lines), encoding="utf-8")
            return True
        if ln.strip():
            last_meta = i
    if last_meta is None:  # 没有 meta 块，不擅自新建
        return False
    lines.insert(last_meta + 1, f"  熔断状态: {value}\n")
    plan_path.write_text("".join(lines), encoding="utf-8")
    return True


def _load_batch(path: str) -> list[tuple[str, str]]:
    """解析批量文件：每行 `<step_id> <status>`（空白分隔），# 开头或空行忽略。"""
    p = Path(path)
    if not p.exists():
        fail("批量文件存在", str(p))
        raise SystemExit(1)
    pairs = []
    # utf-8-sig: Windows 侧用 Out-File/记事本写出的文件常带 BOM，带 BOM 时首个 step_id 会变成
    # 『\ufeff1』而恒匹配不上（v2.5.3 实测：`mark --batch` 报「找到该步骤的『状态』行 — id=1」）。
    for ln in p.read_text(encoding="utf-8-sig").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 2:
            fail("批量文件行格式", f"『{s}』应为『<step_id> <status>』")
            raise SystemExit(1)
        sid, st = parts[0], parts[1]
        if st not in VALID_STATUS:
            fail("状态合法", f"『{st}』不在 {VALID_STATUS}")
            raise SystemExit(1)
        pairs.append((sid, st))
    if not pairs:
        fail("批量文件非空", str(p))
        raise SystemExit(1)
    return pairs


def cmd_mark(plan_path: Path, step_id: str | None, status: str | None,
             fuse: str | None = None, batch: str | None = None) -> int:
    if status is not None and status not in VALID_STATUS:
        fail("状态合法", f"『{status}』不在 {VALID_STATUS}")
        return 1
    if fuse is not None and fuse not in VALID_FUSE:
        fail("熔断状态合法", f"『{fuse}』不在 {VALID_FUSE}")
        return 1
    # 收集本次要改的步骤：(step_id, status)；batch 与单步二选一来源
    if batch is not None:
        pairs = _load_batch(batch)
    else:
        if step_id is None and fuse is None:
            fail("参数", "至少给出 ` <step_id> <状态>` 或 `--fuse <正常|已熔断>` 或 `--batch <文件>`")
            return 1
        if step_id is not None and status is None:
            fail("参数", "给出 <step_id> 时必须同时给出 <状态>")
            return 1
        pairs = [(step_id, status)] if step_id is not None else []
    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1

    # 先处理 fuse（一次性写 meta）
    if fuse is not None:
        if not _set_meta_fuse(plan_path, fuse):
            fail("meta.熔断状态 写入", "未找到 `meta:` 块，请手工添加该键")
            return 1
        ok("meta.熔断状态已更新", f"→ {fuse}")
        if not pairs:
            return 0

    # N7：一次性读盘，定位所有目标行；任一缺失则整体失败、不落盘（信任但验证）
    lines = plan_path.read_text(encoding="utf-8").splitlines(keepends=True)
    targets: dict[str, int] = {}
    for sid, _ in pairs:
        cur = None
        target = None
        for i, ln in enumerate(lines):
            m = re.match(r"^\s*-\s*id:\s*(\S+)\s*$", ln)
            if m:
                cur = m.group(1)
            elif re.match(r"^\s*状态:", ln) and cur == str(sid):
                target = i
                break
        if target is None:
            fail("找到该步骤的『状态』行", f"id={sid}")
            return 1
        targets[sid] = target
    changes = []
    for sid, st in pairs:
        i = targets[sid]
        old = lines[i].strip()
        indent = re.match(r"^(\s*)", lines[i]).group(1)
        lines[i] = f"{indent}状态: {st}\n"
        changes.append(f"{sid}: {old} → 状态: {st}")
    plan_path.write_text("".join(lines), encoding="utf-8")
    ok("步骤状态已更新", f"{len(pairs)} 个：" + "; ".join(changes))
    return 0


def _check_fuse(meta: dict, steps: list, plan_path: Path) -> None:
    """熔断门禁（v2.5.2）：已熔断的任务不得作为可交付物。

    触发：meta「熔断状态」= 已熔断，**或**任一步骤状态为「熔断」（任一命中即阻断，fail-closed）。
    熔断时必须存在同目录《熔断报告.md》，且五个必填节**以标题行形式**出现（缺一即 FAIL）。
    复位须用户明示，且**两步缺一不可**，两步**均由 `mark` 支持**（不要求手改 YAML）：
    ① `mark <plan> --fuse 正常` 把 meta 改回『正常』；
    ② `mark <plan> <步骤id> <非熔断状态>` 把熔断步骤改回。
    合一句即：`mark <plan> <步骤id> 完成 --fuse 正常`。本工具**不做自动复位**。
    """
    raw = str(meta.get("熔断状态", "") or "").strip()
    if raw and raw not in VALID_FUSE:
        fail("meta.熔断状态 合法", f"实际『{raw}』，应为 {' / '.join(VALID_FUSE)} 之一（留空视为『正常』）")
        return
    tripped_steps = [str(s.get("id", "?")) for s in steps if str(s.get("状态", "")).strip() == "熔断"]
    if raw != "已熔断" and not tripped_steps:
        ok("熔断状态", "正常" if raw else "正常（未声明）")
        return

    detail = "meta.熔断状态=已熔断" if raw == "已熔断" else ""
    if tripped_steps:
        detail += ("；" if detail else "") + f"步骤 {'、'.join(tripped_steps)} 状态为『熔断』"
    fail("已熔断：不得作为可交付物",
         detail + " —— 自动化已停止。复位**须用户明示**，且两步缺一不可、均由 `mark` 完成："
         "① `mark <plan> --fuse 正常`；② `mark <plan> <步骤id> <非熔断状态>`。"
         "复位后重跑本命令确认 FAIL 清零（见 SKILL.md 熔断机制）")

    report = plan_path.parent / FUSE_REPORT
    if not report.exists():
        fail("熔断报告存在", f"缺失 {report}")
        return
    ok("熔断报告存在", str(report))
    text = report.read_text(encoding="utf-8", errors="replace")
    # 标题级校验：五个节名必须各自作为 markdown **标题行**出现。两步防绕过：
    #  ① 先剥除所有 fenced code block（```...```）——把节名写进代码块不算数（批D M1 复现的绕过）；
    #  ② 节名必须独占标题行（其后紧跟的不能是"单词字符"，含中文/字母/数字/下划线），
    #     防止「复位条件xx」这类前缀粘连绕过，同时允许「触发条件（质量类）」这种非单词字符后缀。
    text_body = re.sub(r"```.*?```", "", text, flags=re.S)
    miss = [s for s in FUSE_SECTIONS if not re.search(rf"^#+\s*{re.escape(s)}(?![\w])", text_body, re.M)]
    (ok if not miss else fail)(
        "熔断报告必含标题节",
        ("缺标题 " + "、".join(miss)) if miss else f"{len(FUSE_SECTIONS)}/{len(FUSE_SECTIONS)}",
    )


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
            hint = "（未在 --base=<工作区根> 下找到；相对路径以 --base 为基准，工作区根之外的文件须写绝对路径）"
            fail(f"步骤 {sid} 交付物缺失", token[:80] + hint)
        for token in a["非文件型"]:
            skip(f"步骤 {sid} 交付物", f"『{token[:40]}』非文件型，需人工确认")
        if not a["缺失"] and a["交付物总数"] > 0:
            deliverable_ok += 1

    ok("Anti-drop 对账", f"已完成步骤 {done_total} 个，交付物确认 {deliverable_ok} 个")

    _check_fuse(meta, steps, plan_path)
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
    p.add_argument("--light", action="store_true", help="轻量模式：仅统计 meta/步数/状态，跳过逐交付物 exists 检查（N6）")

    p = sub.add_parser("mark", help="更新 plan.yaml 的步骤状态与/或 meta 熔断状态（替代手工编辑）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("step_id", nargs="?", help="步骤 id（只改熔断状态时可省略）")
    p.add_argument("status", nargs="?", choices=VALID_STATUS, help="该步骤的新状态")
    p.add_argument("--fuse", choices=VALID_FUSE,
                   help="设置 meta.熔断状态；复位填『正常』（须与步骤状态一并复位，见 _check_fuse）")
    p.add_argument("--batch", help="批量文件：每行 `<step_id> <status>`（空行/# 忽略）；一次性落盘，避免 N 步 N 次重写（N7）")

    args = ap.parse_args()
    if args.cmd == "skill":
        code = check_skill(Path(args.skill_dir))
        name = "技能自检"
    elif args.cmd == "plan":
        code = check_plan(Path(args.target), Path(args.base))
        name = "计划对账"
    elif args.cmd == "status":
        code = cmd_status(Path(args.workspace), args.archive_days, args.max_tasks, args.light)
        name = "任务总览"
    else:
        code = cmd_mark(Path(args.plan), args.step_id, args.status, args.fuse, args.batch)
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
    else:  # status / mark：表格/明细已即时打印，这里只回显结果行（status 的熔断汇总行在此可见）
        for status, item, note in results:
            mark = {"OK": "[ OK ]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
            print(f"{mark} {item}" + (f" — {note}" if note else ""))
        n_fail = sum(1 for r in results if r[0] == "FAIL")
        return 1 if n_fail else code


if __name__ == "__main__":
    raise SystemExit(main())
