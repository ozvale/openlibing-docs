# UT 覆盖率原始报告下载 — 实现任务

## 进度: 18/18 complete

## 后端 openlibing-coderepo

- [x] T1: `db.changelog.xml` 新增 changeSet：`code_ut_record` 加列 `original_report_obs_url VARCHAR(1024) DEFAULT NULL`（preConditions MARK_RAN 风格）
- [x] T2: `CodeUtRecordEntity` 加 `originalReportObsUrl` 字段；`CodeUtRecordMapper(.xml)` 补列（INSERT/查询列清单同步）
- [x] T3: `UtCoverageServiceImpl#persistUtCoverage` 落库 `originalReportObsUrl = request.getObsUrl()`（`saveFailureRecord` 不落）
- [x] T4: 新增 `ExportStatus` 枚举（INITIALIZED/BUILDING/UPLOADING/SUCCESS/FAILED，message 与 framework 侧一致）
- [x] T5: 新增 4 个导出中心契约 DTO（`ObsFileCreateRequestDTO`/`ObsFileUpdateRequestDTO`/`ObsFileQueryRequestDTO`/`ObsFileResponseDTO`，路径 `business/dto/export/`）
- [x] T6: 新增 `FrameworkExportClient` Feign（create/update/query；contextId=`openlibing-framework-export` 唯一）
- [x] T7: 新增 `UtOriginalReportExportEventDTO`（MQ 消息体，仅 exportRecordId）
- [x] T8: 新增 `UtOriginalReportExportProducer`（投递 + 发送失败兜底回写 FAILED）
- [x] T9: MQ 队列配置：新队列 `ut_original_report_export_queue`（默认交换机 routing key=队列名，持久化），容器工厂复用 `codeMetricsListenerContainerFactory`，并发 2-4、prefetch=1（含 yml 配置项）
- [x] T10: 新增 `UtOriginalReportExportConsumer`：CAS 状态机 INITIALIZED→BUILDING→UPLOADING→SUCCESS(+objectKey)，失败回写 FAILED+截断原因(≤255)，消息体损坏 ACK 丢弃
- [x] T11: 新增 `UtOriginalReportExportService` + Impl：权限校验（复用 UT_COVERAGE_FILE_DETAIL）→ locateRecord → 无原始报告业务失败 → identifier 幂等复用判定 → createExportTask → 投递 MQ → 返回 exportRecordId；规范文件名清洗（非法字符替换 `_`、长度 ≤255）
- [x] T12: `UtCoverageController` 新增 `POST /ut/coverage/original-report/export`（repoId+branchName 必填校验，pipelineRunId 可缺省定位最新）
- [x] T13: `UtCoverageFileDetailVO` 加 `originalReportAvailable`；`getFileDetail` 按 `record.getOriginalReportObsUrl() != null` 填充
- [x] T14: 单测：幂等复用三分支（进行中/已完成复用、FAILED 重建）、CAS 状态机条件更新、MQ 发送失败兜底、无原始报告失败、失败原因截断
- [x] T15: 后端验证：`mvn compile` + 相关单测全绿

## 前端 openlibing-web

- [x] T16: 新增 API 常量与方法：`POST /ut/coverage/original-report/export`（含类型定义）
- [x] T17: UT 覆盖率详情页新增"下载原始报告"按钮：`originalReportAvailable=false` 置灰 + tooltip「功能上线前的历史记录无原始报告」；点击提交成功后按钮短暂 loading 即复位，不自建轮询 UI（进度/失败由框架导出浮层呈现）
- [x] T18: 前端验证：构建通过 + 详情页按钮交互自测
