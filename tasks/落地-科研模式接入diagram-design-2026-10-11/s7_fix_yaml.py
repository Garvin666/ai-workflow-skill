"""s7：通用修 plan.yaml —— flow mapping 行（`- {`）内的裸花括号会破坏 YAML 解析，统一降级为圆括号。"""
import yaml
from pathlib import Path

P = Path(__file__).resolve().parent / "plan.yaml"
raw = P.read_bytes()
assert raw.count(b"\r\n") == 0, "plan.yaml 应为 LF"
lines = raw.decode("utf-8").split("\n")
fixed = 0
for i, line in enumerate(lines):
    s = line.lstrip()
    if not s.startswith("{") and not s.startswith("- {"):
        continue
    first = line.index("{")
    if "}" not in line:
        print(f"  ⚠️ 跳过（本行无闭合花括号）line {i+1}: {line[:120]}")
        continue
    last = line.rindex("}")
    if last <= first:
        continue
    inner = line[first + 1:last]
    if "{" in inner or "}" in inner:
        new_inner = inner.replace("{", "(").replace("}", ")")
        lines[i] = line[:first + 1] + new_inner + line[last:]
        fixed += 1
        print(f"  修 line {i+1}: ...{new_inner[:80]}...")

out = "\n".join(lines)
P.write_bytes(out.encode("utf-8"))

d = yaml.safe_load(out)
print("修复", fixed, "行；YAML 解析 OK，顶层键：", list(d.keys()))
print("steps 数：", len(d["steps"]), "｜meta 键数：", len(d["meta"]))
