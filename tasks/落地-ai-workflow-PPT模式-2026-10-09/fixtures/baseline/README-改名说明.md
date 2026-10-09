# 本目录 `SKILL.md` 已改名（2026-10-09）

- 本目录原含 `SKILL.md`（frontmatter `name: ai-workflow`, version 4.24.0）—— 它是**改动前的冻结基线副本**。
  由于**会话级技能面会递归索引技能目录下的 `SKILL.md`**，它与技能本体同名，构成加载歧义。
- 处置：**只把文件名改为 `SKILL.v4.24.0.md`，文件内容零改动**（字节与 sha256 均未变）；
  目录未移动、`manifest.sha256` 未改、frontmatter 未改。
- 依据（既有先例，2026-10-08 「技能面同名歧义收敛」）：
  `tasks/技能增强-ai-workflow-v4.10.0-2026-09-27/基线/SKILL.v4.8.0.md`
  与 `tasks/技能演进-前提审计机器判据-2026-10-08/fixtures/baseline-frozen/SKILL.v4.21.0.md`
  以及技能本体 `_archive/backups/_backup-v3.3.0/SKILL.v3.3.0.md`（从未被索引）。
- 复原：把文件名改回 `SKILL.md` 即可（sha256 见 `manifest.sha256` 首行）。
