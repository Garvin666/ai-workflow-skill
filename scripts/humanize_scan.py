#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[自研工具] 名称：humanize_scan
用途：对「面向人阅读的散文正文」跑去 AI 味判据（machine 档），并对改写前后做事实保真比对。
      它是 ai-workflow 阶段 3 质检 / 阶段 5 交付前的机器门禁，与 references/humanize-rubric.yaml 同源。
适用场景：报告、方案、文档类交付物（.md/.txt 散文正文）；不适用于代码、JSON、YAML、数据表。
仓库：https://github.com/Garvin666/ai-workflow-tools（待推送）

用法:
  python humanize_scan.py --text draft.md [--rubric humanize-rubric.yaml] [--json]
  python humanize_scan.py --text final.md --gate            # 有 FAIL 即 exit 1
  python humanize_scan.py --diff-fidelity before.md after.md
  python humanize_scan.py --audit                           # 判据集↔实现同源自检
  python humanize_scan.py --selftest
退出码: 0 = 无 FAIL（或 selftest 全过）；1 = 有 FAIL（或 selftest 未过）；2 = 用法/IO 错误

设计口径（三条，不得违背）:
  1. PASS / FAIL / SKIP 严格分开 —— SKIP（未检测）不得并入通过率。
  2. FAIL 档只收「高置信、低误伤」的表层特征；可能是正当用法的（破折号、四字格、AI 高频词）一律只 WARN。
  3. 不得为消 FAIL 改阈值 —— 改阈值即改判据，须留痕并配阴性对照。

⚠️ 诚实边界（原样继承 humanizer 上游声明）：本工具**不判作者身份、不保证通过任何 AI 检测器**；
   模式命中 ≠ AI 生成（「不是 X 而是 Y」「破折号」「四字格」在人类写作里正当存在）；
   `--diff-fidelity` 只证「没改坏事实」，**不证**「读起来更像人」。
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

# ---------------------------------------------------------------- 保护区域
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
FENCED = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
URL = re.compile(r"https?://\S+")
# ⚠️ v1.0.1 修一处**真缺陷**（由「产物行号错位」暴露，非夹具跑得出 —— 夹具太短）：
#   原 `MD_LINK` / `HTML_TAG` 的字符类**允许跨行**（`[^\]]*` / `[^>]+`），于是一处**不成对的尖括号**
#   （实测：方案 §7.1 表格里的 `**<**`）会把**后面 15 行正文整体吞成全角空格**。双重后果：
#     ① **行号错位** —— `snippet` 取 `orig_lines[ln-1]`，错位后"证据可定位"失效（报的行不是命中的行）；
#     ② **漏检** —— 被吞掉的那 15 行正文**根本不被扫描**，且扫描器**没有任何信号**表明它漏了。
#   这正是「静默失真」的教科书形态。修法：给两个字符类都加 `\n` 约束 ——
#   **保护性替换只在本行内生效，绝不跨行吞内容**。同类清扫：`INLINE_CODE` / `URL` 本就不含 `\n`，已安全。
MD_LINK = re.compile(r"\[[^\]\n]*\]\([^)\n]*\)")
HTML_TAG = re.compile(r"<[^>\n]+>")


def strip_protected(text: str):
    """剥掉代码块/行内代码/URL/front matter/HTML 标签 —— 这些按 humanizer 原文须保持原样。
    返回 (可扫正文, 原文行表)。行号按原文计，保证证据可定位。"""
    lines = text.split("\n")
    masked = FRONT_MATTER.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    masked = FENCED.sub(lambda m: "\n" * m.group(0).count("\n"), masked)
    masked = INLINE_CODE.sub(lambda m: "\u3000" * len(m.group(0)), masked)
    masked = MD_LINK.sub(lambda m: "\u3000" * len(m.group(0)), masked)
    masked = URL.sub(lambda m: "\u3000" * len(m.group(0)), masked)
    masked = HTML_TAG.sub(lambda m: "\u3000" * len(m.group(0)), masked)
    return masked, lines


# ---------------------------------------------------------------- 判据表（machine 档）
# id 与 references/humanize-rubric.yaml 的 machine 档规则 id 必须同源（--audit / --selftest 校验）
RULES = [
    # ---- FAIL 档：高置信、低误伤 ----
    dict(id="H01", group="E", name="客服腔", level="FAIL",
         pats=[r"好问题[！!]", r"很好的问题", r"希望这对您有帮助", r"希望这能帮到你",
               r"希望这些内容对你(有)?帮助", r"如有(任何)?疑问[，,]?请(随时)?", r"感谢您的阅读"],
         source="humanizer-zh §E.22"),
    dict(id="H02", group="F", name="套话收尾", level="FAIL",
         pats=[r"让我们拭目以待", r"期待更多可能", r"未来可期", r"值得期待",
               r"总而言之[，,]\s*让我们"],
         source="humanizer-zh §F.31"),
    dict(id="H03", group="D", name="emoji 装饰标题", level="FAIL",
         pats=[r"^#{1,6}\s*[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u2B00-\u2BFF]+"],
         source="humanizer-zh §D.20", line_only=True),
    dict(id="H04", group="D", name="中文正文里的英文直引号", level="FAIL",
         pats=[r"[\u4e00-\u9fff]\"[^\"\n]{1,40}\""],
         source="humanizer-zh §D.21"),
    dict(id="H05", group="F", name="「随着…的发展」式空转开头", level="FAIL",
         pats=[r"在[^，。\n]{0,15}(时代背景|大背景|浪潮|大潮)下", r"^随着[^，。\n]{0,20}(的发展|的进步|的推进|的演进)"],
         source="humanizer-zh §F.30"),
    dict(id="H06", group="C", name="意义拔高", level="FAIL",
         pats=[r"标志着[^，。\n]{0,20}(新时代|新纪元|新篇章|里程碑)",
               r"翻开了[^，。\n]{0,10}新(的)?篇章"],
         source="humanizer-zh §C.13"),
    dict(id="H07", group="A", name="起跑式铺垫", level="FAIL",
         pats=[r"让我们(深入|一起)?(看看|来看看|探讨|了解|聊聊)",
               r"以下是你(需要|必须)知道的", r"接下来我们(将)?(看看|探讨|聊聊)"],
         source="humanizer-zh §A.4"),
    dict(id="H08", group="C", name="句尾补充式拔高", level="FAIL",
         pats=[r"彰显了[^，。\n]{0,15}(不懈追求|卓越追求|深厚底蕴|非凡实力)",
               r"充分(展现|体现)了[^，。\n]{0,15}的(实力|魅力|担当)",
               r"堪称[^，。\n]{0,12}(梦想|理想)(天堂|之选)"],
         source="humanizer-zh §C.15/§C.16"),
    # ---- WARN 档：可能是正当用法，只提示不阻断 ----
    dict(id="H09", group="C", name="AI 高频词", level="WARN",
         pats=[r"赋能", r"至关重要", r"深入探讨", r"无缝", r"闭环", r"全方位", r"多维度",
               r"抓手", r"护城河", r"底层逻辑", r"组合拳"],
         source="humanizer-zh §C.12"),
    dict(id="H12", group="F", name="「进行＋动词」", level="WARN",
         pats=[r"进行(了|着)?(测试|优化|调整|分析|处理|讨论|研究|梳理|检查|评估|验证)"],
         source="humanizer-zh §F.27"),
    dict(id="H13", group="B", name="强凑三段式", level="WARN",
         pats=[r"(带来了|实现了|开启了)[^。\n]{0,40}、[^。\n]{0,20}、"],
         source="humanizer-zh §B.6"),
]

# ---- 密度类（需全文统计，单独实现）----
DENSITY = [
    dict(id="H10", group="B", name="破折号当万能连接", level="WARN", unit="——",
         max_per_500=1.0, source="humanizer-zh §B.8"),
    dict(id="H11", group="D", name="粗体当装饰", level="WARN", unit="bold",
         max_per_para=1.5, source="humanizer-zh §D.19"),
]

# ---- SKIP 档：需语义判断，机器判不了，必须显式登记为人审点 ----
SKIP_RULES = [
    dict(id="S01", name="不是 X，而是 Y（假对比）", source="humanizer-zh §A.1"),
    dict(id="S02", name="单句收尾与戏剧性碎片", source="humanizer-zh §A.2"),
    dict(id="S03", name="格言与伪深度", source="humanizer-zh §A.3"),
    dict(id="S04", name="与假想敌辩论", source="humanizer-zh §A.5"),
    dict(id="S05", name="句式开头复读", source="humanizer-zh §B.7"),
    dict(id="S06", name="限定词堆叠", source="humanizer-zh §B.9"),
    dict(id="S07", name="生造复合词与连接号", source="humanizer-zh §B.10"),
    dict(id="S08", name="被动与缺主语", source="humanizer-zh §C.11"),
    dict(id="S09", name="模糊关联", source="humanizer-zh §C.14"),
    dict(id="S10", name="借权威", source="humanizer-zh §C.17"),
    dict(id="S11", name="回避「是／有」", source="humanizer-zh §C.18"),
    dict(id="S12", name="知识边界免责与猜测填充", source="humanizer-zh §E.23"),
    dict(id="S13", name="首句复读标题", source="humanizer-zh §E.24"),
    dict(id="S14", name="谈论上一稿", source="humanizer-zh §E.25"),
    dict(id="S15", name="层叠的「的」", source="humanizer-zh §F.26"),
    dict(id="S16", name="被字句堆叠", source="humanizer-zh §F.28"),
    dict(id="S17", name="四字词排比", source="humanizer-zh §F.29"),
]

# ---------------------------------------------------------------- 事实保真类目
FIDELITY = {
    "数字": re.compile(r"\d+(?:\.\d+)?\s*(?:%|‰|MB|GB|KB|TB|ms|s|秒|分钟|小时|天|年|月|元|万|亿|倍|个|条|次|项|人)?"),
    "否定": re.compile(r"尚未|从未|不再|无法|不能|不得|禁止|没有|不是|不会|未能|不|无|未|没|非|否"),
    "限定": re.compile(r"可能|或许|也许|据称|据说|计划|拟|正在|尚未|仅|超过|至少|大约|估计|预计|有望|尝试|部分"),
    "归因": re.compile(r"认为|表示|指出|根据|据|称|报告|调研|统计"),
}


def normalize_number(s: str) -> str:
    return re.sub(r"\s+", "", s)


def fidelity_profile(text: str):
    prof = {}
    for cat, rx in FIDELITY.items():
        if cat == "数字":
            items = [normalize_number(m.group(0)) for m in rx.finditer(text)]
        else:
            items = [m.group(0) for m in rx.finditer(text)]
        prof[cat] = Counter(items)
    return prof


def diff_fidelity(before: str, after: str):
    b, a = fidelity_profile(before), fidelity_profile(after)
    report = {}
    for cat in FIDELITY:
        missing = b[cat] - a[cat]
        added = a[cat] - b[cat]
        if missing or added:
            report[cat] = {"缺失": dict(missing), "新增": dict(added)}
    return report


# ---------------------------------------------------------------- 扫描
def scan(text: str):
    body, orig_lines = strip_protected(text)
    lines = body.split("\n")
    hits = []
    seen = set()
    for rule in RULES:
        for ln, line in enumerate(lines, start=1):
            for p in rule["pats"]:
                rx = re.compile(p)
                m = rx.search(line)
                if not m:
                    continue
                key = (rule["id"], ln)
                if key in seen:      # 同一规则同一行只计一次（防计数虚高 —— 静默失真的一种）
                    continue
                seen.add(key)
                frag = orig_lines[ln - 1].strip() if ln - 1 < len(orig_lines) else line.strip()
                hits.append(dict(id=rule["id"], name=rule["name"], level=rule["level"],
                                 line=ln, snippet=frag[:80], source=rule["source"]))
    # 密度类
    total_chars = len(re.sub(r"\s", "", body))
    for rule in DENSITY:
        if rule["unit"] == "——":
            n = body.count("——")
            per = n / max(total_chars / 500.0, 1.0)
            if n > 2 and per > rule["max_per_500"]:
                hits.append(dict(id=rule["id"], name=rule["name"], level=rule["level"], line=0,
                                 snippet=f"「——」出现 {n} 次 / 每 500 字约 {per:.1f} 次",
                                 source=rule["source"]))
        else:
            paras = [p for p in body.split("\n\n") if p.strip()]
            n = len(re.findall(r"\*\*[^*\n]+\*\*", body))
            if paras and n / len(paras) > rule["max_per_para"]:
                hits.append(dict(id=rule["id"], name=rule["name"], level=rule["level"], line=0,
                                 snippet=f"粗体 {n} 处 / {len(paras)} 段 = {n/len(paras):.2f} 处每段",
                                 source=rule["source"]))
    return hits


def summarize(hits):
    fails = [h for h in hits if h["level"] == "FAIL"]
    warns = [h for h in hits if h["level"] == "WARN"]
    return fails, warns


# ---------------------------------------------------------------- 输出
def render(hits, path, show_warn=True):
    fails, warns = summarize(hits)
    out = []
    out.append(f"扫描对象: {path}")
    out.append(f"  FAIL = {len(fails)}  |  WARN = {len(warns)}  |  SKIP = {len(SKIP_RULES)}（未检测，不计入通过率）")
    for label, group in (("FAIL", fails), ("WARN", warns)):
        if not group:
            continue
        if label == "WARN" and not show_warn:
            continue
        out.append(f"  [{label}]")
        for h in group:
            loc = f"L{h['line']}" if h["line"] else "全文"
            out.append(f"    {h['id']} {h['name']} @{loc} —— {h['snippet']}")
    return "\n".join(out)


# ---------------------------------------------------------------- 同源校验
def audit_parity(rubric_path):
    """朴素解析 rubric 的 (id, judgeability)，与实现集合双向比对。"""
    if not os.path.isfile(rubric_path):
        return [f"判据集不存在: {rubric_path}"]
    cur, decl = None, {}
    with open(rubric_path, encoding="utf-8-sig") as f:
        for line in f:
            m = re.match(r"\s*-\s*id:\s*([A-Za-z0-9_]+)", line)
            if m:
                cur = m.group(1)
            m2 = re.match(r"\s*judgeability:\s*(\w+)", line)
            if m2 and cur:
                decl[cur] = m2.group(1)
    impl = {r["id"] for r in RULES} | {r["id"] for r in DENSITY}
    rubric_machine = {k for k, v in decl.items() if v == "machine"}
    problems = []
    for i in sorted(impl - rubric_machine):
        problems.append(f"实现有、判据集 machine 档无: {i}")
    for i in sorted(rubric_machine - impl):
        problems.append(f"判据集 machine 档有、实现无: {i}")
    return problems


# ---------------------------------------------------------------- selftest
def selftest(rubric_path):
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "humanize")
    cases = []

    def load(name):
        with open(os.path.join(base, name), encoding="utf-8-sig") as f:
            return f.read()

    # A: AI 味浓 → FAIL >= 5
    fa = summarize(scan(load("ai-flavored.md")))[0]
    cases.append(("A ai-flavored.md  FAIL>=5", len(fa) >= 5, f"FAIL={len(fa)}"))
    # B: 人工化 → FAIL == 0
    fb = summarize(scan(load("humanized.md")))[0]
    cases.append(("B humanized.md    FAIL==0", len(fb) == 0, f"FAIL={len(fb)}"))
    # D: 正当模式 → FAIL == 0（防误伤）
    fd = summarize(scan(load("legit-pattern.md")))[0]
    cases.append(("D legit-pattern.md FAIL==0", len(fd) == 0, f"FAIL={len(fd)}"))
    # C: 事实篡改 → fidelity 必须报差异
    rep = diff_fidelity(load("fidelity-before.md"), load("fidelity-after.md"))
    cases.append(("C fidelity 篡改被捕获", len(rep) > 0, f"差异类目={sorted(rep)}"))
    # 反向：未篡改 → 必须零差异（防恒红）
    rep2 = diff_fidelity(load("fidelity-before.md"), load("fidelity-before.md"))
    cases.append(("C' fidelity 同文零差异", len(rep2) == 0, f"差异类目={sorted(rep2)}"))
    # 同源
    prob = audit_parity(rubric_path)
    cases.append(("P 判据集↔实现同源", not prob, "一致" if not prob else "; ".join(prob)))

    lines = ["=== humanize_scan --selftest ===", ""]
    ok = True
    for name, passed, detail in cases:
        lines.append(f"  [{'PASS' if passed else 'FAIL'}] {name}  ({detail})")
        ok = ok and passed
    lines.append("")
    lines.append(f"结论: {'全部符合期望' if ok else '存在未达期望项'}（共 {len(cases)} 项）")
    lines.append("")
    lines.append("--- 夹具 A 命中明细（证明判据有牙齿）---")
    lines.append(render(scan(load("ai-flavored.md")), "ai-flavored.md"))
    lines.append("")
    lines.append("--- 夹具 D 命中明细（证明不误伤：FAIL 应为 0，WARN 可有）---")
    lines.append(render(scan(load("legit-pattern.md")), "legit-pattern.md"))
    lines.append("")
    lines.append("--- 夹具 C 保真差异明细 ---")
    lines.append(json.dumps(diff_fidelity(load("fidelity-before.md"), load("fidelity-after.md")),
                            ensure_ascii=False, indent=2))
    print("\n".join(lines))
    return 0 if ok else 1


def _default_rubric():
    """判据集默认位置：技能内 `references/humanize-rubric.yaml`（本脚本在 `scripts/` 下）。"""
    return os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "references", "humanize-rubric.yaml"))


def main():
    ap = argparse.ArgumentParser(description="去 AI 味判据校验器（machine 档 + 事实保真比对）")
    ap.add_argument("--text")
    ap.add_argument("--rubric", default=_default_rubric())
    ap.add_argument("--gate", action="store_true", help="有 FAIL 即 exit 1")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--diff-fidelity", nargs=2, metavar=("BEFORE", "AFTER"))
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest(args.rubric))
    if args.audit:
        prob = audit_parity(args.rubric)
        print("判据集↔实现同源: " + ("一致" if not prob else "不一致"))
        for p in prob:
            print("  - " + p)
        sys.exit(1 if prob else 0)
    if args.diff_fidelity:
        try:
            with open(args.diff_fidelity[0], encoding="utf-8-sig") as f:
                before = f.read()
            with open(args.diff_fidelity[1], encoding="utf-8-sig") as f:
                after = f.read()
        except OSError as e:
            print(f"IO 错误: {e}", file=sys.stderr)
            sys.exit(2)
        rep = diff_fidelity(before, after)
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        else:
            if not rep:
                print("事实保真: PASS（数字/否定/限定/归因 零丢失、零新增）")
            else:
                print("事实保真: FAIL")
                for cat, d in rep.items():
                    print(f"  [{cat}] 缺失={d['缺失']}  新增={d['新增']}")
        sys.exit(1 if rep else 0)
    if not args.text:
        ap.print_help()
        sys.exit(2)
    try:
        with open(args.text, encoding="utf-8-sig") as f:
            text = f.read()
    except OSError as e:
        print(f"IO 错误: {e}", file=sys.stderr)
        sys.exit(2)
    hits = scan(text)
    fails, warns = summarize(hits)
    if args.json:
        print(json.dumps(dict(fail=fails, warn=warns, skip=SKIP_RULES), ensure_ascii=False, indent=2))
    else:
        print(render(hits, args.text))
    sys.exit(1 if (args.gate and fails) else 0)


if __name__ == "__main__":
    main()
