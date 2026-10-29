## Why

接口兼容性管理模块（openlibing-design-api-management）需要日志审计能力，追踪接口新增、修改、删除、导入、PR审批、评审等关键操作。当前日志体系（openlibing-framework）中缺少对应的日志表和配置项，导致 `/manage/logging/find/all/logging/2` 接口在包含 `log_interface` 表名配置后因数据库表不存在而报错。

## What Changes

- 在 openlibing-framework 日志体系中新增 `log_interface` 日志表（Liquibase changelog）
- 在 `LogDataCollectionName.java` 中新增 `INTERFACE_LOG = "log_interface"` 常量及 `MANAGEMENT_LOG` JSON 的 `business_log` 配置项 `"接口兼容性管理": "log_interface"`
- 在 `GetLogsMapper.xml` tableName choose 块新增 `log_interface` 映射
- 在 `db.changelog.xml` 中引入 `log_interface.xml`

## Capabilities

### New Capabilities

- `interface-compatibility-management-log`: 接口兼容性管理模块的操作日志记录，支持通过 openlibing-framework 日志查询接口统一查询

### Modified Capabilities

（无——本 change 为新增能力）

## Impact

- **数据库**: 新增 `log_interface` 表（结构与 `log_tool` 等日志表一致）
- **API**: `/manage/logging/find/all/logging/2` 业务日志查询接口将包含 `log_interface` 数据
- **Mapper**: `GetLogsMapper.xml` 新增 tableName 映射
- **配置**: `LogDataCollectionName.java` 新增常量与 JSON 配置
- **关联系统**: openlibing-design-api-management 的 service 层 @LogApi 注解将使用 `log_interface` 作为 tableName
