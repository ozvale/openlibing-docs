# 代码度量指标下钻 - 实现任务

## 后端（openlibing-coderepo-fork）

- [x] 新增 `code_metrics_file_detail` 建表 changeSet（metrics_json 存储指标，便于扩展）
- [x] 新增 `CodeMetricsFileDetailEntity` 实体类
- [x] 新增 `CodeMetricsFileDetailMapper` 及 XML
- [x] 修改 `CodeMetricsReportDTO`：新增 `FileDetailDTO`（含 functionDetails、duplicationLineCount）和 `FunctionDetailDTO`
- [x] 修改 `CodeMetricsServiceImpl.saveFileDetails`：入库函数明细和重复行数
- [x] 新增 `MetricTypeEnum` 枚举（0=代码规模, 1=平均函数代码行, 2=平均圈复杂度, 3=总代码重复率, 4=总文件重复率）
- [x] 新增 `FileMetricDetailQueryDTO`（repoId, branchName, pipelineRunId, metricType, pageNum, pageSize, fileName, sortByField, sort）
- [x] 新增 `FileMetricDetailVO`（5 种内部类：CodeScaleItem, FunctionLocItem, ComplexityItem, DuplicationRateItem, FileDuplicationItem）
- [x] 修改 `MetricItemVO`：去掉 checkTime，只保留 value + pipelineRunId
- [x] 新增 `POST /metrics/code/file-detail` 接口（分页、模糊查询、排序）
- [x] 修改 `/query-repo-branch` 接口：MetricItemVO 只返回 value + pipelineRunId
- [x] 代码规范优化：方法不超过50行、参数不超过5个、使用工具类判空、不返回null

## CI 插件（test-devops）

- [x] 修改 `LizardDetector.aggregateFileDetails`：保留函数明细（functionName, functionLoc, startLine, endLine）
- [x] 修改 `DuplicationDetector.calculateFileDuplicationDetails`：增加 duplicationLineCount
- [x] 修改 `MetricsCalculator.mergeFileDetails`：合并 functionDetails 和 duplicationLineCount
- [x] 修改 `CoderepoUploader`：payload 中 fileDetails 单独放在顶层
- [x] 修改 `scanner.js`：分离 fileDetails 和总体指标
