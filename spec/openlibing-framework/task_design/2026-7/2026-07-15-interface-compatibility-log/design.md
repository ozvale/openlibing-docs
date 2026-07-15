## Context

openlibing-framework 日志体系基于 `LogDataCollectionName.MANAGEMENT_LOG` JSON 配置动态获取表名列表，通过 `GetLogsMapper.xml` 的 `<choose>` 块做表名映射验证，使用 Liquibase changelog 管理建表。

现有日志模块（如 `log_tool`、`log_wiki`、`log_feedback` 等）均遵循统一模式：
1. `LogDataCollectionName.java` 定义常量 + JSON 配置项
2. `GetLogsMapper.xml` 添加 `<when>` 分支
3. Liquibase changelog XML 创建表
4. `db.changelog.xml` 引入 changelog 文件
5. 业务 Service 层使用 `@LogApi` 注解记录日志

## Goals / Non-Goals

**Goals:**

- 新增 `log_interface` 日志表，表结构与现有日志表一致（id、operation_date、log_code、operation_module、user_name、user_id、operation、old_data、new_data、remark、log_message、is_detail、ex_message、params、account_id、account_platform、log_result、account_name）
- 在 `LogDataCollectionName.java` 新增 `INTERFACE_LOG = "log_interface"` 常量
- 在 `MANAGEMENT_LOG` JSON `business_log` 中新增 `"接口兼容性管理": "log_interface"`
- 在 `GetLogsMapper.xml` 新增 `log_interface` when 分支
- Liquibase changelog 创建 `log_interface` 表并引入到 `db.changelog.xml`
- `/manage/logging/find/all/logging/2` 接口正常返回包含 `log_interface` 的数据

**Non-Goals:**

- 不修改 `log_interface` 表结构与其他日志表不同的字段
- 不新增日志查询专有接口
- 不修改 openlibing-framework 中其他日志模块的代码

## Decisions

### D1: 表结构与 `log_tool` 保持一致

**选择**: `log_interface` 表字段完全复用 `log_tool` 的字段定义（18 列），包含 `account_id`、`account_platform`、`log_result`、`account_name` 等三方账号与操作结果字段。

**理由**: 日志体系统一字段结构便于 UNION ALL 跨表查询和前端展示。

### D2: Liquibase changelog 独立文件

**选择**: 创建独立的 `v1.0.1/tool/log_interface.xml` changelog 文件。

**理由**: 与其他日志表的 changelog 组织方式一致，便于独立管理和回滚。

### D3: MANAGEMENT_LOG JSON 配置项放在 business_log 下

**选择**: `"接口兼容性管理": "log_interface"` 放在 `business_log` 分类中。

**理由**: 接口兼容性管理属于业务操作日志，与项目空间、PR管理、检测中心等同类。

## Risks / Trade-offs

- **[Risk] 数据库表不存在导致查询报错** → 通过 Liquibase changelog 自动建表解决
- **[Risk] 新增表影响 UNION ALL 查询性能** → 可接受；`log_interface` 数据量初期较小

## Migration Plan

1. Liquibase 部署时自动创建 `log_interface` 表
2. 无需数据迁移
3. 验证：`/manage/logging/find/all/logging/2` 接口正常返回
