#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cache_probe.py 的最小测试运行器（无 pytest 依赖，无网络依赖）。
用注入的 fake transport 验证：缓存命中 / 分类正确 / 单 URL 异常隔离 / 跨进程持久。

运行：python test_cache_probe.py
"""
import sys
import tempfile
import time
import json
from pathlib import Path

import tempfile as _tf  # noqa: E402


def _tmp() -> Path:
    return Path(_tf.mkdtemp(prefix="cache_probe_"))

sys.path.insert(0, str(Path(__file__).parent))
from cache_probe import (  # noqa: E402
    ProbeCache,
    ProbeResult,
    probe,
    run,
    classify,
    extract_urls,
    dedup_keep_order,
    STATUS_OK,
    STATUS_404,
    STATUS_BLOCKED,
    STATUS_ERR,
)


def fake_transport(responses: dict):
    """返回一个 transport：url -> (code, final_url, latency)；含 'boom' 抛异常。"""
    calls = {"n": 0}

    def _t(url: str, timeout: float = 10.0):
        calls["n"] += 1
        if "boom" in url:
            raise ValueError("network boom")
        code, final = responses.get(url, (200, url))
        return code, final, 5.0

    _t.calls = calls
    return _t


def test_classify():
    assert classify(200, "") == STATUS_OK, "2xx"
    assert classify(301, "") == STATUS_OK, "3xx"
    assert classify(404, "") == STATUS_404, "404"
    assert classify(403, "") == STATUS_BLOCKED, "403"
    assert classify(429, "") == STATUS_BLOCKED, "429"
    assert classify(500, "") == STATUS_ERR, "5xx"
    assert classify(None, "timeout") == STATUS_ERR, "timeout"


def test_cache_hit_and_persistence():
    tmp = _tmp()
    responses = {"http://a.com": (200, "http://a.com"), "http://dead.com": (404, "http://dead.com")}
    t = fake_transport(responses)

    # 第一次：未命中，调用 transport
    c1 = ProbeCache(tmp, ttl_seconds=3600)
    r1 = probe("http://a.com", c1, t)
    assert r1.status == STATUS_OK and not r1.cached
    assert t.calls["n"] == 1

    # 新进程/新实例：从磁盘加载，应命中缓存，transport 不再被调用
    c2 = ProbeCache(tmp, ttl_seconds=3600)
    r2 = probe("http://a.com", c2, t)
    assert r2.cached is True, "应命中磁盘缓存"
    assert t.calls["n"] == 1, f"缓存命中后不应再调用 transport，实际={t.calls['n']}"


def test_classification_end_to_end():
    tmp = _tmp()
    responses = {
        "http://ok.com": (200, "http://ok.com"),
        "http://gone.com": (404, "http://gone.com"),
        "http://blocked.com": (403, "http://blocked.com"),
        "http://err.com": (503, "http://err.com"),
    }
    t = fake_transport(responses)
    results = run(
        ["http://ok.com", "http://gone.com", "http://blocked.com", "http://err.com"],
        str(tmp),
        concurrency=4,
        transport=t,
    )
    by_url = {r.url: r.status for r in results}
    assert by_url["http://ok.com"] == STATUS_OK
    assert by_url["http://gone.com"] == STATUS_404
    assert by_url["http://blocked.com"] == STATUS_BLOCKED
    assert by_url["http://err.com"] == STATUS_ERR


def test_isolation():
    """坏 URL 抛异常不应中断整批，且被归为 ERR。"""
    tmp = _tmp()
    responses = {"http://ok.com": (200, "http://ok.com")}
    t = fake_transport(responses)
    results = run(
        ["http://ok.com", "http://boom.com", "http://ok.com/x"],
        str(tmp),
        concurrency=3,
        transport=t,
    )
    by_url = {r.url: r.status for r in results}
    assert by_url["http://ok.com"] == STATUS_OK
    assert by_url["http://boom.com"] == STATUS_ERR, "异常 URL 应隔离为 ERR"
    assert by_url["http://ok.com/x"] == STATUS_OK


def test_cache_corruption_ignored():
    """损坏的缓存 json 在 get() 时应被忽略并删除，不崩溃、不返回该条目。"""
    tmp = _tmp()
    # 写一个与本工具命名一致的损坏缓存文件（key 对应某 url）
    from cache_probe import ProbeCache as _PC

    bad_url = "http://bad.example.com/x"
    p = tmp / (_PC._key(bad_url) + ".json")
    p.write_text("{not valid json", encoding="utf-8")
    c = ProbeCache(tmp, ttl_seconds=3600)
    # 实例化不再全量读盘，故不崩溃
    assert c.get(bad_url) is None
    # 损坏文件应已被清理
    assert not p.exists(), "损坏缓存应在 get 时被删除"


def test_lazy_load_construct_is_cheap():
    """实例化不再全量读盘：构造大缓存目录也接近 O(1)。"""
    import tempfile as _t3
    big = Path(_t3.mkdtemp())
    # 预置 2000 条缓存
    for i in range(2000):
        u = f"http://e.com/{i}"
        ProbeCache(big, ttl_seconds=3600).put(
            ProbeResult(url=u, status=STATUS_OK, ts=time.time())
        )
    t0 = time.time()
    c = ProbeCache(big, ttl_seconds=3600)  # 不应读 2000 个文件
    dt = time.time() - t0
    assert dt < 0.05, f"惰性构造应极快，实际 {dt:.3f}s"


def test_prune_removes_expired():
    """prune 删除过期条目，保持目录有界。

    注意：put() 在正常写入时会把 ts 重置为“现在”（新鲜探测结果的语义），
    因此不能用 put 注入一个“旧 ts”来模拟过期。这里直接落盘一个旧 ts 的
    缓存文件，模拟很久以前写下的缓存，再验证 prune 只删它。
    """
    tmp = _tmp()
    c = ProbeCache(tmp, ttl_seconds=3600)
    # 新鲜条目：正常 put（ts 会被置为 now）
    c.put(ProbeResult(url="http://fresh.com", status=STATUS_OK))
    # 过期条目：直接写一个旧 ts 的磁盘文件（绕过 put 的 ts 重置）
    stale = ProbeResult(url="http://stale.com", status=STATUS_OK, ts=time.time() - 99999)
    c._path("http://stale.com").write_text(
        json.dumps(stale.to_row(), ensure_ascii=False), encoding="utf-8"
    )
    removed = c.prune()
    assert removed == 1, f"应删 1 条过期，实际 {removed}"
    assert c.get("http://fresh.com") is not None
    assert c.get("http://stale.com") is None


def test_extract_and_dedup():
    """从 markdown 抽取 URL 并保留顺序去重；末尾标点不应被吃进 URL。"""
    md = (
        "# 参考\n"
        "- 官方文档 https://docs.example.com/a 和 https://docs.example.com/a (重复)\n"
        "- 见 https://blog.example.com/p?x=1#sec.\n"  # 末尾句号应被剥离
        "- 图片 https://img.example.com/i.png)\n"      # 末尾 ) 应被剥离
    )
    got = None  # 仅占位，实际用临时文件
    # extract_urls 接收 Path，这里用临时文件模拟
    import tempfile as _t2
    p = Path(_t2.mkdtemp()) / "sample.md"
    p.write_text(md, encoding="utf-8")
    urls = extract_urls(p)
    assert "https://docs.example.com/a" in urls
    assert "https://blog.example.com/p?x=1#sec" in urls, f"末尾句号未剥离: {urls}"
    assert "https://img.example.com/i.png" in urls, f"末尾 ) 未剥离: {urls}"
    deduped = dedup_keep_order(urls)
    assert deduped.count("https://docs.example.com/a") == 1, "重复未去重"


TESTS = [test_classify, test_cache_hit_and_persistence, test_classification_end_to_end,
         test_isolation, test_cache_corruption_ignored, test_extract_and_dedup,
         test_lazy_load_construct_is_cheap, test_prune_removes_expired]


def main() -> int:
    ok = 0
    for fn in TESTS:
        try:
            fn()
            print(f"[PASS] {fn.__name__}")
            ok += 1
        except AssertionError as e:
            print(f"[FAIL] {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{ok}/{len(TESTS)} 通过")
    return 0 if ok == len(TESTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
