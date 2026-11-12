# UT 覆盖率原始报告下载 — 前端接口说明

| 项          | 内容                                                          |
| ----------- | ------------------------------------------------------------- |
| FE 需求名称 | 【openLiBing】UT原始报告下载能力建设                          |
| 关联 Issue  | https://gitcode.com/openlibing/openlibing-coderepo/issues/276 |
| 后端分支    | feat-ut-original-report-download（openlibing-coderepo）       |
| 发布对象    | openlibing-web 前端同学                                       |
| 更新日期    | 2026-11-09                                                    |

## 1. 提交原始报告导出任务（新增）

```http
POST /gateway/openlibing-coderepo/ut/coverage/original-report/export
Content-Type: application/json
```

**说明**：提交即返回，幂等。进度呈现与自动下载由框架全局「导出任务」浮层托管，前端拿到记录 ID 后直轮接口 2（勿在业务页面自建轮询 UI）。同一记录进行中/已成功的任务直接复用返回原 ID，仅最近一条失败时才重建新任务。

**请求体**（userId 由网关注入，前端不传）：

| 字段          | 类型   | 必填 | 说明                                           |
| ------------- | ------ | ---- | ---------------------------------------------- |
| repoId        | number | 是   | 仓库 ID                                        |
| branchName    | string | 是   | 分支名称                                       |
| pipelineRunId | string | 否   | 传则精确定位该次记录；不传取该分支最新成功记录 |

```json
{ "repoId": 100, "branchName": "master", "pipelineRunId": "run-123" }
```

**响应**：

```json
// 成功：data 为导出中心记录 ID（字符串），据此直轮接口 2
{ "code": "0", "msg": "success", "data": "445805" }

// 业务失败（历史记录无原始报告等），前端直接展示 msg
{ "code": "500", "msg": "该记录为功能上线前的历史上报，无原始报告可下载" }
```

**注意**：`code` 为字符串 `"0"` 表示成功；非 0 由统一拦截器提示，业务页无需额外错误处理。

## 2. 文件级明细接口字段补充（已有接口，响应新增 1 字段）

```http
POST /gateway/openlibing-coderepo/ut/coverage/file-detail
```

响应 `data` 新增字段：

| 字段                    | 类型    | 说明                                                                                   |
| ----------------------- | ------- | -------------------------------------------------------------------------------------- |
| originalReportAvailable | boolean | 原始报告是否可下载。`false`=功能上线前的历史记录，前端据此置灰"下载原始报告"按钮并提示 |

**交互约定**：

- `originalReportAvailable === false` → 按钮置灰 + tooltip「功能上线前的历史记录无原始报告」
- 字段缺失（老后端）按可下载处理，保持向后兼容

## 3. 轮询下载状态（平台既有能力，前端直轮 framework，coderepo 不新建接口）

```http
GET /gateway/openlibing-framework/export/detail?id={exportRecordId}
```

平台全局「导出任务」浮层已集成该轮询：`message` 承载状态（`导出任务已创建 / 导出文件生成中 / 正在上传文件 / 导出成功 / 导出失败：xxx`）；`message=导出成功` 时返回签名下载 URL，浮层自动触发下载并支持「重新下载」。**业务页面零轮询代码。**

## 4. 前端参考实现（已在 feat-ut-original-report-download 分支落地）

- `src/api/Repos/url.ts`：`UT_ORIGINAL_REPORT_EXPORT`
- `src/api/Repos/api.ts`：`submitUtOriginalReportExport`
- `src/views/Repos/dialog/UtCoverageDetailDialog.vue`：按钮 + `useExportTaskSubmit` hook 接入（可直接复用该提交模式）
