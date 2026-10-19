# notice-scan-status-multifilter

## 需求背景

前端制品列表页已通过 SBOM `/sbom-api/queryProductListMultiFilter`（多选过滤分页查询制品列表）展示制品，现需要同时展示各制品的 NOTICE 扫描状态。SCA 侧已有 `tbl_project_notice_scan` 扫描数据，但缺少一个与 SBOM 制品列表过滤条件对齐的批量状态查询接口。

SBOM 仓（openlibing-sbom，sbom-dev 分支）已提供内部接口 `/internal-api/queryProductNamesByMultiFilter`：入参与 `queryProductListMultiFilter` 请求体同构（忽略排序分页），返回全量制品名清单。本需求在 SCA 侧新增聚合接口把两者串起来。

## 功能描述

在 `ProjectNoticeScanController` 新增接口 `POST /project/notice/scan/scanStatusByMultiFilter`：

1. 入参与 SBOM `/sbom-api/queryProductListMultiFilter` 请求体保持一致（`productType` / `filters` / `sortField` / `sortDir` / `pageNum` / `pageSize`），不保留 `userId` query 参数（已与需求方确认）。
2. 服务端调用 SBOM 内部接口 `/internal-api/queryProductNamesByMultiFilter` 获取全量制品名清单。
3. 按制品名批量查询 `tbl_project_notice_scan`，取每个制品最新一次扫描记录的状态，全量返回前端。

不做的事情：

- 不修改 SBOM 仓任何代码（`/internal-api/queryProductNamesByMultiFilter` 已存在）。
- 不做服务端分页：internal-api 契约即"全量制品名"，本接口同样返回全量状态列表，前端自行与制品列表 join（已确认）。
- 未发起过扫描的制品返回一条 `status=null`、`statusName="未扫描"` 的记录（已确认）。
- 不新增数据库表/字段、不修改既有接口行为、不新增 SCA 侧鉴权逻辑（与同 Controller 既有接口保持一致，由网关统一认证）。

## 验收标准

- [ ] 传入与 `queryProductListMultiFilter` 相同的请求体，返回其中所有制品的扫描状态列表。
- [ ] 每个制品返回 `{productName, status, statusName}`；`status` 取该制品最新一次扫描记录的状态（0-PENDING/1-PROCESSING/2-SUCCESS/3-FAILED），`statusName` 为对应中文描述。
- [ ] 未扫描过的制品返回 `status=null`、`statusName="未扫描"`。
- [ ] `productType` 为空时返回业务失败提示，不发起 SBOM 调用。
- [ ] SBOM 调用失败时返回业务失败提示（`ScaException` 链路），不抛 500 裸异常。
- [ ] 响应不包含 `mergedOssUrl` / `errorMsg` 等 OBS 内部地址与冗余字段。
- [ ] 单测覆盖：正常映射 / 未扫描制品 / 空制品列表 / SBOM 失败 / productType 缺失；构建与既有测试通过。

## 影响范围

- 业务仓：`openlibing-sca`（dm 模块 controller/service/dao + common feign + analysis 模块 dto/vo），约 200 行（含单测）。
- 跨仓只读依赖：`openlibing-sbom` sbom-dev 分支的 `/internal-api/queryProductNamesByMultiFilter`（不改 SBOM 仓）。
- 不涉及 Liquibase 迁移、不涉及部署配置变更。
