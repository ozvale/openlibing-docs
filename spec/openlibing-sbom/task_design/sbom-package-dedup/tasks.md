# sbom-package-dedup — 实现任务

## 进度: 13/13 complete

- [x] Task 1: 新增 `PackageGroupVo` 模型类（name + version + List\<PackageWithStatisticsVo\>）
- [x] Task 2: `PackageWithStatisticsVo` 新增 `sourceInfo` 字段，`SbomServiceImpl.packageWithStatisticsVoFromPackage` 映射该字段
- [x] Task 3: `QuerySbomPackagesRequest` 新增 `isGroupByPackage` 字段（G.NAM.08 布尔命名规范，setter 保持原名以保证 Lombok 兼容）
- [x] Task 4: `SbomService` 接口新增 `getPackageGroupByNameForPage` 方法签名
- [x] Task 5: `SbomController` 新增 `@RequestParam(name = "groupByPackage") Boolean isGroupByPackage` 参数 + 分支逻辑
- [x] Task 6: `SbomServiceImpl.getPackageGroupByNameForPage` 初版实现（全量 unpaged 查询 → 内存分组 → 排序 → 分页截取）
- [x] Task 7: 新增 `SbomControllerTest.testQuerySbomPackagesGrouped`
- [x] Task 8: 新增 `SbomServiceImplTest.testGetPackageGroupByNameForPage`
- [x] Task 9: `PackageRepository` 新增 `countPackageGroups`（`SELECT COUNT(*)` 统计去重组数）
- [x] Task 10: `PackageRepository` 新增 `getPackagesByGroupPage`（嵌套子查询 GROUP BY + OFFSET/FETCH）
- [x] Task 11: `SbomServiceImpl.getPackageGroupByNameForPage` 重构为 SQL 分页（SQL count + SQL 分页获取当前页组包详情 + 小批量内存分组），移除全量拉取
- [x] Task 12: setter 参数名对齐 `isGroupByPackage` + 补 `@param isGroupByPackage` Javadoc
- [x] Task 13: SQL 优化（CTE + DISTINCT ON → 嵌套子查询 GROUP BY，过滤条件集中到子查询内）
