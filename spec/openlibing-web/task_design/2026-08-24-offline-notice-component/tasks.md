# 实现任务清单：openlibing-web 功能下线预告组件

- **目标仓**：`openlibing/openlibing-web`
- **业务分支**：`feature/offline-component`
- **流程模式**：Standard
- **创建日期**：2026-08-24

## 实现步骤

### Step 1: 创建组件本体

- [ ] 新建 `apps/web-openlibing/src/components/OfflineNotice.vue`
- [ ] 实现 `<script setup lang="ts">` + Props 类型 `OfflineNoticeProps`
- [ ] 实现 `useNow` composable（内联，不单独抽文件，1 分钟刷新）
- [ ] 实现时间状态机：即将下线 / 今日下线 / 已下线
- [ ] 实现默认警示图标（内联 SVG，与 `NoPermissionPopover.vue` 风格一致）
- [ ] 实现 `el-popover` + `#reference` slot 透传
- [ ] 实现 popperOptions 自适应（复用 `NoPermissionPopover.vue` 模式）
- [ ] 实现 scoped 样式（head + body + link）
- [ ] 实现全局样式覆盖（`offline-notice-popper`）
- [ ] 空值保护：`offlineAt` 无效时组件不渲染

### Step 2: 创建单元测试

- [ ] 新建 `apps/web-openlibing/src/components/__tests__/OfflineNotice.spec.ts`
- [ ] 用例 1：渲染（有效 props → 图标 + aria-label）
- [ ] 用例 2：即将下线状态文案
- [ ] 用例 3：今日下线状态文案
- [ ] 用例 4：已下线状态文案与图标颜色
- [ ] 用例 5：空值/Invalid Date 保护
- [ ] 用例 6：description / link / linkText / placement / trigger / width 透传
- [ ] 用例 7：#reference slot 覆盖默认图标

### Step 3: 验证

- [ ] `pnpm lint`（针对新增文件）
- [ ] `pnpm check:type`（typecheck 通过）
- [ ] `pnpm test:unit`（新增用例全部通过）

### Step 4: 提交

- [ ] 业务仓 commit：`feat(components): add OfflineNotice component for feature deprecation notice`
- [ ] docs 仓 commit：`docs(spec/openlibing-web): add OfflineNotice proposal/design/tasks`
- [ ] 业务仓 PR（用户自测确认后）
- [ ] docs 仓 PR（业务 PR 合入后）

## 验证清单

- [ ] 组件在 dev 服务器下正常渲染
- [ ] hover/click 交互正常
- [ ] 三种状态文案正确
- [ ] 无 lint 错误
- [ ] typecheck 通过
- [ ] 单元测试全部通过

## 不在本轮范围

- 集中配置表（`src/constants/offline-notice.ts`）
- 后端接口下发
- "已读"持久化
- 内联横幅 / Tooltip / 首次弹窗等其他形式
