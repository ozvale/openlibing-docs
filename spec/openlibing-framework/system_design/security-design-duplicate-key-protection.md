# 安全设计：产品/项目/角色唯一约束与防重复插入

## 变更标识

| 字段 | 值 |
|------|-----|
| 仓库 | openlibing-framework |
| Commit | 9a6f479b |
| 变更类型 | 安全加固（防御性） |
| 设计师 | AI 安全架构师 |
| 设计日期 | 2026-09-08 |

## 1. 认证授权

**本变更不涉及认证授权改动。**

新增接口复用已有鉴权体系（Bearer token + JWT），未引入新的认证端点或权限模型。

## 2. 输入输出

### 输入校验

- **校验位置**：Controller 层已有 `@Valid` 参数校验；Service 层通过 `DuplicateKeyException` 捕获做二次保障
- **校验策略**：MyBatis 参数化查询天然防止 SQL 注入，无需额外拼接处理

### 输出安全

- 异常时返回用户友好的业务提示（"产业已存在"、"项目名称已存在"、"角色重复"），**不暴露**数据库堆栈或内部错误信息，符合 Fail Secure 原则
- 正常返回 `DataResult.successData()` / `DataResult.failureMessage()`，统一格式

## 3. 数据保护

### 分类分级

| 表 | 字段 | 分级 | 说明 |
|----|------|------|------|
| product_info | product_name | 内部 | 产品名称，业务标识 |
| project_info | project_name | 内部 | 项目名称，业务标识 |
| role_type_info | role, role_name | 内部 | 角色标识与名称 |

### 传输加密

- 应用层 → 数据库：JDBC 连接使用 TLS（由 MySQL JDBC 驱动配置 `useSSL=true` 控制）
- 客户端 → 网关：HTTPS（由 API 网关统一管控）

### 存储加密

- 当前字段均为业务标识文本，不涉及个人隐私（PII）或机密数据，无需字段级加密
- 若后续角色名称包含敏感信息，可考虑引入 AES-256 字段级加密 + KMS 密钥管理

## 4. 依赖供应链

**本变更不引入新的第三方依赖。**

- `DuplicateKeyException` 来自 `spring-tx` 已有依赖，无需新增
- Liquibase changelog 使用项目已有配置，无新增依赖

## 5. 部署运行时

### 配置管理

- 无需新增配置项
- 数据库连接凭据由已有 `application.yml` + Apollo 配置中心管理，不入仓

### 审计日志

变更涉及的三个 Service 在 `DuplicateKeyException` 捕获后均通过 `logger.warn` 记录告警日志：

```java
logger.warn("Failed to insert duplicate product names: {}", productName, e);
logger.warn("Failed to insert duplicate project names: {}", projectDTO.getProjectName(), e);
logger.warn("Failed to insert duplicate role names: role={}, roleName={}", roleInfoDTO.getRole(), roleInfoDTO.getRoleName(), e);
```

**日志安全性**：
- 日志级别为 `warn`，可被监控系统捕获告警
- 重复尝试的 `productName` / `projectName` / `role` / `roleName` 是业务标识，非敏感信息
- 异常堆栈 `e` 仅记录到日志文件，不返回客户端

### 双实例部署

本变更的核心目标之一就是解决双实例部署下的并发重复插入问题。方案不依赖外部锁（Redis/ZooKeeper），因此：

- 无单点故障
- 无锁超时问题
- 无跨实例通信开销
- 数据库作为最终仲裁者，天然保证一致性

## 6. 失败模式

### Fail Secure

| 场景 | 默认行为 | 安全性 |
|------|---------|--------|
| 数据库唯一约束冲突 | 捕获 DuplicateKeyException → 返回 failureMessage | 安全（拒绝，不暴露细节） |
| 数据库连接异常 | 抛出 DataAccessException，由全局异常处理器处理 | 安全（拒绝，统一错误响应） |
| 双实例同时插入 | 一个成功，一个 DuplicateKeyException | 安全（数据完整性不受影响） |

### 应急响应

- **误报处理**：如果用户报告"明明是新名称却说已存在"，检查 `product_info` / `project_info` / `role_type_info` 表是否已有该名称的另一条记录（可能是软删除或历史数据）
- **唯一约束冲突回滚**：Liquibase changelog 已提供 `rollback` 标签，可通过 `liquibase rollback` 撤销约束

## 7. 验证计划

### 单元测试

| 用例 | 预期 | 覆盖 |
|------|------|------|
| 插入不存在的 product_name | 成功 | ProductServiceImpl |
| 插入已存在的 product_name | DuplicateKeyException → failureMessage | ProductServiceImpl |
| 插入不存在的 project_name | 成功 | ProjectServiceImpl |
| 插入已存在的 project_name | DuplicateKeyException → failureMessage | ProjectServiceImpl |
| 插入不存在的 role/role_name | 成功 | RoleServiceImpl |
| 插入已存在的 role | DuplicateKeyException → failureMessage | RoleServiceImpl |
| 插入已存在的 role_name | DuplicateKeyException → failureMessage | RoleServiceImpl |

### 集成测试

- 模拟双实例并发调用同一接口，验证只有一个成功，另一个返回已存在提示
- 验证数据库约束生效：直接通过 SQL 插入重复数据应被拒绝

### 事后审查

- 已交由 `gitcode-security-check` 审查确认，无新增安全问题

## 8. 设计决策记录

| 决策 | 方案 | 替代方案 | 理由 |
|------|------|---------|------|
| 并发控制 | 数据库唯一约束 + DuplicateKeyException 捕获 | SELECT ... FOR UPDATE / Redis 分布式锁 | 最轻量、无额外依赖、数据库天然原子性 |
| 异常提示 | 用户友好的业务提示 | 直接抛异常或返回堆栈 | 符合 Fail Secure，不泄露内部信息 |
| 日志级别 | warn | error / info | warn 可触发告警但不过度恐慌 |
| 约束变更 | Liquibase changelog（带 precondition） | 手动 DDL 脚本 | 与现有数据库变更管理流程一致，可回滚 |