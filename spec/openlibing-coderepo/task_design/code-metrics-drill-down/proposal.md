# 代码度量指标下钻能力建设

## 需求背景

openlibing-coderepo 的代码度量功能目前只存储和展示总体指标（代码规模、平均函数代码行、平均圈复杂度、总代码重复率、总文件重复率），无法下钻到文件级别查看具体指标数据。用户需要查看每个文件的详细指标，以便定位代码质量问题。

## 需求范围

### 涉及仓库

- **openlibing-coderepo-fork**（后端服务）
- **test-devops**（CI 插件 code-metrics-scan）

### 核心需求

1. 新增 `code_metrics_file_detail` 明细表，存储文件级指标数据
2. 修改 CI 插件，采集并上报每个文件的函数级明细（函数名、行数、开始行、结束行）和重复率明细（重复率、重复行数、重复文件列表）
3. 新增 `POST /metrics/code/file-detail` 接口，支持按指标类型查询文件级详情，支持分页、文件名模糊查询和排序
4. 修改 `/query-repo-branch` 接口，返回各指标的 `value` + `pipelineRunId`（不再返回 checkTime）
5. 指标类型使用枚举 `MetricTypeEnum`（0-4），类型安全

## 验收标准

1. CI 插件扫描后能正确上报文件级指标明细（函数明细、重复率明细）
2. `POST /metrics/code/file-detail` 接口按 metricType 返回不同结构的明细数据
3. metricType=0 返回代码规模（filePath + loc）
4. metricType=1 返回函数级明细（filePath + functionName + functionLoc + startLine + endLine），一个函数一条
5. metricType=2 返回圈复杂度明细（filePath + avgCyclomaticComplexity）
6. metricType=3 返回重复率明细（filePath + duplicationRate + duplicationLineCount）
7. metricType=4 返回文件重复明细（filePath + duplicatedFiles）
8. 支持分页（pageNum + pageSize）、文件名模糊查询（fileName）、排序（sortByField + sort）
9. `/query-repo-branch` 接口返回的 MetricItemVO 只包含 value 和 pipelineRunId
10. 所有代码符合 code_rules 规范
