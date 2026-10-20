# DESIGN.md 的产出与验收（宿主侧接线）

> **这不是规格文档**。规格本体在 google-labs-code/design.md（Apache-2.0），生产实现在 impeccable 的 reference/document.md。本文件只管三件本仓独有的判断：**何时该产、谁来产、怎么验**。
> 版本：1.0（2026-10-20 建，依据 `tasks/拆解-awesome-design-md整合-2026-10-20/` 的结构实测）
> 加载时机：任务产物将含前端件（HTML／CSS／组件／页面），或用户提到设计档案／设计规范／风格指南／DESIGN.md 时。

## 一、口径源分工

同一件事不许两处定义。四层各归各家，本仓只占最后一格。

| 层 | 口径源 | 本仓的动作用 |
| --- | --- | --- |
| 格式规格 | google-labs-code/design.md ＋ npm @google/design.md | 引用，不复述 |
| 生产流程 | impeccable（document 记存量／new-work 建新世界） | 调用，不大改 |
| 风格素材 | `~/.workbuddy/skills/awesome-design-md/`（84 份品牌） | 按需读单文件，只作参照 |
| 触发与验收 | **本文件** | 唯一落点 |

## 二、何时该产

三条触发，命中任一即产：

1. 任务产物含前端件（页面／组件／表单／仪表盘／落地页），且项目尚无 DESIGN.md。
2. 项目已有 DESIGN.md，但实现已漂移（改了色板／字体／组件规则却没回写档案）。
3. 用户明确要「设计档案／设计规范／风格指南／让 agent 一直按这个风格做」。

不触发的三种相邻情形（各有归属，别抢活）：

- 只要一张图（架构图／流程图／示意图）→ `references/diagram-mode.md`。
- 只要演示文稿 → `references/ppt-mode.md`（执行交 ppt-master）。
- 只想审一个已有页面的丑不丑 → impeccable 的 critique／audit，不必产档案。

## 三、谁来产

| 情形 | 走哪条 | 注意 |
| --- | --- | --- |
| 存量项目，已有代码或界面 | impeccable 的 document（scan 模式） | 先扫描 CSS 变量／Tailwind 配置／主题文件，再让用户补定性语言 |
| 全新视觉方向，尚无实现 | impeccable 的 new-work | DESIGN.md 在 finish 阶段由 documenter 从已建成的世界回写，不是动工前先写一版 |
| 已有 DESIGN.md 需要刷新 | 同上，先给用户看原文 | 不得静默覆盖；刷新／覆盖／合并三选一 |
| 扩展一个已有页面 | 不产 | 局部新增不构成系统级改动，除非用户批准改系统 |

**本仓不提供 DESIGN.md 模板。** 模板一旦复制进来，就会和官方规格形成两套口径，且上游改版后必然失同步。要模板就读 impeccable 的 reference/document.md。

## 四、怎么验

四条判据，前两条机器可判，后两条只能人审。

| # | 判据 | 方式 | 跑不了时 |
| --- | --- | --- | --- |
| 1 | frontmatter 可解析，7 键齐（name／description／colors／typography／rounded／spacing／components） | 官方 lint | 标「未检测」 |
| 2 | 八节齐全且同序（Overview／Colors／Typography／Layout／Elevation & Depth／Shapes／Components／Do's and Don'ts） | 官方 lint | 标「未检测」 |
| 3 | Do's and Don'ts 至少 3 条 Don't，且每条带具体值或具体失败形态 | 人审 | — |
| 4 | 同一令牌不在 frontmatter 与正文两处给不同值 | 人审 | — |

**降级口径**（沿用门禁不可用时的行为）：lint 跑不了时，只读动作放行并显式标注「本次未经 lint 校验」；涉及发布／推送等不可逆动作时 fail-closed，不得带着「未检测」出站。

**为什么第 3 条不能省**：素材库里有 1 份（airbnb）八节缺了 Do's and Don'ts，仍能通过结构计数。禁令缺失不改变节的数量，只让档案失去约束力——这正是结构校验抓不到、人审必须补的那一格。

## 五、写作纪律三件

这三条从素材库的方法层抽出来（Known Gaps 43/84、Iteration Guide 50/84、Do's and Don'ts 73/84），形态与品牌无关，是这套语料最值得抄的部分。

**① 承认没取到的部分。** 缺什么、为什么缺、暂时拿什么替代、置信度多少，四样齐。反例是「动画未描述」——读者不知道这是你没看，还是这个站点本来就不动。素材库的写法是 `Animation/transition timings not extracted; recommend 150–200ms ease`。

**② 写清后续怎么改。** 粒度约束、引用令牌而不是绝对值、收尾动作，三样齐。反例是「保持一致性」——无法执行。素材库的写法是 `Focus on ONE component at a time` ＋ `Run npx @google/design.md lint DESIGN.md after edits`。

**③ 禁令要带值。** 反例是「保持克制」；可执行的写法是「主色占屏 ≤10%，胶囊圆角只用于营销级 CTA，导航按钮用 6px」。素材库的 Do 段逐条都带令牌引用与像素值。

## 六、可迁移提示（不限于设计）

三件的形态可以搬到任何「从不完整证据写规范」的产出上。设计之外的用法：

| 形态 | 通用写法 |
| --- | --- |
| Known Gaps | 来源没覆盖到的范围 ＋ 置信度标记 ＋ 暂时替代方案 |
| Iteration Guide | 后续修改的粒度约束 ＋ 引用共享标识符 ＋ 收尾动作 |
| Do/Don't | 带值的禁令，而不是形容词 |

这三条在本仓已有同构机制，**互指而不新造**：科研模式的 N4「未取到范围」管证据边界，`retrieval-judge.md` §5.1 管否定断言的门槛，阶段 3 的「每步前重述目标与判定标准」管执行粒度。

## 七、边界

1. **素材库是社区逆向描述，没有 oracle**：84 份与各品牌线上站点的一致性无法验证（网站会改版），只能作参照、不能作判据，也不得把品牌色值写进 `aesthetic-rubric.yaml`。
2. **本仓无 lint 实跑记录**（截至 2026-10-20，本机未安装 @google/design.md）。任何「已通过校验」的说法在实跑前都不成立。
3. **素材库零改动**：不往 `~/.workbuddy/skills/awesome-design-md/` 写任何本项目自产的 DESIGN.md，项目档案落项目目录。
4. **九节不是规格**：README 那套九节只覆盖 10/84，且这 10 份都没有令牌层。按九节写模板会把旧写法当规范。
