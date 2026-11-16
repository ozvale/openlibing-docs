# 117 — 实现任务

## 进度: 3/3 complete

- [x] Task 1: 新增共享 `validateShieldRolePattern`（长度 ≤ 256、通配符 ≤ 10），在 `shieldRoleEffective` 调用 `dealWithShieldRole` 之前执行，保证 `40052` 不被 500 覆盖（`2f35a709`）
- [x] Task 2: 抽出 `isShieldRolePatternValid`，`dealWithRole` 对 DB 回落路径的存量规则跳过并 `warn`（`b6415fac`）
- [x] Task 3: 拒绝相邻通配符；`dealWithRole` 改用线性 DP `matchesShieldPattern`；补充 `testShieldRoleEffective_*`、`testDealWithRole_SkipsInvalidLegacyPattern` 等用例（`3cfc6d1e`）

## 交付记录

| commit     | 日期       | 标题                                                                       | 关联                                           |
| ---------- | ---------- | -------------------------------------------------------------------------- | ---------------------------------------------- |
| `2f35a709` | 2026-11-05 | fix(analysis): validate shield role pattern to prevent ReDoS               | Refs #117                                      |
| `b6415fac` | 2026-11-05 | fix(analysis): guard shield role match sites against legacy ReDoS patterns | Refs #115（守卫同时覆盖 `/effective` DB 路径） |
| `3cfc6d1e` | 2026-11-11 | fix(shield): match shield patterns via linear DP instead of regex          | Refs #115 #116 #117                            |

- 分支：`ms_scan`（`openlibing-sca`）
- 越权写验收项的实际落地点：`ddc3873a`（2026-11-09，feat(analysis): add community permission check to shield role APIs）与 `c0ce1dfb`（2026-11-10，收窄 `project_cie` 角色），属 #145，详见兄弟目录 `shield-role-api-authz`
- 验证方式（代码内证据）：
  - `ShieldRoleServiceImplTest#testShieldRoleEffective_PatternTooLong_Rejected`：257 字符 pattern 抛 `ScaException`，断言未查询 scan、未 `updateMulti`
  - `#testShieldRoleEffective_TooManyWildcards_Rejected`：`?a?a?...`（11 个 `?`）被拒绝
  - `#testShieldRoleEffective_AdjacentWildcards_Rejected`
  - `#testDealWithRole_SkipsInvalidLegacyPattern`：合法规则 `spring-*` 命中 `spring-core`，非法规则被跳过
  - `#testMatchesShieldPattern_PolynomialPatternStaysLinear`
  - 本轮为回溯补写文档，未重新执行 `mvn test`（测试通过性未验证）；未核验控制器侧鉴权端到端用例
