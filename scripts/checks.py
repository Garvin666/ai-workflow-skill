"""checks.py - ai-workflow 自检工具（子命令式）。

子命令:
    skill [--skill-dir DIR]      技能自身完整性自检（开发/改造后用）
    plan <plan.yaml|任务目录>     任务执行计划校验 + Anti-drop 交付物对账（阶段 3/5 用）
    status [--workspace DIR]     工作区任务总览：层级/步骤完成/交付物完成度/陈旧任务归档建议（阶段 0/6 用）
    mark <plan.yaml> <id> <状态>  安全更新某步骤状态（替代手工编辑，保留文件其余内容）
    decide <plan.yaml> --point …  追加一条能力决策记录到 meta.决策记录（自主决策层留痕，v3.0.0）
    revise <plan.yaml> --trigger … 追加一条计划修订到 meta.计划修订（重规划留痕，v3.0.0）
    selftool <plan.yaml> --name …  追加一条自研工具/技能登记到 meta.自研工具（公开留痕，v3.1.0）

用法:
    python checks.py skill
    python checks.py plan "E:/ChatGPT/工作流/tasks/xxx/plan.yaml" --base "E:/ChatGPT/工作流"
    python checks.py status --workspace "E:/ChatGPT/工作流"
    python checks.py mark "E:/ChatGPT/工作流/tasks/xxx/plan.yaml" 3 完成
    python checks.py decide "…/plan.yaml" --point "缺什么" --basis "一句话判据" --capability 事实 --choice "gh api …"
    python checks.py revise "…/plan.yaml" --trigger R1 --change "新增步骤 3b"
    python checks.py selftool "…/plan.yaml" --name "publish_tools.py" --purpose "推送自研工具到 public 仓" \
        --scenario "产生自研脚本/技能时用；复用第三方或改既有文件时不用" \
        --repo "https://github.com/Garvin666/ai-workflow-tools/blob/main/scripts/publish_tools.py"

skill 子命令检查项:
    1. SKILL.md 存在且 frontmatter 含 name / description / agent_created
    2. 文档间引用完整性（SKILL.md 与 references/*.md 中 `路径.ext` 引用是否真实存在）
    3. assets/templates/*.yaml 统一 schema 字段齐全（9 字段，含 workspace 工作区根）
    4. assets/plan-template.yaml 必填键存在
    5. scripts/*.py 语法编译通过（py_compile；`.pyc` 输出到**系统临时目录**，不产生 __pycache__）
    6. 口径守卫（v3.5.0 / P0-3）：**解析手册与模板**里定义的取值，断言其与下方代码常量为同一集合 ——
       消灭"同源只靠注释声明、不靠测试保证"。覆盖 5 个物理量：模型档位 / 步骤状态 / 能力类 /
       重规划触发 / 熔断状态。**解析不到即 FAIL**（守着一条读不到的规则等于没有规则）。

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
    7. 自研工具留痕（v3.1.0）：meta「自研工具」可选，一旦填写每项必含
       名称/用途/适用场景/仓库链接（空值或占位符链接判 FAIL；『待推送』判 SKIP 需人工确认）
    8. 模型档位合法（v3.4.0 / P9-c）：steps[].「模型档位」可选，留空即跳过；
       一旦填写必须在 strong/mid/cheap/default 内（取值定义见 references/routing-guide.md）
    9. 交付物越界（v3.5.0 / P0-1，红线③机器化）：交付物解析后落在 `meta.工作区根` 之外 →
       FAIL；`meta.越界授权` 登记的路径作白名单，基础设施例外路径（技能目录 / venv / 缓存）自动豁免。
       ⚠️ **旧模板兼容**：plan 里**没有**「越界授权」键（早于 v3.3.0 的产物）时只出 WARN 不阻断 ——
       不为一个新判据去追认历史计划（那等于拿新规则改写旧证据）。
    10. 自研工具漏登记（v3.5.0 / P1-1）：本任务交付物中带 `[自研工具]`/`[自研技能]` 标注头、
       却未登记进 `meta.自研工具` → **WARN**（不是 FAIL：标注头只是充分线索，登记才是判据）。
    11. 阶段门禁（v3.5.0 / P2-2）：阶段 2「方案评审」与阶段 4「数值口径」各一条最低成本门禁，
       **只出 WARN**（首版刻意不设 FAIL，避免造出随机 FAIL 源）。

状态取值: OK / FAIL / SKIP / **WARN**（WARN 只提示、不计入 FAIL，也不改变退出码）

退出码: 0 = 全部通过；1 = 有 FAIL（不可交付）；2 = 用法错误
"""
import argparse
import json
import py_compile
import re
import sys
import tempfile
import time
from datetime import datetime
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
# 自主决策层（v3.0.0）：能力路由 + 自适应计划的留痕口径。字段全为**可选**——
# 纯本地任务本就无外部辅助，强制填空会退化成走过场（见 references/adaptive-planning.md 第三节）。
VALID_CAPABILITY = ("知识", "算力", "事实", "手脚")
VALID_TRIGGER = ("R1", "R2", "R3", "R4", "R5", "R6")
# P9-c（v3.4.0）：`模型档位` 取值 —— 与 references/routing-guide.md 的 enum 同源。
# 可选字段，留空合法；填了必须在此集内（含 `default` = 显式声明按阶段默认档位）。
VALID_MODEL_TIERS = ("strong", "mid", "cheap", "default")
# 决策记录的必填项。⚠️ 此元组是**唯一事实源**：FAIL 文案由它生成，
# 避免"文案写 5 个字段、代码只强制 3 个"这类描述↔实现脱节（v3.0.0 返修项 P4）。
DECISION_KEYS = ("决策点", "能力类", "依据", "选择")
REVISION_KEYS = ("触发", "变化", "时间")
MAX_REVISIONS = 3  # 超上限说明初始拆解有问题，应停下与用户重新对齐目标（非熔断）
# 自研工具与技能公开留痕（v3.1.0）：四项必填。⚠️ 与 DECISION_KEYS 同理，此元组是
# FAIL 文案的唯一事实源，防止再出现"文案写 N 个字段、代码只强制 M 个"的脱节。
SELFTOOL_KEYS = ("名称", "用途", "适用场景", "仓库链接")
# 中间态：登记时尚未推送。允许它是因为"先登记后推送"存在时序，但**交付前必须回填真实链接**
# —— 故门禁对它判 SKIP（需人工确认）而非 OK，避免"填了待推送就当完成"。
SELFTOOL_PENDING = "待推送"
# 占位符链接（<...> / TODO / xxx / 待定 / N/A）不是真实地址，判 FAIL
SELFTOOL_PLACEHOLDER = re.compile(r"[<>]|TODO|todo|XXX|xxx|\{|\}|待定|N/A")
FUSE_REPORT = "熔断报告.md"
FUSE_SECTIONS = ("触发条件", "已试路径", "卡点根因", "待决策选项", "复位条件")
# 业务性相对路径：不是技能内文件，跳过引用检查
REF_WHITELIST = {"plan.yaml", "Ledger.md", "memory/YYYY-MM-DD.md", "README.md",
                 # 用户级人格/记忆文件：按约定存在于 ~/.workbuddy/，不在技能目录内，不应按技能内引用校验
                 "USER.md", "MEMORY.md"}
# 跨根引用前缀（v3.1.1）：这些路径的**根不在技能目录内**（技能库索引 / 工作区代码与数据 /
# 用户级目录），引用它们只为叙述证据出处，无法也不应做存在性校验。留**前缀规则**而非精确文件名，
# 否则每写一篇日志引用一个工作区文件就要往白名单塞一条 —— 2026-09-16 实测：补一次变更日志就撞出 3 条 FAIL。
# ⚠️ 判定顺序是「**先尝试按技能内解析、失败后再判前缀**」（见 check_skill），故本元组不会掩盖
# 技能内真实存在的同名路径（如 `scripts/checks.py` 仍按技能内引用校验）。
REF_EXTERNAL_PREFIXES = (".workbuddy/", ".scratch/", "历史数据集/", "backend/", "frontend/",
                         "indicators/", "daily_scheduler/", "tests/")
# 命名占位符（如 第NNN章-标题.md、报告-YYYY-MM-DD.md、<主题>.md）不是真实文件路径，跳过
REF_PLACEHOLDER = re.compile(r"N{2,}|Y{2,}|M{2,}|D{2,}|<|>|\{|\}|xxx|XXX")
REF_PATTERN = re.compile(r"`([A-Za-z0-9_./\u4e00-\u9fff-]+\.(?:md|yaml|py|ps1))`")

# ── 红线③机器化（v3.5.0 / P0-1）───────────────────────────────────────────────
# 基础设施例外路径：SKILL.md「工作区边界」节列的三个例外，**不算越界**，故自动豁免。
# 用「路径片段」而非完整前缀匹配：例外表的根是 `~`（用户级），而交付物写的是盘符绝对路径，
# 安装位置可迁，硬编码 `C:\Users\<名>\.workbuddy\...` 会在换机后失效（那种判据一改环境就假红）。
INFRA_EXCEPTIONS = (
    "/.workbuddy/skills/",
    "/.workbuddy/binaries/python/envs/ai-workflow/",
    "/.workbuddy/cache/ai-workflow/",
)
SCOPE_AUTH_KEY = "越界授权"
SCOPE_HINT = ("（相对路径以 --base 为基准，故越界只可能来自绝对路径或 `..` 上跳；"
              "确需在工作区根之外产出时，须先取得用户**当次**授权并登记 `meta.越界授权`）")

results: list[tuple[str, str, str]] = []  # (状态, 检查项, 说明)

# 四种状态的行首标记。**一处定义**（原先两份字面量分别写在两个打印分支里，
# 加 WARN 时必须同时改两处 —— 这正是"复制粘贴漏改"最容易命中的形状）。
MARKS = {"OK": "[ OK ]", "FAIL": "[FAIL]", "SKIP": "[SKIP]", "WARN": "[WARN]"}


def ok(item: str, note: str = "") -> None:
    results.append(("OK", item, note))


def fail(item: str, note: str = "") -> None:
    results.append(("FAIL", item, note))


def skip(item: str, note: str = "") -> None:
    results.append(("SKIP", item, note))


def warn(item: str, note: str = "") -> None:
    """WARN（v3.5.0）：**只提示，不计入 FAIL、不改变退出码**。

    用途是给"首版不稳、或线索还不构成判据"的检查一个不误伤的位置 —— 首版就上 FAIL 的
    门禁，一旦判据不成立就会变成随机 FAIL 源，进而被整体绕过（见 security-guide.md §九 末条）。
    """
    results.append(("WARN", item, note))


def result_line() -> str:
    """汇总行。**四个计数分开写**，不写"X/Y 通过" —— 那种写法会把 WARN 和 SKIP 混进
    "通过"里，读者只盯 FAIL=0 就会把"没查"当成"查过了"（本工作区已复现过该误读：
    读 FAIL=0 时必须连带读"已完成 N 个"）。`FAIL=` 子串保持原样，外部脚本仍可解析。
    """
    n = {k: sum(1 for r in results if r[0] == k) for k in MARKS}
    return (f"=== 结果：通过 {n['OK']}/{len(results)}，FAIL={n['FAIL']}，"
            f"SKIP={n['SKIP']}，WARN={n['WARN']} ===")


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
            if ref in seen or REF_PLACEHOLDER.search(ref):
                continue
            seen.add(ref)
            if _resolve(ref, skill_dir) is not None:
                continue  # 技能内文件，已确认存在
            # 走到这里说明按技能内四个位置都找不到。若不是已知的跨根引用，就是真断链。
            # ⚠️ 顺序要紧：**先解析、后判前缀/白名单** —— 反过来会让技能内同名路径被前缀规则误放行。
            if ref in REF_WHITELIST or ref.startswith(REF_EXTERNAL_PREFIXES):
                continue
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
    # ⭐ v3.4.0 / P1：**不要"为了清理而先产生"** —— 把 .pyc 写到**系统临时目录**，
    # 从根上不产生 `scripts/__pycache__`，原先的清理逻辑随之取消。
    #   为什么必须改：`py_compile.compile(str(py))` 默认把 .pyc 写进脚本同目录的
    #   `__pycache__`，于是自检每轮都"先造 10 个文件、再 rmtree 删掉它们"。而本机
    #   `PYTHONPATH` 注入的 shim（`…\cli\vendor\shim`）会把**非临时目录**的 rmtree
    #   改走回收站（spawn 子进程）—— 受控实验：同一个 rmtree 删 8 个 4KB 文件，按父目录
    #   分别为 19.5 / 564.2 / 855.8 ms（43.9×）。实测本机 legacy 路径 = 产生 121 ms +
    #   清理 708 ms = 829 ms；改 `cfile` 后 87 ms 且零残留（原始数据见
    #   `.workbuddy/tmp/perf_baseline_*.json` 与 `rm.txt`）。
    #   诚实标注：该收益**依环境而变**（裸终端里同一个 rmtree 只要 ≈19 ms），
    #   但"不产生"在任何环境下都只有好处、没有坏处。
    with tempfile.TemporaryDirectory(prefix="aiwf_pyc_") as pyc_dir:
        for py in pyfiles:
            try:
                py_compile.compile(str(py), cfile=str(Path(pyc_dir) / (py.stem + ".pyc")), doraise=True)
                ok(f"py_compile：{py.name}")
            except py_compile.PyCompileError as e:
                fail(f"py_compile：{py.name}", str(e).splitlines()[0][:120])
    # 兜底：清掉**历史遗留**的 `__pycache__`（本版不主动造，但旧版本可能已经留下）。
    # 用逐文件 unlink 而非递归 rmtree —— ① shim 只劫持 `shutil.rmtree`，unlink 不受影响；
    # ② 目标只是"别留下垃圾"，**扩大删除面与优化目标相反**。
    cache = skill_dir / "scripts" / "__pycache__"
    if cache.exists():
        for f in sorted(cache.iterdir(), reverse=True):
            try:
                f.rmdir() if f.is_dir() else f.unlink()
            except OSError:
                pass
        try:
            cache.rmdir()
        except OSError:
            pass

    # v3.5.0 / P0-3：口径守卫 —— 手册/模板里写的取值必须与代码常量同源。放在最后，
    # 因为前面几项都是"代码自身"的完整性判据，这一项是"文档 ↔ 代码"的一致性判据。
    _check_parity(skill_dir)
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
        print("        %USERPROFILE%\\.workbuddy\\binaries\\python\\envs\\ai-workflow\\Scripts\\python.exe checks.py ...",
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


def _check_autonomy(meta: dict) -> None:
    """自主决策层留痕校验（v3.0.0）：字段**可选**，但一旦填写必须结构完整。

    设计取舍（与熔断机制同源）：不强制每个任务都产生决策记录 —— 纯本地读写的任务
    本就无外部辅助，"没写"是正常状态；此处只校验"写了的是否合法"。这样既不误伤
    历史 plan（无这些字段 → 判为未使用），也不给新 plan 添空表单负担。
    """
    dec = meta.get("决策记录")
    if dec is None or (isinstance(dec, list) and not dec):
        ok("决策记录", "未使用（无外部辅助引入，属正常）")
    elif not isinstance(dec, list):
        fail("决策记录格式", f"应为列表（每项必含 {'/'.join(DECISION_KEYS)}；时间由工具自动填）")
    else:
        bad = []
        for i, d in enumerate(dec, 1):
            if not isinstance(d, dict):
                bad.append(f"第{i}项非映射")
                continue
            miss = [k for k in DECISION_KEYS if not str(d.get(k, "") or "").strip()]
            if miss:
                bad.append(f"第{i}项缺 {'、'.join(miss)}")
            cap = str(d.get("能力类", "") or "").strip()
            if cap and cap not in VALID_CAPABILITY:
                bad.append(f"第{i}项能力类『{cap}』不在 {VALID_CAPABILITY}")
        (ok if not bad else fail)("决策记录", f"{len(dec)} 条" if not bad else "；".join(bad))

    rev = meta.get("计划修订")
    if rev is None or (isinstance(rev, list) and not rev):
        ok("计划修订", "未使用（未发生重规划）")
    elif not isinstance(rev, list):
        fail("计划修订格式", f"应为列表（每项必含 {'/'.join(REVISION_KEYS)}）")
    else:
        bad = []
        for i, r in enumerate(rev, 1):
            if not isinstance(r, dict):
                bad.append(f"第{i}项非映射")
                continue
            miss = [k for k in REVISION_KEYS if not str(r.get(k, "") or "").strip()]
            if miss:
                bad.append(f"第{i}项缺 {'、'.join(miss)}")
            t = str(r.get("触发", "") or "").strip()
            if t and t not in VALID_TRIGGER:
                bad.append(f"第{i}项触发『{t}』不在 {VALID_TRIGGER}")
        if len(rev) > MAX_REVISIONS:
            bad.append(f"修订 {len(rev)} 次 > 上限 {MAX_REVISIONS}（应停下与用户重新对齐目标）")
        (ok if not bad else fail)("计划修订", f"{len(rev)} 条" if not bad else "；".join(bad))


SELFTOOL_MARKERS = ("[自研工具]", "[自研技能]")

# ⚠️ 只扫**代码脚本**。文档类（`.md`/`.markdown`/`.txt`/`.yaml`/`.yml`/`.json`）一律不参与：
# 标注头在本技能族里是**必须在文档中写出示例**的格式（`references/push-routing.md` 的标注模板、
# `ops.md` 的脚本文档表、`assets/plan-template.yaml` 的字段注释），把这些「为说明格式而写出的
# 标记字符串」判成漏登记，会把门禁变成假的 —— 且会让人不敢在文档里引用这个标记。
# 与 `scripts/push_router.py` 的 `scan_selftool_header` **刻意同口径、同收窄**（两处判据不一致
# 本身就是本技能点名的病灶）。
# ⭐ 本轮实测教训（自撞缺陷，v3.4.0 只修了一半）：v3.4.0 的「缺陷一」把 `.md` 排除掉了，却**漏了
# `.yaml`**，于是 `assets/plan-template.yaml` 里一句注释中的 `[自研工具]` 同时被判成「漏登记」——
# `checks.py` 出 WARN、`push_router.py` 出 FAIL（会阻塞推送）。**同一条理由必须对整个文档类生效，
# 而不是只对上一次被投诉的那个后缀生效**；按后缀逐个打补丁，就是等着下一次换个后缀再犯一遍。
CODE_EXT = (".py", ".ps1", ".sh", ".bat", ".js", ".ts")


def _selftool_marker_in(path: Path) -> tuple[str, str] | None:
    """检出文件是否带自研标注头；命中返回 `(标记, 名称)`，否则 None。

    · `SKILL.md` 走 **frontmatter 分支**（技能包），名称取 frontmatter 的 `name` ——
      与 `push_router.scan_selftool_header` 的技能包分支一致。按 name 比对是必须的：总账里该技能
      记为 `ai-workflow（技能本体）`，而 basename `SKILL.md` 与它不可能字符串相等，
      按 basename 查会得到**永久假告警**（`_selftool_registered` 会按「（」截断后比对）。
    · 其余**非代码后缀直接返回 None**（理由见 `CODE_EXT` 上方注释）。
    · 代码脚本只认**前 40 行内的注释行**（`#`/`//`/`/*`/`*`/`--`），避免正文提到标记即命中。
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw[:4096]:
        return None
    text = raw.decode("utf-8", "replace")

    if path.name == "SKILL.md" and text.startswith("---"):
        end = text.find("\n---", 3)
        fm = text[3:end] if end > 0 else text[:2000]
        if re.search(r"^\s*selfbuilt\s*:\s*true\s*$", fm, re.M):
            m = re.search(r"^\s*name\s*:\s*(\S+)", fm, re.M)
            return "[自研技能]", (m.group(1).strip("\"'") if m else path.parent.name)
        return None

    if path.suffix.lower() not in CODE_EXT:
        return None

    for line in text.splitlines()[:40]:
        s = line.strip()
        if not (s.startswith("#") or s.startswith("//") or s.startswith("/*")
                or s.startswith("*") or s.startswith("--")):
            continue
        for m in SELFTOOL_MARKERS:
            if m in s:
                nm = re.search(r"\[自研[^\]]*\]\s*(\S+)", line)
                return m, (nm.group(1) if nm else path.stem)
    return None


def _selftool_scan_candidates(steps: list, base: Path) -> list[Path]:
    """扫描面 = **本任务的交付物**里已存在的**代码脚本**（后缀见 `CODE_EXT`）。

    ⚠️ **范围取舍（显式声明，不是默默收窄）**：
    · 不递归、不扫 `tasks/*/tmp/`。理由是 `tmp/` 属探针与中间产物，且 `.gitignore` 已排除它
      → **它不会外发**，与「公开留痕」无关；纳入它只会让门禁在自测时被夹具替身误报
      （本工作区正是拿夹具自测流程的）。
    · **文档类不进扫描面**（`.md`/`.txt`/`.yaml`/`.yml`/`.json`）—— 理由见 `CODE_EXT` 上方注释。
    """
    seen: set[str] = set()
    out: list[Path] = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        for tok in _step_tokens(s):
            if not _is_file_like(tok):
                continue
            for cand in _candidate_paths(tok, base):
                rel = str(cand).replace("\\", "/").lower()
                if "/tmp/" in rel or rel in seen or not cand.is_file():
                    continue
                if cand.suffix.lower() not in CODE_EXT:
                    continue
                seen.add(rel)
                out.append(cand)
    return out


_SELFTOOL_LEDGER_CACHE: dict[str, list] = {}


def _selftool_ledger(base: Path) -> list:
    """**自研工具登记总账** = 本工作区全部 `tasks/**/plan.yaml` 的 `meta.自研工具` 合并。

    为什么必须查总账而不是只查本任务的表（本轮实测教训）：
    自研工具的登记发生在**创建它的那次任务**里，后续任务**修改**它时不会再登记一遍。
    只查本任务表 → 每个碰到既有工具的任务都会报一次假告警（实测：`push_router.py` 在 v3.2.0
    已登记，本任务只是改了它，却被判「未登记」）。门禁真正要抓的是
    「**任何登记表里都找不到**」，那才是漏登记。

    排除 `*/tmp/*`（探针伪造的假登记）与 `_backup-*`（历史快照，不是登记）；按 base 缓存。
    """
    key = str(base).replace("\\", "/").lower()
    if key in _SELFTOOL_LEDGER_CACHE:
        return _SELFTOOL_LEDGER_CACHE[key]
    yaml = _require_yaml()
    items: list = []
    tasks = base / "tasks"
    if tasks.is_dir():
        for pp in sorted(tasks.rglob("plan.yaml")):
            rel = pp.relative_to(base).as_posix()
            if "/tmp/" in rel or rel.startswith("_backup") or "/_backup" in rel:
                continue
            try:
                data = yaml.safe_load(pp.read_text(encoding="utf-8-sig"))
            except Exception:            # noqa: BLE001 - 单份 plan 读不了不应中断总账汇总
                continue
            if isinstance(data, dict):
                got = (data.get("meta") or {}).get("自研工具")
                if isinstance(got, list):
                    items.extend(x for x in got if isinstance(x, dict))
    _SELFTOOL_LEDGER_CACHE[key] = items
    return items


def _selftool_registered(name: str, items: list) -> bool:
    """登记表里能否找到该文件（先按名称，再按登记链接的仓内路径 basename）。"""
    base = Path(name).name.lower()
    for it in items:
        if not isinstance(it, dict):
            continue
        nm = str(it.get("名称", "") or "").strip().split("（")[0].strip().lower()
        if nm and nm == base:
            return True
        m = re.search(r"/blob/[^/]+/(.+?)(?:[?#].*)?$", str(it.get("仓库链接", "") or ""))
        if m and Path(m.group(1)).name.lower() == base:
            return True
    return False


def _check_selftools(meta: dict, steps: list | None = None, base: Path | None = None) -> None:
    """自研工具与技能留痕校验（v3.1.0）：字段**可选**，一旦填写必须结构完整。

    与 `_check_autonomy` 同口径 —— 多数任务本就没有自研产出，"没写"是正常状态；
    此处只校验"写了的是否合法"：四项必填非空 + 仓库链接须为真实 http(s) 地址
    （占位符判 FAIL；『待推送』判 SKIP 并明确提示，因为它是中间态而非完成态）。

    v3.5.0 / P1-1 增补：**反向检测**（交付物带标注头却未登记 → WARN）与**文案订正**。
    订正的依据是一次真实误读：原文案写"未使用（本任务无自研产出，**属正常**）"，读起来像
    "已验证本任务无自研产出"，但旧实现**根本没有扫过任何代码** —— 它只是没读到登记项。
    「无登记」不等于「无自研产出」，这句话必须说出来，否则这条判据会被当成"已验证"。
    """
    items = meta.get("自研工具")
    if items is None:
        items = []
    if not isinstance(items, list):
        fail("自研工具格式", f"应为列表（每项必含 {'/'.join(SELFTOOL_KEYS)}）")
        return

    bad, pending = [], []
    for i, t in enumerate(items, 1):
        if not isinstance(t, dict):
            bad.append(f"第{i}项非映射")
            continue
        miss = [k for k in SELFTOOL_KEYS if not str(t.get(k, "") or "").strip()]
        if miss:
            bad.append(f"第{i}项缺 {'、'.join(miss)}")
            continue
        url = str(t.get("仓库链接", "") or "").strip()
        if url == SELFTOOL_PENDING:
            pending.append(f"第{i}项『{str(t.get('名称', '')).strip() or '-'}』")
            continue
        if not re.match(r"^https?://", url) or SELFTOOL_PLACEHOLDER.search(url):
            bad.append(f"第{i}项仓库链接『{url[:40]}』非法：须为 http(s) 真实地址、禁止占位符"
                       f"（未推送前可填『{SELFTOOL_PENDING}』，但交付前必须回填）")

    # 反向检测：交付物里的自研标注头 ↔ **本 plan 的登记表 ∪ 全工作区登记总账**
    # ⚠️ 两侧都不能少（本轮被夹具的阴性对照抓到过）：只查总账 → 落在 `tasks/*/tmp/` 里的 plan
    # 自己的登记会被总账排除（总账刻意不读 tmp，因为那是探针伪造假登记的地方），
    # 于是「刚补登记却仍报警」；只查本 plan → 见 _selftool_ledger 的说明（既有工具被误判）。
    unreg: list[str] = []
    if steps is not None and base is not None:
        ledger = list(items) + _selftool_ledger(base)
        for p in _selftool_scan_candidates(steps, base):
            hit = _selftool_marker_in(p)
            if hit and not _selftool_registered(hit[1], ledger):
                unreg.append(f"{p.name}{hit[0]}")

    if bad:
        fail("自研工具登记", "；".join(bad))
    elif pending:
        skip("自研工具登记", f"{len(items)} 项，其中 {len(pending)} 项链接仍为『{SELFTOOL_PENDING}』"
                            f"（{'、'.join(pending)}）—— 交付前须回填真实仓库链接")
    elif items:
        ok("自研工具登记", f"{len(items)} 项")
    else:
        ok("自研工具登记", "未登记 —— ⚠️ 这是「**未检测**」不是「**已验证无自研**」：本判据只比对"
                           "**本任务交付物**里的自研标注头，且只扫**代码脚本**（不含 `tasks/*/tmp/`、"
                           "不遍历全盘代码、不扫文档类）；**未入交付物的自写脚本不会被发现**")

    if unreg:
        warn("自研工具漏登记", f"检出 {len(unreg)} 个带自研标注头、且**全工作区登记总账里都查不到**的交付物："
                               f"{'、'.join(unreg[:4])} —— 用 `checks.py selftool` 补登记后本告警消失"
                               f"（查表范围 = 本工作区所有 `tasks/**/plan.yaml` 的 `meta.自研工具`；"
                               f"只扫代码脚本，文档类不参与 —— 理由见 `CODE_EXT` 注释。此处只 WARN："
                               f"标注头是线索、登记才是判据，且推送前还有一道 FAIL 级交叉校验）")


def _yaml_scalar(s: str) -> str:
    """把任意字符串写成安全的 YAML 双引号标量（JSON 字符串即合法 YAML flow 标量）。"""
    return json.dumps(s, ensure_ascii=False)


def _append_meta_list(plan_path: Path, key: str, item_lines: list[str]) -> bool:
    """向 meta.<key> 追加列表项（块式 YAML），保留文件其余内容与注释。

    走**就地行操作**而非 yaml.dump —— 与 `_set_meta_fuse` / `cmd_mark` 同一风格：
    整份 dump 会吃掉 plan.yaml 里所有注释与键序，那才是真正的信息损失。
    """
    lines = plan_path.read_text(encoding="utf-8").splitlines(keepends=True)
    key_re = re.compile(rf"^  {re.escape(key)}\s*:(.*)$")
    in_meta, key_idx, meta_end = False, None, None
    for i, ln in enumerate(lines):
        if re.match(r"^meta\s*:\s*$", ln):
            in_meta = True
            continue
        if not in_meta:
            continue
        if re.match(r"^\S", ln):  # 顶层键 → meta 块结束
            meta_end = i
            break
        if key_re.match(ln):
            key_idx = i
    if meta_end is None:
        meta_end = len(lines)

    if key_idx is None:  # meta 内无该键 → 插到 meta 末尾
        lines[meta_end:meta_end] = [f"  {key}:\n"] + item_lines
        plan_path.write_text("".join(lines), encoding="utf-8")
        return True

    # 已有该键：识别 `[]` 占位（可能带行尾注释），并跳到列表块末尾
    val = lines[key_idx].split(":", 1)[1].split("#", 1)[0].strip()
    if val == "[]":
        # 只移除 `[]` 占位，保留该行注释
        lines[key_idx] = re.sub(r"(:\s*)\[\]", r"\1", lines[key_idx], count=1)
        insert_at = key_idx + 1
    else:
        insert_at = key_idx + 1
        while insert_at < meta_end and (not lines[insert_at].strip()
                                        or lines[insert_at].startswith("    ")):
            insert_at += 1
    lines[insert_at:insert_at] = item_lines
    plan_path.write_text("".join(lines), encoding="utf-8")
    return True


def cmd_decide(plan_path: Path, point: str, basis: str,
               capability: str | None, choice: str | None) -> int:
    """追加一条能力决策记录（自主决策层留痕，v3.0.0）。"""
    if capability not in VALID_CAPABILITY:  # argparse choices 已兜一层，此处再防一次
        fail("能力类合法", f"『{capability}』不在 {VALID_CAPABILITY}")
        return 1
    if not (point or "").strip() or not (basis or "").strip() or not (choice or "").strip():
        fail("参数", "必须给出 --point（决策点）、--basis（依据）与 --choice（选择）")
        return 1
    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    item = [
        f"    - 决策点: {_yaml_scalar(point)}\n",
        f"      能力类: {_yaml_scalar(capability or '')}\n",
        f"      依据: {_yaml_scalar(basis)}\n",
        f"      选择: {_yaml_scalar(choice or '')}\n",
        f"      时间: {_yaml_scalar(ts)}\n",
    ]
    if not _append_meta_list(plan_path, "决策记录", item):
        fail("meta.决策记录 写入", "未找到 `meta:` 块，请手工添加该键")
        return 1
    ok("决策记录已追加", f"能力类={capability or '-'}；决策点={point[:40]}")
    return 0


def cmd_revise(plan_path: Path, trigger: str, change: str,
               unchanged: str | None) -> int:
    """追加一条计划修订（重规划留痕，v3.0.0）；超上限 FAIL 并提示重新对齐目标。"""
    if trigger not in VALID_TRIGGER:
        fail("触发编号合法", f"『{trigger}』不在 {VALID_TRIGGER}")
        return 1
    if not (change or "").strip():
        fail("参数", "必须给出 --change（变化摘要）")
        return 1
    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1
    yaml = _require_yaml()
    try:
        data = yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        fail("plan.yaml 可解析", str(e).splitlines()[0][:120])
        return 1
    cur = (data.get("meta") or {}).get("计划修订") or []
    if not isinstance(cur, list):
        fail("meta.计划修订 格式", "应为列表")
        return 1
    if len(cur) >= MAX_REVISIONS:
        fail("计划修订上限", f"已有 {len(cur)} 条，上限 {MAX_REVISIONS}：说明初始拆解方法有问题"
                             "或该任务不适合线性计划，应停下与用户重新对齐目标（这是重新澄清，非熔断）")
        return 1
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    ver = f"v{len(cur) + 1} → v{len(cur) + 2}"
    item = [
        f"    - 版本: {_yaml_scalar(ver)}\n",
        f"      触发: {_yaml_scalar(trigger)}\n",
        f"      时间: {_yaml_scalar(ts)}\n",
        f"      变化: {_yaml_scalar(change)}\n",
        f"      未变: {_yaml_scalar(unchanged or '')}\n",
    ]
    if not _append_meta_list(plan_path, "计划修订", item):
        fail("meta.计划修订 写入", "未找到 `meta:` 块，请手工添加该键")
        return 1
    ok("计划修订已追加", f"第 {len(cur) + 1}/{MAX_REVISIONS} 条；触发={trigger}")
    return 0


def cmd_selftool(plan_path: Path, name: str, purpose: str, scenario: str, repo: str) -> int:
    """追加一条自研工具/技能登记到 meta.自研工具（v3.1.0 公开留痕）。

    四项参数均必填 —— 与 `decide` 同口径：登记的价值在于"事后能查到它是什么、
    从哪来"，缺任何一项都会让留痕退化成走过场。
    """
    if not all((x or "").strip() for x in (name, purpose, scenario, repo)):
        fail("参数", "必须给出 --name（名称）、--purpose（用途）、--scenario（适用场景）与 --repo（仓库链接）")
        return 1
    if plan_path.is_dir():
        plan_path = plan_path / "plan.yaml"
    if not plan_path.exists():
        fail("plan.yaml 存在", str(plan_path))
        return 1
    item = [
        f"    - 名称: {_yaml_scalar(name)}\n",
        f"      用途: {_yaml_scalar(purpose)}\n",
        f"      适用场景: {_yaml_scalar(scenario)}\n",
        f"      仓库链接: {_yaml_scalar(repo)}\n",
    ]
    if not _append_meta_list(plan_path, "自研工具", item):
        fail("meta.自研工具 写入", "未找到 `meta:` 块，请手工添加该键")
        return 1
    ok("自研工具已登记", f"{name}；仓库={repo[:48]}")
    return 0


# ── 红线③机器化（v3.5.0 / P0-1）──────────────────────────────────────────────
def _norm_abs(p) -> str:
    """归一为「绝对、小写、正斜杠、无尾斜杠」串，用于跨写法比较（`C:\\A` / `c:/a/` 视为同一路径）。"""
    try:
        s = str(Path(p).expanduser().resolve())
    except (OSError, RuntimeError):
        s = str(p)
    return s.replace("\\", "/").rstrip("/").lower()


def _under(child: str, parent: str) -> bool:
    return bool(parent) and (child == parent or child.startswith(parent + "/"))


def _step_tokens(s: dict) -> list[str]:
    """与 audit_step 同一套切分口径（花括号展开 → 分隔符切分 → 剥括号注释）。"""
    raw = str(s.get("交付物", "") or "").strip()
    out: list[str] = []
    for variant in _expand_braces(raw):
        out.extend(_clean_token(t) for t in re.split(r"[、,;；]|\s／\s", variant) if t.strip())
    return out


def _check_scope(meta: dict, steps: list, base: Path) -> None:
    """交付物越界判据（v3.5.0 / P0-1）：把红线③从**纪律**变成**门禁**。

    判据：交付物解析后的绝对路径落在 `meta.工作区根` 之外，且既不在 `meta.越界授权` 登记的
    白名单内、也不属基础设施例外 → FAIL。

    ⚠️ **旧模板只警示不阻断**（关键设计，非妥协）：plan 里没有 `越界授权` 键说明它早于
    v3.3.0 的模板 —— 那种 plan 里出现根外交付物是**历史事实**，用新判据去追认它，等于拿新
    规则改写旧证据（技能在 P9-c 已立此口径：改历史记录去迁就新门禁是**为新判据篡改证据**）。
    故：无该键 → WARN 并列明；有该键（哪怕是空列表）→ 严格执行 FAIL。
    """
    root_txt = str(meta.get("工作区根", "") or "").strip()
    root = _norm_abs(Path(root_txt)) if root_txt else _norm_abs(base)
    allowed: list[str] = []
    auth = meta.get(SCOPE_AUTH_KEY)
    if isinstance(auth, list):
        for it in auth:
            if isinstance(it, dict):
                v = str(it.get("路径", "") or "").strip()
                if v:
                    allowed.append(_norm_abs(Path(v)))
    has_key = SCOPE_AUTH_KEY in meta

    outside, authed = [], []
    for s in steps:
        if not isinstance(s, dict):
            continue
        for tok in _step_tokens(s):
            if not _is_file_like(tok):
                continue
            for cand in _candidate_paths(tok, base):
                n = _norm_abs(cand)
                if _under(n, root) or any(x in n for x in INFRA_EXCEPTIONS):
                    continue
                rec = (s.get("id", "?"), tok, str(cand))
                (authed if any(_under(n, a) for a in allowed) else outside).append(rec)

    if not outside:
        note = "全部落在工作区根内（或属基础设施例外）"
        if authed:
            note = f"根外 {len(authed)} 项，均在 meta.{SCOPE_AUTH_KEY} 登记范围内"
        ok("交付物越界检查", note)
        return
    detail = "；".join(f"步骤 {i}『{t}』→ {p}" for i, t, p in outside[:4])
    if not has_key:
        warn("交付物越界检查", f"{len(outside)} 项落在工作区根 {root} 之外，但本 plan 无"
                               f"『{SCOPE_AUTH_KEY}』键（早于 v3.3.0 的旧模板）→ 只警示不阻断：{detail}{SCOPE_HINT}")
        return
    fail("交付物越界检查", f"{len(outside)} 项越界且未获授权：{detail}{SCOPE_HINT}")


# ── 口径守卫（v3.5.0 / P0-3）──────────────────────────────────────────────────
# 每个量 = (判据名, 来源文件, 解析函数, 代码内常量)。**解析函数刻意各写一个**——
# 五个量的字面格式完全不同（表格单元格 / 注释行 / 圆括号后辍），套一个通用正则必然过脆；
# 但每个都锚在**结构化位置**（行首一列的加粗词、`取值:` 之后的枚举），不做自由文本搜索。
def _p_tiers(text: str) -> set:
    """routing-guide.md 档位表首列：`| **strong** | …`。"""
    return set(re.findall(r"^\|\s*\*\*([a-z]+)\*\*\s*\|", text, re.M))


def _p_status(text: str) -> set:
    """plan-template.yaml 注释行：`# status 取值: 待办 / 进行中 / …`。"""
    m = re.search(r"^#\s*status\s*取值\s*[:：]\s*(.+)$", text, re.M)
    return {x.strip() for x in re.split(r"[/／]", m.group(1)) if x.strip()} if m else set()


def _p_caps(text: str) -> set:
    """capability-routing.md 能力表首列：`| ① | **知识** | …` —— 剥掉『（隔离）』这类后辍。"""
    return {m.strip() for m in re.findall(r"^\|\s*[①②③④]\s*\|\s*\*\*([^*（(]+)", text, re.M)}


def _p_triggers(text: str) -> set:
    """adaptive-planning.md 触发表首列：`| **R1** | …`。"""
    return set(re.findall(r"^\|\s*\*\*(R\d)\*\*\s*\|", text, re.M))


def _p_fuse(text: str) -> set:
    """SKILL.md 熔断状态表：`| \\`正常\\` | 存储态 | …` —— 只取「存储态」行，
    刻意排除同表里「复位 = 迁移动作」那行（复位不是存储态，这正是该节反复强调的一点）。"""
    return set(re.findall(r"^\|\s*`([^`]+)`\s*\|\s*存储态\s*\|", text, re.M))


PARITY_ITEMS = (
    ("模型档位", "references/routing-guide.md", _p_tiers, VALID_MODEL_TIERS),
    ("步骤状态", "assets/plan-template.yaml", _p_status, VALID_STATUS),
    ("能力类", "references/capability-routing.md", _p_caps, VALID_CAPABILITY),
    ("重规划触发", "references/adaptive-planning.md", _p_triggers, VALID_TRIGGER),
    ("熔断状态", "SKILL.md", _p_fuse, VALID_FUSE),
)


def _check_parity(skill_dir: Path) -> None:
    """口径守卫（v3.5.0 / P0-3）：断言「手册/模板里写的取值 == 代码内常量」。

    存在意义：`VALID_MODEL_TIERS` 的旧注释写着"与 routing-guide.md 的 enum **同源**"，但
    **同源是靠注释声明的、不是靠测试保证的** —— 改一处忘一处不会抛异常，只会静默分叉。
    本条把该声明变成可机器判定的断言（技能库卫生第 4 条"同一物理量的判据必须跨模块同源
    + 配守卫测试"的落地；该条自 v3.3.0 起已扩展到全流程适用）。

    解析不到即 FAIL：**守着一条读不到的规则等于没有规则**，且"读不到"必须显式，不能静默降级成 OK。
    阴性对照（验收用）：把 `routing-guide.md` 的 `cheap` 改成 `cheapx` → 本判据必须变红。
    """
    cache: dict[Path, str] = {}
    for label, rel, parser, expected in PARITY_ITEMS:
        p = skill_dir / rel
        if p not in cache:
            try:
                cache[p] = p.read_text(encoding="utf-8") if p.exists() else ""
            except OSError:
                cache[p] = ""
        text = cache[p]
        if not text:
            fail(f"口径守卫：{label}", f"源文件缺失或读不到：{rel}（守卫读不到规则 = 没有规则）")
            continue
        got = parser(text)
        want = set(expected)
        if not got:
            fail(f"口径守卫：{label}", f"在 {rel} 中解析不到取值定义（格式可能已变；守卫读不到规则 = 没有规则）")
        elif got != want:
            fail(f"口径守卫：{label}", f"{rel} 解析得 {'/'.join(sorted(got))} ≠ 代码常量 {'/'.join(sorted(want))}"
                                      f"（同一物理量两处不同源 —— 要么统一，要么显式声明二者关系）")
        else:
            ok(f"口径守卫：{label}", f"{rel} ↔ {'/'.join(sorted(want))}（{len(want)} 项一致）")


# ── 阶段 2 / 4 最低成本门禁（v3.5.0 / P2-2）───────────────────────────────────
STAGE2_STEP_RE = re.compile(r"方案评审|候选方案|方案对比|对比表|备选方案")
STAGE2_SIGNAL_RE = re.compile(r"(≥|>=|不少于|至少)\s*2|2\s*个\s*(候选|方案|备选)|方案\s*[AB一二]|候选\s*[AB]|横向对比|双跑")
STAGE4_EXT = (".docx", ".xlsx", ".pdf", ".pptx")
STAGE4_SIGNAL_RE = re.compile(r"口径|一致性|估算|写回|读回|office_io|交叉核对|抽\s*2\s*处|抽两处|抽查|脱敏")


def _check_stage_gates(steps: list) -> None:
    """阶段 2 / 4 的两条最低成本门禁（v3.5.0 / P2-2）：**只出 WARN**。

    背景（《报告》§5.3）：门禁密度实测 —— 阶段 2 与阶段 4 均为 **0 门禁**，而这两处恰是
    「决策质量的关键节点」与技能自认「最容易静默失真」处。原因不是"不该有"，是"没人去建"。

    ⚠️ **诚实标注（三条限制，别当成已验证的保护）**：
      ① 步骤没有"阶段"字段，故此处用**代理判据**（关键词 / 交付物后缀）推断它属哪一阶段；
      ② 它检的是**验证方式里有没有对应信号词**，不是"数值真的一致"—— 能挡住"忘了写"，挡不住"写了没做"；
      ③ **首版只 WARN、不判 FAIL**：判据尚未经受真实数据检验，直接上 FAIL 会造出随机 FAIL 源
         （security-guide.md §九 末条：门禁出问题绝大多数是**误判**而非漏判）。
    """
    g2, g4 = [], []
    for s in steps:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id", "?"))
        do = str(s.get("做什么", "") or "")
        ver = str(s.get("验证方式", "") or "")
        exp = str(s.get("预期产出", "") or "")
        deliv = str(s.get("交付物", "") or "").lower()
        if STAGE2_STEP_RE.search(do) and not STAGE2_SIGNAL_RE.search(ver + " " + exp):
            g2.append(sid)
        if any(e in deliv for e in STAGE4_EXT) and not STAGE4_SIGNAL_RE.search(ver):
            g4.append(sid)
    if g2:
        warn("阶段 2 门禁（方案评审 ≥2 候选）",
             f"步骤 {'、'.join(g2)} 提到方案评审，但「验证方式/预期产出」里读不到「≥2 候选」的可判定信号"
             f" —— 补信号，或写明为何只有一条路（本判据首版只 WARN）")
    if g4:
        warn("阶段 4 门禁（数值口径 / 估算标注 / 脱敏）",
             f"步骤 {'、'.join(g4)} 产出 Office 类交付物，但「验证方式」里读不到口径一致 / 估算标注 / "
             f"写回读回 / 脱敏类信号 —— 这三条正是流程自认最易静默失真处（本判据首版只 WARN）")


def _check_model_tiers(steps: list) -> None:
    """校验每步 `模型档位` 的取值（P9-c，v3.4.0）。

    与 `_check_autonomy` / `_check_selftools` **同口径**：字段可选，**留空即合法**；
    但一旦填了，就必须在 `VALID_MODEL_TIERS` 内 —— 否则"填了"只是装饰，无法参与成本核对。

    ⚠️ 为什么把 `default` 收进合法集而不是改写历史 plan：真实数据（v3.2.0 的 plan.yaml）里
    就有 `default`。改历史记录去迁就新门禁，等于**为新判据篡改证据**；正解是把 `default`
    定义为「显式声明按阶段默认档位」并写进 `plan-template.yaml` 与 `routing-guide.md`，
    让**文档与实际用法一致**。门禁只拦真正的越界值（如拼错的 `cheep`、`fast`）。
    """
    bad, seen = [], []
    for i, s in enumerate(steps, 1):
        if not isinstance(s, dict):
            continue
        v = str(s.get("模型档位", "") or "").strip()
        if not v:
            continue
        seen.append(v)
        if v not in VALID_MODEL_TIERS:
            bad.append(f"步骤 {s.get('id', i)}={v!r}")
    if bad:
        fail("模型档位合法", "非法取值：" + "；".join(bad) + f"（合法：{'/'.join(VALID_MODEL_TIERS)}；留空=跳过）")
    else:
        ok("模型档位合法", f"{len(seen)} 步已标注，取值均在 enum 内" if seen else "步骤均未标注（字段可选）")


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

    _check_scope(meta, steps, base)
    _check_autonomy(meta)
    _check_selftools(meta, steps, base)
    _check_stage_gates(steps)
    _check_model_tiers(steps)
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

    p = sub.add_parser("decide", help="追加一条能力决策记录到 meta.决策记录（自主决策层留痕）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("--point", required=True, help="决策点：这一步缺什么/要决定什么")
    p.add_argument("--basis", required=True, help="依据：一句话判据（说不出可验证收益就别引入）")
    p.add_argument("--capability", required=True, choices=VALID_CAPABILITY, help="能力类：知识/算力/事实/手脚")
    p.add_argument("--choice", required=True, help="选择：实际引入的具体手段")

    p = sub.add_parser("revise", help="追加一条计划修订到 meta.计划修订（重规划留痕）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("--trigger", required=True, choices=VALID_TRIGGER, help="触发编号：R1–R6")
    p.add_argument("--change", required=True, help="变化摘要（改了什么）")
    p.add_argument("--unchanged", help="未变部分（已完成步骤是否受影响）")

    p = sub.add_parser("selftool", help="追加一条自研工具/技能登记到 meta.自研工具（公开留痕，v3.1.0）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("--name", required=True, help="名称：工具/技能叫什么")
    p.add_argument("--purpose", required=True, help="用途：一句话，它做什么")
    p.add_argument("--scenario", required=True, help="适用场景：什么情况该用；什么情况不该用")
    p.add_argument("--repo", required=True, help="仓库链接：http(s) 真实地址；尚未推送时填『待推送』（交付前须回填）")

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
    elif args.cmd == "mark":
        code = cmd_mark(Path(args.plan), args.step_id, args.status, args.fuse, args.batch)
        name = "状态更新"
    elif args.cmd == "decide":
        code = cmd_decide(Path(args.plan), args.point, args.basis, args.capability, args.choice)
        name = "决策留痕"
    elif args.cmd == "revise":
        code = cmd_revise(Path(args.plan), args.trigger, args.change, args.unchanged)
        name = "计划修订"
    else:  # selftool
        code = cmd_selftool(Path(args.plan), args.name, args.purpose, args.scenario, args.repo)
        name = "自研工具登记"

    if args.cmd in ("skill", "plan"):
        print(f"=== ai-workflow {name} ===")
        for status, item, note in results:
            print(f"{MARKS[status]} {item}" + (f" — {note}" if note else ""))
        n_fail = sum(1 for r in results if r[0] == "FAIL")
        if code != 0 and not results:
            # 环境/输入不满足，检查根本没跑起来 —— 绝不能输出"全绿"误导调用方
            print("=== 结果：未执行（环境或输入不满足，见上方 [ERROR]）===")
            return code
        print(result_line())
        return 1 if n_fail else code
    else:  # status / mark：表格/明细已即时打印，这里只回显结果行（status 的熔断汇总行在此可见）
        for status, item, note in results:
            print(f"{MARKS[status]} {item}" + (f" — {note}" if note else ""))
        n_fail = sum(1 for r in results if r[0] == "FAIL")
        return 1 if n_fail else code


if __name__ == "__main__":
    raise SystemExit(main())
