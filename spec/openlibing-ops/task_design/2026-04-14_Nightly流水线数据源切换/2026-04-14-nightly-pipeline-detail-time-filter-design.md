# NightlyPipelineDetail时间筛选和格式化设计文档

## 1. 概述

本文档描述了nightly-dashboard-detail接口的时间筛选功能增强和时间格式化需求的设计方案。

### 1.1 需求背景

当前nightly-dashboard-detail接口只支持基于pipeline_run_endtime的单一时间筛选，无法满足用户对pipelineRunStarttime和pipelineRunEndtime分别进行时间段筛选的需求。同时，返回的时间数据格式包含'T'字符，不符合用户期望的显示格式。

### 1.2 需求目标

1. 支持pipelineRunStarttime和pipelineRunEndtime各自的时间段筛选
2. 返回的时间数据格式从带'T'的ISO格式改为yyyy-MM-dd HH:mm:ss格式

## 2. 需求说明

### 2.1 功能需求

#### 2.1.1 时间筛选功能

接口需要支持以下四个时间参数的筛选：
- `createStartDate`：流水线开始时间起始（筛选pipeline_run_starttime）
- `createEndDate`：流水线开始时间结束（筛选pipeline_run_starttime）
- `finishStartDate`：流水线结束时间起始（筛选pipeline_run_endtime）
- `finishEndDate`：流水线结束时间结束（筛选pipeline_run_endtime）

筛选逻辑：
- createStartDate/createEndDate和finishStartDate/finishEndDate为AND关系
- 所有参数都是可选的
- 如果只提供部分参数，只对提供的参数进行筛选

#### 2.1.2 时间格式化

返回的时间字段需要格式化为以下格式：
- `pipelineRunStarttime`：yyyy-MM-dd HH:mm:ss
- `pipelineRunEndtime`：yyyy-MM-dd HH:mm:ss

### 2.2 非功能需求

- **性能**：时间筛选不应显著影响查询性能
- **兼容性**：新增参数不影响现有功能
- **可维护性**：代码修改应遵循现有代码规范

## 3. 设计方案

### 3.1 技术选型

采用**Mapper XML添加筛选条件 + JSON注解时间格式化**方案：

**理由：**
1. 保持类型安全：字段类型保持LocalDateTime
2. 性能好：无需内存遍历转换
3. 代码简洁：只需添加注解和SQL条件
4. 符合Spring Boot最佳实践

### 3.2 架构设计

```
Controller层 (CommonController)
    ↓
Service层 (NightlyPipelineDetailServiceImpl)
    ↓
Mapper层 (DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper)
    ↓
数据库 (dwr_rd_efc_build_fact_nightly_test_case_pipeline_run)
```

### 3.3 数据库设计

无需修改数据库表结构，利用现有字段：
- `pipeline_run_starttime`：流水线开始时间
- `pipeline_run_endtime`：流水线结束时间

### 3.4 接口设计

#### 3.4.1 请求参数

```java
public class NightlyPipelineDetailReq extends DetailReq {
    private String pipelineId;
    private String pipelineName;
    private String pipelineStatus;
    // 继承自DetailReq的时间参数
    private LocalDate createStartDate;
    private LocalDate createEndDate;
    private LocalDate finishStartDate;
    private LocalDate finishEndDate;
}
```

#### 3.4.2 响应参数

```java
public class NightlyPipelineDetailResp extends DetailResp {
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime pipelineRunStarttime;
    
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime pipelineRunEndtime;
    // ... 其他字段
}
```

### 3.5 核心逻辑

#### 3.5.1 时间筛选逻辑

在Mapper XML中添加时间筛选条件：

```xml
<if test="req.createStartDate != null">
    AND pipeline_run_starttime &gt;= #{req.createStartDate}
</if>
<if test="req.createEndDate != null">
    AND pipeline_run_starttime &lt;= #{req.createEndDate}
</if>
<if test="req.finishStartDate != null">
    AND pipeline_run_endtime &gt;= #{req.finishStartDate}
</if>
<if test="req.finishEndDate != null">
    AND pipeline_run_endtime &lt;= #{req.finishEndDate}
</if>
```

#### 3.5.2 时间格式化逻辑

在Response类中使用`@JsonFormat`注解：

```java
@JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
private LocalDateTime pipelineRunStarttime;

@JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
private LocalDateTime pipelineRunEndtime;
```

### 3.6 数据流

```
用户请求 → CommonController → NightlyPipelineDetailServiceImpl
    ↓
携带createStartDate/createEndDate/finishStartDate/finishEndDate参数
    ↓
DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper
    ↓
执行SQL查询（带时间筛选条件）
    ↓
返回List<DwrRdEfcBuildFactNightlyTestCasePipelineRun>
    ↓
转换为List<NightlyPipelineDetailResp>
    ↓
Jackson序列化时应用@JsonFormat注解
    ↓
返回JSON响应（时间格式：yyyy-MM-dd HH:mm:ss）
```

## 4. 实施计划

### 4.1 修改文件清单

1. **DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.xml**
   - 修改`getNightlyPipelineDetail`查询，添加时间筛选条件
   - 修改`getNightlyPipelineDetailCount`查询，添加时间筛选条件

2. **NightlyPipelineDetailResp.java**
   - 为`pipelineRunStarttime`字段添加`@JsonFormat`注解
   - 为`pipelineRunEndtime`字段添加`@JsonFormat`注解

### 4.2 实施步骤

1. 修改Mapper XML文件，添加时间筛选条件
2. 修改Response类，添加JSON格式化注解
3. 编写单元测试
4. 编写集成测试
5. 执行测试验证

## 5. 测试策略

### 5.1 单元测试

- 测试时间筛选条件的正确性
- 测试边界情况（跨天、跨月）
- 测试空值处理

### 5.2 集成测试

- 测试完整的查询流程
- 测试时间格式化是否正确
- 测试参数验证

### 5.3 边界测试

- 测试createStartDate > createEndDate的情况
- 测试finishStartDate > finishEndDate的情况
- 测试只提供部分时间参数的情况

## 6. 风险与应对

### 6.1 潜在风险

1. **性能风险**：新增时间筛选条件可能影响查询性能
2. **兼容性风险**：可能影响现有调用方
3. **数据一致性**：时间参数格式可能不一致

### 6.2 应对措施

1. 确保时间字段上有合适的索引
2. 保持向后兼容，所有新参数都是可选的
3. 使用Spring Boot的参数验证机制

## 7. 验收标准

1. nightly-dashboard-detail接口支持pipelineRunStarttime和pipelineRunEndtime各自的时间段筛选
2. 返回的时间数据格式为yyyy-MM-dd HH:mm:ss，不包含'T'字符
3. 所有单元测试和集成测试通过
4. 性能测试通过，查询时间不超过2秒
5. 向后兼容性测试通过

## 8. 附录

### 8.1 相关文件

- `src/main/java/com/openlibing/ops/api/request/common/detail/NightlyPipelineDetailReq.java`
- `src/main/java/com/openlibing/ops/api/response/common/detail/NightlyPipelineDetailResp.java`
- `src/main/java/com/openlibing/ops/domain/mapper/pipeline/DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.java`
- `src/main/resources/mapper/DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.xml`

### 8.2 相关文档

- `docs/superpowers/specs/2026-04-13-pipeline-job-refactor-design.md`
- `docs/接口文档-feature_16.md`
