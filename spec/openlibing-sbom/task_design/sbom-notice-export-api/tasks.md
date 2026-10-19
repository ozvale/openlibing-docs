# Tasks: sbom-notice-export-api

分支：`feat-sbom-notice-export-api`（基于 prod/master 401b3d44）

## 实现

- [x] model：新增 `PackageDependencyTypeVo`（name/version/downloadKey/dependencyType）
- [x] model：新增 `QueryPackageDependencyTypesRequest`（productName）
- [x] dao：`ProductRepository#getProductNamesMultiFilter`（同条件 DISTINCT name，无分页）
- [x] dao：`PackageRepository#findPackageDependencyTypesByProductName`（5 列轻量查询）
- [x] interface：`SbomService` 新增 `getProductNamesMultiFilter` / `getPackageDependencyTypes`
- [x] impl：`SbomServiceImpl` 实现两方法（复用 parseProductListFilters/buildAttrFiltersJson；downloadKey 解析；0>2>1 优先级归并；NULL→-1）
- [x] controller：新增 `InternalController`（/internal-api：2 新接口 + queryProductConfig/queryProduct/exportSbom 迁移副本，无横向鉴权、无 userId）
- [x] test：`SbomServiceImplTest` 新增用例（filters 透传/非法 key、空制品、downloadKey 回退、优先级取值）

## 验证

- [x] 模块编译通过（mvn compile）
- [x] 新增单测通过（SbomServiceImplTest 相关方法）
- [x] 改动文件 pre-commit 全部通过

## 交付

- [ ] 用户自测确认
- [ ] 测试环境合入验证（待用户指定源仓远程分支）
- [ ] fork 推送 + 关联 issue + PR
- [ ] spec 归档（docs PR）
