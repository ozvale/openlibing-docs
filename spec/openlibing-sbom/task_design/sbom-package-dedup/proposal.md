# sbom-package-dedup — 包查询按名称+版本合并去重

## 需求背景
`querySbomPackages` 接口当前返回的包列表中，同一个包名+版本可能因为来自不同源码路径（sourceInfo）而出现多条记录，前端无法区分不同副本对应的溯源路径。需要新增按 (name, version) 合并分组的查询模式，将同一包同一版本的多条记录聚合展示。

## 功能描述
1. `querySbomPackages` 接口新增 `groupByPackage` 请求参数（Java 侧使用 `isGroupByPackage` 遵循 G.NAM.08 布尔命名规范，`@RequestParam(name = "groupByPackage")` 保持 API 兼容）
2. `isGroupByPackage=true` 时，返回按 (name, version) 分组的 `PackageGroupVo` 列表，每组内含源记录列表
3. `PackageWithStatisticsVo` 新增 `sourceInfo` 字段，标记不同副本的来源路径
4. `isGroupByPackage=false` 或不传时，接口行为与变更前完全一致

不做：
- 不修改 `getPackageInfoByNameForPage` 原有方法
- 不修改数据库表结构

## 验收标准
- [ ] `groupByPackage=true` 时返回 `PageVo<PackageGroupVo>`，同 name+version 的记录合并为一组
- [ ] `groupByPackage=false` 或不传时返回 `PageVo<PackageWithStatisticsVo>`，行为不变
- [ ] 分组列表按 name 排序，再按 version 排序，空值排末尾
- [ ] 分页在 SQL 层完成（GROUP BY + OFFSET/FETCH），非内存截取
- [ ] 现有测试全部通过
- [ ] 新增测试覆盖分组逻辑（单组多包、多组、空结果）

## 影响范围
- 后端：`openlibing-sbom` 仓
  - `SbomController`：新增 `isGroupByPackage` 参数（显式映射 `name="groupByPackage"`）+ 分支逻辑
  - `SbomService` / `SbomServiceImpl`：新增 `getPackageGroupByNameForPage` 方法
  - `PackageRepository`：新增 `countPackageGroups` + `getPackagesByGroupPage` SQL 分页方法
  - `QuerySbomPackagesRequest`：新增 `isGroupByPackage` 字段
  - `PackageGroupVo`（新增）：分组 VO
  - `PackageWithStatisticsVo`：新增 `sourceInfo` 字段
