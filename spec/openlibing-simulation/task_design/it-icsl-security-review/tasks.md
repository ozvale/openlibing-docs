# IT-ICSL 安全送检专项排查 — 实现任务

> 分支：`fix-ip-or-hostname-validation`（业务仓） / `spec-openlibing-simulation-it-icsl-security-review`（docs 仓）
> 进度：13/52 complete

## 阶段 0：代码侧安全整改（已完成部分）

- [x] SSRF 保留地址策略：`IpPolicyValidator` + `ServerResourceServiceImpl#checkServerInput` + 单测
- [x] 路径 / 命令注入：`ShellEscapeUtils`（`isSafeIpOrHostname` / `isSafeFileName` / `isSafeFilePath`）落地到 server / extend / 任务链路
- [x] 日志注入（CWE-117）：`LogSanitizer` + logback `%replace` 全局兜底 + `LogSanitizerTest`
- [x] 日志敏感数据脱敏：`SensitiveDataConverter` / `SensitiveThrowableConverter` + 单测
- [x] 日志调试信息（CWE-1258）：`ExceptionSummary` 统一降级 + 单测
- [x] 凭据 toString（CWE-798）：10 个实体 `@ToString.Exclude`
- [x] 加密异常包装：`JschUtil#sanitizedJSchException`
- [x] SSH 加固：HostKey 校验、强算法白名单、命令白名单 + 危险字符黑名单、隧道复用
- [x] 内部接口鉴权：`InternalSimulationAuthFilter`（Apollo 密文密钥、fail-closed、健康检查豁免）
- [x] 审计日志：`OperationLogFilter` → `operate.log`，客户端 IP 统一采集
- [x] 分布式锁：`DistributedLockServiceImpl` ownerToken + `qemu_ip_<ip>` 串行化部署
- [x] 依赖治理：enforcer 强制 `jsch >= 2.28.5`、BOM 下限修正、移除重复高危依赖
- [x] SpotBugs `DLS_DEAD_LOCAL_STORE` 修复（commit `21f6c01`）
- [ ] SpotBugs 复扫并归档 0 issue 报告
- [ ] SCA 版本扫描 3 个 `unconfirmedFileNum` 确认后重扫（截止 10-30）

## 阶段 1：业务信息梳理（09-24）

- [ ] 服务信息：服务名称、部署架构、依赖组件
- [ ] 对外接口清单：路径、方法、认证方式
- [ ] 数据流向与认证方式说明

## 阶段 2：安全设计及威胁分析（10-09）

- [ ] lowlevel 威胁分析
- [ ] 架构设计说明书
- [ ] AI 安全威胁分析
- [ ] 通信矩阵
- [ ] 安全组网架构图
- [ ] 运维安全架构图
- [ ] 模块安全威胁建模（skill）分析记录
- [ ] argus 漏洞挖掘结论

## 阶段 3：第一轮安全扫描（09-24）

- [ ] 安全编译选项扫描报告
- [ ] SecBinaryCheck 二进制安全检查报告
- [ ] nmap 端口扫描报告
- [ ] 墨菲 / SC-SAST 静态代码扫描报告
- [ ] SenInfo 敏感信息扫描报告
- [ ] C-Spider 代码安全分析报告
- [ ] SEC-SecEncryScan 加密安全扫描报告
- [ ] 开源合规扫描报告

## 阶段 4：安全配置排查（10-12）

- [ ] 注册中心安全配置核查（Eureka / Nacos）
- [ ] 配置中心安全配置核查（Apollo）

## 阶段 5：安全专项排查（09-30 ~ 10-23）

- [ ] 安全红线落地检查
- [ ] 安全功能规范 checklist 核查
- [ ] 编码要求 checklist 核查
- [ ] TOP 问题排查
- [ ] 4 类常见问题：注入 / XSS / 越权 / 敏感信息泄露
- [ ] Web 应用安全开发规范核查
- [ ] 安全隐私测试用例基线核查
- [ ] 业务逻辑安全排查
- [ ] 审计日志完整性检查
- [ ] 权限最小化原则核查

## 阶段 6：第二轮安全扫描（10-30）

- [ ] 8 类工具全量重扫
- [ ] 第一轮问题逐项闭环确认（问题 → 修复 commit → 复扫通过）
- [ ] 证据归档到 `openlibing-docs/issue_docs/openlibing-simulation/48/`

## 阶段 7：交付（Phase 4 / Phase 5）

- [ ] 业务 PR（`Refs #48` + `ai-assisted` 标签）
- [ ] docs PR（本 spec + 归档材料）
- [ ] Phase 5 归档：`archive.md`（用户触发后执行）
