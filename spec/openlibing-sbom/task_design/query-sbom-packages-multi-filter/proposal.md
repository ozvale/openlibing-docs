# 新增 /querySbomPackagesMultiFilter 多选过滤+排序查询接口 — query-sbom-packages-multi-filter

## 业务 Issue

- Chenmingxu/openlibing-sbom#1 — 【需求】新增 /querySbomPackagesMultiFilter 多选过滤+排序查询接口
- https://gitcode.com/Chenmingxu/openlibing-sbom/issues/1

## 需求背景

现有软件包列表查询接口存在以下痛点：

- `POST /sbom-api/querySbomPackageList`（已废弃，`@RequestParam`）与 `POST /sbom-api/querySbomPackages`（`@RequestBody`）中，`licenseId`、`vulSeverity` 都只支持**单值**，无法同时按多个 license 或多个漏洞等级过滤。
- `multiLicense` / `noLicense` / `legalLicense` / `ilegalLicense` 是四个独立布尔参数，前端需要组合筛选时参数既多又易错。
- 缺少按各漏洞等级数量（critical/high/medium/low/none/unknown）排序的能力，前端无法按风险优先级排序展示。

因此需要新增一个**多选过滤 + 排序**的查询接口，出参与现有接口保持一致，旧接口保持不变。

## 功能描述

新增 `POST /sbom-api/querySbomPackagesMultiFilter`（`@RequestBody`），在现有 `querySbomPackages` 基础上扩展多选与排序能力：

| 入参 | 类型 | 说明 |
|------|------|------|
| `productName` | String | 必填 |
| `packageName` | String | 可选 |
| `isExactly` | Boolean | 精确/模糊匹配 |
| `vulSeverities` | List&lt;String&gt; | 漏洞等级多选，组内 OR |
| `licenseIds` | List&lt;String&gt; | license id 多选，组内 OR |
| `licenseFilters` | List&lt;LicenseFilterEnum&gt; | 合并后的 license 过滤多选，组内 OR |
| `dependencyTypes` | List&lt;Integer&gt; | 依赖类型多选，组内 OR |
| `groupByPackage` | Boolean | 是否按包分组 |
| `sortField` | PackageSortField | 排序字段（漏洞等级数量），null 按默认名称排序 |
| `sortDir` | String | asc/desc，默认 asc |
| `page` / `size` | Integer | 分页 |

### 新增枚举

- `LicenseFilterEnum`：合并 `multiLicense`/`noLicense`/`legalLicense`/`ilegalLicense` 四个布尔维度为单一枚举（NO_LICENSE / SINGLE_LICENSE / MULTI_LICENSE / LEGAL / ILLEGAL），code 1-5，多选时组内 OR。
- `PackageSortField`：排序字段白名单枚举（CRITICAL / HIGH / MEDIUM / LOW / NONE / UNKNOWN_VUL_COUNT），避免用户输入直接拼接进 SQL。

### 出参

不变：`PageVo<PackageGroupVo>`（`groupByPackage=true`）或 `PageVo<PackageWithStatisticsVo>`（`groupByPackage=false`）。

## 不做

- 不修改既有 `querySbomPackageList` / `querySbomPackages` 接口行为
- 不新增数据表 / 不修改表结构
- 不修改前端现有调用（新接口由前端后续切换）

## 验收标准

- [x] 新增 `POST /sbom-api/querySbomPackagesMultiFilter` 接口，`@RequestBody` 入参
- [x] `licenseIds` / `vulSeverities` / `licenseFilters` / `dependencyTypes` 多选过滤生效（组内 OR、组间 AND）
- [x] `sortField` + `sortDir` 排序生效（分组与非分组两种模式）
- [x] 出参结构不变
- [x] 旧接口行为不受影响
- [x] 补充相关单元测试

## 影响范围

| 文件 | 操作 | 说明 |
|------|------|------|
| `model/.../enums/LicenseFilterEnum.java` | 新增 | 合并 license 过滤枚举 |
| `model/.../enums/PackageSortField.java` | 新增 | 排序字段白名单枚举 |
| `model/.../request/sbom/QuerySbomPackagesMultiFilterRequest.java` | 新增 | 多选请求 DTO |
| `dao/PackageRepository.java` | 修改 | 新增批量 DAO 方法 |
| `api/sbom/SbomService.java` | 修改 | 新增 MultiFilter 服务方法 |
| `service/sbom/impl/SbomServiceImpl.java` | 修改 | 实现多选过滤 + 排序 |
| `controller/SbomController.java` | 修改 | 新增 MultiFilter 端点 |
| `test/.../SbomServiceImplTest.java` | 修改 | 补充多选/排序用例 |
| `test/.../SbomControllerTest.java` | 修改 | 补充新接口用例 |

- 业务仓：`openlibing-sbom`
- 不涉及数据模型变更
- 所属分支：`feat-query-sbom-packages-multi`

## 流程模式

Standard 模式：proposal + design + tasks + 相关单元测试。