# dependency-type-identification — SBOM 软件包主被动依赖标识

## 需求背景
openlibing-sbom 软件成分分析页面中，当前未区分软件包的直接依赖与间接依赖属性。开源管理中，主被动依赖管理原则差异较大，需在 SBOM 解析阶段从 spdx-json 元数据层面识别每个软件包的依赖类型（直接/间接），并在包查询接口支持按依赖类型过滤，便于前端展示与运营筛选。

关联 Issue: https://gitcode.com/openlibing/openlibing-sbom/issues/51

## 功能描述
1. `PackageStatistics` 实体新增 `dependencyType` 字段（`Integer`，0=直接依赖，1=间接依赖，3=直接/间接依赖，可扩展）
2. `CollectStatisticsStep` 在统计阶段解析每个软件包的依赖类型，解析规则：
   - 识别根包：通过 `SPDXRef-DOCUMENT` 与 `DESCRIBES` 关系找到根包集合
   - 直接依赖（0）= 根包 `DEPENDS_ON` 的包 ∪ 没被任何包 `DEPENDS_ON` 的包
   - 间接依赖（1）= 通过其他包 `DEPENDS_ON` 链路间接引入的包
   - 既属于直接依赖又属于间接依赖 → 直接/间接依赖（3）
3. `PackageStatisticsVo` 新增 `dependencyType` 字段，通过 `fromPackage` 填充，暴露给前端
4. `querySbomPackageList` / `querySbomPackages` 接口入参新增 `dependencyType` 可选过滤参数，按依赖类型筛选包列表
5. `PackageRepository` 的 `getPackageInfoByNameForPage` / `getPackagesByGroupPage` / `countPackageGroups` 三个 SQL 方法同步新增 `dependencyType` 过滤条件

不做：
- 不修改前端代码（前端组处理）
- 不修改 `SpdxReader` 解析层（已持久化所有 relationships 到 `SbomElementRelationship` 表）
- 不创建 schema 迁移脚本（依赖 Hibernate auto DDL 自动建列）
- 不做 go 语言专属判断（按 Issue 详情要求，实现通用 spdx-json 解析逻辑）
- 不修改其他统计字段逻辑

## 验收标准
- [ ] `package_statistics` 表新增 `dependency_type` 列（Hibernate 自动建列）
- [ ] 解析 spdx-json 后，每个 `PackageStatistics` 都有正确的 `dependencyType` 值（0 或 1）
- [ ] 根包通过 `SPDXRef-DOCUMENT` 与 `DESCRIBES` 关系识别
- [ ] 直接依赖（0）：根包 `DEPENDS_ON` 的包 + 没被任何包 `DEPENDS_ON` 的包
- [ ] 间接依赖（1）：通过其他包 `DEPENDS_ON` 链路间接引入的包
- [ ] 既直接又间接 → 0
- [ ] `PackageStatisticsVo` 返回 `dependencyType` 字段
- [ ] `querySbomPackageList` / `querySbomPackages` 接口支持 `dependencyType` 可选过滤
- [ ] `getPackageInfoByNameForPage` / `getPackagesByGroupPage` / `countPackageGroups` 三个 SQL 方法支持 `dependencyType` 过滤
- [ ] 不传 `dependencyType` 时接口行为与变更前完全一致（向后兼容）
- [ ] 现有测试全部通过
- [ ] Phase 4 阶段补充 `CollectStatisticsStepTest` 测试覆盖根包/直接依赖/间接依赖/无依赖/既直接又间接等场景

## 影响范围
- 后端：`openlibing-sbom` 仓
  - `model` 模块
    - `PackageStatistics`：新增 `dependencyType` 字段 + getter/setter + Javadoc
    - `PackageStatisticsVo`：新增 `dependencyType` 字段 + getter/setter + `fromPackage` 填充
    - `QuerySbomPackagesRequest`：新增 `dependencyType` 字段 + getter/setter + toString
  - `dao` 模块
    - `PackageRepository`：`getPackageInfoByNameForPage` / `getPackagesByGroupPage` / `countPackageGroups` 三个方法新增 `dependencyType` 参数 + SQL 过滤条件
  - `batch` 模块
    - `CollectStatisticsStep`：新增 `collectPackageDependencyType` 方法 + 在 `collectPackageStatistics` 中调用
  - `sbom-web` 模块
    - `SbomServiceImpl`：`getPackageInfoByNameForPage` / `getPackageGroupByNameForPage` 透传 `dependencyType`
    - `SbomController`：`querySbomPackagesDeprecated` 新增 `dependencyType` `@RequestParam`
- 数据库：`package_statistics` 表新增 `dependency_type` 列（Hibernate auto DDL，无迁移脚本）
- 接口：`querySbomPackageList` / `querySbomPackages` 新增可选入参 `dependencyType`，向后兼容
