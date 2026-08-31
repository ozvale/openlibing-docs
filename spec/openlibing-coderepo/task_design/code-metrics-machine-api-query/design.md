# coderepo 暴露代码度量 commit 关联查询接口 - 技术设计

> 状态：最终方案。实现已随业务 PR openlibing/openlibing-coderepo#159 交付。
> 关联 codecheck 仓 spec：`openlibing-codecheck/task_design/full-codecheck-record-codeql-fallback` §4.6.7

## 1. 现状回顾

### 1.1 现有 Controller

[CodeMetricsController.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/controller/CodeMetricsController.java) 类级路径 `/metrics/code`，现有 4 个 POST 接口，**全部面向前端或上游上报**：

| 路径                                          | 用途                           |
| --------------------------------------------- | ------------------------------ |
| `POST /metrics/code/report`                   | apig 上报接口（OBS 中转）      |
| `POST /metrics/code/file-detail`              | 文件级指标详情（前端分页查询） |
| `POST /metrics/code/file-content`             | 文件代码视图（前端）           |
| `POST /metrics/code/duplication-block/detail` | 重复块详情（前端）             |

**关键发现**：现有 Controller 没有任何「按 commit 取度量记录」的 HTTP 接口暴露给后端服务调用。

### 1.2 现有 Service 方法

```java
Map<String, BranchMetricsVO> getLatestMetricsByGitUrl(String gitUrl);
```

实现语义：

- 入参：仅 `gitUrl`
- 查询：`selectLatestByGitUrl(gitUrl)` 返回该仓库所有 status=0 的记录，按 `branch_name, detection_completed_at DESC` 排序
- 内存按 `branchName` 分组，每组用 `buildMergedMetricsVO` 合并 5 个指标
- 返回：`Map<分支名, BranchMetricsVO>`，5 个指标每个独立携带 `pipelineRunId`

**关键发现**：`buildMergedMetricsVO` 的「合并」语义是 5 个度量指标分别从不同 record 中找最早一条包含该指标的 record 合并。这与本次需求「取一条整体 record 的 metrics_data_json 原文」语义**不同**，不能直接复用。

### 1.3 表结构

[CodeMetricsRecordEntity.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/entity/metrics/CodeMetricsRecordEntity.java)：

| 字段                     | 类型            | 用途                                             |
| ------------------------ | --------------- | ------------------------------------------------ |
| `id`                     | BIGINT (雪花ID) | 主键                                             |
| `git_url`                | VARCHAR         | 仓库 URL                                         |
| `branch_name`            | VARCHAR         | 分支名                                           |
| `pipeline_run_id`        | VARCHAR         | 流水线执行记录 ID                                |
| `run_number`             | VARCHAR         | 流水线运行编号                                   |
| `commit_id`              | VARCHAR(64)     | 触发本次扫描的 commit ID（插件端上报，本次新增） |
| `metrics_data_json`      | TEXT            | 指标数据 JSON 原文                               |
| `detection_started_at`   | TIMESTAMP       | 检测开始时间                                     |
| `detection_completed_at` | TIMESTAMP       | 检测完成时间                                     |
| `status`                 | TINYINT         | 0 成功 / 1 失败 / 2 部分成功                     |
| `error_message`          | VARCHAR         | 错误信息                                         |
| `create_time`            | TIMESTAMP       | 记录创建时间                                     |

### 1.4 现有 Mapper 方法

| 方法                                                       | SQL 关键条件                                                                             |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `selectLatestByGitUrl(gitUrl)`                             | `WHERE git_url=#{gitUrl} AND status=0 ORDER BY branch_name, detection_completed_at DESC` |
| `selectByPipelineRunId(gitUrl, branchName, pipelineRunId)` | 三条件精确匹配，`LIMIT 1`                                                                |

## 2. 设计目标

1. **机机接口**：挂载在现有 `InternalProjectRepoController`（类级路径 `/project-repo/internal`），与前端 `CodeMetricsController` 隔离
2. **结构等价**：返回 `CodeMetricsSnapshotDTO`，含 `metrics_data_json` 原文，由消费方（codecheck）自行解析
3. **commit 精确关联**：按 `git_url + branch_name + commit_id` 三元组精确匹配，同一 commit 重跑取 `detection_completed_at` 最新一条
4. **失败过滤**：仅返回 `status = 0` 的成功度量记录
5. **批量优化**：一次性三元组 IN 关联，避免 codecheck 侧 N+1 Feign 调用
6. **契约可演进**：coderepo 后续改 `metrics_data_json` 字段不影响 HTTP 接口契约

## 3. 整体方案

### 3.1 调用链路

```
codecheck Feign client（CodeMetricsFeignClient）
  └─ POST /project-repo/internal/metrics/code/latest-by-commit/batch
       └─ InternalProjectRepoController#getLatestMetricsByCommitBatch
            └─ CodeMetricsServiceImpl#getLatestMetricsByCommitBatch
                 └─ CodeMetricsRecordMapper#selectLatestByCommitBatch
                      └─ SQL: WHERE status=0 AND (git_url, branch_name, commit_id) IN (...)
                            ORDER BY git_url, branch_name, detection_completed_at DESC
                 └─ 按 (gitUrl, branchName, commitId) 分组，每组取 detection_completed_at 最大一条
                 └─ 转 List<CodeMetricsSnapshotDTO> 返回
```

### 3.2 与现有 Service 的隔离

不复用 `getLatestMetricsByGitUrl`：

- 现有方法的「合并 5 指标」语义与新需求不符
- 现有方法返回 `BranchMetricsVO`（5 个固定指标），新需求返回 `metrics_data_json` 原文
- 解耦后，前端页面逻辑不受新接口影响

## 4. 接口设计

### 4.1 Controller

修改 [InternalProjectRepoController.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/controller/InternalProjectRepoController.java)（现有机机接口专用 Controller，类级路径 `/project-repo/internal`）：

```java
/** 【机机接口】批量查询代码度量记录：按 (gitUrl, branchName, commitId) 三元组 IN 精确关联 */
@PostMapping("/metrics/code/latest-by-commit/batch")
public DataResult<List<CodeMetricsSnapshotDTO>> getLatestMetricsByCommitBatch(
    @Valid @RequestBody @Size(min = 1, max = METRICS_BATCH_MAX_SIZE)
        List<LatestMetricsByCommitQueryDTO> queries) {
  logger.info("getLatestMetricsByCommitBatch entry, size={}", queries.size());
  List<CodeMetricsSnapshotDTO> dtos = codeMetricsService.getLatestMetricsByCommitBatch(queries);
  return DataResult.successData(dtos);
}
```

> 完整路径为 `POST /project-repo/internal/metrics/code/latest-by-commit/batch`。不提供单条接口：单条场景由调用方以 1 元素列表复用 batch 接口，避免维护两套契约。

### 4.2 入参 DTO

新增 [LatestMetricsByCommitQueryDTO.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/entity/dto/metrics/LatestMetricsByCommitQueryDTO.java)：

```java
package com.openlibing.coderepo.business.entity.dto.metrics;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class LatestMetricsByCommitQueryDTO {
  /** 代码仓地址（对应 code_metrics_record.git_url） */
  @NotBlank
  private String gitUrl;

  /** 分支名（对应 code_metrics_record.branch_name） */
  @NotBlank
  private String branchName;

  /** commit ID（对应 code_metrics_record.commit_id，由插件端上报） */
  @NotBlank
  private String commitId;
}
```

### 4.3 出参 DTO

新增 [CodeMetricsSnapshotDTO.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/entity/dto/metrics/CodeMetricsSnapshotDTO.java)：

```java
package com.openlibing.coderepo.business.entity.dto.metrics;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.openlibing.coderepo.common.utils.common.DateUtil;
import java.util.Date;
import lombok.Data;

@Data
public class CodeMetricsSnapshotDTO {
  private String gitUrl;
  private String branchName;
  private String pipelineRunId;
  private String runNumber;

  /** commit ID（对应 code_metrics_record.commit_id） */
  private String commitId;

  /** 指标数据 JSON 原文（codecheck 侧自行解析取 codeScale / avgCyclomaticComplexity 等） */
  private String metricsDataJson;

  @JsonFormat(pattern = DateUtil.YYYYMMDDHHMMSS, timezone = "GMT+8")
  private Date detectionStartedAt;

  @JsonFormat(pattern = DateUtil.YYYYMMDDHHMMSS, timezone = "GMT+8")
  private Date detectionCompletedAt;
}
```

> 设计为返回 `metricsDataJson` 原文而非分解字段，避免 coderepo 改一个字段就要改 VO；codecheck 侧 `StaticAlarmSummaryOperation` 自己解析 JSON 取 `codeScale` / `avgCyclomaticComplexity` / `totalCodeDuplicationRate` / `totalFileDuplicationRate` + 6 个新增字段。

### 4.4 Service

修改 [CodeMetricsService.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/service/CodeMetricsService.java) + [Impl](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/service/impl/CodeMetricsServiceImpl.java)：

```java
public interface CodeMetricsService {
  // ... 现有方法保持不变

  /** 批量查询：按 (gitUrl, branchName, commitId) 三元组精确关联，每个三元组取 detection_completed_at 最大的一条 */
  List<CodeMetricsSnapshotDTO> getLatestMetricsByCommitBatch(List<LatestMetricsByCommitQueryDTO> queries);
}
```

**ServiceImpl 实现要点**：

```java
@Override
public List<CodeMetricsSnapshotDTO> getLatestMetricsByCommitBatch(List<LatestMetricsByCommitQueryDTO> queries) {
  if (CollectionUtils.isEmpty(queries)) {
    return Collections.emptyList();
  }
  List<CodeMetricsRecordEntity> entities = codeMetricsRecordMapper.selectLatestByCommitBatch(queries);
  if (CollectionUtils.isEmpty(entities)) {
    return Collections.emptyList();
  }
  // 按 (gitUrl, branchName, commitId) 分组，每组取 detection_completed_at 最大的一条
  // 完成时间为空的记录不参与「最新」竞争（null 兜底比较）
  Map<String, CodeMetricsRecordEntity> latestByGroup = entities.stream()
      .collect(Collectors.toMap(
          e -> e.getGitUrl() + "|" + e.getBranchName() + "|" + e.getCommitId(),
          Function.identity(),
          (a, b) -> {
            Date ta = a.getDetectionCompletedAt();
            Date tb = b.getDetectionCompletedAt();
            if (ta == null) { return b; }
            if (tb == null) { return a; }
            return ta.after(tb) ? a : b;
          }));
  return latestByGroup.values().stream()
      .sorted(Comparator.comparing(CodeMetricsRecordEntity::getGitUrl)
          .thenComparing(CodeMetricsRecordEntity::getBranchName))
      .map(CodeMetricsServiceImpl::toSnapshotDto)
      .collect(Collectors.toList());
}

private static CodeMetricsSnapshotDTO toSnapshotDto(CodeMetricsRecordEntity entity) {
  CodeMetricsSnapshotDTO dto = new CodeMetricsSnapshotDTO();
  dto.setGitUrl(entity.getGitUrl());
  dto.setBranchName(entity.getBranchName());
  dto.setPipelineRunId(entity.getPipelineRunId());
  dto.setRunNumber(entity.getRunNumber());
  dto.setCommitId(entity.getCommitId());
  dto.setMetricsDataJson(entity.getMetricsDataJson());
  dto.setDetectionStartedAt(entity.getDetectionStartedAt());
  dto.setDetectionCompletedAt(entity.getDetectionCompletedAt());
  return dto;
}
```

### 4.5 Mapper

修改 [CodeMetricsRecordMapper.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/mapper/CodeMetricsRecordMapper.java) + [xml](file:///d:/projects/openlibing/openlibing-coderepo/src/main/resources/mapper/CodeMetricsRecordMapper.xml)：

```java
public interface CodeMetricsRecordMapper {
  // ... 现有方法保持不变

  /** 批量：一次性三元组 IN 关联，返回所有命中记录（Service 层分组取最新一条） */
  List<CodeMetricsRecordEntity> selectLatestByCommitBatch(
      @Param("queries") List<LatestMetricsByCommitQueryDTO> queries);
}
```

**Mapper XML**：

```xml
<!-- 【机机接口】批量查询：按 (git_url, branch_name, commit_id) 三元组 IN 精确关联 -->
<select id="selectLatestByCommitBatch" resultType="...CodeMetricsRecordEntity">
  SELECT id, git_url, branch_name, pipeline_run_id, run_number, commit_id,
         metrics_data_json, detection_started_at, detection_completed_at,
         status, error_message, create_time
  FROM code_metrics_record
  WHERE status = 0
    AND (git_url, branch_name, commit_id) IN (
      <foreach collection="queries" item="q" separator=",">
        (#{q.gitUrl}, #{q.branchName}, #{q.commitId})
      </foreach>
    )
  ORDER BY git_url, branch_name, detection_completed_at DESC
</select>
```

### 4.6 数据库改动与索引

- `code_metrics_record` 新增 `commit_id VARCHAR(64)` 列（Liquibase changeSet `20260824_add_commit_id_to_code_metrics_record`，幂等：columnExists 前置检查）
- 表创建时已有的 `idx_git_url_branch (git_url, branch_name)` 联合索引可支撑批量 SQL 的前缀过滤；`(git_url, branch_name, commit_id)` 全量联合索引留待性能验证后评估（见 proposal 遗留项）

## 5. 插件上报改动

### 5.1 metrics_data_json 新增 6 个字段

| #   | 字段名                        | 类型    | 用途         |
| --- | ----------------------------- | ------- | ------------ |
| 1   | `codeLineTotal`               | Integer | 总代码行数   |
| 2   | `commentLines`                | Integer | 注释行数     |
| 3   | `complexityCount`             | Integer | 复杂度计数   |
| 4   | `cyclomaticComplexityPerFile` | Double  | 文件圈复杂度 |
| 5   | `duplicatedBlocks`            | Integer | 重复块数     |
| 6   | `duplicatedLines`             | Integer | 重复行数     |

插件端（code-metrics-scan）同时上报 `commitId`（取 `process.env['ATOMGIT_SHA']`），由 coderepo `readMetaField` 解析 OBS JSON 中的 `commitId` 入库到 `commit_id` 列，作为本接口的关联键。

### 5.2 字段缺失容忍

旧度量记录没有新字段，消费方（codecheck）自行兜底（置 0 / null），coderepo 不强制补默认值。

## 6. 改动文件清单

### 6.1 新增

| 文件                                 | 说明          |
| ------------------------------------ | ------------- |
| `LatestMetricsByCommitQueryDTO.java` | HTTP 入参 DTO |
| `CodeMetricsSnapshotDTO.java`        | HTTP 出参 DTO |

### 6.2 修改

| 文件                                 | 说明                                                                 |
| ------------------------------------ | -------------------------------------------------------------------- |
| `InternalProjectRepoController.java` | 新增机机接口 `POST /metrics/code/latest-by-commit/batch`             |
| `CodeMetricsService.java`            | 新增 `getLatestMetricsByCommitBatch` 方法签名                        |
| `CodeMetricsServiceImpl.java`        | 新增 `getLatestMetricsByCommitBatch` 实现 + `toSnapshotDto` 私有方法 |
| `CodeMetricsRecordMapper.java`       | 新增 `selectLatestByCommitBatch` 方法签名                            |
| `CodeMetricsRecordMapper.xml`        | 新增三元组 IN 批量 SQL                                               |
| `CodeMetricsRecordEntity.java`       | 新增 `commitId` 字段                                                 |
| `db.changelog.xml`                   | 新增 `commit_id` 列（Liquibase，幂等）                               |
| 插件上报逻辑（code-metrics-scan）    | `metrics_data_json` 新增 6 个字段 + `commitId` 上报                  |

### 6.3 测试

| 文件                              | 说明                                |
| --------------------------------- | ----------------------------------- |
| `CodeMetricsServiceImplTest.java` | 修改：补充批量查询 Service 方法用例 |

## 7. 测试策略

### 7.1 单元测试

| 用例                                        | 期望                                                                     |
| ------------------------------------------- | ------------------------------------------------------------------------ |
| 同一 commit 重跑多条记录                    | 返回 `detection_completed_at` 最大的一条（完成时间为空的记录不参与竞争） |
| 批量查询无命中                              | 返回空 list，不抛异常                                                    |
| 批量入参为空 / null                         | Service 层短路返回空 list，不触达 Mapper                                 |
| 批量查询多条命中（混合 repo/branch/commit） | 每个三元组各返回 1 条，按 `gitUrl, branchName` 排序                      |
| 批量查询部分未命中                          | 命中的返回，未命中的不返回（结果数 ≤ 入参数）                            |
| 批量查询入参 > 100 条                       | Controller 层 `@Size(max=100)` 校验拒绝                                  |
| 失败记录过滤                                | `status != 0` 的记录不返回                                               |

### 7.2 集成测试

构造真实 `code_metrics_record` 数据，验证：

- 批量 SQL 在 MySQL 8 上的 IN 元组语法性能
- 现有 `idx_git_url_branch` 索引是否被命中
- 多仓库 / 多分支 / 同 commit 重跑场景下的正确分组

## 8. 关键设计决策

1. **机机接口挂载现有 `InternalProjectRepoController`**：复用现有机机接口专用 Controller，不新建类，避免同类 Controller 碎片化
2. **返回 JSON 原文**：返回 `metricsDataJson` 原文而非分解字段，解耦 coderepo 字段演进与 HTTP 契约
3. **不复用现有 `getLatestMetricsByGitUrl`**：现有「合并 5 指标」语义与新需求「取一条整体 record」不同
4. **commit 三元组精确关联**（取代早期 `git_url + branch_name + beforeTime` 时序窗口方案）：同一 commit 触发的扫描天然对应同一份代码快照，无需时序窗口，彻底避免度量扫描时刻偏离导致指标失真
5. **批量 SQL 用 IN 元组**：一次性关联避免 codecheck 侧 N+1 Feign 调用
6. **status=0 过滤**：仅返回成功度量记录，避免取到失败数据

## 9. 后续演进

| 项                                                   | 时机               |
| ---------------------------------------------------- | ------------------ |
| 批量接口 SQL 在 MySQL 8 上的 IN 元组语法性能验证     | 联调时             |
| `(git_url, branch_name, commit_id)` 全量联合索引评估 | 上线后 RT 不达标时 |
| 现有 `idx_git_url_branch` 索引实际命中率监控         | 上线后 RT 不达标时 |
