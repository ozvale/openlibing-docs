# 【openlibing-web】SBOM 成分分析筛选区改造 — 实现任务

## 进度: 12/12 complete

- [x] Task 1: licenseCompliance 筛选改为单选
- [x] Task 2: 移除漏洞级别"不涉及(NA)"选项
- [x] Task 3: 新增 querySbomPackagesVulCountSummary 接口定义（url.ts 常量 + api.ts 函数）
- [x] Task 4: 漏洞级别筛选从单选改为包含/排除双多选（queryInfo 拆分 includeVulSeverities / excludeVulSeverities）
- [x] Task 5: 新增 IncludeExcludeFilter 组件（el-popover + 三态切换 + 草稿模式）
- [x] Task 6: 面板内展示各级别漏洞数量（countMap prop + 括号包裹）
- [x] Task 7: 筛选变化时调用汇总接口，首次加载也触发
- [x] Task 8: 多选下拉 @change 防抖 400ms（licenseIds、licenseCount、dependencyTypes）
- [x] Task 9: licenseCount 改多选（值改数组，字段名不变）
- [x] Task 10: IncludeExcludeFilter 交互优化（点级别名切换、点已选按钮取消、清除图标、hover 效果）
- [x] Task 11: IncludeExcludeFilter trigger 视觉对齐 el-select（placeholder 浅灰、有值文字 #606266）
- [x] Task 12: 导出按钮文案"导出"→"全量导出"
