# 116 — 技术设计

## 方案概述

`component` 是单次请求内即编译匹配的外部表达式，风险面与 `/list`（库中持久化规则）不同：不依赖写入口，因此修复必须落在「匹配前」而不是「写入时」。方案为「入口校验（复用共享规则）+ 线性 DP 匹配」：

1. `getshieldRleHitNum` 在拿到聚合结果后、进入双重循环前调用 `validateShieldRolePattern(component)`，超限直接 `40052`；
2. 匹配改为 `matchesShieldPattern(component, componentValue)`，通配符数量与匹配成本解耦。

## 数据流（修复后）

```
GET /shield/role/get/shield/hit/number?scanId=&vendor=&component=&userId=&projectId=
  └─ ShieldRoleController#getShieldRleHitNum
       └─ getshieldRleHitNum
            ├─ verifyCommunityPermission(userId, projectId)
            ├─ getNumberGroupVendorAndComponent(scanId)   // Mongo 聚合：blockStatus != BLOCK
            └─ 若聚合结果非空：
                 ├─ validateShieldRolePattern(component)
                 │     长度 ≤ 256、通配符 ≤ 10、无相邻通配符 → 否则 40052
                 └─ for issue in 聚合结果:
                        vendor.equalsIgnoreCase(issue.vendor)
                          && matchesShieldPattern(component, issue.component)
                        → num += Integer.parseInt(issue.count)
```

## 架构决策

| 决策                                                                       | 理由                                                                                                                                                       |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 校验放在 `component` 进入匹配循环之前，复用 `validateShieldRolePattern` | 与 `addRole` / `shieldRoleEffective` 同一阈值（256 / 10），避免多套口径；超限请求不产生任何匹配计算                                                        |
| D2 相邻通配符一并拒绝                                                      | `??`、`**` 在语义上冗余，拒绝可缩小表达式空间（`3cfc6d1e`）                                                                                                |
| D3 匹配用线性 DP 而非 `Pattern`                                            | 旧正则下 `component = ?a?a?...`（10 个 `?`）在失配文本上是 O(len^10) 回溯且无超时；DP 为 O(m×n)，与通配符数量无关                                          |
| D4 保留 `component` 为空的既有行为                                         | `@RequestParam(required = false)`；空值经 `isShieldRolePatternValid` 视为合法，`matchesShieldPattern` 对空 pattern 只在文本为空时返回 true，保持原匹配结果 |
| D5 不改计数与 vendor 匹配逻辑                                              | 只替换表达式实现，避免语义回归；聚合查询条件（`scanId in`、`blockStatus nin BLOCK`）未改动                                                                 |
| D6 不引入按输入长度切换算法的分支                                          | DP 已线性，额外分支只会增加两份语义；`m ≤ 256` 由入口上限保证                                                                                              |

## 涉及文件

| 文件                                                                                    | 操作 | 说明                                                                                                                                                                             |
| --------------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/service/impl/ShieldRoleServiceImpl.java`     | 修改 | `getshieldRleHitNum` 增加 `validateShieldRolePattern(component)`（`b6415fac`）；改为 `matchesShieldPattern`（`3cfc6d1e`）；相邻通配符校验由 `validateShieldRolePattern` 统一提供 |
| `src/test/java/com/openlibing/sca/analysis/service/impl/ShieldRoleServiceImplTest.java` | 修改 | 新增 `testGetshieldRleHitNum_InvalidComponent_Rejected`（`b6415fac`）、`testGetshieldRleHitNum_AdjacentWildcards_Rejected`（`3cfc6d1e`）、DP 语义与线性复杂度用例                |

## 风险 & 缓解

| 风险                                                                                                                   | 缓解                                                                                                       |
| ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 校验位于 `if (CollectionUtils.isNotEmpty(numberGroupVendorAndComponent))` 分支内：聚合结果为空时直接返回 0，不触发校验 | 该路径不编译任何表达式、无 ReDoS 面；返回 0 与原行为一致                                                   |
| 用户合法规则被上限（256 / 10）误伤                                                                                     | 上限对组件名匹配足够宽松；超限返回 `40052` 并带明确文案，可引导用户简化                                    |
| `component` 为空时行为变化                                                                                             | 空值视为合法且仅在文本为空时匹配，与原 `^$` 语义一致（`testMatchesShieldPattern_BasicSemantics` 覆盖空串） |
| `vendor` 为空时 `vendor.equalsIgnoreCase` 仍可能 NPE → 500                                                             | 本轮未改动，不属本 issue；如需要应另开缺陷处理                                                             |
| 单次请求仍需遍历聚合结果，成本随 issue 数量线性增长                                                                    | 与原逻辑同阶（原实现的隐患是指数回溯），未引入新的放大点                                                   |

## 跨仓影响

无。

## 关联 spec

- `shield-role-redos-list`（#115）：同一实现下的 `/list` 命中统计与存量守卫
- `shield-role-redos-effective`（#117）：同一实现下的 `/effective` 入口
- `shield-role-api-authz`（#145）：`verifyCommunityPermission` 鉴权改造
