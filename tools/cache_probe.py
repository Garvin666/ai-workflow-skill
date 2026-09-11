#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨任务持久缓存 + 链接探活复用工具  (cache_probe.py)

解决工作流瓶颈 B2（检索缺口 → 验证税）：不同任务反复对相同 URL 做 HTTP 探活，
本工具把探活结果按 URL 哈希落盘，跨进程 / 跨任务复用，超过 TTL 才刷新。

分类语义（来自 ai-workflow P3 SOP）：
  OK       : 2xx/3xx 可达
  404      : 确属失效，必须修
  BLOCKED  : 401/403/429 等 4xx，多为反爬/限流/鉴权 —— 非失效（标注即可）
  ERR      : 超时 / SSL / 连接失败 / 5xx 等环境错误 —— 非站点失效（标注即可）

设计要点：
  - 单 URL 异常隔离，不中断整批；
  - 缓存损坏条目忽略、缓存写失败不致命；
  - 真实探测 HEAD 失败自动回退 GET，且同 host 只学一次；
  - 惰性按 key 加载：实例化不再全量读盘，只在实际查询某 URL 时读其一文件；
  - transport 可注入，便于无网络环境下单元测试。
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# ---- 状态常量 ----
STATUS_OK = "OK"
STATUS_404 = "404"
STATUS_BLOCKED = "BLOCKED"   # 401/403/429 等 4xx
STATUS_ERR = "ERR"

DEFAULT_UA = "cache-probe/1.0"


@dataclass
class ProbeResult:
    url: str
    status: str                 # OK / 404 / BLOCKED / ERR
    final_url: str = ""
    http_code: Optional[int] = None
    error: str = ""
    latency_ms: float = 0.0
    cached: bool = False
    ts: float = 0.0

    def to_row(self) -> dict:
        return asdict(self)


def classify(http_code: Optional[int], error: str) -> str:
    """把 (http_code, error) 映射到四类状态。"""
    if error:
        return STATUS_ERR
    if http_code is None:
        return STATUS_ERR
    if 200 <= http_code < 400:
        return STATUS_OK
    if http_code == 404:
        return STATUS_404
    if 400 <= http_code < 500:
        # 4xx：鉴权 / 反爬 / 限流，通常非失效（404 已单列）
        return STATUS_BLOCKED
    # 5xx 及未知：判环境错误，不轻易判失效
    return STATUS_ERR


# ---------------------------------------------------------------------------
# 传输层（真实 HTTP），可被测试注入的 fake transport 替换
# ---------------------------------------------------------------------------
def http_transport(
    url: str, timeout: float = 10.0, user_agent: str = DEFAULT_UA
) -> tuple[Optional[int], str, float]:
    """
    返回 (http_code, final_url, latency_ms)。
    异常时 http_code=None 且 final_url=错误描述字符串。
    HEAD 不被支持（405）或失败自动回退 GET。
    """
    # 复用进程内唯一 SSL context（实测 create_default_context 约 13ms/次，
    # 逐请求创建在千级批量上会白白烧掉 20s+ 纯计算，与网络无关）—— 瓶颈 A 修复。
    ctx = _ssl_context()
    start = time.time()

    host = urlparse(url).netloc
    # 同 host 已确认不支持 HEAD → 直接 GET，省一次往返（B2 优化）
    methods = ("GET",) if host in _head_unsupported else ("HEAD", "GET")
    for method in methods:
        req = Request(url, method=method, headers={"User-Agent": user_agent})
        try:
            with urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.getcode(), resp.geturl(), (time.time() - start) * 1000
        except HTTPError as e:
            if method == "GET":
                return e.code, getattr(e, "url", url), (time.time() - start) * 1000
            if e.code == 405:  # Method Not Allowed → 记下来并换 GET
                _head_unsupported.add(host)
                continue
            return e.code, getattr(e, "url", url), (time.time() - start) * 1000
        except URLError as e:
            if method == "GET":
                return None, str(getattr(e, "reason", e)), (time.time() - start) * 1000
            continue  # HEAD 失败，试 GET
        except Exception as e:  # TimeoutError / SSL / 其它
            if method == "GET":
                return None, f"{type(e).__name__}: {e}", (time.time() - start) * 1000
            continue
    return None, "all methods failed", (time.time() - start) * 1000


# 进程内记忆：已确认不支持 HEAD 的 host，避免对同一 host 多链接反复双程（B2）
_head_unsupported: set[str] = set()

# 进程内复用唯一 SSL context（瓶颈 A 修复：create_default_context ~13ms/次，
# 千级批量若逐请求创建会白白烧掉 20s+ 纯计算，与网络无关）
_ssl_context = functools.lru_cache(maxsize=1)(ssl.create_default_context)


# ---------------------------------------------------------------------------
# 持久缓存层
# ---------------------------------------------------------------------------
class ProbeCache:
    def __init__(self, cache_dir: Path, ttl_seconds: int = 7 * 86400):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # 惰性加载：启动不再全量读盘（B1 优化）。仅在实际查询某 URL 时按需读其单文件。
        self._store: dict[str, ProbeResult] = {}

    @staticmethod
    def _key(url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]

    def _path(self, url: str) -> Path:
        return self.cache_dir / (self._key(url) + ".json")

    def _read_file(self, url: str) -> Optional[ProbeResult]:
        """按需读单个缓存文件；缺失/损坏/过期返回 None（损坏与过期文件顺手删掉）。"""
        p = self._path(url)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            r = ProbeResult(**data)
        except Exception:
            try:
                p.unlink()  # 损坏条目：删掉，避免下次再读
            except Exception:
                pass
            return None
        if time.time() - r.ts > self.ttl:
            try:
                p.unlink()  # 过期：删掉，保持目录有界（B3）
            except Exception:
                pass
            return None
        return r

    def get(self, url: str) -> Optional[ProbeResult]:
        # 先查内存；未命中再按需读单文件（O(1) 而非启动 O(N) 全量读）
        r = self._store.get(url)
        if r is None:
            r = self._read_file(url)
            if r is not None:
                self._store[url] = r
        return r

    def prune(self) -> int:
        """删除过期（及损坏）缓存文件，返回删除条数。避免目录无限增长（B3）。"""
        now = time.time()
        removed = 0
        for p in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                expired = now - data.get("ts", 0) > self.ttl
            except Exception:
                expired = True  # 损坏文件也清掉
            if expired:
                try:
                    p.unlink()
                    removed += 1
                except Exception:
                    pass
        return removed

    def put(self, result: ProbeResult) -> None:
        result.ts = time.time()
        self._store[result.url] = result
        try:
            self._path(result.url).write_text(
                json.dumps(asdict(result), ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            # 缓存写失败不致命
            pass


# ---------------------------------------------------------------------------
# 探测
# ---------------------------------------------------------------------------
def probe(
    url: str,
    cache: ProbeCache,
    transport: Callable = http_transport,
    timeout: float = 10.0,
) -> ProbeResult:
    """先查缓存（命中直接返回），未命中才发请求并写回缓存。"""
    cached = cache.get(url)
    if cached is not None:
        cached.cached = True
        return cached
    try:
        code, final_url, latency = transport(url, timeout=timeout)
    except Exception as e:  # 双保险：transport 内部已捕获，这里兜底
        code, final_url, latency = None, f"{type(e).__name__}: {e}", 0.0
    error = "" if code is not None else final_url
    result = ProbeResult(
        url=url,
        status=classify(code, error),
        final_url=final_url,
        http_code=code,
        error=error,
        latency_ms=latency,
    )
    cache.put(result)
    return result


def run(
    urls: list[str],
    cache_dir: str,
    concurrency: int = 8,
    timeout: float = 10.0,
    ttl: int = 7 * 86400,
    transport: Callable = http_transport,
    prune: bool = False,
) -> list[ProbeResult]:
    cache = ProbeCache(Path(cache_dir), ttl_seconds=ttl)
    results: list[ProbeResult] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futures = {
            ex.submit(probe, u, cache, transport, timeout): u for u in urls
        }
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                # 极端兜底：单 URL 不应到这，但保证批处理不崩
                results.append(
                    ProbeResult(url=futures[f], status=STATUS_ERR, error=str(e))
                )
    if prune:
        removed = cache.prune()
        if removed:
            print(f"[prune] 清理过期/损坏缓存 {removed} 条")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def read_urls(path: Path) -> list[str]:
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


# 匹配 http/https URL；排除常见结尾标点，避免把句末「.」「)」「]」吃进 URL
_URL_RE = __import__("re").compile(r"https?://[^\s)\]>'\"\]\}]+")


def extract_urls(path: Path) -> list[str]:
    """从 markdown / html / 文本中抽取 http(s) URL（按顺序、不去重）。"""
    text = path.read_text(encoding="utf-8", errors="ignore")
    found = _URL_RE.findall(text)
    # 去掉个别被 trailing 标点带进来的尾巴
    cleaned = []
    for u in found:
        u = u.rstrip(".,;:")
        cleaned.append(u)
    return cleaned


def dedup_keep_order(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def summarize(results: list[ProbeResult]) -> dict:
    counts = {STATUS_OK: 0, STATUS_404: 0, STATUS_BLOCKED: 0, STATUS_ERR: 0}
    cached = 0
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
        if r.cached:
            cached += 1
    return {"counts": counts, "cached": cached, "total": len(results)}


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="跨任务持久缓存的链接探活工具")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--urls", help="URL 列表文件，每行一个，# 开头为注释")
    g.add_argument(
        "--from-files",
        nargs="+",
        metavar="MD",
        help="从一个或多个 markdown/html 抽取 http(s) URL 并去重（对应 P3 SOP 的 grep|check-links）",
    )
    ap.add_argument("--cache-dir", default=".cache/ai-workflow/probe", help="缓存目录")
    ap.add_argument("--out", default="probe_results.json", help="结果输出文件")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--ttl", type=int, default=7 * 86400, help="缓存有效期（秒）")
    ap.add_argument("--prune", action="store_true", help="运行后清理过期/损坏缓存，保持目录有界")
    args = ap.parse_args(argv)

    if args.from_files:
        urls: list[str] = []
        for f in args.from_files:
            urls.extend(extract_urls(Path(f)))
        urls = dedup_keep_order(urls)
    else:
        urls = read_urls(Path(args.urls))
    if not urls:
        print("[WARN] 未读到任何 URL", file=sys.stderr)
        return 2

    results = run(
        urls, args.cache_dir, args.concurrency, args.timeout, args.ttl,
        prune=args.prune,
    )
    Path(args.out).write_text(
        json.dumps([r.to_row() for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    s = summarize(results)
    print(f"总计 {s['total']} 条 ｜ 缓存命中 {s['cached']} 条")
    print(
        f"  OK={s['counts'][STATUS_OK]}  404(失效)={s['counts'][STATUS_404]}  "
        f"BLOCKED(反爬/限流)={s['counts'][STATUS_BLOCKED]}  ERR(环境)={s['counts'][STATUS_ERR]}"
    )
    print(f"结果已写入: {args.out}")
    # 失效链接单独列出，便于修
    dead = [r.url for r in results if r.status == STATUS_404]
    if dead:
        print(f"\n需修复的失效链接 ({len(dead)}):")
        for u in dead:
            print(f"  {u}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
