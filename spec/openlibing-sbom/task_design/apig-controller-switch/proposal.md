# 【openlibing】【sbom】机机接口下线切换apig

## 需求背景

当前 openlibing-sbom 模块的机机接口直接通过 `/openlibing-sbom/sbom-api/*` 路径对外提供，不符合安全规范。需要将这些接口从 openlibing 切换至 apig（华为云 APIGW，AppCode 鉴权），以保证合规性、提升安全能力并优化运维效率。

关联 Issue: https://gitcode.com/openlibing/openlibing-sbom/issues/61

## 功能描述

- 新建 `ApigController`，路径前缀 `/apig-api`，与原 `SbomController`（`/sbom-api`）并存
- 将 SbomController 中下列 8 个机机接口方法原样复制一份到 ApigController，方法签名、注解、Service 调用、日志、鉴权、`@LogApi`、`@Operation` 等全部保持原样，仅类名与 `@RequestMapping` 路径前缀不同
- 复用的 8 个接口（URL 子路径与原接口一致，仅前缀从 `/sbom-api` 变为 `/apig-api`）：
  1. `POST /apig-api/querySbomPackageList` — 查询 packages 列表
  2. `POST /apig-api/exportAllPackageSbom` — 导出 sbom 的 package
  3. `GET  /apig-api/querySbomPublishResult` — 查询推送结果
  4. `POST /apig-api/exportSbom` — 导出 sbom
  5. `GET  /apig-api/querySbomPackages` — 查询 package
  6. `GET  /apig-api/queryLicenseUniversalApi` — 查询 license
  7. `GET  /apig-api/queryProductStatistics` — 查询单个产物总览数据
  8. `POST /apig-api/addProduct` — sbom 新增 product（已在 apig 平台配置）
- `publishSbomFile` 接口不在本次 ApigController 复制范围（用户决策移除，原 SbomController 中的对应接口保留不变）
- ApigController 注入与 SbomController 相同的依赖（仅 `SbomService`），通过 Spring 自动装配复用同一份 Service 实现

## 不做什么

- 不删除 SbomController 中的原接口（保留并存认，后续下线时再删）
- 不在 ApigController 中复制 `publishSbomFile` 接口
- 不修改 SbomService 或任何业务逻辑层代码
- 不修改数据库 schema、不修改请求/响应数据模型
- 不调整 apig 网关侧的 AppCode 鉴权与路由配置（属于运维侧动作）
- 不新增接口（仅复制已有接口到新 Controller）

## 验收标准

- [ ] 新增 `ApigController` 类，路径前缀 `/apig-api`，包含上述 8 个接口方法
- [ ] 8 个接口方法的方法签名、注解、Service 调用与原 SbomController 完全一致（仅类名与路径前缀不同）
- [ ] 原 SbomController 中的接口保持不变，无回归
- [ ] 项目编译通过（`mvn compile -pl sbom-web`）
- [ ] 相关单测通过（`mvn test -pl sbom-web -Dtest=ApigControllerTest`）
- [ ] 不引入新的硬编码凭证、敏感信息

## 影响范围

| 文件                                                                               | 操作     | 说明                                                                      |
| ---------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------- |
| `sbom-web/src/main/java/org/opensourceway/sbom/controller/ApigController.java`     | **新增** | 复制 SbomController 中 8 个机机接口方法，路径前缀改为 `/apig-api`         |
| `sbom-web/src/test/java/org/opensourceway/sbom/controller/ApigControllerTest.java` | **新增** | ApigController 单元测试（Phase 4 阶段补充，参考 SbomControllerTest 风格） |

## 跨仓影响

无。本次仅涉及 openlibing-sbom 业务仓内部 Controller 层扩展，不影响其他仓。
