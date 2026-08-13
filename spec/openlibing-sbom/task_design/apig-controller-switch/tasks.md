# 【openlibing】【sbom】机机接口下线切换apig — 实现任务

## 进度: 0/6 complete

- [ ] Task 1: 新建 `ApigController.java`，类注解 `@Controller` + `@RequestMapping(path = "/apig-api")` + `@Validated`，注入 `SbomService` 依赖
- [ ] Task 2: 复制 `querySbomPublishResult` 接口方法到 ApigController
- [ ] Task 3: 复制 `exportSbom`、`exportAllPackageSbom` 接口方法 + private 辅助方法 `downloadSbom`、`getDownloadFileExt` 到 ApigController
- [ ] Task 4: 复制 `querySbomPackagesDeprecated` + `querySbomPackages`（前者内部调用后者，必须一起复制）+ `getPackagesInfoByName`（querySbomPackages）到 ApigController
- [ ] Task 5: 复制 `queryLicense`（queryLicenseUniversalApi）、`queryProductStatisticsByProductName`（queryProductStatistics）、`queryProductByFullAttributes`（addProduct）共 3 个接口方法到 ApigController
- [ ] Task 6: 编译验证 `mvn compile -pl sbom-web` 通过；Phase 4 阶段补充 `ApigControllerTest`（参考 SbomControllerTest 风格），运行 `mvn test -pl sbom-web -Dtest=ApigControllerTest` 通过

## 备注
- `publishSbomFile` 接口不在本次 ApigController 复制范围（用户决策移除，原 SbomController 中的对应接口保留不变）
- 按 `openlibing-docs/spec/openlibing-sbom/ai_memory.md` 规则：Phase 3 编码阶段不生成 UT，Phase 4 业务 PR 交付前再补充 ApigControllerTest
- ApigController 中的 `querySbomPackagesDeprecated` 方法内部调用了同类中的 `querySbomPackages` 方法，两者必须一起复制
- `exportSbom` 与 `exportAllPackageSbom` 依赖 private 方法 `downloadSbom` 与 `getDownloadFileExt`，必须一并复制
- 最终 ApigController 共包含 8 个对外接口方法（不含 publishSbomFile）+ 1 个被同类调用的 `querySbomPackages` 方法 + 2 个 private 辅助方法
