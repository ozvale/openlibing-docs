# 新增 /querySbomPackagesMultiFilter 多选过滤查询接口 — query-sbom-packages-multi-filter

## 业务 Issue

- Chenmingxu/openlibing-sbom#1 — 【需求】新增 /querySbomPackagesMultiFilter 多选过滤查询接口
- https://gitcode.com/Chenmingxu/openlibing-sbom/issues/1

## 需求背景

现有 `POST /sbom-api/querySbomPackageList`（已废弃，`@RequestParam`）与 `POST /sbom-api/querySbomPackages`（`@RequestBody`）中，`licenseId`、`vulSeverity` 都只支持**单值**，无法同时按多个 license 或多个漏洞等级过滤。`multiLicense` / `noLicense` / `legalLicense` / `ilegalLicense` 是四个独立布尔参数，组合筛选时参数既多又易错。漏洞类型参数也需要同时支持"包含"与"排除"两种语义。

因此需要新增一个**多选过滤**查询接口，出参与现有接口保持一致，旧接口保持不变。

## 功能描述

新增 `POST /sbom-api/querySbomPackagesMultiFilter`（`@RequestBody`），在现有 `querySbomPackages` 基础上扩展多选能力：

| 入参                   | 类型                           | 说明                                                                           |
| ---------------------- | ------------------------------ | ------------------------------------------------------------------------------ |
| `productName`          | String                         | 必填                                                                           |
| `packageName`          | String                         | 可选                                                                           |
| `isExactly`            | Boolean                        | 精确/模糊匹配                                                                  |
| `includeVulSeverities` | List&lt;String&gt;             | 包含的漏洞级别多选，命中任一选中级别的包被筛选出（组内 OR）                    |
| `excludeVulSeverities` | List&lt;String&gt;             | 排除的漏洞级别多选，命中任一选中级别的包被排除（组内 OR）                      |
| `licenseCount`         | List&lt;LicenseCountFilter&gt; | license 数量过滤（多选，组内 OR）：NO_LICENSE / SINGLE_LICENSE / MULTI_LICENSE |
| `licenseCompliance`    | LicenseComplianceFilter        | license 成分过滤（单选）：LEGAL / ILLEGAL                                      |
| `licenseIds`           | List&lt;String&gt;             | license id 多选，组内 OR                                                       |
| `dependencyTypes`      | List&lt;Integer&gt;            | 依赖类型多选，组内 OR（0=直接，1=间接）                                        |
| `groupByPackage`       | Boolean                        | 是否按包分组                                                                   |
| `page` / `size`        | Integer                        | 分页                                                                           |

### 新增枚举

- `LicenseCountFilter`：license 数量过滤（多选），拆分自原 `licenseFilters`：NO_LICENSE（count=0）/ SINGLE_LICENSE（count=1）/ MULTI_LICENSE（count>1）。
- `LicenseComplianceFilter`：license 成分过滤（单选），拆分自原 `licenseFilters`：LEGAL（is_legal_license=TRUE）/ ILLEGAL（is_legal_license=FALSE）。

### 出参

不变：`PageVo<PackageGroupVo>`（`groupByPackage=true`）或 `PageVo<PackageWithStatisticsVo>`（`groupByPackage=false`）。

## 不做

- 不修改既有 `querySbomPackageList` / `querySbomPackages` 接口行为
- 不新增数据表 / 不修改表结构
- 不修改前端现有调用（新接口由前端后续切换）
- 不按漏洞等级数量排序（原设计中的排序能力已移除，接口仅做多选过滤）

## 验收标准

- [ ] 新增 `POST /sbom-api/querySbomPackagesMultiFilter` 接口，`@RequestBody` 入参
- [ ] `includeVulSeverities` / `excludeVulSeverities`：包含组命中任一级别即筛选出，排除组命中任一级别即排除（均基于各级别漏洞数量字段判断）
- [ ] `licenseIds` / `dependencyTypes` / `licenseCount` 多选过滤生效；`licenseCompliance` 单选过滤生效（组间 AND）
- [ ] 出参结构不变
- [ ] 旧接口行为不受影响
- [ ] 补充相关单元测试

## 影响范围

| 文件                                                              | 操作 | 说明                      |
| ----------------------------------------------------------------- | ---- | ------------------------- |
| `model/.../enums/LicenseCountFilter.java`                         | 新增 | license 数量过滤枚举      |
| `model/.../enums/LicenseComplianceFilter.java`                    | 新增 | license 成分过滤枚举      |
| `model/.../request/sbom/QuerySbomPackagesMultiFilterRequest.java` | 新增 | 多选请求 DTO              |
| `dao/PackageRepository.java`                                      | 修改 | 新增批量 DAO 方法         |
| `api/sbom/SbomService.java`                                       | 修改 | 新增 MultiFilter 服务方法 |
| `service/sbom/impl/SbomServiceImpl.java`                          | 修改 | 实现多选过滤              |
| `controller/SbomController.java`                                  | 修改 | 新增 MultiFilter 端点     |
| `test/.../SbomServiceImplTest.java`                               | 修改 | 补充多选用例              |
| `test/.../SbomControllerTest.java`                                | 修改 | 补充新接口用例            |

- 业务仓：`openlibing-sbom`
- 不涉及数据模型变更
- 所属分支：`feat-query-sbom-packages-multi`

## 流程模式

Standard 模式：proposal + design + tasks + 相关单元测试
