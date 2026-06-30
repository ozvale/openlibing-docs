# engineering-capability-dashboard — 实现任务

## 进度: 0/12 complete

### Phase 3-A：数据层与类型（第 1 轮 commit）

- [ ] Task 1: 新增 `src/types/engineering-capability.ts`，定义 ComponentRow、RepoItem、ResourceMetrics、MetricStatus、ResourcePipelineRow、NightlyPipelineRow、RunsRecord、BranchConfigPayload、LinkConfigPayload、TimeRange 等类型
- [ ] Task 2: 新增 `src/api/dashboard/engineering-capability.ts`，定义 API 函数（getEngineeringCapabilityList、getComponentDetail、getRunsRecord、getBranchConfig、saveBranchConfig、getLinkConfig、saveLinkConfig），走真实 `http` 调用（由 mock 拦截）
- [ ] Task 3: 新增 `mock/engineering-capability.ts`（新建仓库根目录 `mock/` 文件夹），用 `vite-plugin-mock` 定义拦截规则 + 5 个组件完整 mock 数据 + 分支/链接配置 localStorage 持久化
- [ ] Task 4: 新增 `src/views/dashboard/engineering-capability/config/columns.ts`（主表三级表头列配置，`children` 嵌套）+ `config/time-range.ts`（TIME_RANGE_OPTIONS + TimeRange 类型，参照 test-dashboard）

### Phase 3-B：工具栏 + 主表（第 2 轮 commit）

- [ ] Task 5: 新增 `composables/use-engineering-capability.ts`（页面主状态 hook：timeRange/dateRange 联动、组件筛选、下钻面板开合、当前选中组件/列；列显隐由 `column-setting` 组件管理无需单独 hook，分页由 `base-table` 内置）
- [ ] Task 6: 新增 `components/engineering-toolbar.vue`（时间段快捷选项 + `el-date-picker` + `column-setting` 组件复用 + 组件多选）+ `components/status-badge.vue` + `components/kpi-card.vue`
- [ ] Task 7: 新增 `components/main-table.vue`（三级表头 + sticky 首列 + 单元格点击 + tooltip）+ `engineering-capability-view.vue` 页面入口 + 路由注册

### Phase 3-C：下钻面板（第 3 轮 commit）

- [ ] Task 8: 新增 `components/detail-panel.vue`（el-drawer + 3 Tab 容器 + 高亮逻辑）
- [ ] Task 9: 新增 `components/repo-tab.vue`（KPI 卡片 + 代码仓明细表 + 列设置，分页由 base-table 内置）+ `components/resource-tab.vue`（6 KPI + 资源表，分页由 base-table 内置）+ `components/nightly-tab.vue`（2 KPI + Nightly 表，分页由 base-table 内置）

### Phase 3-D：Modal + 样式（第 4 轮 commit）

- [ ] Task 10: 新增 `components/branch-config-modal.vue`（打开调 getBranchConfig，保存调 saveBranchConfig）+ `components/link-config-modal.vue`（打开调 getLinkConfig，保存调 saveLinkConfig）+ `components/runs-record-modal.vue` + `style.less` 模块公共样式

### Phase 3-E：测试（第 5 轮 commit）

- [ ] Task 11: 新增 Vitest 单元测试（columns、mock-data、status-badge、use-engineering-capability、time-range）+ 运行 `npm run test:unit` 通过
- [ ] Task 12: 新增 Playwright E2E `e2e/engineering-capability.spec.ts`（页面加载、时间段快捷选项、筛选、下钻、Tab 切换、分页、Modal 保存）+ 运行 `npm run test:e2e` 通过

### 验证清单（每轮 commit 前必跑）

- [ ] `npm run type-check` 通过
- [ ] `npm run lint` 通过（oxlint + eslint + stylelint）
- [ ] 改动文件数与行数符合预期，单 commit ≤1000 行
- [ ] commit message 符合规范（type(scope): summary + Refs #24 + Co-authored-by + Generated-by）
