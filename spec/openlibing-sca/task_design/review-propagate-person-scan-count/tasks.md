# Tasks: review-propagate-person-scan-count

- **业务 Issue**: openlibing/openlibing-sca#87（反馈轮次）
- **业务分支**: ms_succeed（业务仓）；spec-openlibing-sca-review-propagate-person-scan-count（docs 仓）

## T1 主代码（ConfirmReviewServceImpl）

- [x] T1.1 新增 `InheritScanScope` record（scanIds + personScanIds），scope 缓存类型升级
- [x] T1.2 `resolveInheritScanIds` → `resolveInheritScanScope` + `buildScanScope`（含 personScanIds 提取）
- [x] T1.3 `appendInheritScanPropagation` 命中继承文档时收集 personScanIds
- [x] T1.4 `updateIssueData` 在 `executeUpdate` 后调用 `refreshPersonScanUnConfirmedNum`（逐 scanId try/catch）
- [x] T1.5 `patchRevoke`/`propagateRevokeToInheritScans` 同步接入收集与刷新

## T2 单测（ConfirmReviewServceImplTest）

- [x] T2.1 批复传播用例：verify `uploadUnConfirmFileNum("pr-scan-1")`，verify 版本扫描 scanId 未被刷新
- [x] T2.2 撤回传播用例：verify 同上
- [x] T2.3 无传播目标用例：verify never 刷新
- [x] T2.4 新增刷新失败不阻断批复用例

## T3 验证

- [x] T3.1 `ConfirmReviewServceImplTest` 全量通过（含新增用例）
- [x] T3.2 compile + checkstyle + spotbugs + pmd 通过（pre-commit 全绿）
- [x] T3.3 commit（Refs #87，新 commit 不 amend）：`51bfbd6b`

## T4 交付（用户自测确认后）

- [ ] T4.1 业务 PR（ms_succeed，ai-assisted 标签，关联 #87）
- [ ] T4.2 docs PR（spec 三件套归档 openlibing-docs）
