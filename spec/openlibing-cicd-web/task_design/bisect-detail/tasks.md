# Tasks: PR 问题二分定位功能（BisectDetail）

## 实现步骤

- [x] 1. 新增 `BISECT` 和 `BISECT_RESET` URL 常量（url.ts）
- [x] 2. 新增 `postBisectAxios`、`getBisectAxios`、`postBisectResetAxios` API 函数（api.ts）
- [x] 3. 新增 `BisectDetail.vue` 弹窗主组件（进度摘要、表格、状态图标、刷新/分析/重置交互）
- [x] 4. 新增 `BisectDetailLabel.vue` 标题组件（标题文字 + 帮助文档链接）
- [x] 5. 新增 `pipelineBisectDebug.vue` 配置组件（开关、策略、代码源选择）
- [x] 6. `Detail.vue` 集成 BisectDetail 入口链接和对话框实例
- [x] 7. `pipelineEditDialog.vue` 集成 bisectDebug Tab 和序列化/保存逻辑
- [x] 8. projectId 动态化（从 `app.projectInfo?.projectId` 获取）
- [x] 9. 批量编辑模式下隐藏 bisectDebug Tab
- [x] 10. 菜单文案改为"辅助功能"
- [x] 11. 二分定位配置与展示优化（字段调整、空值处理、文案调整）
- [x] 12. 代码评审问题修复（行尾空白、表达式简化、文本截断移除等）

## 验证步骤

- [ ] 流水线详情页（已执行状态）页头展示"PR问题定位：查看详情"入口
- [ ] 点击入口打开 BisectDetail 对话框，自动加载数据
- [ ] 摘要区域正确展示分析状态、问题 PR 链接、分析时长
- [ ] 时间窗口信息正确展示
- [ ] 进度列表表格各列展示正确，PR 和分析流水线链接可跳转
- [ ] 状态图标与状态码对应正确
- [ ] 重置按钮仅特定状态可用，操作后刷新列表
- [ ] 手动触发分析弹出确认框，确认后启动分析
- [ ] 流水线编辑弹窗展示"辅助功能"Tab
- [ ] 批量编辑模式下"辅助功能"Tab 隐藏
- [ ] 开关开启后代码源必填，仅 gitcode 类型可选
- [ ] PR 筛选策略两个选项可正常切换
- [ ] 保存后配置正确提交到后端

## Commit 记录

| Commit | 说明 |
|--------|------|
| `b8e7f21` | feat: 新增PR问题二分定位弹窗组件 BisectDetail |
| `ba0fd60` | feat: 新增流水线编辑-二分定位配置组件 pipelineBisectDebug |
| `e6bf14c` | feat: BisectDetail 完善二分定位弹窗-进度摘要/表格操作/状态图标/重置重试等交互 |
| `7852c3f` | feat: 集成二分定位功能-API/Detail入口/编辑配置联动 |
| `a4efa98` | fix: 将状态图标从分析流水线列移至分析结果列 |
| `4f8f82d` | fix: BisectDetail 优化-移除分页/字段调整/空值处理 |
| `91ffd5e` | fix: BisectDetail 调整提示文案 |
| `5432908` | fix: BisectDetail 移除分析状态图标 |
| `74a2068` | feat: BisectDetail 引入BuildProductLabel组件 |
| `6d56d6e` | fix: BisectDetail 调整Empty组件空数据提示文案 |
| `58d0a7a` | fix: BisectDetail 调整摘要文案-总体运行时间改为分析时长 |
| `5f3930e` | fix: BisectDetail 重置按钮支持RUN_FAILED状态 |
| `945904f` | fix: BisectDetail 调整重置请求参数并移除失败提示 |
| `b1efdf1` | chore: BisectDetail 修复行尾空白 |
| `69df63b` | refactor: BisectDetail 简化task展开表达式 |
| `13d70d5` | refactor: BisectDetail 代码评审问题修复 |
| `db927fa` | fix: pipelineEditDialog bisectDebug菜单文案改回辅助功能 |
| `e7740b1` | fix: BisectDetail projectId动态化并在批量编辑时隐藏bisectDebug |
| `6c3984d` | refactor: BisectDetail 二分定位配置与展示优化 |
| `2b6428a` | refactor(BisectDetail): remove text truncation from failure message |
