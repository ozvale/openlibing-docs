# dependency-type-identification — 实现任务

## 进度: 0/7 complete

- [ ] Task 1: 修改 `model/.../entity/PackageStatistics.java`：新增 `dependencyType` 字段（`Integer`）+ Javadoc（首行描述 + 空行 + `@see` 取值说明）+ getter/setter
- [ ] Task 2: 修改 `batch/.../step/CollectStatisticsStep.java`：新增 `collectPackageDependencyType(statistics, pkg, sbom)` 方法，在 `collectPackageStatistics` 中调用；实现根包识别（`SPDXRef-DOCUMENT DESCRIBES`）+ 直接/间接依赖解析（`DEPENDS_ON` 关系）
- [ ] Task 3: 修改 `model/.../vo/sbom/PackageStatisticsVo.java`：新增 `dependencyType` 字段 + getter/setter + 在 `fromPackage` 中从 `PackageStatistics` 填充
- [ ] Task 4: 修改 `model/.../request/sbom/QuerySbomPackagesRequest.java`：新增 `dependencyType` 字段（`Integer`）+ getter/setter + 更新 `toString`
- [ ] Task 5: 修改 `dao/.../PackageRepository.java`：`getPackageInfoByNameForPage` / `getPackagesByGroupPage` / `countPackageGroups` 三个 SQL 方法新增 `dependencyType` 参数 + `(:dependencyType IS NULL OR dependency_type = :dependencyType)` 过滤条件
- [ ] Task 6: 修改 `sbom-web/.../service/sbom/impl/SbomServiceImpl.java`：`getPackageInfoByNameForPage` / `getPackageGroupByNameForPage` 透传 `req.getDependencyType()` 参数
- [ ] Task 7: 修改 `sbom-web/.../controller/SbomController.java`：`querySbomPackagesDeprecated` 新增 `@RequestParam(required = false) Integer dependencyType` + 设置到 `QuerySbomPackagesRequest`

## 验证方式
- Phase 3：编译通过（`mvn compile -pl sbom-web -am`）
- Phase 4：按 `ai_memory.md` 规则补充 UT 到 `sbom-web/src/test/java/.../batch/step/CollectStatisticsStepTest.java`，覆盖：
  - 根包识别（`SPDXRef-DOCUMENT DESCRIBES` 关系）
  - 直接依赖（根包 `DEPENDS_ON`）
  - 间接依赖（其他包 `DEPENDS_ON` 链路）
  - 无依赖包（没被任何包 `DEPENDS_ON`）→ 直接依赖
  - 既直接又间接 → 直接依赖
  - 接口过滤参数（`dependencyType=0` / `1` / `null`）
- 测试执行：`mvn test -pl sbom-web "-Dtest=CollectStatisticsStepTest"`（按 `ai_memory.md` 规则，在 `openlibing-sbom` 目录下执行）

## 生成前约束检查
- [x] 只修改 `openlibing-sbom` 业务仓 + `openlibing-docs` spec 文档
- [x] 遵循目标仓既有架构、命名、错误处理、日志、配置、测试风格（Javadoc 断层排版、G.NAM.08 布尔命名、G.FMT.10 行宽 120、G.MET.01 方法 50 行）
- [x] 避免无关重构、无关格式化、元数据 churn
- [x] 无硬编码凭证、敏感信息、危险默认值或明显注入风险
- [x] 行为变化：新增依赖类型识别 + 接口过滤参数（向后兼容），UT 按 `ai_memory.md` 规则留到 Phase 4
