# PR门禁看板详情页增加列设置 + Issue运营标签优化 + 测试仪表盘优化

## 需求背景

PR门禁看板详情页当前缺少列设置功能，用户无法自定义显示的列。同时将导出逻辑和el-drawer从sub-table.vue迁移到pr-info-detail.vue中，使组件职责更清晰。Issue运营页缺少"公开issue"标识。
测试仪表盘的案例历史视图需要增加指标展示和结果类型映射优化。

## 功能描述

### 一、PR门禁看板详情页重构

1. pr-info-detail.vue外层包裹el-drawer，替代sub-table.vue中的drawer
2. sub-table.vue移除el-drawer相关代码
3. 导出逻辑迁移到pr-info-detail.vue（当前通过defineExpose暴露）
4. 在导出按钮后添加列设置（复用column-setting.vue组件）

### 二、Issue运营标签

5. 在open-source-item.vue中issue运营提示语前添加绿色"公开issue"标签

### 三、测试仪表盘 utils.ts 结果类型映射

6. getResultType/getResultLabel 字段映射更新为数字键：1->成功, 0->失败, 3->未执行, 2->跳过
7. 未执行使用 info 类型，跳过使用 warning 类型
8. formatNumber 函数增加空值判断，显示 --

### 四、案例历史视图 case-history-view.vue 优化

9. 增加"总NPU消耗"指标卡片
10. 所有指标单位内联到数据后
11. 5个指标卡片强制单行展示
12. 通过率单位与其他卡片保持一致，移除"通过"文字
13. 指标标签优化：平均vCPU -> 平均vCPU消耗，平均NPU -> 平均NPU消耗

### 五、列设置组件 column-setting.vue 优化

14. 识别所有有子节点的父节点（has-children）
15. 统一根级和子节点的 flex 横向多行布局
16. 父节点加粗显示、添加底部边框增强视觉层次
17. 所有节点内容宽度统一 162px，内边距一致

## 验收标准

- [ ] pr-info-detail.vue 由 div 包裹改为 el-drawer 包裹，drawer 头部包含标题 + 导出 + 列设置
- [ ] sub-table.vue 中的 el-drawer 移除，导出逻辑迁移到 pr-info-detail.vue
- [ ] 列设置功能正常，可显示/隐藏表格列
- [ ] issue运营页面显示绿色"公开issue"标签
- [ ] 测试仪表盘结果标签显示正确（成功/失败/未执行/跳过）
- [ ] 案例历史视图5个指标单行展示，单位内联，空值显示 --
- [ ] 列设置组件布局协调，有子节点和无子节点展示一致

## 影响范围

- openlibing-ops-web 单仓，涉及模块：
  - open-source-project 仪表盘
  - test-dashboard 测试仪表盘
  - components/column-setting.vue 通用组件
