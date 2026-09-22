# 版本级别（nightly）流水线支持开源代码检测工具结果可视 - cicd 侧归档

## 归档信息

| 项目 | 内容 |
|------|------|
| FE 需求名称 | 版本级别（nightly）流水线支持开源代码检测工具结果可视，并能采集数据支撑运营 |
| 业务 PR | openlibing-cicd #351 |
| 关联 PR | openlibing-codecheck #189 |
| 开发分支 | nightly-yym |
| 归档日期 | 2026-06-11 |

## 实现总结

### 功能概述

openlibing-cicd 仓库在本功能中承担触发端角色：在流水线构建产物分析完成后，自动检测 SARIF 文件并通过 Feign 调用 codecheck 仓库的接口触发异步解析。

### 核心改动

1. **新增 `StaticAlarmReceiveDTO`**：定义传递给 codecheck 的数据结构（obsUrl、repoUrl、pipelineId、pipelineName、pipelineRunId、branch、commitId）
2. **修改 `PipelineEventConsumer`**：在构建产物分析流程中增加 SARIF 文件检测逻辑，检测到后构建 DTO 并调用 codecheck 接口
3. **修改 `CodeCheckClient`**：新增 `receiveStaticAlarmResult` Feign 接口，调用 codecheck 的 `/internal/codescan/v1/result/receive`

### 容错设计

- 触发 codecheck 接口失败不影响主流程，只记录日志
- 解析流水线 configJson 失败时跳过填充，仅记录 warn 日志
- 区分 DataAccessException 和其他异常，分别记录不同级别日志

### 关联 spec

完整功能设计详见：`spec/openlibing-codecheck/task_design/static-alarm/`
