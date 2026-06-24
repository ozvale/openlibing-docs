## Why

`openlibing-web` 防投毒详情页（`PoisoningDetail.vue`）已为「任务状态」（`isSuccess`）和「是否通过」（`isPass`）列接入表头筛选，请求体透传 `0`/`1` 至列表接口。但 `openlibing-anti-poison` 的 `ParamModel` 未声明对应字段，`getScanResult` 与 `get-scan-pr-result-group` 的 Mongo 查询也未按这两列过滤，导致前端筛选无效。需补齐后端筛选逻辑并与前端契约对齐。

## What Changes

- 在 `ParamModel` 新增可选筛选字段 `isSuccess`、`isPass`（整型 `0`/`1`，与前端一致）
- 在 `ScanResultDetailOperation.getScanResult` 的 `$match`/Criteria 中按 `is_success`、`is_pass` 过滤（版本级列表）
- 在 `ScanResultDetailOperation.getScanPRResultGroup` 聚合管道的初始 `$match` 中按 `is_success`、`is_pass` 过滤（门禁级 PR 分组列表）
- 统一 API 契约文档：`0` = false，`1` = true；未传参时不施加筛选
- 补充单元测试覆盖筛选条件构建与计数逻辑
- 前端 `openlibing-web` 无需改请求字段名（已对齐）；可选补充 TypeScript 请求类型注释

## Capabilities

### New Capabilities

- `scan-result-filter`: 防投毒扫描结果列表（版本级 `getScanResult` 与门禁级 `get-scan-pr-result-group`）对任务状态、是否通过的后端筛选能力及前后端 API 契约

### Modified Capabilities

（无既有 openspec 基线 spec，本次为新增能力）

## Impact

- **后端**：`ParamModel`、`ScanResultDetailOperation`、相关 Service 层计数逻辑、单元测试
- **前端**：`PoisoningDetail.vue` 已发送 `isSuccess`/`isPass`（`0`/`1`），联调验证即可；接口路径不变
- **API**：`POST /shield/getScanResult`、`POST /shield/get-scan-pr-result-group`（经 ci-portal 转发）
- **数据**：MongoDB 字段 `is_success`、`is_pass`（Boolean），与入参整型映射
