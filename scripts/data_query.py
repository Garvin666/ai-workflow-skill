"""data_query.py - 大数据集 / 大目录检索（DuckDB 直查 + 目录概览）。

补上"本地无索引层、1.4GB 数据集搜不动"的缺口。三条路线:
    1) files  目录概览（文件数/总大小/按扩展名分布/大文件）——先看数据长什么样，再决定检索路线
    2) find   跨文件正则检索（DuckDB read_text + regexp_matches，带行号与上下文）
    3) sql    对 JSON/CSV/Parquet 直接跑 SQL（零导入、不建库）

用法:
    python data_query.py files <目录> [--glob "**/*.json"] [--top 20]
    python data_query.py find  <目录> --pattern "关键词" [--glob "**/*.md"] [--ignore-case]
                              [--max-hits 50] [--context 0] [--files-only]
    python data_query.py sql "SELECT count(*) FROM read_json_auto('data/*.json')"
    python data_query.py big   <目录> [--top 15] [--min-mb 50]

设计取舍:
    - `files` / `big` 用 os.scandir（只读元数据，不读内容）—— 对 20 万文件级别足够快
    - `find` / `sql` 交给 DuckDB：`find` 走 read_text 一次性扫描，避免 Python 逐文件循环
    - 小文件、单文件检索仍应用内置 Grep/Glob，不必动用本脚本
"""
import argparse
import json
import os
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
BIG_SKIP_DIRS = frozenset({".git", "__pycache__"})


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
    print("\n[提示] 结构化(JSON/CSV/Parquet)优先用 `sql` 子命令直查；自由文本用 `find`；"
          "原生 Grep 仍适合小目录", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- big
def cmd_big(args) -> int:
    root = Path(args.path)
    if not root.is_dir():
        print(f"[ERROR] 目录不存在：{root}", file=sys.stderr)
        return 2
    floor = args.min_mb * 1024 * 1024
    hits = [(size, fp) for fp, size in _walk_stat(root, BIG_SKIP_DIRS) if size >= floor]
    hits.sort(reverse=True)
    print(f"≥ {args.min_mb} MB 的文件共 {len(hits)} 个（目录 {root}）：")
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
    glob_lit = "[" + ", ".join(_sql_str(g) for g in glob_abs) + "]"
    pattern = args.pattern
    if args.ignore_case:
        pattern = f"(?i){pattern}"

    # 防呆：先确认 glob 能匹配到文件。DuckDB 语法不支持时是静默 0 命中，极易误判成"没有该内容"
    try:
        n_files = con.execute(f"SELECT count(*) FROM glob({glob_lit})").fetchone()[0]
    except Exception as e:
        print(f"[ERROR] glob 语法有误：{str(e).splitlines()[0][:160]}", file=sys.stderr)
        return 2
    if n_files == 0:
        print(f"[ERROR] glob 未匹配到任何文件（共 {len(glob_abs)} 条模式，示例 {glob_abs[0]}）", file=sys.stderr)
        print("[HINT ] 注意 DuckDB 不支持 `{a,b}` 花括号；请用逗号分隔多个 glob，或检查目录路径", file=sys.stderr)
        return 2

    if args.files_only:
        sql = f"""
            SELECT filename, count(*) AS hits
            FROM (
                SELECT filename, unnest(string_split(content, chr(10))) AS line
                FROM read_text({glob_lit})
            )
            WHERE regexp_matches(line, ?)
            GROUP BY filename ORDER BY hits DESC LIMIT {int(args.max_hits)}
        """
    else:
        sql = f"""
            SELECT filename, lineno, line FROM (
                SELECT filename, i AS lineno, lines[i] AS line
                FROM (
                    SELECT filename, string_split(content, chr(10)) AS lines
                    FROM read_text({glob_lit})
                ), range(1, len(lines) + 1) AS t(i)
            )
            WHERE regexp_matches(line, ?)
            LIMIT {int(args.max_hits)}
        """
    try:
        rows = con.execute(sql, [pattern]).fetchall()
    except Exception as e:  # DuckDB 抛的异常类型较多，统一兜底给出可执行提示
        print(f"[ERROR] 检索失败：{str(e).splitlines()[0][:200]}", file=sys.stderr)
        return 2

    if not rows:
        print(f"[WARN] 扫了 {n_files} 个文件，无命中。pattern={pattern}", file=sys.stderr)
        return 0
    print(f"# 命中 {len(rows)} 条（扫描 {n_files} 个文件）")
    if args.files_only:
        for fn, cnt in rows:
            print(f"{cnt:>6}  {fn}")
    else:
        for fn, lineno, line in rows:
            print(f"{fn}:{lineno}: {line.strip()[:200]}")
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

    p = sub.add_parser("find", help="跨文件正则检索（DuckDB read_text，带行号）")
    p.add_argument("path")
    p.add_argument("--pattern", required=True, help="正则（DuckDB regexp_matches 语法）")
    p.add_argument("--glob", help="glob 模式，逗号分隔多个；默认扫全部文本扩展名。注意 DuckDB 不支持 {a,b} 花括号")
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--max-hits", type=int, default=MAX_ROWS_DEFAULT)
    p.add_argument("--files-only", action="store_true", help="只列命中文件与命中数")

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
