# -*- coding: utf-8 -*-
"""checks 核心层：import、常量、通用工具（不依赖任何其他 checks_* 模块）

由 `scripts/checks.py` 拆分而来（v4.4.2 结构与可维护性优化，行为不变）。
依赖方向：core ← parity ← judges ← cmds ← entry（严格单向，无循环）。
"""
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)

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
VALID_FUSE = ("正常", "已熔断")
VALID_CAPABILITY = ("知识", "算力", "事实", "手脚")
VALID_TRIGGER = ("R1", "R2", "R3", "R4", "R5", "R6")
VALID_MODEL_TIERS = ("strong", "mid", "cheap", "default")
VALID_REFLECT_TRIGGER = ("T1", "T2", "T3")
VALID_TERMINATION = ("升级返修复查", "触发熔断", "升级用户决策", "重规划R")
VALID_CATEGORY = ("chat", "code", "content")
# Git 提交类型（v4.6.0）：源规格 = `references/git-conventions.md` §3.2 + `references/data-model.md` §2.2
#   + `scripts/git_check.py` 的 `COMMIT_TYPES`（工具侧 —— 它要独立分发到 ai-workflow-tools，
#   故刻意不 import 本模块，于是形成**两处代码常量**；该漂移由 checks_parity 的「提交类型」
#   守卫项三源并集比对兜住）。
#   ⚠️ 扩展类型（chore/perf/test 等）须先经用户确认，再同步上述三处（见 git-conventions.md §3.2）。
VALID_COMMIT_TYPES = ("feat", "fix", "refactor", "docs")
DECISION_KEYS = ("决策点", "能力类", "依据", "选择")
REVISION_KEYS = ("触发", "变化", "时间")
MAX_REVISIONS = 3  # 超上限说明初始拆解有问题，应停下与用户重新对齐目标（非熔断）
SELFTOOL_KEYS = ("名称", "用途", "适用场景", "仓库链接")
SELFTOOL_PENDING = "待推送"
SELFTOOL_PLACEHOLDER = re.compile(r"[<>]|TODO|todo|XXX|xxx|\{|\}|待定|N/A")
FUSE_REPORT = "熔断报告.md"
FUSE_SECTIONS = ("触发条件", "已试路径", "卡点根因", "待决策选项", "复位条件")
REF_WHITELIST = {"plan.yaml", "Ledger.md", "memory/YYYY-MM-DD.md", "README.md",
                 # 用户级人格/记忆文件：按约定存在于 ~/.workbuddy/，不在技能目录内，不应按技能内引用校验
                 "USER.md", "MEMORY.md"}
REF_EXTERNAL_PREFIXES = (".workbuddy/", ".scratch/", "历史数据集/", "backend/", "frontend/",
                         "indicators/", "daily_scheduler/", "tests/")
REF_PLACEHOLDER = re.compile(r"N{2,}|Y{2,}|M{2,}|D{2,}|<|>|\{|\}|xxx|XXX")
REF_PATTERN = re.compile(r"`([A-Za-z0-9_./\u4e00-\u9fff-]+\.(?:md|yaml|py|ps1))`")
INFRA_EXCEPTIONS = (
    "/.workbuddy/skills/",
    "/.workbuddy/binaries/python/envs/ai-workflow/",
    "/.workbuddy/cache/ai-workflow/",
)
SCOPE_AUTH_KEY = "越界授权"
SCOPE_HINT = ("（相对路径以 --base 为基准，故越界只可能来自绝对路径或 `..` 上跳；"
              "确需在工作区根之外产出时，须先取得用户**当次**授权并登记 `meta.越界授权`）")
results: list[tuple[str, str, str]] = []  # (状态, 检查项, 说明)
MARKS = {"OK": "[ OK ]", "FAIL": "[FAIL]", "SKIP": "[SKIP]", "WARN": "[WARN]"}
SELFTOOL_MARKERS = ("[自研工具]", "[自研技能]")
CODE_EXT = (".py", ".ps1", ".sh", ".bat", ".js", ".ts")
_SELFTOOL_LEDGER_CACHE: dict[str, list] = {}
_DECL_BEGIN = "<!-- ai-workflow:category-decl:begin -->"
_DECL_END = "<!-- ai-workflow:category-decl:end -->"
_SEP_CELL = re.compile(r"^:?-{2,}:?$")
_BARE_CELL = re.compile(r"^[A-Za-z][A-Za-z0-9_\-]{0,20}$")
CATEGORY_SOURCES = ("SKILL.md", "references/*.md", "assets/*.md", "assets/*.yaml")
STAGE2_STEP_RE = re.compile(r"方案评审|候选方案|方案对比|对比表|备选方案")
STAGE2_SIGNAL_RE = re.compile(r"(≥|>=|不少于|至少)\s*2|2\s*个\s*(候选|方案|备选)|方案\s*[AB一二]|候选\s*[AB]|横向对比|双跑")
STAGE4_EXT = (".docx", ".xlsx", ".pdf", ".pptx")
STAGE4_SIGNAL_RE = re.compile(r"口径|一致性|估算|写回|读回|office_io|交叉核对|抽\s*2\s*处|抽两处|抽查|脱敏")
IRREVERSIBLE_HINT = ("推送", "发布", "上线", "删除", "清空", "force", "覆盖写",
                     "对外发送", "生产配置", "迁移", "回滚", "重建")
ENTRY_KEY = "入口判定"
ENTRY_REQUIRED = ("category", "distribution", "confidence", "dimensions", "ambiguity", "route_hint")
ENTRY_DIMS = ("D1", "D2", "D3", "D4", "D5")
METHOD_KEY = "方法选用"
METHOD_REQUIRED = ("gap_class", "candidates", "needs_tool", "confidence", "route_hint")
METHOD_GAP_CLASSES = ("知识", "算力", "事实", "手脚")
METHOD_SAMPLE_BAND = 0.95
# v4.5.0：retrieval-judge（检索·快判）—— 与上组同构；契约见 references/retrieval-judge.md
RETRIEVAL_KEY = "检索判定"
RETRIEVAL_REQUIRED = ("source_class", "candidates", "needs_retrieval", "confidence", "route_hint")
RETRIEVAL_SOURCE_CLASSES = ("本地资产", "历史留痕", "知识库", "技能手册", "联网")
RETRIEVAL_SAMPLE_BAND = 0.95
# v4.7.0：homework-judge（模式选用 · 快判）—— 与上组同构；契约见 references/homework-judge.md
#   ⚠️ `HOMEWORK_MODES` 是「**模式选用**」枚举，与 `VALID_CATEGORY`（**主类**三态）是**两个物理量** ——
#     二者字形相近但语义无关（一个是"这次产出什么"，一个是"要不要叠加作业模式"），
#     **不得合并、不得互相推导**；口径守卫「作业模式」项与 data-model.md 镜像同源。
#   机检落点：`checks.py plan` 检查项 18（结构合法 + `needs_homework` 派生字段自洽，缺省 WARN、
#     填写则非法即 FAIL）、检查项 19（抽样人审指路，只 WARN）；口径守卫见 `checks.py skill`。
HOMEWORK_KEY = "作业判定"
HOMEWORK_REQUIRED = ("mode", "distribution", "confidence", "dimensions", "ambiguity", "route_hint")
HOMEWORK_MODES = ("作业题", "讲解题", "非作业")
HOMEWORK_DIMS = ("W1", "W2", "W3", "W4", "W5")
HOMEWORK_SAMPLE_BAND = 0.95
SEDIMENT_TOKENS = ("沉淀", "复盘", "sediment", "metrics")
_TRACE_HINT = ("补救：每步执行后 `checks.py trace <plan> --step <id> --action <摘要>`；"
               "收尾 `checks.py metrics <plan> --finalize`")
PLAT_MODULES = {
    "fcntl": "POSIX", "termios": "POSIX", "pty": "POSIX", "pwd": "POSIX", "grp": "POSIX",
    "syslog": "POSIX", "resource": "POSIX", "readline": "POSIX", "crypt": "POSIX",
    "msvcrt": "Windows", "winreg": "Windows", "_winreg": "Windows", "winsound": "Windows",
    "win32api": "Windows", "win32con": "Windows", "pywin32": "Windows", "pythoncom": "Windows",
}
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
PLAT_ALLOW_TOKEN = "platform-check:allow"

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
       消灭"同源只靠注释声明、不靠测试保证"。覆盖 8 个物理量：模型档位 / 步骤状态 / 能力类 /
       重规划触发 / 熔断状态 / 反思触发 / 终止策略 / 提交类型（v4.6.0 新增，三源含工具侧常量）。
       **解析不到即 FAIL**（守着一条读不到的规则等于没有规则）。
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
    14. 方法选用（v4.4.0）：meta「方法选用」可选 —— 阶段 3 第②步 method-judge 的产出，
        完整契约见 references/method-judge.md。**整段缺省 → WARN**（向后兼容旧 plan，
        **不追认历史计划**）；一旦填写须结构合法（gap_class ∈ 知识/算力/事实/手脚 及其 '+' 组合、
        candidates 为含 tool/fit_score 的列表、needs_tool 为 bool、confidence ∈ [0,1]、
        route_hint 非空），非法即 FAIL。
        ⚠️ **它不是门禁**：confidence 由模型自填、校准无法被机器证明（手册 §10 原样写明）。
    15. 方法选用抽样人审（v4.4.0）：**非门禁，只指路** —— 当 `meta.方法选用` 存在
        `needs_tool=true` 或 `confidence < 0.95` 的条目时，WARN 列出建议抽样的条目；
        均不满足则 OK。契约 §10 把「工具选用↔人工复核**一致率**」列为**人审**信号，本项
        只把**抽样池**指出来，**判定靠人**（机器无法判"选得对不对"）；未证实前只报
        **一致率**、**不声称准确率**。

状态取值: OK / FAIL / SKIP / **WARN**（WARN 只提示、不计入 FAIL，也不改变退出码）

退出码: 0 = 全部通过；1 = 有 FAIL（不可交付）；2 = 用法错误
"""
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

def _capability_ok(cap: str | None) -> bool:
    if not cap or not str(cap).strip():
        return False
    parts = [p.strip() for p in str(cap).split("+")]
    return bool(parts) and all(p in VALID_CAPABILITY for p in parts)

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

def _jsonl_append(path: Path, rec: dict) -> None:
    """追加一行 jsonl，目录不存在则建。**追加不覆盖**（与 mark/decide/revise 同风格）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def _task_dir(plan_path: Path) -> Path:
    return plan_path if plan_path.is_dir() else plan_path.parent

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
