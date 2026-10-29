# 需求背景

## 需求描述

修复代码检查告警页面（StaticAlarm）在删除最后一页数据后，列表仍停留在当前页码（已无数据）的问题：批量清理成功后调用 `refresh(false)` 保留当前页码刷新，但删除后总页数变小，原页码已超出 `totalPages`，导致请求到一个不存在的空页，页面显示为空。预期行为是自动跳转到最后一个有数据的页面。

## 关联 Issue

- [openlibing/openlibing-web#358](https://gitcode.com/openlibing/openlibing-web/issues/358)（[缺陷]:代码检查页面删除最后一页的数据后，页面仍停留在当前数据为空的页）

## 验收标准

1. 在最后一页批量清理该页全部告警后，列表自动回退到最后一个有数据的页并正常渲染
2. 清理后数据全部为空时，回退到第 1 页展示空状态，不出现页码越界
3. 页码回退后浏览器地址栏 `pageNo` 查询参数同步更新（刷新页面后不回落到空页）
4. 非末页删除、翻页、改每页条数等常规分页场景回归不受影响

## 变更范围

- `apps/web-openlibing/src/views/StaticAlarm/index.vue`（+12，`fetchList` 数据层页码回退判断）
- `apps/web-openlibing/src/views/StaticAlarm/utils/staticAlarmPagination.ts`（新增，`shouldFallbackPageOnEmptyList` 空列表页码回退判断）
- `apps/web-openlibing/src/views/StaticAlarm/utils/__tests__/staticAlarmPagination.spec.ts`（新增，5 个场景单元测试）

## 优先级

中（交互缺陷：删除后出现无提示的空页）

## 关联 PR

- 业务 PR：[openlibing/openlibing-web#829](https://gitcode.com/openlibing/openlibing-web/merge_requests/829)（分支 `fix-alarm-delete-last-page`，已合入 `release_20261019`）
- spec 归档 PR：[openlibing/openlibing-docs#1154](https://gitcode.com/openlibing/openlibing-docs/merge_requests/1154)
