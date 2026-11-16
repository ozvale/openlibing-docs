# 116 — 实现任务

## 进度: 3/3 complete

- [x] Task 1: 抽取共享 pattern 校验 `validateShieldRolePattern`（长度 ≤ 256、通配符 ≤ 10）（`2f35a709`，本接口在下一步接入）
- [x] Task 2: `getshieldRleHitNum` 在匹配前校验 `component`，超限返回 `40052`；抽出 `isShieldRolePatternValid` 作为库存量守卫（`b6415fac`）
- [x] Task 3: 拒绝相邻通配符，`component` 匹配改为线性 DP `matchesShieldPattern`；补充 `testGetshieldRleHitNum_*` 与 DP 语义/复杂度用例（`3cfc6d1e`）

## 交付记录

| commit     | 日期       | 标题                                                                       | 关联                                     |
| ---------- | ---------- | -------------------------------------------------------------------------- | ---------------------------------------- |
| `2f35a709` | 2026-11-05 | fix(analysis): validate shield role pattern to prevent ReDoS               | Refs #117（提供共享校验函数）            |
| `b6415fac` | 2026-11-05 | fix(analysis): guard shield role match sites against legacy ReDoS patterns | Refs #115（本接口接入 `component` 校验） |
| `3cfc6d1e` | 2026-11-11 | fix(shield): match shield patterns via linear DP instead of regex          | Refs #115 #116 #117                      |

- 分支：`ms_scan`（`openlibing-sca`）
- 说明：三个 commit 均未在 message 中单列 #116，但 `3cfc6d1e` 的 Refs 含 #116，且本接口的 `component` 校验与 DP 替换分别落在 `b6415fac` / `3cfc6d1e`
- 验证方式（代码内证据）：
  - `ShieldRoleServiceImplTest#testGetshieldRleHitNum_InvalidComponent_Rejected`：`?a?a?a?a?a?a?a?a?a?a?a` 触发 `ScaException`
  - `#testGetshieldRleHitNum_AdjacentWildcards_Rejected`
  - `#testMatchesShieldPattern_PolynomialPatternStaysLinear`、`#testMatchesShieldPattern_BasicSemantics`
  - 本轮为回溯补写文档，未重新执行 `mvn test`（测试通过性未验证）；未做真实请求级 CPU 压测
