# -*- coding: utf-8 -*-
"""[自研工具] iface_lint.py

用途：从 `argparse` 定义静态反射自研脚本的对外接口（子命令 / 参数 / 退出码 / 描述），
      生成接口清单，并按契约校验实现与文档同源。
适用场景：修改任一 `scripts/*.py` 的 CLI 参数、退出码或新增脚本后，作为接口契约的机器门禁；
          新增脚本时用它确认「描述齐、退出码合规、根路径参数已登记、两处文档有登记」。
          契约语义见 `references/interface-contract.md` —— 本工具只执行校验，**不定义语义**。

仓库：https://github.com/Garvin666/ai-workflow-tools/blob/main/scripts/iface_lint.py

用法：
  --check      按契约 C1–C5 校验（rc=0 全过 / rc=1 有 FAIL）
  --text       打印人读接口清单
  --json       输出机器可读接口清单（stdout 只有 JSON）
  --selftest   自检：临时目录造假脚本，验证每条判据该红就红

设计边界（如实登记）：
  · 纯静态 AST 反射，**不执行**被检脚本（执行会触发网络与写盘副作用）。
  · 退出码只统计 `main()` 函数体与 `__main__` 块内的 return/exit —— 函数内部的
    `return 15`（退避秒数）、`return 8731`（服务端口）不是退出码。首版曾把它们误认成
    退出码，这条射程是踩过之后补的。
  · 只判结构，不判语义合理性；C5 只判字面覆盖。
"""
import argparse
import ast
import json
import re
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
OPS_DOC = SKILL_ROOT / "references" / "ops.md"
SKILL_DOC = SKILL_ROOT / "SKILL.md"

#: 退出码契约（§1）。四码按「结论是否可得」划分，不按严重程度划分。
EXIT_CODES = {
    0: "成功且结论为通过",
    1: "得出的结论是不通过",
    2: "用法错误或前置条件不满足",
    3: "无法判定（能力缺失/外部不可用/fail-closed）",
}
#: 根路径参数语义表（§2.2）。登记制：未登记的新同名语义判 FAIL。
ROOT_PARAMS = {
    "--base": "相对路径解析基准",
    "--root": "被操作对象的根目录",
    "--workspace": "主扫描根之外的额外工作区",
    # 以下为历史命名，语义同「被操作对象的根目录」；新增脚本请用 --root 或 --base。
    "--skill-dir": "被操作对象的根目录（历史命名：单个技能目录）",
    "--skills-dir": "被操作对象的根目录（历史命名：技能库根）",
    "--kb-root": "被操作对象的根目录（历史命名：知识库根）",
    "--scripts-dir": "被操作对象的根目录（历史命名：脚本目录）",
}
#: 允许出现在参数名里的「根路径类」词汇；出现即须在上表登记。
#: 匹配规则：去掉前导 `--` 后**等于**某词，或**以**某词结尾（`--datadir` / `--output-dir` 均命中）。
#: 首版用「按 `-` 切分取首 token」的规则，`--datadir` 被漏判 —— 单token 复合词是常见写法，
#: 故改为后缀匹配；`--dry-run` / `--patch` 不以任何词结尾，不会误伤。
ROOT_PARAM_HINTS = ("base", "root", "workspace", "dir", "path")


def _is_root_like(arg: str) -> bool:
    stem = arg.split("=")[0].lstrip("-").lower()
    return any(stem == h or stem.endswith(h) for h in ROOT_PARAM_HINTS)


def _unregistered_root_args(args) -> list:
    """返回「看起来是根路径、但没在 ROOT_PARAMS 里登记」的参数名。"""
    return [a for a in args if _is_root_like(a) and a not in ROOT_PARAMS]


def _own_nodes(node):
    """遍历节点自身，但不进入嵌套的函数/类定义（避免把辅助函数的 return 当退出码）。"""
    for child in ast.iter_child_nodes(node):
        yield child
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield from _own_nodes(child)


def _main_scopes(tree):
    """返回 main 路径上的节点：`def main(...)` 与 `if __name__ == "__main__":` 块。"""
    scopes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            scopes.append(node)
        elif isinstance(node, ast.If):
            try:
                test = ast.unparse(node.test)
            except Exception:               # pragma: no cover - 老版本兜底
                test = ""
            if "__main__" in test:
                scopes.append(node)
    return scopes


def _const_str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def scan_script(path: Path) -> dict:
    """静态反射单个脚本的接口面。解析失败时返回 error 字段，不抛异常。"""
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except (OSError, SyntaxError) as exc:
        return {"script": path.name, "error": str(exc), "executable": False}

    descs, subcmds, args, nohelp = [], [], [], []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = getattr(fn, "attr", None) or getattr(fn, "id", None)
        if name == "ArgumentParser":
            for kw in node.keywords:
                if kw.arg == "description":
                    s = _const_str(kw.value)
                    if s and s.strip():
                        descs.append(s.strip())
        elif name == "add_argument":
            if not node.args:
                continue
            arg = _const_str(node.args[0])
            if not arg or not arg.startswith("-"):
                continue
            args.append(arg)
            kws = {kw.arg: kw for kw in node.keywords}
            if "help" not in kws or _const_str(kws["help"].value) in (None, ""):
                nohelp.append(arg)
        elif name == "add_parser":
            if node.args:
                sub = _const_str(node.args[0])
                if sub:
                    subcmds.append(sub)

    exits = set()
    for scope in _main_scopes(tree):
        for node in _own_nodes(scope):
            if isinstance(node, ast.Return):
                v = node.value
                if isinstance(v, ast.Constant) and isinstance(v.value, int) \
                        and not isinstance(v.value, bool):
                    exits.add(v.value)
            elif isinstance(node, ast.Call):
                fn = node.func
                name = getattr(fn, "attr", None) or getattr(fn, "id", None)
                if name == "exit" and node.args:
                    v = node.args[0]
                    if isinstance(v, ast.Constant) and isinstance(v.value, int) \
                            and not isinstance(v.value, bool):
                        exits.add(v.value)

    return {
        "script": path.name,
        "executable": bool(_main_scopes(tree)),
        "description": descs[0] if descs else None,
        "subcommands": sorted(set(subcmds)),
        "args": sorted(set(args)),
        "args_without_help": sorted(set(nohelp)),
        "exit_codes": sorted(exits),
    }


def scan_all(scripts_dir: Path = SCRIPTS_DIR) -> dict:
    out = {}
    for p in sorted(scripts_dir.glob("*.py")):
        info = scan_script(p)
        if info.get("executable"):
            out[p.name] = info
    return out


def _check_docs(skill_root: Path):
    ops = OPS_DOC if skill_root == SKILL_ROOT else skill_root / "references" / "ops.md"
    sm = SKILL_DOC if skill_root == SKILL_ROOT else skill_root / "SKILL.md"
    ops_text = ops.read_text(encoding="utf-8") if ops.exists() else ""
    sm_text = sm.read_text(encoding="utf-8") if sm.exists() else ""
    return ops_text, sm_text


def check(skill_root: Path = SKILL_ROOT) -> list:
    """按契约 C1–C5 校验。返回 [(级别, 检查项, 说明)]，级别取 OK/FAIL/WARN。"""
    results = []
    scripts_dir = skill_root / "scripts"
    infos = scan_all(scripts_dir)
    ops_text, sm_text = _check_docs(skill_root)

    # C1 描述齐备
    bad = [n for n, i in infos.items() if not i.get("description")]
    results.append(("FAIL" if bad else "OK", "C1 接口描述齐备",
                    "缺 description：%s" % ",".join(sorted(bad)) if bad
                    else "%d 个可执行脚本均有非空 description" % len(infos)))

    # C2 退出码在契约内
    bad = []
    for n, i in infos.items():
        over = [c for c in i.get("exit_codes", []) if c not in EXIT_CODES]
        if over:
            bad.append("%s=%s" % (n, over))
    results.append(("FAIL" if bad else "OK", "C2 退出码在契约内",
                    "越界：%s（契约只收 %s）" % ("；".join(bad), sorted(EXIT_CODES)) if bad
                    else "全部 ⊆ %s" % sorted(EXIT_CODES)))

    # C3a 根路径参数已登记（门禁：新增语义必须先落契约表）
    unreg = set()
    for n, i in infos.items():
        for a in _unregistered_root_args(i.get("args", [])):
            unreg.add(a.split("=")[0])
    results.append(("FAIL" if unreg else "OK", "C3a 根路径参数已登记",
                    "未登记：%s" % ",".join(sorted(unreg)) if unreg
                    else "根路径参数 %d 类均已登记" % len(ROOT_PARAMS)))

    # C3b 参数带 help（存量欠账：首版判 WARN，不阻断。门槛待补完后再议，不预设时间表）
    nohelp = []
    for n, i in infos.items():
        for a in i.get("args_without_help", []):
            nohelp.append("%s%s" % (n, a))
    results.append(("WARN" if nohelp else "OK", "C3b 参数带 help",
                    ("缺 help %d 处（存量欠账）：%s%s" % (
                        len(nohelp), ",".join(nohelp[:6]), " …" if len(nohelp) > 6 else ""))
                    if nohelp else "全部参数带 help"))

    # C4 --json 覆盖（信息项，不作门禁）。原设计想校验「文档声明 ↔ 实现」，
    #   实测按「行内共现」抽取会产生假 FAIL（outbound_scan.py 的表格行里同时提到
    #   push_router.py 与 --json，于是被判定为"push_router 声称支持 --json"）。
    #   从自然语言文档可靠抽取接口声明需要结构化标注，本版不做 —— 宁可少一条判据，
    #   不留一条会造红色假信号的判据。见契约 §6 的同样登记。
    njson = sum(1 for i in infos.values() if "--json" in i.get("args", []))
    results.append(("OK", "C4 --json 覆盖（信息项）",
                    "%d/%d 个可执行脚本支持 --json" % (njson, len(infos))))

    # C5 文档两处登记
    miss_ops, miss_sk = [], []
    for n in infos:
        if n not in ops_text:
            miss_ops.append(n)
        if n not in sm_text:
            miss_sk.append(n)
    bad = []
    if miss_ops:
        bad.append("ops.md 缺 %s" % ",".join(sorted(miss_ops)))
    if miss_sk:
        bad.append("SKILL.md 缺 %s" % ",".join(sorted(miss_sk)))
    results.append(("FAIL" if bad else "OK", "C5 文档两处登记",
                    "；".join(bad) if bad else "%d 个脚本在 ops.md 与 SKILL.md 均有登记" % len(infos)))
    return results


def _print_text(infos: dict) -> None:
    for n, i in infos.items():
        codes = ",".join(str(c) for c in i.get("exit_codes", [])) or "-"
        subs = ",".join(i.get("subcommands", [])) or "-"
        print("%-26s 退出码=%-10s 子命令=%-28s 参数=%d" % (n, codes, subs, len(i.get("args", []))))
        print("    %s" % (i.get("description") or "(无 description)"))


def _selftest() -> int:
    """自检：临时目录造 6 个假脚本，验证 C1/C2/C3 该红就红、且射程说明成立。"""
    cases = {
        "good.py": '''import argparse, sys
def main():
    p = argparse.ArgumentParser(description="合规脚本")
    p.add_argument("--base", help="解析基准")
    p.add_argument("--verbose", action="store_true", help="详细输出")
    a = p.parse_args()
    return 0
if __name__ == "__main__":
    sys.exit(main())
''',
        "nodesc.py": '''import argparse
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--x", help="某参数")
    return 0
''',
        "badexit.py": '''import argparse, sys
def main():
    p = argparse.ArgumentParser(description="退出码越界")
    p.add_argument("--x", help="某参数")
    return 5
''',
        "badparam.py": '''import argparse
def main():
    p = argparse.ArgumentParser(description="未登记根参数")
    p.add_argument("--datadir", help="数据目录")
    return 0
''',
        "nohelp.py": '''import argparse
def main():
    p = argparse.ArgumentParser(description="缺 help")
    p.add_argument("--dry-run")
    return 0
''',
        # 射程证明：辅助函数里的整数 return 不是退出码
        "wide.py": '''import argparse, sys
def _backoff():
    return 15
def main():
    p = argparse.ArgumentParser(description="射程证明")
    p.add_argument("--base", help="解析基准")
    _backoff()
    return 0
''',
    }
    expects = {
        "good.py": {"C1": "OK", "C2": "OK", "C3": "OK"},
        "nodesc.py": {"C1": "FAIL"},
        "badexit.py": {"C2": "FAIL"},
        "badparam.py": {"C3": "FAIL"},
        "nohelp.py": {"C3": "FAIL"},
        "wide.py": {"C2": "OK"},          # return 15 不得被判为退出码
    }
    missed = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "scripts").mkdir()
        (root / "references").mkdir()
        (root / "references" / "ops.md").write_text("占位 ops\n", encoding="utf-8")
        (root / "SKILL.md").write_text("# 占位\n", encoding="utf-8")
        for name, body in cases.items():
            (root / "scripts" / name).write_text(body, encoding="utf-8")
        res = {item.split()[0]: lvl for lvl, item, _ in check(root)}
        for name, want in expects.items():
            for cid, lv in want.items():
                # 单脚本级断言：用 scan_script 直接核对该脚本
                info = scan_script(root / "scripts" / name)
                if cid == "C1":
                    got = "OK" if info.get("description") else "FAIL"
                elif cid == "C2":
                    got = "OK" if all(c in EXIT_CODES for c in info["exit_codes"]) else "FAIL"
                else:
                    bad = info["args_without_help"]
                    unreg = _unregistered_root_args(info["args"])
                    got = "FAIL" if (bad or unreg) else "OK"
                hit = got == lv
                missed += 0 if hit else 1
                print("[%s] %-14s %s：实际=%s 期望=%s" % ("PASS" if hit else "MISS", name, cid, got, lv))
        print("    目录级汇总：%s" % res)
    print("\n=== selftest：%d/%d 符合期望 ===" % (
        sum(len(v) for v in expects.values()) - missed, sum(len(v) for v in expects.values())))
    return 0 if missed == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="自研工具接口契约校验器：反射 argparse 定义，校验 C1–C5 并生成接口清单",
        epilog="契约语义见 references/interface-contract.md")
    ap.add_argument("--check", action="store_true", help="按契约 C1–C5 校验（rc=0 全过）")
    ap.add_argument("--text", action="store_true", help="打印人读接口清单")
    ap.add_argument("--json", action="store_true", help="输出机器可读接口清单")
    ap.add_argument("--selftest", action="store_true", help="自检（临时目录造假脚本）")
    ap.add_argument("--scripts-dir", help="被扫描的 scripts 目录（缺省为本技能自带的）")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest()

    sdir = Path(a.scripts_dir) if a.scripts_dir else SCRIPTS_DIR
    infos = scan_all(sdir)

    if a.json:
        print(json.dumps(infos, ensure_ascii=False, indent=2))
        return 0
    if a.text:
        _print_text(infos)
        return 0

    results = check(sdir.parent if a.scripts_dir else SKILL_ROOT)
    marks = {"OK": "[ OK ]", "FAIL": "[FAIL]", "WARN": "[WARN]"}
    for lvl, item, note in results:
        print("%s %s%s" % (marks[lvl], item, (" — " + note) if note else ""))
    n_fail = sum(1 for lvl, _, _ in results if lvl == "FAIL")
    print("\n=== 结果：检查 %d 项，FAIL=%d ===" % (len(results), n_fail))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
