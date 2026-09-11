# 网络安全中文资源 + 本地可用工具链调研（findings-3）

> 调研日期：2026-09-10　｜　对象：中文用户（中国大陆网络）、Windows 11 + Python/全栈（FastAPI + React）背景、免费优先、面向量化项目的安全自查
> 检索轮次：中文 ≥1 轮（网络安全的"中文 学习 社区 靶场"）、英文 ≥1 轮（"open source security tools self-host SAST DAST"）；关键工具一律用 **GitHub REST API（api.github.com/repos/…）实测** star / 许可证 / 最近提交时间
> 证据分级：**【官方/实测】**＝官方页面或 GitHub API 直接取证；**【实践观点】**＝第三方评测、社区总结
> 范围限定：只讲"怎么学、用什么练"，聚焦学习与防御；不教具体攻击手法，不做合规法律长篇论述（必要处仅一句提示）

---

## 0. 结论先行

1. **中文资源不缺，缺的是"动手环境"。** 中文社区（FreeBuf / 先知 / 看雪 / 安全客）内容量大且国内直连无障碍，但它们解决"读"，不解决"练"。真正的练习要么用**在线中文靶场**（攻防世界 / CTFHub / i春秋），要么用**本地开源靶场**（Vulhub / Juice Shop / WebGoat，Docker 一键起）。
2. **给你的最优组合不是"红队工具箱"，而是 DevSecOps 四件套。** 你是"能写代码的人"，SAST + 依赖/密钥扫描 + DAST 这条线能直接落在你的 FastAPI + React 项目上，边际收益远高于学 nmap/Metasploit。
3. **最大的工程障碍是"网络"不是"技术"。** Docker Hub 直连基本不可用、GitHub 主站常超时、PyPI/npm 需换源——这些在"国内可访问性风险"一节逐条给了当前可用的替代方案。
4. **有一个"中文资源已停更"的坑**：`Tencent/secguide`（腾讯代码安全指南）与 `HXSecurity/DongTai`（洞态 IAST）都很有名，但已分别停在 2021 / 2025-05，**当"方法论参考"可以，当"活跃项目集成"要谨慎**。

---

## 1. 中文学习资源（≥5 条，含访问地址 / 内容形式 / 更新活跃度 / 证据等级）

### 1.1 社区与资讯门户（解决"读"）

| # | 资源 | 访问地址 | 内容形式 | 更新活跃度 | 证据等级 |
|---|---|---|---|---|---|
| 1 | **FreeBuf**（斗象科技） | https://www.freebuf.com/ | 行业资讯 + 技术专栏 + 漏洞预警 + 工具分享，量最大 | 日更，国内安全媒体第一梯队 | 【实践观点】 |
| 2 | **先知社区**（阿里云） | https://xz.aliyun.com/ | Web 安全实战长文、代码审计、SRC 挖洞思路，原创质量高 | 高频，开发者/白帽聚集 | 【实践观点】 |
| 3 | **看雪论坛**（Kanxue） | https://bbs.kanxue.com/ ｜ https://www.kanxue.com | 逆向工程、二进制安全、加解密、样本分析 | 老牌社区，仍在运营 | 【实践观点】 |
| 4 | **安全客**（360） | https://www.anquanke.com/ | 漏洞分析、0day/APT 报告、CTF 官方 Writeup | 高频，文章深度高 | 【官方/实测 200】 |
| 5 | **奇安信补天社区** | https://forum.butian.net/ | 漏洞挖掘、SRC 交流、众测 | 活跃 | 【实践观点】 |
| 6 | **吾爱破解 52PoJie** | https://www.52pojie.cn/ | 逆向、破解、脱壳、原创工具、病毒分析区 | 超高频，中文逆向圣地 | 【实践观点】 |
| 7 | **长亭 CT Stack 安全社区** | https://stack.chaitin.com/ | 工具库、安全运维、产品文档 | 活跃 | 【实践观点】 |
| 8 | **404StarLink（知道创宇）** | https://github.com/knownsec/404StarLink | **中文安全工具聚合清单**（精选国产开源安全项目） | 实测 API：11.2k★，最近提交 2026-07-31，未归档 | 【官方/实测】 |

> 说明：FreeBuf / 先知 / 看雪 / 52PoJie / 长亭等站点在本调研的自动化环境里返回 000/403（被 WAF/反爬拦截），**这不代表中国大陆住宅网络不可访问**——主流中文资料一致表明它们是国内直连可达的核心站点，仅作"未获自动化确定性证据"标注（见第 4 节）。

### 1.2 中文靶场与知识库（解决"练"）

| # | 资源 | 访问地址 | 内容形式 | 更新活跃度 | 证据等级 |
|---|---|---|---|---|---|
| 9 | **CTF Wiki（中文）** | https://ctf-wiki.org/ | 中文 CTF 知识库（Web/逆向/Pwn/Crypto/Misc 全体系） | GitHub 实测：9.6k★，最近提交 2026-08-23（活跃） | 【官方/实测】 |
| 10 | **攻防世界 XCTF** | https://adworld.xctf.org.cn/ | 国内头部 CTF 平台，新手区 + 竞赛 + 在线环境 | 赛事驱动，持续运营 | 【实践观点】 |
| 11 | **CTFHub** | https://www.ctfhub.com/ | 中文题库 + 靶场 + 技能树（比 XCTF 更"教学向"） | 持续运营 | 【实践观点】 |
| 12 | **Vulhub** | https://vulhub.org/ ｜ https://github.com/vulhub/vulhub | **中文文档的漏洞复现环境库**（docker-compose 一键起） | GitHub 实测：21.2k★，MIT，最近提交 2026-07-22，活跃 | 【官方/实测】 |
| 13 | **i春秋** | https://www.ichunqiu.com/ | 中文体系化课程 + 靶场 + 论坛（部分免费） | 官网在运营 | 【实践观点】 |
| 14 | **国家智慧教育平台·网络安全课堂** | https://www.smartedu.cn/wlaq | 面向校园的零基础科普课程（官方免费） | 国家平台，长期维护 | 【实践观点】 |

### 1.3 中文"代码安全规则"资料（对你项目最直接）

| # | 资源 | 访问地址 | 内容形式 | 更新活跃度 | 证据等级 |
|---|---|---|---|---|---|
| 15 | **腾讯代码安全指南 Tencent/secguide** | https://github.com/Tencent/secguide | 中文安全编码指南，覆盖 **Python / JavaScript / Node / Go / Java / C++**，含"必须/建议"条目与 sink 点清单 | 实测 API：13.5k★，**最近提交 2023-03-20（内容主体 2021 年定稿）**——⚠️ 已停更，作方法论参考 | 【官方/实测】 |
| 16 | **OWASP Cheat Sheet Series**（含中文翻译碎片） | https://github.com/OWASP/CheatSheetSeries | 安全编码速查（英文为主，社区有中文译版） | 实测：33.1k★，CC-BY-SA-4.0，最近提交 2026-09-08，极活跃 | 【官方/实测】 |
| 17 | **国家漏洞库（中文描述）** | https://www.cnvd.org.cn/ ｜ https://www.cnnvd.org.cn/ | 中文漏洞通报、修复方案 | 官方维护 | 【实践观点】 |

> 一句话合规提示：以上靶场/社区都只用于**自有系统或授权环境**的练习；对未授权目标做扫描/渗透违反《网络安全法》与《刑法》285–287 条，此处不展开。

---

## 2. 本地可自建/自装的免费工具（按用途分组，≥6 个）

> 所有条目均以 **GitHub API 实测**给出 star 数、SPDX 许可证、最近提交时间（截至 2026-09-10）。"Windows/WSL"列标注的是**部署友好度**（原生 exe ＞ pip ＞ 仅 WSL/Docker）。

### 2.1 代码审计 / SAST

| 工具 | 仓库 | 许可证 | 实测活跃度 | Windows/WSL 友好度 | 说明 |
|---|---|---|---|---|---|
| **Semgrep OSS** | semgrep/semgrep | LGPL-2.1 | 16.6k★，提交 2026-09-10（极活跃） | ✅ `pip install semgrep` 可用；WSL 更顺 | **多语言 SAST（含 Python + TS/JS）**，规则用 YAML 写，官方规则包 `p/ci`、`p/python`、`p/typescript`、`p/owasp-top-ten` 开箱可用 |
| **Bandit** | PyCQA/bandit | Apache-2.0 | 8.3k★，提交 2026-08-29（活跃） | ✅ pip，Windows 原生可用 | **Python 专用**零配置 SAST，专抓 `eval/exec`、弱哈希、`subprocess` 注入等；FastAPI 后端首选补充 |
| **SonarQube Community Edition** | SonarSource/sonarqube | LGPL-3.0 | 11.0k★，提交 2026-09-09（活跃） | ⚠️ 需 Docker（WSL/Desktop） | 自托管平台，代码质量 + 安全一体，30+ 语言，带 Web 面板与质量门禁 |
| **CodeQL** | github/codeql | 免费额度‑专有 | 官方维护 | ⚠️ 需 GHAS 或 CLI | 污点分析深度最强；**公开仓库免费**，私有仓库需 Advanced Security（付费），个人项目建议只对 public 用 |

### 2.2 依赖与密钥扫描

| 工具 | 仓库 | 许可证 | 实测活跃度 | Windows/WSL 友好度 | 说明 |
|---|---|---|---|---|---|
| **Gitleaks** | gitleaks/gitleaks | MIT | 29.2k★，提交 2026-09-09（极活跃） | ✅ 官方提供 Windows `.exe` release | **密钥/凭据扫描**事实标准，速度快，pre-commit + CI 双用，适合有交易所 API key 的项目 |
| **TruffleHog** | trufflesecurity/trufflehog | AGPL-3.0 | 27.7k★，提交 2026-09-10（极活跃） | ✅ Windows 二进制 | 扫描 + **验证凭据是否仍然有效**（会真实调用 API 校验），比 Gitleaks 更深但更重；⚠️ AGPL 注意商用条款 |
| **pip-audit** | pypa/pip-audit | Apache-2.0 | 1.4k★，提交 2026-09-09（活跃） | ✅ pip，Windows 原生 | **Python 依赖 CVE 审计**（官方 PyPA 出品），直接吃 `requirements.txt` / 已装环境；FastAPI 项目最贴 |
| **detect-secrets** | Yelp/detect-secrets | Apache-2.0 | 4.6k★，提交 2026-04-02（维护中） | ✅ pip | 轻量密钥扫描，与 pre-commit 生态集成好；活跃度低于 Gitleaks |
| **OWASP Dependency-Check** | dependency-check/DependencyCheck | Apache-2.0 | 7.7k★，提交 2026-09-04（活跃） | ⚠️ 需 Java | 老牌 SCA，基于 NVD 匹配 CVE，支持 Python/JS/Java 等；离线能力好但较重 |

### 2.3 Web / API 测试（DAST）

| 工具 | 仓库 | 许可证 | 实测活跃度 | Windows/WSL 友好度 | 说明 |
|---|---|---|---|---|---|
| **OWASP ZAP** | zaproxy/zaproxy | Apache-2.0 | 15.8k★，提交 2026-09-09（极活跃） | ✅ **Windows 原生安装包** + Docker | **免费 DAST 事实标准**：被动扫描、主动扫描、API 扫描、拦截代理；`zap-baseline.py` 可一条命令跑基线 |
| **Nuclei** | projectdiscovery/nuclei | MIT | 31.1k★，提交 2026-09-10（极活跃） | ✅ Windows 二进制 | YAML 模板驱动的**快速漏洞/暴露面扫描**（9,000+ 社区模板），适合批量探自己资产的暴露面 |
| **sqlmap** | sqlmapproject/sqlmap | GPL-2.0（GitHub 标 NOASSERTION） | 38.4k★，提交 2026-09-08（活跃） | ✅ pip / WSL | SQL 注入检测利用；**仅限自有/授权目标**，学习用请对着 Juice Shop / DVWA |
| **Burp Suite Community** | portswigger.net | 专有（社区版免费） | 官方维护 | ✅ Windows 原生 | 手测 Web/API 的行业标准；社区版免费但限速、无自动扫描 |

### 2.4 流量与日志分析（蓝队/取证）

| 工具 | 仓库 | 许可证 | 实测活跃度 | Windows/WSL 友好度 | 说明 |
|---|---|---|---|---|---|
| **Wireshark** | wireshark/wireshark | GPL-2.0 | 官方维护 | ✅ Windows 原生 | 抓包 + 协议解析，学习 HTTP/TLS 握手的最直观工具 |
| **Suricata** | OISF/suricata | GPL-2.0 | 6.6k★，提交 2026-09-08（活跃） | ⚠️ 主要 WSL/Linux | 高性能 IDS/IPS，规则驱动告警，蓝队入门首选之一 |
| **Zeek** | zeek/zeek | BSD-3（GitHub 标 NOASSERTION） | 8.0k★，提交 2026-09-09（活跃） | ⚠️ 主要 WSL/Linux | 把流量转成结构化日志（conn/http/dns…），配合分析脚本做行为检测 |
| **tcpdump / tshark** | 系统自带 | BSD/GPL | — | ✅ WSL 原生 | 轻量抓包，脚本化分析的基础 |

### 2.5 容器与云配置审计

| 工具 | 仓库 | 许可证 | 实测活跃度 | Windows/WSL 友好度 | 说明 |
|---|---|---|---|---|---|
| **Trivy** | aquasecurity/trivy | Apache-2.0 | **37.9k★**，提交 2026-09-09（极活跃） | ✅ Windows 二进制 + Docker | **一把梭**：依赖 CVE + 密钥 + IaC 配置 + 容器镜像 + SBOM，全覆盖，单二进制零依赖，强烈推荐 |
| **Checkov** | bridgecrewio/checkov | Apache-2.0 | 9.0k★，提交 2026-09-05（活跃） | ✅ pip / Docker | IaC（Terraform/K8s/Helm/Compose）配置错误扫描，策略丰富 |
| **kube-bench** | aquasecurity/kube-bench | Apache-2.0 | 8.2k★，提交 2026-09-07（活跃） | ⚠️ 需 K8s 环境 | 按 CIS Benchmark 检查 K8s 集群与节点配置 |
| **Syft / Grype** | anchore/syft ｜ anchore/grype | Apache-2.0 | 9.5k★ / 12.9k★，提交 2026-09-10（极活跃） | ✅ Windows 二进制 | Syft 生成 SBOM，Grype 基于 SBOM 查漏洞，供应链审计组合 |
| **OPA** | open-policy-agent/opa | Apache-2.0 | 12.2k★，提交 2026-09-10（极活跃） | ✅ Windows 二进制 | Policy-as-Code（Rego），把安全策略固化进 CI |
| **Harbor** | goharbor/harbor | Apache-2.0 | 29.3k★，提交 2026-09-10（极活跃） | ⚠️ 需 Docker | 自托管私有镜像仓库，自带镜像扫描（配 Trivy）——避开第三方 Docker 镜像源的供应链风险 |

### 2.6 AI / LLM 安全（你已做 AI 开发，附带）

| 工具 | 仓库 | 许可证 | 实测活跃度 | Windows/WSL 友好度 | 说明 |
|---|---|---|---|---|---|
| **promptfoo** | promptfoo/promptfoo | MIT | 25.0k★，提交 2026-09-10（极活跃） | ✅ npm | LLM 应用红队/评测框架，可测试提示注入、越狱、数据泄露，适合量化项目里的"智能助手"模块 |
| **NVIDIA garak** | NVIDIA/garak | Apache-2.0 | 9.2k★，提交 2026-09-09（活跃） | ✅ pip | LLM 漏洞扫描器，覆盖幻觉、提示注入、越狱等探测 |

### 2.7 国产/中文开源安全工具（补充，注意停更风险）

| 工具 | 地址 | 许可证 | 实测活跃度 | 说明 |
|---|---|---|---|---|
| **洞态 DongTai IAST** | github.com/HXSecurity/DongTai ｜ doc.dongtai.io | Apache-2.0 | 1.3k★，**最近提交 2025-05-22（已停更约 16 个月）** | 被动插桩式 IAST，**支持 Java + Python**，DevSecOps 场景好；⚠️ 社区版本地化部署需申请，且已停更，谨慎选型 |
| **HFish 蜜罐** | hfish.net ｜ github.com/hacklcx/HFish | 免费开源 | 4.5k★，提交 2026-03-13 | 微步在线出品，一行命令部署蜜罐，捕获攻击载荷，适合自建观测点 |
| **veinmind-tools**（长亭容器安全） | github.com/chaitin/veinmind-tools | MIT | 1.7k★，**最近提交 2024-01-10（停滞）** | 容器镜像/运行时安全工具集；⚠️ 已长期不更新 |
| **pocsuite3**（知道创宇） | github.com/knownsec/pocsuite3 | GPL-2.0 | 3.9k★，最近提交 2025-02-28 | 中文 PoC 框架；⚠️ 更新放缓，且属攻击面工具，仅授权环境用 |

---

## 3. 在你的量化项目上落地安全自查：最小工具链（4 个 + 执行顺序）

> 目标：用**最少工具**覆盖"密钥 → 源码 → 依赖/容器 → 运行时"四道关；全部免费，全部可在 Windows（原生或 WSL）跑，也能直接进 GitHub Actions。
> 你已有一个 skill `github-api-deploy`，说明你的 GitHub 主域可能被阻——这套流水线**建议本地 pre-commit + 走 API 的 CI**两条腿。

### 工具链（4 个）

| 顺序 | 工具 | 作用 | 一条命令示例 | 为什么选它 |
|---|---|---|---|---|
| 0 | **Gitleaks** | 密钥/凭据扫描 | `gitleaks detect --source . --redact -v` | 量化项目最怕**交易所 API key / 数据库密码**入库泄露，先堵这个 |
| 1 | **Semgrep CE** | 源码 SAST（Python + TS/JS 一次覆盖） | `semgrep scan --config p/ci --config p/python --config p/typescript .` | 一套工具同时管 FastAPI 和 React，规则可自定义 |
| 2 | **Trivy** | 依赖 CVE + 密钥 + 配置 + 容器镜像 | `trivy fs --scanners vuln,secret,misconfig .`　`trivy image <your-image>` | 用一个二进制约等于 pip-audit + npm audit + checkov 三个 |
| 3 | **OWASP ZAP（baseline）** | 运行时 DAST（安全头/CORS/认证/注入面） | `docker run -t ghcr.io/zaproxy/zaproxy zap-baseline.py -t http://host.docker.internal:8000` | 唯一能"真打一次运行中的服务"的免费标准工具 |

### 执行顺序与 rationale

```
提交前(pre-commit)         CI(每次 PR)                部署前(本地/预发)
┌──────────────┐      ┌──────────────────────┐      ┌────────────────────┐
│ 0 Gitleaks   │  →   │ 1 Semgrep → 2 Trivy  │  →   │ 3 ZAP baseline     │
│ 堵住密钥泄露 │      │ 查源码、查依赖/镜像  │      │ 打运行中的 API 服务 │
└──────────────┘      └──────────────────────┘      └────────────────────┘
   "左移"最左端                                            
```

- **为什么 Gitleaks 在前**：密钥泄露是"一旦发生就不可逆"的最高危事件（对方可直接下单/转账），且修复成本从"删一个 commit"到"轮换全部密钥"，必须第一道关。
- **为什么 Semgrep 在 Trivy 前**：源码级问题（越权逻辑、注入 sink）只能改代码，依赖问题多数是"升级版本"——先处理"要动手改的"，再处理"可以自动升级的"。
- **为什么 ZAP 放最后**：DAST 需要应用真实跑起来，只能放在部署前；它的价值是捕获"代码里看不出来"的运行时问题（缺安全响应头、CORS 过宽、认证绕过）。
- **WSL 提示**：Gitleaks / Trivy 有 Windows 原生 exe，Semgrep 可 `pip install`，ZAP 有 Windows 安装包——**全部不必依赖 WSL**；但若你已装 Kali WSL，直接用 Linux 包更顺。

### 可选替换（仍在 4 个以内）
- 若**不做容器**：把第 2 步 Trivy 换成 `pip-audit -r requirements.txt` + `npm audit`（Python 侧吃 PyPA 官方源，更专）。
- 若项目里有"智能助手/LLM"模块：在第 1 步后加一次 `promptfoo` 做提示注入红队（≤30 分钟，MIT 免费）。

---

## 4. 国内可访问性风险（实事求是）

> 说明：本节的"实测状态码"来自**自动化沙箱环境**，**不能等同大陆住宅网络的真实结果**——很多中文站返回 000/403 是被 WAF/反爬拦截，而非国家层面不可达。凡涉及需"额外网络条件"的，均结合多方资料标注。

### 4.1 需要额外网络条件（如实标注）

| 目标 | 风险 | 建议替代 |
|---|---|---|
| **GitHub 主站 / raw.githubusercontent.com** | 大陆住宅网络常见 `github.com` 超时、`raw` 被阻；**但 `api.github.com` 通常可达**（本调研全程用 API 完成核对） | 用 Gitee 镜像、ghproxy 类加速；或用本仓库已有的 `github-api-deploy` 思路（PAT + 全 API 操作）；release 二进制可能需代理 |
| **Docker Hub** | 直连极慢/失败，且匿名有拉取限速 | 配国内镜像。**2026-03 多方实测仍可用**：轩辕 `docker.xuanyuan.me`、毫秒 `docker.1ms.run`、DaoCloud `docker.m.daocloud.io`；**已失效**：USTC、清华 TUNA、网易 163（据 2026-03 报道）。⚠️ 第三方镜像有**供应链投毒风险**，生产环境应改用 Harbor 自建/官方源 |
| **PyPI** | 直连慢 | 清华 `https://pypi.tuna.tsinghua.edu.cn/simple` 或阿里云 PyPI 镜像 |
| **npm** | 直连慢 | `https://registry.npmmirror.com`（淘宝源） |
| **PortSwigger / TryHackMe / HTB / Coursera / Google** | 需国际网络，速度慢、部分时段不稳 | 用中文替代（攻防世界 / CTFHub / i春秋）；或错峰访问 |
| **SonarQube / Juice Shop / Vulhub / HFish 等 Docker 镜像** | 依赖 Docker Hub 拉取 | 先配好镜像加速，或从 Gitee 镜像构建 |

### 4.2 国内直连无障碍（可放心用）

- **中文社区**：FreeBuf、先知、看雪、安全客、补天、52PoJie、CT Stack
- **中文靶场/知识库**：CTF Wiki、攻防世界、CTFHub、i春秋、Vulhub、国家智慧教育平台
- **官方漏洞库**：CNVD、CNNVD、CNCERT
- **GitHub 上开源工具的源码**：走 Gitee 镜像或 API 方式获取（见 4.1）

### 4.3 其他风险提醒

1. **停更风险**：`Tencent/secguide`（2023-03）、`DongTai`（2025-05）、`veinmind-tools`（2024-01）都属"知名但不再活跃"——**引用方法论可以，集成做 CI 要自己兜底**。
2. **许可证风险**：TruffleHog 是 **AGPL-3.0**（商用/闭源分发需注意），sqlmap 是 **GPL-2.0**，其余本条链推荐工具均为 MIT / Apache-2.0 / LGPL，个人项目基本无碍。
3. **镜像供应链风险**：第三方 Docker 加速器"有备案、会过滤恶意镜像"是宣传口径，**不等于审计保证**；对量化这种资产敏感的项目，建议关键镜像用 Harbor 自建或锁定 digest。

---

## 5. 来源 URL 汇总

### 中文资源
1. FreeBuf — https://www.freebuf.com/
2. 先知社区 — https://xz.aliyun.com/
3. 看雪 — https://bbs.kanxue.com/ ｜ https://www.kanxue.com
4. 安全客 — https://www.anquanke.com/
5. 奇安信补天 — https://forum.butian.net/
6. 吾爱破解 52PoJie — https://www.52pojie.cn/
7. 长亭 CT Stack — https://stack.chaitin.com/
8. CTF Wiki — https://ctf-wiki.org/ ｜ https://github.com/ctf-wiki/ctf-wiki
9. 攻防世界 XCTF — https://adworld.xctf.org.cn/
10. CTFHub — https://www.ctfhub.com/
11. Vulhub — https://vulhub.org/ ｜ https://github.com/vulhub/vulhub
12. i春秋 — https://www.ichunqiu.com/
13. 国家智慧教育平台·网络安全课堂 — https://www.smartedu.cn/wlaq
14. 腾讯代码安全指南 — https://github.com/Tencent/secguide
15. OWASP Cheat Sheet Series — https://github.com/OWASP/CheatSheetSeries
16. CNVD — https://www.cnvd.org.cn/ ｜ CNNVD — https://www.cnnvd.org.cn/ ｜ CNCERT — https://www.cert.org.cn/
17. 404StarLink 中文安全工具聚合 — https://github.com/knownsec/404StarLink
18. 中科院大学外部资源平台（中文资源导航）— https://inc.ucas.ac.cn/index.php/zh/wlaqe/sfwzgl-4

### 工具（均经 GitHub API 实测）
19. Semgrep — https://github.com/semgrep/semgrep
20. Bandit — https://github.com/PyCQA/bandit
21. SonarQube — https://github.com/SonarSource/sonarqube
22. Gitleaks — https://github.com/gitleaks/gitleaks
23. TruffleHog — https://github.com/trufflesecurity/trufflehog
24. pip-audit — https://github.com/pypa/pip-audit
25. detect-secrets — https://github.com/Yelp/detect-secrets
26. OWASP Dependency-Check — https://github.com/dependency-check/DependencyCheck
27. OWASP ZAP — https://github.com/zaproxy/zaproxy
28. Nuclei — https://github.com/projectdiscovery/nuclei
29. sqlmap — https://github.com/sqlmapproject/sqlmap
30. Suricata — https://github.com/OISF/suricata ｜ Zeek — https://github.com/zeek/zeek
31. Trivy — https://github.com/aquasecurity/trivy
32. Checkov — https://github.com/bridgecrewio/checkov ｜ kube-bench — https://github.com/aquasecurity/kube-bench
33. Syft — https://github.com/anchore/syft ｜ Grype — https://github.com/anchore/grype
34. OPA — https://github.com/open-policy-agent/opa ｜ Harbor — https://github.com/goharbor/harbor
35. promptfoo — https://github.com/promptfoo/promptfoo ｜ NVIDIA garak — https://github.com/NVIDIA/garak
36. DongTai IAST — https://github.com/HXSecurity/DongTai ｜ https://doc.dongtai.io/
37. HFish — https://hfish.net ｜ https://github.com/hacklcx/HFish
38. veinmind-tools — https://github.com/chaitin/veinmind-tools ｜ pocsuite3 — https://github.com/knownsec/pocsuite3
39. Juice Shop — https://github.com/juice-shop/juice-shop ｜ WebGoat — https://github.com/WebGoat/WebGoat
40. PayloadsAllTheThings（防御参考靶场思路）— https://github.com/swisskyrepo/PayloadsAllTheThings

### 网络/镜像资料（第 4 节）
41. Docker 国内镜像源实测汇总 2026-03 — https://developer.cloud.tencent.com/article/2647596
42. Docker 镜像加速源汇总 2026 — https://www.leavescn.com/Articles/Content/4029
43. Docker on Windows + WSL2 安全实验环境搭建 — https://cyberspotacademy.com/building-a-security-testbed-with-docker-on-windows-a-complete-enterprise-guide/
44. WSL2 + Kali 渗透环境搭建（中文）— https://blog.csdn.net/weixin_29233333/article/details/159367901
45. WSL 上搭 WordPress CVE 靶场（含 systemd/Docker 配置）— https://cyberresearchhub.com/building-a-wordpress-cve-lab-for-bug-bounty-practice/

---

## 6. 证据与时效说明

- **工具活跃度/许可证**：全部通过 `https://api.github.com/repos/{owner}/{repo}` 于 2026-09-10 实测（star 数、`license.spdx_id`、`pushed_at`、`archived`），属可复现的**一手证据**。
- **中文资源更新活跃度**：CTF Wiki、Vulhub、secguide、DongTai 等以 GitHub `pushed_at` 为准；FreeBuf/先知/看雪等门户的"日更/高频"来自多方社区描述（【实践观点】）。
- **国内可访问性**：本环境的 curl 实测仅作参考（多个中文站被 WAF/反爬返回 000/403），**真实可达性请以你本机网络为准**；Docker 镜像源可用性引用 2026-03 的第三方实测，时效约半年，建议使用前用 `docker pull` 快速验证。
- **可复现命令**（校验任意仓库）：
  ```bash
  curl -s https://api.github.com/repos/<owner>/<repo> | \
    python -c "import sys,json;d=json.load(sys.stdin);print((d.get('license') or {}).get('spdx_id'),d.get('stargazers_count'),d.get('pushed_at'),d.get('archived'))"
  ```
