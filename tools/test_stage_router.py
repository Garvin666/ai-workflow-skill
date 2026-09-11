#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stage_router.py 最小测试运行器（无 pytest / 无网络依赖）。
覆盖：默认映射 / policy 覆盖 / CRITICAL 红线不可降级 / 缺模型报错。
运行：python test_stage_router.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from stage_router import (  # noqa: E402
    Tier,
    Stage,
    route,
)


REG = {
    Tier.FLAGSHIP: "deepseek-v3",
    Tier.MID: "qwen2.5-32b",
    Tier.CHEAP: "qwen2.5-7b",
}


def test_default_mapping():
    assert route(Stage.EXPLORE, REG).tier == Tier.CHEAP
    assert route(Stage.PLAN, REG).tier == Tier.FLAGSHIP
    assert route(Stage.IMPLEMENT, REG).tier == Tier.MID
    assert route(Stage.TEST, REG).tier == Tier.CHEAP
    assert route(Stage.DOC, REG).tier == Tier.CHEAP


def test_policy_override_non_critical():
    # 把 implement 从 mid 降到 cheap（非红线，允许）
    d = route(Stage.IMPLEMENT, REG, policy={Stage.IMPLEMENT: Tier.CHEAP})
    assert d.tier == Tier.CHEAP
    assert d.model == "qwen2.5-7b"


def test_critical_red_line_not_downgradable():
    # 即便 policy 想把 critical 降到 cheap，也必须保持 flagship
    d = route(Stage.CRITICAL, REG, policy={Stage.CRITICAL: Tier.CHEAP})
    assert d.tier == Tier.FLAGSHIP, "CRITICAL 红线不可被 policy 降级"
    assert d.model == "deepseek-v3"
    assert "人工双审" in d.reason


def test_critical_default_flagship():
    d = route(Stage.CRITICAL, REG)
    assert d.tier == Tier.FLAGSHIP
    assert "人工双审" in d.reason


def test_missing_model_raises():
    partial = {Tier.FLAGSHIP: "x"}  # 缺 mid / cheap
    try:
        route(Stage.EXPLORE, partial)
        raise AssertionError("缺模型时应抛 KeyError")
    except KeyError:
        pass


def test_model_resolution():
    d = route(Stage.PLAN, REG)
    assert d.model == "deepseek-v3"
    assert d.to_dict()["stage"] == "plan"


TESTS = [
    test_default_mapping,
    test_policy_override_non_critical,
    test_critical_red_line_not_downgradable,
    test_critical_default_flagship,
    test_missing_model_raises,
    test_model_resolution,
]


def main() -> int:
    ok = 0
    for fn in TESTS:
        try:
            fn()
            print(f"[PASS] {fn.__name__}")
            ok += 1
        except AssertionError as e:
            print(f"[FAIL] {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{ok}/{len(TESTS)} 通过")
    return 0 if ok == len(TESTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
