# 【openlibing-web】SBOM 成分分析筛选移入表头并支持排序 — 任务清单

## openlibing-sbom（后端，先行）

- [ ] 新增枚举 `PackageSortField`（NAME / DEPENDENCY_TYPE / LICENSE_COUNT / LICENSE_COMPLIANCE / 6×VUL_COUNT）
- [ ] `QuerySbomPackagesMultiFilterRequest` 新增 `sortField` / `sortDir`（getter/setter/toString）
- [ ] `PackageRepository#getPackageInfoByNameForPageBatch` ORDER BY 动态化（CASE 分块 × 2 方向 + 默认排序兜底）
- [ ] `PackageRepository#getPackagesByGroupPageBatch` 子查询 GROUP BY 增加聚合列 + 动态排序
- [ ] `SbomServiceImpl` 两个 multiFilter 方法透传排序 + 白名单/方向规范化 + 分组 Java 侧聚合排序
- [ ] `SbomServiceImplTest` / `SbomControllerTest` 新增/更新用例并通过
- [ ] 改动文件 pre-commit 通过

## openlibing-web（前端）

- [ ] 新增 `HeaderFilterPopover.vue`（漏斗触发器 + popover + active 高亮）
- [ ] `IncludeExcludeFilter.vue` 增加 icon-only 触发形态
- [ ] `index.vue` 移除 `search-filters` 区（保留 search-actions：漏洞依赖刷新 / 全量导出）
- [ ] 软件包名称列表头：package输入框 + 精准查询开关 + 合并展示开关
- [ ] 依赖类型列表头：多选面板
- [ ] 漏洞风险数值列表头：包含/排除筛选 + 排序级别选择（6 级 + 方向）
- [ ] License 列表头：License / License数量 / License合规性 + 排序选择
- [ ] 软件包名称、依赖类型列 `sortable="custom"` + `@sort-change`
- [ ] `sortState` 状态 + `queryList` 组参（sortField/sortDir）+ 排序变化重置页码
- [ ] 样式：表头漏斗间距/高亮、popover 宽度、移除旧筛选区样式
- [ ] pnpm build + vitest 回归
- [ ] 改动文件 pre-commit 通过

## 交付

- [ ] 用户审查代码（两仓 git diff）
- [ ] 用户确认后 commit（分仓提交，遵循 commit 规范）
- [ ] 合入测试环境分支 → 用户手动部署 gamma 验证
- [ ] 验证通过 → fork 推送 + issue + PR（ai-assisted 标签）
- [ ] spec 归档到 openlibing-docs（用户触发）
