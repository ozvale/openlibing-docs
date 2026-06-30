# engineering-capability-dashboard

## 需求背景

OpenLibing 平台当前已有 `open-source-project`（开源项目看板）、`test-dashboard`（测试看板）、`pr-access`、`version-pipeline` 等 dashboard 子页面，但缺少一个**横向聚合各开源组件工程能力建设情况**的运营视图。

运营与工程团队需要一个统一入口，快速回答：

- 各开源组件（MindIE/PTA/openEuler/openGauss/MindSpore）的本地编码、本地构建、PR 流水线、资源消耗、Nightly 流水线能力是否达标？
- 哪些组件存在能力缺口（如编码风格未配置、pre-commit 缺失、规则数为 0）？
- PR/Nightly 流水线的 CPU/NPU 资源消耗趋势如何？是否有浪费？

设计稿 `docs/开源组件运营总览-16.html` 已给出完整交互方案（三级表头 + 下钻面板 + 多 Modal + 分页），本期按设计稿 1:1 还原。

## 功能描述

### 做什么

在 `src/views/dashboard/engineering-capability/` 下新增「工程能力运营看板」页面，包含：

1. **工具栏**
   - 数据时间段筛选：参照 `test-dashboard` 的 `time-range-selector.vue`，提供「今日 / 近7天 / 近30天 / 近90天」快捷选项按钮 + `el-date-picker`（daterange）自定义选择，快捷选项与日期选择器联动（选快捷选项自动填充日期，手动改日期则切换为 custom 态）
   - 列设置：复用仓库公共组件 `column-setting`（树形 + 多级表头 + localStorage 持久化），控制 6 大分组列（整体TTFHW / 本地编码 / 本地构建 / PR流水线 / 资源环境 / Nightly流水线）的显隐
   - 开源组件多选下拉：5 个组件（MindIE/PTA/openEuler/openGauss/MindSpore）+ 全选/全不选

2. **主表（三级表头，36 列）**
   - 第一级分组：开源组件 / 整体TTFHW / 本地编码(colspan=3) / 本地构建(colspan=3) / PR流水线(colspan=4) / 资源环境(colspan=24) / Nightly流水线(colspan=2)
   - 资源环境第二级：PR流水线资源(colspan=8) / Nightly流水线资源(colspan=8) / 流水线整体资源(colspan=8)
   - 每组资源第三级：CPU消耗 / CPU平均消耗 / CPU总量 / CPU使用率 / NPU消耗 / NPU平均消耗 / NPU总量 / NPU使用率
   - 单元格：数值展示 + hover tooltip 明细 + 点击下钻

3. **右侧滑出下钻面板**（3 Tab）
   - **代码仓 Tab**：6 个仓库配置 KPI 卡片（编码风格可视/代码检查/规则数/自动修复/例外备案/PR时长）+ 代码仓明细表（7 列，含状态徽章✓/✗、规则数、PR时长）+ 列设置 + 分页
   - **资源环境 Tab**：6 个 KPI 卡片（CPU消耗/CPU平均/CPU总量/NPU消耗/NPU平均/NPU总量）+ 流水线资源表（流水线名称/类型/CPU消耗/CPU平均/NPU消耗/NPU平均）+ 分页
   - **Nightly Tab**：2 个 KPI 卡片（编译成功率/版本可用度）+ Nightly 流水线表（流水线/编译成功率/可用度）+ 分页

4. **Modal**
   - 代码仓分支配置：展示组件下各代码仓的分支列表，支持勾选切换，**保存时调用接口**（mock 拦截）持久化分支配置
   - 链接配置：为指定列配置跳转数值和链接地址，**保存时调用接口**（mock 拦截）持久化链接配置
   - 流水线运行记录：点击资源表行展示该流水线的运行记录（编号/启动时间/状态/CPU/NPU）+ 分页

5. **交互**
   - 点击主表数据单元格 → 打开下钻面板，根据列类型自动切换 Tab（资源列→资源环境 Tab，Nightly列→Nightly Tab，其他→代码仓 Tab），高亮主表行+列头，高亮面板对应列
   - 点击组件名单元格 → 打开面板，默认代码仓 Tab
   - Tab 切换、分页翻页、列设置联动

### 不做什么

- **不对接真实后端 API**：本期用 mock 数据完整还原交互（用户确认）。mock 数据放在仓库根目录 `mock/` 文件夹，通过 `vite-plugin-mock` 拦截 HTTP 请求；API 函数走真实 `http` 调用，后端就绪后删除 mock 文件即可切换。
- **链接配置 / 分支配置 Modal 调接口**：保存配置时调用 mock 拦截的接口持久化（localStorage 兜底），非纯 UI。
- **不实现设计稿中的「导出」功能**（设计稿未明确，本期略过）。
- **不接入 ECharts 趋势图**：设计稿主视图是表格，下钻面板无趋势图，本期不引入图表。

## 验收标准

- [ ] 路由 `/dashboard/engineering-capability` 可访问，页面标题「工程能力运营看板」
- [ ] 工具栏：时间段快捷选项（今日/近7天/近30天/近90天）与 `el-date-picker` 联动、列设置（6 分组显隐）、组件多选（含全选/全不选）均生效并联动主表
- [ ] 主表三级表头结构、36 列布局、sticky 首列与设计稿一致
- [ ] 主表单元格 hover 显示 tooltip 明细；点击单元格触发下钻面板并自动切换 Tab
- [ ] 下钻面板 3 Tab 内容完整：KPI 卡片数值正确、明细表渲染、分页可翻
- [ ] 下钻面板列高亮、主表行/列头高亮逻辑与设计稿一致
- [ ] 分支配置 Modal 打开调接口加载、保存调接口持久化；链接配置 Modal 同理
- [ ] 流水线运行记录 Modal 可打开/关闭，含分页
- [ ] mock 数据覆盖 5 个组件，每组件含 ≥3 个代码仓、资源数据、Nightly 数据
- [ ] Vitest 单元测试覆盖纯逻辑：列配置结构、mock 数据结构、状态徽章渲染、数据转换、colKey→Tab 映射、timeRange/dateRange 联动
- [ ] Playwright E2E 覆盖关键交互：页面加载、时间段快捷选项、组件筛选、主表点击下钻、Tab 切换、分页翻页、Modal 保存
- [ ] `npm run type-check` 通过
- [ ] `npm run lint` 通过
- [ ] `npm run test:unit` 通过
- [ ] 遵循仓库规范：TS 强制无 any、kebab-case 文件名、组件 ≤400 行、样式去重、API `getXxxList` 命名

## 影响范围

### 业务仓 `openlibing-ops-web`

| 文件                                                                            | 操作 | 说明                                                   |
| ------------------------------------------------------------------------------- | ---- | ------------------------------------------------------ |
| `src/views/dashboard/engineering-capability/engineering-capability-view.vue`    | 新增 | 页面主入口                                             |
| `src/views/dashboard/engineering-capability/components/engineering-toolbar.vue` | 新增 | 工具栏（时间段+列设置+组件多选）                       |
| `src/views/dashboard/engineering-capability/components/main-table.vue`          | 新增 | 三级表头主表                                           |
| `src/views/dashboard/engineering-capability/components/detail-panel.vue`        | 新增 | 右侧滑出下钻面板                                       |
| `src/views/dashboard/engineering-capability/components/repo-tab.vue`            | 新增 | 代码仓 Tab                                             |
| `src/views/dashboard/engineering-capability/components/resource-tab.vue`        | 新增 | 资源环境 Tab                                           |
| `src/views/dashboard/engineering-capability/components/nightly-tab.vue`         | 新增 | Nightly Tab                                            |
| `src/views/dashboard/engineering-capability/components/branch-config-modal.vue` | 新增 | 分支配置 Modal                                         |
| `src/views/dashboard/engineering-capability/components/link-config-modal.vue`   | 新增 | 链接配置 Modal                                         |
| `src/views/dashboard/engineering-capability/components/runs-record-modal.vue`   | 新增 | 流水线运行记录 Modal                                   |
| `src/views/dashboard/engineering-capability/components/kpi-card.vue`            | 新增 | KPI 卡片通用组件                                       |
| `src/views/dashboard/engineering-capability/components/status-badge.vue`        | 新增 | 满足/不满足状态徽章                                    |
| `src/views/dashboard/engineering-capability/config/columns.ts`                  | 新增 | 主表列配置                                             |
| `src/views/dashboard/engineering-capability/config/detail-columns.ts`           | 新增 | 下钻表列配置                                           |
| `src/views/dashboard/engineering-capability/config/time-range.ts`               | 新增 | 时间段快捷选项配置 + TimeRange 类型                    |
| `src/views/dashboard/engineering-capability/style.less`                         | 新增 | 模块公共样式                                           |
| `src/views/dashboard/engineering-capability/__tests__/*.test.ts`                | 新增 | Vitest 单元测试                                        |
| `src/api/dashboard/engineering-capability.ts`                                   | 新增 | API 函数（走真实 http，由 mock 拦截）                  |
| `mock/engineering-capability.ts`                                                | 新增 | vite-plugin-mock 拦截 + mock 数据（新建 mock/ 文件夹） |
| `src/types/engineering-capability.ts`                                           | 新增 | TS 类型定义                                            |
| `src/router/routes/modules/dashboard.ts`                                        | 修改 | 新增路由                                               |
| `e2e/engineering-capability.spec.ts`                                            | 新增 | Playwright E2E                                         |

### 文档仓 `openlibing-docs`

| 文件                                                                               | 操作         |
| ---------------------------------------------------------------------------------- | ------------ |
| `spec/openlibing-ops-web/task_design/engineering-capability-dashboard/proposal.md` | 新增         |
| `spec/openlibing-ops-web/task_design/engineering-capability-dashboard/design.md`   | 新增         |
| `spec/openlibing-ops-web/task_design/engineering-capability-dashboard/tasks.md`    | 新增         |
| `spec/openlibing-ops-web/task_design/engineering-capability-dashboard/archive.md`  | Phase 5 归档 |

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-ops-web/issues/24
- 设计稿: `docs/开源组件运营总览-16.html`
- 技术栈: Vue 3.5 + TS 5.9 + Pinia 3 + Element Plus 2.13 + ECharts 6 + Vitest 4 + Playwright 1.60
