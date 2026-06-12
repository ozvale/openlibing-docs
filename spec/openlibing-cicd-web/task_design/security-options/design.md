# Design: 安全编译选项数据工程能力建设

## 技术方案

### 页面结构

```
SecurityOptions/index.vue (主页面)
├── el-tabs > el-tab-pane "安全编译选项"
│   ├── toolbar (代码仓下拉 + 文件下拉 + 时间范围 + 搜索按钮)
│   ├── el-table (概览表格)
│   └── el-pagination
└── FileDetailDialog.vue (文件详情弹窗)
    ├── el-table (文件明细表格)
    └── el-pagination
```

### API 设计

| 接口 | 路径 | 方法 | 用途 |
|------|------|------|------|
| buildArtifactSecOptionOverview | /build-artifact/sec-option/overview | POST | 概览列表数据 |
| buildArtifactSecOptionDropdown | /build-artifact/sec-option/dropdown | POST | 下拉选项数据 |
| metricsCodeFileDetail | /metrics/code/file-detail | POST | 文件详情数据 |

### 数据结构

概览表格行数据结构：
```json
{
  "repoName": "代码仓名称",
  "runNumber": 123,
  "pipelineLink": "跳转链接",
  "packageName": "文件名",
  "detectionCompletedAt": "2026-06-10 12:00:00",
  "overviewData": {
    "bindNow": { "totalFiles": 10, "yesCount": 8, "rate": "80%" },
    "nx": { "totalFiles": 10, "yesCount": 7, "rate": "70%" },
    "pic": { ... },
    "pie": { ... },
    "relro": { ... },
    "noRpath": { ... },
    "sp": { ... },
    "strip": { ... }
  }
}
```

### 筛选参数

| 参数 | 说明 | 来源 |
|------|------|------|
| projectId | 项目ID | app.projectInfo |
| repoName | 代码仓名称 | 代码仓下拉 |
| packageName | 文件名 | 文件下拉 |
| startTime | 开始时间 | 日期时间选择器 |
| endTime | 结束时间 | 日期时间选择器 |
| sortByField | 排序字段 | 表格排序（去掉 overviewData. 前缀） |
| sort | 排序方向 | asc/desc |

### 影响范围

- 新增文件：SecurityOptions/index.vue、FileDetailDialog.vue、api.ts、url.ts
- 修改文件：router/index.ts（新增路由）、TableHeaderFilter.vue（新增 placement/popperClass props）
