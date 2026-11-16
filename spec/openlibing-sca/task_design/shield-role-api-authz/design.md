# #145 — 技术设计

## 方案概述

不新建 RBAC 框架，直接复用系统中已有的 `CommonService.verifyCommunityPermission(userId, projectId)`：Controller 透传 `userId`（部分端点加 `projectId`），Service 方法首行执行校验，越权抛 `PermissionException`（403），Controller 统一转 `ResponseEntity.failure(code, message)`。角色判定收敛为 SQL：`admin` / `platform_operater` 全局放行，或目标项目下的 `project_manager`（`perm_group_id = 0`）。

## 数据流（修复后）

```
POST /shield/role/add?userName=..&userId=u1  (body: ShieldRoleVO{projectId})
  └─ ShieldRoleController#addRole
       └─ ShieldRoleServiceImpl#addRole(vo, userName, userId)
            ├─ commonService.verifyCommunityPermission(userId, vo.projectId)
            │     ├─ userId 空白 → PermissionException(403, "权限不足")
            │     └─ userRoleMapper.queryCommunityPermission(userId, projectId) == 0
            │           → PermissionException(403, "权限不足")
            └─ insertShieldRole(...)   # 仅授权通过后执行
  catch PermissionException → ResponseEntity.failure(403, "权限不足")
```

`/scanoss/shield/*` 同理，`projectId` 取自 `ScanossShiledVo` 或 `ScanossShieldReq`。

## 架构决策

| 决策                                                                              | 理由                                                                                                            |
| --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| D1 复用 `verifyCommunityPermission` 而非新建门禁组件                              | 该方法已在 `CommonServiceImpl` 存在且被其他管理路径使用，避免再造第二套判定；issue 也将其列为「门禁覆盖遗漏」   |
| D2 校验下沉 Service 首行，Controller 只透传                                       | 防止新增内部调用方绕过 Controller 直调 Service；Controller 保持薄层                                             |
| D3 `userId` 作为请求参数显式传入                                                  | `5852b0d2` 已移除 JwtUtils/JWT 权限逻辑，仓内无可信身份上下文可取；短期内以显式参数打通链路（**遗留风险见下**） |
| D4 越权以 403 + 文案返回，而非抛到全局异常                                        | 与既有 `ScaException` 分支风格一致，前端可按 code 统一处理；`PermissionException.code` 固定 403                 |
| D5 `batchDeleteScanossShield` 入参由 `List<Integer>` 改为 `ScanossShieldReq`      | 删除操作需要 `projectId` 做项目级校验，原签名无法携带                                                           |
| D6 SQL 去掉 `project_cie` 分支                                                    | `project_cie` 仅代表项目 CIE 角色，不应获得屏蔽规则管理权限；收敛为 admin / platform_operater / project_manager |
| D7 查询端点（`/list`、`/queryScanossShield`、`/get/shield/hit/number`）一并加校验 | 屏蔽规则命中数与规则列表本身即门禁敏感数据，仅保护写端点不足以防信息泄露                                        |

## 涉及文件

| 文件                                                                                       | 操作 | 说明                                                                                           |
| ------------------------------------------------------------------------------------------ | ---- | ---------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/controller/ShieldRoleController.java`           | 修改 | 5 个端点增加 `userId`（命中数端点加 `projectId`）、`catch (PermissionException)`               |
| `src/main/java/com/openlibing/sca/analysis/controller/ScanossShieldController.java`        | 修改 | 3 个端点增加 `userId`、`catch (PermissionException)`；日志类名修正为 `ScanossShieldController` |
| `src/main/java/com/openlibing/sca/analysis/service/ShieldRoleService.java`                 | 修改 | 5 个方法签名增加 `userId`（命中数方法加 `projectId`）                                          |
| `src/main/java/com/openlibing/sca/analysis/service/impl/ShieldRoleServiceImpl.java`        | 修改 | 各方法首行调用 `verifyCommunityPermission`（L89 / L110 / L167 / L379 / L404）                  |
| `src/main/java/com/openlibing/sca/analysis/service/ScanossShieldService.java`              | 修改 | 3 个方法签名增加 `userId`；批量删除改收 `ScanossShieldReq`                                     |
| `src/main/java/com/openlibing/sca/analysis/service/impl/ScanossShieldServiceImpl.java`     | 修改 | 三个方法首行 `verifyCommunityPermission`（L35 / L45 / L56）                                    |
| `src/main/java/com/openlibing/sca/analysis/service/impl/CommonServiceImpl.java`            | 修改 | 空白 `userId` / 无权限时文案由「无权限」改为「权限不足」                                       |
| `src/main/java/com/openlibing/sca/analysis/entity/req/ScanossShieldReq.java`               | 修改 | 新增 `projectId`                                                                               |
| `src/main/java/com/openlibing/sca/common/domain/ScanossShiledVo.java`                      | 修改 | 新增 `projectId`                                                                               |
| `src/main/java/com/openlibing/sca/common/domain/ShieldRoleVO.java`                         | 修改 | 新增 `projectId`                                                                               |
| `src/main/resources/mapper/analysis/UserRoleMapper.xml`                                    | 修改 | `queryCommunityPermission` 去掉 `project_cie` 分支                                             |
| `src/test/java/com/openlibing/sca/analysis/controller/ShieldRoleControllerTest.java`       | 修改 | 适配新签名 + 403 用例                                                                          |
| `src/test/java/com/openlibing/sca/analysis/controller/ScanossShieldControllerTest.java`    | 修改 | 适配新签名 + `testAddScanossShieldNoPermission`                                                |
| `src/test/java/com/openlibing/sca/analysis/service/impl/ShieldRoleServiceImplTest.java`    | 修改 | `verifyCommunityPermission` 抛 `PermissionException` 断言                                      |
| `src/test/java/com/openlibing/sca/analysis/service/impl/ScanossShieldServiceImplTest.java` | 修改 | 适配新签名与校验桩                                                                             |

## 风险 & 缓解

| 风险                                                              | 缓解                                                                                                                                                                      |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`userId` 由客户端提交，可伪造/冒充超管**                        | 当前仅能保证「参数为空或无角色即拒绝」，无法证明调用者身份；需网关/SDK 注入可信身份或恢复服务端令牌解析后，才能满足 issue「伪造凭证无法绕过」验收（本轮未闭环，明确遗留） |
| 破坏性契约：8 个端点新增必填参数                                  | 前端/联调需同步补 `userId`/`projectId`；建议发布说明标注                                                                                                                  |
| `project_cie` 用户失去访问，可能影响既有流程                      | 按最小权限收敛；如业务确需，应改为显式授权而非恢复分支                                                                                                                    |
| Service 内多处校验导致重复查询                                    | `queryCommunityPermission` 为轻量 count 查询；如需优化可后续加缓存，本轮不做                                                                                              |
| 仅覆盖 8 个端点，其他管理端点仍裸奔                               | 已在 proposal 明确未覆盖清单；由 #141（下线）与 #156（open-api 鉴权）等分批整改                                                                                           |
| 查询端点加权限影响前端列表页                                      | 属预期行为（屏蔽规则为门禁敏感数据），需前端同步                                                                                                                          |
| `PermissionException` 被通用 `catch (Exception)` 吞掉返回泛化文案 | Controller 中 `catch (PermissionException)` 置于 `catch (Exception)` 之前                                                                                                 |

## 跨仓影响

前端/调用方需为 8 个端点补 `userId`（命中数端点补 `projectId`）；身份可信性依赖网关或平台侧注入（当前未实现，风险未闭环）。spec 文档归档 openlibing-docs 仓（本目录）。
