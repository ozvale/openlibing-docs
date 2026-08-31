# coderepo 暴露代码度量时序关联查询接口 - 技术设计

> 状态：最终方案。等待开发完成。
> 关联 codecheck 仓 spec：`openlibing-codecheck/task_design/full-codecheck-record-codeql-fallback` §4.6.7

## 1. 现状回顾

### 1.1 现有 Controller

[CodeMetricsController.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/controller/CodeMetricsController.java) 类级路径 `/metrics/code`，现有 4 个 POST 接口，**全部面向前端或上游上报**：

| 路径 | 用途 |
|---|---|
| `POST /metrics/code/report` | apig 上报接口（OBS 中转） |
| `POST /metrics/code/file-detail` | 文件级指标详情（前端分页查询） |
| `POST /metrics/code/file-content` | 文件代码视图（前端） |
| `POST /metrics/code/duplication-block/detail` | 重复块详情（前端） |

**关键发现**：现有 Controller 没有任何「按 gitUrl 取最新度量」的 HTTP 接口暴露给后端服务调用。

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

| 字段 | 类型 | 用途 |
|---|---|---|
| `id` | BIGINT (雪花ID) | 主键 |
| `git_url` | VARCHAR | 仓库 URL |
| `branch_name` | VARCHAR | 分支名 |
| `pipeline_run_id` | VARCHAR | 流水线执行记录 ID |
| `run_number` | VARCHAR | 流水线运行编号 |
| `metrics_data_json` | TEXT | 指标数据 JSON 原文 |
| `detection_started_at` | TIMESTAMP | 检测开始时间 |
| `detection_completed_at` | TIMESTAMP | 检测完成时间 |
| `status` | TINYINT | 0 成功 / 1 失败 / 2 部分成功 |
| `error_message` | VARCHAR | 错误信息 |
| `create_time` | TIMESTAMP | 记录创建时间 |

### 1.4 现有 Mapper 方法

| 方法 | SQL 关键条件 |
|---|---|
| `selectLatestByGitUrl(gitUrl)` | `WHERE git_url=#{gitUrl} AND status=0 ORDER BY branch_name, detection_completed_at DESC` |
| `selectByPipelineRunId(gitUrl, branchName, pipelineRunId)` | 三条件精确匹配，`LIMIT 1` |

## 2. 设计目标

1. **机机接口隔离**：新增 `MachineApiCodeMetricsController`，与现有前端 `CodeMetricsController` 分离
2. **结构等价**：返回 `CodeMetricsSnapshotDTO`，含 `metrics_data_json` 原文，由消费方（codecheck）自行解析
3. **时序关联**：按 `git_url + branch_name + detection_completed_at < beforeTime` 取最近一条
4. **失败过滤**：仅返回 `status = 0` 的成功度量记录
5. **批量优化**：一次性 IN 关联，避免 codecheck 侧 N+1 Feign 调用
6. **契约可演进**：coderepo 后续改 `metrics_data_json` 字段不影响 HTTP 接口契约

## 3. 整体方案

### 3.1 调用链路

```
codecheck Feign client
  └─ POST /machine-api/v1/metrics/code/latest-before-time/batch
       └─ MachineApiCodeMetricsController#getLatestMetricsBeforeTimeBatch
            └─ CodeMetricsServiceImpl#getLatestMetricsBeforeTimeBatch
                 └─ CodeMetricsRecordMapper#selectLatestBeforeTimeBatch
                      └─ SQL: WHERE status=0 AND (git_url, branch_name, detection_completed_at) IN (...)
                            ORDER BY git_url, branch_name, detection_completed_at DESC
                 └─ 按 (gitUrl, branchName) 分组，每组取 detection_completed_at 最大一条
                 └─ 转 List<CodeMetricsSnapshotDTO> 返回
```

### 3.2 与现有 Service 的隔离

不复用 `getLatestMetricsByGitUrl`：
- 现有方法的「合并 5 指标」语义与新需求不符
- 现有方法返回 `BranchMetricsVO`（5 个固定指标），新需求返回 `metrics_data_json` 原文
- 解耦后，前端页面逻辑不受新接口影响

## 4. 接口设计

### 4.1 Controller

新增 [MachineApiCodeMetricsController.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/controller/MachineApiCodeMetricsController.java)：

```java
@RestController
@RequestMapping("/machine-api/v1/metrics/code")
public class MachineApiCodeMetricsController {
  private static final Logger logger = LoggerFactory.getLogger(MachineApiCodeMetricsController.class);

  @Autowired private CodeMetricsService codeMetricsService;

  /** 单条查询（备用，codecheck 主要走 batch 接口） */
  @PostMapping("/latest-before-time")
  public DataResult<CodeMetricsSnapshotDTO> getLatestMetricsBeforeTime(
      @Valid @RequestBody LatestMetricsBeforeTimeQueryDTO query) {
    logger.info("getLatestMetricsBeforeTime entry, gitUrl={}, branchName={}, beforeTime={}",
        query.getGitUrl(), query.getBranchName(), query.getBeforeTime());
    CodeMetricsSnapshotDTO dto = codeMetricsService.getLatestMetricsBeforeTime(
        query.getGitUrl(), query.getBranchName(), query.getBeforeTime());
    return DataResult.successData(dto);
  }

  /** 批量查询（codecheck 主要调用入口） */
  @PostMapping("/latest-before-time/batch")
  public DataResult<List<CodeMetricsSnapshotDTO>> getLatestMetricsBeforeTimeBatch(
      @Valid @RequestBody @Size(min = 1, max = 100) List<LatestMetricsBeforeTimeQueryDTO> queries) {
    logger.info("getLatestMetricsBeforeTimeBatch entry, size={}", queries.size());
    List<CodeMetricsSnapshotDTO> dtos = codeMetricsService.getLatestMetricsBeforeTimeBatch(queries);
    return DataResult.successData(dtos);
  }
}
```

### 4.2 入参 DTO

新增 [LatestMetricsBeforeTimeQueryDTO.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/entity/dto/metrics/LatestMetricsBeforeTimeQueryDTO.java)：

```java
package com.openlibing.coderepo.business.entity.dto.metrics;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.Date;
import lombok.Data;

@Data
public class LatestMetricsBeforeTimeQueryDTO {
  /** 代码仓地址（对应 code_metrics_record.git_url） */
  @NotBlank
  private String gitUrl;

  /** 分支名（对应 code_metrics_record.branch_name） */
  @NotBlank
  private String branchName;

  /** 时序过滤上界（取 detection_completed_at < beforeTime 的最近一条） */
  @NotNull
  private Date beforeTime;
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

  /** 指标数据 JSON 原文（codecheck 侧自行解析取 codeScale / avgCyclomaticComplexity 等） */
  private String metricsDataJson;

  @JsonFormat(pattern = DateUtil.YYYYMMDDHHMMSS, timezone = "GMT+8")
  private Date detectionStartedAt;

  @JsonFormat(pattern = DateUtil.YYYYMMDDHHMMSS, timezone = "GMT+8")
  private Date detectionCompletedAt;
}
```

> 设计为返回 `metricsDataJson` 原文而非分解字段，避免 coderepo 改一个字段就要改 VO；codecheck 侧 `CodeQlSummaryOperation` 自己解析 JSON 取 `codeScale` / `avgCyclomaticComplexity` / `totalCodeDuplicationRate` / `totalFileDuplicationRate` + 6 个新增字段。

### 4.4 Service

修改 [CodeMetricsService.java](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/service/CodeMetricsService.java) + [Impl](file:///d:/projects/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/service/impl/CodeMetricsServiceImpl.java)：

```java
public interface CodeMetricsService {
  // ... 现有方法保持不变

  /** 单条查询：取 detection_completed_at < beforeTime 的最近一条成功度量记录 */
  CodeMetricsSnapshotDTO getLatestMetricsBeforeTime(String gitUrl, String branchName, Date beforeTime);

  /** 批量查询：一次性 IN 关联，每个 (gitUrl, branchName) 取 detection_completed_at 最大的一条 */
  List<CodeMetricsSnapshotDTO> getLatestMetricsBeforeTimeBatch(List<LatestMetricsBeforeTimeQueryDTO> queries);
}
```

**ServiceImpl 实现要点**：

```java
@Override
public CodeMetricsSnapshotDTO getLatestMetricsBeforeTime(String gitUrl, String branchName, Date beforeTime) {
  CodeMetricsRecordEntity entity = codeMetricsRecordMapper.selectLatestBeforeTime(gitUrl, branchName, beforeTime);
  return entity == null ? null : toSnapshotDto(entity);
}

@Override
public List<CodeMetricsSnapshotDTO> getLatestMetricsBeforeTimeBatch(List<LatestMetricsBeforeTimeQueryDTO> queries) {
  if (CollectionUtils.isEmpty(queries)) {
    return Collections.emptyList();
  }
  List<CodeMetricsRecordEntity> entities = codeMetricsRecordMapper.selectLatestBeforeTimeBatch(queries);
  // 按 (gitUrl, branchName) 分组，每组取 detection_completed_at 最大的一条
  Map<String, CodeMetricsRecordEntity> latestByGroup = entities.stream()
      .collect(Collectors.toMap(
          e -> e.getGitUrl() + "|" + e.getBranchName(),
          Function.identity(),
          (a, b) -> a.getDetectionCompletedAt().after(b.getDetectionCompletedAt()) ? a : b));
  return latestByGroup.values().stream()
      .sorted(Comparator.comparing(CodeMetricsRecordEntity::getGitUrl)
          .thenComparing(CodeMetricsRecordEntity::getBranchName))
      .map(this::toSnapshotDto)
      .collect(Collectors.toList());
}

private CodeMetricsSnapshotDTO toSnapshotDto(CodeMetricsRecordEntity entity) {
  CodeMetricsSnapshotDTO dto = new CodeMetricsSnapshotDTO();
  dto.setGitUrl(entity.getGitUrl());
  dto.setBranchName(entity.getBranchName());
  dto.setPipelineRunId(entity.getPipelineRunId());
  dto.setRunNumber(entity.getRunNumber());
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

  /** 单条：取 detection_completed_at < beforeTime 的最近一条 */
  CodeMetricsRecordEntity selectLatestBeforeTime(
      @Param("gitUrl") String gitUrl,
      @Param("branchName") String branchName,
      @Param("beforeTime") Date beforeTime);

  /** 批量：一次性 IN 关联，返回所有命中记录（Service 层分组取最近一条） */
  List<CodeMetricsRecordEntity> selectLatestBeforeTimeBatch(
      @Param("queries") List<LatestMetricsBeforeTimeQueryDTO> queries);
}
```

**Mapper XML**：

```xml
<!-- 单条 -->
<select id="selectLatestBeforeTime" resultType="...CodeMetricsRecordEntity">
  SELECT id, git_url, branch_name, pipeline_run_id, run_number,
         metrics_data_json, detection_started_at, detection_completed_at,
         status, error_message, create_time
  FROM code_metrics_record
  WHERE git_url = #{gitUrl}
    AND branch_name = #{branchName}
    AND status = 0
    AND detection_completed_at &lt; #{beforeTime}
  ORDER BY detection_completed_at DESC
  LIMIT 1
</select>

<!-- 批量 -->
<select id="selectLatestBeforeTimeBatch" resultType="...CodeMetricsRecordEntity">
  SELECT id, git_url, branch_name, pipeline_run_id, run_number,
         metrics_data_json, detection_started_at, detection_completed_at,
         status, error_message, create_time
  FROM code_metrics_record
  WHERE status = 0
    AND (git_url, branch_name, detection_completed_at) IN (
      <foreach collection="queries" item="q" separator=",">
        (#{q.gitUrl}, #{q.branchName}, #{q.beforeTime})
      </foreach>
    )
  ORDER BY git_url, branch_name, detection_completed_at DESC
</select>
```

> 注意：XML 中 `<` 需用 `&lt;` 转义，避免 MyBatis 解析冲突。

### 4.6 索引建议

在 `code_metrics_record` 表上建立联合索引：

```sql
CREATE INDEX idx_metrics_git_branch_status_completed
ON code_metrics_record(git_url, branch_name, status, detection_completed_at DESC);
```

支持单条查询和批量查询的 IN 元组语法。

## 5. 插件上报改动

### 5.1 metrics_data_json 新增 6 个字段

| # | 字段名 | 类型 | 用途 |
|---|---|---|---|
| 1 | `codeLineTotal` | Integer | 总代码行数 |
| 2 | `commentLines` | Integer | 注释行数 |
| 3 | `complexityCount` | Integer | 复杂度计数 |
| 4 | `cyclomaticComplexityPerFile` | Double | 文件圈复杂度 |
| 5 | `duplicatedBlocks` | Integer | 重复块数 |
| 6 | `duplicatedLines` | Integer | 重复行数 |

### 5.2 字段缺失容忍

旧度量记录没有新字段，消费方（codecheck）自行兜底（置 0 / null），coderepo 不强制补默认值。

## 6. 改动文件清单

### 6.1 新增

| 文件 | 说明 |
|---|---|
| `MachineApiCodeMetricsController.java` | 机机接口专用 Controller |
| `LatestMetricsBeforeTimeQueryDTO.java` | HTTP 入参 DTO |
| `CodeMetricsSnapshotDTO.java` | HTTP 出参 DTO |

### 6.2 修改

| 文件 | 说明 |
|---|---|
| `CodeMetricsService.java` | 新增 2 个 Service 方法签名 |
| `CodeMetricsServiceImpl.java` | 新增 2 个 Service 方法实现 + `toSnapshotDto` 私有方法 |
| `CodeMetricsRecordMapper.java` | 新增 2 个 Mapper 方法签名 |
| `CodeMetricsRecordMapper.xml` | 新增 2 条 SQL |
| 插件上报逻辑 | `metrics_data_json` 新增 6 个字段 |

### 6.3 测试

| 文件 | 说明 |
|---|---|
| `MachineApiCodeMetricsControllerTest.java` | 新增：HTTP 接口契约测试 |
| `CodeMetricsServiceImplTest.java` | 修改：补充新 Service 方法用例 |
| `CodeMetricsRecordMapperTest.java` | 修改：补充新 Mapper 方法用例 |

## 7. 测试策略

### 7.1 单元测试

| 用例 | 期望 |
|---|---|
| 单条查询命中 | 返回 `detection_completed_at < beforeTime` 的最近一条，含 `metricsDataJson` 原文 |
| 单条查询未命中（无成功记录） | 返回 null，不抛异常 |
| 单条查询过滤失败记录 | `status != 0` 的记录不返回 |
| 批量查询多条命中 | 每个 `(gitUrl, branchName)` 返回 1 条（最大 `detection_completed_at`） |
| 批量查询部分未命中 | 命中的返回，未命中的不返回（结果数 ≤ 入参数） |
| 批量查询入参 > 100 条 | Controller 层 `@Size(max=100)` 校验拒绝 |
| 批量查询入参为空 | Service 层返回空 list |
| 度量扫描晚于 beforeTime | 该记录不返回（时序条件过滤） |

### 7.2 集成测试

构造真实 `code_metrics_record` 数据，验证：
- 单条 + 批量 SQL 在 MySQL 8 上的 IN 元组语法性能
- 索引 `idx_metrics_git_branch_status_completed` 是否被命中
- 多分支同仓库场景下的正确分组

## 8. 关键设计决策

1. **机机接口隔离**：新建 `MachineApiCodeMetricsController` 而非扩展 `CodeMetricsController`，避免前端接口契约被机机调用方牵制
2. **返回 JSON 原文**：返回 `metricsDataJson` 原文而非分解字段，解耦 coderepo 字段演进与 HTTP 契约
3. **不复用现有 `getLatestMetricsByGitUrl`**：现有「合并 5 指标」语义与新需求「取一条整体 record」不同
4. **批量 SQL 用 IN 元组**：一次性关联避免 codecheck 侧 N+1 Feign 调用
5. **status=0 过滤**：仅返回成功度量记录，避免取到失败数据
6. **`detection_completed_at` 时序字段**：表示度量结果可用时刻，比 `detection_started_at` 更贴近「最近可用度量」语义

## 9. 后续演进

| 项 | 时机 |
|---|---|
| 批量接口 SQL 在 MySQL 8 上的 IN 元组语法性能验证 | 联调时 |
| 索引 `idx_metrics_git_branch_status_completed` 实际命中率监控 | 上线后 RT 不达标时 |
| `metrics_data_json` 6 个新字段最终字段名确认 | 插件改造时 |
| docs 仓 spec 分支名重命名为 `spec-openlibing-coderepo-code-metrics-machine-api-query` | docs PR 创建时 |
