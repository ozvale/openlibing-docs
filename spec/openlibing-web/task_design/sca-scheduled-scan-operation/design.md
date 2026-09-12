# Design: 检测中心 - Sca 菜单列表定时扫描与取消定时扫描操作

## 技术方案

### 总体策略

后端已提供定时扫描 API（`/version/scan/batchUpdateScheduled`），前端采用「UI + API 全量接入」模式：

- 在 Sca Tab 批量操作区与列表操作列新增「定时扫描」入口（前次已交付）
- 本次扩展：批量按钮文案「批量定时扫描」→「定时扫描」；列表 tooltip「定时扫描」→「开启定时扫描」
- 本次扩展：新增「取消定时扫描」入口（批量 + 列表操作列），复用 `scaBatchUpdateScheduled({ isScheduled: 0 })`
- 本次再扩展：批量操作收敛为「批量扫描」外置主按钮 +「...」更多操作下拉（批量删除 / 开启定时扫描 / 取消定时扫描三项菜单），`@command="handleBatchCommand"` 统一分发到原批量函数；二次确认弹窗迁移至 CommonDialog 组件（`openCommonDialog`，commit `3c30af18`）
- 列表操作列「开启 / 取消」入口通过 `row.isScheduled` + `row.isOversize` 双字段联合判定（详见下文「状态字段」）
- API 端点常量与请求函数已在前次提交落地，本次无需修改 `url.ts` / `api.ts`
- 事件回调直接调用 `scaBatchUpdateScheduled`，复用现有 `handleBatchDelete` 的错误处理风格
- 调用成功后 `getFullTask()` 刷新列表，失败时弹出 error 提示

### 变更文件

| 文件                                                       | 变更类型   | 说明                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/api/url.ts`                       | 前次已修改 | `SCA_BATCH_UPDATE_SCHEDULED` 端点常量（本次无变更）                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `apps/web-openlibing/src/api/api.ts`                       | 前次已修改 | `scaBatchUpdateScheduled: RequestFunc` 导出（本次无变更）                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `apps/web-openlibing/src/views/InspectionCenter/index.vue` | 修改       | 文案调整 + 新增「取消定时扫描」入口 / 事件回调 + 消费 `isScheduled` / `isOversize` 双字段（0/1）+ 行内图标替换为内联 SVG（移除 `Timer` / `CircleClose` import）+ **批量操作收敛为「...」更多下拉**（`MoreFilled` 触发按钮 + 批量删除 / 开启定时扫描 / 取消定时扫描菜单项 + `handleBatchCommand` 分发 + `QuestionFilled` 问号 tip，移除 `.btn-icon` / `.tip-icon` / `.batch-tips` / `.del-btn` 样式）+ 二次确认弹窗迁移至 `CommonDialog` + 开启定时扫描成功提示语「开启成功，将于每日零点自动执行定时扫描」 |

本次扩展涉及 1 个前端文件，无新增文件、无路由/权限变更、无数据模型变更。

### API 契约

- URL：`POST /openlibing-sca/version/scan/batchUpdateScheduled`
- 入参：`ids`（待更新记录 ID 数组）、`isScheduled`（0-取消定时，1-设为定时）
- 出参：标准响应（`code: 200` 表示成功）
- 本 API 仅切换 `isScheduled` 标志位，调度执行由后端处理

### 状态字段：`isScheduled` + `isOversize`

定时扫描状态由后端 list 接口返回的两个数值字段联合判定：

- `isScheduled`：是否已开启定时扫描。`1`=已开启（可取消），`0`=未开启（可开启）
- `isOversize`：仓库是否超量（>100M）。`1`=超量禁止开启定时扫描，`0`=正常允许开启

**联合判定**（列表操作列入口 + 批量按钮禁用 + 函数过滤均以此为准）：

| 状态组合                            | 列表入口显示                    | 批量菜单项「开启定时扫描」 | 批量菜单项「取消定时扫描」 |
| ----------------------------------- | ------------------------------- | -------------------------- | -------------------------- |
| `isScheduled===1`                   | 取消定时扫描                    | 跳过（已开启）             | 可取消                     |
| `isScheduled!==1 && isOversize!==1` | 开启定时扫描（可点击）          | 可开启                     | 跳过（未开启）             |
| `isScheduled!==1 && isOversize===1` | 开启定时扫描（禁用 + 超量提示） | 跳过（超量）               | 跳过（未开启）             |

- 列表行通过 `v-if="row.isScheduled === 1"` 显示「取消定时扫描」入口；`v-else` 显示「开启定时扫描」入口，并在 `row.isOversize === 1` 时给按钮加 `:disabled` 且 tooltip 文案切为「仓库超过 100M，扫描耗时，占用资源，建议非高峰期手动执行扫描」
- 批量「...」触发按钮：始终可点击展开，不设禁用条件
- 批量菜单项「批量删除」禁用条件：未勾选（`scaSelection.length === 0`）
- 批量菜单项「开启定时扫描」禁用条件：未勾选 或 勾选全无可开启目标（`isScheduled===1` 或 `isOversize===1`）
- 批量菜单项「取消定时扫描」禁用条件：未勾选 或 勾选全为未开启（`isScheduled !== 1`）
- 在代码中以注释 `// isScheduled：1=已开启定时扫描（可取消），0=未开启（可开启）；isOversize：1=超量>100M禁止开启（按钮禁用+提示），0=正常允许开启` 与同义 HTML 注释标注

### UI 设计

1. **批量按钮区**（最终形态）
   - 外置「批量扫描」主按钮：`type="primary"`，`VideoPlay` 图标，`:disabled="batchScanDisabled"`（未勾选 或 全为扫描中），`:loading="batchScanLoading"`
   - 「...」更多操作下拉：外层 `el-tooltip`（content「更多操作」）包裹 `el-dropdown`（`trigger="click"`，`placement="bottom-end"`，`@command="handleBatchCommand"`）；触发按钮为仅图标按钮（`:icon="MoreFilled"`，`class="more-btn"`，无文字），**始终可点击，不设 disabled**
   - 嵌套顺序约束（踩坑记录）：`el-tooltip` 必须在 `el-dropdown` 外层——dropdown 把 click 触发绑定到默认插槽直接子元素，tooltip 若嵌在 dropdown 与 button 之间会导致点击无法展开
   - 下拉菜单项：批量删除（`command="delete"`）、开启定时扫描（`command="scheduled"`）、取消定时扫描（`command="cancel"`），各自 `:disabled` 见「状态字段」
   - 「开启定时扫描」菜单项内容包在 `span.scheduled-item`：文字 + `QuestionFilled` 问号图标（`el-icon.tip-question`）+ `el-tooltip`「定时扫描仅支持≤100MB的仓库」（`placement="top"`，气泡向上）
   - 批量按钮区下方黄色提示行（`.batch-tips`）已移除（提示信息收敛到问号 tooltip）
   - 布局：`.batch-buttons`（`display: flex; align-items: center`，`.el-button + .el-dropdown` 间距 8px）
2. **列表操作列「定时扫描」入口**
   - 位置：Sca 表格 `operation` 列，「开始扫描」与「删除」之间
   - 互斥显示（图标区分，列表入口无文字标签，必须图标区分）：
     - `row.isScheduled === 1`：显示「取消定时扫描」（`CircleClose` 图标，tooltip「取消定时扫描」）
     - 其他（`row.isScheduled !== 1`）：显示「开启定时扫描」（`Timer` 图标）
       - `row.isOversize !== 1`：tooltip「开启定时扫描」，按钮可点击
       - `row.isOversize === 1`（超量未开启）：按钮 `:disabled`，tooltip 切为「仓库超过 100M，扫描耗时，占用资源，建议非高峰期手动执行扫描」（不隐藏入口，让用户感知禁用原因）
   - 操作列宽度保持 200（前次已由 160 调整），避免图标拥挤
3. **图标选择**
   - 「开启定时扫描」/「取消定时扫描」（**仅列表操作列**，批量入口为「...」下拉菜单纯文字菜单项）：**内联 SVG**，绘制钟表轮廓（4 个铃铛装饰 `M7.5 5 Q5.5 2.5 5 5.5` / `M16.5 5 Q18.5 2.5 19 5.5` / `M7.5 19 Q5.5 21.5 5 18.5` / `M16.5 19 Q18.5 21.5 19 18.5` + 表盘 `circle cx=12 cy=12 r=8` + 时针 `M12 12 L12 7.5` + 分针 `M12 12 L15.5 12`），SVG class 为 `.row-icon`；「取消定时扫描」在钟表轮廓基础上**增加一条贯穿斜线** `M3.5 3.5 L20.5 20.5`
   - SVG 节点直接嵌入行内 `<el-button>` 内部（不通过 `:icon` 属性传组件）；`viewBox="0 0 24 24"`，`fill="none"`，`stroke-width="1.2"`，`stroke-linecap="round"`，`stroke-linejoin="round"`；钟表轮廓部分包在 `<g stroke="currentColor">` 内，贯穿斜线单独写 `stroke="currentColor"`
   - 批量「...」触发按钮图标：`MoreFilled`（实心三点，`@element-plus/icons-vue` 组件，`:icon` 属性传入）；按钮本体 `class="more-btn"` 定义图标色（`--el-button-text-color: #191919`）
   - 问号提示图标：`QuestionFilled`（实心问号，`@element-plus/icons-vue` 组件），渲染为 `<el-icon class="tip-question"><QuestionFilled /></el-icon>`；样式 `margin-left: 4px; font-size: 14px; color: #a7a8bc; cursor: pointer`，父级 `span.scheduled-item`（`display: inline-flex; align-items: center`）
   - import 列表（`@element-plus/icons-vue`）：`Delete` / `Edit` / `MoreFilled` / `QuestionFilled` / `VideoPause` / `VideoPlay`（已移除 `Timer` / `CircleClose` / `ArrowDown`）
   - 视觉状态：行内 SVG 颜色靠 `stroke="currentColor"` 跟随 el-button 自身 color（disabled 时 el-button 自动让 currentColor 变灰，SVG 跟随变灰）；列表操作列 SVG 尺寸由 `.row-icon`（`width: 16px; height: 16px; font-size: 16px`）控制；行级 `.disable-class` 仅作模板 class 标识（无自定义 hover 蓝色 `#006be6`，前次 spec 中描述的 hover 蓝色未实现）
   - 行级禁用：`row.isOversize === 1` 时按钮 `:disabled="true"` + `:class="{ 'disable-class': row.isOversize === 1 }"`，靠 el-button disabled 状态自动让 SVG 变灰
   - 无新增 svg 文件资源依赖，SVG path 内联在模板中

### 行为设计

- `handleBatchCommand(command)`（「...」下拉 `@command` 分发函数）：`'delete'` → `handleBatchDelete()`、`'scheduled'` → `handleBatchScheduledScan()`、`'cancel'` → `handleBatchCancelScheduledScan()`；不承载业务逻辑，仅事件路由
- 二次确认弹窗统一使用 `CommonDialog` 组件（`openCommonDialog({ title, message, confirmText, cancelText, onConfirm })`，危险类操作加 `confirmType: 'danger'`；commit `3c30af18` 抽取公共组件，替代原 `ElMessageBox.confirm`）
- `handleBatchScheduledScan`：过滤 `scaSelection` 中 `isScheduled !== 1 && isOversize !== 1` 的行作为 `valid`，传入 `ids` 数组与 `isScheduled: 1`；无可开启行弹 info 提示并终止；含跳过行时在 CommonDialog 二次确认弹窗 message 末尾追加「\n已跳过 N 条不可开启的记录（已开启或仓库超过 100M）。」
- `handleRowScheduledScan(row)`：防御检查 `row.isScheduled === 1`（已开启）/ `row.isOversize === 1`（超量）时直接 return；通过则传入 `[row.id]` 与 `isScheduled: 1`
- 开启定时扫描（批量 / 单行）成功提示语统一为 `ElMessage.success('开启成功，将于每日零点自动执行定时扫描')`（本次扩展调整，原「批量定时扫描已设置」/「定时扫描已设置」）
- 开启定时扫描（批量 / 单行）失败提示语统一为 `ElMessage.error(res?.message || '开启失败')`（res 非 200 与 catch 异常均用此文案）
- `handleBatchCancelScheduledScan`（本次新增）：
  - 过滤 `scaSelection` 中 `isScheduled === 1` 的行作为 `scheduled` 列表
  - 计算 `skipped` 数量；若 `scheduled` 为空弹出 info 提示并终止
  - 若有跳过行时在 CommonDialog 二次确认弹窗 message 末尾追加「\n已跳过 N 条未开启定时扫描的记录。」
  - 通过 CommonDialog 二次确认
  - 调用 `scaBatchUpdateScheduled({ ids: scheduled.map(r => r.id), isScheduled: 0 })`
  - 成功 → `ElMessage.success('取消成功')` + `getFullTask()`
  - 失败 → `ElMessage.error(res?.message || '操作失败')`
- `handleRowCancelScheduledScan(row)`（本次新增）：
  - 防御检查 `row.isScheduled !== 1` 时直接 return（未开启定时扫描，无可取消目标）
  - 调用 `scaBatchUpdateScheduled({ ids: [row.id], isScheduled: 0 })`
  - 成功 → `ElMessage.success('取消成功')` + `getFullTask()`
  - 失败 → `ElMessage.error(res?.message || '操作失败')`
- 错误处理风格与现有 `handleBatchDelete` / `handleSingleDelete` 一致：
  - `try/catch` 捕获网络与逻辑异常
  - `res?.code === 200` 判断业务成功

### 数据流

```
用户在「...」下拉选择菜单项（批量）或点击行内图标（单行）
  → 「开启定时扫描」菜单项 / 行内图标
      → 过滤可开启行（isScheduled !== 1 && isOversize !== 1）→ CommonDialog 二次确认 → 调用 scaBatchUpdateScheduled({ ids, isScheduled: 1 })
      → 成功：success 提示「开启成功，将于每日零点自动执行定时扫描」 + 刷新 SCA 列表
      → 失败：error 提示（后端 message 或默认文案）
  → 「取消定时扫描」菜单项 / 行内图标
      → 批量：过滤 isScheduled===1 → CommonDialog 二次确认 → 调用 scaBatchUpdateScheduled({ ids, isScheduled: 0 })
      → 单行：调用 scaBatchUpdateScheduled({ ids: [row.id], isScheduled: 0 })
      → 成功：success 提示「取消成功」 + 刷新 SCA 列表
      → 失败：error 提示（后端 message 或默认文案）
  → 「批量删除」菜单项
      → CommonDialog 二次确认（危险模板）→ 调用批量删除接口
      → 成功：success 提示「删除成功」 + 刷新 SCA 列表；失败：error 提示
```

### Tab 隔离

现有 `switchTab()` 已在切换时清空 `scaSelection`，定时扫描 / 取消定时扫描按钮的禁用状态、可见性自动跟随 Tab 切换，无需新增响应式变量。

### 可选扩展（待产品确认，非本 spec 范围）

- 「定时状态」列：在 `scaTableHeader` 新增列展示 `isScheduled` 字段（已由后端 list 接口返回，列展示待产品确认）
- `isScheduled` / `isOversize` 字段语义如有扩展（如新增其他取值），同步修改 `index.vue` 与本 spec

### 不再需要的设计（原 spec 假设已移除）

- 4 个 CRUD 端点（save/query/delete/toggle）—— 实际只有 1 个 batch update 接口
- `ScheduledScanDialog.vue` 弹窗组件 —— API 仅切换标志位，无需配置频率/时间
- 频率/时间/星期/日期 UI —— 调度由后端处理
- 唯一约束 —— 单条记录仅一个 isScheduled 标志，不存在多任务冲突

### 无变更项

- 路由 / 权限：无变更
- 数据模型 / 类型：无新增（仅消费列表行上的 `isScheduled` / `isOversize` 数值字段，0/1）
- 依赖：无新增 npm 依赖。内联 SVG 图标直接写在模板中，从 `@element-plus/icons-vue` import 中移除 `Timer` / `CircleClose`（保留 `Delete` / `Edit` / `VideoPause` / `VideoPlay`）；无新增图片/svg 文件资源
- 其他 Tab（CodeCheck / AntiPoison）：无变更
- i18n：与 Sca Tab 现有硬编码中文文案一致，不强制接入 i18n
