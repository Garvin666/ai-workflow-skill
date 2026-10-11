"""s3b：收紧断言重验（把「变更记录里引用旧串」与「真残留」分开）。"""
from pathlib import Path

F = Path(__file__).resolve().parents[2] / "references" / "research-mode.md"
back = F.read_text(encoding="utf-8")
lines = back.splitlines()

# 断言 1：旧串只允许出现在变更记录行（该行以 | v4.30.0 开头）
hits = [(i + 1, lines[i]) for i, l in enumerate(lines) if "外部数据图技能" in l]
assert hits, "旧串一处都不剩 —— 那变更记录里的引用说明岂不是也没了？"
bad = [(n, l[:40]) for n, l in hits if not l.startswith("| v4.30.0 ")]
assert not bad, f"真残留：{bad}"
print(f"断言1 OK：旧串仅出现在变更记录行 {[n for n,_ in hits]}（引用说明，非残留）")

# 断言 2：12 处新串都在位
NEWS = [
    "# 科研模式（research-mode，v4.30.0）",
    "| **R5 撰写与绘图** | 论文结构 ＋ **图**（交本仓 `diagram-mode`（示意图）或已接入的 `diagram-design`（数据图））",
    "归属判据与配图规范见 §7.11",
    "数据图走已接入的 `diagram-design`（N6 / §7.11）",
    "结果图走已接入的 `diagram-design`（N6 / §7.11）",
    "图 → `diagram-design`（数据图直用；示意图另叠",
    "| T1 | **工具只接线，不代管** |",
    "数据图与示意图 → 已接入的 `diagram-design`；示意图**另叠**",
    "N6 / §7.11 的图通道确有机器输入，但**全是复用**",
    "**图片段分界已改按「编码方式」重划**",
    "**本模式只接线、不承担安装**",
    "| v4.30.0 | 2026-10-11 | **科研制图通道落地**",
]
missing = [s for s in NEWS if s not in back]
assert not missing, f"缺失：{missing}"
print(f"断言2 OK：{len(NEWS)} 处新串全部在位")

# 断言 3：§7.11 结构完整
SEC = ["### 7.11 科研制图（R5 展开，v4.30.0 新增）",
       "#### 7.11.1 通道归属", "#### 7.11.2 科研场景 → 类型映射",
       "#### 7.11.3 论文配图八条（RF1–RF8，纪律项）",
       "#### 7.11.4 输出拨盘", "#### 7.11.5 机器自检",
       "#### 7.11.6 与既有面的分界", "#### 7.11.7 诚实边界"]
miss2 = [s for s in SEC if s not in back]
assert not miss2, f"§7.11 缺小节：{miss2}"
print(f"断言3 OK：§7.11 的 {len(SEC)} 个小节齐")

# 断言 4：RF1–RF8 各出现一次
for k in ["RF1", "RF2", "RF3", "RF4", "RF5", "RF6", "RF7", "RF8"]:
    c = back.count(f"**{k}**")
    assert c == 1, f"{k} 出现 {c} 次"
print("断言4 OK：RF1–RF8 各一次")

# 断言 5：既有节未被破坏
assert back.count("## 6. 产出义务 N1–N6") == 1
assert back.count("## 8. 交付前自检（10 项 = 继承 6 + 新增 4）") == 1
assert back.count("## 9. 诚实边界（如实登记，勿夸大）") == 1
assert back.count("## 变更记录") == 1
print("断言5 OK：既有节头各一处")
print("字节数：", len(back.encode("utf-8")), "｜行数：", len(lines))
