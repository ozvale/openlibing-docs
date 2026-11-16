# #145 — 实现任务

## 进度: 3/3 complete

- [x] Task 1: 5 个 `/shield/role/*` 端点 + 3 个 `/scanoss/shield/*` 端点接入 `verifyCommunityPermission`；Controller 增加 `userId`（命中数端点加 `projectId`）与 403 分支；Service 签名扩展；`CommonServiceImpl` 文案改「权限不足」（`ddc3873a`）
- [x] Task 2: `UserRoleMapper.queryCommunityPermission` 去掉 `project_cie` 分支，仅 admin / platform_operater / 目标项目 project_manager 放行（`c0ce1dfb`）
- [x] Task 3: 适配/补充 4 个单测（含 403 用例）并交付 commit（`ddc3873a`、`c0ce1dfb`）

## 交付记录

| commit     | 日期       | 标题                                                                 | 关联 |
| ---------- | ---------- | -------------------------------------------------------------------- | ---- |
| `ddc3873a` | 2026-11-09 | feat(analysis): add community permission check to shield role APIs   | —    |
| `c0ce1dfb` | 2026-11-10 | fix(analysis): drop project_cie role from community permission check | —    |

- 分支：`ms_scan`（`openlibing-sca`）
- 说明：两个 commit message 未带 `Refs #145`；`ddc3873a` 描述为「8 个端点」，与 issue 主述的屏蔽规则写端点对应，并额外覆盖查询端点。
- 验证方式（代码内证据）：
  - `ShieldRoleControllerTest#testAddRoleNoPermission`、`#testDeleteRoleNoPermission`：Service 抛 `PermissionException` 时返回 code=403、message=「权限不足」
  - `ScanossShieldControllerTest#testAddScanossShieldNoPermission`：同理
  - `ShieldRoleServiceImplTest#testAddRole_NoPermission`：`verifyCommunityPermission("user1", null)` 抛 `PermissionException`
  - 代码位置：`ShieldRoleServiceImpl` L89 / L110 / L167 / L379 / L404；`ScanossShieldServiceImpl` L35 / L45 / L56
  - SQL：`UserRoleMapper.xml#queryCommunityPermission` 条件为 `role='admin' or (role='project_manager' and project_id=#{projectId} and perm_group_id=0) or role='platform_operater'`
  - 本轮为回溯补写文档，未执行 `mvn test`（测试通过性未验证）
- 未覆盖 / 遗留：
  - `/project/notice/scan/clear` 空 `productName` 仍触发 `deleteAll()`（权限已由 `449cc555` 单独加，空值拒绝未做）
  - `/version/scan/deleteByIds`、`/email/review/delete` 未接入权限
  - 统一 RBAC 注解/拦截器未落地
  - `userId` 来自请求参数，无验签/可信身份来源，"伪造超管凭证"验收项未闭环
