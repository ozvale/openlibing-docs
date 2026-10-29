# 2026-08-28 敏感词集操作页 URL 权限校验加固 - 任务清单

## 实现步骤

- [x] 梳理操作类型与权限码映射（add/copy/edit/query → `sensitive_rule_set_*`）
- [x] 新增 `OPTION_AUTH_MAP` 常量与 `authReady` 状态
- [x] 从 `@/api/api.ts` 导入 `getOperationPermissions`
- [x] watcher 初始化分支前置 `checkOptionAuth()` 校验
- [x] 实现 `doCheckOptionAuth`：store 优先、后端兜底、fail-closed
- [x] 实现 `fetchOperationPermission`：兼容两种返回结构（与 `Content.vue` 一致）
- [x] 实现 `parseOperationPermission`：跳过 repo 级角色组
- [x] watcher 项目切换分支接入 `recheckOptionAuth` 强制回源校验
- [x] 实现防竞态序号 `_authCheckSeq` 与重入保护 `_authChecking`
- [x] 实现 `denyAccess`：提示 + `setTimeout` 延迟跳转回 `/apps/sensitiveDict`
- [x] 自测：有权限项目正常访问操作页（openlibing）
- [x] 自测：URL 直入无权限操作页被拦截跳回列表页
- [x] 自测：切换到无权限项目（openubmc）自动拦截，跳转后列表页无空白
- [x] 提交 commit（`ecb41b98`）并推送 `fix-sensitiveCfg-url-auth` 分支
- [x] 创建业务 PR 并关联业务 Issue

## 验证记录

| 场景                      | 结果                                         |
| ------------------------- | -------------------------------------------- |
| 有权限项目 URL 直入操作页 | 正常初始化，功能可用                         |
| 无权限项目 URL 直入操作页 | 提示"无操作权限"，跳回列表页，内容区正常渲染 |
| 操作页内切换到无权限项目  | 提示"无操作权限"，跳回列表页                 |
| 操作页内切换到有权限项目  | 停留在操作页，权限按新项目生效               |
| config（查看）操作        | 行为不变，无操作级校验                       |
