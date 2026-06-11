# 版本级别（nightly）流水线支持开源代码检测工具结果可视 - cicd 侧

## 需求背景

openlibing-cicd 仓库负责在流水线构建产物分析完成后，检测 SARIF 文件并触发 openlibing-codecheck 仓库的异步解析流程。本仓库的改动为触发端，核心解析和可视化逻辑在 codecheck 仓库实现。

关联 codecheck 仓库 spec：`spec/openlibing-codecheck/task_design/static-alarm/`

## 验收标准

- [x] 流水线构建产物分析完成后，自动检测 .sarif 后缀文件
- [x] 解析流水线配置获取 repoUrl、branch、pipelineName
- [x] 构建 StaticAlarmReceiveDTO 并通过 Feign 调用 codecheck 接口
- [x] 触发失败不影响主流程，只记录日志

## 关联 PR

| 仓库 | PR | 说明 |
|------|-----|------|
| openlibing-cicd | #351 | 构建产物 SARIF 检测与触发 |
| openlibing-codecheck | #189 | SARIF 解析、问题管理、查询 API |
