# Proposal: 检测中心 - Sca 菜单列表定时扫描与取消定时扫描操作

## 需求背景

`openlibing-web` 检测中心（`InspectionCenter/index.vue`）的 Sca Tab 当前已支持：

- 单行操作：开始扫描、删除
- 批量操作：批量扫描、批量删除、定时扫描（原「批量定时扫描」）
- 列表筛选：仓库 / 分支 / 任务状态

实际运维场景中，用户希望对重点仓库+分支周期性发起 SCA 版本扫描（如每日凌晨、每周一），避免人工重复触发。当前已能开启定时扫描，但缺少「取消定时扫描」入口；同时仓库体积大于 100M 时禁止开启定时扫描（避免扫描耗时过长），且未开启状态与已开启状态需要互斥操作入口，故需结合 `isScheduled`（是否已开启）与 `isOversize`（仓库是否超量）双字段联合判定按钮可见性。

## 需求目标

在 Sca Tab 列表中提供「定时扫描」与「取消定时扫描」两类入口，并按仓库扫描状态互斥展示：

1. **批量操作区**：
   - 原「批量定时扫描」按钮文案调整为「定时扫描」（行为不变，仍批量开启定时扫描）。
   - 新增「取消定时扫描」按钮，对勾选记录中已开启（`isScheduled === 1`）的批量取消定时（`isScheduled: 0`），跳过未开启的行。
2. **列表操作列**：
   - 原「定时扫描」tooltip 文案调整为「开启定时扫描」（行为不变，仍单行开启定时扫描）。
   - 新增「取消定时扫描」入口，**仅在该行已开启定时扫描（`isScheduled === 1`）时出现**，与「开启定时扫描」互斥显示；`isScheduled !== 1 && isOversize === 1`（仓库>100M）时「开启定时扫描」按钮置灰禁用，tooltip 切为「仓库超过 100M，扫描耗时可能过长，禁止开启定时扫描」（不隐藏入口，让用户感知禁用原因）。
3. **状态判定字段**：通过列表接口返回的 `isScheduled` + `isOversize` 双数值字段联合判断：`isScheduled===1` 已开启可取消；`isScheduled!==1 && isOversize!==1` 可开启；`isScheduled!==1 && isOversize===1`（仓库>100M）按钮禁用 + 超量提示。

### 当前阶段范围（前端先行）

后端定时扫描 API 已提供（`POST /openlibing-sca/version/scan/batchUpdateScheduled`，入参 `ids` + `isScheduled` 0/1），前端已全量交付：

**已交付（开启定时扫描）**：

- 新增 UI 入口（按钮 / 操作列图标）
- API 端点常量与请求函数写入 `src/api/url.ts` 与 `src/api/api.ts`
- 批量与单行事件回调已接入 API 调用
- 调用成功后刷新列表，失败时弹出 error 提示

**本次扩展交付（取消定时扫描 + 文案调整 + 图标区分 + 提示语）**：

- 批量按钮文案「批量定时扫描」→「定时扫描」
- 列表操作列 tooltip「定时扫描」→「开启定时扫描」
- 批量操作区新增「取消定时扫描」按钮（warning 类型，始终展示）
- 列表操作列新增「取消定时扫描」入口（v-if `row.isScheduled === 1`，与「开启定时扫描」互斥；`row.isScheduled !== 1 && row.isOversize === 1` 时「开启定时扫描」按钮禁用 + tooltip 切为「仓库超过 100M，扫描耗时可能过长，禁止开启定时扫描」）
- 「开启定时扫描」/「取消定时扫描」改用**内联 SVG 图标**替换 `@element-plus/icons-vue` 的 `Timer` / `CircleClose`，批量按钮 + 列表操作列一致；SVG class 为 `.btn-icon`（批量按钮）/ `.row-icon`（列表操作列）尺寸样式（仅控制 width/height/margin），按钮本体 `.scan-btn` / `.cancel-btn` / 行级 `.disable-class` 仅作模板 class 标识（未在 CSS 中定义）；颜色靠 SVG `stroke="currentColor"` 跟随 el-button 自身 color（disabled 时 el-button 自动变灰）；同步从 `@element-plus/icons-vue` import 中移除 `Timer` 与 `CircleClose`
- 新增 `handleBatchCancelScheduledScan` / `handleRowCancelScheduledScan` 函数，复用 `scaBatchUpdateScheduled({ isScheduled: 0 })`
- 开启定时扫描成功提示语统一为「开启成功，将于每日零点自动执行定时扫描」（批量 / 单行）
- 消费 `isScheduled` + `isOversize` 双数值字段（0/1）：`isScheduled===1` 已开启可取消；`isScheduled!==1 && isOversize!==1` 可开启；`isScheduled!==1 && isOversize===1`（仓库>100M）列表入口按钮禁用 + 超量提示

**可选后续**（待产品确认，非本 spec 范围）：

- 列表新增「定时状态」列展示 `isScheduled` 字段（字段已由后端 list 接口返回，列展示待产品确认）
- `isScheduled` / `isOversize` 字段语义如有扩展（如新增其他取值），同步修改 `index.vue` 与本 spec

## 验收标准

### 批量操作（开启定时）

- [ ] Sca Tab 批量操作区在「批量扫描」「批量删除」之后展示「定时扫描」按钮（文案已由「批量定时扫描」调整）
- [ ] 按钮使用内联 SVG 图标（SVG class `.btn-icon`，钟表轮廓：4 个铃铛装饰 + 表盘 `circle cx=12 cy=12 r=8` + 时针 `M12 12 L12 7.5` + 分针 `M12 12 L15.5 12`），`type="primary"`，按钮本体带 `class="scan-btn"`；禁用时 el-button 自动让 currentColor 变灰，SVG 跟随
- [ ] 未勾选任何行 或 勾选全无可开启目标（已开启 `isScheduled===1` 或 超量 `isOversize===1`）时按钮禁用
- [ ] 勾选行后点击按钮：自动过滤 `isScheduled !== 1 && isOversize !== 1` 的可开启行；含跳过则在二次确认弹窗 message 末尾追加「\n\n已跳过 N 条不可开启的记录（已开启或仓库超过 100M）」（不再单独弹 warning）；全无可开启行弹出 info 提示并终止
- [ ] 通过 `ElMessageBox.confirm` 二次确认后发起 API 请求（`isScheduled: 1`），成功后弹出 success 提示「开启成功，将于每日零点自动执行定时扫描」并刷新列表
- [ ] 失败时弹出 error 提示（后端 message 或默认文案）

### 批量操作（取消定时，本次新增）

- [ ] Sca Tab 批量操作区在「定时扫描」之后新增「取消定时扫描」按钮，使用内联 SVG 图标（SVG class `.btn-icon`，钟表轮廓 + 一条贯穿斜线 `M3.5 3.5 L20.5 20.5`），按钮本体带 `class="cancel-btn"`；禁用时 el-button 自动让 currentColor 变灰，SVG 跟随
- [ ] 按钮始终展示，未勾选任何行 或 勾选全为未开启（`isScheduled !== 1`）时禁用（无可取消定时扫描的目标）
- [ ] 勾选行后点击按钮：自动过滤 `isScheduled === 1` 的行；若有跳过则在二次确认弹窗 message 末尾追加「\n\n已跳过 N 条未开启定时扫描的记录」（不再单独弹 warning）；若无任何已开启行弹出 info 提示并终止
- [ ] 通过 `ElMessageBox.confirm` 二次确认后发起 API 请求（`isScheduled: 0`），成功后弹出 success 提示「取消成功」并刷新列表
- [ ] 失败时弹出 error 提示（后端 message 或默认文案）

### 列表操作列（开启定时）

- [ ] Sca Tab 表格操作列在「开始扫描」「删除」之间展示「开启定时扫描」入口（tooltip 文案已由「定时扫描」调整）
- [ ] 在该行 `isScheduled !== 1` 时显示（与「取消定时扫描」互斥；超量未开启时按钮可见但禁用）
- [ ] 按钮使用内联 SVG 图标（SVG class `.row-icon`）；`row.isOversize === 1` 时按钮 `:disabled="true"` + `:class="{ 'disable-class': row.isOversize === 1 }"`，靠 el-button disabled 状态让 currentColor 变灰，SVG 跟随变灰
- [ ] `row.isOversize !== 1`：按钮可点击，`el-tooltip` 提示文案「开启定时扫描」
- [ ] `row.isOversize === 1`（超量未开启）：按钮 `:disabled`，`el-tooltip` 提示文案切为「仓库超过 100M，扫描耗时可能过长，禁止开启定时扫描」
- [ ] 可点击状态下点击发起 API 请求（单行 `isScheduled: 1`），成功后弹出 success 提示「开启成功，将于每日零点自动执行定时扫描」并刷新列表
- [ ] 失败时弹出 error 提示（后端 message 或默认文案）

### 列表操作列（取消定时，本次新增）

- [ ] Sca Tab 表格操作列在「开始扫描」「删除」之间新增「取消定时扫描」入口
- [ ] **仅在该行 `isScheduled === 1` 时显示**（与「开启定时扫描」互斥）
- [ ] 使用内联 SVG 图标按钮（SVG class `.row-icon`，比「开启定时扫描」多一条贯穿斜线 `M3.5 3.5 L20.5 20.5`，视觉区分），`el-tooltip` 提示文案「取消定时扫描」
- [ ] 点击发起 API 请求（单行 `isScheduled: 0`），成功后弹出 success 提示「取消成功」并刷新列表
- [ ] 失败时弹出 error 提示（后端 message 或默认文案）
- [ ] 不影响「开始扫描」「删除」按钮的现有行为与位置
- [ ] 操作列宽度足以容纳三个图标不折行

### 一致性约束

- [ ] 「定时扫描」「取消定时扫描」按钮在 CodeCheck / AntiPoison 两个 Tab 不展示（仅 Sca Tab）
- [ ] 切换 Tab 时与 `scaSelection` 一并清空，避免跨 Tab 残留
- [ ] 国际化文案保留中文即可（与 Sca Tab 现有硬编码文案一致），不强制接入 i18n
- [ ] `isScheduled` / `isOversize` 字段语义在代码与 spec 中保持一致（`isScheduled`：1=已开启可取消，0=未开启可开启；`isOversize`：1=超量>100M禁止开启，0=正常允许开启）

## 影响范围

- 前端：`openlibing-web` 仓 `apps/web-openlibing/src/views/InspectionCenter/index.vue`（本次扩展仅改此一个文件，`src/api/url.ts` / `src/api/api.ts` 已在前次提交中落地，无需再改）
- 后端：无变更（API 已由后端提供：`/version/scan/batchUpdateScheduled`）；`isScheduled` / `isOversize` 数值字段已由后端 list 接口返回（0/1）
- 路由 / 权限：无变更
- 数据模型：无变更（仅消费列表行上的 `isScheduled` / `isOversize` 数值字段，0/1）

## 后续待办（可选扩展，非本 spec 范围）

后端已提供定时扫描 API（已接入）：

- URL：`POST /openlibing-sca/version/scan/batchUpdateScheduled`
- 入参：`ids`（待更新记录 ID 数组）、`isScheduled`（0-取消定时，1-设为定时）
- 出参：标准响应（`code: 200` 表示成功）

已接入调用：

- 批量定时扫描：过滤 `isScheduled !== 1 && isOversize !== 1` 的可开启行，传入其 `ids` 数组与 `isScheduled: 1`
- 单行定时扫描：防御检查后传入 `[row.id]` 与 `isScheduled: 1`
- 批量取消定时扫描（本次新增）：过滤 `isScheduled === 1` 的已开启行，传入其 `ids` 与 `isScheduled: 0`
- 单行取消定时扫描（本次新增）：防御检查后传入 `[row.id]` 与 `isScheduled: 0`

字段语义：`isScheduled`——`1`=已开启定时扫描（可取消），`0`=未开启（可开启）；`isOversize`——`1`=超量>100M禁止开启定时扫描，`0`=正常允许开启。双字段联合判定规则见「需求目标 / 状态判定字段」。语义如有扩展（如新增其他取值），同步修改 `index.vue` 与本 spec。

可选后续扩展（待产品确认后另起 spec）：

- 「定时状态」列：在 `scaTableHeader` 新增列展示 `isScheduled` 字段（字段已由后端 list 接口返回，列展示待产品确认）

注：本 API 仅切换 `isScheduled` 标志位，不涉及 cron 表达式或调度频率配置；调度执行由后端处理。

## 关联

- 业务仓：openlibing/openlibing-web
- 目标分支（业务 PR base）：openlibing/openlibing-web `release_20260831`
- 业务 Issue：https://gitcode.com/openlibing/openlibing-sca/issues/60（检测中心 - Sca 需求，跨仓引用）
