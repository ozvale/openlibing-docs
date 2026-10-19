# Design: sbom-notice-export-api

> 详细设计（七方面完整版）：`D:\work\design\202610\sbom-notice-export-api.md`；本文为归档摘要 + 实现决策记录。

## 方案概述

openlibing-sbom 新增 `InternalController`（`/internal-api`，feign 机机接口，参照 `ApigController` 先例），承载 2 个新查询接口 + 3 个既有接口并行副本。纯新增，无 schema 变更，旧接口零改动。

## 接口清单

| #   | 接口                                                           | 类型 | 说明                                                                                         |
| --- | -------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------- |
| 1   | POST `/internal-api/queryProductNamesByMultiFilter`            | 新增 | body `QueryProductListMultiFilterRequest`（忽略排序/分页），返回 `List<String>` 全量制品名   |
| 2   | POST `/internal-api/queryPackageDependencyTypes`               | 新增 | body `QueryPackageDependencyTypesRequest{productName}`，返回 `List<PackageDependencyTypeVo>` |
| 3   | GET `/internal-api/queryProductConfig?productType=`            | 副本 | 同 `/sbom-api/queryProductConfig`，去横向鉴权与 userId                                       |
| 4   | POST `/internal-api/queryProduct?productType=` + body          | 副本 | 同 `/sbom-api/queryProduct`，去横向鉴权与 userId                                             |
| 5   | `/internal-api/exportSbom?productName&spec&specVersion&format` | 副本 | 同 `/sbom-api/exportSbom`，tar.gz 流响应，失败 text/plain                                    |

## 核心实现决策

1. **接口 1 SQL**：`ProductRepository#getProductNamesMultiFilter` —— WHERE 条件块与 `getProductListMultiFilterPage` 完全一致（product LEFT JOIN product_statistics/raw_sbom 的 DISTINCT ON 最新子查询），`SELECT DISTINCT p.name COLLATE "C"`（DISTINCT + COLLATE 排序需将 COLLATE 收敛进 SELECT 列，ORDER BY 以输出列位置引用），无分页。服务层复用 `parseProductListFilters` + `buildAttrFiltersJson`。
2. **接口 2 SQL**：`PackageRepository#findPackageDependencyTypesByProductName` —— `SELECT p.name, p.version, p.download_location, ps.purl, ps.dependency_type FROM package p LEFT JOIN package_statistics ps`，sbom_id 经 productName 子查询，按 name/version 升序。
3. **接口 2 出参（v3 口径）**：**原始数据透传**——name / version / downloadLocation（download_location 原值，NOASSERTION/NONE 不处理）/ purl / dependencyType（未刷新为 null）逐列对应；**不去重、不做 0>2>1 优先级归并**，同名同版本多行原样返回，取舍逻辑由调用方（sca）处理。
4. **历史决策（已被 v3 取代）**：曾设计 downloadKey 回退（NOASSERTION/NONE→purl）与 (name,version,downloadKey) 分组优先级取值，因 sca 有特殊处理逻辑、sbom 侧改为只供原始数据而移除。
5. **迁移副本差异**（与 `ApigController` 模式一致）：路径前缀 `/sbom-api` → `/internal-api`、移除横向鉴权段、移除 `userId` 入参；`@LogApi` 审计注解保留。
6. **边界**：接口 2 制品不存在/无 sbom/无软件包 → 200 + `[]`（宽松语义）；productType/productName 空 → 400。

## 类与文件

| 文件                                                             | 动作                                                                         |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `model/.../vo/sbom/PackageDependencyTypeVo.java`                 | 新增：name/version/downloadKey/dependencyType                                |
| `model/.../request/sbom/QueryPackageDependencyTypesRequest.java` | 新增：productName                                                            |
| `dao/ProductRepository.java`                                     | 新增 `getProductNamesMultiFilter(...)`                                       |
| `dao/PackageRepository.java`                                     | 新增 `findPackageDependencyTypesByProductName(...)`                          |
| `interface/.../SbomService.java`                                 | 新增 2 方法声明                                                              |
| `sbom-web/.../SbomServiceImpl.java`                              | 实现 2 方法 + `resolveDownloadKey` / `pickDependencyTypeByPriority` 私有方法 |
| `sbom-web/.../controller/InternalController.java`                | 新增：5 端点                                                                 |
| `sbom-web/.../SbomServiceImplTest.java`                          | 新增用例                                                                     |

## 数据模型

不涉及（只读查询；`package.download_location`、`package_statistics.purl`/`dependency_type` 均为既有字段）。

## 性能

- 接口 1：单 productType 制品数百级，全量 `List<String>` KB 级；SQL 与页面查询同构；
- 接口 2：单制品软件包典型数百（样例 833），4 字段轻量 VO，万行 ~1MB 内；`LinkedHashMap` 单次遍历归并 O(n)。

## 安全

- feign 内网机机接口信任模型（同 `/apig-api`），不经网关、无横向鉴权；原接口鉴权不受影响；
- 全部命名参数，动态列 key 服务层 product_config 白名单校验，无注入面；
- `@LogApi` 审计保留。

## 跨仓影响

openlibing-sca：Feign client 定义（服务注册名 + `/internal-api`）、全量导出编排、页面按钮——sca 团队负责，联调契约见 `D:\work\design\202610\sbom-internal-api-contract.md`。
