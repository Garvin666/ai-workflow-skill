#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段感知模型路由 (stage_router.py)

对应优化方案「优化 3：阶段感知模型路由」：规划→旗舰、实现→中档、探索/测试/文档→最便宜。
行业实测（调研-模型路由报告 §3.1.4）：编码场景阶段路由可降本 70–90%；探索段用便宜模型
（如 Haiku 比 Opus 便宜约 15×）跑只读调研。

本模块是**纯策略**：给定阶段 + 模型注册表，返回应选档位与具体模型名，不发起任何网络/模型调用，
可离线单测。最终由调用方把 tier 映射到具体模型（本地 Ollama/DeepSeek/Qwen 或云 API）。

红线：CRITICAL（安全/资金/权限相关）永远旗舰模型，且 policy 无法降级 —— 对应工作流「高危产出必送独立审核」这一类情形（v2.5.3 起独立审核为抽查制，三类必送：高危产出／用户点名／返修触顶）。
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Tier(str, Enum):
    FLAGSHIP = "flagship"   # 强模型：规划、关键实现、安全相关
    MID = "mid"             # 中档：一般实现
    CHEAP = "cheap"         # 便宜模型：探索 / 调研 / 测试 / 文档


class Stage(str, Enum):
    EXPLORE = "explore"     # 只读调研、检索、找文件
    PLAN = "plan"           # 六要素澄清、方案评审
    IMPLEMENT = "implement" # 代码实现
    CRITICAL = "critical"   # 安全/资金/权限相关实现（红线：必须强模型 + 人工双审）
    TEST = "test"           # 测试、质量门禁
    DOC = "doc"             # 文档、报告、总结


# 默认阶段→档位映射，可被 policy 覆盖（CRITICAL 除外）
DEFAULT_MAP: dict[Stage, Tier] = {
    Stage.EXPLORE: Tier.CHEAP,
    Stage.PLAN: Tier.FLAGSHIP,
    Stage.IMPLEMENT: Tier.MID,
    Stage.CRITICAL: Tier.FLAGSHIP,
    Stage.TEST: Tier.CHEAP,
    Stage.DOC: Tier.CHEAP,
}

# 人类可读说明，便于审计与展示
_STAGE_DESC = {
    Stage.EXPLORE: "只读调研/检索（可容忍便宜模型）",
    Stage.PLAN: "规划与方案评审（需强推理）",
    Stage.IMPLEMENT: "常规代码实现",
    Stage.CRITICAL: "安全/资金/权限相关实现",
    Stage.TEST: "测试与质量门禁",
    Stage.DOC: "文档/报告/总结",
}


@dataclass
class RouteDecision:
    stage: Stage
    tier: Tier
    model: Optional[str]
    reason: str

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "stage_desc": _STAGE_DESC[self.stage],
            "tier": self.tier.value,
            "model": self.model,
            "reason": self.reason,
        }


def route(
    stage: Stage,
    registry: dict[Tier, str],
    policy: Optional[dict[Stage, Tier]] = None,
    critical_requires_human_review: bool = True,
) -> RouteDecision:
    """
    返回某阶段的路由决策。

    :param stage: 工作流阶段
    :param registry: {tier: 具体模型名}，如 {Tier.CHEAP: "qwen2.5-7b", ...}
    :param policy: 可选覆盖（仅对非 CRITICAL 生效）
    :param critical_requires_human_review: CRITICAL 是否强制人工双审标注
    :raises KeyError: stage 不在映射中，或对应 tier 在 registry 中缺模型
    """
    mapping = dict(DEFAULT_MAP)
    if policy:
        for s, t in policy.items():
            if s == Stage.CRITICAL:
                continue  # 红线不可被 policy 降级
            mapping[s] = t

    tier = mapping[stage]

    # 红线：CRITICAL 永远旗舰，且 policy 无法降级
    if stage == Stage.CRITICAL:
        tier = Tier.FLAGSHIP
        if critical_requires_human_review:
            reason = "安全/资金/权限相关：强制旗舰模型 + 人工双审（红线不可降级）"
        else:
            reason = "安全/资金/权限相关：强制旗舰模型（红线不可降级）"
    else:
        reason = f"{stage.value} → 默认 {tier.value} 档"

    # 缺模型即报错，不静默返回 None（避免调用方误用）
    if tier not in registry:
        raise KeyError(f"注册表缺少档位 {tier.value} 的模型：registry={registry}")
    model = registry[tier]
    return RouteDecision(stage=stage, tier=tier, model=model, reason=reason)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="阶段感知模型路由（纯策略，打印决策）")
    ap.add_argument(
        "--stage", required=True,
        choices=[s.value for s in Stage],
        help="工作流阶段",
    )
    # registry 通过 --model flagship=... mid=... cheap=... 传入
    ap.add_argument("--flagship", default="", help="旗舰模型名")
    ap.add_argument("--mid", default="", help="中档模型名")
    ap.add_argument("--cheap", default="", help="便宜模型名")
    args = ap.parse_args(argv)

    registry = {}
    if args.flagship:
        registry[Tier.FLAGSHIP] = args.flagship
    if args.mid:
        registry[Tier.MID] = args.mid
    if args.cheap:
        registry[Tier.CHEAP] = args.cheap
    if not registry:
        # 无显式模型时给占位，便于纯策略演示
        registry = {t: f"<{t.value}>" for t in Tier}

    try:
        d = route(Stage(args.stage), registry)
    except KeyError as e:
        print(f"[ERR] {e}", file=__import__("sys").stderr)
        return 2
    print(json.dumps(d.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
