# IT-ICSL 安全送检专项排查 — 技术设计

## 方案概述

不改业务功能与对外接口契约，按「入口校验 → 运行期防护 → 输出脱敏 → 依赖治理」四层做安全加固，
并用部门扫描工具（SpotBugs / SCA / 其余 7 类）做闭环验证。代码侧交付已在分支
`fix-ip-or-hostname-validation` 完成（master..HEAD：61 commits / 102 files / +3606 −5578，
HEAD `21f6c01`）。

## 架构决策

| 决策 | 内容 | 原因 |
|---|---|---|
| D1 输入校验分层 | `ShellEscapeUtils` 管「格式与 shell 元字符」，`IpPolicyValidator` 管「网络位置」 | `127.0.0.1`、`169.254.169.254` 都是合法 IPv4，格式校验拦不住（H-0004 / CWE-918） |
| D2 私网段放行 | 仅拒绝无可能作为部署目标的保留地址（`0/8`、`127/8`、`169.254/16`、`224/4`、`240/4`、`::`、`::1`、`fe80::/10`、`ff00::/8`） | 私网段是平台节点的正常部署目标，硬封会打断功能 |
| D3 不做 DNS 解析 | 主机名一律放行 | 对不可信输入发起 DNS 查询本身是风险（CWE-350） |
| D4 日志双层防护 | 业务代码用 `LogSanitizer`，logback 全局 `%replace` 兜底；`%msg`/`%wex` 走脱敏转换器 | 单点遗漏时仍有全局兜底，覆盖控制字符注入（CWE-117）与敏感数据外泄 |
| D5 凭证不出对象 | 10 个含凭据的实体统一 `@ToString.Exclude`；异常只输出类型/固定文案（`ExceptionSummary`） | 防止 toString、异常堆栈、日志回显明文（CWE-798 / CWE-1258） |
| D6 内部接口 fail-closed | 共享密钥由 Apollo 下发密文，启动后解密；解密失败即拒绝，仅健康检查豁免 | 内部接口不能被「配置缺失」降级为免认证 |
| D7 并发部署串行化 | 按 `qemu_ip_<ip>` 抢分布式锁，锁带 ownerToken，获取不完整直接中止部署 | 避免同机并发部署导致 NBD / iptables / 容器互相破坏 |
| D8 依赖版本下限强制 | maven-enforcer 强制 `jsch >= 2.28.5`（CVE-2023-48762 Terrapin），BOM 上限修正 | 依赖审计要求关键组件不低于安全版本 |

## 代码落点

| 风险类别 | 主要落点 | 验证方式 |
|---|---|---|
| SSRF / CWE-918 | `utils/IpPolicyValidator`、`ServerResourceServiceImpl#checkServerInput`、指定 IP 部署链路 | `IpPolicyValidatorTest`、`ServerResourceServiceImplTest` |
| 命令 / 路径注入 | `utils/ShellEscapeUtils`（`isSafeIpOrHostname` / `isSafeFileName` / `isSafeFilePath`）+ 调用侧统一 `quote` | `ServerResourceServiceImplTest`（deployPath 用例）、`QemuTaskServiceImplTest` |
| 日志注入 CWE-117 | `utils/LogSanitizer`、`logback-spring.xml` 的 `%replace` | `LogSanitizerTest` |
| 日志敏感数据 | `utils/SensitiveDataConverter`、`SensitiveThrowableConverter`（logback `conversionRule`） | `SensitiveDataConverterTest` |
| 异常信息 CWE-1258 | `utils/ExceptionSummary`（类型 / reason 固定文案） | `ExceptionSummaryTest` |
| 凭据 toString CWE-798 | `@ToString.Exclude`：`RemoteConnect`、`QemuRemoteConnect`、`ServerBasicInfoEntity`（两套）、`NodeInfoEntity`（两套）、`QemuNodeInfoEntity`、`QemuTaskConfigEntity`、`SimulationVerificationEnvNodeInfoEntity`、`LockEntity` | `EntityValidationTest` + 人工核对 |
| 加密异常包装 | `JschUtil#sanitizedJSchException`（不把原始异常透传给上层） | `JschUtilTest` |
| SSH 加固 | `JschUtil`：HostKey 校验、强算法白名单、命令白名单 + 危险字符黑名单、隧道复用与关闭 | `JschUtilTest` |
| 内部接口鉴权 | `filter/InternalSimulationAuthFilter`：`X-Openlibing-Internal-Token`，Apollo 密文密钥，fail-closed，`/simulation/health-check` 豁免 | 手工验证 + 接口联调 |
| 审计日志 | `filter/OperationLogFilter` → `operate.log`；客户端 IP 统一 `OperationLogClientIp` 采集 | 日志核查 |
| 密码 / 密钥 | `AesGcmUtil`、`PasswordUtils`、`SecureRandomUtils`；凭据以 `SecurityUtil` 密文落库 | `AesGcmUtilTest`、`PasswordUtilsTest`、`SecureRandomUtilsTest` |
| 分布式锁 | `DistributedLockServiceImpl`（ownerToken 校验）、`QemuTaskServiceImpl#getServerLock` | `DistributedLockServiceImplTest` |
| 依赖治理 | `pom.xml`：enforcer 版本下限、BOM 下限修正、移除重复高危依赖 | 构建 enforcer + 依赖扫描 |

## 扫描证据矩阵（第二轮，截止 10-30）

| 工具 | 证据 | 状态 |
|---|---|---|
| SpotBugs | `58cd5d6e...log`：`DLS_DEAD_LOCAL_STORE` @ `QemuTaskServiceImpl#executeScriptAndCheckContainer:794` | **已修复**（commit `21f6c01` 删除未使用局部变量），待重跑出 0 issue 报告 |
| SCA 版本扫描 | `j_hDmUE7Up.txt`：`unconfirmedFileNum=3` → `Access control check failed`（2026-10-29 11:49） | **未闭环**：需在平台确认 3 个文件后重扫 |
| 安全编译选项扫描 | 待补 | 未开始 |
| SecBinaryCheck | 待补 | 未开始 |
| nmap 端口扫描 | 待补 | 未开始 |
| 墨菲 / SC-SAST | 待补 | 未开始 |
| SenInfo 敏感信息 | 待补 | 未开始 |
| C-Spider | 待补 | 未开始 |
| SEC-SecEncryScan | 待补 | 未开始 |
| 开源合规 | 待补 | 未开始 |

## 风险 & 缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| SCA 的 3 个未确认文件未处理 | 10-30 截止前第二轮无法闭环 | 今天在平台确认/豁免后重扫 |
| 其余 7 类工具无报告 | 送检材料缺项 | 按工具逐项执行并将报告归档到 `issue_docs/openlibing-simulation/48/` |
| 安全设计类文档缺失（6 份） | IT-ICSL 材料不完整 | 基于现有 11 份 `system_design` 产出初稿后再评审 |
| 校验加严导致合法请求被拒 | 功能回归 | 已有单测覆盖边界；上线前用真实节点 IP/账号做一次联调 |
| 部署流程被 2 小时安装超时卡住 | 关闭/部署状态停滞 | 已把目录清理改为尽力而为（`QemuTaskServiceImpl#deleteTaskPath`），失败只告警不阻断 |

## 跨仓影响

- 仅 `openlibing-simulation` 与 `openlibing-docs` 两个仓；
- 无外部接口契约变化；依赖 `openlibing-common` 1.0.21.2 BOM 提供的安全工具与加解密能力。

## 验证计划

| 验证项 | 命令 / 方式 | 通过标准 |
|---|---|---|
| 构建 | `mvn -q -DskipTests clean package` | BUILD SUCCESS，enforcer 通过（jsch ≥ 2.28.5） |
| 单元测试 | `mvn test` | 26 个测试类全绿；JaCoCo 行覆盖 ≥ 20% |
| SpotBugs | 重跑「安全编码扫描」流水线 | Total Issues = 0 |
| SCA 版本扫描 | 平台确认 3 个未确认文件后重扫 | `unconfirmedFileNum = 0`，`Access control check` 通过 |
| 接口联调 | `/simulation/manage/server/basic/add|update`、`/simulation/qemu/auto/task` | 合法参数 200；非法 IP / 非法 user / 非法 deployPath 返回 400 |
| 审计日志 | 检查 `operate.log` | 每条请求有 JSON 记录，`operator_ip` 为真实客户端地址 |

> 说明：本地终端 `mvn` 不在 PATH（PowerShell profile 加载失败），构建与单测以 CI 流水线结果为准；
> 本地仅能做 IDE 诊断与代码走查。

