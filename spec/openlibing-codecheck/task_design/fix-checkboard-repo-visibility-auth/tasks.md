# fix-checkboard-repo-visibility-auth — 实现任务

## 进度: codecheck !381 已合入；**网关/前端透传为发布阻塞项**

> merge `be124821`，4 个提交；13 files，+871 / -290。
> **在未完成 Task 8–10 前，已登录用户访问私有仓看板/导出可能 4001（非单测覆盖范围）。**

### codecheck（!381）

- [x] Task 1: 新增 `CheckboardRepoAccessHelper`、`CheckboardRepoAccessService`
- [x] Task 2: `CheckboardDelegateImpl` 注入 Helper；趋势/详情数/任务详情等 assert*
- [x] Task 3: auth 方法委托 Helper，去除内联重复
- [x] Task 4: `CheckboardDelegate` + `CheckboardController` 增加 `userId` 入参
- [x] Task 5: `ExportDetailRequestDTO.userId`；`FileDownLoadController` / `ExcelReportImpl` 导出校验
- [x] Task 6: 新增 `CheckboardRepoAccessHelperTest`，更新 Delegate/Controller/Excel 单测
- [x] Task 7: 编译 + 单测通过

### 发布阻塞（须先于或同批宣称修复完成）

- [ ] Task 8: **openlibing-gateway** — 登录访问看板/导出白名单路由 JWT 注入 `userId`；免登录路由不转发客户端自填 `userId`
- [ ] Task 9: **openlibing-web** — 登录态看板/导出请求透传 `userId`
- [ ] Task 10: **联合冒烟** — 已登录私有仓 owner：统计/趋势/导出正常；匿名私有仓仍 4001（design.md 发布清单 4）

### 后续加固

- [ ] Task 11: query `userId` 为空时回退 `AuthUtils` 当前用户（或网关注入 Header），避免已登录误判匿名
- [ ] Task 12: 入参 `userId` 与 `AuthUtils` 一致性强校验 + 单测「伪造 userId」
- [ ] Task 13: **`isExternallyVisible` 统一**：用 `ProjectConstant.RepoVisibility.REPO_EXTERNAL`（及后续集中扩展）替代 `"public"` 字面量；全量/MR/导出匿名分支共用一个方法；`CheckboardRepoAccessHelperTest` / Delegate 单测覆盖双路径一致（§2.3）
