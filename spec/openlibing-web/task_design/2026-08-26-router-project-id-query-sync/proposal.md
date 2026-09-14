# 2026-08-26 路由 query 项目参数同步提案

## 1. 需求背景

平台页面 URL 此前不携带项目上下文，导致三类问题：

- **刷新丢上下文**：落地页刷新后 URL 无项目参数，项目还原依赖 store 记忆，无法通过 URL 恢复
- **分享链接不完整**：转发给他人时对方看到的可能是默认项目
- **历史页签错乱**：页签（tag）持久化保存的是含 query 的完整地址，切换项目后点击旧页签会按旧项目加载页面

### 需求演进（含迭代调整）

1. **初版需求**：store 中 `app.projectInfo.projectId` 或 `projectName` 存在且 route query 未携带时补写参数，二选一（projectId 优先）
2. **迭代 1**：刷新落地页丢参——`ProjectSelect` 异步加载完 projectInfo 后不发生路由跳转，路由守卫无执行时机 → watch 在 projectInfo 就绪后立即补写
3. **迭代 2**：点击历史保存的页签会带旧项目参数 → 守卫增加与 `projectInfo` 的比对，不一致时改写
4. **最终收敛**：按用户要求移除全部 projectName 写入逻辑，**query 统一只写 projectId**，并清除遗留的 projectName

## 2. 验收标准

### 功能验收

- [x] 路由跳转时 query 未携带 projectId → 守卫补写当前项目 projectId
- [x] 刷新落地页（URL 无参数）→ projectInfo 初始化完成后立即补写，无需路由跳转
- [x] 点击历史页签（含旧 projectId）→ URL 改写为当前项目，页面按当前项目加载，页签地址自愈更新
- [x] query 携带 projectName（历史分享链接）→ 初始化时项目还原不受影响，还原后 URL 转为 projectId 风格
- [x] store 无项目信息（初始化中/登出）→ 守卫不介入，保证分享链接参数原样到达 `getProject`
- [x] query 上只写 projectId，不写 projectName，遗留 projectName 被清除

### 代码质量验收

- [x] ESLint 无告警（guard.ts / app.ts）
- [x] `vue-tsc --build --force` 类型检查通过
- [x] query-only 变更不触发视图重载（组件 key 不含 query，KeepAlive 复用）

## 3. 变更范围

### 涉及模块

- **路由守卫**: `apps/web-openlibing/src/router/guard.ts` — `setProjectQueryGuard` 补写/改写 projectId
- **Store**: `apps/web-openlibing/src/stores/app.ts` — projectInfo 就绪/变化时同步 query 的 watch
- **初始化**: `apps/web-openlibing/src/views/Content.vue` — `getProject` 统一写 `app.projectInfo`，保证 watch 立即触发时与当前路由一致

### 变更类型

- 新功能（URL 项目上下文补写与同步）

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 全局路由导航与 URL query；不涉及后端接口变更
- **破坏性变更**: 无（外部链接携带的 projectName/projectId 还原逻辑保留）
- **已知行为**（符合需求设定）：
  - wujie 子应用启动 URL 会带上 projectId（子应用不重载，仅启动参数可见）
  - 无法解析的分享链接（查不到项目）会回退默认项目 `{projectId: 3}` 并同步到 URL

## 5. 关联信息

- **分支**: `jzcfork/202608projectfilter`
- **Commits**: `942db718`（feat 初版）、`f2e85bf0`（fix 收敛为 projectId）
- **标签**: ai-assisted
