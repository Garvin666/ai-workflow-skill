# Laya 本地快判后端（laya-backend）

> **定位：影子 / 对照后端 —— 不接管判定。** Laya 是 `self-judge` / `method-judge` / `retrieval-judge` 三份契约里 **Realization B（独立 System 1 决策模型）** 的本地落地实现。按用户 **2026-09-23** 的决定，本后端以 **C1 形态** 接入：**保留"只上 A，不启用 B"的既定约束**，Laya 只与脑内协议**并行产出**用于对照，**路由与门禁一律仍由 A 决定**，直到温度拟合与一致率两项前提闭环后再另议切换。
>
> 本文件是三份 judge 手册 `§7.3` 的共同下沉点；**契约仍在各 judge 手册**，本文件只记"B 怎么跑、怎么调、有哪些实测边界"。
>
> **接入形态**：扩写 ai-workflow 本体（非独立技能）。新增 `scripts/laya_client.py` + `scripts/judges.json` + 本文件；三份 judge 手册仅在 §7.3 末尾加一条带时点的指向注记。**未改动任何既有判据、门禁与阈值口径。**
>
> **时点注记（2026-09-23 晚，v4.7.0）**：上文"三份 judge 手册"是 **v4.6.1 时点的原话，按「不删原文」保留**。v4.7.0 新增第四份 **`homework-judge`（模式选用 · 快判）**，本后端同步接入 —— 现为**四份 judge**：`self_judge` / `method_judge` / `retrieval_judge` / `homework_judge`。新契约见 `references/homework-judge.md`（其 §7.3 亦以本文件为下沉点）。

---

## 1. 部署事实（本机实测）

| 项 | 值 |
| --- | --- |
| 安装根 | `~/.workbuddy/laya/` —— 用户主目录下（**用 `~` 占位，不写本机用户名**；出站扫描第 3/4 项）；下文简称 **`<根>`** |
| 解释器 | `<根>\venv\Scripts\python.exe`（Python 3.13.12） |
| 服务脚本 | `<根>\app\laya_server.py`（标准库 HTTP，`--cli` / `--selfcheck` 也在这里） |
| 权重 | `<根>\models\english\`（807.0 MB）、`<根>\models\multilingual\`（646.8 MB） |
| 权重来源 | **hf-mirror.com（第三方社区镜像）**，仓库 sha `1c5edc17`；逐文件 sha256 见 `<根>\models\MANIFEST.json` |
| 版本锁定 | `<根>\requirements.lock.txt` |
| 监听 | `127.0.0.1:8731`（默认只回环） |
| 鉴权 | `Authorization: Bearer $LAYA_JUDGE_TOKEN`；token 持久化在 `HKCU\Environment`（用户级环境变量），**不落项目文件、不入 plan.yaml、不打日志**（S1） |
| 运维脚本 | `.workbuddy/laya/bin/`：`serve.cmd` / `.workbuddy/laya/bin/start_laya.ps1` / `.workbuddy/laya/bin/stop_laya.ps1` / `.workbuddy/laya/bin/status_laya.ps1` / `.workbuddy/laya/bin/register_autostart.ps1` / `.workbuddy/laya/bin/setup_token.py` |
| 开机自启 | 计划任务 `LayaJudge`（登录时触发，失败重启 3 次、间隔 1 分钟）。**注册需管理员权限一次**：非提权下 `Register-ScheduledTask` 必然返回「拒绝访问」（实测），注册脚本已加提权前置门禁（明确报错 + `exit 2`）。**未注册时服务不常驻，客户端走 `exit 3` 降级，工作流不中断** |

**实测版本**：`torch 2.14.0+cpu` / `laya 0.3.6` / `transformers 5.17.0` / `huggingface_hub 1.32.0` / `numpy 2.5.3` / `safetensors 0.8.0`。
> ⚠️ `transformers` 实装为 **5.17.0**（laya 0.3.6 声明 `>=4.48`，5.x 为跨大版本）。本机真跑已验证可用；**这是"声明兼容"，不等于"官方测试过"** —— 升级 transformers 前必须重跑 `laya_client.py --selfcheck`。

---

## 2. 调用方式（一步）

```bash
python scripts/laya_client.py --judge self-judge --state "帮我写个脚本，把这三份 CSV 合并成一份"
python scripts/laya_client.py --judge method-judge  --what "取 GitHub star 数" --input "repo a/b" \
       --expect "star 数与推送时间" --candidates "http_fetch.py,Grep,web_search"
python scripts/laya_client.py --judge retrieval-judge --need "该仓库是否还在维护" --clues "只有 owner/repo" \
       --workspace "<工作区根>" --candidates "本地资产,联网,历史留痕"
python scripts/laya_client.py --judge homework-judge --state "求函数 f(x)=x^2-4x+3 的最小值"   # v4.7.0 新增
python scripts/laya_client.py --selfcheck          # 探测服务可用性（0 可用 / 2 不可用 / 3 降级）
```

> `homework-judge` **不注入任何候选**（`build_questions` 对其无候选分支）—— 它的 Choice 是固定的模式三态，不依赖候选池，因此**不落在 `choice:11+` 越界温度桶**里。

输出即该 judge 的契约字段（见 `self-judge.md` §4 / `method-judge.md` §4 / `retrieval-judge.md` §4 / `homework-judge.md` §4），并附 `_laya` 元信息（`model_key` / `entropy_confidence` / `latency_ms` / `attempts` / `degraded`）。

**服务端原始形态**（`POST /v1/judge`，`curl` 可直接调）：

```json
{"state": "<请求原文或步骤三字段 JSON>",
 "questions": {"category": {"type":"choice","instructions":"...","criteria":{"chat":"...","code":"...","content":"..."}},
               "D1": {"type":"score","instructions":"...","criteria":["完全没有","有一点","比较明确","非常明确"]},
               "ambiguity": {"type":"noul","instructions":"..."}}}
```

> **一次前向出全部结论**：`laya.Agent.system_one` 在**单次前向**里并行评估 `questions` 里的**每一个**问题。所以**必须把该 judge 的全部维度塞进一次请求** —— 逐维调用＝逐次前向，会把 Laya 唯一的结构性优势浪费掉。

---

## 3. ★ 口径冲突（最容易踩，已写死）

| 量 | 定义 | 出处 |
| --- | --- | --- |
| 契约 `confidence` | **= max(distribution)** | `self-judge.md` §4 |
| Laya 自带 `confidence` | 熵置信 `1 − H(p)/log(k)` | 运行时字段 |

**这是两个不同的量**。`laya_client.py` 只取 `max(distribution)`，Laya 的熵置信另存 `_laya.entropy_confidence`，并已写入单测断言（`scripts/laya_client.py` 的 `map_self_judge` docstring + `<根>\app\_smoke_test.py`）。违反此口径即触犯「同一物理量的判据跨模块必须同源」。

其余映射：`ambiguity = noul ∈ [0.35, 0.65]`；`gap_class`/`source_class`/`mode` 在 top2 差距 < 0.15 时输出 `A+B` 组合；`needs_tool`/`needs_retrieval = noul ≥ 0.5`；`secondary` 在 top1/top2 差距 < 0.15 时输出。

**`homework_judge` 的两处刻意差异（v4.7.0）**：① `needs_homework` =（`mode` 恰为「作业题」）—— **派生字段，不来自任何问句**，从设计上消除 `mode` 与 flag 自相矛盾（同型坑见 `method-judge` 的 `needs_tool` × `gap_class`）；② **刻意不产 `secondary`** —— 模式本就允许并用，一件事只在一处表达（组合态只体现为 `mode = A+B`）。

---

## 4. 容错与降级

| 项 | 口径 |
| --- | --- |
| 探测超时 | 3 s（`/healthz` `/readyz`） |
| 判定超时 | 15 s（单 socket 超时；⚠️ stdlib `urllib` **不支持 (连接,读取) 分离超时**，需严格分离时改 `http.client` + `socket.settimeout`） |
| 重试 | 指数退避 `(0,2,4,8)`，最多 4 次尝试；**只重试可恢复失败**（连接/超时/5xx/429），4xx 不重试 |
| 快速降级 | 打 `/v1/judge` 前先 3 s 探 `/readyz`，失败**立即降级**（避免服务没起时走完 15 s×4） |
| 降级契约 | 进程 **退出码 3** + `{"degraded": true, "reason": "..."}`；调用侧**回退 Realization A（脑内协议）**，流程不得中断，但须留痕 `laya_status: degraded` |
| 与门禁的关系 | 按 `SKILL.md`「门禁不可用时的行为」：**只读动作**放行并标注"本次未经 Laya 校验"；**不可逆动作 fail-closed**。Laya **不参与**任何放行决策 |

### 4.1 ★ 环境代理会劫持本地回环（真实缺陷，v4.7.0 已修）

| 项 | 内容 |
| --- | --- |
| **现象** | 服务**正常运行**时，`laya_client.py --selfcheck` 与 `healthz()` 对 `http://127.0.0.1:8731` 返回 `HTTPError 502 Bad Gateway`（不是连接类错误） |
| **根因** | 本机环境变量 `HTTP_PROXY` / `HTTPS_PROXY` 均指向 `http://127.0.0.1:51717`，**stdlib `urllib` 默认按环境代理走**，连回环地址也照发代理 → 代理答 502 |
| **危害（关键）** | 502 属 **4xx/5xx 分支**，客户端会判"服务不可用" → **静默降级回 Realization A**：服务明明活着，影子后端却形同虚设，**且不留显式错误**（日志里只见 degraded） |
| **修法** | `scripts/laya_client.py` 新增 `_opener(url)`：目标为本地回环时返回 `urllib.request.build_opener(urllib.request.ProxyHandler({}))`（`_NO_PROXY_OPENER`），`_request` 改用 `_opener(url).open(...)` 取代裸 `urllib.request.urlopen(...)` |
| **判据** | 阴性对照：对**不可达的本地端口**，异常必须是**连接类**（`URLError`）而**非** `HTTPError 502` —— 若又见 502，说明代理旁路失效 |
| **排查提示** | 任何"本地服务明明在跑却被判不可用"的症状，**先查 `HTTP_PROXY`/`HTTPS_PROXY`**，再看服务端日志（见 §7） |

---

## 5. 与工作流节点的关系

```
阶段 0 第 1 步  self-judge ─┬─ A：脑内协议（主判据，产出写 meta.入口判定）  ← 路由只认这个
                            └─ B：Laya（影子，产出并列留痕，不参与路由）
阶段 0 第 3 步前 homework-judge ── 同上（落 meta.作业判定，v4.7.0）
阶段 3 六动作②  method-judge ── 同上（并列 laya 影子字段）
阶段 3 第 5 条前 retrieval-judge ── 同上

红线③ / 出站扫描 / 口径守卫 / 熔断(F1–F5) / 反思重试(T1–T3) ── Laya 完全不参与
```

**不可委派**（与 `self-judge.md` §8 同源）：不授权写操作、不替代安全关键门禁、不读全库、不进入执行期闭环。

**影子期出口条件（需人拍板，未闭环前不得切换）**：
1. 温度拟合完成（见 §6.1）；
2. N ≥ 50 条历史请求上 A/B **一致率**达标（阈值本身**未定值**；口径同 `self-judge.md` §10：只报"一致率"，**不声称"准确率"**）。

> ✅ **时点注记（2026-09-23 补）**：条件 2 此前**结构上无法满足** —— 不是样本不够，而是 **A 侧没有可复现实现**
> （脑内协议每次现场给分布 ⇒ 测出来的"一致率"是噪声）。现 A 侧的**聚合半边已落成代码**：
> `scripts/homework_model.py`（公式 = `references/homework-judge.md` §5.1 唯一口径源），
> 测量走 `homework_model.py agree --pairs <json>`（见该契约 §5.2）。
> ⚠️ 但：**真机 B 侧样本仍为 0 条**、A 侧**独立标注 0 条**、`ANCHORS`/`TAU` **未拟合**、**一致率阈值仍未定值** ——
> 条件 1 与条件 2 的**结论都不变**：工具解决"能不能测"，不解决"有没有得测"。

---

## 6. 实测边界与已知失效（如实登记，不粉饰）

### 6.1 出厂温度不可信（运行时硬证据）

加载 checkpoint 时 laya 自己会告警：

```
RuntimeWarning: laya: this checkpoint ships temperatures outside [0.5, 5] which would distort
confidence; clamping choice:11+=0.1006. Treat confidence from the affected buckets as uncalibrated.
```

意即 **`choice:11+` 桶的出厂温度 0.1006 越界、被强制夹到 0.5，该桶置信度官方自己声明"不可信"**。影响面：
- `self-judge` 的 `category` 只有 3 选项（`choice:3-5` 桶）→ **不落在受影响桶**；
- `method_judge` / `retrieval_judge` 的 **candidates 题一旦超过 10 个选项**即落入 `choice:11+` → **`fit_score` 不可作为阈值依据**。

这条比"出厂未拟合"更具体，也是"温度拟合前阈值不可采信"这条前提的**直接证据**。

### 6.2 ★ 已实测到的失效模式：candidates 题会被词面带偏

实测（multilingual，state 为"取 GitHub 仓库的 star 数"，候选 `[http_fetch.py, Grep, web_search]`）：

```json
{"gap_class": "事实",                      ← 正确
 "candidates": [{"tool": "Grep", "fit_score": 0.9452},   ← 明显错误：本机不可能有该仓库的 star 数
                {"tool": "http_fetch.py", "fit_score": 0.0218}, ...],
 "needs_tool": false}                       ← 与 gap_class=事实 自相矛盾
```

**结论：`candidates` 的单题形式在本机候选项上不可信 —— 高词频工具名（`Grep`）会被系统性高估。** 处置：影子期该字段**只做记录、不作依据**；若要正式启用，需改造问题形式（如把 candidates 与 `gap_class` 拆成两次调用、或在候选项文本里显式写出"本机可完成 / 需联网"判据）—— **此项改造属设计变更，待用户决定**。

> **时点注记（2026-09-23 晚些时候，同一任务复测；原文不删）**：上述"`Grep` 被系统性高估"**在复测中未复现**，故当前只能算**单例观察，不足以定为稳定失效模式**：
> | 轮次 | 候选集 | `Grep` 的 `fit_score` | top1 |
> | --- | --- | --- | --- |
> | 首次（`_verify_http4.json`） | `[http_fetch.py, Grep, web_search]`（3 项） | **0.4531**（top1） | `Grep` |
> | 复测（`_live_accept.json`，本轮） | `[http_fetch.py, gh api, Grep, web_search]`（4 项） | **0.0512**（末位） | `gh api` 0.886 |
>
> 两轮的差距来源**未定位**（候选集构成不同、ckpt 路由不同——见 §6.4——均可能是变量）。**诚实结论**：`candidates` 的 `fit_score` **跨调用不稳定**（同一工具在两次运行里从 top1 掉到末位），这与"温度未拟合"一致；**"不稳定"这一条是两轮共同支持的**，而"具体偏向 `Grep`"只有一轮证据。
> **`needs_tool=false` 与 `gap_class=事实` 自相矛盾**则在**两轮均复现**（本轮 `gap_class=事实+手脚` 仍 `needs_tool=false`），这一条可以定为稳定失效。

### 6.3 其它实测与已知项

| 项 | 实测/说明 |
| --- | --- |
| **中文必须用 multilingual** | 实测同题：multilingual `confidence=0.9969`（`code` 概率 0.9968，判对）；**english ckpt 跑中文** `confidence=0.4574`、分布 `chat .34/code .46/content .20` **分裂**且触发 `secondary` → 与评估报告"英文 ckpt 跑中文 ECE 0.376"的结论一致。【实测】⚠️ **但"不写 `--model` 就自动走 multilingual"是错的** —— 含英文标识符的中文步骤会被 Router 判成英文，见 **§6.4**。 |
| **CPU 延迟** | 8 问题一次前向（505 tokens）：**p50 ≈ 1150 ms**、min 1134 ms、max 1210 ms（4 线程 CPU）。冷加载 multilingual ≈ 59 s、english ≈ 35 s。 |
| **运行时不联网** | 把 `HTTP(S)_PROXY` 指向黑洞 + `HF_HUB_OFFLINE=1` 后仍能加载与推理 → 自证无隐式联网。【实测】 |
| `head_max_len` 上限 | 选项过多会抛 `ValueError: options exceed head_max_len`；**不要**为此缩小该值（应减少选项数或缩短选项描述）。 |
| 版本强绑定 | `load_state_dict(strict=True)` + 逐张量 shape 校验 ⇒ **laya 包与权重必须成对**；内网禁止 `pip install -U`。 |
| `head_layers` 不可改 | 改层数会破坏 state_dict 形状 → 加载失败。**不是可用的"裁剪"手段**。 |
| Router `max_loaded` | 默认 1；本部署已置 **2**（双 checkpoint 常驻），否则中英交替会每请求重载。 |
| 选项顺序敏感度 | 0.150（官方基准）→ **固定 `criteria` 书写顺序**，否则结果不可复现。 |
| 内容审核不可用 | 官方 held-out 毒性 0.530 / macro-F1 0.400，自述"仅略高于随机" → 不接该类用途。 |

---

### 6.4 ★★ 路由会看走眼：中文步骤被判成「English Latin text」→ 走 english ckpt（延迟 5–7 倍）

**这是本轮最有价值的实测发现**，且它**推翻了方案 §3.4 的一个隐含假设**（原文假设：`--default multilingual` 即可保证中文走 multilingual）。

**实测（服务端原始响应，非客户端映射后的 `_laya` 字段）**：

| 请求 | `routing.model` | `routing.reason`（服务端原文） | `latency_ms` |
| --- | --- | --- | --- |
| self-judge（纯中文 state） | `multilingual` | `non-Latin script (han, 100% of letters); the English checkpoint cannot read it` | **1073.3** |
| method-judge（中文三字段 + 英文候选名） | **`english`** | `English Latin text` | **10621.9** |
| retrieval-judge（中文三字段 + 中文候选名） | **`english`** | `English Latin text` | **14856.5** |
| method-judge（**同一 payload + `model=multilingual`**） | `multilingual` | `explicit model='multilingual'` | **1960.2** |

结论三条：
1. **Router 是按"字母里 Han 的占比"判语言的**，而 judge 的 payload 里塞了英文标识符（`http_fetch.py` / `gh api` / `Grep` / `web_search` / `pushed_at`）与英文候选名 —— 只要这些把占比压下去，**中文步骤就会被判成英文**，`--default multilingual` **根本兜不住**（default 只在无法判定时生效，而这里是"判定了、判错了"）。
2. **代价可量化：10.6 / 14.9 s vs 1.96 s（同一 payload 显式指定 multilingual）= 5.4× / 7.6×**。这不是"略慢"，是影子期的主要可优化项。
3. **质量风险**：english ckpt 跑中文 ECE **0.376**（见 §6.3 与评估报告）—— 也就是说，**method-judge / retrieval-judge 目前是在用"读中文最差的那个 ckpt"下判定**，而 self-judge 反而走对了。

**处置（用户 2026-09-23 确认，已落地）**：客户端 `scripts/laya_client.py` 新增常量 `PINNED_MODEL_BY_KIND`，对 `method_judge` / `retrieval_judge` **显式传 `model=multilingual`**；`--model` 显式入参**优先**（可覆盖）。`self_judge` 的 state 是纯中文、实测路由正确（1073.3 ms），**暂不钉**，继续观察。

> **v4.7.0 追加（⚠️ 未实测）**：`PINNED_MODEL_BY_KIND` 已增 `"homework_judge": "multilingual"` —— **本项未经真机验证**（本轮服务未运行，仅跑了"不可达 → exit 3 降级"路径）。推定依据：`homework-judge` 的 payload 是**中文题干 + 中文 mode 取值**（`作业题`/`讲解题`/`非作业`），与 `self_judge` 同属"纯中文"形态、**通常**会路由到 multilingual；但 §6.4 已证 Router 会看走眼，故**首次真跑时必须读服务端 `routing.reason` 复核**，不得默认为对。
> ⚠️ **钉死值是硬编码**：换 checkpoint 名**不会自动跟随**（同 §6.4 口径）；`self_judge` 仍不钉。

**落地后复验（同一三用例真机）**：

| judge | 修前 `model_key` / `latency_ms` | 修后 `model_key` / `latency_ms` | 提速 |
| --- | --- | --- | --- |
| method-judge | `english` / **10621.9** | `multilingual` / **2317.1** | **4.6×** |
| retrieval-judge | `english` / **14856.5** | `multilingual` / **4153.6** | **3.6×** |
| self-judge（未改动） | `multilingual` / 1073.3 | `multilingual` / 617.9 | — |

回归已写进离线冒烟第 4 节，并配**阴性对照**（把钉死表清空后该断言必须 FAIL —— 实测两类 `model` 变 `None` → 判据确实在起作用，非空跑）。

**影子期处置**：两个 judge 的 `_laya.model_key` **仍须一并留痕** —— 钉死只解决"已知的两类"，若将来 payload 形态再变，没有 `model_key` 就无法区分"判定差"是模型能力问题还是**路由又走错**了。
> ⚠️ 附带教训：验收脚本的**鉴权负向探针必须走 POST**。服务端 `do_POST` 是"先判路径(404) → 再判鉴权(401)"，而 `do_GET` 对 `/v1/judge` 直接回 404 —— 用 GET 探测只会拿到"方法不匹配"的 404，**既不能证明也不能否证鉴权**。

---

## 7. 排障

| 症状 | 处理 |
| --- | --- |
| `--readyz` 一直 false | 看 `<根>\logs\server.log`；冷加载双 checkpoint 约 1.5–2 分钟属正常 |
| 服务在跑但被判不可用（`HTTPError 502`） | **环境代理劫持回环** —— 见 §4.1；检查 `HTTP_PROXY`/`HTTPS_PROXY` 是否指向本机代理端口 |
| 端口占用 | `.workbuddy/laya/bin/stop_laya.ps1`；再确认 `netstat -ano | findstr :8731` |
| 客户端 exit 3（降级） | 服务未起/未就绪 —— 这是**设计内行为**，流程继续走 A；看 `_laya` 之外是否留痕 `degraded` |
| HTTP 401 | 环境变量 `LAYA_JUDGE_TOKEN` 未生效：`[Environment]::GetEnvironmentVariable('LAYA_JUDGE_TOKEN','User')` 复核（新开的进程才读得到） |
| `FileNotFoundError: rl_agent_config.json` | 权重目录不完整；比对 `models\MANIFEST.json` |
| 推理变慢数倍 | 线程超订：确认 `OMP_NUM_THREADS`/`MKL_NUM_THREADS` 已设（`serve.cmd` 内置 4） |
| 冒烟测试跑不了 `homework-judge` | 见 §8 —— 部署侧 `app/` 下的客户端副本落后于技能侧，缺 `map_homework_judge`；**服务端不受影响**（服务进程不依赖客户端） |

---

## 8. 客户端双拷贝漂移（2026-09-23 实测）

`laya_client.py` 有**两份物理拷贝**：技能侧 `scripts/laya_client.py` 与部署侧 `<根>/app/laya_client.py`，
此前靠**人工双写、无机器判据**。本次实测结论：

| 项 | 实测 |
| --- | --- |
| 行数 | 技能侧 **476** / 部署侧 **385**（差 91 行） |
| 共享口径函数 `_combine` / `_normalise` / `_renorm` | **逐行一致（无漂移）** |
| 部署侧缺失 | `map_homework_judge`、`_opener`（**代理旁路修复未同步**） |
| `app/judges.json` | 只含 `self/method/retrieval` 三份，**无 `homework_judge`** |

**影响边界（如实登记）**：部署侧**只有冒烟测试脚本引用**该副本，**服务进程不依赖它**
⇒ 服务端 `/v1/judge` 仍可受理 homework-judge 的 questions（questions 由调用方构造），
**不阻塞真机采样**。受影响的只是：① 部署侧冒烟测试无法跑 homework-judge；② 部署侧客户端仍会被
本机 `HTTP_PROXY` 劫持回环（§4.1 的修复未同步）。

**为什么不判 FAIL**：`app/` 是**部署物**，可能刻意精简；把"两份必须一致"做成硬判据会永久红，
违反「只把**确定性不一致**判 FAIL」。故做法是**探测器 + 显式登记**：
`homework_model.py selftest` 的第 ⑫ 项会打印两份的行数、共享口径函数漂移与缺失函数（**只报不 FAIL**）
（⚠️ 该探测用**技能根反推**用户目录定位副本 —— 用 `Path.home()` 在沙箱下会指错位置，
导致"什么都没探到"却打印"仅技能内一份"，**把真实漂移盖掉**）。

⚠️ **同步该副本属技能目录外写入，须用户单独授权** —— 本轮未改。

---

## 变更记录

- **2026-09-23（v4.7.0 随附）**：① 接入第四份 judge `homework_judge`（§2 用法与"不注入候选"说明、§3 两处刻意差异、§5 节点、§6.4 钉死表增项并标注**未实测**）；② 新增 **§4.1「环境代理会劫持本地回环」**（真实缺陷：`HTTP_PROXY` 让回环请求拿到 502 → 服务活着却被判不可用 → 静默降级；修法为回环走 `ProxyHandler({})` opener + 连接类异常阴性对照）；③ §7 排障补一行。**未改动任何既有判据、阈值与路由口径。**
- **2026-09-23（新增）**：本文件随"Laya 本地最小部署 + 接入"任务新增。用户决定：接入形态 A（扩写本体）、权重走 hf-mirror、双 checkpoint、装于用户目录、`setx` 持久化 token、注册开机自启；**§7.3 约束保留（C1 影子形态）**。同步新增 `scripts/laya_client.py`、`scripts/judges.json`，并在三份 judge 手册 §7.3 加指向注记。
- **2026-09-23（同日追加实测）**：① 新增 **§6.4「路由会看走眼」**（含服务端 `routing.reason` 原文与延迟对照，推翻"`--default multilingual` 即够"的假设）；② §6.2 加时点注记 —— "`Grep` 被高估"**复测未复现**，改判为"`fit_score` 跨调用不稳定"（两轮共同支持），而 `needs_tool`/`gap_class` 自相矛盾**两轮均复现**；③ §6.3 该行补 §6.4 交叉引用；④ 运维脚本 `.workbuddy/laya/bin/register_autostart.ps1` 补**提权前置门禁**（非提权下 `Register-ScheduledTask` 报「拒绝访问」，原脚本会把该失败掩盖成"无法对 Null 数组进行索引"）。
