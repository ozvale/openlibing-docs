# Tasks: 检测中心 - Sca 菜单列表定时扫描与取消定时扫描操作

## 实现步骤（前次：开启定时扫描，已完成）

- [x] 1. 在 `@element-plus/icons-vue` 导入中新增 `Timer` 图标
- [x] 2. 在 `scaTableHeader` 中将 `operation` 列 `width` 由 `160` 调整为 `200`
- [x] 3. 在 Sca Tab 批量操作区，「批量删除」按钮之后新增「批量定时扫描」按钮（`type="primary"`, `:icon="Timer"`, 未勾选 或 勾选全无可开启目标（已开启 `isScheduled===1` 或 超量 `isOversize===1`）时禁用）
- [x] 4. 在 Sca 表格 `operation` 列，「开始扫描」与「删除」之间新增「定时扫描」入口（`el-tooltip + el-button`，`Timer` 图标，`v-else` 显示，`row.isOversize === 1` 时 `:disabled` 且 tooltip 切为「仓库超过 100M，扫描耗时可能过长，禁止开启定时扫描」）
- [x] 5. 在 `src/api/url.ts` 新增 `SCA_BATCH_UPDATE_SCHEDULED` 端点常量
- [x] 6. 在 `src/api/api.ts` 新增 `scaBatchUpdateScheduled: RequestFunc` 函数
- [x] 7. 在 `InspectionCenter/index.vue` 导入 `scaBatchUpdateScheduled`
- [x] 8. 替换 `handleBatchScheduledScan` 占位函数为实际 API 调用（批量 `ids` + `isScheduled: 1`，复用 `handleBatchDelete` 的错误处理风格）
- [x] 9. 替换 `handleRowScheduledScan(row)` 占位函数为实际 API 调用（`[row.id]` + `isScheduled: 1`，复用 `handleSingleDelete` 的错误处理风格）
- [x] 10. ESLint 验证通过（`url.ts` / `api.ts` / `InspectionCenter/index.vue`）

## 实现步骤（本次扩展：取消定时扫描 + 文案调整）

- [x] 11. 批量按钮文案「批量定时扫描」调整为「定时扫描」（行为不变）
- [x] 12. 列表操作列 tooltip「定时扫描」调整为「开启定时扫描」（行为不变）
- [x] 13. 在 Sca Tab 批量操作区，「定时扫描」按钮之后新增「取消定时扫描」按钮（`type="warning"`, `:icon="CircleClose"`, 未勾选 或 勾选全为未开启（`isScheduled !== 1`）时禁用，始终展示）
- [x] 14. 在 Sca 表格 `operation` 列新增「取消定时扫描」入口，与「开启定时扫描」通过 `v-if="row.isScheduled === 1"` / `v-else` 互斥显示（`isScheduled!==1 && isOversize===1` 时「开启定时扫描」按钮 `:disabled` + tooltip 切为「仓库超过 100M，扫描耗时可能过长，禁止开启定时扫描」）
- [x] 15. 在列表操作列上方添加注释 `<!-- isScheduled：1=已开启定时扫描（可取消），0=未开启（可开启）；isOversize：1=超量>100M禁止开启（按钮禁用+提示），0=正常允许开启 -->`
- [x] 16. 新增 `handleBatchCancelScheduledScan` 函数：过滤 `scaSelection` 中 `isScheduled === 1` 的行；空列表弹 info 终止；有跳过则在 `ElMessageBox.confirm` 弹窗 message 末尾追加「\n\n已跳过 N 条未开启定时扫描的记录」（不再单独弹 warning）；`ElMessageBox.confirm` 二次确认后调用 `scaBatchUpdateScheduled({ ids, isScheduled: 0 })`；复用 `handleBatchScan` 的错误处理风格
- [x] 17. 新增 `handleRowCancelScheduledScan(row)` 函数：防御检查 `row.isScheduled !== 1` 时 return；调用 `scaBatchUpdateScheduled({ ids: [row.id], isScheduled: 0 })`；复用 `handleRowScheduledScan` 的错误处理风格
- [x] 18. 在四个函数上方添加 `// isScheduled：1=已开启定时扫描（可取消），0=未开启（可开启）；isOversize：1=超量>100M禁止开启（按钮禁用+提示），0=正常允许开启` 注释
- [x] 19. ~~确认 `@element-plus/icons-vue` 的 `Timer` / `CircleClose` 图标导入正确（`import { CircleClose, Delete, Edit, Timer, VideoPause, VideoPlay } from '@element-plus/icons-vue'`），批量按钮 + 列表操作列一致使用~~（**已由后续 commit `d2c183bb` 取代**：图标改为内联 SVG，`Timer` / `CircleClose` 从 import 中移除，详见下方「图标替换 + 删除弹窗重设计」段任务 25-30）
- [x] 20. ~~复用现有 `.icon-btn` 样式，无新增 `.scan-icon` 样式~~（**已由后续 commit `d2c183bb` 取代**：新增 `.btn-icon` / `.row-icon` / `.tip-icon` 尺寸样式，`.scan-btn` / `.cancel-btn` / `.disable-class` 仅作模板 class 标识未在 CSS 中定义，详见任务 28）
- [x] 21. `handleBatchScheduledScan` / `handleRowScheduledScan` 成功提示语统一为「开启成功，将于每日零点自动执行定时扫描」（原「批量定时扫描已设置」/「定时扫描已设置」）
- [x] 22. ESLint 验证通过（`InspectionCenter/index.vue`）—— 已通过
- [x] 23. 新增 `batchScheduledScanDisabled` / `batchCancelScheduledScanDisabled` computed：定时扫描按钮禁用条件为「未勾选 或 勾选全无可开启目标（`isScheduled===1` 或 `isOversize===1`）」，取消定时扫描按钮禁用条件为「未勾选 或 勾选全为未开启（`isScheduled !== 1`）」；两个按钮 `:disabled` 由 `scaSelection.length === 0` 替换为对应 computed
- [x] 24. 双字段重构：列表操作列 v-if 由 `isOversize` 单字段改为 `isScheduled` + `isOversize` 双字段（`isScheduled===1` 取消入口 / `v-else` 开启入口，`isOversize===1` 时按钮 `:disabled` + tooltip 切为超量提示，不再隐藏入口）；`handleBatchScheduledScan` 过滤可开启行（`isScheduled!==1 && isOversize!==1`）；`handleBatchCancelScheduledScan` 过滤已开启行（`isScheduled===1`）；`handleRowScheduledScan` / `handleRowCancelScheduledScan` 加防御检查；函数注释与 HTML 注释更新为双字段语义

## 实现步骤（本次扩展：图标替换 + 删除弹窗重设计）

- [x] 25. 批量按钮区「定时扫描」按钮：移除 `:icon="Timer"`，改为在 `<el-button>` 内嵌入内联 SVG（`<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">`，绘制钟表轮廓：4 个铃铛装饰 `M7.5 5 Q5.5 2.5 5 5.5` / `M16.5 5 Q18.5 2.5 19 5.5` / `M7.5 19 Q5.5 21.5 5 18.5` / `M16.5 19 Q18.5 21.5 19 18.5` + 表盘 `circle cx=12 cy=12 r=8` + 时针 `M12 12 L12 7.5` + 分针 `M12 12 L15.5 12`，`stroke="currentColor"`），按钮本体新增 `class="scan-btn"`
- [x] 26. 批量按钮区「取消定时扫描」按钮：移除 `:icon="CircleClose"`，改为在 `<el-button>` 内嵌入内联 SVG（`<svg class="btn-icon">`，钟表轮廓部分包在 `<g stroke="currentColor">` 内 + 贯穿斜线 `<path d="M3.5 3.5 L20.5 20.5" stroke="currentColor" />`），按钮本体新增 `class="cancel-btn"`
- [x] 27. 列表操作列「开启定时扫描」/「取消定时扫描」入口：同样移除 `:icon` 属性，改为内联 SVG（SVG class `.row-icon`，path 与批量按钮一致）；「开启定时扫描」按钮在 `isOversize===1` 时新增 `:disabled="true"` + `:class="{ 'disable-class': row.isOversize === 1 }"`，靠 el-button disabled 状态自动让 SVG currentColor 变灰
- [x] 28. 新增 scoped 样式：`.btn-icon`（`width: 16px; height: 16px; vertical-align: -0.15em; margin-right: 6px`，用于批量按钮内 SVG）、`.row-icon`（`width: 16px; height: 16px; font-size: 16px`，用于列表操作列内 SVG）、`.tip-icon`（批量提示区图标 `width: 1em; height: 1em; margin-right: 6px; font-size: 14px; flex-shrink: 0`）；`.scan-btn` / `.cancel-btn` / `.disable-class` 仅作模板 class 标识，未在 CSS 中定义独立规则（无自定义 hover 蓝色 `#006be6`，前次 spec 中描述的 hover 蓝色未实现）
- [x] 29. 从 `@element-plus/icons-vue` import 中移除 `Timer` 与 `CircleClose`（保留 `Delete` / `Edit` / `VideoPause` / `VideoPlay`）
- [x] 30. ESLint / 构建验证通过（`InspectionCenter/index.vue`）

## 验证步骤

- [ ] 进入检测中心 Sca Tab，批量操作区按顺序展示：批量扫描 → 批量删除 → 定时扫描 → 取消定时扫描
- [ ] 未勾选任何行时「定时扫描」「取消定时扫描」按钮均置灰；勾选后恢复可点击
- [ ] 点击「定时扫描」按钮，发起 `POST /version/scan/batchUpdateScheduled` 请求，成功后弹出 success 提示「开启成功，将于每日零点自动执行定时扫描」并刷新列表
- [ ] 列表操作列在「开始扫描」与「删除」之间出现「开启定时扫描」内联 SVG 图标（SVG class `.row-icon`，钟表轮廓：4 个铃铛装饰 + 表盘 `circle cx=12 cy=12 r=8` + 时针 `M12 12 L12 7.5` + 分针 `M12 12 L15.5 12`），hover 显示 tooltip「开启定时扫描」（当 `row.isScheduled !== 1 && row.isOversize !== 1`）
- [ ] 列表操作列在 `row.isScheduled === 1` 时显示「取消定时扫描」内联 SVG 图标（SVG class `.row-icon`，钟表 + 贯穿斜线 `M3.5 3.5 L20.5 20.5`），hover 显示 tooltip「取消定时扫描」（与「开启定时扫描」互斥）
- [ ] 列表操作列在 `row.isScheduled !== 1 && row.isOversize === 1`（超量未开启）时，「开启定时扫描」按钮 `:disabled="true"` + `:class="{ 'disable-class': row.isOversize === 1 }"`，靠 el-button disabled 状态让 SVG currentColor 变灰，hover 显示 tooltip「仓库超过 100M，扫描耗时可能过长，禁止开启定时扫描」
- [ ] 「定时扫描」/「取消定时扫描」批量按钮 SVG 颜色靠 `stroke="currentColor"` 跟随 el-button color（disabled 时自动变灰，无自定义 hover 蓝色）
- [ ] 点击「开启定时扫描」图标，发起 `POST /version/scan/batchUpdateScheduled` 请求（`ids: [row.id]`, `isScheduled: 1`），成功后弹出 success 提示并刷新列表
- [ ] 点击「取消定时扫描」图标，发起 `POST /version/scan/batchUpdateScheduled` 请求（`ids: [row.id]`, `isScheduled: 0`），成功后弹出 success 提示「取消成功」并刷新列表
- [ ] 批量点击「取消定时扫描」按钮：若勾选行均为未开启（`isScheduled !== 1`），弹出 info 提示「所选记录均无可取消定时扫描的仓库」并终止
- [ ] 批量点击「取消定时扫描」按钮：若勾选行中含未开启行（`isScheduled !== 1`），二次确认弹窗 message 末尾追加「\n\n已跳过 N 条未开启定时扫描的记录」（不再单独弹 warning）
- [ ] 批量取消定时扫描二次确认弹窗文案：「确认对选中的 N 条记录取消定时扫描？」（含跳过时 message 末尾追加「\n\n已跳过 N 条未开启定时扫描的记录」）
- [ ] 失败场景：API 返回非 200 或抛错时，弹出 error 提示（开启定时扫描为「开启失败」、取消定时扫描为「操作失败」）或后端 message
- [ ] 切换到 CodeCheck / AntiPoison Tab，定时扫描 / 取消定时扫描按钮均不展示，操作列无相关入口
- [ ] 「开始扫描」「删除」按钮行为不受影响
- [ ] 操作列宽度合理，三个图标不出现折行或遮挡
- [ ] `isScheduled` / `isOversize` 字段由后端 list 接口返回：`isScheduled===1` 时「取消定时扫描」入口可见；`isScheduled!==1 && isOversize!==1` 时「开启定时扫描」按钮可点击；`isScheduled!==1 && isOversize===1` 时「开启定时扫描」按钮置灰禁用 + tooltip 切为「仓库超过 100M，扫描耗时可能过长，禁止开启定时扫描」

## Commit 记录

| Commit     | 说明                                                                                                                                                                                                                                                                                                                                                                    |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `4792ccc1` | feat(sca): add scheduled-scan toggle on InspectionCenter（接入定时扫描 API `scaBatchUpdateScheduled` + `SCA_BATCH_UPDATE_SCHEDULED` url + 批量 / 单行「开启 / 取消定时扫描」入口与事件回调 + `isScheduled` & `isOversize` 双字段 computed 禁用规则 + 文案「批量定时扫描」→「定时扫描」/「定时扫描」→「开启定时扫描」）                                                  |
| `d2c183bb` | feat(sca): replace scan icons with inline SVG（批量按钮 + 列表操作列图标 `Timer` / `CircleClose` → 内联 SVG，SVG class `.btn-icon` / `.row-icon`，`.scan-btn` / `.cancel-btn` / `.disable-class` 仅作模板 class 标识；颜色靠 `stroke="currentColor"` 跟随 el-button color；移除 `Timer` / `CircleClose` import；新增 `.btn-icon` / `.row-icon` / `.tip-icon` 尺寸样式） |

## 后续可选扩展（待产品确认，非本 spec 范围）

- [ ] 「定时状态」列：在 `scaTableHeader` 新增列展示 `isScheduled` 字段（字段已由后端 list 接口返回，列展示待产品确认）
- [ ] `isScheduled` / `isOversize` 字段语义如有扩展（如新增其他取值），同步修改 `index.vue` 与本 spec
