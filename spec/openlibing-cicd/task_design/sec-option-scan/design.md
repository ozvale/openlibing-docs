# sec-option-scan 技术方案

## 架构概览

```
test-devops (sec-option-scan 插件)
  │
  │  POST /metrics/sec-option/report
  ▼
openlibing-cicd
  ├── SecOptionScanController
  ├── SecOptionScanService / SecOptionScanServiceImpl
  ├── SecOptionScanRecordMapper
  ├── SecOptionScanFileDetailMapper
  └── MySQL (sec_option_scan_record + sec_option_scan_file_detail)
```

## 数据库设计

### sec_option_scan_record（概览表）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | BIGINT UNSIGNED | 雪花算法主键 |
| git_url | VARCHAR(512) | 仓库URL |
| branch_name | VARCHAR(255) | 分支名称 |
| pipeline_run_id | VARCHAR(128) | 流水线执行ID |
| run_number | VARCHAR(64) | 流水线运行编号 |
| package_name | VARCHAR(512) | 构建产物压缩包文件名 |
| overview_data | JSON | 概览数据（含各选项开启率、有效文件数等） |
| detection_started_at | DATETIME | 检测开始时间 |
| detection_completed_at | DATETIME | 检测完成时间 |
| status | INT | 检测状态(0成功/1失败/2部分成功) |
| error_message | TEXT | 错误信息 |
| create_time | DATETIME | 记录创建时间 |

overview_data JSON 结构：
```json
{
  "totalFiles": 100,
  "options": {
    "bindNow": {"rate": 85.0, "validFiles": 80, "yesCount": 68, "noCount": 12, "naCount": 20},
    "nx": {"rate": 95.0, "validFiles": 90, "yesCount": 85, "noCount": 5, "naCount": 10}
  },
  "averageRate": 75.63
}
```

### sec_option_scan_file_detail（文件明细表）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | BIGINT UNSIGNED | 雪花算法主键 |
| record_id | BIGINT UNSIGNED | 关联概览表ID |
| git_url | VARCHAR(512) | 仓库URL |
| branch_name | VARCHAR(255) | 分支名称 |
| package_name | VARCHAR(512) | 构建产物压缩包文件名 |
| file_path | VARCHAR(512) | 文件路径 |
| file_name | VARCHAR(255) | 文件名 |
| options | JSON | 各选项检测结果 |
| sha1 | VARCHAR(64) | 文件SHA1 |
| created_at | DATETIME | 创建时间 |

options JSON 结构：
```json
{"bindNow": "YES", "nx": "NO", "pic": "N/A", "pie": "YES", "relro": "YES", "rpath": "NO", "sp": "YES", "strip": "NO"}
```

## API 设计

### 上报接口

POST /metrics/sec-option/report

请求体：SecOptionScanReportDTO
- gitUrl (必填)
- branchName (必填)
- pipelineRunId
- runNumber
- packageName
- overviewData (必填, Map<String, Object>)
- detectionStartedAt (ISO 8601)
- detectionCompletedAt (ISO 8601)
- status
- errorMessage
- fileDetails: [{filePath, fileName, options: Map<String, String>, sha1}]

### 概览查询接口

GET /metrics/sec-option/overview?gitUrl=xxx&branchName=xxx&pipelineRunId=xxx

返回：List<SecOptionOverviewVO>
- id, gitUrl, branchName, pipelineRunId, runNumber, pipelineLink, packageName
- overviewData (Map<String, Object>)
- detectionCompletedAt

### 文件详情查询接口

GET /metrics/sec-option/file-detail?gitUrl=xxx&pipelineRunId=xxx&packageName=xxx

返回：SecOptionFileDetailVO
- gitUrl, branchName, pipelineRunId, runNumber, pipelineLink, packageName
- fileDetails: [{filePath, fileName, options: Map<String, String>}]

## 关键设计决策

1. **JSON 列存储**：概览表和详情表均使用 JSON 列存储指标数据，避免为每个选项创建独立列，便于后期扩展新的安全编译选项。

2. **有效文件数**：不同安全编译选项的 N/A 条件不同（如 PIC 只检查共享库，PIE 只检查可执行文件），因此每个选项的有效文件数不同。overviewData 中每个选项包含 validFiles/yesCount/noCount/naCount。

3. **流水线链接**：从 gitUrl 提取 owner/repo，拼接为 `https://gitcode.com/{owner}/{repo}/actions/runs/{pipelineRunId}`。

4. **单条明细入库失败不影响整体**：文件明细逐条入库，单条失败记录 warn 日志继续处理。

## 影响范围

- openlibing-cicd：新增 Controller/Service/Entity/DTO/VO/Mapper/Liquibase
- test-devops：新增 sec-option-scan 插件
