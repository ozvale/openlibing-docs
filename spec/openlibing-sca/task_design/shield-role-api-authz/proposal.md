# #145 — 屏蔽规则与 Scanoss 屏蔽接口的角色/项目权限校验（垂直越权）

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/145
（【安全】【Argus】门禁/屏蔽规则与高危管理操作缺少角色校验（垂直越权，可清空全表扫描数据），CWE-862，高危，当前状态 closed）

来源：Argus 扫描批次 `openlibingsca-20261103130601-009`（置信度已验证，可利用性可实际利用）。

主位置：`src/main/java/com/openlibing/sca/analysis/controller/ShieldRoleController.java:58`。

现状（issue 核实结论）：

- 屏蔽规则三个写端点（`/shield/role/add`、`/delete`、`/effective`）仅有 `@LogApi` + `@PostMapping`，无权限注解；`/add` 的 `userName` 为请求参数，服务端不校验调用者身份；
- `ShieldRoleServiceImpl.addRole` / `deleteRole` 直接操作 `tbl_shield_role`；`shieldRoleEffective` 经 `mongoTemplate.updateMulti` 批量改写 `scan_issue` 的 `blockStatus` / `shieldRole`，无权限判断；
- 全仓无 `@PreAuthorize` / `@Secured` / `HandlerInterceptor` / `hasRole` 兜底；
- 叠加风险：`/project/notice/scan/clear` 空 `productName` 触发 `deleteAll()` 可清空两表扫描数据。

影响：内网任意普通用户可增删/生效屏蔽规则，直接改写 SCA 门禁判定结果（隐藏或暴露合规问题）；叠加全表清空可影响数据可用性。issue 同时指出 `5852b0d2`（移除 JwtUtils 与 JWT 权限逻辑）后服务端已无任何角色校验残留，状况恶化。

## 功能描述

**做什么**：

1. 复用既有 `CommonService.verifyCommunityPermission(userId, projectId)` 作为门禁：`userId` 为空或 `UserRoleMapper.queryCommunityPermission` 计数为 0 时抛 `PermissionException`（`code=403`，文案「权限不足」）；
2. 覆盖 **8 个**屏蔽规则相关端点：
   - `ShieldRoleController`（5）：`POST /shield/role/add`、`POST /shield/role/delete`、`GET /shield/role/list`、`GET /shield/role/get/shield/hit/number`、`POST /shield/role/effective`；
   - `ScanossShieldController`（3）：`POST /scanoss/shield/addScanossShield`、`POST /scanoss/shield/batchDeleteScanossShield`、`POST /scanoss/shield/queryScanossShield`；
3. Controller 增加必填请求参数 `userId`（`/get/shield/hit/number` 另加 `projectId`），把 `userId`（及 `projectId`）传入 Service；Service 方法签名同步扩展：`addRole(vo, userName, userId)`、`deleteRole(vo, userId)`、`selectRole(queryPo, userId)`、`getshieldRleHitNum(scanId, vendor, component, userId, projectId)`、`shieldRoleEffective(po, userId)`；`ScanossShieldService` 三个方法增加 `userId`，`batchDeleteScanossShield` 入参由 `List<Integer>` 改为 `ScanossShieldReq`（以取 `projectId`）；
4. 校验在 **Service 层方法首行**执行，Controller 只做参数透传，保证内部调用同样受控；
5. Controller 增加 `catch (PermissionException e)` → `ResponseEntity.failure(e.getCode(), e.getErrorMessage())`，越权返回 403 与「权限不足」；
6. `ScanossShieldReq` / `ScanossShiledVo` / `ShieldRoleVO` 补充 `projectId` 字段承载校验上下文；
7. `UserRoleMapper.queryCommunityPermission` 去掉 `project_cie` 分支：仅 `admin`、`platform_operater` 全局放行，或目标项目下 `project_manager` 且 `perm_group_id = 0` 放行。

**不做什么**：

- 未引入 `@PreAuthorize` / 统一 RBAC 注解或拦截器（issue P1/P2 的系统性整改，本轮未覆盖）；
- 未覆盖 issue 列举的其他管理写端点：`/project/notice/scan/clear`（本批次未改；权限由 `449cc555` 单独加入，但空 `productName` 仍走 `deleteAll()`，见验收）、`/version/scan/deleteByIds`、`/email/review/delete`（均未接入权限校验）；
- 未建立可信身份基座：`userId` 仍是客户端请求参数，服务端无验签/令牌解析（issue P0 前置条件，本轮未解决）；
- 未补高危机机接口的审计留痕（由 `api-access-audit-log`（#138）的日志能力承接）。

## 验收标准

- [x] 低权限账号调用屏蔽规则写端点返回 403「权限不足」（`ShieldRoleControllerTest#testAddRoleNoPermission`、`#testDeleteRoleNoPermission`；`ScanossShieldControllerTest#testAddScanossShieldNoPermission`；`ShieldRoleServiceImplTest#testAddRole_NoPermission` 断言 `verifyCommunityPermission("user1", null)` 抛出 `PermissionException`）
- [x] 超管/平台运营/目标项目管理员正常调用（SQL 条件 `role = 'admin' or role = 'platform_operater' or (role = 'project_manager' and project_id = #{projectId} and perm_group_id = 0)`）
- [x] `/shield/role/list`、`/get/shield/hit/number` 等读端点同样受项目权限约束（`verifyCommunityPermission` 位于对应 Service 方法首行）
- [x] 仅持 `project_cie` 角色不再放行（`c0ce1dfb` 从 SQL 删除该分支）
- [x] `ScanossShieldReq` 增加 `projectId`，删除接口按请求体项目上下文校验
- [ ] 空 `productName` 的 `/project/notice/scan/clear` 被拒绝、不再触发 `deleteAll()`（**本轮未覆盖**：当前代码 `productName` 为空仍执行 `deleteAll()`，仅增加权限校验）
- [ ] `/version/scan/deleteByIds`、`/email/review/delete` 等端点接入权限（**本轮未覆盖**）
- [ ] 伪造超管身份的未验签凭证无法绕过（**本轮未满足/未验证**：`userId` 来自请求参数，无可信来源校验）
- [ ] 统一 RBAC 注解覆盖所有管理写端点（issue P1/P2，**本轮未覆盖**）
- [ ] `mvn test` 全量执行结果（本轮为回溯补写文档，未执行，未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `ShieldRoleController`、`ScanossShieldController`、`ShieldRoleService(+Impl)`、`ScanossShieldService(+Impl)`、`CommonServiceImpl`（异常文案）、`ScanossShieldReq`、`ScanossShiledVo`、`ShieldRoleVO`；`resources/mapper/analysis/UserRoleMapper.xml`；4 个相关单测
- 接口 / 契约：**破坏性变更**——8 个端点新增必填 `userId`（`/get/shield/hit/number` 另加 `projectId`），调用方未带参数将参数校验失败；越权返回 403
- 配置 / schema：无表结构变更；仅 SQL 判定条件变化（`project_cie` 失权）
- 行为变化：项目内 `project_cie` 用户失去屏蔽规则读/写权限
