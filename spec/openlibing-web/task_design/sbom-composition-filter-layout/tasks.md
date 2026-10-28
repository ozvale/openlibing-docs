# 【openlibing-web】SBOM 成分分析筛选栏布局优化 — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 拆分 `.search-params` 为 `.search-filters`（flex:1 + flex-wrap）与 `.search-actions`（flex-shrink:0）两个子区域
- [x] Task 2: `.query-item` 与操作按钮设置 `flex-shrink: 0`，筛选区支持自动换行，按钮固定第一行右上角
- [x] Task 3: 调整各筛选项宽度（License/License 数量/License 合规性/漏洞级别 180px，依赖类型 160px，package 240px）
- [x] Task 4: 125% 缩放与 100% 缩放下回归验证（布局正常，筛选/查询/重置/导出行为不变）
