# 版本级别（nightly）流水线支持开源代码检测工具结果可视 - cicd 侧技术设计

## 1. 触发流程

```
PipelineEventConsumer.processMessage()
  → 分析构建产物列表
  → 检测 .sarif 后缀文件
  → triggerStaticAlarmIfSarif()
    → buildStaticAlarmDTO()
      → 从 PipelineInfoMapper 查询流水线配置
      → fillPipelineInfo(): 解析 configJson 获取 repoUrl/branch
    → sendToStaticAlarm()
      → CodeCheckClient.receiveStaticAlarmResult(dto)
```

## 2. StaticAlarmReceiveDTO

| 字段 | 类型 | 说明 |
|------|------|------|
| obsUrl | String | SARIF 文件的 OBS 下载地址 |
| repoUrl | String | 代码仓链接 |
| pipelineId | String | 流水线 ID |
| pipelineName | String | 流水线名称 |
| pipelineRunId | String | 流水线运行 ID |
| branch | String | 分支 |
| commitId | String | commit ID |

## 3. CodeCheckClient 新增接口

```java
@PostMapping("/internal/codescan/v1/result/receive")
DataResult<String> receiveStaticAlarmResult(@RequestBody StaticAlarmReceiveDTO dto);
```

## 4. 容错设计

- 触发 codecheck 接口失败只记录日志，不影响主流程
- 区分 DataAccessException（数据访问异常）和其他异常，分别记录
- 解析流水线 configJson 失败时跳过填充，仅记录 warn 日志

## 5. 变更文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| StaticAlarmReceiveDTO | 新增 | 传递给 codecheck 的 DTO |
| PipelineEventConsumer | 修改 | 新增 SARIF 检测与触发逻辑 |
| CodeCheckClient | 修改 | 新增 receiveStaticAlarmResult Feign 接口 |
