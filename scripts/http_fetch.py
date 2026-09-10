"""http_fetch.py - 联网抓取（超时 30s + 退避重试）。

能力:
    1) 普通抓取（保持 v1 行为兼容）
    2) GitHub 仓库指标结构化取值（解决匿名 API 403 限流的坑）
    3) GitHub 仓库搜索（按关键词/限定符找项目，补"只能取不能搜"的缺口）
    4) HTML → 纯文本（省 token，避免把整页 HTML 塞进上下文）
    5) 批量链接存活检查（调研报告引用核验）

用法:
    python http_fetch.py <URL>                      # 内容打印到 stdout
    python http_fetch.py <URL> --out page.html      # 写入文件
    python http_fetch.py <URL> --text               # HTML 提取为纯文本
    python http_fetch.py <URL> --grep "关键词" --max-chars 3000   # 定向提取（省 token）
    python http_fetch.py --github-repo owner/repo   # 输出指标（TSV）
    python http_fetch.py --github-repo a/b,c/d --json
    python http_fetch.py --github-search "code search language:rust stars:>500" --search-limit 20
    python http_fetch.py --github-search "topic:static-analysis pushed:>2026-01-01" --search-sort updated
    python http_fetch.py --check-links links.txt --out check.tsv   # 批量探活（并发、不下载正文）

GitHub 鉴权（可选，提高限额）:
    设置环境变量 GITHUB_TOKEN=<PAT>；未设置则用匿名限额（60 次/小时/IP）。

效率机制:
    - 本地缓存：默认 TTL 3600s（AIWF_HTTP_TTL 可调），同 URL 重复请求不发网络请求；--no-cache 强制刷新
      缓存目录 ~/.workbuddy/cache/ai-workflow/http（AIWF_CACHE_DIR 可改）
    - 多仓库并发：--github-repo 传多个时按 AIWF_GH_CONCURRENCY（默认 5）并发取值

403 处理规则（重要）:
    - GitHub 匿名限流返回 403（不是权限错误）→ 识别 X-RateLimit-* / Retry-After 后等待重试
    - 其他 403 → 视为权限问题，不重试
"""
import argparse
import concurrent.futures
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

TIMEOUT = 30
RETRY_DELAYS = (2, 4, 8)
RATE_LIMIT_MAX_WAIT = int(os.environ.get("AIWF_GITHUB_MAX_WAIT", "60"))  # 单次限流最长等待秒数
RATE_LIMIT_MAX_RETRY = int(os.environ.get("AIWF_GITHUB_MAX_RETRY", "2"))  # 限流重试次数上限
CACHE_TTL = int(os.environ.get("AIWF_HTTP_TTL", "3600"))  # 本地缓存有效秒数，0 = 关闭缓存
CACHE_DIR = Path(os.environ.get("AIWF_CACHE_DIR", str(Path.home() / ".workbuddy" / "cache" / "ai-workflow" / "http")))
GH_CONCURRENCY = int(os.environ.get("AIWF_GH_CONCURRENCY", "5"))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ai-workflow/2.4",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

GITHUB_FIELDS = (
    "full_name",
    "stargazers_count",
    "forks_count",
    "open_issues_count",
    "archived",
    "pushed_at",
    "updated_at",
    "created_at",
    "description",
    "html_url",
)

# GitHub Search API 官方硬限制（2022-11-28 版文档）
SEARCH_ENDPOINT = "https://api.github.com/search/repositories"
SEARCH_SORTS = ("stars", "forks", "updated", "help-wanted-issues")
SEARCH_PER_PAGE_MAX = 100      # per_page 官方上限
SEARCH_RESULT_CAP = 1000       # 每次搜索最多返回 1000 条（=10 页 x 100）
SEARCH_QUERY_MAXLEN = 256      # q 长度上限
SEARCH_BOOL_MAX = 5            # AND/OR/NOT 数量上限
SEARCH_SCOPE_CAP = 4000        # 最多扫描 4000 个匹配仓库
SEARCH_COLS = ("full_name", "stargazers_count", "forks_count", "license_spdx",
               "language", "pushed_at", "archived", "html_url")

# /search/code：与仓库搜索是**不同的端点与配额桶**
CODE_SEARCH_ENDPOINT = "https://api.github.com/search/code"
CODE_SEARCH_ACCEPT = "application/vnd.github.text-match+json"  # 不带头则无 text_matches 片段
CODE_SEARCH_COLS = ("repository", "path", "html_url")


def _rate_limit_wait(headers) -> int:
    """从响应头推算需要等待的秒数；无法判定时给保守默认值。"""
    retry_after = headers.get("Retry-After")
    if retry_after and retry_after.isdigit():
        return min(int(retry_after) + 1, RATE_LIMIT_MAX_WAIT)
    reset = headers.get("X-RateLimit-Reset")
    if reset and reset.isdigit():
        wait = int(reset) - int(time.time()) + 1
        if wait > 0:
            return min(wait, RATE_LIMIT_MAX_WAIT)
    return 15


def _cache_file(url: str) -> Path:
    return CACHE_DIR / (hashlib.sha1(url.encode("utf-8")).hexdigest()[:20] + ".bin")


def cache_get(url: str, ttl: int) -> bytes | None:
    if ttl <= 0:
        return None
    path = _cache_file(url)
    try:
        if path.exists() and (time.time() - path.stat().st_mtime) <= ttl:
            return path.read_bytes()
    except OSError:
        return None
    return None


def cache_put(url: str, data: bytes) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_file(url).write_bytes(data)
    except OSError as e:
        print(f"[WARN] 缓存写入失败（不影响结果）：{e}", file=sys.stderr)


def fetch(url: str, token: str | None = None, use_cache: bool = True, ttl: int = CACHE_TTL,
          headers_extra: dict | None = None) -> bytes:
    if use_cache:
        cached = cache_get(url, ttl)
        if cached is not None:
            print(f"[INFO] 缓存命中（{len(cached)} 字节，TTL {ttl}s）：{url}", file=sys.stderr)
            return cached

    headers = dict(HEADERS)
    if headers_extra:
        headers.update(headers_extra)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"

    last_err = None
    rl_waits = 0
    attempts = (0,) + RETRY_DELAYS
    for i, delay in enumerate(attempts):
        if delay:
            time.sleep(delay)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()
            if use_cache:
                cache_put(url, data)
            return data
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:200]
            except Exception:  # noqa: BLE001 - 读取响应体失败不应掩盖原始错误
                pass
            if e.code == 403 and ("rate limit" in body.lower() or e.headers.get("X-RateLimit-Remaining") == "0"):
                if rl_waits >= RATE_LIMIT_MAX_RETRY:
                    print(
                        f"[ERROR] GitHub API 持续限流（已等待重试 {rl_waits} 次）。"
                        "解决办法：设置环境变量 GITHUB_TOKEN=<PAT> 提高限额，或改用已有实测数据并标注『未实时校验』。",
                        file=sys.stderr,
                    )
                    raise SystemExit(5)
                rl_waits += 1
                wait = _rate_limit_wait(e.headers)
                last_err = f"HTTP 403 限流（等待 {wait}s 后重试）"
                print(f"[WARN] GitHub API 限流，等待 {wait}s 重试（第 {rl_waits}/{RATE_LIMIT_MAX_RETRY} 次）", file=sys.stderr)
                time.sleep(wait)
                continue
            if e.code in (401, 403, 404):
                print(f"[ERROR] HTTP {e.code}（不重试）: {url} :: {body}", file=sys.stderr)
                raise SystemExit(3)
            last_err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = str(e)
        print(f"[WARN] 第 {i + 1} 次失败: {last_err}", file=sys.stderr)
    print(f"[ERROR] 重试耗尽: {last_err}", file=sys.stderr)
    raise SystemExit(4)


def html_to_text(raw: bytes) -> str:
    """极简 HTML → 文本：去脚本/样式/标签，解实体，压缩空行。不引第三方依赖。"""
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            s = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        s = raw.decode("utf-8", errors="replace")
    s = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?is)<!--.*?-->", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6])>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    lines = [re.sub(r"[ \t\u00a0]+", " ", ln).strip() for ln in s.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def github_repo_metrics(slug: str, token: str | None = None, use_cache: bool = True, ttl: int = CACHE_TTL) -> dict:
    slug = slug.strip().strip("/")
    if slug.count("/") != 1:
        print(f"[ERROR] 仓库格式应为 owner/repo，收到: {slug}", file=sys.stderr)
        raise SystemExit(2)
    raw = fetch(f"https://api.github.com/repos/{slug}", token=token, use_cache=use_cache, ttl=ttl)
    data = json.loads(raw.decode("utf-8"))
    out = {k: data.get(k) for k in GITHUB_FIELDS}
    lic = data.get("license") or {}
    out["license_spdx"] = lic.get("spdx_id")
    out["license_name"] = lic.get("name")
    out["_note"] = "NOASSERTION 表示 GitHub 无法自动归类，非『无许可证』；仍久未更新的 pushed_at 是活跃度风险信号"
    return out


def collect_repo_rows(slugs: list[str], token: str | None, use_cache: bool, ttl: int) -> list[dict]:
    """多仓库并发取值（限流时各自退避，互不影响）。"""
    def one(slug: str) -> dict:
        try:
            return github_repo_metrics(slug.strip(), token=token, use_cache=use_cache, ttl=ttl)
        except SystemExit as e:
            msg = f"fetch_failed(code={e.code})"
            print(f"[WARN] {slug.strip()} 取值失败：{msg}（数据缺失请勿编造，改用其他来源或标注『未实时校验』）", file=sys.stderr)
            return {"full_name": slug.strip(), "error": msg}

    if len(slugs) == 1:
        return [one(slugs[0])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(GH_CONCURRENCY, len(slugs))) as pool:
        return list(pool.map(one, slugs))


def github_search(query: str, sort: str = "stars", limit: int = 30,
                  token: str | None = None, use_cache: bool = True, ttl: int = CACHE_TTL,
                  dry_run: bool = False) -> list[dict]:
    """按关键词/限定符搜索仓库（GET /search/repositories）。

    补上"只能按已知仓库名取值、不能按主题搜索"的缺口。
    支持限定符：in:name,description,readme / user: / org: / language: / topic: /
    stars: / forks: / size: / created: / pushed: / archived: / fork:
    官方硬限制：每次搜索最多 1000 条结果、最多扫 4000 个匹配仓库；q ≤256 字符；
    AND/OR/NOT 合计 ≤5 个；限流匿名 10 次/分钟、认证 30 次/分钟。
    """
    q = (query or "").strip()
    if not q:
        print("[ERROR] --github-search 需要查询词，例如 'static analysis language:python pushed:>2026-01-01'", file=sys.stderr)
        raise SystemExit(2)
    if len(q) > SEARCH_QUERY_MAXLEN:
        print(f"[WARN] 查询 {len(q)} 字符，超过官方上限 {SEARCH_QUERY_MAXLEN}，可能被 GitHub 拒绝", file=sys.stderr)
    n_bool = sum(1 for w in re.split(r"\s+", q.upper()) if w in ("AND", "OR", "NOT"))
    if n_bool > SEARCH_BOOL_MAX:
        print(f"[WARN] 布尔算子 {n_bool} 个，超过官方上限 {SEARCH_BOOL_MAX} 个，可能返回 Validation failed", file=sys.stderr)
    if sort not in SEARCH_SORTS:
        print(f"[WARN] --search-sort='{sort}' 不在 {SEARCH_SORTS}，回退 best match", file=sys.stderr)
        sort = ""
    limit = max(1, min(int(limit), SEARCH_PER_PAGE_MAX))
    if not token:
        print("[WARN] 未设 GITHUB_TOKEN：搜索限流仅 10 次/分钟（认证为 30 次/分钟），连续搜索易被打满", file=sys.stderr)

    params = {"q": q, "per_page": str(limit)}
    if sort:
        params["sort"] = sort
        params["order"] = "desc"
    url = SEARCH_ENDPOINT + "?" + urllib.parse.urlencode(params)
    if dry_run:
        print(f"[DRY-RUN] 将请求：{url}")
        print(f"[DRY-RUN] 附加头：无（/search/repositories 匿名可用）")
        print(f"[DRY-RUN] 认证：{'已提供 token' if token else '缺失（匿名限流 10 次/分钟）'}")
        print(f"[DRY-RUN] 注意：该端点官方上限 {SEARCH_RESULT_CAP} 条结果 / 扫描 {SEARCH_SCOPE_CAP} 个仓库")
        return []
    raw = fetch(url, token=token, use_cache=use_cache, ttl=ttl)
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        print(f"[ERROR] 搜索响应不是 JSON（可能被限流页面拦截）：{raw[:200]!r}", file=sys.stderr)
        raise SystemExit(2)
    if isinstance(data, dict) and data.get("message"):
        print(f"[ERROR] GitHub 返回错误：{data['message']}", file=sys.stderr)
        raise SystemExit(2)

    items = data.get("items") or []
    total = data.get("total_count")
    if total is not None:
        cap_note = f"，官方每次搜索最多返回 {SEARCH_RESULT_CAP} 条" if total > SEARCH_RESULT_CAP else ""
        print(f"[INFO] 命中 {total} 个仓库，本次取回 {len(items)} 条{cap_note}", file=sys.stderr)
    if not items:
        print("[WARN] 搜索无结果——缩小限定符或换关键词；不要因空结果就编造仓库", file=sys.stderr)

    rows = []
    for it in items:
        lic = it.get("license") or {}
        desc = (it.get("description") or "").replace("\t", " ").replace("\n", " ")
        rows.append({
            "full_name": it.get("full_name"),
            "stargazers_count": it.get("stargazers_count"),
            "forks_count": it.get("forks_count"),
            "license_spdx": lic.get("spdx_id"),
            "language": it.get("language"),
            "pushed_at": it.get("pushed_at"),
            "archived": it.get("archived"),
            "open_issues_count": it.get("open_issues_count"),
            "topics": ",".join(it.get("topics") or []),
            "description": desc[:70],
            "html_url": it.get("html_url"),
        })
    return rows


def _search_url(endpoint: str, query: str, sort: str = "", limit: int = 30) -> str:
    params = {"q": query, "per_page": str(limit)}
    if sort:
        params["sort"] = sort
        params["order"] = "desc"
    return endpoint + "?" + urllib.parse.urlencode(params)


def github_code_search(query: str, limit: int = 30, token: str | None = None,
                       use_cache: bool = False, ttl: int = CACHE_TTL,
                       dry_run: bool = False) -> list[dict]:
    """按**代码内容**搜索仓库中的文件（GET /search/code）。

    与 --github-search 的区别：后者搜"仓库"（名字/描述/README），本函数搜"代码内容"，
    返回的是「哪个仓库的哪个文件」，带 text_matches 命中片段。

    官方限制（且已实测）：
      - **强制认证**：未带 token 时返回 401（不是限流，是必须登录）。
      - 认证后限流 10 次/分钟，匿名不可用；结果同样受 1000 条上限约束。
      - text_matches 片段需要 Accept: application/vnd.github.text-match+json，否则不返回。
    """
    q = (query or "").strip()
    if not q:
        print("[ERROR] --github-code-search 需要查询词，例如 'add_dependency repo:fastapi/fastapi'", file=sys.stderr)
        raise SystemExit(2)
    if len(q) > SEARCH_QUERY_MAXLEN:
        print(f"[WARN] 查询 {len(q)} 字符，超过官方上限 {SEARCH_QUERY_MAXLEN}，可能被拒绝", file=sys.stderr)
    limit = max(1, min(int(limit), SEARCH_PER_PAGE_MAX))
    url = _search_url(CODE_SEARCH_ENDPOINT, q, sort="", limit=limit)

    if dry_run:
        print(f"[DRY-RUN] 将请求：{url}")
        print(f"[DRY-RUN] 附加头：Accept: {CODE_SEARCH_ACCEPT}")
        print(f"[DRY-RUN] 认证：{'已提供 token' if (token or os.environ.get('GITHUB_TOKEN')) else '缺失（该端点需要 token，否则 401）'}")
        return []

    if not token:
        print("[ERROR] /search/code 强制要求认证，当前没有 GITHUB_TOKEN —— 匿名请求会返回 401。", file=sys.stderr)
        print("[HINT ] 设置环境变量 GITHUB_TOKEN=<PAT> 后重试；认证后该端点限流为 10 次/分钟。", file=sys.stderr)
        print("[HINT ] 只想按仓库名/描述找项目，用 --github-search（匿名可用）。", file=sys.stderr)
        raise SystemExit(2)

    raw = fetch(url, token=token, use_cache=use_cache, ttl=ttl,
                headers_extra={"Accept": CODE_SEARCH_ACCEPT})
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        print(f"[ERROR] 响应不是 JSON：{raw[:200]!r}", file=sys.stderr)
        raise SystemExit(2)
    if isinstance(data, dict) and data.get("message"):
        print(f"[ERROR] GitHub 返回错误：{data['message']}", file=sys.stderr)
        raise SystemExit(2)

    items = data.get("items") or []
    total = data.get("total_count")
    if total is not None:
        print(f"[INFO] 代码命中 {total} 处（官方上限 {SEARCH_RESULT_CAP} 条），本次取回 {len(items)} 条", file=sys.stderr)
    if not items:
        print("[WARN] 无命中——注意 /search/code 默认只搜默认分支、且大仓库可能未被索引", file=sys.stderr)

    rows = []
    for it in items:
        repo = it.get("repository") or {}
        frag = ""
        tms = it.get("text_matches") or []
        if tms:
            frag = (tms[0].get("fragment") or "").replace("\n", " ").replace("\t", " ").strip()
        rows.append({
            "repository": repo.get("full_name"),
            "path": it.get("path"),
            "html_url": it.get("html_url"),
            "fragment": frag[:120],
        })
    return rows


def check_links(urls: list[str], concurrency: int, timeout: int) -> list[dict]:
    """批量链接存活检查：只取状态与元信息，不下载正文（调研报告引用核验专用）。"""
    def probe(url: str) -> dict:
        req = urllib.request.Request(url, headers=dict(HEADERS), method="GET")
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                info = {
                    "url": url,
                    "status": resp.status,
                    "note": "可达",
                    "content_type": (resp.headers.get("Content-Type") or "").split(";")[0],
                    "bytes": resp.headers.get("Content-Length") or "-",
                    "final_url": resp.geturl(),
                    "ms": int((time.time() - t0) * 1000),
                }
            # 立即关闭，不读取正文
            return info
        except urllib.error.HTTPError as e:
            note = {401: "可达但需登录", 403: "可达但被拒绝(反爬/需授权)", 404: "不存在", 429: "限流"}.get(
                e.code, f"HTTP {e.code}"
            )
            return {"url": url, "status": e.code, "note": note, "content_type": "-", "bytes": "-",
                    "final_url": url, "ms": int((time.time() - t0) * 1000)}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return {"url": url, "status": "ERR", "note": f"网络失败: {str(e)[:60]}", "content_type": "-",
                    "bytes": "-", "final_url": url, "ms": int((time.time() - t0) * 1000)}

    if not urls:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(urls)))) as pool:
        return list(pool.map(probe, urls))


def _run_check_links(args) -> None:
    src = Path(args.check_links)
    if not src.exists():
        print(f"[ERROR] 链接清单文件不存在: {src}", file=sys.stderr)
        raise SystemExit(1)
    urls = [ln.strip() for ln in src.read_text(encoding="utf-8-sig").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    if not urls:
        print("[ERROR] 链接清单为空", file=sys.stderr)
        raise SystemExit(1)

    t0 = time.time()
    rows = check_links(urls, args.concurrency, args.timeout)
    cost = time.time() - t0
    ok_n = sum(1 for r in rows if isinstance(r["status"], int) and r["status"] < 400)
    warn_n = sum(1 for r in rows if r["status"] in (401, 403, 429))
    bad_n = len(rows) - ok_n - warn_n

    lines = ["\t".join(["status", "note", "ms", "bytes", "url", "final_url"])]
    for r in rows:
        lines.append("\t".join([str(r["status"]), r["note"], str(r["ms"]), str(r["bytes"]),
                                r["url"], r["final_url"]]))
    summary = (f"# 链接存活检查：共 {len(rows)} 条，可达 {ok_n}，受限 {warn_n}（401/403/429），异常 {bad_n}；"
               f"并发 {args.concurrency}，耗时 {cost:.1f}s")
    text = summary + "\n" + "\n".join(lines) + "\n"

    if args.out:
        with open(args.out, "w", encoding="utf-8-sig") as f:
            f.write(text)
        print(f"[ OK ] 已写入 {args.out}（{summary}）")
    else:
        print(text)
    print(f"[STATS] 平均 {cost / len(rows) * 1000:.0f} ms/条（串行基准约 3400 ms/条）", file=sys.stderr)
    if bad_n or warn_n:
        print(f"[WARN] {warn_n + bad_n} 条需人工确认（受限≠失效：403 多为反爬；ERR 需重试）", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description="联网抓取 / GitHub 指标取值 / HTML 转文本")
    ap.add_argument("url", nargs="?", help="目标 URL（与 --github-repo 二选一）")
    ap.add_argument("--out", help="写入文件（缺省打印 stdout）")
    ap.add_argument("--text", action="store_true", help="HTML 提取为纯文本后再输出/保存")
    ap.add_argument("--github-repo", help="GitHub 仓库 owner/repo，多个用逗号分隔")
    ap.add_argument("--github-search", help="按关键词搜索 GitHub 仓库（官方 /search/repositories）。限定符：in:name,description user: org: language: topic: stars: pushed: archived: fork:")
    ap.add_argument("--github-code-search", help="按**代码内容**搜索文件（官方 /search/code，强制认证）。例：'add_dependency repo:fastapi/fastapi'；返回仓库/路径/命中片段")
    ap.add_argument("--search-sort", default="stars", choices=list(SEARCH_SORTS), help="搜索结果排序（默认 stars）")
    ap.add_argument("--search-limit", type=int, default=30, help=f"搜索返回条数（默认 30，上限 {SEARCH_PER_PAGE_MAX}）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将请求的 URL 与附加头，不发请求（无 token 也能验证参数构造）")
    ap.add_argument("--json", action="store_true", help="GitHub 指标以 JSON 输出（缺省 TSV）")
    ap.add_argument("--token", help="GitHub PAT（缺省读环境变量 GITHUB_TOKEN）")
    ap.add_argument("--grep", help="只输出匹配该正则的行（自动启用 --text，用于精检索省 token）")
    ap.add_argument("--max-chars", type=int, help="输出截断到 N 个字符（配合 --grep 做定向读取）")
    ap.add_argument("--ignore-case", action="store_true", help="--grep 忽略大小写")
    ap.add_argument("--no-cache", action="store_true", help="跳过本地缓存，强制重新抓取")
    ap.add_argument("--ttl", type=int, default=CACHE_TTL, help=f"缓存有效秒数（默认 {CACHE_TTL}，0 = 关闭）")
    ap.add_argument("--check-links", help="批量链接存活检查：每行一个 URL（# 开头为注释），不下载正文")
    ap.add_argument("--concurrency", type=int, default=8, help="--check-links 并发数（默认 8）")
    ap.add_argument("--timeout", type=int, default=15, help="--check-links 单条超时秒数（默认 15）")
    args = ap.parse_args()
    use_cache = not args.no_cache

    if args.dry_run and not (args.github_search or args.github_code_search):
        print("[WARN] --dry-run 只对 --github-search / --github-code-search 生效，本次忽略", file=sys.stderr)

    if args.check_links:
        _run_check_links(args)
        return

    if args.github_search:
        token = args.token or os.environ.get("GITHUB_TOKEN")
        rows = github_search(args.github_search, args.search_sort, args.search_limit,
                             token=token, use_cache=use_cache, ttl=args.ttl, dry_run=args.dry_run)
        if args.dry_run:
            return
        if args.json:
            text = json.dumps(rows, ensure_ascii=False, indent=2)
        else:
            cols = list(SEARCH_COLS) + ["description"]
            text = "\t".join(cols) + "\n"
            for r in rows:
                text += "\t".join(
                    "—" if r.get(c) is None else ("否" if r.get(c) is False else str(r.get(c))) for c in cols
                ) + "\n"
        if args.out:
            with open(args.out, "w", encoding="utf-8-sig") as f:
                f.write(text)
            print(f"[ OK ] 已写入 {args.out}（{len(rows)} 个仓库）")
        else:
            print(text)
        return

    if args.github_code_search:
        token = args.token or os.environ.get("GITHUB_TOKEN")
        rows = github_code_search(args.github_code_search, args.search_limit,
                                  token=token, use_cache=use_cache, ttl=args.ttl,
                                  dry_run=args.dry_run)
        if args.dry_run:
            return
        if args.json:
            text = json.dumps(rows, ensure_ascii=False, indent=2)
        else:
            cols = list(CODE_SEARCH_COLS) + ["fragment"]
            text = "\t".join(cols) + "\n"
            for r in rows:
                text += "\t".join(
                    "—" if r.get(c) is None else str(r.get(c)) for c in cols
                ) + "\n"
        if args.out:
            with open(args.out, "w", encoding="utf-8-sig") as f:
                f.write(text)
            print(f"[ OK ] 已写入 {args.out}（{len(rows)} 处命中）")
        else:
            print(text)
        return

    if args.github_repo:
        token = args.token or os.environ.get("GITHUB_TOKEN")
        slugs = [s for s in args.github_repo.split(",") if s.strip()]
        t0 = time.time()
        rows = collect_repo_rows(slugs, token, use_cache, args.ttl)
        if len(slugs) > 1:
            print(f"[INFO] {len(slugs)} 个仓库并发取值完成，耗时 {time.time() - t0:.1f}s", file=sys.stderr)
        failed = [r for r in rows if r.get("error")]
        if failed:
            print(f"[WARN] {len(failed)}/{len(rows)} 个仓库未取到实测数据，禁止用二手数字替代", file=sys.stderr)
        if args.json:
            text = json.dumps(rows, ensure_ascii=False, indent=2)
        else:
            cols = ["full_name", "stargazers_count", "forks_count", "license_spdx", "pushed_at", "archived", "error"]
            text = "\t".join(cols) + "\n"
            for r in rows:
                text += "\t".join(
                    "—" if r.get(c) is None else ("否" if r.get(c) is False else str(r.get(c))) for c in cols
                ) + "\n"
        if args.out:
            with open(args.out, "w", encoding="utf-8-sig") as f:
                f.write(text)
            print(f"[ OK ] 已写入 {args.out}（{len(rows)} 个仓库）")
        else:
            print(text)
        return

    if not args.url:
        ap.error("必须提供 URL、--github-repo、--github-search 或 --github-code-search")

    try:
        content = fetch(args.url, use_cache=use_cache, ttl=args.ttl)
    except SystemExit:
        if args.out and Path(args.out).exists():
            print(f"[WARN] 抓取失败，{args.out} 未被更新（其中仍是上一次的旧结果），请勿误用", file=sys.stderr)
        raise
    if args.grep and not args.text:
        args.text = True
        print("[INFO] 指定 --grep，自动启用 HTML→文本", file=sys.stderr)
    if args.text:
        text = html_to_text(content)
        if args.grep:
            flags = re.IGNORECASE if args.ignore_case else 0
            try:
                pat = re.compile(args.grep, flags)
            except re.error as e:
                print(f"[ERROR] 正则非法: {e}", file=sys.stderr)
                raise SystemExit(2)
            hits = [f"{i}: {ln}" for i, ln in enumerate(text.splitlines(), 1) if pat.search(ln)]
            print(f"[INFO] grep 命中 {len(hits)} 行（原文 {len(text)} 字符）", file=sys.stderr)
            text = "\n".join(hits)
        if args.max_chars and len(text) > args.max_chars:
            text = text[: args.max_chars] + f"\n...[已截断，原始 {len(text)} 字符]"
        if args.out:
            with open(args.out, "w", encoding="utf-8-sig") as f:
                f.write(text)
            print(f"[ OK ] 已写入 {args.out}（{len(text)} 字符）")
        else:
            print(text)
        return

    if args.out:
        with open(args.out, "wb") as f:
            f.write(content)
        print(f"[ OK ] 已写入 {args.out}（{len(content)} 字节）")
    else:
        sys.stdout.buffer.write(content)


if __name__ == "__main__":
    main()
