# 实现任务清单：openlibing-web 功能下线预告组件

- **目标仓**：`openlibing/openlibing-web`
- **业务分支**：`feature/offline-component`
- **流程模式**：Standard
- **创建日期**：2026-08-24

## 实现步骤

### Step 1: 创建组件本体

- [x] 新建 `apps/web-openlibing/src/components/OfflineNotice.vue`
- [x] 实现 `<script setup lang="ts">` + Props 类型
- [x] 实现默认警示图标（内联 SVG，与 `NoPermissionPopover.vue` 风格一致）
- [x] 实现 `el-popover` + `#reference` slot 透传
- [x] 实现 popperOptions 自适应（复用 `NoPermissionPopover.vue` 模式）
- [x] 实现 scoped 样式（head + 可选 body）
- [x] 实现全局样式覆盖（`offline-notice-popper`）
- [x] 标题文案：`<featureName> 即将下线`，空值回退 `该功能 即将下线`
- [x] body 仅当 `description` 或 `link` 存在时渲染

### Step 2: 创建单元测试

- [x] 新建 `apps/web-openlibing/src/components/__tests__/OfflineNotice.spec.ts`
- [x] 用例 1：渲染 + aria-label
- [x] 用例 2：标题文案
- [x] 用例 3：空 featureName 回退
- [x] 用例 4：description 渲染
- [x] 用例 5：link 渲染 + linkText 覆盖
- [x] 用例 6：body 缺省
- [x] 用例 7：仅 link 无 description
- [x] 用例 8：默认 link 文案
- [x] 用例 9：自定义 iconColor
- [x] 用例 10：默认警示橙
- [x] 用例 11：iconSize 应用
- [x] 用例 12：#reference slot 覆盖

### Step 3: 验证

- [ ] `pnpm lint`（针对新增文件）—— 本地环境受限，留待 CI
- [ ] `pnpm check:type`（typecheck 通过）—— 本地环境受限，留待 CI
- [ ] `pnpm test:unit`（新增用例全部通过）—— 本地环境受限，留待 CI
- [x] IDE LSP 诊断：无 error / warning

### Step 4: 提交

- [ ] 业务仓 commit
- [ ] docs 仓 commit（spec 文档更新）
- [ ] 业务仓 PR（用户自测确认后）
- [ ] docs 仓 PR（业务 PR 合入后）

## 不在本轮范围

- 集中配置表（`src/constants/offline-notice.ts`）
- 后端接口下发
- "已读"持久化
- 内联横幅 / Tooltip / 首次弹窗等其他形式
- **下线时间展示、剩余天数计算、已下线状态切换**（已明确移除）
