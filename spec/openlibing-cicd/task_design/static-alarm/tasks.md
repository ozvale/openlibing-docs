# 版本级别（nightly）流水线支持开源代码检测工具结果可视 - cicd 侧实现任务

- [x] 创建 `StaticAlarmReceiveDTO` 传递给 codecheck 的 DTO
- [x] 修改 `PipelineEventConsumer` 添加 SARIF 文件检测与触发逻辑
  - [x] 注入 `PipelineInfoMapper` 和 `CodeCheckClient` 依赖
  - [x] 实现 `triggerStaticAlarmIfSarif` 方法
  - [x] 实现 `buildStaticAlarmDTO` 方法
  - [x] 实现 `fillPipelineInfo` 方法（解析 configJson）
  - [x] 实现 `sendToStaticAlarm` 方法（容错调用）
- [x] 修改 `CodeCheckClient` 添加 `receiveStaticAlarmResult` Feign 接口
