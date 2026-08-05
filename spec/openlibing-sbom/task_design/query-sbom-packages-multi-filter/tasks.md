# 新增 /querySbomPackagesMultiFilter 多选过滤+排序查询接口 — 实现任务

## 进度: 11/11 complete

- [x] 新增 `LicenseFilterEnum` 枚举（model 模块）
- [x] 新增 `PackageSortField` 枚举（model 模块）
- [x] 新增 `QuerySbomPackagesMultiFilterRequest` DTO（多选 + 排序入参）
- [x] 新增批量 DAO 方法 `getPackageInfoByNameForPageBatch` / `getPackagesByGroupPageBatch` / `countPackageGroupsBatch`（多选过滤 + 排序）
- [x] 新增 service 方法 `getPackageInfoByNameForPageMultiFilter` / `getPackageGroupByNameForPageMultiFilter`，含 join 辅助方法
- [x] Controller 新增 `POST /querySbomPackagesMultiFilter` 端点
- [x] 修复分组查询排序被 service 覆盖的问题（`sortField==null` 才按名称重排）
- [x] 修复 `isExactly` Jackson 绑定问题（`@JsonProperty("isExactly")`）
- [x] `dependencyTypes` 改为多选（`List<Integer>` + `string_to_array` 展开）
- [x] 补充 service / controller 单元测试
- [x] model/dao/interface 编译通过

## 关联

- 业务 Issue：Chenmingxu/openlibing-sbom#1
- 业务分支：`feat-query-sbom-packages-multi`