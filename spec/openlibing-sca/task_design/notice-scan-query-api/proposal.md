# notice-scan-query-api

## 需求背景

项目 NOTICE 扫描（ProjectNoticeScan）目前只提供启动扫描、导出、人工补充、下载地址查询等接口，缺少面向前端展示的扫描记录与扫描明细查询能力。需要按产品名称查询扫描总表记录，并按扫描 ID 查询明细列表，且不能把 OBS 内部地址（总表 `merged_oss_url`、明细表 `readme_oss_url`）暴露给调用方。

## 功能描述

在 `ProjectNoticeScanController` 新增一个接口：

**扫描记录与明细查询**：入参 `productName`，定位 `tbl_project_notice_scan` 最新一次扫描记录，返回除 `merged_oss_url` 外的全部字段，并在同一响应中携带该扫描的明细列表——`tbl_project_notice_scan_detail` 每条记录返回除 `readme_oss_url` 外的全部字段（无明细时为空列表）。

不做的事情：

- 不返回 `merged_oss_url` / `readme_oss_url` 两个 OBS 内部地址字段。
- 不新增数据库表、不修改 Liquibase 变更集。
- 不修改既有接口行为。

## 验收标准

- [ ] 按 `productName` 可查到最新一次扫描记录，响应中不含 `mergedOssUrl` 字段值。
- [ ] 响应同时携带明细列表，每条不含 `readmeOssUrl` 字段值。
- [ ] `productName` 对应记录不存在时返回业务失败（复用 `ScaException` 处理链路）。
- [ ] 扫描记录存在但无明细时，明细列表为空列表。
- [ ] 相关单测通过，构建通过。

## 影响范围

- 业务仓：`openlibing-sca`（dm 模块 + analysis 模块 vo 包），约 200 行以内（含单测）。
- 不涉及数据库迁移、不涉及其他仓。
