# 威胁模型：产品/项目/角色唯一约束与防重复插入

## 变更标识

| 字段     | 值                                                      |
| -------- | ------------------------------------------------------- |
| 仓库     | openlibing-framework                                    |
| Commit   | 9a6f479b                                                |
| 变更类型 | 安全加固（防御性）                                      |
| 涉及模块 | ProductServiceImpl, ProjectServiceImpl, RoleServiceImpl |
| 数据库表 | product_info, project_info, role_type_info              |

## 资产清单

| 资产                            | 分类 | 责任域   | 备注                         |
| ------------------------------- | ---- | -------- | ---------------------------- |
| product_info.product_name       | 内部 | 业务服务 | 产品名称，业务标识           |
| project_info.project_name       | 内部 | 业务服务 | 项目名称，业务标识           |
| role_type_info.role / role_name | 内部 | 业务服务 | 角色标识与名称，权限模型基础 |

## 信任边界

- 客户端 → API 网关：已鉴权（Bearer token）
- API 网关 → 业务服务：内网，token 透传
- 业务服务 → 数据库：内网，JDBC 连接池，账号最小权限

## 数据流

```
客户端 → POST /product/add → API网关 → ProductServiceImpl.addProductInfo → MyBatis INSERT → MySQL(product_info)
客户端 → POST /project/add → API网关 → ProjectServiceImpl.addProject       → MyBatis INSERT → MySQL(project_info)
客户端 → POST /role/add     → API网关 → RoleServiceImpl.addRole             → MyBatis INSERT → MySQL(role_type_info)
```

## STRIDE 评估

| 资产           | S   | T   | R   | I   | D   | E   | 缓解措施                                  |
| -------------- | --- | --- | --- | --- | --- | --- | ----------------------------------------- |
| product_info   | 低  | 中  | 低  | 低  | 低  | 中  | 唯一约束 + DuplicateKeyException 捕获     |
| project_info   | 低  | 中  | 低  | 低  | 低  | 中  | 唯一约束 + DuplicateKeyException 捕获     |
| role_type_info | 低  | 中  | 低  | 低  | 低  | 中  | 双重唯一约束 + DuplicateKeyException 捕获 |

### 重点关注：Tampering（篡改）与 Elevation of Privilege（越权）

**威胁场景**：双实例部署下，两个请求同时到达不同实例，实例 A 的 Check-then-Insert 模式中，两个实例同时检查到"名称不存在"后同时执行 INSERT，导致重复数据。

**STRIDE 分类**：

- **Tampering（篡改）**：重复数据破坏了数据库的完整性约束，本质上是对业务数据的一种非预期篡改。
- **Elevation of Privilege（越权）**：重复数据可能被错误地赋予权限或资源，导致权限扩散。

**缓解措施**：

1. 应用层：`DuplicateKeyException` 捕获 → 返回友好提示（防御层 1）
2. 数据库层：唯一约束 → 从根源阻止重复（防御层 2）

## 关键决策

### 为什么选择"唯一约束 + 异常捕获"而非"预检锁"

| 方案                                | 优点                                              | 缺点                                 |
| ----------------------------------- | ------------------------------------------------- | ------------------------------------ |
| **唯一约束 + 异常捕获（当前方案）** | 无锁、无死锁、无额外 Redis 依赖、数据库天然原子性 | 依赖异常处理流程                     |
| SELECT ... FOR UPDATE 排他锁        | 明确控制并发                                      | 死锁风险、锁竞争、需要事务内统一管理 |
| Redis 分布式锁                      | 应用层可控                                        | 额外 Redis 依赖、锁超时问题          |

**结论**：唯一约束 + DuplicateKeyException 捕获是当前场景下最轻量、最可靠的方案，数据库本身就是最终一致性的仲裁者。

### 异常处理安全性

`DuplicateKeyException` 被捕获后 **不暴露** 数据库内部错误信息，仅返回用户友好的业务提示，避免信息泄露：

- 产品："产业已存在，请勿重复添加"
- 项目："项目名称已存在，请勿重复创建"
- 角色："角色重复，请勿重复提交"
