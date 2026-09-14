# 唯一约束与防重复插入 — 归档

## 关联

| 项           | 链接                                                                                                            |
| ------------ | --------------------------------------------------------------------------------------------------------------- |
| 业务 Commit  | [9a6f479b](https://gitcode.com/openlibing/openlibing-framework/commit/9a6f479b8f096a33c43a910e2b0955affc56907a) |
| 业务 PR      | [#436](https://gitcode.com/openlibing/openlibing-framework/merge_requests/436)                                  |
| 安全威胁模型 | `spec/openlibing-framework/system_design/threat-model-duplicate-key-protection.md`                              |
| 安全设计文档 | `spec/openlibing-framework/system_design/security-design-duplicate-key-protection.md`                           |

## 需求背景

`user_role_info` 表在双实例部署下存在并发重复插入问题。经分析，数据库缺少唯一约束是根本原因——应用层 `SELECT ... FOR UPDATE` 在 `REPEATABLE_READ` 隔离级别下依赖事务快照，无法完全阻止 Check-then-Insert 的并发竞态。

解决方案：在数据库层面添加唯一约束兜底，同时在应用层捕获 `DuplicateKeyException` 返回用户友好提示，去除异常堆栈日志避免敏感信息泄露。

## 变更范围

| 文件                      | 变更类型 | 说明                                                 |
| ------------------------- | -------- | ---------------------------------------------------- |
| `ProductServiceImpl.java` | 修改     | 捕获 DuplicateKeyException，返回"组织已存在"友好提示 |
| `ProjectServiceImpl.java` | 修改     | 同上，返回"项目已存在"友好提示                       |
| `RoleServiceImpl.java`    | 修改     | 同上，返回"角色已存在"友好提示                       |
| `product_info.xml`        | 新增     | product_info.product_name 唯一约束                   |
| `project_info.xml`        | 新增     | project_info.project_name 唯一约束                   |
| `role_type_info.xml`      | 新增     | role_type_info.role + role_name 唯一约束             |
| `db.changelog.xml`        | 修改     | 注册新增的 3 个 changelog                            |

## 交付历程

| Step     | Commit      | 说明                                      |
| -------- | ----------- | ----------------------------------------- |
| 初始实现 | `9a6f479b`  | 添加唯一约束 + DuplicateKeyException 处理 |
| 日志清理 | `5f1e87879` | 去除异常堆栈日志避免敏感信息泄露          |
| 文案统一 | `fd477c313` | "产业" → "组织" 统一提示文案              |

## 安全设计

安全设计文档涵盖以下维度（详见 system_design/ 下的两个文档）：

| 维度       | 状态        | 关键结论                                                     |
| ---------- | ----------- | ------------------------------------------------------------ |
| 威胁模型   | ✅ 已完成   | 资产清单、信任边界、数据流、STRIDE 评估                      |
| 认证授权   | ✅ 无变化   | 复用已有鉴权体系                                             |
| 输入输出   | ✅ 已加固   | 唯一约束做兜底校验，DuplicateKeyException 捕获后返回友好提示 |
| 数据保护   | ✅ 已加固   | 异常信息脱敏，不暴露数据库结构                               |
| 错误处理   | ✅ 已加固   | DuplicateKeyException → 用户友好错误 + 去堆栈日志            |
| 依赖供应链 | ✅ 无新依赖 | 复用 Spring DAO 内置异常体系                                 |
| 部署安全   | ✅ 无影响   | 数据库约束变更兼容存量数据                                   |

## 用户自测反馈

| 反馈                                | 修复                                                           |
| ----------------------------------- | -------------------------------------------------------------- |
| PR 代码检视：3 个 mapper 方法未使用 | `09cc13434` 删除 `deleteByIds`/`countByApiUrl`/`queryByApiUrl` |
| SpotBugs: EI_EXPOSE_REP             | `6eb00357c` 添加防御性拷贝                                     |
| UT 预期文案未同步                   | `e543c7911` 更新测试期望值                                     |

## 最终验证

| 验证项              | 结果                    |
| ------------------- | ----------------------- |
| Maven 编译          | ✅ 通过                 |
| pre-commit 全量检查 | ✅ 通过                 |
| 全量 UT（2172 项）  | ✅ 通过                 |
| SpotBugs 安全扫描   | ✅ 已修复 EI_EXPOSE_REP |
| 远程 Git Hooks      | ✅ 通过                 |

## 设计偏差与取舍

- **方案选择**：优先数据库唯一约束 + 应用层异常捕获，而非仅靠应用层分布式锁。因为：
  - 唯一约束是最根本的兜底机制，不依赖网络/锁服务
  - 兼容存量重复数据（数据库不会对已有数据校验新增约束）
  - 减少运维心智负担
- **not-null 约束升级**：`role_type_info` 的 `role` 和 `role_name` 从 `nullable` 升级为 `not-null + unique`，与业务语义对齐

## 可复用经验

- **并发重复插入治理**：优先在数据库层加唯一约束兜底，应用层捕获 DuplicateKeyException 返回友好提示。不要仅依赖应用层排他锁或 SELECT FOR UPDATE。
- **Maven changelog 命名约定**：唯一约束的 changelog 文件按 `{table_name}.xml` 命名，放在对应版本的 `v1.0.1/` 目录下。
- **异常信息脱敏**：DuplicateKeyException 的堆栈日志不应打印到应用日志，避免数据库结构泄露。使用 `LOG.warn("msg")` 而非 `LOG.error("msg", e)`。

## 归档日期

2026-09-10
