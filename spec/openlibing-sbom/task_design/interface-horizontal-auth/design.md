# Design：SBOM 接口横向鉴权整改

> 本文件为《SBOM 接口横向鉴权整改》的工程收敛版设计文档。

## 1. 方案设计

人机接口全量横向鉴权：Controller 入口反查 productType → 复用 `checkPermissionByProductType` 委托 framework 远端鉴权。机机白名单隔离（internal-api / apig-api / sbom-api 机机 3 接口）。职责：AuthService 负责反查+委托；Controller 负责入口校验与 403 响应；Repository 负责反查 SQL。单仓三模块（interface / dao / sbom-web），gateway 与 framework 不改动。

## 2. 实现逻辑设计

- **productName 链**：blank 检查 → `findByName` → `attribute.get("productType")` → 空则 warn+FALSE → 远端鉴权。
- **packageId 链**：blank/非法 UUID 检查（catch IllegalArgumentException）→ native 三表 JOIN 标量查询 → null 则 warn+FALSE → 远端鉴权。
- **fail-closed**：反查失败、远端异常、userId 缺失一律 FALSE → 403。
- **文件流接口**（exportSbomFile/exportSbom/exportPackageSbom/exportAllPackageSbom）：403 用 `response.setStatus(403)` + JSON 字节直写。
- **body 入参接口**（MultiFilter / VulCountSummary）：productName blank 先 400（对齐 InternalController 先例）。
- **refreshDependencyType**：productName 必传化，删除空刷全量分支。

## 3. 类设计

| 类                            | 变更                                                                                                                                                                                                                   |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AuthService`（interface）    | +`checkPermissionByProductName(url, productName, userId)`、+`checkPermissionByPackageId(url, packageId, userId)`                                                                                                       |
| `AuthServiceImpl`（sbom-web） | 构造注入 ProductRepository/PackageRepository；+2 公开方法（委托 checkPermissionByProductType）；+2 私有 resolve（反查失败 warn+null）                                                                                  |
| `PackageRepository`（dao）    | +`findProductTypeByPackageId(UUID)`：`SELECT pr.attribute->>'productType' FROM package pkg JOIN sbom s ON pkg.sbom_id=s.id JOIN product pr ON s.product_id=pr.id WHERE pkg.id=:packageId`（native 标量，避免 LAZY 链） |
| `SbomController`（sbom-web）  | 25 接口：+`@RequestParam(value="userId", defaultValue="")` 入参 + 开头鉴权样板（url=接口自身路由）                                                                                                                     |
| `AuthServiceImplTest`         | +新方法场景用例                                                                                                                                                                                                        |
| `SbomControllerTest`          | 受影响用例补 mock + 代表性 403 用例                                                                                                                                                                                    |

ProductRepository 不改（findByName 已存在）。

## 4. 数据模型设计

不涉及。无表结构/字段/索引变化，仅新增只读 SELECT（走 product.name 索引与 package.id 主键）。

## 5. 性能设计

每请求新增 1 次本地索引点查 + 1 次 framework 内网 Feign 调用，与既有 4 个已鉴权接口同量级。gamma 规模（product 1307 行 / package 171 万行）点查开销可忽略；三表 JOIN 均主键/外键等值 JOIN 无全表扫描；标量查询无 JSONB 物化开销。

## 6. API 接口设计

25 接口统一：新增可选 query 参数 `userId`（网关注入，缺省空）；新增 403 响应 `DataResult.userNotAuthorized("no permission")`。前端零改造。

行为变化：`POST /sbom-api/refreshDependencyType` productName 必传（缺参 400），空刷全量能力移除。

接口清单（鉴权 url 均为 `/openlibing-sbom/sbom-api/<path>`）：

- productName 类：queryScanStatus、querySbomPackagesMultiFilter、querySbomPackagesVulCountSummary、querySbomPackages(GET)、querySbomPackagesByBinary、querySbomPackageList(废弃)、queryLicenseUniversalApi、queryProductStatistics、queryProductVulTrend、queryVulnerability、queryVulImpact、queryProductVulImpact、refresh、dependencyCache/refresh、refreshDependencyType、exportSbomFile(废弃)、exportSbom、exportPackageSbom、exportAllPackageSbom
- packageId 类：querySbomPackageByPackage、queryPackageBinaryManagement、queryPackageVulnerability、queryPackageLicenseAndCopyright、queryPackageStatistics、queryUpstreamAndPatchInfo

## 7. 安全设计

- 鉴权链路：JWT（gateway 覆盖式注入防伪造）→ Controller → AuthService 反查（本地 PG fail-closed）→ framework productType 维度判定。
- 403 固定文案不区分"不存在/无权限"，原因仅入 warn 日志（审计可查）。
- 反查均为参数化查询（native query 命名参数），无注入面。
- 遗留备案：getPackageUrl/query/package/info 全量接口无鉴权维度（后续专项）；excel-export 分支 productType 缺失 500 语义（后续统一）；机机接口依赖 APIG 凭证+网络隔离。
