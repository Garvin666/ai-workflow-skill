# -*- coding: utf-8 -*-
"""checks 口径守卫层：枚举解析与跨文件同源校验

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
from checks_core import (  # noqa: F401
    VALID_CAPABILITY,
    VALID_FUSE,
    VALID_MODEL_TIERS,
    VALID_REFLECT_TRIGGER,
    VALID_STATUS,
    VALID_TERMINATION,
    VALID_COMMIT_TYPES,
    VALID_TRIGGER,
    HOMEWORK_MODES,
    _BARE_CELL,
    _DECL_BEGIN,
    _DECL_END,
    _DeclError,
    _SEP_CELL,
    _norm_cell,
    _norm_cell_full,
    fail,
    ok,
)

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

def _p_commit_types(text: str) -> set:
    """Git 提交类型（v4.6.0）—— **一个物理量、两种载体、三处来源**：

      · **手册表格**（`references/git-conventions.md` §3.2 / `references/data-model.md` §2.2）：
        `| \\`feat\\` | 新增功能 |` —— 首格是**反引号包裹的小写词**；
      · **工具常量**（`scripts/git_check.py`）：`COMMIT_TYPES = ("feat", "fix", …)` ——
        该脚本要独立分发到 ai-workflow-tools，刻意不 import 技能本体，故成第二处代码常量。

    两种格式都读、取并集 —— 任一载体多写/写错一个取值，并集即变大 → FAIL。

    ⚠️ **并集模型的固有边界：多写会 FAIL，"少写"不会** —— 若某处**漏掉**一个合法类型
    （例如手册只剩 3 项、常量仍 4 项），并集仍为 4 项 → 判绿。这是本表与既有 7 项共有的
    覆盖边界，如实登记，**不声称"全向覆盖"**。

    ⚠️ **手册侧为什么锚定表头、而不像其他 7 项那样"全文件扫格式"**：反引号小写词在本源里
    **不唯一** —— `git-conventions.md` §2.1 的分支职责表首格同样是 `` `main` `` / `` `dev` `` /
    `` `exp-xxx` ``。首版（全文件扫）实测即把这三个分支名并进了提交类型集合：
    `解析得 dev/docs/exp-xxx/feat/fix/main/refactor ≠ 代码常量 docs/feat/fix/refactor`。
    修法取**结构性锚定**（表头 `| 类型 | 含义 |` 唯一），而不是"约定别处别用这种格式" ——
    后者是纪律，前者是判据。**这条首版缺陷由守卫自己在第一次运行中报出，未流到交付。**

    ⚠️ **为什么手册侧用反引号而非加粗**：`references/data-model.md` 同时是「模型档位」守卫的源，
    其解析器 `_p_tiers` 只认 `| **小写词** |`。提交类型表若沿用加粗，会把
    feat/fix/refactor/docs 并进**档位集合** → 假 FAIL。故本表自建立起就用反引号，与之正交。
    """
    vals: set = set()
    m = re.search(r"^\|\s*类型\s*\|\s*含义\s*\|\s*$", text, re.M)
    if m:
        block: list[str] = []
        for ln in text[m.end():].splitlines():
            if ln.strip().startswith("|"):
                block.append(ln)
            elif block:
                break
        vals |= set(re.findall(r"^\|\s*`([a-z][a-z0-9-]*)`\s*\|", "\n".join(block), re.M))
    m2 = re.search(r"^COMMIT_TYPES\s*=\s*\(([^)]*)\)", text, re.M)
    if m2:
        vals |= {x.strip().strip("\"'") for x in m2.group(1).split(",") if x.strip()}
    return vals

def _p_homework_modes(text: str) -> set:
    """作业模式（v4.7.0）—— **一个物理量、三种载体**：

      · **手册表格**（`references/homework-judge.md` §1 与 `references/data-model.md` §2.2 镜像）：
        `| **作业题** | …` —— 首格是**加粗中文词**。
      · **模板 json**（`scripts/judges.json` 的 `homework_judge.mode.criteria`）：走 json 解析。

    ⚠️ **为什么必须锚定表头**：`| **中文加粗** |` 在 `data-model.md` 里**不唯一**
    （档位表 / 能力表 / 熔断表 / 作业模式表都用加粗首格）。沿用"全文件扫格式"会把**别的表**首格
    并进来 → 假 FAIL。这与 v4.6.0「提交类型」首版踩的坑**同型**（那边并进的是分支名 `main/dev/exp-xxx`），
    修法同取**结构性锚定**（表头 `| 模式 | 含义 |` 唯一），而不是"约定别处别用加粗"。

    ⚠️ **另一侧的陷阱（本节特意避开）**：本表与「模型档位」守卫同处 `data-model.md`，
    而 `_p_tiers` 只认 `| **小写英文词** |` —— 本表用**中文**加粗，与之**正交**，故不会互相污染。
    反之若把作业模式写成英文小写词，就会被并进档位集合（假 FAIL）。

    ⚠️ 并集模型固有边界（与既有 8 项共有，如实登记）：**"多写"会 FAIL，"少写"不会**。
    """
    vals: set = set()
    m = re.search(r"^\|\s*模式\s*\|\s*含义\s*\|\s*$", text, re.M)
    if m:
        block: list[str] = []
        for ln in text[m.end():].splitlines():
            if ln.strip().startswith("|"):
                block.append(ln)
            elif block:
                break
        vals |= {x.strip() for x in re.findall(r"^\|\s*\*\*([^*|]+?)\*\*\s*\|", "\n".join(block), re.M)}
    # judges.json 分支：json 解析成功且含 homework_judge 才取值；md 文件解析失败 → 静默跳过
    # （源文件读不到由 _check_parity 的主循环兜，不在这里造第二个 FAIL 源）
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return vals
    if isinstance(data, dict) and isinstance(data.get("homework_judge"), dict):
        crit = (data["homework_judge"].get("mode") or {}).get("criteria") or {}
        vals |= set(crit)
    return vals

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

PARITY_ITEMS = (
    # v4.4.0+（P0-1，2026-09-21）：每项源规格**追加 `references/data-model.md`** ——
    # 把该文件作为各枚举的**受守卫镜像**（中心注册表）。多源取并集比对，故 data-model.md
    # 里多写/写错一个取值 → 并集变大 → FAIL；这是「枚举集中 + 可机检」的落地。
    # ⚠️ 多源（tuple）时 is_single=False，单个文件缺失不单独 FAIL（只由"全部缺失"分支兜底），
    #    这与 v4.2.0 为「入口判定主类」引入多源的语义一致。
    ("模型档位", ("references/routing-guide.md", "references/data-model.md"), _p_tiers, VALID_MODEL_TIERS),
    ("步骤状态", ("assets/plan-template.yaml", "references/data-model.md"), _p_status, VALID_STATUS),
    ("能力类", ("references/capability-routing.md", "references/data-model.md"), _p_caps, VALID_CAPABILITY),
    ("重规划触发", ("references/adaptive-planning.md", "references/data-model.md"), _p_triggers, VALID_TRIGGER),
    ("熔断状态", ("SKILL.md", "references/data-model.md"), _p_fuse, VALID_FUSE),
    ("反思触发", ("references/reflection-retry.md", "references/data-model.md"), _p_reflect_trigger, VALID_REFLECT_TRIGGER),
    ("终止策略", ("references/reflection-retry.md", "references/data-model.md"), _p_reflect_term, VALID_TERMINATION),
    # v4.6.0 新增「提交类型」：**三源**（含工具侧脚本常量）—— 因 `git_check.py` 要独立分发到
    #   ai-workflow-tools，刻意不 import checks_core，于是「提交类型」在代码里存在**两处常量**。
    #   三源并集比对把该漂移纳入射程：任一处多写/写错一个取值 → 并集变大 → FAIL。
    ("提交类型", ("references/git-conventions.md", "references/data-model.md", "scripts/git_check.py"),
     _p_commit_types, VALID_COMMIT_TYPES),
    # v4.7.0 新增「作业模式」：**三源**（手册 + 受守卫镜像 + 模板 json）——
    #   `judges.json` 是 Laya 侧 questions 模板，其 `mode.criteria` 的键就是该枚举的**可执行副本**；
    #   不纳入源，则"改手册忘改模板"不会报错（而模板错了会让 Laya 判出枚举外取值）。
    ("作业模式", ("references/homework-judge.md", "references/data-model.md", "scripts/judges.json"),
     _p_homework_modes, HOMEWORK_MODES),
    # ⚠️「入口判定主类」**不在本表内**（v4.2.0 第五轮换口径后由 `_check_category_decl` 单独判）：
    # 本表的模型是「若干源 → 一个解析器 → 一个集合」，多源时取并集比对；而主类那项需要
    # **跨文件的唯一性判定（源规格面内）**（声明块须恰一处），并集模型表达不了它 ——
    # 两个文件各写一份相同集合时并集仍然相等，于是「重复声明」这一错法会漏判。
)
