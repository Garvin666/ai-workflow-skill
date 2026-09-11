"""data_query.py - 大数据集 / 大目录检索（DuckDB 直查 + 目录概览）。

补上"本地无索引层、1.4GB 数据集搜不动"的缺口。三条路线:
    1) files  目录概览（文件数/总大小/按扩展名分布/大文件）——先看数据长什么样，再决定检索路线
    2) find   跨文件正则检索（DuckDB read_text + regexp_matches，带行号与上下文）
    3) sql    对 JSON/CSV/Parquet 直接跑 SQL（零导入、不建库）

用法:
    python data_query.py files <目录> [--glob "**/*.json"] [--top 20]
    python data_query.py find  <目录> --pattern "关键词" [--glob "**/*.md"] [--ignore-case]
                              [--max-hits 50] [--files-only] [--with-line]
                              [--max-object-size 33554432] [--max-files 1000000]
    python data_query.py sql "SELECT count(*) FROM read_json_auto('data/*.json')"
    python data_query.py big   <目录> [--top 15] [--min-mb 50] [--no-skip]

设计取舍:
    - `files` / `big` 用 os.scandir（只读元数据，不读内容）—— 对 20 万文件级别足够快
    - `big` 默认跳过依赖/缓存目录（BIG_SKIP_DIRS：.venv/venv/node_modules/site-packages 等），
      避免把 torch 之类的第三方大文件当成项目文件；需要旧口径加 --no-skip
    - `find` 交给 DuckDB `read_text`，但**先单遍扫描按大小预过滤**（默认跳过 >32MB 文件，`--max-object-size` 可调/关闭），
      避免把大文件整读进内存导致 OOM（N1）；默认仅返回命中文件名（内存有界），`--with-line` 才展开行号。
      同时消除旧版「先 `count(*)` 再读」的二次目录遍历（N2）。
    - 小文件、单文件检索仍应用内置 Grep/Glob，不必动用本脚本
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# 默认只扫这些文本扩展名：read_text 遇到二进制会报错或产出垃圾
TEXT_EXTS = (
    "md", "txt", "json", "jsonl", "ndjson", "csv", "tsv", "yaml", "yml", "toml", "ini", "cfg", "conf", "log",
    "py", "js", "mjs", "cjs", "ts", "tsx", "jsx", "java", "kt", "c", "h", "cc", "cpp", "hpp", "cs", "go", "rs",
    "rb", "php", "swift", "scala", "sh", "bash", "ps1", "bat", "sql", "html", "htm", "css", "scss", "xml", "vue",
    "svelte", "r", "m", "jl", "lua", "pl", "gradle", "dockerfile", "env", "gitignore", "editorconfig",
)
DEFAULT_EXTS = TEXT_EXTS
# ⚠️ DuckDB 的 glob **不支持 `{a,b}` 花括号展开**，且是静默零命中。
# 必须显式展开成 glob 列表，交给 read_text([...]) / glob([...])。
DEFAULT_GLOBS = tuple(f"**/*.{e}" for e in DEFAULT_EXTS)
MAX_ROWS_DEFAULT = 50
SKIP_DIRS = frozenset({".git", "node_modules", "__pycache__", ".venv", "venv"})  # 与 v2.4 旧实现严格一致
LEGACY_SKIP_DIRS = frozenset({".git", "__pycache__"})  # v2.4.2 旧口径

BIG_SKIP_DIRS = frozenset({
    # 版本控制 / 编译缓存
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".tox", ".nox", ".ipynb_checkpoints", ".cache",
    # 依赖安装目录（体积巨大且与项目无关，v2.4.3 起默认跳过）
    ".venv", "venv", "site-packages", "node_modules", ".conda",
})


def _connect():
    try:
        import duckdb
    except ModuleNotFoundError:
        print("[ERROR] 缺少 duckdb，请先运行 scripts/setup_env.ps1 安装依赖", file=sys.stderr)
        print("[HINT ] 或直接用 venv 解释器：C:\\Users\\26717\\.workbuddy\\binaries\\python\\envs\\ai-workflow\\Scripts\\python.exe",
              file=sys.stderr)
        raise SystemExit(2)
    con = duckdb.connect()
    con.execute("SET enable_progress_bar=false")
    return con


def _sql_str(s: str) -> str:
    """转成 SQL 单引号字面量。

    不要用 json.dumps —— 它默认 ensure_ascii=True 会把中文转义成 \\uXXXX（路径直接失效），
    且产出双引号在 SQL 中是标识符而非字符串。实测两个坑都踩过。
    """
    return "'" + s.replace("'", "''") + "'"


def _human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def _walk_stat(root: Path, skip_dirs: frozenset[str]):
    """产出 (path, size)，跳过 skip_dirs。

    为什么不用 os.walk + os.path.getsize：os.walk 内部虽然用 scandir，但只把**名字**交给调用方，
    随后 os.path.getsize() 会对每个文件**再做一次 stat 系统调用**。在 Windows 上
    DirEntry.stat() 直接复用目录枚举（FindFirstFile/FindNextFile）已返回的数据，
    等于免掉 N 次系统调用——这是 12 万文件目录从 21 秒降到个位数秒的关键。
    """
    stack = [str(root)]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name not in skip_dirs:
                                stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            yield entry.path, entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue


def _glob_to_regex(glob: str) -> "re.Pattern":
    """把 DuckDB 风格 glob 转成正则（仅用于 Python 端预过滤，避免依赖 read_text 的命名参数）。

    逐字符分词，避免「先插入带 `?` 的 `(?:.*/)?` 再被后续 `?`→`[^/]` 替换误伤」的坑。
    支持 `**/`(可选多级目录)、`**`(任意)、`*`(单段)、`?`(单字符)；`.` 与路径中的正则特殊符均转义。
    匹配目标为文件的绝对路径（已统一成 `/`）。
    """
    g = glob.replace("\\", "/")
    out = ["^"]
    i, n = 0, len(g)
    while i < n:
        c = g[i]
        if c == "*":
            if i + 1 < n and g[i + 1] == "*":
                if i + 2 < n and g[i + 2] == "/":
                    out.append("(?:.*/)?")  # **/ 可选多级目录
                    i += 3
                else:
                    out.append(".*")  # 末尾 ** 任意
                    i += 2
            else:
                out.append("[^/]*")  # 单段通配
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == ".":
            out.append(r"\.")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    out.append("$")
    return re.compile("".join(out))


# ---------------------------------------------------------------- files
def cmd_files(args) -> int:
    root = Path(args.path)
    if not root.is_dir():
        print(f"[ERROR] 目录不存在：{root}", file=sys.stderr)
        return 2
    by_ext: dict[str, list[int]] = {}
    total_bytes = 0
    total_files = 0
    biggest: list[tuple[int, str]] = []
    for fp, size in _walk_stat(root, SKIP_DIRS):
        total_files += 1
        total_bytes += size
        ext = (Path(fp).suffix[1:].lower() or "(无扩展名)")
        slot = by_ext.setdefault(ext, [0, 0])
        slot[0] += 1
        slot[1] += size
        if args.top:  # N3：仅当要展示 top-N 大文件时才驻留全部 (size,path) 元组，否则 O(N) 内存浪费
            biggest.append((size, fp))
    print(f"目录：{root}")
    print(f"文件总数：{total_files:,}　总大小：{_human(total_bytes)}")
    rows = sorted(by_ext.items(), key=lambda kv: -kv[1][1])[: args.top]
    print(f"\n按扩展名（前 {len(rows)}，按占用空间排序）：")
    print(f"{'扩展名':<14}{'文件数':>10}{'占用':>14}")
    for ext, (cnt, size) in rows:
        print(f"{ext:<14}{cnt:>10,}{_human(size):>14}")
    if args.top:
        print(f"\n最大的 {min(args.top, len(biggest))} 个文件：")
        for size, fp in sorted(biggest, reverse=True)[: args.top]:
            print(f"{_human(size):>12}  {fp}")
    # 走 stdout：走 stderr 时与 2>&1 合并会因缓冲差异插到正文之前（实测观感错位）
    print("\n[提示] 结构化(JSON/CSV/Parquet)优先用 `sql` 子命令直查；自由文本用 `find`；"
          "原生 Grep 仍适合小目录")
    return 0


# ---------------------------------------------------------------- big
def cmd_big(args) -> int:
    root = Path(args.path)
    if not root.is_dir():
        print(f"[ERROR] 目录不存在：{root}", file=sys.stderr)
        return 2
    floor = args.min_mb * 1024 * 1024
    skip = LEGACY_SKIP_DIRS if getattr(args, "no_skip", False) else BIG_SKIP_DIRS
    hits = [(size, fp) for fp, size in _walk_stat(root, skip) if size >= floor]
    hits.sort(reverse=True)
    note = "" if skip is BIG_SKIP_DIRS else "（--no-skip：v2.4.2 旧口径，含 .venv 等依赖目录）"
    print(f"≥ {args.min_mb} MB 的文件共 {len(hits)} 个（目录 {root}）：{note}")
    for size, fp in hits[: args.top]:
        print(f"{_human(size):>12}  {fp}")
    return 0


# ---------------------------------------------------------------- find
def cmd_find(args) -> int:
    root = Path(args.path)
    if not root.is_dir():
        print(f"[ERROR] 目录不存在：{root}", file=sys.stderr)
        return 2
    con = _connect()
    # glob 列表：默认覆盖文本扩展名；--glob 支持逗号分隔多个
    globs = ([g.strip() for g in args.glob.split(",") if g.strip()] if args.glob else list(DEFAULT_GLOBS))
    # glob 必须相对 --path 解析：DuckDB 按 CWD 解析相对路径，否则从别处调用会静默零命中（实测踩过）
    base = os.path.abspath(str(root)).replace("\\", "/")
    glob_abs = [g if os.path.isabs(g) else f"{base}/{g}" for g in globs]

    cap = args.max_object_size
    max_files = args.max_files
    # --- 大小预过滤（N1，防 OOM）：单遍扫描，只对 <=cap 的文件交给 DuckDB，大文件直接跳过（不读其内容）。
    #     同时消除旧版「先 count(*) 再读」的二次遍历（N2）；显式文件清单交给 read_text，DuckDB 不再做 glob 枚举。
    sel, skipped_big = None, 0
    if cap > 0 or max_files > 0:
        regexes = [_glob_to_regex(g) for g in glob_abs]
        sel = []
        for fp, size in _walk_stat(root, SKIP_DIRS):
            if not any(rx.match(fp.replace("\\", "/")) for rx in regexes):
                continue
            if cap > 0 and size > cap:
                skipped_big += 1
                continue
            sel.append(fp.replace("\\", "/"))
            if max_files > 0 and len(sel) >= max_files:
                break
        if not sel:
            print(f"[ERROR] 无匹配文件（glob {len(glob_abs)} 条；跳过 >{cap}B 大文件 {skipped_big} 个）", file=sys.stderr)
            print("[HINT ] 若确需扫描大文件，调大 --max-object-size（0=不限制）；注意超大文件整读仍有 OOM 风险", file=sys.stderr)
            return 2
        src_lit = "[" + ", ".join(_sql_str(f) for f in sel) + "]"
        scanned = len(sel)
    else:
        # 用户显式关闭两道护栏：走旧版原始 glob 路径（最快，但大文件有 OOM 风险）
        src_lit = "[" + ", ".join(_sql_str(g) for g in glob_abs) + "]"
        scanned = None

    pattern = args.pattern
    if args.ignore_case:
        pattern = f"(?i){pattern}"

    if args.files_only:
        sql = f"""
            SELECT filename, count(*) AS hits
            FROM (
                SELECT filename, unnest(string_split(content, chr(10))) AS line
                FROM read_text({src_lit})
            )
            WHERE regexp_matches(line, ?)
            GROUP BY filename ORDER BY hits DESC LIMIT {int(args.max_hits)}
        """
    elif args.with_line:
        # 行级展开（旧默认）：内存随文件行数增长，仅对 <=cap 的预筛选文件执行
        sql = f"""
            SELECT filename, lineno, line FROM (
                SELECT filename, i AS lineno, lines[i] AS line
                FROM (
                    SELECT filename, string_split(content, chr(10)) AS lines
                    FROM read_text({src_lit})
                ), range(1, len(lines) + 1) AS t(i)
            )
            WHERE regexp_matches(line, ?)
            LIMIT {int(args.max_hits)}
        """
    else:
        # 默认：仅文件级命中（不展开行），内存有界 —— 对应方案 A 的轻路径
        sql = f"""
            SELECT filename FROM read_text({src_lit})
            WHERE regexp_matches(content, ?)
            LIMIT {int(args.max_hits)}
        """
    try:
        rows = con.execute(sql, [pattern]).fetchall()
    except Exception as e:  # DuckDB 抛的异常类型较多，统一兜底给出可执行提示
        print(f"[ERROR] 检索失败：{str(e).splitlines()[0][:200]}", file=sys.stderr)
        return 2

    scanned_msg = (f"扫描 {scanned} 个文件" if scanned is not None else "glob 匹配文件")
    skip_msg = f"；跳过 >{cap}B 大文件 {skipped_big} 个" if skipped_big else ""
    if not rows:
        print(f"[WARN] {scanned_msg}{skip_msg}，无命中。pattern={pattern}", file=sys.stderr)
        return 0
    print(f"# 命中 {len(rows)} 条（{scanned_msg}{skip_msg}）")
    if args.files_only:
        for fn, cnt in rows:
            print(f"{cnt:>6}  {fn}")
    elif args.with_line:
        for fn, lineno, line in rows:
            print(f"{fn}:{lineno}: {line.strip()[:200]}")
    else:
        for (fn,) in rows:
            print(fn)
    return 0


# ---------------------------------------------------------------- sql
def cmd_sql(args) -> int:
    con = _connect()
    if args.cwd:
        os.chdir(args.cwd)
    try:
        cur = con.execute(args.query)
        rows = cur.fetchmany(int(args.max_rows))
        cols = [d[0] for d in cur.description] if cur.description else []
    except Exception as e:
        print(f"[ERROR] SQL 执行失败：{str(e).splitlines()[0][:300]}", file=sys.stderr)
        print("[HINT ] 结构化文件用 read_json_auto / read_csv_auto / read_parquet；"
              "本地未导入的文件可直接写路径，DuckDB 不需要先建库", file=sys.stderr)
        return 2
    if args.json:
        text = json.dumps([dict(zip(cols, r)) for r in rows], ensure_ascii=False, indent=2, default=str)
    else:
        text = "\t".join(cols) + "\n"
        for r in rows:
            text += "\t".join("NULL" if v is None else str(v) for v in r) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8-sig") as f:
            f.write(text)
        print(f"[ OK ] 已写入 {args.out}（{len(rows)} 行）")
    else:
        print(text)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="大数据集/大目录检索（DuckDB 直查）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("files", help="目录概览：文件数/总大小/按扩展名分布/大文件")
    p.add_argument("path")
    p.add_argument("--top", type=int, default=15, help="每类展示条数（默认 15）")

    p = sub.add_parser("big", help="列出超过阈值的大文件")
    p.add_argument("path")
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--min-mb", type=float, default=50, help="最小体积 MB（默认 50）")
    p.add_argument("--no-skip", "--legacy-skip", dest="no_skip", action="store_true",
                   help="按 v2.4.2 旧口径：只跳过 .git/__pycache__（即包含 .venv/node_modules 等依赖目录）")

    p = sub.add_parser("find", help="跨文件正则检索（DuckDB read_text，防 OOM 预过滤）")
    p.add_argument("path")
    p.add_argument("--pattern", required=True, help="正则（DuckDB regexp_matches 语法）")
    p.add_argument("--glob", help="glob 模式，逗号分隔多个；默认扫全部文本扩展名。注意 DuckDB 不支持 {a,b} 花括号")
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--max-hits", type=int, default=MAX_ROWS_DEFAULT)
    p.add_argument("--files-only", action="store_true", help="只列命中文件与命中数（仍受 --max-object-size 约束）")
    p.add_argument("--with-line", action="store_true",
                   help="展开到「文件:行号:内容」（旧默认，内存随行数增长）；默认仅返回命中文件名（内存有界）")
    p.add_argument("--max-object-size", type=int, default=33_554_432,
                   help="单文件大小上限字节，超过则跳过不读（防 OOM，对应 N1）；0=不限制单文件大小（仍受 --max-files 约束）")
    p.add_argument("--max-files", type=int, default=1_000_000,
                   help="最多扫描文件数，超过截断；0=不限制（--max-object-size 0 与 --max-files 0 同时设置才回到旧版 glob 路径）")

    p = sub.add_parser("sql", help="对 JSON/CSV/Parquet 直接跑 SQL（零导入）")
    p.add_argument("query")
    p.add_argument("--cwd", help="切换工作目录后再执行（便于写相对路径）")
    p.add_argument("--max-rows", type=int, default=MAX_ROWS_DEFAULT)
    p.add_argument("--json", action="store_true")
    p.add_argument("--out")

    args = ap.parse_args()
    if args.cmd == "files":
        return cmd_files(args)
    if args.cmd == "big":
        return cmd_big(args)
    if args.cmd == "find":
        return cmd_find(args)
    return cmd_sql(args)


if __name__ == "__main__":
    raise SystemExit(main())
