# 网络安全（信息安全）从零到进阶：学习路径与实操资源调研

> 调研日期：2026-09-10　｜　对象画像：中文数学专业本科 + 全栈/AI 开发者（Python/FastAPI + React），正在做量化交易项目并计划做安全加固
> 检索轮次：英文 ≥1 轮、中文 ≥1 轮，关键平台均用 WebFetch 读官方页面核对现状
> 证据分级：【官方推荐】= 平台/机构官方页面或官方文档直接佐证；【实践观点】= 第三方评测、社区经验、从业者总结
> 范围限定：只回答"怎么学、在哪练"，不罗列安全公司名单、不做行业新闻综述

---

## 0. 结论先行（先给画像定制判断）

**你不该走"零基础转行"路线。** 网上绝大多数"网安自学路线图"是给没有编程基础、想转行做渗透/运维的人写的（先啃 C 语言、再背工具按钮、再去 SRC 挖洞）。你是数学本科 + 全栈/AI 开发者，已经具备两个别人要花半年补的护城河：**能写代码、能读懂数学**。正确的切入点是"**开发者视角的应用安全（AppSec）**"，而不是"攻击者视角的渗透入门"。

因此本报告把主线定为三条，全部与你的现状直接咬合：

1. **Web/API 应用安全** —— 直接加固你现在的 FastAPI + React 量化项目，学完即用。
2. **密码学** —— 你的数学背景在这里是降维打击，且是所有安全的地基。
3. **AI/LLM 安全** —— 你已在做 AI 开发，这是 2026 年最缺人、最新的专项。

红队（渗透）与蓝队（SOC/应急响应）作为"能力扩展"而非主线。

---

## 1. 分级学习路径（基础 → 进阶 → 专项）

时间估算按**每周 8–12 小时**（在职自学的现实节奏）计算；全职可压缩 40%–50%。

### 阶段 A｜地基：网络 + 操作系统 + HTTP（预计 3–5 周）

| 项 | 内容 |
|---|---|
| **目标** | 补上"计算机怎么跑起来"的底层直觉：进程/权限/Linux 命令行、TCP/IP 与 HTTP(S) 全流程、DNS/端口。安全的一切都站在这上面。 |
| **推荐资源** | ① OverTheWire **Bandit**（免费，SSH 闯关学 Linux）② Professor Messer 的 Network+/Security+ 免费视频 ③ Cisco **Networking Essentials**（免费）④ 本地 VirtualBox + Kali/Ubuntu 虚拟机 |
| **预计投入** | 每周 8–10h × 4 周 |
| **可验证里程碑** | ① Bandit 打通到 Level 20+；② 能手画"浏览器打开一个网页"的完整链路（DNS→TCP→TLS→HTTP），并解释每步可能被怎么攻击；③ 在不看教程的情况下用 `nmap`、`curl`、`tcpdump` 完成一次端口扫描与抓包。 |

- OverTheWire 官方明确定义了游戏顺序：Bandit（Linux 基础）→ Natas（Web）/Krypton（密码学）/Leviathan（逆向）→ Narnia…（二进制利用）。【官方推荐】https://overthewire.org/wargames/
- 免费基础课程清单（Professor Messer、Cisco NetAcad、freeCodeCamp）交叉 corroborate。【实践观点】https://coppers.io/how-to-learn-cybersecurity-online

> 注意：**不要**在这一阶段死磕 C 语言或背 OSI 七层定义。你已经有编程能力，把时间花在"用命令行把一个请求从头到尾看穿"这件事上。

---

### 阶段 B｜进阶主线：Web/API 应用安全（预计 6–10 周）★ 对你性价比最高

| 项 | 内容 |
|---|---|
| **目标** | 吃透 OWASP Top 10（Web）与 OWASP API Security Top 10，熟练使用 Burp Suite，能对自己写的 FastAPI/React 应用做**主动漏洞挖掘 + 修复**。 |
| **推荐资源** | ① **PortSwigger Web Security Academy**（100% 免费，Web 安全事实标准）② **OWASP Juice Shop**（本地 Docker 一键起，100+ 关卡，练"无提示式发现"）③ **CodeSignal** 的《OWASP Top 10 with Python/FastAPI》免费路径（10h）④ OWASP API Security Top 10 官方文档 |
| **预计投入** | 每周 8–10h × 8 周 |
| **可验证里程碑** | ① PortSwigger 全部 **Apprentice 级**实验通关（SQLi/XSS/CSRF/SSRF/JWT/访问控制等）；② Juice Shop 得分 ≥ 30；③ **交付物**：给自己量化项目写一份威胁建模（STRIDE 或 OWASP 清单），并真实修掉至少 1 个越权（BOLA）或注入类问题，留一次 git commit 记录。 |

- PortSwigger 官方：Web Security Academy "is 100% free"，含 20+ 主题、250+ 交互式实验，并已新增 **Web LLM attacks（7 labs）**、Web cache deception、API testing 等。【官方推荐】https://portswigger.net/web-security
- PortSwigger 覆盖 OWASP Top 10 且"紧跟最新漏洞类型"、与 Burp Suite 深度集成。【实践观点】https://blog.csdn.net/weixin_34151004/article/details/90561912
- Juice Shop 与 Academy 的分工：Academy 是"有指导的学习"，Juice Shop 是"开放式发现"，真实评估中你不知道漏洞类别，所以两者必须搭配。【实践观点】https://www.offensive360.com/blog/owasp-juice-shop-vs-portswigger-web-security-academy/
- OWASP API Security Top 10 覆盖 BOLA（API1）、Broken Auth（API2）、Mass Assignment（API6）等，且有专门的 FastAPI 加固示例（JWT 依赖注入、显式算法白名单、rate limiting）。【实践观点】https://www.coddykit.com/courses/fastapi/mitigating-the-owasp-api-security-top-10-9286928
- CodeSignal 提供免费的《OWASP Top 10 & Common Attack Vectors in Python (1-5)》，10 小时、含证书；付费路径覆盖 FastAPI 认证/MFA/SSRF 防护。【实践观点】https://www.classcentral.com/subject/broken-authentication

> 这一阶段结束时，你应当能对"我这套 FastAPI + React"做出有依据的安全评审，这正是"计划做安全加固"的直接产出。

---

### 阶段 C｜方向扩展：红队 或 蓝队（二选一，预计 8–12 周）

不必两个都学。以你的开发者身份，建议**先红后蓝**——懂攻击才能写出防得住的后端。

| 子方向 | 目标 | 推荐资源 | 里程碑 |
|---|---|---|---|
| **C1 进攻（红队/渗透）** | 掌握"信息收集→利用→提权→横向移动"完整链路 | ① **TryHackMe** Offensive Pentesting 路径（免费档 + Premium）② **Hack The Box** Starting Point / Easy 机器（免费档）③ VulnHub 本地靶机 | 独立拿下 10 台 easy 机器，每台写 writeup（含思路而非只写命令） |
| **C2 防御（蓝队/SOC）** | 会看告警、会查日志、会做应急响应 | ① **LetsDefend** 免费 SOC 告警（模拟真实 SOC 队列）② **CyberDefenders** 免费 DFIR 挑战 ③ TryHackMe SOC Level 1 路径 | 完成 20+ 条告警研判（能写"true positive / false positive + 依据"） |

- TryHackMe 免费档：免费房间 + 限定路径 + 每天 1 小时 AttackBox；Premium 官方价 **$16.99/月（年付约 $10.50/月）**；2026-06-29 起新增 MAX 档（$29.11/月），**Red Teaming / SOC L2 / Web App Red Teaming 等高级路径现在需要 MAX**。【官方推荐】https://tryhackme.com/pricing
- Hack The Box **已于 2025 年 10 月下线 VIP 档**，只剩 VIP+（**$25/月** 或 $223/年）；Academy 与 Labs 是**分开计价**的两套产品；Academy 免费档送 30 Cubes，Tier 0 模块花 10 Cubes 且完成后全额返还（等于基础内容真免费）；学生档 $8/月。【实践观点】https://thecybersecuritytrail.com/guide/hack-the-box-vs-tryhackme/
- LetsDefend 免费档含免费课程 + 每月有限 SOC 告警；VIP 约 $25/月、VIP+ 约 $40/月；被 HTB 于 2025-09 收购，内容正在并入 HTB 生态（需留意平台变化）。【实践观点】https://cybersecurityrange.com/reviews/letsdefend
- CyberDefenders 定位 100% 蓝队/DFIR，免费挑战可由社区自由练习（微软、卡巴斯基等分析师实名评价其 lab 质量）。【官方推荐】https://cyberdefenders.org/

---

### 阶段 D｜专项深耕（选 1–2 个，预计 3–6 个月）

| 专项 | 为什么适合你 | 推荐资源 | 里程碑 |
|---|---|---|---|
| **D1 密码学** ★ | 数学专业背景直接转化为优势；所有 TLS/签名/区块链/钱包安全的底层 | **CryptoHack**（100% 免费）：Introduction → 对称加密 → RSA → 椭圆曲线 | 通关 RSA + Elliptic Curves 两大课程；能自己实现一次经典 RSA/ECC 攻击（如 ROCA 类思路） |
| **D2 二进制/底层利用** | 补上"计算机底层"认知，含金量高、竞争少 | **pwn.college**（ASU 出品，100% 免费，腰带晋级制）；OverTheWire Narnia → Behemoth | 拿到 pwn.college **绿带**（Green Belt） |
| **D3 AI/LLM 安全** ★ | 你已在做 AI 开发，这是 2026 年最缺人的新赛道 | OWASP **Top 10 for LLM Applications** + PortSwigger **Web LLM attacks** 实验 + **LLMVault**（离线 25 个 OWASP LLM 关卡） | 对自己接的 LLM 应用做一次完整红队测试，输出报告 |
| **D4 AppSec / DevSecOps** ★ | 与你"给项目做安全加固"的目标 100% 重合 | 在 CI 里接入 SAST/依赖扫描（Dependabot/Snyk）、DAST、密钥管理；Docker/K8s 基线加固 | 给量化项目上线一条安全流水线：每次 PR 自动跑依赖扫描 + 静态检查 |

- CryptoHack 官方定位"a free, fun platform for learning modern cryptography"，以解题（RSA/ECC/哈希/对称密码）方式学习，有课程体系与积分/等级。【官方推荐】https://cryptohack.org/
- CryptoHack 的 Mathematics/RSA/ECC 路径明确以模运算、扩展欧几里得、离散对数、椭圆曲线为骨架，数学背景者上手极快。【实践观点】https://blog.csdn.net/Yuiro556/article/details/162374624
- pwn.college 由 **亚利桑那州立大学（ASU）** 团队维护，支撑 ASU 网络安全课程，向全球**免费开放**，以"白带→绿带→蓝带"晋级。官方要求不要外传题解。【官方推荐】https://pwn.college/
- OWASP LLM Top 10 现状：Prompt Injection（LLM01）在已评估的生产 AI 部署中**出现率超过 73%**；2026 年 OWASP 已另立《Agentic Applications Top 10》以覆盖自主智能体。【实践观点】https://elevateconsult.com/insights/owasp-llm-top-10-security-vulnerabilities-every-ai-developer-must-know-in-2026/
- LLMVault：开源离线沙箱，覆盖全部 10 项 OWASP LLM 风险、25 个分层关卡，无需 API key，Docker 一键部署，默认只监听 127.0.0.1。【实践观点】https://github.com/CyberSunil/LLMVault

---

### 路径总览

```
阶段A 地基(3-5周)      →  阶段B Web/API应用安全(6-10周)  →  阶段C 红队/蓝队二选一(8-12周)  →  阶段D 专项深耕(3-6月)
OverTheWire Bandit          PortSwigger Academy               TryHackMe / HTB               CryptoHack / pwn.college
Linux/网络/HTTP             Juice Shop / OWASP API            LetsDefend / CyberDefenders    OWASP LLM / DevSecOps
           │                          │                                 │                            │
      通关Bandit L20+           拿到1个真实修复commit           10台机器或20条告警            绿带 / 一份AI红队报告
```

---

## 2. 实操平台/课程清单（14 个，按推荐优先级）

| # | 平台/课程 | 访问地址 | 免费程度 | 适合阶段 | 证据等级 |
|---|---|---|---|---|---|
| 1 | **PortSwigger Web Security Academy** | https://portswigger.net/web-security | **完全免费**（无付费墙；Burp Pro $475/年非必需） | B（Web 安全） | 【官方推荐】 |
| 2 | **OverTheWire** | https://overthewire.org/wargames/ | **完全免费**（无需账号） | A（Linux 基础） | 【官方推荐】 |
| 3 | **CryptoHack** | https://cryptohack.org/ | **完全免费** | D1（密码学） | 【官方推荐】 |
| 4 | **pwn.college** | https://pwn.college/ | **完全免费**（ASU 出品） | D2（二进制） | 【官方推荐】 |
| 5 | **OWASP Juice Shop** | https://owasp.org/www-project-juice-shop/ | **完全免费**（开源 MIT，本地 Docker） | B | 【实践观点】 |
| 6 | **TryHackMe** | https://tryhackme.com/pricing | **免费档**（免费房间+1h/天 AttackBox）；Premium $16.99/月、MAX $29.11/月 | A/B/C | 【官方推荐】 |
| 7 | **Hack The Box**（Labs + Academy） | https://academy.hackthebox.com/ ｜ https://www.hackthebox.com/ | **免费档**（20 台 active 机器、80+ 挑战、Academy 送 30 Cubes）；VIP+ $25/月；Academy 学生档 $8/月 | B/C（进阶渗透） | 【官方推荐】+【实践观点】 |
| 8 | **LetsDefend** | https://letsdefend.io/ | **免费档**（免费课程 + 每月限量 SOC 告警）；VIP 约 $25/月、VIP+ 约 $40/月 | C2（蓝队 SOC） | 【官方推荐】 |
| 9 | **CyberDefenders** | https://cyberdefenders.org/ | **免费挑战 + 付费 CCD 认证** | C2（DFIR） | 【官方推荐】 |
| 10 | **CyLab Security Academy（原 picoCTF）** | https://cylabacademy.org/ | **完全免费**（卡内基梅隆大学） | A/B（入门 CTF） | 【官方推荐】 |
| 11 | **VulnHub** | https://www.vulnhub.com/ | **完全免费**（可下载靶机，离线练习） | C1 | 【实践观点】 |
| 12 | **CTFHub / 攻防世界 / BUUCTF / ctfshow** | https://www.ctfhub.com/ ｜ https://adworld.xctf.org.cn/ ｜ https://buuoj.cn/ ｜ https://ctf.show/ | **题库免费**（中文，CTF 真题 + 在线环境） | B/C（刷题、备赛） | 【实践观点】 |
| 13 | **i春秋** | https://www.ichunqiu.com/ | **部分免费课 + 付费课/线下班**（如 Web 漏洞讲解 ¥280、CTF 精品 ¥999） | A/B（中文体系化） | 【官方推荐】 |
| 14 | **Google Cybersecurity Professional Certificate**（Coursera） | https://www.coursera.org/professional-certificates/google-cybersecurity | **可免费旁听（Audit）**；拿证需订阅 | A（蓝队入门） | 【实践观点】 |

### 补充：与"AI 开发者"直接相关的免费课程

| 课程 | 地址 | 说明 | 证据等级 |
|---|---|---|---|
| CodeSignal《OWASP Top 10 & Common Attack Vectors in Python/FastAPI (1-5)》 | https://codesignal.com/learn/ | 10 小时，免费，含证书，直接在 FastAPI 里练 OWASP 漏洞修复 | 【实践观点】 |
| PortSwigger Web LLM Attacks（7 labs） | https://portswigger.net/web-security/llm-attacks | 免费，讲间接提示注入、输出处理不当、LLM API 攻击 | 【官方推荐】 |
| OWASP Top 10 for LLM Applications | https://genai.owasp.org/llm-top-10/ | LLM 安全的权威标准与缓解措施 | 【官方推荐】 |
| LLMVault（离线 AI 安全靶场） | https://github.com/CyberSunil/LLMVault | Docker 一键起，25 关覆盖 OWASP LLM Top 10 | 【实践观点】 |

---

## 3. 被过誉 / 已过时的资源（重点避坑）

> 这一节只谈"性价比"和"时效性"，不做人身评价。凡"过誉"多为**实践观点**，请自行复核。

### 3.1 已过时（信息本身变了，别再按旧攻略走）

1. **ISC2 免费 CC 认证名额已结束。** "一百万人免费 CC 课程+考试"是 2022–2026 年的热门福利，但官方已于 **2026-05-20 停止新报名**；仅已拿到考码者可在 2026-12-31 前使用，之后 CC 需正常付费购买。**别再去网上找"免费领取 CC"的旧教程。**【官方推荐】https://www.isc2.org/landing/1mcc
2. **picoCTF.org 已改名为 CyLab Security Academy。** 2026-05-08 后原 picoCTF 账号可继续登录 https://cylabacademy.org/ ，但"picoCTF"作为入口的说法已过时。【官方推荐】https://picoctf.org/
3. **Hack The Box 的 "VIP $14/月" 已不存在。** 官方 2025-10 下线 VIP 档，现在最低付费档是 **VIP+ $25/月**；很多 2024–2025 年的攻略/比价表仍写 VIP，预算会算错。同时 Academy 与 Labs **分开收费**，叠加后可达 $40–50+/月。【实践观点】https://thecybersecuritytrail.com/guide/hack-the-box-vs-tryhackme/
4. **TryHackMe "Premium 就够用" 的说法在 2026-06 之后不再完全成立。** 高级路径（Red Teaming、SOC L2 等）已划入 **MAX** 档。若你的目标是高级红队内容，Premium 会撞墙。【官方推荐】https://tryhackme.com/pricing

### 3.2 被过誉（能用，但性价比名不副实）

5. **CEH（EC-Council）** —— 被从业者批评为"贵、以多选题背题为主、动手实践少"，考试费高达约 **$1,199**；相比之下手动型认证（OSCP、HTB 的 CPTS、INE 的 eJPT）更能证明实战能力。**若目标是证明"会做"而非"会背"，优先动手型认证。**【实践观点】https://www.youtubesummary.com/summary/alXJzbsS-eI
6. **高价网安培训班 / 就业训练营（$5,000–$20,000）** —— 内容大多在免费平台可得；行业评测明确指出"除非能提供经第三方审计的就业数据，否则不值得"。国内"零基础高价线下就业班"同理。【实践观点】https://futurecyber.it/cybersecurity-bootcamp
7. **SANS 单门课（$7,000–$9,000）** —— 质量确实顶级，但**对个人自学者极度不划算**；除非公司报销，否则应放到工作若干年后再考虑。【实践观点】https://hadess.io/cybersecurity-learning-path
8. **纯理论型证书（大部分 CompTIA 系列 / ISC2 的 GRC 类）** —— Security+ 作为基线知识有用（部分美军/政企岗位硬性要求），但其余"多选题+定义式"证书被批评不能直接转化为岗位能力；防御侧更要看动手。**别把"考完 Security+ 就能拿高薪"当预期。**【实践观点】https://www.youtubesummary.com/summary/alXJzbsS-eI
9. **"收藏一堆靶场清单 / 工具清单 / 300G 资料包"式学习** —— 这是中文网安圈最典型的伪努力：免费靶场、资料包满天飞，但**只收藏不动手等于零**。评测反复指出："没主攻方向、今天渗透明天逆向"是初学者最大的坑。【实践观点】https://blog.csdn.net/2401_85688943/article/details/161447397
10. **DVWA / Metasploitable 2 这类"老牌靶场"** —— 仍可用于理解基础漏洞原理，但内容偏旧、难度刻意，**不应作为唯一或主要练习环境**；现代替代是 PortSwigger Academy、Juice Shop、TryHackMe。仅作"入门第一次体验"用即可。【实践观点】https://thecybersecuritytrail.com/guide/best-hands-on-cybersecurity-labs-practice-platforms-in-2026/

### 3.3 一个反直觉提醒

**不要用"红队渗透"作为你的第一主线。** 你的最大杠杆是"能写代码"。应用安全（AppSec）、云安全、AI 安全这些岗位，需要的是"懂开发的安全人"，而这正是渗透培训班出来的学员最缺的。同样花 6 个月，你走 AppSec 路线的稀缺度和收入天花板都高于走渗透路线。

---

## 4. 对你量化项目的即时加固清单（学中做）

配合阶段 B，边学边做，产出可验证的"安全 commit"：

- **认证授权**：FastAPI 里用 `Depends()` 统一注入 JWT 校验依赖，显式白名单算法（`algorithms=["HS256"]`），校验 `exp`，避免"新路由忘了加鉴权"。
- **越权（BOLA/IDOR）** —— API 场景的头号风险：每个涉及 `id` 的接口都要校验"该资源是否属于当前用户"，不能只靠前端隐藏。
- **输入校验**：用 Pydantic 严格约束字段；避免 mass assignment（不要直接把请求体 `**kwargs` 塞进 ORM）。
- **注入**：ORM 参数化查询；禁止拼接 SQL / shell。
- **密钥管理**：密钥放环境变量或 secret manager，不进 git；给仓库加 secret 扫描。
- **依赖与 CI**：接入 Dependabot/Snyk 扫描依赖漏洞；PR 触发 SAST。
- **限流与暴露面**：登录/接口限流；生产环境关闭 debug、收敛 CORS。
- **AI 相关**：若量化项目里有 LLM/智能体，按 OWASP LLM Top 10 重点防**间接提示注入**与**输出处理不当**。

---

## 5. 全部来源 URL

**官方页面（【官方推荐】）**
1. TryHackMe 定价 —— https://tryhackme.com/pricing
2. PortSwigger Web Security Academy —— https://portswigger.net/web-security
3. OverTheWire Wargames —— https://overthewire.org/wargames/
4. CryptoHack —— https://cryptohack.org/
5. CryptoHack RSA 挑战 —— http://cryptohack.org/challenges/rsa/
6. CryptoHack 椭圆曲线课程 —— https://www.cryptohack.org/courses/elliptic/course_details/
7. pwn.college —— https://pwn.college/
8. Hack The Box Academy —— https://academy.hackthebox.com/
9. LetsDefend —— https://letsdefend.io/
10. CyberDefenders —— https://cyberdefenders.org/
11. CyLab Security Academy（原 picoCTF）—— https://picoctf.org/ ｜ https://cylabacademy.org/
12. ISC2 百万 CC 计划（已结束）—— https://www.isc2.org/landing/1mcc
13. ISC2 官方公告 —— https://www.isc2.org/insights/2026/04/one-million-certified-cyber-conclusion
14. Google Cybersecurity Certificate —— https://www.coursera.org/professional-certificates/google-cybersecurity
15. i春秋 —— https://www.ichunqiu.com/
16. OWASP LLM Top 10 —— https://genai.owasp.org/llm-top-10/
17. OWASP Juice Shop —— https://owasp.org/www-project-juice-shop/

**第三方评测/社区（【实践观点】）**
18. TryHackMe vs HTB 2026 定价与免费档 —— https://thecybersecuritytrail.com/guide/hack-the-box-vs-tryhackme/
19. TryHackMe vs HTB 诚实对比 —— https://certcompass.org/tryhackme-vs-hackthebox
20. LetsDefend 评测 2026 —— https://cybersecurityrange.com/reviews/letsdefend
21. 2026 最佳动手实验室盘点 —— https://thecybersecuritytrail.com/guide/best-hands-on-cybersecurity-labs-practice-platforms-in-2026/
22. Juice Shop vs PortSwigger 对比 —— https://www.offensive360.com/blog/owasp-juice-shop-vs-portswigger-web-security-academy/
23. 免费网络安全资源 2026（含 picoCTF/VulnHub 细节）—— https://hackersonlineclub.com/free-cybersecurity-resources/
24. 应该避免的 5 个安全认证 —— https://www.youtubesummary.com/summary/alXJzbsS-eI
25. 2026 学习路径（含"哪些付费资源不值得"）—— https://hadess.io/cybersecurity-learning-path
26. 网安训练营成本与 Reddit 共识 —— https://futurecyber.it/cybersecurity-bootcamp
27. 在线学习路线（免费/付费划分）—— https://coppers.io/how-to-learn-cybersecurity-online
28. FastAPI × OWASP API Top 10 加固 —— https://www.coddykit.com/courses/fastapi/mitigating-the-owasp-api-security-top-10-9286928
29. CodeSignal OWASP Top 10 免费课程索引 —— https://www.classcentral.com/subject/broken-authentication
30. OWASP LLM Top 10 2026 解读 —— https://elevateconsult.com/insights/owasp-llm-top-10-security-vulnerabilities-every-ai-developer-must-know-in-2026/
31. LLMVault 离线 AI 安全靶场 —— https://github.com/CyberSunil/LLMVault
32. 中文自学路线（六阶段）—— https://ima.qq.com/wiki/ （龙哥网络安全，2026-07-25）
33. 中文零基础路线与避坑 —— https://blog.csdn.net/2401_85688943/article/details/161447397
34. 中文靶场大盘点 2026 —— https://www.kuazhi.com/post/716264446.html
35. 国内外靶场全解析（i春秋/CTFHub/攻防世界）—— https://blog.csdn.net/weixin_29291185/article/details/158676201
36. 免费网安学习网站汇总 —— https://m.nowcoder.com/discuss/903947179021062144
37. 渗透靶场推荐 2026 —— https://longyusec.com/archives/157/
38. CTF 靶场盘点 2026 —— https://security.zone.ci/secarticles/wx/498222.html
39. CryptoHack 模运算路径解析 —— https://blog.csdn.net/Yuiro556/article/details/162374624
