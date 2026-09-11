# Findings 2：网络安全「书籍 / 教材 / 官方文档 + 证书路线」调研

- 任务：技术调研-网络安全学习（子方向 2/3）
- 日期：2026-09-10
- 调研对象画像：中文数学专业本科生 + 全栈/AI 开发者（Python 强、数学功底好、对密码学有兴趣）；预算敏感、偏好免费资源；英文优质材料可直接读；当前诉求是**给量化项目做安全加固**，而非求职 SOC。
- 检索轮次：英文 3 轮（books/official docs、crypto textbooks、cert comparison）+ 中文 2 轮（书籍推荐、官方中文文档/正版渠道）。
- 划界声明：本文件**不涉及行业新闻与薪资报告**，只聚焦「学习材料本身」与「认证本身」。**所有条目只列合法获取途径（官方免费版 / 开放获取 / 图书馆 / 官方试读 / 正规付费），不含任何盗版渠道。**

### 证据等级说明
| 等级 | 含义 |
|---|---|
| **A** | 官方一手来源（作者官网、NIST、MITRE、OWASP 官网、出版社官方页） |
| **B** | 权威二手来源（知名机构、高校课程页、基金会页面） |
| **C** | 社区/博客整理（仅作线索，不单独作为结论依据） |

---

## 一、书 / 教材 / 官方文档清单（13 项 ≥ 8 项）

> 获取渠道栏的「免费」均指**官方或作者本人提供的合法免费**，非网盘/PDF 站。

### 1. Security Engineering（第 3 版）——系统安全思想总纲
- **作者**：Ross Anderson（剑桥大学）
- **免费渠道**：作者官网提供**章节级官方下载**（第 1、2 版**全文免费**；第 3 版按与 Wiley 的约定，除 7 个样章外在出版 42 个月后全文免费，目前可读官方样章与第 1/2 版全文）。**A 级**
- **适合阶段**：地基 → 全阶段案头参考。适合数学/工程背景、想理解"如何设计可靠系统"而不只是打漏洞的人。
- **来源 URL**：https://www.cl.cam.ac.uk/~rja14/book.html
- **备注**：与量化项目最相关的一本——讲的是"信任边界、失败模式、经济与心理因素"，是加固设计的思维底座。

### 2. The Joy of Cryptography——为数学背景定制的密码学教材
- **作者**：Mike Rosulek（俄勒冈州立大学），MIT Press 出版
- **免费渠道**：**官方开放获取全文**（CC BY-NC-ND），在线 HTML 全 20 章免费。**A 级**
- **适合阶段**：密码学专项入口（地基之后即可读）。带 Math Review 附录与有限域章节，**对数学专业是最平缓的现代密码学入口**。
- **来源 URL**：https://joyofcryptography.com/
- **备注**：以"可证明安全"为主线（One-Time Pad → PRG → PRF → RSA → 零知识 → 后量子），正好接住你的数学直觉。

### 3. A Graduate Course in Applied Cryptography——密码学进阶（研究生级）
- **作者**：Dan Boneh（斯坦福）+ Victor Shoup
- **免费渠道**：**作者官网免费 PDF**（v0.6，2023-01 最新）。**A 级**
- **适合阶段**：密码学专项·进阶（读完 Joy of Cryptography 后）。含椭圆曲线、格上后量子、安全多方计算、阈值密码。
- **来源 URL**：https://toc.cryptobook.us/

### 4. OWASP Web Security Testing Guide（WSTG）——Web 安全测试方法论
- **作者**：OWASP 社区（项目组）
- **免费渠道**：**官方免费**在线 stable 版 + GitHub 发布 PDF（v4.2 等）。5.0 开发中。**A 级**
- **适合阶段**：应用安全——把"零散漏洞知识"整理成**可执行测试流程**。
- **来源 URL**：https://owasp.org/www-project-web-security-testing-guide/ （v4.2 PDF：https://github.com/OWASP/wstg/releases/download/v4.2/wstg-v4.2.pdf）

### 5. OWASP Top 10 + Cheat Sheet Series——应用安全最小必读
- **作者**：OWASP
- **免费渠道**：**官方免费**（CC BY-SA 4.0）；**Top 10 有官方中文版**（`owasp.org/Top10/zh_CN`）。2025 版已发布。**A 级**
- **适合阶段**：应用安全·第一步。Cheat Sheet 是"每个模块怎么防"的速查手册，做加固时按条目自查。
- **来源 URL**：https://owasp.org/Top10/en ／ 中文：https://owasp.org/Top10/zh_CN ／ https://cheatsheetseries.owasp.org/

### 6. PortSwigger Web Security Academy——免费"书 + 靶场"（实操首选）
- **作者**：PortSwigger（Dafydd Stuttard，《Web 应用黑客手册》作者团队）
- **免费渠道**：**官方 100% 免费**（注册即可，含交互式 Lab、进度跟踪；Burp Suite Community 版免费）。**A 级**
- **适合阶段**：应用安全·实操核心。覆盖 SQLi/XSS/CSRF/XXE/访问控制/**API 测试/LLM 攻击/Web 缓存欺骗**等，持续更新。
- **来源 URL**：https://portswigger.net/web-security
- **备注**：对你的"AI + Web 全栈"背景尤其对口——它已包含 **Web LLM attacks / AI 扫描器漏洞**等新方向。

### 7. MITRE ATT&CK——蓝队/威胁情报的通用语言
- **作者**：MITRE（非营利）
- **免费渠道**：**官方免费开放**（含 ATT&CK Navigator、CALDERA、Atomic Red Team 等工具）。**A 级**
- **适合阶段**：红蓝队——攻击者"怎么做"的目录；蓝队用它做检测覆盖、事件响应与威胁狩猎。
- **来源 URL**：https://attack.mitre.org/ ／ 入门：https://attack.mitre.org/resources

### 8. NIST Cybersecurity Framework (CSF) 2.0 + NIST SP 系列——防御治理地基
- **作者**：NIST（美国国家标准与技术研究院）
- **免费渠道**：**官方免费 PDF/在线**（CSF 2.0 已于 2024-02 定稿；另有 SP 800-53 控制目录、SP 800-61 事件响应指南等；CSF 有官方多语种版本）。**A 级**
- **适合阶段**：地基（防御视角）→ 治理。给你"Identify/Protect/Detect/Respond/Recover + Govern"六职能的框架，量化项目做安全体系化设计时按此对齐。
- **来源 URL**：https://www.nist.gov/cyberframework ／ https://csrc.nist.gov/Pubs/cswp/29/the-nist-cybersecurity-framework-20/final

### 9. The Linux Command Line（第 7 网络版）——Linux 命令行地基
- **作者**：William Shotts（No Starch 出版印刷版）
- **免费渠道**：**作者官网免费 PDF**（CC BY-NC-ND）。**A 级**
- **适合阶段**：地基·Linux。596 页，从 shell 到脚本，安全工具链的前置能力。
- **来源 URL**：https://linuxcommand.org/tlcl.php

### 10. CyBOK（Cyber Security Body of Knowledge）v1.1——学科地图 / 知识域框架
- **作者**：英国国家网络安全计划资助，115 位国际专家编写
- **免费渠道**：**官方免费下载**（v1.1 含 21 个 Knowledge Areas，明确"Free to use for everyone"）。**A 级**
- **适合阶段**：地基·选路用。**不是教材而是地图**——用它确认自己要学哪些知识域、跳过哪些，避免"随机刷教程"。
- **来源 URL**：https://www.cybok.org/ ／ 知识库：https://www.cybok.org/knowledgebase1_1/

### 11. 鸟哥的 Linux 私房菜（基础学习篇）——中文 Linux 地基
- **作者**：鸟哥（蔡德明）
- **免费渠道**：**作者官网免费在线版**（linux.vbird.org，作者本人站点，免费阅读）；纸质/第 4 版为正规付费。**B 级**（作者官网为一手；网页版部分内容偏旧，以官网现状为准）
- **适合阶段**：地基·中文 Linux 补课（若更习惯中文）。
- **来源 URL**：https://linux.vbird.org/

### 12. 《白帽子讲 Web 安全》（第 2 版）——中文应用安全经典
- **作者**：吴翰清（道哥）、叶敏
- **免费渠道**：**付费**（电子工业出版社，定价 ¥108；第 2 版 2023-07）。合法途径：**正规购买 / 图书馆借阅**。**A 级**（出版社官方页）
- **适合阶段**：应用安全·中文巩固（配合 OWASP/PortSwigger 使用）。
- **来源 URL**：https://cbjj.phei.com.cn/module/goods/wssd_content.jsp?bookid=63034
- **备注**：**未找到官方免费全文**——故不建议寻找"免费 PDF"，走正规购买或图书馆。

### 13. OpenSecurityTraining2（OST2）——免费二进制/漏洞/逆向课程（红蓝队专项）
- **作者**：Xeno Kovah 等，501(c)(3) 非营利
- **免费渠道**：**官方免费**（CC 授权，含幻灯片、实验、视频；另有历史站 opensecuritytraining.info 镜像）。**A 级**
- **适合阶段**：红蓝队/专项——软件漏洞（Vulns1001/1002）、x86-64 汇编、逆向、固件、TPM、模糊测试。
- **来源 URL**：https://p.ost2.fyi/courses ／ 旧站：http://opensecuritytraining.info/Training.html

### 补充（付费但值得放书架，仅列合法途径）
- **Serious Cryptography（2nd ed., 2024）** — J-P. Aumasson，No Starch Press。**付费**；合法途径：出版社/亚马逊**官方试读样章 + 正规购买**。适合密码学工程实践（TLS、AEAD、后量子），是"理论→工程"的桥。来源：https://www.amazon.com/Serious-Cryptography-2nd-Introduction-Encryption/dp/1718503849
- **The Web Application Hacker's Handbook** — Stuttard & Pinto。**付费**；但其核心内容已由作者以**免费形式**持续更新进 **PortSwigger Web Security Academy**（见第 6 项），可优先用免费版。来源：https://portswigger.net/web-security/web-application-hackers-handbook

---

## 二、分阶段阅读顺序（与"地基 → 应用安全 → 红蓝队 → 专项"路径对齐）

> 原则：**先补地基，再进应用安全；每读一个主题，立刻在免费靶场动手**。免费资源优先，付费项只在确认需要时买。

### 阶段 0 · 地基（先用地图选路，再补硬技能）
1. **CyBOK v1.1**（选读 Knowledge Areas）— 先花 1–2 天建立学科地图，明确"要学什么、不学什么"。
2. **The Linux Command Line（第 7 版）** 或 **鸟哥的 Linux 私房菜** — Linux/命令行/脚本（后续一切工具的前置）。中文习惯者选鸟哥，追求更新选 Shotts。
3. **NIST CSF 2.0**（快速通读）— 建立"防御六职能 + 治理"框架，直接用于量化项目的安全设计。
4. **Security Engineering（第 3 版，读官方样章/第 1-2 版全文）**— 作为**长期案头参考**，不必一次读完，遇到系统设计问题就查对应章。

### 阶段 1 · 应用安全（与你的全栈/AI 项目直接相关，性价比最高）
5. **OWASP Top 10（中文版）** → **Cheat Sheet Series** — 先建立"十大风险 + 每个怎么防"的最小闭环。
6. **PortSwigger Web Security Academy**（边读边做 Lab）— 系统性实操；重点做访问控制、注入、认证、**API 测试**与 **Web LLM attacks**。
7. **OWASP WSTG** — 把零散漏洞知识升级为**可复用测试方法论**。
8. **《白帽子讲 Web 安全》（第 2 版）**— 中文巩固（正规购买/图书馆）。**做到这一步，你的量化前后端加固能力已成型。**

### 阶段 2 · 红蓝队（按兴趣二选一或先蓝后红）
- **蓝队线**：**MITRE ATT&CK**（+ Navigator）→ NIST SP 800-61（事件响应）→ 用 Atomic Red Team / CALDERA 做"进攻验证防御"。
- **红队线**：**OST2**（Vulns1001/1002 → Arch1001 汇编 → 逆向/模糊测试）→ 进攻性实操靶场（供参考，详见 findings-1 靶场部分）。

### 阶段 3 · 专项：密码学（你的数学优势在这里最能放大）
9. **The Joy of Cryptography**（MIT Press 开放获取）— 可证明安全主线，数学背景读起来最顺。
10. **A Graduate Course in Applied Cryptography**（Boneh & Shoup，免费 PDF）— 研究生级进阶（椭圆曲线、格、MPC、阈值密码）。
11. **Serious Cryptography（2nd ed.，付费）**— 工程视角补 TLS/AEAD/后量子；**确认要深入工程再买**。

> 路径压缩建议（给"时间有限、只想加固量化项目"的你）：**阶段 0 第 2/3 项 + 阶段 1 全部 + 阶段 3 第 9 项**即可覆盖绝大部分实际需求；红蓝队留作兴趣延展。

---

## 三、证书路线：费用 / 门槛 / 性价比对比（7 个认证 ≥ 4 个）

> 说明：价格随汇率与机构调价浮动，下表为 2026 年公开信息汇总，**报考前请以官方页面为准**。总成本 = 考试费 + 培训/实验 + 重考 + 维持费（AMF/CPE）。

| 认证 | 机构 | 考试费（约） | 门槛 | 维持 | 定位 | 对你（数学+全栈，做加固）的性价比判断 |
|---|---|---|---|---|---|---|
| **ISC2 CC** | ISC2 | 原「百万人计划」**免费**（2026-05-20 起停止新报名；已发考试码可用至 2026-12-31）；现转付费 | 无 | US$50/年 AMF | 入门基础凭证 | **可选**。若手上还有未过期免费码=零成本，值得考；否则现在**不必花钱考** |
| **CompTIA Security+** | CompTIA | ~US$404–425（+重考同样价） | 无 | 3 年续期 | 求职/合规通用入门证 | **现在不建议考**。它是"求职敲门砖"，对**已就业做加固**的你增益有限 |
| **eJPT** | INE Security | ~US$249 | 无 | — | 首个**实操**渗透证 | **性价比高**。想验证兴趣/入门红队，比 Security+ 更"真"且更便宜 |
| **PNPT** | TCM Security | ~US$499（含**免费重考**） | 无 | — | 实操渗透证，最划算之一 | **推荐（若要红队）**。含实况汇报，贴近真实咨询 |
| **OSCP / PEN-200** | OffSec | ~US$1,649–1,749（套餐含 90 天实验；无年费） | 无硬门槛，需 200–350h 实操 | 无年费 | 红队**硬通货** | **仅当确定转红队才考**。品牌强但成本与时间高，对"加固自己项目"回报低 |
| **CISSP** | ISC2 | US$749（重考 US$749） | **需 5 年相关工作经验** | 120 CPE/3 年 + AMF | 管理/架构/GRC 顶证 | **现在考不了，也不该考**。经验门槛未满足，方向（管理）与你的技术路线不符 |
| **CEH** | EC-Council | ~US$1,199（常需强制培训，总价可超 US$2,500） | 无（但培训成本高） | 3 年 | "理论型"黑客证 | **明确不建议 / 典型"智商税"**。贵、偏记忆、被 OSCP 等实操证替代，招聘需求下降 |

**价格与趋势来源**：
- CISSP/OSCP/Security+ 对比：https://www.yazoul.net/learn/resource/cissp-vs-oscp-vs-security-plus-which-certification-is-worth-it
- 2026 认证费用表（Security+/PenTest+/CySA+/eJPT/PNPT/SAL1/OSCP）：https://hackerdna.com/blog/cybersecurity-certifications
- 费用/时数/通过率/隐蔽成本对比：https://best-it-certifications-reviews.com/blog/cybersecurity-certifications
- Security+/CC/eJPT/CISSP/CISM/OSCP 总成本拆解：http://course.careers/articles/cybersecurity-course-cost
- CEH 需求下降 / 成本：https://aicybercheck.com/knowledge/are_cybersecurity_certifications_worth_it_in_2026.php
- ISC2 CC 免费计划结束公告（官方）：https://www.isc2.org/landing/1mcc ／ 中文：https://www.isc2china.org/one-million-certified-cyber-conclusion/

### 「不值得现在考」的明确结论与理由
1. **CEH（最不推荐）**：费用高（含强制培训可达 $2,500+）、偏理论记忆、市场正被 OSCP/PNPT 等**实操证**取代，需求下滑。**典型智商税**。
2. **CISSP（现在不适合）**：要求 **5 年工作经验**，且面向管理/GRC，与你的技术+数学路线不符。等未来走安全架构/管理时再考虑。
3. **CompTIA Security+（对你当前目标性价比低）**：它解决的是"入行求职/合规"问题，而你已有开发岗位、目标是**给量化项目做安全加固**——把同样的钱和时间投到 **PortSwigger Academy + OWASP + 免费靶场**，能力提升更直接。**（例外：若明确要进美资/国企合规岗，则它仍是必要项。）**
4. **各类"7 天速成 / 包过 / 内部押题"培训证书**：无权威机构背书、无法验证真实能力，属**纯智商税**，一律不建议。
5. **任何"先买 Advanced 证再补技能"的做法**：官方与行业共识是"**先有可实操的角色需求，再选证书**；证书跟着岗位走，不能倒过来"（依据：https://hackerdna.com/blog/cybersecurity-certifications ）。

### 给你的证书行动建议（一句话）
**现阶段：证书一个都不必考。** 把预算（若有）用于 **PortSwigger Academy（免费）+ 一个实操靶场订阅 + 《白帽子讲 Web 安全》正版书**；只有当你要**正式转红队求职**时，再按 **eJPT → PNPT →（需要品牌时）OSCP** 的顺序投入，并**完全跳过 CEH**。

---

## 四、关键结论（面向"量化项目安全加固"的优先级）

1. **最高优先（立刻可用）**：OWASP Top 10（中文）+ Cheat Sheet + PortSwigger Academy（免费、含 API/LLM 攻击）——直接对应你的全栈/AI 项目。
2. **地基补充**：Linux（Shotts/鸟哥）+ NIST CSF 2.0 + CyBOK（地图）。
3. **数学优势放大点**：Joy of Cryptography → Boneh & Shoup（均**官方免费**）；Serious Cryptography 视需要再付费。
4. **长期案头**：Security Engineering（官方样章/旧版全文免费）。
5. **证书**：**现在一个都不考**；远离 CEH；红队方向再看 eJPT/PNPT/OSCP。

---

### 附：合法获取原则（本次调研执行标准）
- 只采用**作者官网 / 官方组织（NIST、MITRE、OWASP、ISC2）/ 出版社官方页 / 开放获取（CC、MIT Press Open Access）**四类渠道。
- 对仅有付费版的教材（《白帽子讲 Web 安全》、Serious Cryptography），**只标注"正规购买 / 图书馆 / 官方试读"**，不提供、不检索任何非授权下载。
- 若某书"网上有免费 PDF"但非官方发布，本文件**不予收录**。
