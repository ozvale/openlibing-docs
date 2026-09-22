# PR门禁看板详情页增加列设置 + Issue运营标签优化 + 测试仪表盘优化 — 实现任务

## 进度: 17/17 complete

### PR门禁看板详情页重构
- [x] Task 1: 重构 pr-info-detail.vue — 外层包裹 el-drawer，drawer 头部包含标题 + 导出按钮 + 列设置
- [x] Task 2: 重构 sub-table.vue — 移除 el-drawer 相关代码和导出逻辑
- [x] Task 3: 在 pr-info-detail.vue 中集成 column-setting 组件实现列设置功能

### Issue运营标签
- [x] Task 4: open-source-item.vue — 在 issue 运营提示语前添加绿色"公开issue"标签

### 测试仪表盘 utils.ts 结果类型映射
- [x] Task 5: 更新 getResultType/getResultLabel 字段映射为数字键（1/0/3/2）
- [x] Task 6: 未执行使用 info 类型，跳过使用 warning 类型
- [x] Task 7: formatNumber 函数增加空值判断，显示 --

### 案例历史视图 case-history-view.vue 优化
- [x] Task 8: 增加"总NPU消耗"指标卡片
- [x] Task 9: 所有指标单位内联到数据后
- [x] Task 10: 5个指标卡片强制单行展示
- [x] Task 11: 通过率单位与其他卡片保持一致，移除"通过"文字
- [x] Task 12: 指标标签优化：平均vCPU -> 平均vCPU消耗，平均NPU -> 平均NPU消耗

### 列设置组件 column-setting.vue 优化
- [x] Task 13: 识别所有有子节点的父节点（has-children）
- [x] Task 14: 统一根级和子节点的 flex 横向多行布局
- [x] Task 15: 父节点加粗显示、添加底部边框增强视觉层次
- [x] Task 16: 所有节点内容宽度统一 162px，内边距一致

## 验证方式
1. 项目构建无报错（`npm run build` 或 `vue-tsc` 类型检查）
2. 页面效果确认：el-drawer 正常打开/关闭，列设置功能正常，导出功能正常
3. issue 运营 tab 显示绿色标签
4. 测试仪表盘结果标签显示正确（成功/失败/未执行/跳过）
5. 案例历史视图5个指标单行展示，单位内联，空值显示 --
6. 列设置组件布局协调，有子节点和无子节点展示一致