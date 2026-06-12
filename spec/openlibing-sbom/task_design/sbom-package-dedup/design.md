# sbom-package-dedup — 技术设计

## 方案概述
在 SQL 层通过嵌套子查询 + GROUP BY + OFFSET/FETCH 完成分页分组，应用层仅做小批量数据的内存聚合和 VO 转换。

## 架构决策

1. **SQL 层分页而非应用层内存聚合**：最初设计为全量拉包后内存分组，经 review 后改为数据库层分页。
   - `countPackageGroups`：`SELECT COUNT(*)` 统计去重组数
   - `getPackagesByGroupPage`：子查询按 (name, version) GROUP BY → OFFSET/FETCH → 外层 JOIN 拉回当前页组内的包详情
   - 优势：避免全量数据内存加载，totalElements/totalPages 由 SQL 精确计算
2. **分组 key 使用 (name, version)**：name 为包名，version 为版本号。两个维度拼接为 `"name|||version"` 作为 LinkedHashMap key 保证插入顺序。
3. **布尔命名 G.NAM.08**：`QuerySbomPackagesRequest` 内部字段为 `isGroupByPackage`（`is` 前缀），Controller 通过 `@RequestParam(name = "groupByPackage")` 显式映射保持 API 兼容。
4. **排序策略**：子查询按 name 排序（`.` 开头排末尾）、外层同样按 name 排序。
5. **分组 VO 复用现有 PackageWithStatisticsVo**：`PackageGroupVo.packages` 使用 `List<PackageWithStatisticsVo>`，复用已有 `packageWithStatisticsVoFromPackage` 转换方法。
6. **sourceInfo 字段**：在 `PackageWithStatisticsVo` 新增该字段，用于区分同一组内不同来源路径的包副本。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `model/.../PackageGroupVo.java` | 新增 | 分组 VO：name + version + packages 列表 |
| `model/.../PackageWithStatisticsVo.java` | 修改 | 新增 sourceInfo 字段 |
| `model/.../QuerySbomPackagesRequest.java` | 修改 | 新增 isGroupByPackage 字段（G.NAM.08 命名） |
| `dao/.../PackageRepository.java` | 修改 | 新增 countPackageGroups + getPackagesByGroupPage（SQL 分页） |
| `interface/.../SbomService.java` | 修改 | 新增 getPackageGroupByNameForPage 接口方法 |
| `sbom-web/.../SbomController.java` | 修改 | 新增 isGroupByPackage 参数（name="groupByPackage"）+ 分支逻辑 |
| `sbom-web/.../SbomServiceImpl.java` | 修改 | 新增 getPackageGroupByNameForPage 实现（SQL count + SQL 分页 + 小批量内存分组） |
| `sbom-web/.../SbomControllerTest.java` | 修改 | 新增分组查询接口测试 |
| `sbom-web/.../SbomServiceImplTest.java` | 修改 | 新增分组业务逻辑单元测试（mock countPackageGroups + getPackagesByGroupPage） |

## 风险 & 缓解
- **SQL 复杂度**：嵌套子查询重复过滤条件，需与 `getPackageInfoByNameForPage` 同步维护。通过代码审查和测试覆盖缓解。
- **性能**：SQL 层 GROUP BY + OFFSET 性能远优于全量内存分页，且 count 使用高效 `COUNT(*)`。

## 跨仓影响
- 无。仅 `openlibing-sbom` 单仓变更。
