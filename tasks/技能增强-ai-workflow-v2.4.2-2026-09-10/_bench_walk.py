# -*- coding: utf-8 -*-
"""公平基准：同一目录、同一跳读规则下对比两种遍历方式（预热后各跑 3 次取最小值）。

old = os.walk + os.path.getsize（每个文件一次额外 stat 系统调用）
new = os.scandir + DirEntry.stat()（Windows 复用 FindFirstFile 已返回的数据）
"""
import os
import sys
import time

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"E:\ChatGPT\量化分析与数据分析"
SKIP = frozenset({".git", "node_modules", "__pycache__", ".venv", "venv"})


def walk_old(root, skip):
    """v2.4 旧实现口径"""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                out.append(os.path.getsize(fp))
            except OSError:
                pass
    return out


def walk_new(root, skip):
    """v2.4.2 优化实现"""
    out = []
    stack = [str(root)]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name not in skip:
                                stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            out.append(entry.stat(follow_symlinks=False).st_size)
                    except OSError:
                        continue
        except OSError:
            continue
    return out


def best(fn, n=3):
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        res = fn(ROOT, SKIP)
        times.append((time.perf_counter() - t0) * 1000)
    return min(times), times, len(res), sum(res)


# 预热（消除首次冷缓存偏心）
walk_old(ROOT, SKIP)
walk_new(ROOT, SKIP)

t_old, all_old, n_old, sz_old = best(walk_old)
t_new, all_new, n_new, sz_new = best(walk_new)

print("== 预热后各跑 3 次，取最小值 ==")
print(f"旧 os.walk+getsize   : {t_old:9.0f} ms   明细 {[f'{x:.0f}' for x in all_old]}")
print(f"新 os.scandir+stat   : {t_new:9.0f} ms   明细 {[f'{x:.0f}' for x in all_new]}")
print(f"加速比               : {t_old / t_new:.2f}x")
print()
print(f"文件数  旧 {n_old:,} / 新 {n_new:,}  -> {'一致 ✅' if n_old == n_new else '不一致 ❌'}")
print(f"总字节  旧 {sz_old:,} / 新 {sz_new:,}  -> {'一致 ✅' if sz_old == sz_new else '不一致 ❌'}")
