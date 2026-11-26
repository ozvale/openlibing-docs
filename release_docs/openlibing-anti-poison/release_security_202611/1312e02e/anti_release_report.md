# openlibing-anti-poison release_security_202611 发布报告

- **发布分支**：release_security_202611
- **合入 commit**：1312e02e（!150 merge ldb_202611_2 into release_security_202611）
- **业务 PR**：openlibing/openlibing-anti-poison#150（ldb_202611_2 → release_security_202611，4 files，+120/−18；其中 nightly-schedule-scan.yml 来自主干 !148，本次变更实际为 3 files，+119/−13）
- **发布日期**：2026-11-26
- **提交规模**：5 commits（Richard-bean 5）+ 1 merge commit（openLiBingCI）

## 一、Issue 交付清单

| issueID | issue名称                                            | 责任人       | 评审结果 | 日期       |
| ------- | ---------------------------------------------------- | ------------ | -------- | ---------- |
| #79     | 【安全】修复 CVE-2026-53914 并按环境启用 MongoDB SSL | Richard-bean | 待验收   | 2026-11-26 |

注：#79 状态仍为 open，beta / gama / prod 环境部署验收项未勾选。同一变更已通过 !151 合入 master（merge commit 3534f48，2026-11-26）。

## 二、变更概要

### 1. 安全漏洞修复（对应 #79，CVE-2026-53914）

- 漏洞扫描发现 kotlin-stdlib-1.9.10.jar、kotlin-stdlib-common-1.9.10.jar 存在 CVE-2026-53914。
- kotlin-stdlib 删除显式版本 `1.9.10`，改由 openlibing-common BOM 管理（BOM 通过 kotlin-bom 导入，`kotlin.version` 为 2.4.20），依赖树中不再出现 kotlin 1.9.10 构件。

### 2. 缺陷修复

- `PoisonMongoConfig` 原先无条件启用 MongoDB SSL，beta 环境 MongoDB 不使用 SSL 导致无法连接。改为仅在激活 profile 包含 `prod` / `gama` 时启用 SSL，其他环境不启用。
- profile 判断按 `Environment.getActiveProfiles()` 的已激活列表进行，兼容多 profile（如 `prod,monitor`）及非 `spring.profiles.active` 属性激活的场景，避免 prod / gama 因字符串等值比较失败而误关 SSL。
- 新增 `PoisonMongoConfigTest`，通过 `MockEnvironment` 设置 `spring.profiles.active`，覆盖 beta / prod / gama / 未设置 profile / 多 profile 共 6 个用例。

### 3. 依赖与工程

- openlibing-common-sdk 1.0.21.5 → 1.0.21.6

## 三、验证记录

- `mvn dependency:tree` 与 `help:effective-pom` 确认 kotlin 系列构件均解析为 2.4.20。
- `PoisonMongoConfigTest` 6 个用例通过。
- 依赖升级后全量 1169 个单测通过，覆盖率门禁通过。
- 各提交 pre-commit（Spotless / Checkstyle / SpotBugs / PMD）全部通过。

## 四、待验收项

- [ ] beta 环境部署后可正常连接 MongoDB（不启用 SSL）
- [ ] gama / prod 环境部署后 MongoDB 正常连接（TLS-only，依赖代码启用 SSL）
- [ ] 重新执行漏洞扫描，确认 CVE-2026-53914 清零

## 五、提交清单（5 commits）

```text
79183a9 fix(mongo): detect SSL environments from active profiles
65a6769 fix(mongo): enable SSL only for prod and gama environments
e4e9655 build(deps): align kotlin-stdlib version with openlibing-common BOM
2fc77db build(deps): upgrade kotlin-stdlib to 2.4.20 to fix CVE-2026-53914
ca019ec build(deps): upgrade openlibing-common-sdk to 1.0.21.6
```
