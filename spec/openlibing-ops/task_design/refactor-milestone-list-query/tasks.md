# 里程碑分页查询调整为项目列表查询 — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 先更新 `ProductQualityMilestoneControllerTest`、`ProductQualityMilestoneServiceTest`、`ProductQualityMilestoneDomainServiceTest` 和 `ProductQualityCoreMapperXmlTest`，将分页断言改为项目列表、空列表、项目隔离、`id DESC` 排序及分页代码移除断言；定向测试在依赖解析阶段被私服 401 阻塞，未完成 RED/GREEN 运行验证。
- [x] Task 2: 修改 `ProductQualityMilestoneController`、`ProductQualityMilestoneService`、`ProductQualityMilestoneDomainService`、`PqMilestoneMapper` 和 `PqMilestoneMapper.xml`，删除 page 全链路，将 `selectPageByProjectId` 替换为 `selectListByProjectId`，使 `/detail` 仅接收 `projectId` 并返回 `List<MilestoneResp>`；保留更新/删除的单条查询逻辑。
- [x] Task 3: 修正 `ProductQualityCatalogControllerTest`、`ProductQualityCatalogServiceTest`、`ProductQualityCatalogDomainServiceTest` 和 `ProductQualityCoreMapperXmlTest` 中的旧目录方法与 Mapper 引用，对齐根目录/非根目录当前链路；目录主代码保持不变。
- [x] Task 4: 检查 `git diff` 和 `git status`，确认未混入权限变更的额外修改、无分页残留、无旧目录方法引用；不 commit、不 push、不创建 PR。私有依赖仓库返回 401，已记录阻塞并执行可用的静态检查。

## 验证命令

```powershell
mvn "-Dtest=ProductQualityMilestoneControllerTest,ProductQualityMilestoneServiceTest,ProductQualityMilestoneDomainServiceTest,ProductQualityCatalogControllerTest,ProductQualityCatalogServiceTest,ProductQualityCatalogDomainServiceTest,ProductQualityCoreMapperXmlTest" test
```

预期：相关测试全部通过；若构建在依赖解析阶段失败，则明确区分环境失败与代码测试结果。

## 实际验证结果

- 定向 Maven 测试未能进入测试编译或执行阶段：解析 `com.openlibing:openlibing-common:1.0.21.2` 时私有仓库返回 HTTP 401，因此不能声明测试通过。
- 业务仓与文档仓 `git diff --check` 均通过。
- `PqMilestoneMapper.xml` 与 `PqMilestoneCatalogMapper.xml` XML 解析通过。
- `selectPageByProjectId`、`listBasicCatalogs`、`selectByMilestoneId` 和 `domainService.listMilestoneCatalogs` 旧引用检索无匹配。
- 未 commit、未 push、未创建 PR；上一需求的权限相关未提交变更保持原状。
