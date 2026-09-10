# 软件成分数据页「漏洞刷新」功能 — 实现任务

## 进度: 19/19 complete

### openlibing-sbom（主仓，分支 feat-sbom-vul-refresh）

- [x] `SbomConstants` 新增 `TASK_STATUS_VUL_REFRESHING = "VUL_REFRESHING"`
- [x] 新增策略框架：`RefreshType` / `RefreshContext` / `SbomRefreshStrategy` / `SbomRefreshStrategyFactory`
- [x] 新增 `SbomRefreshExecutorConfig`（专用线程池：core=2/max=4/queue=64/AbortPolicy）
- [x] `ExternalVulRefRepository` 新增 `deleteBySbomId(UUID)`
- [x] 新增 `VulRefreshStrategy`（UVP 分批拉取 → REQUIRES_NEW 删旧写新 → 重算 package_statistics 漏洞字段）
- [x] 新增 `SbomRefreshService`（FINISH 校验 / 去重锁 / 状态占用 / 线程池提交 / finally 恢复 / RejectedExecutionException → BUSY）
- [x] `SbomService` / `SbomServiceImpl` 新增 `refreshSbom` 委托；`SbomController` 新增 `POST /refresh`（@LogApi）
- [x] 新增启动恢复 ApplicationRunner（遗留 VUL_REFRESHING 复位 FINISH）
- [x] 单测：`SbomRefreshServiceTest`（校验/去重/状态占用恢复/线程池拒绝/启动恢复）
- [x] 单测：`VulRefreshStrategyTest`（needRequest 跳过/删旧写新/拉取失败旧数据保留/统计重算/空漏洞归 0/回滚）
- [x] 单测：`SbomControllerTest` 补 `/refresh` 用例
- [x] 后端编译 + 相关单测通过

### openlibing-web（跨仓，分支 feat-sbom-vul-refresh）

- [x] 移除"漏洞依赖刷新"按钮及其处理（后端接口保留）
- [x] `url.ts` / `api.ts` 新增 `REFRESH_SBOM_URL` / `refreshSbom`
- [x] 新增"漏洞刷新"按钮：占位全量导出左侧、NoPermissionPopover(refreshDependency) 权限、QuestionFilled 问号 el-tooltip、ElMessageBox.confirm 二次确认
- [x] 解析状态轮询联动（{FINISH, FAILED_FINISH} 完成态集合，5s 轮询，非完成态按钮 disabled+loading，onUnmounted 清理）
- [x] 完成态通知（ElNotification：经历过 VUL_REFRESHING 到 FINISH 弹"漏洞已刷新完成，请刷新页面"；到 FAILED_FINISH 弹差异化 warning；普通解析完成不弹）
- [x] `scanStatusMap` 补 `VUL_REFRESHING: { label: '漏洞信息刷新中', type: 'warning' }`

### 收尾

- [x] 两仓 pre-commit 全部改动文件通过

## 关联

- 业务 Issue：openlibing/openlibing-sbom#74（https://gitcode.com/openlibing/openlibing-sbom/issues/74）
- 业务分支：`feat-sbom-vul-refresh`（两仓）
