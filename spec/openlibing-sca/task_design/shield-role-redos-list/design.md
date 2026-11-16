# 115 — 技术设计

## 方案概述

三层收敛：

1. **入口**：`addRole` 校验 pattern 卫生（长度 ≤ 256、通配符 ≤ 10、禁止相邻通配符、非空），从源头阻断可持久化的高危规则；
2. **存量**：`getshieldRoleHitsNumber` 在编译前逐条过滤，超限规则跳过并 `warn`，不删除、不影响 `/list` 展示与 `/delete`；
3. **执行**：用线性 DP 匹配 `matchesShieldPattern` 取代 `wildCard2RegEx + Pattern.matches`，使匹配复杂度与通配符数量无关（O(pattern×text)），从机制上消除回溯型 ReDoS。

第 2、3 层不依赖入口校验是否生效，可独立兜住历史数据。

## 数据流（修复后）

```
POST /shield/role/add
  └─ addRole
       ├─ verifyCommunityPermission(userId, projectId)
       ├─ blank shieldRole / vendor → 40052
       ├─ trim
       ├─ validateShieldRolePattern：长度 ≤ 256、通配符 ≤ 10、无相邻通配符 → 否则 40052
       └─ insertShieldRole

GET /shield/role/list
  └─ selectRole
       ├─ 查 DB 规则 → 去重 → tblScans 非空则取最近 scanId
       └─ getshieldRoleHitsNumber(rolesNew, scanId)
            ├─ 查 Mongo：scanId = ? 且 blockStatus = BLOCK
            ├─ 过滤：isShieldRolePatternValid(role) 为 false → warn + skip
            └─ 每条 issue × 每条有效规则：
                  vendor 相等 且 matchesShieldPattern(role, component) → hitsNumber + 1
```

## 架构决策

| 决策                                                                               | 理由                                                                                                                           |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| D1 入口共享同一个 `validateShieldRolePattern`（`addRole` + `shieldRoleEffective`） | 两条写入口径一致；校验放在 `dealWithShieldRole` 的 `try-catch` 之前，`40052` 不会被统一 catch 吞成 500（`2f35a709`）           |
| D2 空值与相邻通配符前置拒绝                                                        | 原 `addRole` 直接 `getShieldRole().trim()` 会 NPE → 500；相邻通配符语义冗余（`**` 等价 `*`），拒绝可减少规则歧义（`3cfc6d1e`） |
| D3 存量守卫「跳过 + 告警」而非「拒绝查询」                                         | `/list` 是管理视图，必须能展示并删除脏规则；跳过只影响命中计数，不阻断接口（`b6415fac`）                                       |
| D4 守卫抽成 `isShieldRolePatternValid`（`public static`）                          | 入口校验与各匹配点复用同一判定；`3cfc6d1e` 让 DM 侧 `OpenScanDMServiceImpl#applyVendorShieldRule` 也复用，避免两套阈值漂移     |
| D5 DP 替换正则                                                                     | 旧实现 N 个通配符 = O(len^N) 回溯且无超时；DP 为 O(m×n)，通配符上限退化为入口卫生约束而非安全依赖（`3cfc6d1e`）                |
| D6 两行滚动数组实现 DP，`*` 取 `prev[j]                                            |                                                                                                                                | cur[j-1]`，`?`取`prev[j] |     | prev[j-1]`，字面字符取 `prev[j-1] && text[j-1]==c` | 空间 O(n)，与 `*`/`?` 语义一一对应；空文本分支单独处理零宽匹配 |
| D7 匹配点不再持有 `Pattern`，`java.util.regex.Pattern` 导入从实现类移除            | 消除残留的正则编译路径，避免后续误用                                                                                           |

## 涉及文件

| 文件                                                                                    | 操作 | 说明                                                                                                                                                                                                                                                                                         |
| --------------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/service/impl/ShieldRoleServiceImpl.java`     | 修改 | 新增 `MAX_SHIELD_ROLE_LENGTH=256`、`MAX_SHIELD_ROLE_WILDCARD_COUNT=10`（`2f35a709`）；`validateShieldRolePattern`、`isShieldRolePatternValid`、存量跳过（`b6415fac`）；`matchesShieldPattern`、`hasAdjacentWildcards`、空值校验、`isShieldRolePatternValid` 转 `public static`（`3cfc6d1e`） |
| `src/main/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImpl.java`           | 修改 | `applyVendorShieldRule` 改用 `ShieldRoleServiceImpl.matchesShieldPattern` 并加存量守卫；删除私有 `wildCard2RegEx` 副本（`3cfc6d1e`，同 commit 的第四匹配点）                                                                                                                                 |
| `src/test/java/com/openlibing/sca/analysis/service/impl/ShieldRoleServiceImplTest.java` | 修改 | 新增入口校验、存量跳过、DP 语义与线性复杂度用例                                                                                                                                                                                                                                              |
| `src/test/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImplTest.java`       | 修改 | 新增 `testApplyVendorShieldRule_Match_CaseInsensitive`、`_NoMatch`、`_SkipsInvalidLegacyPattern`（`3cfc6d1e`）                                                                                                                                                                               |

## 风险 & 缓解

| 风险                                                      | 缓解                                                                                       |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 存量非法规则被跳过后 `/list` 命中数偏低，用户误判屏蔽效果 | `warn` 日志带 `roleId`；规则仍可见、可删除，重建合规规则后计数恢复                         |
| `a.*` 等「字面元字符 + `*`」语义从绑定转义字符改为通配符  | 属修正方向（旧行为是转义顺序副作用）；`testMatchesShieldPattern_BasicSemantics` 固定新语义 |
| 相邻通配符拒绝影响历史调用方                              | 相邻通配符本身冗余，`40052` 文案明确原因                                                   |
| DP 对超长 component 单次匹配成本为 O(m×n)                 | m ≤ 256（入口上限），n 为库中 component 长度；线性且无回溯，成本远低于原 O(n^10)           |
| 存量脏规则未清理，长期占用匹配循环                        | 已跳过不参与匹配；清理脚本列入后续项                                                       |

## 跨仓影响

无。

## 关联 spec

- `shield-role-redos-hit-number`（#116）：同批 commit，`component` 直传入口
- `shield-role-redos-effective`（#117）：同批 commit，请求体 pattern 直传入口
- `shield-role-api-authz`（#145）：三个接口的 `verifyCommunityPermission` 鉴权改造
