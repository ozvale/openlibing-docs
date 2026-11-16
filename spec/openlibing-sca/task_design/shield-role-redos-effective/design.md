# 117 — 技术设计

## 方案概述

`/shield/role/effective` 有两条规则来源：请求体直传（非空 `shieldRole` + `vendor` 时绕过 DB）与 DB 回落（请求体为空时读取 `tbl_shield_role`）。两条都必须受控：

1. **请求体路径**：入口 `validateShieldRolePattern` 前移到 `dealWithShieldRole` 的 try-catch 之外，超限直接 `40052`；
2. **DB 回落路径**：`dealWithRole` 逐条 `isShieldRolePatternValid` 过滤，脏规则跳过并 `warn`；
3. **匹配执行**：两条路径统一使用线性 DP `matchesShieldPattern`，消除正则回溯；
4. **权限**：`verifyCommunityPermission(userId, projectId)` 由 #145 引入（`ddc3873a`），本目录不重复实现。

## 数据流（修复后）

```
POST /shield/role/effective  (body: ShieldRolePo, userId)
  └─ shieldRoleEffective
       ├─ verifyCommunityPermission(userId, projectId)              // #145
       ├─ validateShieldRolePattern(shieldRolePo.shieldRole)        // 40052；位于 try-catch 之外
       └─ dealWithShieldRole
            ├─ shieldRole/vendor 均非空 → 单条规则（请求体）
            │  否则 → shieldRoleMapper.selectByComAndRepo(...)（DB 路径）
            ├─ platform 过滤 → scanIds（最近一次 person scan / version scan）
            └─ effectiveRole
                 ├─ Mongo: scanId in scanIds
                 ├─ dealWithRole：逐条规则 isShieldRolePatternValid
                 │     ├─ 非法 → warn + skip
                 │     └─ 合法 → vendor 分组 → matchesShieldPattern(role, component)
                 │          命中 → blockStatus=BLOCK、shieldRole=role
                 └─ 对命中 issue updateMulti(objectId, blockStatus/shieldRole)
```

## 架构决策

| 决策                                                | 理由                                                                                                                                                           |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 校验前移到 `dealWithShieldRole` 之外             | `dealWithShieldRole` 内含 `catch (Exception)` → `ScaException(500)`，若把校验放在内部，`40052` 会被改写为 500，接口无法区分非法输入（`2f35a709` 的明确设计点） |
| D2 请求体为空仍允许走 DB 路径，但 DB 规则必须过守卫 | 「不传规则则按社区/仓库生效全部规则」是既有业务语义；守卫保证历史脏规则不参与匹配（`b6415fac`）                                                                |
| D3 相邻通配符在入口拒绝                             | `**` / `?*` 等冗余写法会放大表达式面；拒绝成本低（`3cfc6d1e`）                                                                                                 |
| D4 匹配改为线性 DP                                  | 旧实现下 10 个通配符的规则对失配组件是 O(len^10) 回溯，且该接口会对该社区全部 issue 逐个匹配；DP 为 O(m×n)                                                     |
| D5 不做「命中即中止后续规则」的短路                 | 保持原语义：多条规则命中时后写覆盖前写，`shieldRole` 记录最后命中的规则                                                                                        |
| D6 权限修复独立于本目录                             | #145 统一给 8 个 shield 端点加社区权限校验，避免与 ReDoS 修复混杂，便于单独评审与回滚                                                                          |

## 涉及文件

| 文件                                                                                    | 操作 | 说明                                                                                                                                                                                                                                     |
| --------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/service/impl/ShieldRoleServiceImpl.java`     | 修改 | `shieldRoleEffective` 增加 `validateShieldRolePattern`（`2f35a709`）、`verifyCommunityPermission`（`ddc3873a`）；`dealWithRole` 存量守卫（`b6415fac`）与 DP 匹配（`3cfc6d1e`）；`validateShieldRolePattern` 增加相邻通配符（`3cfc6d1e`） |
| `src/main/java/com/openlibing/sca/analysis/controller/ShieldRoleController.java`        | 修改 | `/effective` 增加 `userId` 请求参数并透传（`ddc3873a`，属 #145 面）                                                                                                                                                                      |
| `src/test/java/com/openlibing/sca/analysis/service/impl/ShieldRoleServiceImplTest.java` | 修改 | `testShieldRoleEffective_PatternTooLong_Rejected`、`_TooManyWildcards_Rejected`、`_AdjacentWildcards_Rejected`、`testDealWithRole_SkipsInvalidLegacyPattern`                                                                             |
| `src/main/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImpl.java`           | 修改 | 同 commit 收敛 DM 侧第四匹配点（扫描期应用供应商屏蔽规则），统一 DP 与守卫（`3cfc6d1e`）                                                                                                                                                 |

## 风险 & 缓解

| 风险                                                        | 缓解                                                                                                                                                 |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 请求体 pattern 合法但命中量极大，`updateMulti` 逐条执行耗时 | 与原逻辑一致，未引入新放大点；命中集合由 scanIds 限定为最近一次扫描                                                                                  |
| DB 存量脏规则被跳过后屏蔽结果与历史不一致                   | `warn` 日志记录 `roleId`；规则仍可在 `/list` 查看与删除，重建合规规则后重新生效                                                                      |
| 校验前移改变异常码（原可能返回 500）                        | 目标行为：非法输入返回 `40052` 与明确文案；`DataAccessException` 仍映射 500                                                                          |
| 权限校验依赖 `projectId`，请求缺失时行为                    | #145 将 `projectId` 纳入校验入参（`ShieldRoleVO` / `ShieldRolePo` 已有该字段），缺失时按无权限处理（细节见 `shield-role-api-authz`，本轮未逐行核实） |
| 语义边界：`a.*` 从「绑定转义字符」变为通配符                | 属修正方向，`testMatchesShieldPattern_BasicSemantics` 固定新语义                                                                                     |

## 跨仓影响

无。

## 关联 spec

- `shield-role-redos-list`（#115）：`/list` 命中统计与存量守卫
- `shield-role-redos-hit-number`（#116）：`component` 直传入口
- `shield-role-api-authz`（#145）：社区权限校验（本 issue 越权写验收项的实际落地点）
