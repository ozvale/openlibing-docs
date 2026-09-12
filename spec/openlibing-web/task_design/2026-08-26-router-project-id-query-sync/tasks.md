# 2026-08-26 路由 query 项目参数同步 - 任务清单

## 实现步骤

- [x] guard.ts 新增 `setProjectQueryGuard`：query 缺 projectId 时补写（初版 projectId/projectName 二选一）
- [x] app.ts 新增 projectInfo 变化同步 query 的 watch（初版）
- [x] Content.vue `getProject` 统一写 `app.projectInfo`，避免初始化后 URL 被 watch 二次改写
- [x] 迭代 1：修复刷新落地页丢参——移除 watch 中「query 未带参数直接返回」分支，projectInfo 就绪即补写
- [x] 迭代 2：守卫增加与 `projectInfo` 比对——历史页签携带旧项目参数时改写为当前项目，页签地址自愈
- [x] 迭代 3：移除全部 projectName 写入逻辑，query 统一只写 projectId 并清除遗留 projectName；watch 监听源简化为单一 projectId
- [x] ESLint 验证通过（guard.ts / app.ts）
- [x] `vue-tsc --build --force` 类型检查通过
- [x] 提交并推送（commits: `942db718`、`f2e85bf0`，分支 `jzcfork/202608projectfilter`）
- [ ] 创建业务 PR（跨仓 `--head` fork 分支）并打 `ai-assisted` 标签
- [ ] 关联业务 Issue
- [ ] 归档 archive.md（Phase 5 用户触发后）
