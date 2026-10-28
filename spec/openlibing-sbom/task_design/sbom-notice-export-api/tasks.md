# Tasks: sbom-notice-export-api

分支：`feat-sbom-notice-export-api`（基于 prod/master 401b3d44，已合入 release_20261013）

## 实现

- [x] model：新增 `PackageDependencyTypeVo`（name/version/downloadLocation/purl/dependencyType，v3 原始透传口径）
- [x] model：新增 `QueryPackageDependencyTypesRequest`（productName）
- [x] dao：`ProductRepository#getProductNamesMultiFilter`（同条件 DISTINCT name COLLATE "C"，无分页）
- [x] dao：`PackageRepository#findPackageDependencyTypesByProductName`（5 列轻量查询）
- [x] interface：`SbomService` 新增 `getProductNamesMultiFilter` / `getPackageDependencyTypes`
- [x] impl：`SbomServiceImpl` 实现两方法（接口 1 复用 parseProductListFilters/buildAttrFiltersJson；接口 2 逐行透传构造，经 Number 转换适配 PG bigint 投影；**无 downloadKey 解析、无优先级归并、无 NULL→-1 归一化**——v3 口径已移除，取舍由 sca 处理）
- [x] controller：新增 `InternalController`（/internal-api：2 新接口 + queryProductConfig/queryProduct/exportSbom 迁移副本，无横向鉴权、无 userId）
- [x] test：`SbomServiceImplTest` 新增 7 个用例（getProductNamesMultiFilter 3 个：filters 透传/非法 key/空 productType；getPackageDependencyTypes 4 个：空制品/空 productName/原始数据透传/不去重）

## 验证

- [x] 模块编译通过（mvn compile）
- [x] 单测通过（SbomServiceImplTest 89 用例全绿 = 既有 82 + 新增 7）
- [x] 改动文件 pre-commit 全部通过

## 交付

- [x] 用户自测确认（gamma 多轮验证，含 DISTINCT+COLLATE 排序修复、PG bigint 投影 Long 转换修复、v3 口径调整）
- [x] 测试环境合入验证（已合入源仓 sbom-dev@140dfafd 并部署 gamma 实测通过）
- [x] fork 推送 + 关联 issue #113 + PR（业务 PR openlibing/openlibing-sbom!157，base：release_20261019_iter1）
- [x] spec 归档（docs PR openlibing/openlibing-docs!1141）
