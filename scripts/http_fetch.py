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

GitHub 鉴权（可选，提高限额；优先级从高到低）:
    ① --token <PAT>  ② 环境变量 GITHUB_TOKEN  ③ 环境变量 GH_TOKEN  ④ gh CLI（gh auth login 后自动读取）
    均无则用匿名限额（core 60 次/小时/IP，search 10 次/分钟/IP）。凭据只读不落盘。

效率机制:
    - 本地缓存：默认 TTL 3600s（AIWF_HTTP_TTL 可调），同 URL 重复请求不发网络请求；--no-cache 强制刷新
      缓存目录 ~/.workbuddy/cache/ai-workflow/http（AIWF_CACHE_DIR 可改）
    - 链接探活持久缓存：--check-links 的探活结果按 URL 哈希落盘（~/.workbuddy/cache/ai-workflow/probe，
      AIWF_LINKCHECK_CACHE 可改），默认 TTL 7 天（AIWF_LINKCHECK_TTL 可改），同 URL 跨任务/跨进程只探活一次；
      --no-cache 强制刷新。复用进程内唯一 SSL context（避免逐请求重建 ~13ms/次）
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
import shutil
import ssl
import sys
import threading
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
# ---- P8（v3.4.0）：限流桶上限按「有没有凭据」分档 ----
# 之前两端点都**无条件**按匿名上限自限，而带凭据时 GitHub 实际是 5000/h（核心）与 30/min（搜索）。
# 后果：多仓库指标对比（"≥3 个方向必须并行"是流程硬规则）时自限桶会先满，随后每次调用最多
# 白等 RATE_LIMIT_MAX_WAIT（默认 60s）——把上限设在真实配额的 1/10 处纯属自伤。
GH_CORE_LIMIT_ANON = int(os.environ.get("AIWF_GH_CORE_LIMIT_ANON", "60"))
GH_CORE_LIMIT_AUTH = int(os.environ.get("AIWF_GH_CORE_LIMIT_AUTH", "4500"))   # 官方 5000/h，留安全边际
GH_SEARCH_LIMIT_ANON = int(os.environ.get("AIWF_GH_SEARCH_LIMIT_ANON", "10"))
GH_SEARCH_LIMIT_AUTH = int(os.environ.get("AIWF_GH_SEARCH_LIMIT_AUTH", "30"))  # 官方认证 30/min

# ---- 链接探活持久缓存（消除「验证税」：同 URL 跨任务/跨进程只探活一次）----
# 缓存目录落在基础设施例外允许的 ~/.workbuddy/cache/ai-workflow/ 下，与正文缓存(http)分开
LINKCHECK_TTL = int(os.environ.get("AIWF_LINKCHECK_TTL", str(7 * 86400)))  # 默认 7 天
LINKCHECK_CACHE_DIR = Path(os.environ.get("AIWF_LINKCHECK_CACHE",
                                          str(Path.home() / ".workbuddy" / "cache" / "ai-workflow" / "probe")))
# 进程内复用同一 SSL context（逐请求创建 ~13ms/次，批量探活会白白烧纯计算，与网络无关）
_SSL_CTX = ssl.create_default_context()
# N5：进程内记忆已解析的 GitHub 凭据，避免无 env 时每次抓取都 spawn `gh auth token` 子进程
_TOKEN_CACHE: str | None = None
# P3（v3.4.0）：_resolve_token 会被 collect_repo_rows 的多线程并发调用；无锁时会重复 spawn
# 多个 `gh auth token` 子进程（本机单价 ≈120 ms，非沙箱终端 ≈790 ms）
_TOKEN_LOCK = threading.Lock()
# ratelimit.json 里的**非机密布尔位**：本机是否成功解析出过凭据（只存 True/False，不存凭据）
_AUTH_HINT_KEY = "_auth_ok"


def _link_cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _link_cache_path(url: str) -> Path:
    return LINKCHECK_CACHE_DIR / (_link_cache_key(url) + ".json")


def _link_cache_get(url: str, ttl: int) -> dict | None:
    """命中且未过期返回结果 dict；缺失/损坏/过期返回 None（损坏文件顺手删）。"""
    if ttl <= 0:
        return None
    p = _link_cache_path(url)
    try:
        if p.exists() and (time.time() - p.stat().st_mtime) <= ttl:
            return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        try:
            p.unlink()
        except OSError:
            pass
    return None


def _link_cache_put(url: str, info: dict) -> None:
    try:
        LINKCHECK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _link_cache_path(url).write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        print(f"[WARN] 链接缓存写入失败（不影响结果）：{e}", file=sys.stderr)


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


# ---- 跨任务 GitHub 限流保护（消除「验证税」：多任务串行/并发不互相打爆匿名限流）----
# 仅做"节流"（spaced calls），不做"计数拒绝"；任何异常都静默跳过，绝不阻断抓取。
# 状态落基础设施例外目录 ~/.workbuddy/cache/ai-workflow/ratelimit.json（跨任务/跨进程共享）。
_RL_LOCK = threading.Lock()
_RL_STATE = CACHE_DIR.parent / "ratelimit.json"  # ~/.workbuddy/cache/ai-workflow/ratelimit.json


def _rl_load() -> dict:
    try:
        if _RL_STATE.exists():
            return json.loads(_RL_STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _rl_save(state: dict) -> None:
    try:
        _RL_STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _RL_STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_RL_STATE)
    except (OSError, json.JSONDecodeError):
        pass


def _auth_hint() -> bool:
    """**不 spawn 子进程**地判断"本机大概有没有可用凭据"。只用于两件事：
    ① 选限流桶上限（P8）② 信息性告警的措辞。**不用于任何授权决策** —— 真正的授权只由
    `_resolve_token()` 决定；本函数返回 False 不代表请求一定匿名发出去。

    依据（按代价从低到高，任一成立即 True）：
      ① `GITHUB_TOKEN` / `GH_TOKEN` 环境变量；
      ② `ratelimit.json` 里的 `_auth_ok` 位 —— `_resolve_token()` 成功解析过一次后写入的
         **布尔值**（不含凭据本身，故不违反凭据落盘纪律）；
      ③ 不检查 `gh` 是否存在：装了 gh ≠ 已登录，据此判"有凭据"会选错桶。宁可保守按匿名。
    """
    for env_name in ("GITHUB_TOKEN", "GH_TOKEN"):
        v = os.environ.get(env_name)
        if v and v.strip():
            return True
    try:
        return bool(_rl_load().get(_AUTH_HINT_KEY))
    except Exception:
        return False


def _mark_auth_ok() -> None:
    """把"本机确实解析出过凭据"记成一个**非机密布尔位**，供**后续进程**免 spawn 选对限流桶。

    只写 True，**不写凭据本身**（凭据纪律：不落盘、不进记忆）。失败静默 —— 这只是提示位，
    写不进去最多退化为按匿名桶保守自限，绝不能因此影响抓取。
    """
    try:
        with _RL_LOCK:
            state = _rl_load()
            state[_AUTH_HINT_KEY] = True
            _rl_save(state)
    except Exception:
        pass


def _rl_throttle(bucket: str, limit: int, window: int) -> None:
    """按桶节流：窗口内已记录 >= limit 次调用则睡到最早一次过期（最长 RATE_LIMIT_MAX_WAIT）。

    bucket: 端点桶名（gh_core / gh_search）；limit/window: 窗口内最大次数与窗口秒数。
    失败静默跳过（不抛、不阻塞抓取）；先写临时文件再 rename，避免半截文件。
    """
    try:
        with _RL_LOCK:
            now = time.time()
            calls = [t for t in _rl_load().get(bucket, []) if now - t < window]
            if len(calls) >= limit:
                sleep_for = window - (now - calls[0]) + 0.2
                if sleep_for > 0:
                    time.sleep(min(sleep_for, RATE_LIMIT_MAX_WAIT))
                now = time.time()
                calls = [t for t in _rl_load().get(bucket, []) if now - t < window]
            calls.append(now)
            state = _rl_load()
            state[bucket] = calls[-50:]
            _rl_save(state)
    except Exception:
        pass


def _looks_like_token(s: str) -> bool:
    """粗校验凭据形态，避免把 gh 的提示文本/报错当成 token 发出去。

    合法 GitHub 凭据为 ghp_/gho_/ghu_/ghs_/ghr_/github_pat_ 前缀，或经典 40 位十六进制，
    均为无空白的字母数字下划线串且长度 >= 20。
    """
    s = s.strip()
    if len(s) < 20 or any(c.isspace() for c in s):
        return False
    return all(c.isalnum() or c == "_" for c in s)


def _resolve_token(cli_token: str | None = None) -> str | None:
    """解析 GitHub 凭据，优先级：--token > GITHUB_TOKEN > GH_TOKEN > gh CLI（gh auth token）。

    只读不写：不在磁盘落任何明文凭据（gh CLI 的凭据由其自身安全存储管理）。
    返回值仅供内存中使用，任何情况下不得打印完整 token。

    N5：进程内记忆已解析的凭据（含「无凭据」的 None），避免无 env 时每次抓取都
    spawn `gh auth token` 子进程。cli_token 为调用方显式传入，不进缓存（可能每次不同）。

    P3（v3.4.0）：① 加 `_TOKEN_LOCK` —— 本函数会被 `collect_repo_rows` 的多线程并发调用，
    无锁时会重复 spawn 多个 gh 子进程；② 解析成功后写 `_auth_ok` 提示位（**布尔值**，非凭据），
    使**后续进程**能免 spawn 选对限流桶（P8）。
    ⚠️ 调用方**必须**只在"确实要发请求"之后才调用本函数 —— 缓存命中路径不需要凭据，
    提前调用就是白付一张 gh 子进程（实测本机 ≈120 ms，非沙箱终端 ≈790 ms）。
    """
    if cli_token:
        return cli_token
    global _TOKEN_CACHE
    if _TOKEN_CACHE is not None:  # 已解析过（含 None），直接复用，不 spawn 子进程
        return _TOKEN_CACHE
    with _TOKEN_LOCK:  # P3：双检锁，避免并发重复 spawn
        if _TOKEN_CACHE is not None:
            return _TOKEN_CACHE
        for env_name in ("GITHUB_TOKEN", "GH_TOKEN"):
            v = os.environ.get(env_name)
            if v and v.strip():
                _TOKEN_CACHE = v.strip()
                _mark_auth_ok()
                return _TOKEN_CACHE
        try:
            import subprocess
            r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
            cand = (r.stdout or "").strip()
            if r.returncode == 0 and cand:
                if _looks_like_token(cand):
                    print("[INFO] 未设环境变量，改用 gh CLI 凭据（gh auth token）提高限额", file=sys.stderr)
                    _TOKEN_CACHE = cand
                    _mark_auth_ok()
                    return _TOKEN_CACHE
                print(f"[WARN] gh auth token 输出不像凭据（{len(cand)} 字符），已忽略；"
                      "若需认证请设置 GITHUB_TOKEN 或运行 gh auth login", file=sys.stderr)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        _TOKEN_CACHE = None  # 记忆「无凭据」，避免每次重试都 spawn 子进程
        return None


def fetch(url: str, token: str | None = None, use_cache: bool = True, ttl: int = CACHE_TTL,
          headers_extra: dict | None = None, out_file: str | None = None,
          throttle: tuple[str, int, int] | None = None) -> bytes | None:
    """抓取 URL 返回字节体。

    N4：`out_file` 给定时（原始二进制下载）走流式落盘——不把整响应读入内存，也不写入
    内存缓存（避免大文件内存/磁盘翻倍），直接 shutil.copyfileobj 写盘后返回 None。
    文本/grep/stdout/collect 等需整体的路径不传 out_file，照常返回 bytes。

    P3（v3.4.0）：凭据解析只发生在**确实要发请求**之后（缓存命中直接返回，不 spawn gh）。

    P8（v3.4.0）：`throttle=(桶名, 上限, 窗口秒)` —— 由本函数在**缓存未命中**时才调用
    `_rl_throttle`。调用方原先都在 fetch 之前无条件节流，于是**缓存命中也被计入桶**
    （既虚耗配额，又会让"60 次缓存命中"反过来触发一次最长 60s 的睡眠）。限流只对
    "真发出去的请求"计数才是对的。
    """
    if use_cache and out_file is None:
        cached = cache_get(url, ttl)
        if cached is not None:
            print(f"[INFO] 缓存命中（{len(cached)} 字节，TTL {ttl}s）：{url}", file=sys.stderr)
            return cached

    if throttle is not None:
        _rl_throttle(*throttle)

    headers = dict(HEADERS)
    if headers_extra:
        headers.update(headers_extra)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif "api.github.com" in url:
        auto = _resolve_token()
        if auto:
            headers["Authorization"] = f"Bearer {auto}"

    last_err = None
    rl_waits = 0
    attempts = (0,) + RETRY_DELAYS
    for i, delay in enumerate(attempts):
        if delay:
            time.sleep(delay)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                if out_file is not None:  # N4：流式落盘，整响应不进内存、不进缓存
                    with open(out_file, "wb") as f:
                        shutil.copyfileobj(resp, f)
                    size = os.path.getsize(out_file)
                    print(f"[ OK ] 已流式写入 {out_file}（{size} 字节，未载入内存）", file=sys.stderr)
                    return None
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
                        "解决办法：设置 GITHUB_TOKEN / GH_TOKEN，或 gh auth login 后用 gh CLI 凭据；否则改用已有实测数据并标注『未实时校验』。",
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
    # P8：桶上限按「有没有凭据」分档（匿名 60/h vs 认证 4500/h），避免带凭据时自限在 1/75 处白等；
    # P3：节流与凭据解析都交给 fetch 在**缓存未命中**之后做 —— 缓存命中不需要凭据、也不该配额计数。
    limit = GH_CORE_LIMIT_AUTH if _auth_hint() else GH_CORE_LIMIT_ANON
    raw = fetch(f"https://api.github.com/repos/{slug}", token=token, use_cache=use_cache, ttl=ttl,
                throttle=("gh_core", limit, 3600))
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
    # P3：这里**不能**用 `not token` 判断 —— main() 已不再 eager 解析凭据，token=None 只表示
    # "没显式传"，不代表本机没有 gh CLI 凭据（那会让告警误导）。改用不 spawn 子进程的
    # `_auth_hint()` 保守措辞：说"未发现"而不是"未设"。
    if not token and not _auth_hint():
        print("[WARN] 未发现可用凭据（GITHUB_TOKEN / GH_TOKEN / 之前解析成功的 gh CLI）："
              "搜索限流仅 10 次/分钟（认证为 30 次/分钟），连续搜索易被打满", file=sys.stderr)

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
    search_limit = GH_SEARCH_LIMIT_AUTH if _auth_hint() else GH_SEARCH_LIMIT_ANON
    raw = fetch(url, token=token, use_cache=use_cache, ttl=ttl,
                throttle=("gh_search", search_limit, 60))
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
        # 不发请求就不需要凭据，也不再 eager 解析（P3）
        print(f"[DRY-RUN] 认证：{'已显式提供 token' if token else '未显式提供；真实请求时按 GITHUB_TOKEN → GH_TOKEN → gh auth token 自动解析（该端点必须有凭据，否则 401）'}")
        return []

    # P3：**缓存命中不需要凭据**，所以先探一次缓存，只有确实要发请求时才解析并强制校验。
    # 否则"重复搜同一条代码"也会白付一张 gh 子进程（本机 ≈120 ms，非沙箱终端 ≈790 ms）。
    if not token:
        probe = cache_get(url, ttl) if use_cache else None
        if probe is None:
            token = _resolve_token()
    if not token:
        print("[ERROR] /search/code 强制要求认证，当前没有可用凭据 —— 匿名请求会返回 401。", file=sys.stderr)
        print("[HINT ] 三选一：① 设置环境变量 GITHUB_TOKEN=<PAT>；② 设置 GH_TOKEN；③ 运行 gh auth login 后用 gh CLI 凭据（脚本自动读取）。", file=sys.stderr)
        print("[HINT ] 只想按仓库名/描述找项目，用 --github-search（匿名可用）。", file=sys.stderr)
        raise SystemExit(2)

    search_limit = GH_SEARCH_LIMIT_AUTH if _auth_hint() else GH_SEARCH_LIMIT_ANON
    raw = fetch(url, token=token, use_cache=use_cache, ttl=ttl,
                headers_extra={"Accept": CODE_SEARCH_ACCEPT},
                throttle=("gh_search", search_limit, 60))
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


def _classify_403(headers) -> str:
    """按响应头判定 403 的性质：CDN 反爬 / 需授权 / 未知拒绝。

    Cloudflare（cf-ray / cf-mitigated / server: cloudflare）与常见 WAF 的 403
    多为反爬拦截——人工浏览器可访问，不代表链接失效；需与 404 区分对待。
    """
    h = {k.lower(): (v or "") for k, v in (headers.items() if headers else [])}
    server = h.get("server", "")
    low = server.lower()
    if h.get("cf-ray") or h.get("cf-mitigated") or "cloudflare" in low:
        return "403-CDN反爬(Cloudflare，人工可访问)"
    if any(w in low for w in ("akamai", "imperva", "sucuri", "cloudfront", "waf")):
        return f"403-WAF反爬({server.split('/')[0] or 'WAF'}，人工可访问)"
    if h.get("x-ratelimit-remaining") == "0" or h.get("retry-after"):
        return "403-限流"
    return "403-拒绝(需授权或反爬，无法自动区分)"


def _probe_once(url: str, timeout: int, headers: dict) -> tuple[dict | None, Exception | None]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            info = {
                "url": url,
                "status": resp.status,
                "note": "可达",
                "content_type": (resp.headers.get("Content-Type") or "").split(";")[0],
                "bytes": resp.headers.get("Content-Length") or "-",
                "final_url": resp.geturl(),
                "ms": int((time.time() - t0) * 1000),
            }
        return info, None  # 立即关闭，不读取正文
    except urllib.error.HTTPError as e:
        return None, e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, e


def check_links(urls: list[str], concurrency: int, timeout: int,
                use_cache: bool = True) -> tuple[list[dict], int]:
    """批量链接存活检查：只取状态与元信息，不下载正文（调研报告引用核验专用）。

    403 处理：先用常规 UA 探测；若 403，则换一套更接近真实浏览器的头再试一次——
    两次都 403 才判为反爬（CDN/WAF 特征头用于进一步分类），避免把"被反爬"误报成"失效"。

    持久缓存：命中缓存（未过期）直接返回，不发起网络请求——消除「验证税」（同 URL
    跨任务/跨进程只探活一次）。--no-cache 可强制刷新。缓存读写失败不影响结果。
    """
    ALT_HEADERS = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }

    def _probe_live(url: str) -> dict:
        t0 = time.time()
        info, err = _probe_once(url, timeout, dict(HEADERS))
        if info is not None:
            return info
        # 403/429：换头重试一次
        if isinstance(err, urllib.error.HTTPError) and err.code in (403, 429):
            info2, err2 = _probe_once(url, timeout, dict(ALT_HEADERS))
            if info2 is not None:
                return info2
            if isinstance(err2, urllib.error.HTTPError):
                note = _classify_403(err2.headers) if err2.code == 403 else "429-限流"
                return {"url": url, "status": err2.code, "note": note, "content_type": "-",
                        "bytes": "-", "final_url": url, "ms": int((time.time() - t0) * 1000)}
            err = err2
        if isinstance(err, urllib.error.HTTPError):
            note = {401: "可达但需登录", 403: "403-拒绝(需授权或反爬，无法自动区分)", 404: "不存在",
                    429: "429-限流"}.get(err.code, f"HTTP {err.code}")
            return {"url": url, "status": err.code, "note": note, "content_type": "-", "bytes": "-",
                    "final_url": url, "ms": int((time.time() - t0) * 1000)}
        return {"url": url, "status": "ERR", "note": f"网络失败: {str(err)[:60]}", "content_type": "-",
                "bytes": "-", "final_url": url, "ms": int((time.time() - t0) * 1000)}

    def probe_cached(url: str) -> dict:
        if use_cache:
            hit = _link_cache_get(url, LINKCHECK_TTL)
            if hit is not None:
                hits.append(url)
                print(f"[INFO] 链接缓存命中：{url}", file=sys.stderr)
                return hit
        info = _probe_live(url)
        if use_cache:
            _link_cache_put(url, info)
        return info

    if not urls:
        return [], 0
    hits: list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(concurrency, len(urls)))) as pool:
        return list(pool.map(probe_cached, urls)), len(hits)


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

    use_cache = not args.no_cache
    t0 = time.time()
    rows, cached_n = check_links(urls, args.concurrency, args.timeout, use_cache)
    cost = time.time() - t0
    ok_n = sum(1 for r in rows if isinstance(r["status"], int) and r["status"] < 400)
    warn_n = sum(1 for r in rows if r["status"] in (401, 403, 429))
    bad_n = len(rows) - ok_n - warn_n

    lines = ["\t".join(["status", "note", "ms", "bytes", "url", "final_url"])]
    for r in rows:
        lines.append("\t".join([str(r["status"]), r["note"], str(r["ms"]), str(r["bytes"]),
                                r["url"], r["final_url"]]))
    summary = (f"# 链接存活检查：共 {len(rows)} 条，可达 {ok_n}，受限 {warn_n}（401/403/429），异常 {bad_n}；"
               f"并发 {args.concurrency}，耗时 {cost:.1f}s，缓存命中 {cached_n} 条")
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


def selftest() -> int:
    """`--selftest`：只回归**不依赖外部服务**的判据；不发任何请求、不读凭据、不写用户数据。

    覆盖：凭据形态校验、缓存文件路径推导、退避秒数计算、搜索 URL 归一化、403 分类、
    HTML→文本、slug 格式前置拒绝。真实抓取路径（超时/重试/限流等待/并发探活）**不在覆盖范围**，
    见末尾显式声明。
    """
    import io
    from contextlib import redirect_stderr, redirect_stdout

    ok = 0
    total = 0

    def ck(name: str, got, want) -> None:
        nonlocal ok, total
        total += 1
        good = got == want
        ok += good
        print("[%s] %s：实际=%r 期望=%r" % ("PASS" if good else "MISS", name, got, want))

    # A. 凭据形态（把 gh 的提示文本当 token 发出去是最坏的一种失败）
    ck("凭据形态：ghp_ 前缀 40 位 ⇒ 接受", _looks_like_token("ghp_" + "A1b2C3d4" * 5), True)
    ck("阴性：gh 的提示文本（含空格）⇒ 拒绝",
       _looks_like_token("fatal: please run gh auth login first"), False)
    ck("阴性：过短串 ⇒ 拒绝", _looks_like_token("ghp_abc"), False)

    # B. 缓存文件路径推导（同一 URL 必落到同一文件；不同 URL 不得撞 key）
    u1 = "https://api.github.com/repos/a/b"
    u2 = "https://api.github.com/repos/a/c"
    ck("缓存路径 = sha1 前 20 位 + .bin 且落在 CACHE_DIR",
       (_cache_file(u1).name, _cache_file(u1).parent == CACHE_DIR),
       (hashlib.sha1(u1.encode("utf-8")).hexdigest()[:20] + ".bin", True))
    ck("阴性：不同 URL 的缓存键不得相同", _cache_file(u1) == _cache_file(u2), False)
    ck("阴性：TTL=0 ⇒ 缓存关闭（不读盘直接 None）", cache_get(u1, 0), None)

    # C. 退避秒数（纯计算；限流等待实际睡不睡不在此测）
    ck("退避：Retry-After=120 ⇒ 被 RATE_LIMIT_MAX_WAIT 封顶",
       _rate_limit_wait({"Retry-After": "120"}), min(121, RATE_LIMIT_MAX_WAIT))
    ck("退避：Retry-After=3 ⇒ 3+1 秒", _rate_limit_wait({"Retry-After": "3"}),
       min(4, RATE_LIMIT_MAX_WAIT))
    ck("阴性：无法判定的头 ⇒ 保守默认 15s（不得当 0s 立即重试）", _rate_limit_wait({}), 15)

    # D. URL 归一化
    ck("URL 归一化：空格转 + 且 sort 为空时不出现 sort 参数",
       _search_url(SEARCH_ENDPOINT, "a b", "", 30), SEARCH_ENDPOINT + "?q=a+b&per_page=30")
    ck("URL 归一化：限定符编码 + sort/order 追加",
       _search_url(SEARCH_ENDPOINT, "topic:cli stars:>100", "stars", 100),
       SEARCH_ENDPOINT + "?q=topic%3Acli+stars%3A%3E100&per_page=100&sort=stars&order=desc")

    # E. 403 分类
    ck("403 分类：cf-ray ⇒ CDN 反爬（人工可访问，非失效）",
       _classify_403({"cf-ray": "8x"}), "403-CDN反爬(Cloudflare，人工可访问)")
    ck("阴性：普通 nginx 403 不得误判成反爬/限流",
       _classify_403({"Server": "nginx"}), "403-拒绝(需授权或反爬，无法自动区分)")

    # F. HTML→文本
    ck("HTML→文本：去 script、解实体、压空行",
       html_to_text(b"<html><script>var x=1</script><p>a &amp; b</p></html>"), "a & b")

    # G. 阴性对照：slug 格式不合必须在**发请求之前**拒绝（此路径不触网）
    try:
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            github_repo_metrics("a/b/c", use_cache=False)
        slug_rc = "未拒绝"
    except SystemExit as e:
        slug_rc = e.code
    ck("阴性：slug 含两个 / ⇒ 未发请求即拒（rc=2）", slug_rc, 2)

    print("未覆盖：实际网络抓取路径（fetch() 的 30s 超时 / 2-4-8s 退避重试 / 403 限流等待 / "
          "--check-links 并发探活 / 真实 GitHub 响应解析）")
    print("=== selftest：%d/%d ===" % (ok, total))
    return 0 if ok == total else 1


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
    ap.add_argument("--selftest", action="store_true",
                    help="运行内置自检：只测不依赖网络的判据（参数解析/缓存路径/退避/URL 归一化/403 分类），不发任何请求")
    args = ap.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    use_cache = not args.no_cache

    if args.dry_run and not (args.github_search or args.github_code_search):
        print("[WARN] --dry-run 只对 --github-search / --github-code-search 生效，本次忽略", file=sys.stderr)

    if args.check_links:
        _run_check_links(args)
        return

    if args.github_search:
        # P3：**不在此 eager 解析凭据** —— 缓存命中根本不需要凭据，过早解析等于白付一张
        # `gh auth token` 子进程（本机 ≈120 ms／非沙箱终端 ≈790 ms）。真实要发请求时由
        # `fetch()` 惰性解析；`--github-code-search` 的强制认证校验也已改为"缓存未命中才校验"。
        token = args.token
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
        # P3：**不在此 eager 解析凭据** —— 缓存命中根本不需要凭据，过早解析等于白付一张
        # `gh auth token` 子进程（本机 ≈120 ms／非沙箱终端 ≈790 ms）。真实要发请求时由
        # `fetch()` 惰性解析；`--github-code-search` 的强制认证校验也已改为"缓存未命中才校验"。
        token = args.token
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
        # P3：**不在此 eager 解析凭据** —— 缓存命中根本不需要凭据，过早解析等于白付一张
        # `gh auth token` 子进程（本机 ≈120 ms／非沙箱终端 ≈790 ms）。真实要发请求时由
        # `fetch()` 惰性解析；`--github-code-search` 的强制认证校验也已改为"缓存未命中才校验"。
        token = args.token
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

    # N4：原始二进制下载（--out 且非文本/grep）走流式落盘，整响应不进内存
    raw_out = bool(args.out) and not (args.text or args.grep)
    try:
        content = fetch(args.url, use_cache=use_cache, ttl=args.ttl,
                        out_file=args.out if raw_out else None)
    except SystemExit:
        if args.out and Path(args.out).exists():
            print(f"[WARN] 抓取失败，{args.out} 未被更新（其中仍是上一次的旧结果），请勿误用", file=sys.stderr)
        raise
    if content is None:
        return  # 已流式写入 args.out，无需后续处理
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
