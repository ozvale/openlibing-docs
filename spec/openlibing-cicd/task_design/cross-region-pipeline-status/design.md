# cross-region-pipeline-status — 技术设计

## 方案概述
在 `CrossRegionController` 中新增面向外部服务的流水线状态查询接口。通过组织名称、仓库名称、PR 编号和平台维度的联合查询，从 `yellow_region_pipeline` 表获取最新流水线记录，组装为精简状态 VO 返回。

## 架构决策

### 决策 1：查询维度
- 选择：按 orgName + repoName + number + platform 四维联合查询
- 原因：同一 PR 在不同平台（gitee/gitcode）可能有不同流水线，需按平台区分

### 决策 2：返回策略
- 选择：查不到记录时返回 `successData(null)` 而非 404 错误
- 原因：外部服务需区分"查到了"和"没查到"两种状态，null 比错误码更易处理

### 决策 3：耗时计算
- 选择：解析 startTime/endTime 字符串计算差值，格式化输出 `Xs` / `Xm Xs`
- 原因：对端返回的时间为字符串格式，需在服务端统一格式化以减少前端处理负担

### 决策 4：并发错误处理
- 选择：`CONCURRENCY_LIMIT` 关键词从 "最大并发" 调整为 "排队"
- 原因：华为云流水线错误信息已变更，"最大并发" 不再匹配实际返回的错误文本

## 涉及文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `controller/CrossRegionController.java` | 修改 | 新增 `POST /pipelineInfo` 端点 |
| `controller/PipelineControllerV2.java` | 修改 | `getPipelineRunSummary` 标记 `@Deprecated` |
| `dto/cross_region/ExternalPipelineInfoReqDTO.java` | 新增 | 请求体 DTO（owner/repo/platform/prNumber） |
| `vo/YellowPipelineStatusVO.java` | 新增 | 响应 VO（7 个字段） |
| `service/CrossRegionService.java` | 修改 | 新增 `getPipelineStatus` 接口方法 |
| `service/impl/CrossRegionServiceImpl.java` | 修改 | 实现查询 + 耗时计算 |
| `mapper/YelloRegionPipelineMapper.java` | 修改 | 新增 `queryLatestPipelineByPlatform` |
| `mapper/YellowRegionPipelineMapper.xml` | 修改 | 新增对应 SQL |
| `enums/YellowPipelineStatusEnum.java` | 修改 | 新增 `ALREADY_RUNNING` |
| `enums/PipelineStartErrorEnums.java` | 修改 | 修改 `CONCURRENCY_LIMIT` 关键词 |
| `start.sh` | 修改 | 新增 JVM 参数 `-Dapollo.cache.file.enable=false` |

## 风险 & 缓解
- **风险 1**：查询结果为空（无对应流水线记录）
  - 缓解：返回 `successData(null)`，外部服务按 null 处理
- **风险 2**：时间格式解析异常
  - 缓解：`catch DateTimeParseException`，duration 返回 `-`
- **风险 3**：`ALREADY_RUNNING` 新增枚举未被外部识别
  - 缓解：枚举值按现有模式扩展，不加新状态流转，外部按字符串处理

## 跨仓影响
无。改动仅限 `openlibing-cicd` 仓。
