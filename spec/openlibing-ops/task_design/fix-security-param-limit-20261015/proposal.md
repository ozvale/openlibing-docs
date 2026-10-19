# 接口传参大小限制安全加固（#248 / #240 / #209）

## 需求背景

安全漏洞挖掘提出 3 个接口传参无大小限制的缺陷（均指派给 nane），攻击方可通过超大入参放大 JVM 与 MySQL 的 CPU/内存占用，导致接口响应变慢或不可用：

| #   | 问题                                                          | 修复仓            |
| --- | ------------------------------------------------------------- | ----------------- |
| 248 | `/metric/dict` 列表元素数量无上限，可构造超大 IN 查询         | openlibing-metric |
| 240 | 查询接口 pageSize 无上限，大 pageSize 易 OOM                  | openlibing-ops    |
| 209 | `/metric/dict` 传参无大小限制（与 #248 重复），建议集合 ≤ 200 | openlibing-metric |

## 修复方案

| #       | 修复点                                                                                                                                                                | 上限      | 超限行为     |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ------------ |
| 248/209 | `MetricDictQueryReq.codes` 加 `@Size(max = 200)`，Controller 加 `@Valid`；`GlobalExceptionHandler` 补充 `MethodArgumentNotValidException` 处理（返回 400 + 具体原因） | 200       | 返回参数错误 |
| 240     | ops 仓剩余无上限的 7 个请求类 pageSize 加 `@Max(100)`（`DetailReq` 父类一处覆盖约 35 个子类）；`ReportDataQueryReq` 与既有 Schema/钳制对齐限 500                      | 100 / 500 | 返回参数错误 |

ops 仓其余请求类（`RepoQueryReq`、`Precision*ListReq`、`CodeCheckBranchConfigListReq`、`OpsProjectE2eTargetQueryReq`、`ExternalRepoReq`、`ExternalRepoPipelineStatisticsReq` 等）此前已有 `@Max` 上限，本次不重复修改。

## 验收标准

- [x] `POST /manage/digital/metric/dict` 传超过 200 个 codes 返回参数错误
- [x] ops 仓各分页接口 pageSize 超过 100 返回参数错误
- [x] 导出功能不受影响（导出入口不传大 pageSize，后端内部循环分页 setPageSize 不经过入口校验）
- [x] 两仓编译通过、spotless 格式化通过
- [ ] 用户自测确认

## 影响范围与遗留事项

- openlibing-metric：`MetricDictQueryReq`、`DigitalMetricInfoController`、`GlobalExceptionHandler`
- openlibing-ops：`DetailReq`、`OpsOverviewMainReq`、`OpsRepoDetailReq`、`OpsResourceRunReq`、`ExternalRepoIssueDetailReq`、`IssueLegacyStatisticsDto`、`ReportDataQueryReq`
- **前端遗留**：`openlibing-ops-web` 工程能力运营看板 `use-engineering-capability.ts` 以 `pageSize: 999` 调 `/ops-overview/main`，后端限 100 后该查询会返回参数错误，需前端另行改为循环分页拉取（本次按用户要求不动前端）；`metric-store.ts` 两处 `pageSize: 999`（调 metric 仓领域/维度接口）属同类问题，metric 仓分页接口本次未加上限

## 关联 Issue

https://gitcode.com/openlibing/openlibing-ops/issues/248
https://gitcode.com/openlibing/openlibing-ops/issues/240
https://gitcode.com/openlibing/openlibing-ops/issues/209
