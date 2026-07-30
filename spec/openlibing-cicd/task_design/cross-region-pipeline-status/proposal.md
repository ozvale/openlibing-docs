# 【openlibing-cicd】黄蓝协同流水线状态查询接口

## 需求背景
黄蓝协同（跨区域部署）场景中，外部服务需要通过组织名称、代码仓名称、PR 编号和平台信息查询流水线的执行状态。当前 `CrossRegionController` 仅支持内部流水线触发与状态更新，缺少面向外部服务的精简状态查询接口。

关联 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/52

## 功能描述
1. `CrossRegionController` 新增 `POST /pipelineInfo` 接口，接收 `ExternalPipelineInfoReqDTO`，返回 `YellowPipelineStatusVO`
2. `ExternalPipelineInfoReqDTO` 包含：owner（组织名称）、repo（仓库名称）、platform（平台 gitee/gitcode）、prNumber（PR 编号）
3. `YelloRegionPipelineMapper` 新增 `queryLatestPipelineByPlatform` 方法，按 orgName/repoName/number/platform 查询最新流水线
4. `YellowRegionPipelineMapper.xml` 新增对应 SQL 查询，返回结果按 start_time DESC LIMIT 1
5. `CrossRegionServiceImpl.getPipelineStatus` 实现：查询最新流水线 → 组装 VO（含执行耗时计算）
6. `YellowPipelineStatusVO` 包含：status、pipelineStatus、yellowUrl、startTime、endTime、failReason、duration
7. 耗时计算：`calculateDuration(startTime, endTime)` 格式为 `Xs` 或 `Xm Xs`
8. `YellowPipelineStatusEnum` 新增 `ALREADY_RUNNING` 枚举值
9. `PipelineStartErrorEnums.CONCURRENCY_LIMIT` 错误关键词从 "最大并发" 调整为 "排队"
10. `PipelineControllerV2.getPipelineRunSummary` 标记为 `@Deprecated`，调用时记录警告日志

## 不做
- 不修改现有查询流水线的 SQL（仅新增 `queryLatestPipelineByPlatform`）
- 不新增鉴权（由 API 网关统一认证）
- 不修改其他 Controller 接口逻辑

## 验收标准
- [ ] `POST /pipelineInfo` 返回流水线状态 VO（含 status / yellowUrl / duration 等字段）
- [ ] 按 orgName + repoName + number + platform 查询返回最新一条记录
- [ ] 不存在时返回 `successData(null)` 而非错误
- [ ] 耗时计算：< 60s 显示 `Xs`，>= 60s 显示 `Xm Xs`
- [ ] 时间解析异常时耗时返回 `-` 而非抛异常
- [ ] `ALREADY_RUNNING` 状态可被正常返回
- [ ] `CONCURRENCY_LIMIT` 匹配 "排队" 关键词
- [ ] `getPipelineRunSummary` 被标记 `@Deprecated` 并打印警告日志
- [ ] 向后兼容：旧接口行为不变

## 影响范围
- 后端：`openlibing-cicd` 仓
  - `controller/CrossRegionController.java`：新增 `POST /pipelineInfo` 端点
  - `controller/PipelineControllerV2.java`：`getPipelineRunSummary` 标记 `@Deprecated`
  - `dto/cross_region/ExternalPipelineInfoReqDTO.java`：新增请求体 DTO
  - `vo/YellowPipelineStatusVO.java`：新增响应 VO
  - `service/CrossRegionService.java`：新增 `getPipelineStatus` 方法
  - `service/impl/CrossRegionServiceImpl.java`：实现查询 + 耗时计算
  - `mapper/YelloRegionPipelineMapper.java`：新增 `queryLatestPipelineByPlatform`
  - `mapper/YellowRegionPipelineMapper.xml`：新增对应 SQL
  - `enums/YellowPipelineStatusEnum.java`：新增 `ALREADY_RUNNING`
  - `enums/PipelineStartErrorEnums.java`：修改 `CONCURRENCY_LIMIT` 关键词
  - `start.sh`：新增 `-Dapollo.cache.file.enable=false`
