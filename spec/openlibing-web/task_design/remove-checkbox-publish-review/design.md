# 技术方案

## 变更说明

移除发布评审首页表格的复选框功能，简化页面交互。

## 修改方案

### 1. 修改文件

**文件路径**: `apps/web-openlibing/src/views/Publish/publishReview/index.vue`

### 2. 修改内容

将 `publishTable` 组件的 `multiple` 属性从 `true` 修改为 `false`：

```vue
<!-- 修改前 -->
<publishTable
  :multiple="true"
  ...
/>

<!-- 修改后 -->
<publishTable
  :multiple="false"
  ...
/>
```

### 3. 影响范围

- **前端**: 发布评审首页表格不再显示复选框列
- **后端**: 无影响
- **API**: 无影响

## 测试建议

1. 访问发布评审首页，确认表格无复选框列
2. 确认表格其他功能正常（分页、排序、操作按钮等）
3. 确认页面布局正常，无样式错乱