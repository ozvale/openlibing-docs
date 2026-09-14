# 新增《我的导出》功能，统一平台导出入口 — 技术设计

## 方案概述

在 openlibing-framework 仓建设统一的《我的导出》导出任务管理能力，提供导出任务创建/查询/更新/下载签名接口与 `obs_file` 记录表；codecheck、cicd 等业务仓通过 Feign 调用 framework 内部接口，删除本地导出记录表、下载与状态刷新接口，实现平台导出入口与任务状态统一收敛。

## 架构决策

### 决策 1：统一出口收敛到 framework

**选择**：framework 作为导出能力唯一提供方。

**原因**：各业务仓导出能力重复建设、维护成本高；收敛后业务仓仅负责业务数据组装与文件上传，任务记录、下载、清理统一由 framework 管理。

### 决策 2：任务状态机收敛

**选择**：状态统一由 framework `ExportStatus` 枚举管理（`INITIALIZED / UPLOADING / SUCCESS / FAILED`）。

**原因**：避免各仓状态枚举不一致；业务仓仅上报状态流转。

### 决策 3：文件存储与下载收敛

**选择**：文件统一上传 OBS，下载统一走 framework 生成的临时签名 URL（3 小时）。

**原因**：业务仓不再直接透传文件流下载，减少重复实现与带宽占用。

### 决策 4：业务仓本地导出表下线

**选择**：codecheck/cicd 删除本地导出记录表与状态枚举。

**原因**：避免双份记录表数据不一致，任务记录以 framework `obs_file` 为准。

### 决策 5：配置中心与依赖升级

**选择**：common-sdk 升级至 1.0.20.4，Apollo → Nacos。

**原因**：1.0.20.4 已启用 Nacos 替代 Apollo，三个业务仓均移除 Apollo 依赖；升级后 SDK 不再透传 guava，codecheck 显式声明 guava、cicd 显式声明 jakarta.ws.rs，并修复 javax → jakarta 编译问题。

## 接口设计

### framework 导出接口（ExportController）

| 功能点 | 接口路径 | 方法 | 可见性 |
|--------|----------|------|--------|
| 查询我的导出 | `/export/list?userId=` | GET | 外部 |
| 查询导出详情 | `/export/detail?id=&userId=` | GET | 外部 |
| 生成下载链接 | `/export/download-url?id=&userId=` | GET | 外部 |
| 创建导出任务 | `/export/internal-server/create?userId=` | POST | 内部 |
| 更新导出任务 | `/export/internal-server/update` | POST | 内部 |
| 条件查询导出 | `/export/internal-server/query` | POST | 内部 |

### 接口契约示例

**创建导出任务** `POST /export/internal-server/create?userId=`

```json
{
  "type": "static_alarm",
  "fileName": "静态告警导出.xlsx",
  "identifier": "pr-123",
  "data": "{}"
}
```

**更新导出任务** `POST /export/internal-server/update`

```json
{
  "id": 100,
  "message": "导出成功",
  "objectKey": "export/xxx.xlsx",
  "expectedMessages": ["正在上传文件"]
}
```

**条件查询导出任务** `POST /export/internal-server/query`

```json
{
  "identifier": "pr-123",
  "type": "static_alarm",
  "statuses": ["导出成功"],
  "limit": 1
}
```

## 数据模型

### obs_file 表（Liquibase changelog v1.0.1/obs_file.xml，changeSet `20260820_create_table_obs_file`）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT（自增主键） | 主键 |
| type | VARCHAR(255) | 导出类型 |
| file_name | VARCHAR(255) | 文件名称 |
| object_key | VARCHAR(255) | OBS 对象 key（上传后回填） |
| identifier | VARCHAR(255) | 文件内容标识（索引） |
| create_time | DATETIME | 创建时间 |
| update_time | DATETIME | 更新时间 |
| creator | VARCHAR(255) | 创建人（索引） |
| message | VARCHAR(255) | 状态信息 |
| data | VARCHAR(500) | 文件相关信息 |

状态枚举 `ExportStatus`：`INITIALIZED("导出任务已创建")` / `UPLOADING("正在上传文件")` / `SUCCESS("导出成功")` / `FAILED("导出失败")`。

## 涉及文件

### openlibing-framework（feat/obs-file-zjy，26 个文件，+1062/-103）

| 文件 | 操作 | 说明 |
|------|------|------|
| business/controller/ExportController.java | 新增 | 统一导出接口（6 个端点） |
| business/service/ObsService.java + impl/ObsServiceImpl.java | 新增 | 导出任务服务与实现（创建/查询/下载/更新/清理） |
| business/mapper/ObsFileMapper.java | 新增 | obs_file 表 Mapper |
| business/entity/ObsFileEntity.java | 新增 | 导出记录实体 |
| business/dto/obs/ExportStatus.java、ObsFileCreateRequestDTO、ObsFileQueryRequestDTO、ObsFileUpdateRequestDTO | 新增 | 状态枚举与请求 DTO |
| common/job/CleanObsFileJob.java | 新增 | 过期导出记录定时清理（每天 1 点，保留 3 天） |
| common/utils/FrameworkObsUtil.java | 新增 | OBS 客户端封装（上传/删除/签名 URL/分片上传） |
| common/nacos/NacosConfigListener.java + NacosConfigListenerProcessor.java | 新增 | Nacos 配置变更监听机制 |
| common/config/DashboardMatrixConfig.java、RateLimitConfig.java | 修改 | Apollo 改为基于 Environment + Nacos 监听刷新 |
| OpenlibingFrameworkApplication.java | 修改 | 移除 @EnableApolloConfig |
| pom.xml | 修改 | common-sdk 1.0.20.1 → 1.0.20.4 |
| application.yaml / beta / gama / prod | 修改 | Apollo → Nacos |
| GitHelper / SelectServiceImpl / MockIpUtils | 修改 | javax → jakarta、guava → gson 依赖修复 |
| db/changelog/v1.0.1/obs_file.xml | 新增 | obs_file 建表 DDL |

### openlibing-codecheck（feat/obs-file-zjy，29 个文件，+390/-881）

| 文件 | 操作 | 说明 |
|------|------|------|
| business/delegate/OpenlibingFrameworkClient.java | 新增 | Feign 调用 framework 导出内部接口 |
| business/impl/alarm/StaticAlarmServiceImpl.java | 重构 | 导出逻辑改为调用 framework 统一导出 |
| business/consumer/StaticAlarmExportConsumer.java、producer/StaticAlarmExportProducer.java | 修改 | 适配状态上报 |
| controller/alarm/StaticAlarmController.java | 修改 | 移除导出相关接口 |
| entity/alarm/StaticAlarmExportEntity、mapper/StaticAlarmExportMapper(+xml)、vo/alarm/StaticAlarmExportRecordVO、enums/alarm/StaticAlarmExportStatusEnum | 删除 | 本地导出表/状态枚举下线 |
| business/service/ObsBucketService、impl/ObsBucketServiceImpl | 删除 | 桶配置改为继承 framework |
| common/job/XxlJobHandler.java | 重构 | 批量导出改造（-185 行） |
| pom.xml、application*.yaml、OpenlibingCodecheckApplication | 修改 | common-sdk 1.0.20.4 + Nacos 迁移 |

### openlibing-cicd（feat/export-file-zjy，35 个文件，+620/-930）

| 文件 | 操作 | 说明 |
|------|------|------|
| business/feign/FrameworkProjectClient.java | 新增 | Feign 调用 framework 导出内部接口 |
| business/controller/PipelineControllerV2.java | 修改 | 删除 /export/list、/export、/test-report/export-status、/test-report/download |
| business/service/impl/PipelineServiceImpl.java | 重构 | 提交导出任务改调 framework（-468 行） |
| business/service/impl/FileDownloadServiceImpl.java | 重写 | 分片上传 + 状态回填 |
| entity/pipeline/FileExportLogEntity、mapper/FileExportLogMapper(+xml)、FileExportLogEntityBuilder | 删除 | 本地导出记录表下线 |
| common/job/CleanJob、CleanJobTest | 删除 | 本地过期清理任务下线 |
| common/job/XxlJobHandler.java | 修改 | 批量导出改造 |
| pom.xml | 修改 | common-sdk 1.0.20.4 + jakarta.ws.rs-api 3.1.0 |
| application*.yaml、OpenlibingCicdApplication | 修改 | Nacos 迁移 |
| src/test/resources/application-local.yaml | 新增 | 测试屏蔽 Nacos 依赖 |

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|---------|
| 接口契约耦合（codecheck/cicd 强依赖 framework 导出接口） | 接口版本化、contract 提前对齐；跨仓联调验证 |
| 导出状态并发竞争 | `expectedMessages` 条件更新 + 影响行数校验（任务锁抢占） |
| 大文件导出内存/带宽 | OBS 分片上传（默认 5MB/片），流式传输 |
| 过期文件清理失败残留 | 单条失败不影响整体，日志记录失败 id 便于补偿 |
| common-sdk 1.0.20.4 依赖回归 | codecheck 显式声明 guava、cicd 显式声明 jakarta.ws.rs；已彻底移除 Apollo 依赖，编译 + 单测回归 |
| Nacos 迁移配置缺失 | 按环境 namespace/group 逐项核对，灰度验证 |
| 游客（无登录）导出越权 | 仅 GUEST 场景放行，限制查询范围 |

## 跨仓影响

- **调用方**：codecheck（OpenlibingFrameworkClient）、cicd（FrameworkProjectClient）依赖 framework `/export/internal-server/*` 契约
- **接口变更**：cicd 下线 `/export/list`、`/export`、`/test-report/export-status`、`/test-report/download`，前端需切换到《我的导出》新入口
- **数据模型**：新增 `obs_file` 表；codecheck/cicd 本地导出表下线
