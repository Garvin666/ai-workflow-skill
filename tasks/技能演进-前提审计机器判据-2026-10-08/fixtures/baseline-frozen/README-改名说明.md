# 本目录 SKILL.md 已改名（2026-10-08）

- 本目录原含 `SKILL.md`（frontmatter `name: ai-workflow`, version 4.21.0）。由于**会话级技能面会递归索引技能目录下的 `SKILL.md`**，它与技能本体（v4.24.0）**同名**，构成加载歧义（同一次会话的技能列表里出现 3 条 `ai-workflow`）。
- 处置：**只把文件名改为 `SKILL.4.21.0.md`，文件内容零改动**（字节与 sha256 均未变），目录未移动、`manifest.sha256` 未改、frontmatter 未改。
- 依据：技能本体既有先例 `_archive/backups/_backup-v3.3.0/SKILL.v3.3.0.md`（同样非 `SKILL.md` 名）从未被索引。
- 复原：把文件名改回 `SKILL.md` 即可（sha256 见下表）。
- 核查任务：`E:\ChatGPT\工作流\tasks\工作区-ai-workflow应用最新版-2026-10-08\`

| 文件 | 改名后 | 字节 | sha256 |
| --- | --- | --- | --- |
| 原 `SKILL.md` | `SKILL.4.21.0.md` | 141347 | `d8577a12eacbbab45a2c1458267f9871e83ab353ec28f6b2cb7b457b7ee1d420` |
