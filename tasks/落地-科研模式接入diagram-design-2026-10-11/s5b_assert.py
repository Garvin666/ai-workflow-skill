"""s5b：收紧断言重验 external-skills.md（把「历史描述 / 第五上游指代」与「真残留」分开）。"""
from pathlib import Path

ES = Path(__file__).resolve().parents[2] / "references" / "external-skills.md"
back = ES.read_text(encoding="utf-8")
lines = back.splitlines()

# 断言 1：「五上游」只允许出现在「历史描述」或「第五上游」指代里
hits = [(i + 1, l) for i, l in enumerate(lines) if "五上游" in l]
allowed = [(n, l) for n, l in hits if ("五次泛化" in l) or ("第五上游" in l)]
bad = [(n, l[:60]) for n, l in hits if (n, l) not in allowed]
assert not bad, f"真残留：{bad}"
print(f"断言1 OK：「五上游」共 {len(hits)} 处，全部为历史描述 / 第五上游指代 → {[n for n,_ in hits]}")

# 断言 2：六上游化的 4 处
NEWS = [
    "# 外部技能路由与适配（外部技能簇 · 六上游）",
    "> **当前六个上游**（§1.1–§1.5 ＋ §1.7）",
    "## 一、六个上游",
    "# 查 .vendor/ 下全部 lock 登记的外部技能（六上游）",
    "### 1.7 diagram-design（1 个，扁平外挂；**第六上游**）",
    "**第六上游（`diagram-design`，1 个，按 §二 两分类）**",
    "### 7.6 diagram-design（复制安装，无补丁）",
    "12. **`diagram-design` 的边界（引擎 ≠ 契约；装态降级；默认 HTML）**",
    "> ⚠️ **本节五个不是上游**；本簇的**第六上游** `diagram-design` 编号虽在其后（§1.7）",
    "2026-10-11 六次泛化为**六上游**并登记 **diagram-design**",
]
missing = [s for s in NEWS if s not in back]
assert not missing, f"缺失：{missing}"
print(f"断言2 OK：{len(NEWS)} 处六上游化内容全部在位")

# 断言 3：既有结构未被破坏
KEEP = ["### 1.1 mattpocock-skills-zh-CN", "### 1.2 ppt-master", "### 1.3 humanizer",
        "### 1.4 hairline-create", "### 1.5 archify", "### 1.6 本地已装·非 vendored",
        "## 二、调用口径", "## 三、路由表", "## 四、只取机制", "## 五、已知边界",
        "## 六、机器检查", "## 七、同步上游",
        "### 7.1 ppt-master（零拷贝，无补丁）", "### 7.4 archify（复制安装，无补丁）",
        "### 7.5 §1.6 的五个本地技能（**不适用本节**）"]
miss2 = [s for s in KEEP if s not in back]
assert not miss2, f"既有结构缺失：{miss2}"
print(f"断言3 OK：既有 {len(KEEP)} 个节 / 小节全在")

# 断言 4：小节编号唯一（1.1–1.7 / 7.1–7.6 各一次）
import re
for k in ["### 1.7", "### 7.6", "### 7.5"]:
    c = back.count(k)
    assert c == 1, f"{k} 出现 {c} 次"
print("断言4 OK：新增小节编号唯一")
print("字节数：", len(back.encode("utf-8")), "｜行数：", len(lines))
