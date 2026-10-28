# 安全威胁分析报告：openlibing-eureka

| 项 | 内容 |
|---|---|
| 仓库路径 | `D:\skill\skill收集\repo\openlibing-eureka` |
| 分析日期 | 2026-09-02 |
| 分析方法 | 静态代码审计（STRIDE-A 威胁建模 + 配置/依赖/部署检查） |
| 报告语言 | 中文 |
| 部署分类 | 容器化基础设施服务（K8s 集群内服务注册中心，强制 HTTPS，监听 9000 端口，hostname `*.svc.cluster.local`） |

---

## 一、系统概述

### 1.1 用途与技术栈

OpenLiBing 平台的 **Eureka 服务注册发现中心**（`@EnableEurekaServer`）。所有微服务向其注册、从其拉取注册表，是平台服务间调用的"通讯录"，一旦被投毒将导致内网流量劫持。

- Java 21、Spring Boot 3.4.x、`spring-cloud-starter-netflix-eureka-server:4.3.0`、Spring Security 6.5.9（HTTP Basic）
- 容器：openeuler 基础镜像 + RASP agent，强制 TLS1.2/1.3（PKCS12 证书，关闭非安全端口），非 root 运行
- 入口：`EurekaServerApplication.java:23`；安全链：`SecurityConfig.java:24`；健康检查：`HealthCheckController.java:17`

### 1.2 组件与信任边界

| 组件 ID | 锚点 | 职责 | 信任边界 |
|---|---|---|---|
| EurekaServer | `EurekaServerApplication.java:23` | 注册中心服务端 | 集群内基础设施 |
| SecurityConfig | `SecurityConfig.java:24` | HTTP Basic + CSRF 禁用 | 认证边界 |
| HealthCheckController | `HealthCheckController.java:17` | `/health-check`、`/health-beat` | K8s 探针 → 服务 |
| EurekaClients | 各微服务（eureka client） | 注册/拉取/心跳，共享 Basic 凭据 | 服务 ↔ 注册中心 |
| Dashboard | Eureka 内置首页 `/` + `/eureka/apps` | 服务拓扑展示 | 运维/浏览器 → 注册中心 |
| K8sCluster | 部署环境 | 网络可达性边界 | 集群网络 |

**关键信任边界**：注册中心写接口（注册/注销/下架）是内网信任的核心——任何能向其写数据的主体都能篡改服务路由。当前仅靠一对**所有微服务共享的静态 HTTP Basic 凭据**保护，且无 mTLS。

---

## 二、STRIDE-A 威胁分析汇总

| STRIDE 类别 | 威胁数 | 代表性威胁 |
|---|---|---|
| S 仿冒 | 2 | 无 mTLS，凭据泄露即可冒充合法节点注册；Basic 无账号粒度 |
| T 篡改 | 3 | 注册恶意实例/摘除合法实例（注册表投毒）；CSRF 关闭；单节点自注册配置错误 |
| R 抵赖 | 1 | 共享凭据无法区分/审计调用方 |
| I 信息泄露 | 2 | Dashboard/`/eureka/apps` 暴露全量内网拓扑；actuator 未显式收敛 |
| D 拒绝服务 | 3 | 暴力破解无限速；摘除实例致服务中断；自我保护关闭 + 短租约误摘 |
| E 权限提升 | 2 | 凭据泄露后注册恶意服务劫持内网调用流量；Dashboard 被爆破 |
| A 业务滥用 | 1 | 注册大量伪造实例消耗注册表/干扰发现 |

### 关键威胁场景

**场景 1（T/E，注册表投毒）**：任一微服务或任一环境泄露共享 Basic 凭据（凭据在所有服务配置中相同，`application-beta.yml:23-27` 服务端登录与 client 复制凭据同为 `${eureka_name}/${eureka_password}`）→ 攻击者 `POST /eureka/apps` 注册恶意实例，或 `DELETE` 摘除合法实例 → 内网调用被路由到攻击者实例（凭据/令牌窃取）或造成大面积拒绝服务。CSRF 全局禁用（`SecurityConfig.java:38`）、无 mTLS（`client-auth: none`）使该攻击门槛极低。

**场景 2（I/E）**：HTTP Basic 浏览器弹窗无失败限速 → 暴力破解 → 进入 Dashboard 获取全部内网服务实例（主机、端口、状态），为横向移动提供地图。

**场景 3（D，配置缺陷）**：单节点却 `registerWithEureka/fetchRegistry=true` 指向自身（`application-beta.yml:18-22`），叠加 `enable-self-preservation: false`（:12/:15）与极短租约（心跳 8s/过期 16s），网络抖动即引发注册表大面积摘除。

---

## 三、安全发现明细

### 高危

#### FIND-01：注册写接口与 Dashboard 仅靠"单一共享 HTTP Basic 凭据"保护，CSRF 全局关闭

| 属性 | 内容 |
|---|---|
| STRIDE | S / T / E |
| CWE | [CWE-522](https://cwe.mitre.org/data/definitions/522.html) 凭据保护不足（共享凭据）；[CWE-352](https://cwe.mitre.org/data/definitions/352.html) CSRF；[CWE-307](https://cwe.mitre.org/data/definitions/307.html) 认证尝试未限制 |
| OWASP | A01:2025 – Broken Access Control；A07:2025 |
| 利用前提 | 集群网络可达注册中心 9000 端口，且获取/爆破出共享凭据 |
| 证据 | `SecurityConfig.java:36-38` `anyRequest().authenticated()` + `httpBasic()` + `csrf.disable()`；`application.yml:10-11` 与 `application-beta.yml:23-27` 服务端凭据与 eureka client 复制凭据同为 `${eureka_name}/${eureka_password}`；Dashboard `/` 与 `/eureka/apps` 同域，无限流 |
| 风险 | 注册/注销/下架等改写操作仅靠一对全服务共享的静态凭据；任一服务/环境泄露凭据即可注册恶意实例、摘除合法实例（注册表投毒/DoS），进而劫持内网调用；Basic 无账号粒度、无审计、无登录失败锁定，可暴力破解；Dashboard 泄露全量内网拓扑。 |
| 修复建议 | ① 启用 **mTLS**（`client-auth: need`）以证书身份做服务认证，替代/叠加静态密码；② 为注册与拉取使用独立凭据；③ 写操作在网络层限制内网网段/来源，并监控异常注册/下架；④ Dashboard 加 IP 白名单与登录限速，考虑表单登录 + 失败锁定。 |
| 修复成本 | 中 |

### 中危

#### FIND-02：未启用 TLS 双向认证，无法验证对端节点/服务身份

- STRIDE：S ｜ CWE：[CWE-295](https://cwe.mitre.org/data/definitions/295.html) 证书校验不当；[CWE-300](https://cwe.mitre.org/data/definitions/300.html) ｜ OWASP：A02:2025
- 证据：`application-gama.yml:11`（prod :11 同）`client-auth: none`；`application-beta.yml:22` defaultZone 指向自身 HTTPS。
- 风险：仅服务端单向认证，网络可达 + 凭据泄露即可冒充合法节点。
- 建议：启用 `client-auth: need` 并分发客户端证书。
- 修复成本：中

#### FIND-03：单节点以 client 模式自注册/自拉取 + 关闭自我保护 + 极短租约（可用性风险）

- STRIDE：T / D ｜ CWE：[CWE-1188](https://cwe.mitre.org/data/definitions/1188.html) 不安全默认配置 ｜ OWASP：A05:2025
- 证据：`application-beta.yml:18-22`（gama :21-25、prod :21-25）`registerWithEureka: true` / `fetchRegistry: true` / defaultZone 指向 `localhost:${server.port}`；`:12/:15` `enable-self-preservation: false`；心跳 8s、过期 16s。
- 风险：单机部署应 `false/false`；当前配置叠加自我保护关闭与短租约，网络抖动时易引发注册表大面积摘除（级联故障）。
- 建议：单节点设 `registerWithEureka/fetchRegistry=false`；生产开启自我保护或合理调大租约/阈值。
- 修复成本：低

#### FIND-04：Actuator 端点未显式收敛暴露面，与弱 Basic 凭据共用认证域

- STRIDE：I ｜ CWE：[CWE-200](https://cwe.mitre.org/data/definitions/200.html) 信息暴露；[CWE-552](https://cwe.mitre.org/data/definitions/552.html) ｜ OWASP：A05:2025
- 证据：`application-gama.yml:32`（prod :32、beta :29）`status-page-url: .../actuator/info`；仓内未见 `management.endpoints.web.exposure.include` 显式配置。
- 风险：actuator 虽被 `authenticated()` 覆盖，但与 Eureka 同一静态凭据；若外部配置放开 `env/heapdump/beans` 等将造成敏感信息/内存泄露。
- 建议：显式 `management.endpoints.web.exposure.include=health,info`；actuator 独立管理端口、仅内网可达、独立更强访问控制。
- 修复成本：低

### 低危 / 信息

#### FIND-05：monitor.sh 含危险清理操作（当前未启用）

- STRIDE：T / D ｜ CWE：[CWE-73](https://cwe.mitre.org/data/definitions/73.html) 外部控制路径；[CWE-377](https://cwe.mitre.org/data/definitions/377.html) ｜ OWASP：A05:2025
- 证据：`monitor.sh:10-12` `rm -f .../openlibing-eureka-1.0.jar`、`rm -rf "$DST_PATH"/*`（变量未校验）、`rm -rf /tmp`；`entrypoint.sh:4` 该调用被注释（未启用）。
- 建议：删除该脚本或固定/白名单校验路径，禁止 `rm -rf /tmp`。
- 修复成本：低

#### FIND-06：构建期联网动态抓取 JRE 无完整性校验，基础镜像用 `latest`

- STRIDE：T ｜ CWE：[CWE-494](https://cwe.mitre.org/data/definitions/494.html) 下载代码未校验完整性；[CWE-1357](https://cwe.mitre.org/data/definitions/1357.html) ｜ OWASP：A08:2025
- 证据：`Dockerfile:1` `FROM ...openeuler-base:latest`；`:195-196` wget 动态解析"最新"Adoptium JRE，无 checksum/签名。
- 建议：固定基础镜像 digest 与版本；JRE 下载后校验 SHA256/签名。
- 修复成本：低

#### FIND-07：健康探针接口与安全链关系需确认

- STRIDE：R / D ｜ CWE：[CWE-1188](https://cwe.mitre.org/data/definitions/1188.html) ｜ OWASP：A05:2025
- 证据：`HealthCheckController.java:23,33` `/health-check`、`/health-beat` 在 `anyRequest().authenticated()` 下。
- 风险：K8s 存活/就绪探针若不带凭据将收到 401，可能影响探针判定（误重启）。
- 建议：确认探针带凭据，或对这两个只读固定返回探针显式 `permitAll`（风险低）。
- 修复成本：低

#### FIND-08：依赖 `commons-lang:commons-lang:1.0.1` 异常古老

- STRIDE：T ｜ CWE：[CWE-1104](https://cwe.mitre.org/data/definitions/1104.html) 使用过时组件 ｜ OWASP：A06:2025
- 证据：`pom.xml:107` `commons-lang:commons-lang:1.0.1`（2002 年）。
- 建议：迁移 `org.apache.commons:commons-lang3`。
- 修复成本：低

### 正面安全实践（已核实）

- 数据库/证书/登录凭据全部经环境变量注入（`application.yml:10-11`、`application-gama.yml:8` `${KEY_STORE_PASSWORD}`），yml/Java 中无硬编码；证书 `openlibing.pfx/cacerts` 未入库。
- 强制 TLS1.2/1.3、关闭 HTTP 明文端口（`non-secure-port-enabled: false`，`application-gama.yml:30`）。
- 容器基线加固完善：非 root（`Dockerfile:217`）、SSH 加固（禁 root/密码登录）、sysctl 防重定向/源路由、删除 gdb/strace/netcat/perl 等调试工具、umask 0077。
- eureka-server 4.3.0、spring-security 6.5.9、xstream 1.4.21（已修历史反序列化 CVE）、httpclient 4.5.14/5.4.4 均较新；未直接引入 log4j2/fastjson/shiro。

---

## 四、行动摘要（整改优先级）

### Quick Wins（低成本快速修复）

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-03 | 单节点关闭自注册/自拉取，恢复合理租约与自我保护 | 低 |
| FIND-04 | 显式收敛 actuator 暴露为 health,info | 低 |
| FIND-05 | 清理/修正 monitor.sh 危险命令 | 低 |
| FIND-06 | 固定基础镜像版本、JRE 校验 SHA256 | 低 |
| FIND-07 | 健康探针与安全链对齐 | 低 |
| FIND-08 | commons-lang 迁移 lang3 | 低 |

### 需专项处理

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-01/02 | 启用 mTLS 服务身份认证、独立凭据、Dashboard 限速与白名单、写操作网络限制与监控 | 中 |

---

## 五、分析假设与需验证项

1. 注册中心 9000 端口的实际网络可达范围（是否仅集群内、是否有 NetworkPolicy）需在 K8s 环境核验；若仅 Pod 网络可达且已启用网络策略，FIND-01 的外部可利用性降低，但共享凭据 + 无 mTLS 的体系性风险仍在。
2. `${eureka_name}/${eureka_password}` 实际凭据强度与轮换策略需在配置中心/环境变量核验。
3. 是否存在 Spring Boot Admin 或其他系统复用该 Basic 凭据访问 actuator，需在收敛端点前确认兼容性。

## 六、参考标准

- STRIDE-A 威胁建模；OWASP Top 10:2025；CWE/MITRE；CIS Kubernetes/Docker 基线；Spring Cloud Eureka 安全最佳实践（mTLS、基本认证加固）。
