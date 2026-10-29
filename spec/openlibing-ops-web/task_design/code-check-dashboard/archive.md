# 代码检查运营看板 — 归档

## 关联

- 业务 Issue: <https://gitcode.com/openlibing/openlibing-ops-web/issues/33>
- 业务 PR: <https://gitcode.com/openlibing/openlibing-ops-web/pull/100>（`20260731` → `release_20260730_iter2`，已 merged）
- 业务 PR commit 范围：`187adf3..64848cb`（含 `feat-code-check-dashboard` 主线 14 个 + 用户在 `beta_new` 路径上的 2 个修复 `6d77e09` / `15b21d1`）
- 业务 Issue 状态：交付完成（PR #100 已合并到 `release_20260730_iter2`）
- docs 仓归档分支：`spec-openlibing-ops-web-code-check-dashboard-update`
- docs PR: <https://gitcode.com/openlibing/openlibing-docs/merge_requests/716>

## 交付历程

业务仓侧（按时间顺序）：

- commit [`187adf3`](https://gitcode.com/openlibing/openlibing-ops-web/commit/187adf3): `feat(code-check)` 脚手架：dashboard + KPI 卡片 + 明细表
- commit [`bb8ec57`](https://gitcode.com/openlibing/openlibing-ops-web/commit/bb8ec57): `feat(code-check)` 新增 5 个图表：增长趋势 / Top 排行 / 严重度
- commit [`8ea4a59`](https://gitcode.com/openlibing/openlibing-ops-web/commit/8ea4a59): `test(code-check)` api / columns / utils / dashboard e2e 单测
- commit [`adc6c3b`](https://gitcode.com/openlibing/openlibing-ops-web/commit/adc6c3b): `fix(code-check)` 改用语义 tag、修表格标题样式与图例颜色
- commit [`c15f27c`](https://gitcode.com/openlibing/openlibing-ops-web/commit/c15f27c): `fix(code-check)` 对齐 KPI 图标颜色与设计稿
- commit [`9c3970a`](https://gitcode.com/openlibing/openlibing-ops-web/commit/9c3970a): `feat(code-check)` 按 design-final 契约接入真实后端 API
- commit [`44b582f`](https://gitcode.com/openlibing/openlibing-ops-web/commit/44b582f): `fix(code-check)` 简化 toolbar + null-safe 展示
- commit [`8f5a880`](https://gitcode.com/openlibing/openlibing-ops-web/commit/8f5a880): `refactor(code-check)` 仓库筛选切到多选 + 移除 project options API
- commit [`4afb329`](https://gitcode.com/openlibing/openlibing-ops-web/commit/4afb329): `refactor(code-check)` 提取共享样式、调色板、格式器
- commit [`f0e2229`](https://gitcode.com/openlibing/openlibing-ops-web/commit/f0e2229): `refactor(code-check)` `formatFloat` 上提到 `@/utils/format-value.ts` 共享
- commit [`a27d0ac`](https://gitcode.com/openlibing/openlibing-ops-web/commit/a27d0ac): `refactor(code-check)` `EMPTY_VALUE` 统一到 `@/constants` + 删除 4 个透传 slot + ECharts 6 grid 迁移
- commit [`f6042d3`](https://gitcode.com/openlibing/openlibing-ops-web/commit/f6042d3): `refactor(code-check)` 顶部"按代码仓搜索"迁移到明细表表头列筛选
- commit [`7549ae5`](https://gitcode.com/openlibing/openlibing-ops-web/commit/7549ae5): `refactor(code-check)` SeverityRoseChart props 统一为 `data`
- commit [`6d77e09`](https://gitcode.com/openlibing/openlibing-ops-web/commit/6d77e09): `fix` 修改请求参数（用户在 `beta_new` 路径上）
- commit [`15b21d1`](https://gitcode.com/openlibing/openlibing-ops-web/commit/15b21d1): `fix` 问题修改（用户在 `beta_new` 路径上）
- commit [`64848cb`](https://gitcode.com/openlibing/openlibing-ops-web/commit/64848cb): `refactor(code-check)` 文案精简 + top-branch 柱图排序修复 + 列筛选 `filterKey: 'repoIds'`

变更规模：见各 commit（净增约 1500 行 / 业务代码 13 个 .vue + 1 个 .ts + 1 个 .less + 4 个测试文件）。

docs 仓侧：

- commit [`ccd8565`](https://gitcode.com/openlibing/openlibing-docs/commit/ccd8565): `docs(spec-openlibing-ops-web)` 把代码差异回写到 proposal.md / design.md / tasks.md

## 用户自测反馈

- 期间用户未提出功能性反馈，所有 commit 一次性通过 CI。
- 用户主动调整 3 处：① `dashboard-toolbar` 改 `defineModel` 风格；② `columns.ts` 加 `filterKey: 'repoIds'`；③ 多处标题/描述文案精简 + top-branch 柱图排序修复。AI 已跟随并补 commit。

## 最终验证

最近 commit `64848cb` 验证记录（code-check 范围）：

- `npm run type-check`：0 错误（仓库其他模块的 11 处预存错误与本任务无关）
- `npm run lint:es` / `npm run lint:style`：全绿
- `npm run test:unit -- src/views/dashboard/code-check`：3 files / 15 tests 通过
- husky pre-commit：prettier + eslint + stylelint + commitlint 全绿

业务 PR #100 流水线：用户已确认合入到 `release_20260730_iter2`。

## 设计偏差与取舍

1. **范围扩展：mock → 真实 API**：原 proposal 写"本次用 mock 数据"，实际实现直接接 `getCommonDetail` / `getTrend` / `getKpiSummary` / `getRepoList`。后端契约在开发过程中先行确定，前端跳过 mock 阶段节省成本。已通过 `9c3970a` 单 commit 切换。
2. **顶部"按代码仓搜索"控件迁移**：原 proposal 含 el-select 全局搜索。实现中发现：① 与明细表语义重复；② 不符合 sub-table 的"列筛选"范式。改为明细表表头多选（`f6042d3`），并以 `filterKey: 'repoIds'` 提交到后端，对接口契约零侵入。
3. **导出按钮移除**：原设计稿含导出按钮，但本期交付范围不包含；保留后续迭代。
4. **SeverityRoseChart props 收敛**：原方案 `{ loading, buckets, total }` 出现"传 buckets 不传 total"或反之的不一致风险。简化为 `{ loading, data }` + 内部 `total = data.reduce(...)`，避免外部传错（`7549ae5`）。
5. **ECharts 6 `containLabel` 弃用**：原代码用 `containLabel: true`，ECharts 6 已替换为 `outerBoundsMode: 'same'` + `outerBoundsContain: 'axisLabel'`，迁移在 `a27d0ac` 完成。
6. **共享工具上提**：`formatFloat` 与 `EMPTY_VALUE` 原本在各模块内重复。code-check 模块先收敛（`f0e2229` / `a27d0ac`），后续若有其它模块复用，可继续上提到 `@/utils` / `@/constants` 共享层。

## 可复用经验

- **`getCommonDetail` 通用路由接口**：业务仓有 `getCommonDetail<T, U>(data)` 入口，按 `data.category` 字段路由到后端不同 handler。本期在 code-check 大量复用（`codeCheckKpi` / `codeCheckTrend` / `codeCheckRepo`），前端按分区定义独立 TS 类型 + 单一入口调用，**避免每个分区单独写接口函数**。后续同类"运营看板"需求可参考。
- **`base-table` 表头列筛选范式**：当一个列表有"按 XXX 筛选"需求时，**优先用 base-column 的 `filterable: true / filterType: 'multipleSelect' / filterKey: 'xxx'`**，组件挂载时调 `tableRef.value?.updateFilterList('xxx', list)` 注入候选。**不要**画蛇添足在父组件加 el-select 全局控件（参见 `open-source-project/sub-table.vue` 的成熟范式）。配合 `filterKey` 与后端参数名解耦，前端 UI 与接口契约通过 config 显式串联。
- **ECharts 6 grid 配置必填项**：`outerBoundsMode: 'same'` + `outerBoundsContain: 'axisLabel'` 是 ECharts 6 替代 `containLabel: true` 的等价配置；新代码必须用前者，老代码按升级时迁移。
- **`noUncheckedIndexedAccess` + 数组字面量索引**：项目 `tsconfig` 开启 `noUncheckedIndexedAccess` 后，**字面量联合类型索引访问**（如 `KPI_ICON_PALETTE[0 | 1 | 2 | 3]?.bg`）**仍被推断为 `T | undefined`**，必须保留 `?.` / `?? ''`。不要被 `paletteIdx: 0 | 1 | 2 | 3` 的字面类型迷惑。
- **`unplugin-auto-import` 范围**：项目 `unplugin-auto-import` 配置覆盖 `src/api/**` / `src/hooks/**` / `src/utils/**` 等，**但只注入到 `<script setup>` 块，template `{{ }}` 表达式不覆盖**。在 template 用 `formatFloat` / `to` 等必须显式 `import`（本期 `repo-detail-table.vue` 中 `formatFloat` 的 import 即为此例）。
- **type-check 必须用 `npm run type-check`**：项目封装 `vue-tsc --build`（增量 + 严格），不要直接 `npx vue-tsc --noEmit`（静默无输出 = 看似通过实则无检查）。同样的，`npm run lint:es` / `npm run lint:style` / `npm run test:unit` 都用 `package.json` 里的封装命令。

## 归档日期

2026-07-31
