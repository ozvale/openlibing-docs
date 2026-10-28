# Security Findings

---

## Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 findings identified for this repository._

> All components in this system require authentication through the API Gateway before any action can be performed. The system is classified as `NETWORK_SERVICE` with `Internal Only` reachability — not directly exposed to the public internet. Therefore, no Tier 1 (zero-prerequisite) findings apply.

---

## Tier 2 — Conditional Risk (Authenticated / Single Prerequisite)

### FIND-01: SSH 命令注入风险 — execCommand 参数未充分转义

| Attribute                  | Value                                                                                                                                        |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Critical                                                                                                                                     |
| CVSS 4.0                   | 8.1 (CVSS:4.0/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H)                                                                                           |
| CWE                        | [CWE-78](https://cwe.mitre.org/data/definitions/78.html): OS Command Injection                                                               |
| OWASP                      | A03:2025 – Injection                                                                                                                         |
| Exploitation Prerequisites | Authenticated User                                                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                                                    |
| Remediation Effort         | Medium                                                                                                                                       |
| Mitigation Type            | Standard Mitigation                                                                                                                          |
| Component                  | QemuTaskServiceImpl                                                                                                                          |
| Related Threats            | [T01.E](2-stride-analysis.md#qemutaskserviceimpl), [T01.T](2-stride-analysis.md#qemutaskserviceimpl), [T03.E](2-stride-analysis.md#jschutil) |

#### Description

JschUtil.execCommand() 方法直接将传入的 command 字符串设置为 SSH 执行命令，当 QemuTaskServiceImpl 中构造命令时未对所有变量进行 ShellEscapeUtils.quote() 转义，攻击者可通过构造恶意参数在目标节点上执行任意命令。

#### Evidence

**Prerequisite basis:** 系统通过 API Gateway 提供服务，需要认证用户才能访问。

- JschUtil.java 行 200-210: execCommand 方法直接执行传入的 command 字符串
- QemuTaskServiceImpl.java 行 685-688: 构造 checkCmd 时直接拼接引擎版本参数，未转义
- QemuTaskServiceImpl.java 行 723-724: 拼接 `docker load -i %s` 执行 Docker 操作，变量未转义
- QemuTaskServiceImpl.java 行 492-499: 端口检查命令使用字符串拼接

#### Remediation

1. 所有传递给 execCommand 的变量参数必须使用 ShellEscapeUtils.quote() 进行转义
2. 对命令参数实施白名单校验，只允许合法字符
3. 对关键操作（如 docker load、docker run）的参数格式进行严格校验

#### Verification

- 在 QemuTaskServiceImpl 中搜索所有拼接命令的位置，确认每个变量都经过 ShellEscapeUtils.quote() 处理
- 手动测试注入 payload（如 `; cat /etc/passwd`）验证命令不会被执行

---

### FIND-02: 敏感信息在日志中暴露

| Attribute                  | Value                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                                    |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)                                                           |
| CWE                        | [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                                        |
| Exploitation Prerequisites | Authenticated User                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                    |
| Remediation Effort         | Low                                                                                                          |
| Mitigation Type            | Standard Mitigation                                                                                          |
| Component                  | OperationLogFilter                                                                                           |
| Related Threats            | [T01.I](2-stride-analysis.md#qemutaskserviceimpl), [T12.I](2-stride-analysis.md#operationlogfilter)          |

#### Description

系统日志中可能直接打印包含密码、密钥等敏感信息的内容。QemuTaskServiceImpl 中记录了服务器连接信息（IP、端口、用户名），GlobalExceptionHandler 在错误处理中打印完整堆栈，可能包含数据库连接字符串、SSH 密钥路径等敏感信息。

#### Evidence

**Prerequisite basis:** 日志存储在 MySQL 数据库中，需要认证用户访问。

- QemuTaskServiceImpl.java 行 1625-1640: 日志记录中打印服务器连接信息，可能包含密码字段
- QemuTaskServiceImpl.java 行 1640-1650: 错误处理中打印完整调用栈
- OperationLogFilter: 记录完整请求体和响应体

#### Remediation

1. 配置日志脱敏过滤器，自动替换密码、密钥等字段为 `***`
2. 在 OperationLogFilter 中添加请求体脱敏逻辑
3. 生产环境配置 logback/log4j 的脱敏 pattern

#### Verification

- 审查日志配置，确认敏感字段被正确脱敏
- 发送包含模拟敏感数据的请求，检查日志输出

---

### FIND-03: 异常处理信息泄露

| Attribute                  | Value                                                                                                                    |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                                                |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N)                                                                       |
| CWE                        | [CWE-209](https://cwe.mitre.org/data/definitions/209.html): Generation of Error Message Containing Sensitive Information |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                                                    |
| Exploitation Prerequisites | Authenticated User                                                                                                       |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                                |
| Remediation Effort         | Low                                                                                                                      |
| Mitigation Type            | Standard Mitigation                                                                                                      |
| Component                  | GlobalExceptionHandler                                                                                                   |
| Related Threats            | [T01.I](2-stride-analysis.md#qemutaskserviceimpl), [T09.I](2-stride-analysis.md#globalexceptionhandler)                  |

#### Description

GlobalExceptionHandler 可能将内部异常堆栈、数据库连接信息、SSH 配置等直接暴露给客户端，攻击者可利用这些信息了解系统内部结构。

#### Evidence

**Prerequisite basis:** 异常通过 API 返回给认证用户。

- GlobalExceptionHandler.java: 未区分生产/开发环境，可能暴露详细异常
- QemuTaskServiceImpl 中异常直接抛出未做脱敏
- JschUtil 中 SSH 连接异常可能包含主机信息

#### Remediation

1. 生产环境配置中禁用堆栈跟踪输出
2. 统一错误响应格式，仅返回通用错误码和消息
3. 详细错误信息仅记录到日志，不返回给客户端

#### Verification

- 触发异常场景（如连接拒绝、命令失败），检查 API 响应中不包含堆栈信息
- 验证 `spring.profiles.active=prod` 时错误响应格式

---

### FIND-04: SSH 隧道资源泄漏风险

| Attribute                  | Value                                                                                                          |
| -------------------------- | -------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                      |
| CVSS 4.0                   | 5.0 (CVSS:4.0/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:L)                                                             |
| CWE                        | [CWE-401](https://cwe.mitre.org/data/definitions/401.html): Missing Release of Memory after Effective Lifetime |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                           |
| Exploitation Prerequisites | Authenticated User                                                                                             |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                      |
| Remediation Effort         | Low                                                                                                            |
| Mitigation Type            | Standard Mitigation                                                                                            |
| Component                  | JschUtil                                                                                                       |
| Related Threats            | [T04.A](2-stride-analysis.md#jschutil)                                                                         |

#### Description

虽然代码中已修复了 createTunnel 中 target 连接失败时 proxySession 的清理，但在 saveAutoQemuTask 和 closeAutoQemuTask 的多个 return 路径中，隧道可能未被正确关闭。长时间运行后，代理节点上的 SSH 会话和端口转发可能累积，导致资源耗尽。

#### Evidence

**Prerequisite basis:** 需要认证用户触发任务。

- QemuTaskServiceImpl saveAutoQemuTask: 多个 return true 路径（getContainerNum 方法中）可能跳过 tunnel.close()
- QemuTaskServiceImpl closeAutoQemuTask: 已有的 try-finally 确保了关闭，但嵌套调用中仍可能泄漏
- JschUtil.java:158-186: createTunnel 中 targetSession.connect() 失败时的清理已修复

#### Remediation

1. 在所有 saveAutoQemuTask 的 return 路径前确保 tunnel.close() 被调用
2. 使用 finally 块包裹整个任务执行流程
3. 添加隧道超时自动关闭机制
4. 添加隧道健康检查和定期清理

#### Verification

- 使用代码扫描工具检查所有 return 路径是否覆盖了 tunnel.close()
- 压力测试后检查代理节点 SSH 会话数量

---

### FIND-05: known_hosts 文件权限风险

| Attribute                  | Value                                                                                                             |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                          |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:L/AC:L/PR:L/UI:N/S:C/C:L/I:L/A:N)                                                                |
| CWE                        | [CWE-732](https://cwe.mitre.org/data/definitions/732.html): Incorrect Permission Assignment for Critical Resource |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                              |
| Exploitation Prerequisites | Authenticated User                                                                                                |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                         |
| Remediation Effort         | Low                                                                                                               |
| Mitigation Type            | Standard Mitigation                                                                                               |
| Component                  | JschUtil                                                                                                          |
| Related Threats            | [T03.I](2-stride-analysis.md#jschutil), [T04.T](2-stride-analysis.md#jschutil)                                    |

#### Description

/etc/openlibing/known_hosts 文件用于存储 SSH 主机密钥，但文件权限可能未正确设置。若被低权限用户修改，攻击者可注入恶意主机密钥实施中间人攻击。

#### Evidence

**Prerequisite basis:** 需要容器文件系统访问权限。

- Dockerfile 第 154 行: 创建 `/etc/openlibing` 并授权 openlibing 用户
- JschUtil.java: known_hosts 文件路径为 `/etc/openlibing/known_hosts`
- 需确保 known_hosts 文件权限为 644 或更严格

#### Remediation

1. Dockerfile 中创建 known_hosts 文件时设置正确权限：`chmod 600 /etc/openlibing/known_hosts`
2. 定期校验 known_hosts 文件完整性
3. 使用 `stat` 或等效命令在启动时检查文件权限

#### Verification

- 容器内执行 `ls -la /etc/openlibing/known_hosts` 确认权限
- 尝试用非授权用户修改文件验证被拒绝

---

### FIND-06: 分布式锁竞态条件

| Attribute                  | Value                                                                                                                                                                        |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                                                                     |
| CVSS 4.0                   | 5.9 (CVSS:4.0/AV:N/AC:H/PR:L/UI:N/S:U/C:L/I:L/A:L)                                                                                                                           |
| CWE                        | [CWE-362](https://cwe.mitre.org/data/definitions/362.html): Race Condition Within a Thread                                                                                   |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                                                                                         |
| Exploitation Prerequisites | Authenticated User                                                                                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                                                                                    |
| Remediation Effort         | Medium                                                                                                                                                                       |
| Mitigation Type            | Redesign                                                                                                                                                                     |
| Component                  | DistributedLockServiceImpl                                                                                                                                                   |
| Related Threats            | [T10.T](2-stride-analysis.md#distributedlockserviceimpl), [T10.R](2-stride-analysis.md#distributedlockserviceimpl), [T10.D](2-stride-analysis.md#distributedlockserviceimpl) |

#### Description

分布式锁实现基于 MySQL 行锁，但在高并发场景下可能存在竞态条件。锁的获取和释放不是原子操作，多个实例可能同时获取到同一服务器的锁。

#### Evidence

**Prerequisite basis:** 需要认证用户触发并发任务。

- DistributedLockServiceImpl.java 行 37-70: 锁获取逻辑
- QemuTaskServiceImpl.java 行 389-400: 服务器锁定基于 IP 实现
- 锁超时处理和异常释放不完善

#### Remediation

1. 使用数据库唯一索引 + INSERT ... ON DUPLICATE KEY UPDATE 实现原子锁
2. 添加锁持有者标识和心跳机制
3. 使用 SELECT FOR UPDATE 或 Redis SETNX 实现原子性
4. 锁获取和释放操作加入事务

#### Verification

- 多实例并发压力测试验证锁的正确性
- 代码审查锁获取/释放的原子性

---

### FIND-07: 批量接口操作数量无限制

| Attribute                  | Value                                                                                              |
| -------------------------- | -------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                           |
| CVSS 4.0                   | 4.8 (CVSS:4.0/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:L)                                                 |
| CWE                        | [CWE-400](https://cwe.mitre.org/data/definitions/400.html): Uncontrolled Resource Consumption      |
| OWASP                      | A04:2025 – Insecure Design                                                                         |
| Exploitation Prerequisites | Authenticated User                                                                                 |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                          |
| Remediation Effort         | Low                                                                                                |
| Mitigation Type            | Standard Mitigation                                                                                |
| Component                  | SshProxyController                                                                                 |
| Related Threats            | [T07.D](2-stride-analysis.md#sshproxycontroller), [T07.A](2-stride-analysis.md#sshproxycontroller) |

#### Description

SshProxyController 的 batch 接口允许一次提交任意数量的操作，可能导致 SSH 隧道长时间占用、内存耗尽或目标节点资源耗尽。

#### Evidence

**Prerequisite basis:** 需要认证用户构造大量操作。

- TunnelBatchRequest: operations 列表无长度限制
- 批量操作顺序执行，中间失败不自动回滚
- 单次操作超时未设置或超时过长

#### Remediation

1. 限制单次批量操作数量上限（如 10 个）
2. 设置单次批量操作总超时（如 5 分钟）
3. 添加批量操作进度反馈
4. 部分失败时支持重试

#### Verification

- 构造包含 100+ 操作的请求验证被拒绝
- 并发压力测试验证系统稳定性

---

## Tier 3 — Defense-in-Depth (Prior Compromise / Host Access)

### FIND-08: Docker 镜像安全扫描缺失

| Attribute                  | Value                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                |
| CVSS 4.0                   | 7.5 (CVSS:4.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)                                                       |
| CWE                        | [CWE-1104](https://cwe.mitre.org/data/definitions/1104.html): Use of Unmaintained Third Party Components |
| OWASP                      | A06:2025 – Vulnerable and Outdated Components                                                            |
| Exploitation Prerequisites | Host/OS Access                                                                                           |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                                |
| Remediation Effort         | Medium                                                                                                   |
| Mitigation Type            | Standard Mitigation                                                                                      |
| Component                  | QemuTaskServiceImpl                                                                                      |
| Related Threats            | [T02.I](2-stride-analysis.md#qemutaskserviceimpl), [T02.E](2-stride-analysis.md#qemutaskserviceimpl)     |

#### Description

系统使用 Docker 加载 QEMU 镜像但未对镜像进行安全扫描。Dockerfile 中安装的 openssh-clients 等包可能存在已知漏洞。

#### Evidence

**Prerequisite basis:** 需要 host/OS 级访问来加载恶意镜像。

- Dockerfile: 使用 `openeuler/openeuler:24.03-lts-sp1` 作为基础镜像
- `docker load -i` 命令加载外部镜像，无完整性验证
- 未配置 Trivy/Clair 等镜像扫描工具

#### Remediation

1. 在 CI/CD 流程中集成 Docker 镜像安全扫描（Trivy 或 Clair）
2. 对 Dockerfile 进行定期安全审计
3. 镜像加载前验证签名（如 Docker Content Trust）
4. 定期更新基础镜像和依赖包

#### Verification

- 执行 `trivy image <image>` 确认无高危漏洞
- CI 流程中添加镜像扫描步骤

---

### FIND-09: SSH 密钥文件权限保护不足

| Attribute                  | Value                                                                                                             |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                         |
| CVSS 4.0                   | 7.8 (CVSS:4.0/AV:L/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:N)                                                                |
| CWE                        | [CWE-732](https://cwe.mitre.org/data/definitions/732.html): Incorrect Permission Assignment for Critical Resource |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                              |
| Exploitation Prerequisites | Host/OS Access                                                                                                    |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                                         |
| Remediation Effort         | Medium                                                                                                            |
| Mitigation Type            | Standard Mitigation                                                                                               |
| Component                  | JschUtil                                                                                                          |
| Related Threats            | [T04.I](2-stride-analysis.md#jschutil), [T02.T](2-stride-analysis.md#qemutaskserviceimpl)                         |

#### Description

SSH 私钥文件在容器内的权限可能未正确设置。若密钥文件被非授权用户读取，攻击者可获得代理节点和目标节点的 SSH 访问权限。

#### Evidence

**Prerequisite basis:** 需要容器文件系统访问权限。

- JschUtil: 加载 SSH 私钥文件用于认证
- Dockerfile: 密钥文件可能被复制到容器中
- 密钥文件权限未显式设置为 600

#### Remediation

1. Dockerfile 中确保密钥文件权限为 600：`chmod 600 /path/to/private_key`
2. 使用 Docker secrets 或 HashiCorp Vault 管理密钥
3. 密钥加载后从内存中安全擦除
4. 定期轮换 SSH 密钥

#### Verification

- 容器内执行 `ls -la` 确认密钥文件权限
- 验证密钥仅 root/openlibing 用户可读

---

### FIND-10: 硬编码凭证风险

| Attribute                  | Value                                                                                     |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                 |
| CVSS 4.0                   | 7.2 (CVSS:4.0/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:N)                                        |
| CWE                        | [CWE-798](https://cwe.mitre.org/data/definitions/798.html): Use of Hard-coded Credentials |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                     |
| Exploitation Prerequisites | Host/OS Access                                                                            |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                 |
| Remediation Effort         | Medium                                                                                    |
| Mitigation Type            | Standard Mitigation                                                                       |
| Component                  | QemuTaskServiceImpl                                                                       |
| Related Threats            | [T02.E](2-stride-analysis.md#qemutaskserviceimpl), [T04.E](2-stride-analysis.md#jschutil) |

#### Description

ServerBasicInfoEntity 和 RemoteConnect 实体中存储的密码字段可能以明文形式存在于数据库中。若数据库被攻破，所有服务器的 SSH 凭证将直接暴露。

#### Evidence

**Prerequisite basis:** 需要数据库访问权限。

- entity/qemu/ServerBasicInfoEntity.java 行 31: 密码字段未加密
- entity/nodemanage/ServerBasicInfoEntity.java 行 29: 密码字段未加密
- entity/RemoteConnect.java 行 23: 密码字段未加密
- 密码直接存储在 MySQL 数据库中

#### Remediation

1. 使用 AES-GCM 或 ChaCha20 对称加密存储密码
2. 加密密钥存储在独立的密钥管理系统（Vault/AWS KMS）
3. 应用启动时从密钥管理系统加载密钥
4. 查询时动态解密返回明文

#### Verification

- 检查数据库中密码字段为密文格式
- 代码审查确认加密/解密逻辑覆盖所有读写路径

---

## Threat Coverage Verification

| Threat ID | Finding ID       | Status                               |
| --------- | ---------------- | ------------------------------------ |
| T01.T     | FIND-01          | ✅ Covered                           |
| T01.E     | FIND-01          | ✅ Covered                           |
| T01.D     | —                | 🔄 Mitigated by Platform             |
| T01.I     | FIND-02, FIND-03 | ✅ Covered                           |
| T01.A     | FIND-07          | ✅ Covered                           |
| T03.S     | —                | ✅ Mitigated (StrictHostKeyChecking) |
| T03.E     | FIND-01          | ✅ Covered                           |
| T03.D     | FIND-07          | ✅ Covered                           |
| T04.A     | FIND-04          | ✅ Mitigated                         |
| T04.T     | FIND-05          | ✅ Covered                           |
| T04.I     | FIND-09          | ✅ Covered                           |
| T05.S     | —                | ✅ Mitigated (Gateway Auth)          |
| T05.I     | FIND-02, FIND-03 | ✅ Covered                           |
| T05.D     | FIND-07          | ✅ Covered                           |
| T06.E     | —                | 🔄 Mitigated by Platform             |
| T07.D     | FIND-07          | ✅ Covered                           |
| T07.A     | FIND-07          | ✅ Covered                           |
| T09.I     | FIND-03          | ✅ Covered                           |
| T10.T     | FIND-06          | ✅ Covered                           |
| T10.R     | FIND-06          | ✅ Covered                           |
| T10.D     | FIND-06          | ✅ Covered                           |
| T12.I     | FIND-02          | ✅ Covered                           |
| T13.T     | FIND-01          | ✅ Covered                           |
