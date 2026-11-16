# 117 — /shield/role/effective 接口 ReDoS 与越权写修复

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/117
（【安全】【外部参数校验】/shield/role/effective 接口正则表达式 ReDoS 风险，当前状态 closed）

来源：master 外部参数校验排查（commit `8e8fc796`）。

调用链：`POST /shield/role/effective`（`ShieldRoleController#shieldRoleEffective`，`@RequestBody @Validated ShieldRolePo` + `userId`）→ `ShieldRoleServiceImpl#shieldRoleEffective` → `dealWithShieldRole` → `effectiveRole` → `dealWithRole` → `mongoTemplate.updateMulti` 批量改写 `scan_issue.blockStatus` / `shieldRole`。

原有风险（两条独立问题）：

1. **ReDoS**：请求体 `shieldRole` 非空时绕过数据库，直接用请求值构造 `TblShieldRole`；`ShieldRolePo` 仅 `communityName` / `repository` 有 `@NotBlank`，`shieldRole` / `vendor` 无任何约束。`dealWithRole` 用 `wildCard2RegEx(role)` + `Pattern.matches` 对每条 issue 匹配，`*`→`.*`、`?`→`.?` 数量不受限，`?a?a?...` 即可指数回溯（Java `Pattern` 无超时）。
2. **越权写**：接口无鉴权、无社区归属校验，任意调用方可批量改写任意社区/仓库扫描数据的屏蔽状态，直接影响门禁判定结果。

## 功能描述

**做什么**：

1. `shieldRoleEffective` 在调用 `dealWithShieldRole` **之前**校验请求体 pattern（长度 ≤ 256、通配符 ≤ 10），使 `40052` 不被 `dealWithShieldRole` 的 `catch (Exception)` 吞成 500（`2f35a709`）；
2. `3cfc6d1e` 追加拒绝相邻通配符（`**`、`*?`、`?*`、`??`）；
3. `dealWithRole` 对来自数据库的存量规则增加守卫（`isShieldRolePatternValid`），超限规则跳过并 `warn`，避免「请求体为空 → 回落到 DB 规则」路径再次暴露 ReDoS（`b6415fac`）；
4. `dealWithRole` 的匹配改为线性 DP `matchesShieldPattern`（`3cfc6d1e`）；
5. 越权写修复由同批次 #145 落地：`shieldRoleEffective` 增加 `verifyCommunityPermission(userId, projectId)`，控制器传递 `userId`（commit `ddc3873a`，另含 `c0ce1dfb` 收窄角色口径）——本目录只引用，不重复设计。

**不做什么**：

- 不改变「请求体 pattern 命中即批量改写全部匹配 issue」的业务语义（仍按 community/repository 最近一次扫描生效）；
- 不新增审批流或操作审计日志；
- 不重写 `dealWithShieldRole` 的异常包装（`DataAccessException` → 500 / 其他 → 500），只把校验提前到 try-catch 之外；
- 不提供存量脏规则清理脚本（同 #115，本轮未覆盖）。

## 验收标准

- [x] 超长 pattern 被拒绝（`ShieldRoleServiceImplTest#testShieldRoleEffective_PatternTooLong_Rejected`，断言未查询 scan/tbl_scan、未执行 `updateMulti`）
- [x] 过量通配符 pattern 被拒绝（`testShieldRoleEffective_TooManyWildcards_Rejected`，同样断言无副作用写入）
- [x] 相邻通配符 pattern 被拒绝（`testShieldRoleEffective_AdjacentWildcards_Rejected`）
- [x] 存量超限规则在 DB 回落路径被跳过，合法规则正常生效（`testDealWithRole_SkipsInvalidLegacyPattern`：合法规则 `spring-*` 命中 `spring-core`，`blockStatus` 被置为 BLOCK、`shieldRole` 记为 `spring-*`；非法规则不参与）
- [x] 高量级 pattern 不再指数回溯（`testMatchesShieldPattern_PolynomialPatternStaysLinear`）
- [x] 无权限调用无法改写屏蔽状态：由 #145 的 `verifyCommunityPermission` 覆盖（`ddc3873a` 引入，`c0ce1dfb` 收窄为 admin / platform_operater / project_manager），详见兄弟目录 `shield-role-api-authz`
- [ ] 非法 pattern 被拒绝、无权限调用 403 的端到端接口测试：本目录未见对应用例（`ShieldRoleControllerTest` 侧鉴权用例属 #145，未在本轮核实）
- [ ] 单测运行结果与覆盖率：本轮为回溯补写，未执行 `mvn test`、未核对 JaCoCo（未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `ShieldRoleServiceImpl#shieldRoleEffective` / `#dealWithShieldRole` / `#dealWithRole`
- 接口 / 契约：`POST /shield/role/effective` 请求体结构不变；新增 `40052` 拒绝分支；权限不足返回 403（#145）
- 数据：会写入 Mongo `scan_issue.blockStatus` / `shieldRole`，语义不变；存量超限规则不再参与生效
- 配置 / schema：无变化
- 权限：依赖 `CommonService#verifyCommunityPermission`（#145 改造）
