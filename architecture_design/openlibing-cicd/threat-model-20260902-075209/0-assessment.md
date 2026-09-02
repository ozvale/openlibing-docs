# Security Assessment

---

## Report Files

| File | Description |
|------|-------------|
| [0-assessment.md](0-assessment.md) | This document — executive summary, risk rating, action plan, metadata |
| [0.1-architecture.md](0.1-architecture.md) | Architecture overview, components, scenarios, tech stack |
| [1-threatmodel.md](1-threatmodel.md) | Threat model DFD diagram with element, flow, and boundary tables |
| [1.1-threatmodel.mmd](1.1-threatmodel.mmd) | Pure Mermaid DFD source file |
| [1.2-threatmodel-summary.mmd](1.2-threatmodel-summary.mmd) | Summary DFD for large systems |
| [2-stride-analysis.md](2-stride-analysis.md) | Full STRIDE-A analysis for all components |
| [3-findings.md](3-findings.md) | Prioritized security findings with remediation |

---

## Executive Summary

openlibing-cicd 是 openLiBing 平台的 CI/CD 核心服务，单进程 Spring Boot 应用，对外经华为云 APIG 网关统一接入，内部以 RabbitMQ 事件驱动、MySQL 持久化、Redis 缓存，配置与密钥托管于 Nacos。系统消费 GitCode/Gitee Webhook 事件触发流水线与 PR 自动化，并向华为云与三方平台回写状态。本次分析采用 STRIDE-A（STRIDE + Abuse）方法论，对全部 26 个系统元素、35 条数据流、2 个信任边界进行了威胁建模。

整体安全态势为**风险偏高**。系统的信任模型严重依赖 APIG 网关这一外部边界：多处业务入口（遗留 Gitee webhook、CrossRegion 状态回写、内部机机接口）在服务内**不实施鉴权或验签**，而身份来源又信任客户端传入的 userId 与仅解码不验签的 JWT，导致"网关层鉴权被绕过即可直达未设防业务接口"的攻击路径。同时凭据管理高度集中（Nacos 托管全部密钥 + 解密密钥共置），一旦配置中心或数据库失陷可形成全链路凭据接管。好消息是：GitCode 链路 HMAC 验签、MQ 死信/延迟重试、日志脱敏等既有控制已具备，且 Tier 1 直接可利用面集中在少数遗留入口，收敛成本相对可控。

The analysis covers 26 system elements across 2 trust boundaries.

### Risk Rating: Elevated

评级为 Elevated（偏高）而非 Critical，原因在于：影响最重的 Tier 1 发现（FIND-01/02/03）均位于**遗留/跨区域入口**，可在网关侧先行收敛或下线；同时系统核心链路（GitCode HMAC 验签、权限参数化查询、prod 环境 MQ/Redis TLS、日志脱敏）已具备基本防线，直接无前置条件触发的完全接管场景需要网关路由同时失守。但鉴权信任模型（客户端可控 userId + JWT 不验签）是系统性架构缺陷，配合 FIND-08/12 的环境性弱点，实际可利用性高于一般 Elevated 水平，应在短周期内优先处理 Tier 1 与 FIND-05。

> **Note on threat counts:** This analysis identified 64 threats across 25 components. This count reflects comprehensive STRIDE-A coverage, not systemic insecurity. Of these, **19 are directly exploitable** without prerequisites (Tier 1). The remaining 45 represent conditional risks and defense-in-depth considerations.

---

## Action Summary

| Tier | Description | Threats | Findings | Priority |
|------|-------------|---------|----------|----------|
| [Tier 1](3-findings.md#tier-1--direct-exposure-no-prerequisites) | Directly exploitable | 19 | 4 | 🔴 Critical Risk |
| [Tier 2](3-findings.md#tier-2--conditional-risk-authenticated--single-prerequisite) | Requires authenticated access | 36 | 7 | 🟠 Elevated Risk |
| [Tier 3](3-findings.md#tier-3--defense-in-depth-prior-compromise--host-access) | Requires prior compromise | 9 | 3 | 🟡 Moderate Risk |
| **Total** | | **64** | **14** | |

### Priority by Tier and CVSS Score (Top 10)

| Finding | Tier | CVSS Score | SDL Severity | Title |
|---------|------|------------|-------------|-------|
| [FIND-01](3-findings.md#find-01-gitee-webhook-遗留端点无服务内验签可伪造事件触发流水线) | T1 | 9.3 | Critical | Gitee Webhook 遗留端点无服务内验签，可伪造事件触发流水线 |
| [FIND-02](3-findings.md#find-02-crossregion-对外接口缺少鉴权可篡改门禁状态并泄露流水线信息) | T1 | 8.6 | Important | CrossRegion 对外接口缺少鉴权，可篡改门禁状态并泄露流水线信息 |
| [FIND-03](3-findings.md#find-03-gitee-验签不覆盖请求体且无时间窗可重放篡改事件) | T1 | 8.2 | Important | Gitee 验签不覆盖请求体且无时间窗，可重放/篡改事件 |
| [FIND-04](3-findings.md#find-04-匿名访问判定在流水线无资源配置时默认放行) | T1 | 7.5 | Moderate | 匿名访问判定在流水线无资源配置时默认放行 |
| [FIND-05](3-findings.md#find-05-jwt-仅解码不验签且-userid-客户端可控可冒用身份越权) | T2 | 8.1 | Important | JWT 仅解码不验签且 userId 客户端可控，可冒用身份越权 |
| [FIND-06](3-findings.md#find-06-华为云客户端部分链路关闭-ssl-证书校验) | T2 | 7.3 | Important | 华为云客户端部分链路关闭 SSL 证书校验 |
| [FIND-08](3-findings.md#find-08-rabbitmqredis-非-prod-环境明文传输敏感数据) | T2 | 6.9 | Moderate | RabbitMQ/Redis 非 prod 环境明文传输敏感数据 |
| [FIND-09](3-findings.md#find-09-xxl-job-任务参数作为可信输入可被恶意调度滥用) | T2 | 6.9 | Moderate | XXL-Job 任务参数作为可信输入，可被恶意调度滥用 |
| [FIND-10](3-findings.md#find-10-obs-导出签名-url-的-objectkey-归属校验缺失待验证) | T2 | 6.5 | Moderate | OBS 导出签名 URL 的 objectKey 归属校验缺失（待验证） |
| [FIND-07](3-findings.md#find-07-内部机机接口无服务内鉴权内部网络者可触发任意流水线) | T2 | 6.3 | Important | 内部机机接口无服务内鉴权，内部网络者可触发任意流水线 |

### Quick Wins

| Finding | Title | Why Quick |
|---------|-------|-----------|
| [FIND-04](3-findings.md#find-04-匿名访问判定在流水线无资源配置时默认放行) | 匿名访问判定在流水线无资源配置时默认放行 | Tier 1 + Low effort：将空 sources 从"匿名放行"改为"未配置/需显式公开标记"，单点改动即消除一个无前置条件的越权面 |
| [FIND-11](3-findings.md#find-11-redis-公开仓缓存-key-无分隔符拼接存在碰撞可致匿名越权) | Redis 公开仓缓存 key 无分隔符拼接存在碰撞，可致匿名越权 | Tier 2 + Low effort：缓存 key 改为分隔符/哈希拼接，一处改动即消除碰撞型越权 |

---

## Analysis Context & Assumptions

### Analysis Scope

| Constraint | Description |
|------------|-------------|
| Scope | openlibing-cicd 仓全量安全威胁建模（控制器、鉴权、消费者、任务、三方客户端、配置） |
| Excluded | 外部平台内部实现（GitCode/Gitee/华为云/APIG 平台侧）、前端代码、部署编排清单（K8s 清单不在本仓） |
| Focus Areas | 认证/鉴权信任模型、Webhook 验签、凭据与密钥管理、消息/缓存链路、内部接口暴露、日志与审计 |

### Infrastructure Context

| Category | Discovered from Codebase | Findings Affected |
|----------|--------------------------|-------------------|
| Deployment Model | 单进程 Spring Boot，Docker/K8s 集群部署，经华为云 APIG 网关接入，见 [0.1-architecture.md](0.1-architecture.md#deployment-model) | 全部 findings 的暴露面判定 |
| Network Exposure | 全部入站流量经 APIG；MQ/Redis/MySQL/Nacos/XXL-Job 仅集群内网，见 [0.1-architecture.md](0.1-architecture.md#deployment-model) | FIND-07, FIND-08, FIND-09 |
| Credential Management | 凭据与解密密钥 `security.part1` 托管于 Nacos，`SecurityUtil`/Jasypt 统一解密，见 [0.1-architecture.md](0.1-architecture.md#security-infrastructure-inventory) | FIND-12, FIND-05 |
| TLS Usage | prod 环境 MQ/Redis 启用 TLS，非 prod 明文；`HwCloudClient.buildPipelineSslHttpsClient(false)` 部分链路关闭校验，见 [0.1-architecture.md](0.1-architecture.md#security-infrastructure-inventory) | FIND-06, FIND-08 |
| Auth Architecture | 自研 `AuthInterceptor` + `@CheckPermission`/`@ProjectAuth`，身份取自客户端参数 userId/projectId；`JwtUtils` 仅 decode 不 verify，见 [0.1-architecture.md](0.1-architecture.md#security-infrastructure-inventory) | FIND-04, FIND-05 |
| Webhook Trust | GitCode 链路 HMAC-SHA256 验签；Gitee 链路 token+timestamp（不含 body、无时间窗）；遗留入口无服务内验签，见 [0.1-architecture.md](0.1-architecture.md#security-infrastructure-inventory) | FIND-01, FIND-02, FIND-03 |

### Needs Verification

| Item | Question | What to Check | Why Uncertain |
|------|----------|---------------|---------------|
| FIND-10 objectKey 归属 | `PipelineControllerV2.exportBuildLog` 生成的 OBS objectKey 是否绑定流水线/用户归属？ | 检查 `ObsBucketServiceImpl.getSignedUrl` 调用链与 objectKey 拼接逻辑 | 代码路径未完整确认，存在"参数可控 + 无归属校验"的可能 |
| `security.part1` 存放位置 | 解密密钥是存放于 Nacos 配置还是环境变量？ | 确认生产部署中 `security.part1` 的下发方式 | 影响 FIND-12 的实际利用难度 |
| APIG 网关路由范围 | 网关是否将 `/internal/**`、`/cross-region/**`、`/webhookEvent/**` 暴露到外部？ | 核对 APIG 路由与 ACL 配置（网关配置不在本仓） | 决定 FIND-01/02/07 是否可由外部直接触达 |
| 非 prod 网络分段 | 非 prod 环境内网是否对 MQ/Redis 明文链路可窃听？ | 确认非 prod 集群网络策略与 VPC 隔离 | 影响 FIND-08 的实际可利用性 |
| XXL-Job 权限边界 | 谁可操作 XXL-Job 任务参数（jobParam）？ | 确认调度中心访问控制与账号权限 | 影响 FIND-09 的前置条件等级 |

### Finding Overrides

| Finding ID | Original Severity | Override | Justification | New Status |
|------------|-------------------|----------|---------------|------------|
| — | — | — | No overrides applied. Update this section after review. | — |

### Additional Notes

用户要求对 openlibing-cicd 仓执行安全威胁分析，并将结果归档至 openlibing-docs 仓的 `architecture_design/openlibing-cicd` 目录。分析基线为 `release_20260831_iter2` 分支（commit `e478943ce`）。FIND-10 标记为"待验证"，需结合代码进一步确认 objectKey 归属校验。

---

## References Consulted

### Security Standards

| Standard | URL | How Used |
|----------|-----|----------|
| Microsoft SDL Bug Bar | https://www.microsoft.com/en-us/msrc/sdlbugbar | Severity classification |
| OWASP Top 10:2025 | https://owasp.org/Top10/2025/ | Threat categorization |
| CVSS 4.0 | https://www.first.org/cvss/v4.0/specification-document | Risk scoring |
| CWE | https://cwe.mitre.org/ | Weakness classification |
| STRIDE | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats | Threat enumeration methodology |

### Component Documentation

| Component | Documentation URL | Relevant Section |
|-----------|------------------|------------------|
| Spring Boot | https://docs.spring.io/spring-boot/docs/current/reference/html/ | Security / Web |
| Nacos | https://nacos.io/docs/latest/guide/user/auth/ | 配置与权限控制 |
| RabbitMQ TLS | https://www.rabbitmq.com/docs/ssl | 传输加密 |
| Redis TLS | https://redis.io/docs/management/security/encryption/ | 传输加密 |
| XXL-Job | https://www.xuxueli.com/xxl-job/ | 任务参数与鉴权 |
| HuaweiCloud OBS SDK | https://support.huaweicloud.com/obs/ | 签名 URL 与 AK/SK |

---

## Report Metadata

| Field | Value |
|-------|-------|
| Source Location | `c:\Users\Administrator\Documents\openlibing\openlibing-cicd` |
| Git Repository | `https://gitcode.com/openlibing/openlibing-cicd.git` |
| Git Branch | `release_20260831_iter2` |
| Git Commit | `e478943ce` (`2026-09-01`) |
| Model | `DeepSeek-V4-Flash 正式版` |
| Machine Name | `MS-JDBCAWDMUGAI` |
| Analysis Started | `2026-09-02 07:52:09 UTC` |
| Analysis Completed | `2026-09-02 08:43:19 UTC` |
| Duration | `00:51:10` |
| Output Folder | `threat-model-20260902-075209` |
| Prompt | `Use Skill: threat-model-analyst 帮我安全威胁分析 openlibing-cicd 仓，并把结果上传到 openlibing-docs仓，归档到 architecture_design/openlibing-cicd下` |

---

## Classification Reference

| Classification | Values |
|---------------|--------|
| **Exploitability Tiers** | **T1** Direct Exposure (no prerequisites) · **T2** Conditional Risk (single prerequisite) · **T3** Defense-in-Depth (multiple prerequisites or infrastructure access) |
| **STRIDE + Abuse** | **S** Spoofing · **T** Tampering · **R** Repudiation · **I** Information Disclosure · **D** Denial of Service · **E** Elevation of Privilege · **A** Abuse (feature misuse) |
| **SDL Severity** | `Critical` · `Important` · `Moderate` · `Low` |
| **Remediation Effort** | `Low` · `Medium` · `High` |
| **Mitigation Type** | `Redesign` · `Standard Mitigation` · `Custom Mitigation` · `Existing Control` · `Accept Risk` · `Transfer Risk` |
| **Threat Status** | `Open` · `Mitigated` · `Platform` |
| **Incremental Tags** | `[Existing]` · `[Fixed]` · `[Partial]` · `[New]` · `[Removed]` (incremental reports only) |
| **CVSS** | CVSS 4.0 vector with `CVSS:4.0/` prefix |
| **CWE** | Hyperlinked CWE ID (e.g., [CWE-306](https://cwe.mitre.org/data/definitions/306.html)) |
| **OWASP** | OWASP Top 10:2025 mapping (e.g., A01:2025 – Broken Access Control) |
