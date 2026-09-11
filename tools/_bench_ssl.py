#!/usr/bin/env python3
# 量化瓶颈 A：http_transport 每次请求都 ssl.create_default_context() 的冗余开销
import ssl, time

N = 2000
t0 = time.time()
for _ in range(N):
    ctx = ssl.create_default_context()  # 当前代码的逐请求行为
t_old = (time.time() - t0) * 1000
print(f"[before] create_default_context x{N} = {t_old:.1f} ms  ({t_old/N:.3f} ms/次)")

t0 = time.time()
ctx = ssl.create_default_context()  # 修复后：仅创建一次
for _ in range(N):
    _ = ctx  # 复用同一 context
t_new = (time.time() - t0) * 1000
print(f"[after ] 复用同一 context x{N} = {t_new:.1f} ms（首次后 ~0/次）")
print(f"预期每批 {N} 个请求节省：~{t_old:.0f} ms（纯冗余计算，与网络无关）")
