# 【openlibing】【sbom】机机接口下线切换apig — 实现任务

> 本清单为过程文档，最终交付状态与验证结果以同目录 [archive.md](./archive.md) 归档为准。

## 进度: 6/6 complete

- [x] Task 1: 新建 `ApigController.java`，类注解 `@Controller` + `@RequestMapping(path = "/apig-api")` + `@Validated`，注入 `SbomService` 依赖
- [x] Task 2: 复制 `querySbomPublishResult` 接口方法到 ApigController
- [x] Task 3: 复制 `exportSbom`、`exportAllPackageSbom` 接口方法 + private 辅助方法 `downloadSbom`、`getDownloadFileExt` 到 ApigController
- [x] Task 4: 复制 `querySbomPackagesDeprecated` + `querySbomPackages`（前者内部调用后者，必须一起复制）+ `getPackagesInfoByName`（querySbomPackages）到 ApigController
- [x] Task 5: 复制 `queryLicense`（queryLicenseUniversalApi）、`queryProductStatisticsByProductName`（queryProductStatistics）、`queryProductByFullAttributes`（addProduct）共 3 个接口方法到 ApigController
- [x] Task 6: 编译验证 `mvn compile -pl sbom-web` 通过（✅ `mvn compile -pl sbom-web -am` BUILD SUCCESS，11 模块全部通过）。~~Phase 4 阶段补充 `ApigControllerTest` 并运行通过~~ → **范围调整**：`ApigControllerTest` 取消交付，见归档「范围调整说明」

## 备注

- `publishSbomFile` 接口不在本次 ApigController 复制范围（用户决策移除，原 SbomController 中的对应接口保留不变）
- `ApigControllerTest` 单测原计划 Phase 4 补充，经范围调整取消交付（ApigController 为 SbomController 接口的原样复制、复用同一 SbomService 实现），以归档「范围调整说明」为准
- ApigController 中的 `querySbomPackagesDeprecated` 方法内部调用了同类中的 `querySbomPackages` 方法，两者必须一起复制
- `exportSbom` 与 `exportAllPackageSbom` 依赖 private 方法 `downloadSbom` 与 `getDownloadFileExt`，必须一并复制
- 最终 ApigController 共包含 8 个对外接口方法（不含 publishSbomFile）+ 1 个被同类调用的 `querySbomPackages` 方法 + 2 个 private 辅助方法
