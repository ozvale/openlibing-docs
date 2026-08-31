# 新增 /querySbomPackagesMultiFilter 多选过滤查询接口 — 实现任务

## 进度: 11/11 complete

- [x] 新增 `LicenseCountFilter` / `LicenseComplianceFilter` 枚举（model 模块）
- [x] 新增 `QuerySbomPackagesMultiFilterRequest` DTO（多选入参）
- [x] 新增批量 DAO 方法 `getPackageInfoByNameForPageBatch` / `getPackagesByGroupPageBatch` / `countPackageGroupsBatch`（多选过滤）
- [x] 新增 service 方法 `getPackageInfoByNameForPageMultiFilter` / `getPackageGroupByNameForPageMultiFilter`，含 join 辅助方法
- [x] Controller 新增 `POST /querySbomPackagesMultiFilter` 端点
- [x] 修复 `isExactly` Jackson 绑定问题（`@JsonProperty("isExactly")`）
- [x] `dependencyTypes` 改为多选（`List<Integer>` + `string_to_array` 展开）
- [x] 原 licenseFilters 拆分为 `licenseCount`（数量多选）+ `licenseCompliance`（成分单选）两个下拉框
- [x] 移除按漏洞等级数量排序逻辑（原 `sortField`/`sortDir` 已删除）
- [x] 原 `vulSeverities` 拆分为 `includeVulSeverities`（包含）+ `excludeVulSeverities`（排除）两组多选，基于各级别漏洞数量字段判断
- [x] 补充 service / controller 单元测试

## 关联

- 业务 Issue：Chenmingxu/openlibing-sbom#1
- 业务分支：`feat-query-sbom-packages-multi`
