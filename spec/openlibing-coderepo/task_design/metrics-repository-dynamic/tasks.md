# 实现步骤：代码度量流水线链接支持动态仓路径

## Phase 1: 数据模型变更

- [x] `CodeMetricsReportDTO` 新增 `repository` 字段（String 类型，注释说明格式为 owner/repo）
- [x] `CodeMetricsReportDTO.FileMetricsSummary` 内部类 `BigDecimal` 引用统一使用 import
- [x] `CodeMetricsRecordEntity` 新增 `repository` 字段 + `@TableField` 注解
- [x] `CodeMetricsRecordMapper.xml` resultMap 增加 `repository` 映射
- [x] `db.changelog.xml` 新增 changeset `20260615_add_repository_to_code_metrics_record`（含 precondition + rollback）

## Phase 2: 业务逻辑改造

- [x] `CodeMetricsServiceImpl.reportMetrics` 构建 entity 时设置 `repository(request.getRepository())`
- [x] `CodeMetricsServiceImpl.buildPipelineLink` 签名改为 `buildPipelineLink(String repository, String pipelineRunId)`
- [x] `buildPipelineLink` 优先用 repository 拼接 `{gitcodeDomain}/{repository}/actions/runs/{pipelineRunId}`
- [x] `buildPipelineLink` repository 为空时回退到 `gitcodeDomain + pipelineRunId`
- [x] `CodeMetricsServiceImpl.getFileDetail` 调用 `buildPipelineLink` 时传入 `record.getRepository()`

## Phase 3: 查询适配

- [x] `CodeMetricsRecordMapper.xml` 的 `selectByPipelineRunId` 查询增加 `repository` 列

## Phase 4: 配置与日志

- [x] `gitcodeDomain` 配置从完整路径改为仅基础域名
- [x] `CodeMetricsController` 日志增加 `repository` 字段打印

## Phase 5: 测试更新

- [x] `CodeMetricsServiceImplTest` 中 `gitcodeDomain` 测试值从完整路径改为 `https://test.gitcode.net`
