# 新增《我的导出》功能，统一平台导出入口 — 实现任务

## 进度: 6/6 complete

### Task 1: framework 统一导出接口与数据模型（4 项）

- [x] 新增 `ObsFileEntity`、`ObsFileMapper`、`ExportStatus` 枚举及 ObsFile 请求 DTO
- [x] 新增 `ObsService` / `ObsServiceImpl`（创建/按用户查询/详情/下载签名/条件更新/条件查询/过期清理）
- [x] 新增 `ExportController`（/export/list、/export/detail、/export/download-url、/export/internal-server/create|update|query）
- [x] 新增 Liquibase changelog `v1.0.1/obs_file.xml` 落库 `obs_file` 表

### Task 2: framework 过期清理与 OBS 工具（2 项）

- [x] 新增 `CleanObsFileJob`（每天 1 点清理创建超 3 天记录 + 删除 OBS 对象）
- [x] 新增 `FrameworkObsUtil`（上传/删除/临时签名 URL/分片上传）

### Task 3: framework common-sdk 升级与 Nacos 迁移（4 项）

- [x] pom.xml：common-sdk 1.0.20.1 → 1.0.20.4
- [x] 移除 `@EnableApolloConfig`，application*.yaml Apollo → Nacos
- [x] 新增 `NacosConfigListener` / `NacosConfigListenerProcessor`，改造 `DashboardMatrixConfig`、`RateLimitConfig`
- [x] 修复升级编译问题（GitHelper / SelectServiceImpl / MockIpUtils 的 javax → jakarta、guava → gson）

### Task 4: codecheck 静态告警导出适配（7 项）

- [x] 新增 `OpenlibingFrameworkClient` Feign（create/update/query）
- [x] `StaticAlarmServiceImpl` 导出逻辑改调 framework 统一导出
- [x] `StaticAlarmExportProducer` / `Consumer` 适配状态上报
- [x] `StaticAlarmController` 移除导出相关接口
- [x] 删除 `StaticAlarmExportEntity`、`StaticAlarmExportMapper(+xml)`、`StaticAlarmExportRecordVO`、`StaticAlarmExportStatusEnum`、`ObsBucketService` / `Impl`
- [x] `XxlJobHandler` 批量导出改造（-185 行）
- [x] pom.xml（common-sdk 1.0.20.4）+ Nacos 迁移

### Task 5: cicd 流水线/测试用例导出迁移（8 项）

- [x] 新增 `FrameworkProjectClient` Feign（create/update/query）
- [x] `PipelineControllerV2` 删除 `/export/list`、`/export`、`/test-report/export-status`、`/test-report/download`
- [x] `PipelineServiceImpl` 提交导出任务改调 framework（-468 行）
- [x] `FileDownloadServiceImpl` 分片上传 + 状态回填重写
- [x] 删除 `FileExportLogEntity`、`FileExportLogMapper(+xml)`、`FileExportLogEntityBuilder`、`CleanJob` / `CleanJobTest`
- [x] `XxlJobHandler` 批量导出改造
- [x] pom.xml（common-sdk 1.0.20.4 + jakarta.ws.rs-api 3.1.0）+ Nacos 迁移
- [x] 测试更新（PipelineServiceImplTest 等），新增 test `application-local.yaml` 屏蔽 Nacos

### Task 6: 验证（4 项）

- [x] framework：`mvn spotless:check test-compile` 通过
- [x] codecheck：编译与单测通过
- [x] cicd：`mvn spotless:check test-compile` 通过，UT 屏蔽 Nacos 依赖
- [x] 跨仓接口联调验证（framework `/export/internal-server/*` 契约对齐）
