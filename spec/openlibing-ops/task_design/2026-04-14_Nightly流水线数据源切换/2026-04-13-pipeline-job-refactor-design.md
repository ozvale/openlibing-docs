# SdiPipelineJobInfoServiceImpl 改造设计文档

## 需求概述

修改 `SdiPipelineJobInfoServiceImpl#queryDetail` 方法，将数据源从 `SdiPipelineJobInfo` 改为 `dwi_rd_efc_pipeline_run_job` 表，并增加任务类型过滤逻辑。

## 需求详情

### 1. 数据源变更
- 原数据源：`SdiPipelineJobInfo`（内存数据）
- 新数据源：`dwi_rd_efc_pipeline_run_job` 表

### 2. 状态过滤
保留 `PipelineStatusEnum.allShowStatus()` 状态判断，只查询以下状态的任务：
- COMPLETED（成功）
- CANCELED（取消）
- FAILED（失败）
- SKIPPED（跳过）

### 3. 任务类型过滤
根据任务名称前缀判断任务类型，只返回匹配的任务：
- **Build开头**（不区分大小写）→ 编译任务
- **Test或Smoke开头**（不区分大小写）→ 测试任务
- 不匹配任何前缀的任务将被过滤掉

### 4. 请求参数
只支持 `pipelineRunId` 查询：
```json
{
    "category": "pipeline-job",
    "pipelineRunId": "xxx"
}
```

### 5. 返回数据格式
```json
{
    "jobId": "job-123",
    "name": "Build_v2_10_0",
    "type": "编译任务",
    "time": "20.4",
    "result": true,
    "status": "成功",
    "startTime": "2026-04-12 03:00:30",
    "pendingTime": null
}
```

## 技术设计

### 1. 创建实体类

**文件路径**: `src/main/java/com/openlibing/ops/domain/model/pipeline/DwiRdEfcPipelineRunJob.java`

**字段映射**:
| 数据库字段 | Java字段 | 类型 | 说明 |
|-----------|---------|------|------|
| project_id | projectId | String | 项目ID |
| pipeline_id | pipelineId | String | 流水线ID |
| pipeline_run_id | pipelineRunId | String | 流水线运行ID |
| stage_id | stageId | String | 阶段ID |
| job_id | jobId | String | 任务ID |
| pipeline_status | pipelineStatus | String | 流水线状态 |
| job_name | jobName | String | 任务名称 |
| job_status | jobStatus | String | 任务状态 |
| job_start_time | jobStartTime | LocalDateTime | 任务开始时间 |
| job_end_time | jobEndTime | LocalDateTime | 任务结束时间 |
| - | time | BigDecimal | 执行时间（分钟，保留两位小数，SQL计算） |

### 2. 创建Mapper接口

**文件路径**: `src/main/java/com/openlibing/ops/domain/mapper/pipeline/DwiRdEfcPipelineRunJobMapper.java`

**方法定义**:
```java
public interface DwiRdEfcPipelineRunJobMapper extends BaseMapper<DwiRdEfcPipelineRunJob> {
    List<DwiRdEfcPipelineRunJob> queryPipelineJobs(@Param("pipelineRunId") String pipelineRunId,
                                                    @Param("showStatus") List<String> showStatus);
}
```

### 3. 创建Mapper XML

**文件路径**: `src/main/resources/mapper/DwiRdEfcPipelineRunJobMapper.xml`

**SQL逻辑**:
```xml
<select id="queryPipelineJobs" resultMap="PipelineRunJobMap">
    SELECT 
        project_id,
        pipeline_id,
        pipeline_run_id,
        stage_id,
        job_id,
        pipeline_status,
        job_name,
        job_status,
        job_start_time,
        job_end_time,
        ROUND(TIMESTAMPDIFF(SECOND, job_start_time, job_end_time) / 60.0, 2) as time
    FROM dwi_rd_efc_pipeline_run_job
    WHERE pipeline_run_id = #{pipelineRunId}
    AND job_status IN
    <foreach collection="showStatus" open="(" separator="," item="status" close=")">
        #{status}
    </foreach>
    AND (UPPER(job_name) LIKE 'BUILD%' 
         OR UPPER(job_name) LIKE 'TEST%' 
         OR UPPER(job_name) LIKE 'SMOKE%')
    ORDER BY job_start_time ASC, job_name ASC
</select>
```

### 4. 修改PipelineJobResp

**文件路径**: `src/main/java/com/openlibing/ops/api/response/pipeline/PipelineJobResp.java`

**新增构造函数**:
```java
public PipelineJobResp(DwiRdEfcPipelineRunJob job) {
    this.jobId = job.getJobId();
    this.name = job.getJobName();
    this.type = getJobType(job.getJobName());
    
    // 执行时间（从SQL计算结果获取，单位：分钟）
    if (job.getTime() != null) {
        this.time = job.getTime().toString();
    }
    
    // 判断执行结果和状态
    PipelineStatusEnum status = PipelineStatusEnum.valueOf(job.getJobStatus());
    this.result = status.isResult();
    this.status = status.isResult() ? "成功" : "失败";
    
    this.startTime = job.getJobStartTime();
    this.pendingTime = null;
}

private String getJobType(String jobName) {
    if (jobName == null) return null;
    String upperName = jobName.toUpperCase();
    if (upperName.startsWith("BUILD")) return "编译任务";
    if (upperName.startsWith("TEST") || upperName.startsWith("SMOKE")) return "测试任务";
    return null;
}
```

### 5. 修改SdiPipelineJobInfoServiceImpl

**文件路径**: `src/main/java/com/openlibing/ops/domain/service/pipeline/impl/SdiPipelineJobInfoServiceImpl.java`

**修改内容**:
1. 注入 `DwiRdEfcPipelineRunJobMapper`
2. 修改 `queryDetail` 方法：
   - 调用新Mapper查询数据
   - 转换为PipelineJobResp
   - 过滤掉type为null的记录

```java
@Override
public PageResult<PipelineJobResp> queryDetail(PipelineJobDetailReq req) {
    List<String> showStatus = PipelineStatusEnum.allShowStatus();
    List<DwiRdEfcPipelineRunJob> jobList = dwiRdEfcPipelineRunJobMapper.queryPipelineJobs(
        req.getPipelineRunId(), showStatus);
    
    PageResult<PipelineJobResp> result = new PageResult<>();
    List<PipelineJobResp> respList = jobList.stream()
        .map(PipelineJobResp::new)
        .filter(item -> item.getType() != null)
        .toList();
    result.setRecords(respList);
    return result;
}
```

## 数据流程

```
请求 → PipelineJobDetailReq 
     → SdiPipelineJobInfoServiceImpl.queryDetail()
     → DwiRdEfcPipelineRunJobMapper.queryPipelineJobs()
     → SQL查询（过滤状态+过滤任务名称前缀）
     → 返回DwiRdEfcPipelineRunJob列表
     → 转换为PipelineJobResp
     → 过滤type为null的记录
     → 返回结果
```

## 影响范围

### 新增文件
1. `DwiRdEfcPipelineRunJob.java` - 实体类
2. `DwiRdEfcPipelineRunJobMapper.java` - Mapper接口
3. `DwiRdEfcPipelineRunJobMapper.xml` - Mapper XML

### 修改文件
1. `SdiPipelineJobInfoServiceImpl.java` - 修改queryDetail方法
2. `PipelineJobResp.java` - 新增构造函数

### 不受影响
- 请求参数结构（PipelineJobDetailReq）
- 返回数据结构（PipelineJobResp）
- 其他Service实现

## 测试要点

### 1. 功能测试
- 测试按pipelineRunId查询
- 测试状态过滤（只返回COMPLETED、CANCELED、FAILED、SKIPPED状态）
- 测试任务类型过滤（只返回Build、Test、Smoke开头的任务）
- 测试任务类型判断（Build→编译任务，Test/Smoke→测试任务）
- 测试执行时间计算
- 测试执行结果和状态判断

### 2. 边界测试
- pipelineRunId不存在
- pipelineRunId对应没有任务
- 所有任务都不匹配前缀
- 任务开始时间或结束时间为空
- job_status为空

### 3. 性能测试
- 大量任务数据查询性能
- SQL索引是否生效

## 风险评估

### 低风险
- 数据源变更：只影响pipeline-job接口
- 新增代码：不影响现有功能
- SQL查询：使用索引字段查询

### 需要注意
- 确保dwi_rd_efc_pipeline_run_job表数据完整性
- 确保job_status字段值与PipelineStatusEnum匹配
- 确保job_name字段格式符合预期

## 实施步骤

1. 创建实体类 `DwiRdEfcPipelineRunJob`
2. 创建Mapper接口 `DwiRdEfcPipelineRunJobMapper`
3. 创建Mapper XML `DwiRdEfcPipelineRunJobMapper.xml`
4. 修改 `PipelineJobResp` 添加新构造函数
5. 修改 `SdiPipelineJobInfoServiceImpl` 的 `queryDetail` 方法
6. 编译测试
7. 功能测试
8. 代码审查

## 验收标准

1. ✅ 数据从dwi_rd_efc_pipeline_run_job表获取
2. ✅ 保留PipelineStatusEnum.allShowStatus()状态判断
3. ✅ 支持Build、Test、Smoke前缀过滤
4. ✅ 任务类型正确判断
5. ✅ 返回数据格式正确
6. ✅ 编译通过
7. ✅ 功能测试通过
8. ✅ 代码审查通过
