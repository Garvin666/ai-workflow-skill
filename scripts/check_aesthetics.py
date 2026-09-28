#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_aesthetics.py — 审美判据校验器

[自研工具] check_aesthetics.py
用途：审美判据校验器 —— 对 CSS / spec / 渲染色产物逐条判定 PASS/FAIL/SKIP，支持判据↔实现审计、产物级覆盖、批量复算
适用场景：任何需要把审美约束落成「可机器校验门禁」的设计类任务；含令牌（token）式 CSS 产物与渲染后几何
链接：待推送（默认 https://github.com/Garvin666/ai-workflow-tools）

把「好看」拆成可枚举、可机器校验的判据，对设计产物（CSS / spec / 渲染色）逐条判定，
输出 PASS / FAIL / SKIP —— 三者严格分开，**SKIP 不等于 PASS**。

零第三方依赖：内置极简 YAML 子集解析器（只支持本判据文件的语法，见 --self-test）。

用法
    python check_aesthetics.py --rubric 审美判据.yaml --css  <file.css>
    python check_aesthetics.py --rubric 审美判据.yaml --spec <file.md>
    python check_aesthetics.py --rubric 审美判据.yaml --css a.css --spec b.md
    python check_aesthetics.py --rubric 审美判据.yaml --css a.css --product ui
    python check_aesthetics.py --rubric 审美判据.yaml --css a.css --geom a.geom.json
    python check_aesthetics.py --rubric 审美判据.yaml --batch <目录或 "dir/*.css"> --product ppt
    python check_aesthetics.py --rubric 审美判据.yaml --css a.css --override '<json 数组>'
    python check_aesthetics.py --rubric 审美判据.yaml --audit      # 判据 ↔ 实现 一致性审计
    python check_aesthetics.py --rubric 审美判据.yaml --self-test  # 解析器 + ΔE00 自检

退出码
    0  无 FAIL（全部 PASS 或 SKIP）且**无覆盖问题**
    1  存在 FAIL，或覆盖条目有问题（缺 reason / 占位 reason / 未知参数键 / 指向不存在判据）
    2  用法 / 依赖 / 输入错误（硬失败，不降级）

设计纪律（对应 SOUL.md「绿有三种」）
    · 「通过 / 未检测 / 无法判定」分开报，绝不把 SKIP 混进 PASS
    · 汇总语由计数器生成，不硬编码项数
    · 缺依赖 / 缺输入一律硬失败，不用 except 降级为跳过
    · 每条判据的阈值来自 rubric 的 source 字段，不在此处凭空设定
    · 单个检查器内部抛异常 ⇒ **降级为 FAIL**，绝不向上抛（否则整进程 rc=1、零 stdout，
      把前面已算出的结果一并吞掉）——「崩栈」比「跳过」更坏

v1.1.0（2026-09-26）—— 只修取数层，判据（rubric）一字未改
    A. 令牌命名取数：v1.0 只认 `font-size: 26px` 与「含 animation/transition 的行」，
       而令牌式产物写作 `--deck-size-body: 26px` / `--deck-motion-enter-duration: 0.5s`
       ⇒ v1.0 在 21/21 套主题上 **字号取到 0 档**（G6 空过）且 **时长一律取空**（M1 误报）。
    B. 修复一处**不可达 fallback**：`_find_var(v,"primary") or _find_var(v,"accent")`
       —— 未命中返回 `(None, None)`，非空元组恒为真 ⇒ `or` 右支永不执行（死代码）。
    C. 消费 `applies_to`：新增 `--product`，不适用的判据判 SKIP（**不是** PASS）。
    D. 新增 `--batch` 与 `--json`。

v1.2.0（2026-09-26）—— 依 GitHub 调研（plumb / projectwallace / APCA）优化
    P0-1 修**真 bug**：`chk_font_scale_ratio_range` 原先把 caption/body/h/display 的
         全部字号混在一个序列里算相邻阶比 ⇒ 21/21 套 FAIL，其中 **15 套是跨体系假阳性**。
         本版新增 `group_by: role-prefix`，按令牌角色词根分组后**只在组内**算阶比；
         无法分组时降级为整体序列并在 detail 显式标注「未分组」（不假装分过组）。
    P0-2 `contrast_min` 支持 `role: muted`（补契约里 fg-muted=4.5 这一档的覆盖缺口）。
    P1-1 新增 `palette_separation`：CIEDE2000 ΔE00 —— 两色距离 < 容差即「人眼不可辨、应合并」。
         常数 2.0 取自 plumb `color.delta_e_tolerance`（同值反向使用）。
    P1-2 新增 `scale_conformance` / `duration_scale_conformance`：取值必须落在**声明的刻度集**内。
         刻度集为空 ⇒ **no-op（SKIP）**，不是判全部违规（plumb 的原话语义）。
    P1-3 新增 `accent_availability`：契约 accentPolicy 规定 accent 低于 3:1 记 **NOTE 而非 FAIL**。
         本实现保留三态 —— 该情形记 PASS 并在 detail 前置 `NOTE:`（不新增第四态）。
    P1-4 取数层新增**跳过登记**：不可解析的色值不再静默丢弃，输出里显式报「跳过 N 项」。
    P2-1 落地 **override**：判据集表头v1.0承诺但无实现（悬空承诺）。支持逐条浅合并 params、
         整键替换 applies_to；reason 必填且拒绝占位文本。
    P2-2 `audit_rubric` 新增 **params 合法性校验**（未知键 / 类型错 / 枚举越界 ⇒ FAIL），
         对应 plumb 的 "rejects unknown configuration fields"。
    P3   新增渲染色消费（`--geom`）与 `near_alignment` / `sibling_consistency` /
         `baseline_rhythm` 三条几何判据 —— 依据 plumb 的核心判断
         "for rendered websites, **not the code behind it**"。缺渲染色时判 SKIP（未检测）。

v1.2.1（2026-09-26）—— 修 v1.2.0 的三处真缺陷 + 补自检覆盖
    ① `chk_sibling_consistency` 取高度写成 `x[3]`（x 是 `(i, rect)` 二元组）⇒ IndexError。
    ② `chk_near_alignment` append 元组时少写外层括号 ⇒ TypeError。
       ①②使整条 `--geom` 路径**必然崩栈**，且把前面已算出的结果一并吞掉。
    ③ **fail-open**：`run()` / `batch()` 只按 `c["fail"]` 定退出码，**忽略覆盖问题**
       ⇒ 覆盖写了错东西时只打印 `[FAIL] 覆盖 —…`、rc 仍为 0（调用方按 rc 判 = 当通过）。
       现改为 rc = fail 或 probs。同时覆盖参数**开始做规格校验**（未知键 / 类型 / 枚举），
       此前覆盖里写错参数键会被静默忽略 —— 用户以为放宽了阈值，其实没有。
    ④ 新增 **fail-closed 护栏**：单个检查器抛异常降级为 FAIL 并继续跑完其余判据。
    ⑤ `self_test` 补上 **R 组实跑** 与 **护栏自检** —— v1.2.0 的自检完全没覆盖 `--geom` 路径，
       这正是 ①② 能漏到外部的直接原因（「自检全绿」只证被覆盖的那部分自洽）。
    ⚠️ v1.2.1 只修**校验器行为**，`references/aesthetic-rubric.yaml` 当时一字未改。

v1.2.2（2026-09-26）—— 在**真实 deck 页**上首次端到端实测后修「判据造信号」
    背景：v1.2.1 的 R 组只在自造夹具页上跑过。本轮把 ui库 真实 deck 渲染页
    （dist-demo，真 Chrome + CDP）的几何喂进来，R1/R2/R3 **全 FAIL**；逐条取证后发现
    **三条都不是产物的毛病，而是判据在真实数据上的三处口径/实现错误**：

    ① **G1 / G6 口径错位**（21/21 假 FAIL 的真因）。
       判据集 note 早已写明「token 表的调色板规模**不适用**本判据」，
       实现却拿 CSS **令牌清单**去顶「**画面内**」口径 ⇒ 把「设计系统声明了几个令牌色」
       当成「一页画面里出现了几种颜色」。改为：有 `--geom` 就数**真实渲染**出现的
       颜色 / 字号档数；无渲染色判 **SKIP**。**这不是放宽** —— 拿真实渲染帧比 6 色上限照样会 FAIL。
    ② **R1 在造信号**：`_flush_miss` 写 `centroid = int(sum/len)`，把簇心**截断成整数**，
       每个成员被凭空算出差 ≤1px（实测：4 条本该完全重合的右边报成「差 0.39px」×10 处）。
       改浮点均值；并加**噪声地板** `noise_px`（默认 0.5）—— 亚像素差眼睛看不出来，
       而规则原意是「眼看要对齐却没对齐，**眼睛看得出来**」。地板 ≥ 容差 ⇒ SKIP（配置自相矛盾）。
    ③ **R2 分组错**：只按 `parent` 分组 ⇒ 真实封面里**竖排**的 eyebrow/title/subtitle
       被当成一行互比高度（报出「高 528%」）。改为先分「**并排行**」再比：
       水平区间不相交 ∧ 垂直重叠 ≥ `row_overlap`×min(h)。无可比并排行 ⇒ SKIP（不是 PASS）。
    ④ **R3 凭空发明契约**：原默认 `baseline_px=8`，而 ui库 `schema.json#spacing` 明确
       「34 套子键自由命名……不强行归并」—— **该设计系统根本没声明韵律网格**。
       硬套 8px 会把整页判成「7/7 文本全部离格」。改为**必须声明**，未声明 ⇒ SKIP。
    ⑤ 「空节点集」不再判 PASS（R1/R2）：那是「没数据」冒充「没问题」。
    ⑥ `self_test` 的 R 组夹具改为**真实的并排几何**（旧的三个矩形完全重叠，
       在「并排行」语义下本就不构成可比值 —— 夹具自己也得站得住）。
    ⚠️ 本版**同时改判据集**（R1 加 `noise_px`、R2 加 `row_overlap`、R3 去掉默认 8px、
    G1/G6 的 note 与 `applies_to` 说明）—— 因为 ①②③④ 里有三条是判据文本与实现不一致，
    只改代码会让两者继续对不上。改动逐条有实测取证，且都配了阴性/阳性对照。

v1.2.3（2026-09-27）—— 「请闭环」四项待拍板：**三条是判据又数错了，一条决定不动**
    背景：v1.2.2 跑完 21 套真实 deck 页后仍留 49 处 FAIL（G6 21 + G7 21 + G11 7）。
    逐条追到证据之后，**49 处里 49 处都是判据自己的问题**，产物的排版是对的：

    ① **G6 把「容器继承的字号」当成了「层级」**（21/21 假 FAIL 的第二个真因）。
       真实封面上 `.ui-deck__slide` 根容器继承 14px、装饰 span 继承 26px，二者都**没有一个字**，
       却把「4 档」抬成「6 档」。改为**只统计承载文字的节点**（`_text_bearing`）；
       21 套主题无例外地回到 4 档。max 仍为 4 —— 真用 5 档**文字**字号照样 FAIL（有阴性对照）。
    ② **G7 把「引号字形」并进了「引文」的刻度**（21/21 假 FAIL 的第二个真因）。
       `_role_stem` 原取 `parts[0]` ⇒ `--deck-size-quote`(42px) 与 `--deck-size-quote-mark`
       (150px，自带 font/weight/leading/tracking/color 五个独立令牌) 并成一组，阶比 150/42=3.571。
       改为取**完整角色段**（`quote` / `quote-mark` 分家；`body`+`body-sm` 仍同组）。
    ③ **G11 把「层级底色」当成了「该合并的重复色」**（7/21 假 FAIL 的真因）。
       7 套 FAIL **全部**是 `bg ↔ bg-alt ↔ card-bg`（ΔE00 0.61–1.96），**无一涉及 accent/fg**。
       层级底色的微差就是「分层」这一设计意图本身。改为**作用域收窄到语义色**，
       被排除的令牌**逐条打印**（可审计、不静默）。
    ④ **G4/G5 决定不动**：保持 3.0（WCAG 2.1 AA 现行有效；WCAG 3 未定稿、APCA 未成标准）。
       理由写进判据集，避免下次又被当成"待办"。

    ⚠️ 本版**一处阈值都没动**（max:4 / [1.2,1.8] / ΔE00 2.0 / 3.0 全部原样），
    只改「这条判据该吃哪个输入」。三条都配了**阴性对照**证明判据仍有牙齿。

v1.3.0（2026-09-27）—— G12/G13/R3 的**可达性审计**：no-op 与**假绿**是两件事
    起因：v1.2.3 收尾时留下「G12/G13/R3 在真实产物上仍是 no-op」。本轮做的是
    **可达性判定**，而不是「想办法让它们跑起来」—— 因为「让它跑起来」有两条路，
    其中一条会**制造绿灯**。

    ① **`em` 取数错误（真缺陷 #5）**。`_to_px` 把 `em` 与 `rem` 一并 ×16
       ⇒ `font-size: 1em` 被算成 **16px**、`0.94em` → **15.04px**。
       实测取证：ui库 `src/deck/layouts/layouts.css` 的 5 处 `em` 被凭空折成
       12.8 / 14.72 / 15.04 / 16 / 17.6，其中 **4 个**随后被 G12 当成「不在刻度内的字号」
       报出 —— **判据在造信号**（与 v1.2.2 的 R1 `int()` 截断同族）。
       `em` 的基准是父元素计算字号，**脱离渲染树就没有值** ⇒ 改为返回 None，
       并由 `extract_css` 记入 `unresolved_sizes`（**登记、不静默丢弃**，
       与 P1-4 的 `skipped_values` 同构）。`rem`/`pt`/`px` 仍可折（基准已声明）。

    ② **G12/G13 自证式刻度护栏（防假绿）**。实测取证：21 套主题的生成 CSS 里
       raw `font-size:` 数 = **0**，`sizes` 与 `--deck-size-*` 令牌集**逐值相同**；
       时长同理（durations ≡ `--deck-motion-*` 令牌值）。
       ⇒ 若把「产物自己的令牌集」填进 `params.scale`，则 `被检值 ⊆ 刻度` **恒成立**，
       G12/G13 退化为**恒 PASS**。**那不是「启用」，是制造绿灯** —— 比 no-op 更坏，
       因为 no-op 至少诚实地报「未检测」。改为：检出「刻度集 ≡ 被检 CSS 自身导出的
       刻度集」即判 **SKIP** 并说明；正确用法是**声明侧（规范/令牌文件）与被检侧
       （使用侧 CSS）分离**。

    ③ **G13 的 0ms 不参与判定**。实测 `animation-delay: 0s` 被 DUR_RE 收进 durations，
       随后被当成「不在刻度内」。0 是「无延迟」，**不是刻度上的一档**；
       被排除的 0 值数量在 detail 里显式报出（不静默）。非 0 的离格值照样 FAIL。

    ④ **R3 的三态澄清**：ui库 `schema.json#spacing` 明确「不强行归并」⇒ 该产物
       **没有 baseline 网格**。此时 SKIP 是**正确终态（结构性不适用）**，不是待办。
       与本条并存的另两种 SKIP 分开措辞：缺渲染色（未检测）/ 未声明网格（结构性 no-op）。

    ⑤ **取数层 —— 末条声明省略分号时的静默丢项**（同 P1-4 一族）。
       `VAR_RE` 与 `TOK_DUR_RE` 原以 `;` 强制收尾，而 CSS **允许块内最后一条声明省略分号**
       ——实测 `:root{--deck-motion-b-duration:0.8s}`（合法 CSS）**静默丢掉**该令牌，
       于是 G13 的刻度集少一档而不报任何异常。改为以「`;` / `}` / 串尾」收尾。
       ⚠️ **真实语料零变化**（21 套主题：令牌声明数 113 → 113；`TOK_SIZE_RE` 本就不依赖
       分号，本就无漏）—— 这一条是**潜在**缺陷，按「只为实证过的缺陷改代码」的纪律，
       先举证再改，改后证明本体一字未动。

    ⑥ **首次真实读数 + 一条新纪律：声明侧还必须是「同一体系」**。
       把 v1.4 写明的正确形态跑起来（21 主题 × `Deck.css` / `layouts.css`）后：
       第一版实验只取 **deck 主题的排版刻度** 去量 `Deck.css`（组件壳）⇒ 13/14px 与
       140/220ms 全判离格，**37/42 假 FAIL**。追下去发现它们**在 ui kit 自己的刻度上**
       （`src/styles/tokens.css`：`--ui-font-size-sm/md`=13/14px、`--ui-duration-fast/normal`
       =140/220ms）。⇒ 「两侧**不同文件**」还不够，**必须同属一个体系**；一个文件混用多套
       体系时，刻度集应取**该产物已声明刻度的并集**。
       改用并集后的真实读数：**G12 42/42 PASS**；G13 `Deck.css` 判 FAIL，
       `layouts.css` 无时长 ⇒ SKIP 21/21。
       ⚠️ 这次**错的是实验，不是产物** —— 按纪律改实验、**不改期望值迁就**，与 v1.2/v1.3
       两次「错的是判据，不是产物」是同一族错误的两个方向。

    ⚠️ **v1.5.0 复测推翻了 ⑥ 里的两句读数**（原文：「G13 `Deck.css` FAIL 21/21 且离格值
       集合恰好 `[200.0]`」）。成因：那句是从 detail **字符串反解**的
       （`split("：")[1].split("（")[0]`），而 detail 只打印 `off[:6]` —— 于是把
       「前 6 个」读成了「全部」、把「含 delay 阶梯的 6 个」读成了「一处硬编码」。
       按「**上一轮的结论 = 待复测假设**」重测：真实离格值 **6 个**
       （`180 / 200 / 300 / 440 / 600 / 780` ms）。
       ⇒ **读数必须由原始数据统计，不得从被截断的展示字符串反解。**

    ⭐ v1.5.0（2026-09-27）变更摘要 —— **delay/stagger 与 duration 分家 + `--scale-from`**
    （仍**一条阈值都没动**：`tolerance_px 0.5` / `tolerance_ms 1.0` 原样）

    ⑦ **取数层：`delay` 不是 `duration`**。原实现按**行**扫 `(animation|transition)`，
       于是 `animation-delay: 0.08s` 这类**错峰阶梯**也被当成「时长」：实测 ui库
       `Deck.css` 的 `0 / 0.08s / 0.18s / 0.3s / 0.44s / 0.6s / 0.78s`（L386-393）
       因此被判 6 档离格。而 G13 的契约是「**时长**是否来自同一刻度」（source 引
       Tailwind `--default-transition-duration`）—— delay 是「推迟多久开始」，
       与「持续多久」量纲不同。
       改为**按声明级**解析：`*-delay` 归 delay 门；简写 `transition` / `animation`
       取**首个**时间值为 duration、第二个为 delay（CSS 简写规则）。被排除值登记进
       `delay_excluded` 并在 detail 报出（**不静默**）。

    ⑧ **令牌层同病**：`TOK_DUR_RE` 原把 `duration|delay|stagger` 一锅端。实测 21 套主题
       **各有一条** `--deck-motion-stagger = 0 / 0.08s / … / 0.78s`，与 `Deck.css` 的
       delay 阶梯**同值同源** ⇒ 声明侧与被检侧同源，该维度上 `被检值 ⊆ 刻度` **恒真**。
       这是**「假绿」的第二形态**（第一形态见 ②：用产物自身的令牌集当刻度）。
       ⇒ 刻度集只吃 `--*duration*`；`--*delay*` / `--*stagger*` 另立 `delay_tokens` 门。
       **韵律层当前判据集未覆盖** —— 如实记为未覆盖，不假装覆盖。

    ⑨ **`--scale-from`：让 G12/G13 可被常规跑批启用**（此前门禁调用不带 scale ⇒ 永远 SKIP）。
       从**声明源** CSS 的**令牌声明**取刻度并集（`--*-size-*` / `--*-duration*`），
       作为 G12/G13 的 `params.scale` 默认值；**显式 `--override` 优先**。
       **同源护栏**（判据内那道护栏的**输入端**版本）：声明源若与被检文件同一文件 ⇒
       剔除并记 problem；剔除后为空 ⇒ **不合成** override（保持 SKIP），
       绝不因启用开关而变成恒真 PASS。缺失的声明源 ⇒ problem（fail-closed，不静默忽略）。

    ⑩ 修产物后真实读数（21 主题 × `Deck.css` / `layouts.css`，声明源 = ui kit ∪ deck 主题）：
       G12 **PASS**；G13 `Deck.css` 的离格值收敛到**可指认的两行**（`180ms` L124 / `200ms` L105），
       `layouts.css` 仍 SKIP。判据给出的是**两行代码**，不是 58 处泛化告警。

    ⚠️ 本版**没有为了让 FAIL 消失而动阈值**：G12/G13 的判定阈值
    （`tolerance_px 0.5` / `tolerance_ms 1.0`）原样。① 只是**不再把相对单位折成假数值**，
    真实离格值（如 `34px`）照样 FAIL；⑤⑨ 是取数／启用通道；⑦⑧ 是**输入按语义分家**
    —— 分家后照旧精确指认 `Deck.css` 的两处硬编码 duration（有阴性对照）。

  ⭐ v1.6.0（2026-09-27）变更摘要 —— 用户指令「1234 按你的建议走」：
    ① 版本粒度提交；② 产物剩余硬编码时长统一走令牌；③ 补韵律层判据；④ 两处既存 FAIL 定性。
    A. 新增 **G16 错峰阶梯非递减**（**结构性不变量，无阈值**）：判据集 v1.5 的 G13 note 自己
       写着「韵律层未覆盖」，本条补上。两侧输入 = 声明侧 `--*stagger*`/`--*delay*` 令牌序列
       ＋ 应用侧 `nth-child` 序列（**带索引取** —— 取成集合就丢了顺序，而顺序才是其语义）。
       ⚠️ **刻意不要求步长均匀**：真实语料是**加速步长** 80/100/120/140/160/180ms，
       要求等步长会把它判成缺陷 —— 那才是「凭空发明契约」（同 R3 默认 8px 的教训）。
    B. 修 **M1 空集语义**（真缺陷，与 v1.2.2「空集判 PASS→SKIP」同族）：原实现下「该文件
       根本没有动效」与「有动效但没写秒数」**输出完全相同**（都 FAIL）—— 实测
       `ui库/src/deck/layouts/layouts.css` 零动效声明却被判 FAIL，即判据在**造信号**。
       现在：无动效声明 ⇒ **SKIP（无对象）**；有声明却无时长 ⇒ **FAIL**。
       `transition: none` 属显式无动效，不计入（该文件有 4 处）。
    C. 修 **W2 悬空参数**（真缺陷）：`allowed_in_layers` 自 v1.0 起就写在判据集里，而实现
       **一个字符都没被读** ⇒ 判据比文档更严（文档说氛围层可用，实现是「任何 radial 即 FAIL」）。
       现按块内**显式声明** `--ui-layer: <层名>` 放行，**缺声明一律 FAIL（fail-closed）** ——
       同 R3 的 `baseline_px` 处置：**要声明，不猜**。
    D. 取数层新增**块级**解析（`_BLOCK_RE` / `_NTH_RE` / `_LAYER_DECL_RE`）与四项登记
       （`motion_decls` / `motion_without_time` / `rhythm_ladders` / `radial_blocks`）。
    ⚠️ 本版**一条阈值都没动**（`tolerance_px 0.5` / `tolerance_ms 1.0` / `ΔE00 2.0` / `3.0` 全部原样）。

v1.7.0（2026-09-27）——「已声明未消费的参数」由一次性探针升级为**常驻审计** + V1 契约归位
    A. `--audit` 新增**悬空参数**常驻检查（`_dangling_params`）：AST 解析本模块，报出
       「`PARAM_SPEC` 声明了、检查器**从未读取**」的键。v1.6.0 时这是一次性脚本
       （`tmp/v160/audit_params.py`），**发现即会过期**；现在每次 audit 都跑。
       实测基线：**7 个检查器 / 9 个键** —— G2 `expected`、G8 `expected`·`field`、
       G9 `expected`、M3 `elements`、W1 `coverage`、V1 `elements`、C1 `max`。
       ⚠️ 这些**不是「通过」**：它们只是「算不出来」，故**单列一类、不并入「一致」计数**，
       措辞为 WARN。为什么不当场判 FAIL：它们**全部是 `judgeability: spec` 判据**，
       而 `extract_spec()` 只产出**存在性布尔**（`has_accent` / `has_cta` / `has_series` …），
       **没有计数字段** ⇒ 「期望值/期望数量」类参数在 spec 层**没有判定依据**。
       要真落地须先扩展取数层（外加判据名与实现口径的对齐），方向待拍板。
    B. `chk_shot_spec_present`（V1）改**走 `params.elements`**：原先「构图 ∧ 光比/色温」被硬编码
       在 `extract_spec()` 里，判据集却声明了 `elements: [构图, 光比或色温]` —— 参数形同虚设。
       现由 `_ELEMENT_KEYWORDS` 做「契约项 → 关键词」适配：**契约可配，实现只做翻译**。
       行为分界未变（PASS 仍要求两项同时出现），仅 detail 措辞更明确；`extract_spec` 的
       死字段 `has_shot` 一并移除。
    C. `PARAM_SPEC` 清掉 `memory_point_count.field` —— 该键**无判据集声明、无实现读取、
       note 未提及**，属纯冗余白名单（留着会让人以为「配了就能用」）。
    ⚠️ 本版**未改判据集**：`aesthetic-rubric.yaml` 条文与阈值一字未动（判据仍 30 条）。
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

try:  # Windows 控制台中文输出
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

VERSION = "1.7.0"
PRODUCTS = ("ui", "ppt", "chart", "image")
# 覆盖 reason 的占位文本（写了等于没写）
PLACEHOLDER_REASONS = {
    "待定", "无", "暂无", "tbd", "n/a", "na", "-", "—", "？", "?", "todo", "xxx", "...",
}


# --------------------------------------------------------------------------
# 一、极简 YAML 子集解析器
#     只支持本判据文件用到的语法：缩进映射 / "- " 列表 / 内联 {} [] / 标量
#     不支持：锚点、多行标量、行内注释（本判据文件只用整行注释）
# --------------------------------------------------------------------------
def _scalar(v: str):
    v = v.strip()
    if v == "":
        return None
    if v.startswith("{") and v.endswith("}"):
        return _inline_map(v)
    if v.startswith("[") and v.endswith("]"):
        return _inline_list(v)
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v in ("null", "~", "None"):
        return None
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _split_top(s: str, sep: str = ","):
    """按顶层分隔符切分，忽略 {} [] 内部与引号内部的分隔符。"""
    out, buf, depth, in_s, in_d = [], [], 0, False, False
    for ch in s:
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif not in_s and not in_d:
            if ch in "{[":
                depth += 1
            elif ch in "}]":
                depth -= 1
            elif ch == sep and depth == 0:
                out.append("".join(buf))
                buf = []
                continue
        buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


def _inline_map(s: str) -> dict:
    inner = s.strip()[1:-1].strip()
    out: dict = {}
    if not inner:
        return out
    for part in _split_top(inner):
        k, sep, v = part.partition(":")
        if not sep:
            continue
        out[k.strip()] = _scalar(v)
    return out


def _inline_list(s: str) -> list:
    inner = s.strip()[1:-1].strip()
    return [_scalar(p) for p in _split_top(inner)] if inner else []


def mini_yaml_load(text: str):
    rows = []
    for raw in text.splitlines():
        if raw.strip().startswith("#"):
            continue
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        rows.append((indent, raw.strip()))

    pos = [0]

    def parse(indent: int):
        if pos[0] >= len(rows) or rows[pos[0]][0] < indent:
            return None
        if rows[pos[0]][1].startswith("- "):
            return parse_seq(indent)
        return parse_map(indent)

    def parse_seq(indent: int):
        out = []
        while pos[0] < len(rows):
            ind, s = rows[pos[0]]
            if ind != indent or not s.startswith("- "):
                break
            pos[0] += 1
            rest = s[2:].strip()
            if rest == "":
                out.append(parse(rows[pos[0]][0]) if pos[0] < len(rows) else None)
            elif ":" in rest and not rest.startswith(("{", "[")):
                item: dict = {}
                k, _, v = rest.partition(":")
                v = v.strip()
                if v == "":
                    item[k.strip()] = (
                        parse(rows[pos[0]][0])
                        if pos[0] < len(rows) and rows[pos[0]][0] > indent
                        else None
                    )
                else:
                    item[k.strip()] = _scalar(v)
                while pos[0] < len(rows):
                    i2, s2 = rows[pos[0]]
                    if i2 <= indent or s2.startswith("- "):
                        break
                    k2, sep2, v2 = s2.partition(":")
                    if not sep2:
                        break
                    pos[0] += 1
                    v2 = v2.strip()
                    if v2 == "":
                        item[k2.strip()] = (
                            parse(rows[pos[0]][0])
                            if pos[0] < len(rows) and rows[pos[0]][0] > i2
                            else None
                        )
                    else:
                        item[k2.strip()] = _scalar(v2)
                out.append(item)
            else:
                out.append(_scalar(rest))
        return out

    def parse_map(indent: int):
        out: dict = {}
        while pos[0] < len(rows):
            ind, s = rows[pos[0]]
            if ind != indent or s.startswith("- "):
                break
            k, sep, v = s.partition(":")
            if not sep:
                break
            pos[0] += 1
            v = v.strip()
            if v == "":
                out[k.strip()] = (
                    parse(rows[pos[0]][0])
                    if pos[0] < len(rows) and rows[pos[0]][0] > indent
                    else None
                )
            else:
                out[k.strip()] = _scalar(v)
        return out

    return parse(0)


# --------------------------------------------------------------------------
# 二、产物解析（CSS / spec / 渲染色）
# --------------------------------------------------------------------------
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})(?![0-9a-fA-F])")
RGB_RE = re.compile(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)")
FONT_RE = re.compile(r"font-size\s*:\s*([\d.]+)\s*(px|rem|pt|em)")
VAR_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]+?)\s*(?=;|\}|$)")
RADIAL_RE = re.compile(r"radial-gradient\s*\(")
DUR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(ms|s)\b")
ANIM_LINE_RE = re.compile(r"(animation|transition)", re.I)
# v1.5.0：**按声明级**取时长 —— 一条声明 = `property: value`（值内不含 `;{}`）。
#   原实现按行扫 `(animation|transition)`，于是 `animation-delay: 0.08s` 这类
#   **错峰阶梯**也被当成「时长」：实测 ui库 Deck.css 的 `0 / 0.08s / 0.18s / 0.3s /
#   0.44s / 0.6s / 0.78s` 因此被判「6 档离格」。而 G13 的契约是「**时长**是否来自
#   同一刻度」（source 引 Tailwind `--default-transition-duration`）—— delay 是
#   「推迟多久开始」，与「持续多久」量纲不同，混算是又一次作用域错配（同 G1/G6/G7/G11）。
_DECL_RE = re.compile(r"([-\w]+)\s*:\s*([^;{}]+)")
# 简写（`transition` / `animation`）取**首个**时间值为 duration、第二个为 delay；
# 长写只认 `*-duration`；`*-delay` 一律归 delay 侧（**登记**，见 extract_css）。
_SHORTHAND_PROPS = frozenset(("transition", "animation"))
_DUR_PROPS = frozenset(("transition-duration", "animation-duration")) | _SHORTHAND_PROPS
_DELAY_PROPS = frozenset(("transition-delay", "animation-delay"))
# v1.1.0 取数补丁 A：令牌命名（`--deck-size-body: 26px` / `--deck-motion-*-duration: 0.5s`）
TOK_SIZE_RE = re.compile(r"(--[\w-]*?size-[\w-]+)\s*:\s*([\d.]+)\s*(px|rem|pt|em)\b")
# v1.5.0：令牌层同样**按语义分家**。G13 的刻度集只吃 duration 语义的令牌；
#   `--*delay*` / `--*stagger*` 描述的是**错峰序列**（实测 21 套主题各有一条
#   `--deck-motion-stagger = 0 / 0.08s / …`，与 Deck.css 的 delay 阶梯**同源**）
#   ⇒ 若混入刻度集，`被检值 ⊆ 刻度` 在 delay 维度上**恒真**：这是「假绿」的第二形态
#   （第一形态见 chk_scale_conformance 的「用产物自身令牌集当刻度」）。
TOK_DUR_RE = re.compile(r"(--[\w-]*duration[\w-]*)\s*:\s*([^;{}]+?)\s*(?=;|\}|$)")
TOK_DELAY_RE = re.compile(r"(--[\w-]*(?:delay|stagger)[\w-]*)\s*:\s*([^;{}]+?)\s*(?=;|\}|$)")

# v1.6.0：**块级**取数 —— 有两类判据的对象在「块」这一层，不在「声明」层：
#   ① 韵律阶梯（`nth-child` 序列）必须**带索引**取，取成集合就丢了顺序（顺序才是它的语义）；
#   ② radial-gradient 的**所在层**（W2 的 `allowed_in_layers` 此前**一个字符都没被读**，
#      是悬空参数：判据比文档更严，见 chk_skeleton_no_radial）。
_BLOCK_RE = re.compile(r"([^{}]*)\{([^{}]*)\}", re.S)
_NTH_RE = re.compile(r":nth-child\(\s*(?:(\d+)|n\s*\+\s*(\d+))\s*\)", re.I)
# 层标注锚点：块内**显式声明** `--ui-layer: 氛围层;`。缺声明即按「骨架层」处理（fail-closed）。
#   为什么必须显式声明：CSS 里没有任何可机器识别的「层」概念，`氛围层` 无从从选择器/注释推断；
#   默认放行会让 W2 退化成 no-op，默认拒绝才是安全侧。同 R3 的 `baseline_px` 处置：**要声明，不猜**。
_LAYER_DECL_RE = re.compile(r"--[\w-]*(?:layer|层级)[\w-]*\s*:\s*([^;{}]+)")
# 显式「无动效」的关键字：`transition: none` 是「没有动效」，**不是**「有动效但没写时长」。
_NO_MOTION_KEYWORDS = frozenset(("none", "initial", "inherit", "unset", "revert", "revert-layer"))

# v1.2.0 P1-4：跳过登记 —— 名字像颜色槽位、值也长得像颜色、但解析不出来的变量
_COLORISH_NAME_RE = re.compile(r"(?:^|-)(?:bg|fg|accent|border|line|ink|surface|shadow|fill|stroke)(?:-|$)", re.I)
_COLORISH_VAL_RE = re.compile(r"#|rgb|hsl|color|var\(|oklch|lab\(", re.I)

# v1.2.0 P0-1：角色词根提取用的修饰词表
_SIZE_MODS = ("2xs", "3xl", "4xl", "2xl", "xs", "sm", "md", "lg", "xl")

# v1.2.3：**层级/表面色**令牌名模式 —— 这些是「同一语义下的明度阶梯」，不参与 G11。
# 实测取证：21 套主题里 G11 的 7 处 FAIL **全部**是 bg ↔ bg-alt ↔ card-bg 之间的对
# （ΔE00 0.61–1.96），无一涉及 accent / fg。层级底色本就该是微差，用「不可辨即合并」
# 去判它属**作用域错配**（同 G1/G6 一族）。
_LAYER_COLOR_RE = re.compile(
    r"(^|[-_])(bg|background|surface|paper|canvas|card|overlay|scrim|veil|shadow)([-_]|$)",
    re.I,
)


def norm_hex(h: str):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    elif len(h) == 4:
        h = "".join(c * 2 for c in h[:3])
    elif len(h) == 8:
        h = h[:6]
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def parse_color_value(v: str):
    v = v.strip()
    m = HEX_RE.fullmatch(v)
    if m:
        return norm_hex(m.group(0))
    m = RGB_RE.search(v)
    if m:
        return (int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3))))
    return None


def _to_px(val: float, unit: str):
    """把带单位的字号折成设计像素。**折不出来就返回 None**，由调用侧登记（不静默丢弃）。

    ⚠️ v1.3.0 修一处**取数错误**：原先 `unit in ("rem","em")` 一并 ×16 ——
    把 `font-size: 1em` 算成 **16px**、`0.94em` 算成 **15.04px**。`pt` 与 `px` 是绝对单位
    （1pt = 96/72 px，精确）；`rem` 的基准是根字号，本产物固定 16px，可折（视为已声明假设）；
    但 **`em` 的基准是父元素的计算字号 —— 脱离渲染树就没有值**。
    实测取证（ui库 `src/deck/layouts/layouts.css`）：5 处 `em` 被凭空折成
    12.8 / 14.72 / 15.04 / 16 / 17.6 px，其中 4 个随后被 G12 当成「不在刻度内的字号」报出 ——
    **判据在造信号**（与 v1.2.2 的 R1 `int()` 截断同族）。相对单位**没有绝对值，不得参与
    刻度落格判定**，更不能冒充 16px。
    """
    if unit == "em":
        return None
    if unit == "rem":
        val *= 16.0
    elif unit == "pt":
        val *= 96.0 / 72.0
    return round(val, 2)


def _role_stem(name: str) -> str:
    """从令牌名提取「体系词根」（v1.2.0 P0-1；v1.2.3 修一处**误并**）。

    `--deck-size-h2` → `h`；`--deck-size-display-lg` → `display`；
    `--deck-size-body-sm` → `body`。
    返回 "" 表示提取不出词根（调用侧据此降级为「未分组」）。

    ⚠️ v1.2.3：原实现取 `parts[0]`（**只取第一段**）⇒ 凡「同词根 + 不同角色后缀」的
    令牌都被并进同一个体系。实测取证：`--deck-size-quote`（42px，引文正文）与
    `--deck-size-quote-mark`（150px，**引号字形** —— 它自带 font / weight / leading /
    tracking / color 五个独立令牌，在 `ui库/deck/layouts/layouts.css` 里是独立角色）
    被并成 `quote` 一组，于是组内阶比 = 150/42 = 3.571 ⇒ **21 套主题 21/21** 报
    「阶比越界」。二者不是同一刻度的相邻档，是**两个角色**。
    现取完整角色段（`quote` / `quote-mark` 分家）；尺寸修饰词（sm/lg/2xl…）与数字
    仍被剥离（`body` + `body-sm` 仍同组），单成员体系按 `min_group_size` 自动 no-op。
    """
    m = re.search(r"size-([\w-]+)$", name)
    if not m:
        return ""
    parts = [p for p in m.group(1).split("-") if p and p not in _SIZE_MODS and not p.isdigit()]
    if not parts:
        return ""
    return re.sub(r"\d+$", "", "-".join(parts))


def _clean_sel(sel: str) -> str:
    """选择器规范化：**去掉注释**、折叠空白。

    ⚠️ `_BLOCK_RE` 的「选择器」是从上一个 `}` 到本块 `{` 的全部文本，**包含块前的注释**
    （实测 `layouts.css` 的装饰块每个都带 2-3 行设计说明）⇒ 不洗掉的话，W2 的 FAIL
    会打印一大段注释，把「可指认到哪一行」这个价值冲掉（实测踩中）。
    """
    return re.sub(r"\s+", " ", re.sub(r"/\*.*?\*/", " ", sel, flags=re.S)).strip()


def extract_css(css: str) -> dict:
    colors = set()
    for m in HEX_RE.finditer(css):
        colors.add(norm_hex(m.group(0)))
    for m in RGB_RE.finditer(css):
        colors.add((int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3)))))

    sizes = []
    # v1.3.0：折不出绝对值的字号（`em` 等上下文相关单位）—— 登记，不静默丢弃、不冒充数值
    unresolved_sizes = []
    for m in FONT_RE.finditer(css):
        px = _to_px(float(m.group(1)), m.group(2))
        if px is None:
            unresolved_sizes.append({"raw": m.group(0).strip(), "unit": m.group(2)})
        else:
            sizes.append(px)

    # v1.1.0：令牌命名的字号（名 → px），一并计入 sizes（下游 set() 去重）
    size_roles: dict = {}
    for m in TOK_SIZE_RE.finditer(css):
        px = _to_px(float(m.group(2)), m.group(3))
        if px is None:
            unresolved_sizes.append({"raw": m.group(0).strip(), "unit": m.group(3)})
            continue
        sizes.append(px)
        size_roles[m.group(1)] = px

    # v1.5.0：**按声明级**取时长，并按语义分成 duration / delay 两门。
    #   被排除的 delay 值**不静默丢弃**：登记进 `delay_excluded`，判定 detail 如实报出。
    durations = []
    delay_excluded: list = []
    for m in _DECL_RE.finditer(css):
        prop = m.group(1).lower()
        if prop in _DELAY_PROPS:
            delay_excluded.extend(d.group(0) for d in DUR_RE.finditer(m.group(2)))
            continue
        if prop not in _DUR_PROPS:
            continue
        times = [d.group(0) for d in DUR_RE.finditer(m.group(2))]
        if not times:
            continue
        if prop in _SHORTHAND_PROPS:
            durations.append(times[0])            # 简写：首个时间值 = duration
            delay_excluded.extend(times[1:])      # 第二个 = delay，归 delay 侧
        else:
            durations.extend(times)
    # v1.1.0：令牌命名的时长（duration 语义；v1.5.0 起 delay/stagger 令牌另立一门）
    duration_tokens: dict = {}
    for m in TOK_DUR_RE.finditer(css):
        found = [d.group(0) for d in DUR_RE.finditer(m.group(2))]
        if found:
            duration_tokens[m.group(1)] = found
            durations.extend(found)
    delay_tokens: dict = {}
    for m in TOK_DELAY_RE.finditer(css):
        found = [d.group(0) for d in DUR_RE.finditer(m.group(2))]
        if found:
            delay_tokens[m.group(1)] = found
            delay_excluded.extend(found)
    durations = list(dict.fromkeys(durations))
    delay_excluded = list(dict.fromkeys(delay_excluded))

    variables = {m.group(1): m.group(2).strip() for m in VAR_RE.finditer(css)}

    # v1.2.0 P1-4：不可解析值的**跳过登记**（沉默必须与通过可区分）
    skipped = []
    for name, val in variables.items():
        if _COLORISH_NAME_RE.search(name) and _COLORISH_VAL_RE.search(val):
            if parse_color_value(val) is None:
                skipped.append({"name": name, "value": val[:60]})

    # v1.6.0 ①：**动效声明**与「声明了却没有时长」分开登记 —— 让 M1 能区分
    #   「该文件根本没有动效」（无对象 ⇒ SKIP）与「有动效但没写秒数」（真缺陷 ⇒ FAIL）。
    #   原实现只看 durations 是否为空，两种情况**输出完全相同**（都 FAIL）：
    #   实测 `layouts.css` 零动效声明却被判 FAIL —— 又一次「空集冒充问题」。
    motion_decls, motion_without_time = [], []
    for m in _DECL_RE.finditer(css):
        prop = m.group(1).lower()
        if prop not in _DUR_PROPS:
            continue
        val = m.group(2).strip()
        # `!important` 是优先级标记，不是值的一部分 —— 不剥掉的话 `transition: none !important`
        # 会被当成「有动效但没写时长」而造出假 FAIL（实测 ui库 `Deck.css` L447 正是这个形状）。
        _norm = re.sub(r"\s*!important\s*$", "", val, flags=re.I).strip().lower()
        if _norm in _NO_MOTION_KEYWORDS:
            continue                      # `transition: none` 是「没有动效」，不是「漏写时长」
        motion_decls.append(f"{prop}: {val[:40]}")
        if not DUR_RE.search(val):
            motion_without_time.append(f"{prop}: {val[:40]}")

    # v1.6.0 ②：**韵律阶梯**（有序序列）—— `--*stagger*`/`--*delay*` 令牌的斜杠序列，
    #   以及同一选择器前缀下按 `nth-child` 索引排序的 delay 序列。
    rhythm_ladders = []
    for m in TOK_DELAY_RE.finditer(css):
        vals = _ladder_ms(m.group(2))
        if vals and len(vals) >= 2:
            rhythm_ladders.append({"where": f"令牌 {m.group(1)}", "values": vals})
    _groups: dict = {}
    for m in _BLOCK_RE.finditer(css):
        sel, body = m.group(1), m.group(2)
        nth = _NTH_RE.search(sel)
        if not nth:
            continue
        idx = int(nth.group(1) or nth.group(2))
        prefix = _clean_sel(_NTH_RE.sub("<nth>", sel))
        for d in _DECL_RE.finditer(body):
            if d.group(1).lower() in _DELAY_PROPS:
                for tm in DUR_RE.finditer(d.group(2)):
                    _groups.setdefault(prefix, []).append((idx, tm.group(0)))
    for prefix, pts in _groups.items():
        vals = _ladder_ms([v for _i, v in sorted(pts, key=lambda x: x[0])])
        if vals and len(vals) >= 2:
            rhythm_ladders.append({"where": f"选择器 {prefix[:56]}", "values": vals})

    # v1.6.0 ③：radial-gradient 的**所在层**（W2 的 allowed_in_layers 的对象）
    radial_blocks = []
    for m in _BLOCK_RE.finditer(css):
        sel, body = m.group(1), m.group(2)
        if not RADIAL_RE.search(body):
            continue
        lm = _LAYER_DECL_RE.search(body)
        radial_blocks.append({
            "selector": _clean_sel(sel)[:60],
            "layer": lm.group(1).strip() if lm else None,
        })

    return {
        "colors": colors,
        "sizes": sizes,
        "durations": durations,
        "variables": variables,
        "has_radial": bool(RADIAL_RE.search(css)),
        "size_roles": size_roles,
        "duration_tokens": duration_tokens,
        "delay_tokens": delay_tokens,             # v1.5.0：delay/stagger 语义令牌（另立一门）
        "delay_excluded": delay_excluded,         # v1.5.0：不参与 G13 的 delay 语义值（登记）
        "skipped_values": skipped,
        "unresolved_sizes": unresolved_sizes,   # v1.3.0：相对单位，无绝对值
        "motion_decls": motion_decls,           # v1.6.0：动效声明（含关键字过滤）
        "motion_without_time": motion_without_time,  # v1.6.0：声明了动效却无时长（真缺陷）
        "rhythm_ladders": rhythm_ladders,       # v1.6.0：错峰阶梯（有序）
        "radial_blocks": radial_blocks,         # v1.6.0：含 radial 的块 + 其声明的层
    }


def extract_spec(md: str) -> dict:
    lines = [ln.strip() for ln in md.splitlines() if ln.strip()]
    # 按标题分章节：动效条目只取「动效」章节下的列表项，
    # 否则视觉规范里的「- 配色：…」会被误当成动效条目
    sections: dict = {}
    cur = "__head__"
    for ln in lines:
        if ln.startswith("#"):
            cur = ln.lstrip("#").strip()
            sections.setdefault(cur, [])
        else:
            sections.setdefault(cur, []).append(ln)
    motion_items = []
    _motion_types = ("进场", "常态", "交互", "退场")
    for title, items in sections.items():
        if "动效" in title:
            # 动效条目 = 以动效类型开头的列表项；「- 记忆点：…」不是动效条目
            motion_items.extend(
                i
                for i in items
                if i.startswith(("- ", "* "))
                and any(t in i.split("：")[0] for t in _motion_types)
            )
    types = {t for t in ("进场", "常态", "交互", "退场") if any(t in ln for ln in lines)}
    return {
        "text": md,
        "lines": lines,
        "motion_items": motion_items,
        "types": types,
        "has_accent": any("强调色" in ln for ln in lines),
        "has_memory_point": any(("记忆点" in ln or "视觉焦点" in ln) for ln in lines),
        "has_cta": any(("主按钮" in ln or "主 CTA" in ln or "主CTA" in ln) for ln in lines),
        "has_feedback": any(("点击" in ln or "hover" in ln.lower() or "悬停" in ln) for ln in lines),
        # v1.7.0：`has_shot` 已移除 —— V1 改由 params.elements 驱动（见 chk_shot_spec_present）
        "has_series": any("系列" in ln for ln in lines),
    }


def extract_geom(path) -> dict:
    """渲染色（v1.2.0 P3）。契约见 --self-test 输出与技能 references/。

    必填：nodes 数组，每项 {i, parent, tag, rect:{x,y,w,h}, fontSize, visible}
    可选：text / cls / color / bg / fontWeight
    """
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    nodes = d.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("geom JSON 缺 nodes 数组")
    return {"viewport": d.get("viewport") or {}, "nodes": nodes, "source": d.get("source")}


# --------------------------------------------------------------------------
# 三、色彩数学：CIEDE2000（v1.2.0 P1-1）与 WCAG 对比度
# --------------------------------------------------------------------------
def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb) -> float:
    r, g, b = (_lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    l1, l2 = luminance(a), luminance(b)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def rgb_to_lab(rgb) -> tuple:
    """sRGB → CIE Lab (D65)。"""
    r, g, b = (_lin(x) for x in rgb)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    xn, yn, zn = 0.95047, 1.00000, 1.08883

    def f(t):
        return t ** (1.0 / 3.0) if t > (6.0 / 29.0) ** 3 else t / (3 * (6.0 / 29.0) ** 2) + 4.0 / 29.0

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e00(lab1, lab2) -> float:
    """CIEDE2000 色差（Sharma 等 2005 的标准实现）。"""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    Cbar = (C1 + C2) / 2.0
    G = 0.5 * (1 - math.sqrt(Cbar ** 7 / (Cbar ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360.0
    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        d = h2p - h1p
        if d > 180:
            d -= 360
        elif d < -180:
            d += 360
        dhp = d
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lbarp = (L1 + L2) / 2
    Cbarp = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbarp = h1p + h2p
    else:
        s = h1p + h2p
        if abs(h1p - h2p) <= 180:
            hbarp = s / 2
        elif s < 360:
            hbarp = (s + 360) / 2
        else:
            hbarp = (s - 360) / 2
    T = (
        1
        - 0.17 * math.cos(math.radians(hbarp - 30))
        + 0.24 * math.cos(math.radians(2 * hbarp))
        + 0.32 * math.cos(math.radians(3 * hbarp + 6))
        - 0.20 * math.cos(math.radians(4 * hbarp - 63))
    )
    dtheta = 30 * math.exp(-(((hbarp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbarp ** 7 / (Cbarp ** 7 + 25 ** 7))
    Sl = 1 + (0.015 * (Lbarp - 50) ** 2) / math.sqrt(20 + (Lbarp - 50) ** 2)
    Sc = 1 + 0.045 * Cbarp
    Sh = 1 + 0.015 * Cbarp * T
    Rt = -math.sin(math.radians(2 * dtheta)) * Rc
    return math.sqrt(
        (dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)
    )


def apca_lc(fg_rgb, bg_rgb) -> float:
    """APCA-W3 的 Lc（lightness contrast），0–106。符号表示极性。

    来源：APCA-W3 0.1.9 的公开常数（normBG .56 / normTXT .57 / revTXT .62 / revBG .65、
    blkThrs .022、scale .14、offset .027）。用于 R 组与诊断输出，**不作为默认 FAIL 判据**。
    """
    def ys(rgb):
        s = [(c / 255.0) ** 2.4 for c in rgb]
        return 0.2126729 * s[0] + 0.7151522 * s[1] + 0.0721750 * s[2]

    ytxt, ybg = ys(fg_rgb), ys(bg_rgb)
    # soft clamp：APCA 规范是 Y + (blkThrs - Y)^blkClmp（**带指数**），
    # 不是线性拉到 blkThrs —— 后者会让黑字白底算出 98 而非 106。
    ytxt = ytxt + (0.022 - ytxt) ** 1.414 if ytxt < 0.022 else ytxt
    ybg = ybg + (0.022 - ybg) ** 1.414 if ybg < 0.022 else ybg
    if abs(ybg - ytxt) < 0.0005:
        return 0.0
    if ybg > ytxt:  # 深字浅底（正极性）
        s = (ybg ** 0.56 - ytxt ** 0.57) * 1.14
        return ((s if s > 0 else 0.0) - 0.027) * 100
    s = (ybg ** 0.65 - ytxt ** 0.62) * 1.14  # 浅字深底（反极性）
    # ⚠️ 反极性的 offset 是 **加**（APCA-W3 原实现：SAPC + loWoBoffset）
    return ((s if s < 0 else 0.0) + 0.027) * 100


def _find_var(variables: dict, *needles, exclude=()):
    """按变量名包含 needles 全部子串（且不含 exclude 任一子串）取第一个**有颜色值**的变量。

    ⚠️ 未命中返回 `(None, None)` —— 调用侧**必须**判 `[1] is None`，不可用
    `a or b` 形式（非空元组恒为真，会把 fallback 变成死代码，见 v1.1.0 补丁 B）。
    本函数也**只返回可解析的颜色**：不可解析的值在这里就被排除，
    并由 extract_css 记入 skipped_values（v1.2.0 P1-4）。
    """
    for name, val in variables.items():
        low = name.lower()
        if all(n in low for n in needles) and not any(e in low for e in exclude):
            rgb = parse_color_value(val)
            if rgb:
                return name, rgb
    return None, None


# --------------------------------------------------------------------------
# 四、检查实现
#     返回 (status, detail)   status ∈ {PASS, FAIL, SKIP}
# --------------------------------------------------------------------------
def chk_color_count_max(ctx, params):
    """画面内去重色值数上限（G1）。

    ⚠️ v1.2.2 口径修正（**真实 deck 页实测暴露**）：
    「画面内」是**渲染**语境 —— 判据集自己的 note 就写明「token 表的调色板规模
    **不适用**本判据（见 G11）」。但 v1.0/v1.1 的实现拿 CSS **令牌清单**去顶这一口径：
    于是「设计系统声明了几个令牌色」被当成「一页画面里出现了几种颜色」，
    21 套主题 **21/21 FAIL** —— 那是口径错位，不是设计缺陷。
    现在：**有渲染色（--geom）就数画面里真实出现过的颜色**（节点的 color/bg），
    没有渲染色则判 **SKIP**（未检测）—— 不再拿令牌清单冒充画面。
    注意这不是放宽：拿真实渲染帧去比 6 色上限，一样会 FAIL。
    """
    nodes = _geom_nodes(ctx)
    if nodes is None:
        return "SKIP", ("未提供渲染色（--geom）—— 「画面内」口径需要**渲染结果**；"
                        "令牌清单不适用本判据（见判据集 note；令牌层规模由 G11 承接）")
    seen = set()
    for n in nodes:
        if not n.get("visible", True):
            continue
        for k in ("color", "bg"):
            v = n.get(k)
            if isinstance(v, (list, tuple)) and len(v) >= 3:
                try:
                    seen.add((int(v[0]), int(v[1]), int(v[2])))
                except (TypeError, ValueError):
                    continue
    if not seen:
        return "SKIP", "渲染色中未取到任何颜色值（color/bg 全空）"
    n = len(seen)
    if n <= params["max"]:
        return "PASS", f"画面内去重色值 {n} ≤ {params['max']}（渲染实测）"
    return "FAIL", f"画面内去重色值 {n} > {params['max']}（渲染实测）"


def chk_contrast_min(ctx, params):
    if not ctx["css"]:
        return "SKIP", "未提供 CSS"
    role = params["role"]
    v = ctx["css"]["variables"]
    if role == "body":
        _, fg = _find_var(v, "fg", exclude=("subtle", "muted"))
        _, bg = _find_var(v, "bg", exclude=("alt",))
    elif role == "muted":
        _, fg = _find_var(v, "muted")
        _, bg = _find_var(v, "bg", exclude=("alt",))
    elif role == "subtle":
        _, fg = _find_var(v, "subtle")
        _, bg = _find_var(v, "bg", exclude=("alt",))
    else:
        # v1.1.0 补丁 B：显式判空再兜底（v1.0 写作 `a or b`，右支永不执行）
        _, fg = _find_var(v, "primary")
        if fg is None:
            _, fg = _find_var(v, "accent")
        _, bg = _find_var(v, "bg", exclude=("alt",))
    if not fg or not bg:
        return "SKIP", f"CSS 变量中未找到 {role} 前景/背景对"
    r = contrast(fg, bg)
    if r >= params["min"]:
        return "PASS", f"{role} 对比度 {r:.2f}:1 ≥ {params['min']}"
    return "FAIL", f"{role} 对比度 {r:.2f}:1 < {params['min']}"


def chk_font_scale_count_max(ctx, params):
    """画面内字号档数上限（G6）。口径与 G1 同批修正（v1.2.2），**v1.2.3 再修一处**。

    v1.0/v1.1 拿 CSS 里**声明**的字号去顶「画面内」口径 —— 令牌清单的档数
    是「设计系统准备了几个字号」，不是「一页里用了几档」（v1.2.2 已改为吃渲染结果）。

    ⚠️ v1.2.3：吃渲染结果之后**又数多了** —— 原实现取 `fontSize` 非空的**全部可见节点**，
    于是把「**容器继承的字号**」也当成了一个「层级」。真实 deck 封面上
    `.ui-deck__slide` 根容器继承到 14px、装饰 span 继承到 26px，二者都**没有一个字**，
    却让「6 档」超标（真值 4 档：eyebrow 18.4 / meta 20 / subtitle 32.5 / title 96）。
    ⇒ 现只统计**承载文字**的节点（`_text_bearing`）。
    ⚠️ 这不是放宽：max 仍是 4；页面若真用 5 档**文字**字号，照样 FAIL（有阴性对照）。
    若取数器**没有**提供 `text` 字段，则退回全部节点并在 detail 显式标注 ——
    不静默改变口径。
    """
    nodes = _geom_nodes(ctx)
    if nodes is None:
        return "SKIP", ("未提供渲染色（--geom）—— 「画面内」口径需要**渲染结果**；"
                        "令牌清单不适用本判据（见判据集 note；令牌层一致性由 G12 承接）")
    has_text_field = any("text" in x for x in nodes)
    sizes = sorted({x.get("fontSize") for x in nodes
                    if x.get("visible", True) and x.get("fontSize")
                    and (not has_text_field or _text_bearing(x))})
    if not sizes:
        return "SKIP", "渲染色中未取到任何字号（fontSize 全空）"
    n = len(sizes)
    caveat = ("" if has_text_field else
              "；⚠取数器未提供 text 字段 ⇒ 退回全部节点，口径可能偏大")
    if n <= params["max"]:
        return "PASS", f"画面内字号档位 {n} ≤ {params['max']}（渲染实测，只计承载文字的节点；{sizes}{caveat}）"
    return "FAIL", f"画面内字号档位 {n} > {params['max']}（渲染实测，只计承载文字的节点；{sizes}{caveat}）"


def chk_font_scale_ratio_range(ctx, params):
    """v1.2.0 P0-1：**按角色词根分组后**再算相邻阶比。

    v1.0 把 caption/body/h/display 的全部字号混在一个序列里排序，
    而不同体系之间本无可比性 —— 实测 21 套主题全 FAIL，其中 15 套是假阳性。
    """
    if not ctx["css"]:
        return "SKIP", "未提供 CSS"
    lo, hi = params["min"], params["max"]
    group_by = params.get("group_by") or "none"
    min_group = int(params.get("min_group_size") or 2)

    groups: dict = {}
    ungrouped = False
    if group_by == "role-prefix":
        for name, px in (ctx["css"].get("size_roles") or {}).items():
            stem = _role_stem(name)
            if stem:
                groups.setdefault(stem, []).append(px)
        named = len(groups)                       # 过滤前：提取到词根的体系个数
        groups = {k: sorted(set(v)) for k, v in groups.items() if len(set(v)) >= min_group}
        if not groups:
            # ⚠️ v1.2.3：两套「不能比」必须分开 —— 原实现把它们混为一谈：
            #   (a) **一个词根都提不到** ⇒ 令牌没有命名体系 ⇒ 降级为整体序列（并在 detail 标注）
            #   (b) **有词根，但每个体系都不足 min_group 档** ⇒ **没有可比的组** ⇒ 必须判 SKIP
            # 原实现 (b) 也退回整体序列，于是把「不同体系混算」又放了回来 ——
            # 那正是 v1.1 修掉的假阳性来源（实测：`size-quote` 40px 与 `size-quote-mark`
            # 150px 分家之后两组各 1 档，却被混成 [40,150] 报出 3.75 的"越界"）。
            if named:
                return "SKIP", (f"无可用体系（{named} 个词根各自 < {min_group} 档，不构成可比序列）"
                                f"—— 未检测，不是通过；退回整体序列会把不同体系混算（v1.1 已修过的假阳性）")
            ungrouped = True
            groups = {"(未分组)": sorted(set(ctx["css"]["sizes"]))}

    parts, bad_total = [], 0
    for g in sorted(groups):
        vals = groups[g]
        if len(vals) < 2:
            parts.append(f"{g}[{vals} 档位不足]")
            continue
        rs = [round(vals[i + 1] / vals[i], 3) for i in range(len(vals) - 1)]
        bad = [r for r in rs if not (lo <= r <= hi)]
        bad_total += len(bad)
        seg = "/".join(f"{r:g}" for r in rs)
        parts.append(f"{g}[{len(vals)}档]={seg}" + (f" ⚠越界{bad}" if bad else ""))
    detail = "；".join(parts)

    if bad_total:
        return "FAIL", f"{bad_total} 处阶比越界 [{lo}, {hi}] —— {detail}"
    tag = "（未分组：无令牌命名，按整体序列算）" if ungrouped else ""
    return "PASS", f"各组阶比均在 [{lo}, {hi}] {tag}—— {detail}"


def chk_motion_has_duration(ctx, params):
    """M1「时间刻度必填」。

    ⚠️ v1.6.0 修**空集语义**（真缺陷，与 v1.2.2 的「空集判 PASS → 改判 SKIP」同族）：
    原实现只看 `durations` 是否为空，于是「**该文件根本没有动效**」与「**有动效但没写秒数**」
    **输出完全相同**（都 FAIL）。实测 `ui库/src/deck/layouts/layouts.css` 零动效声明
    （`transition` / `animation` / `*duration` 一个都没有）却被判 FAIL —— 判据在**造信号**。
    v1.6.0 起**三态分开**：
      · 有动效声明但缺时长 ⇒ **FAIL**（真缺陷，照旧）；
      · 有动效声明且都带时长 ⇒ **PASS**；
      · 无动效声明、但声明了**时长令牌** ⇒ **PASS**（纯令牌产物如 21 套主题：秒数确实写下来了
        —— 早期版本这一态是靠 `durations` 非空蒙对的，属**作用域错配**，同 G1/G6/G11 一族）；
      · 既无动效声明、也无时长令牌 ⇒ **SKIP（无对象，不是通过）**。
    ⚠️ `transition: none` / `none !important` 属「**显式**无动效」，一律不计入动效声明
    （否则会造出假 FAIL，实测 `Deck.css` 有 4 处、`layouts.css` 也有）。
    """
    if not ctx["css"]:
        return "SKIP", "未提供 CSS"
    decls = ctx["css"].get("motion_decls") or []
    miss = ctx["css"].get("motion_without_time") or []
    toks = ctx["css"].get("duration_tokens") or {}
    # v1.6.0：`coverage` 此前**只声明未消费**（同 W2 的悬空参数，由 AST 探针查出）。
    #   现在真正接上：覆盖率 = 带时长的动效声明 / 全部动效声明。默认 1.0 ⇒ 与旧行为一致。
    cov = float(params.get("coverage") or 1.0)
    if decls:
        ratio = (len(decls) - len(miss)) / len(decls)
        if miss and ratio + 1e-9 < cov:
            return "FAIL", (
                f"{len(miss)}/{len(decls)} 处动效声明**未写时长**（覆盖率 {ratio:.2f} < {cov:g}）"
                f"：不写秒数只能拿到默认缓动 —— {miss[:4]}"
            )
        if miss:
            return "PASS", (f"覆盖率 {ratio:.2f} ≥ {cov:g}；仍有 {len(miss)} 处未写时长（已登记）："
                            f"{miss[:3]}")
        d = ctx["css"]["durations"]
        return "PASS", f"{len(decls)} 处动效声明全部带时长（{len(d)} 个时长值），样例 {d[:4]}"
    # ⚠️ 纯令牌文件（21 套主题就是这个形状）**没有动效声明**，但**声明了时长令牌** ——
    #    秒数确实被写下来了，本条应判 PASS；早期版本只看 `durations` 非空，属**作用域错配**
    #    （拿令牌层顶「动效声明」层，同 G1/G6/G11 一族）。两态在此再分开。
    if toks:
        return "PASS", (f"产物内无动效声明，但声明了 {len(toks)} 个时长令牌（秒数已写下）："
                        f"{list(toks)[:3]}")
    return "SKIP", ("产物内**既无动效声明、也无时长令牌** ⇒ 本条无对象（不是通过）。"
                    "`transition: none` 属显式无动效，不计入。")


def chk_skeleton_no_radial(ctx, params):
    """W2「骨架层不得依赖 radial-gradient」。

    ⚠️ v1.6.0 落地 `allowed_in_layers` —— 修**悬空参数**（声明有、代码无）：
    判据集自 v1.0 起就写着 `params: { allowed_in_layers: [氛围层] }`，而实现**一个字符都没读它**：
    实际是「CSS 里出现任何 radial-gradient 即 FAIL」，比文档更严。实测 `layouts.css` 的
    6 处 radial 全被判 FAIL，其中封面辉光 / 柔雾 / 远山脊线三处明确是装饰氛围。
    锚点：块内**显式声明** `--ui-layer: 氛围层;` 即放行；**缺声明一律 FAIL（fail-closed）**
    —— CSS 没有可机器识别的「层」概念，默认放行会把本判据变成 no-op。
    """
    if not ctx["css"]:
        return "SKIP", "未提供 CSS"
    allow = [str(x) for x in (params.get("allowed_in_layers") or [])]
    blocks = ctx["css"].get("radial_blocks") or []
    if not blocks:
        return "PASS", "未检出 radial-gradient"
    bad = [b for b in blocks if (b.get("layer") or "") not in allow]
    if bad:
        where = "；".join(f"{b['selector']}（层={b.get('layer') or '未声明'}）" for b in bad[:4])
        return "FAIL", (
            f"{len(bad)}/{len(blocks)} 处 radial-gradient 不在允许的层内：{where}"
            f" —— 导出 PPTX 会整层丢失；装饰性用法请在块内声明 `--ui-layer: {'/'.join(allow)}`"
            f"（**缺声明即判 FAIL**，fail-closed）"
        )
    return "PASS", f"{len(blocks)} 处 radial-gradient 均在声明的允许层内（{'、'.join(allow)}）"


# ---- v1.2.0 P1：token 层一致性 ----
def chk_palette_separation(ctx, params):
    """ΔE00 间距：两色距离 < 容差 ⇒ 人眼不可辨，应合并。

    ⚠️ v1.2.3 **作用域收窄到「语义色」**：层级 / 表面色（`bg` / `bg-alt` / `card-bg` /
    `surface-*` / `paper` …）是**同一语义下的明度阶梯**，其微差（ΔE00 0.6–2.0）正是
    「分层」这一设计意图本身，不是「两个该合并的颜色」。
    实测取证：21 套主题里 7 套 FAIL，**全部**是
    `bg ↔ bg-alt ↔ card-bg` 之间的对（ΔE00 0.61–1.96），**无一涉及 accent / fg / 语义色**
    —— 典型的作用域错配（同 G1/G6 一族）。
    被排除的令牌**逐条打印**（可审计、不静默丢弃）；可用 `params.layer_name_re` 覆盖模式。
    """
    if not ctx["css"]:
        return "SKIP", "未提供 CSS"
    try:
        layer_re = re.compile(params.get("layer_name_re") or _LAYER_COLOR_RE.pattern, re.I)
    except re.error:
        return "SKIP", "layer_name_re 非法（正则编译失败）—— 未检测"
    layer_vals, layer_names = set(), []
    for name, val in (ctx["css"].get("variables") or {}).items():
        c = parse_color_value(val)
        if c is not None and layer_re.search(name):
            layer_vals.add(tuple(c))
            if name.lstrip("-") not in layer_names:
                layer_names.append(name.lstrip("-"))
    colors = [c for c in sorted(ctx["css"]["colors"]) if tuple(c) not in layer_vals]
    excl = (f"；已排除 {len(layer_vals)} 个层级/表面色值、{len(layer_names)} 个令牌"
            f"（{'、'.join(sorted(layer_names)[:6])}{'…' if len(layer_names) > 6 else ''}）"
            if layer_names else "；无层级/表面色令牌")
    if len(colors) < 2:
        return "SKIP", f"语义色不足 2 个（{len(colors)}），无法计算间距{excl}"
    thr = float(params.get("min_separation_de") or 2.0)
    labs = [(c, rgb_to_lab(c)) for c in colors]
    pairs = []
    for i in range(len(labs)):
        for j in range(i + 1, len(labs)):
            d = delta_e00(labs[i][1], labs[j][1])
            if d < thr:
                pairs.append((labs[i][0], labs[j][0], round(d, 2)))
    pairs.sort(key=lambda x: x[2])
    if pairs:
        head = "; ".join(
            "#%02X%02X%02X ↔ #%02X%02X%02X ΔE00=%s" % (c1 + c2 + (d,))
            for c1, c2, d in pairs[:3]
        )
        return "FAIL", f"{len(pairs)} 对**语义色** ΔE00 < {thr}（人眼不可辨，应合并）：{head}{excl}"
    return "PASS", f"{len(colors)} 个**语义色**两两 ΔE00 ≥ {thr}{excl}"


def chk_scale_conformance(ctx, params):
    """字号必须落在**声明的刻度集**内。刻度集为空 ⇒ no-op（SKIP，不是通过）。

    ⚠️ v1.3.0 新增**自证式刻度**护栏：刻度集必须来自**独立声明**。
    实测取证：ui库 21 套主题的生成 CSS 里 raw `font-size:` 数 = **0**，
    `sizes` 与 `--deck-size-*` 令牌集**逐值相同**。此时若把「产物自己的令牌集」
    填进 `params.scale`，则 `sizes ⊆ scale` **恒成立** ⇒ 判据退化为恒 PASS。
    那不是「启用」，是**制造绿灯**（比 no-op 更坏：no-op 至少诚实报「未检测」）。
    ⇒ 检出即判 SKIP 并说明；正确用法是**声明侧（规范/令牌）与被检侧（使用 CSS）分离**。
    """
    if not ctx["css"]:
        return "SKIP", "未提供 CSS"
    scale = [float(s) for s in (params.get("scale") or [])]
    if not scale:
        return "SKIP", "未声明刻度集（params.scale 为空）—— 按 no-op 处理，不是通过"
    own = {round(float(v), 2) for v in (ctx["css"].get("size_roles") or {}).values()}
    if own and {round(float(s), 2) for s in scale} == own:
        return "SKIP", (
            f"刻度集与被检值**同源**（都来自本 CSS 的 {len(own)} 档字号令牌）"
            "⇒ 判定恒真，不算通过；刻度集须来自独立声明（另一份规范/令牌文件）"
        )
    tol = float(params.get("tolerance_px") or 0.5)
    vals = sorted(set(ctx["css"]["sizes"]))
    if not vals:
        return "SKIP", "产物内未取到任何字号"
    _un = ctx["css"].get("unresolved_sizes") or []
    note = (
        f"；已跳过 {len(_un)} 处相对单位（{'/'.join(sorted({u['unit'] for u in _un}))} 无绝对值）"
        if _un else ""
    )
    off = [v for v in vals if min(abs(v - s) for s in scale) > tol]
    if off:
        return "FAIL", f"{len(off)}/{len(vals)} 档字号不在声明刻度内：{off[:6]}（刻度 {scale}）{note}"
    return "PASS", f"{len(vals)} 档字号全部落在声明的 {len(scale)} 档刻度内（容差 {tol}px）{note}"


def _dur_to_ms(s: str):
    m = re.match(r"\s*([\d.]+)\s*(ms|s)\s*$", str(s))
    if not m:
        return None
    v = float(m.group(1))
    return v if m.group(2) == "ms" else v * 1000.0


def chk_duration_scale_conformance(ctx, params):
    """时长必须落在**声明的刻度集**内。v1.3.0 三处收紧（同 G12 一族）：

    ① **自证式刻度**护栏 —— 刻度集不得由被检 CSS 自身的时长令牌导出（恒真）。
    ② **0ms 不参与判定** —— 实测 `animation-delay: 0s` 被 DUR_RE 收进 durations，
       随后被当成「不在刻度内」。0 是「无延迟/无时长」，不是刻度上的一档。
       与 ① 不同，这条**不是**放宽：非 0 的离格值照样 FAIL（有阴性对照）。
    ③ detail 显式报出被排除的 0 值数量（与 G11 的「被排除令牌逐条打印」同构，不静默）。

    ⚠️ v1.5.0 ④ **delay/stagger 语义与被检侧分家**（取数层已改，见 extract_css）：
    原实现按行扫 `(animation|transition)`，把 `animation-delay` 的**错峰阶梯**当成时长。
    实测 ui库 `Deck.css` 的 `0 / 0.08s / 0.18s / 0.3s / 0.44s / 0.6s / 0.78s` 因此被判
    6 档离格；同时 21 套主题各有一条 `--deck-motion-stagger` 同值序列 —— 声明侧与被检侧
    **同源**，故该维度上 `被检值 ⊆ 刻度` **恒真**（「假绿」第二形态）。
    ⇒ 现在 durations 只含 duration 语义；delay/stagger 值登记进 `delay_excluded`
    并在 detail 报出（**不静默**）。这不是放宽阈值：真离格的 duration 照样 FAIL
    （修口径后实测 ui库 Deck.css 仍精确指认 `180ms` / `200ms` 两处硬编码）。
    """
    if not ctx["css"]:
        return "SKIP", "未提供 CSS"
    scale = [float(s) for s in (params.get("scale") or [])]
    if not scale:
        return "SKIP", "未声明时长刻度集（params.scale 为空）—— 按 no-op 处理，不是通过"
    own = set()
    for _ds in (ctx["css"].get("duration_tokens") or {}).values():
        for _d in _ds:
            _ms = _dur_to_ms(_d)
            if _ms is not None:
                own.add(round(_ms, 3))
    if own and {round(float(s), 3) for s in scale} == own:
        return "SKIP", (
            f"时长刻度集与被检值**同源**（都来自本 CSS 的 {len(own)} 个时长令牌）"
            "⇒ 判定恒真，不算通过；刻度集须来自独立声明"
        )
    tol = float(params.get("tolerance_ms") or 1.0)
    allv = sorted({ms for ms in (_dur_to_ms(d) for d in ctx["css"]["durations"]) if ms is not None})
    _dx = ctx["css"].get("delay_excluded") or []
    dnote = (f"；另 {len(_dx)} 个 delay/stagger 语义值不参与判定"
             f"（错峰序列属韵律层，本判据集未覆盖）：{_dx[:4]}") if _dx else ""
    if not allv:
        return "SKIP", f"产物内未取到任何时长{dnote}"
    zero = [v for v in allv if v == 0]
    vals = [v for v in allv if v != 0]
    znote = f"；0ms ×{len(zero)} 不参与判定（无延迟不是刻度上的一档）" if zero else ""
    if not vals:
        return "SKIP", f"产物内时长全为 0ms{znote}{dnote}"
    off = [v for v in vals if min(abs(v - s) for s in scale) > tol]
    if off:
        return "FAIL", f"{len(off)}/{len(vals)} 个时长不在声明刻度内：{off[:6]}（刻度 {scale}ms）{znote}{dnote}"
    return "PASS", f"{len(vals)} 个时长全部落在声明的 {len(scale)} 档刻度内（容差 {tol}ms）{znote}{dnote}"


def _ladder_ms(seq) -> list | None:
    """把**有序**的错峰序列折成 ms。任一项不是纯时间（含 `var()`/关键字）即返回 None。

    ⚠️ 不能用 `DUR_RE` 取序列：它要求带单位，会把 `0 / 0.08s / …` 的首项 `0` **静默丢掉**
    （实测 21 套主题的 `--deck-motion-stagger` 正是这个形状）。此处按 `/`、`,` 切分，
    仅对**裸 `0`** 允许省略单位（CSS 里 `0` 是唯一合法的无单位时间）。
    ⚠️ `seq` 允许两种形状：**字符串**（令牌原始值，按 `/`、`,` 切分）与**列表**
    （应用侧已逐个取出的时间串）—— 早期版本对列表也走 `str()` 再切分，于是切出带引号的
    `"['0s'"` 之类、`fullmatch` 全失败 ⇒ 应用侧序列**恒为空**（由自检的 nth-child 用例查出）。
    """
    if isinstance(seq, (list, tuple)):
        parts = list(seq)
    else:
        parts = re.split(r"[/,]", str(seq))
    out = []
    for part in parts:
        t = str(part).strip()
        m = re.fullmatch(r"([\d.]+)\s*(ms|s)?", t)
        if not m:
            return None
        unit = m.group(2)
        if unit is None and float(m.group(1)) != 0:
            return None
        out.append(float(m.group(1)) if (unit or "s") == "ms" else float(m.group(1)) * 1000.0)
    return out


def chk_rhythm_ladder(ctx, params):
    """v1.6.0 新增（G16）：错峰阶梯必须是**非递减**序列。

    ⭐ 这是一条**结构性不变量**，不引入任何数值阈值 —— 错峰的意义是「越靠后的元素越晚入场」，
    阶梯回退意味着后面的元素反而先动。判据集 v1.5 的 G13 note 已如实登记「韵律层未覆盖」，
    本条即补这个缺口。

    ⚠️ **刻意不要求步长均匀**：真实语料（ui库 21 套主题的 `--deck-motion-stagger`
    与 `Deck.css` 的 nth-child 阶梯）用的是**加速步长** 80 / 100 / 120 / 140 / 160 / 180 ms。
    要求等步长会把它判成缺陷 —— 那才是「**凭空发明契约**」（同 R3 默认 8px 的教训）。
    ⚠️ 允许**末尾饱和封顶**（实测 `nth-child(n+8)` 复用末值 `0.78s`，防止无限推迟），
    故判「非递减」而非「严格递增」。

    两侧输入（缺一侧不影响另一侧判定）：① 声明侧 = `--*stagger*`/`--*delay*` 令牌的斜杠序列；
    ② 应用侧 = 同一选择器前缀下按 `nth-child` 索引排序的 delay 序列。
    无长度 ≥ `min_points` 的序列 ⇒ **SKIP**（本判据无对象，不是通过）。
    """
    if not ctx["css"]:
        return "SKIP", "未提供 CSS"
    ladders = ctx["css"].get("rhythm_ladders") or []
    minp = int(params.get("min_points") or 2)
    usable = [L for L in ladders if len(L["values"]) >= minp]
    if not usable:
        return "SKIP", (
            f"未取到长度 ≥{minp} 的错峰序列（本判据**无对象**，不是通过）"
            f"；已登记 {len(ladders)} 条不足 {minp} 点的序列"
        )
    bad = []
    for L in usable:
        v = L["values"]
        for i in range(1, len(v)):
            if v[i] < v[i - 1] - 1e-6:
                bad.append(f"{L['where']}：第 {i + 1} 点 {v[i]:g}ms < 第 {i} 点 {v[i - 1]:g}ms")
    rounds = "；".join(f"{L['values'][0]:g}→{L['values'][-1]:g}ms×{len(L['values'])}点" for L in usable[:3])
    if bad:
        return "FAIL", f"{len(bad)} 处阶梯回退（越靠后越早入场）：" + "；".join(bad[:4])
    return "PASS", f"{len(usable)} 条错峰序列全部非递减（{rounds}）；**不要求步长均匀**（加速阶梯合法）"


def chk_accent_availability(ctx, params):
    """accent 低于阈值**不判 FAIL** —— 契约明确记为 NOTE（`accentPolicy`）。"""
    if not ctx["css"]:
        return "SKIP", "未提供 CSS"
    v = ctx["css"]["variables"]
    _, ac = _find_var(v, "accent", exclude=("strong", "ink"))
    _, bg = _find_var(v, "bg", exclude=("alt",))
    if not ac or not bg:
        return "SKIP", "未找到 accent / bg 对"
    r = contrast(ac, bg)
    thr = float(params.get("min_ratio") or 3.0)
    if r < thr:
        return "PASS", (
            f"NOTE: accent 对 bg 对比度 {r:.2f}:1 < {thr} —— 仅可用于色块/装饰，"
            f"不可直接用作文字色（契约 accentPolicy 记为 NOTE 而非 WARN）"
        )
    return "PASS", f"accent 对 bg 对比度 {r:.2f}:1 ≥ {thr}，可承载文字"


# ---- spec 类 ----
def chk_accent_unique(ctx, params):
    if not ctx["spec"]:
        return "SKIP", "未提供 spec"
    if ctx["spec"]["has_accent"]:
        return "PASS", "spec 已显式声明强调色"
    return "FAIL", "spec 未显式声明强调色 —— 颜色数量约束缺失，AI 只能自由发挥"


def chk_memory_point_count(ctx, params):
    if not ctx["spec"]:
        return "SKIP", "未提供 spec"
    if ctx["spec"]["has_memory_point"]:
        return "PASS", "spec 已显式声明记忆点/视觉焦点"
    return "FAIL", "spec 未显式声明记忆点/视觉焦点 —— 焦点约束缺失，产出必然处处用力"


def chk_primary_cta_count(ctx, params):
    if not ctx["spec"]:
        return "SKIP", "未提供 spec"
    if ctx["spec"]["has_cta"]:
        return "PASS", "spec 已显式声明主按钮/主 CTA"
    return "FAIL", "spec 未显式声明主按钮/主 CTA —— 视觉重心约束缺失"


def chk_motion_types_present(ctx, params):
    if not ctx["spec"]:
        return "SKIP", "未提供 spec"
    required = params.get("required") or []
    missing = [t for t in required if t not in ctx["spec"]["types"]]
    found = sorted(ctx["spec"]["types"])
    if not missing:
        return "PASS", f"已覆盖 {found}，必填 {required} 齐备"
    return "FAIL", f"动效类型缺 {missing}（已覆盖 {found}）"


def chk_motion_minimal_set(ctx, params):
    if not ctx["spec"]:
        return "SKIP", "未提供 spec"
    items = ctx["spec"]["motion_items"]
    if not items:
        return "FAIL", "spec 中未检出任何动效条目（- 开头）"
    # 「- 退场：无」是合法声明（明确无退场），不要求时长
    no_dur = [
        it for it in items if not DUR_RE.search(it) and "无" not in it.split("：", 1)[-1]
    ]
    if not no_dur:
        return "PASS", f"{len(items)} 条动效条目全部带时间刻度"
    return "FAIL", f"{len(no_dur)}/{len(items)} 条动效条目缺时间刻度，如：{no_dur[0][:60]}"


def chk_interactive_feedback_coverage(ctx, params):
    if not ctx["spec"]:
        return "SKIP", "未提供 spec"
    if ctx["spec"]["has_feedback"]:
        return "PASS", "spec 已声明交互反馈"
    return "FAIL", "spec 未声明交互反馈（点击 / hover / 悬停）——「每一次点击都有回应」缺失"


# v1.7.0：契约项 → 关键词的**适配层**。契约（`params.elements`）可配，实现只做翻译；
# 键不存在 ⇒ 显式 FAIL（不静默按空集处理，否则「契约写错了」会退化成 PASS）。
_ELEMENT_KEYWORDS = {
    "构图": ("构图",),
    "光比或色温": ("光比", "色温"),
}


def chk_shot_spec_present(ctx, params):
    """V1：由 `params.elements` 驱动（v1.7.0 之前硬编码在 extract_spec 里，参数形同虚设）。"""
    if not ctx["spec"]:
        return "SKIP", "未提供 spec"
    elems = params.get("elements")
    if elems is None:
        return "FAIL", "判据未声明 params.elements —— 契约缺失，无法判定"
    if not isinstance(elems, list) or not elems:
        return "FAIL", f"params.elements 应为非空列表（当前 {elems!r}）"
    bad = [e for e in elems if e not in _ELEMENT_KEYWORDS]
    if bad:
        return "FAIL", f"params.elements 含无关键词映射的项 {bad} —— 契约无法翻译成可判定的谓词"
    lines = ctx["spec"]["lines"]
    missing = [e for e in elems
               if not any(k in ln for k in _ELEMENT_KEYWORDS[e] for ln in lines)]
    if not missing:
        return "PASS", f"spec 已声明 {' + '.join(elems)}"
    return "FAIL", f"spec 未声明 {'、'.join(missing)}（契约要求同时声明 {' + '.join(elems)}）"


def chk_series_count_max(ctx, params):
    if not ctx["spec"]:
        return "SKIP", "未提供 spec"
    if ctx["spec"]["has_series"]:
        return "PASS", "spec 已声明系列数"
    return "SKIP", "spec 未声明系列数 —— 无法判定（不是通过）"


# ---- v1.2.0 P3：渲染色几何（输入为 --geom 产出的契约 JSON）----
def _geom_nodes(ctx):
    return (ctx.get("geom") or {}).get("nodes")


def _rect(n):
    r = n.get("rect") or {}
    try:
        return float(r.get("x")), float(r.get("y")), float(r.get("w")), float(r.get("h"))
    except (TypeError, ValueError):
        return None


def _text_bearing(n) -> bool:
    """该节点是否**自己承载文字**（v1.2.3 新增）。

    G6 数的是「画面内的**字号层级**」，而「层级」只在**真的渲染出文字**的地方存在。
    实测取证（ai-neon 真实 deck 封面）：全部可见节点为 6 档
    `{14, 18.4, 20, 26, 32.5, 96}`，其中

      · `14px` 落在 `.ui-deck__slide` **根容器**（自身无文字，纯继承）
      · `26px` 是被 `.ui-deck-cover__art*` 等**装饰 span 与容器继承**的基础档

    两者都不承载任何文字。只数承载文字的节点 ⇒ `{18.4, 20, 32.5, 96}` = **4 档**，
    **21 套主题无一例外**。⇒ 原口径（所有元素的计算字号）把「继承值」冒充成了「层级」。
    """
    t = n.get("text")
    return t is not None and bool(str(t).strip())


def chk_near_alignment(ctx, params):
    """兄弟元素四条边的「近乎对齐」（plumb edge/near-alignment）。

    ⚠️ v1.2.2 两处修正（**都在真实 deck 页上实测暴露**，不是推演）：
    ① `_flush_miss` 原写 `centroid = int(sum/len)` —— 把簇心**截断成整数**，
       于是每个成员被凭空算出一个 ≤1px 的差。实测：同一容器内 4 条**本该完全重合**
       的右边（脱敏后 x+w 全等）被报成「差 0.39px」共 10 处 ——
       **是判据在造信号，不是产物有缺陷**。改为浮点均值。
    ② 真实渲染有**亚像素噪声**（缩放画布尤甚：`transform:scale` 会把浏览器
       0.1px 级布局舍入放大到设计像素的零点几 px）。规则原意是「眼看要对齐了
       却没对齐，**眼睛看得出来**」，而亚像素差看不出来 ⇒ 引入**噪声地板**
       `noise_px`（默认 0.5），只报 `noise < d ≤ tolerance`。
       ⚠️ 地板与容差**同单位**（均为设计像素）；`noise ≥ tolerance` 时判
       SKIP —— 配置自相矛盾时不许静默变成「永不报警」。
    """
    nodes = _geom_nodes(ctx)
    if nodes is None:
        return "SKIP", "未提供渲染色（--geom）—— 未检测，不是通过"
    if not nodes:
        # 空集不得判 PASS：那是「没数据」冒充「没问题」（同族：SKIP 不得并入通过）
        return "SKIP", "渲染色为空（nodes=[]）—— 未检测，不是通过"
    tol = float(params.get("tolerance_px") or 2)
    _np = params.get("noise_px")
    noise = float(0.5 if _np is None else _np)
    min_cluster = int(params.get("min_cluster") or 2)
    if noise >= tol:
        return "SKIP", f"noise_px({noise}) ≥ tolerance_px({tol}) —— 判据配置自相矛盾，未检测"
    by_parent: dict = {}
    for n in nodes:
        if not n.get("visible", True):
            continue
        r = _rect(n)
        if r is None:
            continue
        by_parent.setdefault(str(n.get("parent")), []).append((n.get("i"), r))
    misses = []
    for _p, items in by_parent.items():
        if len(items) < min_cluster:
            continue
        for axis, idx in (("left", 0), ("right", None), ("top", 1), ("bottom", None)):
            vals = []
            for i, (x, y, w, h) in items:
                v = (x if idx == 0 else (x + w)) if axis in ("left", "right") else (y if idx == 1 else (y + h))
                vals.append((v, i))
            vals.sort()
            cluster = []
            for v, i in vals:
                if cluster and v - cluster[0][0] > tol:
                    if len(cluster) >= min_cluster:
                        _flush_miss(cluster, tol, noise, misses, axis)
                    cluster = []
                cluster.append((v, i))
            if len(cluster) >= min_cluster:
                _flush_miss(cluster, tol, noise, misses, axis)
    if misses:
        head = "; ".join(f"{a}轴差 {v}px（#{i}）" for a, v, i in misses[:4])
        return "FAIL", f"{len(misses)} 处近乎对齐（噪声地板 {noise}px < 差 ≤ {tol}px 却未对齐）：{head}"
    return "PASS", f"未检出近乎对齐的兄弟边（只报 {noise}px < 差 ≤ {tol}px 的差）"


def _flush_miss(cluster, tol, noise, out, axis):
    # 簇心用**浮点均值** —— v1.2.2 修：原 `int(...)` 截断会凭空造出 ≤1px 的假差
    centroid = sum(v for v, _ in cluster) / len(cluster)
    for v, i in cluster:
        d = abs(v - centroid)
        if noise < d <= tol:
            out.append((axis, round(d, 2), i))


def _side_by_side(a, b, gap=0.5, overlap=0.8):
    """两个矩形是否算「同一视觉行里的**并排**兄弟」。

    plumb 的 sibling/*-consistency 针对的是**同一视觉行**的兄弟。**只按 parent 分组
    是错的** —— 真实 deck 实测：一张封面里 eyebrow / title / subtitle / rule / meta
    是**竖排**的 5 个兄弟（高度 30.4 / 207.3 / 47.1 / 6 / 33），拿它们互比高度会报
    「title 比中位数高 528%」，而这三者根本不在同一行、不构成可比集合。

    并排同行的判据两条（缺一不可）：
      · 水平区间**不相交**（并排，不是套叠/包含 —— 背景光晕包住其它兄弟的情形由此排除）
      · 垂直区间重叠 ≥ overlap × min(两者高度)（同属一行）
    """
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
        return False
    # 水平重叠量：<=0 表示并排（中间有沟槽），>0 表示套叠/包含 ⇒ 非并排
    ovx = min(ax + aw, bx + bw) - max(ax, bx)
    if ovx > gap:
        return False
    oy = min(ay + ah, by + bh) - max(ay, by)
    return oy >= overlap * min(ah, bh)


def chk_sibling_consistency(ctx, params):
    """同一视觉行内兄弟元素尺寸偏离**组中位数**（plumb sibling/*-consistency）。

    ⚠️ v1.2.2：先把兄弟**分成「并排行」**再比（见 `_side_by_side`）。
    行的定义缺失时判 SKIP 而不是 PASS —— 「没有可比的并排行」是**未检测**，
    不是「检测过且没问题」。
    """
    nodes = _geom_nodes(ctx)
    if nodes is None:
        return "SKIP", "未提供渲染色（--geom）—— 未检测，不是通过"
    if not nodes:
        return "SKIP", "渲染色为空（nodes=[]）—— 未检测，不是通过"
    ratio = float(params.get("max_drift_ratio") or 0.02)
    min_group = int(params.get("min_group") or 3)
    overlap = float(params.get("row_overlap") or 0.8)
    by_parent: dict = {}
    for n in nodes:
        if not n.get("visible", True):
            continue
        r = _rect(n)
        if r is None:
            continue
        by_parent.setdefault(str(n.get("parent")), []).append((n.get("i"), r))
    drifts = []
    rows_seen = 0
    for _p, items in by_parent.items():
        if len(items) < min_group:
            continue
        rows: list = []
        for it in items:
            placed = False
            for row in rows:
                if all(_side_by_side(it[1], m[1], overlap=overlap) for m in row):
                    row.append(it)
                    placed = True
                    break
            if not placed:
                rows.append([it])
        for row in rows:
            if len(row) < min_group:
                continue
            rows_seen += 1
            hs = sorted(it[1][3] for it in row)
            med = hs[len(hs) // 2]
            if med <= 0:
                continue
            for i, (_x, _y, _w, h) in row:
                if abs(h - med) / med > ratio:
                    drifts.append((i, round(h, 1), round(med, 1), abs(h - med) / med))
    if drifts:
        head = "; ".join(f"#{i} h={h} vs 行中位 {m}（{d:.1%}）" for i, h, m, d in drifts[:4])
        return "FAIL", f"{len(drifts)} 个**并排行内**兄弟高度偏离行中位数 > {ratio:.0%}：{head}"
    if rows_seen == 0:
        return "SKIP", (f"未找到可比的并排行（组内 ≥ {min_group} 且水平区间不相交）"
                        f"—— 未检测，不是通过")
    return "PASS", f"{rows_seen} 个并排行内高度一致（容差 {ratio:.0%}，组内 ≥ {min_group}）"


def chk_baseline_rhythm(ctx, params):
    """文字基线落在垂直韵律网格上（plumb baseline/rhythm）。

    ⚠️ v1.2.2：**韵律网格必须被声明**，不再默认 8px。
    依据 plumb：`baseline/rhythm` 是**配置驱动**的规则（网格间距来自设计系统声明）。
    实测取证：ui库 的 `src/deck/themes/schema.json#spacing` 明确写着
    「34 套子键自由命名且数量庞大……本层不强行归并」—— **该设计系统根本没有声明
    baseline 网格**。此时硬套 8px 会把整套版式判成「7/7 文本节点全部离格」，
    那是**判据凭空发明了一个契约**，不是产物违约。⇒ 未声明则 SKIP（未检测）。
    """
    nodes = _geom_nodes(ctx)
    if nodes is None:
        return "SKIP", "未提供渲染色（--geom）—— 未检测，不是通过"
    _bp = params.get("baseline_px")
    if _bp in (None, "", 0, "0"):
        return "SKIP", ("未声明韵律网格（params.baseline_px 为空）—— **结构性不适用**"
                        "（该设计系统没有 baseline 网格，不是「等声明了再开」）；"
                        "要启用请用 override 提供该产物实际采用的行距网格")
    base = float(_bp)
    tol = float(params.get("tolerance_px") or 1)
    if base <= 0:
        return "SKIP", "baseline_px 非法（须为正数）"
    off = []
    total = 0
    for n in nodes:
        if not n.get("visible", True) or not (n.get("text") or "").strip():
            continue
        r = _rect(n)
        if r is None:
            continue
        total += 1
        y = r[1]
        d = abs(y - round(y / base) * base)
        if d > tol:
            off.append((n.get("i"), round(y, 1), round(d, 2)))
    if total == 0:
        return "SKIP", "渲染色中无可测文本节点"
    if off:
        head = "; ".join(f"#{i} y={y}（偏 {d}px）" for i, y, d in off[:4])
        return "FAIL", f"{len(off)}/{total} 个文本节点未落在 {base}px 韵律网格上（容差 {tol}px）：{head}"
    return "PASS", f"{total} 个文本节点全部落在 {base}px 韵律网格上"


# --------------------------------------------------------------------------
# 五、check 注册表 + 参数契约（v1.2.0 P2-2）
# --------------------------------------------------------------------------
CHECKS = {
    "color_count_max": ("machine", chk_color_count_max),
    "contrast_min": ("machine", chk_contrast_min),
    "font_scale_count_max": ("machine", chk_font_scale_count_max),
    "font_scale_ratio_range": ("machine", chk_font_scale_ratio_range),
    "motion_has_duration": ("machine", chk_motion_has_duration),
    "skeleton_no_radial": ("machine", chk_skeleton_no_radial),
    "palette_separation": ("machine", chk_palette_separation),
    "scale_conformance": ("machine", chk_scale_conformance),
    "duration_scale_conformance": ("machine", chk_duration_scale_conformance),
    "rhythm_ladder": ("machine", chk_rhythm_ladder),
    "accent_availability": ("machine", chk_accent_availability),
    "near_alignment": ("machine", chk_near_alignment),
    "sibling_consistency": ("machine", chk_sibling_consistency),
    "baseline_rhythm": ("machine", chk_baseline_rhythm),
    "accent_unique": ("spec", chk_accent_unique),
    "memory_point_count": ("spec", chk_memory_point_count),
    "primary_cta_count": ("spec", chk_primary_cta_count),
    "motion_types_present": ("spec", chk_motion_types_present),
    "motion_minimal_set": ("spec", chk_motion_minimal_set),
    "interactive_feedback_coverage": ("spec", chk_interactive_feedback_coverage),
    "shot_spec_present": ("spec", chk_shot_spec_present),
    "series_count_max": ("spec", chk_series_count_max),
}

# params 契约：键 → 允许的取值规格。未知键 / 类型错 / 枚举越界 ⇒ audit FAIL。
# 依据 plumb：`Plumb rejects unknown configuration fields`（配置严格性）。
# ⚠️ 规格用**字符串标记**而非 Python 类型元组 —— 后者会与「枚举白名单也是元组」撞车，
#    导致 `isinstance(allow, tuple)` 先命中、所有数值参数被误判为非法（实测踩中）。
_N = "num"    # 数值（bool 不算）
_L = "list"   # 列表
_S = "str"    # 字符串
PARAM_SPEC = {
    "color_count_max": {"max": _N},
    "contrast_min": {"role": ("body", "muted", "subtle", "accent"), "min": _N},
    "font_scale_count_max": {"max": _N},
    "font_scale_ratio_range": {
        "min": _N, "max": _N, "group_by": ("role-prefix", "none"), "min_group_size": _N,
    },
    "motion_has_duration": {"coverage": _N},
    "palette_separation": {"min_separation_de": _N, "layer_name_re": _S},
    "scale_conformance": {"kind": ("font-size",), "tolerance_px": _N, "scale": _L},
    "duration_scale_conformance": {"tolerance_ms": _N, "scale": _L},
    # v1.6.0：本条参数此前**只登记未消费**（悬空参数），现已真正生效（见 chk_skeleton_no_radial）
    "skeleton_no_radial": {"allowed_in_layers": _L},
    "rhythm_ladder": {"min_points": _N},
    "accent_availability": {"min_ratio": _N},
    "near_alignment": {"tolerance_px": _N, "min_cluster": _N, "noise_px": _N},
    "sibling_consistency": {"kind": ("height", "padding"), "max_drift_ratio": _N, "min_group": _N,
                            "row_overlap": _N},
    "baseline_rhythm": {"baseline_px": _N, "tolerance_px": _N},
    "accent_unique": {"expected": _N},
    # v1.7.0：`field` 与 `expected` 一样**未被实现读取**（属悬空参数，由 _dangling_params 报出）。
    # ⚠️ 但它**确实被判据 V2 声明**（V2 与 G8 复用同一 check，V2 的 params 写了 expected + field）
    #    ⇒ **不能从白名单里删** —— 删了 audit 立刻因「未知参数键 field」判 FAIL（本版实测踩中）。
    #    教训：同一 check 可被多条判据复用，判「到底有没有人声明」必须**逐条核**，不能看一条就下结论。
    "memory_point_count": {"expected": _N, "field": _S},
    "primary_cta_count": {"expected": _N},
    "motion_types_present": {"required": _L},
    "motion_minimal_set": {"elements": _L},
    "interactive_feedback_coverage": {"coverage": _N},
    "shot_spec_present": {"elements": _L},
    "series_count_max": {"max": _N},
}


def _param_ok(allow, v):
    """按规格校验单个参数值。返回 None 表示通过，否则返回错误说明。"""
    if allow == _N:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return f"应为数值（当前 {type(v).__name__}）"
        return None
    if allow == _L:
        return None if isinstance(v, list) else f"应为列表（当前 {type(v).__name__}）"
    if allow == _S:
        return None if isinstance(v, str) else f"应为字符串（当前 {type(v).__name__}）"
    if isinstance(allow, tuple):
        return None if v in allow else f"不在允许取值 {list(allow)}"
    return f"未定义的参数规格 {allow!r}"


def _applies(criterion: dict, product: str | None) -> bool:
    """消费 rubric 的 `applies_to`（v1.1.0 补丁 C）。

    未传 product ⇒ 不过滤（向后兼容 v1.0 行为）；判据未声明 applies_to ⇒ 视为适用全部。
    """
    if not product:
        return True
    ap = criterion.get("applies_to")
    if ap is None:
        return True
    if isinstance(ap, str):
        ap = [p.strip() for p in ap.split(",")]
    return product in ap


# --------------------------------------------------------------------------
# 六、产物级覆盖（v1.2.0 P2-1）
# --------------------------------------------------------------------------
def apply_overrides(criteria: list, overrides: list):
    """把产物级覆盖浅合并进判据。返回 (criteria', applied_log, problems)。

    规则：reason 必填且拒绝占位；未知键由 audit 负责报错，这里只做合并与留痕。
    """
    problems: list = []
    applied: list = []
    by_id = {}
    for o in overrides or []:
        if not isinstance(o, dict) or not o.get("id"):
            problems.append("覆盖条目必须是含 id 的对象")
            continue
        by_id[str(o["id"])] = o

    out = []
    for c in criteria:
        c2 = dict(c)
        cid = str(c.get("id"))
        o = by_id.get(cid)
        if o:
            reason = str(o.get("reason") or "").strip()
            if not reason:
                problems.append(f"{cid}: 覆盖缺 reason")
            elif reason.lower() in PLACEHOLDER_REASONS:
                problems.append(f"{cid}: 覆盖 reason 是占位文本（{reason}）—— 等于没写")
            keys = []
            if isinstance(o.get("params"), dict) and o["params"]:
                spec = PARAM_SPEC.get(c.get("check"), {})
                for pk, pv in o["params"].items():
                    if pk not in spec:
                        problems.append(
                            f"{cid}: 覆盖参数键 {pk} 不在 {c.get('check')} 的规格内"
                            f"（合法键 {sorted(spec)}）—— 会被静默忽略"
                        )
                        continue
                    why = _param_ok(spec[pk], pv)
                    if why:
                        problems.append(f"{cid}: 覆盖参数 {pk} {why}")
                merged = dict(c.get("params") or {})
                merged.update(o["params"])
                c2["params"] = merged
                keys.append("params")
            if "applies_to" in o:
                c2["applies_to"] = o["applies_to"]
                keys.append("applies_to")
            if not keys:
                problems.append(f"{cid}: 覆盖没带 params 也没带 applies_to —— 空覆盖")
            applied.append({"id": cid, "keys": keys, "reason": reason})
        out.append(c2)
    unknown = sorted(set(by_id) - {str(c.get("id")) for c in criteria})
    for u in unknown:
        problems.append(f"{u}: 覆盖指向不存在的判据")
    return out, applied, problems


# --------------------------------------------------------------------------
# 七、审计
# --------------------------------------------------------------------------
def _dangling_params(src_path=None) -> list:
    """AST 解析本模块，找出 `PARAM_SPEC` 声明了、但检查器**从未读取**的参数键。

    v1.7.0：v1.6.0 时这是一次性脚本（`tmp/v160/audit_params.py`），**发现即会过期**
    （下次改动无人重跑）。现挂进 `--audit` 常驻。

    判据：函数体内是否出现 `params.get(k)` / `params[k]`。这是**必要非充分**条件 ——
    读了参数也可能读错键，故本检查只负责**报出**，不冒充「判据正确」。

    返回 [(check_name, [未消费的键, ...]), ...]；默认读本文件，可传入副本用于阴性对照。
    """
    src = Path(src_path or __file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    out = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("chk_"):
            continue
        name = node.name[len("chk_"):]
        decl = set(PARAM_SPEC.get(name) or {})
        if not decl:
            continue
        read = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                f = n.func
                if (isinstance(f, ast.Attribute) and f.attr == "get"
                        and isinstance(f.value, ast.Name) and f.value.id == "params"
                        and n.args and isinstance(n.args[0], ast.Constant)
                        and isinstance(n.args[0].value, str)):
                    read.add(n.args[0].value)
            elif isinstance(n, ast.Subscript):
                if (isinstance(n.value, ast.Name) and n.value.id == "params"
                        and isinstance(n.slice, ast.Constant)
                        and isinstance(n.slice.value, str)):
                    read.add(n.slice.value)
        miss = sorted(decl - read)
        if miss:
            out.append((name, miss))
    return out


def audit_rubric(rubric: dict) -> int:
    """判据 ↔ 实现 一致性审计：
    ① check 有实现且类别匹配 ② applies_to 取值合法 ③ params 键/类型/枚举合法（v1.2.0 P2-2）
    """
    fails, ok, skips = [], 0, 0
    for c in rubric.get("criteria") or []:
        cid = c.get("id")
        judge = c.get("judgeability")
        name = c.get("check")
        if judge in ("manual", "external"):
            if name is not None:
                fails.append(f"{cid}: judgeability={judge} 但声明了 check={name}（应为 null）")
            else:
                skips += 1
            continue
        if name is None:
            fails.append(f"{cid}: judgeability={judge} 但 check 为 null")
            continue
        if name not in CHECKS:
            fails.append(f"{cid}: check={name} 在实现中不存在（文档与实现脱节）")
            continue
        kind, _ = CHECKS[name]
        if kind != judge:
            fails.append(f"{cid}: 判据声明 {judge}，实现类别为 {kind}（口径不一致）")
            continue
        ap = c.get("applies_to")
        if ap is not None:
            bad = [p for p in (ap if isinstance(ap, list) else [ap]) if p not in PRODUCTS]
            if bad:
                fails.append(f"{cid}: applies_to 含未知产物类型 {bad}（合法值 {list(PRODUCTS)}）")
                continue
        # v1.2.0 P2-2：params 合法性（未知键 / 类型错 / 枚举越界）
        spec = PARAM_SPEC.get(name, {})
        badp = []
        for k, v in (c.get("params") or {}).items():
            if k not in spec:
                badp.append(f"未知参数键 {k}（允许：{sorted(spec)}）")
                continue
            err = _param_ok(spec[k], v)
            if err:
                badp.append(f"{k}={v!r} {err}")
        if badp:
            fails.extend(f"{cid}: {m}" for m in badp)
            continue
        ok += 1
    total = len(rubric.get("criteria") or [])
    print("=== 判据 ↔ 实现 一致性审计 ===")
    for f in fails:
        print(f"[FAIL] {f}")
    print(f"=== 结果：一致 {ok}，人审点 {skips}，不一致 {len(fails)}，判据总数 {total} ===")
    # v1.7.0：悬空参数常驻检查。**单列一类、不并入上面的「一致」** —— 它们不是「通过」，
    # 而是「该判据声明的参数没人读」；措辞用 WARN，避免把「未实现」伪装成「合格」。
    try:
        dang = _dangling_params()
    except Exception as ex:  # 崩栈比跳过更坏 ⇒ 降级为显式 FAIL，绝不向上抛
        print(f"[FAIL] 悬空参数探针自身崩栈：{type(ex).__name__}: {ex}")
        return 1
    if dang:
        check2ids = {}
        for c in rubric.get("criteria") or []:
            if c.get("check"):
                check2ids.setdefault(c["check"], []).append(c.get("id"))
        nkeys = sum(len(k) for _, k in dang)
        print(f"=== 悬空参数：{nkeys} 个键 / {len(dang)} 个检查器"
              f"（**已声明未消费 —— 未实现 ≠ 通过**，不并入「一致」）===")
        for name, miss in dang:
            ids = ",".join(x for x in check2ids.get(name, []) if x)
            print(f"[WARN] {ids or '?'}/{name}: {miss} —— 检查器未读取该键")
    return 1 if fails else 0


# --------------------------------------------------------------------------
# 八、主流程
# --------------------------------------------------------------------------
def evaluate(rubric: dict, css_path, spec_path, product=None, geom_path=None, overrides=None) -> list:
    """返回 results：[(status, cid, name, detail)]，顺序与 rubric 一致。"""
    ctx = {"css": None, "spec": None, "geom": None}
    if css_path:
        ctx["css"] = extract_css(Path(css_path).read_text(encoding="utf-8"))
    if spec_path:
        ctx["spec"] = extract_spec(Path(spec_path).read_text(encoding="utf-8"))
    if geom_path:
        ctx["geom"] = extract_geom(geom_path)

    crit, _applied, _probs = apply_overrides(rubric.get("criteria") or [], overrides or [])

    results = []
    for c in crit:
        cid, name, judge = c.get("id"), c.get("name"), c.get("judgeability")
        if judge in ("manual", "external"):
            reason = (
                "人审点（机器不判定）"
                if judge == "manual"
                else "外部工具判定（本校验器不重复实现）"
            )
            results.append(("SKIP", cid, name, reason))
            continue
        if not _applies(c, product):
            results.append(
                ("SKIP", cid, name, f"不适用于 {product}（applies_to={c.get('applies_to')}）")
            )
            continue
        impl = CHECKS.get(c.get("check"))
        if impl is None or not callable(impl[1]):
            results.append(("SKIP", cid, name, f"未实现 check={c.get('check')}（未检测）"))
            continue
        # fail-closed 护栏：单个检查器内部异常**降级为 FAIL**，
        # 绝不向上抛——否则整个进程 rc=1、零 stdout，把前面已算出的结果一并吞掉
        # （2026-09-26 实证：chk_near_alignment 少写一对括号即触发此形态）。
        try:
            status, detail = impl[1](ctx, c.get("params") or {})
        except Exception as e:  # noqa: BLE001 —— 故意兜全部，诊断信息带类型
            status, detail = "FAIL", f"检查器内部异常（{type(e).__name__}: {e}）—— 视为未通过"
        results.append((status, cid, name, detail))
    return results


def _counts(results: list) -> dict:
    return {
        "pass": sum(1 for r in results if r[0] == "PASS"),
        "fail": sum(1 for r in results if r[0] == "FAIL"),
        "skip": sum(1 for r in results if r[0] == "SKIP"),
        "total": len(results),
    }


def _load_overrides(args) -> list:
    if args.override_file:
        return json.loads(Path(args.override_file).read_text(encoding="utf-8"))
    if args.override:
        return json.loads(args.override)
    return []


# --------------------------------------------------------------------------
# 八·五、v1.5.0：`--scale-from` —— 从**声明源**取刻度，让 G12/G13 可被常规跑批启用
# --------------------------------------------------------------------------
def _same_file(a, b) -> bool:
    """两路径是否指向同一文件（解析后比较；Windows 下忽略大小写）。"""
    try:
        pa, pb = Path(str(a)).resolve(), Path(str(b)).resolve()
        return os.path.normcase(str(pa)) == os.path.normcase(str(pb))
    except OSError:
        return False


def scale_from_sources(paths, css_path=None) -> tuple:
    """从**声明源** CSS 提取刻度并集。返回 `(info, problems)`。

    契约（与判据集 G12/G13 的 note 同源，写明理由而不是默默实现）：

      · **只取令牌声明**（`--*size-*` 字号 / `--*duration*` 时长）—— 不取 raw 使用值。
        取 raw 值等于把「被检的东西」当「标准」，判定就恒真了。
      · **同源剔除**：声明源若与被检文件是同一文件 ⇒ 剔除并**报出**；剔除后为空
        ⇒ 调用方**不得**合成 override（保持 SKIP）。这是「自证式刻度」护栏的
        **输入端**版本 —— 判据内部那道护栏只在「刻度集恰好等于令牌集」时触发，
        若有人在 CLI 上手工填同源刻度仍会被判 SKIP；这里提前把源挡掉，两道互为补充。
      · 声明源**不存在** ⇒ 记 problem（fail-closed，不静默忽略）。
    """
    sizes: set = set()
    durs: set = set()
    used: list = []
    dropped: list = []
    problems: list = []
    for raw in paths or []:
        txt = str(raw).strip()
        if not txt:
            continue
        p = Path(txt)
        if not p.is_file():
            problems.append(f"`--scale-from` 声明源不存在：{txt}")
            continue
        if css_path is not None and _same_file(p, css_path):
            dropped.append(txt)
            problems.append(f"`--scale-from` 的『{txt}』与被检文件**同源**，已剔除"
                            f"（同源刻度 ⇒ 判定恒真，不算通过）")
            continue
        try:
            d = extract_css(p.read_text(encoding="utf-8"))
        except OSError as exc:
            problems.append(f"`--scale-from` 声明源读取失败：{txt}（{type(exc).__name__}）")
            continue
        for v in (d.get("size_roles") or {}).values():
            sizes.add(round(float(v), 2))
        for ds in (d.get("duration_tokens") or {}).values():
            for x in ds:
                ms = _dur_to_ms(x)
                if ms is not None:
                    durs.add(round(ms, 3))
        used.append(txt)
    info = {
        "sources": used,
        "dropped_same_source": dropped,
        "sizes": sorted(sizes),
        "durations_ms": sorted(durs),
    }
    return info, problems


def build_scale_overrides(overrides, scale_from, css_path):
    """把 `--scale-from` 的刻度并集合成为 G12/G13 的 override。返回 `(ov, info, problems)`。

    **显式 override 优先**：调用方若已用 `--override` 给了 G12/G13 的非空 `scale`，
    本条不再插手（避免「命令行悄悄改了刻度集」）。刻度为空的一侧**不合成** override
    ⇒ 该判据保持 SKIP（未声明刻度集），绝不因启用本开关而变成恒真 PASS。
    """
    if not scale_from:
        return overrides, None, []
    info, problems = scale_from_sources(scale_from, css_path)
    ov = list(overrides or [])
    have = set()
    for o in ov:
        if isinstance(o, dict) and (o.get("params") or {}).get("scale"):
            have.add(str(o.get("id")))
    if info["sizes"] and "G12" not in have:
        ov.append({"id": "G12", "params": {"scale": info["sizes"]},
                   "reason": f"--scale-from：声明源 {len(info['sources'])} 份的 --*-size-* 令牌并集"
                             f"（{len(info['sizes'])} 档）"})
    if info["durations_ms"] and "G13" not in have:
        ov.append({"id": "G13", "params": {"scale": info["durations_ms"]},
                   "reason": f"--scale-from：声明源 {len(info['sources'])} 份的 --*-duration-* 令牌并集"
                             f"（{len(info['durations_ms'])} 档）"})
    return ov, info, problems


def run(rubric: dict, css_path, spec_path, product=None, as_json=False,
        geom_path=None, overrides=None, scale_from=None) -> int:
    overrides, sf_info, sf_probs = build_scale_overrides(overrides, scale_from, css_path)
    results = evaluate(rubric, css_path, spec_path, product, geom_path, overrides)
    c = _counts(results)
    _crit, applied, probs = apply_overrides(rubric.get("criteria") or [], overrides or [])
    probs = list(probs) + list(sf_probs)
    _cssdata = extract_css(Path(css_path).read_text(encoding="utf-8")) if css_path else {}
    skipped = _cssdata.get("skipped_values") or []
    unresolved = _cssdata.get("unresolved_sizes") or []   # v1.3.0：相对单位，无绝对值

    if as_json:
        print(json.dumps({
            "tool": "check_aesthetics.py",
            "version": VERSION,
            "css": str(css_path) if css_path else None,
            "spec": str(spec_path) if spec_path else None,
            "geom": str(geom_path) if geom_path else None,
            "product": product,
            "overrides_applied": applied,
            "override_problems": probs,
            "scale_from": sf_info,
            "skipped_values": skipped,
            "unresolved_sizes": unresolved,
            **c,
            "results": [
                {"id": r[1], "name": r[2], "status": r[0], "detail": r[3]} for r in results
            ],
        }, ensure_ascii=False, indent=2))
        return 1 if (c["fail"] or probs) else 0

    width = max((len(str(r[1])) for r in results), default=2)
    for status, cid, name, detail in results:
        tag = {"PASS": "[ OK ]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
        print(f"{tag} {str(cid).ljust(width)} {name} — {detail}")
    if probs:
        for p in probs:
            print(f"[FAIL] 覆盖 — {p}")
    if skipped:
        print(f"[NOTE] 取数跳过 {len(skipped)} 个不可解析值（未静默丢弃）：{skipped[:3]}")
    if unresolved:
        print(f"[NOTE] 取数跳过 {len(unresolved)} 处**相对字号**（em 无绝对值，未冒充像素）："
              f"{unresolved[:3]}")
    for a in applied:
        print(f"[NOTE] 覆盖 {a['id']} —— 改了 {a['keys']}，理由：{a['reason'][:60]}")
    if sf_info:
        print(f"[NOTE] 刻度源 --- {len(sf_info['sources'])} 份声明源 → 字号 "
              f"{len(sf_info['sizes'])} 档／时长 {len(sf_info['durations_ms'])} 档"
              + (f"；同源剔除 {len(sf_info['dropped_same_source'])} 份"
                 if sf_info["dropped_same_source"] else ""))

    print(
        f"=== 结果：通过 {c['pass']}/{c['total']}，FAIL={c['fail']}，SKIP={c['skip']}"
        f"（其中 SKIP 为「未检测 / 人审点」，不等于通过）==="
    )
    return 1 if (c["fail"] or probs) else 0


# --------------------------------------------------------------------------
# 九、批量复算：一次跑一组产物，出矩阵 + 逐判据统计
# --------------------------------------------------------------------------
_TAG = {"PASS": "OK", "FAIL": "XX", "SKIP": "--"}


def _collect_targets(pattern: str) -> list:
    p = Path(pattern)
    if p.is_dir():
        return sorted(p.glob("*.css"))
    return sorted(Path(p.parent).glob(p.name))


def batch(rubric: dict, pattern: str, product=None, as_json=False, csv_path=None,
          overrides=None, scale_from=None) -> int:
    files = _collect_targets(pattern)
    if not files:
        print(f"[FAIL] --batch 未匹配到任何 .css：{pattern}", file=sys.stderr)
        return 2
    crit, _applied, probs = apply_overrides(rubric.get("criteria") or [], overrides or [])
    probs = list(probs)
    rows = []
    sf_infos: list = []
    for f in files:
        # v1.5.0：`--scale-from` 逐文件合成 —— 同源剔除是**按被检文件**判的，
        #   批里每个产物各用自己的声明源，不能一次算好共用。
        ov, sfi, sfp = build_scale_overrides(overrides, scale_from, f)
        probs.extend(sfp)
        if sfi:
            sf_infos.append({"file": str(f), **sfi})
        res = evaluate(rubric, f, None, product, None, ov)
        rows.append((f, res, _counts(res)))

    cols = [c.get("id") for c in crit if c.get("judgeability") == "machine"]
    labelw = max([len(f.name) for f, _, _ in rows] + [6])

    if as_json:
        print(json.dumps({
            "tool": "check_aesthetics.py",
            "version": VERSION,
            "product": product,
            "columns": cols,
            "override_problems": probs,
            "scale_from": sf_infos,
            "targets": [
                {
                    "file": str(f),
                    "name": f.name,
                    **_counts(res),
                    "results": [
                        {"id": r[1], "name": r[2], "status": r[0], "detail": r[3]} for r in res
                    ],
                }
                for f, res, _ in rows
            ],
        }, ensure_ascii=False, indent=2))
        return 1 if (any(c["fail"] for _, _, c in rows) or probs) else 0

    print(f"=== 批量复算：{len(rows)} 个产物 · product={product or '（未指定，不过滤）'} ===")
    for p in probs:
        print(f"[FAIL] 覆盖 — {p}")
    print(f"{'产物'.ljust(labelw)}  PASS FAIL SKIP | " + " ".join(c.ljust(3) for c in cols))
    for f, res, c in rows:
        st = {r[1]: _TAG[r[0]] for r in res}
        print(
            f"{f.name.ljust(labelw)}  {c['pass']:4d} {c['fail']:4d} {c['skip']:4d} | "
            + " ".join(st.get(cid, " ? ").ljust(3) for cid in cols)
        )

    # ⚠️ v1.2.2：这里原先把状态写死成字面量 `FAIL`，于是「0 个 FAIL」的判据
    #    （G3/G4/G5…）也被打印成 `FAIL` —— 扫一眼就会读成「这些判据失败了」。
    #    **汇总语必须由计数器生成**，不许有会撒谎的字面量。
    print("--- 逐判据统计（失败数 / 参与判定数；参与 0 = 未检测或本产物类型不适用）---")
    for cid in cols:
        nf = sum(1 for _, res, _ in rows if any(r[1] == cid and r[0] == "FAIL" for r in res))
        ne = sum(1 for _, res, _ in rows if any(r[1] == cid and r[0] in ("PASS", "FAIL") for r in res))
        name = next((c.get("name") for c in crit if c.get("id") == cid), cid)
        tag = "XX" if nf else ("OK" if ne else "--")
        print(f"  [{tag}] {cid.ljust(4)} {str(name).ljust(24)} 失败 {nf:3d} / 参与 {ne}")

    tot_fail = sum(c["fail"] for _, _, c in rows)
    n_bad = sum(1 for _, _, c in rows if c["fail"])
    print(
        f"=== 汇总：产物 {len(rows)}，FAIL 合计 {tot_fail}，"
        f"有 FAIL 的产物 {n_bad}；图例 OK=通过 XX=FAIL --=SKIP（未检测/人审/不适用）==="
    )

    if csv_path:
        import csv as _csv

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
            w = _csv.writer(fh)
            w.writerow(["file"] + cols + ["PASS", "FAIL", "SKIP"])
            for f, res, c in rows:
                st = {r[1]: _TAG[r[0]] for r in res}
                w.writerow(
                    [f.name] + [st.get(cid, "?") for cid in cols] + [c["pass"], c["fail"], c["skip"]]
                )
        print(f"（CSV 已写：{csv_path}）")

    return 1 if (tot_fail or probs) else 0


# --------------------------------------------------------------------------
# 十、自检
# --------------------------------------------------------------------------
# CIEDE2000 的官方测试对（Sharma、Wu、Dalal 2005，表 1 的前 6 组）
_DELTAE_CASES = [
    ((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
    ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
    ((50.0, 2.8361, -74.0200), (50.0, 0.0, -82.7485), 3.4412),
    ((50.0, -1.3802, -84.2814), (50.0, 0.0, -82.7485), 1.0000),
    ((50.0, -1.1848, -84.8006), (50.0, 0.0, -82.7485), 1.0000),
    ((50.0, -0.9009, -85.5211), (50.0, 0.0, -82.7485), 1.0000),
    ((50.0, 0.0, 0.0), (50.0, -1.0, 2.0), 2.3669),
    ((50.0, 0.0, 0.0), (50.0, 1.0, -2.0), 2.3669),
    ((50.0, 2.49, -0.001), (50.0, -2.49, 0.0009), 7.1792),
    ((50.0, 2.49, -0.001), (50.0, -2.49, 0.001), 7.1792),
]


def self_test(rubric_path) -> int:
    text = Path(rubric_path).read_text(encoding="utf-8")
    data = mini_yaml_load(text)
    ids = [c.get("id") for c in (data.get("criteria") or [])]
    raw_ids = re.findall(r"^\s*-\s*id:\s*(\S+)", text, re.M)
    print("=== 解析器自检 ===")
    print(f"顶层键：{sorted(data.keys())}")
    print(f"criteria 条数：{len(ids)}（原文 id 行 {len(raw_ids)}）")
    rc = 0
    if len(ids) != len(raw_ids):
        print("[FAIL] 解析条数与原文 id 行数不一致")
        rc = 1
    elif not ids or any(i is None for i in ids):
        print("[FAIL] 存在未解析出的 id")
        rc = 1
    else:
        print(f"id 序列：{ids}")
        print("[ OK ] 解析器自检通过")

    print("=== CIEDE2000 自检（Sharma 等 2005 官方测试对）===")
    bad = 0
    for lab1, lab2, exp in _DELTAE_CASES:
        got = round(delta_e00(lab1, lab2), 4)
        if abs(got - exp) > 0.0001:
            print(f"[FAIL] ΔE00{lab1} vs {lab2} = {got}（期望 {exp}）")
            bad += 1
    if bad:
        print(f"[FAIL] {bad}/{len(_DELTAE_CASES)} 组 CIEDE2000 测试对不符")
        rc = 1
    else:
        print(f"[ OK ] {len(_DELTAE_CASES)}/{len(_DELTAE_CASES)} 组 CIEDE2000 测试对全部符合")

    print("=== APCA 自检（极性方向）===")
    lc1 = apca_lc((0, 0, 0), (255, 255, 255))
    lc2 = apca_lc((255, 255, 255), (0, 0, 0))
    ok = lc1 > 100 and -110 < lc2 < -100
    print(f"{'[ OK ]' if ok else '[FAIL]'} 黑字白底 Lc={lc1:.1f}（应 ≈106）；白字黑底 Lc={lc2:.1f}（应 ≈-108）")
    if not ok:
        rc = 1

    # ---- v1.2.1 起：R 组几何判据实跑（v1.2.0 的自检**完全没覆盖** --geom 路径）----
    # v1.2.2：夹具改为**真实的并排几何** —— 旧夹具是三个完全重叠的矩形，
    #         在「同一视觉行」语义下本就不构成可比集合（夹具自己也得站得住）。
    print("=== R 组几何判据自检（无geom⇒SKIP；干净⇒PASS；脏⇒FAIL；未声明⇒SKIP）===")
    _cards = [
        {"i": 0, "parent": None, "tag": "div", "rect": {"x": 0, "y": 0, "w": 1200, "h": 600}, "visible": True},
        {"i": 1, "parent": "0", "tag": "div", "rect": {"x": 8, "y": 96, "w": 300, "h": 200}, "visible": True},
        {"i": 2, "parent": "0", "tag": "div", "rect": {"x": 328, "y": 96, "w": 300, "h": 200}, "visible": True},
        {"i": 3, "parent": "0", "tag": "div", "rect": {"x": 648, "y": 96, "w": 300, "h": 200}, "visible": True},
        {"i": 4, "parent": "1", "tag": "p", "text": "标题", "rect": {"x": 16, "y": 104, "w": 100, "h": 24}, "visible": True},
    ]

    def _g(nodes):
        return {"version": "2", "source": "selftest", "viewport": {"w": 1280, "h": 900}, "nodes": nodes}

    def _mut(fn):
        ns = json.loads(json.dumps(_cards))
        fn(ns)
        return _g(ns)

    _ok = _g(_cards)
    _near = _mut(lambda ns: ns[3]["rect"].update({"y": 97.2}))   # 近乎对齐：真差 1.2px
    _noise = _mut(lambda ns: ns[3]["rect"].update({"y": 96.2}))  # 亚像素噪声：差 0.2px
    _sub = _mut(lambda ns: ns[2]["rect"].update({"h": 260}))     # 并排行内尺寸漂移 30%
    _base = _mut(lambda ns: ns[4]["rect"].update({"y": 108}))    # 基线离格 4px（8px 网格）
    _T = [
        ("near_alignment/无geom", chk_near_alignment, {}, None, "SKIP"),
        ("near_alignment/干净", chk_near_alignment, {}, _ok, "PASS"),
        ("near_alignment/近乎对齐1.2px", chk_near_alignment, {}, _near, "FAIL"),
        ("near_alignment/亚像素噪声0.2px必须忽略", chk_near_alignment, {}, _noise, "PASS"),
        ("near_alignment/空节点集⇒SKIP", chk_near_alignment, {}, _g([]), "SKIP"),
        ("near_alignment/地板≥容差⇒SKIP", chk_near_alignment, {"noise_px": 3}, _near, "SKIP"),
        ("sibling_consistency/干净", chk_sibling_consistency, {}, _ok, "PASS"),
        ("sibling_consistency/并行内漂移30%", chk_sibling_consistency, {}, _sub, "FAIL"),
        ("sibling_consistency/无可比并排行⇒SKIP",
         chk_sibling_consistency, {}, _g([_cards[0], _cards[4]]), "SKIP"),
        ("baseline_rhythm/未声明网格⇒SKIP", chk_baseline_rhythm, {}, _ok, "SKIP"),
        ("baseline_rhythm/声明8px且干净", chk_baseline_rhythm, {"baseline_px": 8}, _ok, "PASS"),
        ("baseline_rhythm/声明8px且离格4px", chk_baseline_rhythm, {"baseline_px": 8}, _base, "FAIL"),
    ]
    for _nm, _fn, _pp, _gg, _want in _T:
        try:
            _got, _det = _fn({"geom": _gg}, dict(_pp))
        except Exception as e:  # noqa: BLE001 —— 自检的作用就是让这类崩栈**当场现形**
            print(f"[FAIL] {_nm} 抛异常：{type(e).__name__}: {e}")
            rc = 1
            continue
        if _got == _want:
            print(f"[ OK ] {_nm}: {_got}")
        else:
            print(f"[FAIL] {_nm}: 实得 {_got}（期望 {_want}） — {_det}")
            rc = 1

    # ---- v1.3.0：取数自检 —— `em` 无绝对值，不得折成像素 ----
    # v1.2.2 的教训：自检没覆盖的路径就是能漏到外部的那条。故新增代码路径必须进自检。
    print("=== 取数自检：单位语义（em 不可折 / rem·pt 可折）===")
    _u = extract_css(
        ":root{--deck-size-x:0.94em;--deck-size-y:2rem}"
        ".a{font-size:1em}.b{font-size:24pt}.c{font-size:34px}"
    )
    _u_ok = (
        34.0 in _u["sizes"]                    # px 绝对
        and 32.0 in _u["sizes"]                # 2rem → 32（基准 16 已声明）
        and round(24 * 96 / 72, 2) in _u["sizes"]   # 24pt → 32
        and 15.04 not in _u["sizes"]           # 0.94em **不得**被折成 15.04
        and 16.0 not in _u["sizes"]            # 1em **不得**被折成 16
        and len(_u["unresolved_sizes"]) == 2   # 两处 em 被登记（不静默丢弃）
        and _u["size_roles"] == {"--deck-size-y": 32.0}
    )
    print(f"{'[ OK ]' if _u_ok else '[FAIL]'} sizes={sorted(set(_u['sizes']))} "
          f"unresolved={[x['raw'] for x in _u['unresolved_sizes']]} "
          f"size_roles={_u['size_roles']}（期望 sizes 含 34/32，不含 15.04/16）")
    if not _u_ok:
        rc = 1

    # ---- v1.3.0：末条声明省略分号 ⇒ 不得静默丢项（CSS 允许块内最后一条省分号）----
    _ns = extract_css(":root{--deck-size-a:16px;--deck-size-b:20px;"
                      "--deck-motion-x-duration:0.8s}")
    _ns_ok = (
        len(_ns["size_roles"]) == 2
        and _ns["duration_tokens"].get("--deck-motion-x-duration") == ["0.8s"]
    )
    print(f"{'[ OK ]' if _ns_ok else '[FAIL]'} 末条声明省分号仍取到："
          f"size_roles={_ns['size_roles']} duration_tokens={_ns['duration_tokens']}")
    if not _ns_ok:
        rc = 1

    # ---- v1.3.0：G12/G13 自证式刻度护栏 + 0ms 不参与 ----
    print("=== 刻度一致性自检（未声明⇒SKIP；自证⇒SKIP；独立声明⇒真判）===")
    _own = extract_css(":root{--deck-size-a:16px;--deck-size-b:20px}")
    _indep = extract_css(".x{font-size:13px}.y{font-size:16px}")
    _fit = extract_css(".x{font-size:16px}.y{font-size:20px}")
    _rel = extract_css(".x{font-size:1em}")
    _dur_own = extract_css(":root{--deck-motion-a-duration:0.5s;--deck-motion-b-duration:0.8s}")
    _dur_bad = extract_css(".x{transition:opacity 137ms ease}.y{animation-delay:0s}")
    # v1.5.0 新增夹具：0ms（真 duration）、delay 分家、简写取首个时间值、stagger 令牌
    _dur_zero = extract_css(".x{transition:opacity 0s ease;transition-duration:137ms}")
    _dur_delay = extract_css(".x{animation-delay:0.3s}.y{transition:opacity 220ms}")
    _dur_sh = extract_css(".x{transition:width 220ms cubic-bezier(0.16,1,0.3,1) 500ms}")
    _dur_tok = extract_css(":root{--deck-motion-stagger:0 / 0.08s / 0.3s;"
                           "--deck-motion-slide-duration:0.8s}")
    _T2 = [
        ("scale/未声明刻度⇒SKIP", chk_scale_conformance, {}, _indep, "SKIP"),
        ("scale/自证式刻度⇒SKIP", chk_scale_conformance, {"scale": [16, 20]}, _own, "SKIP"),
        ("scale/独立声明+离格137⇒FAIL",
         chk_scale_conformance, {"scale": [16, 20, 26]}, _indep, "FAIL"),
        ("scale/独立声明+落格⇒PASS", chk_scale_conformance, {"scale": [16, 20, 26]}, _fit, "PASS"),
        ("scale/全为相对单位⇒SKIP", chk_scale_conformance, {"scale": [16, 20]}, _rel, "SKIP"),
        ("duration/自证式刻度⇒SKIP",
         chk_duration_scale_conformance, {"scale": [500, 800]}, _dur_own, "SKIP"),
        ("duration/独立声明+137ms离格⇒FAIL",
         chk_duration_scale_conformance, {"scale": [500, 800]}, _dur_bad, "FAIL"),
    ]
    for _nm, _fn, _pp, _cc, _want in _T2:
        try:
            _got, _det = _fn({"css": _cc}, dict(_pp))
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {_nm} 抛异常：{type(e).__name__}: {e}")
            rc = 1
            continue
        if _got == _want:
            print(f"[ OK ] {_nm}: {_got}")
        else:
            print(f"[FAIL] {_nm}: 实得 {_got}（期望 {_want}） — {_det}")
            rc = 1
    # 0ms 不参与：真·0 duration 不得出现在离格清单里，但**要被显式报出**
    # ⚠️ v1.5.0：原夹具用 `animation-delay:0s` 触发这一分支 —— delay 分家后它
    #   已不进 durations，改由 `transition: opacity 0s`（真 duration 语义）验证。
    _d0, _det0 = chk_duration_scale_conformance(
        {"css": _dur_zero}, {"scale": [500, 800]})
    _z_ok = _d0 == "FAIL" and "137.0" in _det0 and "0ms ×1" in _det0
    print(f"{'[ OK ]' if _z_ok else '[FAIL]'} duration/0ms 不参与判定且被显式报出 — {_det0}")
    if not _z_ok:
        rc = 1

    # ---- v1.5.0：delay/stagger 与 duration **分家**（取数层 + 判定层）----
    # 取数层：delay 语义不得进 durations，且必须被登记（不静默丢弃）；
    #   简写 `transition: <dur> <ease> <delay>` 只取首个时间值为 duration。
    _dx_ok = (_dur_delay["durations"] == ["220ms"] and _dur_delay["delay_excluded"] == ["0.3s"]
              and _dur_sh["durations"] == ["220ms"] and _dur_sh["delay_excluded"] == ["500ms"]
              and _dur_bad["durations"] == ["137ms"] and _dur_bad["delay_excluded"] == ["0s"])
    print(f"{'[ OK ]' if _dx_ok else '[FAIL]'} duration/delay 分家（取数层）— "
          f"delay:{_dur_delay['durations']}/{_dur_delay['delay_excluded']} "
          f"简写:{_dur_sh['durations']}/{_dur_sh['delay_excluded']}")
    if not _dx_ok:
        rc = 1

    # 令牌层：stagger 令牌不得混进 duration_tokens（否则与被检侧 delay 同源 ⇒ 恒真）
    _dt_ok = (list(_dur_tok["duration_tokens"]) == ["--deck-motion-slide-duration"]
              and list(_dur_tok["delay_tokens"]) == ["--deck-motion-stagger"]
              and _dur_tok["durations"] == ["0.8s"])
    print(f"{'[ OK ]' if _dt_ok else '[FAIL]'} duration/stagger 令牌另立一门 — "
          f"dur_tok={list(_dur_tok['duration_tokens'])} delay_tok={list(_dur_tok['delay_tokens'])}")
    if not _dt_ok:
        rc = 1

    # 判定层：delay 被排除，但**真离格的 duration 照样 FAIL**（不是放宽）
    _d1, _det1 = chk_duration_scale_conformance({"css": _dur_bad}, {"scale": [500, 800]})
    _d2, _det2 = chk_duration_scale_conformance({"css": _dur_delay}, {"scale": [220]})
    _d3, _det3 = chk_duration_scale_conformance({"css": _dur_sh}, {"scale": [220]})
    _dd_ok = (_d1 == "FAIL" and "137.0" in _det1
              and _d2 == "PASS" and "1 个 delay/stagger 语义值不参与判定" in _det2
              and _d3 == "PASS" and "1 个 delay/stagger 语义值不参与判定" in _det3)
    print(f"{'[ OK ]' if _dd_ok else '[FAIL]'} duration/delay 分家（判定层）— "
          f"离格仍FAIL:{_d1} / 排除后PASS:{_d2}")
    if not _dd_ok:
        rc = 1

    # ---- v1.5.0：`--scale-from` 声明刻度源 + 同源剔除（fail-closed）----
    print("=== --scale-from 自检（声明源取刻度 / 同源剔除 / 缺失即报错）===")
    _sf_fd, _sf_tok = tempfile.mkstemp(suffix=".css")
    os.close(_sf_fd)
    Path(_sf_tok).write_text(
        ":root{--ui-font-size-sm:13px;--ui-font-size-md:14px;"
        "--ui-duration-fast:140ms;--ui-duration-normal:220ms;"
        "--deck-motion-stagger:0 / 0.08s}", encoding="utf-8")
    try:
        _i1, _p1 = scale_from_sources([_sf_tok])
        _sf_ok = (_i1["sizes"] == [13.0, 14.0] and _i1["durations_ms"] == [140.0, 220.0]
                  and not _p1 and _i1["sources"] == [_sf_tok])
        print(f"{'[ OK ]' if _sf_ok else '[FAIL]'} scale-from/声明源取刻度 — "
              f"字号 {_i1['sizes']} 时长 {_i1['durations_ms']}（stagger 不入刻度）")
        if not _sf_ok:
            rc = 1

        _i2, _p2 = scale_from_sources([_sf_tok], css_path=_sf_tok)
        _sf_same = (not _i2["sources"] and _i2["dropped_same_source"] == [_sf_tok] and _p2)
        print(f"{'[ OK ]' if _sf_same else '[FAIL]'} scale-from/同源剔除并报出 — "
              f"dropped={len(_i2['dropped_same_source'])} problems={len(_p2)}")
        if not _sf_same:
            rc = 1

        _i3, _p3 = scale_from_sources([_sf_tok + ".nope"])
        _sf_miss = (not _i3["sources"] and _p3)
        print(f"{'[ OK ]' if _sf_miss else '[FAIL]'} scale-from/源缺失即 fail-closed — problems={len(_p3)}")
        if not _sf_miss:
            rc = 1

        # 显式 override 优先：已给的 G12 不被命令行覆盖，未给的 G13 照常合成
        _ov, _i4, _p4 = build_scale_overrides(
            [{"id": "G12", "params": {"scale": [16.0]}}], [_sf_tok], None)
        _sf_pri = (len(_ov) == 2 and _ov[0]["params"]["scale"] == [16.0]
                   and _ov[1]["id"] == "G13")
        print(f"{'[ OK ]' if _sf_pri else '[FAIL]'} scale-from/显式 override 优先 — "
              f"{[(o['id'], o['params']['scale']) for o in _ov]}")
        if not _sf_pri:
            rc = 1

        # 剔除后为空 ⇒ 不得合成任何 override（保持 SKIP，绝不变成恒真 PASS）
        _ov2, _i5, _p5 = build_scale_overrides([], [_sf_tok], _sf_tok)
        _sf_empty = (_ov2 == [] and _p5)
        print(f"{'[ OK ]' if _sf_empty else '[FAIL]'} scale-from/全同源 ⇒ 不合成 override — "
              f"ov={len(_ov2)} problems={len(_p5)}")
        if not _sf_empty:
            rc = 1
    finally:
        try:
            os.remove(_sf_tok)
        except OSError:
            pass

    # ---- v1.6.0：G16 韵律阶梯自检 ----
    print("=== 韵律阶梯自检（G16：非递减；**不要求步长均匀**）===")

    def _css_ctx(css_text):
        _fd2, _p = tempfile.mkstemp(suffix=".css")
        os.close(_fd2)
        Path(_p).write_text(css_text, encoding="utf-8")
        try:
            return {"css": extract_css(Path(_p).read_text(encoding="utf-8"))}
        finally:
            try:
                os.remove(_p)
            except OSError:
                pass

    _lad_cases = [
        ("令牌阶梯乱序 ⇒ FAIL",
         ":root{--deck-motion-stagger: 0 / 0.3s / 0.08s / 0.44s;}", "FAIL"),
        ("令牌阶梯=真实语料的加速步长 ⇒ PASS（**不要求等步长**）",
         ":root{--deck-motion-stagger: 0 / 0.08s / 0.18s / 0.3s / 0.44s / 0.6s / 0.78s;}", "PASS"),
        ("应用侧 nth-child 回退 ⇒ FAIL",
         ".a:nth-child(1){animation-delay:0s;}\n.a:nth-child(2){animation-delay:0.6s;}\n"
         ".a:nth-child(3){animation-delay:0.3s;}\n", "FAIL"),
        ("应用侧加速 + 末尾饱和封顶 ⇒ PASS（非递减，非严格递增）",
         ".a:nth-child(1){animation-delay:0s;}\n.a:nth-child(2){animation-delay:0.08s;}\n"
         ".a:nth-child(3){animation-delay:0.3s;}\n.a:nth-child(n+4){animation-delay:0.3s;}\n", "PASS"),
        ("仅单点 ⇒ SKIP（无对象，不是通过）",
         ".a:nth-child(1){animation-delay:0s;}\n", "SKIP"),
        ("裸 0 首项不得被静默丢掉（0/0.1s 两点 ⇒ 参与判定）",
         ":root{--deck-motion-stagger: 0.2s / 0.1s;}", "FAIL"),
    ]
    for _cn, _css, _exp in _lad_cases:
        _st, _det = chk_rhythm_ladder(_css_ctx(_css), {"min_points": 2})
        _ok = (_st == _exp)
        print(f"{'[ OK ]' if _ok else '[FAIL]'} {_cn} — {_st}")
        if not _ok:
            print(f"        实际 detail：{_det}")
            rc = 1

    # ---- v1.6.0：M1 空集语义自检 ----
    print("=== M1 空集语义自检（无动效声明 ≠ 有动效却没写秒数）===")
    _m_cases = [
        ("既无动效声明也无时长令牌（layouts.css 的形状）⇒ SKIP", ".x{background:#fff;}", "SKIP"),
        ("transition: none 属显式无动效 ⇒ SKIP", ".x{transition:none;}\n.y{transition:none !important;}", "SKIP"),
        ("无动效声明但声明了时长令牌（21 套主题的形状）⇒ PASS", ":root{--deck-motion-slide-duration: 0.8s;}", "PASS"),
        ("声明了动效却没写时长 ⇒ FAIL", ".x{transition:opacity;}\n.y{animation:slide;}", "FAIL"),
        ("声明且带时长 ⇒ PASS", ".x{transition:opacity 220ms;}\n.y{animation:slide var(--d, 0.5s);}", "PASS"),
    ]
    for _cn, _css, _exp in _m_cases:
        _st, _det = chk_motion_has_duration(_css_ctx(_css), {"coverage": 1.0})
        _ok = (_st == _exp)
        print(f"{'[ OK ]' if _ok else '[FAIL]'} {_cn} — {_st}")
        if not _ok:
            print(f"        实际 detail：{_det}")
            rc = 1
    # `coverage` 参数**真正生效**（此前只声明未消费 —— 悬空参数，与 W2 同族）
    _cov_css = ".x{transition:opacity 220ms;}\n.y{animation:slide;}"
    _s1, _ = chk_motion_has_duration(_css_ctx(_cov_css), {"coverage": 1.0})
    _s2, _ = chk_motion_has_duration(_css_ctx(_cov_css), {"coverage": 0.5})
    _cov_ok = (_s1 == "FAIL" and _s2 == "PASS")
    print(f"{'[ OK ]' if _cov_ok else '[FAIL]'} M1/coverage 真正生效 — cov=1.0⇒{_s1}，cov=0.5⇒{_s2}")
    if not _cov_ok:
        rc = 1

    # ---- v1.6.0：W2 层参数自检（allowed_in_layers 从「悬空」到「真正生效」）----
    print("=== W2 层参数自检（allowed_in_layers 生效；**缺声明即 FAIL**）===")
    _w_cases = [
        ("无 radial ⇒ PASS", ".x{background:#fff;}", "PASS"),
        ("radial 未声明层 ⇒ FAIL（fail-closed，不得默认放行）",
         ".x{background:radial-gradient(circle,#fff,#000);}", "FAIL"),
        ("radial 声明为氛围层 ⇒ PASS", ".x{--ui-layer: 氛围层;background:radial-gradient(circle,#fff,#000);}", "PASS"),
        ("radial 声明为骨架层 ⇒ FAIL（不在白名单）",
         ".x{--ui-layer: 骨架层;background:radial-gradient(circle,#fff,#000);}", "FAIL"),
        ("一合规一违规 ⇒ FAIL 且**逐块可指认**",
         ".a{--ui-layer: 氛围层;background:radial-gradient(circle,#fff,#000);}\n"
         ".b{background:radial-gradient(circle,#fff,#000);}", "FAIL"),
    ]
    for _cn, _css, _exp in _w_cases:
        _st, _det = chk_skeleton_no_radial(_css_ctx(_css), {"allowed_in_layers": ["氛围层"]})
        _ok = (_st == _exp)
        print(f"{'[ OK ]' if _ok else '[FAIL]'} {_cn} — {_st}")
        if not _ok:
            print(f"        实际 detail：{_det}")
            rc = 1

    # ---- v1.2.1：fail-closed 护栏（某检查器内部异常 ⇒ 降级 FAIL，不得吞掉其它结果）----
    print("=== fail-closed 护栏自检（检查器异常 ⇒ FAIL，其余判据照常产出）===")

    def _boom(_ctx, _params):
        raise ValueError("故意炸")

    CHECKS["_selftest_boom"] = ("machine", _boom)
    _fake = {"criteria": [
        {"id": "Z1", "name": "前置", "judgeability": "machine", "check": "color_count_max",
         "params": {"max": 99}},
        {"id": "Z2", "name": "炸弹", "judgeability": "machine", "check": "_selftest_boom", "params": {}},
        {"id": "Z3", "name": "后置", "judgeability": "machine", "check": "color_count_max",
         "params": {"max": 99}},
    ]}
    _fd, _tmp_css = tempfile.mkstemp(suffix=".css")
    os.close(_fd)
    Path(_tmp_css).write_text(":root{--deck-bg:#FFFFFF;--deck-fg:#111111;}", encoding="utf-8")
    try:
        _zres = evaluate(_fake, _tmp_css, None, None, None, None)
    finally:
        CHECKS.pop("_selftest_boom", None)
        try:
            os.remove(_tmp_css)
        except OSError:
            pass
    _zmap = {r[1]: r[0] for r in _zres}
    _guard_ok = (len(_zres) == 3 and _zmap.get("Z2") == "FAIL"
                 and _zmap.get("Z1") in ("PASS", "FAIL", "SKIP")
                 and _zmap.get("Z3") in ("PASS", "FAIL", "SKIP"))
    print(f"{'[ OK ]' if _guard_ok else '[FAIL]'} 护栏：Z1={_zmap.get('Z1')} Z2={_zmap.get('Z2')} "
          f"Z3={_zmap.get('Z3')}（共 {len(_zres)} 条；期望 Z2=FAIL 且 Z1/Z3 仍产出）")
    if not _guard_ok:
        rc = 1
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="审美判据校验器")
    ap.add_argument("--rubric", required=True, help="判据 YAML 路径")
    ap.add_argument("--css", help="待检 CSS 文件")
    ap.add_argument("--spec", help="待检 spec 文档")
    ap.add_argument("--geom", help="渲染色 JSON（R 组判据的输入；由 CDP 探针产出）")
    ap.add_argument("--product", choices=list(PRODUCTS), help="产物类型，用于消费 rubric.applies_to")
    ap.add_argument("--batch", help="批量复算：目录或 glob（如 \"dir/*.css\"）")
    ap.add_argument("--csv", help="批量模式的可选 CSV 输出路径")
    ap.add_argument("--override", help="产物级覆盖：内联 JSON 数组")
    ap.add_argument("--override-file", help="产物级覆盖：JSON 文件路径")
    ap.add_argument("--scale-from", action="append", default=None,
                    help="声明刻度源（可重复，或逗号分隔）：从这些 CSS 的**令牌声明**"
                         "（--*-size-* / --*-duration-*）取并集，作为 G12/G13 的刻度集。"
                         "与被检文件**同源**的源会被剔除并在 problems 中报出（同源刻度 ⇒ 恒真）")
    ap.add_argument("--json", action="store_true", help="机器可读输出（供门禁比对）")
    ap.add_argument("--audit", action="store_true", help="判据 ↔ 实现 一致性审计")
    ap.add_argument("--self-test", action="store_true", help="解析器 / ΔE00 / APCA 自检")
    args = ap.parse_args()

    rp = Path(args.rubric)
    if not rp.is_file():
        print(f"[FAIL] 判据文件不存在：{rp}", file=sys.stderr)
        return 2

    rubric = mini_yaml_load(rp.read_text(encoding="utf-8"))
    overrides = _load_overrides(args)
    # v1.5.0：`--scale-from` 支持重复与逗号/分号分隔两种写法（同一开关两种用法都吃）
    scale_from = [x.strip() for chunk in (args.scale_from or [])
                  for x in re.split(r"[;,]", chunk) if x.strip()]

    if args.self_test:
        return self_test(rp)
    if args.audit:
        return audit_rubric(rubric)
    if args.batch:
        return batch(rubric, args.batch, args.product, args.json, args.csv,
                     overrides, scale_from)
    if not args.css and not args.spec and not args.geom:
        print("[FAIL] 至少提供 --css / --spec / --geom / --batch 之一", file=sys.stderr)
        return 2

    return run(rubric, args.css, args.spec, args.product, args.json, args.geom,
               overrides, scale_from)


if __name__ == "__main__":
    sys.exit(main())
