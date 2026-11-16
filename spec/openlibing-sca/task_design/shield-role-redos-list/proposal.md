# 115 — /shield/role/list 屏蔽规则 ReDoS 修复

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/115
（【安全】【外部参数校验】/shield/role/list 接口正则表达式 ReDoS 风险，当前状态 closed）

来源：master 外部参数校验排查（commit `8e8fc796`）。

调用链：`GET /shield/role/list`（`ShieldRoleController#selectRole`）→ `ShieldRoleServiceImpl#selectRole` → `getshieldRoleHitsNumber(rolesNew, scanId)`。

原有风险：

1. 规则 pattern 由 `POST /shield/role/add` 写入库，`addRole` 只做 `trim()`，`ShieldRoleVO` 无长度/通配符数量约束；
2. `getshieldRoleHitsNumber` 对 Mongo 中该 `scanId` 下 `blockStatus=BLOCK` 的每条 issue，用 `wildCard2RegEx(role)` 转正则后 `Pattern.matches` 逐一比对；
3. `wildCard2RegEx` 虽转义了 `\.[]{}()+^$|`，但 `*`→`.*`、`?`→`.?` 的数量不受限。用户先持久化 `*a*a*a*...`、`?a?a?...` 之类规则，之后每次查询 `/list` 都会对全量 issue 触发指数级回溯；Java `Pattern` 无执行超时，单请求可打满 CPU，且危害随匹配数据量放大。

## 功能描述

**做什么**：

1. `addRole` 入口校验 pattern：长度 ≤ 256、`*`/`?` 总数 ≤ 10，超限返回 `40052`（`2f35a709`，与 `shieldRoleEffective` 共用 `validateShieldRolePattern`）；
2. 补齐入口健壮性：`addRole` 在 `trim()` 前拒绝空 `shieldRole` / 空 `vendor`（原为 NPE → 500），并拒绝相邻通配符 `**`、`*?`、`?*`、`??`（`3cfc6d1e`）；
3. 存量守卫：`getshieldRoleHitsNumber` 逐条用 `isShieldRolePatternValid` 过滤超限规则，非法规则跳过并 `warn` 日志；规则仍在 `/list` 返回、仍可通过 `/delete` 删除（`b6415fac`）；
4. 匹配实现替换：`wildCard2RegEx + Pattern.matches` → `matchesShieldPattern` 线性 DP（O(pattern×text)），`*` 任意序列、`?` 零或一（`3cfc6d1e`）；
5. `isShieldRolePatternValid` 改为 `public static`，供 DM 侧匹配点复用同一守卫。

**不做什么**：

- 不提供存量高风险规则清理脚本/清理接口（issue 修复建议 3 的一部分，本轮未覆盖，改为运行时跳过）；
- 不在 `/list` 对存量规则硬拒绝或删除数据（保持查询接口可用、规则可管理）；
- 不改变 `/list` 的权限校验（由 #145 的鉴权改造负责，见兄弟目录 `shield-role-api-authz`）；
- 不限制 `/list` 查询参数（`communityName` / `repository` / `vendor` / `platform`）的取值。

## 验收标准

- [x] 添加接口拒绝超长 pattern（`ShieldRoleServiceImplTest#testAddRole_PatternTooLong_Rejected`，断言 `shieldRoleMapper.insert` 未被调用）
- [x] 添加接口拒绝过量通配符 pattern（`testAddRole_TooManyWildcards_Rejected`）
- [x] 添加接口拒绝相邻通配符 pattern（`testAddRole_AdjacentWildcards_Rejected`）
- [x] 空 `shieldRole` / 空 `vendor` 返回业务错误而非 NPE（`testAddRole_NullShieldRole_RejectedNotNpe`、`testAddRole_NullVendor_RejectedNotNpe`）
- [x] 存量超限规则在 `/list` 命中统计中被跳过且不抛异常，合法规则正常计数（`testGetshieldRoleHitsNumber_SkipsInvalidLegacyPattern`）
- [x] 高量级 pattern 不再产生指数回溯：10 个非相邻通配符 + 800 字符不匹配文本即时返回（`testMatchesShieldPattern_PolynomialPatternStaysLinear`）
- [x] 匹配语义保持：`*` 任意序列、`?` 零或一、元字符按字面、空规则/null 容错（`testMatchesShieldPattern_BasicSemantics`）
- [ ] 存量规则清理脚本/接口（issue 修复建议 3，本轮未覆盖）
- [x] 相关单元测试已补充
- [ ] 单测运行结果与覆盖率：本轮为回溯补写，未执行 `mvn test`、未核对 JaCoCo（未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `ShieldRoleServiceImpl`（`/shield/role/list` 命中统计链路）；`3cfc6d1e` 同时把同一匹配实现用于 `/effective`、`/get/shield/hit/number` 与 DM 侧 `OpenScanDMServiceImpl#applyVendorShieldRule`
- 接口 / 契约：`/shield/role/add` 新增 `40052` 校验失败；`/shield/role/list` 响应结构不变，存量非法规则 `hitsNumber` 不再累加
- 配置 / schema：无变化；不做数据迁移
- 行为变化：`a.*` 这类「字面元字符 + `*`」的旧语义（绑定为 `a\.*`）改为通配符语义
