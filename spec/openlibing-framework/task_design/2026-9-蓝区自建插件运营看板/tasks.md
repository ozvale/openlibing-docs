# 蓝区自建插件 GitHub & GitCode 使用运营看板 — 实现任务

## 进度: 4/4 complete

### Task 1: 数据模型与 Mapper

- [x] 新增 `plugin_usage_event` 表（Liquibase changelog）
- [x] 新增 Entity / Mapper / Mapper XML

### Task 2: 上报接口

- [x] 新增 `PluginUsageReportController` 上报接口（`/plugin-usage/report`）
- [x] 上报字段校验（channel 枚举、必填字段、时间格式）
- [x] 去重逻辑（按 `(channel, plugin_code, user_id, event_type, event_time)` 去重）

### Task 3: 看板查询接口

- [x] 新增 `PluginUsageDashboardController` 查询接口（按渠道+时间+指标类型聚合）
- [x] 聚合查询 SQL（按时间桶 + channel + metric_type 分组）

### Task 4: 验证

- [x] `mvn spotless:check test-compile` 通过
- [x] PR 合入 `release_20260923_iter2` 分支
