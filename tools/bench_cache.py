#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bench_cache.py —— 实测 B1（启动全量读盘）优化前后的差距。

做法：
  - 预置 N 条缓存文件；
  - 「旧行为」模拟：实例化时 glob + 全量 json.loads 全部文件（复刻被移除的 _load）；
  - 「新行为」：ProbeCache 惰性构造（不读盘）+ 查 1 个已缓存 URL（只读其单文件）。
两者对比给出启动 I/O 的真实加速比。
"""
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cache_probe import ProbeCache, ProbeResult, STATUS_OK  # noqa: E402


def fake_transport(url, timeout=10.0):
    return 200, url, 1.0


def seed(cache_dir: Path, n: int) -> None:
    c = ProbeCache(cache_dir, ttl_seconds=3600)
    now = time.time()
    for i in range(n):
        c.put(ProbeResult(url=f"http://example.com/{i}", status=STATUS_OK, ts=now))


def eager_load_simulation(cache_dir: Path) -> float:
    """复刻被移除的 _load：glob 全部 + 全量解析。"""
    t0 = time.time()
    for p in cache_dir.glob("*.json"):
        json.loads(p.read_text(encoding="utf-8"))
    return time.time() - t0


def main() -> int:
    N = 3000
    tmp = Path(tempfile.mkdtemp(prefix="bench_cache_"))
    seed(tmp, N)
    print(f"缓存规模：{N} 条文件 @ {tmp}")

    # 旧：启动全量读盘
    t_eager = eager_load_simulation(tmp)

    # 新：惰性构造 + 查 1 条（只读单文件）
    t0 = time.time()
    c = ProbeCache(tmp, ttl_seconds=3600)          # 构造：不读盘
    r = c.get("http://example.com/0")             # 查 1 条：只读 1 文件
    t_lazy = time.time() - t0

    speedup = t_eager / t_lazy if t_lazy > 0 else float("inf")
    print(f"旧（启动全量读 {N} 文件）：{t_eager*1000:.1f} ms")
    print(f"新（惰性构造+查1条）    ：{t_lazy*1000:.1f} ms")
    print(f"加速比（启动 I/O）       ：{speedup:.1f}×")
    assert r is not None and r.status == STATUS_OK, "查到的缓存应有效"
    # 即便只查 1 条，新方案也应远快于旧方案全量读
    assert speedup > 50, f"惰性加载加速比应很大，实际 {speedup:.1f}×"
    print("\n[OK] B1 优化实测成立：启动 I/O 由 O(N) 全量读降为 O(1) 按需读")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
