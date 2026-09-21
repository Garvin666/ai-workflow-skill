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
       消灭"同源只靠注释声明、不靠测试保证"。覆盖 7 个物理量：模型档位 / 步骤状态 / 能力类 /
       重规划触发 / 熔断状态 / 反思触发 / 终止策略。**解析不到即 FAIL**（守着一条读不到的规则等于没有规则）。
    7. 入口判定主类（v4.2.0）：**两半分开，各自的声明与各自的能力对齐** ——
       ① 确定性（FAIL）：`references/self-judge.md` §1 的「机器可读声明块」（一对 ASCII 标记圈定）
          须在**源规格面内恰一处**（源规格见 `CATEGORY_SOURCES`：`SKILL.md`＋`references/*.md`＋`assets/*.md`＋`assets/*.yaml`，**不递归**；技能根目录、`scripts/`、`references/` 子目录、`assets/*.txt`／`assets/templates/` **不在扫描面内**），块形合法（含「首格整格一个裸词」），块内取值集合须恰好等于 `VALID_CATEGORY`；
       ② 启发式（**WARN，不作门禁**）：源规格面内「主类疑似列」扫描，可疑取值只提示并附文件名+行号。
       ⚠️ v4.2.0 前四轮曾在①的位置用「全手册找表头 `| 主类 |`」的解析，被独立复核（未参与实现者）
          实测出 14 种假绿 + 2 种误报（含 §10 那一行被误判成表头）→ **前提不成立，改口径而非再加固正则**。

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
    12. 反思重试配置（v4.1.0）：meta「反思重试配置」可选，缺省即 SKIP（向后兼容旧 plan）；
        一旦填写必须结构合法（最大重试次数整数 ≥1 / 触发条件为 T1–T3 子集 /
        终止策略在枚举内），步骤级覆盖同口径；语义（重试是否真改了）不机器判定，靠抽查。
    13. 入口判定（v4.2.0）：meta「入口判定」可选 —— 阶段 0 第 1 步 self-judge 的产出，
        完整契约见 references/self-judge.md。**整段缺省 → WARN**（向后兼容旧 plan，
        **不追认历史计划**）；一旦填写须结构合法（category ∈ chat/code/content、
        distribution 恰含三键且和=1、confidence ∈ [0,1]、dimensions 含 D1–D5、
        route_hint 非空、ambiguity 为 bool、secondary 留空或在枚举内），非法即 FAIL。
        ⚠️ **它不是门禁**：confidence 由模型自填、校准无法被机器证明（手册 §10 原样写明）。

状态取值: OK / FAIL / SKIP / **WARN**（WARN 只提示、不计入 FAIL，也不改变退出码）

退出码: 0 = 全部通过；1 = 有 FAIL（不可交付）；2 = 用法错误
"""
import argparse
import ast
import json
import py_compile
import re
import subprocess
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
# 反思重试机制（v4.1.0）：触发条件 + 终止策略枚举。
# **唯一取值源**：本常量 + references/reflection-retry.md；二者经 PARITY_ITEMS 口径守卫同源
# （手册写的枚举 == 代码常量，解析不到即 FAIL）。触发条件缺省全开，终止策略缺省「升级返修复查」。
VALID_REFLECT_TRIGGER = ("T1", "T2", "T3")
VALID_TERMINATION = ("升级返修复查", "触发熔断", "升级用户决策", "重规划R")
# self-judge（v4.2.0）：主类枚举。**唯一取值源** = 本常量 + `references/self-judge.md` §1 的
# **机器可读声明块**；二者由 `_check_category_decl` 断言同源（读不到块 = FAIL）。
# ⚠️ 第五轮**换口径**（不是再加固正则）：前四轮用「全手册找表头 `| 主类 |`」的解析来做 FAIL，
# 被独立复核（未参与实现者）实测出 14 种假绿（表头 `**主类**（认知轴）` 组合写法、取值大写／
# 带连字符／全角／零宽字符、引用块 `>`、缺首尾竖线……）与 2 种误报，且 §10 描述守卫射程的那一行
# 因格内引用了 `| 主类 |` 而被**误判成表头**（哑雷）。
# **结论：从任意 markdown 表格里稳定提取枚举这个前提不成立。** 现口径两半：
#   ① FAIL（确定性）＝ 声明块须在**源规格面内**恰一处（见 CATEGORY_SOURCES，不递归）、块形合法（含「首格整格一个裸词」）、取值集合恰好等于本常量；
#   ② WARN（启发式，不作门禁）＝ 源规格面内「主类疑似列」的可疑取值，只提示 + 附文件名/行号。
VALID_CATEGORY = ("chat", "code", "content")
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


def _frontmatter(text: str) -> str:
    """取 YAML frontmatter 块（首对 `---` 之间的内容）；取不到返回空串。

    ⚠️ **不要退回「固定字符窗口」写法**（v4.3.0 实测教训）：本函数替代的是
    `read_text()[:800]`。`description` 是**刻意写长**的字段（能力概述 + 触发词清单），
    它一长就把后面的 key 推出窗口 —— 实测扩充 description 后 `agent_created:` 的偏移
    **恰为 800**，落在半开区间 `[0,800)` 之外，于是对**完全合法**的 frontmatter 报
    FAIL=1。边界只差 1 个字符，而报错文案（「frontmatter 含 agent_created」）指向的是
    **内容缺失**这一错误方向 —— 排查成本因此很高。
    **判据应作用于结构（frontmatter 块），不应作用于长度。**
    """
    m = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", text, re.S)
    return m.group(1) if m else ""


def check_skill(skill_dir: Path) -> int:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        fail("SKILL.md 存在", str(skill_md))
        return 1
    ok("SKILL.md 存在")

    fm = _frontmatter(skill_md.read_text(encoding="utf-8"))
    if not fm:
        fail("frontmatter 可解析",
             "未找到以 `---` 包裹的 frontmatter 块（首行须为 `---`，末行须为 `---`）")
    else:
        ok("frontmatter 可解析",
           f"{len(fm)} 字符 / {fm.count(chr(10)) + 1} 行（结构化取块，非字符窗口）")
        for key in ("name:", "description:", "agent_created:"):
            (ok if key in fm else fail)(f"frontmatter 含 {key.rstrip(':')}")

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
    # v4.2.0 第五轮：主类枚举单独判（声明块 FAIL + 启发式 WARN）—— 它的模型是「跨文件唯一性（源规格面内）」，塞不进 PARITY_ITEMS 的并集模型
    _check_category_decl(skill_dir)
    # v4.3.0 / 批次 B：平台门控 vs 真实 import（AST 口径，不认注释与字符串里的同名字面量）
    _check_platform(skill_dir)
    # v4.3.0 / 批次 C：运行时闸门可用性与同源（gate.py 缺失、或口径另存一份副本，均 FAIL）
    _check_gate(skill_dir)
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


def _p_reflect_trigger(text: str) -> set:
    """reflection-retry.md §2 触发表首列：`| **T1** | …`。"""
    return set(re.findall(r"^\|\s*\*\*(T\d)\*\*\s*\|", text, re.M))


def _p_reflect_term(text: str) -> set:
    """reflection-retry.md §4 终止策略表首列：`| **升级返修复查**（默认，推荐） | …`
    —— 加粗后可能接「（默认，推荐）」而非直接竖线，故只锚定行首 `| **枚举**`，不要求紧邻竖线。"""
    return set(re.findall(r"^\|\s*\*\*(升级返修复查|触发熔断|升级用户决策|重规划R)\*\*", text, re.M))


def _resolve_sources(skill_dir: Path, spec) -> list[Path]:
    '''把 PARITY_ITEMS 的「源规格」解析为文件列表（v4.2.0 返修轮：支持多源）。

    spec 三种形态（前 7 项沿用第一种，行为与本函数引入前一致）：
      · str 单路径（无通配）→ 精确单文件；
      · str 含通配（星号/问号/方括号）→ 在技能根下展开，**不递归**（防命中 _backup-*/ 里的历史副本）；
      · tuple/list[str, ...] → 多源，逐项按上述规则解析后合并去重（v4.2.0 返修轮为
        「入口判定主类」引入：源 = SKILL.md + references/*.md，源规格面内表行取并集）。

    存在意义：单源时守卫看不到「手册侧别处新增/改名取值」—— 该缺口由独立复现审核实测发现
    （往 SKILL.md 插一行主类表行，仍报「3 项一致」），属**单向覆盖**，本函数即为此修复。
    '''
    items = spec if isinstance(spec, (tuple, list)) else (spec,)
    out: list[Path] = []
    for it in items:
        if any(ch in it for ch in "*?["):
            out.extend(sorted(skill_dir.glob(it)))
        else:
            out.append(skill_dir / it)
    seen: set = set()
    uniq: list[Path] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


# ── 入口判定主类：确定性声明块 + 启发式扫描（v4.2.0 第五轮换口径）────────────
# 为什么不再用「全手册找表头」的解析：其建模前提**不成立** ——"用正则从任意 markdown
# 表格里稳定提取枚举"做不到，射程边界由写法的无限变化决定，加固只会换一批绕过。
# 实测依据（独立复核，未参与实现者）：前四轮加固后仍有 14 种假绿与 2 种误报，且
# `references/self-judge.md` §10 描述守卫射程的那一行因格内引用了 `| 主类 |`，按竖线
# 切分后产生恰为 `主类` 的碎片格 → **该行被当成表头（列号=1）**，只因后随空行才未引爆。
# 故：FAIL 只判**确定性**的那一半（标记块），启发式降为 **WARN 通道**（与 v3.5.0 P1-1 同处理）。
# ⚠️ 源规格 = SKILL.md + references/*.md + assets/*.md + assets/*.yaml（**不递归**）。
#    为什么必须含 assets/：实测 `assets/` 下有三个文件也重述了主类枚举（ledger-template.md 的「入口类型」列、plan-template.yaml 的 category 注释、熔断报告模板.md 的字段表）——只扫 references/ 的话，这三处的漂移既不会 FAIL 也不会 WARN。
#    扩源前先侦察：对真文档**零新增命中**（无假警）才扩的。

_DECL_BEGIN = "<!-- ai-workflow:category-decl:begin -->"
_DECL_END = "<!-- ai-workflow:category-decl:end -->"
_SEP_CELL = re.compile(r"^:?-{2,}:?$")
_BARE_CELL = re.compile(r"^[A-Za-z][A-Za-z0-9_\-]{0,20}$")
CATEGORY_SOURCES = ("SKILL.md", "references/*.md", "assets/*.md", "assets/*.yaml")


class _DeclError(Exception):
    """声明块形不合法。**抛异常而不是返回空集** —— 静默回落空集会让判据变成"永远全绿"。"""


def _norm_cell(c: str) -> str:
    """单元格归一：去空白／加粗／反引号；括号后缀只保留前缀（块内列义已定，放宽安全）。

    ⚠️ 用 `replace` 而不是 `strip`：`**image**（图像产出）` 用 `strip("*")` 只去**首尾**星号，
    中间那对留着 → 归一成 `image**`，于是"块内新增第四类"这个阳性对照会**假绿**
    （干跑实测抓到，已改）。枚举取值里不会出现星号/反引号，故全删是安全的。
    """
    c = c.strip().replace("*", "").replace("`", "").strip()
    m = re.match(r"^([^\s（(]+)", c)
    return m.group(1) if m else ""


def _norm_cell_full(c: str) -> str:
    """单元格归一但**不截断**（与 `_norm_cell` 的唯一差别）。

    ⚠️ 为什么需要它：`_norm_cell` 的正则 `^([^\\s（(]+)` **在空白处截断** —— 声明块里写成
    `| **chat** / **image** |` 时它只读回 `chat`，第二个取值被静默丢掉。独立复核（未参与
    实现者）实测 c13 抓到这一点：块内多值/连写**当时不被判**。声明块是本判据的**机器接口**、
    格式由本技能自己定，故 `_p_category_decl` 改为要求「**整格一个裸词**」，这里提供判
    「整格」所需的非截断归一。**别把两者合并** —— 截断版在启发式里是刻意的（见 `_scan_one_table`）。
    """
    return c.strip().replace("*", "").replace("`", "").strip()


def _p_category_decl(text: str) -> set:
    """从**标记块**取主类枚举（确定性）。块形不合法即抛 `_DeclError`（调用方转 FAIL）。

    只认**整行等于标记**的行 —— 文档里用反引号引用标记（`` `<!-- … -->` ``）不算，
    故可以在别处讨论本机制而不破坏「源规格面内恰一处」。

    **块形契约（改块形就须同步改本判据）**：① 表头行；② 分隔行；③ ≥1 数据行；
    ④ 每个数据行的**首格整格一个裸词**（去加粗/反引号后须匹配 `_BARE_CELL`；**空首格**与
    中文说明文字都不算）。④ 分两半补：连写/多值那半由第二轮复核 c13 实测后补，**空首格**
    那半由第三轮复核 N4 实测后补 —— 两半都是「此前静默放过」。
    """
    ls = [l.strip() for l in text.splitlines()]
    b = [i for i, l in enumerate(ls) if l == _DECL_BEGIN]
    e = [i for i, l in enumerate(ls) if l == _DECL_END]
    if len(b) != 1 or len(e) != 1:
        raise _DeclError(f"标记须各恰 1 处（begin={len(b)}，end={len(e)}）")
    if e[0] < b[0]:
        raise _DeclError("标记顺序颠倒（end 在 begin 之前）")
    body = [l for l in ls[b[0] + 1:e[0]] if l.startswith("|")]
    if len(body) < 3:
        raise _DeclError(f"块内表格行 {len(body)} 行（需 表头 + 分隔 + ≥1 数据行）")
    sep = body[1].strip().strip("|").split("|")
    if not sep or not all(_SEP_CELL.match(c.strip()) for c in sep):
        raise _DeclError("块内第 2 行不是表格分隔行")
    vals = set()
    for r in body[2:]:
        cells = r.strip().strip("|").split("|")
        whole = _norm_cell_full(cells[0]) if cells else ""
        # ⚠️ 首格必须**整格一个裸词**。块内写成 `**chat** / **image**`、`**chat**（说明）`、
        # `chat,code` 这类连写/多值/带后缀时，`_norm_cell` 只在空白处截断 → 只读回 `chat`，
        # 多出来的取值**静默消失**（独立复核 c13 实测：块内声明 `image` 却不被罚）。
        # 块是本判据的机器接口、格式自定，故这类写法按「块形不合法」FAIL，而不是漏判。
        # ⚠️ **不跳过空首格**（第三轮独立复核 N4）：此前写成 `if whole and …`，于是空首格行
        # （如 `|  | **image** |`）被静默放过；空首格不是裸词，同样按块形不合法 FAIL。
        if not _BARE_CELL.fullmatch(whole):
            raise _DeclError(
                f"块内首格 {whole!r} 不是「整格一个裸词」—— 每个取值须单独占首格，"
                "说明文字放第 2 格；连写/多值会让解析器只读到首个 token 而静默漏判")
        t = _norm_cell(cells[0]) if cells else ""
        if t:
            vals.add(t)
    if not vals:
        raise _DeclError("块内未解析到任何取值")
    return vals


def _scan_one_table(rows: list, expected: set, tag: str) -> list[str]:
    """单张表：找「主类列」，回报其中的可疑裸词。`rows` = [(行号, 行文本), …]。

    两条并列判据 —— 都**只看真表头行**或**按列占比**，刻意不认「任意一行里出现主类」：
    那正是前四轮的哑雷（§10 描述射程的那一行格内含 `| 主类 |`，切分后产生恰为 `主类`
    的碎片格，于是**数据行被当成表头**，列号=1）。
      ① 真表头（第 1 行）前 3 格里有格恰为「主类」→ 该格即主类列（覆盖"块外新写一张主类表"）；
      ② 否则按**列**判：某列裸词 ≥3 个且其中属于本枚举者过半 → 认该列为疑似列。
         ⚠️ 阈值取「≥3 且过半数」而非「≥2」是**实测调出来的**：§4 输出字段表的类型列恰有
         `chat`（Choice 类型）与 `number` 两个裸词 → ≥2 时会假警；≥3 后该列只剩 2 个裸词，静默。
    ⚠️ **前置闸门：只判「行列整齐」的表**（各行列数一致）。实测依据：`self-judge.md` §4 字段表
    用 `\\|` 转义把类型写成 `\\`chat\\` \\| \\`code\\` \\| \\`content\\`` → 该行 6 格、别行 4 格、
    末行 7 格；按列取格必然错位（实测假警 `第4列 'Noul'` —— 其实是把类型行的 `content`
    当成了说明列的取值）。列数不齐 → 整表跳过：**宁漏不误**（启发式只提示，漏了也只是少一条线索）。
     ⚠️ **已声明盲区（三条，均实测）**：
       ① **斜杠连写式重述**（整格 `chat / code / content`）不是裸词 → 不判（`assets/` 里正是这么写的）；
          token 化拆格试过，在真文档上**成片误报**（`Bug`／`secondary`／`ambiguity`／`true`／`LLM`／
          `fail-closed`／日期串……，处数随扫描面变动、不可复现为定值）→ 按**宁漏不误**退回。
       ② 行列不齐的表整表跳过（上一段）。
       ③ **紧跟另一张表（中间不留空行）时会被并成一张表** → 真表头成了前一张表的表头、
          列占比不过半 → **静默**。故块外新写主类表请**与前一张表空一行**。
    """
    if len(rows) < 2:
        return []
    numbered = [(no, s.strip().strip("|").split("|")) for no, s in rows]
    if len({len(c) for _n, c in numbered}) != 1:
        return []
    width = min(len(c) for _n, c in numbered)
    if width < 1:
        return []
    cat_cols = {j for j, c in enumerate(numbered[0][1][:3]) if _norm_cell(c) == "主类"}
    body = numbered[1:]
    if body and body[0][1] and all(_SEP_CELL.match(c.strip()) for c in body[0][1]):
        body = body[1:]                      # 跳分隔行
    if not body:
        return []
    hits: list[str] = []
    for j in range(width):
        pairs = [(no, _norm_cell(c[j])) for no, c in body if j < len(c)]
        bare = [(n, b) for n, b in pairs if _BARE_CELL.match(b) and b != "主类"]
        if j not in cat_cols:
            if len(bare) < 3:
                continue
            if sum(1 for _n, b in bare if b in expected) / len(bare) < 0.5:
                continue
        for n, b in bare:
            if b not in expected:
                hits.append(f"{tag}:{n} 第{j + 1}列 '{b}'")
    return hits


def _scan_category_tables(text: str, expected: set, tag: str) -> list[str]:
    """启发式：源规格面内"看着像主类清单"的表，其可疑裸词（**只用于 WARN**）。

    用**按列占比**而不是"表头文字"：后者正是前四轮踩的坑（表头缩进／加粗／带序号列／
    带括号后缀／写在第四格……每修一种就冒出下一种）。占比判据**不依赖表头怎么写**，
    故对同一批夹具的实际检出**强于**被判为"已加固"的旧解析器。
    """
    out: list[str] = []
    rows: list = []
    for no, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        if s.startswith("|") and s.endswith("|") and len(s) > 1:
            rows.append((no, s))
            continue
        out += _scan_one_table(rows, expected, tag)
        rows = []
    out += _scan_one_table(rows, expected, tag)
    return out


def _check_category_decl(skill_dir: Path) -> None:
    """入口判定主类：① 声明块（确定性 → FAIL）② 疑似列扫描（启发式 → WARN）。

    阴性对照（验收用，**判据换了必须重做夹具** —— 旧的"表头/绕过"夹具对本案无效）：
      (a) 块内 `code` → `codex`，或 `**chat**` → `**Chat**`（大小写）→ 必须 FAIL；
      (b) 块内**新增一行** `| **image** | … |` → 必须 FAIL 且文案含 `image`；
      (c) 删掉 `end` 标记（或让标记出现两次）→ 必须 FAIL（"读不到块"不得静默降级为绿）；
      (d) **块外**（如 `SKILL.md`）新插一张含 `image` 的主类表 → 确定性项**必须仍绿**、
          启发式项**必须出 WARN** —— 这是"两半各司其职"的证明，**别再宣称块外能 FAIL**；
      (e) 块内无取值 / 第 2 行不是分隔行 → 必须 FAIL（块形是本判据的机器接口）；
      (f) 块内**首格连写/多值**（`| **chat** / **image** |`）→ 必须 FAIL（"块形不合法"）；
      (g) 块内**首格为空**（`|  | **image** |`）→ 必须 FAIL（空首格不是裸词）。
          这是**本轮补的**：此前该写法只被 `_norm_cell` 读到 `chat`、第二个取值静默丢失
          （独立复核 c13 实测）。**阴性对照**：撤掉 `_p_category_decl` 的裸词约束，(f) 必须
          转绿 —— 否则说明该夹具空转。
    """
    label = "口径守卫：入口判定主类"
    item_scan = "口径守卫：入口判定主类扫描（启发式·WARN）"
    want = set(VALID_CATEGORY)
    texts: list[tuple[str, str]] = []
    for p in _resolve_sources(skill_dir, CATEGORY_SOURCES):
        try:
            if p.exists():
                texts.append((p.name, p.read_text(encoding="utf-8")))
        except OSError:
            pass
    if not texts:
        fail(label, "源集合一个文件都读不到（守卫读不到规则 = 没有规则）")
        return
    per = []
    for name, t in texts:
        ls = [l.strip() for l in t.splitlines()]
        per.append((name, ls.count(_DECL_BEGIN), ls.count(_DECL_END)))
    nb = sum(x[1] for x in per)
    ne = sum(x[2] for x in per)
    if nb != 1 or ne != 1:
        where = "、".join(f"{n}(begin {b}/end {e})" for n, b, e in per if b or e) or "无"
        fail(label, f"声明块标记须在**源规格面内各恰 1 处**（源规格＝`CATEGORY_SOURCES`，不递归）：实测 begin={nb}、end={ne}｜出现处：{where}"
                    "｜（第二处声明应改成「引用」：用反引号把标记包起来，不要让它单独成行）")
    else:
        holder = next(n for n, b, _e in per if b)
        src = next(t for n, t in texts if n == holder)
        try:
            got = _p_category_decl(src)
        except _DeclError as exc:
            fail(label, f"声明块解析失败：{exc}｜块形是本判据的机器接口，改块形须同步改判据")
        else:
            if got != want:
                fail(label, f"声明块（{holder}）取值得 {sorted(got)} ≠ 代码常量 {sorted(want)}"
                            "（同一物理量两处不同源 —— 要么统一，要么显式声明二者关系）")
            else:
                ok(label, f"声明块（{holder}，源规格面内须恰 1 处）↔ 代码常量 "
                          f"{'/'.join(sorted(want))}（{len(want)} 项一致）")
    hits: list[str] = []
    for name, t in texts:
        hits += _scan_category_tables(t, want, name)
    if hits:
        warn(item_scan, f"疑似未登记的取值 {len(hits)} 处 —— **只提示不阻断**，请人审："
                        + "；".join(hits[:8]) + ("…" if len(hits) > 8 else ""))
    else:
        ok(item_scan, f"源集合 {len(texts)} 个文件未见「主类疑似列」含未登记取值"
                      "（启发式按列裸词占比判定，会漏会误，**不作门禁**）")




PARITY_ITEMS = (
    ("模型档位", "references/routing-guide.md", _p_tiers, VALID_MODEL_TIERS),
    ("步骤状态", "assets/plan-template.yaml", _p_status, VALID_STATUS),
    ("能力类", "references/capability-routing.md", _p_caps, VALID_CAPABILITY),
    ("重规划触发", "references/adaptive-planning.md", _p_triggers, VALID_TRIGGER),
    ("熔断状态", "SKILL.md", _p_fuse, VALID_FUSE),
    ("反思触发", "references/reflection-retry.md", _p_reflect_trigger, VALID_REFLECT_TRIGGER),
    ("终止策略", "references/reflection-retry.md", _p_reflect_term, VALID_TERMINATION),
    # ⚠️「入口判定主类」**不在本表内**（v4.2.0 第五轮换口径后由 `_check_category_decl` 单独判）：
    # 本表的模型是「若干源 → 一个解析器 → 一个集合」，多源时取并集比对；而主类那项需要
    # **跨文件的唯一性判定（源规格面内）**（声明块须恰一处），并集模型表达不了它 ——
    # 两个文件各写一份相同集合时并集仍然相等，于是「重复声明」这一错法会漏判。
)


def _check_parity(skill_dir: Path) -> None:
    """口径守卫（v3.5.0 / P0-3）：断言「手册/模板里写的取值 == 代码内常量」。

    存在意义：`VALID_MODEL_TIERS` 的旧注释写着"与 routing-guide.md 的 enum **同源**"，但
    **同源是靠注释声明的、不是靠测试保证的** —— 改一处忘一处不会抛异常，只会静默分叉。
    本条把该声明变成可机器判定的断言（技能库卫生第 4 条"同一物理量的判据必须跨模块同源
    + 配守卫测试"的落地；该条自 v3.3.0 起已扩展到全流程适用）。

    解析不到即 FAIL：**守着一条读不到的规则等于没有规则**，且"读不到"必须显式，不能静默降级成 OK。
    阴性对照（验收用）：`routing-guide.md` 的 `cheap` → `cheapx` → 第 1 项必须红（路径未被改坏）。
    ⚠️ 主类那项的阴性对照已随第五轮换口径**搬到 `_check_category_decl` 的 docstring** ——
    **判据换了，夹具必须重做**：夹具与被测判据同生共死，沿用旧夹具的阳性对照会静默退化成空转。
    """
    cache: dict[Path, str] = {}
    for label, spec, parser, expected in PARITY_ITEMS:
        paths = _resolve_sources(skill_dir, spec)
        label_src = spec if isinstance(spec, str) else " + ".join(spec)
        is_single = isinstance(spec, str) and not any(ch in spec for ch in "*?[")
        want = set(expected)
        got: set = set()
        missing: list[str] = []
        for p in paths:
            if p not in cache:
                try:
                    cache[p] = p.read_text(encoding="utf-8") if p.exists() else ""
                except OSError:
                    cache[p] = ""
            text = cache[p]
            if not text:
                try:
                    missing.append(p.relative_to(skill_dir).as_posix())
                except ValueError:
                    missing.append(str(p))
            else:
                got |= parser(text)
        if is_single and missing:
            fail(f"口径守卫：{label}", f"源文件缺失或读不到：{label_src}（守卫读不到规则 = 没有规则）")
            continue
        if not paths or len(missing) == len(paths):
            fail(f"口径守卫：{label}", f"源全部缺失或读不到：{label_src}（守卫读不到规则 = 没有规则）")
            continue
        got_s = "/".join(sorted(got))
        want_s = "/".join(sorted(want))
        if not got:
            fail(f"口径守卫：{label}", f"在 {label_src} 中解析不到取值定义（格式可能已变；守卫读不到规则 = 没有规则）")
        elif got != want:
            fail(f"口径守卫：{label}", f"{label_src} 解析得 {got_s} ≠ 代码常量 {want_s}"
                                      f"（同一物理量两处不同源 —— 要么统一，要么显式声明二者关系）")
        else:
            scope = f"{label_src}（读得 {len(paths) - len(missing)} 个文件，取并集）" if len(paths) > 1 else label_src
            ok(f"口径守卫：{label}", f"{scope} ↔ {want_s}（{len(want)} 项一致）")


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


# --------------------------------------------------------------------------- #
# v4.0.0 / U5 + U2：不可逆副作用登记 与 用户放行留痕
# --------------------------------------------------------------------------- #
IRREVERSIBLE_HINT = ("推送", "发布", "上线", "删除", "清空", "force", "覆盖写",
                     "对外发送", "生产配置", "迁移", "回滚", "重建")


def _check_irreversible(meta: dict, steps: list) -> None:
    """U5：不可逆副作用登记 —— **可选字段，填了就必须合法**。

    口径沿用 `_check_autonomy` / `_check_selftools`：不强制填空，填了就不能糊弄。
      * 命中不可逆关键词却留空 → **SKIP**（"是否该有副作用"无法机器判断，不做 FAIL ——
        逼执行者编造比留空更糟）
      * 登记项缺 `可否回滚`，或取值越界 → **FAIL**
    """
    items = meta.get("不可逆副作用") or []
    if not isinstance(items, list):
        fail("meta.不可逆副作用 合法", f"应为列表，实际 {type(items).__name__}")
        return
    if not items:
        blob = " ".join(str(s.get(k, "") or "") for s in steps
                        for k in ("做什么", "交付物", "验证方式"))
        hit = [h for h in IRREVERSIBLE_HINT if h in blob]
        if hit:
            skip("meta.不可逆副作用",
                 f"步骤文本命中不可逆关键词（{'、'.join(hit[:3])}）但本字段留空"
                 f" —— 需人工确认是否该登记（不 FAIL：无法机器判断「是否该有副作用」）")
        return
    bad = []
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict):
            bad.append(f"第 {i} 项应为映射")
            continue
        v = str(it.get("可否回滚", "") or "").strip()
        if not v:
            bad.append(f"第 {i} 项缺『可否回滚』（未知必须显式写，空值不等于『应该没问题』）")
        elif v not in ("可回滚", "不可回滚", "未知"):
            bad.append(f"第 {i} 项『可否回滚』=『{v}』（只允许 可回滚/不可回滚/未知）")
    if bad:
        fail("meta.不可逆副作用", "；".join(bad[:3]))
    else:
        ok("meta.不可逆副作用", f"登记 {len(items)} 项，合法")


def _check_user_release(meta: dict) -> None:
    """U2：用户放行留痕 —— **非门禁**，只提高伪造成本。

    ⚠️ 本字段做不到真正的机器强制（执行者可自填）。字段注释与 SKILL.md 都必须
    原样保留这一事实，否则就是造「看起来有门禁其实没有」的假安全感 —— 比不做更糟。
    """
    # 适用范围：L2 全量；**L1 可省**（命中模板即跳过追问循环，无独立放行环节 —— 清单 §2.3）
    if str(meta.get("任务层级", "") or "").strip() == "L1":
        return
    items = meta.get("用户放行") or []
    if not isinstance(items, list):
        fail("meta.用户放行 合法", f"应为列表，实际 {type(items).__name__}")
        return
    if not items:
        skip("meta.用户放行", "未记录 —— 本字段**不是门禁**（可自填，机器无法强制），留空只作提示")
        return
    bad = []
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict):
            bad.append(f"第 {i} 项应为映射")
            continue
        for k in ("时间", "摘要"):
            if not str(it.get(k, "") or "").strip():
                bad.append(f"第 {i} 项缺『{k}』")
    if bad:
        fail("meta.用户放行", "；".join(bad[:3]))
    else:
        ok("meta.用户放行", f"登记 {len(items)} 项（**留痕，非门禁**）")


# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# v4.2.0：self-judge 入口判定校验（可选字段，缺省即 WARN —— 向后兼容旧 plan）
# --------------------------------------------------------------------------- #
ENTRY_KEY = "入口判定"
ENTRY_REQUIRED = ("category", "distribution", "confidence", "dimensions", "ambiguity", "route_hint")
ENTRY_DIMS = ("D1", "D2", "D3", "D4", "D5")


def _check_entry_verdict(meta: dict) -> None:
    """v4.2.0：meta.入口判定 —— **可选字段，填了就必须合法**。

    口径与 `_check_user_release` / `_check_reflection_retry` 同源：
      * 整段缺省 → **WARN**（向后兼容旧 plan，**不追认历史计划** ——
        不拿新判据改写旧证据）
      * 非映射 / 缺必填项 / 取值越界 → **FAIL**

    ⚠️ **它不是门禁**：`confidence` 由模型自填，**校准无法被机器证明**。
    本函数只做"结构合法"这一层；"类别选对了没"不在此判据射程内
    （类型合法 ≠ 判断正确）。依据与原文见 references/self-judge.md §10。
    """
    v = meta.get(ENTRY_KEY, None)
    if not v:
        warn("meta.入口判定",
             "未记录 —— 阶段 0 第 1 步（self-judge）本应产出。**只提示不阻断**："
             "向后兼容旧 plan，不追认历史计划；本项**不是门禁**（校准无法机器强制）")
        return
    if not isinstance(v, dict):
        fail("meta.入口判定 合法", f"应为映射，实际 {type(v).__name__}")
        return
    bad = []
    for k in ENTRY_REQUIRED:
        if k not in v or (not isinstance(v[k], (int, float, bool)) and not v[k]):
            bad.append(f"缺『{k}』或为空")
    cat = str(v.get("category", "") or "").strip()
    if cat and cat not in VALID_CATEGORY:
        bad.append(f"category=『{cat}』（只允许 {'/'.join(VALID_CATEGORY)}）")
    conf = v.get("confidence", None)
    if conf is not None:
        if isinstance(conf, bool) or not isinstance(conf, (int, float)):
            bad.append(f"confidence={conf!r}（须为 0–1 的数）")
        elif not 0.0 <= float(conf) <= 1.0:
            bad.append(f"confidence={conf!r}（越界，须在 0–1）")
    amb = v.get("ambiguity", None)
    if amb is not None and not isinstance(amb, bool):
        bad.append(f"ambiguity={amb!r}（须为 bool）")
    dist = v.get("distribution", None)
    if isinstance(dist, dict):
        if set(dist) != set(VALID_CATEGORY):
            bad.append(f"distribution 键={sorted(dist)}（须恰为 {sorted(VALID_CATEGORY)}）")
        else:
            nums = [float(x) for x in dist.values()
                    if isinstance(x, (int, float)) and not isinstance(x, bool)]
            if len(nums) != len(VALID_CATEGORY):
                bad.append("distribution 含非数值项")
            elif abs(sum(nums) - 1.0) > 1e-6:
                bad.append(f"distribution 之和={sum(nums):.4f}（须为 1）")
    elif dist is not None:
        bad.append(f"distribution 应为映射，实际 {type(dist).__name__}")
    dims = v.get("dimensions", None)
    if isinstance(dims, dict):
        miss_d = [d for d in ENTRY_DIMS if d not in dims]
        if miss_d:
            bad.append(f"dimensions 缺 {'/'.join(miss_d)}")
    elif dims is not None:
        bad.append(f"dimensions 应为映射，实际 {type(dims).__name__}")
    sec = v.get("secondary", None)
    if sec not in (None, "") and str(sec).strip() not in VALID_CATEGORY:
        bad.append(f"secondary=『{sec}』（留空或在 {'/'.join(VALID_CATEGORY)} 内）")
    if bad:
        fail("meta.入口判定 合法", "；".join(bad[:3]))
    else:
        ok("meta.入口判定 合法", f"category={cat}（**留痕，非门禁**；结构合法不代表判对）")


# --------------------------------------------------------------------------- #
# v4.1.0：反思重试配置校验（可选块，缺省即 SKIP —— 向后兼容旧 plan）
# --------------------------------------------------------------------------- #
def _validate_reflect_block(block: dict, where: str) -> list:
    """校验一个反思重试配置块（meta 级或步骤级覆盖），返回问题字符串列表（空 = 合法）。"""
    if not isinstance(block, dict):
        return [f"{where}：应为映射，实际 {type(block).__name__}"]
    bad = []
    # 最大重试次数：可选；填了必须整数 ≥1（bool 是 int 子类，显式排除）
    mv = block.get("最大重试次数", None)
    if mv is not None:
        if isinstance(mv, bool) or not isinstance(mv, int) or mv < 1:
            bad.append(f"{where}：「最大重试次数」={mv!r}（必须为整数 ≥1）")
    # 触发条件：可选；填了必须是 T1-T3 的非空子集
    tc = block.get("触发条件", None)
    if tc is not None:
        if not isinstance(tc, list) or not tc:
            bad.append(f"{where}：「触发条件」必须为非空列表（取值 {'/'.join(VALID_REFLECT_TRIGGER)}）")
        else:
            bad_t = [str(x) for x in tc if x not in VALID_REFLECT_TRIGGER]
            if bad_t:
                bad.append(f"{where}：「触发条件」含非法值 {bad_t}（只允许 {'/'.join(VALID_REFLECT_TRIGGER)}）")
    # 终止策略：可选；填了必须在枚举内
    term = block.get("终止策略", None)
    if term is not None and term not in VALID_TERMINATION:
        bad.append(f"{where}：「终止策略」=『{term}』（只允许 {'/'.join(VALID_TERMINATION)}）")
    return bad


def _check_reflection_retry(meta: dict, steps: list) -> None:
    """v4.1.0：反思重试配置 —— **可选块，整段缺省即 SKIP（向后兼容）**。

    口径沿用「可选字段、填了就不能糊弄」：整段（meta + 步骤级覆盖均）缺省＝关闭自动重试，
    旧 plan 不受影响；一旦 meta 或某步骤填了，就校验结构合法（最大重试次数整数 ≥1 /
    触发条件为 T1-T3 子集 / 终止策略在枚举内）。**语义**（"重试是否真的改了什么"）无法
    机器判定，靠抽查。
    """
    cfg = meta.get("反思重试配置", None)
    bad = []
    if cfg:
        bad += _validate_reflect_block(cfg, "meta.反思重试配置")
    # 步骤级覆盖：模板口径「不写则用 meta，写了只对本步生效」—— 即便 meta 无配置，
    # 单步也可独立声明自己的重试策略，故同样校验（不依赖 meta 是否存在）。
    step_overrides = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        ov = s.get("反思重试", None)
        if ov:
            step_overrides.append((s.get("id", "?"), ov))
    if not cfg and not step_overrides:
        skip("meta.反思重试配置", "未配置（含步骤级覆盖）—— 旧 plan 或显式关闭自动重试（不影响判定）")
        return
    for sid, ov in step_overrides:
        bad += _validate_reflect_block(ov, f"步骤 {sid}.反思重试")
    if bad:
        fail("meta.反思重试配置 合法", "；".join(bad[:3]))
    else:
        ok("meta.反思重试配置 合法", "配置结构合法（语义靠抽查，非门禁）")


# --------------------------------------------------------------------------- #
# v4.0.0 / U3 + U8：执行 trace 与任务级指标（共用 jsonl 追加设施）
# --------------------------------------------------------------------------- #
def _jsonl_append(path: Path, rec: dict) -> None:
    """追加一行 jsonl，目录不存在则建。**追加不覆盖**（与 mark/decide/revise 同风格）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _task_dir(plan_path: Path) -> Path:
    return plan_path if plan_path.is_dir() else plan_path.parent


def cmd_trace(plan_path: Path, step: str | None, action: str, command: str,
              result: str, elapsed: float | None, replay: bool,
              note: str = "", attempt: int | None = None) -> int:
    """U3：执行 trace —— `plan.yaml` 记的是**离散状态点**（做到哪/为什么引入/为什么变了），
    不含时序；trace 补上时序，让阶段 6 的复盘四问从"回忆"变"查账"。

    ⚠️ **约定：`trace.jsonl` 不进 `交付物` 字段** —— 它是留痕不是交付物。
    若写进交付物，`_is_file_like()` 会命中 `.jsonl` 并按存在性判定，把留痕误当产物。

    v4.1.0：新增 `--note` / `--attempt` —— 用于结构化记录「反思重试」（action=retry 时
    填根因·调整摘要与第几轮重试），与其它 trace 行同构、可 `--replay` 回放。
    """
    tf = _task_dir(plan_path) / "trace.jsonl"
    if replay:
        if not tf.exists():
            print("[INFO] 无 trace 记录 —— %s 不存在" % tf)
            return 0
        n = 0
        for i, ln in enumerate(tf.read_text(encoding="utf-8").splitlines(), 1):
            if ln.strip():
                print("%3d  %s" % (i, ln[:200]))
                n += 1
        print("=== trace 回放：%d 条 ===" % n)
        return 0
    if not step:
        print("[ERROR] --step 必填（--replay 时不需要）", file=sys.stderr)
        return 2
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M"), "step": str(step),
           "action": action or "", "cmd": command or "", "result": result or ""}
    if elapsed is not None:
        rec["elapsed_s"] = elapsed
    if note:
        rec["note"] = note
    if attempt is not None:
        rec["attempt"] = attempt
    _jsonl_append(tf, rec)
    print("[OK] trace 已追加 —— %s（step=%s）" % (tf, step))
    return 0


def cmd_metrics(plan_path: Path, finalize: bool) -> int:
    """U8：任务级指标沉淀 —— 收尾时把本任务指标追加进**本任务目录**的 `_metrics.jsonl`
    （即 `tasks/<任务>/_metrics.jsonl`）。

    ⚠️ **路径口径修正（v4.3.0）**：此前 docstring 与 `SKILL.md` 都写作"工作区级
    `tasks/_metrics.jsonl`"，但代码一直是 `_task_dir(pp) / "_metrics.jsonl"` —— 落点是**任务
    目录内**。实测工作区：`tasks/*/_metrics.jsonl` 有 1 个、`tasks/_metrics.jsonl` 为 0 个，
    证明实际行为与文档不符。按「同一物理量两处即为不符合」（技能库卫生第 4 条）**改文档对齐
    代码**，而不是改代码去迁就文档 —— 因为按任务分文件才能让归档随任务一起移动。

    目的：此前**没有任何任务级统计**（返修轮次、熔断频次、门禁 FAIL 率、步骤耗时全无），
    技能自身演进缺数据依据。
    """
    if not finalize:
        print("[ERROR] 目前只支持 --finalize（收尾时汇总一次，避免中途写入半成品）", file=sys.stderr)
        return 2
    pp = plan_path if plan_path.is_dir() else plan_path.parent
    if pp.is_dir():
        pp = pp / "plan.yaml"
    if not pp.exists():
        print("[ERROR] 找不到 plan.yaml —— %s" % pp, file=sys.stderr)
        return 2
    yaml = _require_yaml()
    data = yaml.safe_load(pp.read_text(encoding="utf-8")) or {}
    meta = data.get("meta") or {}
    steps = data.get("steps") or []
    st = [str(s.get("状态", "") or "") for s in steps]
    rec = {
        "task": str(meta.get("任务", "") or "")[:80],
        "level": str(meta.get("任务层级", "") or "") or "?",
        "date": time.strftime("%Y-%m-%d"),
        "revisions": len(meta.get("计划修订") or []),
        "fused": str(meta.get("熔断状态", "") or "").strip() == "已熔断",
        "steps": len(steps),
        "done": sum(1 for x in st if x == "完成"),
        "irreversible": len(meta.get("不可逆副作用") or []),
        "released": len(meta.get("用户放行") or []),
    }
    tf = _task_dir(pp) / "_metrics.jsonl"
    _jsonl_append(tf, rec)
    print("[OK] 指标已追加 —— %s" % tf)
    print("    " + json.dumps(rec, ensure_ascii=False)[:220])
    return 0


# ── v4.3.0 / E′：步骤闭环不变量（E「步骤闭环」+ M-1′「零沉淀须显式登记」合并）────────
# 为什么必须合并：两条都落在 check_plan、都管「完成态该留下什么」。分开做会出现两个判据互相
# 打架（一个说"有 trace 就算闭环"，另一个说"得有沉淀登记"），故合成一条链式判定。
#
# ⚠️ **WARN/FAIL 的分级是实测出来的，不是拍脑袋定的**（2026-09-21 上线前影响面实测）：
#   工作区 21 个已完成任务 **全部** 无 trace.jsonl、132 个完成步骤零时序留痕。若直接按 FAIL
#   上线，等于把**全部历史库存判红** —— 那不是发现缺陷，是制造噪音，而噪音的必然结局是判据
#   被整体绕过（v3.5.0 已有此教训）。故分三级：
#     · 无 trace.jsonl（或空文件）      → WARN：提示里给可执行的补救命令
#     · 有 trace 但完成步骤漏记         → FAIL：该任务**已启用** trace 却漏记，是确定的不一致
#     · 零沉淀且未显式写明「无沉淀」理由 → WARN：对齐方案 §4.4（首版不稳的检查先落 WARN）
#   升级时机：当新任务普遍启用 trace（metrics 里有据可查）后，第一档可整体升 FAIL。
#   Sediment（沉淀）的判定口径见下。另注：`PLAN_STEP_REQUIRED` **已包含「验证方式」**，所以 E
#   原本提的"完成态须有验证方式"这一块钱，已由既有「步骤 N 必填字段」判据覆盖，**此处不重复
#   判** —— 重复判不会更严，只会让同一缺陷在输出里出现两次，稀释每条 WARN 的可读性。
SEDIMENT_TOKENS = ("沉淀", "复盘", "sediment", "metrics")
_TRACE_HINT = ("补救：每步执行后 `checks.py trace <plan> --step <id> --action <摘要>`；"
               "收尾 `checks.py metrics <plan> --finalize`")


def _read_trace(path: Path) -> tuple[set[str], list[str]]:
    """读 trace.jsonl → (已记录的 step id 集合, action 列表)。坏行跳过，不算致命错误。"""
    ids: set[str] = set()
    actions: list[str] = []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return ids, actions
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        if isinstance(rec, dict):
            if rec.get("step") is not None:
                ids.add(str(rec.get("step")))
            actions.append(str(rec.get("action", "") or ""))
    return ids, actions


def _check_closure(steps: list[dict], plan_path: Path, meta: dict) -> None:
    """E′：完成态 = 状态 + trace + 沉淀登记（验证方式由 PLAN_STEP_REQUIRED 覆盖）。"""
    done = [s for s in steps if str(s.get("状态", "")).strip() == "完成"]
    if not done:
        skip("步骤闭环不变量", "无已完成步骤")
        return

    trace_path = _task_dir(plan_path) / "trace.jsonl"
    if not trace_path.exists():
        warn("步骤闭环不变量（trace 自证）",
             f"{len(done)}/{len(steps)} 步已完成但无 trace.jsonl —— 复盘只能靠回忆，"
             f"且本次是否沉淀无法自证。{_TRACE_HINT}")
        return

    ids, actions = _read_trace(trace_path)
    if not actions:
        warn("步骤闭环不变量（trace 自证）", f"trace.jsonl 存在但 0 条记录。{_TRACE_HINT}")
        return

    miss = [str(s.get("id", "?")) for s in done if str(s.get("id", "?")) not in ids]
    if miss:
        fail("步骤闭环不变量（trace 自证）",
             f"本任务已启用 trace，但 {len(miss)} 个完成步骤无记录：{','.join(miss[:10])}"
             f"{'…' if len(miss) > 10 else ''}。{_TRACE_HINT}")
    else:
        ok("步骤闭环不变量（trace 自证）", f"{len(done)} 个完成步骤均有 trace 记录")

    # M-1′：零沉淀须**显式登记**。hermes 原文：a pass that does nothing is a missed
    # learning opportunity, **not a neutral outcome** —— 空转通过等于漏掉一次学习。
    noted = str(meta.get("复盘沉淀", "") or "").strip()
    learned = any(any(tok in a for tok in SEDIMENT_TOKENS) for a in actions)
    if noted or learned:
        pieces = []
        if noted:
            pieces.append("meta.复盘沉淀 已登记")
        if learned:
            pieces.append("trace 含沉淀/复盘动作")
        ok("复盘沉淀登记", "；".join(pieces))
    else:
        warn("复盘沉淀登记",
             "本次未登记任何沉淀（既无 meta.复盘沉淀，trace 中亦无沉淀/复盘动作）。"
             "若确无可沉淀内容，须**显式写明**『无沉淀：理由』后重跑；"
             "什么都不做的一次 pass 是漏掉的学习机会，不是中性结果。")


# ── v4.3.0 / B：平台门控 vs 真实 import ────────────────────────────────────────
# 判的是「**用了单平台能力，却在 frontmatter 宣称跨平台**」这一自相矛盾，**不判**"这个类库
# 装没装"（后者与平台无关，装不上会在运行时炸，轮不到这里管）。
#
# 用 **AST 而非正则**：正则会把注释里、字符串里的同名文本也算命中。本机最典型的一课是
# `checks.py:755/787` 与 `verify_push.py:254` 三处 `"/tmp/" in rel` —— 那是**跳过临时目录的
# 路径过滤器**，与平台无关；按字面量判定会 100% 假红自身。故两条纪律：
#   ① 只认 AST 里的真实 import 与属性调用；② **不把 `/tmp` 字面量视作平台信号**。
#   这是**收窄判据**而不是放水：真正的单平台能力（`fcntl`/`termios`/`os.fork`/`winreg`…）一条未放过。
PLAT_MODULES = {
    "fcntl": "POSIX", "termios": "POSIX", "pty": "POSIX", "pwd": "POSIX", "grp": "POSIX",
    "syslog": "POSIX", "resource": "POSIX", "readline": "POSIX", "crypt": "POSIX",
    "msvcrt": "Windows", "winreg": "Windows", "_winreg": "Windows", "winsound": "Windows",
    "win32api": "Windows", "win32con": "Windows", "pywin32": "Windows", "pythoncom": "Windows",
}
# 模块本身跨平台，但某些成员不是（写成 "模块.成员"）
PLAT_ATTRS = {
    "os.setsid": "POSIX", "os.fork": "POSIX", "os.forkpty": "POSIX", "os.openpty": "POSIX",
    "os.killpg": "POSIX", "os.waitpid": "POSIX", "os.wait": "POSIX", "os.getpgid": "POSIX",
    "os.setpgid": "POSIX", "os.getuid": "POSIX", "os.getgid": "POSIX", "os.setuid": "POSIX",
    "os.mkfifo": "POSIX", "os.mknod": "POSIX", "os.execv": "POSIX", "os.execve": "POSIX",
    "os.nice": "POSIX", "signal.SIGKILL": "POSIX", "signal.SIGCHLD": "POSIX", "signal.SIGQUIT": "POSIX",
    "ctypes.windll": "Windows", "ctypes.WinDLL": "Windows", "ctypes.OleDLL": "Windows",
    "ctypes.wintypes": "Windows",
}
PLAT_ABS_PATHS = ("/usr/bin/", "/usr/local/", "/var/run/", "/etc/", "/bin/", "/proc/")  # platform-check:allow（本判据自身的规则表，不是真实路径依赖）
# 行内豁免：命中的行里若出现本标记，则不计入 FAIL、改计入「豁免」并单独列出。
# 唯一合法用途与 outbound_scan.py 的 `outbound-scan:allow` 完全同源 —— ① 判据自身的规则表；
# ② 文档中示范该格式的行。**收窄判据，而不是把文档改得躲开门禁**。
# ⚠️ 本判据首次上线时**第一个命中的就是它自己的规则表**（checks.py 的 PLAT_ABS_PATHS），
#    与 v3.5.0「新门禁第一次拦住的通常是引入它的那次改动」是同一现象。
PLAT_ALLOW_TOKEN = "platform-check:allow"


def _attr_chain(node: ast.AST) -> str:
    """把 `a.b.c` 的属性链还原成字符串；非纯 Name/Attribute 链返回空串。"""
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return ""


class _PlatVisitor(ast.NodeVisitor):
    """收集单平台依赖。只记录确定命中的形态，宁可不报也不误报。"""

    def __init__(self) -> None:
        self.hits: list[tuple[str, str, str, int]] = []  # (类别, 名称, 平台, 行号)
        self.aliases: dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for al in node.names:
            top = al.name.split(".")[0]
            if top in PLAT_MODULES:
                self.hits.append(("模块", al.name, PLAT_MODULES[top], node.lineno))
            self.aliases[al.asname or top] = top
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        top = (node.module or "").split(".")[0]
        if top in PLAT_MODULES:
            self.hits.append(("模块", node.module or "", PLAT_MODULES[top], node.lineno))
        for al in node.names:
            self.aliases[al.asname or al.name] = f"{top}.{al.name}"
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        chain = _attr_chain(node)
        if chain:
            top = chain.split(".")[0]
            full = self.aliases.get(top, top) + chain[len(top):]
            plat = PLAT_ATTRS.get(full)
            if plat:
                self.hits.append(("成员", full, plat, node.lineno))
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            for pref in PLAT_ABS_PATHS:
                if node.value.startswith(pref):
                    self.hits.append(("绝对路径", node.value[:40], "POSIX", node.lineno))
                    break
        self.generic_visit(node)


def _check_platform(skill_dir: Path) -> None:
    """B：脚本用了单平台能力 vs frontmatter 是否声明 `platforms:`。"""
    skill_md = skill_dir / "SKILL.md"
    head = _frontmatter(skill_md.read_text(encoding="utf-8")) if skill_md.exists() else ""
    declared = bool(re.search(r"^\s*platforms\s*[:\-]", head, re.M))

    hits: list[tuple[str, str, str, str, int]] = []  # (文件, 类别, 名称, 平台, 行号)
    allowed: list[str] = []
    for py in sorted((skill_dir / "scripts").glob("*.py")):
        try:
            src = py.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src, filename=str(py))
        except (SyntaxError, ValueError, OSError):
            continue  # 语法不合法由「py_compile」判据负责，这里不重复报错
        lines = src.splitlines()
        v = _PlatVisitor()
        v.visit(tree)
        for cat, name, plat, ln in v.hits:
            if 0 < ln <= len(lines) and PLAT_ALLOW_TOKEN in lines[ln - 1]:
                allowed.append(f"{py.name}:{name}@{ln}")
                continue
            hits.append((py.name, cat, name, plat, ln))

    if allowed:
        # 豁免不是逃生门 —— 它必须被**看见**（列出文件名与行号），否则就成了"悄悄地放行"。
        ok("平台门控：行内豁免", f"{len(allowed)} 处（{'; '.join(allowed[:5])}"
                                f"{'…' if len(allowed) > 5 else ''}）—— 合法用途仅限判据自身规则表与文档示范")

    if not hits:
        ok("平台门控 vs 真实 import", "scripts/*.py 无单平台 API 依赖（AST 口径）")
        return

    detail = "；".join(f"{f}:{nm}@{ln}[{pl}]" for f, _c, nm, pl, ln in hits[:6])
    if len(hits) > 6:
        detail += f"…（共 {len(hits)} 处）"
    pol = "/".join(sorted({pl for _, _, _, pl, _ in hits}))
    if declared:
        ok("平台门控 vs 真实 import",
           f"frontmatter 已声明 platforms；命中 {len(hits)} 处 {pol} 依赖 —— {detail}。"
           f"⚠️ **声明与实际是否一致本判据不代您核对**（它能发现『未声明』，无法发现『声明得不对』）。")
    else:
        fail("平台门控 vs 真实 import",
             f"用了 {pol} 专属能力却未在 frontmatter 声明 `platforms:` —— {detail}。"
             f"补声明，或改用跨平台实现（如 `tempfile`/`pathlib` 替代硬编码路径）。")


def _check_gate(skill_dir: Path) -> None:
    """C-1 常驻判据：运行时闸门 `gate.py` 的可用性 + 同源性 + fail-closed 行为。

    三级判据，缺一不可 ——
      ① **存在性/语法**：文件在且能 AST 解析（不靠 py_compile 代劳，独立判定）；
      ② **同源性**：`INFRA_EXCEPTIONS` 必须**从 checks.py 加载**（技能库卫生第 4 条：
         同一物理量单一事实源）。**自建副本 → FAIL** —— 那正是「复制粘贴」的复发形态；
      ③ **行为**：跑 `--selftest`，要求退出码 0（含决策层 × 意图对照）。
    ⚠️ 本判据**不复制** `INFRA_EXCEPTIONS` 的取值，只断言「它是被加载来的」——
    否则判据自己就成了第三个副本。
    """
    NAME = "运行时闸门（gate.py 可用性与同源）"
    gate = skill_dir / "scripts" / "gate.py"
    if not gate.exists():
        fail(NAME, "scripts/gate.py 缺失 —— 红线③在**运行时**无收口："
                   "阶段 3 的删改既有文件动作失去前置拦截（事后对账拦不住已发生的事）")
        return
    try:
        src = gate.read_text(encoding="utf-8", errors="ignore")
        ast.parse(src, filename=str(gate))
    except SyntaxError as e:
        fail(NAME, f"gate.py 语法错误（L{e.lineno}）：{e.msg}")
        return
    except (ValueError, OSError) as e:
        fail(NAME, f"gate.py 不可读：{type(e).__name__}: {e}")
        return

    # ② 同源性：不得自建 INFRA_EXCEPTIONS 副本；必须由 checks.py 加载
    self_def = bool(re.search(r"^INFRA_EXCEPTIONS\s*[:=]", src, re.M))
    loads_it = bool(re.search(r"spec_from_file_location|importlib", src)) and "INFRA_EXCEPTIONS" in src
    if self_def:
        fail(NAME, "gate.py **自行定义**了 INFRA_EXCEPTIONS —— 违反技能库卫生第 4 条"
                   "（同一物理量必须单一事实源）。改为从 checks.py 加载，不要复制取值。")
        return
    if not loads_it:
        fail(NAME, "gate.py 未见从 checks.py 加载 INFRA_EXCEPTIONS 的代码 —— 同源性无法证明"
                   "（口径来源不可验证即随时可能漂移）")
        return

    # ③ 行为：阴性对照。第一版假绿正出在「只测范围不测决策」，故这里要求整组退出码 0。
    try:
        r = subprocess.run([sys.executable, str(gate), "--selftest"],
                           capture_output=True, text=True, errors="replace", timeout=120)
    except subprocess.TimeoutExpired:
        fail(NAME, "--selftest 超时（120s）—— 闸门自身可能死锁")
        return
    except OSError as e:
        fail(NAME, f"--selftest 无法启动：{type(e).__name__}: {e}")
        return
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        bad = [l.strip() for l in out.splitlines() if "[XX " in l]
        extra = f"：{'；'.join(bad[:3])}" if bad else ""
        fail(NAME, f"--selftest 退出码 {r.returncode}（{len(bad)} 项不符预期）{extra}")
        return
    n_ok = out.count("[OK ]")
    ok(NAME, f"gate.py 就位；INFRA_EXCEPTIONS 由 checks.py 同源加载（未自建副本）；"
             f"--selftest 退出码 0（{n_ok} 项对照全绿）")


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
    _check_irreversible(meta, steps)
    _check_user_release(meta)
    _check_entry_verdict(meta)
    _check_autonomy(meta)
    _check_selftools(meta, steps, base)
    _check_stage_gates(steps)
    _check_model_tiers(steps)
    _check_reflection_retry(meta, steps)
    _check_fuse(meta, steps, plan_path)
    # v4.3.0 / 批次 B：E′ 步骤闭环不变量（trace 自证 + 零沉淀须显式登记）。放最后，
    # 因为它依赖前面各项的判定结果（plan 可解析、meta 完整），且它的输出会引用 step id。
    _check_closure(steps, plan_path, meta)
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

    p = sub.add_parser("trace", help="追加一条执行 trace（v4.0.0 / U3：补 plan.yaml 缺失的时序）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("--step", help="步骤 id（--replay 时不需要）")
    p.add_argument("--action", default="", help="本步动作摘要")
    p.add_argument("--command", default="", help="实际执行的命令（避免与子命令名 cmd 冲突，故拼全）")
    p.add_argument("--result", default="", help="结果摘要")
    p.add_argument("--elapsed", type=float, help="耗时（秒）")
    p.add_argument("--note", default="", help="执行备注（v4.1.0：反思重试时填根因·调整摘要）")
    p.add_argument("--attempt", type=int, help="重试轮次（v4.1.0：action=retry 时填第几轮）")
    p.add_argument("--replay", action="store_true", help="回放该任务的完整时序")

    p = sub.add_parser("metrics", help="任务级指标沉淀（v4.0.0 / U8：写入 tasks/_metrics.jsonl）")
    p.add_argument("plan", help="plan.yaml 路径或任务目录")
    p.add_argument("--finalize", action="store_true", help="收尾时汇总写入一次")

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
    elif args.cmd == "selftool":
        code = cmd_selftool(Path(args.plan), args.name, args.purpose, args.scenario, args.repo)
        name = "自研工具登记"
    elif args.cmd == "trace":
        code = cmd_trace(Path(args.plan), args.step, args.action, args.command,
                         args.result, args.elapsed, args.replay, args.note, args.attempt)
        name = "执行 trace"
    else:  # metrics
        code = cmd_metrics(Path(args.plan), args.finalize)
        name = "指标沉淀"

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
