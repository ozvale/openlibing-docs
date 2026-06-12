# Tasks: 安全编译选项数据工程能力建设

## 实现步骤

- [x] 1. 创建 API 层（url.ts + api.ts），定义 overview、dropdown、file-detail 三个接口
- [x] 2. 创建 SecurityOptions/index.vue 主页面，el-tabs + el-table 布局
- [x] 3. 实现代码仓下拉筛选，数据来源于 dropdown 接口 data.repoNames
- [x] 4. 实现文件联动下拉筛选，数据来源于 dropdown 接口 data.packageNames
- [x] 5. 实现检测完成时间范围筛选（datetimerange），传入 startTime/endTime
- [x] 6. 实现表格列配置（27列），包含 8 个安全指标组
- [x] 7. 实现嵌套属性渲染（overviewData.bindNow.totalFiles 等）
- [x] 8. 实现开启率列颜色标记（>=80% 绿色 / >=50% 橙色 / <50% 红色）
- [x] 9. 实现表格自定义排序，参数格式为 sortByField/sort
- [x] 10. 实现左侧固定列（代码仓/流水线/文件）
- [x] 11. 实现流水线列跳转链接（pipelineLink）
- [x] 12. 实现文件列下钻弹窗（FileDetailDialog.vue）
- [x] 13. 弹窗内文件名支持 TableHeaderFilter 模糊搜索
- [x] 14. 增强 TableHeaderFilter 组件（新增 placement、popperClass props）
- [x] 15. 添加路由配置 /security-options
- [x] 16. 添加检测完成时间列（detectionCompletedAt），支持排序
