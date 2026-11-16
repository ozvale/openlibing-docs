# 116 — /shield/role/get/shield/hit/number 接口 ReDoS 修复

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/116
（【安全】【外部参数校验】/shield/role/get/shield/hit/number 接口正则表达式 ReDoS 风险，当前状态 closed）

来源：master 外部参数校验排查（commit `8e8fc796`）。该接口被 issue 认定为「仓内最易利用的正则注入/ReDoS 点」：无需预先创建规则，单次请求即可触发。

调用链：`GET /shield/role/get/shield/hit/number`（`ShieldRoleController#getShieldRleHitNum`，`scanId` 为 `@NotBlank`，`vendor` / `component` 为 `@RequestParam(required = false)`）→ `ShieldRoleServiceImpl#getshieldRleHitNum`。

原有风险：

1. `component` 直接来自请求参数，无长度、字符或通配符约束；
2. 服务层 `getNumberGroupVendorAndComponent(scanId)` 取回该扫描下未屏蔽 issue 的 vendor/component 聚合结果后，对每条用 `wildCard2RegEx(component)` 转正则并 `Pattern.matches`；
3. `wildCard2RegEx` 中 `?`→`.?`、`*`→`.*` 数量不受限。提交 `?a?a?a?...` 这类 component 即对每条 issue 做指数级回溯，单请求打满 CPU（Java `Pattern` 无执行超时）。

## 功能描述

**做什么**：

1. 在匹配前对 `component` 复用 `validateShieldRolePattern`：长度 ≤ 256、`*`/`?` 总数 ≤ 10，超限返回 `40052` 且不进入匹配循环（`b6415fac` 落地到本入口）；
2. `3cfc6d1e` 追加拒绝相邻通配符（`**`、`*?`、`?*`、`??`）；
3. 匹配实现由 `wildCard2RegEx + Pattern.matches` 替换为线性 DP `matchesShieldPattern(component, issue.component)`（O(pattern×text)），与 `/list`、`/effective` 及 DM 侧共用同一实现。

**不做什么**：

- 不做「超长 component 改用包含判断」的降级分支：DP 已是线性，无需按输入长度切换算法（issue 修复建议 2 的目标由 DP + 上限共同达成）；
- 不把 `component` 持久化，也不对其做存量守卫（仅入参，不落库）；
- 不改变 vendor 过滤与计数语义（仍按 vendor 大小写不敏感相等 + component 表达式匹配，累加聚合 `count`）；
- 不处理 `vendor` 为空时的空指针问题（本轮未改动，不属本 issue 范围）。

## 验收标准

- [x] 过量通配符的 `component` 被拒绝：`ShieldRoleServiceImplTest#testGetshieldRleHitNum_InvalidComponent_Rejected`（`?a?a?...` 抛 `ScaException`）
- [x] 相邻通配符的 `component` 被拒绝（`testGetshieldRleHitNum_AdjacentWildcards_Rejected`）
- [x] 构造回溯模式的请求无法造成 CPU 飙升：匹配改为 O(pattern×text) DP，通配符上限 ≤ 10（`testMatchesShieldPattern_PolynomialPatternStaysLinear` 以 10 通配符 × 800 字符验证即时返回）
- [x] 匹配语义与旧实现一致（`testMatchesShieldPattern_BasicSemantics`）
- [x] 相关单元测试已补充
- [ ] 单测运行结果与覆盖率：本轮为回溯补写，未执行 `mvn test`、未核对 JaCoCo（未验证）
- [ ] 真实请求级压测（构造高量级 component 观察 CPU）：未执行（未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `ShieldRoleServiceImpl#getshieldRleHitNum`
- 接口 / 契约：`/shield/role/get/shield/hit/number` 参数与响应结构不变；新增 `40052` 拒绝分支（仅当聚合结果非空时触发校验，见 design 风险表）
- 配置 / schema：无变化
- 权限：本接口的 `verifyCommunityPermission(userId, projectId)` 由 #145 引入，见兄弟目录 `shield-role-api-authz`
