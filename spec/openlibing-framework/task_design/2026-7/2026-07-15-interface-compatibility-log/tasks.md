## 1. LogDataCollectionName 常量与配置

- [x] 1.1 在 `LogDataCollectionName.java` 新增 `INTERFACE_LOG = "log_interface"` 常量
- [x] 1.2 在 `MANAGEMENT_LOG` JSON `business_log` 中新增 `"接口兼容性管理": "log_interface"`

## 2. GetLogsMapper.xml 表名映射

- [x] 2.1 在 `GetLogsMapper.xml` tableName `<choose>` 块新增 `log_interface` when 分支

## 3. Liquibase changelog 建表

- [x] 3.1 创建 `v1.0.1/tool/log_interface.xml` changelog 文件，定义 `log_interface` 表（字段与 `log_tool` 一致）
- [x] 3.2 在 `db.changelog.xml` 中引入 `log_interface.xml`

## 4. 验证

- [x] 4.1 Liquibase 自动建表 `log_interface` 成功
- [x] 4.2 `/manage/logging/find/all/logging/2` 接口正常返回包含 `log_interface` 的数据
- [x] 4.3 日志查询、统计、详情等各接口对新增表兼容
