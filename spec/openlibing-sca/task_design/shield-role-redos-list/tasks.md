# 115 — 实现任务

## 进度: 4/4 complete

- [x] Task 1: `ShieldRoleServiceImpl` 增加 `MAX_SHIELD_ROLE_LENGTH=256` / `MAX_SHIELD_ROLE_WILDCARD_COUNT=10` 与 `validateShieldRolePattern`，接入 `addRole`、`shieldRoleEffective`（`2f35a709`）
- [x] Task 2: 抽出 `isShieldRolePatternValid` 存量守卫；`getshieldRoleHitsNumber` 与 `dealWithRole` 跳过非法存量规则并 `warn`（`b6415fac`）
- [x] Task 3: 新增 `matchesShieldPattern` 线性 DP 替换 `wildCard2RegEx + Pattern.matches`；`addRole` 空值前置校验与相邻通配符拒绝；`isShieldRolePatternValid` 转 `public static` 供 DM 侧复用（`3cfc6d1e`）
- [x] Task 4: 单测补充（入口拒绝、存量跳过、DP 语义与线性复杂度、DM 侧规则应用）+ 交付 commit

## 交付记录

| commit     | 日期       | 标题                                                                       | 关联                |
| ---------- | ---------- | -------------------------------------------------------------------------- | ------------------- |
| `2f35a709` | 2026-11-05 | fix(analysis): validate shield role pattern to prevent ReDoS               | Refs #117           |
| `b6415fac` | 2026-11-05 | fix(analysis): guard shield role match sites against legacy ReDoS patterns | Refs #115           |
| `3cfc6d1e` | 2026-11-11 | fix(shield): match shield patterns via linear DP instead of regex          | Refs #115 #116 #117 |

- 分支：`ms_scan`（`openlibing-sca`）
- 三 commit 共用同一组改动面，本目录聚焦 `/shield/role/list`（`getshieldRoleHitsNumber`）入口与存量守卫；#116 / #117 的入口差异见兄弟目录
- 验证方式（代码内证据）：
  - `ShieldRoleServiceImplTest#testGetshieldRoleHitsNumber_SkipsInvalidLegacyPattern`：存量超限规则被跳过、合法规则命中计数为 1、非法规则计数保持 0
  - `#testMatchesShieldPattern_PolynomialPatternStaysLinear`：`*a*a*...`（10 通配符）× 800 字符不匹配文本即时返回 false
  - `#testMatchesShieldPattern_BasicSemantics`：`*` / `?` / 元字符 / 空串 / null 语义
  - `#testAddRole_PatternTooLong_Rejected`、`#testAddRole_TooManyWildcards_Rejected`、`#testAddRole_AdjacentWildcards_Rejected`、`#testAddRole_NullShieldRole_RejectedNotNpe`、`#testAddRole_NullVendor_RejectedNotNpe`
  - `OpenScanDMServiceImplTest#testApplyVendorShieldRule_*`（第四匹配点）
  - 本轮为回溯补写文档，未重新执行 `mvn test`（测试通过性未验证）
- 未覆盖：存量规则清理脚本/接口（issue 修复建议 3）
