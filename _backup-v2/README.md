# 备份说明

| 目录/文件 | 内容 | 说明 |
| --- | --- | --- |
| `_backup-v1/SKILL.v1.md` | v1.0 原版 | 含 scripts/assets/references 全量原版 |
| `_backup-v2/SKILL.v2.md` | v2.0 | 本目录内 scripts/assets/references 为 v2.0 状态 |

**v2.1 → v2.2 的差异**未单独留快照，具体改动逐条记录在：
- `E:/ChatGPT/工作流/tasks/技能改造-ai-workflow-2026-09-10/改动对照表.md`（v1→v2.0）
- `E:/ChatGPT/工作流/tasks/技能增强-ai-workflow-v2.1-2026-09-10/改动对照表-v2.1.md`（v2.0→v2.1）
- `E:/ChatGPT/工作流/tasks/技能增强-ai-workflow-v2.2-2026-09-10/改动对照表-v2.2.md`（v2.1→v2.2）

**建议**：如需精确逐次回滚，在本目录执行 `git init && git add -A && git commit -m "ai-workflow v2.2 baseline"`，
之后再改就有完整 diff 历史（比目录快照更可靠）。
