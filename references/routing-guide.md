# 阶段感知模型路由 · 使用说明

> 配套 `SKILL.md`「阶段感知模型路由」与 `scripts/model_tiers.json`。
> 本文件本身属于「文档」阶段，按路由表走 **cheap** 档（本地 Ollama，近 0 成本）。

## 一、为什么路由

不同阶段推理成本弹性差异极大：规划/关键实现容错低，烧旗舰值得；探索/调研/测试/文档
容错高，烧旗舰是纯浪费。按阶段选模型而非全程旗舰，行业实测编码场景成本降 **70–90%**
（findings-3：Haiku 比 Opus 便宜约 15×）。

## 二、三档位

| 档位 | 模型 | 适用阶段 | ¥/百万 token（输入/输出） |
| --- | --- | --- | --- |
| **strong** | deepseek-reasoner | 规划 / 关键实现 / 安全相关 | 4 / 16 |
| **mid** | deepseek-chat | 常规实现 | 1 / 2 |
| **cheap** | qwen2.5:7b（本地 Ollama） | 探索 / 调研 / 测试 / 文档 / 格式转换 | 0 / 0 |

价格取自官方公开价目表（标准档、非缓存价；启用缓存后更便宜）。换模型/改价只动
`model_tiers.json` 一个文件。

## 三、怎么调用

```bash
PY="C:/Users/26717/.workbuddy/binaries/python/envs/ai-workflow/Scripts/python.exe"
SK="C:/Users/26717/.workbuddy/skills/ai-workflow"

# 探索/文档档：走本地 Ollama，0 成本
"$PY" "$SK/scripts/ai_call.py" --tier cheap --prompt-file 调研笔记.txt --out 总结.md

# 规划/关键实现档：走强模型，并回显 token 用量与成本
"$PY" "$SK/scripts/ai_call.py" --tier strong --stats --prompt-file 方案.md

# 批量（测试档）：并发跑一批用例，自动写账本
"$PY" "$SK/scripts/ai_call.py" --tier cheap --batch-file cases.txt --concurrency 4
```

`--tier` 自动按 `model_tiers.json` 解析 base/key/model/price；本地档（Ollama）无需真实 key，
脚本注入 `none` 占位。每次调用（成功）会把 `档位 / 模型 / token / 成本` 追加到
`~/.workbuddy/cache/ai-workflow/usage_ledger.jsonl` 账本。

## 四、怎么看降本

账本里的真实 token 用量 × 官方价目表，即可得到「路由后成本」与「若全程强模型」的反事实成本：

```
降本% = (全程强模型成本 − 路由后成本) / 全程强模型成本
```

token 只取决于文本、与是否联网无关；因此**即使本机没配 AI_API_KEY / Ollama 没起**，
也能用「真实 token 用量 × 价目表」做可复现测算。配好凭据或起 Ollama 后，账本直接出
真实账单口径的降本%。

## 五、硬规则（红线）

1. 探索段**默认** cheap，不得无理由升档。
2. 红线相关产出（安全/资金/权限/凭据/不可逆动作）仍 strong + 必要双审，不因降本放松查收。
3. 模型档位在 `plan.yaml` 每步的「模型档位」字段注明，便于回溯与成本核对。
