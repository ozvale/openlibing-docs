# 定时同步流水线信息需增加超时机制

## 需求背景

`syncPipelineConfigInfo` 定时任务于7月11日12时执行后卡住，此后所有 `@Scheduled` 定时任务停摆，影响流水线状态监控和清理等关键功能。

### 根因

1. **HTTP 调用无超时**：`fetchPipelineDetailFromRemote` 调用链上的 `buildHuaweiCloudSdkClient` 和 `getDataResultFromHWCloudHttpApi` 均未设置超时。Apache HttpClient 默认超时为 `0`（无限等待），当华为云 API 无响应时线程永久阻塞。
2. **Spring 调度器单线程**：默认 `scheduling-1` 单线程，一个任务卡死导致所有 `@Scheduled` 任务停摆。

### 事件时间线

```
7月11日 12:00  syncPipelineConfigInfo 启动
               成功同步 pipelineId: 14e45318f18a42fbb170714b2d5b27cf
               下一条流水线的 HTTP 请求卡死（华为云 API 无响应 + 无超时）
               [scheduling-1] 线程永久阻塞
7月12日 00:00  定时触发无法执行（线程被占）
7月12日 12:00  定时触发无法执行
7月13日        至今无新日志
```

## 修复方案

1. **增加超时机制**：为 SSL HTTP Client 和华为云 SDK 客户端增加连接/读取超时配置
2. **迁移调度方式**：将 `syncPipelineConfigInfo` 从 `@Scheduled` 迁移到 xxl-job 管理

## 验收标准

- [ ] `fetchPipelineDetailFromRemote` 使用的 SDK 客户端带有超时（connect=10s, read=20s）
- [ ] `fetchPipelineDetailFromRemote` 使用的 HTTP API 客户端带有超时（connect=10s, socket=20s）
- [ ] `syncPipelineConfigInfo` 不再由 `@Scheduled` 调度，改由 xxl-job 管理
- [ ] 新增 xxl-job handler `syncPipelineConfigInfoHandler`，功能与原方法一致
- [ ] 华为云 API 无响应时，请求在 20s 内超时返回失败，不会永久阻塞线程
- [ ] 现有其他 HTTP API 调用（非定时任务路径）不受影响

## 关联 Issue

- openlibing/openlibing-cicd#180
