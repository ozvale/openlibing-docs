# 【openlibing-web】SBOM 成分分析页制品列表重构 — 实现任务

## 进度: 已完成（分支 dev-chenning-20260923-sbom）

- [x] Task 1: 新增 queryProductListMultiFilter / queryProductFilterFields 接口定义（url.ts 常量 + api.ts 函数，均为 POST）
- [x] Task 2: CategorySearch 新增 custom 条件类型（editor-\<field\> 插槽、hasValue/formatValue），值类型扩展为 Record\<string, string[]\>
- [x] Task 3: CategorySearchEditor 选项支持 count 徽标
- [x] Task 4: ColumnFilter.vue 值类型收窄兼容
- [x] Task 5: 新增 HeaderFilterPopover 表头漏斗弹层组件（多选面板/搜索/全选/数量徽标/插槽自定义面板）
- [x] Task 6: IncludeExcludeFilter 拆出 IncludeExcludePanel 三态面板，新增 iconOnly / inline 形态
- [x] Task 7: 新增 SortPopover 字段排序面板（草稿模式）
- [x] Task 8: 制品列表首屏重建：制品名称/动态属性列/解析状态/依赖包数量/License 数量/漏洞风险/详情入口
- [x] Task 9: License IDs/数量/合规性合并为列头单面板；包名关键字+精准搜索移入表头漏斗
- [x] Task 10: 动态属性列 caret 排序与 SortPopover 全局单字段排序共存
- [x] Task 11: 双版块互斥展开/收起；下钻收起为选中一行预览；筛选变更自动展开对应版块
- [x] Task 12: 筛选查询 GET 改 POST 避免 414；表头筛选条件透传 queryProductFilterFields
- [x] Task 13: 解析状态 tag + tooltip、按标签分组筛选值（expandScanStatusFilterValues）
- [x] Task 14: 轮询改为 setTimeout 链式调度，keep-alive 启停；刷新通知保留"刷新页面数据"按钮
- [x] Task 15: 表格高度固定（首屏 10 行测量一次）与漏洞徽标单行省略等样式打磨
- [x] Task 16: sbomHome.vue 移除单 tab 包装
