# remove-dialog-z-index

## 需求
ExportFloatPanel 组件中 `DownloadCenterDialog` 子组件传递了 `:dialog-z-index="6100"` 属性，该属性在子组件中已不再需要，移除该无效 prop 传递。

## 验收
- [ ] ExportFloatPanel 中 `DownloadCenterDialog` 不再传递 `dialog-z-index` prop
- [ ] 导出历史弹窗功能正常，无控制台警告
