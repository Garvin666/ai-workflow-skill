"""s1 附：A/B 对照 —— 新增第 4 个 lock 后，三个旧上游的 lint 结论是否逐条不回归。

对照设计（消掉变量）：lint 脚本**一字未改**；每个 lock 自成一个判定域。
A 侧 = 只喂单个旧 lock 跑（等价于「只有该上游存在」）；
B 侧 = 全量跑（4 个 lock）中属于该上游的结论。
两侧的 (状态, 技能, 判据名) 集合必须逐条一致。
"""
import collections
import pathlib
import re

D = pathlib.Path("tmp/hairline-20261009")
PAT = re.compile(r"^\[\s*(OK|FAIL|SKIP|WARN)\s*\]\s+(\S+)\s+·\s+(.*)$")


def rows(path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = PAT.match(line)
        if m:
            out.append((m.group(1), m.group(2), m.group(3).split(" — ")[0]))
    return out


def main():
    full = rows(D / "lint-after.txt")
    print(f"全量跑结论行数：{len(full)}")
    print(f"非 OK 项：{ [r for r in full if r[0] != 'OK'] or '无' }")
    total_mismatch = 0
    for name in ("mattpocock", "humanizer", "ppt-master"):
        sub = rows(D / f"lint-{name}.txt")
        keys = {(s, t) for _, s, t in sub}
        hit = [(st, s, t) for st, s, t in full if (s, t) in keys]
        ca, cb = collections.Counter(sub), collections.Counter(hit)
        only_a = ca - cb
        only_b = cb - ca
        total_mismatch += sum(only_a.values()) + sum(only_b.values())
        print(f"\n--- {name} ---")
        print(f"  A 侧（单 lock 跑）：{len(sub)} 条")
        print(f"  B 侧（全量跑命中）：{len(hit)} 条")
        print(f"  仅 A 侧有：{dict(only_a) or '无'}")
        print(f"  仅 B 侧有：{dict(only_b) or '无'}")
    print(f"\n=== A/B 结论：不一致项 {total_mismatch} 个 ===")
    return 1 if total_mismatch else 0


if __name__ == "__main__":
    raise SystemExit(main())
