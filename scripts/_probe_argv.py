import argparse, sys

def build():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    wp = sub.add_parser("with")
    wp.add_argument("--base", default=None)
    wp.add_argument("--timeout", type=float, default=180.0)
    wp.add_argument("cmd", nargs=argparse.REMAINDER)
    return p

cases = [
    ["with", "selftest"],
    ["with", "--timeout", "150", "--", "python", "x.py", "selftest"],
    ["with", "--", "python", "x.py"],
    ["with", "python", "x.py"],
    ["--timeout", "150", "with", "--", "python", "x.py"],
]
out = []
for c in cases:
    try:
        ns = build().parse_args(c)
        out.append("%-58s -> cmd=%r base=%r t=%r" % (c, ns.cmd, ns.base, ns.timeout))
    except SystemExit as e:
        out.append("%-58s -> SystemExit(%s)" % (c, e.code))
pathlib.Path(r"D:\数模\tmp\argv_probe.txt").write_text("\n".join(out), encoding="utf-8")
print("ok")