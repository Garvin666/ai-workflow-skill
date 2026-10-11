import yaml
from pathlib import Path

p = Path(__file__).resolve().parent / "plan.yaml"
txt = p.read_text(encoding="utf-8")
lines = txt.splitlines()
try:
    d = yaml.safe_load(txt)
    print("解析 OK，顶层键：", list(d.keys()))
except Exception as e:
    print(type(e).__name__, ":", e)
    mk = getattr(e, "problem_mark", None) or getattr(e, "context_mark", None)
    if mk:
        print("line", mk.line + 1, "col", mk.column + 1)
        for i in range(max(0, mk.line - 3), min(len(lines), mk.line + 4)):
            flag = ">>" if i == mk.line else "  "
            print(f"{flag}{i+1:4d}| {lines[i][:220]}")
